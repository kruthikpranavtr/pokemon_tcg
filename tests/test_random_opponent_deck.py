import unittest
import os
import json
from collections import Counter
from src.engine.tcg_match_engine import TCGMatchEngine

class TestRandomOpponentDeck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open("data/cards_dataset.json", "r", encoding="utf-8") as f:
            cards_data = json.load(f)
            cls.card_db = {c["card_id"]: c for c in cards_data["cards"]}
        cls.engine = TCGMatchEngine(cls.card_db)

    def test_deck_generation_rules_100_runs(self):
        """Verify that 100 randomly generated opponent decks strictly obey all Pokémon TCG rules."""
        for run in range(100):
            deck_data = self.engine.generate_rule_based_random_deck(f"TestOppDeck_{run}")
            deck = deck_data["cards"]
            
            # Rule 1: Exactly 60 cards
            self.assertEqual(len(deck), 60, f"Run {run}: Deck must have exactly 60 cards, got {len(deck)}")
            
            # Rule 2: Max 4 copies of any non-energy card
            counts = Counter(deck)
            has_basic_pokemon = False
            pokemon_types = set()
            evolutions = []
            
            for card_name, count in counts.items():
                meta = self.engine._get_meta(card_name)
                card_type = (meta.get("card_type") or meta.get("supertype") or "").lower() if meta else ""
                clean_name = card_name.lower()
                is_energy = "energy" in card_type or "energy" in clean_name
                
                if not is_energy:
                    self.assertLessEqual(count, 4, f"Run {run}: Non-energy card '{card_name}' exceeds max 4 copies (count={count})")
                
                if meta and card_type == "pokemon":
                    stage = (meta.get("stage") or "Basic").strip()
                    ptype = meta.get("pokemon_type") or "Colorless"
                    if ptype and ptype != "Colorless":
                        pokemon_types.add(ptype)
                        
                    if stage == "Basic":
                        has_basic_pokemon = True
                    else:
                        evolutions.append((card_name, meta))
            
            # Rule 3: Must have at least 1 Basic Pokémon
            self.assertTrue(has_basic_pokemon, f"Run {run}: Deck must contain at least 1 Basic Pokémon")
            
            # Rule 4: Evolution Integrity - each evolution must have its lower stage
            for evo_name, meta in evolutions:
                stage = meta.get("stage", "")
                evolves_from = (meta.get("evolves_from") or "").strip().lower()
                if evolves_from:
                    # Look for base in the deck
                    has_pre_evo = any(
                        evolves_from in c.lower() or c.lower() in evolves_from
                        for c in deck
                    )
                    self.assertTrue(
                        has_pre_evo,
                        f"Run {run}: Evolution '{evo_name}' (evolves from '{evolves_from}') has no pre-evolution in deck!"
                    )

            # Rule 5: Energies present in deck matching types
            energy_cards = [c for c in deck if "energy" in c.lower()]
            self.assertGreater(len(energy_cards), 0, f"Run {run}: Deck must contain energy cards")
            self.assertGreaterEqual(len(energy_cards), 10, f"Run {run}: Expected at least 10 energies for a playable deck, got {len(energy_cards)}")

    def test_match_start_with_random_opponent_deck(self):
        """Verify resetting / starting a match with random opponent deck works seamlessly."""
        for _ in range(25):
            state = self.engine.reset_match(player_deck_id="charizard-fire", opp_deck_id="random")
            
            # Initial state verification
            self.assertEqual(state["phase"], "SETUP")
            self.assertIsNone(state["winner"])
            self.assertEqual(len(state["player"]["hand"]), 5)
            self.assertGreaterEqual(state["opponent"]["hand_count"], 1)
            
            # Verify Opponent has an active Pokémon placed and ready
            self.assertIsNotNone(self.engine.opp_active)
            self.assertGreater(self.engine.opp_active["current_hp"], 0)
            
            # Opponent card conservation: active (1) + bench + hand + deck + prizes = 60 cards total
            opp_active_count = 1 if self.engine.opp_active else 0
            opp_bench_count = len([b for b in self.engine.opp_bench if b is not None])
            total_opp_cards = (
                opp_active_count +
                opp_bench_count +
                len(self.engine.opp_hand) +
                len(self.engine.opp_deck) +
                len(self.engine.opp_prizes)
            )
            self.assertEqual(total_opp_cards, 60, f"Opponent all card zones must sum to 60, got {total_opp_cards}")

if __name__ == "__main__":
    unittest.main()
