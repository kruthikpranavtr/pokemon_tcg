/**
 * ai/index.js
 * Unified entry point for the Pokémon TCG AI Battle Analyzer Engine.
 * 
 * Usage:
 *   const { analyzeBattle, AIAnalyzer } = require('./ai');
 *   // or in browser:
 *   <script src="ai/index.js"></script>
 *   const result = analyzeBattle(gameState);
 */

const {
  ActionType,
  ThreatLevel,
  PokemonType,
  TYPE_WEAKNESS_MAP,
  TYPE_RESISTANCE_MAP,
  sanitizeOpponentState,
  normalizePlayerState
} = require('./types');

const { ThreatAnalyzer, threatAnalyzer, calculateDamage, canUseAttack } = require('./threatAnalyzer');
const { MoveGenerator, moveGenerator } = require('./moveGenerator');
const { MoveEvaluator, moveEvaluator } = require('./moveEvaluator');
const { StrategyEngine, strategyEngine } = require('./strategyEngine');
const { RecommendationEngine, recommendationEngine } = require('./recommendationEngine');
const { AIAnalyzer, analyzeBattle, defaultAnalyzer } = require('./battleAnalyzer');

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    // Primary API
    analyzeBattle,
    AIAnalyzer,
    defaultAnalyzer,

    // Core Sub-Engines
    threatAnalyzer,
    ThreatAnalyzer,
    moveGenerator,
    MoveGenerator,
    moveEvaluator,
    MoveEvaluator,
    strategyEngine,
    StrategyEngine,
    recommendationEngine,
    RecommendationEngine,

    // Utilities & Types
    ActionType,
    ThreatLevel,
    PokemonType,
    TYPE_WEAKNESS_MAP,
    TYPE_RESISTANCE_MAP,
    sanitizeOpponentState,
    normalizePlayerState,
    calculateDamage,
    canUseAttack
  };
}

if (typeof window !== 'undefined') {
  window.PokemonAI = {
    analyzeBattle,
    AIAnalyzer,
    defaultAnalyzer,
    threatAnalyzer,
    moveGenerator,
    moveEvaluator,
    strategyEngine,
    recommendationEngine,
    ActionType,
    ThreatLevel
  };
  window.analyzeBattle = analyzeBattle;
}
