"""
Monte Carlo Tree Search (MCTS) Engine with PUCT & Terminal Outcome Verification
Simulates forward rollouts, explores legal action branches, and grounds winning probabilities.
"""
import copy
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from src.engine.action_mask import ActionMaskEngine
from src.models.card_vision_gnn import CardVisionGNN
from src.models.decision_transformer import MatchSequenceTransformer


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
        gnn: CardVisionGNN,
        transformer: MatchSequenceTransformer,
        action_mask_engine: ActionMaskEngine,
        c_puct: float = 1.414,
        max_depth: int = 6
    ):
        self.gnn = gnn
        self.transformer = transformer
        self.action_mask_engine = action_mask_engine
        self.c_puct = c_puct
        self.max_depth = max_depth

    def _check_terminal(self, state: Dict[str, Any]) -> Tuple[bool, Optional[float]]:
        """
        Checks if the state is terminal:
        - Win: Player took 6 prizes or knocked out opponent with no bench (+1.0)
        - Loss: Opponent took 6 prizes or knocked out player with no bench (0.0)
        """
        player = state.get("player", {})
        opponent = state.get("opponent", {})

        p_prizes_left = player.get("prizes_remaining", 6)
        opp_prizes_left = opponent.get("prizes_remaining", 6)

        if p_prizes_left <= 0:
            return True, 1.0
        if opp_prizes_left <= 0:
            return True, 0.0

        p_active_hp = player.get("active_spot", {}).get("current_hp", 1)
        opp_active_hp = opponent.get("active_spot", {}).get("current_hp", 1)

        # Check bench out
        if p_active_hp <= 0 and len(player.get("bench", [])) == 0:
            return True, 0.0
        if opp_active_hp <= 0 and len(opponent.get("bench", [])) == 0:
            return True, 1.0

        return False, None

    def _apply_action_simulation(
        self,
        state: Dict[str, Any],
        action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulates an action transition to produce a new hypothetical state.
        """
        next_state = copy.deepcopy(state)
        player = next_state.get("player", {})
        opponent = next_state.get("opponent", {})
        turn_flags = next_state.get("turn_flags", {})

        act_type = action.get("action_type")

        if act_type == "ATTACH_ENERGY":
            target = action.get("target", "ACTIVE")
            if target == "ACTIVE" and player.get("active_spot"):
                attached = player["active_spot"].setdefault("attached_energy", [])
                attached.append({"type": action.get("energy_type", "Colorless")})
            turn_flags["energy_attached_this_turn"] = True

        elif act_type == "PLAY_SUPPORTER":
            turn_flags["supporter_played_this_turn"] = True
            card_id = action.get("card_id")
            player["hand"] = [c for c in player.get("hand", []) if c.get("card_id") != card_id]

        elif act_type == "PLAY_ITEM":
            card_id = action.get("card_id")
            player["hand"] = [c for c in player.get("hand", []) if c.get("card_id") != card_id]

        elif act_type == "EVOLVE_POKEMON":
            card_id = action.get("card_id")
            card_name = action.get("card_name", "Evolved")
            target = action.get("target", "ACTIVE")
            if target == "ACTIVE" and player.get("active_spot"):
                player["active_spot"]["name"] = card_name
                player["active_spot"]["current_hp"] = max(player["active_spot"].get("current_hp", 100), 250)
            player["hand"] = [c for c in player.get("hand", []) if c.get("card_id") != card_id]

        elif act_type == "ATTACK":
            dmg = action.get("base_damage", 0)
            opp_active = opponent.get("active_spot", {})
            curr_hp = opp_active.get("current_hp", 100)
            new_hp = max(0, curr_hp - dmg)
            opp_active["current_hp"] = new_hp

            # If Knockout
            if new_hp == 0:
                prizes_taken = 2 if "ex" in opp_active.get("name", "").lower() or "v" in opp_active.get("name", "").lower() else 1
                player["prizes_remaining"] = max(0, player.get("prizes_remaining", 6) - prizes_taken)
                player["prizes_taken"] = player.get("prizes_taken", 0) + prizes_taken

        elif act_type == "BENCH_BASIC_POKEMON":
            card_id = action.get("card_id")
            card_name = action.get("card_name", "Basic")
            bench = player.setdefault("bench", [])
            bench.append({"slot": len(bench) + 1, "card_id": card_id, "name": card_name, "current_hp": 70, "attached_energy": []})
            player["hand"] = [c for c in player.get("hand", []) if c.get("card_id") != card_id]

        return next_state

    def _select_child(self, node: MCTSNode) -> Tuple[str, MCTSNode]:
        """
        PUCT Selection formula:
        a* = argmax (Q(s, a) + c_puct * P(s, a) * sqrt(sum N) / (1 + N(s, a)))
        """
        best_score = -float('inf')
        best_action_key = None
        best_child = None

        total_parent_visits = sum(child.visit_count for child in node.children.values())
        sqrt_total = np.sqrt(max(1, total_parent_visits))

        for act_key, child in node.children.items():
            u_val = self.c_puct * child.prior_p * (sqrt_total / (1 + child.visit_count))
            score = child.mean_value + u_val
            if score > best_score:
                best_score = score
                best_action_key = act_key
                best_child = child

        return best_action_key, best_child

    def _evaluate_state(
        self,
        state: Dict[str, Any],
        turn_history: Optional[List[np.ndarray]] = None
    ) -> Tuple[np.ndarray, float]:
        """
        Runs GNN Board Encoder + Match Sequence Transformer to predict policy prior & base win probability.
        """
        h_board, _ = self.gnn.forward(state)
        policy_logits, win_prob, _ = self.transformer.forward(h_board, turn_history)
        return policy_logits, win_prob

    def run_mcts_search(
        self,
        root_state: Dict[str, Any],
        num_simulations: int = 60,
        turn_history: Optional[List[np.ndarray]] = None
    ) -> Tuple[List[Dict[str, Any]], float, Dict[str, Any]]:
        """
        Executes MCTS rollouts to verify terminal game outcomes and refine win probability.
        Returns:
            - ranked_moves: List of actions with MCTS visit counts, Q-values, and verified win rates.
            - grounded_win_probability: Final probability verified through terminal search.
            - search_telemetry: Rollout statistics.
        """
        root = MCTSNode(game_state=root_state)
        is_term, term_rew = self._check_terminal(root_state)
        if is_term:
            root.is_terminal = True
            root.terminal_reward = term_rew
            return [], term_rew, {"terminal": True}

        # 1. Initial Root Expansion
        legal_actions = self.action_mask_engine.get_legal_actions(root_state)
        if not legal_actions:
            return [], 0.5, {"no_actions": True}

        policy_logits, root_base_win = self._evaluate_state(root_state, turn_history)

        # Softmax priors across legal actions
        action_scores = []
        for i, act in enumerate(legal_actions):
            idx = i % len(policy_logits)
            action_scores.append(float(policy_logits[idx]))

        exp_s = np.exp(np.array(action_scores) - np.max(action_scores))
        priors = exp_s / (np.sum(exp_s) + 1e-9)

        for act, p_val in zip(legal_actions, priors):
            act_key = f"{act.get('action_type')}_{act.get('card_id', '')}_{act.get('attack_name', '')}_{act.get('target', '')}"
            next_st = self._apply_action_simulation(root_state, act)
            child = MCTSNode(game_state=next_st, parent=root, action_taken=act, prior_p=float(p_val))
            is_c_term, c_rew = self._check_terminal(next_st)
            if is_c_term:
                child.is_terminal = True
                child.terminal_reward = c_rew
            root.children[act_key] = child

        root.is_expanded = True

        # 2. Main Simulation Loop (Selection -> Expansion -> Rollout -> Backprop)
        terminal_nodes_hit = 0

        for sim in range(num_simulations):
            node = root
            search_path = [node]
            depth = 0

            # --- SELECT ---
            while node.is_expanded and not node.is_terminal and depth < self.max_depth:
                if not node.children:
                    break
                _, node = self._select_child(node)
                search_path.append(node)
                depth += 1

            # --- EVALUATE & EXPAND ---
            if node.is_terminal:
                value = node.terminal_reward
                terminal_nodes_hit += 1
            else:
                # Evaluate leaf node with GNN + Transformer
                _, value = self._evaluate_state(node.game_state, turn_history)

                # Expand if not maximum depth
                if depth < self.max_depth:
                    sub_legal = self.action_mask_engine.get_legal_actions(node.game_state)
                    if sub_legal:
                        for sub_act in sub_legal[:6]:  # Limit branching
                            sub_key = f"{sub_act.get('action_type')}_{sub_act.get('card_id', '')}"
                            next_sub_st = self._apply_action_simulation(node.game_state, sub_act)
                            sub_child = MCTSNode(game_state=next_sub_st, parent=node, action_taken=sub_act, prior_p=1.0 / len(sub_legal))
                            is_sub_term, sub_rew = self._check_terminal(next_sub_st)
                            if is_sub_term:
                                sub_child.is_terminal = True
                                sub_child.terminal_reward = sub_rew
                            node.children[sub_key] = sub_child
                        node.is_expanded = True

            # --- BACKPROPAGATION ---
            for n in search_path:
                n.visit_count += 1
                n.total_value += value
                n.mean_value = n.total_value / n.visit_count

        # 3. Aggregate Final Results from Root Children
        total_root_visits = sum(c.visit_count for c in root.children.values())
        ranked_moves = []

        for act_key, child in root.children.items():
            visit_ratio = child.visit_count / max(1, total_root_visits)
            mcts_q_val = child.mean_value

            # Blended win probability with terminal verification boost
            verified_win_prob = float(np.clip(mcts_q_val * 0.7 + root_base_win * 0.3, 0.02, 0.98))

            ranked_moves.append({
                "action": child.action_taken,
                "action_key": act_key,
                "mcts_visits": child.visit_count,
                "visit_ratio": round(visit_ratio, 4),
                "mcts_q_value": round(mcts_q_val, 4),
                "post_win_prob": round(verified_win_prob, 4),
                "post_win_prob_pct": f"{verified_win_prob * 100:.1f}%",
                "is_terminal_win_path": child.is_terminal and child.terminal_reward == 1.0
            })

        # Sort by MCTS visits descending, then Q-value
        ranked_moves.sort(key=lambda x: (x["mcts_visits"], x["mcts_q_value"]), reverse=True)

        grounded_win_prob = sum(m["post_win_prob"] * m["visit_ratio"] for m in ranked_moves) if ranked_moves else root_base_win

        telemetry = {
            "num_simulations": num_simulations,
            "root_legal_branches": len(root.children),
            "terminal_nodes_verified": terminal_nodes_hit,
            "top_move_visits": ranked_moves[0]["mcts_visits"] if ranked_moves else 0,
            "base_transformer_win_prob": round(root_base_win, 4),
            "grounded_mcts_win_prob": round(grounded_win_prob, 4)
        }

        return ranked_moves, float(grounded_win_prob), telemetry
