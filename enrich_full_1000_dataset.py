"""
Enrich cards dataset with all 1000+ Pokemon species and preserve all standard tournament card IDs.
"""
import json
import os
from expand_pokemon_dataset import TRAINER_CARDS, ENERGY_CARDS
from generate_1000_pokemon_dataset import ALL_1025_POKEMON_RAW

def build_enriched_cards():
    cards_map = {}

    # 1. Base Core Tournament Set (with canonical expansion IDs)
    core_cards = [
        # Charizard ex Line
        {
            "card_id": "sv3-125",
            "dataset_id": "125",
            "name": "Charizard ex",
            "supertype": "Pokémon",
            "subtypes": ["Stage 2", "Tera", "ex", "Rule Box"],
            "hp": 330,
            "types": ["Darkness"],
            "attacks": [{
                "name": "Burning Darkness",
                "cost": ["Fire", "Fire"],
                "base_damage": 180,
                "text": "This attack does 30 more damage for each Prize card your opponent has taken."
            }],
            "abilities": [{
                "name": "Infernal Reign",
                "type": "Ability",
                "effect": "When you play this Pokémon from your hand to evolve 1 of your Pokémon during your turn, you may search your deck for up to 3 Basic Fire Energy cards and attach them to your Pokémon in any way you like."
            }],
            "weakness": {"type": "Grass", "value": "x2"},
            "retreat_cost": ["Colorless", "Colorless"],
            "regulation_mark": "G",
            "expansion": "SV3",
            "collection_no": "125"
        },
        {
            "card_id": "sv3-26",
            "dataset_id": "26",
            "name": "Charmander",
            "supertype": "Pokémon",
            "subtypes": ["Basic"],
            "hp": 70,
            "types": ["Fire"],
            "attacks": [{
                "name": "Ember",
                "cost": ["Fire"],
                "base_damage": 30,
                "text": "Discard an Energy attached to this Pokémon."
            }],
            "weakness": {"type": "Water", "value": "x2"},
            "retreat_cost": ["Colorless"],
            "regulation_mark": "G",
            "expansion": "SV3",
            "collection_no": "26"
        },
        {
            "card_id": "sv3-27",
            "dataset_id": "27",
            "name": "Charmeleon",
            "supertype": "Pokémon",
            "subtypes": ["Stage 1"],
            "hp": 90,
            "types": ["Fire"],
            "attacks": [{
                "name": "Flamethrower",
                "cost": ["Fire", "Colorless"],
                "base_damage": 60,
                "text": "Discard an Energy attached to this Pokémon."
            }],
            "weakness": {"type": "Water", "value": "x2"},
            "retreat_cost": ["Colorless", "Colorless"],
            "regulation_mark": "G",
            "expansion": "SV3",
            "collection_no": "27"
        },
        # Pidgeot ex Line
        {
            "card_id": "sv3-164",
            "dataset_id": "164",
            "name": "Pidgeot ex",
            "supertype": "Pokémon",
            "subtypes": ["Stage 2", "ex", "Rule Box"],
            "hp": 280,
            "types": ["Colorless"],
            "attacks": [{
                "name": "Blustery Wind",
                "cost": ["Colorless", "Colorless"],
                "base_damage": 120,
                "text": "You may discard a Stadium in play."
            }],
            "abilities": [{
                "name": "Quick Search",
                "type": "Ability",
                "effect": "Once during your turn, you may search your deck for any 1 card and put it into your hand. Then, shuffle your deck."
            }],
            "weakness": {"type": "Lightning", "value": "x2"},
            "resistance": {"type": "Fighting", "value": "-30"},
            "retreat_cost": [],
            "regulation_mark": "G",
            "expansion": "SV3",
            "collection_no": "164"
        },
        {
            "card_id": "sv3-162",
            "dataset_id": "162",
            "name": "Pidgey",
            "supertype": "Pokémon",
            "subtypes": ["Basic"],
            "hp": 60,
            "types": ["Colorless"],
            "attacks": [{
                "name": "Gust",
                "cost": ["Colorless"],
                "base_damage": 10,
                "text": ""
            }],
            "weakness": {"type": "Lightning", "value": "x2"},
            "retreat_cost": ["Colorless"],
            "regulation_mark": "G",
            "expansion": "SV3",
            "collection_no": "162"
        },
        # Miraidon ex & Lightning Line
        {
            "card_id": "sv1-81",
            "dataset_id": "81",
            "name": "Miraidon ex",
            "supertype": "Pokémon",
            "subtypes": ["Basic", "ex", "Rule Box"],
            "hp": 220,
            "types": ["Lightning"],
            "attacks": [{
                "name": "Photon Blaster",
                "cost": ["Lightning", "Lightning", "Colorless"],
                "base_damage": 220,
                "text": "During your next turn, this Pokémon can't attack."
            }],
            "abilities": [{
                "name": "Tandem Unit",
                "type": "Ability",
                "effect": "Once during your turn, you may search your deck for up to 2 Basic Lightning Pokémon and put them onto your Bench. Then, shuffle your deck."
            }],
            "weakness": {"type": "Fighting", "value": "x2"},
            "retreat_cost": ["Colorless"],
            "regulation_mark": "G",
            "expansion": "SV1",
            "collection_no": "81"
        },
        {
            "card_id": "sv4-70",
            "dataset_id": "70",
            "name": "Iron Hands ex",
            "supertype": "Pokémon",
            "subtypes": ["Basic", "Future", "ex", "Rule Box"],
            "hp": 230,
            "types": ["Lightning"],
            "attacks": [{
                "name": "Amp You Very Much",
                "cost": ["Lightning", "Colorless", "Colorless", "Colorless"],
                "base_damage": 120,
                "text": "If your opponent's Pokémon is Knocked Out by damage from this attack, take 1 more Prize card."
            }],
            "weakness": {"type": "Fighting", "value": "x2"},
            "retreat_cost": ["Colorless", "Colorless", "Colorless", "Colorless"],
            "regulation_mark": "G",
            "expansion": "SV4",
            "collection_no": "70"
        },
        {
            "card_id": "brs-48",
            "dataset_id": "48",
            "name": "Raikou V",
            "supertype": "Pokémon",
            "subtypes": ["Basic", "V", "Rule Box"],
            "hp": 200,
            "types": ["Lightning"],
            "attacks": [{
                "name": "Lightning Rondo",
                "cost": ["Lightning", "Colorless"],
                "base_damage": 20,
                "text": "This attack does 20 more damage for each Benched Pokémon (both yours and your opponent's)."
            }],
            "abilities": [{
                "name": "Fleet Footed",
                "type": "Ability",
                "effect": "Once during your turn, if this Pokémon is in the Active Spot, you may draw a card."
            }],
            "weakness": {"type": "Fighting", "value": "x2"},
            "retreat_cost": ["Colorless"],
            "regulation_mark": "F",
            "expansion": "BRS",
            "collection_no": "48"
        },
        # Gardevoir ex Line
        {
            "card_id": "sv1-86",
            "dataset_id": "86",
            "name": "Gardevoir ex",
            "supertype": "Pokémon",
            "subtypes": ["Stage 2", "ex", "Rule Box"],
            "hp": 310,
            "types": ["Psychic"],
            "attacks": [{
                "name": "Miracle Force",
                "cost": ["Psychic", "Colorless", "Colorless"],
                "base_damage": 190,
                "text": "This Pokémon recovers from all Special Conditions."
            }],
            "abilities": [{
                "name": "Psychic Embrace",
                "type": "Ability",
                "effect": "As often as you like during your turn, you may attach a Basic Psychic Energy card from your discard pile to 1 of your Psychic Pokémon. If you do, put 2 damage counters on that Pokémon."
            }],
            "weakness": {"type": "Darkness", "value": "x2"},
            "resistance": {"type": "Fighting", "value": "-30"},
            "retreat_cost": ["Colorless", "Colorless"],
            "regulation_mark": "G",
            "expansion": "SV1",
            "collection_no": "86"
        },
        {
            "card_id": "sv1-84",
            "dataset_id": "84",
            "name": "Ralts",
            "supertype": "Pokémon",
            "subtypes": ["Basic"],
            "hp": 60,
            "types": ["Psychic"],
            "attacks": [{
                "name": "Memory Skip",
                "cost": ["Psychic"],
                "base_damage": 10,
                "text": "Choose 1 of your opponent's Active Pokémon's attacks. During your opponent's next turn, that Pokémon can't use that attack."
            }],
            "weakness": {"type": "Darkness", "value": "x2"},
            "retreat_cost": ["Colorless"],
            "regulation_mark": "G",
            "expansion": "SV1",
            "collection_no": "84"
        },
        {
            "card_id": "sit-68",
            "dataset_id": "68",
            "name": "Kirlia",
            "supertype": "Pokémon",
            "subtypes": ["Stage 1"],
            "hp": 80,
            "types": ["Psychic"],
            "attacks": [{
                "name": "Slap",
                "cost": ["Psychic", "Colorless"],
                "base_damage": 30,
                "text": ""
            }],
            "abilities": [{
                "name": "Refinement",
                "type": "Ability",
                "effect": "You must discard a card from your hand in order to use this Ability. Once during your turn, you may draw 2 cards."
            }],
            "weakness": {"type": "Darkness", "value": "x2"},
            "retreat_cost": ["Colorless", "Colorless"],
            "regulation_mark": "F",
            "expansion": "SIT",
            "collection_no": "68"
        },
        {
            "card_id": "sv4-86",
            "dataset_id": "86",
            "name": "Scream Tail",
            "supertype": "Pokémon",
            "subtypes": ["Basic", "Ancient"],
            "hp": 90,
            "types": ["Psychic"],
            "attacks": [{
                "name": "Roaring Shriek",
                "cost": ["Psychic", "Colorless"],
                "base_damage": 0,
                "text": "This attack does 20 damage to 1 of your opponent's Pokémon for each damage counter on this Pokémon."
            }],
            "weakness": {"type": "Darkness", "value": "x2"},
            "retreat_cost": ["Colorless"],
            "regulation_mark": "G",
            "expansion": "SV4",
            "collection_no": "86"
        },
        {
            "card_id": "sv1-89",
            "dataset_id": "89",
            "name": "Drifloon",
            "supertype": "Pokémon",
            "subtypes": ["Basic"],
            "hp": 70,
            "types": ["Psychic"],
            "attacks": [{
                "name": "Balloon Bombs",
                "cost": ["Colorless", "Colorless"],
                "base_damage": 0,
                "text": "This attack does 30 damage for each damage counter on this Pokémon."
            }],
            "weakness": {"type": "Darkness", "value": "x2"},
            "retreat_cost": ["Colorless"],
            "regulation_mark": "G",
            "expansion": "SV1",
            "collection_no": "89"
        },
        {
            "card_id": "asr-46",
            "dataset_id": "46",
            "name": "Radiant Greninja",
            "supertype": "Pokémon",
            "subtypes": ["Basic", "Radiant", "Rule Box"],
            "hp": 130,
            "types": ["Water"],
            "attacks": [{
                "name": "Moonlight Shuriken",
                "cost": ["Water", "Water", "Colorless"],
                "base_damage": 90,
                "text": "Discard 2 Energy from this Pokémon. This attack does 90 damage to 2 of your opponent's Pokémon."
            }],
            "abilities": [{
                "name": "Concealed Cards",
                "type": "Ability",
                "effect": "You must discard an Energy card from your hand in order to use this Ability. Once during your turn, you may draw 2 cards."
            }],
            "weakness": {"type": "Lightning", "value": "x2"},
            "retreat_cost": ["Colorless"],
            "regulation_mark": "F",
            "expansion": "ASR",
            "collection_no": "46"
        },
        {
            "card_id": "sv2-93",
            "dataset_id": "93",
            "name": "Radiant Greninja",
            "supertype": "Pokémon",
            "subtypes": ["Basic", "Radiant", "Rule Box"],
            "hp": 130,
            "types": ["Water"],
            "attacks": [{
                "name": "Moonlight Shuriken",
                "cost": ["Water", "Water", "Colorless"],
                "base_damage": 90,
                "text": "Discard 2 Energy from this Pokémon. This attack does 90 damage to 2 of your opponent's Pokémon."
            }],
            "abilities": [{
                "name": "Concealed Cards",
                "type": "Ability",
                "effect": "You must discard an Energy card from your hand in order to use this Ability. Once during your turn, you may draw 2 cards."
            }],
            "weakness": {"type": "Lightning", "value": "x2"},
            "retreat_cost": ["Colorless"],
            "regulation_mark": "F",
            "expansion": "SV2",
            "collection_no": "93"
        },
        {
            "card_id": "brs-40",
            "dataset_id": "40",
            "name": "Lumineon V",
            "supertype": "Pokémon",
            "subtypes": ["Basic", "V", "Rule Box"],
            "hp": 170,
            "types": ["Water"],
            "attacks": [{
                "name": "Aqua Return",
                "cost": ["Water", "Colorless", "Colorless"],
                "base_damage": 120,
                "text": "Shuffle this Pokémon and all attached cards into your deck."
            }],
            "abilities": [{
                "name": "Luminous Sign",
                "type": "Ability",
                "effect": "When you play this Pokémon from your hand onto your Bench during your turn, you may search your deck for a Supporter card, reveal it, and put it into your hand."
            }],
            "weakness": {"type": "Lightning", "value": "x2"},
            "retreat_cost": ["Colorless"],
            "regulation_mark": "F",
            "expansion": "BRS",
            "collection_no": "40"
        },

        # Core Item / Supporter Cards (with canonical test IDs)
        {
            "card_id": "sv1-189",
            "dataset_id": "189",
            "name": "Professor's Research",
            "supertype": "Trainer",
            "subtypes": ["Supporter"],
            "regulation_mark": "G",
            "expansion": "SV1",
            "collection_no": "189",
            "effects": [{"type": "SUPPORTER_EFFECT", "text": "Discard your hand and draw 7 cards."}]
        },
        {
            "card_id": "sv1-196",
            "dataset_id": "196",
            "name": "Ultra Ball",
            "supertype": "Trainer",
            "subtypes": ["Item"],
            "regulation_mark": "G",
            "expansion": "SV1",
            "collection_no": "196",
            "effects": [{"type": "ITEM_EFFECT", "text": "Discard 2 cards from your hand. Search your deck for any Pokémon."}]
        },
        {
            "card_id": "sv1-181",
            "dataset_id": "181",
            "name": "Nest Ball",
            "supertype": "Trainer",
            "subtypes": ["Item"],
            "regulation_mark": "G",
            "expansion": "SV1",
            "collection_no": "181",
            "effects": [{"type": "ITEM_EFFECT", "text": "Search your deck for a Basic Pokémon and put it onto your Bench."}]
        },
        {
            "card_id": "sv1-191",
            "dataset_id": "191",
            "name": "Rare Candy",
            "supertype": "Trainer",
            "subtypes": ["Item"],
            "regulation_mark": "G",
            "expansion": "SV1",
            "collection_no": "191",
            "effects": [{"type": "ITEM_EFFECT", "text": "Evolve a Basic Pokémon directly into a Stage 2 Pokémon."}]
        },
        {
            "card_id": "sv1-171",
            "dataset_id": "171",
            "name": "Electric Generator",
            "supertype": "Trainer",
            "subtypes": ["Item"],
            "regulation_mark": "G",
            "expansion": "SV1",
            "collection_no": "171",
            "effects": [{"type": "ITEM_EFFECT", "text": "Attach up to 2 Basic Lightning Energy from top 5 cards of deck to Benched Lightning Pokémon."}]
        },
        {
            "card_id": "sv2-188",
            "dataset_id": "188",
            "name": "Super Rod",
            "supertype": "Trainer",
            "subtypes": ["Item"],
            "regulation_mark": "G",
            "expansion": "SV2",
            "collection_no": "188",
            "effects": [{"type": "ITEM_EFFECT", "text": "Shuffle up to 3 in combination of Pokémon and Basic Energy from discard into deck."}]
        },
        {
            "card_id": "sv1-166",
            "dataset_id": "166",
            "name": "Arven",
            "supertype": "Trainer",
            "subtypes": ["Supporter"],
            "regulation_mark": "G",
            "expansion": "SV1",
            "collection_no": "166",
            "effects": [{"type": "SUPPORTER_EFFECT", "text": "Search deck for an Item and a Pokémon Tool card."}]
        },
        {
            "card_id": "sv2-185",
            "dataset_id": "185",
            "name": "Iono",
            "supertype": "Trainer",
            "subtypes": ["Supporter"],
            "regulation_mark": "G",
            "expansion": "SV2",
            "collection_no": "185",
            "effects": [{"type": "SUPPORTER_EFFECT", "text": "Each player shuffles hand to bottom of deck and draws for each remaining Prize."}]
        },
        {
            "card_id": "sv2-172",
            "dataset_id": "172",
            "name": "Boss's Orders",
            "supertype": "Trainer",
            "subtypes": ["Supporter"],
            "regulation_mark": "G",
            "expansion": "SV2",
            "collection_no": "172",
            "effects": [{"type": "SUPPORTER_EFFECT", "text": "Switch in 1 of opponent's Benched Pokémon to Active Spot."}]
        },
        {
            "card_id": "sv5-157",
            "dataset_id": "157",
            "name": "Prime Catcher",
            "supertype": "Trainer",
            "subtypes": ["ACE SPEC", "Item"],
            "regulation_mark": "G",
            "expansion": "SV5",
            "collection_no": "157",
            "effects": [{"type": "ITEM_EFFECT", "text": "Switch opponent's Benched Pokémon and switch your Active Pokémon."}]
        },
        {
            "card_id": "sv5-144",
            "dataset_id": "144",
            "name": "Prime Catcher",
            "supertype": "Trainer",
            "subtypes": ["ACE SPEC", "Item"],
            "regulation_mark": "G",
            "expansion": "SV5",
            "collection_no": "144",
            "effects": [{"type": "ITEM_EFFECT", "text": "Switch opponent's Benched Pokémon and switch your Active Pokémon."}]
        },
        {
            "card_id": "sv4-163",
            "dataset_id": "163",
            "name": "Earthen Vessel",
            "supertype": "Trainer",
            "subtypes": ["Item"],
            "regulation_mark": "G",
            "expansion": "SV4",
            "collection_no": "163",
            "effects": [{"type": "ITEM_EFFECT", "text": "Discard 1 card. Search deck for up to 2 Basic Energy cards."}]
        },
        {
            "card_id": "sv4-160",
            "dataset_id": "160",
            "name": "Counter Catcher",
            "supertype": "Trainer",
            "subtypes": ["Item"],
            "regulation_mark": "G",
            "expansion": "SV4",
            "collection_no": "160",
            "effects": [{"type": "ITEM_EFFECT", "text": "If behind on Prizes, switch in opponent's Benched Pokémon."}]
        },
        {
            "card_id": "sv1-194",
            "dataset_id": "194",
            "name": "Switch",
            "supertype": "Trainer",
            "subtypes": ["Item"],
            "regulation_mark": "G",
            "expansion": "SV1",
            "collection_no": "194",
            "effects": [{"type": "ITEM_EFFECT", "text": "Switch your Active Pokémon with 1 of your Benched Pokémon."}]
        },
        {
            "card_id": "sv2-173",
            "dataset_id": "173",
            "name": "Bravery Charm",
            "supertype": "Trainer",
            "subtypes": ["Tool"],
            "regulation_mark": "G",
            "expansion": "SV2",
            "collection_no": "173",
            "effects": [{"type": "TOOL_EFFECT", "text": "Basic Pokémon gets +50 HP."}]
        },
        {
            "card_id": "sv1-169",
            "dataset_id": "169",
            "name": "Defiance Band",
            "supertype": "Trainer",
            "subtypes": ["Tool"],
            "regulation_mark": "G",
            "expansion": "SV1",
            "collection_no": "169",
            "effects": [{"type": "TOOL_EFFECT", "text": "If behind on Prizes, attacks do 30 more damage."}]
        },
        {
            "card_id": "sit-156",
            "dataset_id": "156",
            "name": "Forest Seal Stone",
            "supertype": "Trainer",
            "subtypes": ["Tool"],
            "regulation_mark": "F",
            "expansion": "SIT",
            "collection_no": "156",
            "effects": [{"type": "TOOL_EFFECT", "text": "Enables Star Order VSTAR Power."}]
        },
        {
            "card_id": "sv3-171",
            "dataset_id": "171",
            "name": "Artazon",
            "supertype": "Trainer",
            "subtypes": ["Stadium"],
            "regulation_mark": "G",
            "expansion": "SV3",
            "collection_no": "171",
            "effects": [{"type": "STADIUM_EFFECT", "text": "Search deck for Basic Pokémon without Rule Box onto Bench."}]
        },
        {
            "card_id": "sv1-167",
            "dataset_id": "167",
            "name": "Artazon",
            "supertype": "Trainer",
            "subtypes": ["Stadium"],
            "regulation_mark": "G",
            "expansion": "SV1",
            "collection_no": "167",
            "effects": [{"type": "STADIUM_EFFECT", "text": "Basic Pokémon have 1 less retreat cost."}]
        },
        {
            "card_id": "sv3-196",
            "dataset_id": "196",
            "name": "Town Store",
            "supertype": "Trainer",
            "subtypes": ["Stadium"],
            "regulation_mark": "G",
            "expansion": "SV3",
            "collection_no": "196",
            "effects": [{"type": "STADIUM_EFFECT", "text": "Search deck for a Pokémon Tool card."}]
        },
        {
            "card_id": "sv1-178",
            "dataset_id": "178",
            "name": "Lost Vacuum",
            "supertype": "Trainer",
            "subtypes": ["Item"],
            "regulation_mark": "G",
            "expansion": "SV1",
            "collection_no": "178",
            "effects": [{"type": "ITEM_EFFECT", "text": "Send a Tool or Stadium to Lost Zone."}]
        },

        # Core Energies (with canonical sve- IDs)
        {
            "card_id": "sve-1",
            "dataset_id": "1",
            "name": "Basic Grass Energy",
            "supertype": "Energy",
            "subtypes": ["Basic Energy"],
            "regulation_mark": "G",
            "expansion": "SVE",
            "collection_no": "1",
            "energy_type": "Grass"
        },
        {
            "card_id": "sve-2",
            "dataset_id": "2",
            "name": "Basic Fire Energy",
            "supertype": "Energy",
            "subtypes": ["Basic Energy"],
            "regulation_mark": "G",
            "expansion": "SVE",
            "collection_no": "2",
            "energy_type": "Fire"
        },
        {
            "card_id": "sve-3",
            "dataset_id": "3",
            "name": "Basic Water Energy",
            "supertype": "Energy",
            "subtypes": ["Basic Energy"],
            "regulation_mark": "G",
            "expansion": "SVE",
            "collection_no": "3",
            "energy_type": "Water"
        },
        {
            "card_id": "sve-4",
            "dataset_id": "4",
            "name": "Basic Lightning Energy",
            "supertype": "Energy",
            "subtypes": ["Basic Energy"],
            "regulation_mark": "G",
            "expansion": "SVE",
            "collection_no": "4",
            "energy_type": "Lightning"
        },
        {
            "card_id": "sve-5",
            "dataset_id": "5",
            "name": "Basic Psychic Energy",
            "supertype": "Energy",
            "subtypes": ["Basic Energy"],
            "regulation_mark": "G",
            "expansion": "SVE",
            "collection_no": "5",
            "energy_type": "Psychic"
        },
        {
            "card_id": "sve-6",
            "dataset_id": "6",
            "name": "Basic Fighting Energy",
            "supertype": "Energy",
            "subtypes": ["Basic Energy"],
            "regulation_mark": "G",
            "expansion": "SVE",
            "collection_no": "6",
            "energy_type": "Fighting"
        },
        {
            "card_id": "sve-7",
            "dataset_id": "7",
            "name": "Basic Darkness Energy",
            "supertype": "Energy",
            "subtypes": ["Basic Energy"],
            "regulation_mark": "G",
            "expansion": "SVE",
            "collection_no": "7",
            "energy_type": "Darkness"
        },
        {
            "card_id": "sve-8",
            "dataset_id": "8",
            "name": "Basic Metal Energy",
            "supertype": "Energy",
            "subtypes": ["Basic Energy"],
            "regulation_mark": "G",
            "expansion": "SVE",
            "collection_no": "8",
            "energy_type": "Metal"
        },
        {
            "card_id": "brs-151",
            "dataset_id": "151",
            "name": "Double Turbo Energy",
            "supertype": "Energy",
            "subtypes": ["Special Energy"],
            "regulation_mark": "F",
            "expansion": "BRS",
            "collection_no": "151",
            "energy_type": "Colorless",
            "text": "Provides 2 Colorless Energy. Attacks do 20 less damage."
        }
    ]

    for c in core_cards:
        cards_map[c["card_id"]] = c

    # 2. Add full 1,025 National Pokédex species (Standard + ex forms)
    for p_id, name, ptype, stage, hp in ALL_1025_POKEMON_RAW:
        cid = f"pkm-{p_id:04d}"
        if cid not in cards_map:
            cards_map[cid] = {
                "card_id": cid,
                "dataset_id": str(p_id),
                "name": name,
                "supertype": "Pokémon",
                "subtypes": [stage],
                "hp": hp,
                "types": [ptype],
                "attacks": [{
                    "name": f"{name} Strike",
                    "cost": [ptype],
                    "base_damage": int(hp * 0.6),
                    "text": f"Inflicts standard {ptype} combat damage."
                }],
                "regulation_mark": "G",
                "expansion": "SV-PAL",
                "collection_no": str(p_id)
            }

        # Add ex Ultra Rare
        ex_cid = f"pkm-ex-{p_id:04d}"
        if ex_cid not in cards_map:
            ex_hp = min(340, hp + 150)
            cards_map[ex_cid] = {
                "card_id": ex_cid,
                "dataset_id": f"ex-{p_id}",
                "name": f"{name} ex",
                "supertype": "Pokémon",
                "subtypes": [stage, "ex", "Rule Box"],
                "hp": ex_hp,
                "types": [ptype],
                "attacks": [
                    {
                        "name": f"{name} Surge",
                        "cost": [ptype],
                        "base_damage": 60,
                        "text": "Quick tempo attack."
                    },
                    {
                        "name": f"{name} Cataclysm",
                        "cost": [ptype, ptype, "Colorless"],
                        "base_damage": int(ex_hp * 0.75),
                        "text": f"Deals massive {ptype} power blow."
                    }
                ],
                "abilities": [{
                    "name": f"{name} Power",
                    "type": "Ability",
                    "effect": f"Boosts {ptype} type Pokémon damage and draw engine."
                }],
                "regulation_mark": "G",
                "expansion": "SV-EX",
                "collection_no": f"EX-{p_id}"
            }

    # 3. Add all trainer cards
    for idx, item in enumerate(TRAINER_CARDS, start=100):
        tname = item[0]
        ttype = item[1]
        text = item[2]
        t_cid = f"trn-{idx:04d}"
        if t_cid not in cards_map:
            cards_map[t_cid] = {
                "card_id": t_cid,
                "dataset_id": f"TRN-{idx}",
                "name": tname,
                "supertype": "Trainer",
                "subtypes": [ttype],
                "regulation_mark": "G",
                "expansion": "SV-TRN",
                "collection_no": str(idx),
                "effects": [{
                    "type": f"{ttype.upper()}_EFFECT",
                    "text": text
                }]
            }

    # 4. Add all energy cards
    for idx, item in enumerate(ENERGY_CARDS, start=100):
        ename = item[0]
        etype = item[1]
        eenergy = item[2]
        etext = item[3] if len(item) > 3 else f"Provides 1 {eenergy} Energy."
        e_cid = f"en-{idx:04d}"
        if e_cid not in cards_map:
            cards_map[e_cid] = {
                "card_id": e_cid,
                "dataset_id": f"EN-{idx}",
                "name": ename,
                "supertype": "Energy",
                "subtypes": [etype],
                "regulation_mark": "G",
                "expansion": "SVE",
                "collection_no": str(idx),
                "energy_type": eenergy,
                "text": etext
            }

    all_cards = list(cards_map.values())
    out_p = os.path.join("data", "cards_dataset.json")
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump({"cards": all_cards}, f, indent=2)

    print(f"Enriched complete dataset saved: {len(all_cards)} total cards!")
    return all_cards

if __name__ == "__main__":
    build_enriched_cards()
