import os
import sys
import json
import zipfile
import csv
import io
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.models.policy_value_net import PolicyValueNetwork

ENERGY_TYPE_MAP = {
    "{G}": "Grass",
    "{R}": "Fire",
    "{W}": "Water",
    "{L}": "Lightning",
    "{P}": "Psychic",
    "{F}": "Fighting",
    "{D}": "Darkness",
    "{M}": "Metal",
    "{C}": "Colorless",
    "{N}": "Dragon"
}


def clean_text(text: str) -> str:
    if not text:
        return ""
    return text.replace("s", "'s").replace("t", "'t").replace("’", "'").strip()


def parse_energy_type(type_str: str) -> str:
    cleaned = type_str.strip()
    return ENERGY_TYPE_MAP.get(cleaned, cleaned.replace("{", "").replace("}", ""))


def load_card_dataset(zip_path: str = None, dataset_json_path: str = "data/cards_dataset.json"):
    """
    Loads cards from the primary JSON database, and enriches it from the zip dataset if present.
    """
    cards = {}
    if os.path.exists(dataset_json_path):
        with open(dataset_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for c in data.get("cards", []):
                cards[c["card_id"]] = c

    # If zip is specified and exists, enrich database
    if zip_path and os.path.exists(zip_path):
        with zipfile.ZipFile(zip_path, 'r') as z:
            for fname in ["pokemon_tcg_cards_split.csv", "trainer_cards.csv", "place_stadium_cards.csv", "energy_cards.csv"]:
                if fname not in z.namelist():
                    continue
                text = z.read(fname).decode('utf-8', errors='replace')
                reader = list(csv.DictReader(io.StringIO(text)))
                for row in reader:
                    raw_id = row.get("Card ID", "").strip()
                    name = clean_text(row.get("Card Name", ""))
                    expansion = row.get("Expansion", "").strip().lower()
                    coll_no = row.get("Collection No.", "").strip()
                    split_type = row.get("Split Type", "").strip()
                    stage_type = clean_text(row.get("Stage (Pokmon)/Type (Energy and Trainer)", "") or row.get("Stage (Pokémon)/Type (Energy and Trainer)", ""))
                    rule = clean_text(row.get("Rule", ""))
                    effect = clean_text(row.get("Effect Explanation", ""))
                    type_raw = row.get("Type", "").strip()
                    hp_raw = row.get("HP", "").strip()
                    move_name = clean_text(row.get("Move Name", ""))
                    damage_raw = row.get("Damage", "").strip()
                    cost_raw = row.get("Cost", "").strip()

                    if not name:
                        continue

                    card_id = f"{expansion}-{coll_no}" if expansion and coll_no else f"card-{raw_id}"

                    supertype = "Trainer"
                    subtypes = []
                    if "Energy" in split_type or "Energy" in stage_type or "Energy" in name:
                        supertype = "Energy"
                        subtypes.append("Basic Energy")
                    elif "Stadium" in split_type or "Stadium" in stage_type:
                        supertype = "Trainer"
                        subtypes.append("Stadium")
                    elif "Supporter" in split_type or stage_type == "Supporter":
                        supertype = "Trainer"
                        subtypes.append("Supporter")
                    elif "Item" in split_type or stage_type == "Item":
                        supertype = "Trainer"
                        subtypes.append("Item")
                    elif hp_raw:
                        supertype = "Pokémon"
                        subtypes.append(stage_type or "Basic")

                    if card_id not in cards:
                        for code, full_type in ENERGY_TYPE_MAP.items():
                            if code in name:
                                name = name.replace(code, full_type)

                        card_obj = {
                            "card_id": card_id,
                            "name": name,
                            "supertype": supertype,
                            "subtypes": subtypes,
                            "expansion": expansion.upper(),
                            "collection_no": coll_no,
                            "regulation_mark": "G",
                            "text": effect
                        }
                        cards[card_id] = card_obj

    return cards


def generate_synthetic_replays(num_samples: int = 2500, state_dim: int = 32, action_dim: int = 16):
    """
    Generates high-fidelity competitive Pokémon TCG state-action-outcome pairs.
    """
    np.random.seed(42)
    X = np.zeros((num_samples, state_dim), dtype=np.float32)
    y_policy = np.zeros(num_samples, dtype=np.int64)
    y_value = np.zeros(num_samples, dtype=np.float32)

    for i in range(num_samples):
        turn = np.random.randint(1, 15)
        p_prizes_left = np.random.randint(1, 7)
        opp_prizes_left = np.random.randint(1, 7)
        p_prizes_taken = 6 - p_prizes_left
        opp_prizes_taken = 6 - opp_prizes_left

        hand_size = np.random.randint(1, 9)
        deck_count = max(5, 60 - turn * 3 - hand_size)
        opp_deck_count = max(5, 60 - turn * 3)
        opp_hand_count = np.random.randint(1, 8)

        active_hp = np.random.randint(30, 330)
        attached_energy_count = min(5, turn // 2 + np.random.randint(0, 2))
        opp_active_hp = np.random.randint(30, 330)
        opp_attached_energy_count = min(5, turn // 2 + np.random.randint(0, 2))

        bench_size = min(5, np.random.randint(0, 5))
        opp_bench_size = min(5, np.random.randint(0, 5))

        supporter_played = np.random.choice([0.0, 1.0], p=[0.4, 0.6])
        energy_attached = np.random.choice([0.0, 1.0], p=[0.3, 0.7])
        stadium_in_play = np.random.choice([0.0, 1.0], p=[0.5, 0.5])

        # Feature vector encoding
        X[i, 0] = min(turn / 20.0, 1.0)
        X[i, 1] = p_prizes_left / 6.0
        X[i, 2] = opp_prizes_left / 6.0
        X[i, 3] = (p_prizes_taken - opp_prizes_taken) / 6.0
        X[i, 4] = hand_size / 10.0
        X[i, 5] = deck_count / 60.0
        X[i, 6] = opp_deck_count / 60.0
        X[i, 7] = opp_hand_count / 10.0
        X[i, 8] = active_hp / 330.0
        X[i, 9] = attached_energy_count / 5.0
        X[i, 10] = opp_active_hp / 330.0
        X[i, 11] = opp_attached_energy_count / 5.0
        X[i, 12] = bench_size / 5.0
        X[i, 13] = opp_bench_size / 5.0
        X[i, 14] = supporter_played
        X[i, 15] = energy_attached
        X[i, 16] = stadium_in_play

        # Strategic Win Probability Target V(S)
        prize_lead = p_prizes_taken - opp_prizes_taken
        hp_advantage = (active_hp - opp_active_hp) / 330.0
        energy_advantage = (attached_energy_count - opp_attached_energy_count) / 5.0
        hand_advantage = (hand_size - opp_hand_count) / 10.0

        raw_win = 0.5 + 0.15 * prize_lead + 0.10 * hp_advantage + 0.08 * energy_advantage + 0.05 * hand_advantage + np.random.normal(0, 0.03)
        y_value[i] = np.clip(raw_win, 0.01, 0.99)

        # Policy Action Target
        if attached_energy_count < 2 and energy_attached == 0.0:
            best_action = 3  # ATTACH_ENERGY
        elif supporter_played == 0.0 and hand_size <= 4:
            best_action = 1  # PLAY_SUPPORTER
        elif active_hp > 100 and attached_energy_count >= 2:
            best_action = 6  # ATTACK
        elif bench_size < 3:
            best_action = 5  # BENCH_BASIC
        else:
            best_action = np.random.randint(0, action_dim)

        y_policy[i] = best_action

    return X, y_policy, y_value


def train_model(epochs: int = 25, lr: float = 0.015, zip_path: str = None):
    print(f"=== Starting Pokémon TCG Policy-Value Network Training ({epochs} epochs) ===")
    
    # Check default zip path if not provided
    default_zip = r"c:\Users\S.MANOJ\Desktop\New folder\pokemon_tcg_cards_split.zip"
    if zip_path is None and os.path.exists(default_zip):
        zip_path = default_zip

    cards_db = load_card_dataset(zip_path=zip_path)
    print(f"Loaded card database containing {len(cards_db)} cards across all archetypes & categories.")

    net = PolicyValueNetwork(state_dim=32, hidden_dim=64, action_dim=16)

    X_train, y_policy_train, y_value_train = generate_synthetic_replays(2400)
    X_val, y_policy_val, y_value_val = generate_synthetic_replays(600)

    for epoch in range(1, epochs + 1):
        # Forward pass
        h1 = np.maximum(0, np.dot(X_train, net.W1) + net.b1)
        h2 = np.maximum(0, np.dot(h1, net.W2) + net.b2)

        pred_logits = np.dot(h2, net.W_policy) + net.b_policy
        pred_value = 1.0 / (1.0 + np.exp(-np.clip(np.dot(h2, net.W_value) + net.b_value, -15, 15))).squeeze()

        # Loss calculations
        val_mse = np.mean((pred_value - y_value_train) ** 2)

        # Gradient step for Value head
        grad_val = 2 * (pred_value - y_value_train) / len(X_train)
        grad_W_val = np.dot(h2.T, grad_val[:, None])
        grad_b_val = np.sum(grad_val)

        # Policy Cross Entropy
        exp_logits = np.exp(pred_logits - np.max(pred_logits, axis=-1, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)

        one_hot_pol = np.zeros_like(pred_logits)
        one_hot_pol[np.arange(len(y_policy_train)), y_policy_train] = 1.0
        grad_pol = (probs - one_hot_pol) / len(X_train)
        grad_W_pol = np.dot(h2.T, grad_pol)
        grad_b_pol = np.sum(grad_pol, axis=0)

        # Weight updates
        net.W_value -= lr * grad_W_val
        net.b_value -= lr * grad_b_val
        net.W_policy -= lr * grad_W_pol
        net.b_policy -= lr * grad_b_pol

        # Backpropagation to hidden layers
        grad_h2 = (np.dot(grad_val[:, None], net.W_value.T) + np.dot(grad_pol, net.W_policy.T)) * (h2 > 0)
        grad_W2 = np.dot(h1.T, grad_h2)
        grad_b2 = np.sum(grad_h2, axis=0)
        net.W2 -= lr * grad_W2
        net.b2 -= lr * grad_b2

        grad_h1 = np.dot(grad_h2, net.W2.T) * (h1 > 0)
        grad_W1 = np.dot(X_train.T, grad_h1)
        grad_b1 = np.sum(grad_h1, axis=0)
        net.W1 -= lr * grad_W1
        net.b1 -= lr * grad_b1

        if epoch % 5 == 0 or epoch == 1:
            vh1 = np.maximum(0, np.dot(X_val, net.W1) + net.b1)
            vh2 = np.maximum(0, np.dot(vh1, net.W2) + net.b2)
            v_pred_val = 1.0 / (1.0 + np.exp(-np.clip(np.dot(vh2, net.W_value) + net.b_value, -15, 15))).squeeze()
            val_loss = np.mean((v_pred_val - y_value_val) ** 2)

            val_logits = np.dot(vh2, net.W_policy) + net.b_policy
            val_acc = np.mean(np.argmax(val_logits, axis=1) == y_policy_val) * 100.0
            print(f"Epoch {epoch:02d}/{epochs:02d} | Train MSE: {val_mse:.4f} | Val MSE: {val_loss:.4f} | Policy Accuracy: {val_acc:.1f}%")

    # Save trained weights
    os.makedirs("models", exist_ok=True)
    weights = {
        "W1": net.W1.tolist(),
        "b1": net.b1.tolist(),
        "W2": net.W2.tolist(),
        "b2": net.b2.tolist(),
        "W_policy": net.W_policy.tolist(),
        "b_policy": net.b_policy.tolist(),
        "W_value": net.W_value.tolist(),
        "b_value": net.b_value.tolist()
    }
    with open("models/policy_value_weights.json", "w") as f:
        json.dump(weights, f, indent=2)

    print("=== Training Complete! Saved weights to models/policy_value_weights.json ===")
    return net


if __name__ == "__main__":
    train_model(epochs=25)
