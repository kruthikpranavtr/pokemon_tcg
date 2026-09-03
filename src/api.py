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


# --- INTERACTIVE DASHBOARD HTML ---
HTML_DASHBOARD_CONTENT = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>POKÉMON TCG // 60-CARD QUANTUM MATCH & DECISION ENGINE</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-void: #03050c;
                --surface-cyber: rgba(8, 14, 28, 0.88);
                --surface-glass: rgba(13, 22, 44, 0.75);
                --neon-cyan: #00f3ff;
                --neon-cyan-glow: 0 0 15px rgba(0, 243, 255, 0.6), 0 0 30px rgba(0, 243, 255, 0.25);
                --neon-green: #00ff88;
                --neon-green-glow: 0 0 15px rgba(0, 255, 136, 0.6), 0 0 30px rgba(0, 255, 136, 0.25);
                --neon-magenta: #ff007f;
                --neon-magenta-glow: 0 0 15px rgba(255, 0, 127, 0.6), 0 0 30px rgba(255, 0, 127, 0.25);
                --neon-purple: #b026ff;
                --neon-amber: #ffaa00;
                --card-gold: #fbbf24;
                --text-glow: #e2f3fe;
                --text-dim: #738aa6;
                --font-orbitron: 'Orbitron', monospace;
                --font-mono: 'JetBrains Mono', monospace;
                --font-hud: 'Rajdhani', sans-serif;
            }

            * { box-sizing: border-box; margin: 0; padding: 0; }

            /* ESPORTS TCG ARENA THEME */
            body {
                background: radial-gradient(circle at 50% 10%, #0c1427 0%, #060b17 60%, #020409 100%);
                color: #e2f3fe;
                font-family: var(--font-hud);
                min-height: 100vh;
                overflow-x: hidden;
                position: relative;
            }

            .scanlines {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.15) 50%);
                background-size: 100% 4px;
                z-index: 1;
                pointer-events: none;
                opacity: 0.3;
            }

            .cyber-container {
                max-width: 1480px;
                margin: 0 auto;
                padding: 20px 24px 100px 24px;
                position: relative;
                z-index: 2;
            }

            header {
                text-align: center;
                margin-bottom: 20px;
                position: relative;
            }

            .cyber-badge {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                font-family: var(--font-orbitron);
                font-size: 0.75rem;
                font-weight: 800;
                letter-spacing: 2px;
                color: var(--neon-cyan);
                background: rgba(0, 243, 255, 0.08);
                border: 1px solid rgba(0, 243, 255, 0.4);
                padding: 6px 18px;
                border-radius: 30px;
                box-shadow: 0 0 15px rgba(0, 243, 255, 0.2);
                margin-bottom: 10px;
                text-transform: uppercase;
            }

            .cyber-glitch-title {
                font-family: var(--font-orbitron);
                font-size: 2.2rem;
                font-weight: 900;
                color: #fff;
                letter-spacing: 3px;
                text-transform: uppercase;
                text-shadow: 0 0 20px rgba(0, 243, 255, 0.7), 0 0 40px rgba(0, 243, 255, 0.3);
                margin-bottom: 8px;
            }

            /* TOP TAB NAVIGATION BAR */
            .tab-nav-bar {
                display: flex;
                gap: 16px;
                justify-content: center;
                align-items: center;
                margin: 20px 0 28px 0;
                background: rgba(13, 22, 44, 0.85);
                border: 1px solid rgba(0, 243, 255, 0.35);
                border-radius: 14px;
                padding: 10px 16px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8), inset 0 0 20px rgba(0, 243, 255, 0.05);
                backdrop-filter: blur(16px);
                flex-wrap: wrap;
            }
            .tab-btn {
                background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(8, 14, 28, 0.95) 100%);
                border: 1px solid rgba(0, 243, 255, 0.25);
                color: var(--text-dim);
                font-family: var(--font-orbitron);
                font-size: 0.88rem;
                font-weight: 800;
                padding: 12px 24px;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                display: flex;
                align-items: center;
                gap: 8px;
                letter-spacing: 0.5px;
            }
            .tab-btn:hover {
                color: #fff;
                border-color: var(--neon-cyan);
                background: linear-gradient(135deg, rgba(0, 243, 255, 0.2) 0%, rgba(15, 23, 42, 0.95) 100%);
                box-shadow: 0 0 20px rgba(0, 243, 255, 0.4);
                transform: translateY(-2px);
            }
            .tab-btn.active {
                background: linear-gradient(135deg, rgba(0, 243, 255, 0.3) 0%, rgba(16, 185, 129, 0.3) 100%);
                border: 2px solid var(--neon-cyan);
                color: #fff;
                box-shadow: 0 0 25px rgba(0, 243, 255, 0.6), inset 0 0 15px rgba(0, 243, 255, 0.2);
                text-shadow: 0 0 10px var(--neon-cyan);
                transform: scale(1.02);
            }

            .btn-cyber-sm {
                background: rgba(0, 243, 255, 0.15);
                border: 1px solid var(--neon-cyan);
                color: var(--neon-cyan);
                font-family: var(--font-orbitron);
                font-size: 0.75rem;
                font-weight: 800;
                padding: 8px 14px;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s;
            }
            .btn-cyber-sm:hover {
                background: var(--neon-cyan);
                color: #000;
                box-shadow: var(--neon-cyan-glow);
            }

            .btn-exec-ai {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                border: 1px solid #34d399;
                color: #fff;
                font-family: var(--font-orbitron);
                font-size: 0.85rem;
                font-weight: 900;
                padding: 10px 18px;
                border-radius: 6px;
                cursor: pointer;
                box-shadow: 0 0 15px rgba(16, 185, 129, 0.5);
                transition: all 0.2s;
                letter-spacing: 0.5px;
            }
            .btn-exec-ai:hover {
                transform: translateY(-2px);
                box-shadow: 0 0 25px rgba(16, 185, 129, 0.8);
            }

            .neon-input-key {
                background: rgba(2, 6, 23, 0.9);
                border: 1px solid var(--neon-cyan);
                color: #fff;
                font-family: var(--font-mono);
                font-size: 0.82rem;
                padding: 8px 12px;
                border-radius: 6px;
                outline: none;
            }

            .deck-builder-panel {
                background: rgba(15, 23, 42, 0.92);
                border: 2px solid var(--neon-purple);
                border-radius: 14px;
                padding: 24px;
                box-shadow: 0 12px 35px rgba(0, 0, 0, 0.85), 0 0 20px rgba(176, 38, 255, 0.2);
                backdrop-filter: blur(16px);
                margin-bottom: 90px;
            }
            .deck-cards-list {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
                gap: 12px;
                max-height: 520px;
                overflow-y: auto;
                padding-right: 6px;
            }
            .deck-card-item {
                background: rgba(2, 6, 23, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 10px 14px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                transition: all 0.2s;
            }
            .deck-card-item:hover {
                border-color: var(--neon-purple);
                box-shadow: 0 0 12px rgba(176, 38, 255, 0.3);
            }
            .column-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 14px;
                flex-wrap: wrap;
                gap: 10px;
            }
            .col-title {
                font-family: var(--font-orbitron);
                font-size: 1.25rem;
                font-weight: 900;
                letter-spacing: 1px;
            }

            /* 3-COLUMN COMMAND CENTER LAYOUT */
            .app-3col-layout {
                display: grid;
                grid-template-columns: 310px 1fr 330px;
                gap: 18px;
                align-items: start;
                margin-bottom: 80px;
            }
            @media (max-width: 1200px) {
                .app-3col-layout { grid-template-columns: 1fr; }
            }

            .side-column-panel {
                background: rgba(15, 23, 42, 0.95);
                border: 1px solid rgba(0, 243, 255, 0.3);
                border-radius: 12px;
                padding: 18px;
                backdrop-filter: blur(16px);
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
                display: flex;
                flex-direction: column;
                gap: 14px;
            }

            .panel-header-title {
                font-family: var(--font-orbitron);
                font-size: 0.92rem;
                font-weight: 800;
                color: var(--neon-cyan);
                border-bottom: 1px solid rgba(0, 243, 255, 0.2);
                padding-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .win-rate-display-box {
                background: linear-gradient(135deg, rgba(0, 243, 255, 0.15) 0%, rgba(16, 185, 129, 0.15) 100%);
                border: 1px solid var(--neon-cyan);
                border-radius: 8px;
                padding: 14px;
                text-align: center;
            }
            .win-rate-val {
                font-family: var(--font-orbitron);
                font-size: 2.2rem;
                font-weight: 900;
                color: var(--neon-green);
                text-shadow: 0 0 15px rgba(0, 255, 136, 0.5);
            }

            .rec-move-card {
                background: rgba(2, 4, 9, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px;
            }

            .bench-card.empty-slot {
                border: 1px dashed rgba(0, 243, 255, 0.4);
                background: rgba(0, 243, 255, 0.03);
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 65px;
            }
            .btn-summon-slot {
                background: rgba(0, 253, 255, 0.1);
                border: 1px solid var(--neon-cyan);
                color: var(--neon-cyan);
                font-family: var(--font-orbitron);
                font-size: 0.65rem;
                font-weight: 700;
                padding: 6px 8px;
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.2s;
                text-align: center;
            }
            .btn-summon-slot:hover {
                background: var(--neon-cyan);
                color: #000;
                box-shadow: var(--neon-cyan-glow);
            }

            /* BATTLE MATRIX & TCG PLAYMAT LAYOUT */
            .tcg-playmat-container {
                display: flex;
                flex-direction: column;
                gap: 16px;
                background: rgba(8, 15, 30, 0.9);
                border: 2px solid rgba(0, 243, 255, 0.3);
                border-radius: 14px;
                padding: 20px;
                backdrop-filter: blur(16px);
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.85), inset 0 0 50px rgba(0, 243, 255, 0.04);
            }

            .opp-top-board, .player-bottom-board {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 16px;
                background: rgba(15, 23, 42, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 14px;
            }
            @media (max-width: 768px) {
                .opp-top-board, .player-bottom-board { grid-template-columns: 1fr; }
            }

            .board-subzone { display: flex; flex-direction: column; justify-content: space-between; }
            .prizes-subzone {
                background: rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(251, 191, 36, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
            }

            .active-spot-center {
                display: flex;
                flex-direction: column;
                align-items: center;
                margin: 4px 0;
            }
            .active-spot-center .visual-active-card {
                width: 100%;
                max-width: 680px;
            }

            /* CENTER ARENA DIVIDER */
            .arena-divider-bar {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 16px;
                margin: 8px 0;
            }
            .divider-line {
                flex: 1;
                height: 2px;
                background: linear-gradient(90deg, rgba(0, 243, 255, 0) 0%, var(--neon-cyan) 50%, rgba(0, 243, 255, 0) 100%);
            }
            .divider-badge {
                font-family: var(--font-orbitron);
                font-size: 0.8rem;
                font-weight: 800;
                color: var(--neon-cyan);
                letter-spacing: 2px;
                text-shadow: 0 0 10px var(--neon-cyan);
                background: rgba(0, 243, 255, 0.1);
                border: 1px solid var(--neon-cyan);
                padding: 4px 16px;
                border-radius: 20px;
            }

            /* PRIZES & DECK TRAY */
            .prizes-rack { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
            .prize-card-slot {
                width: 26px;
                height: 38px;
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                border: 1px solid var(--card-gold);
                border-radius: 4px;
                box-shadow: 0 0 8px rgba(251, 191, 36, 0.4);
                transition: all 0.3s;
            }
            .prize-card-slot.taken {
                background: rgba(255, 255, 255, 0.05);
                border-color: rgba(255, 255, 255, 0.2);
                box-shadow: none;
                opacity: 0.25;
            }
            .deck-counter-badge {
                font-family: var(--font-orbitron);
                font-size: 0.85rem;
                font-weight: 800;
                color: #38bdf8;
            }

            /* VISUAL ACTIVE CARD */
            .visual-active-card {
                background: linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(3, 7, 18, 0.98) 100%);
                border: 2px solid var(--neon-cyan);
                border-radius: 10px;
                padding: 14px;
                box-shadow: var(--neon-cyan-glow);
                margin-bottom: 6px;
                position: relative;
            }
            .visual-active-card.opp-active-card {
                border-color: var(--neon-magenta);
                box-shadow: var(--neon-magenta-glow);
            }
            .card-top-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
            .card-name-hero { font-family: var(--font-orbitron); font-size: 1.25rem; font-weight: 900; color: #fff; }
            .card-type-tag {
                font-family: var(--font-mono);
                font-size: 0.75rem;
                padding: 3px 8px;
                border-radius: 4px;
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                font-weight: 700;
            }

            .hp-info { display: flex; justify-content: space-between; font-family: var(--font-orbitron); font-size: 0.82rem; font-weight: 700; margin-bottom: 4px; }
            .hp-track { height: 9px; background: rgba(0, 0, 0, 0.6); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 6px; overflow: hidden; margin-bottom: 8px; }
            .hp-fill { height: 100%; background: linear-gradient(90deg, #10b981 0%, #34d399 100%); transition: width 0.4s; }
            .hp-fill.danger { background: linear-gradient(90deg, #ef4444 0%, #f87171 100%); }
            .hp-fill.warning { background: linear-gradient(90deg, #f59e0b 0%, #fbbf24 100%); }

            .energy-tray { display: flex; align-items: center; gap: 6px; margin: 8px 0; flex-wrap: wrap; }
            .energy-pill {
                background: rgba(239, 68, 68, 0.2);
                border: 1px solid #ef4444;
                color: #fca5a5;
                font-family: var(--font-mono);
                font-size: 0.72rem;
                padding: 2px 7px;
                border-radius: 10px;
            }

            /* ATTACKS BOX */
            .attacks-box { background: rgba(0, 0, 0, 0.45); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 8px; margin-top: 8px; }
            .attack-item {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 5px;
                padding: 6px 10px;
                margin-bottom: 5px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 8px;
            }
            .atk-name { font-family: var(--font-orbitron); font-size: 0.88rem; font-weight: 700; color: #fff; }
            .atk-cost { font-family: var(--font-mono); font-size: 0.7rem; color: #cbd5e1; }
            .atk-dmg { font-family: var(--font-orbitron); font-size: 1.1rem; font-weight: 900; color: var(--neon-amber); }
            .btn-strike {
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                border: none;
                color: white;
                font-family: var(--font-orbitron);
                font-size: 0.72rem;
                font-weight: 800;
                padding: 5px 10px;
                border-radius: 4px;
                cursor: pointer;
                box-shadow: 0 0 8px rgba(239, 68, 68, 0.5);
                transition: all 0.2s;
            }
            .btn-strike:hover { transform: scale(1.05); }

            /* BENCH GRID (3 SLOTS) */
            .section-label {
                font-family: var(--font-orbitron);
                font-size: 0.72rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                color: var(--text-dim);
                margin: 6px 0 4px 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .bench-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; min-height: 70px; }

            .bench-card {
                background: rgba(15, 23, 42, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 6px;
                text-align: center;
            }
            .b-name { font-family: var(--font-orbitron); font-size: 0.75rem; font-weight: 700; }
            .b-hp { font-family: var(--font-mono); font-size: 0.68rem; color: #38bdf8; }

            /* HAND CARDS */
            .hand-cards-section {
                background: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(0, 243, 255, 0.2);
                border-radius: 10px;
                padding: 12px;
            }
            .hand-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 8px; }
            .hand-card-chip {
                background: rgba(15, 23, 42, 0.95);
                border: 1px solid rgba(0, 243, 255, 0.25);
                border-radius: 6px;
                padding: 6px 8px;
                position: relative;
            }
            .hand-card-chip:hover { border-color: var(--neon-green); box-shadow: 0 0 10px rgba(0, 255, 136, 0.3); }
            .h-type-pill { font-size: 0.62rem; font-family: var(--font-mono); text-transform: uppercase; color: var(--neon-cyan); }
            .h-title { font-family: var(--font-orbitron); font-size: 0.78rem; font-weight: 700; margin: 2px 0 4px 0; }
            .btn-hand-play {
                background: rgba(0, 255, 136, 0.15);
                border: 1px solid var(--neon-green);
                color: var(--neon-green);
                font-size: 0.65rem;
                font-family: var(--font-orbitron);
                padding: 2px 6px;
                border-radius: 3px;
                cursor: pointer;
                width: 100%;
            }
            .btn-hand-play:hover { background: var(--neon-green); color: #000; }

            /* STICKY BOTTOM AI CO-PILOT HUD */
            .sticky-ai-hud-bar {
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100vw;
                z-index: 999;
                background: linear-gradient(135deg, rgba(8, 14, 28, 0.97) 0%, rgba(3, 5, 12, 0.98) 100%);
                border-top: 2px solid var(--neon-cyan);
                box-shadow: 0 -5px 25px rgba(0, 243, 255, 0.35);
                padding: 10px 24px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                backdrop-filter: blur(14px);
            }
            @media (max-width: 768px) {
                .sticky-ai-hud-bar { flex-direction: column; gap: 8px; padding: 8px 12px; }
            }

            /* MATCH ACTIONS BAR */
            .match-actions-bar {
                display: flex;
                gap: 12px;
                justify-content: center;
                margin: 15px 0;
                flex-wrap: wrap;
            }
            .btn-action-main {
                background: linear-gradient(135deg, rgba(0, 243, 255, 0.2) 0%, rgba(56, 189, 248, 0.3) 100%);
                border: 1px solid var(--neon-cyan);
                color: #fff;
                font-family: var(--font-orbitron);
                font-size: 0.95rem;
                font-weight: 800;
                padding: 12px 24px;
                border-radius: 6px;
                cursor: pointer;
                letter-spacing: 1px;
                transition: all 0.2s;
            }
            .btn-action-main:hover { background: var(--neon-cyan); color: #000; box-shadow: var(--neon-cyan-glow); }
            .btn-action-main:disabled { opacity: 0.45; cursor: not-allowed; border-color: #64748b; background: rgba(255, 255, 255, 0.05); }

            /* COMBAT LOG TERMINAL */
            .combat-log-box {
                background: #020409;
                border: 1px solid var(--neon-green);
                border-radius: 8px;
                padding: 10px;
                font-family: var(--font-mono);
                font-size: 0.78rem;
                color: var(--neon-green);
                max-height: 120px;
                overflow-y: auto;
            }

            /* VISUAL ACTIVE CARD (FULL-SIZE TCG ARENA LEAD) */
            .visual-active-card {
                background: linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(3, 7, 18, 0.98) 100%);
                border: 2px solid var(--neon-cyan);
                border-radius: 12px;
                padding: 20px;
                box-shadow: var(--neon-cyan-glow);
                margin-bottom: 6px;
                position: relative;
                min-height: 280px;
            }
            .visual-active-card.opp-active-card {
                border-color: var(--neon-magenta);
                box-shadow: var(--neon-magenta-glow);
            }

            /* HAND CARDS (LARGE FULL-SIZE TCG CARDS) */
            .hand-cards-section {
                background: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(0, 243, 255, 0.2);
                border-radius: 10px;
                padding: 14px;
            }
            .hand-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(155px, 1fr));
                gap: 12px;
                min-height: 190px;
            }
            .hand-card-chip {
                background: rgba(15, 23, 42, 0.95);
                border: 2px solid rgba(0, 243, 255, 0.35);
                border-radius: 8px;
                padding: 12px;
                min-height: 185px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                box-shadow: 0 8px 20px rgba(0, 0, 0, 0.6);
                transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                cursor: grab;
            }
            .hand-card-chip:hover {
                transform: translateY(-6px) scale(1.03);
                border-color: var(--neon-green);
                box-shadow: 0 12px 25px rgba(0, 255, 136, 0.4);
            }

            /* BENCH CARDS (LARGE SUB SLOTS) */
            .bench-card {
                background: rgba(15, 23, 42, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 10px;
                text-align: center;
                min-height: 115px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }

            /* 3D DECK STACK CARDS */
            .deck-card-3d {
                width: 105px !important;
                height: 145px !important;
                transition: all 0.3s;
            }
            @keyframes cardFlipGlide3D {
                0% {
                    transform: perspective(800px) rotateY(0deg) scale(1) translateY(0);
                    box-shadow: 0 5px 15px rgba(0, 243, 255, 0.4);
                }
                50% {
                    transform: perspective(800px) rotateY(180deg) scale(1.3) translateY(-60px);
                    box-shadow: 0 0 35px rgba(0, 243, 255, 0.9);
                }
                100% {
                    transform: perspective(800px) rotateY(360deg) scale(1) translateY(120px);
                    box-shadow: 0 5px 15px rgba(0, 243, 255, 0.4);
                }
            }
            .animating-flip-3d {
                animation: cardFlipGlide3D 0.75s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards !important;
            }

            /* ALL CARDS DATABASE & CUSTOM DECK BUILDER STYLES */
            .all-cards-section {
                display: flex;
                flex-direction: column;
                gap: 18px;
                margin-bottom: 90px;
            }
            .deck-builder-control-card {
                background: rgba(15, 23, 42, 0.95);
                border: 2px solid var(--neon-cyan);
                border-radius: 12px;
                padding: 18px 22px;
                box-shadow: 0 10px 30px rgba(0, 243, 255, 0.2);
                backdrop-filter: blur(16px);
                display: flex;
                flex-direction: column;
                gap: 14px;
            }
            .cd-stat-pill {
                background: rgba(0, 0, 0, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.15);
                padding: 6px 14px;
                border-radius: 20px;
                font-family: var(--font-orbitron);
                font-size: 0.8rem;
                display: flex;
                align-items: center;
                gap: 6px;
            }
            .cards-filter-bar {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                align-items: center;
                justify-content: space-between;
                background: rgba(8, 14, 28, 0.85);
                border: 1px solid rgba(0, 243, 255, 0.2);
                border-radius: 10px;
                padding: 12px 16px;
            }
            .cards-search-box {
                flex: 1;
                min-width: 250px;
                position: relative;
            }
            .cards-search-input {
                width: 100%;
                background: rgba(2, 6, 23, 0.9);
                border: 1px solid var(--neon-cyan);
                color: #fff;
                font-family: var(--font-mono);
                font-size: 0.85rem;
                padding: 8px 14px;
                border-radius: 6px;
                outline: none;
                transition: all 0.2s;
            }
            .cards-search-input:focus {
                box-shadow: var(--neon-cyan-glow);
                border-color: #38bdf8;
            }
            .filter-chip {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.15);
                color: var(--text-dim);
                font-family: var(--font-orbitron);
                font-size: 0.72rem;
                font-weight: 700;
                padding: 6px 12px;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s;
            }
            .filter-chip:hover {
                border-color: var(--neon-cyan);
                color: #fff;
            }
            .filter-chip.active {
                background: rgba(0, 243, 255, 0.2);
                border-color: var(--neon-cyan);
                color: var(--neon-cyan);
                box-shadow: 0 0 10px rgba(0, 243, 255, 0.3);
            }
            .all-cards-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
                gap: 16px;
            }
            .dataset-card-box {
                background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(3, 7, 18, 0.98) 100%);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                padding: 14px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
                transition: all 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                position: relative;
            }
            .dataset-card-box:hover {
                transform: translateY(-5px);
                border-color: var(--neon-cyan);
                box-shadow: 0 12px 30px rgba(0, 243, 255, 0.35);
            }
            .dataset-card-box.in-deck-active {
                border-color: var(--neon-green);
                box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
            }
            .card-deck-stepper {
                display: flex;
                align-items: center;
                justify-content: space-between;
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 4px;
                margin-top: 10px;
                gap: 6px;
            }
            .stepper-btn {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: #fff;
                font-family: var(--font-orbitron);
                font-size: 0.9rem;
                font-weight: 900;
                width: 32px;
                height: 30px;
                border-radius: 4px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
            }
            .stepper-btn:hover {
                background: var(--neon-cyan);
                color: #000;
            }
            .stepper-btn:disabled {
                opacity: 0.3;
                cursor: not-allowed;
            }
            .stepper-count-badge {
                font-family: var(--font-orbitron);
                font-size: 0.8rem;
                font-weight: 800;
                color: #38bdf8;
                flex: 1;
                text-align: center;
            }
            .btn-quick-add {
                background: rgba(0, 255, 136, 0.15);
                border: 1px solid var(--neon-green);
                color: var(--neon-green);
                font-family: var(--font-orbitron);
                font-size: 0.72rem;
                font-weight: 800;
                padding: 6px 10px;
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.2s;
                text-align: center;
                width: 100%;
                margin-top: 6px;
            }
            .btn-quick-add:hover {
                background: var(--neon-green);
                color: #000;
            }

            /* CATEGORY SECTIONS & CHOSEN DECK TRAY */
            .category-section-box {
                background: rgba(15, 23, 42, 0.65);
                border: 1px solid rgba(0, 243, 255, 0.2);
                border-radius: 12px;
                padding: 20px;
                display: flex;
                flex-direction: column;
                gap: 16px;
                margin-top: 10px;
            }
            .category-section-title {
                font-family: var(--font-orbitron);
                font-size: 1.15rem;
                font-weight: 900;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding-bottom: 8px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            .deck-chips-tray {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
                max-height: 140px;
                overflow-y: auto;
                background: rgba(2, 6, 23, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 10px;
            }
            .deck-chip-item {
                background: rgba(15, 23, 42, 0.95);
                border: 1px solid rgba(0, 243, 255, 0.4);
                border-radius: 6px;
                padding: 4px 8px;
                display: flex;
                align-items: center;
                gap: 8px;
                font-family: var(--font-orbitron);
                font-size: 0.72rem;
                color: #fff;
            }
            .deck-chip-btn {
                background: rgba(239, 68, 68, 0.2);
                border: 1px solid #ef4444;
                color: #fca5a5;
                font-size: 0.7rem;
                font-weight: 800;
                width: 20px;
                height: 20px;
                border-radius: 3px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .deck-chip-btn:hover {
                background: #ef4444;
                color: #fff;
            }
        </style>
    </head>
    <body onload="initApp()">
        <div class="scanlines"></div>

        <div class="cyber-container">
            <header>
                <div class="cyber-badge">🏆 OFFICIAL POKÉMON TCG ESPORTS MATCH ARENA // VER 2.2</div>
                <h1 class="cyber-glitch-title">POKÉMON TCG // COMPETITIVE MATCH ENGINE</h1>
            </header>

            <!-- MODE SWITCH TABS -->
            <div class="tab-nav-bar">
                <button id="tab-btn-match" class="tab-btn active" onclick="switchMode('match')">⚔️ 60-CARD LIVE MATCH MODE</button>
                <button id="tab-btn-cards" class="tab-btn" onclick="switchMode('cards')">🃏 CHOOSE 4 CARDS & DATASET (CSV)</button>
                <button id="tab-btn-deck" class="tab-btn" onclick="switchMode('deck')">🏆 PRE-SET META ARCHETYPES</button>
            </div>

            <!-- ================= VIEW 1: 60-CARD LIVE MATCH (3-COLUMN LAYOUT) ================= -->
            <div id="view-match">
                <div class="app-3col-layout">
                    <!-- LEFT COLUMN: AI RECOMMENDATION SYSTEM -->
                    <div class="side-column-panel">
                        <div class="panel-header-title">🧠 AI RECOMMENDATION SYSTEM</div>
                        <div class="win-rate-display-box">
                            <div style="font-size:0.75rem; color:var(--text-dim); font-family:var(--font-orbitron);">LIVE MATCH WIN RATE</div>
                            <div id="left-win-pct" class="win-rate-val">--%</div>
                        </div>
                        
                        <div class="rec-move-card">
                            <div style="font-family:var(--font-orbitron); font-size:0.75rem; color:var(--neon-cyan); margin-bottom:4px;">TOP RECOMMENDED ACTION</div>
                            <div id="left-rec-action" style="font-family:var(--font-orbitron); font-size:0.95rem; font-weight:800; color:#fff;">Evaluating Match State...</div>
                            <div id="left-rec-desc" style="font-size:0.8rem; color:#cbd5e1; margin-top:6px; line-height:1.3;">AI Engine is computing real-time optimal plays from the arena...</div>
                        </div>

                        <div class="rec-move-card">
                            <div style="font-family:var(--font-orbitron); font-size:0.75rem; color:var(--neon-amber); margin-bottom:6px;">TOP RANKED PLAYS</div>
                            <div id="left-ranked-list" style="font-size:0.78rem; display:flex; flex-direction:column; gap:6px;">
                                <div>1. Calculating highest-scoring action...</div>
                                <div>2. Evaluating counter-attacks...</div>
                                <div>3. Analyzing energy tempo...</div>
                            </div>
                        </div>

                        <button class="btn-exec-ai" style="width:100%; text-align:center;" onclick="executeAiRecommendation()">⚡ EXECUTE PLAY</button>
                    </div>

                    <!-- CENTER COLUMN: TCG BATTLE ARENA PLAYMAT -->
                    <div class="tcg-playmat-container">
                        <!-- OPPONENT TOP BOARD: SUB POKÉMON (3 SLOTS) & DECK CARD GENERATOR -->
                        <div class="opp-top-board">
                            <div class="board-subzone">
                                <div class="section-label"><span>OPPONENT SUB POKÉMON (3 SLOTS)</span></div>
                                <div id="opp-bench-view" class="bench-grid"></div>
                            </div>
                            <div class="board-subzone deck-generator-subzone" style="align-items: center; justify-content: center;">
                                <div class="section-label"><span>OPPONENT 60-CARD MYSTERY DECK</span></div>
                                <div class="deck-generator-box" style="display:flex; flex-direction:column; align-items:center;">
                                    <div class="mystery-card-back opp-mystery deck-card-3d" style="width:160px; height:220px; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:12px; border-radius:10px; border:2px solid var(--neon-magenta); box-shadow:0 0 20px rgba(255,0,127,0.4);">
                                        <div style="font-size:2.8rem;">🃏</div>
                                        <div style="font-family:var(--font-orbitron); font-size:0.85rem; color:var(--neon-magenta); font-weight:900; margin-top:8px;">OPPONENT DECK</div>
                                        <div style="font-size:0.7rem; color:#cbd5e1; margin-top:4px;">[ 60 CARDS MYSTERY ]</div>
                                    </div>
                                    <div class="deck-counter-badge" style="color: var(--neon-magenta); margin-top: 8px;">
                                        🃏 OPP DECK: <span id="opp-deck-count">47</span>/60
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- OPPONENT MAIN POKÉMON -->
                        <div class="active-spot-center">
                            <div class="section-label" style="justify-content: center; color: var(--neon-magenta);">
                                <span>👑 OPPONENT MAIN POKÉMON</span>
                            </div>
                            <div id="opp-active-view" class="visual-active-card opp-active-card"></div>
                        </div>

                        <!-- CENTER MATCH ARENA DIVIDER -->
                        <div class="arena-divider-bar">
                            <div class="divider-line"></div>
                            <div class="divider-badge">~~~~~~~~~~~~~~~~~~~~~~~~ MATCH ARENA ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~</div>
                            <div class="divider-line"></div>
                        </div>

                        <!-- PLAYER MAIN POKÉMON -->
                        <div class="active-spot-center">
                            <div class="section-label" style="justify-content: center; color: var(--neon-cyan);">
                                <span>👑 YOUR MAIN POKÉMON</span>
                            </div>
                            <div id="player-active-view" class="visual-active-card"></div>
                        </div>

                        <!-- PLAYER BOTTOM BOARD: SUB POKÉMON (3 SLOTS) & DECK CARD GENERATOR -->
                        <div class="player-bottom-board">
                            <div class="board-subzone">
                                <div class="section-label"><span>YOUR SUB POKÉMON (3 SLOTS)</span></div>
                                <div id="player-bench-view" class="bench-grid"></div>
                            </div>
                            <div class="board-subzone deck-generator-subzone" style="align-items: center; justify-content: center;">
                                <div class="section-label"><span>YOUR 60-CARD DECK GENERATOR</span></div>
                                <div class="deck-generator-box" style="display:flex; flex-direction:column; align-items:center;">
                                    <div class="mystery-card-back deck-card-3d" onclick="claimRandomDeckCard()" style="width:160px; height:220px; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:12px; border-radius:10px; border:2px solid var(--neon-cyan); box-shadow:0 0 20px rgba(0,243,255,0.4); cursor:pointer;" title="Click card to flip and draw 1 random card into hand!">
                                        <div style="font-size:2.8rem;">🃏</div>
                                        <div style="font-family:var(--font-orbitron); font-size:0.85rem; color:var(--neon-cyan); font-weight:900; margin-top:8px;">MYSTERY DECK</div>
                                        <div style="font-size:0.7rem; color:#cbd5e1; margin-top:4px;">[ CLICK TO FLIP & DRAW ]</div>
                                    </div>
                                    <button id="btn-claim-deck-card" class="btn-action-main" style="margin-top: 10px; width: 100%; font-size: 0.78rem; padding: 8px 12px; border-color: var(--neon-cyan); box-shadow: 0 0 15px rgba(0,243,255,0.35); text-align: center;" onclick="claimRandomDeckCard()">
                                        🃏 CLAIM DECK CARD
                                    </button>
                                    <div style="margin-top: 8px; display: flex; gap: 14px; align-items: center; justify-content: center;">
                                        <div class="deck-counter-badge">🃏 DECK: <span id="p-deck-count">34</span>/60</div>
                                        <div style="font-size: 0.8rem; color: var(--text-dim); font-family: var(--font-mono);">DISCARD: <span id="p-discard-count">8</span></div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- PLAYER HAND CARDS -->
                        <div class="hand-cards-section">
                            <div class="section-label">
                                <span>YOUR HAND CARDS (INITIAL 4 CARDS &bull; MAX 10 LIMIT)</span>
                            </div>
                            <div id="player-hand-view" class="hand-grid"></div>
                        </div>

                        <!-- MATCH CONTROLS -->
                        <div class="match-actions-bar">
                            <button id="btn-add-energy-main" class="btn-action-main" style="border-color: var(--neon-cyan);" onclick="promptAddEnergyDirect('player')">⚡ + ADD ENERGY (1 PER TURN)</button>
                            <button class="btn-action-main" style="border-color: var(--neon-green);" onclick="endPlayerTurn()">⏭️ END TURN & LET OPPONENT PLAY</button>
                        </div>
                    </div>

                    <!-- RIGHT COLUMN: MATCH DETAILS & STATUS -->
                    <div class="side-column-panel">
                        <div class="panel-header-title">📊 MATCH DETAILS & STATUS</div>

                        <!-- SCOREBOARD -->
                        <div style="background:rgba(2,4,9,0.8); border:1px solid rgba(0,243,255,0.2); border-radius:8px; padding:12px;">
                            <div style="font-family:var(--font-orbitron); font-size:0.75rem; color:var(--text-dim); margin-bottom:6px;">3 MAIN POKÉMON LOSS SCOREBOARD</div>
                            <div style="display:flex; justify-content:space-between; font-family:var(--font-orbitron); font-size:0.88rem;">
                                <span style="color:var(--neon-green);">YOUR KOs: <b id="p-ko-count" style="font-size:1.1rem;">0</b>/3</span>
                                <span style="color:var(--neon-magenta);">OPP KOs: <b id="opp-ko-count" style="font-size:1.1rem;">0</b>/3</span>
                            </div>
                            <div id="match-status-banner" class="cyber-badge" style="margin-top:10px; width:100%; justify-content:center;">MATCH IN PROGRESS</div>
                        </div>

                        <!-- DECK SELECTOR -->
                        <div style="background:rgba(2,4,9,0.8); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:12px;">
                            <div style="font-family:var(--font-orbitron); font-size:0.75rem; color:var(--neon-cyan); margin-bottom:6px;">ACTIVE ARCHETYPE DECK</div>
                            <button class="btn-action-main" style="background:rgba(0,243,255,0.15); border-color:var(--neon-cyan); color:var(--neon-cyan); font-weight:900; width:100%; margin-bottom:8px; padding:10px; font-size:0.78rem;" onclick="switchMode('cards')">🎯 CHOOSE YOUR 4 CARDS (FROM CSV)</button>
                            <button class="btn-cyber-sm" style="background:var(--neon-amber); color:#000; font-weight:900; width:100%; margin-bottom:10px; padding:10px; box-shadow:0 0 12px rgba(255,170,0,0.5);" onclick="loadTop60RecommendedDeck()">💡 LOAD TOP-60 STRATEGIC DECK</button>
                            <select id="deck-select" class="neon-input-key" style="width:100%; margin-bottom:8px;" onchange="startMatchWithDeck(this.value)">
                                <option value="ai-top-60-optimized">⚡ AI TOP-60 STRATEGIC OPTIMIZED DECK</option>
                                <option value="charizard-ex-pidgeot">Charizard ex / Pidgeot ex (Tier 1)</option>
                                <option value="miraidon-ex-regieleki">Miraidon ex / Iron Hands ex (Tier 1)</option>
                                <option value="gardevoir-ex">Gardevoir ex / Scream Tail (Tier 1)</option>
                            </select>
                            <button class="btn-cyber-sm" style="width:100%; text-align:center;" onclick="startNewMatch()">⚡ RESTART MATCH</button>
                        </div>

                        <!-- COMBAT LOG -->
                        <div style="font-family:var(--font-orbitron); font-size:0.75rem; color:var(--neon-green);">MATCH COMBAT LOG</div>
                        <div id="combat-log" class="combat-log-box" style="max-height:220px;"></div>
                    </div>
                </div>
            </div>

            <!-- ================= VIEW 2: COMPLETE CARDS DATABASE & CUSTOM DECK BUILDER ================= -->
            <div id="view-cards" class="all-cards-section" style="display:none;">
                <!-- 4-CARD BATTLE SELECTION DOCK -->
                <div class="deck-builder-control-card" style="border: 2px solid var(--neon-cyan); box-shadow: 0 0 25px rgba(0,243,255,0.25); margin-bottom: 20px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                        <div>
                            <div style="font-family:var(--font-orbitron); font-size:1.15rem; font-weight:900; color:var(--neon-cyan);">
                                🎯 CHOOSE YOUR 4 CARDS (1 MAIN ACTIVE + 3 BENCH SUB POKÉMON)
                            </div>
                            <div style="font-size:0.82rem; color:var(--text-dim); margin-top:2px;">
                                Pick 4 cards from the official Pokémon dataset below. Place 1 as your Main Pokémon and 3 on your Bench. The AI will sample 4 counter Pokémon and launch your match!
                            </div>
                        </div>
                        <div style="display:flex; gap:10px; flex-wrap:wrap;">
                            <button id="btn-start-4cards" class="btn-action-main" style="padding:10px 22px; font-size:0.9rem; border-color:var(--neon-green); box-shadow:var(--neon-green-glow);" onclick="startBattleWithSelected4Cards()">
                                ⚔️ PLACE MY 4 CARDS & START BATTLE
                            </button>
                            <button class="btn-cyber-sm" style="background:var(--neon-amber); color:#000; font-weight:900; padding:10px 14px;" onclick="dealRandom4Cards()">
                                🎲 AUTO-DEAL 4 RANDOM CARDS
                            </button>
                            <button class="btn-cyber-sm" style="border-color:#ef4444; color:#fca5a5; padding:10px 14px;" onclick="resetChosen4Cards()">
                                🔄 RESET
                            </button>
                        </div>
                    </div>

                    <!-- 4 Slots Display -->
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px; margin-top:14px;">
                        <div id="slot-card-1" class="cd-stat-pill" style="border:2px solid var(--neon-cyan); background:rgba(0,243,255,0.12); flex-direction:column; align-items:flex-start; padding:10px;">
                            <div style="font-size:0.7rem; color:var(--neon-cyan); font-family:var(--font-orbitron); font-weight:800;">👑 SLOT 1: MAIN ACTIVE</div>
                            <div id="slot-name-1" style="font-size:0.95rem; font-weight:900; color:#fff; margin-top:3px;">Charizard ex (330 HP)</div>
                            <div id="slot-type-1" style="font-size:0.7rem; color:#cbd5e1;">Type: Fire &bull; 180 DMG</div>
                        </div>
                        <div id="slot-card-2" class="cd-stat-pill" style="border:1px solid rgba(0,255,136,0.4); background:rgba(0,255,136,0.06); flex-direction:column; align-items:flex-start; padding:10px;">
                            <div style="font-size:0.7rem; color:var(--neon-green); font-family:var(--font-orbitron); font-weight:800;">🛡️ SLOT 2: BENCH SUB #1</div>
                            <div id="slot-name-2" style="font-size:0.95rem; font-weight:900; color:#fff; margin-top:3px;">Charmander (70 HP)</div>
                            <div id="slot-type-2" style="font-size:0.7rem; color:#cbd5e1;">Type: Fire &bull; 30 DMG</div>
                        </div>
                        <div id="slot-card-3" class="cd-stat-pill" style="border:1px solid rgba(0,255,136,0.4); background:rgba(0,255,136,0.06); flex-direction:column; align-items:flex-start; padding:10px;">
                            <div style="font-size:0.7rem; color:var(--neon-green); font-family:var(--font-orbitron); font-weight:800;">🛡️ SLOT 3: BENCH SUB #2</div>
                            <div id="slot-name-3" style="font-size:0.95rem; font-weight:900; color:#fff; margin-top:3px;">Pidgeot ex (280 HP)</div>
                            <div id="slot-type-3" style="font-size:0.7rem; color:#cbd5e1;">Type: Colorless &bull; 120 DMG</div>
                        </div>
                        <div id="slot-card-4" class="cd-stat-pill" style="border:1px solid rgba(0,255,136,0.4); background:rgba(0,255,136,0.06); flex-direction:column; align-items:flex-start; padding:10px;">
                            <div style="font-size:0.7rem; color:var(--neon-green); font-family:var(--font-orbitron); font-weight:800;">🛡️ SLOT 4: BENCH SUB #3</div>
                            <div id="slot-name-4" style="font-size:0.95rem; font-weight:900; color:#fff; margin-top:3px;">Venusaur ex (240 HP)</div>
                            <div id="slot-type-4" style="font-size:0.7rem; color:#cbd5e1;">Type: Grass &bull; 120 DMG</div>
                        </div>
                    </div>
                </div>

                <!-- CUSTOM DECK CONTROL PANEL -->
                <div class="deck-builder-control-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                        <div>
                            <div style="font-family:var(--font-orbitron); font-size:1.15rem; font-weight:900; color:var(--neon-cyan);">
                                🎴 COMPLETE CARDS DATASET & CUSTOM 60-CARD DECK BUILDER
                            </div>
                            <div style="font-size:0.82rem; color:var(--text-dim); margin-top:2px;">
                                Choose cards from the separate Pokémon, Trainer, and Energy sections below (max 60 cards in deck, max 4 copies per card name except Basic Energy).
                            </div>
                        </div>
                        <div style="display:flex; gap:10px; flex-wrap:wrap;">
                            <button id="btn-play-custom-deck" class="btn-action-main" style="padding:10px 20px; font-size:0.85rem; border-color:var(--neon-green);" onclick="startMatchWithCustomDeck()">
                                ⚔️ PLAY MATCH WITH THIS DECK (0/60)
                            </button>
                            <button class="btn-cyber-sm" style="background:var(--neon-amber); color:#000; font-weight:900; padding:10px 14px;" onclick="autoFillBasicEnergy()">
                                ⚡ AUTO-FILL WITH BASIC ENERGY
                            </button>
                            <button class="btn-cyber-sm" style="border-color:#ef4444; color:#fca5a5; padding:10px 14px;" onclick="clearCustomDeck()">
                                🗑️ CLEAR DECK
                            </button>
                        </div>
                    </div>

                    <!-- DECK METRICS & STATS -->
                    <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-top:4px;">
                        <div class="cd-stat-pill" style="border-color:var(--neon-cyan); background:rgba(0,243,255,0.1);">
                            <span>🎴 TOTAL CARDS:</span>
                            <span id="cd-total-count" style="font-weight:900; color:var(--neon-cyan); font-size:1.1rem;">0</span> / 60
                        </div>
                        <div class="cd-stat-pill" style="border-color:#ef4444; color:#fca5a5;">
                            <span>🔴 POKÉMON:</span>
                            <b id="cd-pkmn-count" style="color:#fff;">0</b>
                        </div>
                        <div class="cd-stat-pill" style="border-color:var(--neon-amber); color:#fde68a;">
                            <span>📜 TRAINERS:</span>
                            <b id="cd-trainer-count" style="color:#fff;">0</b>
                        </div>
                        <div class="cd-stat-pill" style="border-color:var(--neon-green); color:#86efac;">
                            <span>⚡ ENERGY:</span>
                            <b id="cd-energy-count" style="color:#fff;">0</b>
                        </div>
                    </div>
                    <div class="hp-track" style="margin-top:2px; height:8px;">
                        <div id="cd-progress-fill" class="hp-fill" style="width:0%;"></div>
                    </div>

                    <!-- CHOSEN DECK CARDS TRAY -->
                    <div style="margin-top:8px;">
                        <div style="font-family:var(--font-orbitron); font-size:0.75rem; color:var(--neon-cyan); margin-bottom:6px; display:flex; justify-content:space-between;">
                            <span>🃏 CURRENTLY CHOSEN DECK CARDS (<span id="chosen-distinct-count">0</span> UNIQUE CARDS):</span>
                            <span style="color:var(--text-dim);">Click [-] or [+] to adjust quantity</span>
                        </div>
                        <div id="chosen-deck-chips" class="deck-chips-tray">
                            <div style="color:var(--text-dim); font-size:0.75rem; padding:6px;">Your custom deck is currently empty. Use the select options on any card below to add cards!</div>
                        </div>
                    </div>
                </div>

                <!-- SEARCH & FILTER TOOLBAR -->
                <div class="cards-filter-bar">
                    <div class="cards-search-box">
                        <input type="text" id="cards-search-input" class="cards-search-input" placeholder="🔍 Search cards by name, attack, ability, type, or card ID..." oninput="filterCardsDatabase()">
                    </div>
                    <div style="display:flex; gap:6px; flex-wrap:wrap;">
                        <button class="filter-chip active" onclick="setCardCategoryFilter('all', this)">All Sections (69)</button>
                        <button class="filter-chip" onclick="setCardCategoryFilter('pokemon', this)">🔥 Pokémon Section</button>
                        <button class="filter-chip" onclick="setCardCategoryFilter('trainer', this)">📜 Trainers Section</button>
                        <button class="filter-chip" onclick="setCardCategoryFilter('energy', this)">⚡ Energy Section</button>
                    </div>
                </div>

                <!-- SEPARATE SECTION 1: ALL POKÉMON IN DATASET -->
                <div id="section-pokemon-container" class="category-section-box">
                    <div class="category-section-title" style="color:#f87171;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span>👑 POKÉMON ROSTER & BATTLE CARDS</span>
                            <span id="badge-pkmn-total" class="cyber-badge" style="font-size:0.65rem; border-color:#ef4444; color:#fca5a5;">1,218 CARDS</span>
                        </div>
                        <span style="font-size:0.72rem; color:var(--text-dim); font-family:var(--font-mono);">All 1,025 National Pokédex species + Ultra Rare ex forms</span>
                    </div>
                    <div id="pokemon-cards-grid" class="all-cards-grid"></div>
                    <div id="pokemon-load-more-box" style="display:flex; justify-content:center; gap:12px; margin-top:16px;">
                        <button class="btn-cyber-sm" style="background:rgba(239,68,68,0.2); border-color:#ef4444; color:#fff; font-weight:800; padding:10px 20px;" onclick="loadMorePokemon()">
                            📥 LOAD MORE POKÉMON (+60)
                        </button>
                        <button class="btn-cyber-sm" style="background:rgba(0,243,255,0.2); border-color:var(--neon-cyan); color:var(--neon-cyan); font-weight:800; padding:10px 20px;" onclick="showAllPokemon()">
                            ✨ SHOW ALL POKÉMON
                        </button>
                    </div>
                </div>

                <!-- SEPARATE SECTION 2: ALL TRAINERS & SUPPORTERS IN DATASET -->
                <div id="section-trainer-container" class="category-section-box">
                    <div class="category-section-title" style="color:var(--neon-amber);">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span>📜 TRAINERS & SUPPORTERS</span>
                            <span id="badge-trainer-total" class="cyber-badge" style="font-size:0.65rem; border-color:var(--neon-amber); color:#fde68a;">22 CARDS</span>
                        </div>
                        <span style="font-size:0.72rem; color:var(--text-dim); font-family:var(--font-mono);">Supporters, Items, Tools & Stadiums</span>
                    </div>
                    <div id="trainer-cards-grid" class="all-cards-grid"></div>
                </div>

                <!-- SEPARATE SECTION 3: ALL ENERGY CARDS IN DATASET -->
                <div id="section-energy-container" class="category-section-box">
                    <div class="category-section-title" style="color:var(--neon-green);">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span>⚡ ENERGY CARDS</span>
                            <span id="badge-energy-total" class="cyber-badge" style="font-size:0.65rem; border-color:var(--neon-green); color:#86efac;">9 CARDS</span>
                        </div>
                        <span style="font-size:0.72rem; color:var(--text-dim); font-family:var(--font-mono);">Basic & Special Energy</span>
                    </div>
                    <div id="energy-cards-grid" class="all-cards-grid"></div>
                </div>
            </div>

            <!-- ================= VIEW 3: 60-CARD PRE-SET ARCHETYPES ================= -->
            <div id="view-deck" class="deck-builder-panel" style="display:none;">
                <div class="column-header">
                    <div>
                        <div class="col-title" style="color: var(--neon-purple);">🏆 60-CARD PRE-SET TOURNAMENT META ARCHETYPES</div>
                        <div style="font-size: 0.85rem; color: var(--text-dim); margin-top: 4px;">
                            Choose an official tournament meta deck to inspect its full 60 cards, or instantly load & play in live match!
                        </div>
                    </div>
                    <div style="display:flex; gap:10px; flex-wrap:wrap;">
                        <button id="btn-play-archetype-deck" class="btn-action-main" style="border-color:var(--neon-green); padding:10px 18px; font-size:0.85rem;" onclick="startMatchWithCurrentDeck()">
                            ⚡ PLAY MATCH WITH THIS ARCHETYPE
                        </button>
                        <button class="btn-cyber-sm" style="background:var(--neon-amber); color:#000; font-weight:900; padding:10px 14px;" onclick="importCurrentArchetypeToCustomDeck()">
                            📋 IMPORT INTO CUSTOM BUILDER
                        </button>
                    </div>
                </div>

                <!-- ARCHETYPE TABS -->
                <div style="display:flex; gap:10px; flex-wrap:wrap; margin:16px 0;">
                    <button class="filter-chip archetype-chip active" onclick="selectArchetypePreview('charizard-ex-pidgeot', this)">🔥 Charizard ex / Pidgeot ex (Tier 1)</button>
                    <button class="filter-chip archetype-chip" onclick="selectArchetypePreview('miraidon-ex-regieleki', this)">⚡ Miraidon ex / Iron Hands ex (Tier 1)</button>
                    <button class="filter-chip archetype-chip" onclick="selectArchetypePreview('gardevoir-ex', this)">🔮 Gardevoir ex / Scream Tail (Tier 1)</button>
                    <button class="filter-chip archetype-chip" onclick="selectArchetypePreview('ai-top-60-optimized', this)">🌟 AI Top-60 Strategic Optimized</button>
                </div>

                <!-- ARCHETYPE STATS SUMMARY -->
                <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:16px;">
                    <div class="cd-stat-pill" style="border-color:var(--neon-purple); background:rgba(176,38,255,0.15);">
                        <span>🏆 ACTIVE DECK:</span>
                        <b id="arch-active-name" style="color:#fff;">Charizard ex / Pidgeot ex</b>
                    </div>
                    <div class="cd-stat-pill" style="border-color:var(--neon-cyan);">
                        <span>🎴 TOTAL:</span>
                        <b style="color:var(--neon-cyan);">60 Cards</b>
                    </div>
                    <div class="cd-stat-pill" style="border-color:#ef4444; color:#fca5a5;">
                        <span>🔴 POKÉMON:</span>
                        <b id="arch-pkmn-count" style="color:#fff;">16</b>
                    </div>
                    <div class="cd-stat-pill" style="border-color:var(--neon-amber); color:#fde68a;">
                        <span>📜 TRAINERS:</span>
                        <b id="arch-trainer-count" style="color:#fff;">30</b>
                    </div>
                    <div class="cd-stat-pill" style="border-color:var(--neon-green); color:#86efac;">
                        <span>⚡ ENERGY:</span>
                        <b id="arch-energy-count" style="color:#fff;">14</b>
                    </div>
                </div>

                <div id="deck-preview-cards" class="deck-cards-list"></div>
            </div>
        </div>

        <!-- STICKY BOTTOM AI CO-PILOT HUD -->
        <div id="sticky-ai-hud" class="sticky-ai-hud-bar">
            <div style="display: flex; align-items: center; gap: 14px;">
                <span style="font-size: 1.4rem;">🧠</span>
                <div>
                    <div style="font-family: var(--font-orbitron); font-size: 0.88rem; font-weight: 800; color: var(--neon-cyan);">
                        AI CO-PILOT HUD &bull; WIN CHANCE: <span id="hud-win-pct" style="color: var(--neon-green); font-size: 1.05rem;">--%</span>
                    </div>
                    <div id="hud-rec-text" style="font-family: var(--font-hud); font-size: 0.85rem; color: #e2f3fe; margin-top: 2px;">
                        Initializing AI Battle Analyzer Engine...
                    </div>
                </div>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <button id="hud-exec-btn" class="btn-exec-ai" onclick="executeAiRecommendation()">⚡ EXECUTE RECOMMENDED PLAY</button>
                <button class="btn-action-main" style="padding: 6px 14px; font-size: 0.78rem;" onclick="endPlayerTurn()">⏭️ END TURN</button>
            </div>
        </div>

        <script>
            // ================= POKÉMON TCG OFFICIAL DATASET CARDS (FROM CSV) =================
            const DATASET_CARDS = [
                {
                    card_id: "24", name: "Kangaskhan ex", hp: 230, supertype: "Pokémon", subtypes: ["Basic", "ex"], types: ["Colorless"],
                    weaknesses: [{ type: "Fighting", value: "x2" }], retreat: 2,
                    attacks: [
                        { name: "Comet Punch", cost: ["Colorless", "Colorless"], base_damage: 60, text: "Flip 4 coins. 30 damage for each heads." },
                        { name: "Wicked Impact", cost: ["Colorless", "Colorless", "Colorless"], base_damage: 120, text: "Deals 120 damage to opponent." }
                    ]
                },
                {
                    card_id: "26", name: "Leafeon", hp: 120, supertype: "Pokémon", subtypes: ["Stage 1"], types: ["Grass"],
                    weaknesses: [{ type: "Fire", value: "x2" }], retreat: 1,
                    attacks: [
                        { name: "Leaflet Blessings", cost: ["Colorless"], base_damage: 0, text: "Attach a Grass Energy from hand to bench." },
                        { name: "Solar Beam", cost: ["Grass", "Colorless"], base_damage: 70, text: "Deals 70 Grass damage." }
                    ]
                },
                {
                    card_id: "27", name: "Venusaur", hp: 120, supertype: "Pokémon", subtypes: ["Basic"], types: ["Grass"],
                    weaknesses: [{ type: "Fire", value: "x2" }], retreat: 2,
                    attacks: [
                        { name: "Vine Whip", cost: ["Grass"], base_damage: 40, text: "Strikes target with vines." },
                        { name: "Solar Beam", cost: ["Grass", "Grass", "Colorless"], base_damage: 100, text: "Deals 100 heavy Grass damage." }
                    ]
                },
                {
                    card_id: "29", name: "Sinistcha ex", hp: 240, supertype: "Pokémon", subtypes: ["Stage 1", "ex"], types: ["Grass"],
                    weaknesses: [{ type: "Fire", value: "x2" }], retreat: 1,
                    attacks: [
                        { name: "Re-Brew", cost: ["Colorless"], base_damage: 40, text: "Put 2 damage counters for each Energy in discard." },
                        { name: "Matcha Splash", cost: ["Grass", "Colorless"], base_damage: 120, text: "Heal 30 damage from each of your Pokémon." }
                    ]
                },
                {
                    card_id: "30", name: "Magcargo ex", hp: 270, supertype: "Pokémon", subtypes: ["Stage 1", "ex"], types: ["Fire"],
                    weaknesses: [{ type: "Water", value: "x2" }], retreat: 3,
                    attacks: [
                        { name: "Hot Magma", cost: ["Fire", "Colorless"], base_damage: 70, text: "Your opponent's Active Pokémon is now Burned." },
                        { name: "Ground Burn", cost: ["Fire", "Fire", "Colorless"], base_damage: 140, text: "Discard the top card of each player's deck." }
                    ]
                },
                {
                    card_id: "31", name: "Ninetales", hp: 120, supertype: "Pokémon", subtypes: ["Stage 1"], types: ["Fire"],
                    weaknesses: [{ type: "Water", value: "x2" }], retreat: 1,
                    attacks: [
                        { name: "Will-O-Wisp", cost: ["Fire"], base_damage: 40, text: "Burns the target." },
                        { name: "Fire Blast", cost: ["Fire", "Fire", "Colorless"], base_damage: 110, text: "Deals 110 fire damage." }
                    ]
                },
                {
                    card_id: "37", name: "Tyranitar ex", hp: 230, supertype: "Pokémon", subtypes: ["Stage 2", "ex"], types: ["Lightning"],
                    weaknesses: [{ type: "Fighting", value: "x2" }], retreat: 3,
                    attacks: [
                        { name: "Volt Cyclone", cost: ["Lightning", "Colorless", "Colorless"], base_damage: 140, text: "Move an Energy from this Pokémon to Bench." }
                    ]
                },
                {
                    card_id: "40", name: "Greninja ex", hp: 310, supertype: "Pokémon", subtypes: ["Stage 2", "ex"], types: ["Fighting"],
                    weaknesses: [{ type: "Psychic", value: "x2" }], retreat: 1,
                    attacks: [
                        { name: "Shinobi Blade", cost: ["Water"], base_damage: 170, text: "Search deck for any 1 card and put into hand." },
                        { name: "Mirage Barrage", cost: ["Water", "Colorless", "Colorless"], base_damage: 120, text: "120 damage to 2 opponent Pokémon." }
                    ]
                },
                {
                    card_id: "41", name: "Lucario", hp: 140, supertype: "Pokémon", subtypes: ["Stage 1"], types: ["Fighting"],
                    weaknesses: [{ type: "Psychic", value: "x2" }], retreat: 2,
                    attacks: [
                        { name: "Aura Sphere", cost: ["Fighting"], base_damage: 60, text: "Deals 60 damage to opponent." },
                        { name: "Close Combat", cost: ["Fighting", "Fighting", "Colorless"], base_damage: 130, text: "Deals 130 Fighting damage." }
                    ]
                },
                {
                    card_id: "44", name: "Snorlax ex", hp: 260, supertype: "Pokémon", subtypes: ["Basic", "ex"], types: ["Colorless"],
                    weaknesses: [{ type: "Fighting", value: "x2" }], retreat: 4,
                    attacks: [
                        { name: "Heavy Slam", cost: ["Colorless", "Colorless", "Colorless"], base_damage: 140, text: "Massive body slam." },
                        { name: "Hyper Beam", cost: ["Colorless", "Colorless", "Colorless", "Colorless"], base_damage: 200, text: "Devastating hyper beam attack." }
                    ]
                },
                {
                    card_id: "46", name: "Arcanine ex", hp: 230, supertype: "Pokémon", subtypes: ["Stage 1", "ex"], types: ["Fire"],
                    weaknesses: [{ type: "Water", value: "x2" }], retreat: 2,
                    attacks: [
                        { name: "Heat Blast", cost: ["Fire", "Colorless"], base_damage: 60, text: "Deals 60 damage." },
                        { name: "Raging Inferno", cost: ["Fire", "Fire", "Colorless"], base_damage: 260, text: "Devastating 260 fire explosion." }
                    ]
                },
                {
                    card_id: "49", name: "Feraligatr", hp: 180, supertype: "Pokémon", subtypes: ["Stage 2"], types: ["Water"],
                    weaknesses: [{ type: "Lightning", value: "x2" }], retreat: 3,
                    attacks: [
                        { name: "Giant Wave", cost: ["Water", "Water"], base_damage: 160, text: "Massive 160 water tsunami attack." }
                    ]
                },
                {
                    card_id: "51", name: "Palafin", hp: 150, supertype: "Pokémon", subtypes: ["Stage 1"], types: ["Water"],
                    weaknesses: [{ type: "Lightning", value: "x2" }], retreat: 2,
                    attacks: [
                        { name: "Vanguard Punch", cost: ["Water"], base_damage: 130, text: "Deals 130 damage." },
                        { name: "Double Hit", cost: ["Water", "Colorless", "Colorless"], base_damage: 90, text: "Flip 2 coins. 90 for each heads." }
                    ]
                },
                {
                    card_id: "56", name: "Gengar", hp: 130, supertype: "Pokémon", subtypes: ["Stage 2"], types: ["Psychic"],
                    weaknesses: [{ type: "Darkness", value: "x2" }], retreat: 1,
                    attacks: [
                        { name: "Shadow Ball", cost: ["Psychic", "Colorless"], base_damage: 90, text: "Put 2 damage counters on opponent's bench." }
                    ]
                },
                {
                    card_id: "58", name: "Machamp", hp: 150, supertype: "Pokémon", subtypes: ["Stage 2"], types: ["Fighting"],
                    weaknesses: [{ type: "Psychic", value: "x2" }], retreat: 3,
                    attacks: [
                        { name: "Dynamic Punch", cost: ["Fighting", "Fighting", "Colorless", "Colorless"], base_damage: 160, text: "Deals 160 brute damage." }
                    ]
                },
                {
                    card_id: "61", name: "Salamence", hp: 150, supertype: "Pokémon", subtypes: ["Stage 2"], types: ["Darkness"],
                    weaknesses: [{ type: "Grass", value: "x2" }], retreat: 2,
                    attacks: [
                        { name: "Speed Wing", cost: ["Darkness", "Colorless", "Colorless"], base_damage: 120, text: "High speed dark wing strike." }
                    ]
                },
                {
                    card_id: "62", name: "Koraidon", hp: 140, supertype: "Pokémon", subtypes: ["Basic"], types: ["Dragon"],
                    weaknesses: [], retreat: 2,
                    attacks: [
                        { name: "Shred", cost: ["Fire", "Fighting", "Colorless"], base_damage: 130, text: "Damage ignores effects on active Pokémon." }
                    ]
                },
                {
                    card_id: "63", name: "Dragonite ex", hp: 250, supertype: "Pokémon", subtypes: ["Stage 2", "ex"], types: ["Dragon"],
                    weaknesses: [], retreat: 2,
                    attacks: [
                        { name: "Dragon Pulse", cost: ["Lightning", "Fighting"], base_damage: 160, text: "Deals 160 draconic damage." }
                    ]
                },
                {
                    card_id: "75", name: "Venusaur ex", hp: 240, supertype: "Pokémon", subtypes: ["Stage 2", "ex"], types: ["Grass"],
                    weaknesses: [{ type: "Fire", value: "x2" }], retreat: 2,
                    attacks: [
                        { name: "Giant Bloom", cost: ["Grass", "Grass", "Colorless"], base_damage: 180, text: "Deals 180 solar bloom damage and heals 30 HP." }
                    ]
                },
                {
                    card_id: "79", name: "Incineroar ex", hp: 320, supertype: "Pokémon", subtypes: ["Stage 2", "ex"], types: ["Fire"],
                    weaknesses: [{ type: "Water", value: "x2" }], retreat: 2,
                    attacks: [
                        { name: "Blaze Blast", cost: ["Fire", "Colorless", "Colorless", "Colorless"], base_damage: 240, text: "Your opponent's Active Pokémon is now Burned." }
                    ]
                },
                {
                    card_id: "80", name: "Alakazam ex", hp: 220, supertype: "Pokémon", subtypes: ["Stage 2", "ex"], types: ["Psychic"],
                    weaknesses: [{ type: "Darkness", value: "x2" }], retreat: 1,
                    attacks: [
                        { name: "Psychic", cost: ["Psychic", "Colorless", "Colorless"], base_damage: 130, text: "Deals 130 psychic wave damage." }
                    ]
                },
                {
                    card_id: "101", name: "Charizard ex", hp: 330, supertype: "Pokémon", subtypes: ["Stage 2", "ex"], types: ["Fire"],
                    weaknesses: [{ type: "Grass", value: "x2" }], retreat: 2,
                    attacks: [
                        { name: "Burning Darkness", cost: ["Fire", "Fire"], base_damage: 180, text: "Deals 180 damage plus 30 for each Prize taken." },
                        { name: "Slash", cost: ["Colorless"], base_damage: 60, text: "Quick slashing claws." }
                    ]
                },
                {
                    card_id: "102", name: "Charmander", hp: 70, supertype: "Pokémon", subtypes: ["Basic"], types: ["Fire"],
                    weaknesses: [{ type: "Water", value: "x2" }], retreat: 1,
                    attacks: [
                        { name: "Scratch", cost: ["Colorless"], base_damage: 10, text: "Scratches target." },
                        { name: "Ember", cost: ["Fire", "Colorless"], base_damage: 30, text: "Discards 1 Energy from this Pokémon." }
                    ]
                },
                {
                    card_id: "103", name: "Pidgeot ex", hp: 280, supertype: "Pokémon", subtypes: ["Stage 2", "ex"], types: ["Colorless"],
                    weaknesses: [{ type: "Lightning", value: "x2" }], retreat: 0,
                    attacks: [
                        { name: "Blustery Wind", cost: ["Colorless", "Colorless"], base_damage: 120, text: "Discards any Stadium in play." }
                    ]
                },
                {
                    card_id: "104", name: "Miraidon ex", hp: 220, supertype: "Pokémon", subtypes: ["Basic", "ex"], types: ["Lightning"],
                    weaknesses: [{ type: "Fighting", value: "x2" }], retreat: 1,
                    attacks: [
                        { name: "Photon Blaster", cost: ["Lightning", "Lightning", "Colorless"], base_damage: 220, text: "Massive photon beam strike." }
                    ]
                },
                {
                    card_id: "105", name: "Raichu", hp: 120, supertype: "Pokémon", subtypes: ["Stage 1"], types: ["Lightning"],
                    weaknesses: [{ type: "Fighting", value: "x2" }], retreat: 1,
                    attacks: [
                        { name: "Thunderbolt", cost: ["Lightning", "Lightning", "Colorless"], base_damage: 120, text: "Discard all Energy from this Pokémon." }
                    ]
                },
                {
                    card_id: "106", name: "Zapdos", hp: 120, supertype: "Pokémon", subtypes: ["Basic"], types: ["Lightning"],
                    weaknesses: [{ type: "Lightning", value: "x2" }], retreat: 2,
                    attacks: [
                        { name: "Thunder", cost: ["Lightning", "Lightning", "Colorless"], base_damage: 90, text: "Deals 90 damage." }
                    ]
                },
                {
                    card_id: "107", name: "Eevee", hp: 50, supertype: "Pokémon", subtypes: ["Basic"], types: ["Colorless"],
                    weaknesses: [{ type: "Fighting", value: "x2" }], retreat: 1,
                    attacks: [
                        { name: "Quick Attack", cost: ["Colorless"], base_damage: 30, text: "Flip a coin. If heads, does +20." }
                    ]
                },
                {
                    card_id: "108", name: "Glaceon", hp: 120, supertype: "Pokémon", subtypes: ["Stage 1"], types: ["Water"],
                    weaknesses: [{ type: "Metal", value: "x2" }], retreat: 1,
                    attacks: [
                        { name: "Icicle Missile", cost: ["Water", "Colorless"], base_damage: 70, text: "Shoots icicles." }
                    ]
                },
                {
                    card_id: "109", name: "Mewtwo ex", hp: 220, supertype: "Pokémon", subtypes: ["Basic", "ex"], types: ["Psychic"],
                    weaknesses: [{ type: "Darkness", value: "x2" }], retreat: 2,
                    attacks: [
                        { name: "Psystrike", cost: ["Psychic", "Psychic", "Colorless"], base_damage: 150, text: "Unleashes telekinetic psychic burst." }
                    ]
                },
                {
                    card_id: "110", name: "Lucario", hp: 130, supertype: "Pokémon", subtypes: ["Stage 1"], types: ["Fighting"],
                    weaknesses: [{ type: "Psychic", value: "x2" }], retreat: 2,
                    attacks: [
                        { name: "Aura Sphere", cost: ["Fighting", "Colorless"], base_damage: 110, text: "Concentrated fighting aura." }
                    ]
                },
                {
                    card_id: "111", name: "Snorlax", hp: 150, supertype: "Pokémon", subtypes: ["Basic"], types: ["Colorless"],
                    weaknesses: [{ type: "Fighting", value: "x2" }], retreat: 4,
                    attacks: [
                        { name: "Heavy Impact", cost: ["Colorless", "Colorless", "Colorless"], base_damage: 130, text: "Heavy body slam." }
                    ]
                },
                // TRAINERS
                { card_id: "201", name: "Professor's Research", supertype: "Trainer", subtypes: ["Supporter"], effects: [{ text: "Discard your hand and draw 7 cards." }] },
                { card_id: "202", name: "Boss's Orders", supertype: "Trainer", subtypes: ["Supporter"], effects: [{ text: "Switch 1 of your opponent's Benched Pokémon to Active Spot." }] },
                { card_id: "203", name: "Arven", supertype: "Trainer", subtypes: ["Supporter"], effects: [{ text: "Search your deck for an Item and a Tool card." }] },
                { card_id: "204", name: "Iono", supertype: "Trainer", subtypes: ["Supporter"], effects: [{ text: "Shuffle hand into deck and draw equal to Prize cards." }] },
                { card_id: "205", name: "Ultra Ball", supertype: "Trainer", subtypes: ["Item"], effects: [{ text: "Search deck for any Pokémon card." }] },
                { card_id: "206", name: "Nest Ball", supertype: "Trainer", subtypes: ["Item"], effects: [{ text: "Search deck for a Basic Pokémon and put onto Bench." }] },
                { card_id: "207", name: "Rare Candy", supertype: "Trainer", subtypes: ["Item"], effects: [{ text: "Evolve a Basic Pokémon directly into a Stage 2 Pokémon." }] },
                { card_id: "208", name: "Switch", supertype: "Trainer", subtypes: ["Item"], effects: [{ text: "Switch your Active Pokémon with 1 of your Benched Pokémon." }] },
                // ENERGIES
                { card_id: "301", name: "Basic Fire Energy", supertype: "Energy", subtypes: ["Basic Energy"], energy_type: "Fire" },
                { card_id: "302", name: "Basic Water Energy", supertype: "Energy", subtypes: ["Basic Energy"], energy_type: "Water" },
                { card_id: "303", name: "Basic Grass Energy", supertype: "Energy", subtypes: ["Basic Energy"], energy_type: "Grass" },
                { card_id: "304", name: "Basic Lightning Energy", supertype: "Energy", subtypes: ["Basic Energy"], energy_type: "Lightning" },
                { card_id: "305", name: "Basic Psychic Energy", supertype: "Energy", subtypes: ["Basic Energy"], energy_type: "Psychic" },
                { card_id: "306", name: "Basic Fighting Energy", supertype: "Energy", subtypes: ["Basic Energy"], energy_type: "Fighting" },
                { card_id: "307", name: "Basic Darkness Energy", supertype: "Energy", subtypes: ["Basic Energy"], energy_type: "Darkness" },
                { card_id: "308", name: "Basic Metal Energy", supertype: "Energy", subtypes: ["Basic Energy"], energy_type: "Metal" }
            ];

            // Global State
            const ALL_CARDS_MAP = {};
            DATASET_CARDS.forEach(c => {
                ALL_CARDS_MAP[c.name.toLowerCase()] = c;
                ALL_CARDS_MAP[c.card_id] = c;
            });

            let CHOSEN_4_CARDS = ["Charizard ex", "Charmander", "Pidgeot ex", "Venusaur ex"];
            let OPPONENT_4_CARDS = ["Miraidon ex", "Tyranitar ex", "Raichu", "Zapdos"];
            let CURRENT_MATCH_STATE = null;
            let LATEST_AI_REC = null;
            let CUSTOM_DECK = {};
            let CURRENT_CATEGORY_FILTER = 'all';
            let CURRENT_PREVIEW_ARCHETYPE = 'charizard-ex-pidgeot';

            function getMeta(cname) {
                if (!cname) return { name: "Unknown", hp: 100, types: ["Normal"], attacks: [] };
                const clean = cname.toLowerCase().trim();
                return ALL_CARDS_MAP[clean] || { name: cname, hp: 100, types: ["Normal"], attacks: [{ name: "Strike", base_damage: 60 }] };
            }

            function getApiKey() {
                return 'tcg-live-secret-key-2026';
            }

            // ================= 1. MODE & TAB SWITCHING =================
            function switchMode(mode) {
                const vm = document.getElementById('view-match');
                const vc = document.getElementById('view-cards');
                const vd = document.getElementById('view-deck');
                const bm = document.getElementById('tab-btn-match');
                const bc = document.getElementById('tab-btn-cards');
                const bd = document.getElementById('tab-btn-deck');

                if (vm) vm.style.display = 'none';
                if (vc) vc.style.display = 'none';
                if (vd) vd.style.display = 'none';
                if (bm) bm.classList.remove('active');
                if (bc) bc.classList.remove('active');
                if (bd) bd.classList.remove('active');

                if (mode === 'match') {
                    if (vm) vm.style.display = 'block';
                    if (bm) bm.classList.add('active');
                } else if (mode === 'cards') {
                    if (vc) vc.style.display = 'block';
                    if (bc) bc.classList.add('active');
                    renderCardsDatabaseGrid();
                    updateChosen4CardsUI();
                } else if (mode === 'deck') {
                    if (vd) vd.style.display = 'block';
                    if (bd) bd.classList.add('active');
                    renderDeckBuilderPreview(CURRENT_PREVIEW_ARCHETYPE);
                }
            }

            // ================= 2. 4-CARD SELECTION DOCK =================
            function updateChosen4CardsUI() {
                for (let i = 0; i < 4; i++) {
                    const cname = CHOSEN_4_CARDS[i] || 'Empty Slot';
                    const meta = getMeta(cname);
                    const nameEl = document.getElementById(`slot-name-${i+1}`);
                    const typeEl = document.getElementById(`slot-type-${i+1}`);
                    if (nameEl) nameEl.textContent = `${cname} (${meta.hp || 70} HP)`;
                    if (typeEl) typeEl.textContent = `Type: ${(meta.types || ['Normal']).join('/')} • Top Atk: ${(meta.attacks && meta.attacks[0]) ? meta.attacks[0].base_damage + ' DMG' : 'Support'}`;
                }
            }

            function chooseCardFor4Slot(cname) {
                let idx = CHOSEN_4_CARDS.indexOf(cname);
                if (idx !== -1) {
                    alert(`ℹ️ '${cname}' is already selected in Slot #${idx+1}.`);
                    return;
                }
                CHOSEN_4_CARDS.shift();
                CHOSEN_4_CARDS.push(cname);
                updateChosen4CardsUI();
                alert(`✨ Added '${cname}' to your 4-Card Battle Deck! Current cards:\n1. ${CHOSEN_4_CARDS[0]}\n2. ${CHOSEN_4_CARDS[1]}\n3. ${CHOSEN_4_CARDS[2]}\n4. ${CHOSEN_4_CARDS[3]}`);
            }

            function dealRandom4Cards() {
                const pokemons = DATASET_CARDS.filter(c => (c.supertype || '').toLowerCase().includes('pok'));
                const shuffled = [...pokemons].sort(() => 0.5 - Math.random());
                CHOSEN_4_CARDS = shuffled.slice(0, 4).map(c => c.name);
                updateChosen4CardsUI();
            }

            function resetChosen4Cards() {
                CHOSEN_4_CARDS = ["Charizard ex", "Charmander", "Pidgeot ex", "Venusaur ex"];
                updateChosen4CardsUI();
            }

            function startBattleWithSelected4Cards() {
                if (CHOSEN_4_CARDS.length < 4) {
                    alert("⚠️ Please pick 4 cards first!");
                    return;
                }
                const oppPool = DATASET_CARDS.filter(c => (c.supertype || '').toLowerCase().includes('pok') && !CHOSEN_4_CARDS.includes(c.name));
                const oppShuffled = [...oppPool].sort(() => 0.5 - Math.random());
                OPPONENT_4_CARDS = oppShuffled.slice(0, 4).map(c => c.name);

                startNewMatch();
                switchMode('match');
            }

            // ================= 3. MATCH INITIALIZATION & STATE ENGINE =================
            function build60CardDeck(cardNames) {
                const deck = [];
                cardNames.forEach(n => {
                    for (let i = 0; i < 3; i++) deck.push(n);
                });
                const trainers = ["Professor's Research", "Boss's Orders", "Arven", "Iono", "Ultra Ball", "Nest Ball", "Rare Candy", "Switch"];
                trainers.forEach(t => {
                    for (let i = 0; i < 3; i++) deck.push(t);
                });
                while (deck.length < 60) {
                    deck.push("Basic Fire Energy");
                    if (deck.length < 60) deck.push("Basic Lightning Energy");
                    if (deck.length < 60) deck.push("Basic Water Energy");
                }
                return deck.sort(() => 0.5 - Math.random());
            }

            function startNewMatch() {
                const pDeck = build60CardDeck(CHOSEN_4_CARDS);
                const oppDeck = build60CardDeck(OPPONENT_4_CARDS);

                const pActiveMeta = getMeta(CHOSEN_4_CARDS[0]);
                const oppActiveMeta = getMeta(OPPONENT_4_CARDS[0]);

                const pHand = [pDeck.pop(), pDeck.pop(), pDeck.pop(), pDeck.pop()];
                const oppHand = [oppDeck.pop(), oppDeck.pop(), oppDeck.pop(), oppDeck.pop()];

                CURRENT_MATCH_STATE = {
                    turn_number: 1,
                    winner: null,
                    turn_flags: {
                        is_first_turn_of_game: true,
                        supporter_played_this_turn: false,
                        energy_attached_this_turn: false
                    },
                    player: {
                        active_spot: {
                            name: CHOSEN_4_CARDS[0],
                            current_hp: pActiveMeta.hp || 200,
                            max_hp: pActiveMeta.hp || 200,
                            attached_energy: ["Fire"],
                            power_boost: 0,
                            card_id: pActiveMeta.card_id
                        },
                        bench: [
                            { name: CHOSEN_4_CARDS[1], current_hp: getMeta(CHOSEN_4_CARDS[1]).hp || 70, max_hp: getMeta(CHOSEN_4_CARDS[1]).hp || 70, attached_energy: [] },
                            { name: CHOSEN_4_CARDS[2], current_hp: getMeta(CHOSEN_4_CARDS[2]).hp || 100, max_hp: getMeta(CHOSEN_4_CARDS[2]).hp || 100, attached_energy: [] },
                            { name: CHOSEN_4_CARDS[3], current_hp: getMeta(CHOSEN_4_CARDS[3]).hp || 120, max_hp: getMeta(CHOSEN_4_CARDS[3]).hp || 120, attached_energy: [] }
                        ],
                        hand: pHand,
                        deck: pDeck,
                        discard: [],
                        prizes_taken: 0
                    },
                    opponent: {
                        active_spot: {
                            name: OPPONENT_4_CARDS[0],
                            current_hp: oppActiveMeta.hp || 220,
                            max_hp: oppActiveMeta.hp || 220,
                            attached_energy: ["Lightning"],
                            card_id: oppActiveMeta.card_id
                        },
                        bench: [
                            { name: OPPONENT_4_CARDS[1], current_hp: getMeta(OPPONENT_4_CARDS[1]).hp || 100, max_hp: getMeta(OPPONENT_4_CARDS[1]).hp || 100, attached_energy: [] },
                            { name: OPPONENT_4_CARDS[2], current_hp: getMeta(OPPONENT_4_CARDS[2]).hp || 100, max_hp: getMeta(OPPONENT_4_CARDS[2]).hp || 100, attached_energy: [] },
                            { name: OPPONENT_4_CARDS[3], current_hp: getMeta(OPPONENT_4_CARDS[3]).hp || 120, max_hp: getMeta(OPPONENT_4_CARDS[3]).hp || 120, attached_energy: [] }
                        ],
                        hand: oppHand,
                        deck: oppDeck,
                        discard: [],
                        prizes_taken: 0
                    },
                    match_log: [
                        `⚔️ Esports Match Initialized: [${CHOSEN_4_CARDS[0]}] vs [${OPPONENT_4_CARDS[0]}]!`,
                        `🃏 60-Card decks shuffled. Initial 4-card hands drawn. 3-Knockout victory limit active.`
                    ]
                };

                updateMatchView(CURRENT_MATCH_STATE);
                runDynamicAiAnalysis(CURRENT_MATCH_STATE);
            }

            // ================= 4. REAL-TIME DYNAMIC AI BATTLE ANALYZER =================
            function runDynamicAiAnalysis(state) {
                if (!state || !state.player || !state.player.active_spot) return;

                const pActive = state.player.active_spot;
                const oppActive = state.opponent.active_spot;
                const pMeta = getMeta(pActive.name);
                const oppMeta = getMeta(oppActive ? oppActive.name : '');

                const pHpRatio = Math.max(0, pActive.current_hp) / Math.max(1, pActive.max_hp);
                const oppHpRatio = oppActive ? (Math.max(0, oppActive.current_hp) / Math.max(1, oppActive.max_hp)) : 0;
                const koAdvantage = (state.player.prizes_taken - state.opponent.prizes_taken) * 0.12;

                let weaknessBonus = 0;
                const pTypes = pMeta.types || ['Normal'];
                const oppWeaknesses = (oppMeta.weaknesses || []).map(w => w.type);
                if (pTypes.some(t => oppWeaknesses.includes(t))) weaknessBonus += 0.15;
                const oppTypes = oppMeta.types || ['Normal'];
                const pWeaknesses = (pMeta.weaknesses || []).map(w => w.type);
                if (oppTypes.some(t => pWeaknesses.includes(t))) weaknessBonus -= 0.12;

                const energyBonus = (pActive.attached_energy || []).length >= 2 ? 0.08 : 0.02;
                const rawProb = 0.50 + (pHpRatio * 0.25) - (oppHpRatio * 0.22) + koAdvantage + weaknessBonus + energyBonus;
                const winProb = Math.min(0.96, Math.max(0.18, rawProb));
                const winPctStr = (winProb * 100).toFixed(1) + '%';

                const candidateMoves = [];
                const attacks = pMeta.attacks || [{ name: "Strike", base_damage: 60 }];

                attacks.forEach(atk => {
                    let dmg = atk.base_damage || 50;
                    if (pActive.power_boost) dmg += pActive.power_boost;
                    let isWeak = false;
                    if (pTypes.some(t => oppWeaknesses.includes(t))) {
                        dmg *= 2;
                        isWeak = true;
                    }
                    const lethal = oppActive && (dmg >= oppActive.current_hp);
                    let score = lethal ? 95 : (dmg > 100 ? 80 : 65);
                    if (isWeak) score += 10;

                    let rationale = lethal ? `⚔️ Strike with [${atk.name}] for ${dmg} DMG! Lethal knockout—earns 1 Prize Point toward victory!` : (isWeak ? `🔥 Type Advantage: [${atk.name}] hits weakness for ${dmg} DMG!` : `⚔️ Attack with [${atk.name}] dealing ${dmg} DMG.`);

                    candidateMoves.push({
                        action_type: 'ATTACK',
                        title: `Strike: ${atk.name} (${dmg} DMG)`,
                        damage: dmg,
                        attack_name: atk.name,
                        base_damage: atk.base_damage || 50,
                        score: score,
                        win_pct: (Math.min(95, winProb * 100 + (lethal ? 6 : 2))).toFixed(1) + '%',
                        rationale: rationale
                    });
                });

                if (!state.turn_flags.energy_attached_this_turn) {
                    candidateMoves.push({
                        action_type: 'ATTACH_ENERGY',
                        title: `Attach Energy to ${pActive.name}`,
                        score: 72,
                        win_pct: (Math.min(92, winProb * 100 + 3.2)).toFixed(1) + '%',
                        rationale: `⚡ Attach Energy to Active [${pActive.name}] to satisfy high-damage attack costs.`
                    });
                }

                if (state.player.bench.length < 3) {
                    candidateMoves.push({
                        action_type: 'BENCH_POKEMON',
                        title: `Bench Reserve Pokémon`,
                        score: 60,
                        win_pct: (winProb * 100).toFixed(1) + '%',
                        rationale: `🛡️ Place a Sub Pokémon onto your Bench to guard against active knockout.`
                    });
                }

                candidateMoves.push({
                    action_type: 'CLAIM_CARD',
                    title: `Claim Card from Deck`,
                    score: 55,
                    win_pct: (winProb * 100 - 1.5).toFixed(1) + '%',
                    rationale: `🃏 Draw 1 random card to replenish hand options.`
                });

                candidateMoves.sort((a, b) => b.score - a.score);
                const topMove = candidateMoves[0];
                LATEST_AI_REC = { win_pct: winPctStr, top_move: topMove, ranked_moves: candidateMoves.slice(0, 3) };

                const leftWin = document.getElementById('left-win-pct');
                const leftAction = document.getElementById('left-rec-action');
                const leftDesc = document.getElementById('left-rec-desc');
                const leftRanked = document.getElementById('left-ranked-list');
                const hudWin = document.getElementById('hud-win-pct');
                const hudRec = document.getElementById('hud-rec-text');

                if (leftWin) { leftWin.textContent = winPctStr; leftWin.style.color = winProb > 0.55 ? 'var(--neon-green)' : (winProb > 0.40 ? 'var(--neon-cyan)' : 'var(--neon-amber)'); }
                if (leftAction) leftAction.textContent = topMove.title;
                if (leftDesc) leftDesc.textContent = topMove.rationale;
                if (leftRanked) { leftRanked.innerHTML = candidateMoves.slice(0, 3).map((m, idx) => `<div><b>${idx+1}.</b> ${m.title} &bull; <span style="color:var(--neon-green); font-weight:800;">${m.win_pct}</span></div>`).join(''); }
                if (hudWin) { hudWin.textContent = winPctStr; }
                if (hudRec) { hudRec.textContent = `Recommended: "${topMove.title}" — ${topMove.rationale.substring(0, 85)}...`; }
            }

            // ================= 5. MATCH ARENA RENDERING =================
            function updateMatchView(state) {
                if (!state) return;
                CURRENT_MATCH_STATE = state;

                const pKos = state.player.prizes_taken || 0;
                const oppKos = state.opponent.prizes_taken || 0;
                const pKoEl = document.getElementById('p-ko-count');
                const oppKoEl = document.getElementById('opp-ko-count');
                if (pKoEl) pKoEl.textContent = pKos;
                if (oppKoEl) oppKoEl.textContent = oppKos;

                const statusBanner = document.getElementById('match-status-banner');
                if (statusBanner) {
                    if (state.winner === 'Player' || pKos >= 3) {
                        statusBanner.textContent = '🏆 VICTORY: KNOCKED OUT 3 OPPONENT MAIN POKÉMON!';
                        statusBanner.style.borderColor = 'var(--neon-green)';
                        statusBanner.style.color = 'var(--neon-green)';
                    } else if (state.winner === 'Opponent' || oppKos >= 3) {
                        statusBanner.textContent = '❌ DEFEAT: YOUR 3 MAIN POKÉMON WERE KNOCKED OUT!';
                        statusBanner.style.borderColor = 'var(--neon-magenta)';
                        statusBanner.style.color = 'var(--neon-magenta)';
                    } else {
                        statusBanner.textContent = `MATCH IN PROGRESS (TURN ${state.turn_number || 1} • 3-KO LIMIT)`;
                        statusBanner.style.borderColor = 'var(--neon-cyan)';
                        statusBanner.style.color = 'var(--neon-cyan)';
                    }
                }

                const eBtn = document.getElementById('btn-add-energy-main');
                if (eBtn) {
                    const eUsed = state.turn_flags && state.turn_flags.energy_attached_this_turn;
                    eBtn.disabled = !!eUsed;
                    eBtn.textContent = eUsed ? '⚡ + ADD ENERGY (1/1 ATTACHED)' : '⚡ + ADD ENERGY (1 PER TURN)';
                    eBtn.style.opacity = eUsed ? '0.5' : '1';
                }

                const pDeckEl = document.getElementById('p-deck-count');
                const oppDeckEl = document.getElementById('opp-deck-count');
                const pDiscEl = document.getElementById('p-discard-count');
                if (pDeckEl) pDeckEl.textContent = state.player.deck ? state.player.deck.length : 45;
                if (oppDeckEl) oppDeckEl.textContent = state.opponent.deck ? state.opponent.deck.length : 45;
                if (pDiscEl) pDiscEl.textContent = (state.player.discard || []).length;

                renderActiveCard('player-active-view', state.player.active_spot, true);
                renderActiveCard('opp-active-view', state.opponent.active_spot, false);
                renderBenchGrid('player-bench-view', state.player.bench, true);
                renderBenchGrid('opp-bench-view', state.opponent.bench, false);
                renderHandGrid(state.player.hand);
                renderCombatLog(state.match_log || []);
            }

            function renderActiveCard(containerId, pkmn, isPlayer) {
                const box = document.getElementById(containerId);
                if (!box || !pkmn) return;

                const meta = getMeta(pkmn.name);
                const maxHp = pkmn.max_hp || meta.hp || 120;
                const currHp = Math.max(0, pkmn.current_hp);
                const hpPct = Math.max(0, Math.min(100, (currHp / maxHp) * 100));
                
                let attacksHtml = '';
                (meta.attacks || [{ name: "Strike", base_damage: 60 }]).forEach(atk => {
                    const cost = (atk.cost || []).map(e => `<span class="energy-pill">⚡ ${e}</span>`).join(' ') || 'Free';
                    let dmg = atk.base_damage || 0;
                    if (isPlayer && pkmn.power_boost) dmg += pkmn.power_boost;
                    const strikeBtn = isPlayer ? `<button class="btn-strike" onclick="matchAttack('${atk.name.replace(/'/g, "\\'")}', ${dmg})">⚡ STRIKE</button>` : '';

                    attacksHtml += `
                        <div class="attack-item" style="display:flex; justify-content:space-between; padding:6px; background:rgba(255,255,255,0.03);">
                            <div><div style="font-size:0.8rem; font-weight:800;">${atk.name}</div><div style="font-size:0.65rem;">Cost: [${cost}]</div></div>
                            <div><div style="color:var(--neon-amber); font-weight:900;">${dmg > 0 ? dmg + ' DMG' : 'Effect'}</div>${strikeBtn}</div>
                        </div>
                    `;
                });

                box.innerHTML = `
                    <div style="font-family:var(--font-orbitron); font-size:1rem; color:${isPlayer ? 'var(--neon-cyan)' : 'var(--neon-magenta)'}; font-weight:900;">👑 ${pkmn.name}</div>
                    <div style="font-size:0.8rem; font-weight:800;">HP: ${currHp} / ${maxHp}</div>
                    <div class="hp-track" style="height:6px; background:#111; margin:6px 0;"><div class="hp-fill" style="width:${hpPct}%; background:${hpPct < 30 ? '#ef4444' : '#34d399'}; height:100%;"></div></div>
                    <div class="energy-tray" style="font-size:0.7rem;">ENERGY: ${(pkmn.attached_energy || []).join(', ')}</div>
                    ${attacksHtml}
                `;
            }

            function renderBenchGrid(containerId, bench, isPlayer) {
                const box = document.getElementById(containerId);
                if (!box) return;
                box.innerHTML = (bench || []).map((b, i) => `<div class="bench-card" style="font-size:0.75rem; padding:6px; border:1px solid #333;">🛡️ SUB #${i+1}: ${b.name} (${b.current_hp} HP)</div>`).join('');
            }

            function renderHandGrid(hand) {
                const box = document.getElementById('player-hand-view');
                if (!box) return;
                box.innerHTML = (hand || []).map(item => {
                    const cname = typeof item === 'string' ? item : item.name;
                    return `<div class="hand-card-chip" style="font-size:0.75rem; border:1px solid var(--neon-cyan); padding:4px; margin:2px;">${cname} <button onclick="matchPlayCard('${cname}')">Play</button></div>`;
                }).join('');
            }

            function renderCombatLog(log) {
                const box = document.getElementById('combat-log');
                if (!box) return;
                box.innerHTML = log.map(l => `<div>&gt; ${l}</div>`).join('');
                box.scrollTop = box.scrollHeight;
            }

            // ================= 6. ACTIONS =================
            function claimRandomDeckCard() {
                if (!CURRENT_MATCH_STATE) return;
                const drawn = CURRENT_MATCH_STATE.player.deck.pop();
                CURRENT_MATCH_STATE.player.hand.push(drawn);
                CURRENT_MATCH_STATE.match_log.push(`🃏 Drew ${drawn}.`);
                updateMatchView(CURRENT_MATCH_STATE);
                runDynamicAiAnalysis(CURRENT_MATCH_STATE);
            }

            function matchAttack(atkName, dmg) {
                const pActive = CURRENT_MATCH_STATE.player.active_spot;
                const oppActive = CURRENT_MATCH_STATE.opponent.active_spot;
                oppActive.current_hp -= dmg;
                CURRENT_MATCH_STATE.match_log.push(`⚔️ Used ${atkName} for ${dmg} DMG.`);
                if (oppActive.current_hp <= 0) {
                    CURRENT_MATCH_STATE.player.prizes_taken += 1;
                    CURRENT_MATCH_STATE.match_log.push("🔥 Opponent KO'd!");
                }
                updateMatchView(CURRENT_MATCH_STATE);
                runDynamicAiAnalysis(CURRENT_MATCH_STATE);
            }

            function endPlayerTurn() {
                CURRENT_MATCH_STATE.turn_number += 1;
                CURRENT_MATCH_STATE.turn_flags.energy_attached_this_turn = false;
                CURRENT_MATCH_STATE.match_log.push(`⏭️ Turn ended. Drawing card.`);
                CURRENT_MATCH_STATE.player.hand.push(CURRENT_MATCH_STATE.player.deck.pop());
                updateMatchView(CURRENT_MATCH_STATE);
                runDynamicAiAnalysis(CURRENT_MATCH_STATE);
            }

            function matchPlayCard(cname) {
                CURRENT_MATCH_STATE.player.hand = CURRENT_MATCH_STATE.player.hand.filter(c => c !== cname);
                CURRENT_MATCH_STATE.match_log.push(`Played ${cname}.`);
                updateMatchView(CURRENT_MATCH_STATE);
                runDynamicAiAnalysis(CURRENT_MATCH_STATE);
            }

            function promptAddEnergyDirect() {
                CURRENT_MATCH_STATE.player.active_spot.attached_energy.push("Fire");
                CURRENT_MATCH_STATE.turn_flags.energy_attached_this_turn = true;
                updateMatchView(CURRENT_MATCH_STATE);
                runDynamicAiAnalysis(CURRENT_MATCH_STATE);
            }

            function executeAiRecommendation() {
                if (!LATEST_AI_REC || !LATEST_AI_REC.top_move) { claimRandomDeckCard(); return; }
                const top = LATEST_AI_REC.top_move;
                if (top.action_type === 'ATTACK') matchAttack(top.attack_name, top.damage);
                else if (top.action_type === 'ATTACH_ENERGY') promptAddEnergyDirect();
                else claimRandomDeckCard();
            }

            // ================= 7. 3D CARD REVEAL MODAL =================
            function show3DCardRevealModal(cardName, cardType) {
                let modal = document.getElementById('card-reveal-modal');
                if (!modal) {
                    modal = document.createElement('div');
                    modal.id = 'card-reveal-modal';
                    modal.style.cssText = 'position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.85); backdrop-filter:blur(14px); z-index:99999; display:flex; flex-direction:column; align-items:center; justify-content:center; perspective:1200px; transition:opacity 0.4s;';
                    modal.onclick = () => { modal.style.display = 'none'; };
                    document.body.appendChild(modal);
                }

                const meta = getMeta(cardName);
                const types = (meta.types || ['Normal']).join(', ');

                modal.innerHTML = `
                    <div style="font-family:var(--font-orbitron); font-size:1.4rem; color:var(--neon-cyan); margin-bottom:18px; font-weight:900; text-shadow:0 0 20px rgba(0,243,255,0.8);">
                        🃏 CARD DRAWN FROM MYSTERY DECK
                    </div>
                    <div style="width:260px; height:360px; background:linear-gradient(135deg, #0d162c, #050a14); border:2px solid var(--neon-cyan); border-radius:14px; padding:18px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 0 35px rgba(0,243,255,0.6); animation:cardFlipIn 0.8s ease-out;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-dim);">${cardType}</span>
                            <span style="font-family:var(--font-orbitron); font-size:0.85rem; color:#34d399; font-weight:800;">${meta.hp ? meta.hp + ' HP' : ''}</span>
                        </div>
                        <div style="text-align:center; padding:10px 0;">
                            <div style="font-size:3.5rem; margin-bottom:8px;">🔥</div>
                            <div style="font-family:var(--font-orbitron); font-size:1.2rem; font-weight:900; color:#fff;">${cardName}</div>
                            <div style="font-size:0.75rem; color:var(--neon-cyan); margin-top:4px;">${types}</div>
                        </div>
                        <div style="font-size:0.7rem; color:#94a3b8; text-align:center;">Click anywhere to place card in Hand</div>
                    </div>
                `;

                modal.style.display = 'flex';
                modal.style.opacity = '1';

                setTimeout(() => {
                    modal.style.opacity = '0';
                    setTimeout(() => { modal.style.display = 'none'; }, 400);
                }, 1800);
            }

            // ================= 8. CARDS DATABASE GRID =================
            function renderCardsDatabaseGrid() {
                const pkmnGrid = document.getElementById('pokemon-cards-grid');
                const trGrid = document.getElementById('trainer-cards-grid');
                const enGrid = document.getElementById('energy-cards-grid');

                if (pkmnGrid) pkmnGrid.innerHTML = '';
                if (trGrid) trGrid.innerHTML = '';
                if (enGrid) enGrid.innerHTML = '';

                DATASET_CARDS.forEach(c => {
                    const stype = (c.supertype || '').toLowerCase();
                    const div = document.createElement('div');
                    div.className = 'dataset-card-box';
                    div.style.cssText = 'background:rgba(13,22,44,0.85); border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:12px; display:flex; flex-direction:column; justify-content:space-between; margin-bottom:10px;';

                    let content = `
                        <div>
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-family:var(--font-mono); font-size:0.68rem; color:var(--text-dim);">${c.subtypes ? c.subtypes.join(' • ') : c.supertype}</span>
                                <span style="font-family:var(--font-orbitron); font-size:0.85rem; font-weight:900; color:#34d399;">${c.hp ? c.hp + ' HP' : ''}</span>
                            </div>
                            <div style="font-family:var(--font-orbitron); font-size:1rem; font-weight:900; color:#fff; margin:6px 0;">${c.name}</div>
                            <div style="font-size:0.75rem; color:var(--neon-cyan); margin-bottom:6px;">Type: ${(c.types || []).join(', ') || 'Colorless'}</div>
                    `;

                    (c.attacks || []).forEach(atk => {
                        content += `
                            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); border-radius:4px; padding:4px 6px; margin-top:4px; display:flex; justify-content:space-between; font-size:0.75rem;">
                                <span>${atk.name}</span>
                                <b style="color:var(--neon-amber);">${atk.base_damage ? atk.base_damage + ' DMG' : 'Effect'}</b>
                            </div>
                        `;
                    });

                    content += `</div>`;

                    if (stype.includes('pok')) {
                        content += `
                            <div style="margin-top:12px;">
                                <button class="btn-action-main btn-choose-card" style="width:100%; font-size:0.75rem; padding:6px 10px; border-color:var(--neon-cyan); text-align:center;">🎯 CHOOSE FOR 4-CARD BATTLE</button>
                            </div>
                        `;
                    }

                    div.innerHTML = content;
                    const btn = div.querySelector('.btn-choose-card');
                    if (btn) btn.onclick = () => chooseCardFor4Slot(c.name);

                    if (stype.includes('pok') && pkmnGrid) pkmnGrid.appendChild(div);
                    else if (stype.includes('trainer') && trGrid) trGrid.appendChild(div);
                    else if (stype.includes('energy') && enGrid) enGrid.appendChild(div);
                });
            }

            function filterCardsDatabase() {
                const input = document.getElementById('cards-search-input');
                const query = input ? input.value.toLowerCase().trim() : '';
                document.querySelectorAll('.dataset-card-box').forEach(el => {
                    const text = el.textContent.toLowerCase();
                    el.style.display = text.includes(query) ? 'flex' : 'none';
                });
            }

            function setCardCategoryFilter(cat, btnEl) {
                document.querySelectorAll('.filter-chip').forEach(b => b.classList.remove('active'));
                if (btnEl) btnEl.classList.add('active');

                const sp = document.getElementById('section-pokemon-container');
                const st = document.getElementById('section-trainer-container');
                const se = document.getElementById('section-energy-container');

                if (cat === 'all') {
                    if (sp) sp.style.display = 'block';
                    if (st) st.style.display = 'block';
                    if (se) se.style.display = 'block';
                } else if (cat === 'pokemon') {
                    if (sp) sp.style.display = 'block';
                    if (st) st.style.display = 'none';
                    if (se) se.style.display = 'none';
                } else if (cat === 'trainer') {
                    if (sp) sp.style.display = 'none';
                    if (st) st.style.display = 'block';
                    if (se) se.style.display = 'none';
                } else if (cat === 'energy') {
                    if (sp) sp.style.display = 'none';
                    if (st) st.style.display = 'none';
                    if (se) se.style.display = 'block';
                }
            }

            // ================= 9. META PRESETS =================
            function renderDeckBuilderPreview(deckId) {
                CURRENT_PREVIEW_ARCHETYPE = deckId;
                const nameEl = document.getElementById('arch-active-name');
                if (nameEl) nameEl.textContent = deckId.replace(/-/g, ' ').toUpperCase();
            }

            function selectArchetypePreview(deckId, btnEl) {
                document.querySelectorAll('.archetype-chip').forEach(b => b.classList.remove('active'));
                if (btnEl) btnEl.classList.add('active');
                renderDeckBuilderPreview(deckId);
            }

            function startMatchWithCurrentDeck() {
                if (CURRENT_PREVIEW_ARCHETYPE === 'miraidon-ex-regieleki') {
                    CHOSEN_4_CARDS = ["Miraidon ex", "Tyranitar ex", "Raichu", "Zapdos"];
                    OPPONENT_4_CARDS = ["Charizard ex", "Charmander", "Pidgeot ex", "Venusaur ex"];
                } else if (CURRENT_PREVIEW_ARCHETYPE === 'gardevoir-ex') {
                    CHOSEN_4_CARDS = ["Mewtwo ex", "Gengar", "Alakazam ex", "Kangaskhan ex"];
                    OPPONENT_4_CARDS = ["Salamence", "Dragonite ex", "Lucario", "Machamp"];
                } else {
                    CHOSEN_4_CARDS = ["Charizard ex", "Charmander", "Pidgeot ex", "Venusaur ex"];
                    OPPONENT_4_CARDS = ["Miraidon ex", "Tyranitar ex", "Raichu", "Zapdos"];
                }
                startNewMatch();
                switchMode('match');
            }

            function initApp() {
                const bm = document.getElementById('tab-btn-match');
                const bc = document.getElementById('tab-btn-cards');
                const bd = document.getElementById('tab-btn-deck');
                if (bm) bm.onclick = () => switchMode('match');
                if (bc) bc.onclick = () => switchMode('cards');
                if (bd) bd.onclick = () => switchMode('deck');

                startNewMatch();
                renderCardsDatabaseGrid();
                updateChosen4CardsUI();
            }

            window.initApp = initApp;
            window.switchMode = switchMode;
            window.chooseCardFor4Slot = chooseCardFor4Slot;
            window.dealRandom4Cards = dealRandom4Cards;
            window.resetChosen4Cards = resetChosen4Cards;
            window.startBattleWithSelected4Cards = startBattleWithSelected4Cards;
            window.claimRandomDeckCard = claimRandomDeckCard;
            window.matchAttack = matchAttack;
            window.endPlayerTurn = endPlayerTurn;
            window.executeAiRecommendation = executeAiRecommendation;
            window.promptAddEnergyDirect = promptAddEnergyDirect;
            window.getApiKey = getApiKey;
            window.renderCardsDatabaseGrid = renderCardsDatabaseGrid;
            window.filterCardsDatabase = filterCardsDatabase;
            window.setCardCategoryFilter = setCardCategoryFilter;
            window.selectArchetypePreview = selectArchetypePreview;
            window.startMatchWithCurrentDeck = startMatchWithCurrentDeck;
            window.onload = initApp;
        </script>
    </body>
    </html>
    """


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
