"""
Demo Client: Call Pokémon TCG AI Move Recommender via API Key
Demonstrates passing our card details and opponent deck details to receive optimal move recommendations.
"""
import sys
import json

API_URL = "http://127.0.0.1:8000/api/v1/recommend-move"
API_KEY = "tcg-live-secret-key-2026"

payload = {
    "session_id": "live-tournament-round-4",
    "our_cards": {
        "active_pokemon": {
            "name": "Charmander",
            "current_hp": 70,
            "attached_energy": ["Fire"],
            "turns_in_play": 1
        },
        "hand_cards": [
            "Charizard ex",
            "Rare Candy",
            "Ultra Ball",
            "Professor's Research",
            "Basic Fire Energy"
        ],
        "bench_pokemon": [
            {"name": "Pidgey", "current_hp": 60, "attached_energy": []},
            {"name": "Radiant Greninja", "current_hp": 130, "attached_energy": []}
        ],
        "prizes_remaining": 6,
        "prizes_taken": 0
    },
    "opponent_cards": {
        "deck_archetype": "miraidon-ex-regieleki",
        "active_pokemon": {
            "name": "Miraidon ex",
            "current_hp": 220,
            "attached_energy": ["Lightning", "Lightning"]
        },
        "bench_pokemon": [
            {"name": "Iron Hands ex", "current_hp": 230, "attached_energy": []},
            {"name": "Raikou V", "current_hp": 200, "attached_energy": []}
        ],
        "prizes_remaining": 6,
        "prizes_taken": 0
    },
    "turn_context": {
        "turn_number": 3,
        "supporter_played_this_turn": False,
        "energy_attached_this_turn": False
    }
}

def main():
    print("=" * 75)
    print("[*] Pokemon TCG AI Move Recommender Client (API Key Authenticated)")
    print("=" * 75)
    print(f"API Endpoint : {API_URL}")
    print(f"API Key      : {API_KEY[:6]}...{API_KEY[-4:]}")
    print(f"Our Active   : {payload['our_cards']['active_pokemon']['name']} ({payload['our_cards']['active_pokemon']['current_hp']} HP)")
    print(f"Opponent     : {payload['opponent_cards']['active_pokemon']['name']} ({payload['opponent_cards']['active_pokemon']['current_hp']} HP) | Deck: {payload['opponent_cards']['deck_archetype']}")
    print("-" * 75)

    try:
        import requests
        response = requests.post(
            API_URL,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY
            },
            json=payload,
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            print(f"[+] Match Win Probability : {data.get('current_win_probability_pct')}")
            print("\n[>>>] TOP RECOMMENDED MOVE (#1):")
            top = data.get("top_recommended_move", {})
            print(f"  * Action Type  : {top.get('action_type')}")
            print(f"  * Card / Target: {top.get('card_name')}")
            print(f"  * Post Win %   : {top.get('expected_win_probability_pct')}")
            print(f"  * Rationale    : {top.get('strategic_rationale')}")

            print("\n[+] ALTERNATIVE RANKED MOVES:")
            for m in data.get("all_recommended_moves", [])[1:]:
                print(f"  #{m.get('rank')} [{m.get('action_type')}] {m.get('card_name') or ''} -> Post Win Prob: {m.get('expected_win_probability_pct')} | {m.get('strategic_rationale')}")
        else:
            print(f"[-] Error ({response.status_code}): {response.text}")

    except Exception:
        print("[!] Server is offline. Running direct in-process engine simulation:")
        from src.engine.card_resolver import CardResolver
        from src.engine.action_mask import ActionMaskEngine
        from src.engine.explainer import ActionExplainer
        from src.models.policy_value_net import PolicyValueNetwork

        with open("data/cards_dataset.json", "r", encoding="utf-8") as f:
            cards = {c["card_id"]: c for c in json.load(f)["cards"]}
        resolver = CardResolver(cards)
        masker = ActionMaskEngine(cards)
        explainer = ActionExplainer(cards)
        net = PolicyValueNetwork()

        game_state = resolver.build_game_state(payload["our_cards"], payload["opponent_cards"], payload["turn_context"])
        legal = masker.get_legal_actions(game_state)
        ranked, base_win = net.rank_legal_actions(game_state, legal)

        print(f"[+] Evaluated {len(legal)} legal actions. Current win rate: {base_win * 100:.1f}%")
        top_act = ranked[0]["action"]
        print(f"[>>>] Best Play (#1): {top_act.get('action_type')} ({top_act.get('card_name')}) -> {ranked[0]['post_win_prob']*100:.1f}%")
        print(f"  Rationale: {explainer.explain(top_act, game_state, ranked[0]['post_win_prob'])}")

        print("\n[+] Alternative Moves:")
        for rank_idx, item in enumerate(ranked[1:4], start=2):
            act = item["action"]
            print(f"  #{rank_idx} [{act.get('action_type')}] {act.get('card_name', '')} -> {item['post_win_prob']*100:.1f}% | {explainer.explain(act, game_state, item['post_win_prob'])}")

if __name__ == "__main__":
    main()
