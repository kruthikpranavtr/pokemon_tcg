"""
Comprehensive Game Evaluation Function & Winning Route Analyzer
Calculates:
V(S) = w1*WinProb + w2*PrizeAdv + w3*BoardAdv + w4*HPAdv + w5*EnergyAdv + w6*HandAdv + w7*SetupPot + w8*Tempo - w9*Risk - w10*OppThreat
EV(A) = sum P(S_i|I) * V(S_i, A)
Computes "The Winning Route" multi-turn prize sequence to reach 6 prizes.
"""
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
from ..cards.card_database import CardDatabase


class EvaluationWeights:
    def __init__(
        self,
        w1_win_prob: float = 0.30,
        w2_prize_adv: float = 0.20,
        w3_board_adv: float = 0.10,
        w4_hp_adv: float = 0.10,
        w5_energy_adv: float = 0.08,
        w6_hand_adv: float = 0.06,
        w7_setup_pot: float = 0.06,
        w8_tempo: float = 0.05,
        w9_risk: float = 0.08,
        w10_opp_threat: float = 0.10
    ):
        self.w1 = w1_win_prob
        self.w2 = w2_prize_adv
        self.w3 = w3_board_adv
        self.w4 = w4_hp_adv
        self.w5 = w5_energy_adv
        self.w6 = w6_hand_adv
        self.w7 = w7_setup_pot
        self.w8 = w8_tempo
        self.w9 = w9_risk
        self.w10 = w10_opp_threat

    def to_dict(self) -> Dict[str, float]:
        return {
            "w1_win_prob": self.w1,
            "w2_prize_adv": self.w2,
            "w3_board_adv": self.w3,
            "w4_hp_adv": self.w4,
            "w5_energy_adv": self.w5,
            "w6_hand_adv": self.w6,
            "w7_setup_pot": self.w7,
            "w8_tempo": self.w8,
            "w9_risk": self.w9,
            "w10_opp_threat": self.w10
        }


