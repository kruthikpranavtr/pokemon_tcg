"""
Database and Authentication Module for Pokémon TCG Collection Game
Uses SQLite, standard library hashlib (PBKDF2-HMAC-SHA256) and secrets.
"""
import os
import sys
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "pokemon_tcg.db")
CARDS_FILE = os.path.join(DATA_DIR, "cards_dataset.json")


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return key.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    expected_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(expected_hash, password_hash)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL COLLATE NOCASE,
        email TEXT UNIQUE NOT NULL COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 3. Master Cards Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS master_cards (
        card_id TEXT PRIMARY KEY,
        dataset_id TEXT,
        name TEXT NOT NULL,
        card_type TEXT NOT NULL, -- 'pokemon', 'trainer', 'energy'
        pokemon_type TEXT,        -- Fire, Water, etc.
        stage TEXT,               -- Basic, Stage 1, Stage 2
        evolves_from TEXT,
        rarity TEXT NOT NULL,     -- Common, Uncommon, Rare, Ultra Rare, Special
        hp INTEGER,
        image TEXT,
        attacks_json TEXT,
        effect TEXT,
        raw_json TEXT
    );
    """)

    # 4. User Collection Table (Tracks card ownership and quantities)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_collection (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        card_id TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        first_obtained TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_obtained TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, card_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (card_id) REFERENCES master_cards(card_id) ON DELETE CASCADE
    );
    """)

    # 5. Pack History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pack_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        cards_json TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    conn.commit()

    # Seed master cards if table is empty
    count = cursor.execute("SELECT COUNT(*) FROM master_cards").fetchone()[0]
    if count == 0:
        seed_master_cards(conn)
    else:
        # Check if classic trainers like Potion and Poké Ball exist, if not ensure them
        ensure_classic_trainers(conn)

    conn.close()


def assign_card_rarity(c: dict) -> str:
    stype = (c.get("supertype") or c.get("card_type") or "").lower()
    name = c.get("name", "")
    subtypes = [s.lower() for s in (c.get("subtypes") or [])]
    stage = c.get("stage")

    if "energy" in stype:
        if "special" in name.lower() or any("special" in s for s in subtypes):
            return "Uncommon"
        return "Common"

    if "trainer" in stype:
        if any(s in subtypes for s in ["supporter", "stadium"]):
            return "Uncommon"
        if any(w in name.lower() for w in ["prime", "ultra", "master", "belt", "unfair"]):
            return "Rare"
        return "Common"

    # Pokémon Cards
    is_legendary = any(leg in name.lower() for leg in [
        "mewtwo", "rayquaza", "arceus", "miraidon", "koraidon", "lugia", "ho-oh",
        "dialga", "palkia", "giratina", "kyogre", "groudon", "zacian", "zamazenta",
        "necrozma", "solgaleo", "lunala", "reshiram", "zekrom"
    ])
    if is_legendary and ("ex" in subtypes or "v" in subtypes or "ex" in name.lower()):
        return "Special"

    if "ex" in subtypes or "v" in subtypes or "vstar" in subtypes or "tera" in subtypes or "ex" in name.lower():
        return "Ultra Rare"

    if stage == "Stage 2" or "stage 2" in subtypes:
        return "Rare"

    if stage == "Stage 1" or "stage 1" in subtypes:
        return "Uncommon"

    # Basic Pokémon: if high HP or iconic rare basic
    hp = c.get("hp") or 0
    if hp >= 130:
        return "Rare"
    if hp >= 90:
        return "Uncommon"

    return "Common"


def get_pokemon_image_url(c: dict) -> str:
    # Try dataset_id if numeric (Pokédex ID)
    ds_id = c.get("dataset_id")
    pokedex_id = None
    if ds_id:
        try:
            clean_id = str(ds_id).replace("ex-", "").replace("pkm-", "").strip()
            num = int(clean_id)
            if 1 <= num <= 1025:
                pokedex_id = num
        except (ValueError, TypeError):
            pass

    if pokedex_id:
        return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{pokedex_id}.png"

    return ""


