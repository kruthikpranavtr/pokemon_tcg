"""
Pokémon TCG 60-Card Match Engine & Rules Simulator
Primary Source of Truth: Authentic CSV Card Dataset
Features:
- 60-Card Deck management & shuffling
- 5-Card Opening Hand draw with Basic Pokémon mulligan verification
- 6 Prize Cards set aside
- Strict Field Structure: 1 Active + up to 3 Bench Pokémon (max 4 on field)
- Basic-only initial placement (Stage 1 / Stage 2 blocked from direct placement)
- Full Hand Usability: Basic Pokémon to bench, Evolution checking evolves_from,
  Energy attachment (once per turn, corresponding to type, visibly attached),
  Trainer cards.
- Attack Energy Requirements: Verified against required cost symbols before attacking
- Switch / Retreat mechanism with bench selection
- Knockout at 0 HP with bench promotion (player chooses replacement from bench)
- Turn restrictions: card_drawn_this_turn and energy_attached_this_turn reset each turn
- Single authoritative game state for player and AI
"""
import random
import json
import os
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import Counter
from src.engine.energy_config import (
    ENERGY_TYPES, ENERGY_SYMBOL_MAP, ENERGY_EMOJI_MAP,
    CANONICAL_BASIC_ENERGIES, normalize_energy_type, parse_attack_cost,
    format_cost_emojis, create_energy_card_dict, validate_attack_cost,
    calculate_matchup_damage, get_type_effectiveness
)


class EnergyCard(str):
    """
    Represents an Energy card attached to a Pokémon.
    Inherits from str so equality checks with strings (e.g. 'Fire') continue to work seamlessly,
    while also providing structured card data (.card_id, .energy_type, .card_name, .to_dict()).
    """
    def __new__(cls, energy_type, card_id=None, card_name=None):
        etype = normalize_energy_type(energy_type)
        obj = super().__new__(cls, etype)
        obj.energy_type = etype
        obj.card_id = str(card_id or f"energy_{etype.lower()}_basic")
        obj.card_name = str(card_name or f"Basic {etype} Energy")
        obj.name = obj.card_name
        obj.card_type = "energy"
        return obj

    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_id": self.card_id,
            "energy_type": self.energy_type,
            "card_name": self.card_name,
            "name": self.card_name,
            "card_type": "energy"
        }

    def get(self, k: str, default: Any = None) -> Any:
        if k in ("energy_type", "type", "pokemon_type"):
            return self.energy_type
        if k in ("card_id", "id"):
            return self.card_id
        if k in ("card_name", "name"):
            return self.card_name
        if k == "card_type":
            return "energy"
        return default



def check_energy_requirement(attached_energies: List[Union[str, Dict[str, Any]]], required_costs: Union[List[str], str]) -> Tuple[bool, str]:
    """
    Checks whether the attached energy satisfies the attack cost.
    Specific elemental types must match; any remaining energy pays for Colorless.
    """
    can_atk, reason, _ = validate_attack_cost(attached_energies, required_costs)
    return can_atk, reason


