"""
Comprehensive Test Suite for Pokémon TCG AI Engine
"""
import json
import unittest
from src.engine.rules_engine import RulesEngine
from src.engine.action_mask import ActionMaskEngine
from src.engine.explainer import ActionExplainer
from src.models.deck_optimizer import DeckOptimizerModel
from src.models.policy_value_net import PolicyValueNetwork


class TestPokemonTCGAIEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open("data/cards_dataset.json", "r", encoding="utf-8") as f:
            cards_data = json.load(f)
            cls.card_db = {c["card_id"]: c for c in cards_data["cards"]}

        with open("data/tournament_meta.json", "r", encoding="utf-8") as f:
            cls.meta_db = json.load(f)

        cls.rules = RulesEngine(cls.card_db)
        cls.masker = ActionMaskEngine(cls.card_db)
        cls.explainer = ActionExplainer(cls.card_db)
        cls.deck_opt = DeckOptimizerModel(cls.card_db, cls.meta_db)
        cls.policy_val = PolicyValueNetwork()

    def test_60_card_deck_validator(self):
        # 1. Invalid count test (under 60)
        invalid_deck = [{"card_id": "sv3-125", "count": 2}]
        is_valid, errors = self.rules.validate_deck(invalid_deck)
        self.assertFalse(is_valid)
        self.assertTrue(any("60 cards" in e for e in errors))

        # 2. Exceeded 4-copy rule test
        invalid_copies = [
            {"card_id": "sv1-196", "count": 5}, # 5 Ultra Balls
            {"card_id": "sv3-26", "count": 1},  # 1 Charmander
            {"card_id": "sve-2", "count": 54}   # 54 Energy
        ]
        is_valid, errors = self.rules.validate_deck(invalid_copies)
        self.assertFalse(is_valid)
        self.assertTrue(any("Exceeded 4 copies" in e for e in errors))

        # 3. Valid deck test
        opt_res = self.deck_opt.optimize_deck([{"card_id": "sv3-125", "count": 3}])
        is_valid, errors = self.rules.validate_deck(opt_res["deck_list"])
        self.assertTrue(is_valid, f"Validation errors: {errors}")
        self.assertEqual(opt_res["total_cards"], 60)

    def test_action_masking_supporter_rule(self):
        # When supporter already played, no Supporter should appear in legal actions
        state_supporter_played = {
            "turn_number": 2,
            "turn_flags": {
                "is_first_turn_of_game": False,
                "supporter_played_this_turn": True, # Already played!
                "energy_attached_this_turn": False,
                "retreated_this_turn": False,
                "stadium_played_this_turn": False
            },
            "player": {
                "hand": [
                    {"card_id": "sv1-189", "name": "Professor's Research"},
                    {"card_id": "sv1-196", "name": "Ultra Ball"}
                ],
                "active_spot": {"card_id": "sv3-26", "name": "Charmander", "attached_energy": []},
                "bench": []
            }
        }
        legal_actions = self.masker.get_legal_actions(state_supporter_played)
        action_types = [a["action_type"] for a in legal_actions]

        self.assertNotIn("PLAY_SUPPORTER", action_types, "Supporter should be masked when already played this turn.")
        self.assertIn("PLAY_ITEM", action_types, "Item cards should remain playable.")

    def test_turn_1_going_first_restriction(self):
        # On Turn 1 Going First, player cannot attack or play supporter
        state_turn1_first = {
            "turn_number": 1,
            "turn_flags": {
                "is_first_turn_of_game": True,
                "supporter_played_this_turn": False,
                "energy_attached_this_turn": False
            },
            "player": {
                "hand": [
                    {"card_id": "sv1-189", "name": "Professor's Research"},
                    {"card_id": "sve-2", "name": "Basic Fire Energy"}
                ],
                "active_spot": {
                    "card_id": "sv3-26",
                    "name": "Charmander",
                    "attached_energy": [{"type": "Fire"}]
                },
                "bench": []
            }
        }
        legal_actions = self.masker.get_legal_actions(state_turn1_first)
        action_types = [a["action_type"] for a in legal_actions]

        self.assertNotIn("PLAY_SUPPORTER", action_types, "Turn 1 Going 1st cannot play Supporter.")
        self.assertNotIn("ATTACK", action_types, "Turn 1 Going 1st cannot Attack.")
        self.assertIn("ATTACH_ENERGY", action_types, "Energy attachment is allowed on Turn 1.")

    def test_policy_value_network_bounds(self):
        sample_state = {
            "turn_number": 3,
            "player": {"prizes_remaining": 4, "prizes_taken": 2, "hand": [{"card_id": "sv1-196"}]},
            "opponent": {"prizes_remaining": 5, "prizes_taken": 1}
        }
        state_vec = self.policy_val.encode_state(sample_state)
        self.assertEqual(len(state_vec), self.policy_val.state_dim)

        logits, win_prob = self.policy_val.forward(state_vec)
        self.assertGreaterEqual(win_prob, 0.0)
        self.assertLessEqual(win_prob, 1.0)


if __name__ == "__main__":
    unittest.main()
