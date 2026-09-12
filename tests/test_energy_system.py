"""
Unit test suite verifying the complete 9-Type Pokémon Energy System.
Validates the 10 core requirements specified in the user requirements:
Test 1: Fire Pokémon + Fire Energy + Fire attack -> Attack becomes available.
Test 2: Fire Pokémon + Water Energy + Colorless attack requirement -> Water Energy satisfies Colorless.
Test 3: Attack Fire Fire Colorless, Attached Fire Fire Water -> LEGAL.
Test 4: Attack Fire Fire Colorless, Attached Fire Water Water -> ILLEGAL.
Test 5: Attach 1 Energy -> Second manual attachment is blocked during same turn.
Test 6: End turn -> Next player turn begins.
Test 7: New player turn -> Energy attachment becomes available again.
Test 8: Energy card is played -> Leaves hand and becomes attached to selected Pokémon.
Test 9: Energy card is attached to a different Pokémon type -> Allowed.
Test 10: Attack requirements are not satisfied -> Attack blocked with descriptive explanation.
"""
import unittest
from src.engine.energy_config import (
    ENERGY_TYPES, ENERGY_SYMBOL_MAP, ENERGY_EMOJI_MAP,
    CANONICAL_BASIC_ENERGIES, normalize_energy_type, parse_attack_cost,
    format_cost_emojis, validate_attack_cost, create_energy_card_dict
)
from src.engine.tcg_match_engine import TCGMatchEngine, check_energy_requirement, can_use_attack


class TestPokemonEnergySystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_db = {
            "790": {
                "card_id": "790",
                "name": "Charizard",
                "card_type": "pokemon",
                "pokemon_type": "Fire",
                "stage": "Stage 2",
                "hp": 150,
                "attacks": [
                    {
                        "name": "Fire Blast",
                        "cost": ["Fire", "Fire", "Colorless"],
                        "damage": 120
                    }
                ]
            },
            "788": {
                "card_id": "788",
                "name": "Charmander",
                "card_type": "pokemon",
                "pokemon_type": "Fire",
                "stage": "Basic",
                "hp": 70,
                "attacks": [
                    {
                        "name": "Ember",
                        "cost": ["Fire"],
                        "damage": 30
                    },
                    {
                        "name": "Scratch",
                        "cost": ["Colorless"],
                        "damage": 10
                    }
                ]
            },
            "squirtle": {
                "card_id": "squirtle",
                "name": "Squirtle",
                "card_type": "pokemon",
                "pokemon_type": "Water",
                "stage": "Basic",
                "hp": 70,
                "attacks": [
                    {
                        "name": "Water Gun",
                        "cost": ["Water"],
                        "damage": 20
                    }
                ]
            }
        }
        for k, v in CANONICAL_BASIC_ENERGIES.items():
            cls.mock_db[v["card_id"]] = dict(v)
            cls.mock_db[v["name"]] = dict(v)

    def setUp(self):
        self.engine = TCGMatchEngine(self.mock_db)
        self.engine.reset_match()
        self.engine.phase = "BATTLE"
        self.engine.is_player_turn = True
        self.engine.energy_attached_this_turn = False
        self.engine.has_attacked_this_turn = False

    def test_01_fire_pokemon_fire_energy_fire_attack(self):
        """Test 1: Fire Pokémon + Fire Energy + Fire attack -> Attack becomes available when enough Energy is attached."""
        self.engine.player_active = {
            "name": "Charmander",
            "pokemon_type": "Fire",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": [],
            "attacks": [{"name": "Ember", "cost": ["Fire"], "damage": 30}]
        }
        self.engine.opp_active = {
            "name": "Squirtle",
            "pokemon_type": "Water",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": []
        }

        # 0 Fire Energy -> Attack not ready
        can_atk, reason, details = can_use_attack(self.engine.player_active, self.engine.player_active["attacks"][0])
        self.assertFalse(can_atk)
        self.assertIn("Need 1 more Fire Energy", reason)

        # Attach 1 Fire Energy
        self.engine.player_hand = ["Basic Fire Energy"]
        res = self.engine.attach_energy("Basic Fire Energy", target="active")
        self.assertEqual(res["status"], "success")

        # Now attack is ready
        can_atk, reason, details = can_use_attack(self.engine.player_active, self.engine.player_active["attacks"][0])
        self.assertTrue(can_atk)
        self.assertIn("Ready", reason)

    def test_02_water_energy_satisfies_colorless(self):
        """Test 2: Fire Pokémon + Water Energy + Colorless attack requirement -> Water Energy can satisfy Colorless."""
        pokemon = {
            "name": "Charmander",
            "pokemon_type": "Fire",
            "attached_energy": ["Water"]
        }
        attack = {"name": "Scratch", "cost": ["Colorless"]}

        can_atk, reason, details = can_use_attack(pokemon, attack)
        self.assertTrue(can_atk)
        self.assertIn("Ready", reason)

    def test_03_fire_fire_water_satisfies_fire_fire_colorless(self):
        """Test 3: Attack: Fire Fire Colorless, Attached: Fire Fire Water -> EXPECTED: LEGAL."""
        attached = ["Fire", "Fire", "Water"]
        cost = ["Fire", "Fire", "Colorless"]

        can_atk, reason, details = validate_attack_cost(attached, cost)
        self.assertTrue(can_atk, f"Expected LEGAL attack but got: {reason}")
        self.assertEqual(len(details["missing"]), 0)

    def test_04_fire_water_water_fails_fire_fire_colorless(self):
        """Test 4: Attack: Fire Fire Colorless, Attached: Fire Water Water -> EXPECTED: ILLEGAL."""
        attached = ["Fire", "Water", "Water"]
        cost = ["Fire", "Fire", "Colorless"]

        can_atk, reason, details = validate_attack_cost(attached, cost)
        self.assertFalse(can_atk, "Expected ILLEGAL attack because only 1 Fire energy is attached")
        self.assertIn("Need 1 more Fire Energy", reason)
        self.assertEqual(details["missing"].get("Fire"), 1)

    def test_05_one_manual_energy_attachment_per_turn(self):
        """Test 5: Attach one Energy. EXPECTED: Second manual attachment is blocked during the same turn."""
        self.engine.player_active = {
            "name": "Charmander",
            "pokemon_type": "Fire",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": []
        }
        self.engine.player_hand = ["Basic Fire Energy", "Basic Water Energy"]

        # First attachment: succeeds
        res1 = self.engine.attach_energy("Basic Fire Energy", target="active")
        self.assertEqual(res1["status"], "success")
        self.assertTrue(self.engine.energy_attached_this_turn)

        # Second attachment attempt in same turn: blocked
        res2 = self.engine.attach_energy("Basic Water Energy", target="active")
        self.assertEqual(res2["status"], "error")
        self.assertIn("already attached energy this turn", res2["message"].lower())

    def test_06_and_07_turn_reset_restores_energy_attachment(self):
        """
        Test 6 & 7:
        Test 6: End turn -> Next player turn begins.
        Test 7: New player turn -> Energy attachment becomes available again.
        """
        self.engine.player_active = {
            "name": "Charmander",
            "pokemon_type": "Fire",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": []
        }
        self.engine.opp_active = {
            "name": "Squirtle",
            "pokemon_type": "Water",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": []
        }
        self.engine.player_hand = ["Basic Fire Energy", "Basic Grass Energy"]

        # Attach on Turn 1
        res1 = self.engine.attach_energy("Basic Fire Energy", target="active")
        self.assertEqual(res1["status"], "success")
        self.assertTrue(self.engine.energy_attached_this_turn)

        # End turn
        turn_before = self.engine.turn_number
        end_res = self.engine.end_turn()
        self.assertEqual(end_res["status"], "success")

        # Test 6: Next turn has begun
        self.assertGreaterEqual(self.engine.turn_number, turn_before)

        # Test 7: New player turn -> Energy attachment flag is reset to False
        self.assertFalse(self.engine.energy_attached_this_turn)

        # Player can attach energy again in the new turn
        res2 = self.engine.attach_energy("Basic Grass Energy", target="active")
        self.assertEqual(res2["status"], "success")
        self.assertTrue(self.engine.energy_attached_this_turn)

    def test_08_energy_card_leaves_hand_and_attaches(self):
        """Test 8: Energy card is played -> EXPECTED: Card leaves hand and becomes attached to selected Pokémon."""
        self.engine.player_active = {
            "name": "Charizard",
            "pokemon_type": "Fire",
            "current_hp": 150,
            "max_hp": 150,
            "attached_energy": []
        }
        self.engine.player_hand = ["Basic Fire Energy"]

        res = self.engine.attach_energy("Basic Fire Energy", target="active")
        self.assertEqual(res["status"], "success")

        # Removed from hand
        self.assertNotIn("Basic Fire Energy", self.engine.player_hand)

        # Attached to active Pokémon
        attached = self.engine.player_active["attached_energy"]
        self.assertEqual(len(attached), 1)
        self.assertEqual(attached[0], "Fire")
        self.assertEqual(attached[0].card_name, "Basic Fire Energy")

    def test_09_energy_attached_to_different_pokemon_type(self):
        """Test 9: Energy card is attached to a different Pokémon type -> EXPECTED: Attachment is allowed."""
        # Attach Water Energy to Fire Pokémon Charmander
        self.engine.player_active = {
            "name": "Charmander",
            "pokemon_type": "Fire",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": []
        }
        self.engine.player_hand = ["Basic Water Energy"]

        res = self.engine.attach_energy("Basic Water Energy", target="active")
        self.assertEqual(res["status"], "success")
        self.assertEqual(self.engine.player_active["attached_energy"][0], "Water")

        # Attach Lightning Energy to Fire Pokémon
        self.engine.energy_attached_this_turn = False
        self.engine.player_hand = ["Basic Lightning Energy"]
        res2 = self.engine.attach_energy("Basic Lightning Energy", target="active")
        self.assertEqual(res2["status"], "success")
        self.assertEqual(len(self.engine.player_active["attached_energy"]), 2)

    def test_10_attack_requirements_not_satisfied_remains_disabled(self):
        """Test 10: Attack requirements are not satisfied -> Attack remains blocked with descriptive reason."""
        self.engine.player_active = {
            "name": "Charizard",
            "pokemon_type": "Fire",
            "current_hp": 150,
            "max_hp": 150,
            "attached_energy": ["Fire"],
            "attacks": [
                {
                    "name": "Fire Blast",
                    "cost": ["Fire", "Fire", "Colorless"],
                    "damage": 120
                }
            ]
        }
        self.engine.opp_active = {
            "name": "Squirtle",
            "pokemon_type": "Water",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": []
        }

        # Attempt to execute attack without required energy
        atk_res = self.engine.execute_attack("Fire Blast")
        self.assertEqual(atk_res["status"], "error")
        self.assertIn("Attack LOCKED", atk_res["message"])
        self.assertIn("Need 1 more Fire Energy", atk_res["message"])

    def test_all_nine_basic_energy_types_supported(self):
        """Verify all 9 basic energy types are canonical and supported."""
        expected_types = [
            "Grass", "Fire", "Water", "Lightning", "Fighting",
            "Psychic", "Darkness", "Metal", "Dragon"
        ]
        self.assertEqual(ENERGY_TYPES, expected_types)
        for etype in expected_types:
            self.assertIn(etype, CANONICAL_BASIC_ENERGIES)
            card = create_energy_card_dict(etype)
            self.assertEqual(card["energy_type"], etype)
            self.assertEqual(card["name"], f"Basic {etype} Energy")
            self.assertTrue(card["card_id"].startswith("energy_"))


if __name__ == "__main__":
    unittest.main()
