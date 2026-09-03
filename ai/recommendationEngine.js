/**
 * recommendationEngine.js
 * Synthesizes evaluated moves, threat context, best Pokémon, and winning paths
 * into the exact structured JSON response and human-readable explanation text.
 */

class RecommendationEngine {
  /**
   * Builds the final recommendation payload.
   * @param {Array} evaluatedMoves - Evaluated moves sorted descending by score
   * @param {Object} threatContext - Output from threatAnalyzer
   * @param {Object} bestPokemon - Output from strategyEngine
   * @param {Object} winningPathData - Winning path and strategy points from strategyEngine
   * @returns {Object} Structured recommendation object matching specification
   */
  generateRecommendation(evaluatedMoves, threatContext, bestPokemon, winningPathData) {
    if (!evaluatedMoves || evaluatedMoves.length === 0) {
      return {
        recommendedMove: "Pass Turn",
        score: 10,
        confidence: 50,
        reason: ["No legal aggressive or resource actions currently available in this game state."],
        alternatives: [],
        strategy: ["Conserve resources and wait for next turn draw"],
        threats: threatContext?.threats || [],
        bestPokemon: bestPokemon || {},
        winningPath: winningPathData?.winningPath || {},
        explanationText: "🤖 Recommended Move\n\nPass Turn\n\nWhy?\n• No other legal moves available in current state\n\nConfidence: 50%"
      };
    }

    const topMove = evaluatedMoves[0];
    const secondMove = evaluatedMoves.length > 1 ? evaluatedMoves[1] : null;

    // Confidence Calculation:
    // Blends absolute move score with the lead margin over the #2 alternative
    const scoreLead = secondMove ? Math.max(0, topMove.score - secondMove.score) : 15;
    const confidenceRaw = (topMove.score * 0.75) + Math.min(20, scoreLead * 1.2);
    const confidence = Math.max(50, Math.min(99, Math.round(confidenceRaw)));

    // Format alternative moves
    const alternatives = evaluatedMoves.slice(1, 5).map(m => ({
      move: m.shortName || m.displayName,
      score: m.score
    }));

    // Filter and deduplicate reasons
    const cleanReasons = [...new Set(topMove.reason || [])].filter(Boolean);
    if (cleanReasons.length === 0) {
      cleanReasons.push("Optimizes current board position and advances resource advantage");
    }

    // Recommended move name
    const moveTitle = topMove.shortName || topMove.displayName;

    // Build Formatted Explanation Text (Section 8 Format)
    const reasonBullets = cleanReasons.map(r => `• ${r}`).join('\n');
    const explanationText = `🤖 Recommended Move\n\n${moveTitle}\n\nWhy?\n\n${reasonBullets}\n\nConfidence: ${confidence}%`;

    return {
      recommendedMove: moveTitle,
      score: topMove.score,
      confidence: confidence,
      reason: cleanReasons,
      alternatives: alternatives,
      strategy: winningPathData?.strategy || [],
      threats: threatContext?.threats || [],
      bestPokemon: bestPokemon || {},
      winningPath: winningPathData?.winningPath || {},
      explanationText: explanationText,
      // Granular metadata for rich UI dashboards or deep debugging
      actionDetails: {
        id: topMove.id,
        type: topMove.type,
        displayName: topMove.displayName,
        breakdown: topMove.breakdown
      },
      allPossibleMoves: evaluatedMoves.map(m => ({
        move: m.displayName,
        shortMove: m.shortName,
        type: m.type,
        score: m.score,
        reasons: m.reason
      }))
    };
  }
}

const recommendationEngine = new RecommendationEngine();

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    RecommendationEngine,
    recommendationEngine
  };
}
