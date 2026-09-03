# Pokémon TCG AI Engine: Recommendation & In-Game Decision Model
### Comprehensive Technical Specification & System Prompt

---

## 1. Executive Overview & Domain Context

This specification outlines the architecture, data schemas, feature engineering pipelines, and machine learning models for an end-to-end **Competitive Pokémon Trading Card Game (TCG) Recommendation & Decision AI Engine**.

The system addresses two distinct operational modalities:
1. **Offline Meta-Deck Builder & Tech-Card Optimizer:** Combinatorial deck construction (60-card optimization, 4-copy rule, energy curves, ACE SPEC / Radiant constraints) optimized against the current tournament metagame matrix.
2. **Real-Time In-Match Sequencer & Play Advisor:** A Partially Observable Markov Decision Process (POMDP) policy-value engine that recommends optimal legal actions (card plays, bench management, search targets, attack sequencing, prize-map calculation) to maximize win probability.

```
+----------------------------------------------------------------------------------------------------+
|                                    POKÉMON TCG AI ENGINE ARCHITECTURE                               |
+----------------------------------------------------------------------------------------------------+
|  [ DATA INGESTION ]                                                                                |
|  - PokemonTCG.io API (Card Database & Mechanics)                                                   |
|  - LimitlessTCG / RK9 Labs (Tournament Decklists, Matchups, Meta Shares)                           |
|  - PTCG Live Logs & Simulators (Action-State Trajectories, Replays)                               |
+----------------------------------------------------------------------------------------------------+
                                      |
         +----------------------------+----------------------------+
         v                                                         v
+------------------------------------+    +--------------------------------------------------------+
|  MODULE A: METAGAME & DECK ENGINE  |    |  MODULE B: REAL-TIME IN-GAME SEQUENCING ENGINE         |
|  - GNN / Hypergraph Embeddings     |    |  - Transformer State-Action Encoder (POMDP)           |
|  - 60-Card Constraint Solver (ILP) |    |  - Dynamic Legal Action Masking (1 Supporter, Energy)  |
|  - Nash Equilibrium Meta Optimizer |    |  - Monte Carlo Tree Search (MCTS) / AlphaZero Policy   |
+------------------------------------+    +--------------------------------------------------------+
         |                                                         |
         v                                                         v
  [ Deck & Tech Recommendations ]                           [ Turn-by-Turn Action & Search Ranking ]
```

---

## 2. Competitive Pokémon TCG Domain Truths & Rules Engine

A valid ML model must strictly enforce official Pokémon TCG game rules (Standard Format - Regulation Marks `F`, `G`, `H`, etc.):

### 2.1 Game Structure & Turn Restrictions
* **Deck Constraints:** Exactly **60 cards**, maximum **4 copies** of any card with the same name (except Basic Energy).
* **Special Rule-Box Restrictions:**
  * **Radiant Pokémon:** Maximum 1 Radiant card in the entire deck.
  * **ACE SPEC Cards:** Maximum 1 ACE SPEC card in the entire deck.
  * **Rule Box Multi-Prize Mechanics:**
    * Regular Pokémon: Gives up **1 Prize card** when Knocked Out (KO).
    * Pokémon ex / Pokémon V / VSTAR: Gives up **2 Prize cards** when KO'd.
    * Pokémon VMAX / V-UNION: Gives up **3 Prize cards** when KO'd.
* **Turn 1 (Going 1st) Restrictions:** The player going first **cannot attack** and **cannot play a Supporter card**.
* **Per-Turn Action Limits:**
  * **Supporter Card:** Exactly **1 Supporter per turn** (unless modified by specific card effects).
  * **Manual Energy Attachment:** Exactly **1 Energy attachment from hand per turn** to either Active or Bench (excluding energy acceleration abilities/items).
  * **Retreat:** Exactly **1 Manual Retreat per turn** (must pay exact Retreat Cost in attached energy).
  * **Stadium Card:** Maximum **1 Stadium card played per turn**; cannot play a Stadium with the exact same name as the active Stadium on board.
  * **Item Cards & Pokémon Tools:** Unlimited plays per turn. Maximum 1 Tool attached per Pokémon.
* **Energy & Type System:**
  * **Official TCG Types:** `Grass (G)`, `Fire (R)`, `Water (W)`, `Lightning (L)`, `Psychic (P)`, `Fighting (F)`, `Darkness (D)`, `Metal (M)`, `Dragon (N)`, `Colorless (C)`. *(Note: Fairy type has been phased out in Standard).*
  * **Energy Requirement:** Specific colored energy + generic Colorless costs.
