import math
import random
from board import Board
from state import GameState, RESOURCES, GAME_OVER
import rules

class Agent:
    """Minimal identity + decision-policy interface. All actual game data
    lives in GameState — an Agent is just "a color plus a policy"."""

    def __init__(self, color):
        self.color = color

    def choose_action(self, game_state, player_index):
        raise NotImplementedError


def play_game(agents, board=None, max_actions=6000, seed=None):
    """
    Runs one full game with the given list of Agent instances (index = player
    index) from a fresh setup through GAME_OVER (or until max_actions is hit,
    as a safety cap). Returns the final GameState. Shared by tests and by
    the co-evolution trainer so there's one canonical game loop.
    """
    if seed is not None:
        random.seed(seed)
    if board is None:
        board = Board()
 
    gs = GameState(board, n_players=len(agents))
    actionNum = 0
    while gs.phase != GAME_OVER and actionNum < max_actions:
        actions = rules.legal_actions(gs)
        if gs.is_chance_node():
            outcome = sample_chance_outcome(gs)
            if outcome is None:
                break
            gs = rules.apply(gs, outcome)
        else:
            p = gs.current_player()
            action = agents[p].choose_action(gs, p)
            if action is None:
                break
            gs = rules.apply(gs, action)
        actionNum += 1
    return gs

DEFAULT_WEIGHTS = {
    "victory_points": 10.0,
    "settlements": 4.0,
    "cities": 8.0,
    "roads": 0.5,
    "resource_total": 0.2,
    "dev_cards": 0.25,
    "longest_road_bonus": 2,   
    "largest_army_bonus": 2,   
}

def evaluate_state(game_state, player_index, weights=DEFAULT_WEIGHTS):
    s = game_state
    hand = s.hands[player_index]

    n_settlements = sum(1 for owner in s.settlements.values() if owner == player_index)
    n_cities = sum(1 for owner in s.cities.values() if owner == player_index)
    n_roads = sum(1 for owner in s.roads.values() if owner == player_index)
    n_dev = sum(s.dev_hands[player_index].values())
    resource_total = sum(hand.values())

    score = 0.0
    score += weights["victory_points"] * s.victory_points(player_index)
    score += weights["settlements"] * n_settlements
    score += weights["cities"] * n_cities
    score += weights["roads"] * n_roads
    score += weights["resource_total"] * resource_total
    score += weights["dev_cards"] * n_dev
    if s.longest_road_holder == player_index:
        score += weights["longest_road_bonus"]
    if s.largest_army_holder == player_index:
        score += weights["largest_army_bonus"]
    return score

def sample_chance_outcome(game_state, rng=random):
    """Sample a chance-node action according to its listed probabilities.
    Used by rollouts/simulations; game-loop code should call this directly
    for ROLL/STEAL/DEV_DRAW phases rather than routing through an agent."""
    actions = rules.legal_actions(game_state)
    if not actions:
        return None
    weights = [a.get("prob", 1) for a in actions]
    return rng.choices(actions, weights=weights, k=1)[0]

class RandomAgent(Agent):

    def __init__(self, color, seed=None):
        super().__init__(color)
        self.rng = random.Random(seed)

    def choose_action(self, game_state, player_index):
        actions = rules.legal_actions(game_state)
        if not actions:
            return None
        return self.rng.choice(actions)

class HeuristicAgent(Agent):
    """Greedy 1-ply lookahead: tries every legal action, evaluates the
    resulting state with a fixed weight vector, picks the best. Tracks its
    weights (tunable by hand) as the "relevant information" that defines
    its behavior."""

    def __init__(self, color, weights=None):
        super().__init__(color)
        self.weights = dict(weights) if weights else dict(DEFAULT_WEIGHTS)

    def choose_action(self, game_state, player_index):
        actions = rules.legal_actions(game_state)
        if not actions:
            return None

        best_action, best_score = None, float("-inf")
        for a in actions:
            resulting_state = rules.apply(game_state, a)
            score = evaluate_state(resulting_state, player_index, self.weights)
            if score > best_score:
                best_action, best_score = a, score
        return best_action