# Pokémon TCG AI Battle Analyzer Engine

A modular, zero-dependency **AI Battle Analyzer Engine** for competitive Pokémon Trading Card Game applications.

Built strictly according to competitive Pokémon TCG mechanics, turn constraints, and a **zero-cheating guarantee** (only evaluates publicly visible opponent information).

---

## 📁 Architecture

```text
ai/
├── battleAnalyzer.js       # Main entry point & model-ready AIAnalyzer class
├── moveGenerator.js        # Generates 100% legal actions according to official rules
├── moveEvaluator.js        # Multi-factor normalized (0–100) scoring engine
├── threatAnalyzer.js       # Visible opponent threat & imminent KO detection
├── strategyEngine.js       # Multi-turn winning paths & best Pokémon selection
├── recommendationEngine.js # Formats structured JSON recommendations & explanations
├── types.js                # Action types, constants, and no-cheating sanitizer
├── index.js                # Clean unified module export
├── ai_engine_bundle.js     # Standalone single-file browser bundle (no bundler needed)
└── test_ai_engine.js       # Verification test script with showcase scenarios
```

---

## 🚀 Quick Integration

### Option A: In a Node.js / Bundler Environment (ES6 / CommonJS)

```javascript
const { analyzeBattle, AIAnalyzer } = require('./ai');
// or: import { analyzeBattle } from './ai/battleAnalyzer.js';

const recommendation = analyzeBattle(gameState);
console.log(recommendation.recommendedMove);
console.log(recommendation.explanationText);
```

### Option B: In Plain HTML / Vanilla JavaScript (Browser)

Simply drop the bundle into your HTML file:

```html
<script src="ai/ai_engine_bundle.js"></script>
<script>
  // Called whenever your game state updates
  const result = window.analyzeBattle(gameState);

  // Update your game UI
  document.getElementById('recommended-move').innerText = result.recommendedMove;
  document.getElementById('move-confidence').innerText = result.confidence + '%';
  document.getElementById('ai-explanation').innerText = result.explanationText;
</script>
```

---

## 🛡️ Strict No-Cheating Guarantee

The engine **never** accesses private opponent data. If hidden fields are present in `gameState` (such as `opponent.hand`, `opponent.deck`, face-down prize cards, or future draws), the sanitizer **completely ignores and strips them**.

The analyzer evaluates only what a human tournament player can see:
* Opponent's Active Pokémon & visible Bench
* Visible HP, Damage, Type, Weakness, Resistance, Retreat Cost
* Visible Attached Energy
* Known attacks, abilities, and status conditions

---

## 📥 Input Schema (`gameState`)

```javascript
const gameState = {
  mySide: {
    active: {
      name: "Pikachu",
      hp: 100,
      maxHp: 100,
      currentHp: 100,
      type: "Lightning",
      weakness: "Fighting",
      retreatCost: 1,
      attachedEnergy: ["Lightning", "Lightning"],
      attacks: [
        { name: "Thunderbolt", damage: 100, cost: ["Lightning", "Lightning"] }
      ],
      statusConditions: [] // e.g. ["Asleep", "Paralyzed"]
    },
    bench: [
      {
        name: "Charizard",
        currentHp: 180,
        maxHp: 180,
        type: "Fire",
        attachedEnergy: ["Fire"],
        attacks: [{ name: "Fire Blast", damage: 140, cost: ["Fire", "Fire", "Colorless"] }],
        prizeValue: 2
      }
    ],
    hand: ["Basic Lightning Energy", "Professor's Research", "Ultra Ball"],
    availableEnergy: ["Basic Lightning Energy"],
    availableTrainers: ["Professor's Research", "Ultra Ball"],
    prizesRemaining: 4,
    energyAttachedThisTurn: false,
    supporterPlayedThisTurn: false,
    retreatedThisTurn: false,
    isFirstTurnGoingFirst: false
  },

  opponent: {
    active: {
      name: "Gyarados",
      currentHp: 90,
      maxHp: 160,
      type: "Water",
      weakness: "Lightning",
      weaknessMultiplier: 2,
      retreatCost: 3,
      attachedEnergy: ["Water", "Water"],
      attacks: [{ name: "Waterfall", damage: 70, cost: ["Water", "Water"] }],
      prizeValue: 1
    },
    bench: [
      { name: "Magikarp", currentHp: 30, maxHp: 30, type: "Water", attachedEnergy: [] }
    ],
    prizesRemaining: 5
  }
};
```

---

## 📤 Output Format

```javascript
{
  "recommendedMove": "Attack with Pikachu",
  "score": 92,
  "confidence": 89,
  "reason": [
    "Opponent's Active Pokémon (Gyarados) has 90 HP remaining",
    "Pikachu can deal 200 damage using Thunderbolt",
    "Opponent has a type weakness to Lightning (2x damage)",
    "Required Energy (Lightning, Lightning) is already attached",
    "This results in a KNOCKOUT, taking 1 Prize card(s)",
    "Knocking it out strips the opponent of their active attacker"
  ],
  "alternatives": [
    { "move": "Switch to Charizard", "score": 78 },
    { "move": "Attach Energy to Charizard", "score": 71 },
    { "move": "Play Professor's Research", "score": 68 }
  ],
  "strategy": [
    "Knock out the opponent's Active (Gyarados)",
    "Prepare Charizard on the Bench for sustained offense",
    "Save the Trainer card for the next turn"
  ],
  "threats": [
    {
      "level": "MEDIUM",
      "type": "HEAVY_DAMAGE_RISK",
      "title": "⚡ MEDIUM THREAT: Severe Damage Risk",
      "description": "Opponent's Active (Gyarados) can deal 70 damage next turn.",
      "recommendedAction": "Prepare a bench attacker or attach defensive tools/energy."
    }
  ],
  "bestPokemon": {
    "attacker": "Pikachu",
    "defender": "Charizard",
    "benchSetup": "Charizard",
    "reason": "Charizard requires additional Energy but has high future damage potential (140 max damage)."
  },
  "winningPath": {
    "current": "Pikachu is armed with 2 Energy",
    "bestMove": "Attack with Pikachu",
    "nextAction": "Prepare Charizard on the Bench",
    "futureSetup": "Deploy Charizard against opponent's follow-up attackers",
    "goal": "Maintain the Prize race lead (4 prizes remaining vs opponent's 5)"
  },
  "explanationText": "🤖 Recommended Move\n\nAttack with Pikachu\n\nWhy?\n\n• Opponent's Active Pokémon (Gyarados) has 90 HP remaining\n• Pikachu can deal 200 damage using Thunderbolt\n• Opponent has a type weakness to Lightning (2x damage)\n• Required Energy (Lightning, Lightning) is already attached\n• This results in a KNOCKOUT, taking 1 Prize card(s)\n• Knocking it out strips the opponent of their active attacker\n\nConfidence: 89%"
}
```

---

## 🤖 Model-Ready Extensibility (Plugging in an ML Model or LLM)

To replace the rule-based evaluator with a custom ML model or neural network:

```javascript
const { AIAnalyzer } = require('./ai');

const myAnalyzer = new AIAnalyzer();

// Inject custom ML scoring function
myAnalyzer.setCustomEvaluator((move, playerState, opponentState, threatContext) => {
  // Call your trained neural net / Decision Transformer / LLM here:
  const mlScore = predictMoveScoreWithModel(move, playerState, opponentState);
  
  return {
    ...move,
    score: mlScore,
    reason: ["Evaluated using neural policy-value network."]
  };
});

// Run analysis with custom model
const result = myAnalyzer.analyzeBattle(gameState);
```
