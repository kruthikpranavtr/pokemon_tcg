"""
Card Data Ingestion and Validation Engine for Pokémon TCG.
Primary Source of Truth: Csvfiles/EN_Card_Data.csv
Preserves exact card names, dual attacks, abilities, types, HP, and stages.
"""
import os
import csv
import json
import re
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKSPACE_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
CSV_PATH = os.path.join(WORKSPACE_ROOT, "Csvfiles", "EN_Card_Data.csv")
CARDS_JSON_PATH = os.path.join(BASE_DIR, "data", "cards_dataset.json")

ENERGY_SYMBOL_MAP = {
    "{G}": "Grass",
    "{R}": "Fire",
    "{W}": "Water",
    "{L}": "Lightning",
    "{P}": "Psychic",
    "{F}": "Fighting",
    "{D}": "Darkness",
    "{M}": "Metal",
    "{C}": "Colorless",
    "{N}": "Dragon",
    "●": "Colorless",
    "竜": "Dragon"
}

TYPE_NAME_MAP = {
    "{G}": "Grass",
    "{R}": "Fire",
    "{W}": "Water",
    "{L}": "Lightning",
    "{P}": "Psychic",
    "{F}": "Fighting",
    "{D}": "Darkness",
    "{M}": "Metal",
    "{C}": "Colorless",
    "{N}": "Dragon",
    "竜": "Dragon",
    "{A}": "Colorless",
    "{A}{A}": "Colorless",
    "{Team Rocket}{Team Rocket}": "Darkness",
    "{C}{C}{C}": "Colorless"
}

POKEDEX_MAP = {
    'bulbasaur': 1, 'ivysaur': 2, 'venusaur': 3, 'charmander': 4, 'charmeleon': 5, 'charizard': 6,
    'squirtle': 7, 'wartortle': 8, 'blastoise': 9, 'caterpie': 10, 'metapod': 11, 'butterfree': 12,
    'weedle': 13, 'kakuna': 14, 'beedrill': 15, 'pidgey': 16, 'pidgeotto': 17, 'pidgeot': 18,
    'rattata': 19, 'raticate': 20, 'spearow': 21, 'fearow': 22, 'ekans': 23, 'arbok': 24,
    'pikachu': 25, 'raichu': 26, 'sandshrew': 27, 'sandslash': 28, 'nidoran': 29, 'nidorina': 30,
    'nidoqueen': 31, 'nidorino': 33, 'nidoking': 34, 'clefairy': 35, 'clefable': 36, 'vulpix': 37,
    'ninetales': 38, 'jigglypuff': 39, 'wigglytuff': 40, 'zubat': 41, 'golbat': 42, 'oddish': 43,
    'gloom': 44, 'vileplume': 45, 'paras': 46, 'parasect': 47, 'venonat': 48, 'venomoth': 49,
    'diglett': 50, 'dugtrio': 51, 'meowth': 52, 'persian': 53, 'psyduck': 54, 'golduck': 55,
    'mankey': 56, 'primeape': 57, 'growlithe': 58, 'arcanine': 59, 'poliwag': 60, 'poliwhirl': 61,
    'poliwrath': 62, 'abra': 63, 'kadabra': 64, 'alakazam': 65, 'machop': 66, 'machoke': 67,
    'machamp': 68, 'bellsprout': 69, 'weepinbell': 70, 'victreebel': 71, 'tentacool': 72,
    'tentacruel': 73, 'geodude': 74, 'graveler': 75, 'golem': 76, 'ponyta': 77, 'rapidash': 78,
    'slowpoke': 79, 'slowbro': 80, 'magnemite': 81, 'magneton': 82, "farfetch'd": 83, 'doduo': 84,
    'dodrio': 85, 'seel': 86, 'dewgong': 87, 'grimer': 88, 'muk': 89, 'shellder': 90, 'cloyster': 91,
    'gastly': 92, 'haunter': 93, 'gengar': 94, 'onix': 95, 'drowzee': 96, 'hypno': 97, 'krabby': 98,
    'kingler': 99, 'voltorb': 100, 'electrode': 101, 'exeggcute': 102, 'exeggutor': 103, 'cubone': 104,
    'marowak': 105, 'hitmonlee': 106, 'hitmonchan': 107, 'lickitung': 108, 'koffing': 109, 'weezing': 110,
    'rhyhorn': 111, 'rhydon': 112, 'chansey': 113, 'tangela': 114, 'kangaskhan': 115, 'horsea': 116,
    'seadra': 117, 'goldeen': 118, 'seaking': 119, 'staryu': 120, 'starmie': 121, 'mr. mime': 122,
    'scyther': 123, 'jynx': 124, 'electabuzz': 125, 'magmar': 126, 'pinsir': 127, 'tauros': 128,
    'magikarp': 129, 'gyarados': 130, 'lapras': 131, 'ditto': 132, 'eevee': 133, 'vaporeon': 134,
    'jolteon': 135, 'flareon': 136, 'porygon': 137, 'omanyte': 138, 'omastar': 139, 'kabuto': 140,
    'kabutops': 141, 'aerodactyl': 142, 'snorlax': 143, 'articuno': 144, 'zapdos': 145, 'moltres': 146,
    'dratini': 147, 'dragonair': 148, 'dragonite': 149, 'mewtwo': 150, 'mew': 151, 'miraidon': 1008,
    'koraidon': 1007, 'scraggy': 559, 'scrafty': 560
}