class PositionEvaluator:
    def __init__(
        self,
        weights: Optional[EvaluationWeights] = None,
        card_db: Optional[CardDatabase] = None
    ):
        self.weights = weights or EvaluationWeights()
        self.card_db = card_db or CardDatabase.get_instance()

    def evaluate_position(
        self,
        state: Dict[str, Any],
        base_win_prob: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Computes the multi-factor heuristic evaluation score V(S) and individual components.
        Score normalized approximately in [0, 1].
        """
        player = state.get("player", {})
        opp = state.get("opponent", {})

        p_prizes = player.get("prizes_remaining", 6)
        opp_prizes = opp.get("prizes_remaining", 6)
        p_taken = player.get("prizes_taken", 6 - p_prizes)
        opp_taken = opp.get("prizes_taken", 6 - opp_prizes)

        # 1. Win Probability
        if p_prizes <= 0:
            win_prob = 1.0
        elif opp_prizes <= 0:
            win_prob = 0.0
        elif base_win_prob is not None:
            win_prob = base_win_prob
        else:
            # Baseline sigmoid prize difference
            prize_diff = p_taken - opp_taken
            win_prob = 1.0 / (1.0 + np.exp(-0.8 * prize_diff))

        # 2. Prize Advantage in [0, 1]
        prize_adv = max(0.0, min(1.0, 0.5 + (p_taken - opp_taken) / 12.0))

        # 3. Board Advantage (Active & Bench Presence)
        p_bench_count = len(player.get("bench", []))
        opp_bench_count = len(opp.get("bench", []))
        board_adv = max(0.0, min(1.0, 0.5 + (p_bench_count - opp_bench_count) / 10.0))

        # 4. HP Advantage
        def _e_cnt(x):
            return len(x) if isinstance(x, list) else (int(x) if isinstance(x, (int, float)) else 0)

        p_act = player.get("active_spot") or player.get("active_pokemon") or {}
        opp_act = opp.get("active_spot") or opp.get("active_pokemon") or {}
        p_tot_hp = p_act.get("current_hp", 0) + sum(b.get("current_hp", 0) for b in player.get("bench", []))
        opp_tot_hp = opp_act.get("current_hp", 0) + sum(b.get("current_hp", 0) for b in opp.get("bench", []))
        hp_adv = p_tot_hp / max(1, p_tot_hp + opp_tot_hp)

        # 5. Energy Advantage
        p_tot_energy = _e_cnt(p_act.get("attached_energy", [])) + sum(_e_cnt(b.get("attached_energy", [])) for b in player.get("bench", []))
        opp_tot_energy = _e_cnt(opp_act.get("attached_energy", [])) + sum(_e_cnt(b.get("attached_energy", [])) for b in opp.get("bench", []))
        energy_adv = max(0.0, min(1.0, 0.5 + (p_tot_energy - opp_tot_energy) / 10.0))

        # 6. Hand Advantage
        p_hand_size = len(player.get("hand", []))
        opp_hand_size = opp.get("hand_count", 5)
        hand_adv = max(0.0, min(1.0, 0.5 + (p_hand_size - opp_hand_size) / 14.0))

        # 7. Setup Potential
        has_evolution = any("stage" in (c.get("stage", "") if isinstance(c, dict) else "").lower() for c in player.get("hand", []))
        setup_pot = 0.8 if has_evolution and p_bench_count >= 2 else (0.5 if p_bench_count >= 1 else 0.2)

        # 8. Tempo
        is_opp_active_low = opp_act.get("current_hp", 100) <= 60
        tempo = 0.85 if is_opp_active_low else 0.5

        # 9. Risk (Vulnerability to sudden knockout or 0 bench)
        p_act_hp = p_act.get("current_hp", 100)
        risk = 0.8 if (p_act_hp <= 50 and p_bench_count == 0) else (0.4 if p_act_hp <= 50 else 0.15)

        # 10. Opponent Threat
        opp_energy = _e_cnt(opp_act.get("attached_energy", []))
        opp_threat = 0.75 if opp_energy >= 2 else 0.35

        w = self.weights
        total_v = (
            w.w1 * win_prob
            + w.w2 * prize_adv
            + w.w3 * board_adv
            + w.w4 * hp_adv
            + w.w5 * energy_adv
            + w.w6 * hand_adv
            + w.w7 * setup_pot
            + w.w8 * tempo
            - w.w9 * risk
            - w.w10 * opp_threat
        )
        total_v = max(0.0, min(1.0, total_v))

        return {
            "position_value": round(total_v, 4),
            "win_probability": round(win_prob, 4),
            "prize_advantage": round(prize_adv, 4),
            "board_advantage": round(board_adv, 4),
            "hp_advantage": round(hp_adv, 4),
            "energy_advantage": round(energy_adv, 4),
            "hand_advantage": round(hand_adv, 4),
            "setup_potential": round(setup_pot, 4),
            "tempo": round(tempo, 4),
            "risk": round(risk, 4),
            "opponent_threat": round(opp_threat, 4)
        }

    def compute_winning_route(
        self,
        state: Dict[str, Any],
        best_action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synthesizes the optimal mathematical path to victory ("The Winning Route").
        Maps out prize acquisition sequence, required knockouts, and turn timeline.
        """
        player = state.get("player", {})
        opp = state.get("opponent", {})

        p_prizes_needed = player.get("prizes_remaining", 6)
        player_act = player.get("active_pokemon") or player.get("active_spot") or {}
        opp_act = opp.get("active_pokemon") or opp.get("active_spot") or {}
        opp_hp = opp_act.get("current_hp", 100)
        opp_prizes_val = 2 if "ex" in opp_act.get("name", "").lower() else 1
        opp_bench = opp.get("bench", [])

        route_steps = []
        prizes_mapped = 0
        current_step = 1

        # Extract hand cards and state resources
        hand = player.get("hand", [])
        turn_flags = state.get("turn_flags", {})
        p_bench = player.get("bench", [])
        p_act_hp = player_act.get("current_hp", 70)
        p_act_max_hp = player_act.get("max_hp", 70)

        hand_card_names = [c.get("name") if isinstance(c, dict) else str(c) for c in hand]
        turn_energy_used = turn_flags.get("energy_attached_this_turn", False)
        supporter_used = turn_flags.get("supporter_played_this_turn", False)

        # 1. Hand Item / Healing Power: If holding Potion and active is damaged
        potion_card = next((c for c in hand_card_names if "potion" in c.lower()), None)
        if potion_card and p_act_hp < p_act_max_hp:
            route_steps.append({
                "step": current_step,
                "phase": "Hand Item Power",
                "action": f"Play [{potion_card}] from hand to heal active [{player_act.get('name')}]",
                "action_type": "PLAY_ITEM",
                "card_name": potion_card,
                "damage": 0,
                "prizes_gained": 0,
                "remaining_needed": p_prizes_needed,
                "strategic_impact": f"Restores HP on [{player_act.get('name')}] ({p_act_hp}/{p_act_max_hp} HP) to preserve field presence."
            })
            current_step += 1

        # 2. Hand Draw/Search Power: If holding draw or search trainer
        draw_card = next((c for c in hand_card_names if any(d in c.lower() for d in ("research", "iono", "ball", "cheren", "draw"))), None)
        if draw_card:
            is_supp = any(s in draw_card.lower() for s in ("research", "iono", "cheren", "supporter"))
            if not is_supp or not supporter_used:
                route_steps.append({
                    "step": current_step,
                    "phase": "Hand Draw/Search Power",
                    "action": f"Play [{draw_card}] from hand to draw resources",
                    "action_type": "PLAY_SUPPORTER" if is_supp else "PLAY_ITEM",
                    "card_name": draw_card,
                    "damage": 0,
                    "prizes_gained": 0,
                    "remaining_needed": p_prizes_needed,
                    "strategic_impact": "Accelerates deck searching and hand card advantage."
                })
                current_step += 1
                if is_supp:
                    supporter_used = True

        # 3. Hand Evolution Power: If holding evolution card that matches in play
        evo_card = None
        evo_target_name = None
        for c in hand_card_names:
            meta = self.card_db.get_meta(c)
            evo_from = (meta.get("evolves_from") or "").lower().strip()
            if evo_from:
                if evo_from in player_act.get("name", "").lower():
                    evo_card = c
                    evo_target_name = player_act.get("name")
                    break
                for b in p_bench:
                    b_name = b.get("name") if isinstance(b, dict) else str(b)
                    if evo_from in b_name.lower():
                        evo_card = c
                        evo_target_name = b_name
                        break
            if evo_card:
                break

        if evo_card:
            route_steps.append({
                "step": current_step,
                "phase": "Hand Evolution Power",
                "action": f"Evolve [{evo_target_name}] into [{evo_card}] from hand",
                "action_type": "EVOLVE_POKEMON",
                "card_name": evo_card,
                "target": "ACTIVE" if evo_target_name == player_act.get("name") else "BENCH",
                "damage": 0,
                "prizes_gained": 0,
                "remaining_needed": p_prizes_needed,
                "strategic_impact": f"Evolves [{evo_target_name}] for increased max HP and attack tier."
            })
            current_step += 1

        # 4. Hand Bench Deployment: If holding basic Pokémon and bench < 3
        if len(p_bench) < 3:
            basic_card = next((c for c in hand_card_names if self.card_db.is_basic_pokemon(c) and c != evo_card), None)
            if basic_card:
                route_steps.append({
                    "step": current_step,
                    "phase": "Hand Bench Power",
                    "action": f"Deploy Basic [{basic_card}] from hand to Bench",
                    "action_type": "BENCH_POKEMON",
                    "card_name": basic_card,
                    "damage": 0,
                    "prizes_gained": 0,
                    "remaining_needed": p_prizes_needed,
                    "strategic_impact": "Establishes reserve attacker to prevent bench-out loss."
                })
                current_step += 1

        # 5. Hand Energy Power (1/turn rule)
        energy_card = next((c for c in hand_card_names if "energy" in c.lower()), None)
        if not turn_energy_used and (energy_card or best_action.get("action_type") == "ATTACH_ENERGY"):
            target_pkmn = best_action.get('target_pokemon') or player_act.get('name', 'Active')
            e_name = energy_card or best_action.get('card_name') or "Basic Energy"
            route_steps.append({
                "step": current_step,
                "phase": "Energy Sequencing (1/turn)",
                "action": f"Attach [{e_name}] from hand to [{target_pkmn}]",
                "action_type": "ATTACH_ENERGY",
                "card_name": e_name,
                "damage": 0,
                "prizes_gained": 0,
                "remaining_needed": p_prizes_needed,
                "strategic_impact": "Powers attack cost within the 1-attachment per turn rule."
            })
            current_step += 1

        # 6. Terminal Offensive Strike for Current Turn
        p_active_meta = self.card_db.get_meta(player_act.get("name", ""))
        attacks = p_active_meta.get("attacks", [])
        top_atk = attacks[0] if attacks else {"name": "Strike", "base_damage": 40}
        act_type = best_action.get("action_type")
        if act_type == "ATTACK":
            atk_name = best_action.get("attack_name", top_atk.get("name", "Strike"))
            base_dmg = int(best_action.get("base_damage", top_atk.get("base_damage", 40)) or 40)
        else:
            atk_name = top_atk.get("name", "Strike")
            base_dmg = int(top_atk.get("base_damage", 40) or 40)

        is_lethal = base_dmg >= opp_hp and opp_hp > 0
        prizes = opp_prizes_val if is_lethal else 0
        prizes_mapped += prizes

        route_steps.append({
            "step": current_step,
            "phase": "Turn 1 Offensive Strike",
            "action": f"Strike active [{opp_act.get('name')}] with [{atk_name}] for {base_dmg} DMG",
            "action_type": "ATTACK",
            "attack_name": atk_name,
            "damage": base_dmg,
            "prizes_gained": prizes,
            "remaining_needed": max(0, p_prizes_needed - prizes_mapped),
            "strategic_impact": "Secures lethal knockout and prize pickup." if is_lethal else "Pressures active Pokémon to set up lethal prize extraction next turn."
        })
        current_step += 1


        # Step 2: Next turn follow-up knockout
        if prizes_mapped < p_prizes_needed:
            target_bench = opp_bench[0] if opp_bench else {"name": "Opponent Benched Pokémon", "current_hp": 70}
            target_prizes = 2 if "ex" in target_bench.get("name", "").lower() else 1
            prizes_mapped += target_prizes

            route_steps.append({
                "step": current_step,
                "phase": "Turn 2 Follow-up",
                "action": f"Target [{target_bench.get('name')}] for prize pickup",
                "damage": 120,
                "prizes_gained": target_prizes,
                "remaining_needed": max(0, p_prizes_needed - prizes_mapped),
                "strategic_impact": "Capitalizes on opponent tempo loss to extend prize lead."
            })
            current_step += 1

        # Step 3: Game-Winning Terminal Knockout
        if prizes_mapped < p_prizes_needed:
            final_prizes = max(1, p_prizes_needed - prizes_mapped)
            route_steps.append({
                "step": current_step,
                "phase": "Turn 3 Game-Winning Closer",
                "action": f"Execute final Boss's Orders / Heavy Attack to claim final {final_prizes} Prize(s)",
                "damage": 180,
                "prizes_gained": final_prizes,
                "remaining_needed": 0,
                "strategic_impact": "Takes final prize cards to trigger mathematical tournament victory."
            })

        turns_to_win = len(route_steps)
        return {
            "summary": f"Winning Route identified: {turns_to_win}-turn prize sequencing path to tournament victory.",
            "estimated_turns_to_victory": turns_to_win,
            "target_prizes_total": p_prizes_needed,
            "steps": route_steps,
            "key_condition": "Maintain manual energy tempo and protect bench attacker from lethal counter-attack."
        }
