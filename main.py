import random
from board import Board
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

# testing
if __name__ == "__main__":
    for seed in (1, 2):
        for n in (1, 2):
            gs = play(seed, n, verbose=True)
            print(f"seed {seed}: winner=P{gs.winner()} "
                f"VPs={[gs.victory_points(p) for p in range(gs.n)]}")



