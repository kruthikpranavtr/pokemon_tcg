"""
Unit tests for Pokémon Type Advantage & Disadvantage Damage System.
Rules tested:
1. Type Advantage: +50% damage (1.5x) against opponent (e.g. Water vs Fire, Fire vs Grass, Grass vs Water).
2. Type Disadvantage: 50% less damage (0.5x) against opponent (e.g. Water vs Grass/Lightning, Fire vs Water).
3. Neutral Matchup: Normal damage (1.0x) for neutral interactions.
4. Non-Blocking Attacks: Attacks are never blocked or reduced to 0 by type (minimum 1 DMG).
5. Opponent AI: Opponent adheres to the exact same 1.5x / 0.5x / 1.0x damage rules.
"""
import unittest
from src.engine.energy_config import (
    get_type_effectiveness, calculate_matchup_damage,
    TYPE_ADVANTAGES, TYPE_DISADVANTAGES, CANONICAL_BASIC_ENERGIES
)
from src.engine.tcg_match_engine import TCGMatchEngine


class TestTypeAdvantageSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mock_db = {
            "charmander": {
                "card_id": "charmander",
                "name": "Charmander",
                "card_type": "pokemon",
                "pokemon_type": "Fire",
                "weakness": "Water",
                "stage": "Basic",
                "hp": 70,
                "attacks": [
                    {"name": "Ember", "cost": ["Fire"], "damage": 30}
                ]
            },
            "squirtle": {
                "card_id": "squirtle",
                "name": "Squirtle",
                "card_type": "pokemon",
                "pokemon_type": "Water",
                "weakness": "Lightning",
                "stage": "Basic",
                "hp": 70,
                "attacks": [
                    {"name": "Water Gun", "cost": ["Water"], "damage": 40}
                ]
            },
            "bulbasaur": {
                "card_id": "bulbasaur",
                "name": "Bulbasaur",
                "card_type": "pokemon",
                "pokemon_type": "Grass",
                "weakness": "Fire",
                "stage": "Basic",
                "hp": 70,
                "attacks": [
                    {"name": "Vine Whip", "cost": ["Grass"], "damage": 30}
                ]
            },
            "pikachu": {
                "card_id": "pikachu",
                "name": "Pikachu",
                "card_type": "pokemon",
                "pokemon_type": "Lightning",
                "weakness": "Fighting",
                "stage": "Basic",
                "hp": 70,
                "attacks": [
                    {"name": "Thunder Shock", "cost": ["Lightning"], "damage": 30}
                ]
            }
        }
        for k, v in CANONICAL_BASIC_ENERGIES.items():
            cls.mock_db[v["card_id"]] = dict(v)

    def setUp(self):
        self.engine = TCGMatchEngine(card_db=self.mock_db)
        self.engine.phase = "BATTLE"
        self.engine.is_player_turn = True

    # 1. Direct Helper Calculations
    def test_01_water_vs_fire_advantage(self):
        """Water attacking Fire deals +50% damage (1.5x)."""
        dmg, mult, label, reason = calculate_matchup_damage(40, "Water", "Fire")
        self.assertEqual(mult, 1.5)
        self.assertEqual(label, "ADVANTAGE")
        self.assertEqual(dmg, 60)

        # 30 base dmg -> 45
        dmg30, _, _, _ = calculate_matchup_damage(30, "Water", "Fire")
        self.assertEqual(dmg30, 45)

    def test_02_water_vs_grass_disadvantage(self):
        """Water attacking Grass deals 50% less damage (0.5x)."""
        dmg, mult, label, reason = calculate_matchup_damage(40, "Water", "Grass")
        self.assertEqual(mult, 0.5)
        self.assertEqual(label, "DISADVANTAGE")
        self.assertEqual(dmg, 20)

        # 30 base dmg -> 15
        dmg30, _, _, _ = calculate_matchup_damage(30, "Water", "Grass")
        self.assertEqual(dmg30, 15)

    def test_03_water_vs_lightning_disadvantage(self):
        """Water attacking Lightning deals 50% less damage (0.5x)."""
        dmg, mult, label, reason = calculate_matchup_damage(30, "Water", "Lightning")
        self.assertEqual(mult, 0.5)
        self.assertEqual(label, "DISADVANTAGE")
        self.assertEqual(dmg, 15)

    def test_04_neutral_matchups(self):
        """Neutral matchups deal normal base damage (1.0x)."""
        dmg, mult, label, reason = calculate_matchup_damage(40, "Water", "Psychic")
        self.assertEqual(mult, 1.0)
        self.assertEqual(label, "NEUTRAL")
        self.assertEqual(dmg, 40)

        dmg_col, mult_col, _, _ = calculate_matchup_damage(30, "Colorless", "Fire")
        self.assertEqual(mult_col, 1.0)
        self.assertEqual(dmg_col, 30)

    def test_05_fire_type_matchups(self):
        """Fire deals +50% vs Grass/Metal and -50% vs Water."""
        dmg_grass, mult_grass, _, _ = calculate_matchup_damage(40, "Fire", "Grass")
        self.assertEqual(mult_grass, 1.5)
        self.assertEqual(dmg_grass, 60)

        dmg_metal, mult_metal, _, _ = calculate_matchup_damage(40, "Fire", "Metal")
        self.assertEqual(mult_metal, 1.5)
        self.assertEqual(dmg_metal, 60)

        dmg_water, mult_water, _, _ = calculate_matchup_damage(40, "Fire", "Water")
        self.assertEqual(mult_water, 0.5)
        self.assertEqual(dmg_water, 20)

    def test_06_non_blocking_minimum_damage(self):
        """Attacks are never reduced to 0 by type disadvantage (minimum 1 DMG)."""
        # Base 1 DMG at 50% reduction must still deal at least 1 DMG
        dmg1, mult1, _, _ = calculate_matchup_damage(1, "Water", "Grass")
        self.assertEqual(mult1, 0.5)
        self.assertGreaterEqual(dmg1, 1)

        # Base 2 DMG at 50% reduction = 1 DMG
        dmg2, _, _, _ = calculate_matchup_damage(2, "Water", "Grass")
        self.assertEqual(dmg2, 1)

    # 2. Match Engine execute_attack Integration Tests
    def test_07_engine_execute_attack_with_advantage(self):
        """Engine execute_attack applies +50% damage and updates log."""
        self.engine.player_active = {
            "name": "Squirtle",
            "pokemon_type": "Water",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": ["Water"]
        }
        self.engine.opp_active = {
            "name": "Charmander",
            "pokemon_type": "Fire",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": ["Fire"]
        }

        # Squirtle attacks Charmander with base 40 damage -> 60 DMG (+50%)
        res = self.engine.execute_attack("Water Gun", base_damage=40)
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(self.engine.opp_active["current_hp"], 10)  # 70 - 60 = 10
        self.assertTrue(any("+50% Type Advantage vs Fire!" in msg for msg in self.engine.match_log))

    def test_08_engine_execute_attack_with_disadvantage(self):
        """Engine execute_attack applies -50% damage and updates log."""
        self.engine.player_active = {
            "name": "Squirtle",
            "pokemon_type": "Water",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": ["Water"]
        }
        self.engine.opp_active = {
            "name": "Bulbasaur",
            "pokemon_type": "Grass",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": ["Grass"]
        }

        # Squirtle attacks Bulbasaur with base 40 damage -> 20 DMG (-50%)
        res = self.engine.execute_attack("Water Gun", base_damage=40)
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(self.engine.opp_active["current_hp"], 50)  # 70 - 20 = 50
        self.assertTrue(any("-50% Type Disadvantage vs Grass" in msg for msg in self.engine.match_log))

    def test_09_opponent_ai_attack_respects_type_advantage(self):
        """Opponent AI attacks player applying the same +50% advantage scaling."""
        self.engine.player_active = {
            "name": "Bulbasaur",
            "pokemon_type": "Grass",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": ["Grass"]
        }
        self.engine.opp_active = {
            "name": "Charmander",
            "pokemon_type": "Fire",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": ["Fire"],
            "attacks": [
                {"name": "Ember", "cost": ["Fire"], "damage": 30}
            ]
        }
        self.engine.opp_hand = []

        # End turn simulates opponent turn: Charmander (Fire) attacks Bulbasaur (Grass)
        # Base 30 damage -> 45 DMG (+50%)
        self.engine.end_turn()

        # Bulbasaur HP: 70 - 45 = 25
        self.assertEqual(self.engine.player_active["current_hp"], 25)
        self.assertTrue(any("+50% Type Advantage vs Grass!" in msg for msg in self.engine.match_log))

    def test_10_card_metadata_weakness_triggers_advantage(self):
        """If card metadata has explicit weakness, it guarantees +50% advantage."""
        # Defender has explicit weakness to Lightning
        dmg, mult, label, _ = calculate_matchup_damage(
            base_damage=40,
            attacker_type="Lightning",
            defender_type="Colorless",
            defender_weakness="Lightning"
        )
        self.assertEqual(mult, 1.5)
        self.assertEqual(dmg, 60)


if __name__ == "__main__":
    unittest.main()
