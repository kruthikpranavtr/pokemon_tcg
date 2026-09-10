import os
import sys
import json
from typing import Dict, List, Any, Optional, Union
from fastapi import FastAPI, HTTPException, Header, Query, Depends, Security
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery
from fastapi.responses import HTMLResponse
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

# Load data assets
CARDS_FILE = os.path.join(BASE_DIR, "data", "cards_dataset.json")
META_FILE = os.path.join(BASE_DIR, "data", "tournament_meta.json")
WEIGHTS_FILE = os.path.join(BASE_DIR, "models", "policy_value_weights.json")

with open(CARDS_FILE, "r", encoding="utf-8") as f:
    cards_data = json.load(f)
    CARD_DB = {c["card_id"]: c for c in cards_data["cards"]}

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

    # If key is missing or invalid
    raise HTTPException(
        status_code=401,
        detail="Unauthorized: Missing or invalid API Key. Please provide a valid key via the 'X-API-Key' header, 'Authorization: Bearer <key>', or '?api_key=<key>' query parameter. Default demo key: 'tcg-live-secret-key-2026'"
    )


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

    player = game_state.get("player", {})
    opponent = game_state.get("opponent", {})
    opp_active = opponent.get("active_spot", {})

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

    return {
        "status": "success",
        "session_id": session_id,
        "model_architecture": "Hybrid GNN + Match Sequence Transformer + MCTS Verifier",
        "current_win_probability": round(grounded_mcts_win_prob, 4),
        "current_win_probability_pct": f"{grounded_mcts_win_prob * 100:.1f}%",
        "base_transformer_win_prob_pct": f"{base_transformer_win_prob * 100:.1f}%",
        "turn_summary": {
            "turn_number": game_state.get("turn_number", 1),
            "our_active": player.get("active_spot", {}).get("name"),
            "our_active_hp": player.get("active_spot", {}).get("current_hp"),
            "our_hand_size": len(player.get("hand", [])),
            "opponent_active": opp_active.get("name"),
            "opponent_active_hp": opp_active.get("current_hp"),
            "opponent_archetype": opponent.get("archetype", "Opponent Deck")
        },
        "top_recommended_move": top_move,
        "all_recommended_moves": turn_recommendations[:6],
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
    player_deck_id: Optional[str] = Field(default="charizard-ex-pidgeot")
    opp_deck_id: Optional[str] = Field(default="miraidon-ex-regieleki")
    custom_deck_list: Optional[List[Union[str, Dict[str, Any]]]] = Field(default=None)


class PlayMatchCardRequest(BaseModel):
    card_name: str
    target: Optional[str] = None


class AttackMatchRequest(BaseModel):
    attack_name: str
    base_damage: Optional[int] = 0


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
    api_key: str = Depends(verify_api_key)
):
    """Initializes a full 60-card Pokémon TCG match with custom or archetype deck list."""
    tcg_match_engine.reset_match(
        player_deck_id=req.player_deck_id or "charizard-ex-pidgeot",
        opp_deck_id=req.opp_deck_id or "miraidon-ex-regieleki",
        custom_player_deck=req.custom_deck_list
    )
    state = tcg_match_engine.get_game_state_dict()
    ai_recs = process_recommendation_inference(state, session_id="live-match-60card", mcts_simulations=40)
    return {
        "status": "success",
        "message": "60-Card Match Initialized.",
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


@app.post("/api/v1/match/draw")
def draw_card_endpoint(api_key: str = Depends(verify_api_key)):
    """Draws a card from the 60-card deck to hand."""
    card = tcg_match_engine.draw_card(is_player=True)
    state = tcg_match_engine.get_game_state_dict()
    ai_recs = process_recommendation_inference(state, session_id="live-match-60card", mcts_simulations=30)
    return {
        "status": "success",
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
    """Plays a card from hand (bench, evolve, energy attachment, supporter, item)."""
    result = tcg_match_engine.play_hand_card(req.card_name, req.target)
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
    """Executes active Pokémon attack against opponent active with damage & prize resolutions."""
    result = tcg_match_engine.execute_attack(req.attack_name, req.base_damage or 0)
    state = tcg_match_engine.get_game_state_dict()
    ai_recs = process_recommendation_inference(state, session_id="live-match-60card", mcts_simulations=30)
    return {
        "status": "success",
        "attack_result": result,
        "match_state": state,
        "winner": tcg_match_engine.winner,
        "match_log": tcg_match_engine.match_log,
        "ai_recommendation": ai_recs
    }


@app.post("/api/v1/match/end-turn")
def end_turn_endpoint(api_key: str = Depends(verify_api_key)):
    """Passes turn, simulates opponent response, and draws for next turn."""
    tcg_match_engine.end_turn()
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
    res = tcg_match_engine.summon_pokemon_from_deck(is_player=True, card_name=cname)
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


@app.post('/api/v1/battle/validate-deck')
def api_validate_deck(
    req: ValidateDeckRequest,
    user: Dict[str, Any] = Depends(require_current_user)
):
    if len(req.chosen_cards) != 4:
        raise HTTPException(status_code=400, detail='Must provide exactly 4 card names.')

    owned_cards = db.get_user_collection(user['id'], limit=1000)
    owned_map = {c['name'].lower(): c for c in owned_cards}

    for name in req.chosen_cards:
        clean = name.lower().strip()
        if clean not in owned_map:
            raise HTTPException(status_code=400, detail=f'You do not own {name}!')
        card = owned_map[clean]
        if card.get('stage') not in [None, 'Basic']:
            raise HTTPException(status_code=400, detail=f'{name} is not a Basic Pokémon!')

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
