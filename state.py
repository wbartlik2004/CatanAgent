import copy
import random

### CONSTANTS ###
# resource/dev card types to key player hands; hand[player]["resource"]
RESOURCES = ["WOOD", "BRICK", "SHEEP", "WHEAT", "ORE"]
DEV_TYPES = ["KNIGHT", "VICTORY_POINT", "ROAD_BUILDING", "YEAR_OF_PLENTY", "MONOPOLY"]

DEV_DECK_COUNTS = {"KNIGHT": 14, "VICTORY_POINT": 5, "ROAD_BUILDING": 2, "YEAR_OF_PLENTY": 2,
                    "MONOPOLY": 2}

BUILDING_COSTS = {
    "ROAD": {"WOOD": 1, "BRICK": 1},
    "SETTLEMENT": {"WOOD": 1, "BRICK": 1, "SHEEP": 1, "WHEAT": 1},
    "CITY": {"WHEAT": 2, "ORE": 3},
}
DEV_CARD_COST = {"SHEEP": 1, "WHEAT": 1, "ORE": 1}

PIECE_LIMITS = {"ROAD": 15, "SETTLEMENT": 5, "CITY": 4}

BANK_TRADE_RATIO = 4  # no ports modeled yet; always 4:1 with the bank

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
# All phase constants in a fixed order, used for a fixed-length phase
# one-hot in GameState.to_vector().
ALL_PHASES = [SETUP_SETTLEMENT, SETUP_ROAD, ROLL, DISCARD, MOVE_ROBBER, STEAL,
              MAIN, DEV_DRAW, ROAD_BUILDING, YEAR_OF_PLENTY, MONOPOLY, GAME_OVER]

# Fixed category order for one-hot tile-resource encoding in to_vector().
# "NONE" represents the desert (tile["resource"] is None).
TILE_RESOURCE_CATEGORIES = RESOURCES + ["NONE"]


