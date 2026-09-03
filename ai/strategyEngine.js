/**
 * strategyEngine.js
 * Analyzes multi-turn winning paths and determines:
 * - Best Active Pokémon
 * - Best Attacking Pokémon
 * - Best Defensive Pokémon
 * - Best Bench Pokémon to prepare
 * - Winning Path (Immediate -> Next -> Future -> Goal)
 * - Strategic recommendations list
 */

const { calculateDamage } = require('./threatAnalyzer');

class StrategyEngine {
  /**
   * Identifies the best Pokémon roles across the player's board.
   * @param {Object} playerState - Normalized player state
   * @param {Object} opponentState - Sanitized opponent visible state
   * @returns {Object} Best Pokémon selections with tactical justifications
   */
  determineBestPokemon(playerState, opponentState) {
    const active = playerState?.active;
    const bench = playerState?.bench || [];
    const allFriendly = active ? [active, ...bench] : [...bench];
    const oppActive = opponentState?.active;

    if (allFriendly.length === 0) {
      return {
        bestActive: null,
        bestAttacker: null,
        bestDefender: null,
        bestBenchSetup: null,
        reason: 'No friendly Pokémon currently in play.'
      };
    }

    // 1. Determine Best Attacker
    // Score based on damage to opponent active, type advantage, energy readiness
    let bestAttacker = allFriendly[0];
    let highestAttackScore = -1;

    for (const p of allFriendly) {
      const attacks = p.attacks || [];
      const attachedCount = p.attachedEnergy?.length || 0;
      let pScore = 0;

      for (const atk of attacks) {
        const baseDmg = atk.damage || 0;
        const effDmg = oppActive ? calculateDamage(baseDmg, p.type, oppActive) : baseDmg;
        const reqEnergy = atk.cost?.length || 1;
        const isReady = attachedCount >= reqEnergy;

        const atkScore = (effDmg * 1.5) + (isReady ? 50 : Math.max(0, 30 - (reqEnergy - attachedCount) * 15));
        if (atkScore > pScore) pScore = atkScore;
      }

      if (pScore > highestAttackScore) {
        highestAttackScore = pScore;
        bestAttacker = p;
      }
    }

    // 2. Determine Best Defender (Highest effective HP, resistance, low prize yield)
    let bestDefender = allFriendly[0];
    let highestDefenseScore = -1;

    for (const p of allFriendly) {
      const prizePenalty = (p.prizeValue || 1) >= 2 ? 20 : 0;
      const resistanceBonus = oppActive && p.resistance?.toLowerCase() === oppActive.type?.toLowerCase() ? 30 : 0;
      const weaknessPenalty = oppActive && p.weakness?.toLowerCase() === oppActive.type?.toLowerCase() ? 40 : 0;

      const defScore = p.currentHp + resistanceBonus - weaknessPenalty - prizePenalty;
      if (defScore > highestDefenseScore) {
        highestDefenseScore = defScore;
        bestDefender = p;
      }
    }

    // 3. Determine Best Bench Setup (High potential bench Pokémon needing investment)
    let bestBenchSetup = null;
    let highestSetupScore = -1;

    for (const p of bench) {
      const isHighPrize = (p.prizeValue || 1) >= 2 || p.name.includes(' ex') || p.name.includes(' V');
      const maxDmg = p.attacks?.reduce((max, a) => Math.max(max, a.damage || 0), 0) || 0;
      const energyNeeded = p.attacks?.[0]?.cost?.length || 2;
      const energyAttached = p.attachedEnergy?.length || 0;

      const setupScore = (maxDmg * 1.2) + (isHighPrize ? 35 : 15) + (p.maxHp * 0.2) - (Math.abs(energyNeeded - energyAttached) * 5);

      if (setupScore > highestSetupScore) {
        highestSetupScore = setupScore;
        bestBenchSetup = p;
      }
    }

    // Fallback if bench is empty or has only 1 option
    if (!bestBenchSetup && bench.length > 0) {
      bestBenchSetup = bench[0];
    }

    // Generate clear reason
    let setupReason = '';
    if (bestBenchSetup) {
      const maxAtk = bestBenchSetup.attacks?.reduce((max, a) => Math.max(max, a.damage || 0), 0) || 0;
      setupReason = `${bestBenchSetup.name} has high future damage potential (${maxAtk} max damage) and should be energized for upcoming turns.`;
    } else {
      setupReason = 'Active Pokémon is currently the primary board asset; prepare basic Pokémon on Bench when drawn.';
    }

    return {
      bestActive: active?.name || 'None',
      bestAttacker: bestAttacker.name,
      bestDefender: bestDefender.name,
      bestBenchSetup: bestBenchSetup?.name || 'None',
      reason: setupReason
    };
  }

