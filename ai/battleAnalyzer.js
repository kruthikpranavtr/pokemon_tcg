/**
 * battleAnalyzer.js
 * Core AI Battle Analyzer Engine for the Pokémon Trading Card Game.
 * 
 * Provides:
 * 1. Simple standalone API:
 *    const result = analyzeBattle(gameState);
 * 
 * 2. Model-Ready Object-Oriented AIAnalyzer class:
 *    class AIAnalyzer {
 *      analyzeBattle(gameState)
 *      generateMoves(gameState)
 *      evaluateMove(move, gameState)
 *      recommendMove(gameState)
 *    }
 * 
 * STRICT NO-CHEATING: Ignores all private/hidden opponent information.
 * PLUGGABLE: Easily replace or augment the evaluator with an ML model / LLM later.
 */

const { sanitizeOpponentState, normalizePlayerState } = require('./types');
const { moveGenerator } = require('./moveGenerator');
const { moveEvaluator } = require('./moveEvaluator');
const { threatAnalyzer } = require('./threatAnalyzer');
const { strategyEngine } = require('./strategyEngine');
const { recommendationEngine } = require('./recommendationEngine');

/**
 * Extracts player and opponent states from diverse game state schemas
 * (supports camelCase, snake_case, nested objects, and common TCG state wrappers).
 */
function extractSides(gameState) {
  if (!gameState || typeof gameState !== 'object') {
    throw new Error('Invalid gameState: Expected an object.');
  }

  // Find Player / Our side
  const rawPlayer = gameState.mySide || 
                    gameState.my_side || 
                    gameState.player || 
                    gameState.our_cards || 
                    gameState.ourCards || 
                    gameState.playerState || 
                    gameState.me ||
                    // Fallback: If active is on top level and opponent is specified
                    (gameState.active && gameState.opponent ? gameState : null) ||
                    {};

  // Find Opponent side
  const rawOpponent = gameState.opponent || 
                      gameState.opponent_side || 
                      gameState.opponentSide || 
                      gameState.opponentVisible || 
                      gameState.opponent_visible || 
                      gameState.opponent_cards || 
                      gameState.opponentCards || 
                      gameState.opponentState || 
                      gameState.enemy ||
                      {};

  return {
    playerState: normalizePlayerState(rawPlayer),
    opponentState: sanitizeOpponentState(rawOpponent)
  };
}

/**
 * Main AI Analyzer Class.
 * Designed to be model-ready so that evaluateMove or recommendMove
 * can be replaced with a neural network, Decision Transformer, or LLM.
 */
class AIAnalyzer {
  constructor(options = {}) {
    this.customEvaluator = options.customEvaluator || null;
  }

  /**
   * Plugs in a custom scoring engine or ML model.
   * Signature: (move, playerState, opponentState, threatContext) => ScoredMove
   */
  setCustomEvaluator(evaluatorFn) {
    this.customEvaluator = evaluatorFn;
  }

  /**
   * Generates all currently legal actions for the player.
   * @param {Object} gameState - Current game state
   * @returns {Array} List of legal action objects
   */
  generateMoves(gameState) {
    const { playerState, opponentState } = extractSides(gameState);
    return moveGenerator.generateLegalMoves(playerState, opponentState);
  }

  /**
   * Evaluates a single move within the game state.
   * @param {Object} move - Action object
   * @param {Object} gameState - Current game state
   * @returns {Object} Scored action with rationales
   */
  evaluateMove(move, gameState) {
    const { playerState, opponentState } = extractSides(gameState);
    const threatContext = threatAnalyzer.analyzeThreats(playerState, opponentState);

    if (typeof this.customEvaluator === 'function') {
      return this.customEvaluator(move, playerState, opponentState, threatContext);
    }
    return moveEvaluator.evaluateMove(move, playerState, opponentState, threatContext);
  }

  /**
   * Main recommendation generator returning the top move and alternatives.
   * @param {Object} gameState - Current game state
   * @returns {Object} Structured recommendation output
   */
  recommendMove(gameState) {
    return this.analyzeBattle(gameState);
  }

  /**
   * Full end-to-end battle analysis pipeline:
   * Game State -> Move Generator -> Move Evaluator -> Threat Analyzer -> Strategy Engine -> Recommendation Engine
   * @param {Object} gameState - Current game state
   * @returns {Object} Final AI recommendation and explanation
   */
  analyzeBattle(gameState) {
    // 1. Sanitize & Normalize (NO-CHEATING GUARANTEE)
    const { playerState, opponentState } = extractSides(gameState);

    // 2. Threat Detection
    const threatContext = threatAnalyzer.analyzeThreats(playerState, opponentState);

    // 3. Generate Legal Moves
    const legalMoves = moveGenerator.generateLegalMoves(playerState, opponentState);

    // 4. Evaluate Moves
    let evaluatedMoves;
    if (typeof this.customEvaluator === 'function') {
      evaluatedMoves = legalMoves.map(m => this.customEvaluator(m, playerState, opponentState, threatContext));
      evaluatedMoves.sort((a, b) => (b.score || 0) - (a.score || 0));
    } else {
      evaluatedMoves = moveEvaluator.evaluateAllMoves(legalMoves, playerState, opponentState, threatContext);
    }

    // 5. Strategy & Winning Path Analysis
    const bestPokemon = strategyEngine.determineBestPokemon(playerState, opponentState);
    const topMove = evaluatedMoves[0] || null;
    const winningPathData = strategyEngine.generateWinningPath(
      playerState,
      opponentState,
      topMove,
      bestPokemon,
      threatContext
    );

    // 6. Synthesize Final Structured Output
    return recommendationEngine.generateRecommendation(
      evaluatedMoves,
      threatContext,
      bestPokemon,
      winningPathData
    );
  }
}

// Default singleton instance
const defaultAnalyzer = new AIAnalyzer();

/**
 * Primary API function specified in the prompt:
 * const result = analyzeBattle(gameState);
 */
function analyzeBattle(gameState) {
  return defaultAnalyzer.analyzeBattle(gameState);
}

// Universal Export: Node.js, CommonJS, Browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    AIAnalyzer,
    analyzeBattle,
    defaultAnalyzer
  };
}

// Browser global exposure
if (typeof window !== 'undefined') {
  window.PokemonAI = window.PokemonAI || {};
  window.PokemonAI.AIAnalyzer = AIAnalyzer;
  window.PokemonAI.analyzeBattle = analyzeBattle;
  window.analyzeBattle = analyzeBattle;
}
