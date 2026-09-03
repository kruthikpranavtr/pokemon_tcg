/**
 * types.js
 * Core data structures, action types, constants, and no-cheating sanitizer
 * for the Pokémon TCG AI Battle Analyzer Engine.
 */

// Action Types
const ActionType = Object.freeze({
  ATTACK: 'ATTACK',
  ATTACH_ENERGY: 'ATTACH_ENERGY',
  RETREAT: 'RETREAT',
  SWITCH: 'SWITCH',
  PLAY_TRAINER: 'PLAY_TRAINER',
  EVOLVE: 'EVOLVE',
  USE_ABILITY: 'USE_ABILITY',
  PASS_TURN: 'PASS_TURN'
});

// Threat Severity Levels
const ThreatLevel = Object.freeze({
  HIGH: 'HIGH',
  MEDIUM: 'MEDIUM',
  LOW: 'LOW'
});

// Pokémon Types (Standard)
const PokemonType = Object.freeze({
  GRASS: 'Grass',
  FIRE: 'Fire',
  WATER: 'Water',
  LIGHTNING: 'Lightning',
  PSYCHIC: 'Psychic',
  FIGHTING: 'Fighting',
  DARKNESS: 'Darkness',
  METAL: 'Metal',
  DRAGON: 'Dragon',
  COLORLESS: 'Colorless'
});

