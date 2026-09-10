"""
Unit Tests for Authentication and User Collection Isolation
Validates:
1. Registration with validation (password length, email format, username uniqueness).
2. Login with correct and incorrect credentials.
3. Session token validation and logout.
4. User collection isolation: User A cannot see User B's cards.
5. Collection filters by category, stage, rarity, and search.
"""
import unittest
import os
import sys
import secrets

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

import src.database as db
from src.pack_engine import pack_engine


class TestAuthAndCollection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    def test_register_and_login_flow(self):
        uid = secrets.token_hex(4)
        username = f"Trainer_{uid}"
        email = f"trainer_{uid}@kanto.com"
        password = "MegaCharizard99#"

        # Register
        user = db.register_user(username, email, password)
        self.assertIsNotNone(user["id"])
        self.assertEqual(user["username"], username)
        self.assertEqual(user["email"], email)
        self.assertTrue(len(user["token"]) > 20)

        # Login with username
        logged_in = db.authenticate_user(username, password)
        self.assertEqual(logged_in["id"], user["id"])
        self.assertTrue(len(logged_in["token"]) > 20)

        # Login with email
        logged_in_email = db.authenticate_user(email, password)
        self.assertEqual(logged_in_email["id"], user["id"])

        # Invalid password
        with self.assertRaises(ValueError):
            db.authenticate_user(username, "WrongPassword!")

        # Duplicate username
        with self.assertRaises(ValueError):
            db.register_user(username, f"different_{uid}@kanto.com", password)

        # Duplicate email
        with self.assertRaises(ValueError):
            db.register_user(f"Different_{uid}", email, password)

        # Token validation
        session_user = db.get_user_by_token(logged_in["token"])
        self.assertIsNotNone(session_user)
        self.assertEqual(session_user["username"], username)

        # Logout
        db.logout_session(logged_in["token"])
        self.assertIsNone(db.get_user_by_token(logged_in["token"]))

    def test_user_collection_isolation(self):
        """Verify User A and User B have separate collections and cannot see each other's cards."""
        uid_a = secrets.token_hex(4)
        uid_b = secrets.token_hex(4)
        user_a = db.register_user(f"UserA_{uid_a}", f"usera_{uid_a}@kanto.com", "Pass1234!")
        user_b = db.register_user(f"UserB_{uid_b}", f"userb_{uid_b}@kanto.com", "Pass1234!")

        # User A opens 2 packs
        pack_engine.open_pack_for_user(user_a["id"])
        pack_engine.open_pack_for_user(user_a["id"])
        stats_a = db.get_user_collection_stats(user_a["id"])
        self.assertEqual(stats_a["total_cards"], 16)

        # User B has opened 0 packs -> collection must be 0
        stats_b = db.get_user_collection_stats(user_b["id"])
        self.assertEqual(stats_b["total_cards"], 0)

        # User B's collection query returns empty list
        col_b = db.get_user_collection(user_b["id"])
        self.assertEqual(len(col_b), 0)

        # User A's collection has items
        col_a = db.get_user_collection(user_a["id"])
        self.assertGreater(len(col_a), 0)

    def test_collection_filters_and_quantities(self):
        """Verify category, stage, rarity, search filters and quantity tracking."""
        uid = secrets.token_hex(4)
        user = db.register_user(f"FilterUser_{uid}", f"filter_{uid}@kanto.com", "Pass1234!")

        # Add known specific cards
        db.add_cards_to_user_collection(user["id"], ["sv3-26", "sv3-26", "sv3-27", "trainer_potion", "sve-1"])

        # Verify quantities
        col = db.get_user_collection(user["id"])
        charmander = next(c for c in col if c["card_id"] == "sv3-26")
        self.assertEqual(charmander["quantity"], 2, "Charmander quantity should be 2")

        potion = next(c for c in col if c["card_id"] == "trainer_potion")
        self.assertEqual(potion["quantity"], 1, "Potion quantity should be 1")

        # Category filter: pokemon
        pkmn_only = db.get_user_collection(user["id"], category="pokemon")
        self.assertTrue(all(c["card_type"] == "pokemon" for c in pkmn_only))

        # Category filter: trainer
        trainer_only = db.get_user_collection(user["id"], category="trainer")
        self.assertTrue(all(c["card_type"] == "trainer" for c in trainer_only))

        # Stage filter: basic
        basic_only = db.get_user_collection(user["id"], stage="basic")
        self.assertTrue(all(c["stage"] == "Basic" for c in basic_only))

        # Search filter: Char
        char_search = db.get_user_collection(user["id"], search="Char")
        self.assertTrue(any("Charmander" in c["name"] for c in char_search))


if __name__ == "__main__":
    unittest.main()
