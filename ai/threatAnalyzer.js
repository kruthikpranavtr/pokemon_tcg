/**
 * threatAnalyzer.js
 * Analyzes opponent's publicly visible board to detect threats,
 * imminent knockouts, type disadvantages, and bench vulnerabilities.
 * 
 * STRICT NO-CHEATING: ONLY uses publicly visible opponent information.
 */

const { ThreatLevel, TYPE_WEAKNESS_MAP, TYPE_RESISTANCE_MAP } = require('./types');

/**
 * Calculates attack damage factoring in weakness and resistance.
 */
function calculateDamage(baseDamage, attackerType, defender) {
  if (!baseDamage || baseDamage <= 0) return 0;
  let damage = baseDamage;

  // Weakness check
  if (defender.weakness && defender.weakness.toLowerCase() === attackerType?.toLowerCase()) {
    damage *= (defender.weaknessMultiplier || 2);
  }

  // Resistance check
  if (defender.resistance && defender.resistance.toLowerCase() === attackerType?.toLowerCase()) {
    damage += (defender.resistanceValue || -30);
  }

  return Math.max(0, damage);
}

/**
 * Checks if a Pokémon has enough energy attached for an attack.
 */
function canUseAttack(pokemon, attack) {
  if (!attack || !attack.cost) return true;
  const attached = pokemon.attachedEnergy || [];
  const requiredCount = attack.cost.length;
  if (attached.length < requiredCount) return false;

  // Basic color match check
  const attachedCopy = [...attached];
  const costCopy = [...attack.cost];

  // Match colored costs first
  for (let i = costCopy.length - 1; i >= 0; i--) {
    const costType = costCopy[i];
    if (costType !== 'Colorless') {
      const idx = attachedCopy.findIndex(e => e.toLowerCase() === costType.toLowerCase());
      if (idx !== -1) {
        attachedCopy.splice(idx, 1);
        costCopy.splice(i, 1);
      }
    }
  }

  // Any remaining costs can be paid with remaining energy
  return attachedCopy.length >= costCopy.length;
}

/**
 * Main Threat Analysis Engine.
 */
