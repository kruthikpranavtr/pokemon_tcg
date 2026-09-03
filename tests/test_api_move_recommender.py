"""
Test suite for API Key Authentication & Card Details Move Recommender
"""
import unittest
from fastapi.testclient import TestClient
from src.api import app


class TestAPIKeyAndMoveRecommender(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.valid_api_key = "tcg-live-secret-key-2026"
        self.invalid_api_key = "bad-key-123"

    def test_auth_verification(self):
        # 1. Missing key -> 401
        res = self.client.get("/api/v1/auth/verify")
        self.assertEqual(res.status_code, 401)

        # 2. Invalid key -> 401
        res = self.client.get("/api/v1/auth/verify", headers={"X-API-Key": self.invalid_api_key})
        self.assertEqual(res.status_code, 401)

        # 3. Valid key in header -> 200
        res = self.client.get("/api/v1/auth/verify", headers={"X-API-Key": self.valid_api_key})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get("status"), "authenticated")

        # 4. Valid key in query parameter -> 200
        res = self.client.get(f"/api/v1/auth/verify?api_key={self.valid_api_key}")
        self.assertEqual(res.status_code, 200)

    def test_recommend_move_with_card_details(self):
        payload = {
            "session_id": "test-match-1",
            "our_cards": {
                "hand_cards": [
                    "Charizard ex",
                    "Professor's Research",
                    "Basic Fire Energy",
                    "Ultra Ball",
                    "Rare Candy"
                ],
                "active_pokemon": {
                    "name": "Charmander",
                    "current_hp": 70,
                    "attached_energy": ["Fire"],
                    "turns_in_play": 1
                },
                "bench_pokemon": [
                    {"name": "Pidgey", "current_hp": 60}
                ],
                "prizes_remaining": 6
            },
            "opponent_cards": {
                "deck_archetype": "miraidon-ex-regieleki",
                "active_pokemon": {
                    "name": "Miraidon ex",
                    "current_hp": 220,
                    "attached_energy": ["Lightning", "Lightning"]
                },
                "bench_pokemon": [
                    {"name": "Iron Hands ex", "current_hp": 230}
                ],
                "prizes_remaining": 6
            },
            "turn_context": {
                "turn_number": 3,
                "supporter_played_this_turn": False,
                "energy_attached_this_turn": False
            }
        }

        # Request with valid API key
        res = self.client.post(
            "/api/v1/recommend-move",
            headers={"X-API-Key": self.valid_api_key},
            json=payload
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("current_win_probability", data)
        self.assertIn("top_recommended_move", data)
        self.assertTrue(len(data.get("all_recommended_moves", [])) > 0)

        # Verify recommended moves have rationales and actions
        top_move = data["top_recommended_move"]
        self.assertIn("action_type", top_move)
        self.assertIn("strategic_rationale", top_move)
        self.assertIn("expected_win_probability", top_move)

    def test_card_search_endpoint(self):
        res = self.client.get("/api/v1/cards/search?q=charizard")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["results_count"] > 0)


if __name__ == "__main__":
    unittest.main()
