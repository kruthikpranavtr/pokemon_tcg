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
        raise HTTPException(status_code=400, detail="No legal actions available in given game state.")

    # 1. Multi-Modal GNN Board Encoding
    h_board, gnn_telemetry = gnn_model.forward(game_state, card_images)

    # 2. Match Sequence Transformer Forward Pass
    transformer_policy, base_transformer_win_prob, transformer_telemetry = transformer_model.forward(h_board)

    # 3. Monte Carlo Tree Search (MCTS) with Terminal Verification
    ranked_mcts_moves, grounded_mcts_win_prob, mcts_telemetry = mcts_engine.run_mcts_search(
        root_state=game_state,
        num_simulations=mcts_simulations
    )

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
                <button id="tab-btn-cards" class="tab-btn" onclick="switchMode('cards')">🃏 ALL CARDS & CUSTOM DECK BUILDER (60 CARDS)</button>
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
                            <div id="left-win-pct" class="win-rate-val">56.4%</div>
                        </div>
                        
                        <div class="rec-move-card">
                            <div style="font-family:var(--font-orbitron); font-size:0.75rem; color:var(--neon-cyan); margin-bottom:4px;">TOP RECOMMENDED ACTION</div>
                            <div id="left-rec-action" style="font-family:var(--font-orbitron); font-size:0.95rem; font-weight:800; color:#fff;">Play Supporter: Arven</div>
                            <div id="left-rec-desc" style="font-size:0.8rem; color:#cbd5e1; margin-top:6px; line-height:1.3;">Scanning deck draw odds and energy race...</div>
                        </div>

                        <div class="rec-move-card">
                            <div style="font-family:var(--font-orbitron); font-size:0.75rem; color:var(--neon-amber); margin-bottom:6px;">TOP RANKED PLAYS</div>
                            <div id="left-ranked-list" style="font-size:0.78rem; display:flex; flex-direction:column; gap:6px;">
                                <div>1. Play Supporter (Arven) - 56.4%</div>
                                <div>2. Attach Energy - 52.1%</div>
                                <div>3. Bench Basic - 50.0%</div>
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
                        AI CO-PILOT HUD &bull; WIN CHANCE: <span id="hud-win-pct" style="color: var(--neon-green); font-size: 1.05rem;">56.4%</span>
                    </div>
                    <div id="hud-rec-text" style="font-family: var(--font-hud); font-size: 0.85rem; color: #e2f3fe; margin-top: 2px;">
                        Recommended: "Play Supporter"
                    </div>
                </div>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <button id="hud-exec-btn" class="btn-exec-ai" onclick="executeAiRecommendation()">⚡ EXECUTE RECOMMENDED PLAY</button>
                <button class="btn-action-main" style="padding: 6px 14px; font-size: 0.78rem;" onclick="endPlayerTurn()">⏭️ END TURN</button>
            </div>
        </div>

        <script>
            let ALL_CARDS_MAP = {};
            let ALL_CARDS_ARRAY = [];
            let ALL_DECKS_MAP = {};
            let CURRENT_MATCH_STATE = null;
            let LATEST_AI_REC = null;
            let CUSTOM_DECK = {}; // cardName -> count
            let CURRENT_CATEGORY_FILTER = 'all';
            let CURRENT_PREVIEW_ARCHETYPE = 'charizard-ex-pidgeot';

            async function initApp() {
                try {
                    const [cRes, dRes] = await Promise.all([
                        fetch('/api/v1/cards/all'),
                        fetch('/api/v1/decks/all')
                    ]);
                    if (cRes.ok) {
                        const data = await cRes.json();
                        ALL_CARDS_ARRAY = data.cards || [];
                        ALL_CARDS_ARRAY.forEach(c => { 
                            if (c && c.name) {
                                ALL_CARDS_MAP[c.name.toLowerCase()] = c; 
                                ALL_CARDS_MAP[c.card_id] = c; 
                            }
                        });
                    }
                    if (dRes.ok) {
                        const dData = await dRes.json();
                        ALL_DECKS_MAP = dData.decks || {};
                        renderDeckBuilderPreview('charizard-ex-pidgeot');
                    }
                } catch(e) {
                    console.error("Init failed:", e);
                }

                // Explicitly bind navigation buttons for instant response
                const btnMatch = document.getElementById('tab-btn-match');
                const btnCards = document.getElementById('tab-btn-cards');
                const btnDeck = document.getElementById('tab-btn-deck');
                if (btnMatch) btnMatch.onclick = () => switchMode('match');
                if (btnCards) btnCards.onclick = () => switchMode('cards');
                if (btnDeck) btnDeck.onclick = () => switchMode('deck');

                startNewMatch();
            }

            window.addEventListener('DOMContentLoaded', initApp);

            function getMeta(nameOrId) {
                if (!nameOrId) return {};
                return ALL_CARDS_MAP[nameOrId.toLowerCase()] || ALL_CARDS_MAP[nameOrId] || {};
            }

            function switchMode(mode) {
                console.log("Switching view mode to:", mode);
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                const vm = document.getElementById('view-match');
                const vc = document.getElementById('view-cards');
                const vd = document.getElementById('view-deck');
                
                if (vm) vm.style.display = 'none';
                if (vc) vc.style.display = 'none';
                if (vd) vd.style.display = 'none';

                if (mode === 'match') {
                    const btn = document.getElementById('tab-btn-match');
                    if (btn) btn.classList.add('active');
                    if (vm) vm.style.display = 'block';
                } else if (mode === 'cards') {
                    const btn = document.getElementById('tab-btn-cards');
                    if (btn) btn.classList.add('active');
                    if (vc) vc.style.display = 'flex';
                    renderAllCardsDatabase();
                } else if (mode === 'deck') {
                    const btn = document.getElementById('tab-btn-deck');
                    if (btn) btn.classList.add('active');
                    if (vd) vd.style.display = 'block';
                    renderDeckBuilderPreview(CURRENT_PREVIEW_ARCHETYPE || 'charizard-ex-pidgeot');
                }
            }

            async function selectArchetypePreview(deckId, btnEl) {
                CURRENT_PREVIEW_ARCHETYPE = deckId;
                document.querySelectorAll('.archetype-chip').forEach(b => b.classList.remove('active'));
                if (btnEl) btnEl.classList.add('active');
                await renderDeckBuilderPreview(deckId);
            }

            async function renderDeckBuilderPreview(deckId) {
                if (!deckId) deckId = CURRENT_PREVIEW_ARCHETYPE || 'charizard-ex-pidgeot';
                CURRENT_PREVIEW_ARCHETYPE = deckId;

                if (!ALL_DECKS_MAP || Object.keys(ALL_DECKS_MAP).length === 0) {
                    try {
                        const res = await fetch('/api/v1/decks/all');
                        if (res.ok) {
                            const data = await res.json();
                            ALL_DECKS_MAP = data.decks || {};
                        }
                    } catch(e) {
                        console.error("Failed to load decks:", e);
                    }
                }

                const d = ALL_DECKS_MAP[deckId];
                const box = document.getElementById('deck-preview-cards');
                if (!d || !box) return;

                const nameEl = document.getElementById('arch-active-name');
                if (nameEl) nameEl.textContent = d.name || deckId;

                let pkmnCnt = 0, trCnt = 0, enCnt = 0;
                box.innerHTML = '';

                (d.deck_list || []).forEach(item => {
                    const cname = item.name;
                    const count = item.count || 1;
                    const meta = getMeta(cname);
                    const stype = (meta.supertype || '').toLowerCase();
                    
                    let badgeColor = 'rgba(0,243,255,0.2)';
                    let badgeBorder = 'var(--neon-cyan)';
                    let badgeText = 'Pokémon';
                    let icon = '🔥';

                    if (stype.includes('trainer')) {
                        trCnt += count;
                        badgeColor = 'rgba(255,170,0,0.2)';
                        badgeBorder = 'var(--neon-amber)';
                        badgeText = 'Trainer';
                        icon = '📜';
                    } else if (stype.includes('energy')) {
                        enCnt += count;
                        badgeColor = 'rgba(0,255,136,0.2)';
                        badgeBorder = 'var(--neon-green)';
                        badgeText = 'Energy';
                        icon = '⚡';
                    } else {
                        pkmnCnt += count;
                        badgeColor = 'rgba(239,68,68,0.2)';
                        badgeBorder = '#ef4444';
                        badgeText = 'Pokémon';
                        icon = '🔥';
                    }

                    const cardDiv = document.createElement('div');
                    cardDiv.className = 'deck-card-item';
                    cardDiv.innerHTML = `
                        <div style="display:flex; align-items:center; gap:10px;">
                            <div style="font-size:1.4rem;">${icon}</div>
                            <div>
                                <div style="font-family:var(--font-orbitron); font-size:0.85rem; font-weight:800; color:#fff;">${cname}</div>
                                <div style="font-size:0.72rem; color:var(--text-dim); margin-top:2px;">${count}x in Deck</div>
                            </div>
                        </div>
                        <span class="cyber-badge" style="font-size:0.65rem; padding:3px 8px; background:${badgeColor}; border-color:${badgeBorder};">${badgeText.toUpperCase()}</span>
                    `;
                    box.appendChild(cardDiv);
                });

                const pEl = document.getElementById('arch-pkmn-count');
                const tEl = document.getElementById('arch-trainer-count');
                const eEl = document.getElementById('arch-energy-count');
                if (pEl) pEl.textContent = pkmnCnt;
                if (tEl) tEl.textContent = trCnt;
                if (eEl) eEl.textContent = enCnt;
            }

            function importCurrentArchetypeToCustomDeck() {
                const d = ALL_DECKS_MAP[CURRENT_PREVIEW_ARCHETYPE || 'charizard-ex-pidgeot'];
                if (!d || !d.deck_list) return;
                CUSTOM_DECK = {};
                d.deck_list.forEach(item => {
                    CUSTOM_DECK[item.name] = item.count;
                });
                alert(`📋 Imported 60 cards from '${d.name}' into your Custom Deck Builder! Switching to Custom Deck tab.`);
                switchMode('cards');
                updateCustomDeckUI();
            }

            function setCardCategoryFilter(category, btnEl) {
                CURRENT_CATEGORY_FILTER = category;
                document.querySelectorAll('.cards-filter-bar .filter-chip').forEach(b => b.classList.remove('active'));
                if (btnEl) btnEl.classList.add('active');
                renderAllCardsDatabase();
            }

            function filterCardsDatabase() {
                renderAllCardsDatabase();
            }

            function createCardBoxElement(c) {
                const cname = c.name || 'Card';
                const cid = c.card_id || '0';
                const stype = c.supertype || 'Card';
                const subtypes = (c.subtypes || []).join(' • ');
                const inDeck = CUSTOM_DECK[cname] || 0;
                
                const isPok = stype.toLowerCase().includes('pok');
                const isTrainer = stype.toLowerCase().includes('trainer');
                const isEnergy = stype.toLowerCase().includes('energy');

                let typeBadge = '';
                let hpBadge = '';
                let abilityHtml = '';
                let attacksHtml = '';

                if (isPok) {
                    const types = (c.types || []).join(', ') || 'Colorless';
                    typeBadge = `<span class="card-type-tag" style="background:rgba(239,68,68,0.2); border-color:#ef4444; color:#fca5a5;">${types}</span>`;
                    hpBadge = `<span style="font-family:var(--font-orbitron); font-size:0.85rem; font-weight:900; color:#34d399;">${c.hp || 70} HP</span>`;

                    (c.abilities || []).forEach(ab => {
                        abilityHtml += `
                            <div style="background:rgba(176,38,255,0.15); border:1px solid var(--neon-purple); border-radius:5px; padding:6px; margin:6px 0; font-size:0.72rem;">
                                <span style="font-family:var(--font-orbitron); color:var(--neon-purple); font-weight:800;">⚡ ABILITY: ${ab.name || 'Ability'}</span>
                                <div style="color:#cbd5e1; margin-top:2px;">${ab.effect || ''}</div>
                            </div>
                        `;
                    });

                    (c.attacks || []).forEach(atk => {
                        const cost = (atk.cost || []).map(e => `<span class="energy-pill" style="font-size:0.6rem; padding:1px 4px;">⚡ ${e}</span>`).join(' ') || '<span style="font-size:0.65rem; color:#94a3b8;">Free</span>';
                        attacksHtml += `
                            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-radius:5px; padding:6px; margin-top:5px; display:flex; justify-content:space-between; align-items:center; gap:6px;">
                                <div style="flex:1;">
                                    <div style="font-family:var(--font-orbitron); font-size:0.78rem; font-weight:700; color:#fff;">${atk.name || 'Attack'}</div>
                                    <div style="margin-top:2px;">${cost}</div>
                                    ${atk.text ? `<div style="font-size:0.68rem; color:#94a3b8; margin-top:2px;">${atk.text}</div>` : ''}
                                </div>
                                <div style="font-family:var(--font-orbitron); font-size:0.95rem; font-weight:900; color:var(--neon-amber);">${atk.base_damage ? atk.base_damage + ' DMG' : 'Effect'}</div>
                            </div>
                        `;
                    });
                } else if (isTrainer) {
                    typeBadge = `<span class="card-type-tag" style="background:rgba(255,170,0,0.2); border-color:var(--neon-amber); color:#fde68a;">📜 Trainer</span>`;
                    (c.effects || []).forEach(eff => {
                        attacksHtml += `<div style="font-size:0.75rem; color:#cbd5e1; margin-top:6px; line-height:1.3;">${eff.text || ''}</div>`;
                    });
                } else if (isEnergy) {
                    typeBadge = `<span class="card-type-tag" style="background:rgba(0,255,136,0.2); border-color:var(--neon-green); color:#86efac;">⚡ Energy</span>`;
                    attacksHtml = `<div style="font-size:0.75rem; color:#86efac; margin-top:6px;">Provides 1 Energy attachment for matching Pokémon attack requirements.</div>`;
                }

                const div = document.createElement('div');
                div.className = 'dataset-card-box ' + (inDeck > 0 ? 'in-deck-active' : '');
                div.setAttribute('data-card-name', cname);
                div.innerHTML = `
                    <div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <span style="font-size:0.65rem; color:var(--text-dim); font-family:var(--font-mono);">#${cid} &bull; ${subtypes || stype}</span>
                            <div style="display:flex; gap:6px; align-items:center;">
                                ${hpBadge}
                                ${typeBadge}
                            </div>
                        </div>
                        <div style="font-family:var(--font-orbitron); font-size:1.05rem; font-weight:800; color:#fff; margin-bottom:6px;">
                            ${cname}
                        </div>
                        ${abilityHtml}
                        ${attacksHtml}
                    </div>
                    
                    <div style="margin-top:12px; border-top:1px solid rgba(255,255,255,0.1); padding-top:10px;">
                        <div class="card-deck-stepper">
                            <button class="stepper-btn btn-step-minus" title="Remove 1 copy">-</button>
                            <span class="stepper-count-badge cd-card-badge">${inDeck} in Deck</span>
                            <button class="stepper-btn btn-step-plus" title="Add 1 copy">+</button>
                        </div>
                        <button class="btn-quick-add btn-card-add-main">+ SELECT / ADD TO DECK</button>
                    </div>
                `;

                const minusBtn = div.querySelector('.btn-step-minus');
                const plusBtn = div.querySelector('.btn-step-plus');
                const addMainBtn = div.querySelector('.btn-card-add-main');

                if (minusBtn) minusBtn.onclick = () => changeCardCountInDeck(cname, -1);
                if (plusBtn) plusBtn.onclick = () => changeCardCountInDeck(cname, 1);
                if (addMainBtn) addMainBtn.onclick = () => changeCardCountInDeck(cname, 1);

                return div;
            }

            let POKEMON_DISPLAY_LIMIT = 60;

            function loadMorePokemon() {
                POKEMON_DISPLAY_LIMIT += 60;
                renderAllCardsDatabase();
            }

            function showAllPokemon() {
                POKEMON_DISPLAY_LIMIT = 99999;
                renderAllCardsDatabase();
            }

            async function renderAllCardsDatabase() {
                if (ALL_CARDS_ARRAY.length === 0) {
                    try {
                        const res = await fetch('/api/v1/cards/all');
                        if (res.ok) {
                            const data = await res.json();
                            ALL_CARDS_ARRAY = data.cards || [];
                            ALL_CARDS_ARRAY.forEach(c => { 
                                if (c && c.name) {
                                    ALL_CARDS_MAP[c.name.toLowerCase()] = c; 
                                    ALL_CARDS_MAP[c.card_id] = c; 
                                }
                            });
                        }
                    } catch(e) {
                        console.error("Failed to load cards:", e);
                    }
                }
                
                const searchInput = document.getElementById('cards-search-input');
                const searchVal = searchInput ? searchInput.value.toLowerCase().trim() : '';

                const pkmnGrid = document.getElementById('pokemon-cards-grid');
                const trainerGrid = document.getElementById('trainer-cards-grid');
                const energyGrid = document.getElementById('energy-cards-grid');

                const pkmnSec = document.getElementById('section-pokemon-container');
                const trainerSec = document.getElementById('section-trainer-container');
                const energySec = document.getElementById('section-energy-container');
                const loadMoreBox = document.getElementById('pokemon-load-more-box');

                if (pkmnGrid) pkmnGrid.innerHTML = '';
                if (trainerGrid) trainerGrid.innerHTML = '';
                if (energyGrid) energyGrid.innerHTML = '';

                // Show/hide section containers according to category filter
                if (pkmnSec) pkmnSec.style.display = (CURRENT_CATEGORY_FILTER === 'all' || CURRENT_CATEGORY_FILTER === 'pokemon') ? 'flex' : 'none';
                if (trainerSec) trainerSec.style.display = (CURRENT_CATEGORY_FILTER === 'all' || CURRENT_CATEGORY_FILTER === 'trainer') ? 'flex' : 'none';
                if (energySec) energySec.style.display = (CURRENT_CATEGORY_FILTER === 'all' || CURRENT_CATEGORY_FILTER === 'energy') ? 'flex' : 'none';

                let pkmnTotal = 0, pkmnRendered = 0, trainerCount = 0, energyCount = 0;

                ALL_CARDS_ARRAY.forEach(c => {
                    if (!c) return;
                    const stype = (c.supertype || '').toLowerCase();
                    const isPok = stype.includes('pok');
                    const isTrainer = stype.includes('trainer');
                    const isEnergy = stype.includes('energy');

                    if (searchVal) {
                        const nameMatch = (c.name || '').toLowerCase().includes(searchVal);
                        const idMatch = (c.card_id || '').toLowerCase().includes(searchVal);
                        const typeMatch = Array.isArray(c.types) && c.types.some(t => typeof t === 'string' && t.toLowerCase().includes(searchVal));
                        const subtypeMatch = Array.isArray(c.subtypes) && c.subtypes.some(s => typeof s === 'string' && s.toLowerCase().includes(searchVal));
                        const attackMatch = Array.isArray(c.attacks) && c.attacks.some(a => a && ((a.name || '').toLowerCase().includes(searchVal) || (a.text || '').toLowerCase().includes(searchVal)));
                        const abilityMatch = Array.isArray(c.abilities) && c.abilities.some(ab => ab && ((ab.name || '').toLowerCase().includes(searchVal) || (ab.effect || '').toLowerCase().includes(searchVal)));
                        if (!nameMatch && !idMatch && !typeMatch && !subtypeMatch && !attackMatch && !abilityMatch) return;
                    }

                    if (isPok) {
                        pkmnTotal++;
                        if (searchVal || pkmnRendered < POKEMON_DISPLAY_LIMIT) {
                            if (pkmnGrid) {
                                pkmnGrid.appendChild(createCardBoxElement(c));
                                pkmnRendered++;
                            }
                        }
                    } else if (isTrainer && trainerGrid) {
                        trainerGrid.appendChild(createCardBoxElement(c));
                        trainerCount++;
                    } else if (isEnergy && energyGrid) {
                        energyGrid.appendChild(createCardBoxElement(c));
                        energyCount++;
                    } else if (pkmnGrid) {
                        pkmnTotal++;
                        if (searchVal || pkmnRendered < POKEMON_DISPLAY_LIMIT) {
                            pkmnGrid.appendChild(createCardBoxElement(c));
                            pkmnRendered++;
                        }
                    }
                });

                const bPk = document.getElementById('badge-pkmn-total');
                const bTr = document.getElementById('badge-trainer-total');
                const bEn = document.getElementById('badge-energy-total');
                if (bPk) bPk.textContent = `${pkmnTotal} CARDS`;
                if (bTr) bTr.textContent = `${trainerCount} CARDS`;
                if (bEn) bEn.textContent = `${energyCount} CARDS`;

                if (loadMoreBox) {
                    if (searchVal || pkmnRendered >= pkmnTotal) {
                        loadMoreBox.style.display = 'none';
                    } else {
                        loadMoreBox.style.display = 'flex';
                    }
                }

                if (pkmnGrid && pkmnGrid.children.length === 0) {
                    pkmnGrid.innerHTML = '<div style="grid-column: 1/-1; color:var(--text-dim); padding:10px; font-size:0.8rem;">No Pokémon cards match current query.</div>';
                }
                if (trainerGrid && trainerGrid.children.length === 0) {
                    trainerGrid.innerHTML = '<div style="grid-column: 1/-1; color:var(--text-dim); padding:10px; font-size:0.8rem;">No Trainer cards match current query.</div>';
                }
                if (energyGrid && energyGrid.children.length === 0) {
                    energyGrid.innerHTML = '<div style="grid-column: 1/-1; color:var(--text-dim); padding:10px; font-size:0.8rem;">No Energy cards match current query.</div>';
                }

                updateCustomDeckUI();
            }

            function changeCardCountInDeck(cardName, delta) {
                const meta = getMeta(cardName);
                const isBasicEnergy = (meta.supertype || '').toLowerCase().includes('energy') && ((meta.subtypes || []).map(s => s.toLowerCase()).includes('basic') || cardName.toLowerCase().includes('basic'));
                const maxPerCard = isBasicEnergy ? 60 : 4;
                
                const currCount = CUSTOM_DECK[cardName] || 0;
                const totalCount = Object.values(CUSTOM_DECK).reduce((a, b) => a + b, 0);

                if (delta > 0) {
                    if (totalCount >= 60) {
                        alert("⚠️ Deck Limit Reached: Your custom deck already contains 60 cards (maximum allowed).");
                        return;
                    }
                    if (currCount >= maxPerCard) {
                        alert(`⚠️ Copy Limit: You can include at most ${maxPerCard} copies of '${cardName}' in a Standard 60-card deck.`);
                        return;
                    }
                    CUSTOM_DECK[cardName] = currCount + 1;
                } else if (delta < 0) {
                    if (currCount > 1) {
                        CUSTOM_DECK[cardName] = currCount - 1;
                    } else {
                        delete CUSTOM_DECK[cardName];
                    }
                }
                updateCustomDeckUI();
            }

            function updateCustomDeckUI() {
                let total = 0;
                let pkmnCount = 0;
                let trainerCount = 0;
                let energyCount = 0;
                let distinctCount = 0;

                const chipsBox = document.getElementById('chosen-deck-chips');
                if (chipsBox) chipsBox.innerHTML = '';

                for (const [cname, cnt] of Object.entries(CUSTOM_DECK)) {
                    if (cnt <= 0) continue;
                    total += cnt;
                    distinctCount++;
                    const meta = getMeta(cname);
                    const stype = (meta.supertype || '').toLowerCase();
                    if (stype.includes('pok')) pkmnCount += cnt;
                    else if (stype.includes('trainer')) trainerCount += cnt;
                    else if (stype.includes('energy')) energyCount += cnt;
                    else pkmnCount += cnt;

                    if (chipsBox) {
                        const chip = document.createElement('div');
                        chip.className = 'deck-chip-item';
                        chip.innerHTML = `
                            <span>${cname} <b>x${cnt}</b></span>
                            <div style="display:flex; gap:3px;">
                                <button class="deck-chip-btn btn-chip-minus" title="Remove 1">-</button>
                                <button class="deck-chip-btn btn-chip-plus" style="border-color:var(--neon-cyan); color:#38bdf8;" title="Add 1">+</button>
                            </div>
                        `;
                        const mBtn = chip.querySelector('.btn-chip-minus');
                        const pBtn = chip.querySelector('.btn-chip-plus');
                        if (mBtn) mBtn.onclick = () => changeCardCountInDeck(cname, -1);
                        if (pBtn) pBtn.onclick = () => changeCardCountInDeck(cname, 1);

                        chipsBox.appendChild(chip);
                    }
                }

                if (chipsBox && distinctCount === 0) {
                    chipsBox.innerHTML = '<div style="color:var(--text-dim); font-size:0.75rem; padding:6px;">Your custom deck is currently empty. Use the select options on any card below to add cards!</div>';
                }

                const distEl = document.getElementById('chosen-distinct-count');
                if (distEl) distEl.textContent = distinctCount;

                const totalEl = document.getElementById('cd-total-count');
                const pkmnEl = document.getElementById('cd-pkmn-count');
                const trEl = document.getElementById('cd-trainer-count');
                const enEl = document.getElementById('cd-energy-count');
                const progEl = document.getElementById('cd-progress-fill');
                const playBtn = document.getElementById('btn-play-custom-deck');

                if (totalEl) totalEl.textContent = total;
                if (pkmnEl) pkmnEl.textContent = pkmnCount;
                if (trEl) trEl.textContent = trainerCount;
                if (enEl) enEl.textContent = energyCount;

                if (progEl) {
                    progEl.style.width = Math.min(100, (total / 60) * 100) + '%';
                    if (total === 60) progEl.className = 'hp-fill';
                    else progEl.className = 'hp-fill warning';
                }

                if (playBtn) {
                    if (total === 60) {
                        playBtn.disabled = false;
                        playBtn.style.boxShadow = 'var(--neon-green-glow)';
                        playBtn.style.borderColor = 'var(--neon-green)';
                        playBtn.textContent = '⚔️ PLAY MATCH WITH THIS 60-CARD DECK (READY!)';
                    } else {
                        playBtn.disabled = false;
                        playBtn.textContent = `⚔️ PLAY MATCH WITH THIS DECK (${total}/60 CARDS)`;
                    }
                }

                document.querySelectorAll('.dataset-card-box').forEach(el => {
                    const cname = el.getAttribute('data-card-name');
                    const badge = el.querySelector('.cd-card-badge');
                    const count = CUSTOM_DECK[cname] || 0;
                    if (badge) {
                        badge.textContent = `${count} in Deck`;
                        badge.style.color = count > 0 ? 'var(--neon-green)' : '#38bdf8';
                    }
                    if (count > 0) el.classList.add('in-deck-active');
                    else el.classList.remove('in-deck-active');
                });
            }

            function autoFillBasicEnergy() {
                const total = Object.values(CUSTOM_DECK).reduce((a, b) => a + b, 0);
                if (total >= 60) {
                    alert("Deck already contains 60 cards!");
                    return;
                }
                const needed = 60 - total;
                CUSTOM_DECK['Basic Fire Energy'] = (CUSTOM_DECK['Basic Fire Energy'] || 0) + needed;
                updateCustomDeckUI();
            }

            function clearCustomDeck() {
                CUSTOM_DECK = {};
                updateCustomDeckUI();
            }

            async function startMatchWithCustomDeck() {
                const flatDeck = [];
                for (const [cname, cnt] of Object.entries(CUSTOM_DECK)) {
                    for (let i = 0; i < cnt; i++) flatDeck.push(cname);
                }
                if (flatDeck.length === 0) {
                    alert("⚠️ Please add cards to your custom deck before starting!");
                    return;
                }
                if (flatDeck.length < 60) {
                    const rem = 60 - flatDeck.length;
                    for (let i = 0; i < rem; i++) flatDeck.push("Basic Fire Energy");
                }

                const apiKey = document.getElementById('api-key-input') ? document.getElementById('api-key-input').value.trim() : 'tcg-live-secret-key-2026';
                try {
                    const res = await fetch('/api/v1/match/start', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
                        body: JSON.stringify({
                            custom_deck_list: flatDeck,
                            opp_deck_id: 'miraidon-ex-regieleki'
                        })
                    });
                    if (res.ok) {
                        const data = await res.json();
                        CURRENT_MATCH_STATE = data.match_state;
                        LATEST_AI_REC = data.ai_recommendation;
                        updateMatchView(data);
                        switchMode('match');
                    }
                } catch(e) {
                    console.error("Failed to start match with custom deck:", e);
                }
            }

            async function loadTop60RecommendedDeck() {
                const res = await fetch('/api/v1/deck/analyze-top60');
                if (res.ok) {
                    const data = await res.json();
                    alert(`✨ AI Card Dataset Analysis Complete!\n\nGenerated: ${data.recommended_deck.name}\nCards Analyzed: ${data.total_cards_analyzed}\n\nLoading top 60 strategic deck now!`);
                    const dsEl = document.getElementById('deck-select');
                    if (dsEl) dsEl.value = 'ai-top-60-optimized';
                    await startMatchWithDeck('ai-top-60-optimized');
                }
            }

            async function startNewMatch() {
                const deckSelectEl = document.getElementById('deck-select');
                const deckId = deckSelectEl ? deckSelectEl.value : 'ai-top-60-optimized';
                await startMatchWithDeck(deckId);
            }

            async function startMatchWithDeck(deckId) {
                const keyEl = document.getElementById('api-key-input');
                const apiKey = keyEl ? keyEl.value.trim() : 'tcg-live-secret-key-2026';
                try {
                    const res = await fetch('/api/v1/match/start', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
                        body: JSON.stringify({ player_deck_id: deckId || 'ai-top-60-optimized', opp_deck_id: 'miraidon-ex-regieleki' })
                    });
                    if (res.ok) {
                        const data = await res.json();
                        CURRENT_MATCH_STATE = data.match_state;
                        LATEST_AI_REC = data.ai_recommendation;
                        updateMatchView(data);
                    }
                } catch(e) {
                    console.error("Failed to start match:", e);
                }
            }

            function updateMatchView(data) {
                const st = data.match_state;
                if (!st) return;
                CURRENT_MATCH_STATE = st;

                // 3-Card KO Scoreboard
                const pKos = st.player.prizes_taken || 0;
                const oppKos = st.opponent.prizes_taken || 0;
                const pKoEl = document.getElementById('p-ko-count');
                const oppKoEl = document.getElementById('opp-ko-count');
                if (pKoEl) pKoEl.textContent = pKos;
                if (oppKoEl) oppKoEl.textContent = oppKos;

                const statusBanner = document.getElementById('match-status-banner');
                if (statusBanner) {
                    if (data.winner === 'Player' || pKos >= 3) {
                        statusBanner.textContent = '🏆 VICTORY: KNOCKED OUT 3 OPPONENT MAIN POKÉMON!';
                        statusBanner.style.borderColor = 'var(--neon-green)';
                        statusBanner.style.color = 'var(--neon-green)';
                    } else if (data.winner === 'Opponent' || oppKos >= 3) {
                        statusBanner.textContent = '❌ DEFEAT: YOUR 3 MAIN POKÉMON WERE KNOCKED OUT!';
                        statusBanner.style.borderColor = 'var(--neon-magenta)';
                        statusBanner.style.color = 'var(--neon-magenta)';
                    } else {
                        statusBanner.textContent = 'MATCH IN PROGRESS (3 MAIN POKÉMON LOSS LIMIT)';
                        statusBanner.style.borderColor = 'var(--neon-cyan)';
                        statusBanner.style.color = 'var(--neon-cyan)';
                    }
                }

                // Energy attachment button locking
                const eUsed = st.turn_flags && st.turn_flags.energy_attached_this_turn;
                const eMainBtn = document.getElementById('btn-add-energy-main');
                if (eMainBtn) {
                    if (eUsed) {
                        eMainBtn.disabled = true;
                        eMainBtn.textContent = '⚡ + ADD ENERGY (1/1 USED THIS TURN)';
                    } else {
                        eMainBtn.disabled = false;
                        eMainBtn.textContent = '⚡ + ADD ENERGY (1 PER TURN)';
                    }
                }

                // Deck counts
                const pDeckEl = document.getElementById('p-deck-count');
                const oppDeckEl = document.getElementById('opp-deck-count');
                const pDiscEl = document.getElementById('p-discard-count');
                if (pDeckEl) pDeckEl.textContent = st.player.deck_count;
                if (oppDeckEl) oppDeckEl.textContent = st.opponent.deck_count;
                if (pDiscEl) pDiscEl.textContent = (st.player.discard || []).length;

                // Main Pokémon Cards
                renderActiveCard('player-active-view', st.player.active_spot, true);
                renderActiveCard('opp-active-view', st.opponent.active_spot, false);

                // Sub Pokémon Bench Cards (3 slots max)
                renderBenchGrid('player-bench-view', st.player.bench, true);
                renderBenchGrid('opp-bench-view', st.opponent.bench, false);

                // Hand Cards
                renderHandGrid(st.player.hand);

                // AI Coach Banner
                updateAiBanner(data.ai_recommendation);

                // Combat Log
                renderCombatLog(data.match_log || []);
            }

            function renderPrizesRack(id, takenCount, isPlayer) {
                const rack = document.getElementById(id);
                if (!rack) return;
                rack.innerHTML = '';
                for (let i = 0; i < 6; i++) {
                    const slot = document.createElement('div');
                    if (i < (6 - takenCount)) {
                        slot.className = 'prize-card-slot mystery-card-back ' + (isPlayer ? '' : 'opp-mystery');
                        slot.innerHTML = `<span style="font-size:0.55rem; font-family:var(--font-orbitron); color:${isPlayer ? 'var(--neon-cyan)' : 'var(--neon-magenta)'}">🃏 MYSTERY</span>`;
                    } else {
                        slot.className = 'prize-card-slot taken';
                        slot.innerHTML = `<span style="font-size:0.55rem; color:#64748b;">CLAIMED</span>`;
                    }
                    rack.appendChild(slot);
                }
            }

            function renderActiveCard(containerId, pkmn, isPlayer) {
                const box = document.getElementById(containerId);
                if (!pkmn) { box.innerHTML = '<div style="color:#64748b;">No Main Pokémon Selected</div>'; return; }

                if (isPlayer) {
                    box.ondragover = (e) => e.preventDefault();
                    box.ondrop = (e) => handleDropOnPokemon(e, 'main');
                }

                const meta = getMeta(pkmn.name);
                const maxHp = pkmn.max_hp || meta.hp || 120;
                const currHp = pkmn.current_hp;
                const hpPct = Math.max(0, Math.min(100, (currHp / maxHp) * 100));
                const hpClass = hpPct < 30 ? 'danger' : (hpPct < 60 ? 'warning' : '');

                const boost = pkmn.power_boost || 0;
                const boostBadge = boost > 0 ? `<div style="background:rgba(255,170,0,0.25); border:1px solid var(--neon-amber); color:var(--neon-amber); font-family:var(--font-orbitron); font-size:0.75rem; padding:3px 8px; border-radius:4px; margin-top:6px; font-weight:800; text-shadow:0 0 8px rgba(255,170,0,0.6);">⚡ SUPPORTER POWER BOOST: +${boost} ATK DMG</div>` : '';

                let attacksHtml = '';
                (meta.attacks || []).forEach(atk => {
                    const cost = (atk.cost || []).join(' ') || 'Free';
                    const dmg = atk.base_damage || 0;
                    const totalDmg = dmg > 0 ? (dmg + boost) : 0;
                    const strikeBtn = isPlayer ? `<button class="btn-strike" onclick="matchAttack('${atk.name}', ${dmg})">⚡ STRIKE (${totalDmg > 0 ? totalDmg + ' DMG' : 'EFFECT'})</button>` : '';
                    attacksHtml += `
                        <div class="attack-item">
                            <div>
                                <div class="atk-name">${atk.name}</div>
                                <div class="atk-cost">Cost: [${cost}] &bull; ${atk.text || ''}</div>
                            </div>
                            <div class="atk-dmg">${totalDmg > 0 ? totalDmg + ' DMG' : 'Effect'}</div>
                            ${strikeBtn}
                        </div>
                    `;
                });

                let energyHtml = (pkmn.attached_energy || []).map(e => `<span class="energy-pill">⚡ ${e}</span>`).join(' ');
                const eUsed = CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.turn_flags && CURRENT_MATCH_STATE.turn_flags.energy_attached_this_turn;
                const addEnergyBtn = isPlayer ? (
                    eUsed ? 
                    `<button class="btn-cyber-sm" disabled style="font-size:0.65rem; padding:2px 6px; margin-left:8px; opacity:0.4; cursor:not-allowed;">+ ADD ENERGY (1/1 USED)</button>` :
                    `<button class="btn-cyber-sm" style="font-size:0.65rem; padding:2px 6px; margin-left:8px;" onclick="promptAddEnergyDirect('player')">+ ADD ENERGY</button>`
                ) : '';

                box.innerHTML = `
                    <div class="card-top-row">
                        <div class="card-name-hero">👑 MAIN POKÉMON: ${pkmn.name}</div>
                        <div class="card-type-tag">${(meta.types || ['Normal']).join(', ')} | ${(meta.subtypes || []).join(' ')}</div>
                    </div>
                    <div class="hp-info"><span>HP STATUS</span><span style="color:${currHp > 0 ? '#34d399' : '#f87171'}">${currHp} / ${maxHp} HP</span></div>
                    <div class="hp-track"><div class="hp-fill ${hpClass}" style="width:${hpPct}%"></div></div>
                    ${boostBadge}
                    <div class="energy-tray" style="margin-top:6px;">
                        <span style="font-size:0.7rem; color:var(--text-dim); font-family:var(--font-orbitron);">ATTACHED ENERGY:</span> 
                        ${energyHtml || '<span style="font-size:0.7rem; color:#64748b;">None</span>'}
                        ${addEnergyBtn}
                    </div>
                    <div class="attacks-box">
                        <div style="font-family:var(--font-orbitron); font-size:0.7rem; color:var(--neon-cyan); margin-bottom:4px;">POKÉMON ATTACKS & POWERS (DATASET)</div>
                        ${attacksHtml || '<div style="font-size:0.75rem; color:#64748b;">No attacks listed.</div>'}
                    </div>
                `;
            }

            function renderBenchGrid(containerId, bench, isPlayer) {
                const box = document.getElementById(containerId);
                box.innerHTML = '';
                const maxSlots = 3;
                const count = bench ? bench.length : 0;

                for (let i = 0; i < maxSlots; i++) {
                    if (i < count) {
                        const b = bench[i];
                        const card = document.createElement('div');
                        card.className = 'bench-card';
                        if (isPlayer) {
                            card.ondragover = (e) => e.preventDefault();
                            card.ondrop = (e) => handleDropOnPokemon(e, 'sub');
                        }
                        card.innerHTML = `<div class="b-name">🛡️ SUB #${i+1}: ${b.name}</div><div class="b-hp">${b.current_hp || 70} HP</div>`;
                        box.appendChild(card);
                    } else {
                        const slot = document.createElement('div');
                        slot.className = 'bench-card empty-slot';
                        if (isPlayer) {
                            slot.ondragover = (e) => e.preventDefault();
                            slot.ondrop = (e) => handleDropOnPokemon(e, 'sub');
                            slot.innerHTML = `<button class="btn-summon-slot" onclick="promptPlayHandToBench()">+ PLAY POKÉMON FROM HAND #${i+1}</button>`;
                        } else {
                            slot.innerHTML = `<div style="font-size:0.68rem; color:#64748b;">[ Sub Spot #${i+1} Empty ]</div>`;
                        }
                        box.appendChild(slot);
                    }
                }
            }

            function promptPlayHandToBench() {
                if (!CURRENT_MATCH_STATE || !CURRENT_MATCH_STATE.player || !CURRENT_MATCH_STATE.player.hand) return;
                const hand = CURRENT_MATCH_STATE.player.hand;
                const basicCards = hand.filter(c => {
                    const cname = typeof c === 'string' ? c : c.name;
                    const meta = getMeta(cname);
                    const stype = (meta.supertype || '').toLowerCase();
                    const sub = (meta.subtypes || []).map(s => s.toLowerCase());
                    return stype.includes('pok') && sub.includes('basic');
                });

                if (basicCards.length === 0) {
                    alert("⚠️ No Basic Pokémon in your hand! Draw/claim a card from your Deck Generator first.");
                    return;
                }

                const cardNames = basicCards.map(c => typeof c === 'string' ? c : c.name);
                const chosen = prompt(`Select a Basic Pokémon from your Hand to place onto the Bench:\n\nAvailable in Hand:\n${cardNames.map((n, idx) => `${idx+1}. ${n}`).join('\n')}\n\nEnter exact Pokémon Name:`, cardNames[0]);
                if (chosen && cardNames.includes(chosen.trim())) {
                    matchPlayCard(chosen.trim());
                }
            }

            function renderHandGrid(hand) {
                const box = document.getElementById('player-hand-view');
                box.innerHTML = '';
                if (!hand || hand.length === 0) {
                    box.innerHTML = '<div style="font-size:0.75rem; color:#64748b; padding:4px;">Hand is empty. Click Deck Generator to claim cards.</div>';
                    return;
                }
                hand.forEach(item => {
                    const cname = (typeof item === 'string') ? item : item.name;
                    const meta = getMeta(cname);
                    const stype = meta.supertype || 'Card';
                    const div = document.createElement('div');
                    div.className = 'hand-card-chip';
                    div.draggable = true;
                    div.ondragstart = (e) => handleDragStart(e, cname);
                    div.innerHTML = `
                        <div class="h-type-pill">${stype}</div>
                        <div class="h-title">${cname}</div>
                        <button class="btn-hand-play" onclick="matchPlayCard('${cname}')">Play / Drag to Arena</button>
                    `;
                    box.appendChild(div);
                });
            }

            let DRAGGED_CARD_NAME = null;

            function handleDragStart(e, cname) {
                DRAGGED_CARD_NAME = cname;
                e.dataTransfer.setData('text/plain', cname);
            }

            async function handleDropOnPokemon(e, targetType) {
                e.preventDefault();
                const cname = e.dataTransfer.getData('text/plain') || DRAGGED_CARD_NAME;
                if (!cname) return;
                await matchPlayCard(cname);
            }

            async function claimRandomDeckCard() {
                if (CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.player && CURRENT_MATCH_STATE.player.hand && CURRENT_MATCH_STATE.player.hand.length >= 10) {
                    alert("⚠️ Hand Limit Reached: Your hand already has 10 cards (max limit)!");
                    return;
                }

                const apiKey = document.getElementById('api-key-input') ? document.getElementById('api-key-input').value.trim() : 'tcg-live-secret-key-2026';
                const res = await fetch('/api/v1/match/draw', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
                    body: JSON.stringify({})
                });
                if (res.ok) {
                    const data = await res.json();
                    const cardName = data.drawn_card || (data.match_state && data.match_state.player && data.match_state.player.hand && data.match_state.player.hand.length > 0 ? (typeof data.match_state.player.hand[data.match_state.player.hand.length - 1] === 'string' ? data.match_state.player.hand[data.match_state.player.hand.length - 1] : data.match_state.player.hand[data.match_state.player.hand.length - 1].name) : 'Pokemon Card');
                    const meta = getMeta(cardName);
                    show3DCardRevealModal(cardName, meta.supertype || 'Card');
                    updateMatchView(data);
                }
            }

            function show3DCardRevealModal(cardName, cardType) {
                let modal = document.getElementById('card-reveal-modal');
                if (!modal) {
                    modal = document.createElement('div');
                    modal.id = 'card-reveal-modal';
                    modal.style.cssText = 'position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.85); backdrop-filter:blur(14px); z-index:99999; display:flex; flex-direction:column; align-items:center; justify-content:center; perspective:1200px; transition:opacity 0.4s;';
                    document.body.appendChild(modal);
                }
                const meta = getMeta(cardName);
                const isPokemon = (cardType || '').toLowerCase().includes('pok') || (meta.supertype || '').toLowerCase().includes('pok');
                const isEnergy = (cardType || '').toLowerCase().includes('energy') || cardName.toLowerCase().includes('energy');
                const isSupporter = (meta.subtypes || []).map(s => s.toLowerCase()).includes('supporter') || cardName.toLowerCase().includes('arven') || cardName.toLowerCase().includes('research');
                
                let accentColor = 'var(--neon-cyan)';
                let glowColor = 'rgba(0, 243, 255, 0.8)';
                let badgeText = (cardType || 'CARD').toUpperCase();
                let iconSymbol = '🃏';
                let extraDetails = '';

                if (isPokemon) {
                    accentColor = '#ef4444';
                    glowColor = 'rgba(239, 68, 68, 0.8)';
                    badgeText = `BASIC POKÉMON • ${meta.hp || 70} HP`;
                    iconSymbol = '🔥';
                    if (meta.attacks && meta.attacks.length > 0) {
                        extraDetails = `<div style="font-size:0.75rem; color:#cbd5e1; margin-top:8px; font-family:var(--font-mono);">Attack: <b>${meta.attacks[0].name}</b> (${meta.attacks[0].base_damage || 0} DMG)</div>`;
                    }
                } else if (isEnergy) {
                    accentColor = 'var(--neon-green)';
                    glowColor = 'rgba(0, 255, 136, 0.8)';
                    badgeText = 'BASIC ENERGY CARD';
                    iconSymbol = '⚡';
                    extraDetails = `<div style="font-size:0.75rem; color:#86efac; margin-top:8px; font-family:var(--font-mono);">+ Provides 1 Energy Attachment</div>`;
                } else if (isSupporter) {
                    accentColor = 'var(--neon-amber)';
                    glowColor = 'rgba(255, 170, 0, 0.8)';
                    badgeText = 'SUPPORTER TRAINER';
                    iconSymbol = '📜';
                    extraDetails = `<div style="font-size:0.75rem; color:#fde68a; margin-top:8px; font-family:var(--font-mono);">Draw & Search Power (1/Turn)</div>`;
                }

                modal.style.opacity = '1';
                modal.style.display = 'flex';
                modal.innerHTML = `
                    <div id="modal-title-header" style="font-family:var(--font-orbitron); font-size:1.35rem; color:var(--neon-cyan); font-weight:900; margin-bottom:24px; text-shadow:0 0 25px var(--neon-cyan); letter-spacing:1.5px; transition:all 0.4s;">
                        ✨ 3D 180° CARD FLIP & DRAW REVEAL
                    </div>
                    <div id="card-flipper-box" style="width:250px; height:350px; position:relative; transform-style:preserve-3d; transition:transform 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275), translateY 0.5s ease, opacity 0.5s ease;">
                        <!-- BACK FACE (INITIAL 0 DEG) -->
                        <div style="position:absolute; width:100%; height:100%; backface-visibility:hidden; background:linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%); border:3px solid var(--neon-cyan); border-radius:16px; box-shadow:0 0 35px rgba(0,243,255,0.7); display:flex; flex-direction:column; align-items:center; justify-content:center; padding:20px; text-align:center;">
                            <div style="font-size:3.8rem; filter:drop-shadow(0 0 10px rgba(0,243,255,0.8));">🃏</div>
                            <div style="font-family:var(--font-orbitron); font-size:1.15rem; color:var(--neon-cyan); font-weight:900; margin-top:14px;">MYSTERY DECK CARD</div>
                            <div style="font-size:0.72rem; color:#94a3b8; margin-top:6px; font-family:var(--font-mono);">DRAWING FROM 60-CARD DECK</div>
                        </div>
                        <!-- FRONT FACE (180 DEG REVEAL) -->
                        <div style="position:absolute; width:100%; height:100%; backface-visibility:hidden; transform:rotateY(180deg); background:linear-gradient(135deg, #0f172a 0%, #020617 100%); border:3px solid ${accentColor}; border-radius:16px; box-shadow:0 0 45px ${glowColor}; display:flex; flex-direction:column; align-items:center; justify-content:space-between; padding:20px 16px; text-align:center;">
                            <div style="display:flex; justify-content:space-between; width:100%; align-items:center; border-bottom:1px solid rgba(255,255,255,0.15); padding-bottom:6px;">
                                <span style="font-family:var(--font-orbitron); font-size:0.7rem; color:${accentColor}; font-weight:800;">${badgeText}</span>
                                <span style="font-size:1.2rem;">${iconSymbol}</span>
                            </div>
                            <div style="margin: auto 0;">
                                <div style="font-size:3.2rem; filter:drop-shadow(0 0 15px ${glowColor}); margin-bottom:8px;">${iconSymbol}</div>
                                <div style="font-family:var(--font-orbitron); font-size:1.35rem; font-weight:900; color:#fff; text-shadow:0 0 10px rgba(255,255,255,0.5);">${cardName}</div>
                                ${extraDetails}
                            </div>
                            <div style="font-size:0.78rem; color:#38bdf8; font-family:var(--font-mono); font-weight:700; background:rgba(0,243,255,0.1); border:1px solid rgba(0,243,255,0.3); padding:4px 10px; border-radius:20px; width:100%;">
                                ↓ SLIDING INTO YOUR HAND TRAY
                            </div>
                        </div>
                    </div>
                `;

                const flipper = document.getElementById('card-flipper-box');
                const titleHeader = document.getElementById('modal-title-header');
                
                // 1. Trigger 180-degree 3D Y-Axis Flip
                setTimeout(() => {
                    if (flipper) flipper.style.transform = 'rotateY(180deg) scale(1.05)';
                }, 90);

                // 2. Slide into Hand Tray Animation
                setTimeout(() => {
                    if (flipper) {
                        flipper.style.transform = 'rotateY(180deg) translateY(240px) scale(0.65)';
                        flipper.style.opacity = '0';
                    }
                    if (titleHeader) titleHeader.style.opacity = '0';
                    modal.style.opacity = '0';
                }, 1350);

                // 3. Close Modal
                setTimeout(() => {
                    modal.style.display = 'none';
                }, 1750);
            }

            function updateAiBanner(aiRec) {
                if (!aiRec) return;
                const top = aiRec.top_recommended_move;
                if (top) {
                    const title = top.card_name || top.action_type;
                    const winPct = top.expected_win_probability_pct || '56.4%';
                    const actName = top.action_type ? top.action_type.replace(/_/g, ' ') : 'Play Supporter';
                    
                    const leftWin = document.getElementById('left-win-pct');
                    const leftAction = document.getElementById('left-rec-action');
                    const leftDesc = document.getElementById('left-rec-desc');
                    const leftRanked = document.getElementById('left-ranked-list');

                    if (leftWin) leftWin.textContent = winPct;
                    if (leftAction) leftAction.textContent = `${actName}: ${title}`;
                    if (leftDesc) leftDesc.textContent = top.strategic_rationale;

                    if (leftRanked && aiRec.top_ranked_moves) {
                        leftRanked.innerHTML = aiRec.top_ranked_moves.slice(0, 3).map((m, idx) => `
                            <div><b>${idx+1}.</b> ${m.action_type.replace(/_/g, ' ')} (${m.card_name || ''}) - <span style="color:var(--neon-green);">${m.expected_win_probability_pct}</span></div>
                        `).join('');
                    }

                    const hudWin = document.getElementById('hud-win-pct');
                    const hudRec = document.getElementById('hud-rec-text');
                    if (hudWin) hudWin.textContent = winPct;
                    if (hudRec) hudRec.textContent = `Recommended: "${actName}: ${title}" — ${top.strategic_rationale}`;
                }
            }

            function renderCombatLog(log) {
                const box = document.getElementById('combat-log');
                box.innerHTML = log.map(l => `&gt; ${l}`).join('<br>');
                box.scrollTop = box.scrollHeight;
            }

            function getApiKey() {
                const keyEl = document.getElementById('api-key-input');
                return keyEl && keyEl.value ? keyEl.value.trim() : 'tcg-live-secret-key-2026';
            }

            // --- MATCH ACTIONS ---
            async function matchPlayCard(cname) {
                const apiKey = getApiKey();
                try {
                    const res = await fetch('/api/v1/match/play', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
                        body: JSON.stringify({ card_name: cname })
                    });
                    if (res.ok) {
                        const data = await res.json();
                        if (data.status === 'error') {
                            alert(`❌ Rule Restriction: ${data.message}`);
                        }
                        updateMatchView(data);
                    }
                } catch(e) {
                    console.error("Play card failed:", e);
                }
            }

            async function promptAddEnergyDirect(side) {
                if (CURRENT_MATCH_STATE && CURRENT_MATCH_STATE.turn_flags && CURRENT_MATCH_STATE.turn_flags.energy_attached_this_turn) {
                    alert("⚡ Official TCG Rules: You can only attach Energy ONCE per turn. Pass turn to attach again!");
                    return;
                }
                const pick = prompt("Enter Energy to Attach in TCG (Fire, Lightning, Psychic, Water, Grass, Darkness, Metal):", "Fire");
                if (pick) {
                    await matchPlayCard(`Basic ${pick.trim()} Energy`);
                }
            }

            async function matchAttack(atkName, dmg) {
                const apiKey = getApiKey();
                try {
                    const res = await fetch('/api/v1/match/attack', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
                        body: JSON.stringify({ attack_name: atkName, base_damage: dmg })
                    });
                    if (res.ok) updateMatchView(await res.json());
                } catch(e) {
                    console.error("Attack failed:", e);
                }
            }

            async function endPlayerTurn() {
                const apiKey = getApiKey();
                try {
                    const res = await fetch('/api/v1/match/end-turn', { method: 'POST', headers: { 'X-API-Key': apiKey } });
                    if (res.ok) updateMatchView(await res.json());
                } catch(e) {
                    console.error("End turn failed:", e);
                }
            }

            async function executeAiRecommendation() {
                if (!LATEST_AI_REC || !LATEST_AI_REC.top_recommended_move) return;
                const top = LATEST_AI_REC.top_recommended_move;
                const act = top.action_details || {};
                const actType = act.action_type || top.action_type;

                if (actType === 'ATTACK') {
                    await matchAttack(act.attack_name || 'Burning Darkness', act.base_damage || 180);
                } else if (actType === 'ATTACH_ENERGY' || actType === 'PLAY_SUPPORTER' || actType === 'PLAY_ITEM' || actType === 'BENCH_POKEMON') {
                    await matchPlayCard(act.card_name || top.card_name);
                }
            }

            // Expose globally to window
            window.initApp = initApp;
            window.switchMode = switchMode;
            window.selectArchetypePreview = selectArchetypePreview;
            window.importCurrentArchetypeToCustomDeck = importCurrentArchetypeToCustomDeck;
            window.setCardCategoryFilter = setCardCategoryFilter;
            window.filterCardsDatabase = filterCardsDatabase;
            window.renderAllCardsDatabase = renderAllCardsDatabase;
            window.loadMorePokemon = loadMorePokemon;
            window.showAllPokemon = showAllPokemon;
            window.renderDeckBuilderPreview = renderDeckBuilderPreview;
            window.changeCardCountInDeck = changeCardCountInDeck;
            window.updateCustomDeckUI = updateCustomDeckUI;
            window.autoFillBasicEnergy = autoFillBasicEnergy;
            window.clearCustomDeck = clearCustomDeck;
            window.startMatchWithCustomDeck = startMatchWithCustomDeck;
            window.loadTop60RecommendedDeck = loadTop60RecommendedDeck;
            window.startNewMatch = startNewMatch;
            window.startMatchWithDeck = startMatchWithDeck;
            window.startMatchWithCurrentDeck = startMatchWithCurrentDeck;
            window.claimRandomDeckCard = claimRandomDeckCard;
            window.matchPlayCard = matchPlayCard;
            window.matchAttack = matchAttack;
            window.endPlayerTurn = endPlayerTurn;
            window.executeAiRecommendation = executeAiRecommendation;
            window.promptAddEnergyDirect = promptAddEnergyDirect;
            window.getApiKey = getApiKey;

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
