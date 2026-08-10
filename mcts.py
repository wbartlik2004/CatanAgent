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
import json

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
        node.children[_action_key(action)]
        pass




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
            w = rules.winner(state)
            return {p: (1.0 if w == p else 0.0) for p in range(state.n)}

        # and for a rollout ending at nonterminal state
        # we'll apply our custom weights, need helper function for now placeholder eval_state
        else:
            return {p: evaluate_state(state, p, self.rollout_weights) for p in range(state.n)}
        pass

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


    def _ucb(self, child):
        pass





def _action_key(action):
        """
        Helper
        node.children[action] = child gives errors beacuse action = {"type": "BUILD_ROAD", "edge": (7,8)}
        dictionaries mutable
        so need to freeze dictionary; at CST we used json dumps for this
        """
        return json.dumps(action, sort_keys=True)