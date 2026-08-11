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
import math
import random
import rules
import json
from eval import evaluate_state

# will's default weights (he cheated a little)
WILL_DEFAULT_WEIGHTS = {
    "victory_points": 10.0,
    "settlements": 4.0,
    "cities": 8.0,
    "roads": 4,
    "resource_total": 0.25,
    "dev_cards": 1,
    "longest_road_bonus": 2,
    "largest_army_bonus": 2,
    "resource_diversity": 0.5,
}

# jack's default weights

# Will had to tune up some weights (roads) because greedy agent was trash
# but MCTS looks way further, can set weights to 0 and see how agent reacts
JACK_DEFAULT_WEIGHTS = {
    "victory_points": 6.0,
    "settlements": 4.0,
    "cities": 8.0,
    "roads": 2.0,
    "resource_total": 0.5,
    "dev_cards": 1.0,
    "longest_road_bonus": 2,
    "largest_army_bonus": 2,
    "resource_diversity": 0.5,
}



# so what if we just weight by catan weightings?
CATAN_DEFAULT_WEIGHTS = {
    "victory_points": 10.0,
    "settlements": 2.0,
    "cities": 4.0,
    "roads": 4,
    "resource_total": 0.2,
    "dev_cards": 0.4, #this ones tough to quantify because dev cards have victory point value
    # of 1/5 = 2/5 since im doubling, but some dev cards can help more... 0.5
    "longest_road_bonus": 2,
    "largest_army_bonus": 2,
    "resource_diversity": 0.5,
}




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
        self.children = {}
        self.untried_actions = list(rules.legal_actions(state))
        self.visits = 0
        # read backprop; if we want 4 players, we can't just return one value like typical MCTS
        self.value_sums = {p: 0.0 for p in range(state.n)}

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
    def __init__(self, player, n_simulations, c, rollout_depth, rollout_weights, seed):
        self.player = player
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
            values = self._rollout(node.state)
            self._backpropagate(node, values)

        best = max(root.children.values(), key=lambda ch: ch.visits)
        return best.action_from_parent

    def _select(self, node):
        """
        Start at root node
        Walk down exisiting nodes (which are fully expanded, have no untried actions left)
        Checking if untried actions/terminal
        If node is untried or terminal, we expand it
        """
        # so if we're at a non-terminal node that has untried actions, return that node for expand
        # and in the case that the node has been expanded, move on to its best child by UCB
        # will require helper - like ai-boson implementation
        while not node.is_terminal():
            if node.untried_actions:
                return node
            node = self._best_child(node)
        # and in the case that the node is terminal, we can just return that node for rollout
        return node

    def _best_child(self, node):
        """
        Helper function allowing select to move down tree from
        one fully-expanded node to its child with highest value
        """
        # if a node is a chance node it doesn't have a best child,
        # and we need to just pick one from prob dist, done many times
        if node.state.is_chance_node():
            children = list(node.children.values())
            weights = [ch.action_from_parent["prob"] for ch in children]
            return self.rng.choices(children, weights=weights)[0]

        # for player decision nodes, if a child node is unvisited we have to return that node for selection
        mover = node.state.current_player()
        for ch in node.children.values():
            if ch.visits == 0:
                return ch

        # if children all visited, return the child with the highest UCB score
        return max(node.children.values(), key=lambda ch: self._ucb(ch, mover))

    def _ucb(self, child, mover):
        """
        UCB formula implementation: Q(s, a) + c * (ln(parent visits) / child visits)
        The point of UCB is, as we went over in class, to balance expansion into
        nodes suspected to be good with exploration of nodes we have little data on

        """
        exploit = child.q(mover)
        explore = self.c * math.sqrt(math.log(child.parent.visits) / child.visits)
        return exploit + explore

    def _expand(self,node):
        """
        At a node with untried actions (unexplored children):
        Pick some untried action
        Use rules.apply to enact action, go from current game state (node)
        to next game state (child)
        Wrap Node(child game state)

        action_key(action) turns action dict to string for hashing purposes

        """
        if node.is_terminal():
            return node

        # random action from list of unexplored actions
        action = self.rng.choice(node.untried_actions)

        # and remove from list
        node.untried_actions.remove(action)

        # new Node obj out of child
        child_state = rules.apply(node.state, action)
        child = Node(child_state, parent=node, action_from_parent=action)
        #node.children[action] = child
        node.children[_action_key(action)] = child
        return child




    def _rollout(self, state):
        """
        A rollout will output a dict of form value_sums that will be backprogated
        back up the tree. To do so we need to
        - take in a state Node
        - play n actions, n = rollout_depth (or until end of game, <= n)
        - return value_sums dict judging resulting state for each player ind

        """
        depth = 0
        # i think it will be basically the main.py test runner
        # oh then I totally should use randonm seeds
        while not state.is_terminal() and depth < self.rollout_depth:
            actions = rules.legal_actions(state)
            if state.is_chance_node():
                action = self.rng.choices(actions, weights=[a["prob"] for a in actions])[0]
            else:
                action = self.rng.choice(actions)
            state = rules.apply(state, action)
            depth += 1

        # then for generating the value dicts once rollout_depth reached
        # for a rollout ending in p0 winning the game we want {p0: 1, p1: 0, p2: 0...}
        if state.is_terminal():
            w = state.winner()
            return {p: (1.0 if w == p else 0.0) for p in range(state.n)}

        # and for a rollout ending at nonterminal state
        # we'll apply our custom weights, need helper function for now placeholder eval_state
        # but this will value terminal states differently from depth-capped rollouts, probably need to normalize
        # the depth cap evals to 0-1
        else:
            return {p: evaluate_state(state, p, self.rollout_weights) for p in range(state.n)}
        pass

        #but

    def _backpropagate(self, node, values):
        """
        The goal is to make this usable for 4-player games, so we can't just return
        a value up the tree like typical MCTS. But also I really would like it to mainly
        be used for 2-player so will still support it.

        Send values dict like {p0: 1.0, p1: 0.0, p2: 0.0} back up tree, adding it to each
        parent node's respective values dict. Then per player calculations can be made.
        And in 2-p games the dict will just be {p0: n, p1: -n}

        Backprop will take in values dict output rollout
        Add to parent's value_sums
        Move to grandparent
        Add to grandparent's value_sums...
        """
        while node is not None:
            # update node's visit count
            node.visits += 1

            # add each player's rollout output score to node's value_sums
            for p, v in values.items():
                node.value_sums[p] += v
            # switch to parent node
            node = node.parent

def _action_key(action):
    """
    Helper
    node.children[action] = child gives errors beacuse action = {"type": "BUILD_ROAD", "edge": (7,8)}
    dictionaries mutable
    so need to freeze dictionary; at CST we used json dumps for this
    """
    return json.dumps(action, sort_keys=True)