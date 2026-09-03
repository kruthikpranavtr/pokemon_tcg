"""
Multi-Modal Card Vision & Graph Neural Network (GNN) Board Encoder
Models cards as graph nodes (with text/stats + visual features) and board relationships as edges.
"""
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union


class CardVisionGNN:
    def __init__(
        self,
        node_feat_dim: int = 32,
        hidden_dim: int = 64,
        out_dim: int = 128,
        num_heads: int = 4,
        seed: int = 42
    ):
        np.random.seed(seed)
        self.node_feat_dim = node_feat_dim
        self.hidden_dim = hidden_dim
        self.out_dim = out_dim
        self.num_heads = num_heads

        # Node feature projection weights
        self.W_node = np.random.randn(node_feat_dim, hidden_dim) * np.sqrt(2.0 / node_feat_dim)
        self.b_node = np.zeros(hidden_dim)

        # Graph Attention Network (GAT) weights (Multi-Head)
        head_dim = hidden_dim // num_heads
        self.W_attn_src = np.random.randn(num_heads, head_dim, 1) * 0.1
        self.W_attn_dst = np.random.randn(num_heads, head_dim, 1) * 0.1
        self.W_proj = np.random.randn(hidden_dim, hidden_dim) * np.sqrt(2.0 / hidden_dim)

        # Edge relation bias weights: [ATTACHED_TO, EVOLVES_FROM, BENCH_NEIGHBOR, ATTACK_TARGET, STADIUM]
        self.num_edge_types = 5
        self.W_edge_rel = np.random.randn(self.num_edge_types, hidden_dim) * 0.1

        # Global Readout / Pooling MLP
        self.W_pool = np.random.randn(hidden_dim * 2, out_dim) * np.sqrt(2.0 / (hidden_dim * 2))
        self.b_pool = np.zeros(out_dim)

    def _relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def _leaky_relu(self, x: np.ndarray, alpha: float = 0.2) -> np.ndarray:
        return np.where(x > 0, x, x * alpha)

    def _softmax(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        exp_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return exp_x / (np.sum(exp_x, axis=axis, keepdims=True) + 1e-9)

    def encode_card_node(
        self,
        card: Dict[str, Any],
        image_embedding: Optional[Union[List[float], np.ndarray]] = None,
        role: str = "HAND"
    ) -> np.ndarray:
        """
        Converts a single card's metadata + optional visual embedding into a node feature vector.
        """
        feat = np.zeros(self.node_feat_dim, dtype=np.float32)

        # 1. Base Stats
        hp = card.get("hp") or card.get("current_hp") or 0
        feat[0] = min(hp / 330.0, 1.0)
        curr_hp = card.get("current_hp", hp)
        feat[1] = min(curr_hp / 330.0, 1.0)

        # 2. Supertype one-hot
        supertype = card.get("supertype", "").lower()
        if "pok" in supertype:
            feat[2] = 1.0
        elif "train" in supertype:
            feat[3] = 1.0
        elif "energy" in supertype:
            feat[4] = 1.0

        # 3. Subtype features
        subtypes = [s.lower() for s in card.get("subtypes", [])]
        if "basic" in subtypes:
            feat[5] = 1.0
        if "stage 1" in subtypes:
            feat[6] = 1.0
        if "stage 2" in subtypes:
            feat[7] = 1.0
        if "supporter" in subtypes:
            feat[8] = 1.0
        if "item" in subtypes:
            feat[9] = 1.0
        if "stadium" in subtypes:
            feat[10] = 1.0
        if "ex" in subtypes or "v" in subtypes:
            feat[11] = 1.0  # 2-Prize rulebox Pokémon

        # 4. Energy attached & turn count
        attached = card.get("attached_energy", [])
        feat[12] = len(attached) / 5.0
        feat[13] = min(card.get("turns_in_play", 1) / 5.0, 1.0)

        # 5. Attacks damage summary
        attacks = card.get("attacks", [])
        if attacks:
            max_dmg = max([a.get("base_damage", 0) for a in attacks], default=0)
            feat[14] = min(max_dmg / 300.0, 1.0)
            min_cost = min([len(a.get("cost", [])) for a in attacks], default=1)
            feat[15] = min(min_cost / 4.0, 1.0)

        # 6. Role on field
        role_map = {"ACTIVE": 16, "BENCH": 17, "HAND": 18, "STADIUM": 19, "OPP_ACTIVE": 20, "OPP_BENCH": 21}
        if role in role_map:
            feat[role_map[role]] = 1.0

        # 7. Visual features / Image embedding injection
        if image_embedding is not None:
            img_arr = np.array(image_embedding, dtype=np.float32).flatten()
            n_visual = min(10, len(img_arr))
            feat[22:22 + n_visual] = img_arr[:n_visual]
        else:
            # Synthetic visual hash derived from card name / type for consistency
            cname = card.get("name", "")
            h_val = float(sum(ord(c) for c in cname) % 100) / 100.0
            feat[22] = h_val

        return feat

    def build_board_graph(
        self,
        game_state: Dict[str, Any],
        card_images: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Constructs the Heterogeneous Board Graph (Node Feature Matrix, Adjacency Matrix, Edge Type Matrix).
        """
        images = card_images or {}
        nodes = []
        node_indices = {}

        def add_node(card_dict: Dict[str, Any], role: str) -> int:
            cid = card_dict.get("card_id") or card_dict.get("name") or f"node_{len(nodes)}"
            img_emb = images.get(cid)
            feat = self.encode_card_node(card_dict, img_emb, role)
            idx = len(nodes)
            nodes.append(feat)
            node_indices[cid] = idx
            return idx

        player = game_state.get("player", {})
        opponent = game_state.get("opponent", {})

        # 1. Player Active & Attached Energy
        p_active = player.get("active_spot", {})
        p_active_idx = add_node(p_active, "ACTIVE") if p_active else None

        edges = []  # (src, dst, rel_type)

        if p_active:
            for e_idx, e in enumerate(p_active.get("attached_energy", [])):
                e_card = {"name": f"Energy_{e_idx}", "supertype": "Energy", "subtypes": ["Basic Energy"]}
                e_node_idx = add_node(e_card, "ACTIVE")
                edges.append((e_node_idx, p_active_idx, 0))  # ATTACHED_TO

        # 2. Player Bench
        p_bench_indices = []
        for b in player.get("bench", []):
            b_idx = add_node(b, "BENCH")
            p_bench_indices.append(b_idx)
            if p_active_idx is not None:
                edges.append((b_idx, p_active_idx, 2))  # BENCH_NEIGHBOR
            # Bench attached energy
            for e_idx, e in enumerate(b.get("attached_energy", [])):
                e_card = {"name": f"Bench_Energy_{b_idx}_{e_idx}", "supertype": "Energy", "subtypes": ["Basic Energy"]}
                e_node_idx = add_node(e_card, "BENCH")
                edges.append((e_node_idx, b_idx, 0))

        # 3. Opponent Active & Bench
        opp_active = opponent.get("active_spot", {})
        opp_active_idx = add_node(opp_active, "OPP_ACTIVE") if opp_active else None
        if p_active_idx is not None and opp_active_idx is not None:
            edges.append((p_active_idx, opp_active_idx, 3))  # ATTACK_TARGET
            edges.append((opp_active_idx, p_active_idx, 3))

        for b in opponent.get("bench", []):
            opp_b_idx = add_node(b, "OPP_BENCH")
            if opp_active_idx is not None:
                edges.append((opp_b_idx, opp_active_idx, 2))

        # 4. Player Hand Cards
        for h in player.get("hand", []):
            h_idx = add_node(h, "HAND")
            if p_active_idx is not None:
                edges.append((h_idx, p_active_idx, 1))  # EVOLVES_FROM / PLAY_TARGET

        # 5. Stadium
        stadium = game_state.get("stadium_in_play")
        if stadium:
            stad_idx = add_node(stadium, "STADIUM")
            if p_active_idx is not None:
                edges.append((stad_idx, p_active_idx, 4))  # STADIUM_EFFECT
            if opp_active_idx is not None:
                edges.append((stad_idx, opp_active_idx, 4))

        N = len(nodes)
        X = np.array(nodes, dtype=np.float32)
        A = np.eye(N, dtype=np.float32)  # Self-loops
        E_rel = np.zeros((N, N), dtype=np.int32)

        for src, dst, rel in edges:
            if src < N and dst < N:
                A[src, dst] = 1.0
                A[dst, src] = 1.0
                E_rel[src, dst] = rel
                E_rel[dst, src] = rel

        return X, A, E_rel

    def forward(
        self,
        game_state: Dict[str, Any],
        card_images: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Runs Multi-Head Graph Attention (GAT) message passing and returns the global board representation h_board.
        """
        X, A, E_rel = self.build_board_graph(game_state, card_images)
        N = X.shape[0]

        # 1. Initial Linear Projection: H0 = ReLU(X * W_node + b_node)
        H0 = self._relu(np.dot(X, self.W_node) + self.b_node)  # [N, hidden_dim]

        # 2. Multi-Head Graph Attention (GAT)
        head_dim = self.hidden_dim // self.num_heads
        H_heads = []
        attention_matrices = []

        for h in range(self.num_heads):
            # Slice features for this head
            H_h = H0[:, h * head_dim:(h + 1) * head_dim]  # [N, head_dim]

            # Attention scores: e_ij = LeakyReLU(H_i * W_src + H_j * W_dst)
            score_src = np.dot(H_h, self.W_attn_src[h])  # [N, 1]
            score_dst = np.dot(H_h, self.W_attn_dst[h])  # [N, 1]
            E_scores = score_src + score_dst.T  # [N, N]
            E_scores = self._leaky_relu(E_scores)

            # Mask non-adjacent nodes with -inf
            mask = (A == 0)
            E_scores[mask] = -1e9

            # Softmax to get attention coefficients alpha_ij
            alpha = self._softmax(E_scores, axis=-1)  # [N, N]
            attention_matrices.append(alpha)

            # Message Aggregation: H_out_h = alpha * H_h
            H_out_h = np.dot(alpha, H_h)  # [N, head_dim]
            H_heads.append(H_out_h)

        # Concatenate heads
        H_gat = np.concatenate(H_heads, axis=-1)  # [N, hidden_dim]
        H_gat = self._relu(np.dot(H_gat, self.W_proj) + H0)  # Residual connection

        # 3. Global Readout Pooling (Mean Pooling + Max Pooling)
        h_mean = np.mean(H_gat, axis=0)  # [hidden_dim]
        h_max = np.max(H_gat, axis=0)    # [hidden_dim]
        h_concat = np.concatenate([h_mean, h_max])  # [hidden_dim * 2]

        # Global board representation vector
        h_board = self._relu(np.dot(h_concat, self.W_pool) + self.b_pool)  # [out_dim]

        telemetry = {
            "num_nodes": N,
            "num_edges": int(np.sum(A > 0) - N) // 2,
            "mean_attention": float(np.mean(attention_matrices[0])),
            "gnn_embedding_norm": float(np.linalg.norm(h_board))
        }

        return h_board, telemetry
