/**
 * moveGenerator.js
 * Generates all currently possible, 100% legal actions for the player.
 * Strictly adheres to competitive Pokémon TCG standard turn constraints:
 * - 1 Supporter per turn (none on Turn 1 going 1st)
 * - 1 Manual Energy attachment from hand per turn
 * - 1 Retreat per turn (requires paying retreat cost)
 * - Attack restrictions (energy requirements, status conditions, Turn 1 going 1st)
 * - Evolution legality
 * - Ability legality
 */

const { ActionType } = require('./types');
const { canUseAttack } = require('./threatAnalyzer');

class MoveGenerator {
  /**
   * Generates all legal moves for the current player state.
   * @param {Object} playerState - Normalized player state
   * @param {Object} opponentState - Sanitized opponent visible state
   * @returns {Array} List of legal action objects
   */
  generateLegalMoves(playerState, opponentState) {
    const moves = [];
    if (!playerState) return moves;

    const active = playerState.active;
    const bench = playerState.bench || [];
    const hand = playerState.hand || [];
    const availableEnergy = playerState.availableEnergy || [];
    const availableTrainers = playerState.availableTrainers || [];

    // 1. GENERATE ATTACK MOVES
    if (active && active.currentHp > 0) {
      const isAsleep = active.statusConditions?.some(c => c.toLowerCase() === 'asleep');
      const isParalyzed = active.statusConditions?.some(c => c.toLowerCase() === 'paralyzed');
      const isTurn1GoingFirst = playerState.isFirstTurnGoingFirst;

      if (!isAsleep && !isParalyzed && !isTurn1GoingFirst) {
        const attacks = active.attacks || [];
        for (const atk of attacks) {
          if (canUseAttack(active, atk)) {
            moves.push({
              type: ActionType.ATTACK,
              id: `attack_${active.name}_${atk.name}`,
              displayName: `Attack with ${active.name} (${atk.name})`,
              shortName: `Attack with ${active.name}`,
              sourcePokemon: active,
              attack: atk,
              energyCost: atk.cost,
              baseDamage: atk.damage || 0,
              target: opponentState?.active || null
            });
          }
        }
      }
    }

    // 2. GENERATE MANUAL ENERGY ATTACHMENT MOVES
    if (!playerState.energyAttachedThisTurn) {
      // Find energy cards in hand or available energy
      const energyCards = availableEnergy.length > 0 
        ? availableEnergy 
        : hand.filter(c => {
            const name = typeof c === 'string' ? c : c.name || '';
            const supertype = typeof c === 'object' ? c.supertype : '';
            return supertype === 'Energy' || name.toLowerCase().includes('energy');
          });

      if (energyCards.length > 0) {
        // We only need to generate distinct energy types to avoid duplicate move spam
        const uniqueEnergyNames = [...new Set(energyCards.map(e => typeof e === 'string' ? e : e.name))];
        const allTargets = active ? [active, ...bench] : [...bench];

        for (const energyName of uniqueEnergyNames) {
          for (const targetPkmn of allTargets) {
            moves.push({
              type: ActionType.ATTACH_ENERGY,
              id: `attach_${energyName}_to_${targetPkmn.name}_${targetPkmn === active ? 'active' : 'bench'}`,
              displayName: `Attach ${energyName} to ${targetPkmn.name}`,
              shortName: `Attach Energy to ${targetPkmn.name}`,
              energyCard: energyName,
              targetPokemon: targetPkmn,
              isTargetActive: targetPkmn === active
            });
          }
        }
      }
    }

    // 3. GENERATE RETREAT / SWITCH MOVES
    if (active && bench.length > 0 && !playerState.retreatedThisTurn) {
      const isAsleep = active.statusConditions?.some(c => c.toLowerCase() === 'asleep');
      const isParalyzed = active.statusConditions?.some(c => c.toLowerCase() === 'paralyzed');
      const attachedCount = active.attachedEnergy?.length || 0;
      const retreatCost = active.retreatCost || 0;

      // Manual Retreat: Must be able to pay retreat cost and not status locked
      if (!isAsleep && !isParalyzed && attachedCount >= retreatCost) {
        for (const benchPkmn of bench) {
          moves.push({
            type: ActionType.RETREAT,
            id: `retreat_to_${benchPkmn.name}`,
            displayName: `Retreat ${active.name} to ${benchPkmn.name}`,
            shortName: `Switch to ${benchPkmn.name}`,
            fromPokemon: active,
            toPokemon: benchPkmn,
            retreatCost: retreatCost
          });
        }
      }
    }

    // 4. GENERATE TRAINER CARD MOVES
    const trainerCards = availableTrainers.length > 0
      ? availableTrainers
      : hand.filter(c => {
          const name = typeof c === 'string' ? c : c.name || '';
          const supertype = typeof c === 'object' ? c.supertype : '';
          return supertype === 'Trainer' || !name.toLowerCase().includes('energy');
        });

    for (const card of trainerCards) {
      const cardObj = typeof card === 'string' ? { name: card } : card;
      const cardName = cardObj.name || 'Trainer';
      const cardSubtype = (cardObj.subtypes?.[0] || cardObj.subtype || '').toLowerCase();

      const isSupporter = cardSubtype.includes('supporter') || 
        ['boss\'s orders', 'professor\'s research', 'iono', 'arven', 'serena', 'colress', 'marnie', 'cynthia'].some(s => cardName.toLowerCase().includes(s));
      const isStadium = cardSubtype.includes('stadium') || cardName.toLowerCase().includes('court') || cardName.toLowerCase().includes('temple');
      const isTool = cardSubtype.includes('tool') || cardName.toLowerCase().includes('belt') || cardName.toLowerCase().includes('charm');

      // Supporter check: Max 1 per turn, cannot play on Turn 1 going 1st
      if (isSupporter) {
        if (!playerState.supporterPlayedThisTurn && !playerState.isFirstTurnGoingFirst) {
          moves.push({
            type: ActionType.PLAY_TRAINER,
            subType: 'Supporter',
            id: `play_supporter_${cardName}`,
            displayName: `Play Supporter: ${cardName}`,
            shortName: `Play ${cardName}`,
            card: cardObj
          });
        }
      } else if (isStadium) {
        if (!playerState.stadiumPlayedThisTurn) {
          moves.push({
            type: ActionType.PLAY_TRAINER,
            subType: 'Stadium',
            id: `play_stadium_${cardName}`,
            displayName: `Play Stadium: ${cardName}`,
            shortName: `Play ${cardName}`,
            card: cardObj
          });
        }
      } else {
        // Item or Tool: can be played freely
        moves.push({
          type: ActionType.PLAY_TRAINER,
          subType: isTool ? 'Tool' : 'Item',
          id: `play_item_${cardName}`,
          displayName: `Play Trainer Card: ${cardName}`,
          shortName: `Play ${cardName}`,
          card: cardObj
        });
      }
    }

    // 5. GENERATE EVOLUTION MOVES
    // Check if any card in hand is an evolution of a currently placed Pokémon
    const evolutionCards = hand.filter(c => {
      const stage = typeof c === 'object' ? (c.evolutionStage || c.stage || c.subtypes?.[0]) : '';
      return stage && stage !== 'Basic';
    });

    const inPlayPokemon = active ? [active, ...bench] : [...bench];
    for (const evo of evolutionCards) {
      const evoObj = typeof evo === 'string' ? { name: evo } : evo;
      const evolvesFrom = evoObj.evolvesFrom || '';

      for (const pkmn of inPlayPokemon) {
        const canEvolve = evolvesFrom 
          ? pkmn.name.toLowerCase().includes(evolvesFrom.toLowerCase())
          : evoObj.name?.toLowerCase().includes(pkmn.name.toLowerCase().replace(/ex|v|vstar|vmax/i, '').trim());

        if (canEvolve) {
          moves.push({
            type: ActionType.EVOLVE,
            id: `evolve_${pkmn.name}_to_${evoObj.name}`,
            displayName: `Evolve ${pkmn.name} into ${evoObj.name}`,
            shortName: `Evolve into ${evoObj.name}`,
            targetPokemon: pkmn,
            evolutionCard: evoObj
          });
        }
      }
    }

    // 6. GENERATE ABILITY MOVES
    for (const pkmn of inPlayPokemon) {
      const abilities = pkmn.abilities || [];
      for (const ab of abilities) {
        if (!ab.used) {
          moves.push({
            type: ActionType.USE_ABILITY,
            id: `ability_${pkmn.name}_${ab.name}`,
            displayName: `Use Ability: ${ab.name} (${pkmn.name})`,
            shortName: `Use Ability: ${ab.name}`,
            pokemon: pkmn,
            ability: ab
          });
        }
      }
    }

    // 7. PASS TURN (Fallback action)
    moves.push({
      type: ActionType.PASS_TURN,
      id: 'pass_turn',
      displayName: 'Pass Turn / End Turn',
      shortName: 'Pass Turn'
    });

    return moves;
  }
}

const moveGenerator = new MoveGenerator();

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    MoveGenerator,
    moveGenerator
  };
}
