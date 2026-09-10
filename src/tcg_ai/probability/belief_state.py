"""
Bayesian Hidden Information Engine & Belief State Particle Sampler
Strictly adheres to Information Honesty:
- Categorizes all card state as KNOWN, UNKNOWN, INFERRED, or PROBABILISTIC
- Maintains Bayesian probability distribution P(card | evidence)
- Generates normalized particle samples S_1, ..., S_n for MCTS and Monte Carlo rollouts
"""
import copy
import random
from typing import Dict, List, Any, Tuple, Optional
from ..cards.card_database import CardDatabase


class InformationCategory:
    KNOWN = "KNOWN"              # Cards directly visible (Active, Bench, Discard, Revealed Hand)
    INFERRED = "INFERRED"        # Strongly inferred from deck archetype or search history
    PROBABILISTIC = "PROBABILISTIC" # Estimated via prior distribution and deck subtraction
    UNKNOWN = "UNKNOWN"          # Unrevealed cards in face-down prizes or shuffled deck


class BeliefStateTracker:
    def __init__(self, card_db: Optional[CardDatabase] = None):
        self.card_db = card_db or CardDatabase.get_instance()

    def build_information_audit(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates an audit clearly categorizing all card entities into:
        KNOWN, INFERRED, PROBABILISTIC, UNKNOWN.
        Never claims an unrevealed card is known with certainty.
        """
        player = game_state.get("player", {})
        opp = game_state.get("opponent", {})

        known_items = []
        inferred_items = []
        probabilistic_items = []
        unknown_items = []

        # Known Player side
        if player.get("active_spot"):
            known_items.append(f"Player Active: {player['active_spot'].get('name')}")
        for i, b in enumerate(player.get("bench", [])):
            known_items.append(f"Player Bench #{i+1}: {b.get('name')}")
        for c in player.get("hand", []):
            name = c.get("name") if isinstance(c, dict) else c
            known_items.append(f"Player Hand: {name}")
        for c in player.get("discard", []):
            name = c.get("name") if isinstance(c, dict) else c
            known_items.append(f"Player Discard: {name}")

        # Known Opponent side
        if opp.get("active_spot"):
            known_items.append(f"Opponent Active: {opp['active_spot'].get('name')}")
        for i, b in enumerate(opp.get("bench", [])):
            known_items.append(f"Opponent Bench #{i+1}: {b.get('name')}")
        for c in opp.get("discard", []):
            name = c.get("name") if isinstance(c, dict) else c
            known_items.append(f"Opponent Discard: {name}")
        for c in opp.get("known_hand", []):
            name = c.get("name") if isinstance(c, dict) else c
            known_items.append(f"Opponent Revealed Hand: {name}")

        # Unknown & Probabilistic
        opp_hidden_hand = max(0, opp.get("hand_count", 5) - len(opp.get("known_hand", [])))
        if opp_hidden_hand > 0:
            probabilistic_items.append(f"Opponent Unrevealed Hand ({opp_hidden_hand} cards)")
        
        opp_deck_count = opp.get("deck_count", 40)
        probabilistic_items.append(f"Opponent Deck Pool ({opp_deck_count} cards remaining)")

        p_prizes = player.get("prizes_remaining", 6)
        opp_prizes = opp.get("prizes_remaining", 6)
        unknown_items.append(f"Player Unrevealed Prize Pool ({p_prizes} cards)")
        unknown_items.append(f"Opponent Unrevealed Prize Pool ({opp_prizes} cards)")

        # Archetype inference
        opp_act_name = (opp.get("active_spot") or {}).get("name", "")
        if "charizard" in opp_act_name.lower():
            inferred_items.append("Opponent Archetype: Darkness/Fire Charizard ex Engine")
        elif "miraidon" in opp_act_name.lower():
            inferred_items.append("Opponent Archetype: Lightning Turbo Miraidon ex Engine")
        elif "lugia" in opp_act_name.lower():
            inferred_items.append("Opponent Archetype: Colorless Lugia VSTAR Engine")
        else:
            inferred_items.append("Opponent Archetype: Standard Meta Competitive Archetype")

        return {
            "KNOWN": known_items,
            "INFERRED": inferred_items,
            "PROBABILISTIC": probabilistic_items,
            "UNKNOWN": unknown_items
        }

    def estimate_card_probabilities(
        self,
        game_state: Dict[str, Any],
        candidate_cards: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Computes Bayesian posterior probability P(Opponent holds Card C in hand | Evidence).
        """
        opp = game_state.get("opponent", {})
        known_hand = [c.get("name", "") if isinstance(c, dict) else str(c) for c in opp.get("known_hand", [])]
        opp_hand_count = opp.get("hand_count", 5)
        hidden_count = max(0, opp_hand_count - len(known_hand))
        opp_deck_count = max(1, opp.get("deck_count", 40))

        if candidate_cards is None:
            candidate_cards = [
                "Boss's Orders",
                "Professor's Research",
                "Iono",
                "Ultra Ball",
                "Rare Candy",
                "Basic Energy",
                "Switch",
                "Prime Catcher"
            ]

        results = {}
        for c in candidate_cards:
            # If card is already directly visible in known hand: P = 1.0
            if any(c.lower() in kh.lower() for kh in known_hand):
                results[c] = 1.0
                continue

            if hidden_count == 0:
                results[c] = 0.0
                continue

            # Prior copies remaining in unrevealed deck/hand (standard max 4, - discard)
            discard_copies = sum(
                1 for d in opp.get("discard", [])
                if c.lower() in (d.get("name", "") if isinstance(d, dict) else str(d)).lower()
            )
            max_copies = 1 if "prime catcher" in c.lower() or "radiant" in c.lower() else 4
            remaining_copies = max(0, max_copies - discard_copies)

            # Hypergeometric draw probability:
            # P(at least 1 copy in hidden hand) = 1 - ((Total - Copies) choose Hand) / (Total choose Hand)
            total_unseen = opp_deck_count + hidden_count
            if total_unseen <= 0 or remaining_copies <= 0:
                results[c] = 0.0
                continue

            prob_none = 1.0
            for i in range(hidden_count):
                if total_unseen - i <= 0:
                    break
                prob_none *= max(0.0, (total_unseen - remaining_copies - i) / (total_unseen - i))

            p_in_hand = round(max(0.0, min(1.0, 1.0 - prob_none)), 4)
            results[c] = p_in_hand

        return results

    def sample_belief_state(
        self,
        game_state: Dict[str, Any],
        archetype_pool: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Samples a concrete, consistent hypothetical game state S_i ~ P(S | Information)
        by assigning plausible concrete cards to opponent's hidden hand from the unrevealed card distribution.
        """
        state_sample = copy.deepcopy(game_state)
        opp = state_sample.get("opponent", {})

        opp_hand_count = opp.get("hand_count", 5)
        known_hand = opp.get("known_hand", [])
        needed = max(0, opp_hand_count - len(known_hand))

        pool = archetype_pool or [
            "Basic Lightning Energy", "Basic Fire Energy", "Professor's Research",
            "Ultra Ball", "Nest Ball", "Iono", "Boss's Orders", "Switch",
            "Rare Candy", "Super Rod"
        ]

        sampled_hand = list(known_hand)
        for _ in range(needed):
            sampled_hand.append(random.choice(pool))

        opp["hand"] = sampled_hand
        return state_sample

    def generate_particle_belief_states(
        self,
        game_state: Dict[str, Any],
        num_particles: int = 5
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Generates S_1, ..., S_n particle states with normalized probabilities sum P(S_i|I) = 1.
        """
        particles = []
        weight = 1.0 / max(1, num_particles)
        for _ in range(num_particles):
            s = self.sample_belief_state(game_state)
            particles.append((s, weight))
        return particles
