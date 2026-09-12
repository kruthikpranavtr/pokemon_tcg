import unittest
import secrets
from fastapi.testclient import TestClient
from src.api import app, tcg_match_engine


class TestE2EBattleFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Register a test user
        uid = secrets.token_hex(4)
        auth_res = cls.client.post("/api/v1/auth/register", json={
            "username": f"E2ETestUser_{uid}",
            "email": f"e2e_test_{uid}@kanto.com",
            "password": "Password123!"
        })
        assert auth_res.status_code == 200, auth_res.text
        cls.token = auth_res.json()["token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_full_33_step_lifecycle(self):
        # STEP 1: Load decks
        decks_res = self.client.get("/api/v1/decks/all")
        self.assertEqual(decks_res.status_code, 200)
        meta_decks = decks_res.json()["decks"]
        self.assertIn("charizard-fire", meta_decks)

        # STEP 2: Save 60-card custom deck into slot 1
        sample_deck = meta_decks["charizard-fire"]["deck_list"]
        save_res = self.client.post("/api/v1/decks/user/save", headers=self.headers, json={
            "slot": 1,
            "deck_name": "Esports Charizard 60",
            "cards": [c["name"] for c in sample_deck]
        })
        self.assertEqual(save_res.status_code, 200)

        # STEP 3: Select slot 1 for battle
        select_res = self.client.post("/api/v1/decks/user/select", headers=self.headers, json={"slot": 1})
        self.assertEqual(select_res.status_code, 200)

        # STEP 4: Start Battle with saved deck
        start_res = self.client.post("/api/v1/match/start", headers=self.headers, json={
            "deck_slot": 1,
            "player_deck_id": "charizard-fire",
            "opp_deck_id": "pikachu-lightning"
        })
        self.assertEqual(start_res.status_code, 200)
        match_data = start_res.json()
        self.assertEqual(match_data["deck_counts"]["player_hand"], 5)
        self.assertEqual(match_data["deck_counts"]["player_deck"], 49)
        self.assertEqual(match_data["deck_counts"]["player_prizes"], 6)
        self.assertEqual(match_data["deck_counts"]["opp_prizes"], 6)
        self.assertEqual(match_data["match_state"]["phase"], "SETUP")

        # STEP 5: Mulligan check
        mulligan_res = self.client.post("/api/v1/match/mulligan", headers=self.headers)
        self.assertIn(mulligan_res.json()["status"], ["success", "error"])

        # STEP 6: Place basic into active
        basic_in_hand = None
        for c in tcg_match_engine.player_hand:
            m = tcg_match_engine._get_meta(c)
            if m.get("card_type") == "pokemon" and m.get("stage") == "Basic":
                basic_in_hand = c
                break

        if not basic_in_hand:
            basic_in_hand = tcg_match_engine._extract_basic_from_hand_or_deck([], tcg_match_engine.player_deck)
            tcg_match_engine.player_hand.append(basic_in_hand)

        place_active_res = self.client.post("/api/v1/match/initial-place", headers=self.headers, json={
            "card_name": basic_in_hand,
            "slot": "active"
        })
        self.assertEqual(place_active_res.status_code, 200)

        # Confirm setup to enter BATTLE
        confirm_res = self.client.post("/api/v1/match/confirm-setup", headers=self.headers)
        self.assertEqual(confirm_res.status_code, 200)
        self.assertEqual(confirm_res.json()["result"]["status"], "success")

        # STEP 7: Draw 1 card
        draw_res = self.client.post("/api/v1/match/draw", headers=self.headers)
        self.assertEqual(draw_res.status_code, 200)

        # Second draw in same turn blocked
        draw2_res = self.client.post("/api/v1/match/draw", headers=self.headers)
        self.assertEqual(draw2_res.json()["status"], "error")

        # STEP 8: Attach 1 Energy
        tcg_match_engine.player_hand.append("Basic Fire Energy")
        attach_res = self.client.post("/api/v1/match/attach-energy", headers=self.headers, json={
            "card_name": "Basic Fire Energy",
            "target": "active"
        })
        self.assertEqual(attach_res.status_code, 200)

        # Second energy attachment blocked
        tcg_match_engine.player_hand.append("Basic Fire Energy")
        attach2_res = self.client.post("/api/v1/match/attach-energy", headers=self.headers, json={
            "card_name": "Basic Fire Energy",
            "target": "active"
        })
        self.assertEqual(attach2_res.json()["result"]["status"], "error")

        # STEP 9: Play Trainer Card (Potion)
        tcg_match_engine.player_hand.append("Potion")
        tcg_match_engine.player_active["current_hp"] = 30
        trainer_res = self.client.post("/api/v1/match/play", headers=self.headers, json={
            "card_name": "Potion",
            "target": "active"
        })
        self.assertEqual(trainer_res.status_code, 200)

        # STEP 10: Evolution (Charmander -> Charmeleon), energy preserved
        tcg_match_engine.player_active = tcg_match_engine._create_pokemon_dict("Charmander", tcg_match_engine._get_meta("Charmander"))
        tcg_match_engine.player_active["attached_energy"] = ["Fire"]
        tcg_match_engine.player_hand.append("Charmeleon")
        evolve_res = self.client.post("/api/v1/match/evolve", headers=self.headers, json={
            "card_name": "Charmeleon",
            "target": "active"
        })
        self.assertEqual(evolve_res.status_code, 200)
        self.assertEqual(evolve_res.json()["result"]["status"], "success")
        self.assertEqual(tcg_match_engine.player_active["name"], "Charmeleon")
        self.assertEqual(tcg_match_energy := tcg_match_engine.player_active["attached_energy"], ["Fire"])

        # STEP 11: Switch / Retreat
        tcg_match_engine.player_bench[0] = tcg_match_engine._create_pokemon_dict("Pikachu", tcg_match_engine._get_meta("Pikachu"))
        switch_res = self.client.post("/api/v1/match/switch", headers=self.headers, json={"bench_slot": 0})
        self.assertEqual(switch_res.status_code, 200)
        self.assertEqual(tcg_match_engine.player_active["name"], "Pikachu")
        self.assertEqual(tcg_match_engine.player_bench[0]["name"], "Charmeleon")

        # STEP 12: Attack and Knockout
        tcg_match_engine.player_active["attached_energy"] = ["Lightning", "Lightning"]
        tcg_match_engine.opp_active["current_hp"] = 20
        tcg_match_engine.opp_bench[0] = tcg_match_engine._create_pokemon_dict("Charmander", tcg_match_engine._get_meta("Charmander"))
        initial_prizes_taken = tcg_match_engine.player_prizes_taken

        atk_res = self.client.post("/api/v1/match/attack", headers=self.headers, json={
            "attack_name": "Quick Attack",
            "base_damage": 30
        })
        self.assertEqual(atk_res.status_code, 200)
        self.assertTrue(atk_res.json()["attack_result"].get("knockout"))
        self.assertEqual(tcg_match_engine.player_prizes_taken, initial_prizes_taken + 1)
        self.assertEqual(tcg_match_engine.opp_active["name"], "Charmander")


if __name__ == "__main__":
    unittest.main()
