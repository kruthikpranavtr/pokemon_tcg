"""
Pokémon TCG Rules & Validation Engine
Enforces standard tournament rules, deck constraints, prize mechanics, and board constraints.
"""
from typing import Dict, List, Any, Tuple, Optional


class RulesEngine:
    def __init__(self, card_db: Dict[str, Any]):
        """
        card_db: dictionary mapping card_id -> card metadata
        """
        self.card_db = card_db

    def validate_deck(self, deck_list: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        Validates a 60-card Standard format deck list.
        deck_list: list of dicts with {"card_id": str, "count": int}
        Returns: (is_valid, list_of_error_messages)
        """
        errors = []
        total_cards = sum(item.get("count", 0) for item in deck_list)
        if total_cards != 60:
            errors.append(f"Deck must contain exactly 60 cards. Current count: {total_cards}")

        radiant_count = 0
        ace_spec_count = 0
        basic_pokemon_count = 0

        for item in deck_list:
            cid = item.get("card_id")
            count = item.get("count", 0)
            card = self.card_db.get(cid)

            if not card:
                errors.append(f"Card ID '{cid}' not found in card database.")
                continue

            supertype = card.get("supertype", "")
            subtypes = card.get("subtypes", [])
            name = card.get("name", "")

            # 4-copy rule (Basic Energy exempt)
            if "Basic Energy" not in subtypes:
                if count > 4:
                    errors.append(f"Exceeded 4 copies of '{name}' (count: {count}).")

            # Radiant rule
            if "Radiant" in subtypes:
                radiant_count += count

            # ACE SPEC rule
            if "ACE SPEC" in subtypes:
                ace_spec_count += count

            # Basic Pokémon rule
            if supertype.lower().startswith("pok") and "Basic" in subtypes:
                basic_pokemon_count += count

        if radiant_count > 1:
            errors.append(f"Deck can only have max 1 Radiant Pokémon (found {radiant_count}).")

        if ace_spec_count > 1:
            errors.append(f"Deck can only have max 1 ACE SPEC card (found {ace_spec_count}).")

        if basic_pokemon_count < 1:
            errors.append("Deck must contain at least 1 Basic Pokémon.")

        return (len(errors) == 0, errors)

    def calculate_attack_damage(
        self,
        attacker_card: Dict[str, Any],
        attack: Dict[str, Any],
        defender_card: Dict[str, Any],
        opponent_prizes_taken: int = 0
    ) -> int:
        """
        Calculates attack damage including damage scaling, weakness, and resistance.
        """
        base_damage = attack.get("base_damage", 0)
        scaling = attack.get("damage_scaling")

        # Example: Charizard ex Burning Darkness (+30 per opponent prize taken)
        if scaling == "30_PER_OPPONENT_PRIZE_TAKEN":
            base_damage += 30 * opponent_prizes_taken

        attacker_types = attacker_card.get("types", [])
        defender_weaknesses = defender_card.get("weaknesses", [])
        defender_resistances = defender_card.get("resistances", [])

        # Apply Weakness (standard is x2)
        for w in defender_weaknesses:
            if w.get("type") in attacker_types:
                if "×2" in w.get("value", "") or "x2" in w.get("value", ""):
                    base_damage *= 2

        # Apply Resistance
        for r in defender_resistances:
            if r.get("type") in attacker_types:
                val = r.get("value", "0")
                try:
                    reduction = int(val)
                    base_damage = max(0, base_damage + reduction)
                except ValueError:
                    pass

        return base_damage

    def compute_prize_map(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates Turns-To-Win (TTW) and prize paths for both players.
        """
        player = game_state.get("player", {})
        opponent = game_state.get("opponent", {})

        p_prizes_left = player.get("prizes_remaining", 6)
        opp_prizes_left = opponent.get("prizes_remaining", 6)

        # Active check
        p_active = player.get("active_spot", {})
        opp_active = opponent.get("active_spot", {})

        # Compute active knock-out potential
        p_active_card = self.card_db.get(p_active.get("card_id", ""), {})
        opp_active_card = self.card_db.get(opp_active.get("card_id", ""), {})

        opp_active_hp = opp_active.get("current_hp", 100)
        opp_prize_yield = opp_active_card.get("prize_yield", 1)

        # Estimated turns to take remaining prizes
        player_ttw = max(1, (p_prizes_left + 1) // 2)
        opp_ttw = max(1, (opp_prizes_left + 1) // 2)

        return {
            "player_prizes_remaining": p_prizes_left,
            "opponent_prizes_remaining": opp_prizes_left,
            "player_projected_ttw": player_ttw,
            "opponent_projected_ttw": opp_ttw,
            "prize_differential": (6 - p_prizes_left) - (6 - opp_prizes_left)
        }
