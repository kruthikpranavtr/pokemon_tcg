"""
Canonical 9-Type Pokémon Energy System Configuration and Cost Engine
Source of truth for Energy types, card definitions, symbol mappings, and attack validation.
"""
from typing import Dict, List, Any, Union, Tuple, Optional
from collections import Counter
import re

# The 9 canonical Basic Energy types in Pokémon TCG
ENERGY_TYPES = [
    "Grass",
    "Fire",
    "Water",
    "Lightning",
    "Fighting",
    "Psychic",
    "Darkness",
    "Metal",
    "Dragon"
]

# Attack cost symbol mapping from CSV / dataset encodings to canonical names
ENERGY_SYMBOL_MAP = {
    "G": "Grass",
    "R": "Fire",
    "W": "Water",
    "L": "Lightning",
    "F": "Fighting",
    "P": "Psychic",
    "D": "Darkness",
    "M": "Metal",
    "N": "Dragon",
    "C": "Colorless",
    "●": "Colorless",
    "{G}": "Grass",
    "{R}": "Fire",
    "{W}": "Water",
    "{L}": "Lightning",
    "{F}": "Fighting",
    "{P}": "Psychic",
    "{D}": "Darkness",
    "{M}": "Metal",
    "{N}": "Dragon",
    "{C}": "Colorless"
}

# Visual emoji mapping for each energy type
ENERGY_EMOJI_MAP = {
    "Grass": "🌿",
    "Fire": "🔥",
    "Water": "💧",
    "Lightning": "⚡",
    "Fighting": "🥊",
    "Psychic": "🔮",
    "Darkness": "🌑",
    "Metal": "⚙️",
    "Dragon": "🐉",
    "Colorless": "⚪"
}

# The 9 canonical Basic Energy card definitions with stable card_ids
CANONICAL_BASIC_ENERGIES = {
    "Grass": {
        "card_id": "energy_grass_basic",
        "card_name": "Basic Grass Energy",
        "name": "Basic Grass Energy",
        "card_type": "energy",
        "supertype": "Energy",
        "pokemon_type": "Grass",
        "energy_type": "Grass",
        "stage": None,
        "rarity": "Common",
        "image": "/static/card_images/energy_grass_basic.png",
        "effect": "Provides 1 Grass Energy."
    },
    "Fire": {
        "card_id": "energy_fire_basic",
        "card_name": "Basic Fire Energy",
        "name": "Basic Fire Energy",
        "card_type": "energy",
        "supertype": "Energy",
        "pokemon_type": "Fire",
        "energy_type": "Fire",
        "stage": None,
        "rarity": "Common",
        "image": "/static/card_images/energy_fire_basic.png",
        "effect": "Provides 1 Fire Energy."
    },
    "Water": {
        "card_id": "energy_water_basic",
        "card_name": "Basic Water Energy",
        "name": "Basic Water Energy",
        "card_type": "energy",
        "supertype": "Energy",
        "pokemon_type": "Water",
        "energy_type": "Water",
        "stage": None,
        "rarity": "Common",
        "image": "/static/card_images/energy_water_basic.png",
        "effect": "Provides 1 Water Energy."
    },
    "Lightning": {
        "card_id": "energy_lightning_basic",
        "card_name": "Basic Lightning Energy",
        "name": "Basic Lightning Energy",
        "card_type": "energy",
        "supertype": "Energy",
        "pokemon_type": "Lightning",
        "energy_type": "Lightning",
        "stage": None,
        "rarity": "Common",
        "image": "/static/card_images/energy_lightning_basic.png",
        "effect": "Provides 1 Lightning Energy."
    },
    "Fighting": {
        "card_id": "energy_fighting_basic",
        "card_name": "Basic Fighting Energy",
        "name": "Basic Fighting Energy",
        "card_type": "energy",
        "supertype": "Energy",
        "pokemon_type": "Fighting",
        "energy_type": "Fighting",
        "stage": None,
        "rarity": "Common",
        "image": "/static/card_images/energy_fighting_basic.png",
        "effect": "Provides 1 Fighting Energy."
    },
    "Psychic": {
        "card_id": "energy_psychic_basic",
        "card_name": "Basic Psychic Energy",
        "name": "Basic Psychic Energy",
        "card_type": "energy",
        "supertype": "Energy",
        "pokemon_type": "Psychic",
        "energy_type": "Psychic",
        "stage": None,
        "rarity": "Common",
        "image": "/static/card_images/energy_psychic_basic.png",
        "effect": "Provides 1 Psychic Energy."
    },
    "Darkness": {
        "card_id": "energy_darkness_basic",
        "card_name": "Basic Darkness Energy",
        "name": "Basic Darkness Energy",
        "card_type": "energy",
        "supertype": "Energy",
        "pokemon_type": "Darkness",
        "energy_type": "Darkness",
        "stage": None,
        "rarity": "Common",
        "image": "/static/card_images/energy_darkness_basic.png",
        "effect": "Provides 1 Darkness Energy."
    },
    "Metal": {
        "card_id": "energy_metal_basic",
        "card_name": "Basic Metal Energy",
        "name": "Basic Metal Energy",
        "card_type": "energy",
        "supertype": "Energy",
        "pokemon_type": "Metal",
        "energy_type": "Metal",
        "stage": None,
        "rarity": "Common",
        "image": "/static/card_images/energy_metal_basic.png",
        "effect": "Provides 1 Metal Energy."
    },
    "Dragon": {
        "card_id": "energy_dragon_basic",
        "card_name": "Basic Dragon Energy",
        "name": "Basic Dragon Energy",
        "card_type": "energy",
        "supertype": "Energy",
        "pokemon_type": "Dragon",
        "energy_type": "Dragon",
        "stage": None,
        "rarity": "Common",
        "image": "/static/card_images/energy_dragon_basic.png",
        "effect": "Provides 1 Dragon Energy."
    }
}