class ThreatAnalyzer {
  /**
   * Evaluates the visible threat posed by the opponent.
   * @param {Object} playerState - Normalized player state
   * @param {Object} opponentState - Sanitized opponent visible state
   * @returns {Object} Structured threat assessment
   */
  analyzeThreats(playerState, opponentState) {
    const threats = [];
    const playerActive = playerState?.active;
    const opponentActive = opponentState?.active;
    const opponentBench = opponentState?.bench || [];
    const playerBench = playerState?.bench || [];

    let maxIncomingDamage = 0;
    let highestThreatAttack = null;
    let isImminentKo = false;

    if (!opponentActive && opponentBench.length === 0) {
      return {
        threats: [],
        maxIncomingDamage: 0,
        isImminentKo: false,
        summary: 'No active opponent threats detected.'
      };
    }

    // 1. Check Opponent Active attacks against Player Active
    if (opponentActive && playerActive) {
      const knownAttacks = opponentActive.attacks || [];

      for (const atk of knownAttacks) {
        const canExecute = canUseAttack(opponentActive, atk);
        const dmg = calculateDamage(atk.damage, opponentActive.type, playerActive);

        if (canExecute && dmg > maxIncomingDamage) {
          maxIncomingDamage = dmg;
          highestThreatAttack = { ...atk, projectedDamage: dmg };
        }
      }

      // If attacks list is empty/unknown, estimate standard damage based on energy
      if (knownAttacks.length === 0 && opponentActive.attachedEnergy?.length > 0) {
        const estimatedBase = opponentActive.attachedEnergy.length * 30;
        const estDmg = calculateDamage(estimatedBase, opponentActive.type, playerActive);
        if (estDmg > maxIncomingDamage) {
          maxIncomingDamage = estDmg;
          highestThreatAttack = { name: 'Standard Attack', damage: estimatedBase, projectedDamage: estDmg };
        }
      }

      // Check Imminent Knockout
      if (playerActive.currentHp > 0 && maxIncomingDamage >= playerActive.currentHp) {
        isImminentKo = true;
        threats.push({
          level: ThreatLevel.HIGH,
          type: 'IMMINENT_KNOCKOUT',
          title: '⚠️ HIGH THREAT: Imminent Active Knockout',
          description: `Opponent's Active (${opponentActive.name}) can deal ${maxIncomingDamage} damage next turn using ${highestThreatAttack?.name || 'attack'}, knocking out your Active ${playerActive.name} (${playerActive.currentHp} HP).`,
          recommendedAction: 'Switch to a defensive or sacrificial Pokémon, or retreat your Active.'
        });
      } else if (maxIncomingDamage >= playerActive.currentHp * 0.6) {
        threats.push({
          level: ThreatLevel.MEDIUM,
          type: 'HEAVY_DAMAGE_RISK',
          title: '⚡ MEDIUM THREAT: Severe Damage Risk',
          description: `Opponent's Active (${opponentActive.name}) can deal ${maxIncomingDamage} damage, leaving ${playerActive.name} critically damaged.`,
          recommendedAction: 'Prepare a bench attacker or attach defensive tools/energy.'
        });
      }

      // Check Type Advantage / Weakness
      if (playerActive.weakness && playerActive.weakness.toLowerCase() === opponentActive.type?.toLowerCase()) {
        threats.push({
          level: ThreatLevel.MEDIUM,
          type: 'TYPE_DISADVANTAGE',
          title: '🎯 TYPE WEAKNESS DETECTED',
          description: `Your Active ${playerActive.name} has a direct weakness to ${opponentActive.name}'s ${opponentActive.type} type (${playerActive.weaknessMultiplier || 2}x damage).`,
          recommendedAction: 'Consider switching to a non-weak bench Pokémon.'
        });
      }

      // Check Low HP Active
      if (playerActive.currentHp <= 40 && playerActive.currentHp < playerActive.maxHp) {
        threats.push({
          level: ThreatLevel.MEDIUM,
          type: 'LOW_ACTIVE_HP',
          title: '❤️ LOW HP WARNING',
          description: `Your Active ${playerActive.name} has only ${playerActive.currentHp}/${playerActive.maxHp} HP remaining.`,
          recommendedAction: 'Retreat or heal if possible, or execute an attack before being KO\'d.'
        });
      }
    }

    // 2. Check Opponent Bench Building Threats
    for (const b of opponentBench) {
      const energyCount = b.attachedEnergy?.length || 0;
      const isHighPrize = (b.prizeValue || 1) >= 2 || b.name?.includes(' ex') || b.name?.includes(' V');

      if (energyCount >= 2 || (energyCount >= 1 && isHighPrize)) {
        threats.push({
          level: energyCount >= 3 ? ThreatLevel.HIGH : ThreatLevel.MEDIUM,
          type: 'BENCH_ATTACKER_CHARGING',
          title: `🔋 Opponent Bench Threat: ${b.name}`,
          description: `Opponent is charging ${b.name} on the Bench (${energyCount} energy attached, ${b.currentHp || b.hp} HP).`,
          recommendedAction: 'Prepare a counter-attacker or prioritize taking prize cards quickly.'
        });
      }
    }

    // 3. Check Player Bench Vulnerabilities
    for (const pb of playerBench) {
      if (pb.prizeValue >= 2 && pb.currentHp <= 80 && pb.currentHp < pb.maxHp) {
        threats.push({
          level: ThreatLevel.MEDIUM,
          type: 'VULNERABLE_BENCH_TARGET',
          title: `🛡️ Vulnerable High-Prize Bench: ${pb.name}`,
          description: `Your ${pb.name} on the Bench gives up ${pb.prizeValue} prizes and is damaged (${pb.currentHp}/${pb.maxHp} HP).`,
          recommendedAction: 'Avoid placing it in the active spot without energy, or evolve it.'
        });
      }
    }

    // 4. Resource Starvation Check
    const totalPlayerEnergyInPlay = (playerActive?.attachedEnergy?.length || 0) +
      playerBench.reduce((acc, p) => acc + (p.attachedEnergy?.length || 0), 0);
    const availableEnergyInHand = playerState?.availableEnergy?.length || 0;

    if (totalPlayerEnergyInPlay === 0 && availableEnergyInHand === 0) {
      threats.push({
        level: ThreatLevel.LOW,
        type: 'ENERGY_STARVATION',
        title: '⚡ Energy Reserve Low',
        description: 'No energy attached on board and no energy in hand. Attack capabilities may stall.',
        recommendedAction: 'Use search or draw Trainer cards to locate Energy.'
      });
    }

    // Sort threats: HIGH first, then MEDIUM, then LOW
    const severityOrder = { [ThreatLevel.HIGH]: 0, [ThreatLevel.MEDIUM]: 1, [ThreatLevel.LOW]: 2 };
    threats.sort((a, b) => severityOrder[a.level] - severityOrder[b.level]);

    const summary = threats.length > 0
      ? `${threats[0].title}: ${threats[0].description}`
      : 'Board state is stable. No critical immediate threats.';

    return {
      threats,
      maxIncomingDamage,
      highestThreatAttack,
      isImminentKo,
      summary
    };
  }
}

const threatAnalyzer = new ThreatAnalyzer();

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    ThreatAnalyzer,
    threatAnalyzer,
    calculateDamage,
    canUseAttack
  };
}
