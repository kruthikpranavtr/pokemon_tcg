import unittest
from src.tcg_ai.evaluation.evaluator import PositionEvaluator
from src.tcg_ai.cards.card_database import CardDatabase


class TestWeaknessAndBenchEval(unittest.TestCase):
    def setUp(self):
        self.evaluator = PositionEvaluator()
        self.card_db = CardDatabase.get_instance()

    def test_evaluate_pokemon_as_main_weakness_advantage(self):
        # Opponent is Bulbasaur (Grass, weak to Fire, 40 HP remaining)
        opp_act = {"name": "Bulbasaur", "current_hp": 40, "max_hp": 70}

        # Charmander is Fire -> hits Grass weakness
        charmander_eval = self.evaluator.evaluate_pokemon_as_main("Charmander", opp_act)
        # Snorlax is Colorless -> neutral
        snorlax_eval = self.evaluator.evaluate_pokemon_as_main("Snorlax", opp_act)

        self.assertTrue(charmander_eval["hits_weakness"])
        self.assertFalse(snorlax_eval["hits_weakness"])
        self.assertTrue(charmander_eval["is_1hit_ko"])
        self.assertGreater(charmander_eval["win_probability_val"], snorlax_eval["win_probability_val"])
        self.assertIn("Hits opponent weakness (2x)", charmander_eval["matchup_summary"])

    def test_bench_candidate_selection_picks_best_matchup(self):
        # Opponent is Bulbasaur (Grass)
        # Hand has Charmander (Fire, weakness advantage) and Snorlax (Colorless)
        # Bench has space
        state = {
            "player": {
                "active_spot": {"name": "Pikachu", "current_hp": 70, "max_hp": 70, "attached_energy": []},
                "bench": [],
                "hand": ["Charmander", "Snorlax", "Basic Fire Energy"],
                "prizes_remaining": 6
            },
            "opponent": {
                "active_spot": {"name": "Bulbasaur", "current_hp": 70, "max_hp": 70, "attached_energy": []},
                "bench": [],
                "prizes_remaining": 6
            },
            "turn_flags": {"energy_attached_this_turn": False, "supporter_played_this_turn": False}
        }
        best_action = {"action_type": "ATTACK", "attack_name": "Pikachu Strike", "base_damage": 40}

        route = self.evaluator.compute_winning_route(state, best_action)
        bench_steps = [s for s in route["steps"] if s["action_type"] == "BENCH_POKEMON"]

        self.assertTrue(len(bench_steps) > 0)
        # Should pick Charmander because of Fire vs Grass weakness advantage
        self.assertEqual(bench_steps[0]["card_name"], "Charmander")
        self.assertTrue(bench_steps[0]["weakness_exploited"])
        self.assertIn("Win Possibility as Main", bench_steps[0]["action"])

    def test_switch_sequencing_promotes_weakness_exploiter(self):
        # Player Active Pikachu (neutral), Bench has Charmander (exploits Bulbasaur weakness)
        # Hand has Switch
        state = {
            "player": {
                "active_spot": {"name": "Pikachu", "current_hp": 30, "max_hp": 70, "attached_energy": []},
                "bench": [{"name": "Charmander", "current_hp": 70, "max_hp": 70, "attached_energy": []}],
                "hand": ["Switch", "Basic Fire Energy"],
                "prizes_remaining": 6
            },
            "opponent": {
                "active_spot": {"name": "Bulbasaur", "current_hp": 70, "max_hp": 70, "attached_energy": []},
                "bench": [],
                "prizes_remaining": 6
            },
            "turn_flags": {"energy_attached_this_turn": False, "supporter_played_this_turn": False}
        }
        best_action = {"action_type": "ATTACK", "attack_name": "Pikachu Strike", "base_damage": 40}

        route = self.evaluator.compute_winning_route(state, best_action)
        switch_steps = [s for s in route["steps"] if s["action_type"] == "PLAY_ITEM" and "switch" in s["card_name"].lower()]

        self.assertTrue(len(switch_steps) > 0)
        self.assertEqual(switch_steps[0]["target_pokemon"], "Charmander")
        self.assertIn("promote [Charmander]", switch_steps[0]["action"])


if __name__ == "__main__":
    unittest.main()
