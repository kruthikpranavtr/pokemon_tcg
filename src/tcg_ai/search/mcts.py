"""
Monte Carlo Tree Search (MCTS) Engine for POMDP TCG Environments
Implements:
- PUCT Selection with progressive widening:
  UCB_i = Q_i/N_i + C * prior_i * sqrt(ln(N_parent)) / (1 + N_i)
- Expansion of legal moves only (strict rules engine enforcement)
- Belief-state multi-turn rollouts incorporating Opponent Behavior Model
- Grounded terminal backpropagation (Prize exhaustion & bench-out victories)
"""
import copy
import math
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from ..rules.rules_engine import RulesEngine
from ..opponent_model.behavior_model import OpponentBehaviorModel
from ..ml.neural_evaluator import DualHeadNeuralEvaluator
from ..state.game_state import GameStateManager


class MCTSNode:
    def __init__(
        self,
        game_state: Dict[str, Any],
        parent: Optional['MCTSNode'] = None,
        action_taken: Optional[Dict[str, Any]] = None,
        prior_p: float = 1.0
    ):
        self.game_state = game_state
        self.parent = parent
        self.action_taken = action_taken
        self.prior_p = prior_p

        self.children: Dict[str, 'MCTSNode'] = {}
        self.visit_count: int = 0
        self.total_value: float = 0.0
        self.mean_value: float = 0.5
        self.is_expanded: bool = False
        self.is_terminal: bool = False
        self.terminal_reward: Optional[float] = None

    def get_q_value(self) -> float:
        return self.mean_value if self.visit_count > 0 else self.prior_p


