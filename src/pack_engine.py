"""
Pokémon TCG Booster Pack Opening & Probability Engine
Rules:
- Total Cards = Exactly 8
- Pokémon Cards = Exactly 5 (Slots 1-5)
- Trainer / Energy Cards = Exactly 3 (Slots 6-8)
- 40% probability per slot to select an owned card (if owned pool is empty, fall back to master pool)
- 60% probability per slot to select from the general card pool (preferring unowned cards if available)
- Rarity weights: Common (55%), Uncommon (25%), Rare (12%), Ultra Rare (6%), Special (2%)
- Category boundary strictly enforced (never Trainer in Pokémon slot or Pokémon in Trainer slot)
- Saves newly opened cards to user's SQLite collection with updated quantities
"""
import random
from typing import Dict, List, Any, Optional, Set
import src.database as db

# Rarity distribution configuration
RARITY_WEIGHTS = [
    ("Common", 0.55),
    ("Uncommon", 0.25),
    ("Rare", 0.12),
    ("Ultra Rare", 0.06),
    ("Special", 0.02)
]

OWNED_DUPLICATE_CHANCE = 0.40


def roll_rarity() -> str:
    r = random.random()
    cumulative = 0.0
    for rarity, weight in RARITY_WEIGHTS:
        cumulative += weight
        if r <= cumulative:
            return rarity
    return "Common"


class PackEngine:
    def __init__(self):
        self._load_master_pools()

    def _load_master_pools(self):
        conn = db.get_db_connection()
        cursor = conn.cursor()

        # Pokémon Cards by rarity
        self.pokemon_by_rarity = {
            "Common": [],
            "Uncommon": [],
            "Rare": [],
            "Ultra Rare": [],
            "Special": []
        }
        self.all_pokemon = []

        pkmn_rows = cursor.execute("SELECT card_id, rarity FROM master_cards WHERE card_type = 'pokemon'").fetchall()
        for r in pkmn_rows:
            cid = r["card_id"]
            rarity = r["rarity"]
            self.all_pokemon.append(cid)
            if rarity in self.pokemon_by_rarity:
                self.pokemon_by_rarity[rarity].append(cid)
            else:
                self.pokemon_by_rarity["Common"].append(cid)

        # Other Cards (Trainer / Energy) by rarity
        self.other_by_rarity = {
            "Common": [],
            "Uncommon": [],
            "Rare": [],
            "Ultra Rare": [],
            "Special": []
        }
        self.all_other = []

        other_rows = cursor.execute("SELECT card_id, rarity FROM master_cards WHERE card_type != 'pokemon'").fetchall()
        for r in other_rows:
            cid = r["card_id"]
            rarity = r["rarity"]
            self.all_other.append(cid)
            if rarity in self.other_by_rarity:
                self.other_by_rarity[rarity].append(cid)
            else:
                self.other_by_rarity["Common"].append(cid)

        conn.close()

    def _select_master_card(
        self,
        is_pokemon: bool,
        desired_rarity: str,
        owned_set: Optional[Set[str]] = None
    ) -> str:
        pool_dict = self.pokemon_by_rarity if is_pokemon else self.other_by_rarity
        fallback_all = self.all_pokemon if is_pokemon else self.all_other

        # Check candidate cards in desired rarity
        candidates = pool_dict.get(desired_rarity, [])
        if not candidates:
            # Fallback to other rarities
            for r in ["Common", "Uncommon", "Rare", "Ultra Rare", "Special"]:
                if pool_dict.get(r):
                    candidates = pool_dict[r]
                    break

        if not candidates:
            candidates = fallback_all

        # If user has an owned set, prefer cards not yet in owned_set to honor the ~40% duplicate balance
        if owned_set is not None:
            unowned = [c for c in candidates if c not in owned_set]
            if unowned:
                return random.choice(unowned)

        if candidates:
            return random.choice(candidates)

        if fallback_all:
            return random.choice(fallback_all)

        raise RuntimeError(f"No cards available in {'Pokemon' if is_pokemon else 'Other'} master pool!")

    def generate_pack_card_ids(self, user_id: Optional[int] = None) -> List[str]:
        """
        Generates exactly 8 card IDs:
        Slots 1-5: Pokémon
        Slots 6-8: Trainer / Other
        40% chance per slot to choose from owned cards in that category.
        """
        owned_pokemon = []
        owned_other = []
        owned_set: Set[str] = set()

        if user_id is not None:
            conn = db.get_db_connection()
            cursor = conn.cursor()
            rows = cursor.execute("""
            SELECT uc.card_id, m.card_type
            FROM user_collection uc
            JOIN master_cards m ON uc.card_id = m.card_id
            WHERE uc.user_id = ?
            """, (user_id,)).fetchall()
            conn.close()

            for r in rows:
                cid = r["card_id"]
                owned_set.add(cid)
                if r["card_type"] == "pokemon":
                    owned_pokemon.append(cid)
                else:
                    owned_other.append(cid)

        selected_cids = []

        # 1. Exactly 5 Pokémon Cards (Slots 1-5)
        for _ in range(5):
            rarity = roll_rarity()
            use_owned = (random.random() <= OWNED_DUPLICATE_CHANCE) and (len(owned_pokemon) > 0)
            if use_owned:
                card_id = random.choice(owned_pokemon)
            else:
                card_id = self._select_master_card(is_pokemon=True, desired_rarity=rarity, owned_set=owned_set)
            selected_cids.append(card_id)

        # 2. Exactly 3 Other Cards (Trainer/Energy) (Slots 6-8)
        for _ in range(3):
            rarity = roll_rarity()
            use_owned = (random.random() <= OWNED_DUPLICATE_CHANCE) and (len(owned_other) > 0)
            if use_owned:
                card_id = random.choice(owned_other)
            else:
                card_id = self._select_master_card(is_pokemon=False, desired_rarity=rarity, owned_set=owned_set)
            selected_cids.append(card_id)

        return selected_cids

    def open_pack_for_user(self, user_id: int) -> Dict[str, Any]:
        """
        Generates 8 cards for the user, persists them to the user's collection,
        records the pack opening history, and returns the cards with duplicate flags.
        """
        card_ids = self.generate_pack_card_ids(user_id=user_id)
        cards_received = db.add_cards_to_user_collection(user_id, card_ids)
        db.record_pack_opening(user_id, cards_received)
        new_stats = db.get_user_collection_stats(user_id)

        return {
            "status": "success",
            "pack_size": len(cards_received),
            "cards": cards_received,
            "collection_stats": new_stats
        }


# Singleton instance
pack_engine = PackEngine()
