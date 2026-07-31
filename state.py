"""
state.py
game state interface that
currently:
game data
future:
rules of game
"""
import copy

### CONSTANTS ###
# resource/dev card types to key player hands; hand[player]["resource"]
RESOURCES = ["WOOD", "BRICK", "SHEEP", "WHEAT", "ORE"]
DEV_TYPES = ["KNIGHT", "VICTORY_POINT", "ROAD_BUILDING", "YEAR_OF_PLENTY", "MONOPOLY"]

DEV_DECK_COUNTS = {"KNIGHT": 14, "VICTORY_POINT": 5, "ROAD_BUILDING": 2, "YEAR_OF_PLENTY": 2,
                    "MONOPOLY": 2}

# die for MCTS chance nodes implementation
DICE_PROB = {2: 1/36, 3: 2/36, 4: 3/36, 5: 4/36, 6: 5/36, 7: 6/36,
             8: 5/36, 9: 4/36, 10: 3/36, 11: 2/36, 12: 1/36}

# necessary value limits for turns
VP_TO_WIN = 10
DISCARD_LIMIT = 6
LONGEST_ROAD_MIN = 5
LARGEST_ARMY_MIN = 3

# TURN PHASES #
# each of these phases will be one phase node of one turn

# 1. opening turn phases
SETUP_SETTLEMENT = "SETUP_SETTLEMENT"
SETUP_ROAD = "SETUP_ROAD"

# 2. general turn phases
ROLL = "ROLL"   # chance; what was rolled?
DISCARD = "DISCARD"    # 7 rolled, player must discard
MOVE_ROBBER = "MOVE_ROBBER"    # choose robber tile + steal victim
STEAL = "STEAL"  # chance; which card was stolen?
MAIN = "MAIN"   # build / trade / buy dev / play dev / end

# 3. dev-specific turn phases
DEV_DRAW = "DEV_DRAW"   # chance; which dev card was drawn?
ROAD_BUILDING = "ROAD_BUILDING"      # 2 free roads to place from dev card
YEAR_OF_PLENTY = "YEAR_OF_PLENTY"     # 2 free resources to add to hand from dev card
MONOPOLY = "MONOPOLY"           # name the resource to steal all of

# 4. GAME OVER probably
GAME_OVER = "GAME_OVER"

CHANCE_PHASES = {ROLL, STEAL, DEV_DRAW}



class GameState:
    """
    everything mutable (not board) will live in GameState
    """
    def __init__(self, board, n_players=4):

        self.board = board
        self.n = n_players
        self.phase = SETUP_SETTLEMENT
        self.current = 0

        # each player needs a hand full of resources, all of which start at 0
        self.hands = [{r: 0 for r in RESOURCES} for _ in range(n_players)]

        self.settlements =
        self.cities =
        self.roads =


        self.robber_tile =


        self.dev_deck = dict(DEV_DECK_COUNTS)
        self.dev_hands = [{d: 0 for d in DEV_TYPES} for _ in range(n_players)]
        self.dev_bought_this_turn =
        self.dev_played_this_turn = False
        self.knights_played = [0] * n_players


        self.longest_road_holder =
        self.largest_army_holder =

        self.last_roll = None
        self.discards_needed = [0] * n_players


    def current_player(self):
        """
        Index of player whose turn it is to act
        """
        return self.current

    def is_chance_node(self):
        """
        Chance node -> not up to agent. Not chance node -> agent decision point
        """
        return self.phase in CHANCE_PHASES

    def legal_actions(self):
        """
        NEED A LOT OF STUFF IN HERE;; ENUMERATE ALL LEGAL MOVES AT PHASE X FOR AGENTS
        """
        pass

    def apply(self, action):
        """
        Will take in GAME STATE X, AGENT (OR NON_AGENT in case of chance node) ACTION Y
        Returns NEW GAME STATE S
        To be used at each agent decision point
        """
        pass

    def is_terminal(self):
        """
        apply(action) returns game state S. if S == GAME_OVER, then terminal game state
        """
        return self.phase == GAME_OVER

    def winner(self):
        """
        At terminal game state S, must decide winner, which will be player with >=10 VP
        Or less VP if we choose more simple game tree, which is why VP not hardcoded in the first place
        """
        if not self.is_terminal():
            return None
        for p in range(self.n):
            if self.victory_points(p) >= VP_TO_WIN:
                return p
        return None








