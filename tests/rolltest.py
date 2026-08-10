"""
Gonna test rolluots by simming a game up to some move, letting MCTS agent rollout from there
Node, rollout, backprop, expand written currently
"""

import random
from board import Board
import state, rules
from mcts import MCTSAgent, JACK_DEFAULT_WEIGHTS

# simple game sim
rng = random.Random(0)
gs = state.GameState(Board(), 2)
for _ in range(50):
    acts = rules.legal_actions(gs)
    a = rng.choices(acts, weights=[x["prob"] for x in acts])[0] if gs.is_chance_node() else rng.choice(acts)
    gs = rules.apply(gs, a)

# then run three rollouts, seeing as rollout starts with
# picking random action
# so three random action rollouts
agent = MCTSAgent("test", n_simulations=100, c=1.5, rollout_depth=50, rollout_weights=JACK_DEFAULT_WEIGHTS, seed=0)
print(agent._rollout(gs))
print(agent._rollout(gs))
print(agent._rollout(gs))

"""
yeah I have to fix a few things regarding how positions are evaluated in the rollout
this test eturned:
{0: 28.0, 1: 35.5}
{0: 35.5, 1: 28.5}
{0: 29.5, 1: 29.5}

had a terminal state been reached in one test, it would have returned {0: 1.0, 1: 0.0}
and that would be backpropagated up the tree
adding {0: 1.0, 1: 0.0} to each parent's value sums

whose magnitudes are dwarfed by those of the values we just reached in non-terminal states
So must normalize non-terminal values preferably to 1-0 scale

all = add up all vals in values
for player in range(state.n):
divide value by all

then, no matter the dict, all values will add up to 1

"""