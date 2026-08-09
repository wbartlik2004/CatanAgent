"""
MCTS agent for our Catan game.

At each AGENT decision point:
- turn current state into tree root
- UCB formula to descend tree
- at unexplored node (untried actions): pick an action, apply that action, then new game state is child node
- from that child node, play game to some depth n (some number of turns) and assign a value to that outcome
    - value based on eval function, could use ga to evolve eval func?
- repeat as many teimes as feasible; ideally until all child nodes have been thoroughly explored
- tree will grow more where promising moves are made, exploring more future outcomes from decent children/grandchildren
- choose in-game action based off child node with the most visits or highest avg per visit

"""
import random
import rules



class Node:
    """
    Each tree ndoe will represent one game state. Each node will need to hold:
    - parent node
    - action from parent -> child
    - children
    - actions possible from node that havent yet generated children, untried actions
    - value of that node based on value of states reached from that node
    - number of times node has been visited
    - game state at node
    need to figure out how/if we wanna handle 4 player with MCTS
    """

    __slots__ = ("state", "parent", "action_from_parent", "children", "untried_actions", "visits", "value_sums")

    def __init__(self, state, parent=None, action_from_parent=None):
        self.state = state
        self.parent = parent
        self.action_from_parent = action_from_parent
        self.childen = {}
        self.untried_actions = list(rules.legal_actions(state))
        self.visits = 0
        self.value_sums =

    # nedd some identifier for terminal nodes and nodes that have no more untried actions
    def is_fully_expanded(self):
        return len(self.untried_actions) == 0

    def is_terminal(self):
        return self.state.is_terminal()

    # and need to calculate avg value of nodes for UCB descent
    def q(self, player):
        return self.value_sums[player] / self.visits if self.visits else 0.0


class MCTSAgent:
    """
    MCTS Agent is going to need:
    - Selection
    - Expansion
    - Rollout
    - Backpropagation


    *big shoutout to github users "ai-boson" and "gist"*
    """
    def __init__(self, n_simulations, c, rollout_depth, rollout_weights, seed):
        self.n_simulations = n_simulations
        self.c = c
        self.rollout_depth = rollout_depth
        self.rollout_weights = rollout_weights
        self.rng = random.Random(seed)

    def choose_action(self, gs, player_index):
        """
        Choose action function that will replace our main.py random choice
        Builds tree from Node(gs), runs S/E/R/B loop n_simulations times, returns
        the most visited child.

        Needs methods for S/E/R/B still

        Also probably needs edge cases if a player's only move is to end their turn
        """
        actions = rules.legal_actions(gs)

        root = Node(gs)
        for _ in range(self.n_simulations):
            node = self._select(root)
            node = self._expand(node)
            values = self._rollout(node)
            self._backpropogate(node)

        best = max(root.children.values())
        return #best action from parent -> bes child

    def _select(self, node):
        pass

    def _expand(self,node):
        pass

    def _rollout(self):
        pass

    def _backpropagate(self):
        pass

    def _ucb(self, child):
        pass