def normalize_energy_type(raw_type: Any) -> str:
    """Normalizes any string or raw identifier to a canonical Energy type."""
    if not raw_type:
        return "Colorless"
    
    if isinstance(raw_type, dict):
        raw_type = raw_type.get("energy_type") or raw_type.get("pokemon_type") or raw_type.get("type") or raw_type.get("name") or "Colorless"

    s = str(raw_type).strip()
    s_clean = s.replace("{", "").replace("}", "").strip()
    
    # Direct symbol match
    if s in ENERGY_SYMBOL_MAP:
        return ENERGY_SYMBOL_MAP[s]
    if s_clean in ENERGY_SYMBOL_MAP:
        return ENERGY_SYMBOL_MAP[s_clean]

    # Substring matching
    s_lower = s.lower()
    for etype in ENERGY_TYPES:
        if etype.lower() in s_lower:
            return etype
    if "dark" in s_lower:
        return "Darkness"
    if "electric" in s_lower or "lightning" in s_lower:
        return "Lightning"
    if "colorless" in s_lower or "normal" in s_lower or "●" in s:
        return "Colorless"

    return "Colorless"


def parse_attack_cost(cost: Union[List[str], str, None]) -> List[str]:
    """
    Parses any raw attack cost (list of strings, encoded string like '{R}{R}●', etc.)
    into a canonical list of energy types (e.g. ['Fire', 'Fire', 'Colorless']).
    """
    if not cost:
        return []

    if isinstance(cost, list):
        parsed = []
        for item in cost:
            if not item:
                continue
            item_str = str(item).strip()
            if "{" in item_str or "●" in item_str:
                parsed.extend(parse_attack_cost_string(item_str))
            else:
                parsed.append(normalize_energy_type(item_str))
        return parsed

    if isinstance(cost, str):
        return parse_attack_cost_string(cost)

    return ["Colorless"]


def parse_attack_cost_string(cost_str: str) -> List[str]:
    """Parses a compact cost string such as '{R}{R}●' or 'Fire Fire Colorless'."""
    cost_str = cost_str.strip()
    if not cost_str:
        return []

    tokens = []
    pattern = re.compile(r"\{[A-Za-z0-9]+\}|●|[A-Za-z]+")
    matches = pattern.findall(cost_str)
    if matches:
        for m in matches:
            t = normalize_energy_type(m)
            tokens.append(t)
    else:
        for ch in cost_str:
            tokens.append(normalize_energy_type(ch))
    return tokens