class GameState:
    def __init__(self, board, n_players=4):

        self.board = board
        self.n = n_players
        self.phase = SETUP_SETTLEMENT
        self.current = 0

        # each player needs a hand full of resources, all of which start at 0
        self.hands = [{r: 0 for r in RESOURCES} for _ in range(n_players)]

        self.settlements = {}   # vertex_id -> player index
        self.cities = {}        # vertex_id -> player index
        self.roads = {}         # (v1, v2) -> player index

        # robber starts on the desert tile if one exists, else tile 0
        desert = next((t["id"] for t in board.tiles if t["resource"] is None), 0)
        self.robber_tile = desert

        self.dev_deck = dict(DEV_DECK_COUNTS)
        self.dev_hands = [{d: 0 for d in DEV_TYPES} for _ in range(n_players)]
        self.dev_bought_this_turn = []
        self.dev_played_this_turn = False
        self.knights_played = [0] * n_players

        self.longest_road_holder = None
        self.largest_army_holder = None

        self.last_roll = None
        self.discards_needed = [0] * n_players

        self.pending_discards = []       # queue of player indices still owing a discard
        self.free_roads_remaining = 0    # counts down during ROAD_BUILDING dev card
        self.setup_order = self._build_setup_order(n_players)  # snake draft
        self.setup_index = 0             # position within setup_order
        self.last_setup_vertex = None    # vertex just placed, so SETUP_ROAD knows what to attach to
        self.robber_victim_pending = None  # set by MOVE_ROBBER when a steal is owed, consumed by STEAL
        self.winner_id = None


    def copy(self):
        return copy.deepcopy(self)

    def __deepcopy__(self, memo):
        memo[id(self.board)] = self.board
        new = self.__class__.__new__(self.__class__)
        memo[id(self)] = new
        for k, v in self.__dict__.items():
            setattr(new, k, copy.deepcopy(v, memo))
        return new

    def current_player(self):
        """
        Index of player whose turn it is to act
        """
        if self.phase == DISCARD and self.pending_discards:
            return self.pending_discards[0]
        return self.current

    def is_chance_node(self):
        """
        Chance node -> not up to agent. Not chance node -> agent decision point
        """
        return self.phase in CHANCE_PHASES

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
        return self.winner_id



    def victory_points(self, player):
        """
        Total VP for `player`: 1 per settlement, 2 per city, +2 for longest
        road / largest army if held, +1 per VICTORY_POINT dev card in hand.
        (God-view simplification: VP dev cards counted even though in a
        real game they're hidden until played/win.)
        """
        vp = 0
        vp += sum(1 for owner in self.settlements.values() if owner == player)
        vp += sum(2 for owner in self.cities.values() if owner == player)
        if self.longest_road_holder == player:
            vp += 2
        if self.largest_army_holder == player:
            vp += 2
        vp += self.dev_hands[player]["VICTORY_POINT"]
        return vp

    @staticmethod
    def vector_length(n_players):
        """Exact length of to_vector()'s output for a game with n_players,
        without having to build one. Useful for sizing a model's input
        layer ahead of time."""
        tile_len = 19 * (len(TILE_RESOURCE_CATEGORIES) + 2)       # +number, +robber flag
        vertex_len = 54 * (2 * n_players + 1)                     # NONE + settlement-by-p + city-by-p
        edge_len = 72 * (n_players + 1)                           # NONE + owner-by-p
        per_player_len = n_players * (len(RESOURCES) + len(DEV_TYPES) + 4)
        # +4 = victory_points, knights_played, is_longest_road_holder, is_largest_army_holder
        global_len = 1 + n_players + len(ALL_PHASES) + len(DEV_TYPES)
        return tile_len + vertex_len + edge_len + per_player_len + global_len

    def _player_order(self, perspective_player):
        """Absolute seat order (0..n-1) by default. If perspective_player is
        given, rotates so that player is first and turn order continues from
        there -- lets one set of agent weights/genome behave identically
        regardless of which seat it's sitting in."""
        if perspective_player is None:
            return list(range(self.n))
        return [(perspective_player + i) % self.n for i in range(self.n)]

    def to_vector(self, perspective_player=None):
        """
        Flattens this GameState into one fixed-length list of floats:
            - per tile:   resource one-hot (WOOD/BRICK/SHEEP/WHEAT/ORE/NONE), dice number, robber-here flag
            - per vertex: NONE / SETTLEMENT-by-player / CITY-by-player one-hot
            - per edge:   NONE / road-owner-by-player one-hot
            - per player: resource hand, dev card hand, victory points, knights played, longest-road flag, largest-army flag
            - global:     last dice roll, current-player one-hot, phase one-hot, remaining dev deck counts
        Computed fresh from live state every call (board/settlements/hands/
        etc.) -- nothing here is cached, so it's always consistent with
        whatever GameState it's called on. If `perspective_player` is given, every per-player block (vertices,
        edges, per-player stats, current-player one-hot) is reordered so that player's data comes first, in turn order from there. Leave it
        None for a fixed, absolute seat-0..seat-(n-1) ordering instead. Output is raw, unnormalized floats/0-1 flags -- scale before feeding
        into a model that expects normalized inputs. Length is deterministic for a given self.n; see vector_length(n) to get it without building
        a vector. """

        order = self._player_order(perspective_player)
        vec = []

        # --- tiles ---
        for tile in self.board.tiles:
            resource = tile["resource"] if tile["resource"] else "NONE"
            for cat in TILE_RESOURCE_CATEGORIES:
                vec.append(1.0 if cat == resource else 0.0)
            vec.append(float(tile["number"] or 0))
            vec.append(1.0 if tile["id"] == self.robber_tile else 0.0)

        # --- vertices ---
        for v in sorted(self.board.vertices):
            owner, building = None, None
            if v in self.cities:
                owner, building = self.cities[v], "CITY"
            elif v in self.settlements:
                owner, building = self.settlements[v], "SETTLEMENT"

            vec.append(1.0 if owner is None else 0.0)
            for p in order:
                vec.append(1.0 if (owner == p and building == "SETTLEMENT") else 0.0)
            for p in order:
                vec.append(1.0 if (owner == p and building == "CITY") else 0.0)

        # --- edges ---
        for e in sorted(self.board.edges):
            owner = self.roads.get(e)
            vec.append(1.0 if owner is None else 0.0)
            for p in order:
                vec.append(1.0 if owner == p else 0.0)

        # --- per-player stats, in (possibly rotated) order ---
        for p in order:
            hand = self.hands[p]
            for r in RESOURCES:
                vec.append(float(hand[r]))
            dev_hand = self.dev_hands[p]
            for d in DEV_TYPES:
                vec.append(float(dev_hand[d]))
            vec.append(float(self.victory_points(p)))
            vec.append(float(self.knights_played[p]))
            vec.append(1.0 if self.longest_road_holder == p else 0.0)
            vec.append(1.0 if self.largest_army_holder == p else 0.0)

        # --- global scalars ---
        vec.append(float(self.last_roll or 0))
        current = self.current_player()
        for p in order:
            vec.append(1.0 if p == current else 0.0)
        for ph in ALL_PHASES:
            vec.append(1.0 if self.phase == ph else 0.0)
        for d in DEV_TYPES:
            vec.append(float(self.dev_deck[d]))

        expected = self.vector_length(self.n)
        assert len(vec) == expected, f"to_vector length mismatch: got {len(vec)}, expected {expected}"
        return vec


    '''settlement/road setup helpers'''
    @staticmethod
    def _build_setup_order(n_players):
        # standard Catan snake draft: 0,1,...,n-1, n-1,...,1,0
        forward = list(range(n_players))
        return forward + list(reversed(forward))


