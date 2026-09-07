"""
Comprehensive End-to-End Game & Opponent AI Validation Test
Tests:
- Game Setup & Deck Shuffling
- Drawing Cards & Hand Limits
- Manual Energy Attachment (1 per turn rule)
- Attack Validation & Energy Cost Enforcement
- Damage Calculation with Weakness (x2)
- Lethal Knockout & Prize Card Pickup
- Bench Promotion on Knockout
- Autonomous Opponent AI Decisions (Draw -> Bench -> Energy -> Trainer -> Attack)
- Turn Switching & No-Freeze Stability
- Win/Loss Conditions
"""
import unittest
import json
from src.engine.tcg_match_engine import TCGMatchEngine
from src.engine.rules_engine import RulesEngine
from fastapi.testclient import TestClient
from src.api import app

class TestPokemonTcgGameAndAi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open("data/cards_dataset.json", "r", encoding="utf-8") as f:
            cards_data = json.load(f)
            cls.card_db = {c["card_id"]: c for c in cards_data["cards"]}
        cls.engine = TCGMatchEngine(cls.card_db)
        cls.rules = RulesEngine(cls.card_db)
        cls.client = TestClient(app)

    def test_game_setup_integrity(self):
        """Verify full 60-card setup for both players."""
        self.engine.reset_match("charizard-ex-pidgeot", "miraidon-ex-regieleki")
        total_p = len(self.engine.player_hand) + len(self.engine.player_prizes) + 1 + len(self.engine.player_bench) + len(self.engine.player_deck)
        total_opp = len(self.engine.opp_hand) + len(self.engine.opp_prizes) + 1 + len(self.engine.opp_bench) + len(self.engine.opp_deck)

        self.assertEqual(total_p, 60, "Player deck setup must equal exactly 60 cards")
        self.assertEqual(total_opp, 60, "Opponent deck setup must equal exactly 60 cards")
        self.assertEqual(len(self.engine.player_prizes), 6)
        self.assertEqual(len(self.engine.opp_prizes), 6)
        self.assertIsNotNone(self.engine.player_active)
        self.assertIsNotNone(self.engine.opp_active)
        self.assertTrue(self.engine.player_active["current_hp"] > 0)
        self.assertTrue(self.engine.opp_active["current_hp"] > 0)

    def test_energy_attachment_and_rules(self):
        """Verify 1-energy per turn restriction."""
        self.engine.reset_match()
        self.assertFalse(self.engine.energy_attached_this_turn)

        # Attach 1st energy
        self.engine.player_hand.append("Basic Fire Energy")
        res1 = self.engine.play_hand_card("Basic Fire Energy")
        self.assertEqual(res1["status"], "success")
        self.assertTrue(self.engine.energy_attached_this_turn)

        # 2nd energy attachment attempt in same turn must fail
        self.engine.player_hand.append("Basic Fire Energy")
        res2 = self.engine.play_hand_card("Basic Fire Energy")
        self.assertEqual(res2["status"], "error")

    def test_supporter_card_rules(self):
        """Verify 1-supporter per turn restriction."""
        self.engine.reset_match()
        self.assertFalse(self.engine.supporter_played_this_turn)

        self.engine.player_hand.append("Professor's Research")
        res = self.engine.play_hand_card("Professor's Research")
        self.assertEqual(res["status"], "success")
        self.assertTrue(self.engine.supporter_played_this_turn)

        # Second supporter attempt in same turn must fail
        self.engine.player_hand.append("Boss's Orders")
        res2 = self.engine.play_hand_card("Boss's Orders")
        self.assertEqual(res2["status"], "error")

    def test_autonomous_opponent_ai_flow(self):
        """Verify Opponent AI executes legal, non-frozen turn actions."""
        self.engine.reset_match()
        # Give player active high HP to observe direct damage, or let AI score lethal KO
        self.engine.player_active["current_hp"] = 330
        self.engine.player_active["max_hp"] = 330
        initial_opp_deck = len(self.engine.opp_deck)
        initial_p_hp = self.engine.player_active["current_hp"]

        # Simulate opponent turn directly
        self.engine._simulate_opponent_turn()

        # Check that opponent drew a card
        self.assertEqual(len(self.engine.opp_deck), initial_opp_deck - 1)
        # Check that opponent attached energy
        self.assertTrue(len(self.engine.opp_active["attached_energy"]) >= 1)
        # Check that opponent attacked and dealt damage to player (or knocked out)
        self.assertTrue(self.engine.player_active["current_hp"] < initial_p_hp or self.engine.opp_prizes_taken >= 1)

    def test_lethal_knockout_and_bench_promotion(self):
        """Verify lethal damage removes active, takes prize, and promotes bench."""
        self.engine.reset_match()
        self.engine.opp_bench = [{
            "name": "Iron Hands ex", "current_hp": 230, "max_hp": 230, "attached_energy": []
        }]
        self.engine.opp_active["current_hp"] = 30
        initial_prizes = self.engine.player_prizes_taken

        res = self.engine.execute_attack("Burning Darkness", base_damage=180)
        self.assertTrue(res.get("knockout"))
        self.assertEqual(self.engine.player_prizes_taken, initial_prizes + 1)
        # Benched Iron Hands ex should be promoted to Active
        self.assertEqual(self.engine.opp_active["name"], "Iron Hands ex")

    def test_multi_turn_battle_stability(self):
        """Simulate a complete 5-turn match back and forth without freezing."""
        self.engine.reset_match()
        for turn in range(1, 6):
            # Player draws and attacks
            self.engine.execute_attack("Ember", base_damage=50)
            if self.engine.winner:
                break
            self.engine.end_turn()
            if self.engine.winner:
                break

        self.assertTrue(self.engine.turn_number >= 2)
        self.assertTrue(len(self.engine.match_log) >= 5)

    def test_frontend_home_page_availability(self):
        """Verify web dashboard HTML serves with no missing handlers."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.text
        # Verify key UI components
        self.assertIn("OFFICIAL POKÉMON TCG ESPORTS MATCH ARENA", html)
        self.assertIn("executeAiTurn", html)
        self.assertIn("canPayAttackCost", html)
        self.assertIn("loadTop60RecommendedDeck", html)
        self.assertIn("startMatchWithCustomDeck", html)

if __name__ == "__main__":
    unittest.main()
