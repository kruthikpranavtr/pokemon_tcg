"""
Match Sequence & Decision Transformer
Models multi-turn game trajectories and resource history with Multi-Head Self-Attention.
"""
import numpy as np
from typing import Dict, List, Any, Tuple, Optional


class MatchSequenceTransformer:
    def __init__(
        self,
        embed_dim: int = 128,
        num_heads: int = 4,
        max_seq_len: int = 16,
        action_dim: int = 16,
        seed: int = 42
    ):
        np.random.seed(seed)
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.max_seq_len = max_seq_len
        self.action_dim = action_dim
        self.head_dim = embed_dim // num_heads

        # Positional Embeddings
        self.pos_embeddings = np.random.randn(max_seq_len, embed_dim) * 0.02

        # Multi-Head Self-Attention Weights
        self.W_q = np.random.randn(embed_dim, embed_dim) * np.sqrt(2.0 / embed_dim)
        self.W_k = np.random.randn(embed_dim, embed_dim) * np.sqrt(2.0 / embed_dim)
        self.W_v = np.random.randn(embed_dim, embed_dim) * np.sqrt(2.0 / embed_dim)
        self.W_o = np.random.randn(embed_dim, embed_dim) * np.sqrt(2.0 / embed_dim)

        # Feed-Forward Network (FFN)
        ffn_dim = embed_dim * 2
        self.W_ffn1 = np.random.randn(embed_dim, ffn_dim) * np.sqrt(2.0 / embed_dim)
        self.b_ffn1 = np.zeros(ffn_dim)
        self.W_ffn2 = np.random.randn(ffn_dim, embed_dim) * np.sqrt(2.0 / ffn_dim)
        self.b_ffn2 = np.zeros(embed_dim)

        # Dual Heads: Policy Prior Head & Value Head
        self.W_policy_head = np.random.randn(embed_dim, action_dim) * np.sqrt(2.0 / embed_dim)
        self.b_policy_head = np.zeros(action_dim)

        self.W_value_head = np.random.randn(embed_dim, 1) * np.sqrt(2.0 / embed_dim)
        self.b_value_head = np.zeros(1)

    def _relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -15, 15)))

    def _softmax(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        exp_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return exp_x / (np.sum(exp_x, axis=axis, keepdims=True) + 1e-9)

    def multi_head_attention(self, Q: np.ndarray, K: np.ndarray, V: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Scaled Dot-Product Multi-Head Self-Attention:
        Attention(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V
        """
        seq_len = Q.shape[0]

        # Linear projections
        q = np.dot(Q, self.W_q).reshape(seq_len, self.num_heads, self.head_dim).swapaxes(0, 1)  # [H, S, D]
        k = np.dot(K, self.W_k).reshape(seq_len, self.num_heads, self.head_dim).swapaxes(0, 1)  # [H, S, D]
        v = np.dot(V, self.W_v).reshape(seq_len, self.num_heads, self.head_dim).swapaxes(0, 1)  # [H, S, D]

        # Scaled Dot-Product Scores
        scale = np.sqrt(self.head_dim)
        scores = np.matmul(q, k.swapaxes(-1, -2)) / scale  # [H, S, S]

        # Causal Attention Mask (autoregressive history)
        causal_mask = np.triu(np.ones((seq_len, seq_len)), k=1) * -1e9
        scores = scores + causal_mask

        attn_weights = self._softmax(scores, axis=-1)  # [H, S, S]
        attn_out = np.matmul(attn_weights, v)          # [H, S, D]

        # Concatenate heads and project
        attn_out = attn_out.swapaxes(0, 1).reshape(seq_len, self.embed_dim)  # [S, embed_dim]
        out = np.dot(attn_out, self.W_o)

        return out, attn_weights

    def forward(
        self,
        board_tokens: np.ndarray,
        turn_history: Optional[List[np.ndarray]] = None
    ) -> Tuple[np.ndarray, float, Dict[str, Any]]:
        """
        Forward pass over sequence of turns/tokens.
        Returns:
            - policy_logits [action_dim]
            - base_win_probability in [0, 1]
            - transformer attention telemetry
        """
        # Prepare token sequence: [History_tokens ..., Current_token]
        if turn_history and len(turn_history) > 0:
            seq_list = list(turn_history[-self.max_seq_len + 1:])
            seq_list.append(board_tokens)
            X_seq = np.array(seq_list, dtype=np.float32)
        else:
            X_seq = np.expand_dims(board_tokens, axis=0)  # [1, embed_dim]

        seq_len = min(X_seq.shape[0], self.max_seq_len)
        X_seq = X_seq[-seq_len:]

        # 1. Add Positional Encoding
        H = X_seq + self.pos_embeddings[:seq_len]

        # 2. Self-Attention Block with Residual Connection & Layer Norm approximation
        attn_out, attn_weights = self.multi_head_attention(H, H, H)
        H_attn = H + attn_out

        # 3. Feed-Forward Network Block (FFN)
        ffn_h = self._relu(np.dot(H_attn, self.W_ffn1) + self.b_ffn1)
        ffn_out = np.dot(ffn_h, self.W_ffn2) + self.b_ffn2
        H_final = H_attn + ffn_out  # [S, embed_dim]

        # 4. Extract current turn token representation (last token in sequence)
        current_rep = H_final[-1]

        # 5. Dual Prediction Heads
        policy_logits = np.dot(current_rep, self.W_policy_head) + self.b_policy_head
        raw_val = np.dot(current_rep, self.W_value_head) + self.b_value_head
        base_win_prob = float(self._sigmoid(raw_val).item())

        telemetry = {
            "seq_len": seq_len,
            "mean_attention_entropy": float(np.mean(-np.sum(attn_weights * np.log(attn_weights + 1e-9), axis=-1))),
            "transformer_norm": float(np.linalg.norm(current_rep))
        }

        return policy_logits, base_win_prob, telemetry