def ensure_classic_trainers(conn: sqlite3.Connection):
    cursor = conn.cursor()
    classic = [
        {
            "card_id": "trainer_potion",
            "name": "Potion",
            "card_type": "trainer",
            "pokemon_type": "Item",
            "stage": None,
            "evolves_from": None,
            "rarity": "Common",
            "hp": None,
            "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/potion.png",
            "attacks_json": "[]",
            "effect": "Heal 30 damage from 1 of your Pokémon.",
            "raw_json": json.dumps({
                "card_id": "trainer_potion", "name": "Potion", "supertype": "Trainer",
                "subtypes": ["Item"], "effects": [{"type": "HEAL", "text": "Heal 30 damage from 1 of your Pokémon."}]
            })
        },
        {
            "card_id": "trainer_pokeball",
            "name": "Poké Ball",
            "card_type": "trainer",
            "pokemon_type": "Item",
            "stage": None,
            "evolves_from": None,
            "rarity": "Common",
            "hp": None,
            "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png",
            "attacks_json": "[]",
            "effect": "Flip a coin. If heads, search your deck for a Pokémon, reveal it, and put it into your hand.",
            "raw_json": json.dumps({
                "card_id": "trainer_pokeball", "name": "Poké Ball", "supertype": "Trainer",
                "subtypes": ["Item"], "effects": [{"type": "SEARCH", "text": "Flip a coin. If heads, draw 1 Pokémon from deck."}]
            })
        }
    ]
    for card in classic:
        cursor.execute("""
        INSERT OR IGNORE INTO master_cards (
            card_id, dataset_id, name, card_type, pokemon_type, stage,
            evolves_from, rarity, hp, image, attacks_json, effect, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            card["card_id"], card["card_id"], card["name"], card["card_type"],
            card["pokemon_type"], card["stage"], card["evolves_from"], card["rarity"],
            card["hp"], card["image"], card["attacks_json"], card["effect"], card["raw_json"]
        ))
    conn.commit()


def seed_master_cards(conn: sqlite3.Connection):
    if not os.path.exists(CARDS_FILE):
        return

    with open(CARDS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    cards = data.get("cards", [])
    cursor = conn.cursor()

    for c in cards:
        cid = c.get("card_id") or str(c.get("dataset_id"))
        if not cid:
            continue
        ds_id = str(c.get("dataset_id", cid))
        name = c.get("name", "Unknown Card")
        stype = (c.get("supertype") or "Pokémon").lower()
        if "trainer" in stype:
            card_type = "trainer"
        elif "energy" in stype:
            card_type = "energy"
        else:
            card_type = "pokemon"

        # Types
        types = c.get("types") or []
        pkmn_type = types[0] if types else (c.get("energy_type") or ("Item" if card_type == "trainer" else "Colorless"))

        stage = c.get("stage")
        if not stage:
            subs = [s.lower() for s in (c.get("subtypes") or [])]
            if "stage 2" in subs:
                stage = "Stage 2"
            elif "stage 1" in subs:
                stage = "Stage 1"
            elif "basic" in subs or card_type == "pokemon":
                stage = "Basic"
            else:
                stage = None

        evolves_from = c.get("evolves_from")
        rarity = c.get("rarity") or assign_card_rarity(c)
        hp = c.get("hp")
        image = c.get("image") or get_pokemon_image_url(c)
        attacks_json = json.dumps(c.get("attacks") or [])
        
        effect = ""
        if c.get("effects"):
            effect = " ".join(e.get("text", "") for e in c["effects"])
        elif c.get("abilities"):
            effect = " ".join(a.get("effect", "") for a in c["abilities"])

        cursor.execute("""
        INSERT OR REPLACE INTO master_cards (
            card_id, dataset_id, name, card_type, pokemon_type, stage,
            evolves_from, rarity, hp, image, attacks_json, effect, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cid, ds_id, name, card_type, pkmn_type, stage,
            evolves_from, rarity, hp, image, attacks_json, effect, json.dumps(c)
        ))

    ensure_classic_trainers(conn)
    conn.commit()


# --- AUTHENTICATION & USERS ---

def register_user(username: str, email: str, password: str) -> Dict[str, Any]:
    username = username.strip()
    email = email.strip().lower()

    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters long.")
    if "@" not in email or "." not in email:
        raise ValueError("Please provide a valid email address.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    pwd_hash, salt = hash_password(password)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO users (username, email, password_hash, salt)
        VALUES (?, ?, ?, ?)
        """, (username, email, pwd_hash, salt))
        user_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError as e:
        err_msg = str(e).lower()
        if "users.username" in err_msg or "unique constraint failed: users.username" in err_msg:
            raise ValueError(f"Username '{username}' is already registered.")
        elif "users.email" in err_msg or "unique constraint failed: users.email" in err_msg:
            raise ValueError(f"Email '{email}' is already registered.")
        else:
            raise ValueError("An account with this username or email already exists.")
    finally:
        conn.close()

    token = create_session(user_id)
    return {
        "id": user_id,
        "username": username,
        "email": email,
        "token": token
    }


def authenticate_user(username_or_email: str, password: str) -> Dict[str, Any]:
    ident = username_or_email.strip()
    conn = get_db_connection()
    cursor = conn.cursor()

    row = cursor.execute("""
    SELECT id, username, email, password_hash, salt FROM users
    WHERE username = ? OR email = ?
    """, (ident, ident.lower())).fetchone()

    conn.close()

    if not row:
        raise ValueError("Invalid username/email or password.")

    if not verify_password(password, row["password_hash"], row["salt"]):
        raise ValueError("Invalid username/email or password.")

    token = create_session(row["id"])
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "token": token
    }


def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    expires_at = get_utc_now() + timedelta(days=14)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO sessions (token, user_id, expires_at)
    VALUES (?, ?, ?)
    """, (token, user_id, expires_at.isoformat()))
    conn.commit()
    conn.close()
    return token