* **Special Conditions (Active Pokémon Only):**
  * `Asleep`, `Confused`, `Paralyzed` (Mutually exclusive: new condition overwrites previous).
  * `Poisoned`, `Burned` (Can co-exist with each other and with one orientation condition).
* **Game Zones:**
  * Active Spot (1 Pokémon), Bench (Max 5 Pokémon, or 8 with Stadiums like *Area Zero Underdepths* / *Sky Field*), Hand, Deck, Discard Pile, Prize Cards (6 cards), **Lost Zone** (cards cannot be recovered or searched by standard effects).
* **Win Conditions:**
  1. Take all 6 Prize cards.
  2. Knock Out the opponent's Active Pokémon when they have no Benched Pokémon.
  3. Opponent begins their turn with an empty deck and cannot draw a card (Deck Out).

---

## 3. Standard Data Schemas

### 3.1 Card Master Dataset (`pokemon_tcg_cards.parquet`)
```json
{
  "card_id": "sv3-125",
  "name": "Charizard ex",
  "supertype": "Pokémon",
  "subtypes": ["Stage 2", "Tera", "ex"],
  "regulation_mark": "G",
  "format_legalities": {
    "standard": true,
    "expanded": true
  },
  "hp": 330,
  "types": ["Darkness"],
  "evolves_from": "Charmeleon",
  "abilities": [
    {
      "name": "Infernal Reign",
      "type": "Ability",
      "text": "When you play this Pokémon from your hand to evolve 1 of your Pokémon during your turn, you may search your deck for up to 3 Basic Fire Energy cards and attach them to your Pokémon in any way you like. Then, shuffle your deck.",
      "trigger": "ON_EVOLVE_FROM_HAND",
      "effect_type": "ENERGY_ACCELERATION",
      "target_zone": "DECK",
      "max_energy_searched": 3,
      "energy_type": "Fire"
    }
  ],
  "attacks": [
    {
      "name": "Burning Darkness",
      "cost": ["Fire", "Fire"],
      "converted_energy_cost": 2,
      "base_damage": 180,
      "damage_scaling": {
        "condition": "PER_OPPONENT_PRIZE_TAKEN",
        "multiplier": 30
      },
      "text": "This attack does 30 more damage for each Prize card your opponent has taken."
    }
  ],
  "weaknesses": [{"type": "Grass", "value": "×2"}],
  "resistances": [],
  "retreat_cost": 2,
  "prize_yield": 2,
  "rules": ["Pokémon ex rule: When your Pokémon ex is Knocked Out, your opponent takes 2 Prize cards."]
}
```

### 3.2 Trainer & Energy Schema (`trainer_energy_cards.parquet`)
```json
{
  "card_id": "sv1-189",
  "name": "Professor's Research",
  "supertype": "Trainer",
  "subtypes": ["Supporter"],
  "regulation_mark": "G",
  "effects": {
    "type": "HAND_REFRESH",
    "discard_current_hand": true,
    "cards_drawn": 7
  },
  "per_turn_limit": "SUPPORTER_RULE"
}
```

### 3.3 Metagame & Tournament Schema (`tournament_meta.parquet`)
Derived from LimitlessTCG and official RK9 tournament exports:
```json
{
  "tournament_id": "EUIC-2026",
  "format": "Standard 2026 (F-G-H)",
  "archetypes": [
    {
      "archetype_id": "charizard-ex-pidgeot",
      "archetype_name": "Charizard ex / Pidgeot ex",
      "meta_share_pct": 18.4,
      "tier": "Tier 1",
      "core_cards": [
        {"card_id": "sv3-125", "count": 3},
        {"card_id": "sv3-164", "count": 2},
        {"card_id": "sv1-196", "count": 4}
      ],
      "matchup_matrix": {
        "gardevoir-ex": 0.54,
        "miraidon-ex": 0.62,
        "lost-zone-box": 0.47,
        "lugia-vstar": 0.58
      }
    }
  ]
}
```

