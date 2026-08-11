import random
from agent import HeuristicAgent, RandomAgent, CoEvolutionAgent, sample_chance_outcome
from mctsCoEvo import CoEvolutionMCTSAgent  
from board import Board
from coevolutionHelp import CoEvolutionTrainer, playEvol
import state
import rules
              
def evaluate_vs_opponent(best_weights, opponent_type="random", num_games=10, agent_factory=None):
    """Evaluates the evolved weights/genome against a specified opponent type across N games.
    agent_factory: callable(color, genome) -> Agent, so this works for both
    HeuristicAgent and CoEvolutionMCTSAgent-style evolved agents."""
    if agent_factory is None:
        agent_factory = lambda color, genome: HeuristicAgent(color=color, weights=genome)
    evolved_wins = 0
    evolved_vps = []
    opponent_vps = []
    print(f"\n==========================================")
    print(f"   BENCHMARK: Evolved Agent vs {opponent_type.upper()} ({num_games} Games)")
    print(f"==========================================")
    for i in range(num_games):
        seed = random.randint(0, 2_000_000_000)
        evolved_agent = agent_factory("Evolved", best_weights)
        if opponent_type.lower() == "random":
            opponent_agent = RandomAgent(color="Random", seed=seed)
        else:
            opponent_agent = HeuristicAgent(color="StandardHeuristic")
        if i % 2 == 0:
            agents = [evolved_agent, opponent_agent]
            evolved_idx, opp_idx = 0, 1
        else:
            agents = [opponent_agent, evolved_agent]
            evolved_idx, opp_idx = 1, 0
        gs = playEvol(agents, seed=seed, verbose=False, max_actions=200)
        winner = gs.winner()
        e_vp = gs.victory_points(evolved_idx)
        o_vp = gs.victory_points(opp_idx)
        evolved_vps.append(e_vp)
        opponent_vps.append(o_vp)
        if winner == evolved_idx:
            evolved_wins += 1
            result = "WIN "
        else:
            result = "LOSS"
        pos_str = f"P{evolved_idx}"
        print(f"Game {i+1:2d} ({pos_str}): {result} | Evolved VP: {e_vp:2d}  vs  {opponent_type.capitalize()} VP: {o_vp:2d}")

    win_rate = (evolved_wins / num_games) * 100
    avg_e_vp = sum(evolved_vps) / num_games
    avg_o_vp = sum(opponent_vps) / num_games
    print(f"------------------------------------------")
    print(f"Summary vs {opponent_type.upper()}:")
    print(f"  Win Rate:         {win_rate:.1f}% ({evolved_wins}/{num_games})")
    print(f"  Avg Evolved VP:   {avg_e_vp:.2f}")
    print(f"  Avg Opponent VP:  {avg_o_vp:.2f}")
    print(f"==========================================\n")


def run_greedy_coevolution():
    print("\n########## GREEDY HEURISTIC CO-EVOLUTION ##########")
    trainer = CoEvolutionTrainer(
        agent_class=CoEvolutionAgent,   # default, but explicit here for clarity
        population_size=2,
        n_generations=4,
        games_per_round=1,
        elite_fraction=0.2,
        tournament_k=8,
        mutation_rate=0.35,
        mutation_sigma=0.25,
        max_actions_per_game=600,
        seed=None,)
    trainer.runEvolution(verbose=True)
    best_weights = trainer.best_genome()
    print("\nBest Genome (Greedy):")
    print(best_weights)
    evaluate_vs_opponent(best_weights, opponent_type="random", num_games=10)
    evaluate_vs_opponent(best_weights, opponent_type="heuristic", num_games=10)
    return best_weights

def run_mcts_coevolution():
    print("\n########## MCTS CO-EVOLUTION ##########")
    trainer = CoEvolutionTrainer(
        agent_class= CoEvolutionMCTSAgent,
        agent_kwargs={"n_simulations": 30, "c": 1.4, "rollout_depth": 20},  # kept small -- MCTS is expensive
        population_size=8,        # smaller population than greedy given the cost
        n_generations=5,          # fewer generations for the same reason
        games_per_round=2,
        elite_fraction=0.2,
        tournament_k=4,
        mutation_rate=0.35,
        mutation_sigma=0.25,
        max_actions_per_game=600,
        seed=None,)
    trainer.runEvolution(verbose=True)
    best_weights = trainer.best_genome()
    print("\nBest Genome (MCTS rollout weights):")
    print(best_weights)
    mcts_factory = lambda color, genome: CoEvolutionMCTSAgent(color, n_simulations=30, c=1.4, rollout_depth=20, genome=genome)
    evaluate_vs_opponent(best_weights, opponent_type="random", num_games=10, agent_factory=mcts_factory)
    evaluate_vs_opponent(best_weights, opponent_type="heuristic", num_games=10, agent_factory=mcts_factory)
    return best_weights


if __name__ == "__main__":
    mcts_best = run_mcts_coevolution()
    greedy_best = run_greedy_coevolution()
    print("\n\n=== FINAL COMPARISON ===")
    print("Greedy best genome:", greedy_best)
    print("MCTS best genome:  ", mcts_best)
    
