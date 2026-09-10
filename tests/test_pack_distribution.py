"""
Statistical and Functional Test Suite for Pokémon TCG Pack Opening System.
Validates:
1. Exact 8 cards per pack (5 Pokémon + 3 Other cards).
2. Exactly 500 Pokémon cards (62.5%) and 300 Other cards (37.5%) across 100 packs.
3. 40% owned duplicate probability across card slots.
4. Handling of empty collection for first-time users.
5. Duplicates are allowed and increment card quantities.
"""
import unittest
import os
import sys
import secrets

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

import src.database as db
from src.pack_engine import pack_engine, OWNED_DUPLICATE_CHANCE


class TestPackDistribution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    def test_single_pack_exact_rules(self):
        """Verify a single pack contains exactly 8 cards: 5 Pokémon and 3 Other."""
        uid = secrets.token_hex(4)
        user = db.register_user(f"SingleUser_{uid}", f"single_{uid}@pack.com", "Secret123!")
        pack = pack_engine.open_pack_for_user(user["id"])

        self.assertEqual(pack["pack_size"], 8)
        self.assertEqual(len(pack["cards"]), 8)

        pokemon_cards = [c for c in pack["cards"] if c["card_type"] == "pokemon"]
        other_cards = [c for c in pack["cards"] if c["card_type"] != "pokemon"]

        self.assertEqual(len(pokemon_cards), 5, "Must have exactly 5 Pokémon cards")
        self.assertEqual(len(other_cards), 3, "Must have exactly 3 Other cards (Trainer/Energy)")

    def test_empty_user_collection_fallback(self):
        """A new user with empty collection should open packs without errors."""
        uid = secrets.token_hex(4)
        user = db.register_user(f"EmptyUser_{uid}", f"empty_{uid}@pack.com", "Secret123!")
        stats_before = db.get_user_collection_stats(user["id"])
        self.assertEqual(stats_before["total_cards"], 0)

        # First pack
        pack1 = pack_engine.open_pack_for_user(user["id"])
        self.assertEqual(len(pack1["cards"]), 8)
        stats_after = db.get_user_collection_stats(user["id"])
        self.assertEqual(stats_after["total_cards"], 8)

    def test_100_packs_distribution_and_duplicate_rate(self):
        """
        Statistical test: Open 100 packs (800 cards).
        Asserts:
        - Exactly 500 Pokémon cards (62.5%)
        - Exactly 300 Other cards (37.5%)
        - Duplicate / owned-card selection rate approaches ~40%
        """
        uid = secrets.token_hex(4)
        user = db.register_user(f"StatsUser_{uid}", f"stats_{uid}@pack.com", "Secret123!")

        total_pokemon = 0
        total_other = 0
        total_cards = 0
        total_duplicates = 0

        for pack_num in range(100):
            pack = pack_engine.open_pack_for_user(user["id"])
            cards = pack["cards"]
            self.assertEqual(len(cards), 8, f"Pack #{pack_num + 1} did not contain 8 cards")

            p_in_pack = [c for c in cards if c["card_type"] == "pokemon"]
            o_in_pack = [c for c in cards if c["card_type"] != "pokemon"]

            self.assertEqual(len(p_in_pack), 5, f"Pack #{pack_num + 1} did not have 5 Pokémon")
            self.assertEqual(len(o_in_pack), 3, f"Pack #{pack_num + 1} did not have 3 Other cards")

            total_pokemon += len(p_in_pack)
            total_other += len(o_in_pack)
            total_cards += len(cards)

            # Count cards that were marked duplicate
            dups = [c for c in cards if c.get("is_duplicate")]
            total_duplicates += len(dups)

        # 1. Check exact card category counts
        self.assertEqual(total_cards, 800)
        self.assertEqual(total_pokemon, 500, "100 packs must yield exactly 500 Pokémon (62.5%)")
        self.assertEqual(total_other, 300, "100 packs must yield exactly 300 Other cards (37.5%)")

        pokemon_pct = total_pokemon / total_cards
        other_pct = total_other / total_cards
        self.assertAlmostEqual(pokemon_pct, 0.625, places=4)
        self.assertAlmostEqual(other_pct, 0.375, places=4)

        # 2. Check duplicate / owned rate
        # With 40% probability per slot once owned pool is populated:
        dup_rate = total_duplicates / total_cards
        print(f"\n[Statistical Test] Total cards: {total_cards}, Pokémon: {total_pokemon} ({pokemon_pct:.1%}), Other: {total_other} ({other_pct:.1%}), Duplicates: {total_duplicates} ({dup_rate:.1%})")
        self.assertGreater(dup_rate, 0.25, f"Duplicate rate {dup_rate:.2%} should be >= 25%")
        self.assertLess(dup_rate, 0.55, f"Duplicate rate {dup_rate:.2%} should be <= 55%")

        # 3. Collection quantities verification
        stats = db.get_user_collection_stats(user["id"])
        self.assertEqual(stats["total_cards"], 800)
        self.assertLess(stats["distinct_cards"], 800, "Distinct cards must be less than 800 due to duplicates")
        self.assertGreater(stats["distinct_cards"], 100, "Should have a good variety of distinct cards")


if __name__ == "__main__":
    unittest.main()
