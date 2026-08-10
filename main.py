import random

import outcome
from agent import HeuristicAgent, RandomAgent, sample_chance_outcome
from board import Board
from coevolutionHelp import CoEvolutionTrainer, playEvol
import state
import rules

def play(seed=0, n_players=2, verbose=False):
    # replicable randome seed for demo purposes
    rng = random.Random(seed)

    # starting gamestate initialization
    gs = state.GameState(Board(), n_players)

    while not gs.is_terminal():
        # possible actions at every gamestate
        actions = rules.legal_actions(gs)
        # bug catching
        if not actions:
            raise RuntimeError(f"no legal actions at phase {gs.phase}")

        # for chance nodes we make weighted random choices based on weight associated with random action
        # be it dice rolls (weighted by prob of rolling #) or steals (wegihted by # of each reasource in victim hand)
        if gs.is_chance_node():
            # using random seed for replicability
            action = rng.choices(actions, weights=[a["prob"] for a in actions])[0]
        else:
            ### BASELINE "RANDOM AGENT" that just picks a random choice from those given
            action = rng.choice(actions)
        # optional mode to watch game play out via terminal, NOT for running long sims Will
        if verbose:
            print(f"{gs.phase:<16} P{gs.current_player()} {action}")
        # and then we make an apply call that copies gs, makes chosen move, returns gs + action
        gs = rules.apply(gs, action)

    return gs

'''# testing
if __name__ == "__main__":
    for seed in (1, 2):
        for n in (1, 2):
            gs = play(seed, n, verbose=True)
            print(f"seed {seed}: winner=P{gs.winner()} "
                f"VPs={[gs.victory_points(p) for p in range(gs.n)]}")'''

 

def play2(agents, seed=0, verbose=False):
    rng2 = random.Random(seed)
    n_players = len(agents)
    gs = state.GameState(Board(), n_players)
    while not gs.is_terminal():
        if gs.is_chance_node():
            action = sample_chance_outcome(gs)
            if action is None:
                raise RuntimeError(f"no legal chance actions at phase {gs.phase}")
        else:
            p = gs.current_player()
            action = agents[p].choose_action(gs, p)
            if action is None:
                raise RuntimeError(f"no legal actions for P{p} at phase {gs.phase}")
        if verbose:
            print(f"{gs.phase:<16} P{gs.current_player()} {action}")
        gs = rules.apply(gs, action)
    return gs

'''if __name__ == "__main__":
    seeds = [random.randint(0, 2_000_000_000) for _ in range(1)]
    for seed in seeds:
        agents = [HeuristicAgent(color="red"), HeuristicAgent(color="blue")]
        gs = play2(agents, seed=seed, verbose=True)
        print(f"seed {seed}: winner=P{gs.winner()} "
              f"VPs={[gs.victory_points(p) for p in range(gs.n)]}")'''
              
def evaluate_vs_opponent(best_weights, opponent_type="random", num_games=10):
    """Evaluates the evolved weights against a specified opponent type across N games."""
    evolved_wins = 0
    evolved_vps = []
    opponent_vps = []

    print(f"\n==========================================")
    print(f"   BENCHMARK: Evolved Agent vs {opponent_type.upper()} ({num_games} Games)")
    print(f"==========================================")

    for i in range(num_games):
        seed = random.randint(0, 2_000_000_000)
        # Instantiate Evolved Agent using the best weights
        evolved_agent = HeuristicAgent(color="Evolved", weights=best_weights)
        # Instantiate Opponent
        if opponent_type.lower() == "random":
            opponent_agent = RandomAgent(color="Random", seed=seed)
        else:
            # Standard HeuristicAgent uses DEFAULT_WEIGHTS automatically
            opponent_agent = HeuristicAgent(color="StandardHeuristic")
        # Alternate starting player (P0 vs P1) each game to remove first-player advantage
        if i % 2 == 0:
            agents = [evolved_agent, opponent_agent]
            evolved_idx, opp_idx = 0, 1
        else:
            agents = [opponent_agent, evolved_agent]
            evolved_idx, opp_idx = 1, 0
        # Play game
        gs = playEvol(agents, seed=seed, verbose=False, max_actions=2000)
        winner = gs.winner()
        # Record metrics
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
    # Summary Statistics
    win_rate = (evolved_wins / num_games) * 100
    avg_e_vp = sum(evolved_vps) / num_games
    avg_o_vp = sum(opponent_vps) / num_games
    print(f"------------------------------------------")
    print(f"Summary vs {opponent_type.upper()}:")
    print(f"  Win Rate:         {win_rate:.1f}% ({evolved_wins}/{num_games})")
    print(f"  Avg Evolved VP:   {avg_e_vp:.2f}")
    print(f"  Avg Opponent VP:  {avg_o_vp:.2f}")
    print(f"==========================================\n")
    
if __name__ == "__main__":
    trainer = CoEvolutionTrainer(
        population_size=16, 
        n_generations=10, 
        games_per_round=4,
        elite_fraction=0.2, 
        tournament_k=8, 
        mutation_rate=0.35,
        mutation_sigma=0.25, 
        max_actions_per_game=600, 
        seed=None
    )
    trainer.runEvolution(verbose=True)
    print("\n--- Training Complete ---")
    best_weights = trainer.best_genome()
    print("\nBest Genome Discovered:")
    print(best_weights)
    # 2. Benchmark Benchmark 1: 10 Games vs Random Agent
    evaluate_vs_opponent(best_weights, opponent_type="random", num_games=10)
    # 3. Benchmark Benchmark 2: 10 Games vs Standard Heuristic Agent
    evaluate_vs_opponent(best_weights, opponent_type="heuristic", num_games=10)
     