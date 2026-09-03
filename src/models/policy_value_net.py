"""
Model 2: Real-Time In-Game Sequencer & Policy-Value Network
Dual-head architecture:
- Policy Head: Action selection & move ranking over masked legal moves.
- Value Head: Real-time match win probability estimation in [0, 1].
"""
import numpy as np
from typing import Dict, List, Any, Tuple


class PolicyValueNetwork:
    def __init__(self, state_dim: int = 32, hidden_dim: int = 64, action_dim: int = 16, seed: int = 42):
        np.random.seed(seed)
        self.state_dim = state_dim
        self.hidden_dim = hidden_dim
        self.action_dim = action_dim

        # State Encoder weights
        self.W1 = np.random.randn(state_dim, hidden_dim) * np.sqrt(2.0 / state_dim)
        self.b1 = np.zeros(hidden_dim)

        self.W2 = np.random.randn(hidden_dim, hidden_dim) * np.sqrt(2.0 / hidden_dim)
        self.b2 = np.zeros(hidden_dim)

        # Policy Head (Action Logits)
        self.W_policy = np.random.randn(hidden_dim, action_dim) * np.sqrt(2.0 / hidden_dim)
        self.b_policy = np.zeros(action_dim)

        # Value Head (Scalar Win Probability)
        self.W_value = np.random.randn(hidden_dim, 1) * np.sqrt(2.0 / hidden_dim)
        self.b_value = np.zeros(1)

    def _relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -15, 15)))

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e_x / np.sum(e_x, axis=-1, keepdims=True)

    def encode_state(self, game_state: Dict[str, Any]) -> np.ndarray:
        """
        Converts the discrete game_state JSON into a normalized 32-dim feature vector.
        """
        features = np.zeros(self.state_dim, dtype=np.float32)
        player = game_state.get("player", {})
        opponent = game_state.get("opponent", {})
        turn_flags = game_state.get("turn_flags", {})

        # 1. Turn & Prize features
        features[0] = min(game_state.get("turn_number", 1) / 20.0, 1.0)
        features[1] = player.get("prizes_remaining", 6) / 6.0
        features[2] = opponent.get("prizes_remaining", 6) / 6.0
        features[3] = (player.get("prizes_taken", 0) - opponent.get("prizes_taken", 0)) / 6.0

        # 2. Hand & Deck counts
        features[4] = len(player.get("hand", [])) / 10.0
        features[5] = player.get("deck_count", 40) / 60.0
        features[6] = opponent.get("deck_count", 40) / 60.0
        features[7] = opponent.get("hand_count", 5) / 10.0

        # 3. Active Pokémon HP & Energy
        p_active = player.get("active_spot", {})
        features[8] = p_active.get("current_hp", 0) / 330.0
        features[9] = len(p_active.get("attached_energy", [])) / 5.0

        opp_active = opponent.get("active_spot", {})
        features[10] = opp_active.get("current_hp", 0) / 330.0
        features[11] = len(opp_active.get("attached_energy", [])) / 5.0

        # 4. Bench size & status
        features[12] = len(player.get("bench", [])) / 5.0
        features[13] = len(opponent.get("bench", [])) / 5.0

        # 5. Turn flags
        features[14] = 1.0 if turn_flags.get("supporter_played_this_turn", False) else 0.0
        features[15] = 1.0 if turn_flags.get("energy_attached_this_turn", False) else 0.0
        features[16] = 1.0 if game_state.get("stadium_in_play") else 0.0

        return features

    def forward(self, state_vec: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Forward pass returning (policy_logits, win_probability).
        """
        # Encoder
        h1 = self._relu(np.dot(state_vec, self.W1) + self.b1)
        h2 = self._relu(np.dot(h1, self.W2) + self.b2)

        # Policy & Value
        policy_logits = np.dot(h2, self.W_policy) + self.b_policy
        raw_value = np.dot(h2, self.W_value) + self.b_value
        win_prob = float(self._sigmoid(raw_value).item())

        return policy_logits, win_prob

    def rank_legal_actions(
        self,
        game_state: Dict[str, Any],
        legal_actions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Scores and ranks strictly legal actions using policy network + heuristics.
        """
        if not legal_actions:
            return [], 0.5

        state_vec = self.encode_state(game_state)
        policy_logits, base_win_prob = self.forward(state_vec)

        # Action type preference weights
        action_weights = {
            "EVOLVE_POKEMON": 1.4,
            "PLAY_SUPPORTER": 1.3,
            "PLAY_ITEM": 1.25,
            "ATTACH_ENERGY": 1.2,
            "USE_STADIUM_EFFECT": 1.15,
            "BENCH_BASIC_POKEMON": 1.1,
            "ATTACK": 1.35,
            "PASS_TURN": 0.5
        }

        ranked_actions = []
        for i, act in enumerate(legal_actions):
            act_type = act.get("action_type", "PASS_TURN")
            # Map into policy logit index
            idx = i % self.action_dim
            logit_score = float(policy_logits[idx])
            weight = action_weights.get(act_type, 1.0)

            # Combined score
            score = (logit_score + 10.0) * weight

            # Simulated win probability after play
            delta = min(0.08, max(-0.05, (score - 10.0) * 0.01))
            post_win_prob = float(np.clip(base_win_prob + delta, 0.05, 0.95))

            ranked_actions.append({
                "action": act,
                "score": score,
                "post_win_prob": post_win_prob
            })

        # Sort descending by score
        ranked_actions.sort(key=lambda x: x["score"], reverse=True)

        return ranked_actions, base_win_prob
