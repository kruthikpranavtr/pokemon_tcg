"""
Action Mask Engine: Dynamic Legal Move Generator
Enforces all turn-based restrictions (1 Supporter, 1 Energy attachment, 1 Stadium, Turn 1 Going 1st rule).
"""
from typing import Dict, List, Any


class ActionMaskEngine:
    def __init__(self, card_db: Dict[str, Any]):
        self.card_db = card_db
        self.legacy_map = {
            "sv1-196": "1121",  # Ultra Ball
            "sv3-26": "788",    # Charmander
            "sv3-27": "789",    # Charmeleon
            "sv3-125": "790",   # Mega Charizard X ex / Charizard ex
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

    def _resolve_card(self, item: Any) -> Dict[str, Any]:
        """Resolves a card dictionary from card_id, legacy ID, or name."""
        if not item:
            return {}
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
        return {}

    def get_legal_actions(self, game_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extracts all legally permissible atomic moves given current game state.
        """
        legal_actions = []
        player = game_state.get("player", {})
        turn_flags = game_state.get("turn_flags", {})
        turn_number = game_state.get("turn_number", 1)
        is_first_turn_of_game = turn_flags.get("is_first_turn_of_game", False)

        supporter_played = turn_flags.get("supporter_played_this_turn", False)
        energy_attached = turn_flags.get("energy_attached_this_turn", False)
        stadium_played = turn_flags.get("stadium_played_this_turn", False)
        retreated = turn_flags.get("retreated_this_turn", False)

        hand = player.get("hand") or []
        active = player.get("active_spot") or {}
        bench = player.get("bench") or []
        stadium_in_play = game_state.get("stadium_in_play")

        # 0. SETUP PHASE LEGAL MOVES
        if game_state.get("phase") == "SETUP":
            has_active = bool(active and active.get("name"))
            setup_actions = []
            for idx, item in enumerate(hand):
                cid = item.get("card_id") if isinstance(item, dict) else str(item)
                card = self._resolve_card(item)
                subtypes = card.get("subtypes", [])
                is_basic = "Basic" in subtypes or card.get("stage") == "Basic" or (card.get("supertype") == "Pokémon" and not card.get("evolves_from"))
                if is_basic:
                    cname = card.get("name") or (item.get("name") if isinstance(item, dict) else str(item))
                    if not has_active:
                        setup_actions.append({
                            "action_type": "PLACE_ACTIVE_POKEMON",
                            "card_id": cid,
                            "card_name": cname,
                            "target": "ACTIVE",
                            "hand_index": idx
                        })
                    if len([b for b in bench if b]) < 3:
                        setup_actions.append({
                            "action_type": "BENCH_BASIC_POKEMON",
                            "card_id": cid,
                            "card_name": cname,
                            "target": "BENCH",
                            "hand_index": idx
                        })
            if has_active:
                setup_actions.append({"action_type": "CONFIRM_SETUP"})
            return setup_actions or [{"action_type": "MULLIGAN"}]

        # 1. EVALUATE CARDS IN HAND
        for idx, item in enumerate(hand):
            cid = item.get("card_id") if isinstance(item, dict) else str(item)
            card = self._resolve_card(item)
            supertype = card.get("supertype", "")
            subtypes = card.get("subtypes", [])

            # --- TRAINER CARDS ---
            if supertype == "Trainer":
                if "Supporter" in subtypes:
                    # Turn 1 Going 1st rule: Cannot play supporter
                    if is_first_turn_of_game and turn_number == 1:
                        continue
                    if not supporter_played:
                        legal_actions.append({
                            "action_type": "PLAY_SUPPORTER",
                            "card_id": cid,
                            "card_name": card.get("name"),
                            "hand_index": idx,
                            "effects": card.get("effects", {})
                        })
                elif "Stadium" in subtypes:
                    # Can play if stadium not played and not duplicate name
                    if not stadium_played:
                        if not (stadium_in_play and stadium_in_play.get("card_id") == cid):
                            legal_actions.append({
                                "action_type": "PLAY_STADIUM",
                                "card_id": cid,
                                "card_name": card.get("name"),
                                "hand_index": idx
                            })
                elif "Item" in subtypes:
                    legal_actions.append({
                        "action_type": "PLAY_ITEM",
                        "card_id": cid,
                        "card_name": card.get("name"),
                        "hand_index": idx,
                        "effects": card.get("effects", {})
                    })

            # --- ENERGY ATTACHMENT ---
            elif supertype == "Energy":
                if not energy_attached:
                    # Can attach to active
                    if active and active.get("name"):
                        legal_actions.append({
                            "action_type": "ATTACH_ENERGY",
                            "card_id": cid,
                            "card_name": card.get("name"),
                            "target": "ACTIVE",
                            "target_pokemon": active.get("name"),
                            "hand_index": idx
                        })
                    # Can attach to benched Pokémon
                    for b in bench:
                        legal_actions.append({
                            "action_type": "ATTACH_ENERGY",
                            "card_id": cid,
                            "card_name": card.get("name"),
                            "target": f"BENCH_SLOT_{b.get('slot')}",
                            "target_pokemon": b.get("name"),
                            "hand_index": idx
                        })

            # --- POKÉMON (BENCHING OR EVOLVING) ---
            elif supertype == "Pokémon":
                if "Basic" in subtypes:
                    if len(bench) < 3:
                        legal_actions.append({
                            "action_type": "BENCH_BASIC_POKEMON",
                            "card_id": cid,
                            "card_name": card.get("name"),
                            "hand_index": idx
                        })
                elif "Stage 1" in subtypes or "Stage 2" in subtypes:
                    evolves_from = card.get("evolves_from")
                    # Check if Active evolves from this
                    if active and evolves_from and evolves_from.lower() in active.get("name", "").lower():
                        legal_actions.append({
                            "action_type": "EVOLVE_POKEMON",
                            "card_id": cid,
                            "card_name": card.get("name"),
                            "target": "ACTIVE",
                            "target_pokemon": active.get("name"),
                            "hand_index": idx
                        })
                    # Check Bench evolves
                    for b_idx, b in enumerate(bench):
                        if b and evolves_from and evolves_from.lower() in b.get("name", "").lower():
                            legal_actions.append({
                                "action_type": "EVOLVE_POKEMON",
                                "card_id": cid,
                                "card_name": card.get("name"),
                                "target": f"BENCH_SLOT_{b.get('slot', b_idx)}",
                                "target_pokemon": b.get("name"),
                                "hand_index": idx
                            })

        # 2. DRAW CARD ACTION (once per turn)
        card_drawn = turn_flags.get("card_drawn_this_turn", False)
        if not card_drawn:
            legal_actions.append({
                "action_type": "DRAW_CARD"
            })

        # 3. STADIUM ON-FIELD ABILITY (e.g. Artazon)
        if stadium_in_play:
            legal_actions.append({
                "action_type": "USE_STADIUM_EFFECT",
                "card_id": stadium_in_play.get("card_id"),
                "card_name": stadium_in_play.get("name")
            })

        # 4. RETREAT / SWITCH WITH BENCH
        for b_idx, b in enumerate(bench):
            if b:
                legal_actions.append({
                    "action_type": "RETREAT",
                    "bench_slot": b_idx,
                    "target_pokemon": b.get("name")
                })

        # 5. ACTIVE ATTACK
        # Check Turn 1 Going 1st restriction
        can_attack = not (is_first_turn_of_game and turn_number == 1)
        if can_attack and active:
            active_card = self.card_db.get(active.get("card_id", ""), {})
            attacks = active_card.get("attacks") or active.get("attacks") or []
            attached_energies = active.get("attached_energy", [])

            from src.engine.tcg_match_engine import check_energy_requirement

            for atk in attacks:
                can_atk, _ = check_energy_requirement(attached_energies, atk.get("cost", []))
                if can_atk:
                    legal_actions.append({
                        "action_type": "ATTACK",
                        "attack_name": atk.get("name"),
                        "base_damage": atk.get("base_damage", 0),
                        "attacker": active.get("name")
                    })

        # 6. PASS TURN (Always legal)
        legal_actions.append({
            "action_type": "PASS_TURN"
        })

        return legal_actions