  /**
   * Synthesizes multi-turn winning path and structured strategic steps.
   * @param {Object} playerState - Normalized player state
   * @param {Object} opponentState - Sanitized opponent visible state
   * @param {Object} topMove - Top evaluated move
   * @param {Object} bestPokemon - Best Pokémon selections
   * @param {Object} threatContext - Threat analysis results
   * @returns {Object} Structured winning path and strategy points
   */
  generateWinningPath(playerState, opponentState, topMove, bestPokemon, threatContext = {}) {
    const active = playerState?.active;
    const oppActive = opponentState?.active;
    const playerPrizes = playerState?.prizesRemaining || 6;
    const oppPrizes = opponentState?.prizesRemaining || 6;

    const currentDesc = active?.attachedEnergy?.length > 0
      ? `${active.name} is armed with ${active.attachedEnergy.length} Energy`
      : `${active?.name || 'Active Pokémon'} is currently in play`;

    const bestMoveDesc = topMove?.shortName || 'Attack or advance board position';

    const benchTarget = bestPokemon?.bestBenchSetup !== 'None' ? bestPokemon.bestBenchSetup : 'secondary attacker';
    const nextAction = `Prepare ${benchTarget} on the Bench`;

    const futureSetup = `Deploy ${benchTarget} against opponent's follow-up attackers`;

    const goal = playerPrizes <= 2
      ? `Take your final ${playerPrizes} Prize card(s) to close out the victory`
      : `Maintain the Prize race lead (${playerPrizes} prizes remaining vs opponent's ${oppPrizes})`;

    // Generate 3 clean strategy points
    const strategy = [];

    // Point 1: Immediate focus
    if (topMove?.type === 'ATTACK') {
      const isKO = topMove.breakdown?.offensiveValue >= 90;
      strategy.push(isKO 
        ? `Knock out the opponent's Active (${oppActive?.name || 'Active'})`
        : `Apply heavy attack pressure to ${oppActive?.name || 'Active'}`);
    } else if (topMove?.type === 'RETREAT') {
      strategy.push(`Preserve your damaged Active and pivot to ${topMove.toPokemon?.name || 'safety'}`);
    } else {
      strategy.push(`Power up your board and unlock tactical advantages`);
    }

    // Point 2: Bench / Resource Setup
    if (bestPokemon?.bestBenchSetup && bestPokemon.bestBenchSetup !== 'None') {
      strategy.push(`Prepare ${bestPokemon.bestBenchSetup} on the Bench for sustained offense`);
    } else {
      strategy.push(`Search for basic Pokémon to reinforce your Bench`);
    }

    // Point 3: Resource conservation & Prize path
    if (playerState?.availableTrainers?.length > 1 || playerState?.hand?.length >= 4) {
      strategy.push(`Conserve high-impact Trainer cards for future critical turns`);
    } else {
      strategy.push(`Secure Prize card advantages to maintain game tempo`);
    }

    return {
      winningPath: {
        current: currentDesc,
        bestMove: bestMoveDesc,
        nextAction: nextAction,
        futureSetup: futureSetup,
        goal: goal
      },
      strategy: strategy
    };
  }
}

const strategyEngine = new StrategyEngine();

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    StrategyEngine,
    strategyEngine
  };
}
