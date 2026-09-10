"""
Collection-to-Gameplay Integration Test Suite.
Validates:
1. Master cards endpoint returns full dataset with category & search.
2. User can only validate/start battle with owned cards.
3. User cannot pick Stage 1 or Stage 2 Pokémon as starting cards.
4. Deck validation and evolution integrity.
5. Pack history endpoint returns accurate history logs.
"""
import unittest
import os
import sys
import secrets
from fastapi.testclient import TestClient

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from src.api import app
import src.database as db
from src.pack_engine import pack_engine


class TestCollectionGameplayIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()
        cls.client = TestClient(app)

    def test_master_cards_api(self):
        """Verify master cards API exposes all 1,280+ cards without slice/hardcoded limit."""
        res = self.client.get("/api/v1/cards/master?limit=10")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertGreater(data["total"], 1200, "Master database must contain >1200 cards")
        self.assertEqual(len(data["cards"]), 10)

        # Category filter: pokemon
        pkmn_res = self.client.get("/api/v1/cards/master?category=pokemon&limit=5")
        self.assertEqual(pkmn_res.status_code, 200)
        self.assertTrue(all(c["card_type"] == "pokemon" for c in pkmn_res.json()["cards"]))

        # Search query: Pikachu
        search_res = self.client.get("/api/v1/cards/master?search=Pikachu")
        self.assertEqual(search_res.status_code, 200)
        self.assertTrue(any("Pikachu" in c["name"] for c in search_res.json()["cards"]))

    def test_pack_opening_and_history_api(self):
        """Verify opening pack via API increments collection and logs history."""
        uid = secrets.token_hex(4)
        reg_res = self.client.post("/api/v1/auth/register", json={
            "username": f"PackApiUser_{uid}",
            "email": f"packapi_{uid}@kanto.com",
            "password": "Password123!"
        })
        self.assertEqual(reg_res.status_code, 200)
        token = reg_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Open 1st pack
        open_res = self.client.post("/api/v1/pack/open", headers=headers)
        self.assertEqual(open_res.status_code, 200)
        pack_data = open_res.json()
        self.assertEqual(pack_data["pack_size"], 8)
        self.assertEqual(len(pack_data["cards"]), 8)

        pkmn = [c for c in pack_data["cards"] if c["card_type"] == "pokemon"]
        other = [c for c in pack_data["cards"] if c["card_type"] != "pokemon"]
        self.assertEqual(len(pkmn), 5, "Pack must contain exactly 5 Pokémon")
        self.assertEqual(len(other), 3, "Pack must contain exactly 3 Other cards")

        # Check collection stats
        stats_res = self.client.get("/api/v1/collection/stats", headers=headers)
        self.assertEqual(stats_res.status_code, 200)
        self.assertEqual(stats_res.json()["stats"]["total_cards"], 8)

        # Check pack history
        hist_res = self.client.get("/api/v1/pack/history", headers=headers)
        self.assertEqual(hist_res.status_code, 200)
        self.assertEqual(len(hist_res.json()["history"]), 1)

    def test_battle_deck_validation_requires_owned_basic_pokemon(self):
        """User cannot battle with cards they don't own or with Stage 1/2 cards in starting slots."""
        uid = secrets.token_hex(4)
        user = db.register_user(f"BattleUser_{uid}", f"battle_{uid}@kanto.com", "Password123!")
        token = user["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Give user specific owned cards: 3 Basics and 1 Stage 1
        db.add_cards_to_user_collection(user["id"], ["sv3-26", "pkm-0025", "pkm-0133", "sv3-27"])
        # sv3-26: Charmander (Basic)
        # pkm-0025: Pikachu (Basic)
        # pkm-0133: Eevee (Basic)
        # sv3-27: Charmeleon (Stage 1)

        # Attempt to validate deck with an unowned card (Snorlax) -> must fail
        bad_res1 = self.client.post("/api/v1/battle/validate-deck", headers=headers, json={
            "chosen_cards": ["Charmander", "Pikachu", "Eevee", "Snorlax"]
        })
        self.assertEqual(bad_res1.status_code, 400)
        self.assertIn("You do not own Snorlax", bad_res1.json()["detail"])

        # Attempt to validate deck with Stage 1 (Charmeleon) in starting slot -> must fail
        bad_res2 = self.client.post("/api/v1/battle/validate-deck", headers=headers, json={
            "chosen_cards": ["Charmander", "Pikachu", "Eevee", "Charmeleon"]
        })
        self.assertEqual(bad_res2.status_code, 400)
        self.assertIn("not a Basic Pokémon", bad_res2.json()["detail"])

        # Valid 4 Basic Pokémon -> must succeed
        # Add Snorlax (Basic) to collection
        conn = db.get_db_connection()
        snorlax_row = conn.execute("SELECT card_id FROM master_cards WHERE name = 'Snorlax'").fetchone()
        conn.close()
        snorlax_id = snorlax_row["card_id"] if snorlax_row else "pkm-0143"
        db.add_cards_to_user_collection(user["id"], [snorlax_id])

        good_res = self.client.post("/api/v1/battle/validate-deck", headers=headers, json={
            "chosen_cards": ["Charmander", "Pikachu", "Eevee", "Snorlax"]
        })
        self.assertEqual(good_res.status_code, 200)
        self.assertTrue(good_res.json()["valid"])


if __name__ == "__main__":
    unittest.main()