// Standard Type Weakness Mapping (Default standard matches)
const TYPE_WEAKNESS_MAP = {
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

// Standard Type Resistance Mapping (Typical -30)
const TYPE_RESISTANCE_MAP = {
  Grass: 'Water',
  Fire: 'Grass',
  Water: 'Fire',
  Lightning: 'Metal',
  Psychic: 'Fighting',
  Fighting: 'Darkness',
  Darkness: 'Psychic',
  Metal: 'Grass'
};

/**
 * NO-CHEATING SANITIZER:
 * Strips all hidden/private opponent fields (hand, deck, prize faces, future draws).
 * Returns only publicly visible information:
 * - Active Pokémon
 * - Visible Bench Pokémon
 * - Known HP, damage, type, weakness, resistance, retreat cost, attached energy, attacks, abilities, status.
 */
function sanitizeOpponentState(rawOpponent) {
  if (!rawOpponent) return null;

  const sanitizePokemon = (p) => {
    if (!p) return null;
    return {
      name: p.name || p.cardName || 'Unknown Pokémon',
      hp: Number(p.hp || p.currentHp || p.current_hp || p.maxHp || p.max_hp || 0),
      maxHp: Number(p.maxHp || p.max_hp || p.hp || 0),
      damage: Number(p.damage || 0),
      currentHp: Math.max(0, Number(p.currentHp ?? p.current_hp ?? ((p.maxHp || p.max_hp || p.hp || 0) - (p.damage || 0)))),
      type: p.type || p.pokemonType || p.types?.[0] || 'Colorless',
      weakness: p.weakness || p.weaknesses?.[0]?.type || TYPE_WEAKNESS_MAP[p.type] || null,
      weaknessMultiplier: Number(p.weaknessMultiplier || p.weaknesses?.[0]?.value?.replace('x', '') || 2),
      resistance: p.resistance || p.resistances?.[0]?.type || null,
      resistanceValue: Number(p.resistanceValue || p.resistances?.[0]?.value || -30),
      retreatCost: Number(p.retreatCost ?? p.retreat_cost ?? p.retreat ?? 1),
      attachedEnergy: Array.isArray(p.attachedEnergy || p.attached_energy)
        ? [...(p.attachedEnergy || p.attached_energy)]
        : typeof (p.attachedEnergy || p.attached_energy) === 'number'
          ? Array(p.attachedEnergy || p.attached_energy).fill('Colorless')
          : [],
      attacks: Array.isArray(p.attacks) ? p.attacks.map(a => ({
        name: a.name || 'Unknown Attack',
        damage: Number(a.damage || a.baseDamage || 0),
        cost: a.cost || a.energyCost || ['Colorless'],
        effect: a.effect || a.description || ''
      })) : [],
      abilities: Array.isArray(p.abilities) ? p.abilities.map(ab => ({
        name: ab.name || 'Unknown Ability',
        effect: ab.effect || ab.description || '',
        type: ab.type || 'Ability'
      })) : [],
      statusConditions: p.statusConditions || p.status || p.condition || [],
      evolutionStage: p.evolutionStage || p.stage || p.subtypes?.[0] || 'Basic',
      prizeValue: Number(p.prizeValue || p.prizes || (p.name?.includes(' VMAX') ? 3 : (p.name?.includes(' ex') || p.name?.includes(' V') ? 2 : 1)))
    };
  };

  return {
    active: sanitizePokemon(rawOpponent.active || rawOpponent.activePokemon || rawOpponent.active_pokemon),
    bench: Array.isArray(rawOpponent.bench || rawOpponent.benchPokemon || rawOpponent.bench_pokemon)
      ? (rawOpponent.bench || rawOpponent.benchPokemon || rawOpponent.bench_pokemon).map(sanitizePokemon).filter(Boolean)
      : [],
    prizesRemaining: Number(rawOpponent.prizesRemaining ?? rawOpponent.prizes_remaining ?? rawOpponent.prizes ?? 6)
  };
}

/**
 * Normalizes the player's side of the game state into a consistent structure.
 */
function normalizePlayerState(rawPlayer) {
  if (!rawPlayer) return null;

  const normalizePokemon = (p) => {
    if (!p) return null;
    const maxHp = Number(p.maxHp || p.max_hp || p.hp || 100);
    const damage = Number(p.damage || 0);
    const currentHp = Math.max(0, Number(p.currentHp ?? p.current_hp ?? (maxHp - damage)));

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
        ? [...(p.attachedEnergy || p.attached_energy)]
        : typeof (p.attachedEnergy || p.attached_energy) === 'number'
          ? Array(p.attachedEnergy || p.attached_energy).fill('Colorless')
          : [],
      attacks: Array.isArray(p.attacks) ? p.attacks.map(a => ({
        name: a.name || 'Attack',
        damage: Number(a.damage || a.baseDamage || 0),
        cost: a.cost || a.energyCost || ['Colorless'],
        effect: a.effect || a.description || ''
      })) : [],
      abilities: Array.isArray(p.abilities) ? p.abilities.map(ab => ({
        name: ab.name || 'Ability',
        effect: ab.effect || ab.description || '',
        used: Boolean(ab.used || ab.usedThisTurn)
      })) : [],
      statusConditions: Array.isArray(p.statusConditions || p.status)
        ? (p.statusConditions || p.status)
        : (p.statusConditions || p.status ? [p.statusConditions || p.status] : []),
      evolutionStage: p.evolutionStage || p.stage || p.subtypes?.[0] || 'Basic',
      prizeValue: Number(p.prizeValue || p.prizes || (p.name?.includes(' VMAX') ? 3 : (p.name?.includes(' ex') || p.name?.includes(' V') ? 2 : 1)))
    };
  };

  return {
    active: normalizePokemon(rawPlayer.active || rawPlayer.activePokemon || rawPlayer.active_pokemon),
    bench: Array.isArray(rawPlayer.bench || rawPlayer.benchPokemon || rawPlayer.bench_pokemon)
      ? (rawPlayer.bench || rawPlayer.benchPokemon || rawPlayer.bench_pokemon).map(normalizePokemon).filter(Boolean)
      : [],
    hand: Array.isArray(rawPlayer.hand || rawPlayer.handCards || rawPlayer.hand_cards)
      ? [...(rawPlayer.hand || rawPlayer.handCards || rawPlayer.hand_cards)]
      : [],
    availableTrainers: Array.isArray(rawPlayer.availableTrainers || rawPlayer.trainers)
      ? [...(rawPlayer.availableTrainers || rawPlayer.trainers)]
      : [],
    availableEnergy: Array.isArray(rawPlayer.availableEnergy || rawPlayer.energyCards || rawPlayer.energy_cards)
      ? [...(rawPlayer.availableEnergy || rawPlayer.energyCards || rawPlayer.energy_cards)]
      : [],
    prizesRemaining: Number(rawPlayer.prizesRemaining ?? rawPlayer.prizes_remaining ?? rawPlayer.prizes ?? 6),
    energyAttachedThisTurn: Boolean(rawPlayer.energyAttachedThisTurn ?? rawPlayer.energy_attached_this_turn),
    supporterPlayedThisTurn: Boolean(rawPlayer.supporterPlayedThisTurn ?? rawPlayer.supporter_played_this_turn),
    retreatedThisTurn: Boolean(rawPlayer.retreatedThisTurn ?? rawPlayer.retreated_this_turn),
    stadiumPlayedThisTurn: Boolean(rawPlayer.stadiumPlayedThisTurn ?? rawPlayer.stadium_played_this_turn),
    isFirstTurnGoingFirst: Boolean(rawPlayer.isFirstTurnGoingFirst ?? rawPlayer.turn_1_going_first)
  };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    ActionType,
    ThreatLevel,
    PokemonType,
    TYPE_WEAKNESS_MAP,
    TYPE_RESISTANCE_MAP,
    sanitizeOpponentState,
    normalizePlayerState
  };
}