### 3.4 In-Game Live State Representation (`game_state.json`)
```json
{
  "match_id": "ptcgl-live-892147",
  "format": "Standard",
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
    "name": "Artazon",
    "played_by": "player"
  },
  "lost_zone_counts": {
    "player": 0,
    "opponent": 4
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
      "max_hp": 70,
      "damage_counters": 0,
      "attached_energy": [{"type": "Fire", "is_special": false}],
      "attached_tool": null,
      "special_conditions": [],
      "turns_in_play": 1
    },
    "bench": [
      {
        "slot": 1,
        "card_id": "sv3-162",
        "name": "Pidgey",
        "current_hp": 60,
        "damage_counters": 0,
        "attached_energy": [],
        "attached_tool": null,
        "special_conditions": []
      }
    ],
    "discard_pile": ["sv1-166", "sv1-191"]
  },
  "opponent": {
    "prizes_remaining": 6,
    "prizes_taken": 0,
    "deck_count": 48,
    "hand_count": 6,
    "revealed_hand": [],
    "active_spot": {
      "card_id": "sv1-86",
      "name": "Miraidon ex",
      "current_hp": 220,
      "damage_counters": 0,
      "attached_energy": [{"type": "Lightning", "is_special": false}],
      "special_conditions": []
    },
    "bench": [
      {"slot": 1, "card_id": "sv1-65", "name": "Mareep", "current_hp": 50, "damage_counters": 0}
    ],
    "discard_pile": ["sv1-189"]
  }
}
```

---

## 4. Feature Engineering: Competitive Game Theory & TCG Metrics

### 4.1 Prize Trade & Tempo Metrics (The "Prize Map")
* **Turns-to-Win (TTW):** Calculated from current board damage output vs. opponent's active/bench HP and Prize yield (1-Prize vs. 2-Prize KO paths).
* **Prize Differential:** $\Delta P = \text{PrizesTaken}_{\text{player}} - \text{PrizesTaken}_{\text{opp}}$.
* **Prize Trade Efficiency:** $\text{PTE} = \frac{\text{Prizes Taken by Attack}}{\text{Prizes Yielded on Retaliation KO}}$.
* **Effective HP (EHP):** $\text{EHP} = \text{Base HP} - \text{Damage Counters} + \text{Healing Potential} - \text{Weakness Multiplier} \times \text{Expected Incoming Damage}$.

### 4.2 Resource Consistency & Search "Outs"
* **Setup Outs:** Hypergeometric probability $P(X \ge 1)$ of drawing or searching an evolution piece (e.g., Rare Candy + Stage 2) given remaining deck composition and search cards in hand.
* **Energy Availability Factor:** Available manual energy + search/acceleration ability bandwidth (e.g., *Infernal Reign*, *Electric Generator*, *Archeops Primal Turbo*).
* **Hand Disruption Vulnerability:** Sensitivity to opponent playing *Iono*, *Judge*, or *Roxanne* at current prize count ($N_{\text{cards}} = \text{Prizes Remaining}$).

### 4.3 Archetype & Tech Card Synergy Embeddings
* **Card Co-occurrence & Graph Centrality:** Hypergraph adjacency matrix weighted by tournament win rate.
* **Meta-Counter Score:** Damage coverage against Top-5 metagame archetypes adjusted for weakness calculations (e.g., Lightning damage vs. Lugia VSTAR, Grass damage vs. Charizard ex).

---

## 5. Machine Learning Architectures

```
+---------------------------------------------------------------------------------------------------+
| MODEL 1: METAGAME & 60-CARD DECK CONSTRUCTOR                                                     |
| (Hypergraph Neural Network + Integer Linear Programming)                                          |
|                                                                                                   |
| Objective: Argmax WinRate(Deck D | Metagame Distribution M)                                       |
| Subject to: |D| = 60, Copies(c) <= 4, Count(ACE SPEC) <= 1, Count(Radiant) <= 1, Count(Basic) >= 1  |
+---------------------------------------------------------------------------------------------------+

+---------------------------------------------------------------------------------------------------+
| MODEL 2: REAL-TIME IN-GAME SEQUENCING & DECISION ENGINE                                           |
| (Transformer Encoder-Decoder + Legal Action Masking + Policy/Value Heads)                        |
|                                                                                                   |
| State S_t ──> [ Transformer State Encoder ] ──> Action Mask M(S_t) ──> Policy Head P(a | S_t)     |
|                                             └──> Value Head V(S_t) ──> Win Probability in [0, 1]  |
+---------------------------------------------------------------------------------------------------+
```

### 5.1 Model 1: Deck Construction Optimizer (Offline)
* **Architecture:** Graph Convolutional Network (GCN) card embeddings combined with a **Constrained Genetic Algorithm (GA)** or **Integer Linear Programming (ILP)** solver.
* **Loss Function:** Tournament placement cross-entropy + meta-weight calibration.
* **Output:** Optimal 60-card list, recommended counts (e.g., 3-1-3 line vs. 4-0-4 line with Rare Candy), and energy/trainer ratios.

