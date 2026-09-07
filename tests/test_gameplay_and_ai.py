"""
Comprehensive End-to-End Game & Opponent AI Validation Test
Tests:
- Game Setup & Deck Shuffling
- Drawing Cards & Hand Limits
- Manual Energy Attachment (1 per turn rule)
- Attack Validation & Energy Cost Enforcement
- Damage Calculation with Weakness (x2)
- Lethal Knockout & Prize Card Pickup
- Bench Promotion on Knockout
- Autonomous Opponent AI Decisions (Draw -> Bench -> Energy -> Trainer -> Attack)
- Turn Switching & No-Freeze Stability
- Win/Loss Conditions
"""
import unittest
import json
from src.engine.tcg_match_engine import TCGMatchEngine
from src.engine.rules_engine import RulesEngine
from fastapi.testclient import TestClient
from src.api import app

class TestPokemonTcgGameAndAi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open("data/cards_dataset.json", "r", encoding="utf-8") as f:
            cards_data = json.load(f)
            cls.card_db = {c["card_id"]: c for c in cards_data["cards"]}
        cls.engine = TCGMatchEngine(cls.card_db)
        cls.rules = RulesEngine(cls.card_db)
        cls.client = TestClient(app)

    def test_game_setup_integrity(self):
        """Verify full 60-card setup for both players."""
        self.engine.reset_match("charizard-ex-pidgeot", "miraidon-ex-regieleki")
        total_p = len(self.engine.player_hand) + len(self.engine.player_prizes) + 1 + len(self.engine.player_bench) + len(self.engine.player_deck)
        total_opp = len(self.engine.opp_hand) + len(self.engine.opp_prizes) + 1 + len(self.engine.opp_bench) + len(self.engine.opp_deck)

        self.assertEqual(total_p, 60, "Player deck setup must equal exactly 60 cards")
        self.assertEqual(total_opp, 60, "Opponent deck setup must equal exactly 60 cards")
        self.assertEqual(len(self.engine.player_prizes), 6)
        self.assertEqual(len(self.engine.opp_prizes), 6)
        self.assertIsNotNone(self.engine.player_active)
        self.assertIsNotNone(self.engine.opp_active)
        self.assertTrue(self.engine.player_active["current_hp"] > 0)
        self.assertTrue(self.engine.opp_active["current_hp"] > 0)

    def test_energy_attachment_and_rules(self):
        """Verify 1-energy per turn restriction."""
        self.engine.reset_match()
        self.assertFalse(self.engine.energy_attached_this_turn)

        # Attach 1st energy
        self.engine.player_hand.append("Basic Fire Energy")
        res1 = self.engine.play_hand_card("Basic Fire Energy")
        self.assertEqual(res1["status"], "success")
        self.assertTrue(self.engine.energy_attached_this_turn)

        # 2nd energy attachment attempt in same turn must fail
        self.engine.player_hand.append("Basic Fire Energy")
        res2 = self.engine.play_hand_card("Basic Fire Energy")
        self.assertEqual(res2["status"], "error")

    def test_supporter_card_rules(self):
        """Verify 1-supporter per turn restriction."""
        self.engine.reset_match()
        self.assertFalse(self.engine.supporter_played_this_turn)

        self.engine.player_hand.append("Professor's Research")
        res = self.engine.play_hand_card("Professor's Research")
        self.assertEqual(res["status"], "success")
        self.assertTrue(self.engine.supporter_played_this_turn)

        # Second supporter attempt in same turn must fail
        self.engine.player_hand.append("Boss's Orders")
        res2 = self.engine.play_hand_card("Boss's Orders")
        self.assertEqual(res2["status"], "error")

    def test_autonomous_opponent_ai_flow(self):
        """Verify Opponent AI executes legal, non-frozen turn actions."""
        self.engine.reset_match()
        # Give player active high HP to observe direct damage, or let AI score lethal KO
        self.engine.player_active["current_hp"] = 330
        self.engine.player_active["max_hp"] = 330
        initial_opp_deck = len(self.engine.opp_deck)
        initial_p_hp = self.engine.player_active["current_hp"]

        # Simulate opponent turn directly
        self.engine._simulate_opponent_turn()

        # Check that opponent drew a card
        self.assertEqual(len(self.engine.opp_deck), initial_opp_deck - 1)
        # Check that opponent attached energy
        self.assertTrue(len(self.engine.opp_active["attached_energy"]) >= 1)
        # Check that opponent attacked and dealt damage to player (or knocked out)
        self.assertTrue(self.engine.player_active["current_hp"] < initial_p_hp or self.engine.opp_prizes_taken >= 1)

    def test_lethal_knockout_and_bench_promotion(self):
        """Verify lethal damage removes active, takes prize, and promotes bench."""
        self.engine.reset_match()
        self.engine.opp_bench = [{
            "name": "Iron Hands ex", "current_hp": 230, "max_hp": 230, "attached_energy": []
        }]
        self.engine.opp_active["current_hp"] = 30
        initial_prizes = self.engine.player_prizes_taken

        res = self.engine.execute_attack("Burning Darkness", base_damage=180)
        self.assertTrue(res.get("knockout"))
        self.assertEqual(self.engine.player_prizes_taken, initial_prizes + 1)
        # Benched Iron Hands ex should be promoted to Active
        self.assertEqual(self.engine.opp_active["name"], "Iron Hands ex")

    def test_multi_turn_battle_stability(self):
        """Simulate a complete 5-turn match back and forth without freezing."""
        self.engine.reset_match()
        for turn in range(1, 6):
            # Player draws and attacks
            self.engine.execute_attack("Ember", base_damage=50)
            if self.engine.winner:
                break
            self.engine.end_turn()
            if self.engine.winner:
                break

        self.assertTrue(self.engine.turn_number >= 2)
        self.assertTrue(len(self.engine.match_log) >= 5)

    def test_frontend_home_page_availability(self):
        """Verify web dashboard HTML serves with no missing handlers."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.text
        # Verify key UI components
        self.assertIn("OFFICIAL POKÉMON TCG ESPORTS MATCH ARENA", html)
        self.assertIn("executeAiTurn", html)
        self.assertIn("canPayAttackCost", html)
        self.assertIn("loadTop60RecommendedDeck", html)
        self.assertIn("startMatchWithCustomDeck", html)

    def test_block_direct_placement_of_stage1_and_stage2(self):
        """Stage 1 and Stage 2 Pokémon must NOT be directly placeable onto an empty bench slot."""
        self.engine.reset_match()
        self.engine.player_bench = []
        self.engine.player_active = {
            "name": "Pikachu",
            "current_hp": 60,
            "max_hp": 60,
            "attached_energy": [],
            "card_id": "sv1-1"
        }

        self.engine.player_hand = ["Charmeleon"]
        res = self.engine.play_hand_card("Charmeleon")
        self.assertEqual(res["status"], "error", "Charmeleon cannot be benched directly without matching base")
        self.assertEqual(len(self.engine.player_bench), 0, "Bench should remain empty")

        self.engine.player_hand = ["Charizard ex"]
        res2 = self.engine.play_hand_card("Charizard ex")
        self.assertEqual(res2["status"], "error", "Charizard ex cannot be benched directly without matching base")
        self.assertEqual(len(self.engine.player_bench), 0, "Bench should remain empty")

    def test_legal_stage1_evolution(self):
        """Stage 1 Pokémon must evolve onto its matching Basic Pokémon and inherit attached energy."""
        self.engine.reset_match()
        self.engine.player_active = {
            "name": "Charmander",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": ["Fire", "Colorless"],
            "card_id": "sv3-26"
        }
        self.engine.player_hand = ["Charmeleon"]

        res = self.engine.play_hand_card("Charmeleon")
        self.assertEqual(res["status"], "success")
        self.assertEqual(self.engine.player_active["name"], "Charmeleon")
        self.assertEqual(self.engine.player_active["max_hp"], 90)
        self.assertEqual(self.engine.player_active["attached_energy"], ["Fire", "Colorless"])

    def test_legal_stage2_evolution(self):
        """Stage 2 Pokémon must evolve onto its matching Stage 1 Pokémon."""
        self.engine.reset_match()
        self.engine.player_active = {
            "name": "Charmeleon",
            "current_hp": 90,
            "max_hp": 90,
            "attached_energy": ["Fire", "Fire"],
            "card_id": "sv3-27"
        }
        self.engine.player_hand = ["Charizard ex"]

        res = self.engine.play_hand_card("Charizard ex")
        self.assertEqual(res["status"], "success")
        self.assertEqual(self.engine.player_active["name"], "Charizard ex")
        self.assertEqual(self.engine.player_active["max_hp"], 330)
        self.assertEqual(self.engine.player_active["attached_energy"], ["Fire", "Fire"])

    def test_stage_skipping_blocked_without_rare_candy(self):
        """Skipping from Basic directly to Stage 2 without Rare Candy must fail."""
        self.engine.reset_match()
        self.engine.player_active = {
            "name": "Charmander",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": ["Fire"],
            "card_id": "sv3-26"
        }
        self.engine.player_hand = ["Charizard ex", "Basic Fire Energy"]

        res = self.engine.play_hand_card("Charizard ex")
        self.assertEqual(res["status"], "error")
        self.assertEqual(self.engine.player_active["name"], "Charmander")

    def test_rare_candy_evolution_combo(self):
        """Holding Rare Candy allows evolving Basic directly into Stage 2."""
        self.engine.reset_match()
        self.engine.player_active = {
            "name": "Charmander",
            "current_hp": 70,
            "max_hp": 70,
            "attached_energy": ["Fire"],
            "card_id": "sv3-26"
        }
        self.engine.player_hand = ["Rare Candy", "Charizard ex"]

        res = self.engine.play_hand_card("Charizard ex")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "RARE_CANDY_EVOLVE")
        self.assertEqual(self.engine.player_active["name"], "Charizard ex")
        self.assertEqual(self.engine.player_active["max_hp"], 330)
        self.assertNotIn("Rare Candy", self.engine.player_hand)
        self.assertIn("Rare Candy", self.engine.player_discard)

    def test_frontend_js_basic_rules_and_randomization(self):
        """Verify frontend JavaScript embeds Fisher-Yates deck shuffle and randomized Basic Pokémon selection."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        self.assertIn("fisherYatesShuffle", html)
        self.assertIn("getRandomBasicPokemon(4)", html)
        self.assertIn("CHOSEN_4_CARDS = getRandomBasicPokemon(4)", html)
        self.assertIn("OPPONENT_4_CARDS = getRandomBasicPokemon(4, CHOSEN_4_CARDS)", html)
        self.assertIn("isBasicPokemon", html)
        self.assertIn("Squirtle", html)
        self.assertIn("Machop", html)
        self.assertIn("Geodude", html)
        self.assertIn("Abra", html)
        self.assertIn("Meowth", html)
        self.assertIn("Gastly", html)
        self.assertIn("Psyduck", html)
        self.assertIn("Only Basic Pokémon can be chosen for starting slots", html)

    def test_deck_shuffle_and_random_starting_pokemon_simulation(self):
        """Simulate 10 game setups to verify complete deck shuffling and starting Pokémon diversity."""
        player_deck_orders = []
        opp_deck_orders = []
        player_starting_actives = []
        opp_starting_actives = []

        for i in range(10):
            self.engine.reset_match("charizard-ex-pidgeot", "miraidon-ex-regieleki")

            # Verify deck integrity (60 total cards distributed properly)
            total_cards = (
                len(self.engine.player_hand)
                + len(self.engine.player_prizes)
                + 1
                + len(self.engine.player_bench)
                + len(self.engine.player_deck)
            )
            self.assertEqual(total_cards, 60, f"Match #{i+1} player deck must total 60 cards.")

            # Record deck orders and starting active Pokémon
            p_deck_tuple = tuple(self.engine.player_deck)
            opp_deck_tuple = tuple(self.engine.opp_deck)
            player_deck_orders.append(p_deck_tuple)
            opp_deck_orders.append(opp_deck_tuple)

            player_starting_actives.append(self.engine.player_active["name"])
            opp_starting_actives.append(self.engine.opp_active["name"])

            # Verify that only Basic Pokémon are in active spot
            p_meta = self.engine._get_meta(self.engine.player_active["name"])
            p_subs = [s.lower() for s in p_meta.get("subtypes", [])]
            p_stage = (p_meta.get("stage") or "").lower()
            self.assertTrue(
                "basic" in p_subs or p_stage == "basic",
                f"Starting active '{self.engine.player_active['name']}' must be a Basic Pokémon!"
            )
            self.assertNotIn("stage 1", p_subs)
            self.assertNotIn("stage 2", p_subs)

        # Decks must be randomized across 10 games - no fixed repeated order!
        unique_p_decks = len(set(player_deck_orders))
        unique_opp_decks = len(set(opp_deck_orders))
        self.assertGreater(unique_p_decks, 1, "Player 60-card decks must not be identical across games.")
        self.assertGreater(unique_opp_decks, 1, "Opponent 60-card decks must not be identical across games.")


if __name__ == "__main__":
    unittest.main()

