"""
Game State Representation & Dense Feature Vector Encoder
POMDP State: S_t = { board, hand, known_info, hidden_info_belief, resources, prizes, discard, turn, phase }
Encodes discrete state into normalized dense numerical feature vector for neural models and MCTS evaluations.
"""
import copy
import numpy as np
from typing import Dict, List, Any, Optional
from ..cards.card_database import CardDatabase


class GameStateManager:
    FEATURE_VECTOR_DIM = 48

    def __init__(self, card_db: Optional[CardDatabase] = None):
        self.card_db = card_db or CardDatabase.get_instance()

    def build_standard_state(
        self,
        player_active: Dict[str, Any],
        player_bench: List[Dict[str, Any]],
        player_hand: List[Any],
        player_prizes: int,
        opp_active: Dict[str, Any],
        opp_bench: List[Dict[str, Any]],
        opp_hand_count: int,
        opp_prizes: int,
        turn_number: int = 1,
        turn_flags: Optional[Dict[str, bool]] = None,
        discard_p: Optional[List[Any]] = None,
        discard_opp: Optional[List[Any]] = None,
        deck_size_p: int = 40,
        deck_size_opp: int = 40,
        stadium: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates canonical structured game state.
        """
        return {
            "turn_number": turn_number,
            "turn_flags": turn_flags or {
                "energy_attached_this_turn": False,
                "supporter_played_this_turn": False,
                "retreated_this_turn": False
            },
            "stadium": stadium,
            "player": {
                "active_spot": player_active,
                "bench": player_bench,
                "hand": player_hand,
                "prizes_remaining": player_prizes,
                "prizes_taken": 6 - player_prizes,
                "deck_count": deck_size_p,
                "discard": discard_p or []
            },
            "opponent": {
                "active_spot": opp_active,
                "bench": opp_bench,
                "hand_count": opp_hand_count,
                "known_hand": [],  # Revealed cards in opponent hand
                "prizes_remaining": opp_prizes,
                "prizes_taken": 6 - opp_prizes,
                "deck_count": deck_size_opp,
                "discard": discard_opp or []
            }
        }

    def encode_feature_vector(self, state: Dict[str, Any]) -> np.ndarray:
        """
        Encodes the structured game state into a 48-dimensional normalized float32 vector.
        Features:
        [0..3]: Turn & Prize Dynamics
        [4..7]: Hand & Deck Resources
        [8..15]: Active Pokémon Combat Dynamics (HP, Energy, Damage Capacity, Threat)
        [16..23]: Opponent Active Dynamics
        [24..31]: Bench Depth & Reserves
        [32..39]: Resource Advantage & Status Effects
        [40..47]: Strategic Potentials & Win Readiness
        """
        vec = np.zeros(self.FEATURE_VECTOR_DIM, dtype=np.float32)

        player = state.get("player", {})
        opp = state.get("opponent", {})
        turn_flags = state.get("turn_flags", {})

        p_prizes = player.get("prizes_remaining", 6)
        opp_prizes = opp.get("prizes_remaining", 6)
        p_taken = player.get("prizes_taken", 6 - p_prizes)
        opp_taken = opp.get("prizes_taken", 6 - opp_prizes)

        # 1. Turn & Prizes (0..3)
        vec[0] = min(state.get("turn_number", 1) / 25.0, 1.0)
        vec[1] = p_prizes / 6.0
        vec[2] = opp_prizes / 6.0
        vec[3] = (p_taken - opp_taken) / 6.0  # Prize advantage in [-1, 1]

        # 2. Hand & Deck Resources (4..7)
        vec[4] = len(player.get("hand", [])) / 10.0
        vec[5] = opp.get("hand_count", 5) / 10.0
        vec[6] = player.get("deck_count", 40) / 60.0
        vec[7] = opp.get("deck_count", 40) / 60.0

        # Helper for attached_energy length
        def _get_e_count(val):
            return len(val) if isinstance(val, list) else (int(val) if isinstance(val, (int, float)) else 0)

        # 3. Player Active Dynamics (8..15)
        p_act = player.get("active_spot") or player.get("active_pokemon") or {}
        p_meta = self.card_db.get_meta(p_act.get("name", ""))
        p_max_hp = p_act.get("max_hp") or p_meta.get("hp", 100)
        p_curr_hp = max(0, p_act.get("current_hp", p_max_hp))
        p_energy_count = _get_e_count(p_act.get("attached_energy", []))

        vec[8] = p_curr_hp / 340.0
        vec[9] = (p_curr_hp / max(1, p_max_hp))
        vec[10] = p_energy_count / 6.0
        vec[11] = 1.0 if "ex" in p_act.get("name", "").lower() else 0.0

        # Calculate best attack damage for player active
        p_best_dmg = 0
        attacks = p_meta.get("attacks", [])
        for a in attacks:
            p_best_dmg = max(p_best_dmg, a.get("base_damage", 0))
        vec[12] = min(p_best_dmg / 250.0, 1.0)

        # 4. Opponent Active Dynamics (16..23)
        opp_act = opp.get("active_spot") or opp.get("active_pokemon") or {}
        opp_meta = self.card_db.get_meta(opp_act.get("name", ""))
        opp_max_hp = opp_act.get("max_hp") or opp_meta.get("hp", 100)
        opp_curr_hp = max(0, opp_act.get("current_hp", opp_max_hp))
        opp_energy_count = _get_e_count(opp_act.get("attached_energy", []))

        vec[16] = opp_curr_hp / 340.0
        vec[17] = (opp_curr_hp / max(1, opp_max_hp))
        vec[18] = opp_energy_count / 6.0
        vec[19] = 1.0 if "ex" in opp_act.get("name", "").lower() else 0.0

        opp_best_dmg = 0
        for a in opp_meta.get("attacks", []):
            opp_best_dmg = max(opp_best_dmg, a.get("base_damage", 0))
        vec[20] = min(opp_best_dmg / 250.0, 1.0)

        # Immediate Knockout Potential
        vec[21] = 1.0 if (opp_curr_hp > 0 and p_best_dmg >= opp_curr_hp) else 0.0
        vec[22] = 1.0 if (p_curr_hp > 0 and opp_best_dmg >= p_curr_hp) else 0.0

        # 5. Bench Depth & Reserves (24..31)
        p_bench = player.get("bench", [])
        opp_bench = opp.get("bench", [])
        vec[24] = len(p_bench) / 5.0
        vec[25] = len(opp_bench) / 5.0

        total_p_bench_hp = sum(b.get("current_hp", 70) for b in p_bench)
        total_opp_bench_hp = sum(b.get("current_hp", 70) for b in opp_bench)
        vec[26] = min(total_p_bench_hp / 500.0, 1.0)
        vec[27] = min(total_opp_bench_hp / 500.0, 1.0)

        total_p_energy = p_energy_count + sum(_get_e_count(b.get("attached_energy", [])) for b in p_bench)
        total_opp_energy = opp_energy_count + sum(_get_e_count(b.get("attached_energy", [])) for b in opp_bench)
        vec[28] = min(total_p_energy / 12.0, 1.0)
        vec[29] = min(total_opp_energy / 12.0, 1.0)

        # 6. Turn Flags & Modifiers (32..39)
        vec[32] = 1.0 if turn_flags.get("energy_attached_this_turn", False) else 0.0
        vec[33] = 1.0 if turn_flags.get("supporter_played_this_turn", False) else 0.0
        vec[34] = 1.0 if turn_flags.get("retreated_this_turn", False) else 0.0
        vec[35] = 1.0 if state.get("stadium") else 0.0

        # Discard pile sizes
        vec[36] = min(len(player.get("discard", [])) / 30.0, 1.0)
        vec[37] = min(len(opp.get("discard", [])) / 30.0, 1.0)

        # 7. Strategic Potentials (40..47)
        # Ratio of Player HP to Opponent HP
        tot_p_hp = p_curr_hp + total_p_bench_hp
        tot_opp_hp = opp_curr_hp + total_opp_bench_hp
        vec[40] = float(tot_p_hp / max(1, tot_p_hp + tot_opp_hp))

        # Win condition proximity
        vec[41] = float(p_taken / 6.0)
        vec[42] = float(opp_taken / 6.0)

        # Bench vulnerability: active dead with 0 bench
        vec[43] = 1.0 if len(p_bench) == 0 else 0.0
        vec[44] = 1.0 if len(opp_bench) == 0 else 0.0

        # Hand card type counts (Basic, Evolution, Energy, Trainer)
        hand = player.get("hand", [])
        has_energy = any("energy" in (c.get("name", "") if isinstance(c, dict) else str(c)).lower() for c in hand)
        has_supporter = any(isinstance(c, dict) and "supporter" in [s.lower() for s in c.get("subtypes", [])] for c in hand)
        vec[45] = 1.0 if has_energy else 0.0
        vec[46] = 1.0 if has_supporter else 0.0
        vec[47] = 1.0 if (p_prizes <= 2) else 0.0  # Late-game urgency

        return vec
