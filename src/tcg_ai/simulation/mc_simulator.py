"""
Monte Carlo Rollout Simulator & Statistical Confidence Engine
Simulates thousands of stochastic trajectories over belief states:
1. Sample hidden opponent cards from Bayesian belief distribution
2. Sample card draws
3. Execute player action -> Opponent model response -> Follow-up moves
4. Return Win Rate, Loss Rate, Expected Prizes, Expected Damage, Risk, and 95% Confidence Interval
"""
import copy
import math
import random
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from ..rules.rules_engine import RulesEngine
from ..opponent_model.behavior_model import OpponentBehaviorModel
from ..probability.belief_state import BeliefStateTracker
from ..evaluation.evaluator import PositionEvaluator


class MonteCarloSimulator:
    def __init__(
        self,
        rules_engine: Optional[RulesEngine] = None,
        opponent_model: Optional[OpponentBehaviorModel] = None,
        belief_tracker: Optional[BeliefStateTracker] = None,
        evaluator: Optional[PositionEvaluator] = None
    ):
        self.rules_engine = rules_engine or RulesEngine()
        self.opponent_model = opponent_model or OpponentBehaviorModel()
        self.belief_tracker = belief_tracker or BeliefStateTracker()
        self.evaluator = evaluator or PositionEvaluator()

    def simulate_action_rollouts(
        self,
        state: Dict[str, Any],
        action: Dict[str, Any],
        num_rollouts: int = 100,
        rollout_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Executes N stochastic Monte Carlo rollouts starting from state after action.
        """
        wins = 0
        losses = 0
        draws = 0
        prizes_accum = []
        damage_accum = []

        for _ in range(num_rollouts):
            # 1. Sample hidden state from Bayesian belief distribution
            hypo_state = self.belief_tracker.sample_belief_state(state)

            # 2. Apply player action
            hypo_state = self._apply_quick_action(hypo_state, action, is_player=True)

            # Check immediate outcome
            p_prizes = hypo_state["player"].get("prizes_remaining", 6)
            opp_prizes = hypo_state["opponent"].get("prizes_remaining", 6)
            opp_act_hp = (hypo_state["opponent"].get("active_spot") or {}).get("current_hp", 1)

            damage_accum.append(action.get("base_damage", 0))

            if p_prizes <= 0 or (opp_act_hp <= 0 and len(hypo_state["opponent"].get("bench", [])) == 0):
                wins += 1
                prizes_accum.append(6 - p_prizes)
                continue

            # 3. Multi-turn step simulation
            sim_state = hypo_state
            for _ in range(rollout_depth):
                # Opponent response
                opp_responses = self.opponent_model.sample_top_responses(sim_state, top_k=2)
                if opp_responses:
                    # Sample probabilistically
                    probs = [r["probability"] for r in opp_responses]
                    chosen_opp = random.choices(opp_responses, weights=probs, k=1)[0]["action"]
                    sim_state = self._apply_quick_action(sim_state, chosen_opp, is_player=False)

                # Check terminal after opponent
                p_prizes_curr = sim_state["player"].get("prizes_remaining", 6)
                opp_prizes_curr = sim_state["opponent"].get("prizes_remaining", 6)
                p_act_hp_curr = (sim_state["player"].get("active_spot") or {}).get("current_hp", 1)

                if opp_prizes_curr <= 0 or (p_act_hp_curr <= 0 and len(sim_state["player"].get("bench", [])) == 0):
                    losses += 1
                    break

                # Player reply action
                p_legal = self.rules_engine.generate_legal_actions(sim_state, is_player=True)
                if p_legal:
                    # Pick an attack or advance move
                    p_atk = [a for a in p_legal if a.get("action_type") == "ATTACK"]
                    chosen_p = p_atk[0] if p_atk else p_legal[0]
                    sim_state = self._apply_quick_action(sim_state, chosen_p, is_player=True)

                if sim_state["player"].get("prizes_remaining", 6) <= 0:
                    wins += 1
                    break
            else:
                # Intermediate leaf evaluation: position_value represents win probability
                eval_res = self.evaluator.evaluate_position(sim_state)
                pos_val = eval_res["position_value"]
                wins += pos_val
                losses += (1.0 - pos_val)

            prizes_accum.append(6 - sim_state["player"].get("prizes_remaining", 6))

        # Statistical Calculations
        win_rate = max(0.01, min(0.99, wins / max(1, num_rollouts)))
        loss_rate = max(0.01, min(0.99, losses / max(1, num_rollouts)))
        draw_rate = 0.0

        # 95% Confidence Interval: p +/- 1.96 * sqrt(p(1-p)/N)
        std_err = math.sqrt(max(0.0, win_rate * (1.0 - win_rate)) / max(1, num_rollouts))
        ci_lower = max(0.0, win_rate - 1.96 * std_err)
        ci_upper = min(1.0, win_rate + 1.96 * std_err)

        avg_prizes = sum(prizes_accum) / max(1, len(prizes_accum))
        avg_damage = sum(damage_accum) / max(1, len(damage_accum))

        # Risk metric based on variance and loss rate
        risk_score = (loss_rate * 0.7) + (std_err * 0.3)
        risk_level = "HIGH" if risk_score >= 0.45 else ("MEDIUM" if risk_score >= 0.25 else "LOW")

        return {
            "num_rollouts": num_rollouts,
            "win_rate": round(win_rate, 4),
            "win_rate_pct": f"{win_rate * 100:.1f}%",
            "loss_rate": round(loss_rate, 4),
            "draw_rate": round(draw_rate, 4),
            "confidence_interval_95": [round(ci_lower, 4), round(ci_upper, 4)],
            "confidence_interval_95_str": f"[{ci_lower * 100:.1f}%, {ci_upper * 100:.1f}%]",
            "expected_prizes": round(avg_prizes, 2),
            "expected_damage": round(avg_damage, 1),
            "risk_score": round(risk_score, 4),
            "risk_level": risk_level
        }

    def _apply_quick_action(
        self,
        state: Dict[str, Any],
        action: Dict[str, Any],
        is_player: bool = True
    ) -> Dict[str, Any]:
        """Fast state update for rollouts."""
        actor = state["player" if is_player else "opponent"]
        other = state["opponent" if is_player else "player"]

        act_type = action.get("action_type")
        if act_type == "ATTACK":
            dmg = action.get("base_damage", 0)
            opp_act = other.get("active_spot") or {}
            new_hp = max(0, opp_act.get("current_hp", 100) - dmg)
            opp_act["current_hp"] = new_hp
            if new_hp == 0:
                prizes = action.get("prizes_to_gain", 1)
                actor["prizes_remaining"] = max(0, actor.get("prizes_remaining", 6) - prizes)
                actor["prizes_taken"] = actor.get("prizes_taken", 0) + prizes
                if other.get("bench"):
                    promoted = other["bench"].pop(0)
                    other["active_spot"] = {
                        "name": promoted.get("name"),
                        "current_hp": promoted.get("current_hp", 70),
                        "max_hp": promoted.get("max_hp", 70),
                        "attached_energy": promoted.get("attached_energy", [])
                    }
        elif act_type == "ATTACH_ENERGY":
            if actor.get("active_spot"):
                actor["active_spot"].setdefault("attached_energy", []).append({"type": "Colorless"})

        return state