def format_cost_emojis(cost_list: List[str]) -> str:
    """Formats a list of energy types into visual emojis (e.g. '🔥 🔥 ⚪')."""
    if not cost_list:
        return "⚪ (Free)"
    return " ".join(ENERGY_EMOJI_MAP.get(normalize_energy_type(c), "⚪") for c in cost_list)


def create_energy_card_dict(energy_type: str, card_id: Optional[str] = None) -> Dict[str, Any]:
    """Creates a full authoritative Energy card dictionary with stable card_id."""
    etype = normalize_energy_type(energy_type)
    if etype not in CANONICAL_BASIC_ENERGIES:
        etype = "Fire"
    base = dict(CANONICAL_BASIC_ENERGIES[etype])
    if card_id:
        base["card_id"] = str(card_id)
    return base


def validate_attack_cost(
    attached_energies: List[Union[str, Dict[str, Any]]],
    required_costs: Union[List[str], str, None]
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Authoritative attack energy validation.
    1. Extracts energy types from attached cards (supports strings and dicts).
    2. Satisfies specific elemental requirements first (Fire, Water, Grass, etc.).
    3. Any remaining energy of ANY type pays for Colorless requirements.
    4. Returns (can_attack, descriptive_reason, detailed_breakdown).
    """
    norm_required = parse_attack_cost(required_costs)
    if not norm_required:
        return True, "Ready", {
            "can_attack": True,
            "cost_emojis": "⚪",
            "required": {},
            "attached": {},
            "missing": {}
        }

    clean_attached = []
    for e in (attached_energies or []):
        if not e:
            continue
        clean_attached.append(normalize_energy_type(e))

    attached_counts = Counter(clean_attached)
    req_counts = Counter(norm_required)
    cost_emojis = format_cost_emojis(norm_required)

    colorless_req = req_counts.pop("Colorless", 0)
    missing_breakdown = {}

    # 1. Satisfy specific elemental requirements first
    for etype, req_amt in req_counts.items():
        have_amt = attached_counts.get(etype, 0)
        if have_amt < req_amt:
            deficit = req_amt - have_amt
            missing_breakdown[etype] = deficit
            attached_counts[etype] = 0
        else:
            attached_counts[etype] -= req_amt

    # If any specific elemental requirement was unmet, attack is illegal
    if missing_breakdown:
        deficit_strs = [
            f"Need {cnt} more {etype} Energy"
            for etype, cnt in missing_breakdown.items()
        ]
        reason = f"Requires: {cost_emojis} • {', '.join(deficit_strs)}"
        return False, reason, {
            "can_attack": False,
            "cost_emojis": cost_emojis,
            "required": dict(Counter(norm_required)),
            "attached": dict(Counter(clean_attached)),
            "missing": missing_breakdown
        }

    # 2. Satisfy Colorless requirements using any remaining attached energy
    total_leftover = sum(attached_counts.values())
    if total_leftover < colorless_req:
        deficit = colorless_req - total_leftover
        missing_breakdown["Colorless"] = deficit
        reason = f"Requires: {cost_emojis} • Need {deficit} more Energy (any type) for Colorless cost"
        return False, reason, {
            "can_attack": False,
            "cost_emojis": cost_emojis,
            "required": dict(Counter(norm_required)),
            "attached": dict(Counter(clean_attached)),
            "missing": missing_breakdown
        }

    return True, "Ready to attack!", {
        "can_attack": True,
        "cost_emojis": cost_emojis,
        "required": dict(Counter(norm_required)),
        "attached": dict(Counter(clean_attached)),
        "missing": {}
    }


# ==============================================================================
# 5. POKÉMON TYPE ADVANTAGE & MATCHUP DAMAGE CALCULATION
# ==============================================================================

# Canonical Type Advantages: Attacker Type -> types it deals +50% damage against
TYPE_ADVANTAGES: Dict[str, Set[str]] = {
    "Water": {"Fire", "Fighting"},
    "Fire": {"Grass", "Metal"},
    "Grass": {"Water", "Fighting"},
    "Lightning": {"Water"},
    "Fighting": {"Darkness", "Metal", "Colorless"},
    "Psychic": {"Fighting"},
    "Darkness": {"Psychic"},
    "Metal": {"Grass", "Psychic"},
    "Dragon": {"Dragon"},
    "Colorless": set(),
}

# Canonical Type Disadvantages: Attacker Type -> types it deals 50% less damage against
TYPE_DISADVANTAGES: Dict[str, Set[str]] = {
    "Water": {"Grass", "Lightning"},
    "Fire": {"Water"},
    "Grass": {"Fire"},
    "Lightning": {"Fighting"},
    "Fighting": {"Psychic", "Grass"},
    "Psychic": {"Darkness", "Metal"},
    "Darkness": {"Fighting", "Grass"},
    "Metal": {"Fire", "Fighting"},
    "Dragon": set(),
    "Colorless": {"Fighting"},
}


def get_type_effectiveness(
    attacker_type: str,
    defender_type: str,
    defender_weakness: str = "",
    defender_resistance: str = "",
    attacker_weakness: str = ""
) -> Tuple[float, str, str]:
    """
    Evaluates type effectiveness multiplier (+50% / -50% / Normal) and descriptive reason.
    - Advantage: +50% damage (1.5x)
    - Disadvantage: 50% less damage (0.5x)
    - Neutral: normal damage (1.0x)
    Attacks are never blocked due to type.
    """
    atk_norm = normalize_energy_type(attacker_type)
    def_norm = normalize_energy_type(defender_type)
    def_weak = (defender_weakness or "").strip().lower()
    def_res = (defender_resistance or "").strip().lower()
    atk_weak = (attacker_weakness or "").strip().lower()

    # 1. Check defender explicit weakness (guaranteed advantage)
    if def_weak and atk_norm.lower() in def_weak:
        return 1.5, "ADVANTAGE", f"+50% Type Advantage (Opponent weak to {atk_norm})"

    # 2. Check defender explicit resistance or attacker weakness (guaranteed disadvantage)
    if def_res and atk_norm.lower() in def_res:
        return 0.5, "DISADVANTAGE", f"-50% Type Disadvantage (Opponent resists {atk_norm})"
    if atk_weak and def_norm.lower() in atk_weak:
        return 0.5, "DISADVANTAGE", f"-50% Type Disadvantage (Weak to {def_norm})"

    # 3. Check canonical type advantage table
    adv_types = TYPE_ADVANTAGES.get(atk_norm, set())
    if def_norm in adv_types:
        return 1.5, "ADVANTAGE", f"+50% Type Advantage ({atk_norm} vs {def_norm})"

    # 4. Check canonical type disadvantage table
    dis_types = TYPE_DISADVANTAGES.get(atk_norm, set())
    if def_norm in dis_types:
        return 0.5, "DISADVANTAGE", f"-50% Type Disadvantage ({atk_norm} vs {def_norm})"

    # 5. Default: Neutral (normal damage)
    return 1.0, "NEUTRAL", f"Neutral Type Matchup ({atk_norm} vs {def_norm})"


def calculate_matchup_damage(
    base_damage: int,
    attacker_type: str,
    defender_type: str,
    defender_weakness: str = "",
    defender_resistance: str = "",
    attacker_weakness: str = ""
) -> Tuple[int, float, str, str]:
    """
    Calculates final damage applying the +50% / -50% / Normal type advantage rule.
    Guarantees attacks are never reduced to 0 or blocked due to type (min 1 DMG if base > 0).
    Returns (final_damage, multiplier, label, reason).
    """
    if base_damage <= 0:
        return 0, 1.0, "NEUTRAL", "Non-damaging attack"

    mult, label, reason = get_type_effectiveness(
        attacker_type, defender_type,
        defender_weakness, defender_resistance, attacker_weakness
    )

    final_dmg = int(round(base_damage * mult))
    # Guarantee attack is never blocked or reduced to 0 (minimum 1 DMG)
    final_dmg = max(1, final_dmg)

    return final_dmg, mult, label, reason