def parse_cost_list(cost_str: str) -> List[str]:
    if not cost_str or cost_str == 'n/a' or cost_str.strip().lower() == 'no cost':
        return []
    tokens = re.findall(r'\{[A-Za-z0-9\s]+\}|●|\S', cost_str.strip())
    costs = []
    for t in tokens:
        costs.append(ENERGY_SYMBOL_MAP.get(t, "Colorless"))
    return costs


def parse_pokemon_type(raw_type: str) -> str:
    cleaned = raw_type.strip()
    return TYPE_NAME_MAP.get(cleaned, cleaned.replace("{", "").replace("}", "") or "Colorless")


def parse_base_damage(dmg_str: str) -> int:
    if not dmg_str or dmg_str == 'n/a':
        return 0
    clean = re.sub(r'[^\d]', '', dmg_str)
    return int(clean) if clean else 0


def assign_rarity(card: Dict[str, Any]) -> str:
    stype = card.get("card_type", "").lower()
    name = card.get("name", "").lower()
    rule = card.get("rule", "").lower()
    stage = card.get("stage")

    if stype == "energy":
        return "Uncommon" if "special" in name or card.get("is_special_energy") else "Common"

    if stype == "trainer":
        subtype = (card.get("subtypes") or ["Item"])[0].lower()
        if "ace spec" in rule or "ace spec" in name:
            return "Rare"
        if subtype in ["supporter", "stadium"]:
            return "Uncommon"
        return "Common"

    # Pokémon
    if "mega" in rule or "mega" in name:
        return "Special"
    if "ex" in rule or "ex" in name:
        return "Ultra Rare"
    if stage == "Stage 2":
        return "Rare"
    if stage == "Stage 1":
        return "Uncommon"
    hp = card.get("hp") or 0
    if hp >= 110:
        return "Uncommon"
    return "Common"


def get_image_url(name: str, card_id: str, card_type: str, subtype: str = "") -> str:
    # 1. Exact authentic image mapped by card_id from extracted asset collection
    img_filename = f"{card_id}.png"
    img_disk_path = os.path.join(BASE_DIR, "static", "card_images", img_filename)
    if os.path.exists(img_disk_path):
        return f"/static/card_images/{img_filename}"

    # 2. Designated placeholder per category (Never display wrong Pokémon)
    if card_type == "energy":
        return "/static/card_images/placeholder_energy.svg"
    if card_type == "trainer":
        st_lower = subtype.lower()
        if "supporter" in st_lower:
            return "/static/card_images/placeholder_supporter.svg"
        if "tool" in st_lower:
            return "/static/card_images/placeholder_tool.svg"
        if "stadium" in st_lower:
            return "/static/card_images/placeholder_stadium.svg"
        return "/static/card_images/placeholder_item.svg"

    return "/static/card_images/placeholder_pokemon.svg"


