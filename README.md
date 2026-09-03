# Pokémon TCG Recommendation & Decision ML Engine

An AI-driven recommendation and strategic decision system for the **Pokémon Trading Card Game (Standard Format)**. 

Built with official TCG competitive mechanics (Standard regulation marks, 60-card constraints, 1-Supporter/turn rule, 1-Energy attachment/turn rule, ACE SPEC / Radiant limits, Turn 1 Going 1st penalties) and a dual-engine ML architecture:
1. **Model 1 (Offline Deck Constructor & Optimizer):** Graph synergy embeddings + combinatorial solver to generate optimal 60-card tournament decklists.
2. **Model 2 (Real-Time In-Match Sequencer):** Dual-head Neural Policy-Value Network + deterministic legal action masking that predicts match win probability $V(S) \in [0, 1]$ and ranks turn-by-turn plays with tactical rationale.

---

## Project Structure

```
.
├── data/
│   ├── cards_dataset.json        # Standard format card database (attacks, abilities, rule-boxes)
│   └── tournament_meta.json      # Metagame tier shares & archetype matchup win-rate matrix
├── src/
│   ├── engine/
│   │   ├── rules_engine.py       # 60-card validator, damage calculation, Prize Map (TTW)
│   │   ├── action_mask.py        # Legal action mask (1 Supporter, 1 Energy, Turn 1 Going 1st)
│   │   └── explainer.py          # Strategic rationale generator for recommended actions
│   ├── models/
│   │   ├── deck_optimizer.py     # Model 1: 60-card combinatorial deck optimization
│   │   └── policy_value_net.py   # Model 2: Dual-head Policy-Value Network
│   ├── api.py                    # FastAPI REST API serving endpoints
│   └── train.py                  # Training pipeline & synthetic replay generator
├── models/
│   └── policy_value_weights.json # Saved model checkpoint weights
├── tests/
│   └── test_system.py            # Unit test suite for rules, masks, and network outputs
├── demo.py                       # Interactive CLI demonstration
├── requirements.txt              # Project dependencies
└── README.md                     # Project documentation
```

---

## Quick Start & Usage

### 1. Requirements & Setup

Make sure you have Python 3.10+ installed.

```bash
# Optional: Install FastAPI & Uvicorn for the REST API
pip install fastapi uvicorn pydantic numpy
```

---

### 2. Run the Interactive Showcase / Demo

Runs the end-to-end demo showcasing **Model 1 (60-Card Deck Construction)** and **Model 2 (Real-Time Turn Decision & Move Ranking)**:

```bash
python demo.py
```

**Demo Output Preview:**
* **Scenario 1:** Assembles an optimized 60-card Charizard ex / Pidgeot ex list with a 56.4% expected win rate against the tournament meta.
* **Scenario 2:** Evaluates a live Turn 3 game state, masks illegal moves, estimates win probability (50.6%), and outputs top-3 recommended plays with tactical rationales (e.g. attacking with Ember for 54.7% projected win rate).

---

### 3. Train the Model

To generate synthetic match trajectories and train the Policy-Value Network:

```bash
python src/train.py
```

This will run 20 epochs of gradient descent, display loss progression, and save weights to `models/policy_value_weights.json`.

---

### 4. Run the Unit Test Suite

Validates all rules engine constraints, legal move masks, and model prediction bounds:

```bash
python -m unittest tests/test_system.py
```

---

### 5. Launch the REST API Server

Start the high-throughput FastAPI inference server:

```bash
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

* **Interactive Web Dashboard**: Open [http://localhost:8000](http://localhost:8000) in your browser.
* **Interactive Swagger API Docs**: Open [http://localhost:8000/docs](http://localhost:8000/docs).

---

## API Key Authentication & Prediction Usage

All core prediction endpoints are secured using API Key authentication.
* **Default Demo API Key**: `tcg-live-secret-key-2026` (or configure `POKEMON_TCG_API_KEY` environment variable).
* Pass the API key via `X-API-Key` header, `Authorization: Bearer <key>`, or `?api_key=<key>` query param.

### Endpoint: Real-Time Move Recommender (`POST /api/v1/recommend-move`)

Accepts user card details (active Pokémon, attached energy, hand cards, bench) and opponent deck details to compute legal actions, win probabilities, and optimal ranked plays.

#### cURL Example:

```bash
curl -X POST "http://localhost:8000/api/v1/recommend-move" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: tcg-live-secret-key-2026" \
     -d '{
       "session_id": "match-01",
       "our_cards": {
         "active_pokemon": {
           "name": "Charmander",
           "current_hp": 70,
           "attached_energy": ["Fire"]
         },
         "hand_cards": [
           "Charizard ex",
           "Rare Candy",
           "Ultra Ball",
           "Professor'\''s Research",
           "Basic Fire Energy"
         ],
         "bench_pokemon": ["Pidgey", "Radiant Greninja"],
         "prizes_remaining": 6
       },
       "opponent_cards": {
         "deck_archetype": "miraidon-ex-regieleki",
         "active_pokemon": {
           "name": "Miraidon ex",
           "current_hp": 220,
           "attached_energy": ["Lightning", "Lightning"]
         },
         "bench_pokemon": ["Iron Hands ex", "Raikou V"],
         "prizes_remaining": 6
       },
       "turn_context": {
         "turn_number": 3,
         "supporter_played_this_turn": false,
         "energy_attached_this_turn": false
       }
     }'
```

#### Python Example:

```python
import requests

API_URL = "http://localhost:8000/api/v1/recommend-move"
HEADERS = {"X-API-Key": "tcg-live-secret-key-2026"}

payload = {
    "our_cards": {
        "active_pokemon": {"name": "Charmander", "current_hp": 70, "attached_energy": ["Fire"]},
        "hand_cards": ["Charizard ex", "Rare Candy", "Ultra Ball", "Professor's Research", "Basic Fire Energy"],
        "bench_pokemon": ["Pidgey"],
        "prizes_remaining": 6
    },
    "opponent_cards": {
        "deck_archetype": "miraidon-ex-regieleki",
        "active_pokemon": {"name": "Miraidon ex", "current_hp": 220, "attached_energy": ["Lightning", "Lightning"]},
        "bench_pokemon": ["Iron Hands ex"],
        "prizes_remaining": 6
    },
    "turn_context": {
        "turn_number": 3,
        "supporter_played_this_turn": False,
        "energy_attached_this_turn": False
    }
}

response = requests.post(API_URL, headers=HEADERS, json=payload)
data = response.json()
print("Top Recommended Move:", data["top_recommended_move"])
```

---

## Core Features & Mechanics Enforced

* **API Key Security**: Validates all client requests with customizable keys and environment support.
* **Smart Card Resolution**: Resolves card names, aliases, HP, energy costs, and abilities automatically via `CardResolver`.
* **Official Turn Constraints:** Deterministic mask enforces max 1 Supporter per turn, max 1 manual Energy attachment from hand per turn, max 1 Stadium per turn, and Turn 1 Going 1st restrictions.
* **Prize Economics & Prize Map:** Real-time calculation of Turns-To-Win (TTW) across 1-Prize, 2-Prize (ex/V), and 3-Prize (VMAX) Knockout paths.
* **Dual-Head Policy-Value Network:** Computes win probability $V(S) \in [0, 1]$ and move logits $\pi(a|S)$ in $<5\text{ms}$.
