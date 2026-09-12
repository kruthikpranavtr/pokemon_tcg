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
        has_evolution = any("stage" in str(c.get("stage") or "").lower() for c in player.get("hand", []) if isinstance(c, dict))
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

    def evaluate_pokemon_as_main(self, candidate_name: str, opp_act_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates a candidate Pokémon's strategic matchup and winning possibility
        if deployed as the active main card against the opponent's active Pokémon.
        Analyzes type weakness (2x multiplier), attack damage, turns to KO, and survivability.
        """
        cand_meta = self.card_db.get_meta(candidate_name)
        cand_hp = int(cand_meta.get("hp", 70) or 70)
        cand_types = cand_meta.get("types", ["Colorless"])
        cand_weaknesses = cand_meta.get("weaknesses", [])

        opp_name = opp_act_state.get("name", "") if isinstance(opp_act_state, dict) else str(opp_act_state)
        opp_meta = self.card_db.get_meta(opp_name)
        opp_hp = int(opp_act_state.get("current_hp", opp_meta.get("hp", 70)) or 70) if isinstance(opp_act_state, dict) else int(opp_meta.get("hp", 70) or 70)
        opp_types = opp_meta.get("types", ["Colorless"])
        opp_weaknesses = opp_meta.get("weaknesses", [])

        # Check if candidate hits opponent weakness
        hits_weakness = False
        for w in opp_weaknesses:
            if isinstance(w, dict) and w.get("type") in cand_types:
                hits_weakness = True
                break

        # Check if opponent hits candidate weakness
        opp_hits_weakness = False
        for w in cand_weaknesses:
            if isinstance(w, dict) and w.get("type") in opp_types:
                opp_hits_weakness = True
                break

        # Calculate candidate damage vs opponent
        attacks = cand_meta.get("attacks", []) or [{"name": f"{candidate_name} Strike", "base_damage": 50, "cost": cand_types}]
        best_atk = attacks[0]
        base_dmg = int(best_atk.get("base_damage", 50) or 50)
        final_dmg = base_dmg * (2 if hits_weakness else 1)

        is_1hit_ko = final_dmg >= opp_hp and opp_hp > 0
        turns_to_ko = 1 if is_1hit_ko else max(2, int(np.ceil(opp_hp / max(1, final_dmg))))

        # Opponent counterattack threat
        opp_attacks = opp_meta.get("attacks", []) or [{"name": "Strike", "base_damage": 40, "cost": opp_types}]
        opp_base_dmg = int(opp_attacks[0].get("base_damage", 40) or 40)
        opp_final_dmg = opp_base_dmg * (2 if opp_hits_weakness else 1)
        cand_survives = cand_hp > opp_final_dmg

        # Win probability formula
        win_prob = 50
        if hits_weakness:
            win_prob += 25
        if is_1hit_ko:
            win_prob += 18
        elif turns_to_ko == 2:
            win_prob += 8

        if cand_hp >= opp_hp:
            win_prob += 8
        if cand_survives:
            win_prob += 8
        else:
            win_prob -= 12

        if opp_hits_weakness:
            win_prob -= 20

        win_prob = max(15, min(98, win_prob))

        if hits_weakness:
            summary = f"Hits opponent weakness (2x) for {final_dmg} DMG ({'1-Hit KO' if is_1hit_ko else f'{turns_to_ko}-Turn KO'})"
        else:
            summary = f"Deals {final_dmg} DMG ({turns_to_ko}-Turn KO, {cand_hp} HP)"

        return {
            "name": candidate_name,
            "hp": cand_hp,
            "types": cand_types,
            "best_attack": best_atk.get("name"),
            "expected_damage": final_dmg,
            "hits_weakness": hits_weakness,
            "opp_hits_weakness": opp_hits_weakness,
            "is_1hit_ko": is_1hit_ko,
            "turns_to_ko": turns_to_ko,
            "cand_survives": cand_survives,
            "win_probability_val": win_prob,
            "win_probability_pct": f"{win_prob}%",
            "matchup_summary": summary
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

        hand_card_names = [str(c.get("name") or c.get("card_name") or c.get("card_id") or "") if isinstance(c, dict) else str(c or "") for c in hand]
        hand_card_names = [c for c in hand_card_names if c]
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

        # 4. Hand Bench Deployment with Matchup & Weakness Evaluation
        benched_candidate_name = None
        if len(p_bench) < 3:
            basic_cards = [c for c in hand_card_names if self.card_db.is_basic_pokemon(c) and c != evo_card]
            if basic_cards:
                evals = [self.evaluate_pokemon_as_main(c, opp_act) for c in basic_cards]
                evals.sort(key=lambda x: x["win_probability_val"], reverse=True)
                best_cand = evals[0]
                benched_candidate_name = best_cand["name"]

                route_steps.append({
                    "step": current_step,
                    "phase": "Hand Bench Power (Weakness Analysis)",
                    "action": f"Deploy Best Matchup [{best_cand['name']}] from hand to Bench ({best_cand['win_probability_pct']} Win Possibility as Main)",
                    "action_type": "BENCH_POKEMON",
                    "card_name": best_cand["name"],
                    "winning_possibility": best_cand["win_probability_pct"],
                    "weakness_exploited": best_cand["hits_weakness"],
                    "damage": 0,
                    "prizes_gained": 0,
                    "remaining_needed": p_prizes_needed,
                    "strategic_impact": f"Evaluated hand Pokémon: [{best_cand['name']}] achieves {best_cand['win_probability_pct']} win possibility as main card ({best_cand['matchup_summary']}). Establishing on bench."
                })
                current_step += 1

        # 5. Tactical Switch / Escape Rope
        switch_card = next((c for c in hand_card_names if any(s in c.lower() for s in ("switch", "rope", "escape"))), None)
        if switch_card:
            act_eval = self.evaluate_pokemon_as_main(player_act.get("name", ""), opp_act)
            available_bench = [b.get("name") if isinstance(b, dict) else str(b) for b in p_bench]
            if benched_candidate_name and benched_candidate_name not in available_bench:
                available_bench.append(benched_candidate_name)

            if available_bench:
                bench_evals = [self.evaluate_pokemon_as_main(b, opp_act) for b in available_bench]
                bench_evals.sort(key=lambda x: x["win_probability_val"], reverse=True)
                best_bench = bench_evals[0]

                if (best_bench["win_probability_val"] > act_eval["win_probability_val"]) or (best_bench["hits_weakness"] and not act_eval["hits_weakness"]):
                    route_steps.append({
                        "step": current_step,
                        "phase": "Tactical Switch (Weakness Exploit)",
                        "action": f"Play [{switch_card}] from hand to promote [{best_bench['name']}] to Active Spot ({best_bench['win_probability_pct']} Win Possibility)",
                        "action_type": "PLAY_ITEM",
                        "card_name": switch_card,
                        "target_pokemon": best_bench["name"],
                        "damage": 0,
                        "prizes_gained": 0,
                        "remaining_needed": p_prizes_needed,
                        "strategic_impact": f"Switches active spot from [{player_act.get('name')}] ({act_eval['win_probability_pct']}) to [{best_bench['name']}] ({best_bench['win_probability_pct']}) to exploit opponent weakness and maximize win probability."
                    })
                    current_step += 1
                    player_act = {"name": best_bench["name"], "current_hp": best_bench["hp"], "max_hp": best_bench["hp"]}
                    p_act_hp = best_bench["hp"]

        # 6. Supporter Disruption (Weakness Target)
        boss_card = next((c for c in hand_card_names if any(b in c.lower() for b in ("boss", "gust", "catcher", "serena"))), None)
        if boss_card and not supporter_used and opp_bench:
            p_meta = self.card_db.get_meta(player_act.get("name", ""))
            p_types = p_meta.get("types", ["Colorless"])
            target_opp = None
            for ob in opp_bench:
                ob_name = ob.get("name") if isinstance(ob, dict) else str(ob)
                ob_meta = self.card_db.get_meta(ob_name)
                ob_weak = ob_meta.get("weaknesses", [])
                if any(w.get("type") in p_types for w in ob_weak if isinstance(w, dict)):
                    target_opp = ob
                    break
            if not target_opp:
                target_opp = min(opp_bench, key=lambda b: (b.get("current_hp", 70) if isinstance(b, dict) else 70))

            target_opp_name = target_opp.get("name") if isinstance(target_opp, dict) else str(target_opp)
            route_steps.append({
                "step": current_step,
                "phase": "Supporter Disruption (Weakness Target)",
                "action": f"Play [{boss_card}] to drag opponent's vulnerable [{target_opp_name}] into Active Spot",
                "action_type": "PLAY_SUPPORTER",
                "card_name": boss_card,
                "target_pokemon": target_opp_name,
                "damage": 0,
                "prizes_gained": 0,
                "remaining_needed": p_prizes_needed,
                "strategic_impact": f"Gusts opponent's [{target_opp_name}] into active spot to exploit weakness and secure prize knockout."
            })
            current_step += 1
            supporter_used = True
            opp_act = target_opp if isinstance(target_opp, dict) else {"name": target_opp_name, "current_hp": 70}
            opp_hp = int(opp_act.get("current_hp", 70) or 70)

        # 7. Hand Energy Power (1/turn rule)
        energy_card = next((c for c in hand_card_names if "energy" in c.lower()), None)
        if not turn_energy_used and (energy_card or best_action.get("action_type") == "ATTACH_ENERGY"):
            target_pkmn = player_act.get('name', 'Active')
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

        # 8. Terminal Offensive Strike for Current Turn
        p_active_meta = self.card_db.get_meta(player_act.get("name", ""))
        attacks = p_active_meta.get("attacks", [])
        top_atk = attacks[0] if attacks else {"name": "Strike", "base_damage": 40}
        act_type = best_action.get("action_type")
        if act_type == "ATTACK" and player_act.get("name") == (state.get("player", {}).get("active_spot", {}).get("name")):
            atk_name = best_action.get("attack_name", top_atk.get("name", "Strike"))
            base_dmg = int(best_action.get("base_damage", top_atk.get("base_damage", 40)) or 40)
        else:
            atk_name = top_atk.get("name", f"{player_act.get('name')} Strike")
            base_dmg = int(top_atk.get("base_damage", 40) or 40)

        p_types = p_active_meta.get("types", ["Colorless"])
        opp_meta = self.card_db.get_meta(opp_act.get("name", ""))
        opp_weak = opp_meta.get("weaknesses", [])
        is_weak = any(w.get("type") in p_types for w in opp_weak if isinstance(w, dict))
        strike_dmg = base_dmg * (2 if is_weak else 1)

        is_lethal = strike_dmg >= opp_hp and opp_hp > 0
        prizes = opp_prizes_val if is_lethal else 0
        prizes_mapped += prizes

        route_steps.append({
            "step": current_step,
            "phase": "Turn 1 Offensive Strike",
            "action": f"Strike active [{opp_act.get('name')}] with [{atk_name}] for {strike_dmg} DMG{' (WEAKNESS x2!)' if is_weak else ''}",
            "action_type": "ATTACK",
            "attack_name": atk_name,
            "damage": strike_dmg,
            "prizes_gained": prizes,
            "remaining_needed": max(0, p_prizes_needed - prizes_mapped),
            "strategic_impact": f"Secures lethal knockout on [{opp_act.get('name')}]!" if is_lethal else f"Deals {strike_dmg} DMG to [{opp_act.get('name')}] to set up knockout."
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
                "action_type": "ATTACK",
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
                "action_type": "ATTACK",
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
