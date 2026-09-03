"""
Unit Tests for 60-Card Pokémon TCG Match Engine and AI Guidance
"""
import unittest
import json
from src.engine.tcg_match_engine import TCGMatchEngine
from fastapi.testclient import TestClient
from src.api import app

class Test60CardMatchEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open("data/cards_dataset.json", "r", encoding="utf-8") as f:
            cards_data = json.load(f)
            cls.card_db = {c["card_id"]: c for c in cards_data["cards"]}
        cls.engine = TCGMatchEngine(cls.card_db)
        cls.client = TestClient(app)

    def test_60card_match_setup(self):
        self.engine.reset_match("charizard-ex-pidgeot", "miraidon-ex-regieleki")
        # Check 60 cards total per player: hand (7) + prizes (6) + active (1) + bench (0-1) + deck = 60
        total_p_cards = len(self.engine.player_hand) + len(self.engine.player_prizes) + 1 + len(self.engine.player_bench) + len(self.engine.player_deck)
        self.assertEqual(total_p_cards, 60)
        self.assertEqual(len(self.engine.player_prizes), 6)
        self.assertTrue(self.engine.player_active["current_hp"] > 0)
        self.assertTrue(self.engine.opp_active["current_hp"] > 0)

    def test_play_actions_and_energy(self):
        self.engine.reset_match()
        self.engine.player_hand.append("Basic Fire Energy")
        res = self.engine.play_hand_card("Basic Fire Energy")
        self.assertEqual(res["status"], "success")
        self.assertTrue(self.engine.energy_attached_this_turn)

        # Test duplicate energy attachment failure
        self.engine.player_hand.append("Basic Fire Energy")
        res2 = self.engine.play_hand_card("Basic Fire Energy")
        self.assertEqual(res2["status"], "error")

    def test_attack_and_knockout_resolution(self):
        self.engine.reset_match()
        # Add bench to opponent so match continues after active KO
        self.engine.opp_bench.append({
            "name": "Iron Hands ex", "current_hp": 230, "max_hp": 230, "attached_energy": []
        })
        self.engine.opp_active["current_hp"] = 50
        res = self.engine.execute_attack("Burning Darkness", base_damage=180)
        self.assertIn(res["status"], ["success", "match_won"])
        self.assertTrue(res.get("knockout") or res.get("ko"))
        self.assertTrue(self.engine.player_prizes_taken >= 1)

    def test_api_60card_match_endpoints(self):
        # 1. Start Match
        res = self.client.post(
            "/api/v1/match/start",
            headers={"X-API-Key": "tcg-live-secret-key-2026"},
            json={"player_deck_id": "charizard-ex-pidgeot", "opp_deck_id": "miraidon-ex-regieleki"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("ai_recommendation", data)

        # 2. Draw Card
        res_draw = self.client.post(
            "/api/v1/match/draw",
            headers={"X-API-Key": "tcg-live-secret-key-2026"}
        )
        self.assertEqual(res_draw.status_code, 200)

        # 3. Attack
        res_atk = self.client.post(
            "/api/v1/match/attack",
            headers={"X-API-Key": "tcg-live-secret-key-2026"},
            json={"attack_name": "Burning Darkness", "base_damage": 180}
        )
        self.assertEqual(res_atk.status_code, 200)

        # 4. End Turn
        res_end = self.client.post(
            "/api/v1/match/end-turn",
            headers={"X-API-Key": "tcg-live-secret-key-2026"}
        )
        self.assertEqual(res_end.status_code, 200)

    def test_custom_deck_match_setup(self):
        # Create a custom 60-card list
        custom_deck = ["Charmander"] * 4 + ["Arven"] * 4 + ["Ultra Ball"] * 4 + ["Basic Fire Energy"] * 48
        res = self.client.post(
            "/api/v1/match/start",
            headers={"X-API-Key": "tcg-live-secret-key-2026"},
            json={"custom_deck_list": custom_deck, "opp_deck_id": "miraidon-ex-regieleki"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["match_state"]["player"]["hand"]), 4)
        total_p = data["deck_counts"]["player_deck"] + data["deck_counts"]["player_hand"] + data["deck_counts"]["player_prizes"] + 1 + len(data["match_state"]["player"]["bench"])
        self.assertEqual(total_p, 60)


if __name__ == "__main__":
    unittest.main()