def load_and_validate_cards_dataset(csv_file_path: Optional[str] = None) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    path = csv_file_path or CSV_PATH
    if not os.path.exists(path):
        alt_path = os.path.join(BASE_DIR, "Csvfiles", "EN_Card_Data.csv")
        if os.path.exists(alt_path):
            path = alt_path
        else:
            raise FileNotFoundError(f"Could not find EN_Card_Data.csv at {path} or {alt_path}")

    cards_by_id = defaultdict(list)
    with open(path, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = (row.get("Card ID") or row.get("\ufeffCard ID") or "").strip()
            if cid:
                cards_by_id[cid].append(row)

    processed_cards = {}
    validation_issues = []
    pokemon_count = 0
    energy_count = 0
    trainer_count = 0

    for cid, rows in cards_by_id.items():
        r0 = rows[0]
        name = r0.get("Card Name", "").strip()
        expansion = r0.get("Expansion", "").strip()
        coll_no = r0.get("Collection No.", "").strip()
        st = (r0.get("Stage (Pokémon)/Type (Energy and Trainer)") or r0.get("Stage (Pokmon)/Type (Energy and Trainer)") or "").strip()
        rule = r0.get("Rule", "").strip()
        category = r0.get("Category", "").strip()
        prev_stage = r0.get("Previous stage", "").strip()
        if prev_stage == "n/a" or not prev_stage:
            prev_stage = None
        hp_raw = r0.get("HP", "").strip()
        type_raw = r0.get("Type", "").strip()
        weakness = r0.get("Weakness", "").strip()
        if weakness == "n/a":
            weakness = ""
        resistance = r0.get("Resistance (Type)", "").strip()
        if resistance == "n/a":
            resistance = ""
        retreat = r0.get("Retreat", "").strip()
        retreat_cost = int(retreat) if retreat and retreat.isdigit() else 0

        # Determine card_type and stage
        if any(k in st for k in ["Item", "Supporter", "Stadium", "Pokémon Tool", "Tool"]):
            card_type = "trainer"
            stage = None
            trainer_count += 1
            trainer_subtype = "Item"
            if "Supporter" in st:
                trainer_subtype = "Supporter"
            elif "Stadium" in st:
                trainer_subtype = "Stadium"
            elif "Tool" in st:
                trainer_subtype = "Tool"
            subtypes = [trainer_subtype]
            if "ACE SPEC" in rule or "ACE SPEC" in name:
                subtypes.append("ACE SPEC")
            p_type = trainer_subtype
            hp = None
        elif "Energy" in st:
            card_type = "energy"
            stage = None
            energy_count += 1
            is_special = "Special" in st or "Special" in name
            subtypes = ["Special Energy"] if is_special else ["Basic Energy"]
            p_type = parse_pokemon_type(type_raw)
            hp = None
        else:
            card_type = "pokemon"
            pokemon_count += 1
            if "Stage 2" in st:
                stage = "Stage 2"
            elif "Stage 1" in st:
                stage = "Stage 1"
            else:
                stage = "Basic"
            subtypes = [stage]
            if "ex" in rule.lower() or "ex" in name.lower():
                subtypes.append("ex")
            if "mega" in rule.lower() or "mega" in name.lower():
                subtypes.append("Mega")
            p_type = parse_pokemon_type(type_raw)
            try:
                hp = int(hp_raw) if hp_raw and hp_raw != 'n/a' else 70
            except ValueError:
                hp = 70

        # Parse moves, abilities, attacks
        attacks = []
        abilities = []
        for r in rows:
            move_name = r.get("Move Name", "").strip()
            eff = r.get("Effect Explanation", "").strip()
            dmg_raw = r.get("Damage", "").strip()
            cost_raw = r.get("Cost", "").strip()

            if not move_name:
                continue

            if move_name.startswith("[Ability]") or move_name.startswith("[Tera]"):
                clean_abil_name = move_name.replace("[Ability]", "").replace("[Tera]", "").strip()
                abilities.append({
                    "name": clean_abil_name or move_name,
                    "text": eff
                })
            else:
                cost_list = parse_cost_list(cost_raw)
                base_dmg = parse_base_damage(dmg_raw)
                attacks.append({
                    "name": move_name,
                    "damage": dmg_raw if dmg_raw and dmg_raw != 'n/a' else "",
                    "base_damage": base_dmg,
                    "cost": cost_list,
                    "cost_raw": cost_raw if cost_raw != 'n/a' else "",
                    "text": eff
                })

        # Attack 1 and Attack 2 attributes
        atk_1_name = attacks[0]["name"] if len(attacks) > 0 else None
        atk_1_dmg = attacks[0]["damage"] if len(attacks) > 0 else None
        atk_1_energy = attacks[0]["cost"] if len(attacks) > 0 else []

        atk_2_name = attacks[1]["name"] if len(attacks) > 1 else None
        atk_2_dmg = attacks[1]["damage"] if len(attacks) > 1 else None
        atk_2_energy = attacks[1]["cost"] if len(attacks) > 1 else []

        ability_str = None
        if abilities:
            ability_str = f"{abilities[0]['name']}: {abilities[0]['text']}"

        # Card effect for Trainers
        effect_str = ""
        if card_type == "trainer":
            effect_str = rows[0].get("Effect Explanation", "").strip()

        rarity = assign_rarity({
            "card_type": card_type,
            "name": name,
            "rule": rule,
            "stage": stage,
            "hp": hp,
            "subtypes": subtypes,
            "is_special_energy": "Special Energy" in subtypes
        })

        image_url = get_image_url(name, cid, card_type, subtypes[0] if subtypes else "")

        card_obj = {
            "card_id": cid,
            "dataset_id": cid,
            "card_name": name,
            "name": name,
            "card_type": card_type,
            "supertype": "Pokémon" if card_type == "pokemon" else ("Energy" if card_type == "energy" else "Trainer"),
            "pokemon_type": p_type,
            "types": [p_type] if card_type == "pokemon" else [],
            "stage": stage,
            "subtypes": subtypes,
            "evolves_from": prev_stage,
            "hp": hp,
            "attack_1_name": atk_1_name,
            "attack_1_damage": atk_1_dmg,
            "attack_1_energy": atk_1_energy,
            "attack_2_name": atk_2_name,
            "attack_2_damage": atk_2_dmg,
            "attack_2_energy": atk_2_energy,
            "ability": ability_str,
            "attacks": attacks,
            "abilities": abilities,
            "weakness": parse_pokemon_type(weakness) if weakness else "",
            "weaknesses": [{"type": parse_pokemon_type(weakness), "value": "×2"}] if weakness else [],
            "resistance": parse_pokemon_type(resistance) if resistance else "",
            "resistances": [{"type": parse_pokemon_type(resistance), "value": "-30"}] if resistance else [],
            "retreat_cost": retreat_cost,
            "image": image_url,
            "rarity": rarity,
            "rule": rule,
            "category": category,
            "expansion": expansion,
            "collection_no": coll_no,
            "effect": effect_str,
            "effects": [{"text": effect_str, "type": "ITEM_EFFECT"}] if effect_str else []
        }
        card_obj["raw_json"] = json.dumps(card_obj)
        processed_cards[cid] = card_obj

    # Validation Checks
    for cid, card in processed_cards.items():
        if not card.get("name"):
            validation_issues.append(f"Card {cid}: Missing card name")
        if card["card_type"] == "pokemon":
            if not card.get("hp") or card["hp"] <= 0:
                validation_issues.append(f"Pokemon {cid} ({card['name']}): Invalid HP")
            if not card["attacks"] and not card["abilities"]:
                validation_issues.append(f"Pokemon {cid} ({card['name']}): Missing attacks and abilities")

    report = {
        "cards_loaded": len(processed_cards),
        "pokemon": pokemon_count,
        "energy": energy_count,
        "trainer": trainer_count,
        "invalid_cards": len(validation_issues),
        "issues": validation_issues
    }

    print("\n==================== CARD DATA VALIDATION REPORT ====================")
    print(f"Cards loaded: {report['cards_loaded']}")
    print(f"Pokémon: {report['pokemon']}")
    print(f"Energy: {report['energy']}")
    print(f"Trainer: {report['trainer']}")
    print(f"Invalid cards: {report['invalid_cards']}")
    if validation_issues:
        print(f"Validation issues ({len(validation_issues)}):", validation_issues[:5])
    print("====================================================================\n")

    return processed_cards, report


def export_cards_dataset_json(output_path: Optional[str] = None):
    out = output_path or CARDS_JSON_PATH
    cards_map, report = load_and_validate_cards_dataset()
    data = {"cards": list(cards_map.values())}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Exported {len(cards_map)} cards to {out}")
    return cards_map, report


validate_csv_dataset = load_and_validate_cards_dataset

if __name__ == "__main__":
    export_cards_dataset_json()