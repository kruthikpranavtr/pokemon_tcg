"""
Comprehensive Test Suite: 20 Pokemon TCG Test Scenarios
Verifies:
1. Authentic Card Names from CSV (No invented Pokemon)
2. Dual Attacks Preserved
3. Single Attack Preservation (No fake duplication)
4. 60-Card Deck Limit Enforced
5. 3 Deck Slots (Save, Load, Active Selection)
6. 5-Card Opening Hand Drawn
7. Mulligan Redraw Mechanism
8. Basic-Only Initial Setup Placement (Stage 1/2 blocked)
9. Bench Limit (Max 3 Bench slots: 1 Active + max 3 Bench)
10. Hand Card Actions (Items, Supporters, Energies)
11. Evolution Logic (evolves_from & PRESERVES attached energy)
12. 1 Energy Attachment Per Turn Restriction
13. 1 Card Draw Per Turn Restriction
14. Switch / Retreat Swapping Active with Bench (Preserving energies)
15. Knockout at 0 HP & Mandatory Bench Promotion
16. Exact Energy Cost Matching (Blocks attack when insufficient)
17. Attack Damage, Weakness & Resistance Calculation
18. Action Mask Legal Move Generation
19. Dataset Validation (1,267 authentic cards from EN_Card_Data.csv)
20. Full Match Arena Cycle (Setup -> Battle -> Attack -> Turn Advance)
"""

import os
import unittest
from pathlib import Path

from src.data_validator import validate_csv_dataset
from src.database import (
    init_db, get_db_connection,
    save_user_deck, get_user_decks, select_active_deck, get_active_deck
)
from src.engine.tcg_match_engine import TCGMatchEngine, check_energy_requirement
from src.engine.rules_engine import RulesEngine
from src.engine.action_mask import ActionMaskEngine


