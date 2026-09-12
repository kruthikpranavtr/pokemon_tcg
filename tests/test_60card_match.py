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
        self.engine.reset_match("charizard-fire", "pikachu-lightning")
        # 60 cards total per player: hand (5) + prizes (6) + deck (49) = 60
        total_p_cards = len(self.engine.player_hand) + len(self.engine.player_prizes) + len(self.engine.player_deck)
        self.assertEqual(total_p_cards, 60)
        self.assertEqual(len(self.engine.player_prizes), 6)
        self.assertEqual(len(self.engine.player_hand), 5)
        self.assertEqual(self.engine.phase, "SETUP")
        self.assertTrue(self.engine.opp_active["current_hp"] > 0)

    def test_play_actions_and_energy(self):
        self.engine.reset_match()
        self.engine.player_active = {
            "name": "Charmander", "current_hp": 70, "max_hp": 70,
            "pokemon_type": "Fire", "attached_energy": []
        }
        self.engine.phase = "BATTLE"
        self.engine.player_hand.append("Basic Fire Energy")
        res = self.engine.attach_energy("Basic Fire Energy", target="active")
        self.assertEqual(res["status"], "success")
        self.assertTrue(self.engine.energy_attached_this_turn)

        # Test duplicate energy attachment failure
        self.engine.player_hand.append("Basic Fire Energy")
        res2 = self.engine.attach_energy("Basic Fire Energy", target="active")
        self.assertEqual(res2["status"], "error")

    def test_attack_and_knockout_resolution(self):
        self.engine.reset_match()
        self.engine.phase = "BATTLE"
        self.engine.player_active = {
            "name": "Charizard ex", "current_hp": 330, "max_hp": 330,
            "pokemon_type": "Fire", "attached_energy": ["Fire", "Fire"],
            "attacks": [{"name": "Burning Darkness", "damage": 180, "cost": ["Fire", "Fire"]}]
        }
        # Add bench to opponent so match continues after active KO
        self.engine.opp_bench[0] = {
            "name": "Pikachu ex", "current_hp": 200, "max_hp": 200, "attached_energy": []
        }
        self.engine.opp_active = {
            "name": "Miraidon ex", "current_hp": 50, "max_hp": 220, "attached_energy": []
        }
        res = self.engine.execute_attack("Burning Darkness", base_damage=180)
        self.assertIn(res["status"], ["success", "match_won"])
        self.assertTrue(res.get("knockout") or res.get("ko"))
        self.assertTrue(self.engine.player_prizes_taken >= 1)

    def test_api_60card_match_endpoints(self):
        # 1. Start Match
        res = self.client.post(
            "/api/v1/match/start",
            headers={"X-API-Key": "tcg-live-secret-key-2026"},
            json={"player_deck_id": "charizard-fire", "opp_deck_id": "pikachu-lightning"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("ai_recommendation", data)

        # 2. Place Active Pokémon in Setup
        hand = self.engine.player_hand
        basic_card = next((c for c in hand if self.engine.card_db.get(c, {}).get("stage") == "Basic" and self.engine.card_db.get(c, {}).get("card_type") == "pokemon"), None)
        if not basic_card:
            basic_card = "Charmander"
            self.engine.player_hand.append("Charmander")

        res_place = self.client.post(
            "/api/v1/match/initial-place",
            headers={"X-API-Key": "tcg-live-secret-key-2026"},
            json={"card_name": basic_card, "slot": "active"}
        )
        self.assertEqual(res_place.status_code, 200)

        res_confirm = self.client.post(
            "/api/v1/match/confirm-setup",
            headers={"X-API-Key": "tcg-live-secret-key-2026"}
        )
        self.assertEqual(res_confirm.status_code, 200)

        # 3. Draw Card
        res_draw = self.client.post(
            "/api/v1/match/draw",
            headers={"X-API-Key": "tcg-live-secret-key-2026"}
        )
        self.assertEqual(res_draw.status_code, 200)

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
            json={"custom_deck_list": custom_deck, "opp_deck_id": "pikachu-lightning"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["deck_counts"]["player_hand"], 5)
        total_p = data["deck_counts"]["player_deck"] + data["deck_counts"]["player_hand"] + data["deck_counts"]["player_prizes"]
        self.assertEqual(total_p, 60)


if __name__ == "__main__":
    unittest.main()
