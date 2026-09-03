"""
Card Resolution & Input Parsing Engine
Resolves card names, aliases, and simplified user board states into standardized TCG game states.
"""
import re
from typing import Dict, List, Any, Optional, Union


class CardResolver:
    def __init__(self, card_db: Dict[str, Any]):
        self.card_db = card_db
        # Build normalized name lookup dictionary
        self.name_to_card = {}
        for cid, card in card_db.items():
            name_norm = self._normalize(card.get("name", ""))
            if name_norm and name_norm not in self.name_to_card:
                self.name_to_card[name_norm] = card

    def _normalize(self, text: str) -> str:
        if not text:
            return ""
        # Lowercase and remove punctuation / excess spaces
        return re.sub(r"[^a-z0-9]", "", text.lower())

    def resolve_card(self, card_input: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Resolves a card identifier (name, ID, or partial dict) to a full card metadata dict.
        """
        if isinstance(card_input, dict):
            cid = card_input.get("card_id", "")
            cname = card_input.get("name", "")

            # If card_id is found in DB
            if cid and cid in self.card_db:
                base = dict(self.card_db[cid])
                base.update(card_input)
                return base

            # If name is found in DB
            norm_name = self._normalize(cname)
            if norm_name in self.name_to_card:
                base = dict(self.name_to_card[norm_name])
                base.update(card_input)
                return base

            # Try partial substring match on DB names
            for norm_key, card in self.name_to_card.items():
                if norm_name and (norm_name in norm_key or norm_key in norm_name):
                    base = dict(card)
                    base.update(card_input)
                    return base

            # Fallback for ad-hoc custom card dict
            return {
                "card_id": cid or f"custom-{self._normalize(cname) or 'card'}",
                "name": cname or "Unknown Card",
                "supertype": card_input.get("supertype", "Pokémon"),
                "subtypes": card_input.get("subtypes", ["Basic"]),
                "hp": card_input.get("hp", card_input.get("current_hp", 100)),
                "current_hp": card_input.get("current_hp", card_input.get("hp", 100)),
                "attached_energy": card_input.get("attached_energy", []),
                "turns_in_play": card_input.get("turns_in_play", 1),
                "attacks": card_input.get("attacks", [{"name": "Quick Attack", "base_damage": 30, "cost": ["Colorless"]}])
            }

        elif isinstance(card_input, str):
            raw_str = card_input.strip()
            # 1. Exact card_id
            if raw_str in self.card_db:
                return dict(self.card_db[raw_str])

            # 2. Normalized name match
            norm_str = self._normalize(raw_str)
            if norm_str in self.name_to_card:
                return dict(self.name_to_card[norm_str])

            # 3. Substring match
            for norm_key, card in self.name_to_card.items():
                if norm_str and (norm_str in norm_key or norm_key in norm_str):
                    return dict(card)

            # 4. Energy shorthand checks (e.g. "Fire Energy", "Basic Fire")
            if "energy" in norm_str:
                return {
                    "card_id": f"energy-{norm_str}",
                    "name": raw_str.title(),
                    "supertype": "Energy",
                    "subtypes": ["Basic Energy"]
                }

            # 5. Trainer shorthand checks
            if any(k in norm_str for k in ["ball", "research", "iono", "boss", "candy", "catcher", "arven", "rod", "vessel"]):
                return {
                    "card_id": f"trainer-{norm_str}",
                    "name": raw_str.title(),
                    "supertype": "Trainer",
                    "subtypes": ["Supporter" if any(s in norm_str for s in ["research", "iono", "boss", "arven"]) else "Item"]
                }

            # 6. Default fallback Pokémon
            return {
                "card_id": f"pkmn-{norm_str}",
                "name": raw_str.title(),
                "supertype": "Pokémon",
                "subtypes": ["Basic"],
                "hp": 120,
                "attacks": [{"name": "Standard Strike", "base_damage": 50, "cost": ["Colorless"]}]
            }

        return {
            "card_id": "unknown-1",
            "name": "Unknown",
            "supertype": "Pokémon",
            "subtypes": ["Basic"]
        }

    def parse_energy_list(self, energy_input: Any) -> List[Dict[str, str]]:
        """
        Standardizes energy attachments into a list of dicts [{'type': 'Fire'}, ...]
        Supports integer counts (e.g. 2 -> [{'type': 'Colorless'}, {'type': 'Colorless'}])
        or string lists (e.g. ['Fire', 'Fire']).
        """
        if isinstance(energy_input, int):
            return [{"type": "Colorless"} for _ in range(max(0, energy_input))]
        elif isinstance(energy_input, list):
            res = []
            for item in energy_input:
                if isinstance(item, dict):
                    res.append(item)
                elif isinstance(item, str):
                    res.append({"type": item.replace("Energy", "").strip() or "Colorless"})
            return res
        return []

    def build_game_state(
        self,
        our_cards: Dict[str, Any],
        opponent_cards: Dict[str, Any],
        turn_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Constructs a complete standard game state dict from high-level user & opponent card inputs.
        """
        turn_ctx = turn_context or {}
        turn_num = turn_ctx.get("turn_number", 3)
        turn_flags = {
            "is_first_turn_of_game": turn_ctx.get("is_first_turn_of_game", False),
            "supporter_played_this_turn": turn_ctx.get("supporter_played_this_turn", False),
            "energy_attached_this_turn": turn_ctx.get("energy_attached_this_turn", False),
            "retreated_this_turn": turn_ctx.get("retreated_this_turn", False),
            "stadium_played_this_turn": turn_ctx.get("stadium_played_this_turn", False)
        }

        # --- 1. RESOLVE OUR PLAYER CARDS ---
        # Hand
        raw_hand = our_cards.get("hand", []) or our_cards.get("hand_cards", [])
        resolved_hand = []
        for h in raw_hand:
            resolved_card = self.resolve_card(h)
            resolved_hand.append(resolved_card)

        # Active Spot
        raw_p_active = our_cards.get("active", {}) or our_cards.get("active_spot", {}) or our_cards.get("active_pokemon", {})
        if isinstance(raw_p_active, str):
            raw_p_active = {"name": raw_p_active}
        
        resolved_p_active_meta = self.resolve_card(raw_p_active)
        max_hp = resolved_p_active_meta.get("hp", 120)
        curr_hp = raw_p_active.get("current_hp", raw_p_active.get("hp", max_hp))
        energy_input = raw_p_active.get("attached_energy", raw_p_active.get("energy", []))
        attached_energy = self.parse_energy_list(energy_input)

        p_active_spot = {
            "card_id": resolved_p_active_meta.get("card_id"),
            "name": resolved_p_active_meta.get("name"),
            "current_hp": int(curr_hp),
            "max_hp": int(max_hp),
            "attached_energy": attached_energy,
            "turns_in_play": raw_p_active.get("turns_in_play", 1)
        }

        # Bench
        raw_p_bench = our_cards.get("bench", []) or our_cards.get("bench_pokemon", [])
        resolved_p_bench = []
        for idx, b in enumerate(raw_p_bench, start=1):
            if isinstance(b, str):
                b = {"name": b}
            b_meta = self.resolve_card(b)
            b_max_hp = b_meta.get("hp", 100)
            b_curr_hp = b.get("current_hp", b.get("hp", b_max_hp))
            b_energy = self.parse_energy_list(b.get("attached_energy", b.get("energy", [])))
            resolved_p_bench.append({
                "slot": b.get("slot", idx),
                "card_id": b_meta.get("card_id"),
                "name": b_meta.get("name"),
                "current_hp": int(b_curr_hp),
                "attached_energy": b_energy,
                "turns_in_play": b.get("turns_in_play", 1)
            })

        # --- 2. RESOLVE OPPONENT CARDS ---
        raw_opp_active = opponent_cards.get("active", {}) or opponent_cards.get("active_spot", {}) or opponent_cards.get("active_pokemon", {})
        if isinstance(raw_opp_active, str):
            raw_opp_active = {"name": raw_opp_active}

        resolved_opp_active_meta = self.resolve_card(raw_opp_active)
        opp_max_hp = resolved_opp_active_meta.get("hp", 200)
        opp_curr_hp = raw_opp_active.get("current_hp", raw_opp_active.get("hp", opp_max_hp))
        opp_energy = self.parse_energy_list(raw_opp_active.get("attached_energy", raw_opp_active.get("energy", [])))

        opp_active_spot = {
            "card_id": resolved_opp_active_meta.get("card_id"),
            "name": resolved_opp_active_meta.get("name"),
            "current_hp": int(opp_curr_hp),
            "max_hp": int(opp_max_hp),
            "attached_energy": opp_energy,
            "turns_in_play": raw_opp_active.get("turns_in_play", 1)
        }

        raw_opp_bench = opponent_cards.get("bench", []) or opponent_cards.get("bench_pokemon", [])
        resolved_opp_bench = []
        for idx, b in enumerate(raw_opp_bench, start=1):
            if isinstance(b, str):
                b = {"name": b}
            b_meta = self.resolve_card(b)
            b_max_hp = b_meta.get("hp", 100)
            b_curr_hp = b.get("current_hp", b.get("hp", b_max_hp))
            b_energy = self.parse_energy_list(b.get("attached_energy", b.get("energy", [])))
            resolved_opp_bench.append({
                "slot": b.get("slot", idx),
                "card_id": b_meta.get("card_id"),
                "name": b_meta.get("name"),
                "current_hp": int(b_curr_hp),
                "attached_energy": b_energy
            })

        # Stadium
        stadium_obj = None
        stadium_raw = turn_ctx.get("stadium_in_play") or our_cards.get("stadium") or opponent_cards.get("stadium")
        if stadium_raw:
            if isinstance(stadium_raw, str):
                s_meta = self.resolve_card(stadium_raw)
                stadium_obj = {"card_id": s_meta.get("card_id"), "name": s_meta.get("name")}
            elif isinstance(stadium_raw, dict):
                stadium_obj = stadium_raw

        return {
            "turn_number": turn_num,
            "turn_flags": turn_flags,
            "stadium_in_play": stadium_obj,
            "player": {
                "prizes_remaining": int(our_cards.get("prizes_remaining", 6)),
                "prizes_taken": int(our_cards.get("prizes_taken", 6 - int(our_cards.get("prizes_remaining", 6)))),
                "deck_count": int(our_cards.get("deck_count", 40)),
                "hand": resolved_hand,
                "active_spot": p_active_spot,
                "bench": resolved_p_bench
            },
            "opponent": {
                "archetype": opponent_cards.get("deck_archetype", opponent_cards.get("archetype", "Standard Opponent")),
                "prizes_remaining": int(opponent_cards.get("prizes_remaining", 6)),
                "prizes_taken": int(opponent_cards.get("prizes_taken", 6 - int(opponent_cards.get("prizes_remaining", 6)))),
                "hand_count": int(opponent_cards.get("hand_count", 5)),
                "deck_count": int(opponent_cards.get("deck_count", 40)),
                "active_spot": opp_active_spot,
                "bench": resolved_opp_bench
            }
        }
