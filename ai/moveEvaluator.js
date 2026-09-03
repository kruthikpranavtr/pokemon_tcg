/**
 * moveEvaluator.js
 * Comprehensive multi-factor evaluation engine for legal Pokémon TCG actions.
 * 
 * Scores moves across 5 core dimensions:
 * 1. Offensive Value (Damage, Knockout potential, Type weakness, Prize advantage)
 * 2. Defensive Value (Damage reduction, Incoming KO mitigation, HP preservation)
 * 3. Resource Value (Energy efficiency, Draw/search value, Setup momentum)
 * 4. Future Board Position (Bench readiness, Evolution potential, Prize map progress)
 * 5. Risk Penalty (Vulnerability, Overcommitting, Sacrificing key assets)
 * 
 * Returns normalized scores from 0 to 100 with clear tactical rationales.
 */

const { ActionType } = require('./types');
const { calculateDamage } = require('./threatAnalyzer');

class MoveEvaluator {
  /**
   * Evaluates a single legal move within the current game context.
   * @param {Object} move - Legal action object
   * @param {Object} playerState - Normalized player state
   * @param {Object} opponentState - Sanitized opponent visible state
   * @param {Object} threatContext - Output from threatAnalyzer
   * @returns {Object} Scored action with granular breakdown and explanations
   */
  evaluateMove(move, playerState, opponentState, threatContext = {}) {
    let offensiveValue = 0;
    let defensiveValue = 0;
    let resourceValue = 0;
    let futureBoardValue = 0;
    let risk = 0;
    const reasons = [];

    const active = playerState?.active;
    const oppActive = opponentState?.active;
    const playerPrizes = playerState?.prizesRemaining || 6;
    const oppPrizes = opponentState?.prizesRemaining || 6;

    switch (move.type) {
      case ActionType.ATTACK: {
        const atk = move.attack;
        const baseDmg = atk.damage || 0;
        const effectiveDmg = oppActive ? calculateDamage(baseDmg, active.type, oppActive) : baseDmg;
        const oppCurrentHp = oppActive?.currentHp || 100;
        const isKnockout = oppActive && effectiveDmg >= oppCurrentHp;
        const prizesTaken = oppActive ? (oppActive.prizeValue || 1) : 1;
        const isGameWinningKO = isKnockout && (prizesTaken >= playerPrizes);

        if (oppActive) {
          reasons.push(`Opponent's Active Pokémon (${oppActive.name}) has ${oppCurrentHp} HP remaining`);
          reasons.push(`${active.name} can deal ${effectiveDmg} damage using ${atk.name}`);
        }

        // Weakness / Resistance tactical explanation
        if (oppActive?.weakness && oppActive.weakness.toLowerCase() === active.type?.toLowerCase()) {
          reasons.push(`Opponent has a type weakness to ${active.type} (${oppActive.weaknessMultiplier || 2}x damage)`);
          offensiveValue += 20;
        }
        if (oppActive?.resistance && oppActive.resistance.toLowerCase() === active.type?.toLowerCase()) {
          reasons.push(`Opponent has resistance (-30 damage applied)`);
          offensiveValue -= 10;
        }

        reasons.push(`Required Energy (${atk.cost?.join(', ') || 'None'}) is already attached`);

        if (isGameWinningKO) {
          offensiveValue = 100;
          futureBoardValue = 100;
          reasons.push(`🏆 THIS KNOCKOUT TAKES YOUR FINAL PRIZE(S) AND WINS THE MATCH!`);
        } else if (isKnockout) {
          offensiveValue = 90 + Math.min(10, prizesTaken * 4);
          futureBoardValue = 85;
          reasons.push(`This results in a KNOCKOUT, taking ${prizesTaken} Prize card(s)`);
          reasons.push(`Knocking it out strips the opponent of their active attacker`);
        } else {
          // Non-KO Attack
          const damageFraction = oppCurrentHp > 0 ? (effectiveDmg / oppCurrentHp) : 0.5;
          offensiveValue = Math.min(80, Math.round(damageFraction * 75) + 15);
          futureBoardValue = 60;
          reasons.push(`Deals significant pressure (${effectiveDmg} damage), setting up a 2-turn knockout`);

          // Check retaliation risk
          if (threatContext.isImminentKo) {
            risk = 35;
            reasons.push(`Warning: Your Active is vulnerable to a return KO next turn`);
          }
        }

        defensiveValue = isKnockout ? 75 : 40;
        resourceValue = 50;
        break;
      }

      case ActionType.ATTACH_ENERGY: {
        const target = move.targetPokemon;
        const isTargetActive = move.isTargetActive;
        const attachedCount = target.attachedEnergy?.length || 0;
        const nextAttack = target.attacks?.[0];

        resourceValue = 75;

        if (isTargetActive) {
          offensiveValue = 65;
          futureBoardValue = 75;
          defensiveValue = 50;
          reasons.push(`Attaching ${move.energyCard} to Active ${target.name} powers up immediate attacks`);
        } else {
          // Bench attachment
          const isHighValueBench = (target.prizeValue >= 2) || target.name.includes(' ex') || target.name.includes(' V');
          futureBoardValue = isHighValueBench ? 85 : 70;
          offensiveValue = 55;
          defensiveValue = 60;
          reasons.push(`Prepares ${target.name} on the Bench as a secondary or late-game attacker`);
          if (isHighValueBench) {
            reasons.push(`Investing in ${target.name} builds a heavy-damage carry for upcoming turns`);
          }
        }

        if (target.retreatCost > attachedCount) {
          reasons.push(`Also contributes towards paying retreat cost if an escape is needed later`);
        }

        risk = 10;
        break;
      }

      case ActionType.RETREAT: {
        const fromPkmn = move.fromPokemon;
        const toPkmn = move.toPokemon;
        const incomingDmg = threatContext.maxIncomingDamage || 0;

        if (threatContext.isImminentKo) {
          defensiveValue = 90;
          futureBoardValue = 80;
          reasons.push(`Shields ${fromPkmn.name} (${fromPkmn.currentHp} HP) from an imminent knockout next turn`);
          reasons.push(`Denies opponent ${fromPkmn.prizeValue || 1} easy Prize card(s)`);
        } else if (fromPkmn.currentHp <= 40) {
          defensiveValue = 75;
          futureBoardValue = 70;
          reasons.push(`Preserves heavily damaged Active ${fromPkmn.name}`);
        } else {
          defensiveValue = 50;
          futureBoardValue = 50;
          reasons.push(`Switches active position to ${toPkmn.name}`);
        }

        // Check if toPkmn is ready to attack
        const canNewActiveAttack = toPkmn.attacks?.some(a => (toPkmn.attachedEnergy?.length || 0) >= (a.cost?.length || 1));
        if (canNewActiveAttack) {
          offensiveValue = 70;
          reasons.push(`${toPkmn.name} is ready to fight with sufficient energy attached`);
        } else {
          offensiveValue = 35;
          reasons.push(`Note: ${toPkmn.name} may need energy before launching strong attacks`);
        }

        resourceValue = 45; // Cost of discarding energy
        risk = threatContext.isImminentKo ? 10 : 25;
        break;
      }

      case ActionType.PLAY_TRAINER: {
        const cardName = move.card?.name || 'Trainer';
        const subType = move.subType;

        if (subType === 'Supporter') {
          resourceValue = 85;
          futureBoardValue = 80;
          offensiveValue = 50;
          defensiveValue = 60;
          reasons.push(`Playing Supporter ${cardName} accelerates card draw and searches for crucial resources`);
          reasons.push(`Refills hand and unlocks vital tactical options for current and upcoming turns`);
        } else if (subType === 'Stadium') {
          resourceValue = 70;
          futureBoardValue = 75;
          offensiveValue = 55;
          defensiveValue = 60;
          reasons.push(`Playing Stadium ${cardName} alters field conditions in your favor`);
        } else {
          // Item / Tool
          resourceValue = 75;
          futureBoardValue = 70;
          offensiveValue = 50;
          defensiveValue = 55;
          reasons.push(`Playing Item ${cardName} offers immediate zero-cost board acceleration`);
        }

        risk = 5;
        break;
      }

      case ActionType.EVOLVE: {
        const target = move.targetPokemon;
        const evo = move.evolutionCard;

        futureBoardValue = 88;
        offensiveValue = 75;
        defensiveValue = 80;
        resourceValue = 70;
        risk = 5;

        reasons.push(`Evolving ${target.name} into ${evo.name} unlocks higher HP and more devastating attacks`);
        reasons.push(`Reinforces board presence and prevents the Basic form from being targeted`);
        break;
      }

      case ActionType.USE_ABILITY: {
        const ab = move.ability;
        resourceValue = 80;
        futureBoardValue = 75;
        offensiveValue = 60;
        defensiveValue = 60;
        risk = 5;

        reasons.push(`Using ${move.pokemon.name}'s ability "${ab.name}" provides free engine value`);
        break;
      }

      case ActionType.PASS_TURN: {
        offensiveValue = 10;
        defensiveValue = 20;
        resourceValue = 10;
        futureBoardValue = 15;
        risk = 40;
        reasons.push(`No further advantageous plays available this turn; passes initiative to opponent`);
        break;
      }

      default: {
        offensiveValue = 50;
        defensiveValue = 50;
        resourceValue = 50;
        futureBoardValue = 50;
        risk = 20;
        reasons.push(`Standard tactical execution`);
      }
    }

    // Normalized 0 - 100 Score Calculation
    // Weights: Offensive (35%), Defensive (25%), Resource (20%), Future Board (20%), minus Risk (up to 20)
    const rawScore = (offensiveValue * 0.35) + 
                     (defensiveValue * 0.25) + 
                     (resourceValue * 0.20) + 
                     (futureBoardValue * 0.20) - 
                     (risk * 0.20);

    const score = Math.max(5, Math.min(100, Math.round(rawScore)));

    return {
      ...move,
      score,
      breakdown: {
        offensiveValue,
        defensiveValue,
        resourceValue,
        futureBoardValue,
        risk
      },
      reason: reasons
    };
  }

  /**
   * Evaluates and sorts all legal moves.
   * @param {Array} moves - List of legal moves from moveGenerator
   * @param {Object} playerState - Normalized player state
   * @param {Object} opponentState - Sanitized opponent visible state
   * @param {Object} threatContext - Output from threatAnalyzer
   * @returns {Array} Evaluated moves sorted in descending order of score
   */
  evaluateAllMoves(moves, playerState, opponentState, threatContext = {}) {
    if (!moves || moves.length === 0) return [];

    const evaluated = moves.map(m => this.evaluateMove(m, playerState, opponentState, threatContext));
    // Sort descending by score
    evaluated.sort((a, b) => b.score - a.score);
    return evaluated;
  }
}

const moveEvaluator = new MoveEvaluator();

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    MoveEvaluator,
    moveEvaluator
  };
}
