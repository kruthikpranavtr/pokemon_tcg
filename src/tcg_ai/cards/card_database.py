"""
Card Database and Metadata Ingestion Engine
Loads, indexes, and normalizes Pokémon TCG card data for deterministic rules and AI evaluation.
Ingests both JSON dataset and SQLite master_cards for comprehensive Pokémon, Trainer, and Energy support.
"""
import os
import json
import sqlite3
from typing import Dict, List, Any, Optional


class CardDatabase:
    _instance: Optional['CardDatabase'] = None

    def __init__(self, data_path: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        if data_path is None:
            data_path = os.path.join(base_dir, "data", "cards_dataset.json")

        self.db_path = os.path.join(base_dir, "data", "pokemon_tcg.db")
        self.cards_by_id: Dict[str, Dict[str, Any]] = {}
        self.cards_by_name: Dict[str, Dict[str, Any]] = {}
        self.basic_pokemon_pool: List[str] = []
        self.evolution_map: Dict[str, List[str]] = {}

        self._load_dataset(data_path)
        self._load_from_sqlite()

    @classmethod
    def get_instance(cls, data_path: Optional[str] = None) -> 'CardDatabase':
        if cls._instance is None:
            cls._instance = CardDatabase(data_path)
        return cls._instance

    def _load_dataset(self, data_path: str):
        if not os.path.exists(data_path):
            return

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        card_list = data.get("cards", []) if isinstance(data, dict) else data
        for card in card_list:
            cid = card.get("card_id")
            name = card.get("name", "")
            if not cid:
                continue

            self.cards_by_id[cid] = card
            norm_name = name.lower().strip()
            self.cards_by_name[norm_name] = card

            stype = card.get("supertype", "").lower()
            subtypes = [s.lower() for s in card.get("subtypes", [])]
            stage = (card.get("stage") or "").lower()

            if stype.startswith("pok") and ("basic" in subtypes or stage == "basic"):
                if name not in self.basic_pokemon_pool:
                    self.basic_pokemon_pool.append(name)

            evolves_from = (card.get("evolves_from") or "").lower().strip()
            if evolves_from:
                self.evolution_map.setdefault(evolves_from, []).append(name)

    def _load_from_sqlite(self):
        if not os.path.exists(self.db_path):
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT card_id, name, card_type, pokemon_type, stage, evolves_from, rarity, hp, attacks_json, raw_json FROM master_cards")
            rows = cursor.fetchall()
            for r in rows:
                cid, name, ctype, ptype, stage, evo_from, rarity, hp, atks_json, raw_json = r
                card_obj = {}
                if raw_json:
                    try:
                        card_obj = json.loads(raw_json)
                    except Exception:
                        pass

                supertype = "Pokémon" if ctype == "pokemon" else ("Trainer" if ctype == "trainer" else "Energy")
                subtypes = card_obj.get("subtypes", [stage] if stage else [])

                attacks = []
                if atks_json:
                    try:
                        attacks = json.loads(atks_json)
                    except Exception:
                        attacks = []

                entry = {
                    "card_id": cid,
                    "name": name,
                    "supertype": supertype,
                    "card_type": ctype,
                    "subtypes": subtypes,
                    "stage": stage or ("Basic" if supertype == "Pokémon" else ""),
                    "hp": hp or (220 if "ex" in name.lower() else 80),
                    "types": [ptype] if ptype else ["Colorless"],
                    "attacks": attacks or ([{"name": "Strike", "base_damage": 50, "cost": ["Colorless"]}] if supertype == "Pokémon" else []),
                    "retreat_cost": ["Colorless"],
                    "weaknesses": card_obj.get("weaknesses", [])
                }

                self.cards_by_id[cid] = entry
                norm_name = name.lower().strip()
                self.cards_by_name[norm_name] = entry

                if supertype == "Pokémon" and (stage == "Basic" or "basic" in [s.lower() for s in subtypes]):
                    if name not in self.basic_pokemon_pool:
                        self.basic_pokemon_pool.append(name)

                if evo_from:
                    self.evolution_map.setdefault(evo_from.lower().strip(), []).append(name)

            conn.close()
        except Exception as ex:
            print(f"[CardDatabase] SQLite load error: {ex}")

    def get_card(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Lookup by card_id or name."""
        if not identifier:
            return None
        if identifier in self.cards_by_id:
            return self.cards_by_id[identifier]
        norm = identifier.lower().strip()
        if norm in self.cards_by_name:
            return self.cards_by_name[norm]
        return None

    def get_meta(self, identifier: str) -> Dict[str, Any]:
        """Returns card metadata with safe fallbacks."""
        card = self.get_card(identifier)
        if card:
            return card

        clean = identifier.strip() if identifier else "Unknown"
        clean_lower = clean.lower()

        # Categorize by keyword
        trainer_kw = ["ball", "research", "orders", "iono", "arven", "candy", "rod", "catcher", "potion", "switch", "vessel"]
        if any(kw in clean_lower for kw in trainer_kw):
            supertype = "Trainer"
            subtypes = ["Supporter"] if any(s in clean_lower for s in ("research", "iono", "orders", "arven")) else ["Item"]
            return {
                "card_id": f"gen-{clean_lower.replace(' ', '-')}",
                "name": clean,
                "supertype": supertype,
                "card_type": "trainer",
                "subtypes": subtypes,
                "stage": ""
            }

        if "energy" in clean_lower:
            return {
                "card_id": f"gen-{clean_lower.replace(' ', '-')}",
                "name": clean,
                "supertype": "Energy",
                "card_type": "energy",
                "subtypes": ["Basic Energy"],
                "stage": ""
            }

        is_ex = "ex" in clean_lower or " v" in clean_lower
        return {
            "card_id": f"gen-{clean_lower.replace(' ', '-')}",
            "name": clean,
            "supertype": "Pokémon",
            "card_type": "pokemon",
            "subtypes": ["Basic"],
            "stage": "Basic",
            "hp": 220 if is_ex else 80,
            "types": ["Colorless"],
            "attacks": [{"name": "Strike", "base_damage": 50, "cost": ["Colorless"]}],
            "retreat_cost": ["Colorless"],
            "weaknesses": []
        }

    def is_basic_pokemon(self, identifier: str) -> bool:
        if not identifier:
            return False
        clean = identifier.lower().strip()
        non_pokemon = ["energy", "ball", "research", "orders", "iono", "arven", "candy", "rod", "catcher", "potion", "switch", "vessel"]
        if any(kw in clean for kw in non_pokemon):
            return False

        meta = self.get_meta(identifier)
        stype = meta.get("supertype", "").lower()
        if not stype.startswith("pok"):
            return False

        subtypes = [s.lower() for s in meta.get("subtypes", [])]
        stage = (meta.get("stage") or "").lower()
        if "stage 1" in subtypes or "stage 2" in subtypes or stage in ("stage 1", "stage 2"):
            return False
        return "basic" in subtypes or stage == "basic" or len(subtypes) == 0

    def get_evolutions_for(self, pre_evo_name: str) -> List[str]:
        return self.evolution_map.get(pre_evo_name.lower().strip(), [])
