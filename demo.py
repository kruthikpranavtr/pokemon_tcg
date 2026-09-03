"""
Interactive Pokémon TCG AI Engine Demo
Demonstrates real-time turn recommendation and 60-card deck optimization.
"""
import json
from src.engine.rules_engine import RulesEngine
from src.engine.action_mask import ActionMaskEngine
from src.engine.explainer import ActionExplainer
from src.models.deck_optimizer import DeckOptimizerModel
from src.models.policy_value_net import PolicyValueNetwork


def run_demo():
    print("=" * 80)
    print("  POKÉMON TCG AI ENGINE: DEMONSTRATION & INFERENCE SHOWCASE")
    print("=" * 80)

    # 1. Load Data Assets
    with open("data/cards_dataset.json", "r", encoding="utf-8") as f:
        cards_data = json.load(f)
        card_db = {c["card_id"]: c for c in cards_data["cards"]}

    with open("data/tournament_meta.json", "r", encoding="utf-8") as f:
        meta_db = json.load(f)

    rules = RulesEngine(card_db)
    masker = ActionMaskEngine(card_db)
    explainer = ActionExplainer(card_db)
    deck_opt = DeckOptimizerModel(card_db, meta_db)
    policy_val = PolicyValueNetwork()

    # =========================================================================
    # DEMO 1: 60-Card Deck Construction & Optimization (Model 1)
    # =========================================================================
    print("\n[SCENARIO 1] 60-Card Tournament Deck Optimization")
    print("-" * 80)
    seed = [{"card_id": "sv3-125", "count": 3}] # Charizard ex seed
    deck_result = deck_opt.optimize_deck(seed, target_archetype="charizard-ex-pidgeot")
    is_valid, errors = rules.validate_deck(deck_result["deck_list"])

    print(f"Target Archetype: {deck_result['archetype']}")
    print(f"Total Cards: {deck_result['total_cards']} | Valid 60-Card List: {is_valid}")
    print(f"Expected Tournament Meta Win-Rate: {deck_result['expected_meta_winrate']:.1%}")
    print("Key Cards in Optimized Deck:")
    for card in deck_result["deck_list"][:6]:
        print(f"  - {card['count']}x {card['name']} ({card['supertype']})")
    print("  ... (and full trainer/energy suite to complete 60 cards)")

    # =========================================================================
    # DEMO 2: Real-Time In-Match Live State Decision (Model 2)
    # =========================================================================
    print("\n[SCENARIO 2] Real-Time In-Match Move Recommendation & Win Probability")
    print("-" * 80)

    # Simulate Turn 3 Game State (Charizard Player vs. Miraidon Player)
    sample_game_state = {
        "turn_number": 3,
        "active_turn_player": "player",
        "turn_flags": {
            "is_first_turn_of_game": false,
            "supporter_played_this_turn": false,
            "energy_attached_this_turn": false,
            "retreated_this_turn": false,
            "stadium_played_this_turn": false
        },
        "stadium_in_play": {
            "card_id": "sv1-167",
            "name": "Artazon"
        },
        "player": {
            "prizes_remaining": 6,
            "prizes_taken": 0,
            "deck_count": 47,
            "hand": [
                {"card_id": "sv3-125", "name": "Charizard ex"},
                {"card_id": "sv1-189", "name": "Professor's Research"},
                {"card_id": "sv1-196", "name": "Ultra Ball"},
                {"card_id": "sve-2", "name": "Basic Fire Energy"}
            ],
            "active_spot": {
                "card_id": "sv3-26",
                "name": "Charmander",
                "current_hp": 70,
                "attached_energy": [{"type": "Fire"}],
                "turns_in_play": 1
            },
            "bench": [
                {"slot": 1, "card_id": "sv3-162", "name": "Pidgey", "current_hp": 60, "turns_in_play": 1}
            ]
        },
        "opponent": {
            "prizes_remaining": 6,
            "prizes_taken": 0,
            "deck_count": 48,
            "active_spot": {
                "card_id": "sv1-86",
                "name": "Miraidon ex",
                "current_hp": 220,
                "attached_energy": [{"type": "Lightning"}]
            },
            "bench": [
                {"slot": 1, "card_id": "sv4-70", "name": "Iron Hands ex", "current_hp": 230}
            ]
        }
    }

    # 1. Filter Legal Actions via Deterministic Mask
    legal_moves = masker.get_legal_actions(sample_game_state)
    print(f"Legal Moves Found by Action Mask: {len(legal_moves)}")
    for m in legal_moves:
        print(f"  [Permitted] {m['action_type']} -> {m.get('card_name', m.get('attack_name', ''))}")

    # 2. Score and Rank Moves via Policy-Value Network
    ranked_moves, win_prob = policy_val.rank_legal_actions(sample_game_state, legal_moves)
    prize_map = rules.compute_prize_map(sample_game_state)

    print(f"\nCurrent Estimated Win Probability: {win_prob:.1%}")
    print(f"Prize Map: Player TTW = {prize_map['player_projected_ttw']} turns | Opponent TTW = {prize_map['opponent_projected_ttw']} turns")
    print("\n--- TOP RANKED ACTION RECOMMENDATIONS ---")

    for rank, item in enumerate(ranked_moves[:3], start=1):
        act = item["action"]
        rationale = explainer.explain(act, sample_game_state, item["post_win_prob"])
        name = act.get("card_name", act.get("attack_name", act.get("action_type")))
        print(f"\nRANK #{rank}: {act['action_type']} ({name})")
        print(f"  • Projected Win Prob: {item['post_win_prob']:.1%}")
        print(f"  • Rationale: {rationale}")

    print("\n" + "=" * 80)
    print("  DEMONSTRATION COMPLETED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    # Fix boolean in python
    false = False
    true = True
    run_demo()
