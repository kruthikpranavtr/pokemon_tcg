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
        self.legacy_map = {
            "sv1-196": "1121",  # Ultra Ball
            "sv3-26": "788",    # Charmander
            "sv3-27": "789",    # Charmeleon
            "sv3-125": "790",   # Mega Charizard X ex / Charizard ex
            "sv3-164": "790",   # Pidgeot ex
            "sv3-162": "788",   # Pidgey
            "sv2-93": "40",     # Radiant Greninja / Greninja ex
            "sve-2": "2",       # Basic {R} Energy
            "sve-4": "4",       # Basic {L} Energy
            "sv1-189": "1079",  # Professor's Research
            "sv1-181": "1119",  # Nest Ball / Energy Search
            "sv1-191": "1079",  # Rare Candy
            "sv1-166": "1130",  # Arven
            "sv2-185": "265",   # Iono
            "sv5-144": "1088",  # Prime Catcher
            "sv1-167": "1135",  # Artazon
            "sv1-86": "313",    # Miraidon ex
            "sv4-70": "313",    # Iron Hands ex
        }
        self.energy_aliases = {
            "basic fire energy": "2",
            "basic grass energy": "1",
            "basic water energy": "3",
            "basic lightning energy": "4",
            "basic psychic energy": "5",
            "basic fighting energy": "6",
            "basic darkness energy": "7",
            "basic metal energy": "8",
        }
        self.name_map = {}
        for c in card_db.values():
            if c.get("name"):
                self.name_map[c["name"].lower()] = c
            if c.get("card_name"):
                self.name_map[c["card_name"].lower()] = c

    def _resolve_card(self, item: Any) -> Optional[Dict[str, Any]]:
        """Resolves a card dictionary from card_id, legacy ID, or name."""
        if not item:
            return None
        cid = None
        cname = None
        if isinstance(item, dict):
            cid = str(item.get("card_id", "")).strip()
            cname = str(item.get("name") or item.get("card_name", "")).strip()
        else:
            cid = str(item).strip()
            cname = cid

        if cid in self.card_db:
            return self.card_db[cid]
        if cid in self.legacy_map:
            leg_id = self.legacy_map[cid]
            if leg_id in self.card_db:
                return self.card_db[leg_id]
        if cname:
            cn_lower = cname.lower()
            if cn_lower in self.energy_aliases:
                eid = self.energy_aliases[cn_lower]
                if eid in self.card_db:
                    return self.card_db[eid]
            if cn_lower in self.name_map:
                return self.name_map[cn_lower]
        return None

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
            card = self._resolve_card(item)

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
        p_active = player.get("active_spot") or {}
        opp_active = opponent.get("active_spot") or {}

        # Compute active knock-out potential
        p_active_card = self.card_db.get(p_active.get("card_id", ""), {}) if isinstance(p_active, dict) else {}
        opp_active_card = self.card_db.get(opp_active.get("card_id", ""), {}) if isinstance(opp_active, dict) else {}

        opp_active_hp = opp_active.get("current_hp", 100) if isinstance(opp_active, dict) else 100
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
