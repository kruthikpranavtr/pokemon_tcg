"""
Action Mask Engine: Dynamic Legal Move Generator
Enforces all turn-based restrictions (1 Supporter, 1 Energy attachment, 1 Stadium, Turn 1 Going 1st rule).
"""
from typing import Dict, List, Any


class ActionMaskEngine:
    def __init__(self, card_db: Dict[str, Any]):
        self.card_db = card_db

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

        hand = player.get("hand", [])
        active = player.get("active_spot", {})
        bench = player.get("bench", [])
        stadium_in_play = game_state.get("stadium_in_play")

        # 1. EVALUATE CARDS IN HAND
        for idx, item in enumerate(hand):
            cid = item.get("card_id")
            card = self.card_db.get(cid, {})
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
                    if len(bench) < 5:
                        legal_actions.append({
                            "action_type": "BENCH_BASIC_POKEMON",
                            "card_id": cid,
                            "card_name": card.get("name"),
                            "hand_index": idx
                        })
                elif "Stage 1" in subtypes or "Stage 2" in subtypes:
                    evolves_from = card.get("evolves_from")
                    # Check if Active evolves from this
                    if active and active.get("name") == evolves_from and active.get("turns_in_play", 0) >= 1:
                        legal_actions.append({
                            "action_type": "EVOLVE_POKEMON",
                            "card_id": cid,
                            "card_name": card.get("name"),
                            "target": "ACTIVE",
                            "target_pokemon": active.get("name"),
                            "hand_index": idx
                        })
                    # Check Bench evolves
                    for b in bench:
                        if b.get("name") == evolves_from and b.get("turns_in_play", 1) >= 1:
                            legal_actions.append({
                                "action_type": "EVOLVE_POKEMON",
                                "card_id": cid,
                                "card_name": card.get("name"),
                                "target": f"BENCH_SLOT_{b.get('slot')}",
                                "target_pokemon": b.get("name"),
                                "hand_index": idx
                            })

        # 2. STADIUM ON-FIELD ABILITY (e.g. Artazon)
        if stadium_in_play:
            legal_actions.append({
                "action_type": "USE_STADIUM_EFFECT",
                "card_id": stadium_in_play.get("card_id"),
                "card_name": stadium_in_play.get("name")
            })

        # 3. ACTIVE ATTACK
        # Check Turn 1 Going 1st restriction
        can_attack = not (is_first_turn_of_game and turn_number == 1)
        if can_attack and active:
            active_card = self.card_db.get(active.get("card_id", ""), {})
            attacks = active_card.get("attacks", [])
            attached_energies = active.get("attached_energy", [])
            energy_count = len(attached_energies)

            for atk in attacks:
                req_cost = len(atk.get("cost", []))
                # For simplified cost check: if count >= required cost
                if energy_count >= req_cost:
                    legal_actions.append({
                        "action_type": "ATTACK",
                        "attack_name": atk.get("name"),
                        "base_damage": atk.get("base_damage", 0),
                        "attacker": active.get("name")
                    })

        # 4. PASS TURN (Always legal)
        legal_actions.append({
            "action_type": "PASS_TURN"
        })

        return legal_actions