### 5.2 Model 2: Real-Time In-Match Sequencer & Policy-Value Network (Online)
* **Architecture:** Transformer with masked self-attention over hand, board, discard, and prize count.
* **POMDP State Tracking:** Opponent hand is modeled as a probability distribution over the known archetype card pool minus revealed cards.
* **Legal Action Masking Layer:** A deterministic rule-layer that zeroes out logits for illegal actions (e.g., attempting a 2nd Supporter, illegal energy attachment, attacking on Turn 1 Going 1st).
* **Dual Heads:**
  1. **Policy Head ($P(a | S_t)$):** Distribution over all legal atomic actions (Play Card, Attach Energy, Use Ability, Retreat, Attack, Pass).
  2. **Value Head ($V(S_t)$):** Scalar prediction $[0, 1]$ representing game win probability from state $S_t$.

---

## 6. Real-Time Recommendation Engine API Specification

### Input Payload
```json
{
  "session_id": "match_90123",
  "format": "standard",
  "game_state": { ... } // See Section 3.4
}
```

### Recommendation Output
```json
{
  "status": "success",
  "current_win_probability": 0.684,
  "turn_recommendations": [
    {
      "rank": 1,
      "action_type": "PLAY_TRAINER",
      "card_id": "sv1-196",
      "card_name": "Ultra Ball",
      "action_parameters": {
        "discard_targets": ["sv1-189", "sve-2"],
        "search_target": "sv3-125 (Charizard ex)"
      },
      "expected_win_probability_after_play": 0.742,
      "strategic_rationale": "Discard dead resources to fetch Charizard ex. Enables 'Infernal Reign' evolution onto active Charmander, attaching 2 Fire energy to power up 'Burning Darkness' for an immediate OHKO on opponent's Miraidon ex (Taking 2 Prizes)."
    },
    {
      "rank": 2,
      "action_type": "USE_STADIUM",
      "card_id": "sv1-167",
      "card_name": "Artazon",
      "action_parameters": {
        "search_target": "sv3-162 (Pidgey)"
      },
      "expected_win_probability_after_play": 0.691,
      "strategic_rationale": "Setup secondary Pidgey on Bench to prepare future 'Quick Search' engine."
    }
  ],
  "prize_map_summary": {
    "current_player_prizes": 6,
    "projected_turns_to_win": 3,
    "opponent_projected_turns_to_win": 4,
    "win_con_path": "KO Active Miraidon ex (2 prizes) -> KO Bench Raikou V (2 prizes) -> KO Iron Hands ex (2 prizes)"
  }
}
```

---

## 7. Model Evaluation & Benchmark Metrics

1. **Top-1 Action Match (Behavioral Cloning Accuracy):** % agreement with top-cut Masters Division players from regional/international tournament replays (Target: $> 78\%$).
2. **Win-Rate Calibration Error (ECE):** Expected Calibration Error between predicted win probability $V(S)$ and empirical match outcomes (Target: $\text{ECE} < 0.04$).
3. **Legal Action Compliance:** $100.0\%$ (Strict zero-tolerance for illegal plays via action masking).
4. **Search Quality (Optimal Target Retrieval):** Top-3 accuracy on deck search selections (Ultra Ball, Nest Ball, Pidgeot ex Quick Search, Arven).
5. **Inference Latency:** $< 65\text{ms}$ per game state evaluation on standard CPU/GPU instances for live client pairing.

---

## 8. Development Roadmap & Implementation Tasks

- [x] **Card Database & Rule Constraints:** Standard format JSON schema, ability trigger parser, legal action mask.
- [ ] **Tournament Data Ingestion:** ETL pipeline connecting LimitlessTCG tournament data and RK9 decklists into `.parquet`.
- [ ] **State Representation & Tokenizer:** Tokenizer for 60-card decks, board states, prize pools, and discard piles.
- [ ] **Model 1 (GNN/ILP):** 60-card Deck Optimizer training against current tier metagame matrix.
- [ ] **Model 2 (Transformer Policy/Value):** Offline supervised pre-training on expert tournament game logs followed by MCTS self-play refinement.
- [ ] **FastAPI Inference Service:** High-throughput endpoint with legal action masking and explainable tactical outputs.
- [ ] **Validation Suite:** Benchmarking against historical World Championship & Regional final matches.
