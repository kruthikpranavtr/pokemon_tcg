"""
Dual-Head Neural Network Evaluator (Pure NumPy High-Speed Vectorized Architecture)
Architecture:
Input (48 features) -> Linear(48, 128) + LeakyReLU -> Linear(128, 64) + LeakyReLU
  |--> Value Head: Linear(64, 1) + Tanh -> V(S) in [-1, 1], Win Probability in [0, 1]
  |--> Policy Head: Linear(64, 24) -> Action Logits & Masked Softmax P(a | S)

Supports full forward pass, backpropagation, and weight serialization to/from JSON.
"""
import os
import json
import numpy as np
from typing import Dict, List, Any, Tuple, Optional


class DualHeadNeuralEvaluator:
    ACTION_VOCAB = [
        "ATTACK_1", "ATTACK_2", "ATTACK_3",
        "ATTACH_ENERGY_ACTIVE", "ATTACH_ENERGY_BENCH_1", "ATTACH_ENERGY_BENCH_2", "ATTACH_ENERGY_BENCH_3",
        "BENCH_POKEMON_1", "BENCH_POKEMON_2", "BENCH_POKEMON_3",
        "EVOLVE_ACTIVE", "EVOLVE_BENCH_1", "EVOLVE_BENCH_2",
        "PLAY_SUPPORTER_RESEARCH", "PLAY_SUPPORTER_IONO", "PLAY_SUPPORTER_BOSS", "PLAY_SUPPORTER_GENERIC",
        "PLAY_ITEM_BALL", "PLAY_ITEM_CANDY", "PLAY_ITEM_GENERIC",
        "RETREAT_BENCH_1", "RETREAT_BENCH_2", "RETREAT_BENCH_3",
        "PASS_TURN"
    ]

    def __init__(
        self,
        input_dim: int = 48,
        hidden1_dim: int = 128,
        hidden2_dim: int = 64,
        action_dim: int = 24,
        seed: int = 42
    ):
        np.random.seed(seed)
        self.input_dim = input_dim
        self.hidden1_dim = hidden1_dim
        self.hidden2_dim = hidden2_dim
        self.action_dim = action_dim

        # He initialization for LeakyReLU
        self.W1 = np.random.randn(input_dim, hidden1_dim) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros(hidden1_dim)

        self.W2 = np.random.randn(hidden1_dim, hidden2_dim) * np.sqrt(2.0 / hidden1_dim)
        self.b2 = np.zeros(hidden2_dim)

        # Value Head: Linear(64, 1)
        self.W_val = np.random.randn(hidden2_dim, 1) * np.sqrt(2.0 / hidden2_dim)
        self.b_val = np.zeros(1)

        # Policy Head: Linear(64, 24)
        self.W_pol = np.random.randn(hidden2_dim, action_dim) * np.sqrt(2.0 / hidden2_dim)
        self.b_pol = np.zeros(action_dim)

        # Adam optimizer moments
        self.m = {k: np.zeros_like(v) for k, v in self._get_params().items()}
        self.v = {k: np.zeros_like(v) for k, v in self._get_params().items()}
        self.t = 0

    def _get_params(self) -> Dict[str, np.ndarray]:
        return {
            "W1": self.W1, "b1": self.b1,
            "W2": self.W2, "b2": self.b2,
            "W_val": self.W_val, "b_val": self.b_val,
            "W_pol": self.W_pol, "b_pol": self.b_pol
        }

    def _leaky_relu(self, x: np.ndarray, alpha: float = 0.01) -> np.ndarray:
        return np.where(x > 0, x, x * alpha)

    def _leaky_relu_grad(self, x: np.ndarray, alpha: float = 0.01) -> np.ndarray:
        return np.where(x > 0, 1.0, alpha)

    def forward(
        self,
        state_vec: np.ndarray
    ) -> Tuple[float, float, np.ndarray]:
        """
        Forward pass.
        Returns:
            - position_value: V(S) in [-1, 1]
            - win_probability: in [0, 1]
            - policy_logits: raw logits over 24 action dimensions
        """
        if state_vec.ndim == 1:
            state_vec = state_vec.reshape(1, -1)

        # Layer 1
        z1 = np.dot(state_vec, self.W1) + self.b1
        h1 = self._leaky_relu(z1)

        # Layer 2
        z2 = np.dot(h1, self.W2) + self.b2
        h2 = self._leaky_relu(z2)

        # Value Head (Tanh in [-1, 1])
        z_val = np.dot(h2, self.W_val) + self.b_val
        val = float(np.tanh(z_val).item())
        win_prob = float((val + 1.0) / 2.0)  # Map [-1, 1] -> [0, 1]

        # Policy Head
        logits = (np.dot(h2, self.W_pol) + self.b_pol).flatten()

        return val, win_prob, logits

    def map_action_to_index(self, action: Dict[str, Any]) -> int:
        """Maps an action dict to an index in ACTION_VOCAB."""
        act_type = action.get("action_type", "")
        if act_type == "ATTACK":
            return 0
        if act_type == "ATTACH_ENERGY":
            return 3 if action.get("target") == "ACTIVE" else 4
        if act_type == "BENCH_POKEMON":
            return 7
        if act_type == "EVOLVE_POKEMON":
            return 10 if action.get("target") == "ACTIVE" else 11
        if act_type == "PLAY_SUPPORTER":
            cname = action.get("card_name", "")
            if "research" in cname.lower():
                return 13
            if "iono" in cname.lower():
                return 14
            if "boss" in cname.lower():
                return 15
            return 16
        if act_type == "PLAY_ITEM":
            cname = action.get("card_name", "")
            if "ball" in cname.lower():
                return 17
            if "candy" in cname.lower():
                return 18
            return 19
        if act_type == "RETREAT":
            return 20
        return 23  # PASS_TURN

    def rank_actions_with_prior(
        self,
        state_vec: np.ndarray,
        legal_actions: List[Dict[str, Any]]
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Calculates masked softmax probabilities over the exact legal actions available.
        Never allocates probability to illegal actions.
        """
        if not legal_actions:
            return []

        _, _, logits = self.forward(state_vec)

        # Extract logits for legal actions
        action_indices = [self.map_action_to_index(a) for a in legal_actions]
        legal_logits = np.array([logits[idx] for idx in action_indices])

        # Numerically stable softmax
        exp_l = np.exp(legal_logits - np.max(legal_logits))
        priors = exp_l / (np.sum(exp_l) + 1e-9)

        result = []
        for action, p in zip(legal_actions, priors):
            result.append((action, float(p)))

        result.sort(key=lambda x: x[1], reverse=True)
        return result

    def train_step(
        self,
        state_vec: np.ndarray,
        target_value: float,
        target_action_idx: int,
        lr: float = 0.001
    ) -> float:
        """
        Single SGD/Adam training step optimizing joint Loss = MSE(V, target_V) + CrossEntropy(Policy, target_A).
        """
        if state_vec.ndim == 1:
            state_vec = state_vec.reshape(1, -1)

        # Forward
        z1 = np.dot(state_vec, self.W1) + self.b1
        h1 = self._leaky_relu(z1)

        z2 = np.dot(h1, self.W2) + self.b2
        h2 = self._leaky_relu(z2)

        z_val = np.dot(h2, self.W_val) + self.b_val
        val = np.tanh(z_val)

        z_pol = np.dot(h2, self.W_pol) + self.b_pol
        exp_p = np.exp(z_pol - np.max(z_pol))
        p_probs = exp_p / np.sum(exp_p)

        # Losses
        # 1. Value loss (MSE)
        v_loss = 0.5 * (val.item() - target_value) ** 2
        d_val = (val - target_value) * (1.0 - val ** 2)  # derivative of tanh

        # 2. Policy loss (Cross Entropy)
        one_hot = np.zeros((1, self.action_dim))
        one_hot[0, target_action_idx] = 1.0
        d_pol = p_probs - one_hot

        # Gradients
        grad_W_val = np.dot(h2.T, d_val)
        grad_b_val = np.sum(d_val, axis=0)

        grad_W_pol = np.dot(h2.T, d_pol)
        grad_b_pol = np.sum(d_pol, axis=0)

        dh2 = np.dot(d_val, self.W_val.T) + np.dot(d_pol, self.W_pol.T)
        dz2 = dh2 * self._leaky_relu_grad(z2)

        grad_W2 = np.dot(h1.T, dz2)
        grad_b2 = np.sum(dz2, axis=0)

        dh1 = np.dot(dz2, self.W2.T)
        dz1 = dh1 * self._leaky_relu_grad(z1)

        grad_W1 = np.dot(state_vec.T, dz1)
        grad_b1 = np.sum(dz1, axis=0)

        grads = {
            "W1": grad_W1, "b1": grad_b1,
            "W2": grad_W2, "b2": grad_b2,
            "W_val": grad_W_val, "b_val": grad_b_val,
            "W_pol": grad_W_pol, "b_pol": grad_b_pol
        }

        # Adam update
        self.t += 1
        beta1, beta2, eps = 0.9, 0.999, 1e-8
        for k in self._get_params():
            g = grads[k]
            self.m[k] = beta1 * self.m[k] + (1 - beta1) * g
            self.v[k] = beta2 * self.v[k] + (1 - beta2) * (g ** 2)
            m_hat = self.m[k] / (1 - beta1 ** self.t)
            v_hat = self.v[k] / (1 - beta2 ** self.t)
            getattr(self, k)[:] -= lr * m_hat / (np.sqrt(v_hat) + eps)

        return float(v_loss)

    def save_weights(self, filepath: str):
        params = {k: v.tolist() for k, v in self._get_params().items()}
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(params, f)

    def load_weights(self, filepath: str) -> bool:
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                params = json.load(f)
            # Ensure shape compatibility
            if "W1" in params and np.array(params["W1"]).shape != self.W1.shape:
                return False
            for k in self._get_params():
                if k in params:
                    arr = np.array(params[k], dtype=np.float32)
                    if arr.shape == getattr(self, k).shape:
                        setattr(self, k, arr)
            return True
        except Exception:
            return False
