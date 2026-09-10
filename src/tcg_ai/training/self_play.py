"""
Self-Play Training & Weight Optimization Engine
Simulates AI vs AI matches with asymmetric strategies and exploration parameters.
Collects POMDP trajectories without data leakage and trains the DualHeadNeuralEvaluator.
"""
import copy
import random
from typing import Dict, List, Any, Tuple, Optional
from ..rules.rules_engine import RulesEngine
from ..opponent_model.behavior_model import OpponentBehaviorModel, OpponentStrategy
from ..state.game_state import GameStateManager
from ..ml.neural_evaluator import DualHeadNeuralEvaluator


class SelfPlayTrainer:
    def __init__(
        self,
        neural_evaluator: Optional[DualHeadNeuralEvaluator] = None,
        rules_engine: Optional[RulesEngine] = None,
        state_manager: Optional[GameStateManager] = None
    ):
        self.neural_evaluator = neural_evaluator or DualHeadNeuralEvaluator()
        self.rules_engine = rules_engine or RulesEngine()
        self.state_manager = state_manager or GameStateManager()

    def generate_initial_match_state(self) -> Dict[str, Any]:
        """Generates a competitive initial 6-prize state for self-play training."""
        return {
            "turn_number": 1,
            "turn_flags": {
                "energy_attached_this_turn": False,
                "supporter_played_this_turn": False,
                "retreated_this_turn": False
            },
            "player": {
                "active_spot": {"name": "Miraidon ex", "current_hp": 220, "max_hp": 220, "attached_energy": [{"type": "Lightning"}]},
                "bench": [
                    {"name": "Pikachu", "current_hp": 60, "max_hp": 60, "attached_energy": []},
                    {"name": "Zapdos", "current_hp": 120, "max_hp": 120, "attached_energy": []}
                ],
                "hand": ["Basic Lightning Energy", "Professor's Research", "Ultra Ball", "Switch"],
                "prizes_remaining": 6,
                "prizes_taken": 0,
                "deck_count": 47,
                "discard": []
            },
            "opponent": {
                "active_spot": {"name": "Charizard ex", "current_hp": 330, "max_hp": 330, "attached_energy": [{"type": "Fire"}, {"type": "Fire"}]},
                "bench": [
                    {"name": "Charmander", "current_hp": 70, "max_hp": 70, "attached_energy": []},
                    {"name": "Pidgey", "current_hp": 60, "max_hp": 60, "attached_energy": []}
                ],
                "hand_count": 5,
                "known_hand": [],
                "prizes_remaining": 6,
                "prizes_taken": 0,
                "deck_count": 47,
                "discard": []
            }
        }

    def play_training_game(
        self,
        strategy_a: str = OpponentStrategy.OPTIMAL,
        strategy_b: str = OpponentStrategy.AGGRESSIVE,
        max_turns: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Plays one complete AI vs AI game, recording decision transitions:
        (state_vec, action_idx, reward)
        """
        state = self.generate_initial_match_state()
        trajectory: List[Dict[str, Any]] = []

        opp_model = OpponentBehaviorModel(rules_engine=self.rules_engine, default_strategy=strategy_b)

        winner = None
        for turn in range(1, max_turns + 1):
            state["turn_number"] = turn
            state["turn_flags"] = {
                "energy_attached_this_turn": False,
                "supporter_played_this_turn": False,
                "retreated_this_turn": False
            }

            # --- Player Move (Agent A) ---
            p_legal = self.rules_engine.generate_legal_actions(state, is_player=True)
            if not p_legal:
                break

            s_vec = self.state_manager.encode_feature_vector(state)
            ranked = self.neural_evaluator.rank_actions_with_prior(s_vec, p_legal)
            # Epsilon-greedy exploration during self-play
            if random.random() < 0.15:
                chosen_act = random.choice(p_legal)
            else:
                chosen_act = ranked[0][0]

            act_idx = self.neural_evaluator.map_action_to_index(chosen_act)
            trajectory.append({
                "state_vector": s_vec,
                "action_index": act_idx,
                "player": "A"
            })

            # Execute Player move
            self._apply_inplace(state, chosen_act, is_player=True)

            # Check win condition
            if state["player"]["prizes_remaining"] <= 0:
                winner = "A"
                break
            if state["opponent"]["active_spot"]["current_hp"] <= 0 and len(state["opponent"]["bench"]) == 0:
                winner = "A"
                break

            # --- Opponent Move (Agent B) ---
            opp_dist = opp_model.predict_action_distribution(state)
            if opp_dist:
                opp_act = opp_dist[0][0]
                self._apply_inplace(state, opp_act, is_player=False)

            if state["opponent"]["prizes_remaining"] <= 0:
                winner = "B"
                break
            if state["player"]["active_spot"]["current_hp"] <= 0 and len(state["player"]["bench"]) == 0:
                winner = "B"
                break

        final_reward = 1.0 if winner == "A" else (-1.0 if winner == "B" else 0.0)
        for entry in trajectory:
            entry["reward"] = final_reward

        return trajectory

    def train_on_self_play(self, num_games: int = 15, lr: float = 0.002) -> Dict[str, Any]:
        """
        Executes self-play match iterations and trains neural evaluator on experience buffer.
        """
        all_transitions = []
        for _ in range(num_games):
            traj = self.play_training_game()
            all_transitions.extend(traj)

        losses = []
        for item in all_transitions:
            loss = self.neural_evaluator.train_step(
                state_vec=item["state_vector"],
                target_value=item["reward"],
                target_action_idx=item["action_index"],
                lr=lr
            )
            losses.append(loss)

        avg_loss = sum(losses) / max(1, len(losses))
        return {
            "num_games_simulated": num_games,
            "transitions_trained": len(all_transitions),
            "average_training_loss": round(avg_loss, 5)
        }

    def _apply_inplace(self, state: Dict[str, Any], action: Dict[str, Any], is_player: bool):
        actor = state["player" if is_player else "opponent"]
        other = state["opponent" if is_player else "player"]

        act_type = action.get("action_type")
        if act_type == "ATTACK":
            dmg = action.get("base_damage", 0)
            opp_act = other["active_spot"]
            new_hp = max(0, opp_act.get("current_hp", 100) - dmg)
            opp_act["current_hp"] = new_hp
            if new_hp == 0:
                prizes = action.get("prizes_to_gain", 1)
                actor["prizes_remaining"] = max(0, actor["prizes_remaining"] - prizes)
                actor["prizes_taken"] += prizes
                if other.get("bench"):
                    other["active_spot"] = other["bench"].pop(0)
        elif act_type == "ATTACH_ENERGY":
            actor["active_spot"].setdefault("attached_energy", []).append({"type": "Colorless"})
            if is_player:
                state["turn_flags"]["energy_attached_this_turn"] = True


def run_self_play_benchmark(num_games: int = 10) -> Dict[str, Any]:
    trainer = SelfPlayTrainer()
    result = trainer.train_on_self_play(num_games=num_games)
    print(f"Self-Play Benchmark Completed: {result}")
    return result
