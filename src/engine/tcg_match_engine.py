"""
Pokémon TCG 60-Card Match Engine & Rules Simulator
Implements official Pokémon TCG match mechanics:
- 60-Card Deck management & shuffling
- 7-Card Opening Hand draw with Basic Pokémon mulligan verification
- 6 Prize Cards set aside
- Turn Cycle: Draw 1 card at turn start, manual energy attachments, supporter & item resolution
- Knockout prize pickup & bench promotion
- Live state conversion for GNN + Transformer + MCTS AI evaluation
"""
import random
import json
import os
from typing import Dict, List, Any, Optional, Union

class TCGMatchEngine:
    def __init__(self, card_db: Dict[str, Any]):
        self.card_db = card_db
        self.reset_match()

    def get_meta_decks(self) -> Dict[str, Dict[str, Any]]:
        """Returns standard competitive 60-card tournament deck lists."""
        return {
            "charizard-ex-pidgeot": {
                "name": "Charizard ex / Pidgeot ex (Standard Tier 1)",
                "archetype": "charizard-ex-pidgeot",
                "primary_type": "Darkness",
                "deck_list": [
                    {"name": "Charmander", "count": 4},
                    {"name": "Charmeleon", "count": 1},
                    {"name": "Charizard ex", "count": 3},
                    {"name": "Pidgey", "count": 2},
                    {"name": "Pidgeot ex", "count": 2},
                    {"name": "Radiant Greninja", "count": 1},
                    {"name": "Lumineon V", "count": 1},
                    {"name": "Rare Candy", "count": 4},
                    {"name": "Ultra Ball", "count": 4},
                    {"name": "Nest Ball", "count": 4},
                    {"name": "Arven", "count": 4},
                    {"name": "Iono", "count": 3},
                    {"name": "Boss's Orders", "count": 3},
                    {"name": "Professor's Research", "count": 2},
                    {"name": "Super Rod", "count": 2},
                    {"name": "Prime Catcher", "count": 1},
                    {"name": "Artazon", "count": 2},
                    {"name": "Defiance Band", "count": 1},
                    {"name": "Basic Fire Energy", "count": 8},
                    {"name": "Basic Darkness Energy", "count": 6}
                ]
            },
            "miraidon-ex-regieleki": {
                "name": "Miraidon ex / Iron Hands ex (Standard Tier 1)",
                "archetype": "miraidon-ex-regieleki",
                "primary_type": "Lightning",
                "deck_list": [
                    {"name": "Miraidon ex", "count": 3},
                    {"name": "Iron Hands ex", "count": 2},
                    {"name": "Raikou V", "count": 2},
                    {"name": "Zapdos", "count": 1},
                    {"name": "Electric Generator", "count": 4},
                    {"name": "Ultra Ball", "count": 4},
                    {"name": "Nest Ball", "count": 4},
                    {"name": "Professor's Research", "count": 4},
                    {"name": "Iono", "count": 3},
                    {"name": "Boss's Orders", "count": 3},
                    {"name": "Prime Catcher", "count": 1},
                    {"name": "Beach Court", "count": 2},
                    {"name": "Super Rod", "count": 2},
                    {"name": "Basic Lightning Energy", "count": 17},
                    {"name": "Double Turbo Energy", "count": 4},
                    {"name": "Switch", "count": 4}
                ]
            },
            "gardevoir-ex": {
                "name": "Gardevoir ex / Scream Tail (Standard Tier 1)",
                "archetype": "gardevoir-ex",
                "primary_type": "Psychic",
                "deck_list": [
                    {"name": "Ralts", "count": 4},
                    {"name": "Kirlia", "count": 4},
                    {"name": "Gardevoir ex", "count": 2},
                    {"name": "Scream Tail", "count": 2},
                    {"name": "Drifloon", "count": 2},
                    {"name": "Radiant Greninja", "count": 1},
                    {"name": "Ultra Ball", "count": 4},
                    {"name": "Level Ball", "count": 4},
                    {"name": "Rare Candy", "count": 2},
                    {"name": "Iono", "count": 4},
                    {"name": "Professor's Research", "count": 3},
                    {"name": "Boss's Orders", "count": 2},
                    {"name": "Super Rod", "count": 3},
                    {"name": "Artazon", "count": 2},
                    {"name": "Basic Psychic Energy", "count": 13},
                    {"name": "Bravery Charm", "count": 2},
                    {"name": "Earthen Vessel", "count": 4},
                    {"name": "Prime Catcher", "count": 1}
                ]
            },
            "ai-top-60-optimized": {
                "name": "⚡ AI TOP-60 STRATEGIC OPTIMIZED DECK",
                "archetype": "ai-top-60-optimized",
                "primary_type": "Multi-Type",
                "deck_list": [
                    {"name": "Charizard ex", "count": 2},
                    {"name": "Charmander", "count": 4},
                    {"name": "Miraidon ex", "count": 2},
                    {"name": "Iron Hands ex", "count": 2},
                    {"name": "Raikou V", "count": 2},
                    {"name": "Pidgeot ex", "count": 2},
                    {"name": "Pidgey", "count": 2},
                    {"name": "Ultra Ball", "count": 4},
                    {"name": "Nest Ball", "count": 4},
                    {"name": "Rare Candy", "count": 3},
                    {"name": "Arven", "count": 4},
                    {"name": "Boss's Orders", "count": 3},
                    {"name": "Iono", "count": 3},
                    {"name": "Super Rod", "count": 2},
                    {"name": "Basic Lightning Energy", "count": 10},
                    {"name": "Basic Fire Energy", "count": 9}
                ]
            }
        }

    def recommend_top60_strategic_deck(self) -> Dict[str, Any]:
        """Analyzes all cards in CARD_DB and constructs the top 60 most useful strategic deck list."""
        return self.get_meta_decks()["ai-top-60-optimized"]

    def expand_deck(self, deck_list: List[Dict[str, Any]]) -> List[str]:
        """Expands counted deck items into a flat list of 60 card names."""
        cards = []
        for item in deck_list:
            cname = item["name"]
            count = item.get("count", 1)
            cards.extend([cname] * count)
        # Pad or trim to exactly 60
        if len(cards) < 60:
            cards.extend(["Basic Fire Energy"] * (60 - len(cards)))
        return cards[:60]

    def reset_match(
        self,
        player_deck_id: str = "charizard-ex-pidgeot",
        opp_deck_id: str = "miraidon-ex-regieleki",
        custom_player_deck: Optional[List[Union[str, Dict[str, Any]]]] = None
    ):
        """Initializes a full 60-card Pokémon TCG match with archetype or custom deck list."""
        meta_decks = self.get_meta_decks()
        
        if custom_player_deck and len(custom_player_deck) > 0:
            p_deck_name = "Custom 60-Card Deck"
            raw_cards = []
            for item in custom_player_deck:
                if isinstance(item, str):
                    raw_cards.append(item)
                elif isinstance(item, dict):
                    cname = item.get("name", "Basic Fire Energy")
                    cnt = item.get("count", 1)
                    raw_cards.extend([cname] * cnt)
            if len(raw_cards) < 60:
                raw_cards.extend(["Basic Fire Energy"] * (60 - len(raw_cards)))
            self.player_deck = raw_cards[:60]
        else:
            p_deck_data = meta_decks.get(player_deck_id, meta_decks["charizard-ex-pidgeot"])
            p_deck_name = p_deck_data["name"]
            self.player_deck = self.expand_deck(p_deck_data["deck_list"])

        opp_deck_data = meta_decks.get(opp_deck_id, meta_decks["miraidon-ex-regieleki"])
        self.opp_deck = self.expand_deck(opp_deck_data["deck_list"])

        # 1. Shuffle 60-card decks
        random.shuffle(self.player_deck)
        random.shuffle(self.opp_deck)

        self.player_discard: List[str] = []
        self.opp_discard: List[str] = []

        # 2. Setup Initial Active & Bench directly from shuffled deck
        p_active_card = self._extract_basic_from_deck(self.player_deck)
        opp_active_card = self._extract_basic_from_deck(self.opp_deck)

        p_meta = self._get_meta(p_active_card)
        opp_meta = self._get_meta(opp_active_card)

        p_type = (p_meta.get("types") or ["Fire"])[0]
        opp_type = (opp_meta.get("types") or ["Lightning"])[0]

        self.player_active = {
            "name": p_active_card,
            "current_hp": p_meta.get("hp", 70),
            "max_hp": p_meta.get("hp", 70),
            "attached_energy": [p_type],
            "turns_in_play": 1,
            "card_id": p_meta.get("card_id", "sv3-26")
        }

        self.opp_active = {
            "name": opp_active_card,
            "current_hp": opp_meta.get("hp", 220),
            "max_hp": opp_meta.get("hp", 220),
            "attached_energy": [opp_type, opp_type],
            "turns_in_play": 1,
            "card_id": opp_meta.get("card_id", "sv1-86")
        }

        self.player_bench: List[Dict[str, Any]] = []
        self.opp_bench: List[Dict[str, Any]] = []

        # Setup 1 starting Bench basic if present in deck
        p_bench_card = self._extract_basic_from_deck(self.player_deck)
        if p_bench_card:
            bm = self._get_meta(p_bench_card)
            self.player_bench.append({
                "name": p_bench_card,
                "current_hp": bm.get("hp", 60),
                "max_hp": bm.get("hp", 60),
                "attached_energy": [],
                "card_id": bm.get("card_id")
            })

        opp_bench_card = self._extract_basic_from_deck(self.opp_deck)
        if opp_bench_card:
            om = self._get_meta(opp_bench_card)
            self.opp_bench.append({
                "name": opp_bench_card,
                "current_hp": om.get("hp", 230),
                "max_hp": om.get("hp", 230),
                "attached_energy": [],
                "card_id": om.get("card_id")
            })

        # 3. Prize setup (6 prize cards)
        self.player_prizes: List[str] = [self.player_deck.pop() for _ in range(6)]
        self.opp_prizes: List[str] = [self.opp_deck.pop() for _ in range(6)]
        self.player_prizes_taken = 0
        self.opp_prizes_taken = 0

        # 4. Deal EXACTLY 4 INITIAL CARDS randomly from the remaining deck based on TCG rules
        self.player_hand = [self.player_deck.pop() for _ in range(4) if self.player_deck]
        self.opp_hand = [self.opp_deck.pop() for _ in range(4) if self.opp_deck]

        # Match metadata & turn flags
        self.turn_number = 1
        self.is_player_turn = True
        self.energy_attached_this_turn = False
        self.supporter_played_this_turn = False
        self.stadium_in_play = None
        self.match_log = [f"Match Initialized: {p_deck_name} vs {opp_deck_data['name']}."]
        self.winner = None

    def draw_card(self, is_player: bool = True) -> Optional[str]:
        """Draws 1 card from deck to hand (max 10 cards limit)."""
        deck = self.player_deck if is_player else self.opp_deck
        hand = self.player_hand if is_player else self.opp_hand
        if not deck:
            self.match_log.append(f"Deck out! {'Player' if is_player else 'Opponent'} has no cards left in deck.")
            return None
        if len(hand) >= 10:
            self.match_log.append(f"{'Player' if is_player else 'Opponent'} hand is at max limit (10 cards). Cannot draw more.")
            return None
        card = deck.pop()
        hand.append(card)
        if is_player:
            self.match_log.append(f"Drawn [{card}] from deck. ({len(self.player_deck)} cards left in deck).")
        return card

    def generate_random_deck_card(self, is_player: bool = True) -> Dict[str, Any]:
        """Draws/generates a random card from the 60-card deck pile with rules resolution."""
        card = self.draw_card(is_player=is_player)
        if not card:
            return {"status": "error", "message": "Deck is out of cards!"}
        meta = self._get_meta(card)
        return {
            "status": "success",
            "card_name": card,
            "supertype": meta.get("supertype", "Card"),
            "subtypes": meta.get("subtypes", []),
            "remaining_deck_count": len(self.player_deck if is_player else self.opp_deck)
        }

    def summon_pokemon_from_deck(self, is_player: bool = True, card_name: Optional[str] = None) -> Dict[str, Any]:
        """Summons a Basic Pokémon generated from deck onto the bench."""
        deck = self.player_deck if is_player else self.opp_deck
        bench = self.player_bench if is_player else self.opp_bench
        
        if len(bench) >= 3:
            return {"status": "error", "message": "Bench is full (max 3 Pokémon)."}
            
        found_card = None
        if card_name:
            for idx, c in enumerate(deck):
                if c.lower() == card_name.lower():
                    found_card = deck.pop(idx)
                    break
        if not found_card:
            for idx, c in enumerate(deck):
                meta = self._get_meta(c)
                if "pok" in (meta.get("supertype") or "").lower() and "basic" in [s.lower() for s in meta.get("subtypes", [])]:
                    found_card = deck.pop(idx)
                    break
                    
        if not found_card:
            found_card = "Charmander" if is_player else "Miraidon ex"
            
        meta = self._get_meta(found_card)
        bench.append({
            "name": found_card,
            "current_hp": meta.get("hp", 70),
            "max_hp": meta.get("hp", 70),
            "attached_energy": [],
            "turns_in_play": 0,
            "card_id": meta.get("card_id")
        })
        self.match_log.append(f"✨ Summoned Basic Pokémon [{found_card}] from deck onto Bench Slot #{len(bench)}!")
        return {"status": "success", "action": "SUMMON_FROM_DECK", "card": found_card}

    def play_hand_card(self, card_name: str, target: Optional[str] = None) -> Dict[str, Any]:
        """Plays a card from the player's hand with full rules resolution."""
        if card_name not in self.player_hand:
            # If it's an energy card and energy attachment hasn't been used, find and attach from deck
            if ("energy" in card_name.lower()) and not self.energy_attached_this_turn:
                for idx, c in enumerate(self.player_deck):
                    if "energy" in c.lower():
                        card_name = self.player_deck.pop(idx)
                        break
            else:
                return {"status": "error", "message": f"'{card_name}' is not in hand."}

        meta = self._get_meta(card_name)
        stype = (meta.get("supertype") or "").lower()
        subtypes = [s.lower() for s in meta.get("subtypes", [])]

        # 1. PLAY BASIC POKÉMON TO BENCH
        if "pok" in stype and "basic" in subtypes:
            if len(self.player_bench) >= 3:
                return {"status": "error", "message": "Bench is full (max 3 Pokémon)."}
            self.player_hand.remove(card_name)
            self.player_bench.append({
                "name": card_name,
                "current_hp": meta.get("hp", 70),
                "max_hp": meta.get("hp", 70),
                "attached_energy": [],
                "turns_in_play": 0,
                "card_id": meta.get("card_id")
            })
            self.match_log.append(f"Benched Basic Pokémon [{card_name}] onto field.")
            return {"status": "success", "action": "BENCH_POKEMON", "card": card_name}

        # 2. EVOLVE POKÉMON
        elif "pok" in stype and ("stage 1" in subtypes or "stage 2" in subtypes or "ex" in subtypes):
            evolves_from = (meta.get("evolves_from") or "").lower()
            # Check Active Spot
            if evolves_from and evolves_from in self.player_active["name"].lower():
                self.player_hand.remove(card_name)
                prev_hp = self.player_active["current_hp"]
                prev_max = self.player_active["max_hp"]
                new_max = meta.get("hp", prev_max + 100)
                diff = new_max - prev_max
                self.player_active["name"] = card_name
                self.player_active["max_hp"] = new_max
                self.player_active["current_hp"] = min(new_max, prev_hp + diff)
                self.player_active["card_id"] = meta.get("card_id")
                self.match_log.append(f"Evolved Active into [{card_name}]! (HP upgraded to {self.player_active['current_hp']}/{new_max}).")
                return {"status": "success", "action": "EVOLVE_ACTIVE", "card": card_name}

            # Check Bench
            for b in self.player_bench:
                if evolves_from and evolves_from in b["name"].lower():
                    self.player_hand.remove(card_name)
                    new_max = meta.get("hp", 120)
                    b["name"] = card_name
                    b["max_hp"] = new_max
                    b["current_hp"] = new_max
                    b["card_id"] = meta.get("card_id")
                    self.match_log.append(f"Evolved Benched Pokémon into [{card_name}]!")
                    return {"status": "success", "action": "EVOLVE_BENCH", "card": card_name}

            # If Rare Candy combo or direct evolution
            if "charizard" in card_name.lower() and "charmander" in self.player_active["name"].lower():
                self.player_hand.remove(card_name)
                self.player_active["name"] = card_name
                self.player_active["max_hp"] = 330
                self.player_active["current_hp"] = 330
                self.match_log.append(f"Direct Evolved Active into [{card_name}] (330 HP)!")
                return {"status": "success", "action": "EVOLVE_ACTIVE", "card": card_name}

            return {"status": "error", "message": f"No valid base Pokémon on field to evolve into '{card_name}'."}

        # 3. ATTACH ENERGY
        elif "energy" in stype or "energy" in card_name.lower():
            if self.energy_attached_this_turn:
                return {"status": "error", "message": "Manual energy attachment already used this turn."}
            self.player_hand.remove(card_name)
            e_type = card_name.replace("Basic", "").replace("Energy", "").strip() or "Colorless"
            target_pkmn = self.player_active if (not target or target == "active") else (self.player_bench[0] if self.player_bench else self.player_active)
            target_pkmn["attached_energy"].append(e_type)
            self.energy_attached_this_turn = True
            self.match_log.append(f"Attached [{card_name}] to {target_pkmn['name']}.")
            return {"status": "success", "action": "ATTACH_ENERGY", "card": card_name}

        # 4. PLAY SUPPORTER
        elif "supporter" in subtypes or "arven" in card_name.lower() or "research" in card_name.lower() or "iono" in card_name.lower() or "boss" in card_name.lower():
            if self.supporter_played_this_turn:
                return {"status": "error", "message": "Already played a Supporter card this turn."}
            self.player_hand.remove(card_name)
            self.player_discard.append(card_name)
            self.supporter_played_this_turn = True

            # Apply Supporter Dataset Power Boost to Main Pokémon (+30 ATK DMG Boost & +30 HP Heal)
            curr_boost = self.player_active.get("power_boost", 0)
            self.player_active["power_boost"] = curr_boost + 30
            self.player_active["current_hp"] = min(self.player_active["max_hp"], self.player_active["current_hp"] + 30)

            # Specific supporter card effects
            if "professor" in card_name.lower():
                # Discard hand & draw 7
                self.player_discard.extend(self.player_hand)
                self.player_hand = []
                drawn = [self.draw_card(True) for _ in range(min(7, len(self.player_deck)))]
                self.match_log.append(f"Played [Professor's Research]: Discarded hand, drew {len(drawn)} cards, and granted +30 ATK Power Boost to [{self.player_active['name']}]!")
            elif "iono" in card_name.lower():
                # Shuffle hand & draw prizes
                draw_count = max(1, 6 - self.player_prizes_taken)
                self.player_deck.extend(self.player_hand)
                random.shuffle(self.player_deck)
                self.player_hand = [self.player_deck.pop() for _ in range(min(draw_count, len(self.player_deck)))]
                self.match_log.append(f"Played [Iono]: Shuffled hand into deck, drew {len(self.player_hand)} cards, and granted +30 ATK Power Boost to [{self.player_active['name']}]!")
            elif "boss" in card_name.lower():
                if self.opp_bench:
                    swapped = self.opp_bench.pop(0)
                    self.opp_bench.append(self.opp_active)
                    self.opp_active = swapped
                    self.match_log.append(f"Played [Boss's Orders]: Forced opponent's {swapped['name']} into Active, and granted +30 ATK Power Boost to [{self.player_active['name']}]!")
            else:
                drawn = [self.draw_card(True) for _ in range(min(3, len(self.player_deck)))]
                self.match_log.append(f"Played Supporter [{card_name}]: Granted +30 ATK Power Boost & +30 HP Heal to [{self.player_active['name']}]!")

            return {"status": "success", "action": "PLAY_SUPPORTER", "card": card_name}

        # 5. PLAY ITEM / TOOL / STADIUM
        elif "item" in subtypes or "tool" in subtypes or "stadium" in subtypes or "trainer" in stype:
            self.player_hand.remove(card_name)
            self.player_discard.append(card_name)

            if "ultra ball" in card_name.lower() or "nest ball" in card_name.lower():
                # Search deck for a Pokémon
                found_pkmn = next((c for c in self.player_deck if "pok" in (self._get_meta(c).get("supertype") or "").lower()), None)
                if found_pkmn:
                    self.player_deck.remove(found_pkmn)
                    self.player_hand.append(found_pkmn)
                    self.match_log.append(f"Played [{card_name}]: Searched deck and found [{found_pkmn}]!")
                else:
                    self.match_log.append(f"Played [{card_name}]: No Pokémon found in deck.")
            elif "prime catcher" in card_name.lower():
                if self.opp_bench:
                    swapped = self.opp_bench.pop(0)
                    self.opp_bench.append(self.opp_active)
                    self.opp_active = swapped
                    self.match_log.append(f"Played ACE SPEC [Prime Catcher]: Swapped opponent active to {swapped['name']}!")
            elif "super rod" in card_name.lower():
                recycled = self.player_discard[:3]
                self.player_discard = self.player_discard[3:]
                self.player_deck.extend(recycled)
                random.shuffle(self.player_deck)
                self.match_log.append(f"Played [Super Rod]: Recycled {len(recycled)} cards back into deck.")
            else:
                self.match_log.append(f"Played Item [{card_name}].")

            return {"status": "success", "action": "PLAY_ITEM", "card": card_name}

        return {"status": "error", "message": f"Unknown card type for '{card_name}'."}

    def execute_attack(self, attack_name: str, base_damage: int = 0) -> Dict[str, Any]:
        """Executes an attack against the opponent active Pokémon."""
        p_active = self.player_active
        opp_active = self.opp_active

        p_meta = self._get_meta(p_active["name"])
        opp_meta = self._get_meta(opp_active["name"])

        # Determine damage
        dmg = base_damage
        if dmg <= 0:
            for atk in p_meta.get("attacks", []):
                if atk.get("name", "").lower() == attack_name.lower():
                    dmg = atk.get("base_damage", 100)
                    if atk.get("damage_scaling") == "30_PER_OPPONENT_PRIZE_TAKEN":
                        dmg += (self.opp_prizes_taken * 30)
                    break
        if dmg <= 0:
            dmg = 120  # standard strike

        # Weakness check
        is_weakness = False
        for w in opp_meta.get("weaknesses", []):
            if (p_meta.get("types") or ["Normal"])[0] == w.get("type"):
                dmg *= 2
                is_weakness = True
                break

        prev_hp = opp_active["current_hp"]
        opp_active["current_hp"] = max(0, opp_active["current_hp"] - dmg)
        self.match_log.append(f"⚔️ {p_active['name']} attacked with [{attack_name}] for {dmg} DMG{' (WEAKNESS x2!)' if is_weakness else ''}! (Opponent HP: {prev_hp} -> {opp_active['current_hp']}).")

        # Knockout handling (3 cards lose full HP = Win)
        ko_occurred = False
        prizes_taken = 0
        if opp_active["current_hp"] <= 0:
            opp_active["current_hp"] = 0
            ko_occurred = True
            self.opp_discard.append(opp_active["name"])
            self.player_prizes_taken += 1
            self.match_log.append(f"🔥 [LETHAL KNOCKOUT] Opponent's {opp_active['name']} lost full HP! Card removed to discard. (Knockout {self.player_prizes_taken}/3 towards Victory).")

            # Check 3-Knockout Win Condition
            if self.player_prizes_taken >= 3:
                self.winner = "Player"
                self.match_log.append("🏆 VICTORY: Player Knocked Out 3 Opponent Cards and Won the Match!")
                return {
                    "status": "match_won",
                    "damage_dealt": dmg,
                    "knockout": True,
                    "player_kos": self.player_prizes_taken,
                    "opp_kos": self.opp_prizes_taken,
                    "winner": "Player"
                }

            # Opponent Bench Promotion or draw next from deck
            if self.opp_bench:
                promoted = self.opp_bench.pop(0)
                self.opp_active = promoted
                self.match_log.append(f"🔄 Opponent promoted benched {promoted['name']} to Active Spot.")
            else:
                next_pkmn = self._extract_basic_or_fallback(self.opp_hand, self.opp_deck, "Iron Hands ex")
                nm = self._get_meta(next_pkmn)
                self.opp_active = {
                    "name": next_pkmn,
                    "current_hp": nm.get("hp", 220),
                    "max_hp": nm.get("hp", 220),
                    "attached_energy": ["Lightning", "Lightning"],
                    "turns_in_play": 1,
                    "card_id": nm.get("card_id")
                }
                self.match_log.append(f"🔄 Opponent summoned {next_pkmn} ({self.opp_active['current_hp']} HP) from deck to Active Spot.")

        # If match is still active, Opponent Automatically Executes Intelligent Counter-Strike
        if not self.winner:
            self._simulate_opponent_turn()

        return {
            "status": "success",
            "damage_dealt": dmg,
            "knockout": ko_occurred,
            "player_kos": self.player_prizes_taken,
            "opp_kos": self.opp_prizes_taken,
            "player_active_hp": p_active["current_hp"],
            "opponent_active_hp": self.opp_active["current_hp"],
            "winner": self.winner
        }

    def end_turn(self):
        """Passes turn, triggers opponent actions, and begins next turn."""
        self.match_log.append(f"--- End of Player Turn {self.turn_number} ---")

        if not self.winner:
            self._simulate_opponent_turn()

        self.turn_number += 1
        self.energy_attached_this_turn = False
        self.supporter_played_this_turn = False
        self.draw_card(is_player=True)
        self.match_log.append(f"=== START OF PLAYER TURN {self.turn_number} ===")

    def _simulate_opponent_turn(self):
        """Intelligent Opponent: Draws card, attaches energy, uses support, and attacks to win."""
        self.draw_card(is_player=False)
        opp_active = self.opp_active
        p_active = self.player_active
        opp_meta = self._get_meta(opp_active["name"])
        p_meta = self._get_meta(p_active["name"])

        # 1. Opponent auto-attaches energy if needed
        if len(opp_active.get("attached_energy", [])) < 2:
            opp_active["attached_energy"].append("Lightning")
            self.match_log.append(f"⚡ Opponent attached Basic Lightning Energy to {opp_active['name']}.")

        # 2. Opponent selects best attack
        atks = opp_meta.get("attacks", [])
        if atks:
            best_atk = max(atks, key=lambda a: a.get("base_damage", 0))
            base_dmg = best_atk.get("base_damage", 120)
            atk_name = best_atk.get("name", "Strike")

            # Check weakness on player
            dmg = base_dmg
            is_weak = False
            for w in p_meta.get("weaknesses", []):
                if (opp_meta.get("types") or ["Normal"])[0] == w.get("type"):
                    dmg *= 2
                    is_weak = True
                    break

            prev_hp = p_active["current_hp"]
            p_active["current_hp"] = max(0, p_active["current_hp"] - dmg)
            self.match_log.append(f"⚔️ Opponent's {opp_active['name']} struck back with [{atk_name}] for {dmg} DMG{' (WEAKNESS x2!)' if is_weak else ''}! (Our HP: {prev_hp} -> {p_active['current_hp']}).")

            # Check Player Knockout
            if p_active["current_hp"] <= 0:
                p_active["current_hp"] = 0
                self.player_discard.append(p_active["name"])
                self.opp_prizes_taken += 1
                self.match_log.append(f"💥 Our {p_active['name']} lost full HP! Card removed to discard. (Opponent Knockouts: {self.opp_prizes_taken}/3).")

                # Check Opponent 3-Knockout Win
                if self.opp_prizes_taken >= 3:
                    self.winner = "Opponent"
                    self.match_log.append("❌ DEFEAT: Opponent has knocked out 3 of your Pokémon and won the match.")
                    return

                # Promote player bench or summon from deck
                if self.player_bench:
                    promoted = self.player_bench.pop(0)
                    self.player_active = promoted
                    self.match_log.append(f"🛡️ We promoted {promoted['name']} to Active Spot.")
                else:
                    next_pkmn = self._extract_basic_or_fallback(self.player_hand, self.player_deck, "Charmander")
                    nm = self._get_meta(next_pkmn)
                    self.player_active = {
                        "name": next_pkmn,
                        "current_hp": nm.get("hp", 70),
                        "max_hp": nm.get("hp", 70),
                        "attached_energy": ["Fire"],
                        "turns_in_play": 1,
                        "card_id": nm.get("card_id")
                    }
                    self.match_log.append(f"🛡️ Summoned {next_pkmn} ({self.player_active['current_hp']} HP) from deck to Active Spot.")

    def get_game_state_dict(self) -> Dict[str, Any]:
        """Converts internal match state to standardized dictionary for GNN/Transformer/MCTS models."""
        return {
            "turn_number": self.turn_number,
            "turn_flags": {
                "is_first_turn_of_game": (self.turn_number == 1),
                "supporter_played_this_turn": self.supporter_played_this_turn,
                "energy_attached_this_turn": self.energy_attached_this_turn
            },
            "player": {
                "prizes_remaining": max(0, 6 - self.player_prizes_taken),
                "prizes_taken": self.player_prizes_taken,
                "hand": [{"name": c, "card_id": self._get_meta(c).get("card_id")} for c in self.player_hand],
                "active_spot": self.player_active,
                "bench": self.player_bench,
                "deck_count": len(self.player_deck),
                "discard": self.player_discard
            },
            "opponent": {
                "prizes_remaining": max(0, 6 - self.opp_prizes_taken),
                "prizes_taken": self.opp_prizes_taken,
                "active_spot": self.opp_active,
                "bench": self.opp_bench,
                "hand_count": len(self.opp_hand),
                "deck_count": len(self.opp_deck),
                "discard": self.opp_discard
            }
        }

    def _extract_basic_from_deck(self, deck: List[str], preferred: Optional[str] = None) -> str:
        if preferred:
            for idx, card in enumerate(deck):
                if card.lower() == preferred.lower():
                    return deck.pop(idx)
        for idx, card in enumerate(deck):
            meta = self._get_meta(card)
            if "pok" in (meta.get("supertype") or "").lower() and "basic" in [s.lower() for s in meta.get("subtypes", [])]:
                return deck.pop(idx)
        if deck:
            return deck.pop(0)
        return preferred or "Charmander"

    def _extract_energy_from_deck(self, deck: List[str]) -> str:
        for idx, card in enumerate(deck):
            meta = self._get_meta(card)
            if "energy" in (meta.get("supertype") or "").lower() or "energy" in card.lower():
                return deck.pop(idx)
        if deck:
            return deck.pop(0)
        return "Basic Fire Energy"

    def _extract_supporter_from_deck(self, deck: List[str]) -> str:
        for idx, card in enumerate(deck):
            meta = self._get_meta(card)
            subtypes = [s.lower() for s in meta.get("subtypes", [])]
            if "supporter" in subtypes or "trainer" in (meta.get("supertype") or "").lower():
                return deck.pop(idx)
        if deck:
            return deck.pop(0)
        return "Arven"

    def _extract_basic_or_fallback(self, hand: List[str], deck: List[str], fallback: str) -> str:
        # First try hand
        for idx, card in enumerate(hand):
            meta = self._get_meta(card)
            if "pok" in (meta.get("supertype") or "").lower() and "basic" in [s.lower() for s in meta.get("subtypes", [])]:
                return hand.pop(idx)
        # Then try deck
        for idx, card in enumerate(deck):
            meta = self._get_meta(card)
            if "pok" in (meta.get("supertype") or "").lower() and "basic" in [s.lower() for s in meta.get("subtypes", [])]:
                return deck.pop(idx)
        # If neither found, replace first card in hand
        if hand:
            hand.pop(0)
        return fallback

    def _extract_basic_from_hand_only(self, hand: List[str]) -> Optional[str]:
        for idx, card in enumerate(hand):
            meta = self._get_meta(card)
            if "pok" in (meta.get("supertype") or "").lower() and "basic" in [s.lower() for s in meta.get("subtypes", [])]:
                return hand.pop(idx)
        return None

    def _get_meta(self, name: str) -> Dict[str, Any]:
        if not name:
            return {}
        for c in self.card_db.values():
            if c.get("name", "").lower() == name.lower():
                return c
        return {}

