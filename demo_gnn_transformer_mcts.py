"""
Interactive Showcase: Hybrid GNN + Transformer + MCTS Winning Probability Engine
Demonstrates:
  1. GNN Multi-Modal Board Graph Construction (Card Nodes, Attachments, Bench Edges, Visual Embeddings)
  2. Match Sequence Transformer Self-Attention
  3. MCTS Terminal Outcome Lookahead (60 Rollouts with PUCT Verification)
"""
import json
import numpy as np
from src.engine.card_resolver import CardResolver
from src.engine.action_mask import ActionMaskEngine
from src.engine.explainer import ActionExplainer
from src.models.card_vision_gnn import CardVisionGNN
from src.models.decision_transformer import MatchSequenceTransformer
from src.engine.mcts_engine import MCTSEngine

def main():
    print("=" * 80)
    print("[*] POKEMON TCG // HYBRID GNN + TRANSFORMER + MCTS DECISION ENGINE")
    print("=" * 80)

    # 1. Load cards database
    with open("data/cards_dataset.json", "r", encoding="utf-8") as f:
        cards = {c["card_id"]: c for c in json.load(f)["cards"]}

    resolver = CardResolver(cards)
    masker = ActionMaskEngine(cards)
    explainer = ActionExplainer(cards)

    # 2. Instantiate Neural Modules
    print("[1/4] Initializing Multi-Modal GNN, Sequence Transformer & MCTS Engine...")
    gnn = CardVisionGNN(node_feat_dim=32, hidden_dim=64, out_dim=128, num_heads=4)
    transformer = MatchSequenceTransformer(embed_dim=128, num_heads=4, action_dim=16)
    mcts = MCTSEngine(gnn, transformer, masker, c_puct=1.414, max_depth=6)

    # 3. Define Live Competitive Scenario
    our_cards = {
        "active_pokemon": {"name": "Charizard ex", "current_hp": 330, "attached_energy": ["Fire", "Fire"]},
        "hand_cards": ["Boss's Orders", "Prime Catcher", "Ultra Ball", "Super Rod", "Basic Fire Energy"],
        "bench_pokemon": [
            {"name": "Pidgeot ex", "current_hp": 280, "attached_energy": []},
            {"name": "Radiant Greninja", "current_hp": 130, "attached_energy": []}
        ],
        "prizes_remaining": 2,
        "prizes_taken": 4
    }

    opponent_cards = {
        "deck_archetype": "miraidon-ex-regieleki",
        "active_pokemon": {"name": "Miraidon ex", "current_hp": 140, "attached_energy": ["Lightning", "Lightning"]},
        "bench_pokemon": [
            {"name": "Iron Hands ex", "current_hp": 230, "attached_energy": []},
            {"name": "Raikou V", "current_hp": 200, "attached_energy": []}
        ],
        "prizes_remaining": 2,
        "prizes_taken": 4
    }

    turn_context = {
        "turn_number": 5,
        "supporter_played_this_turn": False,
        "energy_attached_this_turn": False
    }

    # Build standard game state
    game_state = resolver.build_game_state(our_cards, opponent_cards, turn_context)

    # 4. GNN Multi-Modal Board Encoding
    print("\n[2/4] Executing Multi-Modal Graph Neural Network (GNN) Message Passing...")
    # Synthetic visual features / image embeddings
    card_images = {
        "sv3-125": np.random.randn(8) * 0.5,  # Charizard ex image embedding
        "sv1-86": np.random.randn(8) * 0.5    # Miraidon ex image embedding
    }
    h_board, gnn_telemetry = gnn.forward(game_state, card_images)
    print(f"  * Board Graph Nodes  : {gnn_telemetry['num_nodes']} card nodes")
    print(f"  * Relational Edges   : {gnn_telemetry['num_edges']} connections (attachments, evolutions, targets)")
    print(f"  * Global Embedding   : h_board vector shape = {h_board.shape}, norm = {gnn_telemetry['gnn_embedding_norm']:.3f}")

    # 5. Sequence Transformer Attention
    print("\n[3/4] Running Match Sequence Transformer Self-Attention...")
    turn_history = [np.random.randn(128) * 0.1 for _ in range(4)]  # Simulated turns 1-4
    policy_logits, base_trans_win, trans_telemetry = transformer.forward(h_board, turn_history)
    print(f"  * Trajectory Tokens  : {trans_telemetry['seq_len']} match turns encoded")
    print(f"  * Base Transformer V : {base_trans_win * 100:.1f}% estimated win probability")

    # 6. MCTS Terminal Outcome Verification
    print("\n[4/4] Executing Monte Carlo Tree Search (60 Forward Rollouts & Terminal Verification)...")
    ranked_moves, grounded_win, mcts_telemetry = mcts.run_mcts_search(
        root_state=game_state,
        num_simulations=60,
        turn_history=turn_history
    )

    print(f"\n{'=' * 80}")
    print(f"[+] MCTS VERIFIED WIN PROBABILITY : {grounded_win * 100:.1f}%")
    print(f"    (Terminal Nodes Verified: {mcts_telemetry['terminal_nodes_verified']} | Branches: {mcts_telemetry['root_legal_branches']})")
    print("=" * 80)

    print("\nRANKED STRATEGIC PLAYS (Verified by MCTS):")
    for rank, m in enumerate(ranked_moves[:4], start=1):
        act = m["action"]
        card_label = act.get("card_name") or act.get("attack_name") or act.get("action_type")
        is_term = "[TERMINAL WIN PATH]" if m.get("is_terminal_win_path") else ""
        print(f"  #{rank} [{act.get('action_type')}] {card_label} {is_term}")
        print(f"      * MCTS Visits: {m['mcts_visits']} ({m['visit_ratio']*100:.1f}%) | Q-Value: {m['mcts_q_value']:.3f} | Post Win Rate: {m['post_win_prob']*100:.1f}%")
        print(f"      * Rationale  : {explainer.explain(act, game_state, m['post_win_prob'])}")

if __name__ == "__main__":
    main()
