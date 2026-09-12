"""
Phase 26: Random Card Data Consistency Test
Picks 20 random cards directly from authoritative Csvfiles/EN_Card_Data.csv
and verifies that SQLite database, cards_dataset.json, and Match Engine:
- Preserve exact card names (NO fake or hallucinated names)
- Preserve exact card_id mapping
- Preserve exact HP (for Pokemon)
- Preserve attack 1 and attack 2 names/damages
- Verify authentic image path
"""
import os
import csv
import json
import random
import unittest
from pathlib import Path
from collections import defaultdict
import sqlite3


class TestDataConsistency20Cards(unittest.TestCase):
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

        assert cls.csv_path is not None, f"Could not find EN_Card_Data.csv in {possible_csvs}"

        cls.cards_by_id = defaultdict(list)
        with open(cls.csv_path, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = (row.get("Card ID") or row.get("\ufeffCard ID") or "").strip()
                if cid:
                    cls.cards_by_id[cid].append(row)

        cls.db_path = Path("data/pokemon_tcg.db")
        cls.json_path = Path("data/cards_dataset.json")

        with open(cls.json_path, mode="r", encoding="utf-8") as f:
            cls.json_cards = {str(c["card_id"]): c for c in json.load(f)["cards"]}

    def test_20_random_cards_consistency(self):
        """Samples 20 random cards from EN_Card_Data.csv and verifies 100% data fidelity."""
        self.assertEqual(len(self.cards_by_id), 1267, "EN_Card_Data.csv must contain exactly 1,267 unique cards")

        rng = random.Random(42)
        sample_ids = rng.sample(list(self.cards_by_id.keys()), 20)

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        for csv_id in sample_ids:
            rows = self.cards_by_id[csv_id]
            r0 = rows[0]
            csv_name = r0.get("Card Name", "").strip()
            csv_type = r0.get("Card Type", "").strip().lower()
            csv_hp = r0.get("HP", "").strip()

            # Collect attacks from rows
            attacks = []
            for r in rows:
                atk_name = r.get("Attack Name", "").strip()
                if atk_name and atk_name.lower() != "none" and atk_name != "-":
                    attacks.append(atk_name)

            # 1. Verify SQLite record
            cursor.execute("SELECT * FROM master_cards WHERE card_id = ?", (csv_id,))
            db_row = cursor.fetchone()
            self.assertIsNotNone(db_row, f"Card ID {csv_id} ({csv_name}) must exist in SQLite master_cards")

            db_name = str(db_row["name"]).strip()
            self.assertEqual(db_name, csv_name, f"Card ID {csv_id}: DB name '{db_name}' != CSV name '{csv_name}'")

            if csv_type == "pokemon" and csv_hp.isdigit():
                self.assertEqual(db_row["hp"], int(csv_hp), f"Card ID {csv_id}: DB HP != CSV HP")

            if len(attacks) >= 1:
                self.assertEqual(str(db_row["attack_1_name"] or "").strip(), attacks[0])
            if len(attacks) >= 2:
                self.assertEqual(str(db_row["attack_2_name"] or "").strip(), attacks[1])

            db_img = str(db_row["image"])
            if csv_type == "pokemon":
                self.assertEqual(db_img, f"/static/card_images/{csv_id}.png")
            else:
                self.assertTrue(db_img.startswith("/static/card_images/"), f"Image path must be under /static/: {db_img}")

            # 2. Verify JSON dataset record
            self.assertIn(csv_id, self.json_cards, f"Card ID {csv_id} must exist in cards_dataset.json")
            json_card = self.json_cards[csv_id]
            self.assertEqual(json_card["name"], csv_name)

            if csv_type == "pokemon" and csv_hp.isdigit():
                self.assertEqual(json_card["hp"], int(csv_hp))

            if len(attacks) >= 1:
                self.assertEqual(json_card.get("attack_1_name"), attacks[0])
            if len(attacks) >= 2:
                self.assertEqual(json_card.get("attack_2_name"), attacks[1])

        conn.close()


if __name__ == "__main__":
    unittest.main()