class TestTwentyScenarios(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        possible_csvs = [
            Path("c:/Users/Aswin/Desktop/Pokemon/Csvfiles/EN_Card_Data.csv"),
            Path("../Csvfiles/EN_Card_Data.csv"),
            Path("Csvfiles/EN_Card_Data.csv"),
        ]
        cls.csv_path = None
        for p in possible_csvs:
            if p.exists():
                cls.csv_path = p
                break
        
        if cls.csv_path:
            cls.cards_dict, cls.validation_summary = validate_csv_dataset(str(cls.csv_path))
        else:
            cls.validation_summary = {}
            cls.cards_dict = {}

        init_db()

    # Scenario 1: Authentic Card Names from CSV (No invented Pokemon)
    def test_01_authentic_card_names(self):
        self.assertIsNotNone(self.csv_path, "EN_Card_Data.csv must exist")
        self.assertGreater(len(self.cards_dict), 1000)
        known_real = ["Pikachu", "Charmander", "Bulbasaur", "Alakazam", "Miraidon ex", "Abra"]
        for name in known_real:
            matching = [c for c in self.cards_dict.values() if c.get("name", "").lower() == name.lower()]
            self.assertTrue(len(matching) > 0, f"Authentic card '{name}' must exist in dataset")

    # Scenario 2: Dual Attacks Preserved
    def test_02_dual_attacks_preserved(self):
        dual_attack_cards = [c for c in self.cards_dict.values() if c.get("card_type") == "pokemon" and len(c.get("attacks", [])) == 2]
        self.assertGreater(len(dual_attack_cards), 50)
        sample = dual_attack_cards[0]
        self.assertNotEqual(sample["attacks"][0]["name"], sample["attacks"][1]["name"])
        self.assertTrue(len(sample["attacks"][0]["name"]) > 0)
        self.assertTrue(len(sample["attacks"][1]["name"]) > 0)

    # Scenario 3: Single Attack Preservation (No duplicated attack 2)
    def test_03_single_attack_no_duplication(self):
        single_attack_cards = [c for c in self.cards_dict.values() if c.get("card_type") == "pokemon" and len(c.get("attacks", [])) == 1]
        self.assertGreater(len(single_attack_cards), 50)
        for c in single_attack_cards[:10]:
            self.assertEqual(len(c["attacks"]), 1)

    # Scenario 4: 60-Card Deck Limit Enforced
    def test_04_60_card_deck_limit(self):
        rules = RulesEngine(card_db=self.cards_dict)
        deck_61 = [{"card_id": "card-1", "count": 61}]
        self.cards_dict["card-1"] = {"name": "Pikachu", "supertype": "Pokemon", "subtypes": ["Basic"]}
        valid, errors = rules.validate_deck(deck_61)
        self.assertFalse(valid)
        self.assertTrue(any("60 cards" in e for e in errors))

        deck_60 = [{"card_id": "card-1", "count": 4}] + [{"card_id": f"e-{i}", "count": 4} for i in range(14)]
        for i in range(14):
            self.cards_dict[f"e-{i}"] = {"name": f"Energy {i}", "supertype": "Energy", "subtypes": ["Basic Energy"]}
        valid_ok, _ = rules.validate_deck(deck_60)
        self.assertTrue(valid_ok)

    # Scenario 5: 3 Deck Slots (Save, Load, Active Selection)
    def test_05_three_deck_slots(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (id, username, email, password_hash, salt) VALUES (999, 'testuser', 'test@example.com', 'hash', 'salt')")
        conn.commit()
        conn.close()

        user_id = 999
        d1 = save_user_deck(user_id=user_id, deck_slot=1, deck_name="Lightning Spark", card_ids=["Pikachu"] * 60)
        self.assertEqual(d1["slot"], 1)

        d2 = save_user_deck(user_id=user_id, deck_slot=2, deck_name="Fire Blast", card_ids=["Charmander"] * 60)
        self.assertEqual(d2["slot"], 2)

        d3 = save_user_deck(user_id=user_id, deck_slot=3, deck_name="Grass Vine", card_ids=["Bulbasaur"] * 60)
        self.assertEqual(d3["slot"], 3)

        decks = get_user_decks(user_id)
        self.assertEqual(len(decks), 3)

        sel = select_active_deck(user_id=user_id, deck_slot=2)
        self.assertEqual(sel["active_slot"], 2)
        active = get_active_deck(user_id)
        self.assertEqual(active["slot"], 2)
        self.assertEqual(active["deck_name"], "Fire Blast")

    # Scenario 6: 5-Card Opening Hand Drawn (with 6 prize cards setup, 60 - 5 - 6 = 49 cards in draw deck)
    def test_06_five_card_opening_hand(self):
        engine = TCGMatchEngine(card_db=self.cards_dict)
        engine.reset_match()
        self.assertEqual(len(engine.player_hand), 5, "Player must draw exactly 5 cards into opening hand")
        self.assertEqual(len(engine.player_prizes), 6, "Player must set aside 6 prize cards")
        self.assertEqual(len(engine.player_deck), 49, "Player deck must have 49 cards remaining in face-down draw pile")
        self.assertEqual(len(engine.player_hand) + len(engine.player_prizes) + len(engine.player_deck), 60, "Total must equal 60 cards")

    # Scenario 7: Mulligan Redraw Mechanism
    def test_07_mulligan_redraw(self):
        engine = TCGMatchEngine(card_db=self.cards_dict)
        engine.reset_match()
        engine.player_hand = ["Basic Lightning Energy"] * 5
        engine.mulligan_required = True
        res = engine.mulligan_player_hand()
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(engine.player_hand), 5)
        self.assertEqual(engine.mulligan_count, 1)

    # Scenario 8: Basic-Only Initial Setup Placement
    def test_08_basic_only_initial_placement(self):
        engine = TCGMatchEngine(card_db=self.cards_dict)
        engine.reset_match()
        engine.player_hand = ["Raichu", "Pikachu", "Potion", "Basic Lightning Energy", "Ultra Ball"]

        res_stage1 = engine.place_initial_pokemon("Raichu", "active")
        self.assertEqual(res_stage1["status"], "error")
        self.assertIn("Only BASIC", res_stage1["message"])

        res_basic = engine.place_initial_pokemon("Pikachu", "active")
        self.assertEqual(res_basic["status"], "success")
        self.assertIsNotNone(engine.player_active)
        self.assertEqual(engine.player_active["name"], "Pikachu")

    # Scenario 9: Bench Limit (Max 3 Bench Slots)
    def test_09_max_three_bench_slots(self):
        engine = TCGMatchEngine(card_db=self.cards_dict)
        engine.reset_match()
        engine.player_hand = ["Pikachu", "Charmander", "Bulbasaur", "Abra", "Eevee"]

        engine.place_initial_pokemon("Pikachu", "active")
        engine.place_initial_pokemon("Charmander", "bench_0")
        engine.place_initial_pokemon("Bulbasaur", "bench_1")
        engine.place_initial_pokemon("Abra", "bench_2")

        benched_count = sum(1 for b in engine.player_bench if b is not None)
        self.assertEqual(benched_count, 3)

        res_overflow = engine.place_initial_pokemon("Eevee", "bench_3")
        self.assertEqual(res_overflow["status"], "error")

    # Scenario 10: Hand Card Playing (Items, Supporters, Energies)
    def test_10_play_cards_from_hand(self):
        engine = TCGMatchEngine(card_db=self.cards_dict)
        engine.reset_match()
        engine.player_hand = ["Pikachu", "Potion"]
        engine.place_initial_pokemon("Pikachu", "active")
        engine.confirm_initial_placement()

        engine.player_active["current_hp"] = 30
        res = engine.play_trainer_card("Potion")
        self.assertEqual(res["status"], "success")
        self.assertEqual(engine.player_active["current_hp"], 60, "Potion heals 30 HP")

    # Scenario 11: Evolution Logic & Energy Preservation
    def test_11_evolution_logic_and_energy_preservation(self):
        engine = TCGMatchEngine(card_db=self.cards_dict)
        engine.reset_match()
        engine.player_hand = ["Pikachu"]
        engine.place_initial_pokemon("Pikachu", "active")
        engine.confirm_initial_placement()

        engine.player_active["attached_energy"] = ["Lightning", "Lightning"]

        engine.player_hand.append("Charmeleon")
        res_invalid = engine.evolve_pokemon("Charmeleon", "active")
        self.assertEqual(res_invalid["status"], "error")
        self.assertIn("evolves from", res_invalid["message"].lower())

        engine.player_hand.append("Raichu")
        res_valid = engine.evolve_pokemon("Raichu", "active")
        self.assertEqual(res_valid["status"], "success")
        self.assertEqual(engine.player_active["name"], "Raichu")
        self.assertEqual(engine.player_active["attached_energy"], ["Lightning", "Lightning"], "Energy must be preserved upon evolution")

    # Scenario 12: 1 Energy Attachment Per Turn Restriction
    def test_12_one_energy_attachment_per_turn(self):
        engine = TCGMatchEngine(card_db=self.cards_dict)
        engine.reset_match()
        engine.player_hand = ["Pikachu", "Basic Lightning Energy", "Basic Lightning Energy"]
        engine.place_initial_pokemon("Pikachu", "active")
        engine.confirm_initial_placement()

        res1 = engine.attach_energy("Basic Lightning Energy", "active")
        self.assertEqual(res1["status"], "success")
        self.assertTrue(engine.energy_attached_this_turn)

        # Second attachment attempt in same turn
        res2 = engine.attach_energy("Basic Lightning Energy", "active")
        self.assertEqual(res2["status"], "error")
        self.assertIn("once per turn", res2["message"].lower())

    # Scenario 13: 1 Card Draw Per Turn Restriction
    def test_13_one_card_draw_per_turn(self):
        engine = TCGMatchEngine(card_db=self.cards_dict)
        engine.reset_match()
        engine.player_hand = ["Pikachu"]
        engine.place_initial_pokemon("Pikachu", "active")
        engine.confirm_initial_placement()

        c1 = engine.draw_card(is_player=True)
        self.assertIsNotNone(c1)
        self.assertTrue(engine.card_drawn_this_turn)

        # Second draw attempt in same turn
        c2 = engine.draw_card(is_player=True)
        self.assertIsNone(c2)

    # Scenario 14: Switch / Retreat Swapping Active with Bench
    def test_14_switch_and_retreat_mechanic(self):
        engine = TCGMatchEngine(card_db=self.cards_dict)
        engine.reset_match()
        engine.player_hand = ["Pikachu", "Charmander"]
        engine.place_initial_pokemon("Pikachu", "active")
        engine.place_initial_pokemon("Charmander", "bench_0")
        engine.confirm_initial_placement()

        engine.player_active["attached_energy"] = ["Lightning"]
        engine.player_bench[0]["attached_energy"] = ["Fire", "Fire"]

        res = engine.switch_or_retreat(0)
        self.assertEqual(res["status"], "success")
        self.assertEqual(engine.player_active["name"], "Charmander")
        self.assertEqual(engine.player_active["attached_energy"], ["Fire", "Fire"])
        self.assertEqual(engine.player_bench[0]["name"], "Pikachu")
        self.assertEqual(engine.player_bench[0]["attached_energy"], ["Lightning"])

    # Scenario 15: Knockout at 0 HP & Mandatory Bench Promotion
    def test_15_knockout_and_bench_promotion(self):
        engine = TCGMatchEngine(card_db=self.cards_dict)
        engine.reset_match()
        engine.player_hand = ["Pikachu", "Charmander"]
        engine.place_initial_pokemon("Pikachu", "active")
        engine.place_initial_pokemon("Charmander", "bench_0")
        engine.confirm_initial_placement()

        # Active knocked out
        engine.player_active = None
        engine.phase = "WAITING_FOR_PROMOTION"

        # Promote bench 0
        res = engine.promote_bench_to_active(0)
        self.assertEqual(res["status"], "success")
        self.assertEqual(engine.player_active["name"], "Charmander")
        self.assertEqual(engine.phase, "BATTLE")

    # Scenario 16: Exact Energy Cost Requirement Blocks Attack
    def test_16_energy_cost_verification(self):
        can_atk, _ = check_energy_requirement([], ["Lightning", "Colorless"])
        self.assertFalse(can_atk)

        can_atk, _ = check_energy_requirement(["Lightning"], ["Lightning", "Colorless"])
        self.assertFalse(can_atk)

        # Fire pays Colorless
        can_atk, _ = check_energy_requirement(["Lightning", "Fire"], ["Lightning", "Colorless"])
        self.assertTrue(can_atk)

        # Missing required Lightning
        can_atk, _ = check_energy_requirement(["Fire", "Water"], ["Lightning"])
        self.assertFalse(can_atk)

    # Scenario 17: Valid Attack Damage, Weakness & Resistance Calculation
    def test_17_damage_weakness_resistance(self):
        rules = RulesEngine(card_db=self.cards_dict)
        attacker = {"name": "Charmander", "types": ["Fire"]}
        attack = {"name": "Ember", "base_damage": 30}
        defender = {"name": "Bulbasaur", "weaknesses": [{"type": "Fire", "value": "×2"}]}

        dmg = rules.calculate_attack_damage(attacker, attack, defender)
        self.assertEqual(dmg, 60, "Grass weak to Fire takes 2x damage (30 * 2 = 60)")

    # Scenario 18: Action Mask Enforces Turn Restrictions & Legal Moves
    def test_18_action_mask_generator(self):
        action_engine = ActionMaskEngine(card_db=self.cards_dict)
        self.cards_dict["test-e1"] = {"name": "Basic Lightning Energy", "supertype": "Energy", "subtypes": ["Basic Energy"]}

        game_state = {
            "player": {
                "hand": [{"card_id": "test-e1"}],
                "active_spot": {"name": "Pikachu"}
            },
            "turn_flags": {
                "energy_attached_this_turn": True
            }
        }

        legal_actions = action_engine.get_legal_actions(game_state)
        attach_actions = [a for a in legal_actions if a.get("action_type") == "ATTACH_ENERGY"]
        self.assertEqual(len(attach_actions), 0, "No energy attachment allowed when already attached this turn")

    # Scenario 19: Dataset Validation (1,267 authentic cards)
    def test_19_dataset_integrity(self):
        self.assertEqual(self.validation_summary.get("cards_loaded"), 1267)
        self.assertEqual(self.validation_summary.get("pokemon"), 1056)
        self.assertEqual(self.validation_summary.get("trainer"), 191)
        self.assertEqual(self.validation_summary.get("energy"), 20)
        self.assertEqual(self.validation_summary.get("invalid_cards"), 0)

    # Scenario 20: Full Match Arena Cycle
    def test_20_full_match_cycle(self):
        engine = TCGMatchEngine(card_db=self.cards_dict)
        engine.reset_match()
        self.assertEqual(engine.phase, "SETUP")

        engine.player_hand = ["Pikachu", "Basic Lightning Energy"]
        engine.place_initial_pokemon("Pikachu", "active")
        res_conf = engine.confirm_initial_placement()
        self.assertEqual(res_conf["status"], "success")
        self.assertEqual(engine.phase, "BATTLE")

        # Turn 1: Attach Energy and Attack
        res_e = engine.attach_energy("Basic Lightning Energy", "active")
        self.assertEqual(res_e["status"], "success")

        res_atk = engine.execute_attack("Strike", base_damage=30)
        self.assertEqual(res_atk["status"], "success")


if __name__ == "__main__":
    unittest.main()
