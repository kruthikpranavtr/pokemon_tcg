"""
Unified TCG Strategic AI Engine
Main entry point orchestrating:
1. Rules Engine & Legal Action Generation
2. Bayesian Belief State & Hidden Information Tracking
3. Opponent Behavioral Model
4. MCTS with PUCT & Progressive Widening
5. Stochastic Monte Carlo Rollouts with Confidence Intervals
6. Multi-Factor Evaluation & "The Winning Route"
7. Dual-Head Neural Policy-Value Evaluator
8. Explainable AI & Mathematical Report Generator
"""
import os
from typing import Dict, List, Any, Optional
from .cards.card_database import CardDatabase
from .rules.rules_engine import RulesEngine
from .state.game_state import GameStateManager
from .probability.belief_state import BeliefStateTracker
from .opponent_model.behavior_model import OpponentBehaviorModel, OpponentStrategy
from .ml.neural_evaluator import DualHeadNeuralEvaluator
from .search.mcts import MCTSEngine
from .simulation.mc_simulator import MonteCarloSimulator
from .evaluation.evaluator import PositionEvaluator
from .explanation.explainer import StrategicExplainer


class OperationalMode:
    FAST = "FAST"              # 30 simulations, search depth 3 (~50ms)
    BALANCED = "BALANCED"      # 100 simulations, search depth 5 (~200ms)
    DEEP = "DEEP"              # 300 simulations, search depth 8 (~600ms)
    TOURNAMENT = "TOURNAMENT"  # 600 simulations, search depth 10 (~1.2s)


class TCGStrategicAIEngine:
    _instance: Optional['TCGStrategicAIEngine'] = None

    def __init__(
        self,
        weights_path: Optional[str] = None,
        data_path: Optional[str] = None
    ):
        self.card_db = CardDatabase.get_instance(data_path)
        self.rules_engine = RulesEngine(self.card_db)
        self.state_manager = GameStateManager(self.card_db)
        self.belief_tracker = BeliefStateTracker(self.card_db)
        self.opponent_model = OpponentBehaviorModel(self.rules_engine, self.card_db)
        self.evaluator = PositionEvaluator(card_db=self.card_db)
        self.explainer = StrategicExplainer(self.card_db)

        self.neural_evaluator = DualHeadNeuralEvaluator()

        # Load weights if available
        if weights_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            weights_path = os.path.join(base_dir, "models", "policy_value_weights.json")

        if os.path.exists(weights_path):
            self.neural_evaluator.load_weights(weights_path)

        self.mcts_engine = MCTSEngine(
            rules_engine=self.rules_engine,
            opponent_model=self.opponent_model,
            neural_evaluator=self.neural_evaluator,
            state_manager=self.state_manager
        )

        self.mc_simulator = MonteCarloSimulator(
            rules_engine=self.rules_engine,
            opponent_model=self.opponent_model,
            belief_tracker=self.belief_tracker,
            evaluator=self.evaluator
        )

    @classmethod
    def get_instance(cls) -> 'TCGStrategicAIEngine':
        if cls._instance is None:
            cls._instance = TCGStrategicAIEngine()
        return cls._instance

    def analyze(
        self,
        game_state: Dict[str, Any],
        mode: str = OperationalMode.BALANCED,
        simulation_budget: Optional[int] = None,
        search_depth: Optional[int] = None,
        opponent_strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main Analysis Function.
        Analyzes game state, determines legal options, explores MCTS forward rollouts,
        extracts the Winning Route, and returns the full 9-point structured analysis.
        """
        # Configure operational budget
        if simulation_budget is not None:
            num_sims = simulation_budget
        elif mode == OperationalMode.FAST:
            num_sims = 30
        elif mode == OperationalMode.DEEP:
            num_sims = 300
        elif mode == OperationalMode.TOURNAMENT:
            num_sims = 600
        else:
            num_sims = 100

        depth = search_depth or (3 if mode == OperationalMode.FAST else (8 if mode == OperationalMode.DEEP else 5))
        self.mcts_engine.max_depth = depth

        if opponent_strategy:
            self.opponent_model.strategy = opponent_strategy

        # 1. Information Honesty Audit
        info_audit = self.belief_tracker.build_information_audit(game_state)

        # 2. Generate Legal Moves
        legal_actions = self.rules_engine.generate_legal_actions(game_state, is_player=True)
        if not legal_actions:
            return {
                "status": "terminal_or_no_actions",
                "best_move": "PASS_TURN: Pass Turn",
                "why": "No legal actions available. Passing turn to opponent.",
                "win_probability": 0.5
            }

        # 3. Initial Baseline Evaluation
        init_eval = self.evaluator.evaluate_position(game_state)
        init_win_prob = init_eval["win_probability"]

        # 4. MCTS Forward Tree Search
        ranked_moves, grounded_win_prob, mcts_telemetry = self.mcts_engine.search(
            root_state=game_state,
            num_simulations=num_sims
        )

        top_move_entry = ranked_moves[0] if ranked_moves else {"action": legal_actions[0], "win_probability": 0.5}
        best_action = top_move_entry["action"]
        final_win_prob = top_move_entry.get("win_probability", grounded_win_prob)

        # 5. Stochastic Monte Carlo Rollouts for Top Move
        sim_result = self.mc_simulator.simulate_action_rollouts(
            state=game_state,
            action=best_action,
            num_rollouts=min(100, num_sims)
        )

        # 6. Sample Opponent Top Responses
        hypo_after_best = self.mcts_engine.apply_action(game_state, best_action, is_player=True)
        opp_responses = self.opponent_model.sample_top_responses(hypo_after_best, top_k=3)

        # 7. Synthesize "The Winning Route"
        winning_route = self.evaluator.compute_winning_route(game_state, best_action)

        # 8. Assemble Full Explainable AI Report
        report = self.explainer.assemble_comprehensive_explanation(
            best_action=best_action,
            initial_win_prob=init_win_prob,
            final_win_prob=final_win_prob,
            ranked_moves=ranked_moves,
            opponent_responses=opp_responses,
            eval_result=init_eval,
            sim_result=sim_result,
            winning_route=winning_route,
            info_audit=info_audit
        )

        # Attach telemetry and metadata
        report["status"] = "success"
        report["operational_mode"] = mode
        report["mcts_telemetry"] = mcts_telemetry
        report["ranked_moves_count"] = len(ranked_moves)

        return report