def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute("""
    SELECT u.id, u.username, u.email, u.created_at, s.expires_at
    FROM sessions s
    JOIN users u ON s.user_id = u.id
    WHERE s.token = ?
    """, (token,)).fetchone()
    conn.close()

    if not row:
        return None

    try:
        exp = datetime.fromisoformat(row["expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < get_utc_now():
            logout_session(token)
            return None
    except Exception:
        pass

    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "created_at": row["created_at"]
    }


def logout_session(token: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


# --- USER COLLECTION & QUANTITIES ---

def get_user_collection_stats(user_id: int) -> Dict[str, int]:
    conn = get_db_connection()
    cursor = conn.cursor()

    rows = cursor.execute("""
    SELECT m.card_type, SUM(uc.quantity) as total_qty, COUNT(uc.card_id) as distinct_cards
    FROM user_collection uc
    JOIN master_cards m ON uc.card_id = m.card_id
    WHERE uc.user_id = ?
    GROUP BY m.card_type
    """, (user_id,)).fetchall()

    conn.close()

    stats = {
        "total_cards": 0,
        "distinct_cards": 0,
        "pokemon": 0,
        "trainer": 0,
        "energy": 0
    }
    for r in rows:
        ctype = r["card_type"]
        qty = r["total_qty"] or 0
        dist = r["distinct_cards"] or 0
        stats["total_cards"] += qty
        stats["distinct_cards"] += dist
        if ctype == "pokemon":
            stats["pokemon"] = qty
        elif ctype == "trainer":
            stats["trainer"] = qty
        elif ctype == "energy":
            stats["energy"] = qty

    return stats


def get_user_collection(
    user_id: int,
    category: Optional[str] = None,
    stage: Optional[str] = None,
    rarity: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200,
    offset: int = 0
) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT uc.quantity, uc.first_obtained, uc.last_obtained,
           m.card_id, m.dataset_id, m.name, m.card_type, m.pokemon_type,
           m.stage, m.evolves_from, m.rarity, m.hp, m.image,
           m.attacks_json, m.effect, m.raw_json
    FROM user_collection uc
    JOIN master_cards m ON uc.card_id = m.card_id
    WHERE uc.user_id = ?
    """
    params = [user_id]

    if category and category.lower() != 'all':
        cat = category.lower()
        if cat == 'pokemon':
            query += " AND m.card_type = 'pokemon'"
        elif cat == 'trainer':
            query += " AND m.card_type = 'trainer'"
        elif cat == 'energy':
            query += " AND m.card_type = 'energy'"
        elif cat in ['item', 'supporter', 'stadium']:
            query += " AND (LOWER(m.pokemon_type) = ? OR LOWER(m.raw_json) LIKE ?)"
            params.extend([cat, f"%{cat}%"])

    if stage and stage.lower() != 'all':
        stg = stage.lower()
        if 'basic' in stg:
            query += " AND (m.stage = 'Basic' OR (m.stage IS NULL AND m.card_type = 'pokemon'))"
        elif 'stage 1' in stg:
            query += " AND m.stage = 'Stage 1'"
        elif 'stage 2' in stg:
            query += " AND m.stage = 'Stage 2'"

    if rarity and rarity.lower() != 'all':
        query += " AND LOWER(m.rarity) = ?"
        params.append(rarity.lower())

    if search and search.strip():
        s = f"%{search.strip().lower()}%"
        query += " AND (LOWER(m.name) LIKE ? OR LOWER(m.pokemon_type) LIKE ? OR LOWER(m.attacks_json) LIKE ? OR LOWER(m.effect) LIKE ?)"
        params.extend([s, s, s, s])

    query += " ORDER BY m.card_type ASC, m.name ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = cursor.execute(query, params).fetchall()
    conn.close()

    result = []
    for r in rows:
        c = dict(r)
        c["attacks"] = json.loads(c.get("attacks_json") or "[]")
        c["raw_data"] = json.loads(c.get("raw_json") or "{}")
        result.append(c)

    return result


def add_cards_to_user_collection(user_id: int, card_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Adds a list of card IDs to a user's collection.
    Increments quantity for duplicates and tracks previous vs new quantity.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = get_utc_now().isoformat()

    results = []
    for cid in card_ids:
        row = cursor.execute("""
        SELECT quantity FROM user_collection
        WHERE user_id = ? AND card_id = ?
        """, (user_id, cid)).fetchone()

        if row:
            prev_qty = row["quantity"]
            new_qty = prev_qty + 1
            cursor.execute("""
            UPDATE user_collection
            SET quantity = ?, last_obtained = ?
            WHERE user_id = ? AND card_id = ?
            """, (new_qty, now_iso, user_id, cid))
            is_dup = True
        else:
            prev_qty = 0
            new_qty = 1
            cursor.execute("""
            INSERT INTO user_collection (user_id, card_id, quantity, first_obtained, last_obtained)
            VALUES (?, ?, 1, ?, ?)
            """, (user_id, cid, now_iso, now_iso))
            is_dup = False

        card_row = cursor.execute("SELECT * FROM master_cards WHERE card_id = ?", (cid,)).fetchone()
        c_dict = dict(card_row) if card_row else {"card_id": cid, "name": cid, "rarity": "Common", "card_type": "pokemon"}
        c_dict["attacks"] = json.loads(c_dict.get("attacks_json") or "[]")
        c_dict["previous_quantity"] = prev_qty
        c_dict["quantity"] = new_qty
        c_dict["is_duplicate"] = is_dup
        results.append(c_dict)

    conn.commit()
    conn.close()
    return results


def record_pack_opening(user_id: int, cards: List[Dict[str, Any]]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cards_summary = [
        {
            "card_id": c.get("card_id"),
            "name": c.get("name"),
            "card_type": c.get("card_type"),
            "rarity": c.get("rarity"),
            "quantity": c.get("quantity"),
            "is_duplicate": c.get("is_duplicate", False)
        }
        for c in cards
    ]
    cursor.execute("""
    INSERT INTO pack_history (user_id, cards_json)
    VALUES (?, ?)
    """, (user_id, json.dumps(cards_summary)))
    conn.commit()
    conn.close()


def get_user_pack_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute("""
    SELECT id, opened_at, cards_json
    FROM pack_history
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()

    history = []
    for r in rows:
        history.append({
            "id": r["id"],
            "opened_at": r["opened_at"],
            "cards": json.loads(r["cards_json"])
        })
    return history


def get_master_cards(
    category: Optional[str] = None,
    stage: Optional[str] = None,
    rarity: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Tuple[int, List[Dict[str, Any]]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    base_where = " WHERE 1=1"
    params = []

    if category and category.lower() != 'all':
        cat = category.lower()
        if cat in ['pokemon', 'trainer', 'energy']:
            base_where += " AND card_type = ?"
            params.append(cat)

    if stage and stage.lower() != 'all':
        stg = stage.lower()
        if 'basic' in stg:
            base_where += " AND (stage = 'Basic' OR (stage IS NULL AND card_type = 'pokemon'))"
        elif 'stage 1' in stg:
            base_where += " AND stage = 'Stage 1'"
        elif 'stage 2' in stg:
            base_where += " AND stage = 'Stage 2'"

    if rarity and rarity.lower() != 'all':
        base_where += " AND LOWER(rarity) = ?"
        params.append(rarity.lower())

    if search and search.strip():
        s = f"%{search.strip().lower()}%"
        base_where += " AND (LOWER(name) LIKE ? OR LOWER(pokemon_type) LIKE ? OR LOWER(attacks_json) LIKE ? OR LOWER(effect) LIKE ?)"
        params.extend([s, s, s, s])

    total = cursor.execute(f"SELECT COUNT(*) FROM master_cards{base_where}", params).fetchone()[0]

    query = f"SELECT * FROM master_cards{base_where} ORDER BY card_type ASC, name ASC LIMIT ? OFFSET ?"
    rows = cursor.execute(query, params + [limit, offset]).fetchall()
    conn.close()

    cards = []
    for r in rows:
        c = dict(r)
        c["attacks"] = json.loads(c.get("attacks_json") or "[]")
        c["raw_data"] = json.loads(c.get("raw_json") or "{}")
        cards.append(c)

    return total, cards


# Automatically initialize schema and seed on module import
init_db()
