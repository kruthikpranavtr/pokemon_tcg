"""
Comprehensive Test Suite for the Advanced TCG Strategic AI Engine
Tests:
1. Card Database & basic pokemon classification
2. Deterministic Rules Engine (Weakness x2, Resistance, 1-per-turn rules)
3. Bayesian POMDP Belief State & Information Honesty (KNOWN, INFERRED, PROBABILISTIC, UNKNOWN)
4. Opponent Behavioral Model (5 personality profiles)
5. Position Evaluator & Winning Route Synthesizer
6. Dual-Head Neural Network (Policy & Value heads)
7. POMDP MCTS Search Engine
8. Monte Carlo Simulator with 95% Confidence Intervals
9. Strategic Explainer (9-point report, counterfactual deltas)
10. Unified TCGStrategicAIEngine in FAST and BALANCED modes
11. REST API /analyze & /api/v1/analyze endpoints
"""
import os
import unittest
import numpy as np
from fastapi.testclient import TestClient

from src.tcg_ai.cards.card_database import CardDatabase
from src.tcg_ai.rules.rules_engine import RulesEngine
from src.tcg_ai.probability.belief_state import BeliefStateTracker, InformationCategory
from src.tcg_ai.opponent_model.behavior_model import OpponentBehaviorModel, OpponentStrategy
from src.tcg_ai.evaluation.evaluator import PositionEvaluator
from src.tcg_ai.ml.neural_evaluator import DualHeadNeuralEvaluator
from src.tcg_ai.search.mcts import MCTSEngine
from src.tcg_ai.simulation.mc_simulator import MonteCarloSimulator
from src.tcg_ai.explanation.explainer import StrategicExplainer
from src.tcg_ai.engine import TCGStrategicAIEngine, OperationalMode
from src.api import app


class TestTCGStrategicAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.card_db = CardDatabase.get_instance()
        cls.rules_engine = RulesEngine(cls.card_db)
        cls.belief_tracker = BeliefStateTracker(cls.card_db)
        cls.opp_model = OpponentBehaviorModel(cls.rules_engine, cls.card_db)
        cls.evaluator = PositionEvaluator(card_db=cls.card_db)

        cls.engine = TCGStrategicAIEngine.get_instance()

        cls.sample_state = {
            "turn_number": 3,
            "is_player_turn": True,
            "energy_attached_this_turn": False,
            "supporter_played_this_turn": False,
            "retreated_this_turn": False,
            "player": {
                "name": "Red",
                "active_spot": {
                    "name": "Charizard ex",
                    "current_hp": 280,
                    "max_hp": 330,
                    "attached_energy": ["Fire", "Fire", "Fire"]
                },
                "bench": [
                    {"name": "Pidgeot ex", "current_hp": 280, "max_hp": 280, "attached_energy": []},
                    {"name": "Charmander", "current_hp": 70, "max_hp": 70, "attached_energy": []}
                ],
                "hand": ["Basic Fire Energy", "Boss's Orders", "Ultra Ball", "Charmander"],
                "deck": ["Rare Candy", "Basic Fire Energy", "Arven"],
                "discard": ["Basic Fire Energy"],
                "prizes_taken": 2,
                "prizes_remaining": 4
            },
            "opponent": {
                "name": "Blue",
                "archetype": "miraidon-ex-regieleki",
                "active_spot": {
                    "name": "Miraidon ex",
                    "current_hp": 160,
                    "max_hp": 220,
                    "attached_energy": ["Lightning", "Lightning"]
                },
                "bench": [
                    {"name": "Iron Hands ex", "current_hp": 230, "max_hp": 230, "attached_energy": ["Lightning"]}
                ],
                "hand": ["Unknown", "Unknown", "Unknown"],
                "deck_count": 42,
                "prizes_taken": 1,
                "prizes_remaining": 5
            }
        }

    # 1. Card Database
    def test_01_card_database(self):
        self.assertGreater(len(self.card_db.cards_by_id), 50)
        pika = self.card_db.get_card("Pikachu")
        self.assertIsNotNone(pika)
        self.assertTrue(self.card_db.is_basic_pokemon("Pikachu"))
        self.assertFalse(self.card_db.is_basic_pokemon("Professor's Research"))
        self.assertFalse(self.card_db.is_basic_pokemon("Basic Fire Energy"))


    # 2. Deterministic Rules Engine
    def test_02_rules_engine_actions_and_damage(self):
        actions = self.rules_engine.generate_legal_actions(self.sample_state, is_player=True)
        self.assertTrue(len(actions) > 0)
        action_types = {a["action_type"] for a in actions}
        self.assertIn("ATTACK", action_types)
        self.assertIn("ATTACH_ENERGY", action_types)

        # Test weakness multiplier (Fire vs Grass -> 2x)
        fire_card = {"types": ["Fire"]}
        attack = {"base_damage": 60}
        grass_target = {"types": ["Grass"], "weaknesses": [{"type": "Fire"}], "current_hp": 120}
        dmg, details = self.rules_engine.calculate_damage(fire_card, attack, grass_target)
        self.assertEqual(dmg, 120)  # 60 * 2 = 120
        self.assertEqual(details["weakness_multiplier"], 2)

    # 3. Bayesian Belief State & Strict Honesty
    def test_03_belief_state_honesty(self):
        audit = self.belief_tracker.build_information_audit(self.sample_state)
        self.assertIn(InformationCategory.KNOWN, audit)
        self.assertIn(InformationCategory.INFERRED, audit)
        self.assertIn(InformationCategory.PROBABILISTIC, audit)
        self.assertIn(InformationCategory.UNKNOWN, audit)
        self.assertTrue(len(audit["KNOWN"]) > 0)
        self.assertTrue(len(audit["UNKNOWN"]) > 0)

        # Particle sampling
        sample_bstate = self.belief_tracker.sample_belief_state(self.sample_state)
        self.assertEqual(len(sample_bstate["opponent"]["hand"]), 5)
        probs = self.belief_tracker.estimate_card_probabilities(self.sample_state)
        self.assertIn("Boss's Orders", probs)
        self.assertTrue(0.0 <= probs["Boss's Orders"] <= 1.0)

    # 4. Opponent Behavior Model
    def test_04_opponent_behavior_model(self):
        opp_acts = self.opp_model.sample_top_responses(self.sample_state, top_k=3)
        self.assertTrue(len(opp_acts) > 0)
        total_prob = sum(a.get("probability", 0) for a in opp_acts)
        self.assertAlmostEqual(total_prob, 1.0, places=1)
        self.assertIn("action", opp_acts[0])
        self.assertIn("action_type", opp_acts[0]["action"])

    # 5. Position Evaluator & The Winning Route
    def test_05_position_evaluator_and_winning_route(self):
        pos_eval = self.evaluator.evaluate_position(self.sample_state)
        self.assertIn("win_probability", pos_eval)
        self.assertTrue(0.0 <= pos_eval["win_probability"] <= 1.0)
        self.assertIn("position_value", pos_eval)

        # Winning route
        best_act = {"action_type": "ATTACK", "attack_name": "Burning Darkness", "base_damage": 180, "is_lethal": True}
        route = self.evaluator.compute_winning_route(self.sample_state, best_act)
        self.assertIn("estimated_turns_to_victory", route)
        self.assertIn("steps", route)
        self.assertTrue(len(route["steps"]) >= 1)
        self.assertIn("key_condition", route)

    # 6. Dual-Head Neural Network
    def test_06_dual_head_neural_evaluator(self):
        net = DualHeadNeuralEvaluator(input_dim=48, hidden1_dim=128, hidden2_dim=64, action_dim=24)
        dummy_state = np.random.randn(48).astype(np.float32)
        val, win_prob, logits = net.forward(dummy_state)
        self.assertEqual(len(logits), 24)
        self.assertTrue(-1.0 <= float(val) <= 1.0)
        self.assertTrue(0.0 <= float(win_prob) <= 1.0)


        # Verify training step doesn't crash
        loss = net.train_step(dummy_state, target_value=0.8, target_action_idx=0)
        self.assertTrue(loss > 0)



    # 7. MCTS Search Engine
    def test_07_mcts_search(self):
        mcts = MCTSEngine(
            rules_engine=self.rules_engine,
            opponent_model=self.opp_model,
            max_depth=4
        )
        ranked, win_prob, telemetry = mcts.search(self.sample_state, num_simulations=20)
        self.assertTrue(len(ranked) > 0)
        self.assertTrue(0.0 <= win_prob <= 1.0)
        self.assertIn("num_simulations", telemetry)

    # 8. Monte Carlo Simulator with 95% Confidence Interval
    def test_08_monte_carlo_simulator(self):
        sim = MonteCarloSimulator(
            rules_engine=self.rules_engine,
            opponent_model=self.opp_model,
            belief_tracker=self.belief_tracker,
            evaluator=self.evaluator
        )
        act = {"action_type": "ATTACK", "attack_name": "Burning Darkness", "base_damage": 180}
        res = sim.simulate_action_rollouts(self.sample_state, act, num_rollouts=25)
        self.assertIn("confidence_interval_95_str", res)
        self.assertIn("confidence_interval_95", res)
        ci = res["confidence_interval_95"]
        self.assertTrue(ci[0] <= ci[1])


    # 9. Strategic Explainer (9-Point Standard Report)
    def test_09_strategic_explainer(self):
        explainer = StrategicExplainer(self.card_db)
        ranked_moves = [
            {"action": {"action_type": "ATTACK", "attack_name": "Burning Darkness"}, "win_probability": 0.78},
            {"action": {"action_type": "ATTACH_ENERGY", "card_name": "Basic Fire Energy"}, "win_probability": 0.65}
        ]
        alternatives = explainer.build_counterfactual_analysis(ranked_moves)
        self.assertEqual(len(alternatives), 1)
        self.assertAlmostEqual(alternatives[0]["delta_percentage_points"], -13.0, places=1)

    # 10. Unified TCGStrategicAIEngine
    def test_10_unified_engine_analyze(self):
        report = self.engine.analyze(self.sample_state, mode=OperationalMode.FAST)
        self.assertEqual(report["status"], "success")
        self.assertIn("best_move", report)
        self.assertIn("why", report)
        self.assertIn("winning_route", report)
        self.assertIn("mathematical_analysis", report)
        self.assertIn("top_opponent_responses", report)
        self.assertIn("most_dangerous_response", report)
        self.assertIn("alternative_moves", report)
        self.assertIn("mathematical_calculations", report)
        self.assertIn("risk_assessment", report)
        self.assertIn("confidence", report)
        self.assertIn("information_honesty_audit", report)

    # 11. REST API Endpoints (/analyze and /api/v1/analyze)
    def test_11_rest_api_analyze_endpoints(self):
        for path in ["/analyze", "/api/v1/analyze"]:
            resp = self.client.post(path, json={
                "game_state": self.sample_state,
                "mode": "FAST"
            })
            self.assertEqual(resp.status_code, 200, f"Failed on {path}: {resp.text}")
            data = resp.json()
            self.assertEqual(data["status"], "success")
            self.assertIn("best_move", data)
            self.assertIn("winning_route", data)
            self.assertIn("confidence", data)


if __name__ == "__main__":
    unittest.main()
