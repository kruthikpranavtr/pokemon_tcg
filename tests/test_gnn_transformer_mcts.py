"""
Comprehensive Test Suite for Hybrid GNN + Transformer + MCTS Decision Engine
"""
import unittest
import json
import numpy as np
from src.engine.action_mask import ActionMaskEngine
from src.engine.card_resolver import CardResolver
from src.models.card_vision_gnn import CardVisionGNN
from src.models.decision_transformer import MatchSequenceTransformer
from src.engine.mcts_engine import MCTSEngine
from fastapi.testclient import TestClient
from src.api import app


class TestGNNTransformerMCTSEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open("data/cards_dataset.json", "r", encoding="utf-8") as f:
            cards_data = json.load(f)
            cls.card_db = {c["card_id"]: c for c in cards_data["cards"]}

        cls.card_resolver = CardResolver(cls.card_db)
        cls.action_masker = ActionMaskEngine(cls.card_db)
        cls.gnn = CardVisionGNN(node_feat_dim=32, hidden_dim=64, out_dim=128, num_heads=4)
        cls.transformer = MatchSequenceTransformer(embed_dim=128, num_heads=4, action_dim=16)
        cls.mcts = MCTSEngine(cls.gnn, cls.transformer, cls.action_masker, c_puct=1.414, max_depth=5)
        cls.client = TestClient(app)

    def setUp(self):
        self.sample_match_state = {
            "turn_number": 3,
            "turn_flags": {
                "is_first_turn_of_game": False,
                "supporter_played_this_turn": False,
                "energy_attached_this_turn": False
            },
            "player": {
                "prizes_remaining": 6,
                "prizes_taken": 0,
                "hand": [
                    {"card_id": "sv3-125", "name": "Charizard ex"},
                    {"card_id": "sv1-189", "name": "Professor's Research"},
                    {"card_id": "sv1-196", "name": "Ultra Ball"},
                    {"card_id": "sve-2", "name": "Basic Fire Energy"}
                ],
                "active_spot": {
                    "card_id": "sv3-26",
                    "name": "Charmander",
                    "current_hp": 70,
                    "attached_energy": [{"type": "Fire"}],
                    "turns_in_play": 1
                },
                "bench": [
                    {"slot": 1, "card_id": "sv3-162", "name": "Pidgey", "current_hp": 60, "attached_energy": []}
                ]
            },
            "opponent": {
                "prizes_remaining": 6,
                "prizes_taken": 0,
                "active_spot": {
                    "card_id": "sv1-86",
                    "name": "Miraidon ex",
                    "current_hp": 220,
                    "attached_energy": [{"type": "Lightning"}, {"type": "Lightning"}]
                },
                "bench": []
            }
        }

    def test_gnn_board_encoding(self):
        # 1. Test Node Encoding with optional visual embeddings
        dummy_card = {"name": "Charizard ex", "hp": 330, "supertype": "Pokémon", "subtypes": ["Stage 2", "ex"]}
        img_emb = np.random.randn(8)
        feat = self.gnn.encode_card_node(dummy_card, img_emb, role="HAND")
        self.assertEqual(feat.shape, (32,))
        self.assertEqual(feat[2], 1.0)  # Pokémon supertype

        # 2. Test Board Graph Construction & Multi-Head GAT
        h_board, telemetry = self.gnn.forward(self.sample_match_state)
        self.assertEqual(h_board.shape, (128,))
        self.assertTrue(telemetry["num_nodes"] >= 4)
        self.assertTrue(telemetry["gnn_embedding_norm"] > 0)

    def test_sequence_transformer(self):
        h_board, _ = self.gnn.forward(self.sample_match_state)
        turn_history = [np.random.randn(128) * 0.1, np.random.randn(128) * 0.1]

        # Forward pass with turn history
        logits, win_prob, telemetry = self.transformer.forward(h_board, turn_history)
        self.assertEqual(logits.shape, (16,))
        self.assertTrue(0.0 <= win_prob <= 1.0)
        self.assertEqual(telemetry["seq_len"], 3)

    def test_mcts_rollout_search_and_terminal_verification(self):
        # Run 40 MCTS rollouts
        ranked_moves, grounded_win_prob, telemetry = self.mcts.run_mcts_search(
            root_state=self.sample_match_state,
            num_simulations=40
        )

        self.assertTrue(len(ranked_moves) > 0)
        self.assertTrue(0.0 <= grounded_win_prob <= 1.0)
        self.assertEqual(telemetry["num_simulations"], 40)
        self.assertTrue(telemetry["root_legal_branches"] > 0)

        # Check that top move has visits and post win prob
        top = ranked_moves[0]
        self.assertIn("mcts_visits", top)
        self.assertIn("post_win_prob", top)
        self.assertTrue(top["mcts_visits"] > 0)

    def test_api_recommend_move_with_mcts_and_gnn(self):
        payload = {
            "session_id": "hybrid-test-1",
            "our_cards": {
                "hand_cards": ["Charizard ex", "Professor's Research", "Basic Fire Energy"],
                "active_pokemon": {"name": "Charmander", "current_hp": 70, "attached_energy": ["Fire"]},
                "bench_pokemon": [{"name": "Pidgey", "current_hp": 60}],
                "prizes_remaining": 6
            },
            "opponent_cards": {
                "deck_archetype": "miraidon-ex-regieleki",
                "active_pokemon": {"name": "Miraidon ex", "current_hp": 220, "attached_energy": ["Lightning", "Lightning"]},
                "bench_pokemon": [],
                "prizes_remaining": 6
            },
            "turn_context": {
                "turn_number": 3,
                "supporter_played_this_turn": False,
                "energy_attached_this_turn": False
            },
            "mcts_simulations": 30
        }

        res = self.client.post(
            "/api/v1/recommend-move",
            headers={"X-API-Key": "tcg-live-secret-key-2026"},
            json=payload
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("mcts_search_telemetry", data)
        self.assertIn("gnn_board_telemetry", data)
        self.assertIn("transformer_telemetry", data)
        self.assertIn("current_win_probability", data)
        self.assertTrue(len(data.get("all_recommended_moves", [])) > 0)


if __name__ == "__main__":
    unittest.main()
