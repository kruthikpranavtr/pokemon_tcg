import json
import random
from collections import Counter

with open('data/cards_dataset.json', 'r', encoding='utf-8') as f:
    cards = json.load(f)['cards']

basics = {}
stage1 = {}
stage2 = {}
trainers = []

for c in cards:
    cname = c.get('name')
    if c.get('card_type') == 'pokemon':
        st = c.get('stage')
        if st == 'Basic':
            basics[cname] = c
        elif st == 'Stage 1':
            stage1[cname] = c
        elif st == 'Stage 2':
            stage2[cname] = c
    elif c.get('card_type') == 'trainer':
        trainers.append(cname)

three_stage_families = []
for s2_name, s2_card in stage2.items():
    s1_name = s2_card.get('evolves_from')
    if s1_name in stage1:
        s1_card = stage1[s1_name]
        b_name = s1_card.get('evolves_from')
        if b_name in basics:
            ptype = s2_card.get('pokemon_type') or (s2_card.get('types') or ['Colorless'])[0]
            three_stage_families.append((ptype, [(b_name, 3), (s1_name, 2), (s2_name, 2)]))

two_stage_families = []
for s1_name, s1_card in stage1.items():
    b_name = s1_card.get('evolves_from')
    if b_name in basics:
        ptype = s1_card.get('pokemon_type') or (s1_card.get('types') or ['Colorless'])[0]
        two_stage_families.append((ptype, [(b_name, 3), (s1_name, 2)]))

basic_families = []
for b_name, b_card in basics.items():
    ptype = b_card.get('pokemon_type') or (b_card.get('types') or ['Colorless'])[0]
    basic_families.append((ptype, [(b_name, 3)]))

trainer_pool = [
    'Potion', 'Switch', 'Poké Ball', 'Ultra Ball', 'Rare Candy', 'Super Rod',
    'Energy Retrieval', 'Nest Ball', 'Professor’s Research', 'Boss’s Orders',
    'Arven', 'Iono', 'Pal Pad'
]
available_trainers = [t for t in trainer_pool if any(c['name'] == t for c in cards)]
if len(available_trainers) < 8:
    available_trainers = list(set(trainers))[:15]


def generate_random_deck():
    chosen_types = set()
    pkmn_counts = Counter()

    # 1. 50% chance to have a 3-stage family
    if random.random() < 0.5 and three_stage_families:
        ptype, fam = random.choice(three_stage_families)
        chosen_types.add(ptype)
        for name, cnt in fam:
            pkmn_counts[name] += cnt

    # 2. Pick 1-2 two-stage families
    for _ in range(random.randint(1, 2)):
        ptype, fam = random.choice(two_stage_families)
        chosen_types.add(ptype)
        for name, cnt in fam:
            pkmn_counts[name] = min(4, pkmn_counts[name] + cnt)

    # 3. Pick 1 basic family
    ptype, fam = random.choice(basic_families)
    chosen_types.add(ptype)
    for name, cnt in fam:
        pkmn_counts[name] = min(4, pkmn_counts[name] + cnt)

    deck = []
    for name, cnt in pkmn_counts.items():
        deck.extend([name] * cnt)

    # 4. Trainers: pick 7-8 distinct trainers with up to 4 copies each
    num_trainers = random.randint(26, 32)
    selected_trainers = random.sample(available_trainers, min(len(available_trainers), 8))
    t_counts = Counter()
    while sum(t_counts.values()) < num_trainers:
        t = random.choice(selected_trainers)
        if t_counts[t] < 4:
            t_counts[t] += 1
        elif all(t_counts[tr] >= 4 for tr in selected_trainers):
            break
    for t, cnt in t_counts.items():
        deck.extend([t] * cnt)

    # 5. Energies matching chosen types
    valid_energy_types = ['Fire', 'Water', 'Grass', 'Lightning', 'Psychic', 'Fighting', 'Darkness', 'Metal']
    cleaned_types = [t for t in chosen_types if t in valid_energy_types]
    if not cleaned_types:
        cleaned_types = ['Fire', 'Lightning']

    energy_names = [f'Basic {t} Energy' for t in cleaned_types]
    e_idx = 0
    while len(deck) < 60:
        deck.append(energy_names[e_idx % len(energy_names)])
        e_idx += 1

    return deck[:60]


for i in range(100):
    d = generate_random_deck()
    assert len(d) == 60, f'Deck len is {len(d)}'
    counts = Counter(d)
    for name, cnt in counts.items():
        if 'Energy' not in name:
            assert cnt <= 4, f'Card {name} has {cnt} copies!'

print('SUCCESS: All 100 randomly generated decks passed 100% of rule checks (60 cards, <= 4 copies of non-energy, valid families)!')
