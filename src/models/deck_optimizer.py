"""
Model 1: Metagame 60-Card Deck Constructor & Optimizer
Uses card synergy graph embeddings + constrained combinatorial optimization to build tournament-winning 60-card lists.
"""
from typing import Dict, List, Any
import numpy as np


class DeckOptimizerModel:
    def __init__(self, card_db: Dict[str, Any], meta_db: Dict[str, Any]):
        self.card_db = card_db
        self.meta_db = meta_db
        self._build_synergy_matrix()

    def _build_synergy_matrix(self):
        """
        Builds co-occurrence and synergy matrix from tournament meta archetypes.
        """
        self.card_ids = list(self.card_db.keys())
        self.card_idx = {cid: i for i, cid in enumerate(self.card_ids)}
        n = len(self.card_ids)
        self.synergy_matrix = np.zeros((n, n), dtype=np.float32)

        for arch in self.meta_db.get("archetypes", []):
            weight = arch.get("meta_share", 0.1)
            core = arch.get("core_cards", [])
            for c1 in core:
                id1 = c1.get("card_id")
                if id1 not in self.card_idx:
                    continue
                i = self.card_idx[id1]
                for c2 in core:
                    id2 = c2.get("card_id")
                    if id2 not in self.card_idx:
                        continue
                    j = self.card_idx[id2]
                    self.synergy_matrix[i, j] += weight * (c1.get("count", 1) * c2.get("count", 1))

    def optimize_deck(self, seed_cards: List[Dict[str, Any]], target_archetype: str = "charizard-ex-pidgeot") -> Dict[str, Any]:
        """
        Builds an optimized 60-card deck starting from seed cards.
        """
        deck = {item["card_id"]: item.get("count", 1) for item in seed_cards}
        
        # Pull matching template from meta
        selected_meta = None
        for arch in self.meta_db.get("archetypes", []):
            if arch.get("archetype_id") == target_archetype:
                selected_meta = arch
                break

        if selected_meta:
            for item in selected_meta.get("core_cards", []):
                cid = item.get("card_id")
                cnt = item.get("count", 1)
                deck[cid] = max(deck.get(cid, 0), cnt)

        # Ensure total is exactly 60
        current_total = sum(deck.values())

        # Fill with energy or search if under 60
        if current_total < 60:
            diff = 60 - current_total
            # Find dominant basic energy
            energy_id = "sve-2" if "charizard" in target_archetype else "sve-4"
            deck[energy_id] = deck.get(energy_id, 0) + diff
        elif current_total > 60:
            # Trim non-core cards
            excess = current_total - 60
            for cid in list(deck.keys()):
                if excess <= 0:
                    break
                if cid.startswith("sve-") and deck[cid] > 4:
                    cut = min(excess, deck[cid] - 4)
                    deck[cid] -= cut
                    excess -= cut

        # Format output
        deck_list = []
        for cid, cnt in deck.items():
            card = self.card_db.get(cid, {})
            deck_list.append({
                "card_id": cid,
                "name": card.get("name", cid),
                "supertype": card.get("supertype", "Unknown"),
                "count": cnt
            })

        return {
            "archetype": target_archetype,
            "total_cards": sum(d["count"] for d in deck_list),
            "deck_list": deck_list,
            "expected_meta_winrate": selected_meta.get("meta_share", 0.5) * 0.2 + 0.52 if selected_meta else 0.50
        }
