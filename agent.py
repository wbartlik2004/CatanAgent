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
    "roads": 4.0,
    "resource_total": 0.50,
    "dev_cards": 2.0,
    "longest_road_bonus": 2.0,   
    "largest_army_bonus": 2.0,   
    "resource_diversity": 2.0,
    "dice_prob": 144
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
            score = _evaluate_action(game_state, a, player_index, self.weights)
            if score > best_score:
                best_action, best_score = a, score
        return best_action

def _evaluate_action(game_state, action, player_index, weights):
    resulting_state = rules.apply(game_state, action)
    if action["type"] != "TRADE_BANK":
        return evaluate_state(resulting_state, player_index, weights)
    follow_up_actions = rules.legal_actions(resulting_state)
    if not follow_up_actions:
        return evaluate_state(resulting_state, player_index, weights)
    best_follow_up_score = float("-inf")
    for follow_up in follow_up_actions:
        follow_up_state = rules.apply(resulting_state, follow_up)
        score = evaluate_state(follow_up_state, player_index, weights)
        if score > best_follow_up_score:
            best_follow_up_score = score
    return best_follow_up_score
    
class CoEvolutionAgent(Agent):
    """Same greedy 1-ply decision rule as HeuristicAgent, but the weight vector
    ("genome") is meant to be evolved by an outer evolutionary loop rather
    than hand-tuned. genome -> the actual evolvable parameters (dict, same, keys as DEFAULT_WEIGHTS)
    generation -> which generation this individual belongs to games_played -> fitness bookkeeping across a generation
    fitness_history-> per-game results, for computing average fitness
    mutate()/crossover() are provided so an external co-evolution driver (which owns the population and generation loop) can produce offspring
    without reaching into genome internals directly."""
 
    def __init__(self, color, genome=None, generation=0):
        super().__init__(color)
        self.genome = dict(genome) if genome else {k: v * random.uniform(0.9, 1.1) for k, v in DEFAULT_WEIGHTS.items()}
        self.generation = generation
        self.games_played = 0
        self.fitness_history = []  # list of final VP (or win=1/loss=0) per game
 
    def choose_action(self, game_state, player_index):
        actions = rules.legal_actions(game_state)
        if not actions:
            return None
        best_action, best_score = None, float("-inf")
        for a in actions:
            resulting_state = rules.apply(game_state, a)
            score = evaluate_state(resulting_state, player_index, self.genome)
            if score > best_score:
                best_action, best_score = a, score
        return best_action
 
    def record_result(self, final_vp, won):
        """Call once per completed game to feed the evolutionary loop."""
        self.games_played += 1
        self.fitness_history.append({"vp": final_vp, "won": won})
 
    def average_fitness(self):
        if not self.fitness_history:
            return 0.0
        return sum(g["vp"] + (5 if g["won"] else 0) for g in self.fitness_history) / len(self.fitness_history)
 
    def mutate(self, rate=0.2, sigma=0.25):
        """Return a NEW CoEvolutionAgent with a perturbed genome (doesn't mutate self — evolution should compare parent and child, not
        silently overwrite the parent)."""
        child_genome = dict(self.genome)
        for k in child_genome:
            if random.random() < rate:
                child_genome[k] = max(0.0, child_genome[k] + random.gauss(0, sigma))
        return CoEvolutionAgent(self.color, genome=child_genome, generation=self.generation + 1)
 
    def crossover(self, other):
        """Uniform crossover: each weight independently comes from self or
        other. Returns a new offspring CoEvolutionAgent."""
        child_genome = {}
        for k in self.genome:
            child_genome[k] = self.genome[k] if random.random() < 0.5 else other.genome[k]
        return CoEvolutionAgent(self.color, genome=child_genome, generation=max(self.generation, other.generation) + 1)