class MCTSEngine:
    def __init__(
        self,
        rules_engine: Optional[RulesEngine] = None,
        opponent_model: Optional[OpponentBehaviorModel] = None,
        neural_evaluator: Optional[DualHeadNeuralEvaluator] = None,
        state_manager: Optional[GameStateManager] = None,
        c_puct: float = 1.414,
        max_depth: int = 6,
        progressive_widening_k: float = 2.0,
        progressive_widening_alpha: float = 0.5
    ):
        self.rules_engine = rules_engine or RulesEngine()
        self.opponent_model = opponent_model or OpponentBehaviorModel()
        self.neural_evaluator = neural_evaluator or DualHeadNeuralEvaluator()
        self.state_manager = state_manager or GameStateManager()
        self.c_puct = c_puct
        self.max_depth = max_depth
        self.pw_k = progressive_widening_k
        self.pw_alpha = progressive_widening_alpha

    def check_terminal(self, state: Dict[str, Any]) -> Tuple[bool, Optional[float]]:
        """
        Terminal conditions:
        - Win (+1.0): Player took 6 prizes or opponent has 0 HP and 0 bench
        - Loss (0.0): Opponent took 6 prizes or player has 0 HP and 0 bench
        """
        player = state.get("player", {})
        opp = state.get("opponent", {})

        p_prizes = player.get("prizes_remaining", 6)
        opp_prizes = opp.get("prizes_remaining", 6)

        if p_prizes <= 0:
            return True, 1.0
        if opp_prizes <= 0:
            return True, 0.0

        p_act_hp = (player.get("active_spot") or {}).get("current_hp", 1)
        opp_act_hp = (opp.get("active_spot") or {}).get("current_hp", 1)

        if opp_act_hp <= 0 and len(opp.get("bench", [])) == 0:
            return True, 1.0
        if p_act_hp <= 0 and len(player.get("bench", [])) == 0:
            return True, 0.0

        return False, None

    def apply_action(
        self,
        state: Dict[str, Any],
        action: Dict[str, Any],
        is_player: bool = True
    ) -> Dict[str, Any]:
        """
        Simulates execution of an action and transitions the state deterministically.
        """
        next_state = copy.deepcopy(state)
        actor = next_state.get("player" if is_player else "opponent", {})
        other = next_state.get("opponent" if is_player else "player", {})
        turn_flags = next_state.get("turn_flags", {})

        act_type = action.get("action_type")

        if act_type == "ATTACK":
            dmg = action.get("base_damage", 0)
            target = other.get("active_spot") or {}
            curr_hp = target.get("current_hp", 100)
            new_hp = max(0, curr_hp - dmg)
            target["current_hp"] = new_hp

            if new_hp == 0:
                prizes_to_take = action.get("prizes_to_gain", 1)
                actor["prizes_remaining"] = max(0, actor.get("prizes_remaining", 6) - prizes_to_take)
                actor["prizes_taken"] = actor.get("prizes_taken", 0) + prizes_to_take

                # Promote from bench if available
                bench = other.get("bench", [])
                if bench:
                    promoted = bench.pop(0)
                    other["active_spot"] = {
                        "name": promoted.get("name"),
                        "current_hp": promoted.get("current_hp", 70),
                        "max_hp": promoted.get("max_hp", 70),
                        "attached_energy": promoted.get("attached_energy", [])
                    }

        elif act_type == "ATTACH_ENERGY":
            target = action.get("target")
            cname = action.get("card_name", "Basic Energy")
            energy_entry = {"type": cname.replace("Basic", "").replace("Energy", "").strip() or "Colorless"}

            if target == "ACTIVE" and actor.get("active_spot"):
                actor["active_spot"].setdefault("attached_energy", []).append(energy_entry)
            elif target == "BENCH":
                t_name = action.get("target_pokemon")
                for b in actor.get("bench", []):
                    if b.get("name") == t_name:
                        b.setdefault("attached_energy", []).append(energy_entry)
                        break
            if is_player:
                turn_flags["energy_attached_this_turn"] = True

        elif act_type == "BENCH_POKEMON":
            cname = action.get("card_name", "Basic")
            cid = action.get("card_id", "c-basic")
            actor.setdefault("bench", []).append({
                "name": cname,
                "card_id": cid,
                "current_hp": 70,
                "max_hp": 70,
                "attached_energy": []
            })
            if "hand" in actor:
                actor["hand"] = [c for c in actor["hand"] if (c.get("card_id") if isinstance(c, dict) else c) != cid]

        elif act_type == "EVOLVE_POKEMON":
            cname = action.get("card_name", "Evolved")
            target = action.get("target")
            meta = self.rules_engine.card_db.get_meta(cname)
            new_hp = meta.get("hp", 150)

            if target == "ACTIVE" and actor.get("active_spot"):
                actor["active_spot"]["name"] = cname
                actor["active_spot"]["max_hp"] = new_hp
                actor["active_spot"]["current_hp"] = new_hp
            elif target == "BENCH":
                t_name = action.get("target_pokemon")
                for b in actor.get("bench", []):
                    if b.get("name") == t_name:
                        b["name"] = cname
                        b["max_hp"] = new_hp
                        b["current_hp"] = new_hp
                        break

        elif act_type == "RETREAT":
            switch_name = action.get("switch_with")
            bench = actor.get("bench", [])
            for i, b in enumerate(bench):
                if b.get("name") == switch_name:
                    old_active = actor.get("active_spot")
                    actor["active_spot"] = b
                    bench[i] = old_active
                    break
            if is_player:
                turn_flags["retreated_this_turn"] = True

        elif act_type == "PLAY_SUPPORTER":
            if is_player:
                turn_flags["supporter_played_this_turn"] = True

        return next_state

    def select_child(self, node: MCTSNode) -> Tuple[str, MCTSNode]:
        """
        PUCT selection with progressive widening.
        """
        best_score = -float('inf')
        best_key = None
        best_child = None

        total_parent_visits = sum(c.visit_count for c in node.children.values())
        sqrt_n = math.sqrt(max(1, total_parent_visits))

        # Progressive widening threshold
        max_allowed_children = max(2, int(self.pw_k * (node.visit_count ** self.pw_alpha)))
        items = list(node.children.items())[:max_allowed_children]

        for act_key, child in items:
            u_val = self.c_puct * child.prior_p * (sqrt_n / (1.0 + child.visit_count))
            score = child.mean_value + u_val
            if score > best_score:
                best_score = score
                best_key = act_key
                best_child = child

        return best_key, best_child

    def search(
        self,
        root_state: Dict[str, Any],
        num_simulations: int = 60
    ) -> Tuple[List[Dict[str, Any]], float, Dict[str, Any]]:
        """
        Executes MCTS simulations and returns:
        - ranked_actions: List of evaluated legal moves with visit counts, Q-values, win rates
        - grounded_win_prob: Win probability computed from tree rollouts
        - telemetry: Search metadata (terminal hits, depth, nodes explored)
        """
        root = MCTSNode(game_state=root_state)
        is_term, term_rew = self.check_terminal(root_state)
        if is_term:
            root.is_terminal = True
            root.terminal_reward = term_rew
            return [], term_rew, {"terminal": True, "simulations": 0}

        legal_actions = self.rules_engine.generate_legal_actions(root_state, is_player=True)
        if not legal_actions:
            return [], 0.5, {"no_actions": True, "simulations": 0}

        # Prior probabilities from Neural Evaluator
        state_vec = self.state_manager.encode_feature_vector(root_state)
        ranked_priors = self.neural_evaluator.rank_actions_with_prior(state_vec, legal_actions)
        prior_map = {id(a): p for a, p in ranked_priors}

        for i, act in enumerate(legal_actions):
            act_key = f"{act.get('action_type')}_{act.get('card_name', '')}_{act.get('attack_name', '')}_{i}"
            next_st = self.apply_action(root_state, act, is_player=True)
            prior = prior_map.get(id(act), 1.0 / len(legal_actions))
            child = MCTSNode(game_state=next_st, parent=root, action_taken=act, prior_p=prior)

            is_c_term, c_rew = self.check_terminal(next_st)
            if is_c_term:
                child.is_terminal = True
                child.terminal_reward = c_rew
            root.children[act_key] = child

        root.is_expanded = True
        terminal_nodes_hit = 0

        # Main Simulation Loop
        for _ in range(num_simulations):
            node = root
            search_path = [node]
            depth = 0

            # 1. SELECT
            while node.is_expanded and not node.is_terminal and depth < self.max_depth:
                if not node.children:
                    break
                _, node = self.select_child(node)
                search_path.append(node)
                depth += 1

            # 2. EXPAND & SIMULATE
            if node.is_terminal:
                value = node.terminal_reward
                terminal_nodes_hit += 1
            else:
                # Simulate opponent response
                opp_top_responses = self.opponent_model.sample_top_responses(node.game_state, top_k=2)
                if opp_top_responses:
                    best_opp_act = opp_top_responses[0]["action"]
                    hypo_st = self.apply_action(node.game_state, best_opp_act, is_player=False)
                else:
                    hypo_st = node.game_state

                # Neural / Heuristic Value estimation
                s_vec = self.state_manager.encode_feature_vector(hypo_st)
                _, win_prob, _ = self.neural_evaluator.forward(s_vec)
                value = win_prob

            # 3. BACKPROPAGATE
            for n in reversed(search_path):
                n.visit_count += 1
                n.total_value += value
                n.mean_value = n.total_value / n.visit_count

        # Extract ranked results
        total_root_visits = sum(c.visit_count for c in root.children.values())
        ranked_actions = []

        for child in root.children.values():
            act = child.action_taken
            win_p = child.mean_value
            ranked_actions.append({
                "action": act,
                "action_type": act.get("action_type"),
                "card_name": act.get("card_name") or act.get("attack_name") or "Action",
                "mcts_visits": child.visit_count,
                "mcts_q_value": round(child.mean_value, 4),
                "win_probability": round(win_p, 4),
                "win_probability_pct": f"{win_p * 100:.1f}%",
                "prior_probability": round(child.prior_p, 4)
            })

        # Sort descending by visit count then win probability
        ranked_actions.sort(key=lambda x: (x["mcts_visits"], x["win_probability"]), reverse=True)

        grounded_prob = ranked_actions[0]["win_probability"] if ranked_actions else 0.5
        telemetry = {
            "num_simulations": num_simulations,
            "root_visits": total_root_visits,
            "terminal_nodes_hit": terminal_nodes_hit,
            "max_search_depth": self.max_depth,
            "c_puct": self.c_puct
        }

        return ranked_actions, grounded_prob, telemetry