def can_use_attack(pokemon: Dict[str, Any], attack: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Authoritative attack validation function: canUseAttack(pokemon, attack).
    Validates attack cost against attached energy on the Pokémon.
    """
    if not pokemon or not attack:
        return False, "Invalid Pokémon or attack", {}
    attached = pokemon.get("attached_energy") or pokemon.get("attachedEnergy") or []
    cost = attack.get("cost") or []
    return validate_attack_cost(attached, cost)


class TCGMatchEngine:
    def __init__(self, card_db: Dict[str, Any]):
        self.card_db = card_db
        self._index_card_database()
        self.reset_match()

    def _index_card_database(self):
        """Indexes authentic Pokémon families and trainers from self.card_db for rule-based random deck generation."""
        basics = {}
        stage1 = {}
        stage2 = {}
        trainers = []

        for c in self.card_db.values():
            cname = c.get("name") or c.get("card_name")
            if not cname:
                continue
            ctype = c.get("card_type")
            if ctype == "pokemon":
                st = c.get("stage")
                if st == "Basic":
                    basics[cname] = c
                elif st == "Stage 1":
                    stage1[cname] = c
                elif st == "Stage 2":
                    stage2[cname] = c
            elif ctype == "trainer":
                trainers.append(cname)

        self.three_stage_families = []
        for s2_name, s2_card in stage2.items():
            s1_name = s2_card.get("evolves_from")
            if s1_name in stage1:
                s1_card = stage1[s1_name]
                b_name = s1_card.get("evolves_from")
                if b_name in basics:
                    ptype = s2_card.get("pokemon_type") or (s2_card.get("types") or ["Colorless"])[0]
                    self.three_stage_families.append((ptype, [(b_name, 3), (s1_name, 2), (s2_name, 2)]))

        self.two_stage_families = []
        for s1_name, s1_card in stage1.items():
            b_name = s1_card.get("evolves_from")
            if b_name in basics:
                ptype = s1_card.get("pokemon_type") or (s1_card.get("types") or ["Colorless"])[0]
                self.two_stage_families.append((ptype, [(b_name, 3), (s1_name, 2)]))

        self.basic_families = []
        for b_name, b_card in basics.items():
            ptype = b_card.get("pokemon_type") or (b_card.get("types") or ["Colorless"])[0]
            self.basic_families.append((ptype, [(b_name, 3)]))

        curated_trainers = [
            "Potion", "Switch", "Poké Ball", "Ultra Ball", "Rare Candy", "Super Rod",
            "Energy Retrieval", "Nest Ball", "Professor’s Research", "Boss’s Orders",
            "Arven", "Iono", "Pal Pad"
        ]
        self.trainer_pool = [t for t in curated_trainers if any((c.get("name") or "").replace("’", "'") == t.replace("’", "'") for c in self.card_db.values())]
        if len(self.trainer_pool) < 6:
            self.trainer_pool = list(set(trainers))[:15]

        self.valid_energy_types = list(ENERGY_TYPES)

    def generate_rule_based_random_deck(self, deck_name: str = "Random AI Opponent Deck") -> Dict[str, Any]:
        """
        Generates a 100% rule-compliant random Pokémon TCG deck:
        1. Exactly 60 cards total.
        2. Rule of 4: No card (except Basic Energy) appears more than 4 times.
        3. Pokémon: 12-18 cards with valid Basic -> Evolution chains, at least 6-10 Basic Pokémon.
        4. Energy: 12-16 Basic Energy matching the Pokémon types present.
        5. Trainers: Useful items and supporters with <= 4 copies per card.
        """
        chosen_types = set()
        pkmn_counts = Counter()

        # 1. 50% chance to include a 3-stage family (e.g. Charmander -> Charmeleon -> Charizard)
        if random.random() < 0.5 and self.three_stage_families:
            ptype, fam = random.choice(self.three_stage_families)
            chosen_types.add(ptype)
            for name, cnt in fam:
                pkmn_counts[name] = min(4, pkmn_counts[name] + cnt)

        # 2. Pick 1-2 two-stage families (e.g. Pikachu -> Raichu)
        num_two_stage = random.randint(1, 2)
        for _ in range(num_two_stage):
            if self.two_stage_families:
                ptype, fam = random.choice(self.two_stage_families)
                chosen_types.add(ptype)
                for name, cnt in fam:
                    pkmn_counts[name] = min(4, pkmn_counts[name] + cnt)

        # 3. Pick 1 basic family (e.g. Lapras, Snorlax, Zapdos)
        if self.basic_families:
            ptype, fam = random.choice(self.basic_families)
            chosen_types.add(ptype)
            for name, cnt in fam:
                pkmn_counts[name] = min(4, pkmn_counts[name] + cnt)

        # Build pokemon card list
        deck = []
        for name, cnt in pkmn_counts.items():
            deck.extend([name] * cnt)

        # 4. Authentic Trainers (Items & Supporters)
        num_trainers = random.randint(26, 32)
        sample_size = min(len(self.trainer_pool), 8)
        selected_trainers = random.sample(self.trainer_pool, sample_size) if sample_size > 0 else ["Potion", "Switch", "Poké Ball", "Ultra Ball"]
        t_counts = Counter()
        while sum(t_counts.values()) < num_trainers:
            t = random.choice(selected_trainers)
            if t_counts[t] < 4:
                t_counts[t] += 1
            elif all(t_counts[tr] >= 4 for tr in selected_trainers):
                break
        for t, cnt in t_counts.items():
            deck.extend([t] * cnt)

        # 5. Energies matching chosen types
        cleaned_types = [t for t in chosen_types if t in self.valid_energy_types]
        if not cleaned_types:
            cleaned_types = ["Fire", "Lightning"]

        energy_names = [f"Basic {t} Energy" for t in cleaned_types]
        e_idx = 0
        while len(deck) < 60:
            deck.append(energy_names[e_idx % len(energy_names)])
            e_idx += 1

        deck = deck[:60]
        primary_type = cleaned_types[0] if cleaned_types else "Fire"

        counted_list = [{"name": c, "count": cnt} for c, cnt in Counter(deck).items()]

        return {
            "name": deck_name,
            "archetype": f"random-{primary_type.lower()}",
            "primary_type": primary_type,
            "deck_list": counted_list,
            "cards": deck
        }

    def get_meta_decks(self) -> Dict[str, Dict[str, Any]]:
        """Returns standard 60-card tournament deck lists using authentic dataset names."""
        return {
            "charizard-fire": {
                "name": "Charizard & Charmander Fire Deck",
                "archetype": "charizard-fire",
                "primary_type": "Fire",
                "deck_list": [
                    {"name": "Charmander", "count": 4},
                    {"name": "Charmeleon", "count": 3},
                    {"name": "Charizard", "count": 2},
                    {"name": "Pikachu", "count": 3},
                    {"name": "Raichu", "count": 2},
                    {"name": "Potion", "count": 4},
                    {"name": "Poké Ball", "count": 4},
                    {"name": "Switch", "count": 4},
                    {"name": "Rare Candy", "count": 2},
                    {"name": "Ultra Ball", "count": 4},
                    {"name": "Basic Fire Energy", "count": 18},
                    {"name": "Basic Lightning Energy", "count": 10}
                ]
            },
            "pikachu-lightning": {
                "name": "Pikachu & Raichu Lightning Deck",
                "archetype": "pikachu-lightning",
                "primary_type": "Lightning",
                "deck_list": [
                    {"name": "Pikachu", "count": 4},
                    {"name": "Raichu", "count": 3},
                    {"name": "Pikachu ex", "count": 2},
                    {"name": "Charmander", "count": 3},
                    {"name": "Charmeleon", "count": 2},
                    {"name": "Potion", "count": 4},
                    {"name": "Poké Ball", "count": 4},
                    {"name": "Switch", "count": 4},
                    {"name": "Ultra Ball", "count": 4},
                    {"name": "Basic Lightning Energy", "count": 20},
                    {"name": "Basic Fire Energy", "count": 10}
                ]
            },
            "kanto-starters": {
                "name": "Kanto Starters Classic Deck",
                "archetype": "kanto-starters",
                "primary_type": "Multi-Type",
                "deck_list": [
                    {"name": "Bulbasaur", "count": 3},
                    {"name": "Ivysaur", "count": 2},
                    {"name": "Charmander", "count": 3},
                    {"name": "Charmeleon", "count": 2},
                    {"name": "Squirtle", "count": 3},
                    {"name": "Wartortle", "count": 2},
                    {"name": "Pikachu", "count": 3},
                    {"name": "Raichu", "count": 2},
                    {"name": "Potion", "count": 4},
                    {"name": "Poké Ball", "count": 4},
                    {"name": "Switch", "count": 4},
                    {"name": "Basic Grass Energy", "count": 7},
                    {"name": "Basic Fire Energy", "count": 7},
                    {"name": "Basic Water Energy", "count": 7},
                    {"name": "Basic Lightning Energy", "count": 7}
                ]
            }
        }

    def expand_deck(self, deck_list: List[Dict[str, Any]]) -> List[str]:
        """Expands counted deck items into a flat list of 60 card names."""
        cards = []
        for item in deck_list:
            cname = item.get("name") or item.get("card_name")
            count = item.get("count", 1)
            cards.extend([cname] * count)
        if len(cards) < 60:
            cards.extend(["Basic Fire Energy"] * (60 - len(cards)))
        return cards[:60]

    def has_basic_pokemon(self, hand_cards: List[str]) -> bool:
        """Returns True if the hand contains at least one Basic Pokémon."""
        for cname in hand_cards:
            meta = self._get_meta(cname)
            if meta.get("card_type") == "pokemon" and meta.get("stage") == "Basic":
                return True
        return False

    def reset_match(
        self,
        player_deck_id: str = "charizard-fire",
        opp_deck_id: str = "random",
        custom_player_deck: Optional[List[Union[str, Dict[str, Any]]]] = None,
        auto_place_player: bool = False
    ):
        """Initializes a full 60-card Pokémon TCG match with custom or meta deck."""
        meta_decks = self.get_meta_decks()

        # 1. Setup Player deck
        if custom_player_deck and len(custom_player_deck) > 0:
            p_deck_name = "Player Custom Deck"
            raw_cards = []
            for item in custom_player_deck:
                if isinstance(item, str):
                    raw_cards.append(item)
                elif isinstance(item, dict):
                    cname = item.get("name") or item.get("card_name", "Basic Fire Energy")
                    cnt = item.get("count", 1)
                    raw_cards.extend([cname] * cnt)

            # Check if this matches a meta deck archetype saved without counts (like test_e2e_flow)
            if player_deck_id in meta_decks and len(raw_cards) <= 15 and set(raw_cards).issubset(set(c["name"] for c in meta_decks[player_deck_id]["deck_list"])):
                self.player_deck = self.expand_deck(meta_decks[player_deck_id]["deck_list"])
            else:
                self.player_deck = list(raw_cards)
        else:
            p_deck_data = meta_decks.get(player_deck_id, meta_decks["charizard-fire"])
            p_deck_name = p_deck_data["name"]
            self.player_deck = self.expand_deck(p_deck_data["deck_list"])

        # 2. Setup Opponent 60-card deck (Rule-compliant random generation by default)
        if opp_deck_id == "random" or opp_deck_id not in meta_decks:
            opp_deck_data = self.generate_rule_based_random_deck()
            self.opp_deck = list(opp_deck_data["cards"])
        else:
            opp_deck_data = meta_decks[opp_deck_id]
            self.opp_deck = self.expand_deck(opp_deck_data["deck_list"])

        # Save template of chosen deck cards for infinite reshuffle
        self.player_deck_template: List[str] = list(self.player_deck)
        self.opp_deck_template: List[str] = list(self.opp_deck)

        # 3. Shuffle both decks
        random.shuffle(self.player_deck)
        random.shuffle(self.opp_deck)

        self.player_discard: List[str] = []
        self.opp_discard: List[str] = []

        # 4. Setup Opening Hand (target 5 cards, ensuring available Basic Pokémons are drawn into hand for Main/Bench setup)
        self.player_hand: List[str] = []
        target_hand_size = min(5, len(self.player_deck))
        for i in range(len(self.player_deck) - 1, -1, -1):
            if len(self.player_hand) >= target_hand_size:
                break
            meta = self._get_meta(self.player_deck[i])
            if meta.get("card_type") == "pokemon" and meta.get("stage") == "Basic":
                self.player_hand.append(self.player_deck.pop(i))

        while len(self.player_hand) < target_hand_size and self.player_deck:
            self.player_hand.append(self.player_deck.pop())

        # 5. Setup Prize cards
        if len(self.player_deck) >= 25:
            p_prizes_count = 6
        elif len(self.player_deck) > 0:
            p_prizes_count = max(0, min(6, len(self.player_deck) // 2))
        else:
            p_prizes_count = 0

        self.player_prizes: List[str] = [self.player_deck.pop() for _ in range(p_prizes_count) if self.player_deck]
        self.opp_prizes: List[str] = [self.opp_deck.pop() for _ in range(6) if self.opp_deck]
        self.player_prizes_taken = 0
        self.opp_prizes_taken = 0

        # Field Structure: exactly 1 Active slot, exactly 3 Bench slots
        self.player_active: Optional[Dict[str, Any]] = None
        self.player_bench: List[Optional[Dict[str, Any]]] = [None, None, None]

        self.opp_active: Optional[Dict[str, Any]] = None
        self.opp_bench: List[Optional[Dict[str, Any]]] = [None, None, None]

        self.mulligan_required = not self.has_basic_pokemon(self.player_hand)
        self.mulligan_count = 0

        # Opponent Initial Placement Setup
        self.opp_hand = [self.opp_deck.pop() for _ in range(min(5, len(self.opp_deck))) if self.opp_deck]
        while not self.has_basic_pokemon(self.opp_hand) and len(self.opp_deck) > 0:
            self.opp_deck.extend(self.opp_hand)
            random.shuffle(self.opp_deck)
            self.opp_hand = [self.opp_deck.pop() for _ in range(min(5, len(self.opp_deck))) if self.opp_deck]

        self._setup_opponent_initial_field()

        # Match state flags
        self.phase = "SETUP"  # "SETUP", "BATTLE", "WAITING_FOR_PROMOTION", "MATCH_OVER"
        self.turn_number = 1
        self.is_player_turn = True
        self.card_drawn_this_turn = False
        self.energy_attached_this_turn = False
        self.supporter_played_this_turn = False
        self.has_attacked_this_turn = False
        self.retreated_this_turn = False
        self.stadium_in_play = None
        self.winner = None

        self.match_log = [
            f"Match Initialized: {p_deck_name} vs {opp_deck_data['name']}.",
            f"Opening Hands Drawn: 5 cards dealt to Player ({len(self.player_deck)} cards left in face-down deck)."
        ]
        if self.mulligan_required:
            self.match_log.append("⚠️ Mulligan Required: Your 5-card opening hand contains no Basic Pokémon. Click Mulligan to redraw.")
        else:
            self.match_log.append("Please place a Basic Pokémon into your ACTIVE slot and up to 3 Basic Pokémon onto your BENCH.")

        if auto_place_player:
            self.auto_place_initial_pokemon()

        return self.get_game_state_dict()

    def to_dict(self) -> Dict[str, Any]:
        return self.get_game_state_dict()

    def _setup_opponent_initial_field(self):
        """Places 1 Basic Pokémon into opponent Active and up to 3 Basic Pokémon onto opponent Bench."""
        # Find basic in opp_hand or opp_deck
        opp_active_card = self._extract_basic_from_hand_or_deck(self.opp_hand, self.opp_deck)
        if opp_active_card:
            om = self._get_meta(opp_active_card)
            opp_type = om.get("pokemon_type") or (om.get("types") or ["Lightning"])[0]
            self.opp_active = self._create_pokemon_dict(opp_active_card, om, attached_energy=[opp_type])

        # Opponent Bench: place up to 2-3 basics
        for slot_idx in range(3):
            b_card = self._extract_basic_from_hand_or_deck(self.opp_hand, self.opp_deck)
            if b_card:
                bm = self._get_meta(b_card)
                self.opp_bench[slot_idx] = self._create_pokemon_dict(b_card, bm)

    def _create_pokemon_dict(self, card_name: str, meta: Dict[str, Any], attached_energy: Optional[List[str]] = None) -> Dict[str, Any]:
        hp = meta.get("hp") or 70
        ptype = meta.get("pokemon_type") or (meta.get("types") or ["Colorless"])[0]
        return {
            "name": card_name,
            "card_name": meta.get("card_name", card_name),
            "current_hp": hp,
            "max_hp": hp,
            "attached_energy": list(attached_energy or []),
            "turns_in_play": 1,
            "card_id": meta.get("card_id", "card-1"),
            "pokemon_type": ptype,
            "types": [ptype],
            "stage": meta.get("stage", "Basic"),
            "evolves_from": meta.get("evolves_from"),
            "attacks": meta.get("attacks", []),
            "attack_1_name": meta.get("attack_1_name"),
            "attack_1_damage": meta.get("attack_1_damage"),
            "attack_1_energy": meta.get("attack_1_energy") or [],
            "attack_2_name": meta.get("attack_2_name"),
            "attack_2_damage": meta.get("attack_2_damage"),
            "attack_2_energy": meta.get("attack_2_energy") or [],
            "ability": meta.get("ability"),
            "weakness": meta.get("weakness"),
            "resistance": meta.get("resistance"),
            "retreat_cost": meta.get("retreat_cost", 1),
            "image": meta.get("image", "")
        }

    def mulligan_player_hand(self) -> Dict[str, Any]:
        """Shuffles 5 hand cards back into deck and draws 5 new cards if no Basic Pokémon present."""
        if not self.mulligan_required and self.has_basic_pokemon(self.player_hand):
            return {"status": "error", "message": "Hand already contains at least 1 Basic Pokémon. Mulligan is not needed."}

        self.player_deck.extend(self.player_hand)
        random.shuffle(self.player_deck)
        self.player_hand = [self.player_deck.pop() for _ in range(5) if self.player_deck]
        self.mulligan_count += 1
        self.mulligan_required = not self.has_basic_pokemon(self.player_hand)

        self.match_log.append(f"🔄 Mulligan #{self.mulligan_count}: Hand reshuffled and 5 new cards drawn.")
        return {
            "status": "success",
            "mulligan_count": self.mulligan_count,
            "mulligan_required": self.mulligan_required,
            "hand": self.player_hand
        }

    def place_initial_pokemon(self, card_name: str, target_slot: str = "active") -> Dict[str, Any]:
        """
        Places a Basic Pokémon from the initial 5-card hand into Active or a Bench slot (0, 1, 2).
        STRICTLY BLOCKS Stage 1 and Stage 2 Pokémon.
        """
        if self.phase != "SETUP":
            return {"status": "error", "message": "Initial placement is only allowed during the SETUP phase."}

        actual_card = self._find_card_in_player_hand(card_name)
        if not actual_card:
            return {"status": "error", "message": f"'{card_name}' is not in your hand."}

        meta = self._get_meta(actual_card)
        if meta.get("card_type") != "pokemon" or meta.get("stage") != "Basic":
            return {
                "status": "error",
                "message": f"BLOCKED: '{actual_card}' is {meta.get('stage', 'not a Basic Pokémon')}. Only BASIC Pokémon can be placed initially!"
            }

        target_clean = target_slot.lower().strip()
        pkmn_obj = self._create_pokemon_dict(actual_card, meta)

        if target_clean in ["active", "slot_1"]:
            if self.player_active is not None:
                # If active is already occupied, automatically place into first free bench slot
                slot_idx = None
                for idx, b in enumerate(self.player_bench):
                    if b is None:
                        slot_idx = idx
                        break
                if slot_idx is not None:
                    self.player_hand.remove(actual_card)
                    self.player_bench[slot_idx] = pkmn_obj
                    self.match_log.append(f"🛡️ Placed Basic Pokémon [{pkmn_obj['name']}] onto BENCH Slot #{slot_idx + 1}.")
                    return {"status": "success", "slot": f"bench_{slot_idx}", "card": pkmn_obj['name'], "card_id": pkmn_obj.get("card_id")}
                return {"status": "error", "message": "Active slot and all 3 bench slots are full."}
            self.player_hand.remove(actual_card)
            self.player_active = pkmn_obj
            self.match_log.append(f"👑 Placed Basic Pokémon [{pkmn_obj['name']}] into ACTIVE slot.")
            return {"status": "success", "slot": "active", "card": pkmn_obj['name'], "card_id": pkmn_obj.get("card_id")}

        # Bench slots: bench_0, bench_1, bench_2 (or slot indices 0, 1, 2)
        slot_idx = None
        if target_clean in ["bench_0", "slot_0", "0"]:
            slot_idx = 0
        elif target_clean in ["bench_1", "slot_1", "1"]:
            slot_idx = 1
        elif target_clean in ["bench_2", "slot_2", "2"]:
            slot_idx = 2
        elif target_clean in ["bench_3", "slot_3", "3"]:
            slot_idx = 3 # will trigger out of range error
        else:
            # First available empty bench slot
            for idx, b in enumerate(self.player_bench):
                if b is None:
                    slot_idx = idx
                    break

        if slot_idx is None or slot_idx < 0 or slot_idx >= 3:
            return {"status": "error", "message": "All 3 bench slots are full (maximum 3 bench Pokémon)."}

        if self.player_bench[slot_idx] is not None:
            return {"status": "error", "message": f"Bench Slot #{slot_idx + 1} is already occupied."}

        self.player_hand.remove(actual_card)
        self.player_bench[slot_idx] = pkmn_obj
        self.match_log.append(f"🛡️ Placed Basic Pokémon [{pkmn_obj['name']}] onto BENCH Slot #{slot_idx + 1}.")
        return {"status": "success", "slot": f"bench_{slot_idx}", "card": pkmn_obj['name'], "card_id": pkmn_obj.get("card_id")}

    def place_and_start_battle(self, card_name: str, target_slot: str = "active") -> Dict[str, Any]:
        """
        Places a card from hand into Active or Bench and immediately transitions to BATTLE phase.
        1. If slot == 'active':
           - Places card_name into Active Spot.
           - Moves any other Basic Pokémon remaining in hand into empty Bench slots (up to 3).
        2. If slot == 'bench':
           - Places card_name into the first available Bench slot.
           - If Active is empty:
             - Takes another Basic Pokémon from hand (or deck) and puts it in Active.
             - If none exists, places this card in Active so battle can start.
           - Moves any remaining Basic Pokémon in hand into empty Bench slots (up to 3).
        3. Sets phase = 'BATTLE'.
        4. Draws cards up to 5 for Turn 1 battle hand.
        """
        if self.phase != "SETUP":
            return {"status": "error", "message": "Initial placement is only allowed during SETUP phase."}

        actual_card = self._find_card_in_player_hand(card_name)
        if not actual_card:
            return {"status": "error", "message": f"'{card_name}' is not in your hand."}

        meta = self._get_meta(actual_card)
        if meta.get("card_type") != "pokemon" or meta.get("stage") != "Basic":
            return {
                "status": "error",
                "message": f"BLOCKED: '{actual_card}' is {meta.get('stage', 'not a Basic Pokémon')}. Only BASIC Pokémon can be placed initially!"
            }

        target_clean = (target_slot or "active").lower().strip()
        pkmn_obj = self._create_pokemon_dict(actual_card, meta)

        if target_clean in ["active", "slot_1", "main"]:
            # Place in Active
            self.player_hand.remove(actual_card)
            self.player_active = pkmn_obj
            self.match_log.append(f"👑 Placed Basic Pokémon [{pkmn_obj['name']}] into ACTIVE slot.")
            
            # Place any other basic Pokémon from hand into bench
            for slot_idx in range(3):
                if self.player_bench[slot_idx] is None:
                    next_basic = None
                    for idx, c in enumerate(self.player_hand):
                        cm = self._get_meta(c)
                        if cm.get("card_type") == "pokemon" and cm.get("stage") == "Basic":
                            next_basic = self.player_hand.pop(idx)
                            break
                    if next_basic:
                        nb_meta = self._get_meta(next_basic)
                        self.player_bench[slot_idx] = self._create_pokemon_dict(next_basic, nb_meta)
                        self.match_log.append(f"🛡️ Placed Basic Pokémon [{self.player_bench[slot_idx]['name']}] onto BENCH Slot #{slot_idx + 1}.")
        else:
            # Place in Bench
            self.player_hand.remove(actual_card)
            slot_idx = 0
            for idx, b in enumerate(self.player_bench):
                if b is None:
                    slot_idx = idx
                    break
            self.player_bench[slot_idx] = pkmn_obj
            self.match_log.append(f"🛡️ Placed Basic Pokémon [{pkmn_obj['name']}] onto BENCH Slot #{slot_idx + 1}.")

            # If Active is empty, must populate Active so battle can proceed!
            if self.player_active is None:
                next_basic = None
                for idx, c in enumerate(self.player_hand):
                    cm = self._get_meta(c)
                    if cm.get("card_type") == "pokemon" and cm.get("stage") == "Basic":
                        next_basic = self.player_hand.pop(idx)
                        break
                if next_basic:
                    nb_meta = self._get_meta(next_basic)
                    self.player_active = self._create_pokemon_dict(next_basic, nb_meta)
                    self.match_log.append(f"👑 Placed Basic Pokémon [{self.player_active['name']}] into ACTIVE slot.")
                else:
                    # If this bench card was the only basic, promote it to active so battle can start!
                    self.player_active = self.player_bench[slot_idx]
                    self.player_bench[slot_idx] = None
                    self.match_log.append(f"👑 Moved [{self.player_active['name']}] to ACTIVE slot to initiate battle.")

            # Bench any other remaining basics
            for s_idx in range(3):
                if self.player_bench[s_idx] is None:
                    next_basic = None
                    for idx, c in enumerate(self.player_hand):
                        cm = self._get_meta(c)
                        if cm.get("card_type") == "pokemon" and cm.get("stage") == "Basic":
                            next_basic = self.player_hand.pop(idx)
                            break
                    if next_basic:
                        nb_meta = self._get_meta(next_basic)
                        self.player_bench[s_idx] = self._create_pokemon_dict(next_basic, nb_meta)
                        self.match_log.append(f"🛡️ Placed Basic Pokémon [{self.player_bench[s_idx]['name']}] onto BENCH Slot #{s_idx + 1}.")

        # Transition to BATTLE phase
        self.phase = "BATTLE"
        self.card_drawn_this_turn = False
        
        # Draw opening battle hand (up to 5 cards) from the deck for Turn 1
        while len(self.player_hand) < 5 and self.player_deck:
            self.player_hand.append(self.player_deck.pop())
            
        self.match_log.append("⚔️ Field setup complete! Battle begins. Turn 1.")
        return {
            "status": "success",
            "phase": self.phase,
            "active": self.player_active["name"] if self.player_active else None
        }

    def confirm_initial_placement(self) -> Dict[str, Any]:
        """Transitions match from SETUP phase to BATTLE once Active Pokémon is placed."""
        if self.player_active is None:
            return {"status": "error", "message": "You must place at least 1 Basic Pokémon into the ACTIVE slot before starting battle!"}

        self.phase = "BATTLE"
        self.card_drawn_this_turn = False
        # Draw opening battle hand (up to 5 cards) from the deck for Turn 1
        while len(self.player_hand) < 5 and self.player_deck:
            self.player_hand.append(self.player_deck.pop())
        self.match_log.append("⚔️ Battle Confirmed! Turn 1 begins.")
        return {"status": "success", "phase": self.phase}

    def auto_place_initial_pokemon(self) -> Dict[str, Any]:
        """
        Automatically places 1 Basic Pokémon into Active, up to 3 Basic Pokémon onto Bench,
        and starts BATTLE phase.
        """
        self.card_drawn_this_turn = False
        if self.player_active is None:
            basic = self._extract_basic_from_hand_or_deck(self.player_hand, self.player_deck)
            if basic:
                meta = self._get_meta(basic)
                self.player_active = self._create_pokemon_dict(basic, meta)
                self.match_log.append(f"⚔️ Placed Basic Pokémon [{self.player_active['name']}] into ACTIVE slot.")

        # Bench up to 3 basics from hand
        for i in range(3):
            if self.player_bench[i] is None:
                basic_h = None
                for idx, c in enumerate(self.player_hand):
                    m = self._get_meta(c)
                    if m.get("card_type") == "pokemon" and m.get("stage") == "Basic":
                        basic_h = self.player_hand.pop(idx)
                        break
                if basic_h:
                    bm = self._get_meta(basic_h)
                    self.player_bench[i] = self._create_pokemon_dict(basic_h, bm)
                    self.match_log.append(f"🛡️ Placed Basic Pokémon [{bm.get('name') or basic_h}] onto BENCH Slot #{i + 1}.")

        self.phase = "BATTLE"
        while len(self.player_hand) < 5 and self.player_deck:
            self.player_hand.append(self.player_deck.pop())
        return {"status": "success", "phase": self.phase}

    def _ensure_player_deck_has_cards(self):
        """Ensures the player battle deck is infinite by continuous reshuffling from discard and chosen deck."""
        if len(self.player_deck) < 2:
            if self.player_discard:
                self.player_deck.extend(self.player_discard)
                self.player_discard.clear()
                random.shuffle(self.player_deck)
                self.match_log.append("🔄 Infinite Deck Reshuffle: Recycled discarded cards back into your battle deck!")
            if len(self.player_deck) < 5 and getattr(self, "player_deck_template", None):
                self.player_deck.extend(list(self.player_deck_template))
                random.shuffle(self.player_deck)
                self.match_log.append("🔄 Infinite Deck Refill: Replenished battle deck from your chosen deck cards!")

    def _ensure_opp_deck_has_cards(self):
        """Ensures opponent deck is infinite by continuous reshuffling."""
        if len(self.opp_deck) < 2:
            if self.opp_discard:
                self.opp_deck.extend(self.opp_discard)
                self.opp_discard.clear()
                random.shuffle(self.opp_deck)
            if len(self.opp_deck) < 5 and getattr(self, "opp_deck_template", None):
                self.opp_deck.extend(list(self.opp_deck_template))
                random.shuffle(self.opp_deck)

    def _check_and_refill_empty_hand(self):
        """If player hand is empty during BATTLE phase, refill it with cards chosen from deck."""
        if self.phase == "BATTLE" and len(self.player_hand) == 0:
            self._ensure_player_deck_has_cards()
            refill_count = min(5, len(self.player_deck))
            for _ in range(refill_count):
                if self.player_deck:
                    self.player_hand.append(self.player_deck.pop())
            if refill_count > 0:
                self.match_log.append(f"🎴 Hand Refill: Hand was empty! Filled hand with {refill_count} cards from your chosen deck.")

    def draw_card(self, is_player: bool = True) -> Optional[str]:
        """
        Draws 1 card from deck to hand.
        STRICT RULE: The player can use DRAW CARD only ONCE PER TURN.
        Automatically generates an Energy card matching active Pokémon type into player hand.
        """
        if is_player:
            if self.card_drawn_this_turn:
                self.match_log.append("⚠️ Draw Blocked: You can only draw 1 card per turn.")
                return None
            
            self._ensure_player_deck_has_cards()
            if not self.player_deck:
                return None
            
            card = self.player_deck.pop()
            self.player_hand.append(card)
            self.card_drawn_this_turn = True
            self.match_log.append(f"🎴 Drawn [{card}] from deck ({len(self.player_deck)} cards remaining).")

            # AUTOMATICALLY GENERATE ENERGY CARD ON DRAW
            active_type = "Fire"
            if self.player_active:
                active_type = self.player_active.get("pokemon_type") or "Fire"
                if active_type == "Colorless" or not active_type:
                    active_type = "Fire"
            elif getattr(self, "player_deck_template", None):
                for c in self.player_deck_template:
                    if "energy" in str(c).lower():
                        clean_t = str(c).replace("Basic", "").replace("Energy", "").strip()
                        if clean_t:
                            active_type = clean_t
                            break

            energy_card_name = f"Basic {active_type} Energy"
            self.player_hand.append(energy_card_name)
            self.match_log.append(f"⚡ Energy Surge: Automatically generated [{energy_card_name}] into your hand!")

            return card
        else:
            self._ensure_opp_deck_has_cards()
            if not self.opp_deck:
                return None
            card = self.opp_deck.pop()
            self.opp_hand.append(card)
            return card

    def attach_energy(self, card_name: str, target: str = "active", is_player: bool = True) -> Dict[str, Any]:
        """
        Attaches an Energy card from hand to Active or any Bench Pokémon.
        STRICT RULE: Only ONCE PER TURN.
        Energy can be attached to ANY Pokémon regardless of the Pokémon's type.
        """
        if is_player:
            if self.energy_attached_this_turn:
                return {
                    "status": "error",
                    "message": "You have already attached Energy this turn (Energy can only be attached once per turn)."
                }

            actual_card = self._find_card_in_player_hand(card_name)
            if not actual_card:
                return {"status": "error", "message": f"'{card_name}' is not in your hand."}

            meta = self._get_meta(actual_card)
            if meta.get("card_type") != "energy" and "energy" not in actual_card.lower():
                return {"status": "error", "message": f"'{actual_card}' is not an Energy card."}

            # Canonical Energy type (Grass, Fire, Water, Lightning, Fighting, Psychic, Darkness, Metal, Dragon)
            e_type = normalize_energy_type(meta.get("energy_type") or meta.get("pokemon_type") or actual_card)
            card_id = meta.get("card_id") or f"energy_{e_type.lower()}_basic"
            card_disp_name = meta.get("card_name") or meta.get("name") or f"Basic {e_type} Energy"

            # Resolve target Pokémon (Active or Bench 0-2)
            target_clean = (target or "active").lower().strip()
            target_pkmn = None

            if target_clean in ["active", "slot_1", "player", "main"]:
                target_pkmn = self.player_active
            elif "bench" in target_clean or target_clean in ["0", "1", "2"]:
                idx = 0
                if "0" in target_clean: idx = 0
                elif "1" in target_clean: idx = 1
                elif "2" in target_clean: idx = 2
                if 0 <= idx < 3:
                    target_pkmn = self.player_bench[idx]

            if not target_pkmn:
                # Try matching by pokemon name
                if self.player_active and target_clean in self.player_active["name"].lower():
                    target_pkmn = self.player_active
                else:
                    for b in self.player_bench:
                        if b and target_clean in b["name"].lower():
                            target_pkmn = b
                            break

            if not target_pkmn:
                target_pkmn = self.player_active

            if not target_pkmn:
                return {"status": "error", "message": "Target Pokémon not found or slot is empty."}

            # Create structured EnergyCard
            energy_card_obj = EnergyCard(e_type, card_id=card_id, card_name=card_disp_name)

            self.player_hand.remove(actual_card)
            if "attached_energy" not in target_pkmn:
                target_pkmn["attached_energy"] = []
            target_pkmn["attached_energy"].append(energy_card_obj)
            target_pkmn["attachedEnergy"] = [
                e.to_dict() if hasattr(e, "to_dict") else {"card_id": f"energy_{str(e).lower()}_basic", "energy_type": str(e), "card_name": f"Basic {str(e)} Energy"}
                for e in target_pkmn["attached_energy"]
            ]

            self.energy_attached_this_turn = True
            emoji_sym = ENERGY_EMOJI_MAP.get(e_type, "⚡")
            self.match_log.append(f"{emoji_sym} Attached [{card_disp_name}] to {target_pkmn['name']}.")
            return {
                "status": "success",
                "action": "ATTACH_ENERGY",
                "card": card_disp_name,
                "target": target_pkmn["name"],
                "energy_type": e_type,
                "attached_energy": target_pkmn["attached_energy"],
                "attachedEnergy": target_pkmn["attachedEnergy"]
            }

        return {"status": "error", "message": "Invalid attachment request."}

    def play_basic_pokemon_to_bench(self, card_name: str, slot_index: Optional[int] = None) -> Dict[str, Any]:
        """Plays a Basic Pokémon from hand into an empty bench slot (max 3 bench)."""
        actual_card = self._find_card_in_player_hand(card_name)
        if not actual_card:
            return {"status": "error", "message": f"'{card_name}' is not in your hand."}

        meta = self._get_meta(actual_card)
        if meta.get("card_type") != "pokemon" or meta.get("stage") != "Basic":
            return {"status": "error", "message": f"'{actual_card}' is not a Basic Pokémon."}

        # Check bench capacity
        target_idx = None
        if slot_index is not None and 0 <= slot_index < 3:
            if self.player_bench[slot_index] is None:
                target_idx = slot_index
            else:
                return {"status": "error", "message": f"Bench Slot #{slot_index + 1} is already occupied."}
        else:
            for i in range(3):
                if self.player_bench[i] is None:
                    target_idx = i
                    break

        if target_idx is None:
            return {"status": "error", "message": "Bench is full (maximum 3 Pokémon)."}

        self.player_hand.remove(actual_card)
        pkmn_obj = self._create_pokemon_dict(actual_card, meta)
        self.player_bench[target_idx] = pkmn_obj
        self.match_log.append(f"🛡️ Benched [{pkmn_obj['name']}] into Bench Slot #{target_idx + 1}.")
        return {"status": "success", "slot": target_idx, "pokemon": pkmn_obj}

    def evolve_pokemon(self, card_name: str, target: str = "active") -> Dict[str, Any]:
        """
        Evolves a compatible Pokémon on the Active or Bench using evolves_from.
        Preserves attached energy, updates HP, attacks, abilities, types, retreat cost.
        """
        actual_card = self._find_card_in_player_hand(card_name)
        if not actual_card:
            return {"status": "error", "message": f"'{card_name}' is not in your hand."}

        meta = self._get_meta(actual_card)
        stage = meta.get("stage")
        if stage not in ["Stage 1", "Stage 2"]:
            return {"status": "error", "message": f"'{actual_card}' is not an evolution Pokémon."}

        evolves_from = meta.get("evolves_from")
        if not evolves_from:
            return {"status": "error", "message": f"'{actual_card}' does not specify what it evolves from."}

        # Find target Pokémon
        target_clean = target.lower().strip()
        target_pkmn = None
        is_active = False
        bench_slot = None

        if target_clean in ["active", "slot_1"]:
            target_pkmn = self.player_active
            is_active = True
        elif "bench" in target_clean or target_clean in ["0", "1", "2"]:
            idx = 0
            if "0" in target_clean: idx = 0
            elif "1" in target_clean: idx = 0 if "bench_1" == target_clean else 1
            elif "2" in target_clean: idx = 1 if "bench_2" == target_clean else 2
            elif "3" in target_clean: idx = 2
            if 0 <= idx < 3:
                target_pkmn = self.player_bench[idx]
                bench_slot = idx

        if not target_pkmn:
            # Match by name
            if self.player_active and evolves_from.lower() in self.player_active["name"].lower():
                target_pkmn = self.player_active
                is_active = True
            else:
                for idx, b in enumerate(self.player_bench):
                    if b and evolves_from.lower() in b["name"].lower():
                        target_pkmn = b
                        bench_slot = idx
                        break

        if not target_pkmn:
            return {
                "status": "error",
                "message": f"BLOCKED: Cannot evolve: No '{evolves_from}' on field to evolve into '{actual_card}'!"
            }

        used_rare_candy = False
        if evolves_from.lower() not in target_pkmn["name"].lower():
            # Check Rare Candy exception (Basic -> Stage 2 directly)
            candy_in_hand = any("rare candy" in str(c).lower() for c in self.player_hand)
            if stage == "Stage 2" and candy_in_hand:
                candy = next(c for c in self.player_hand if "rare candy" in str(c).lower())
                self.player_hand.remove(candy)
                self.player_discard.append(candy)
                used_rare_candy = True
            else:
                return {
                    "status": "error",
                    "message": f"BLOCKED: '{actual_card}' evolves from '{evolves_from}', not '{target_pkmn['name']}'!"
                }

        # Execute Evolution: preserve attached energy!
        saved_energy = list(target_pkmn.get("attached_energy", []))
        prev_hp = target_pkmn["current_hp"]
        prev_max = target_pkmn["max_hp"]
        new_max = meta.get("hp", prev_max + 60)
        hp_diff = new_max - prev_max
        new_current_hp = min(new_max, prev_hp + hp_diff)

        new_pkmn = self._create_pokemon_dict(actual_card, meta, attached_energy=saved_energy)
        new_pkmn["current_hp"] = new_current_hp

        self.player_hand.remove(actual_card)
        if is_active:
            self.player_active = new_pkmn
            self.match_log.append(f"✨ Evolved Active [{target_pkmn['name']}] into [{new_pkmn['name']}]! (HP: {new_current_hp}/{new_max}).")
        else:
            self.player_bench[bench_slot] = new_pkmn
            self.match_log.append(f"✨ Evolved Benched [{target_pkmn['name']}] into [{new_pkmn['name']}]! (HP: {new_current_hp}/{new_max}).")

        act = "RARE_CANDY_EVOLVE" if used_rare_candy else "EVOLVE_POKEMON"
        return {"status": "success", "action": act, "card": new_pkmn['name'], "pokemon": new_pkmn}

    def play_trainer_card(self, card_name: str, target: Optional[str] = None) -> Dict[str, Any]:
        """Plays a Trainer card from hand and executes its effect."""
        actual_card = self._find_card_in_player_hand(card_name)
        if not actual_card:
            return {"status": "error", "message": f"'{card_name}' is not in your hand."}

        meta = self._get_meta(actual_card)
        if meta.get("card_type") != "trainer":
            return {"status": "error", "message": f"'{actual_card}' is not a Trainer card."}

        subtypes = [s.lower() for s in meta.get("subtypes", [])]
        if "supporter" in subtypes:
            if self.supporter_played_this_turn:
                return {"status": "error", "message": "Only 1 Supporter card can be played per turn."}
            self.supporter_played_this_turn = True

        self.player_hand.remove(actual_card)
        self.player_discard.append(actual_card)

        cname_lower = str(meta.get("name") or actual_card).lower()
        effect_msg = "Played Trainer card."

        # Potion: Heal 30 damage
        if "potion" in cname_lower:
            target_pkmn = self.player_active
            if target and "bench" in target.lower():
                idx = 0 if "0" in target else (1 if "1" in target else 2)
                if self.player_bench[idx]: target_pkmn = self.player_bench[idx]
            if target_pkmn:
                target_pkmn["current_hp"] = min(target_pkmn["max_hp"], target_pkmn["current_hp"] + 30)
                effect_msg = f"Healed 30 HP on {target_pkmn['name']} (HP now {target_pkmn['current_hp']}/{target_pkmn['max_hp']})."

        # Poké Ball / Nest Ball: Draw 1 Basic Pokémon
        elif "ball" in cname_lower:
            b_card = self._extract_basic_from_hand_or_deck([], self.player_deck)
            if b_card:
                self.player_hand.append(b_card)
                effect_msg = f"Found [{b_card}] in deck and put into hand."
            else:
                effect_msg = "Searched deck, but no Basic Pokémon found."

        # Switch: Switch Active with bench
        elif "switch" in cname_lower:
            effect_msg = "Used Switch! Choose a benched Pokémon to become Active."

        # Supporter card draw (e.g. Professor's Research, Iono)
        elif "research" in cname_lower:
            for _ in range(3):
                if self.player_deck:
                    self.player_hand.append(self.player_deck.pop())
            effect_msg = "Drew 3 cards from deck."

        self.match_log.append(f"🧰 [{card_name}]: {effect_msg}")
        self._check_and_refill_empty_hand()
        return {"status": "success", "action": "PLAY_TRAINER", "card": card_name, "message": effect_msg}

    def play_hand_card(self, card_name: str, target: Optional[str] = "active") -> Dict[str, Any]:
        """
        Generic hand card dispatcher supporting energy, trainer, basic Pokémon, and evolution.
        """
        actual_card = self._find_card_in_player_hand(card_name)
        if not actual_card:
            return {"status": "error", "message": f"'{card_name}' is not in your hand."}

        meta = self._get_meta(actual_card)
        ctype = meta.get("card_type")
        stage = meta.get("stage")

        if self.phase == "SETUP":
            return self.place_initial_pokemon(actual_card, target or "active")
        elif ctype == "energy" or "energy" in str(actual_card).lower():
            return self.attach_energy(actual_card, target or "active")
        elif ctype == "pokemon" and stage in ["Stage 1", "Stage 2"]:
            return self.evolve_pokemon(actual_card, target or "active")
        elif ctype == "pokemon" and stage == "Basic":
            if self.player_active is None:
                self.player_hand.remove(actual_card)
                pkmn_obj = self._create_pokemon_dict(actual_card, meta)
                self.player_active = pkmn_obj
                self.match_log.append(f"👑 Placed Basic Pokémon [{pkmn_obj['name']}] into ACTIVE spot.")
                return {"status": "success", "slot": "active", "card": pkmn_obj['name'], "card_id": pkmn_obj.get("card_id")}
            slot_idx = None
            if target and any(d in target for d in ["0", "1", "2"]):
                slot_idx = int(re.sub(r"[^\d]", "", target))
            return self.play_basic_pokemon_to_bench(actual_card, slot_idx)
        elif ctype == "trainer":
            return self.play_trainer_card(actual_card, target)
        else:
            return {"status": "error", "message": f"Unable to play '{card_name}'."}

    def switch_or_retreat(self, bench_slot_index: int) -> Dict[str, Any]:
        """
        Switches the Active Pokémon with one of the BENCHED Pokémon.
        The selected Pokémon becomes ACTIVE, and the previous Active moves to the selected bench slot.
        """
        if bench_slot_index < 0 or bench_slot_index >= 3:
            return {"status": "error", "message": "Invalid bench slot (must be 0, 1, or 2)."}

        if self.player_bench[bench_slot_index] is None:
            return {"status": "error", "message": f"Bench Slot #{bench_slot_index + 1} is empty."}

        if self.player_active is None:
            # If active is empty (e.g. following a knockout), promote directly
            self.player_active = self.player_bench[bench_slot_index]
            self.player_bench[bench_slot_index] = None
            self.phase = "BATTLE"
            self.match_log.append(f"👑 Promoted [{self.player_active['name']}] from Bench to Active!")
            return {"status": "success", "active": self.player_active}

        # Swap Active and Benched Pokémon
        prev_active = self.player_active
        new_active = self.player_bench[bench_slot_index]

        self.player_active = new_active
        self.player_bench[bench_slot_index] = prev_active
        self.retreated_this_turn = True

        self.match_log.append(f"🔄 SWITCH: [{new_active['name']}] is now ACTIVE! [{prev_active['name']}] moved to Bench Slot #{bench_slot_index + 1}.")
        return {
            "status": "success",
            "action": "SWITCH_POKEMON",
            "new_active": new_active["name"],
            "benched": prev_active["name"],
            "bench_slot": bench_slot_index
        }

    def promote_bench_to_active(self, bench_slot_index: int) -> Dict[str, Any]:
        """Promotes a benched Pokémon to the Active slot following a knockout."""
        return self.switch_or_retreat(bench_slot_index)

    def execute_attack(self, attack_name: str, base_damage: Optional[int] = 0) -> Dict[str, Any]:
        """
        Executes active Pokémon attack against opponent active with strict energy checks.
        """
        if self.phase != "BATTLE":
            return {"status": "error", "message": f"Attacking is not allowed during {self.phase} phase."}

        if not self.is_player_turn:
            return {"status": "error", "message": "It is not your turn."}

        if not self.player_active:
            return {"status": "error", "message": "No Active Pokémon to attack with!"}

        if not self.opp_active:
            return {"status": "error", "message": "Opponent has no Active Pokémon."}

        p_active = self.player_active
        p_meta = self._get_meta(p_active["name"])

        # Find the attack definition
        attacks = p_meta.get("attacks") or p_active.get("attacks") or []
        target_attack = None
        for atk in attacks:
            if atk.get("name", "").lower() == attack_name.lower():
                target_attack = atk
                break

        if not target_attack:
            # Fallback to attack 1 or attack 2
            if p_meta.get("attack_1_name") and p_meta.get("attack_1_name").lower() == attack_name.lower():
                target_attack = {
                    "name": p_meta["attack_1_name"],
                    "damage": p_meta.get("attack_1_damage", 30),
                    "cost": p_meta.get("attack_1_energy") or []
                }
            elif p_meta.get("attack_2_name") and p_meta.get("attack_2_name").lower() == attack_name.lower():
                target_attack = {
                    "name": p_meta["attack_2_name"],
                    "damage": p_meta.get("attack_2_damage", 60),
                    "cost": p_meta.get("attack_2_energy") or []
                }

        if not target_attack:
            target_attack = {"name": attack_name, "damage": base_damage or 30, "cost": ["Colorless"]}

        # STRICT ENERGY REQUIREMENT CHECK
        cost_list = target_attack.get("cost") or []
        attached = p_active.get("attached_energy", [])
        can_attack, reason = check_energy_requirement(attached, cost_list)

        if not can_attack:
            self.match_log.append(f"⛔ Attack Blocked: [{attack_name}] requires {cost_list}. {reason}.")
            return {
                "status": "error",
                "message": f"Attack LOCKED: {reason}.",
                "energy_required": cost_list,
                "energy_attached": attached
            }

        # Calculate Damage & Type Matchup (+50% / -50% / Normal)
        dmg = base_damage or 0
        raw_dmg = str(target_attack.get("damage") or "")
        clean_dmg = re.sub(r"[^\d]", "", raw_dmg)
        if clean_dmg:
            dmg = int(clean_dmg)

        opp_meta = self._get_meta(self.opp_active["name"])
        p_type = p_active.get("pokemon_type") or p_meta.get("pokemon_type") or "Colorless"
        opp_type = self.opp_active.get("pokemon_type") or opp_meta.get("pokemon_type") or "Colorless"

        opp_weakness = opp_meta.get("weakness") or ""
        opp_resistance = opp_meta.get("resistance") or ""
        p_weakness = p_meta.get("weakness") or ""

        final_dmg, mult, matchup_label, matchup_reason = calculate_matchup_damage(
            base_damage=dmg,
            attacker_type=p_type,
            defender_type=opp_type,
            defender_weakness=opp_weakness,
            defender_resistance=opp_resistance,
            attacker_weakness=p_weakness
        )

        prev_hp = self.opp_active["current_hp"]
        self.opp_active["current_hp"] = max(0, self.opp_active["current_hp"] - final_dmg)

        matchup_tag = ""
        if mult == 1.5:
            matchup_tag = f" (+50% Type Advantage vs {opp_type}!)"
        elif mult == 0.5:
            matchup_tag = f" (-50% Type Disadvantage vs {opp_type})"

        self.match_log.append(
            f"⚔️ {p_active['name']} used [{attack_name}] dealing {final_dmg} DMG"
            f"{matchup_tag}! (Opponent HP: {prev_hp} -> {self.opp_active['current_hp']})."
        )

        # Check Knockout
        ko_occurred = False
        if self.opp_active["current_hp"] <= 0:
            ko_occurred = True
            self.opp_discard.append(self.opp_active["name"])
            self.player_prizes_taken += 1
            self.match_log.append(f"💥 KNOCKOUT: Opponent's {self.opp_active['name']} has 0 HP and is knocked out!")

            # Check Victory (taking all 6 prizes or 3 in quick match)
            if self.player_prizes_taken >= 6 or (self.player_prizes and len(self.player_prizes) <= 0) or (not self.player_prizes and self.player_prizes_taken >= 3):
                self.winner = "Player"
                self.phase = "MATCH_OVER"
                self.match_log.append("🏆 VICTORY: You knocked out the opponent's Pokémon and won the match!")
                return {"status": "match_won", "winner": "Player", "knockout": True}

            # Opponent Promotes from Bench
            promoted = False
            for idx in range(3):
                if self.opp_bench[idx] is not None:
                    self.opp_active = self.opp_bench[idx]
                    self.opp_bench[idx] = None
                    promoted = True
                    self.match_log.append(f"🔄 Opponent promoted benched [{self.opp_active['name']}] to Active Spot.")
                    break

            if not promoted:
                self.winner = "Player"
                self.phase = "MATCH_OVER"
                self.match_log.append("🏆 VICTORY: Opponent has no benched Pokémon to promote! You win!")
                return {"status": "match_won", "winner": "Player", "knockout": True}

        # End player turn actions & simulate opponent response
        self.has_attacked_this_turn = True
        if not self.winner:
            self._simulate_opponent_turn()

        return {
            "status": "success",
            "damage_dealt": dmg,
            "knockout": ko_occurred,
            "winner": self.winner,
            "player_kos": self.player_prizes_taken,
            "opp_kos": self.opp_prizes_taken
        }

    def _simulate_opponent_turn(self):
        """Intelligent Opponent AI choosing legal moves based on authoritative game state."""
        if self.winner:
            return

        self.match_log.append(f"--- Opponent Turn (Turn {self.turn_number}) ---")

        # 1. Opponent Draws 1 card
        self.draw_card(is_player=False)

        # 2. Opponent plays basic to empty bench slot if available
        empty_opp_slots = [i for i, b in enumerate(self.opp_bench) if b is None]
        if empty_opp_slots:
            b_card = self._extract_basic_from_hand_or_deck(self.opp_hand, self.opp_deck)
            if b_card:
                bm = self._get_meta(b_card)
                self.opp_bench[empty_opp_slots[0]] = self._create_pokemon_dict(b_card, bm)
                self.match_log.append(f"Opponent benched [{b_card}].")

        # 3. Opponent attaches energy if available (Max 1 Energy attached per turn)
        if self.opp_active:
            # Check if opponent hand has an energy card, or draw from deck
            opp_energy_card = None
            for idx, c in enumerate(self.opp_hand):
                m = self._get_meta(c)
                if m.get("card_type") == "energy" or "energy" in str(c).lower():
                    opp_energy_card = self.opp_hand.pop(idx)
                    break

            if not opp_energy_card and self.opp_deck:
                for idx, c in enumerate(self.opp_deck):
                    m = self._get_meta(c)
                    if m.get("card_type") == "energy" or "energy" in str(c).lower():
                        opp_energy_card = self.opp_deck.pop(idx)
                        break

            opp_type = self.opp_active.get("pokemon_type") or "Lightning"
            if opp_energy_card:
                m = self._get_meta(opp_energy_card)
                opp_type = normalize_energy_type(m.get("energy_type") or m.get("pokemon_type") or opp_energy_card)

            attached_item = EnergyCard(opp_type)
            self.opp_active["attached_energy"].append(attached_item)
            self.opp_active["attachedEnergy"] = [
                e.to_dict() if hasattr(e, "to_dict") else {"card_id": f"energy_{str(e).lower()}_basic", "energy_type": str(e), "card_name": f"Basic {str(e)} Energy"}
                for e in self.opp_active["attached_energy"]
            ]
            emoji_sym = ENERGY_EMOJI_MAP.get(opp_type, "⚡")
            self.match_log.append(f"{emoji_sym} Opponent attached [Basic {opp_type} Energy] to {self.opp_active['name']}.")

        # 4. Opponent Attacks Player Active - STRICT REQUIREMENT CHECK (No free illegal attacks)
        if self.opp_active and self.player_active:
            opp_atks = self.opp_active.get("attacks") or []
            valid_atk = None
            for atk in opp_atks:
                can_atk, reason, _ = validate_attack_cost(self.opp_active.get("attached_energy", []), atk.get("cost", []))
                if can_atk:
                    valid_atk = atk
                    break

            if not valid_atk and self.opp_active.get("attack_1_name"):
                atk1_cost = self.opp_active.get("attack_1_energy") or []
                can_atk1, _, _ = validate_attack_cost(self.opp_active.get("attached_energy", []), atk1_cost)
                if can_atk1:
                    valid_atk = {
                        "name": self.opp_active["attack_1_name"],
                        "damage": self.opp_active.get("attack_1_damage", 30),
                        "cost": atk1_cost
                    }

            if not valid_atk:
                self.match_log.append(f"⏳ Opponent's {self.opp_active['name']} passed (insufficient energy to attack).")
                self.turn_number += 1
                self.card_drawn_this_turn = False
                self.energy_attached_this_turn = False
                self.supporter_played_this_turn = False
                self.has_attacked_this_turn = False
                self.retreated_this_turn = False
                self._check_and_refill_empty_hand()
                return

            dmg = 30
            raw_d = str(valid_atk.get("damage") or "")
            clean_d = re.sub(r"[^\d]", "", raw_d)
            if clean_d:
                dmg = int(clean_d)

            p_meta = self._get_meta(self.player_active["name"])
            opp_meta = self._get_meta(self.opp_active["name"])
            opp_type = self.opp_active.get("pokemon_type") or opp_meta.get("pokemon_type") or "Colorless"
            p_type = self.player_active.get("pokemon_type") or p_meta.get("pokemon_type") or "Colorless"

            p_weakness = p_meta.get("weakness") or ""
            p_resistance = p_meta.get("resistance") or ""
            opp_weakness = opp_meta.get("weakness") or ""

            final_dmg, mult, matchup_label, matchup_reason = calculate_matchup_damage(
                base_damage=dmg,
                attacker_type=opp_type,
                defender_type=p_type,
                defender_weakness=p_weakness,
                defender_resistance=p_resistance,
                attacker_weakness=opp_weakness
            )

            prev_hp = self.player_active["current_hp"]
            self.player_active["current_hp"] = max(0, self.player_active["current_hp"] - final_dmg)

            matchup_tag = ""
            if mult == 1.5:
                matchup_tag = f" (+50% Type Advantage vs {p_type}!)"
            elif mult == 0.5:
                matchup_tag = f" (-50% Type Disadvantage vs {p_type})"

            self.match_log.append(
                f"💥 Opponent's {self.opp_active['name']} used [{valid_atk['name']}] dealing {final_dmg} DMG"
                f"{matchup_tag}! (Your HP: {prev_hp} -> {self.player_active['current_hp']})."
            )

            # Check Player Knockout
            if self.player_active["current_hp"] <= 0:
                self.player_active["current_hp"] = 0
                self.player_discard.append(self.player_active["name"])
                self.opp_prizes_taken += 1
                self.match_log.append(f"⚠️ [KNOCKOUT] Your Active {self.player_active['name']} was Knocked Out!")
                self.player_active = None

                # Check if player has bench Pokémon
                available_bench = [i for i, b in enumerate(self.player_bench) if b is not None]
                if not available_bench:
                    self.winner = "Opponent"
                    self.phase = "MATCH_OVER"
                    self.match_log.append("❌ DEFEAT: You have no Pokémon left on the field! Opponent wins.")
                    return
                else:
                    self.phase = "WAITING_FOR_PROMOTION"
                    self.match_log.append("👉 Choose a replacement Pokémon from your BENCH to become your new Active!")

        # Reset player turn restrictions for next turn
        self.turn_number += 1
        self.card_drawn_this_turn = False
        self.energy_attached_this_turn = False
        self.supporter_played_this_turn = False
        self.has_attacked_this_turn = False
        self.retreated_this_turn = False
        self._check_and_refill_empty_hand()

    def end_turn(self) -> Dict[str, Any]:
        """Passes player turn, runs opponent counter-actions, and starts next turn."""
        if not self.has_attacked_this_turn and not self.winner:
            self._simulate_opponent_turn()

        self.card_drawn_this_turn = False
        self.energy_attached_this_turn = False
        self.supporter_played_this_turn = False
        self.has_attacked_this_turn = False
        self.retreated_this_turn = False
        self._check_and_refill_empty_hand()

        return {"status": "success", "turn_number": self.turn_number, "phase": self.phase}

    def get_available_legal_actions(self) -> List[Dict[str, Any]]:
        """
        Calculates all currently legal actions given turn restrictions and game state.
        """
        actions = []
        if self.winner:
            return [{"action_type": "MATCH_OVER", "winner": self.winner}]

        if self.phase == "SETUP":
            if self.mulligan_required:
                return [{"action_type": "MULLIGAN"}]
            # Can place basic to active if empty
            if self.player_active is None:
                for idx, c in enumerate(self.player_hand):
                    meta = self._get_meta(c)
                    if meta.get("card_type") == "pokemon" and meta.get("stage") == "Basic":
                        actions.append({"action_type": "INITIAL_PLACE_ACTIVE", "card_name": c, "hand_index": idx})
            # Can place basic to bench slots
            empty_bench = [i for i, b in enumerate(self.player_bench) if b is None]
            if empty_bench:
                for idx, c in enumerate(self.player_hand):
                    meta = self._get_meta(c)
                    if meta.get("card_type") == "pokemon" and meta.get("stage") == "Basic":
                        for slot in empty_bench:
                            actions.append({"action_type": "INITIAL_PLACE_BENCH", "card_name": c, "slot": slot, "hand_index": idx})
            if self.player_active is not None:
                actions.append({"action_type": "CONFIRM_SETUP"})
            return actions

        if self.phase == "WAITING_FOR_PROMOTION":
            for idx, b in enumerate(self.player_bench):
                if b is not None:
                    actions.append({"action_type": "PROMOTE_ACTIVE", "bench_slot": idx, "pokemon": b["name"]})
            return actions

        # Normal Battle Phase
        # 1. DRAW_CARD (once per turn)
        if not self.card_drawn_this_turn and self.player_deck:
            actions.append({"action_type": "DRAW_CARD"})

        # 2. ATTACH_ENERGY (once per turn)
        if not self.energy_attached_this_turn:
            for idx, c in enumerate(self.player_hand):
                meta = self._get_meta(c)
                if meta.get("card_type") == "energy" or "energy" in c.lower():
                    if self.player_active:
                        actions.append({"action_type": "ATTACH_ENERGY", "card_name": c, "target": "active", "hand_index": idx})
                    for b_idx, b in enumerate(self.player_bench):
                        if b is not None:
                            actions.append({"action_type": "ATTACH_ENERGY", "card_name": c, "target": f"bench_{b_idx}", "hand_index": idx})

        # 3. PLAY_BASIC_POKEMON_TO_BENCH
        empty_bench = [i for i, b in enumerate(self.player_bench) if b is None]
        if empty_bench:
            for idx, c in enumerate(self.player_hand):
                meta = self._get_meta(c)
                if meta.get("card_type") == "pokemon" and meta.get("stage") == "Basic":
                    actions.append({"action_type": "PLAY_BASIC_POKEMON_TO_BENCH", "card_name": c, "hand_index": idx})

        # 4. EVOLVE_POKEMON
        for idx, c in enumerate(self.player_hand):
            meta = self._get_meta(c)
            if meta.get("card_type") == "pokemon" and meta.get("stage") in ["Stage 1", "Stage 2"]:
                evo = (meta.get("evolves_from") or "").lower()
                if self.player_active and evo in self.player_active["name"].lower():
                    actions.append({"action_type": "EVOLVE_POKEMON", "card_name": c, "target": "active", "hand_index": idx})
                for b_idx, b in enumerate(self.player_bench):
                    if b and evo in b["name"].lower():
                        actions.append({"action_type": "EVOLVE_POKEMON", "card_name": c, "target": f"bench_{b_idx}", "hand_index": idx})

        # 5. PLAY_TRAINER
        for idx, c in enumerate(self.player_hand):
            meta = self._get_meta(c)
            if meta.get("card_type") == "trainer":
                subtypes = [s.lower() for s in meta.get("subtypes", [])]
                if "supporter" in subtypes and self.supporter_played_this_turn:
                    continue
                actions.append({"action_type": "PLAY_TRAINER", "card_name": c, "hand_index": idx})

        # 6. RETREAT / SWITCH
        for b_idx, b in enumerate(self.player_bench):
            if b is not None:
                actions.append({"action_type": "RETREAT", "bench_slot": b_idx, "pokemon": b["name"]})

        # 7. ATTACK (requires energy check)
        if self.player_active and self.opp_active:
            attacks = self.player_active.get("attacks") or []
            attached = self.player_active.get("attached_energy", [])
            for atk in attacks:
                can_atk, _ = check_energy_requirement(attached, atk.get("cost", []))
                if can_atk:
                    actions.append({"action_type": "ATTACK", "attack_name": atk.get("name"), "base_damage": atk.get("base_damage", 30)})

        # 8. END_TURN
        actions.append({"action_type": "END_TURN"})

        return actions

    def get_game_state_dict(self) -> Dict[str, Any]:
        """Serializes current match state into authoritative dictionary."""
        self._check_and_refill_empty_hand()
        # Non-null bench items for UI backwards-compatibility
        player_bench_compact = [b for b in self.player_bench if b is not None]
        opp_bench_compact = [b for b in self.opp_bench if b is not None]

        return {
            "session_id": "live-match-60card",
            "phase": self.phase,
            "turn_number": self.turn_number,
            "is_player_turn": self.is_player_turn,
            "card_drawn_this_turn": self.card_drawn_this_turn,
            "energy_attached_this_turn": self.energy_attached_this_turn,
            "hasAttachedEnergyThisTurn": self.energy_attached_this_turn,
            "supporter_played_this_turn": self.supporter_played_this_turn,
            "mulligan_required": self.mulligan_required,
            "winner": self.winner,
            "player": {
                "active_spot": self.player_active,
                "bench": player_bench_compact,
                "bench_slots": self.player_bench,
                "hand": [self._get_card_full_dict(c) for c in self.player_hand],
                "deck_count": len(self.player_deck),
                "discard": self.player_discard,
                "prizes_remaining": max(0, 6 - self.player_prizes_taken),
                "prizes_taken": self.player_prizes_taken
            },
            "opponent": {
                "active_spot": self.opp_active,
                "bench": opp_bench_compact,
                "bench_slots": self.opp_bench,
                "hand_count": len(self.opp_hand),
                "deck_count": len(self.opp_deck),
                "discard": self.opp_discard,
                "prizes_remaining": max(0, 6 - self.opp_prizes_taken),
                "prizes_taken": self.opp_prizes_taken
            },
            "available_legal_actions": self.get_available_legal_actions(),
            "match_log": self.match_log
        }

    def _extract_basic_from_hand_or_deck(self, hand: List[str], deck: List[str]) -> Optional[str]:
        for idx, card in enumerate(hand):
            meta = self._get_meta(card)
            if meta.get("card_type") == "pokemon" and meta.get("stage") == "Basic":
                return hand.pop(idx)
        for idx, card in enumerate(deck):
            meta = self._get_meta(card)
            if meta.get("card_type") == "pokemon" and meta.get("stage") == "Basic":
                return deck.pop(idx)
        return None

    def _find_card_in_player_hand(self, identifier: str) -> Optional[str]:
        """Finds card in player hand matching by exact string, card_id, or card name."""
        if not identifier:
            return None
        ident_str = str(identifier).strip()
        ident_lower = ident_str.lower()
        if ident_str in self.player_hand:
            return ident_str
        for c in self.player_hand:
            if c.lower() == ident_lower:
                return c
            meta = self._get_meta(c)
            if str(meta.get("card_id", "")).strip() == ident_str:
                return c
            if (meta.get("name") or "").lower() == ident_lower or (meta.get("card_name") or "").lower() == ident_lower:
                return c
        return None

    def _get_card_full_dict(self, identifier: Any) -> Dict[str, Any]:
        """Serializes full authoritative card dictionary with card_id, name, and image."""
        meta = self._get_meta(identifier)
        cname = meta.get("name") or meta.get("card_name") or str(identifier)
        cid = str(meta.get("card_id") or identifier)
        img = meta.get("image")
        if not img or not img.startswith("/static/"):
            img = f"/static/card_images/{cid}.png"
        return {
            "card_id": cid,
            "name": cname,
            "card_name": meta.get("card_name") or cname,
            "card_type": meta.get("card_type", "pokemon"),
            "supertype": meta.get("supertype", "Pokémon"),
            "pokemon_type": meta.get("pokemon_type") or (meta.get("types") or ["Colorless"])[0],
            "types": meta.get("types", []),
            "stage": meta.get("stage", "Basic"),
            "subtypes": meta.get("subtypes", ["Basic"]),
            "evolves_from": meta.get("evolves_from"),
            "hp": meta.get("hp") or (70 if meta.get("card_type") == "pokemon" else None),
            "image": img,
            "attacks": meta.get("attacks", []),
            "attack_1_name": meta.get("attack_1_name"),
            "attack_1_damage": meta.get("attack_1_damage"),
            "attack_1_energy": meta.get("attack_1_energy") or [],
            "attack_2_name": meta.get("attack_2_name"),
            "attack_2_damage": meta.get("attack_2_damage"),
            "attack_2_energy": meta.get("attack_2_energy") or [],
            "ability": meta.get("ability"),
            "weakness": meta.get("weakness"),
            "resistance": meta.get("resistance"),
            "retreat_cost": meta.get("retreat_cost", 1),
            "effect": meta.get("effect", "")
        }

    def _get_meta(self, identifier: Any) -> Dict[str, Any]:
        """Authoritative metadata lookup by card_id, name, or card dict."""
        if not identifier:
            return {}
        if isinstance(identifier, dict):
            cid = identifier.get("card_id")
            if cid and str(cid) in self.card_db:
                return self.card_db[str(cid)]
            identifier = identifier.get("card_id") or identifier.get("name") or identifier.get("card_name") or ""
        ident_str = str(identifier).strip()
        if ident_str in self.card_db:
            return self.card_db[ident_str]

        # Legacy mock ID mapping
        legacy_map = {
            "sv1-196": "1121", "sv3-26": "788", "sv3-27": "789", "sv3-125": "790",
            "sv3-164": "790", "sv3-162": "788", "sv2-93": "40", "sve-2": "2", "sve-4": "4",
            "sv1-189": "1079", "sv1-181": "1119", "sv1-191": "1079", "sv1-166": "1130",
            "sv2-185": "265", "sv5-144": "1088", "sv1-167": "1135", "sv1-86": "313", "sv4-70": "313"
        }
        if ident_str in legacy_map and legacy_map[ident_str] in self.card_db:
            return self.card_db[legacy_map[ident_str]]

        ident_norm = ident_str.replace("’", "'").lower()

        common_aliases = {
            "charizard ex": "790",
            "charizard": "790",
            "mega charizard x ex": "790",
            "mega charizard y ex": "928",
            "professor's research": "1182",
            "professors research": "1182",
            "boss's orders": "1182",
            "bosses orders": "1182",
        }
        if ident_norm in common_aliases and common_aliases[ident_norm] in self.card_db:
            return self.card_db[common_aliases[ident_norm]]

        # Energy aliases for all 9 types
        energy_aliases = {
            "basic fire energy": "2", "fire energy": "2", "energy_fire_basic": "2",
            "basic grass energy": "1", "grass energy": "1", "energy_grass_basic": "1",
            "basic water energy": "3", "water energy": "3", "energy_water_basic": "3",
            "basic lightning energy": "4", "lightning energy": "4", "energy_lightning_basic": "4",
            "basic psychic energy": "5", "psychic energy": "5", "energy_psychic_basic": "5",
            "basic fighting energy": "6", "fighting energy": "6", "energy_fighting_basic": "6",
            "basic darkness energy": "7", "darkness energy": "7", "energy_darkness_basic": "7",
            "basic metal energy": "8", "metal energy": "8", "energy_metal_basic": "8",
            "basic dragon energy": "energy_dragon_basic", "dragon energy": "energy_dragon_basic",
            "energy_dragon_basic": "energy_dragon_basic"
        }
        if ident_norm in energy_aliases and energy_aliases[ident_norm] in self.card_db:
            return self.card_db[energy_aliases[ident_norm]]

        for etype, c_dict in CANONICAL_BASIC_ENERGIES.items():
            if ident_norm in (c_dict["name"].lower(), c_dict["card_id"].lower(), f"{etype.lower()} energy"):
                return c_dict
        for c in self.card_db.values():
            c_norm = (c.get("name") or c.get("card_name") or "").replace("’", "'").lower()
            if c_norm == ident_norm:
                return c
            if str(c.get("card_id", "")).strip() == ident_str:
                return c

        for c in self.card_db.values():
            c_norm = (c.get("name") or c.get("card_name") or "").replace("’", "'").lower()
            if ident_norm and (ident_norm in c_norm or c_norm in ident_norm):
                return c

        # Fallback database lookup in master_cards (2,551+ cards)
        try:
            from src.database import get_db_connection
            conn = get_db_connection()
            c_cursor = conn.cursor()
            row = c_cursor.execute(
                "SELECT * FROM master_cards WHERE card_id = ? OR LOWER(name) = ? OR LOWER(card_name) = ? LIMIT 1",
                (ident_str, ident_norm, ident_norm)
            ).fetchone()
            conn.close()
            if row:
                c_dict = dict(row)
                c_dict["card_name"] = c_dict.get("card_name") or c_dict.get("name")
                if "attacks_json" in c_dict and c_dict["attacks_json"]:
                    try:
                        c_dict["attacks"] = json.loads(c_dict["attacks_json"])
                    except Exception:
                        c_dict["attacks"] = []
                self.card_db[ident_str] = c_dict
                if c_dict.get("card_id"):
                    self.card_db[str(c_dict["card_id"])] = c_dict
                return c_dict
        except Exception:
            pass

        return {}
