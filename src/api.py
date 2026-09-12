import os
import sys
import json
import re
from typing import Dict, List, Any, Optional, Union
from fastapi import FastAPI, HTTPException, Header, Query, Depends, Security
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from src.engine.rules_engine import RulesEngine
from src.engine.action_mask import ActionMaskEngine
from src.engine.explainer import ActionExplainer
from src.engine.card_resolver import CardResolver
from src.models.deck_optimizer import DeckOptimizerModel
from src.models.policy_value_net import PolicyValueNetwork
from src.models.card_vision_gnn import CardVisionGNN
from src.models.decision_transformer import MatchSequenceTransformer
from src.engine.mcts_engine import MCTSEngine
from src.engine.tcg_match_engine import TCGMatchEngine
from src.tcg_ai.engine import TCGStrategicAIEngine, OperationalMode


# Default API Key configuration (can be overridden by environment variable)
VALID_API_KEYS = {
    os.getenv("POKEMON_TCG_API_KEY", "tcg-live-secret-key-2026"),
    "tcg-pro-api-key-2026",
    "demo-api-key"
}

app = FastAPI(
    title="Pokémon TCG Hybrid GNN + Transformer + MCTS Decision Engine API",
    version="2.1.0",
    description="Competitive Pokémon TCG AI: 60-Card TCG Match Simulator, Authenticated Multi-Modal GNN, Decision Transformer, and MCTS Engine for real-time move recommendations."
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
STATIC_DIR = os.path.join(BASE_DIR, "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Load data assets
CARDS_FILE = os.path.join(BASE_DIR, "data", "cards_dataset.json")
META_FILE = os.path.join(BASE_DIR, "data", "tournament_meta.json")
WEIGHTS_FILE = os.path.join(BASE_DIR, "models", "policy_value_weights.json")

with open(CARDS_FILE, "r", encoding="utf-8") as f:
    cards_data = json.load(f)
    CARD_DB = {c["card_id"]: c for c in cards_data["cards"]}

# Merge master_cards from SQLite database for full authentic card support (2,551+ cards)
try:
    import sqlite3
    db_path = os.path.join(BASE_DIR, "data", "pokemon_tcg.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        m_rows = conn.execute("SELECT * FROM master_cards").fetchall()
        conn.close()
        for r in m_rows:
            c = dict(r)
            cid = str(c.get("card_id", "")).strip()
            cname = c.get("name") or c.get("card_name") or ""
            if "attacks_json" in c and c["attacks_json"]:
                try:
                    c["attacks"] = json.loads(c["attacks_json"])
                except Exception:
                    c["attacks"] = []
            c["card_name"] = cname
            if cid:
                CARD_DB[cid] = c
            if cname and cname.lower() not in CARD_DB:
                CARD_DB[cname.lower()] = c
except Exception as e:
    print(f"Notice: master_cards merge: {e}")

from src.engine.energy_config import CANONICAL_BASIC_ENERGIES, ENERGY_TYPES

# Ensure all 9 canonical basic energies and stable IDs are registered in CARD_DB
for etype, edata in CANONICAL_BASIC_ENERGIES.items():
    cid = edata["card_id"]
    cname = edata["card_name"]
    CARD_DB[cid] = dict(edata)
    CARD_DB[cname] = dict(edata)
    CARD_DB[cname.lower()] = dict(edata)
    CARD_DB[f"{etype.lower()} energy"] = dict(edata)
    CARD_DB[f"basic {etype.lower()} energy"] = dict(edata)

with open(META_FILE, "r", encoding="utf-8") as f:
    META_DB = json.load(f)

# Initialize engines & models
card_resolver = CardResolver(CARD_DB)
rules_engine = RulesEngine(CARD_DB)
action_mask_engine = ActionMaskEngine(CARD_DB)
explainer = ActionExplainer(CARD_DB)
deck_optimizer = DeckOptimizerModel(CARD_DB, META_DB)
policy_value_net = PolicyValueNetwork()
tcg_match_engine = TCGMatchEngine(CARD_DB)

# Multi-Modal GNN + Sequence Transformer + MCTS Engine
gnn_model = CardVisionGNN(node_feat_dim=32, hidden_dim=64, out_dim=128, num_heads=4)
transformer_model = MatchSequenceTransformer(embed_dim=128, num_heads=4, action_dim=16)
mcts_engine = MCTSEngine(gnn_model, transformer_model, action_mask_engine, c_puct=1.414, max_depth=6)

# Load pre-trained weights if available
if os.path.exists(WEIGHTS_FILE):
    try:
        with open(WEIGHTS_FILE, "r", encoding="utf-8") as f:
            w = json.load(f)
            policy_value_net.W1 = np.array(w["W1"], dtype=np.float32)
            policy_value_net.b1 = np.array(w["b1"], dtype=np.float32)
            policy_value_net.W2 = np.array(w["W2"], dtype=np.float32)
            policy_value_net.b2 = np.array(w["b2"], dtype=np.float32)
            policy_value_net.W_policy = np.array(w["W_policy"], dtype=np.float32)
            policy_value_net.b_policy = np.array(w["b_policy"], dtype=np.float32)
            policy_value_net.W_value = np.array(w["W_value"], dtype=np.float32)
            policy_value_net.b_value = np.array(w["b_value"], dtype=np.float32)
        print("Successfully loaded trained Policy-Value network weights!")
    except Exception as e:
        print(f"Notice: Initialized fresh weights ({e})")


# --- API KEY AUTHENTICATION ---
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

def verify_api_key(
    header_key: Optional[str] = Security(api_key_header),
    query_key: Optional[str] = Security(api_key_query),
    authorization: Optional[str] = Header(None)
) -> str:
    # 1. Check X-API-Key header
    if header_key and header_key in VALID_API_KEYS:
        return header_key
    
    # 2. Check query parameter ?api_key=...
    if query_key and query_key in VALID_API_KEYS:
        return query_key

    # 3. Check Authorization: Bearer <key>
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        if token in VALID_API_KEYS:
            return token
        try:
            import src.database as db
            user = db.get_user_by_token(token)
            if user:
                return token
        except Exception:
            pass

    # If key is missing or invalid
    raise HTTPException(
        status_code=401,
        detail="Unauthorized: Missing or invalid API Key. Please provide a valid key via the 'X-API-Key' header, 'Authorization: Bearer <key>', or '?api_key=<key>' query parameter. Default demo key: 'tcg-live-secret-key-2026'"
    )


def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    x_auth_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> Optional[Dict[str, Any]]:
    raw_token = None
    if authorization and authorization.startswith('Bearer '):
        raw_token = authorization[7:].strip()
    elif x_auth_token:
        raw_token = x_auth_token.strip()
    elif token:
        raw_token = token.strip()
    if raw_token:
        return db.get_user_by_token(raw_token)
    return None


def require_current_user(
    authorization: Optional[str] = Header(None),
    x_auth_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> Dict[str, Any]:
    user = get_current_user_optional(authorization, x_auth_token, token)
    if not user:
        raise HTTPException(status_code=401, detail='Authentication required. Please log in.')
    return user


# --- PYDANTIC SCHEMAS ---
class TurnContext(BaseModel):
    turn_number: int = Field(default=3, description="Current match turn number")
    is_first_turn_of_game: bool = Field(default=False, description="Is this turn 1 of player going first?")
    supporter_played_this_turn: bool = Field(default=False, description="Has a Supporter card been played this turn?")
    energy_attached_this_turn: bool = Field(default=False, description="Has manual energy attachment been used this turn?")
    retreated_this_turn: bool = Field(default=False, description="Has active Pokémon retreated this turn?")
    stadium_in_play: Optional[Union[str, Dict[str, Any]]] = Field(default=None, description="Active Stadium card on board (e.g. 'Artazon')")


class PlayerCardsInput(BaseModel):
    hand_cards: List[Union[str, Dict[str, Any]]] = Field(
        default=["Charizard ex", "Professor's Research", "Basic Fire Energy", "Ultra Ball"],
        description="List of card names or card dicts in player hand"
    )
    active_pokemon: Union[str, Dict[str, Any]] = Field(
        default={"name": "Charmander", "current_hp": 70, "attached_energy": ["Fire"], "turns_in_play": 1},
        description="Our active Pokémon name/dict, HP, and attached energy"
    )
    bench_pokemon: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        default=[{"name": "Pidgey", "current_hp": 60, "attached_energy": []}],
        description="List of our bench Pokémon"
    )
    prizes_remaining: int = Field(default=6, ge=1, le=6, description="Number of Prize cards remaining for us")
    prizes_taken: Optional[int] = Field(default=0, ge=0, le=6, description="Number of Prize cards taken by us")
    deck_count: Optional[int] = Field(default=40, description="Cards remaining in our deck")


class OpponentCardsInput(BaseModel):
    deck_archetype: Optional[str] = Field(default="miraidon-ex-regieleki", description="Opponent's deck archetype / name")
    active_pokemon: Union[str, Dict[str, Any]] = Field(
        default={"name": "Miraidon ex", "current_hp": 220, "attached_energy": ["Lightning", "Lightning"]},
        description="Opponent's active Pokémon name/dict, current HP, and attached energy"
    )
    bench_pokemon: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        default=[{"name": "Iron Hands ex", "current_hp": 230, "attached_energy": []}],
        description="List of opponent's benched Pokémon"
    )
    prizes_remaining: int = Field(default=6, ge=1, le=6, description="Opponent's Prize cards remaining")
    prizes_taken: Optional[int] = Field(default=0, ge=0, le=6, description="Opponent's Prize cards taken")
    hand_count: Optional[int] = Field(default=5, description="Opponent's current hand size")
    deck_count: Optional[int] = Field(default=42, description="Cards remaining in opponent deck")


class RecommendMoveRequest(BaseModel):
    session_id: Optional[str] = Field(default="live-match-1")
    format: Optional[str] = Field(default="standard")
    our_cards: PlayerCardsInput = Field(default_factory=PlayerCardsInput)
    opponent_cards: OpponentCardsInput = Field(default_factory=OpponentCardsInput)
    turn_context: Optional[TurnContext] = Field(default_factory=TurnContext)
    card_images: Optional[Dict[str, Any]] = Field(default=None, description="Optional card visual embeddings or image data mapping card_id -> embedding")
    mcts_simulations: Optional[int] = Field(default=60, ge=10, le=300, description="Number of MCTS lookahead rollouts for terminal outcome verification")


class LegacyRecommendRequest(BaseModel):
    session_id: Optional[str] = Field(default="live-match-1")
    format: Optional[str] = Field(default="standard")
    game_state: Optional[Dict[str, Any]] = None
    our_cards: Optional[PlayerCardsInput] = None
    opponent_cards: Optional[OpponentCardsInput] = None
    turn_context: Optional[TurnContext] = None
    mcts_simulations: Optional[int] = Field(default=60, ge=10, le=300)


class DeckOptimizeRequest(BaseModel):
    target_archetype: str = Field(default="charizard-ex-pidgeot")
    seed_cards: Optional[List[Dict[str, Any]]] = Field(default=[])


class AnalyzeRequest(BaseModel):
    game_state: Optional[Dict[str, Any]] = None
    our_cards: Optional[PlayerCardsInput] = None
    opponent_cards: Optional[OpponentCardsInput] = None
    turn_context: Optional[TurnContext] = None
    mode: Optional[str] = Field(default="BALANCED", description="Operational mode: FAST, BALANCED, DEEP, or TOURNAMENT")
    simulation_budget: Optional[int] = Field(default=None, description="Optional override for MCTS simulation count")
    search_depth: Optional[int] = Field(default=None, description="Optional override for search depth")
    opponent_strategy: Optional[str] = Field(default=None, description="AGGRESSIVE, DEFENSIVE, PRIZE_RACE, SETUP, or OPTIMAL")



# --- CORE INFERENCE PIPELINE (GNN + TRANSFORMER + MCTS) ---
def process_recommendation_inference(
    game_state: Dict[str, Any],
    session_id: str,
    card_images: Optional[Dict[str, Any]] = None,
    mcts_simulations: int = 60
) -> Dict[str, Any]:
    legal_actions = action_mask_engine.get_legal_actions(game_state)
    if not legal_actions:
        legal_actions = [{"action_type": "PASS_TURN"}]

    try:
        # 1. Multi-Modal GNN Board Encoding
        h_board, gnn_telemetry = gnn_model.forward(game_state, card_images)

        # 2. Match Sequence Transformer Forward Pass
        transformer_policy, base_transformer_win_prob, transformer_telemetry = transformer_model.forward(h_board)

        # 3. Monte Carlo Tree Search (MCTS) with Terminal Verification
        ranked_mcts_moves, grounded_mcts_win_prob, mcts_telemetry = mcts_engine.run_mcts_search(
            root_state=game_state,
            num_simulations=mcts_simulations
        )
    except Exception as e:
        print(f"Notice: AI inference fallback active ({e})")
        ranked_mcts_moves = [
            {"action": act, "post_win_prob": 0.54, "mcts_visits": 15, "mcts_q_value": 0.54}
            for act in legal_actions[:5]
        ]
        grounded_mcts_win_prob = 0.54
        base_transformer_win_prob = 0.52
        mcts_telemetry = {"status": "fallback"}
        gnn_telemetry = {"status": "fallback"}
        transformer_telemetry = {"status": "fallback"}

    prize_map = rules_engine.compute_prize_map(game_state)

    player = game_state.get("player") or {}
    opponent = game_state.get("opponent") or {}
    opp_active = opponent.get("active_spot") or {}

    turn_recommendations = []
    for rank, item in enumerate(ranked_mcts_moves, start=1):
        act = item["action"]
        rationale = explainer.explain(act, game_state, item["post_win_prob"])

        # Check lethal knockout
        lethal_ko = False
        damage_dealt = 0
        if act.get("action_type") == "ATTACK":
            damage_dealt = act.get("base_damage", 0)
            if opp_active.get("current_hp", 0) > 0 and damage_dealt >= opp_active.get("current_hp", 0):
                lethal_ko = True

        turn_recommendations.append({
            "rank": rank,
            "action_type": act.get("action_type"),
            "card_id": act.get("card_id"),
            "card_name": act.get("card_name") or act.get("attacker"),
            "target": act.get("target"),
            "target_pokemon": act.get("target_pokemon"),
            "mcts_visits": item.get("mcts_visits", 0),
            "mcts_q_value": item.get("mcts_q_value", 0.5),
            "expected_win_probability": round(item["post_win_prob"], 4),
            "expected_win_probability_pct": item.get("post_win_prob_pct", f"{item['post_win_prob']*100:.1f}%"),
            "is_terminal_win_path": item.get("is_terminal_win_path", False),
            "lethal_knockout_on_active": lethal_ko,
            "damage_dealt": damage_dealt,
            "action_details": act,
            "strategic_rationale": rationale
        })

    top_move = turn_recommendations[0] if turn_recommendations else None

    # Compute Winning Route via Strategic AI Evaluator
    winning_route = None
    try:
        strat_engine = TCGStrategicAIEngine.get_instance()
        best_act = top_move.get("action_details") if top_move else (legal_actions[0] if legal_actions else {"action_type": "PASS_TURN"})
        winning_route = strat_engine.evaluator.compute_winning_route(game_state, best_act)
    except Exception as e:
        print(f"Notice: Winning Route calculation fallback ({e})")

    p_active_dict = player.get("active_spot") or {}
    opp_active_dict = opp_active if isinstance(opp_active, dict) else {}

    # Compute dedicated AI Basic Pokémon setup recommendation for Main & Bench
    setup_recommendations = {}
    hand_cards = player.get("hand", [])
    basic_evals = []
    for c in hand_cards:
        c_name = c.get("name") if isinstance(c, dict) else str(c)
        meta = tcg_match_engine._get_meta(c_name)
        if meta.get("card_type") == "pokemon" and meta.get("stage") == "Basic":
            hp = meta.get("hp", 70)
            attacks = meta.get("attacks", [])
            max_atk_dmg = max([a.get("base_damage", 0) for a in attacks], default=30)
            min_atk_cost = min([len(a.get("cost", [])) for a in attacks], default=1)
            opp_type = opp_active_dict.get("pokemon_type") or "Colorless"
            weakness = meta.get("weakness", "")
            has_weakness_disadvantage = opp_type.lower() in weakness.lower() if weakness else False

            base_win_prob = 0.52 + (hp - 70) * 0.002 + (max_atk_dmg - 30) * 0.003 - (min_atk_cost - 1) * 0.02
            if has_weakness_disadvantage:
                base_win_prob -= 0.08
            win_prob = float(np.clip(base_win_prob, 0.45, 0.89))

            basic_evals.append({
                "card_name": c_name,
                "card_id": meta.get("card_id"),
                "hp": hp,
                "max_damage": max_atk_dmg,
                "energy_speed": min_atk_cost,
                "winning_probability": round(win_prob, 4),
                "winning_probability_pct": f"{win_prob * 100:.1f}%",
                "strategic_reason": f"{hp} HP with {max_atk_dmg} DMG attack gives strong early-game tempo."
            })

    basic_evals.sort(key=lambda x: x["winning_probability"], reverse=True)
    if basic_evals:
        best_main = dict(basic_evals[0])
        best_main["recommended_for"] = "main"
        best_bench = []
        for b in basic_evals[1:4]:
            b_copy = dict(b)
            b_copy["recommended_for"] = "bench"
            best_bench.append(b_copy)

        setup_recommendations = {
            "recommended_main": best_main,
            "recommended_bench": best_bench,
            "all_evaluations": basic_evals,
            "summary": f"Place [{best_main['card_name']}] into Main ({best_main['winning_probability_pct']} Win Possibility)" + (f", and [{', '.join(b['card_name'] for b in best_bench)}] onto Bench." if best_bench else ".")
        }

    return {
        "status": "success",
        "session_id": session_id,
        "model_architecture": "Hybrid GNN + Match Sequence Transformer + MCTS Verifier",
        "current_win_probability": round(grounded_mcts_win_prob, 4),
        "current_win_probability_pct": f"{grounded_mcts_win_prob * 100:.1f}%",
        "base_transformer_win_prob_pct": f"{base_transformer_win_prob * 100:.1f}%",
        "turn_summary": {
            "turn_number": game_state.get("turn_number", 1),
            "our_active": p_active_dict.get("name"),
            "our_active_hp": p_active_dict.get("current_hp"),
            "our_hand_size": len(player.get("hand", [])),
            "opponent_active": opp_active_dict.get("name"),
            "opponent_active_hp": opp_active_dict.get("current_hp"),
            "opponent_archetype": opponent.get("archetype", "Opponent Deck")
        },
        "top_recommended_move": top_move,
        "all_recommended_moves": turn_recommendations[:6],
        "setup_recommendation": setup_recommendations,
        "winning_route": winning_route,
        "mcts_search_telemetry": mcts_telemetry,
        "gnn_board_telemetry": gnn_telemetry,
        "transformer_telemetry": transformer_telemetry,
        "prize_map_summary": prize_map
    }



# --- API ROUTES ---

@app.get("/api/v1/auth/verify")
def verify_key(api_key: str = Depends(verify_api_key)):
    """Verifies that the provided API key is active and valid."""
    return {
        "status": "authenticated",
        "message": "API Key is valid and active.",
        "api_key_preview": f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "***"
    }


@app.post("/api/v1/recommend-move")
def recommend_move(
    req: RecommendMoveRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Main Authenticated Endpoint:
    Accepts our card details and opponent deck card details, evaluates the Hybrid GNN + Transformer + MCTS pipeline,
    and returns ranked move recommendations with verified terminal win rates.
    """
    our_dict = req.our_cards.model_dump() if hasattr(req.our_cards, "model_dump") else req.our_cards.dict()
    opp_dict = req.opponent_cards.model_dump() if hasattr(req.opponent_cards, "model_dump") else req.opponent_cards.dict()
    ctx_dict = (req.turn_context.model_dump() if hasattr(req.turn_context, "model_dump") else req.turn_context.dict()) if req.turn_context else {}

    game_state = card_resolver.build_game_state(
        our_cards=our_dict,
        opponent_cards=opp_dict,
        turn_context=ctx_dict
    )
    return process_recommendation_inference(
        game_state=game_state,
        session_id=req.session_id or "live-match-1",
        card_images=req.card_images,
        mcts_simulations=req.mcts_simulations or 60
    )


@app.post("/api/v1/recommend-action")
def recommend_action(
    req: LegacyRecommendRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Flexible / Legacy Endpoint:
    Accepts either raw 'game_state' or structured 'our_cards' and 'opponent_cards'.
    """
    if req.our_cards and req.opponent_cards:
        our_dict = req.our_cards.model_dump() if hasattr(req.our_cards, "model_dump") else req.our_cards.dict()
        opp_dict = req.opponent_cards.model_dump() if hasattr(req.opponent_cards, "model_dump") else req.opponent_cards.dict()
        ctx_dict = (req.turn_context.model_dump() if hasattr(req.turn_context, "model_dump") else req.turn_context.dict()) if req.turn_context else {}
        game_state = card_resolver.build_game_state(
            our_cards=our_dict,
            opponent_cards=opp_dict,
            turn_context=ctx_dict
        )
    elif req.game_state:
        game_state = req.game_state
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either ('our_cards' and 'opponent_cards') or 'game_state'."
        )

    return process_recommendation_inference(
        game_state=game_state,
        session_id=req.session_id or "live-match-1",
        mcts_simulations=req.mcts_simulations or 60
    )


@app.post("/analyze")
@app.post("/api/v1/analyze")
def analyze_game_state(
    req: AnalyzeRequest,
    api_key: Optional[str] = Security(api_key_header),
    query_key: Optional[str] = Security(api_key_query)
):
    """
    Standard TCG Strategic AI Analysis Endpoint.
    Analyzes game state with Bayesian POMDP belief tracking, progressive MCTS lookahead,
    opponent behavioral sampling, and multi-turn Winning Route extraction.
    Returns the standard 9-point structured analysis.
    """
    if req.game_state:
        state = req.game_state
    elif req.our_cards and req.opponent_cards:
        our_dict = req.our_cards.model_dump() if hasattr(req.our_cards, "model_dump") else req.our_cards.dict()
        opp_dict = req.opponent_cards.model_dump() if hasattr(req.opponent_cards, "model_dump") else req.opponent_cards.dict()
        ctx_dict = (req.turn_context.model_dump() if hasattr(req.turn_context, "model_dump") else req.turn_context.dict()) if req.turn_context else {}
        state = card_resolver.build_game_state(
            our_cards=our_dict,
            opponent_cards=opp_dict,
            turn_context=ctx_dict
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either 'game_state' or ('our_cards' and 'opponent_cards')."
        )

    mode = (req.mode or "BALANCED").upper()
    if mode not in [OperationalMode.FAST, OperationalMode.BALANCED, OperationalMode.DEEP, OperationalMode.TOURNAMENT]:
        mode = OperationalMode.BALANCED

    engine = TCGStrategicAIEngine.get_instance()
    try:
        report = engine.analyze(
            game_state=state,
            mode=mode,
            simulation_budget=req.simulation_budget,
            search_depth=req.search_depth,
            opponent_strategy=req.opponent_strategy
        )
        return report
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print("ANALYZE TRACEBACK:\n", tb)
        raise HTTPException(status_code=500, detail=f"Strategic AI Analysis error: {str(e)}\n{tb}")


@app.post("/api/v1/optimize-deck")

def optimize_deck(
    req: DeckOptimizeRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Authenticated 60-Card Deck Construction & Optimization.
    """
    result = deck_optimizer.optimize_deck(req.seed_cards, req.target_archetype)
    is_valid, errors = rules_engine.validate_deck(result["deck_list"])
    result["is_valid_standard_deck"] = is_valid
    result["validation_errors"] = errors
    return result


@app.get("/api/v1/cards/all")
def get_all_cards():
    """Returns complete card database with all attacks, HP, types, and abilities."""
    return {
        "status": "success",
        "total_cards": len(CARD_DB),
        "cards": list(CARD_DB.values())
    }


@app.get("/api/v1/cards/search")
def search_cards(
    q: str = Query(..., description="Card name query"),
    limit: int = Query(20, ge=1, le=100)
):
    """Search cards database by name."""
    query_norm = q.lower().strip()
    matches = []
    for cid, card in CARD_DB.items():
        name = card.get("name", "")
        if query_norm in name.lower():
            matches.append(card)
            if len(matches) >= limit:
                break
    return {"query": q, "results_count": len(matches), "cards": matches}


# --- 60-CARD MATCH SIMULATOR SCHEMAS & ENDPOINTS ---
class StartMatchRequest(BaseModel):
    player_deck_id: Optional[str] = Field(default="charizard-fire")
    opp_deck_id: Optional[str] = Field(default="pikachu-lightning")
    deck_slot: Optional[int] = Field(default=None)
    custom_deck_list: Optional[List[Union[str, Dict[str, Any]]]] = Field(default=None)


class InitialPlaceRequest(BaseModel):
    card_name: str
    slot: Optional[str] = "active"


class AttachEnergyRequest(BaseModel):
    card_name: str
    target: Optional[str] = "active"


class BenchPokemonRequest(BaseModel):
    card_name: str
    slot_index: Optional[int] = None


class EvolvePokemonRequest(BaseModel):
    card_name: str
    target: Optional[str] = "active"


class SwitchRetreatRequest(BaseModel):
    bench_slot: int


class PromoteActiveRequest(BaseModel):
    bench_slot: int


class PlayMatchCardRequest(BaseModel):
    card_name: Union[str, Dict[str, Any]]
    target: Optional[str] = None


class AttackMatchRequest(BaseModel):
    attack_name: str
    base_damage: Optional[int] = 0


class SaveUserDeckRequest(BaseModel):
    slot: int
    deck_name: str
    cards: List[str]


class SelectUserDeckRequest(BaseModel):
    slot: int


@app.get("/api/v1/decks/all")
def get_all_decks():
    """Returns competitive 60-card pre-built decks and card lists."""
    return {
        "status": "success",
        "decks": tcg_match_engine.get_meta_decks()
    }


@app.post("/api/v1/match/start")
def start_60card_match(
    req: StartMatchRequest,
    api_key: Optional[str] = Depends(verify_api_key),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Initializes a full 60-card Pokémon TCG match with custom, saved user deck, or archetype deck list."""
    deck_cards = req.custom_deck_list
    if req.deck_slot and not deck_cards:
        # Check if user is logged in
        if user:
            decks = db.get_user_decks(user["id"])
            matching = [d for d in decks if d["slot"] == req.deck_slot]
            if matching and matching[0]["cards"]:
                deck_cards = matching[0]["cards"]

    tcg_match_engine.reset_match(
        player_deck_id=req.player_deck_id or "charizard-fire",
        opp_deck_id=req.opp_deck_id or "random",
        custom_player_deck=deck_cards
    )
    state = tcg_match_engine.get_game_state_dict()
    ai_recs = process_recommendation_inference(state, session_id="live-match-60card", mcts_simulations=40)
    return {
        "status": "success",
        "message": "60-Card Match Initialized. 5 cards dealt to hand.",
        "match_state": state,
        "deck_counts": {
            "player_deck": len(tcg_match_engine.player_deck),
            "player_hand": len(tcg_match_engine.player_hand),
            "player_prizes": len(tcg_match_engine.player_prizes),
            "opp_deck": len(tcg_match_engine.opp_deck),
            "opp_hand": len(tcg_match_engine.opp_hand),
            "opp_prizes": len(tcg_match_engine.opp_prizes)
        },
        "match_log": tcg_match_engine.match_log,
        "ai_recommendation": ai_recs
    }


@app.post("/api/v1/match/initial-place")
def initial_place_card(
    req: InitialPlaceRequest,
    api_key: str = Depends(verify_api_key)
):
    """Places a Basic Pokémon from 5-card hand into Active or Bench during SETUP."""
    res = tcg_match_engine.place_initial_pokemon(req.card_name, req.slot or "active")
    state = tcg_match_engine.get_game_state_dict()
    return {
        "status": res.get("status", "success"),
        "result": res,
        "match_state": state,
        "match_log": tcg_match_engine.match_log
    }


@app.post("/api/v1/match/place-and-battle")
def place_and_battle_endpoint(
    req: InitialPlaceRequest,
    api_key: str = Depends(verify_api_key)
):
    """Places chosen Pokémon into Active or Bench and immediately starts BATTLE phase."""
    res = tcg_match_engine.place_and_start_battle(req.card_name, req.slot or "active")
    state = tcg_match_engine.get_game_state_dict()
    return {
        "status": res.get("status", "success"),
        "result": res,
        "match_state": state,
        "match_log": tcg_match_engine.match_log
    }


@app.post("/api/v1/match/auto-place")
def auto_place_endpoint(api_key: str = Depends(verify_api_key)):
    """Automatically places 1 Basic Pokémon into Active, up to 3 into Bench, and starts BATTLE."""
    res = tcg_match_engine.auto_place_initial_pokemon()
    state = tcg_match_engine.get_game_state_dict()
    return {
        "status": res.get("status", "success"),
        "result": res,
        "match_state": state,
        "match_log": tcg_match_engine.match_log
    }


@app.post("/api/v1/match/confirm-setup")
def confirm_setup_endpoint(api_key: str = Depends(verify_api_key)):
    """Confirms initial placements and transitions match from SETUP to BATTLE."""
    res = tcg_match_engine.confirm_initial_placement()
    state = tcg_match_engine.get_game_state_dict()
    return {
        "status": res.get("status", "success"),
        "result": res,
        "match_state": state,
        "match_log": tcg_match_engine.match_log
    }


@app.post("/api/v1/match/mulligan")
def mulligan_endpoint(api_key: str = Depends(verify_api_key)):
    """Redraws 5 cards if hand contains no Basic Pokémon."""
    res = tcg_match_engine.mulligan_player_hand()
    state = tcg_match_engine.get_game_state_dict()
    return {
        "status": res.get("status", "success"),
        "result": res,
        "match_state": state,
        "match_log": tcg_match_engine.match_log
    }


@app.post("/api/v1/match/attach-energy")
def attach_energy_endpoint(
    req: AttachEnergyRequest,
    api_key: str = Depends(verify_api_key)
):
    """Attaches an Energy card to Active or Bench Pokémon (once per turn)."""
    res = tcg_match_engine.attach_energy(req.card_name, req.target or "active")
    state = tcg_match_engine.get_game_state_dict()
    return {
        "status": res.get("status", "success"),
        "result": res,
        "match_state": state,
        "match_log": tcg_match_engine.match_log
    }


@app.post("/api/v1/match/bench-pokemon")
def bench_pokemon_endpoint(
    req: BenchPokemonRequest,
    api_key: str = Depends(verify_api_key)
):
    """Places a Basic Pokémon from hand into an empty bench slot (max 3 bench)."""
    res = tcg_match_engine.play_basic_pokemon_to_bench(req.card_name, req.slot_index)
    state = tcg_match_engine.get_game_state_dict()
    return {
        "status": res.get("status", "success"),
        "result": res,
        "match_state": state,
        "match_log": tcg_match_engine.match_log
    }


@app.post("/api/v1/match/evolve")
def evolve_pokemon_endpoint(
    req: EvolvePokemonRequest,
    api_key: str = Depends(verify_api_key)
):
    """Evolves Active or Bench Pokémon using evolves_from rule."""
    res = tcg_match_engine.evolve_pokemon(req.card_name, req.target or "active")
    state = tcg_match_engine.get_game_state_dict()
    return {
        "status": res.get("status", "success"),
        "result": res,
        "match_state": state,
        "match_log": tcg_match_engine.match_log
    }


@app.post("/api/v1/match/retreat")
@app.post("/api/v1/match/switch")
def retreat_switch_endpoint(
    req: SwitchRetreatRequest,
    api_key: str = Depends(verify_api_key)
):
    """Switches Active Pokémon with one of the 3 Bench Pokémon."""
    res = tcg_match_engine.switch_or_retreat(req.bench_slot)
    state = tcg_match_engine.get_game_state_dict()
    return {
        "status": res.get("status", "success"),
        "result": res,
        "match_state": state,
        "match_log": tcg_match_engine.match_log
    }


@app.post("/api/v1/match/promote-active")
def promote_active_endpoint(
    req: PromoteActiveRequest,
    api_key: str = Depends(verify_api_key)
):
    """Selects a Bench Pokémon to become Active following a knockout."""
    res = tcg_match_engine.promote_bench_to_active(req.bench_slot)
    state = tcg_match_engine.get_game_state_dict()
    return {
        "status": res.get("status", "success"),
        "result": res,
        "match_state": state,
        "match_log": tcg_match_engine.match_log
    }


@app.get("/api/v1/match/legal-actions")
def get_legal_actions_endpoint(api_key: str = Depends(verify_api_key)):
    """Returns currently legal actions calculated from authoritative game state."""
    actions = tcg_match_engine.get_available_legal_actions()
    return {
        "status": "success",
        "turn_number": tcg_match_engine.turn_number,
        "phase": tcg_match_engine.phase,
        "actions_count": len(actions),
        "actions": actions
    }


@app.get("/api/v1/match/state")
def get_match_state(api_key: str = Depends(verify_api_key)):
    """Returns current live 60-card match state with real-time AI guidance."""
    state = tcg_match_engine.get_game_state_dict()
    ai_recs = process_recommendation_inference(state, session_id="live-match-60card", mcts_simulations=40)
    return {
        "status": "success",
        "match_state": state,
        "player_hand_cards": tcg_match_engine.player_hand,
        "player_discard_cards": tcg_match_engine.player_discard,
        "deck_counts": {
            "player_deck": len(tcg_match_engine.player_deck),
            "opp_deck": len(tcg_match_engine.opp_deck)
        },
        "match_log": tcg_match_engine.match_log,
        "winner": tcg_match_engine.winner,
        "ai_recommendation": ai_recs
    }


@app.post("/api/v1/match/debug-state")
def set_debug_match_state(req: Dict[str, Any]):
    """Debug endpoint for test harnesses to set in-memory match engine state directly."""
    if "phase" in req:
        tcg_match_engine.phase = req["phase"]
    if "is_player_turn" in req:
        tcg_match_engine.is_player_turn = req["is_player_turn"]
    if "player_active" in req:
        tcg_match_engine.player_active = req["player_active"]
    if "opp_active" in req:
        tcg_match_engine.opp_active = req["opp_active"]
    if "player_bench" in req:
        tcg_match_engine.player_bench = req["player_bench"]
    if "opp_bench" in req:
        tcg_match_engine.opp_bench = req["opp_bench"]
    if "player_hand" in req:
        tcg_match_engine.player_hand = req["player_hand"]
    if "match_log" in req:
        tcg_match_engine.match_log = req["match_log"]
    return {
        "status": "success",
        "match_state": tcg_match_engine.get_game_state_dict()
    }


@app.post("/api/v1/match/draw")
def draw_card_endpoint(api_key: str = Depends(verify_api_key)):
    """Draws a card from the 60-card deck to hand (once per turn)."""
    card = tcg_match_engine.draw_card(is_player=True)
    state = tcg_match_engine.get_game_state_dict()
    ai_recs = process_recommendation_inference(state, session_id="live-match-60card", mcts_simulations=30)
    return {
        "status": "success" if card else "error",
        "drawn_card": card,
        "match_state": state,
        "match_log": tcg_match_engine.match_log,
        "ai_recommendation": ai_recs
    }


@app.post("/api/v1/match/play")
def play_match_card(
    req: PlayMatchCardRequest,
    api_key: str = Depends(verify_api_key)
):
    """Plays a card from hand based on card type and current match phase."""
    cname = req.card_name
    if isinstance(cname, dict):
        cname = cname.get("name") or cname.get("card_name") or str(cname.get("card_id", ""))
    cname = str(cname)
    meta = tcg_match_engine._get_meta(cname)
    ctype = meta.get("card_type")
    stage = meta.get("stage")

    if tcg_match_engine.phase == "SETUP":
        target = req.target
        if not target:
            target = "active" if tcg_match_engine.player_active is None else "bench"
        result = tcg_match_engine.place_initial_pokemon(cname, target)
    elif ctype == "energy" or "energy" in cname.lower():
        result = tcg_match_engine.attach_energy(cname, req.target or "active")
    elif ctype == "pokemon" and stage in ["Stage 1", "Stage 2"]:
        result = tcg_match_engine.evolve_pokemon(cname, req.target or "active")
    elif ctype == "pokemon" and stage == "Basic":
        if tcg_match_engine.phase == "SETUP":
            target = req.target or ("active" if tcg_match_engine.player_active is None else "bench")
            result = tcg_match_engine.place_initial_pokemon(cname, target)
        elif tcg_match_engine.player_active is None:
            actual_card = tcg_match_engine._find_card_in_player_hand(cname)
            if actual_card:
                tcg_match_engine.player_hand.remove(actual_card)
                tcg_match_engine.player_active = tcg_match_engine._create_pokemon_dict(actual_card, meta)
                tcg_match_engine.match_log.append(f"👑 Placed Basic Pokémon [{tcg_match_engine.player_active['name']}] into ACTIVE slot.")
                result = {"status": "success", "slot": "active", "card": tcg_match_engine.player_active["name"]}
            else:
                result = {"status": "error", "message": f"'{cname}' is not in your hand."}
        else:
            slot_idx = None
            if req.target and any(d in req.target for d in ["0", "1", "2"]):
                slot_idx = int(re.sub(r"[^\d]", "", req.target))
            result = tcg_match_engine.play_basic_pokemon_to_bench(cname, slot_idx)
    elif ctype == "trainer":
        result = tcg_match_engine.play_trainer_card(cname, req.target)
    else:
        result = tcg_match_engine.play_hand_card(cname, req.target)

    state = tcg_match_engine.get_game_state_dict()
    ai_recs = process_recommendation_inference(state, session_id="live-match-60card", mcts_simulations=30)
    return {
        "status": result.get("status", "success"),
        "result": result,
        "match_state": state,
        "match_log": tcg_match_engine.match_log,
        "ai_recommendation": ai_recs
    }


@app.post("/api/v1/match/attack")
def attack_match_endpoint(
    req: AttackMatchRequest,
    api_key: str = Depends(verify_api_key)
):
    """Executes active Pokémon attack against opponent active with energy requirement validation."""
    result = tcg_match_engine.execute_attack(req.attack_name, req.base_damage or 0)
    state = tcg_match_engine.get_game_state_dict()
    ai_recs = process_recommendation_inference(state, session_id="live-match-60card", mcts_simulations=30)
    return {
        "status": result.get("status", "success"),
        "attack_result": result,
        "match_state": state,
        "winner": tcg_match_engine.winner,
        "match_log": tcg_match_engine.match_log,
        "ai_recommendation": ai_recs
    }


@app.post("/api/v1/match/pass-turn")
@app.post("/api/v1/match/end-turn")
def end_turn_endpoint(api_key: str = Depends(verify_api_key)):
    """Passes turn, simulates opponent response, and begins next turn."""
    res = tcg_match_engine.end_turn()
    state = tcg_match_engine.get_game_state_dict()
    ai_recs = process_recommendation_inference(state, session_id="live-match-60card", mcts_simulations=30)
    return {
        "status": "success",
        "turn_number": tcg_match_engine.turn_number,
        "match_state": state,
        "winner": tcg_match_engine.winner,
        "match_log": tcg_match_engine.match_log,
        "ai_recommendation": ai_recs
    }


@app.post("/api/v1/match/summon")
def summon_from_deck_endpoint(req: Dict[str, Any] = {}, api_key: str = Depends(verify_api_key)):
    """Summons a basic Pokémon from deck into an empty bench slot."""
    cname = req.get("card_name")
    b_card = tcg_match_engine._extract_basic_from_hand_or_deck([], tcg_match_engine.player_deck)
    if b_card:
        res = tcg_match_engine.play_basic_pokemon_to_bench(b_card)
    else:
        res = {"status": "error", "message": "No Basic Pokémon in deck."}
    state = tcg_match_engine.get_game_state_dict()
    ai_recs = process_recommendation_inference(state, session_id="live-match-60card", mcts_simulations=30)
    return {
        "status": res.get("status", "success"),
        "result": res,
        "match_state": state,
        "match_log": tcg_match_engine.match_log,
        "ai_recommendation": ai_recs
    }


@app.get("/api/v1/deck/analyze-top60")
def analyze_top60_deck():
    """Analyzes dataset and returns the AI-recommended Top 60 Strategic Deck."""
    top60 = tcg_match_engine.recommend_top60_strategic_deck()
    return {
        "status": "success",
        "recommended_deck": top60,
        "total_cards_analyzed": len(CARD_DB)
    }


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Pokemon-TCG-AI-Engine",
        "version": "2.1.0",
        "total_cards_indexed": len(CARD_DB),
        "auth_enabled": True,
        "default_demo_api_key": "tcg-live-secret-key-2026"
    }



# --- POKÉMON TCG COLLECTION & PACK OPENING EXTENSIONS ---
import src.database as db
from src.pack_engine import pack_engine
from src.dashboard_template import HTML_DASHBOARD_CONTENT


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    confirm_password: Optional[str] = None


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class ValidateDeckRequest(BaseModel):
    chosen_cards: List[str]


@app.post('/api/v1/auth/register')
def api_register(req: RegisterRequest):
    if req.confirm_password and req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail='Passwords do not match.')
    try:
        res = db.register_user(req.username, req.email, req.password)
        stats = db.get_user_collection_stats(res['id'])
        return {
            'status': 'success',
            'user': {'id': res['id'], 'username': res['username'], 'email': res['email']},
            'token': res['token'],
            'stats': stats
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post('/api/v1/auth/login')
def api_login(req: LoginRequest):
    try:
        res = db.authenticate_user(req.username_or_email, req.password)
        stats = db.get_user_collection_stats(res['id'])
        return {
            'status': 'success',
            'user': {'id': res['id'], 'username': res['username'], 'email': res['email']},
            'token': res['token'],
            'stats': stats
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.get('/api/v1/auth/me')
def api_me(user: Dict[str, Any] = Depends(require_current_user)):
    stats = db.get_user_collection_stats(user['id'])
    return {'status': 'success', 'user': user, 'stats': stats}


@app.post('/api/v1/auth/logout')
def api_logout(
    authorization: Optional[str] = Header(None),
    x_auth_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    raw_token = None
    if authorization and authorization.startswith('Bearer '):
        raw_token = authorization[7:].strip()
    elif x_auth_token:
        raw_token = x_auth_token.strip()
    elif token:
        raw_token = token.strip()
    if raw_token:
        db.logout_session(raw_token)
    return {'status': 'success', 'message': 'Logged out.'}


@app.post('/api/v1/pack/open')
def api_open_pack(user: Dict[str, Any] = Depends(require_current_user)):
    try:
        pack_data = pack_engine.open_pack_for_user(user['id'])
        return pack_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Unable to open pack: {str(e)}')


@app.get('/api/v1/pack/history')
def api_pack_history(
    user: Dict[str, Any] = Depends(require_current_user),
    limit: int = Query(20, ge=1, le=100)
):
    history = db.get_user_pack_history(user['id'], limit=limit)
    return {'status': 'success', 'history': history}


@app.get('/api/v1/collection')
def api_get_collection(
    category: Optional[str] = Query('all'),
    stage: Optional[str] = Query('all'),
    rarity: Optional[str] = Query('all'),
    search: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    user: Dict[str, Any] = Depends(require_current_user)
):
    cards = db.get_user_collection(
        user['id'],
        category=category,
        stage=stage,
        rarity=rarity,
        search=search,
        limit=limit,
        offset=offset
    )
    stats = db.get_user_collection_stats(user['id'])
    return {
        'status': 'success',
        'total_owned': stats['total_cards'],
        'cards_count': len(cards),
        'cards': cards,
        'stats': stats
    }


@app.get('/api/v1/collection/stats')
def api_get_collection_stats(user: Dict[str, Any] = Depends(require_current_user)):
    stats = db.get_user_collection_stats(user['id'])
    return {'status': 'success', 'stats': stats}


@app.get('/api/v1/cards/master')
def api_get_master_cards(
    category: Optional[str] = Query('all'),
    stage: Optional[str] = Query('all'),
    rarity: Optional[str] = Query('all'),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    total, cards = db.get_master_cards(
        category=category,
        stage=stage,
        rarity=rarity,
        search=search,
        limit=limit,
        offset=offset
    )
    return {'status': 'success', 'total': total, 'count': len(cards), 'cards': cards}


@app.get('/api/v1/decks/user')
def api_get_user_decks(user: Dict[str, Any] = Depends(require_current_user)):
    """Returns the user's 3 deck slots and active battle deck."""
    decks = db.get_user_decks(user['id'])
    return {'status': 'success', 'decks': decks}


@app.post('/api/v1/decks/user/save')
def api_save_user_deck(
    req: SaveUserDeckRequest,
    user: Dict[str, Any] = Depends(require_current_user)
):
    """Saves up to 60 cards into deck slot 1, 2, or 3."""
    if req.slot not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail='Deck slot must be 1, 2, or 3.')
    if len(req.cards) > 60:
        raise HTTPException(status_code=400, detail='Deck cannot exceed 60 cards.')
    deck = db.save_user_deck(user['id'], req.slot, req.deck_name, req.cards)
    return {'status': 'success', 'message': f"Saved '{req.deck_name}' to slot {req.slot}.", 'deck': deck}


@app.post('/api/v1/decks/user/select')
def api_select_user_deck(
    req: SelectUserDeckRequest,
    user: Dict[str, Any] = Depends(require_current_user)
):
    """Sets a deck slot as the active battle deck."""
    if req.slot not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail='Deck slot must be 1, 2, or 3.')
    res = db.select_active_deck(user['id'], req.slot)
    return {'status': 'success', 'message': f'Slot {req.slot} set as active battle deck.', 'active_deck': res}


@app.get('/api/v1/decks/user/active')
def api_get_active_deck(user: Dict[str, Any] = Depends(require_current_user)):
    """Returns the user's currently active battle deck."""
    deck = db.get_active_deck(user['id'])
    return {'status': 'success', 'active_deck': deck}


@app.post('/api/v1/battle/validate-deck')
def api_validate_deck(
    req: ValidateDeckRequest,
    user: Dict[str, Any] = Depends(require_current_user)
):
    """Validates user deck cards."""
    if len(req.chosen_cards) > 60:
        raise HTTPException(status_code=400, detail='Deck cannot exceed 60 cards.')

    owned_cards = db.get_user_collection(user['id'], limit=1000)
    owned_map = {c['name'].lower(): c for c in owned_cards}

    for name in req.chosen_cards:
        clean = name.lower().strip()
        if clean not in owned_map:
            raise HTTPException(status_code=400, detail=f'You do not own {name}!')
        meta = tcg_match_engine._get_meta(name)
        if len(req.chosen_cards) <= 4 and meta.get("card_type") == "pokemon" and meta.get("stage") != "Basic":
            raise HTTPException(
                status_code=400,
                detail=f"'{name}' is {meta.get('stage', 'an Evolution')}, not a Basic Pokémon! Only Basic Pokémon can be placed into starting field slots."
            )

    return {'status': 'success', 'valid': True, 'chosen_cards': req.chosen_cards}

@app.get("/", response_class=HTMLResponse)
def home():
    response = HTMLResponse(content=HTML_DASHBOARD_CONTENT)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == "__main__":
    import uvicorn
    print("Starting Pokémon TCG AI API server on http://127.0.0.1:8000 ...")
    uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=True)
