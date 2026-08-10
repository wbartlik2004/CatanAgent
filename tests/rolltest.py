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
agent = MCTSAgent("t", n_simulations=100, c=1.5, rollout_depth=50, rollout_weights=JACK_DEFAULT_WEIGHTS, seed=0)
print(agent._rollout(gs))
print(agent._rollout(gs))
print(agent._rollout(gs))