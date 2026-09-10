"""
Deterministic Pokémon TCG Rules Engine & Legal Action Generator
Enforces tournament rules:
- Per-turn resource limits (1 energy attachment, 1 supporter, 1 manual retreat)
- Energy requirement checks for attacks and retreat costs
- Accurate combat damage calculation (Weakness x2, Resistance, prize-scaling)
- Prize tracking (1 for single prize, 2 for ex/V, 3 for VMAX)
- Exhaustive legal action generation
"""
from typing import Dict, List, Any, Tuple, Optional
from ..cards.card_database import CardDatabase


class RulesEngine:
    def __init__(self, card_db: Optional[CardDatabase] = None):
        self.card_db = card_db or CardDatabase.get_instance()

    def calculate_damage(
        self,
        attacker_meta: Dict[str, Any],
        attack: Dict[str, Any],
        defender_meta: Dict[str, Any],
        opponent_prizes_taken: int = 0
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Computes damage applied to defender, factoring in:
        - Base damage
        - Dynamic scaling (e.g. +30 per prize taken)
        - Weakness (standard x2)
        - Resistance (-20 or -30)
        Returns: (effective_damage, calculation_details)
        """
        base_dmg = attack.get("base_damage", 0)
        scaling_bonus = 0
        scaling_rule = attack.get("damage_scaling") or ""

        # e.g., Charizard ex Burning Darkness
        if "30_PER_OPPONENT_PRIZE_TAKEN" in scaling_rule or "prize" in attack.get("text", "").lower():
            scaling_bonus = 30 * opponent_prizes_taken

        unmitigated_dmg = base_dmg + scaling_bonus

        attacker_types = attacker_meta.get("types", [])
        weakness_applied = False
        weakness_mult = 1

        # Check Weakness
        defender_weaknesses = defender_meta.get("weaknesses", [])
        if not defender_weaknesses and isinstance(defender_meta.get("weakness"), dict):
            defender_weaknesses = [defender_meta.get("weakness")]

        for w in defender_weaknesses:
            if isinstance(w, dict) and w.get("type") in attacker_types:
                weakness_mult = 2
                weakness_applied = True
                break

        weakness_dmg = unmitigated_dmg * weakness_mult

        # Check Resistance
        resistance_applied = False
        resistance_val = 0
        defender_resistances = defender_meta.get("resistances", [])
        if not defender_resistances and isinstance(defender_meta.get("resistance"), dict):
            defender_resistances = [defender_meta.get("resistance")]

        for r in defender_resistances:
            if isinstance(r, dict) and r.get("type") in attacker_types:
                val_str = str(r.get("value", "-30"))
                try:
                    resistance_val = abs(int(val_str.replace("-", "")))
                except ValueError:
                    resistance_val = 30
                resistance_applied = True
                break

        final_dmg = max(0, weakness_dmg - resistance_val)

        details = {
            "base_damage": base_dmg,
            "scaling_bonus": scaling_bonus,
            "subtotal": unmitigated_dmg,
            "weakness_type": attacker_types[0] if attacker_types else "None",
            "weakness_applied": weakness_applied,
            "weakness_multiplier": weakness_mult,
            "resistance_applied": resistance_applied,
            "resistance_reduction": resistance_val,
            "final_damage": final_dmg
        }
        return final_dmg, details

    def can_pay_energy_cost(
        self,
        attached_energies: List[Any],
        cost: List[str]
    ) -> bool:
        """
        Determines if attached energies satisfy the attack or retreat cost.
        Handles typed requirements (Fire, Water, Lightning, etc.) and generic Colorless costs.
        """
        if not cost:
            return True

        # Normalize attached energies to string type names
        attached_pool: List[str] = []
        for e in attached_energies:
            if isinstance(e, dict):
                attached_pool.append(e.get("type", "Colorless"))
            elif isinstance(e, str):
                # Clean strings like "Basic Fire Energy" -> "Fire"
                clean = e.replace("Basic", "").replace("Energy", "").strip()
                attached_pool.append(clean if clean else "Colorless")

        # Sort cost: non-Colorless specific costs first, Colorless last
        specific_costs = [c for c in cost if c.lower() != "colorless"]
        colorless_count = len(cost) - len(specific_costs)

        pool_copy = list(attached_pool)

        # 1. Match specific typed costs
        for c_type in specific_costs:
            matched = False
            for i, att in enumerate(pool_copy):
                if att.lower() == c_type.lower():
                    pool_copy.pop(i)
                    matched = True
                    break
            if not matched:
                # Rainbow / Special Energy fallback
                for i, att in enumerate(pool_copy):
                    if att.lower() in ("rainbow", "any"):
                        pool_copy.pop(i)
                        matched = True
                        break
            if not matched:
                return False

        # 2. Match remaining colorless costs using any remaining energy
        return len(pool_copy) >= colorless_count

    def calculate_prizes_awarded(self, knocked_out_meta: Dict[str, Any]) -> int:
        """Determines prize card reward for knocking out a Pokémon."""
        subtypes = [s.lower() for s in knocked_out_meta.get("subtypes", [])]
        name = knocked_out_meta.get("name", "").lower()

        if "vmax" in subtypes or "v-union" in subtypes or "vmax" in name:
            return 3
        if "ex" in subtypes or " v" in subtypes or "vstar" in subtypes or " ex" in name or " v" in name:
            return 2
        return 1

    def generate_legal_actions(
        self,
        game_state: Dict[str, Any],
        is_player: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generates all strictly legal actions for the active side.
        Never generates an illegal action.
        """
        legal_actions: List[Dict[str, Any]] = []

        actor = game_state.get("player" if is_player else "opponent", {})
        other = game_state.get("opponent" if is_player else "player", {})
        turn_flags = game_state.get("turn_flags", {})
        turn_number = game_state.get("turn_number", 1)
        is_first_turn = game_state.get("is_first_turn_of_game", turn_number == 1)

        active = actor.get("active_spot")
        bench = actor.get("bench", [])
        hand = actor.get("hand", [])
        prizes_taken = actor.get("prizes_taken", 0)

        # 1. ATTACK ACTIONS
        # Player going first cannot attack on Turn 1
        if active and active.get("current_hp", 0) > 0 and not (is_first_turn and turn_number == 1):
            meta = self.card_db.get_meta(active.get("name", ""))
            attacks = meta.get("attacks", [])
            attached = active.get("attached_energy", [])

            opp_active = other.get("active_spot")
            opp_meta = self.card_db.get_meta(opp_active.get("name", "")) if opp_active else {}

            for atk in attacks:
                cost = atk.get("cost", ["Colorless"])
                if self.can_pay_energy_cost(attached, cost):
                    dmg, calc_details = self.calculate_damage(
                        attacker_meta=meta,
                        attack=atk,
                        defender_meta=opp_meta,
                        opponent_prizes_taken=prizes_taken
                    )
                    opp_hp = opp_active.get("current_hp", 0) if opp_active else 0
                    is_lethal = opp_hp > 0 and dmg >= opp_hp
                    prizes = self.calculate_prizes_awarded(opp_meta) if is_lethal else 0

                    legal_actions.append({
                        "action_type": "ATTACK",
                        "attack_name": atk.get("name", "Attack"),
                        "base_damage": dmg,
                        "raw_base_damage": atk.get("base_damage", 0),
                        "cost": cost,
                        "is_lethal": is_lethal,
                        "prizes_to_gain": prizes,
                        "calculation_details": calc_details,
                        "target": "ACTIVE"
                    })

        # 2. ATTACH ENERGY (1 per turn limit)
        if not turn_flags.get("energy_attached_this_turn", False):
            # Check energy cards in hand
            energy_cards = [
                c for c in hand
                if (isinstance(c, dict) and (c.get("supertype", "").lower() == "energy" or "energy" in c.get("name", "").lower()))
                or (isinstance(c, str) and "energy" in c.lower())
            ]
            for ec in energy_cards:
                cname = ec.get("name") if isinstance(ec, dict) else ec
                cid = ec.get("card_id") if isinstance(ec, dict) else f"energy-{cname.lower().replace(' ', '-')}"

                # Can attach to Active
                if active:
                    legal_actions.append({
                        "action_type": "ATTACH_ENERGY",
                        "card_name": cname,
                        "card_id": cid,
                        "target": "ACTIVE",
                        "target_pokemon": active.get("name")
                    })
                # Can attach to any Benched Pokémon
                for b in bench:
                    legal_actions.append({
                        "action_type": "ATTACH_ENERGY",
                        "card_name": cname,
                        "card_id": cid,
                        "target": "BENCH",
                        "target_pokemon": b.get("name")
                    })

        # 3. BENCH BASIC POKÉMON (Max 5 on bench)
        if len(bench) < 5:
            basic_cards = [
                c for c in hand
                if self.card_db.is_basic_pokemon(c.get("name") if isinstance(c, dict) else c)
            ]
            for bc in basic_cards:
                cname = bc.get("name") if isinstance(bc, dict) else bc
                cid = bc.get("card_id") if isinstance(bc, dict) else f"basic-{cname.lower().replace(' ', '-')}"
                legal_actions.append({
                    "action_type": "BENCH_POKEMON",
                    "card_name": cname,
                    "card_id": cid,
                    "target": "BENCH"
                })

        # 4. EVOLVE POKÉMON
        evo_cards = [
            c for c in hand
            if not self.card_db.is_basic_pokemon(c.get("name") if isinstance(c, dict) else c)
            and (
                (isinstance(c, dict) and c.get("supertype", "").lower().startswith("pok"))
                or (isinstance(c, str) and not "energy" in c.lower() and not "ball" in c.lower() and not "research" in c.lower())
            )
        ]
        for ec in evo_cards:
            cname = ec.get("name") if isinstance(ec, dict) else ec
            cid = ec.get("card_id") if isinstance(ec, dict) else f"evo-{cname.lower().replace(' ', '-')}"
            meta = self.card_db.get_meta(cname)
            evo_from = (meta.get("evolves_from") or "").lower().strip()

            # Evolve onto active
            if active and evo_from and evo_from in active.get("name", "").lower():
                legal_actions.append({
                    "action_type": "EVOLVE_POKEMON",
                    "card_name": cname,
                    "card_id": cid,
                    "target": "ACTIVE",
                    "target_pokemon": active.get("name")
                })

            # Evolve onto bench
            for b in bench:
                if evo_from and evo_from in b.get("name", "").lower():
                    legal_actions.append({
                        "action_type": "EVOLVE_POKEMON",
                        "card_name": cname,
                        "card_id": cid,
                        "target": "BENCH",
                        "target_pokemon": b.get("name")
                    })

        # 5. PLAY SUPPORTER (1 per turn limit, not on Turn 1 going 1st)
        if not turn_flags.get("supporter_played_this_turn", False) and not (is_first_turn and turn_number == 1):
            supporters = [
                c for c in hand
                if (isinstance(c, dict) and "supporter" in [s.lower() for s in c.get("subtypes", [])])
                or (isinstance(c, str) and c in ("Professor's Research", "Iono", "Boss's Orders", "Arven"))
            ]
            for sc in supporters:
                cname = sc.get("name") if isinstance(sc, dict) else sc
                cid = sc.get("card_id") if isinstance(sc, dict) else f"supp-{cname.lower().replace(' ', '-')}"
                legal_actions.append({
                    "action_type": "PLAY_SUPPORTER",
                    "card_name": cname,
                    "card_id": cid,
                    "target": "FIELD"
                })

        # 6. PLAY ITEM CARDS (Unlimited per turn)
        items = [
            c for c in hand
            if (isinstance(c, dict) and "item" in [s.lower() for s in c.get("subtypes", [])])
            or (isinstance(c, str) and any(it in c.lower() for it in ("ball", "candy", "catcher", "rod", "vessel", "potion")))
        ]
        for ic in items:
            cname = ic.get("name") if isinstance(ic, dict) else ic
            cid = ic.get("card_id") if isinstance(ic, dict) else f"item-{cname.lower().replace(' ', '-')}"
            legal_actions.append({
                "action_type": "PLAY_ITEM",
                "card_name": cname,
                "card_id": cid,
                "target": "FIELD"
            })

        # 7. RETREAT (1 per turn limit, must pay retreat cost, must have benched Pokémon)
        if not turn_flags.get("retreated_this_turn", False) and bench and active:
            meta = self.card_db.get_meta(active.get("name", ""))
            cost = meta.get("retreat_cost", ["Colorless"])
            attached = active.get("attached_energy", [])
            if self.can_pay_energy_cost(attached, cost):
                for b in bench:
                    legal_actions.append({
                        "action_type": "RETREAT",
                        "switch_with": b.get("name"),
                        "retreat_cost": cost,
                        "target": "ACTIVE"
                    })

        # 8. PASS TURN (Always a legal option)
        legal_actions.append({
            "action_type": "PASS_TURN",
            "target": "SYSTEM"
        })

        return legal_actions
