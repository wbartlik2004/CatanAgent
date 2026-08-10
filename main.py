import random

import outcome
from agent import HeuristicAgent, RandomAgent, sample_chance_outcome
from board import Board
from coevolutionHelp import CoEvolutionTrainer
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
    for seed in (1, 2):
        agents = [RandomAgent(color="red", seed=seed), HeuristicAgent(color="blue")]
        gs = play2(agents, seed=seed, verbose=True)
        print(f"seed {seed}: winner=P{gs.winner()} "
              f"VPs={[gs.victory_points(p) for p in range(gs.n)]}")'''

if __name__ == "__main__":
    trainer = CoEvolutionTrainer(population_size=8, n_generations=10, games_per_round=1,
                                 elite_fraction=0.25, tournament_k=3, mutation_rate=0.2,
                                 mutation_sigma=0.5, max_actions_per_game=4000, seed=None)
    trainer.runEvolution(verbose=True)
    print("\n--- Training Complete ---")
    best_weights = trainer.best_genome()
    print("\nBest Genome Discovered:" + f"\n{best_weights}")
    
    
    