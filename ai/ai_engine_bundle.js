/**
 * ai_engine_bundle.js
 * Standalone Browser & Node.js Universal Bundle for Pokémon TCG AI Battle Analyzer Engine.
 * Zero-dependency: Drop directly into any HTML page via:
 *   <script src="ai/ai_engine_bundle.js"></script>
 * Then call:
 *   const result = analyzeBattle(gameState);
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    var exp = factory();
    root.PokemonAI = exp;
    root.analyzeBattle = exp.analyzeBattle;
    root.AIAnalyzer = exp.AIAnalyzer;
  }
}(typeof self !== 'undefined' ? self : this, function () {

  // 1. TYPES & CONSTANTS
  var ActionType = Object.freeze({
    ATTACK: 'ATTACK',
    ATTACH_ENERGY: 'ATTACH_ENERGY',
    RETREAT: 'RETREAT',
    SWITCH: 'SWITCH',
    PLAY_TRAINER: 'PLAY_TRAINER',
    EVOLVE: 'EVOLVE',
    USE_ABILITY: 'USE_ABILITY',
    PASS_TURN: 'PASS_TURN'
  });

  var ThreatLevel = Object.freeze({
    HIGH: 'HIGH',
    MEDIUM: 'MEDIUM',
    LOW: 'LOW'
  });

  var TYPE_WEAKNESS_MAP = {
    Fire: 'Water',
    Water: 'Lightning',
    Lightning: 'Fighting',
    Fighting: 'Psychic',
    Psychic: 'Darkness',
    Darkness: 'Grass',
    Grass: 'Fire',
    Metal: 'Fire',
    Dragon: 'Colorless',
    Colorless: 'Fighting'
  };

  // 2. NO-CHEATING SANITIZER
  function sanitizeOpponentState(rawOpponent) {
    if (!rawOpponent) return null;

    function sanitizePokemon(p) {
      if (!p) return null;
      var maxHp = Number(p.maxHp || p.max_hp || p.hp || 0);
      var damage = Number(p.damage || 0);
      var currentHp = Math.max(0, Number(p.currentHp ?? p.current_hp ?? (maxHp - damage)));

      return {
        name: p.name || p.cardName || 'Unknown Pokémon',
        hp: currentHp,
        maxHp: maxHp,
        damage: damage,
        currentHp: currentHp,
        type: p.type || p.pokemonType || p.types?.[0] || 'Colorless',
        weakness: p.weakness || p.weaknesses?.[0]?.type || TYPE_WEAKNESS_MAP[p.type] || null,
        weaknessMultiplier: Number(p.weaknessMultiplier || p.weaknesses?.[0]?.value?.replace('x', '') || 2),
        resistance: p.resistance || p.resistances?.[0]?.type || null,
        resistanceValue: Number(p.resistanceValue || p.resistances?.[0]?.value || -30),
        retreatCost: Number(p.retreatCost ?? p.retreat_cost ?? p.retreat ?? 1),
        attachedEnergy: Array.isArray(p.attachedEnergy || p.attached_energy)
          ? (p.attachedEnergy || p.attached_energy).slice()
          : typeof (p.attachedEnergy || p.attached_energy) === 'number'
            ? Array(p.attachedEnergy || p.attached_energy).fill('Colorless')
            : [],
        attacks: Array.isArray(p.attacks) ? p.attacks.map(function (a) {
          return {
            name: a.name || 'Unknown Attack',
            damage: Number(a.damage || a.baseDamage || 0),
            cost: a.cost || a.energyCost || ['Colorless'],
            effect: a.effect || a.description || ''
          };
        }) : [],
        abilities: Array.isArray(p.abilities) ? p.abilities.map(function (ab) {
          return {
            name: ab.name || 'Unknown Ability',
            effect: ab.effect || ab.description || '',
            type: ab.type || 'Ability'
          };
        }) : [],
        statusConditions: p.statusConditions || p.status || p.condition || [],
        evolutionStage: p.evolutionStage || p.stage || p.subtypes?.[0] || 'Basic',
        prizeValue: Number(p.prizeValue || p.prizes || (p.name && p.name.includes(' VMAX') ? 3 : (p.name && (p.name.includes(' ex') || p.name.includes(' V')) ? 2 : 1)))
      };
    }

    return {
      active: sanitizePokemon(rawOpponent.active || rawOpponent.activePokemon || rawOpponent.active_pokemon),
      bench: Array.isArray(rawOpponent.bench || rawOpponent.benchPokemon || rawOpponent.bench_pokemon)
        ? (rawOpponent.bench || rawOpponent.benchPokemon || rawOpponent.bench_pokemon).map(sanitizePokemon).filter(Boolean)
        : [],
      prizesRemaining: Number(rawOpponent.prizesRemaining ?? rawOpponent.prizes_remaining ?? rawOpponent.prizes ?? 6)
    };
  }

  // 3. NORMALIZER FOR PLAYER
  function normalizePlayerState(rawPlayer) {
    if (!rawPlayer) return null;

    function normalizePokemon(p) {
      if (!p) return null;
      var maxHp = Number(p.maxHp || p.max_hp || p.hp || 100);
      var damage = Number(p.damage || 0);
      var currentHp = Math.max(0, Number(p.currentHp ?? p.current_hp ?? (maxHp - damage)));

      return {
        name: p.name || p.cardName || 'Unknown Pokémon',
        hp: currentHp,
        maxHp: maxHp,
        damage: damage,
        currentHp: currentHp,
        type: p.type || p.pokemonType || p.types?.[0] || 'Colorless',
        weakness: p.weakness || p.weaknesses?.[0]?.type || TYPE_WEAKNESS_MAP[p.type] || null,
        weaknessMultiplier: Number(p.weaknessMultiplier || 2),
        resistance: p.resistance || p.resistances?.[0]?.type || null,
        resistanceValue: Number(p.resistanceValue || -30),
        retreatCost: Number(p.retreatCost ?? p.retreat_cost ?? p.retreat ?? 1),
        attachedEnergy: Array.isArray(p.attachedEnergy || p.attached_energy)
          ? (p.attachedEnergy || p.attached_energy).slice()
          : typeof (p.attachedEnergy || p.attached_energy) === 'number'
            ? Array(p.attachedEnergy || p.attached_energy).fill('Colorless')
            : [],
        attacks: Array.isArray(p.attacks) ? p.attacks.map(function (a) {
          return {
            name: a.name || 'Attack',
            damage: Number(a.damage || a.baseDamage || 0),
            cost: a.cost || a.energyCost || ['Colorless'],
            effect: a.effect || a.description || ''
          };
        }) : [],
        abilities: Array.isArray(p.abilities) ? p.abilities.map(function (ab) {
          return {
            name: ab.name || 'Ability',
            effect: ab.effect || ab.description || '',
            used: Boolean(ab.used || ab.usedThisTurn)
          };
        }) : [],
        statusConditions: Array.isArray(p.statusConditions || p.status)
          ? (p.statusConditions || p.status)
          : (p.statusConditions || p.status ? [p.statusConditions || p.status] : []),
        evolutionStage: p.evolutionStage || p.stage || p.subtypes?.[0] || 'Basic',
        prizeValue: Number(p.prizeValue || p.prizes || (p.name && p.name.includes(' VMAX') ? 3 : (p.name && (p.name.includes(' ex') || p.name.includes(' V')) ? 2 : 1)))
      };
    }

    return {
      active: normalizePokemon(rawPlayer.active || rawPlayer.activePokemon || rawPlayer.active_pokemon),
      bench: Array.isArray(rawPlayer.bench || rawPlayer.benchPokemon || rawPlayer.bench_pokemon)
        ? (rawPlayer.bench || rawPlayer.benchPokemon || rawPlayer.bench_pokemon).map(normalizePokemon).filter(Boolean)
        : [],
      hand: Array.isArray(rawPlayer.hand || rawPlayer.handCards || rawPlayer.hand_cards)
        ? (rawPlayer.hand || rawPlayer.handCards || rawPlayer.hand_cards).slice()
        : [],
      availableTrainers: Array.isArray(rawPlayer.availableTrainers || rawPlayer.trainers)
        ? (rawPlayer.availableTrainers || rawPlayer.trainers).slice()
        : [],
      availableEnergy: Array.isArray(rawPlayer.availableEnergy || rawPlayer.energyCards || rawPlayer.energy_cards)
        ? (rawPlayer.availableEnergy || rawPlayer.energyCards || rawPlayer.energy_cards).slice()
        : [],
      prizesRemaining: Number(rawPlayer.prizesRemaining ?? rawPlayer.prizes_remaining ?? rawPlayer.prizes ?? 6),
      energyAttachedThisTurn: Boolean(rawPlayer.energyAttachedThisTurn ?? rawPlayer.energy_attached_this_turn),
      supporterPlayedThisTurn: Boolean(rawPlayer.supporterPlayedThisTurn ?? rawPlayer.supporter_played_this_turn),
      retreatedThisTurn: Boolean(rawPlayer.retreatedThisTurn ?? rawPlayer.retreated_this_turn),
      stadiumPlayedThisTurn: Boolean(rawPlayer.stadiumPlayedThisTurn ?? rawPlayer.stadium_played_this_turn),
      isFirstTurnGoingFirst: Boolean(rawPlayer.isFirstTurnGoingFirst ?? rawPlayer.turn_1_going_first)
    };
  }

  // 4. DAMAGE & ENERGY HELPER
  function calculateDamage(baseDamage, attackerType, defender) {
    if (!baseDamage || baseDamage <= 0) return 0;
    var damage = baseDamage;
    if (defender && defender.weakness && attackerType && defender.weakness.toLowerCase() === attackerType.toLowerCase()) {
      damage *= (defender.weaknessMultiplier || 2);
    }
    if (defender && defender.resistance && attackerType && defender.resistance.toLowerCase() === attackerType.toLowerCase()) {
      damage += (defender.resistanceValue || -30);
    }
    return Math.max(0, damage);
  }

  function canUseAttack(pokemon, attack) {
    if (!attack || !attack.cost) return true;
    var attached = pokemon.attachedEnergy || [];
    if (attached.length < attack.cost.length) return false;

    var attachedCopy = attached.slice();
    var costCopy = attack.cost.slice();

    for (var i = costCopy.length - 1; i >= 0; i--) {
      var costType = costCopy[i];
      if (costType !== 'Colorless') {
        var idx = attachedCopy.findIndex(function (e) {
          return e.toLowerCase() === costType.toLowerCase();
        });
        if (idx !== -1) {
          attachedCopy.splice(idx, 1);
          costCopy.splice(i, 1);
        }
      }
    }
    return attachedCopy.length >= costCopy.length;
  }

  // 5. THREAT ANALYZER
  function analyzeThreats(playerState, opponentState) {
    var threats = [];
    var playerActive = playerState ? playerState.active : null;
    var opponentActive = opponentState ? opponentState.active : null;
    var opponentBench = opponentState ? opponentState.bench : [];
    var playerBench = playerState ? playerState.bench : [];

    var maxIncomingDamage = 0;
    var highestThreatAttack = null;
    var isImminentKo = false;

    if (opponentActive && playerActive) {
      var knownAttacks = opponentActive.attacks || [];
      for (var i = 0; i < knownAttacks.length; i++) {
        var atk = knownAttacks[i];
        if (canUseAttack(opponentActive, atk)) {
          var dmg = calculateDamage(atk.damage, opponentActive.type, playerActive);
          if (dmg > maxIncomingDamage) {
            maxIncomingDamage = dmg;
            highestThreatAttack = atk;
          }
        }
      }

      if (knownAttacks.length === 0 && opponentActive.attachedEnergy && opponentActive.attachedEnergy.length > 0) {
        var estBase = opponentActive.attachedEnergy.length * 30;
        var estDmg = calculateDamage(estBase, opponentActive.type, playerActive);
        if (estDmg > maxIncomingDamage) {
          maxIncomingDamage = estDmg;
          highestThreatAttack = { name: 'Standard Attack', damage: estBase };
        }
      }

      if (playerActive.currentHp > 0 && maxIncomingDamage >= playerActive.currentHp) {
        isImminentKo = true;
        threats.push({
          level: ThreatLevel.HIGH,
          type: 'IMMINENT_KNOCKOUT',
          title: '⚠️ HIGH THREAT: Imminent Knockout',
          description: "Opponent's Active Pokémon can knock out your Active Pokémon next turn.",
          recommendedAction: 'Switch to your defensive Pokémon.'
        });
      } else if (maxIncomingDamage >= playerActive.currentHp * 0.6) {
        threats.push({
          level: ThreatLevel.MEDIUM,
          type: 'HEAVY_DAMAGE_RISK',
          title: '⚡ MEDIUM THREAT: Heavy Damage Risk',
          description: "Opponent's Active can deal " + maxIncomingDamage + " damage to your Active.",
          recommendedAction: 'Prepare a bench attacker or retreat.'
        });
      }

      if (playerActive.weakness && opponentActive.type && playerActive.weakness.toLowerCase() === opponentActive.type.toLowerCase()) {
        threats.push({
          level: ThreatLevel.MEDIUM,
          type: 'TYPE_DISADVANTAGE',
          title: '🎯 Opponent Type Advantage',
          description: "Opponent has a type advantage against your Active Pokémon (" + (playerActive.weaknessMultiplier || 2) + "x).",
          recommendedAction: 'Consider switching to a non-weak Pokémon.'
        });
      }

      if (playerActive.currentHp <= 40 && playerActive.currentHp < playerActive.maxHp) {
        threats.push({
          level: ThreatLevel.MEDIUM,
          type: 'LOW_ACTIVE_HP',
          title: '❤️ My Active Pokémon is Low HP',
          description: 'Your Active has only ' + playerActive.currentHp + '/' + playerActive.maxHp + ' HP left.',
          recommendedAction: 'Heal or retreat before being knocked out.'
        });
      }
    }

    for (var b = 0; b < opponentBench.length; b++) {
      var ob = opponentBench[b];
      var obEnergy = ob.attachedEnergy ? ob.attachedEnergy.length : 0;
      if (obEnergy >= 2) {
        threats.push({
          level: obEnergy >= 3 ? ThreatLevel.HIGH : ThreatLevel.MEDIUM,
          type: 'BENCH_ATTACKER_CHARGING',
          title: '🔋 Opponent Building Strong Attacker',
          description: 'Opponent is charging ' + ob.name + ' on the Bench with ' + obEnergy + ' Energy.',
          recommendedAction: 'Pressure opponent actively before bench attacker enters play.'
        });
      }
    }

    for (var pb = 0; pb < playerBench.length; pb++) {
      var myB = playerBench[pb];
      if (myB.prizeValue >= 2 && myB.currentHp <= 80 && myB.currentHp < myB.maxHp) {
        threats.push({
          level: ThreatLevel.MEDIUM,
          type: 'VULNERABLE_BENCH_TARGET',
          title: '🛡️ Important Bench Pokémon is Vulnerable',
          description: myB.name + ' on Bench gives up ' + myB.prizeValue + ' prizes and is damaged.',
          recommendedAction: 'Keep safe from bench-targeting attacks.'
        });
      }
    }

    var totalEnergy = (playerActive && playerActive.attachedEnergy ? playerActive.attachedEnergy.length : 0);
    if (totalEnergy === 0 && (!playerState.availableEnergy || playerState.availableEnergy.length === 0)) {
      threats.push({
        level: ThreatLevel.LOW,
        type: 'ENERGY_STARVATION',
        title: '⚡ Running Out of Energy',
        description: 'Low energy presence on board and hand.',
        recommendedAction: 'Use search or draw Trainers to acquire energy.'
      });
    }

    return {
      threats: threats,
      maxIncomingDamage: maxIncomingDamage,
      highestThreatAttack: highestThreatAttack,
      isImminentKo: isImminentKo
    };
  }

  // 6. MOVE GENERATOR
  function generateLegalMoves(playerState, opponentState) {
    var moves = [];
    if (!playerState) return moves;

    var active = playerState.active;
    var bench = playerState.bench || [];
    var hand = playerState.hand || [];
    var availableEnergy = playerState.availableEnergy || [];
    var availableTrainers = playerState.availableTrainers || [];

    // Attacks
    if (active && active.currentHp > 0) {
      var isAsleep = active.statusConditions && active.statusConditions.some(function (c) { return c.toLowerCase() === 'asleep'; });
      var isParalyzed = active.statusConditions && active.statusConditions.some(function (c) { return c.toLowerCase() === 'paralyzed'; });
      if (!isAsleep && !isParalyzed && !playerState.isFirstTurnGoingFirst) {
        var attacks = active.attacks || [];
        for (var i = 0; i < attacks.length; i++) {
          var atk = attacks[i];
          if (canUseAttack(active, atk)) {
            moves.push({
              type: ActionType.ATTACK,
              id: 'attack_' + active.name + '_' + atk.name,
              displayName: 'Attack with ' + active.name + ' (' + atk.name + ')',
              shortName: 'Attack with ' + active.name,
              sourcePokemon: active,
              attack: atk,
              energyCost: atk.cost,
              baseDamage: atk.damage || 0,
              target: opponentState ? opponentState.active : null
            });
          }
        }
      }
    }

    // Attach Energy
    if (!playerState.energyAttachedThisTurn) {
      var energyCards = availableEnergy.length > 0
        ? availableEnergy
        : hand.filter(function (c) {
          var name = typeof c === 'string' ? c : c.name || '';
          return name.toLowerCase().includes('energy');
        });

      if (energyCards.length > 0) {
        var energyNames = [];
        for (var e = 0; e < energyCards.length; e++) {
          var eName = typeof energyCards[e] === 'string' ? energyCards[e] : energyCards[e].name;
          if (energyNames.indexOf(eName) === -1) energyNames.push(eName);
        }
        var targets = active ? [active].concat(bench) : bench;
        for (var en = 0; en < energyNames.length; en++) {
          for (var t = 0; t < targets.length; t++) {
            moves.push({
              type: ActionType.ATTACH_ENERGY,
              id: 'attach_' + energyNames[en] + '_to_' + targets[t].name,
              displayName: 'Attach ' + energyNames[en] + ' to ' + targets[t].name,
              shortName: 'Attach Energy to ' + targets[t].name,
              energyCard: energyNames[en],
              targetPokemon: targets[t],
              isTargetActive: targets[t] === active
            });
          }
        }
      }
    }

    // Retreat / Switch
    if (active && bench.length > 0 && !playerState.retreatedThisTurn) {
      var attachedCount = active.attachedEnergy ? active.attachedEnergy.length : 0;
      var retreatCost = active.retreatCost || 0;
      if (attachedCount >= retreatCost) {
        for (var bi = 0; bi < bench.length; bi++) {
          moves.push({
            type: ActionType.RETREAT,
            id: 'retreat_to_' + bench[bi].name,
            displayName: 'Retreat ' + active.name + ' to ' + bench[bi].name,
            shortName: 'Switch to ' + bench[bi].name,
            fromPokemon: active,
            toPokemon: bench[bi],
            retreatCost: retreatCost
          });
        }
      }
    }

    // Trainer Cards
    var trainers = availableTrainers.length > 0
      ? availableTrainers
      : hand.filter(function (c) {
        var name = typeof c === 'string' ? c : c.name || '';
        return !name.toLowerCase().includes('energy');
      });

    for (var tr = 0; tr < trainers.length; tr++) {
      var card = trainers[tr];
      var cardObj = typeof card === 'string' ? { name: card } : card;
      var cardName = cardObj.name || 'Trainer';
      var isSupporter = cardName.toLowerCase().includes('research') || cardName.toLowerCase().includes('iono') || cardName.toLowerCase().includes('boss');

      if (isSupporter) {
        if (!playerState.supporterPlayedThisTurn && !playerState.isFirstTurnGoingFirst) {
          moves.push({
            type: ActionType.PLAY_TRAINER,
            subType: 'Supporter',
            id: 'play_' + cardName,
            displayName: 'Play Supporter: ' + cardName,
            shortName: 'Play ' + cardName,
            card: cardObj
          });
        }
      } else {
        moves.push({
          type: ActionType.PLAY_TRAINER,
          subType: 'Item',
          id: 'play_' + cardName,
          displayName: 'Play Trainer Card: ' + cardName,
          shortName: 'Play ' + cardName,
          card: cardObj
        });
      }
    }

    // Evolve
    var allInPlay = active ? [active].concat(bench) : bench;
    for (var h = 0; h < hand.length; h++) {
      var hCard = hand[h];
      var hObj = typeof hCard === 'string' ? { name: hCard } : hCard;
      var evoFrom = hObj.evolvesFrom || '';
      for (var pIdx = 0; pIdx < allInPlay.length; pIdx++) {
        var inPlay = allInPlay[pIdx];
        if (evoFrom && inPlay.name.toLowerCase().includes(evoFrom.toLowerCase())) {
          moves.push({
            type: ActionType.EVOLVE,
            id: 'evolve_' + inPlay.name + '_to_' + hObj.name,
            displayName: 'Evolve ' + inPlay.name + ' into ' + hObj.name,
            shortName: 'Evolve into ' + hObj.name,
            targetPokemon: inPlay,
            evolutionCard: hObj
          });
        }
      }
    }

    // Pass turn fallback
    moves.push({
      type: ActionType.PASS_TURN,
      id: 'pass_turn',
      displayName: 'Pass Turn',
      shortName: 'Pass Turn'
    });

    return moves;
  }

  // 7. MOVE EVALUATOR
  function evaluateMove(move, playerState, opponentState, threatContext) {
    var offensiveValue = 0;
    var defensiveValue = 0;
    var resourceValue = 0;
    var futureBoardValue = 0;
    var risk = 0;
    var reasons = [];

    var active = playerState ? playerState.active : null;
    var oppActive = opponentState ? opponentState.active : null;

    if (move.type === ActionType.ATTACK) {
      var atk = move.attack;
      var baseDmg = atk.damage || 0;
      var effDmg = oppActive ? calculateDamage(baseDmg, active.type, oppActive) : baseDmg;
      var oppHp = oppActive ? oppActive.currentHp : 100;
      var isKo = oppActive && effDmg >= oppHp;

      if (oppActive) {
        reasons.push("Opponent's Active Pokémon has " + oppHp + " HP remaining");
        reasons.push(active.name + " can deal " + effDmg + " damage");
      }
      if (oppActive && oppActive.weakness && active && oppActive.weakness.toLowerCase() === active.type.toLowerCase()) {
        reasons.push("Opponent has a type weakness");
        offensiveValue += 20;
      }
      reasons.push("Required Energy is already attached");

      if (isKo) {
        offensiveValue = 95;
        futureBoardValue = 90;
        reasons.push("This results in a knockout");
        reasons.push("Knocking it out gives a strong advantage");
      } else {
        var pct = oppHp > 0 ? (effDmg / oppHp) : 0.5;
        offensiveValue = Math.min(80, Math.round(pct * 75) + 15);
        futureBoardValue = 65;
        reasons.push("Weakens opponent's active attacker");
      }
      defensiveValue = isKo ? 75 : 40;
      resourceValue = 50;
    } else if (move.type === ActionType.ATTACH_ENERGY) {
      resourceValue = 75;
      if (move.isTargetActive) {
        offensiveValue = 65;
        futureBoardValue = 75;
        defensiveValue = 50;
        reasons.push("Powers up Active " + move.targetPokemon.name + "'s attacks");
      } else {
        offensiveValue = 55;
        futureBoardValue = 85;
        defensiveValue = 60;
        reasons.push("Prepares " + move.targetPokemon.name + " on the Bench");
      }
    } else if (move.type === ActionType.RETREAT) {
      if (threatContext && threatContext.isImminentKo) {
        defensiveValue = 90;
        futureBoardValue = 80;
        reasons.push("Shields " + move.fromPokemon.name + " from incoming knockout");
      } else {
        defensiveValue = 60;
        futureBoardValue = 60;
        reasons.push("Switches active Pokémon to " + move.toPokemon.name);
      }
      offensiveValue = 50;
      resourceValue = 40;
    } else if (move.type === ActionType.PLAY_TRAINER) {
      resourceValue = 80;
      futureBoardValue = 75;
      offensiveValue = 50;
      defensiveValue = 55;
      reasons.push("Provides valuable card draw and tactical options");
    } else if (move.type === ActionType.EVOLVE) {
      futureBoardValue = 90;
      offensiveValue = 75;
      defensiveValue = 80;
      resourceValue = 70;
      reasons.push("Increases Max HP and unlocks stronger attacks");
    } else {
      // Pass turn
      offensiveValue = 10;
      defensiveValue = 20;
      resourceValue = 10;
      futureBoardValue = 10;
      risk = 30;
      reasons.push("Passes initiative to opponent");
    }

    var rawScore = (offensiveValue * 0.35) +
                   (defensiveValue * 0.25) +
                   (resourceValue * 0.20) +
                   (futureBoardValue * 0.20) -
                   (risk * 0.20);
    var score = Math.max(5, Math.min(100, Math.round(rawScore)));

    return {
      type: move.type,
      id: move.id,
      displayName: move.displayName,
      shortName: move.shortName,
      score: score,
      reason: reasons
    };
  }

  // 8. STRATEGY ENGINE
  function determineBestPokemon(playerState, opponentState) {
    var active = playerState ? playerState.active : null;
    var bench = playerState ? playerState.bench : [];
    var all = active ? [active].concat(bench) : bench;

    var attacker = all.length > 0 ? all[0].name : 'None';
    var defender = all.length > 0 ? all[0].name : 'None';
    var benchSetup = bench.length > 0 ? bench[0].name : 'None';

    if (all.length > 1) {
      // Find highest max attack
      var maxAtk = -1;
      for (var i = 0; i < all.length; i++) {
        var p = all[i];
        var atks = p.attacks || [];
        for (var a = 0; a < atks.length; a++) {
          if ((atks[a].damage || 0) > maxAtk) {
            maxAtk = atks[a].damage || 0;
            attacker = p.name;
          }
        }
      }
      // Defender is highest HP
      var maxHp = -1;
      for (var j = 0; j < all.length; j++) {
        if (all[j].currentHp > maxHp) {
          maxHp = all[j].currentHp;
          defender = all[j].name;
        }
      }
    }

    return {
      attacker: attacker,
      defender: defender,
      benchSetup: benchSetup,
      reason: benchSetup !== 'None'
        ? benchSetup + ' requires additional Energy but has high future damage potential.'
        : 'Active Pokémon is currently the primary board asset.'
    };
  }

  // 9. AI ANALYZER CLASS
  function AIAnalyzer(options) {
    this.customEvaluator = (options && options.customEvaluator) ? options.customEvaluator : null;
  }

  AIAnalyzer.prototype.generateMoves = function (gameState) {
    var p = normalizePlayerState(gameState.mySide || gameState.player || gameState.ourCards || gameState);
    var o = sanitizeOpponentState(gameState.opponent || gameState.opponentVisible || gameState.opponentCards);
    return generateLegalMoves(p, o);
  };

  AIAnalyzer.prototype.evaluateMove = function (move, gameState) {
    var p = normalizePlayerState(gameState.mySide || gameState.player || gameState.ourCards || gameState);
    var o = sanitizeOpponentState(gameState.opponent || gameState.opponentVisible || gameState.opponentCards);
    var t = analyzeThreats(p, o);
    if (typeof this.customEvaluator === 'function') {
      return this.customEvaluator(move, p, o, t);
    }
    return evaluateMove(move, p, o, t);
  };

  AIAnalyzer.prototype.recommendMove = function (gameState) {
    return this.analyzeBattle(gameState);
  };

  AIAnalyzer.prototype.analyzeBattle = function (gameState) {
    // 1. Sanitize sides (NO-CHEATING)
    var playerState = normalizePlayerState(
      gameState.mySide || gameState.player || gameState.ourCards || gameState.our_cards || gameState
    );
    var opponentState = sanitizeOpponentState(
      gameState.opponent || gameState.opponentVisible || gameState.opponent_visible || gameState.opponentCards || gameState.opponent_cards
    );

    // 2. Threats
    var threatContext = analyzeThreats(playerState, opponentState);

    // 3. Legal Moves
    var legalMoves = generateLegalMoves(playerState, opponentState);

    // 4. Evaluate
    var evaluated = [];
    for (var i = 0; i < legalMoves.length; i++) {
      evaluated.push(evaluateMove(legalMoves[i], playerState, opponentState, threatContext));
    }
    evaluated.sort(function (a, b) { return b.score - a.score; });

    var topMove = evaluated[0] || {
      shortName: 'Pass Turn',
      score: 10,
      reason: ['No legal actions available']
    };
    var secondMove = evaluated.length > 1 ? evaluated[1] : null;

    // Confidence
    var scoreMargin = secondMove ? Math.max(0, topMove.score - secondMove.score) : 15;
    var confidence = Math.max(50, Math.min(99, Math.round((topMove.score * 0.75) + Math.min(20, scoreMargin * 1.2))));

    // Best Pokémon & Strategy
    var bestPkmn = determineBestPokemon(playerState, opponentState);

    var alternatives = evaluated.slice(1, 4).map(function (m) {
      return { move: m.shortName || m.displayName, score: m.score };
    });

    var strategy = [
      topMove.type === ActionType.ATTACK ? "Knock out the Active Pokémon" : "Advance board position",
      bestPkmn.benchSetup !== 'None' ? "Prepare " + bestPkmn.benchSetup + " on the Bench" : "Build bench reserves",
      "Save the Trainer card for the next turn"
    ];

    var reasons = topMove.reason || [];
    var bullets = reasons.map(function (r) { return "• " + r; }).join('\n');
    var explanationText = "🤖 Recommended Move\n\n" + (topMove.shortName || topMove.displayName) + "\n\nWhy?\n\n" + bullets + "\n\nConfidence: " + confidence + "%";

    return {
      recommendedMove: topMove.shortName || topMove.displayName,
      score: topMove.score,
      confidence: confidence,
      reason: reasons,
      alternatives: alternatives,
      strategy: strategy,
      threats: threatContext.threats,
      bestPokemon: bestPkmn,
      winningPath: {
        current: (playerState && playerState.active ? playerState.active.name : 'Active') + " has enough Energy",
        bestMove: topMove.shortName || topMove.displayName,
        nextAction: "Prepare " + bestPkmn.benchSetup + " on Bench",
        futureSetup: "Use " + bestPkmn.benchSetup + " against opponent's next Pokémon",
        goal: "Gain the remaining Prize advantage"
      },
      explanationText: explanationText
    };
  };

  var defaultAnalyzer = new AIAnalyzer();

  function analyzeBattle(gameState) {
    return defaultAnalyzer.analyzeBattle(gameState);
  }

  return {
    analyzeBattle: analyzeBattle,
    AIAnalyzer: AIAnalyzer,
    ActionType: ActionType,
    ThreatLevel: ThreatLevel,
    sanitizeOpponentState: sanitizeOpponentState,
    normalizePlayerState: normalizePlayerState
  };
}));
