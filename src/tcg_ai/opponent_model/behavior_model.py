"""
Opponent Behavioral Model & Multi-Response Simulator
Estimates P(opponent_action | game_state) across competitive psychological styles:
- AGGRESSIVE: Maximizes instant attack damage & knockouts
- DEFENSIVE: Focuses on preserving HP, healing, retreating damaged attackers
- PRIZE_RACE: Focuses on prize tempo and multi-prize targets
- SETUP: Prioritizes bench building, evolutions, and energy acceleration
- RESOURCE_CONSERVATION: Avoids wasteful discards, holds key combo cards
- OPTIMAL: Game-theoretic / Minimax best response
"""
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
from ..rules.rules_engine import RulesEngine
from ..cards.card_database import CardDatabase


class OpponentStrategy:
    AGGRESSIVE = "AGGRESSIVE"
    DEFENSIVE = "DEFENSIVE"
    PRIZE_RACE = "PRIZE_RACE"
    SETUP = "SETUP"
    RESOURCE_CONSERVATION = "RESOURCE_CONSERVATION"
    OPTIMAL = "OPTIMAL"


class OpponentBehaviorModel:
    def __init__(
        self,
        rules_engine: Optional[RulesEngine] = None,
        card_db: Optional[CardDatabase] = None,
        default_strategy: str = OpponentStrategy.OPTIMAL
    ):
        self.rules_engine = rules_engine or RulesEngine()
        self.card_db = card_db or CardDatabase.get_instance()
        self.strategy = default_strategy

    def score_opponent_action(
        self,
        action: Dict[str, Any],
        state: Dict[str, Any],
        strategy: str
    ) -> float:
        """Assigns a heuristic preference score to an opponent action under a given strategy profile."""
        act_type = action.get("action_type")
        player_active = (state.get("player") or {}).get("active_spot") or {}
        p_hp = player_active.get("current_hp", 100)

        score = 1.0

        if act_type == "ATTACK":
            dmg = action.get("base_damage", 0)
            is_lethal = dmg >= p_hp and p_hp > 0

            if strategy == OpponentStrategy.AGGRESSIVE:
                score += (dmg * 0.1) + (50.0 if is_lethal else 0.0)
            elif strategy == OpponentStrategy.PRIZE_RACE:
                prizes = action.get("prizes_to_gain", 1) if is_lethal else 0
                score += (prizes * 30.0) + (dmg * 0.05)
            elif strategy == OpponentStrategy.DEFENSIVE:
                score += (dmg * 0.05) + (20.0 if is_lethal else 0.0)
            elif strategy == OpponentStrategy.SETUP:
                score += (dmg * 0.04) + (25.0 if is_lethal else 0.0)
            else:  # OPTIMAL
                score += (dmg * 0.08) + (40.0 if is_lethal else 0.0)

        elif act_type == "ATTACH_ENERGY":
            if strategy in (OpponentStrategy.SETUP, OpponentStrategy.RESOURCE_CONSERVATION):
                score += 15.0
            else:
                score += 8.0

        elif act_type == "EVOLVE_POKEMON":
            score += 20.0 if strategy == OpponentStrategy.SETUP else 12.0

        elif act_type == "BENCH_POKEMON":
            score += 10.0 if strategy == OpponentStrategy.SETUP else 5.0

        elif act_type == "PLAY_SUPPORTER":
            score += 14.0

        elif act_type == "PLAY_ITEM":
            score += 8.0

        elif act_type == "RETREAT":
            opp_active = (state.get("opponent") or {}).get("active_spot") or {}
            opp_hp = opp_active.get("current_hp", 100)
            if opp_hp <= 40:
                score += 25.0 if strategy == OpponentStrategy.DEFENSIVE else 10.0
            else:
                score += 2.0

        elif act_type == "PASS_TURN":
            score = 0.1  # Usually least preferred unless no other options

        return max(0.1, score)

    def predict_action_distribution(
        self,
        hypothetical_state: Dict[str, Any],
        strategy: Optional[str] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Computes P(opponent_action | state) normalized as a probability distribution over legal opponent actions.
        """
        active_strategy = strategy or self.strategy
        legal_actions = self.rules_engine.generate_legal_actions(hypothetical_state, is_player=False)

        if not legal_actions:
            return [({"action_type": "PASS_TURN", "target": "SYSTEM"}, 1.0)]

        raw_scores = [self.score_opponent_action(a, hypothetical_state, active_strategy) for a in legal_actions]
        # Softmax with temperature
        temperature = 1.0 if active_strategy != OpponentStrategy.OPTIMAL else 0.5
        scaled = np.array(raw_scores) / temperature
        exp_s = np.exp(scaled - np.max(scaled))
        probs = exp_s / (np.sum(exp_s) + 1e-9)

        distribution = []
        for a, p in zip(legal_actions, probs):
            distribution.append((a, float(p)))

        # Sort descending by probability
        distribution.sort(key=lambda x: x[1], reverse=True)
        return distribution

    def sample_top_responses(
        self,
        hypothetical_state: Dict[str, Any],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Extracts the most probable opponent response moves with tactical descriptions.
        """
        dist = self.predict_action_distribution(hypothetical_state)
        responses = []
        for action, prob in dist[:top_k]:
            act_desc = action.get("action_type")
            if act_desc == "ATTACK":
                summary = f"Strikes with '{action.get('attack_name')}' for {action.get('base_damage', 0)} DMG"
            elif act_desc == "ATTACH_ENERGY":
                summary = f"Attaches {action.get('card_name')} to {action.get('target_pokemon')}"
            elif act_desc == "EVOLVE_POKEMON":
                summary = f"Evolves into {action.get('card_name')}"
            elif act_desc == "PLAY_SUPPORTER":
                summary = f"Plays Supporter '{action.get('card_name')}'"
            elif act_desc == "RETREAT":
                summary = f"Retreats damaged active into {action.get('switch_with')}"
            else:
                summary = f"Executes {act_desc}"

            responses.append({
                "action": action,
                "probability": round(prob, 4),
                "probability_pct": f"{prob * 100:.1f}%",
                "summary": summary,
                "is_dangerous": action.get("is_lethal", False) or (action.get("base_damage", 0) >= 80)
            })
        return responses
