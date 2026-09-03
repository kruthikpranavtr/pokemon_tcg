"""
Strategic Rationale & Competitive Explainer Engine
Generates human-understandable, expert TCG tactical rationales for model-selected moves.
"""
from typing import Dict, Any


class ActionExplainer:
    def __init__(self, card_db: Dict[str, Any]):
        self.card_db = card_db

    def explain(self, action: Dict[str, Any], game_state: Dict[str, Any], win_prob: float) -> str:
        """
        Synthesizes a tactical rationale based on action type, card mechanics, and game context.
        """
        action_type = action.get("action_type")
        card_name = action.get("card_name", "")
        player = game_state.get("player", {})
        opponent = game_state.get("opponent", {})

        p_prizes = player.get("prizes_remaining", 6)
        opp_prizes = opponent.get("prizes_remaining", 6)
        opp_active = opponent.get("active_spot", {})
        opp_name = opp_active.get("name", "Opponent's Active")
        opp_hp = opp_active.get("current_hp", 0)

        if action_type == "PLAY_SUPPORTER":
            if card_name == "Professor's Research":
                return f"Discards hand to draw 7 fresh cards, aggressively digging for key evolution and energy pieces."
            elif card_name == "Iono":
                if opp_prizes <= 2:
                    return f"Potent late-game hand disruption: reduces opponent to {opp_prizes} cards while refreshing your hand to {p_prizes} cards."
                return f"Resets hand to {p_prizes} cards to refresh options and disrupt opponent's planned turn sequence."
            elif card_name == "Boss's Orders":
                return f"Gusts a high-value benched Pokémon into the Active Spot to secure key Prize cards or stall."
            elif card_name == "Arven":
                return "Guarantees Item search (e.g., Rare Candy/Ultra Ball) and Tool search to secure instant board evolution."
            return f"Executes Supporter play '{card_name}' to advance board tempo and resource acceleration."

        elif action_type == "PLAY_ITEM":
            if card_name == "Ultra Ball":
                return f"Discards surplus cards to search your primary win-condition Pokémon directly from the deck."
            elif card_name == "Nest Ball":
                return f"Deploys a basic setup Pokémon to the Bench to establish safety against sudden Active knockouts."
            elif card_name == "Rare Candy":
                return f"Accelerates instant Stage 2 evolution, skipping Stage 1 to threaten massive damage against {opp_name}."
            elif card_name == "Prime Catcher":
                return f"ACE SPEC tactical switch: pulls {opp_name} or an opponent's vulnerable bench target into Active."
            elif card_name == "Super Rod":
                return f"Recycles critical Pokémon and basic Energy from the discard pile back into the deck."
            elif card_name == "Earthen Vessel":
                return f"Discards 1 card to search 2 basic Energy, guaranteeing turn attachments."
            return f"Plays Item '{card_name}' to optimize hand velocity and deck thinning."

        elif action_type == "EVOLVE_POKEMON":
            target = action.get("target_pokemon", "Active Spot")
            return f"Evolves {target} into {card_name}, unlocking higher HP threshold and superior attack damage vs {opp_name}."

        elif action_type == "ATTACH_ENERGY":
            target = action.get("target_pokemon", "Active Spot")
            return f"Attaches {card_name} to {target} to fuel attack energy requirements for upcoming strike."

        elif action_type == "USE_STADIUM_EFFECT":
            return f"Activates Stadium '{card_name}' on field to deploy setup basics without consuming Supporter turn."

        elif action_type == "ATTACK":
            atk_name = action.get("attack_name", "Attack")
            base_dmg = action.get("base_damage", 0)
            if opp_hp > 0 and base_dmg >= opp_hp:
                return f"[LETHAL KNOCKOUT] Strikes with '{atk_name}' ({base_dmg} DMG), taking down {opp_name} ({opp_hp} HP remaining) and claiming Prize cards!"
            elif opp_hp > 0:
                rem_hp = max(0, opp_hp - base_dmg)
                return f"Strikes {opp_name} with '{atk_name}' for {base_dmg} DMG (leaves {opp_name} at {rem_hp} HP) to swing prize race."
            return f"Unleashes '{atk_name}' ({base_dmg} base damage) to apply prize pressure on opponent."

        elif action_type == "BENCH_BASIC_POKEMON":
            return f"Benches {card_name} to develop board presence and prepare future attacker or draw support engine."

        elif action_type == "PASS_TURN":
            return f"Passes turn to conserve resources and await optimal attack configuration next turn."

        return f"Executes {action_type} to maximize board positioning and win probability ({win_prob:.1%})."
