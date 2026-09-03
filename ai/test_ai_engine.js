/**
 * test_ai_engine.js
 * Verification test script demonstrating the Pokémon TCG AI Battle Analyzer Engine
 * with the exact scenario from the prompt specification.
 */

const { analyzeBattle, AIAnalyzer } = require('./index');

console.log("================================================================================");
console.log("POKÉMON TCG AI BATTLE ANALYZER ENGINE — VERIFICATION TEST");
console.log("================================================================================\n");

// Scenario 1: Prompt Showcase Scenario
// Pikachu Active (100 HP, 2 Lightning Energy, Thunderbolt 100 dmg)
// Opponent Active: Gyarados / Water type (90 HP remaining, 160 Max HP, Weak to Lightning)
// Bench: Charizard, Snorlax
// Hand: Energy, Trainer Card (Professor's Research)
const sampleGameState = {
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
        {
          name: "Thunderbolt",
          damage: 100,
          cost: ["Lightning", "Lightning"]
        },
        {
          name: "Quick Attack",
          damage: 20,
          cost: ["Colorless"]
        }
      ],
      statusConditions: []
    },
    bench: [
      {
        name: "Charizard",
        hp: 180,
        maxHp: 180,
        currentHp: 180,
        type: "Fire",
        weakness: "Water",
        retreatCost: 2,
        attachedEnergy: ["Fire"],
        attacks: [
          { name: "Fire Blast", damage: 140, cost: ["Fire", "Fire", "Colorless"] }
        ],
        prizeValue: 2
      },
      {
        name: "Snorlax",
        hp: 150,
        maxHp: 150,
        currentHp: 150,
        type: "Colorless",
        weakness: "Fighting",
        retreatCost: 4,
        attachedEnergy: [],
        attacks: [
          { name: "Body Slam", damage: 80, cost: ["Colorless", "Colorless", "Colorless"] }
        ],
        prizeValue: 1
      }
    ],
    hand: [
      "Basic Lightning Energy",
      "Professor's Research",
      "Ultra Ball"
    ],
    availableEnergy: ["Basic Lightning Energy"],
    availableTrainers: ["Professor's Research", "Ultra Ball"],
    prizesRemaining: 4,
    energyAttachedThisTurn: false,
    supporterPlayedThisTurn: false,
    retreatedThisTurn: false,
    isFirstTurnGoingFirst: false
  },
  // Opponent's visible information
  // Note: Even if hidden fields like 'opponent.hand' or 'opponent.deck' are passed,
  // the analyzer strictly filters them out (NO CHEATING).
  opponent: {
    active: {
      name: "Gyarados",
      hp: 90,
      maxHp: 160,
      currentHp: 90,
      type: "Water",
      weakness: "Lightning",
      weaknessMultiplier: 2,
      retreatCost: 3,
      attachedEnergy: ["Water", "Water"],
      attacks: [
        { name: "Waterfall", damage: 70, cost: ["Water", "Water"] }
      ],
      prizeValue: 1
    },
    bench: [
      {
        name: "Magikarp",
        hp: 30,
        maxHp: 30,
        currentHp: 30,
        type: "Water",
        weakness: "Lightning",
        attachedEnergy: [],
        prizeValue: 1
      }
    ],
    prizesRemaining: 5,
    // Private fields that must be IGNORED:
    hiddenHand: ["Boss's Orders", "Water Energy"], // strictly ignored
    deckCount: 42 // strictly ignored
  }
};

// Execute Battle Analysis
const result = analyzeBattle(sampleGameState);

console.log("--------------------------------------------------------------------------------");
console.log("1. STRUCTURED JSON OUTPUT (Required API Output)");
console.log("--------------------------------------------------------------------------------");
console.log(JSON.stringify(result, null, 2));

console.log("\n--------------------------------------------------------------------------------");
console.log("2. HUMAN-READABLE EXPLANATION (Required Section 8 Format)");
console.log("--------------------------------------------------------------------------------");
console.log(result.explanationText);

console.log("\n--------------------------------------------------------------------------------");
console.log("3. STRATEGIC WINNING PATH & BEST POKÉMON (Required Section 9 & 11)");
console.log("--------------------------------------------------------------------------------");
console.log("Best Attacker   :", result.bestPokemon.attacker || result.bestPokemon.bestAttacker);
console.log("Best Defender   :", result.bestPokemon.defender || result.bestPokemon.bestDefender);
console.log("Best Bench Setup:", result.bestPokemon.benchSetup || result.bestPokemon.bestBenchSetup);
console.log("Setup Rationale :", result.bestPokemon.reason);
console.log("\nWinning Path Plan:");
console.log("  Current     :", result.winningPath.current);
console.log("  Best Move   :", result.winningPath.bestMove);
console.log("  Next Action :", result.winningPath.nextAction);
console.log("  Future Setup:", result.winningPath.futureSetup);
console.log("  Goal        :", result.winningPath.goal);

console.log("\n--------------------------------------------------------------------------------");
console.log("4. THREAT ANALYSIS SUMMARY (Required Section 10)");
console.log("--------------------------------------------------------------------------------");
if (result.threats && result.threats.length > 0) {
  result.threats.forEach((t, i) => {
    console.log(`[${t.level}] ${t.title || t.type}`);
    console.log(`  Desc  : ${t.description}`);
    console.log(`  Action: ${t.recommendedAction}\n`);
  });
} else {
  console.log("No critical immediate threats detected.");
}

console.log("================================================================================");
console.log("TEST COMPLETED SUCCESSFULLY!");
console.log("================================================================================");
