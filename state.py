import copy
import random
from topologyhelpers import _distance_rule_ok, _edges_at_vertex, _canon_edge, _vertex_neighbors, _player_road_vertices, _settlement_connected, _road_connected, _is_occupied, _tile_vertices


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
        for p in range(self.n):
            if self.victory_points(p) >= VP_TO_WIN:
                return p
        return None

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

    def legal_actions(self):
        """
        NEED A LOT OF STUFF IN HERE;; ENUMERATE ALL LEGAL MOVES AT PHASE X FOR AGENTS
        """
        if self.phase == SETUP_SETTLEMENT:
            return self._legal_setup_settlement()
        if self.phase == SETUP_ROAD:
            return self._legal_setup_road()
        if self.phase == ROLL:
            return self._legal_roll()
        if self.phase == DISCARD:
            return self._legal_discard()
        if self.phase == MOVE_ROBBER:
            return self._legal_move_robber()
        if self.phase == STEAL:
            return self._legal_steal()
        if self.phase == MAIN:
            return self._legal_main()
        if self.phase == DEV_DRAW:
            return self._legal_dev_draw()
        if self.phase == ROAD_BUILDING:
            return self._legal_road_building()
        if self.phase == YEAR_OF_PLENTY:
            return self._legal_year_of_plenty()
        if self.phase == MONOPOLY:
            return self._legal_monopoly()
        if self.phase == GAME_OVER:
            return []
        raise ValueError(f"Unknown phase: {self.phase}")

    def apply(self, action):
        """
        Will take in GAME STATE X, AGENT (OR NON_AGENT in case of chance node) ACTION Y
        Returns NEW GAME STATE S
        To be used at each agent decision point
        """
        s = copy.deepcopy(self)

        if s.phase == SETUP_SETTLEMENT:
            s._apply_setup_settlement(action)
        elif s.phase == SETUP_ROAD:
            s._apply_setup_road(action)
        elif s.phase == ROLL:
            s._apply_roll(action)
        elif s.phase == DISCARD:
            s._apply_discard(action)
        elif s.phase == MOVE_ROBBER:
            s._apply_move_robber(action)
        elif s.phase == STEAL:
            s._apply_steal(action)
        elif s.phase == MAIN:
            s._apply_main(action)
        elif s.phase == DEV_DRAW:
            s._apply_dev_draw(action)
        elif s.phase == ROAD_BUILDING:
            s._apply_road_building(action)
        elif s.phase == YEAR_OF_PLENTY:
            s._apply_year_of_plenty(action)
        elif s.phase == MONOPOLY:
            s._apply_monopoly(action)
        else:
            raise ValueError(f"Unknown phase: {s.phase}")

        return s

    '''settlement/road setup helpers'''
    @staticmethod
    def _build_setup_order(n_players):
        # standard Catan snake draft: 0,1,...,n-1, n-1,...,1,0
        forward = list(range(n_players))
        return forward + list(reversed(forward))

    def _legal_setup_settlement(self):
        free_vertices = [v for v in self.board.vertices if _distance_rule_ok(self, v)]
        return [{"type": "BUILD_SETTLEMENT", "vertex": v} for v in free_vertices]

    def _apply_setup_settlement(self, action):
        v = action["vertex"]
        p = self.setup_order[self.setup_index]
        self.settlements[v] = p
        self.last_setup_vertex = v

        # second settlement of setup grants starting resources (standard rule)
        is_second_pass = self.setup_index >= self.n
        if is_second_pass:
            for tile in self.board.tiles:
                if v in tile["vertices"] and tile["resource"]:
                    self.hands[p][tile["resource"]] += 1

        self.phase = SETUP_ROAD

    def _legal_setup_road(self):
        v = self.last_setup_vertex
        options = []
        for e in _edges_at_vertex(self,v):
            if e not in self.roads:
                options.append({"type": "BUILD_ROAD", "edge": e})
        return options

    def _apply_setup_road(self, action):
        p = self.setup_order[self.setup_index]
        e = _canon_edge(self, *action["edge"])
        self.roads[e] = p

        self.setup_index += 1
        if self.setup_index >= len(self.setup_order):
            # setup complete, real game begins with player 0's roll
            self.current = 0
            self.phase = ROLL
        else:
            self.current = self.setup_order[self.setup_index]
            self.phase = SETUP_SETTLEMENT

    '''Post Roll'''
    def _legal_roll(self):
        # chance node: the "actions" are the possible dice totals with their probabilities
        return [{"type": "ROLL_RESULT", "value": v, "prob": p} for v, p in DICE_PROB.items()]

    def _apply_roll(self, action):
        total = action["value"]
        self.last_roll = total

        if total == 7:
            self._start_discard_phase()
        else:
            self._distribute_resources(total)
            self.phase = MAIN

    def _distribute_resources(self, roll):
        for tile in self.board.tiles:
            if tile["number"] != roll or not tile["resource"] or tile["id"] == self.robber_tile:
                continue
            res = tile["resource"]
            for v in tile["vertices"]:
                if v in self.settlements:
                    self.hands[self.settlements[v]][res] += 1
                elif v in self.cities:
                    self.hands[self.cities[v]][res] += 2

    def _start_discard_phase(self):
        self.discards_needed = [0] * self.n
        self.pending_discards = []
        for p in range(self.n):
            total = sum(self.hands[p].values())
            if total > DISCARD_LIMIT:
                self.discards_needed[p] = total // 2
                self.pending_discards.append(p)
        if self.pending_discards:
            self.phase = DISCARD
        else:
            self.phase = MOVE_ROBBER

    '''Discarding'''
    def _enumerate_discards(self, hand, need):
        """All ways to pick exactly `need` cards total from `hand`, as
        {resource: count} dicts (only nonzero counts included). Small
        search space at Catan's scale (5 resource types, need <= ~10)."""
        results = []

        def backtrack(idx, remaining, chosen):
            if remaining == 0:
                results.append({r: c for r, c in chosen.items() if c > 0})
                return
            if idx == len(RESOURCES):
                return
            r = RESOURCES[idx]
            max_take = min(hand[r], remaining)
            for take in range(max_take + 1):
                chosen[r] = take
                backtrack(idx + 1, remaining - take, chosen)
            chosen[r] = 0

        backtrack(0, need, {r: 0 for r in RESOURCES})
        return results

    def _legal_discard(self):
        p = self.current_player()
        need = self.discards_needed[p]
        hand = self.hands[p]
        combos = self._enumerate_discards(hand, need)
        return [{"type": "DISCARD", "player": p, "resources": combo} for combo in combos]

    def _apply_discard(self, action):
        p = action["player"]
        to_discard = action["resources"]
        if to_discard is None:
            raise ValueError("DISCARD action must specify a concrete {resource: count} dict")
        needed = self.discards_needed[p]
        if sum(to_discard.values()) != needed:
            raise ValueError(f"Player {p} must discard exactly {needed} cards")
        for r, qty in to_discard.items():
            if self.hands[p][r] < qty:
                raise ValueError(f"Player {p} does not have {qty} {r} to discard")
            self.hands[p][r] -= qty

        self.discards_needed[p] = 0
        self.pending_discards.pop(0)
        if not self.pending_discards:
            self.phase = MOVE_ROBBER

    '''moving robber/stealing'''
    def _legal_move_robber(self):
        options = []
        for tile in self.board.tiles:
            if tile["id"] == self.robber_tile:
                continue
            victims = set()
            for v in tile["vertices"]:
                owner = self.settlements.get(v, self.cities.get(v))
                if owner is not None and owner != self.current:
                    victims.add(owner)
            if victims:
                for victim in victims:
                    options.append({"type": "MOVE_ROBBER", "tile": tile["id"], "victim": victim})
            else:
                options.append({"type": "MOVE_ROBBER", "tile": tile["id"], "victim": None})
        return options

    def _apply_move_robber(self, action):
        self.robber_tile = action["tile"]
        victim = action["victim"]
        if victim is not None and sum(self.hands[victim].values()) > 0:
            self.robber_victim_pending = victim
            self.phase = STEAL
        else:
            self.robber_victim_pending = None
            self.phase = MAIN

    def _legal_steal(self):
        victim = self.robber_victim_pending
        hand = self.hands[victim]
        total = sum(hand.values())
        if total == 0:
            return []
        return [{"type": "STEAL_RESULT", "resource": r, "prob": qty / total}
                for r, qty in hand.items() if qty > 0]

    def _apply_steal(self, action):
        victim = self.robber_victim_pending
        r = action["resource"]
        self.hands[victim][r] -= 1
        self.hands[self.current][r] += 1
        self.robber_victim_pending = None
        self.phase = MAIN

    '''main functions: build, trade, buy dev, play dev, end turn'''

    def _can_afford(self, player, cost):
        return all(self.hands[player][r] >= qty for r, qty in cost.items())

    def _pay(self, player, cost):
        for r, qty in cost.items():
            self.hands[player][r] -= qty

    def _legal_main(self):
        p = self.current
        options = [{"type": "END_TURN"}]

        # --- build road ---
        if self._can_afford(p, BUILDING_COSTS["ROAD"]) and len(self._player_roads(p)) < PIECE_LIMITS["ROAD"]:
            for e in self.board.edges:
                if e not in self.roads and _road_connected(self, e, p):
                    options.append({"type": "BUILD_ROAD", "edge": e})

        # --- build settlement ---
        n_settlements = sum(1 for o in self.settlements.values() if o == p)
        if self._can_afford(p, BUILDING_COSTS["SETTLEMENT"]) and n_settlements < PIECE_LIMITS["SETTLEMENT"]:
            for v in self.board.vertices:
                if _distance_rule_ok(self, v) and _settlement_connected(self, v, p):
                    options.append({"type": "BUILD_SETTLEMENT", "vertex": v})

        # --- build city (upgrade own settlement) ---
        n_cities = sum(1 for o in self.cities.values() if o == p)
        if self._can_afford(p, BUILDING_COSTS["CITY"]) and n_cities < PIECE_LIMITS["CITY"]:
            for v, owner in self.settlements.items():
                if owner == p:
                    options.append({"type": "BUILD_CITY", "vertex": v})

        # --- buy dev card ---
        if self._can_afford(p, DEV_CARD_COST) and sum(self.dev_deck.values()) > 0:
            options.append({"type": "BUY_DEV"})

        # --- play dev card (max one per turn, can't play one bought this turn) ---
        if not self.dev_played_this_turn:
            for d in DEV_TYPES:
                if d == "VICTORY_POINT":
                    continue  # never "played", just banked toward VP
                owned = self.dev_hands[p][d]
                bought_this_turn = self.dev_bought_this_turn.count(d)
                if owned - bought_this_turn > 0:
                    if d == "MONOPOLY":
                        for r in RESOURCES:
                            options.append({"type": "PLAY_DEV", "dev": d, "resource": r})
                    elif d == "YEAR_OF_PLENTY":
                        for i, r1 in enumerate(RESOURCES):
                            for r2 in RESOURCES[i:]:
                                options.append({"type": "PLAY_DEV", "dev": d, "resources": [r1, r2]})
                    else:
                        options.append({"type": "PLAY_DEV", "dev": d})

        # --- trade with bank (no ports modeled: flat 4:1) ---
        for give in RESOURCES:
            if self.hands[p][give] >= BANK_TRADE_RATIO:
                for get in RESOURCES:
                    if get != give:
                        options.append({"type": "TRADE_BANK", "give": give, "get": get,
                                         "ratio": BANK_TRADE_RATIO})

        return options

    def _player_roads(self, player):
        return [e for e, owner in self.roads.items() if owner == player]

    def _apply_main(self, action):
        p = self.current
        t = action["type"]

        if t == "END_TURN":
            self._end_turn()
            return

        if t == "BUILD_ROAD":
            e = _canon_edge(self, *action["edge"])
            self._pay(p, BUILDING_COSTS["ROAD"])
            self.roads[e] = p
            self._update_longest_road()
            return

        if t == "BUILD_SETTLEMENT":
            v = action["vertex"]
            self._pay(p, BUILDING_COSTS["SETTLEMENT"])
            self.settlements[v] = p
            return

        if t == "BUILD_CITY":
            v = action["vertex"]
            self._pay(p, BUILDING_COSTS["CITY"])
            del self.settlements[v]
            self.cities[v] = p
            return

        if t == "BUY_DEV":
            self._pay(p, DEV_CARD_COST)
            self.phase = DEV_DRAW
            return

        if t == "PLAY_DEV":
            self._play_dev(action)
            return

        if t == "TRADE_BANK":
            give, get, ratio = action["give"], action["get"], action["ratio"]
            self.hands[p][give] -= ratio
            self.hands[p][get] += 1
            return

        raise ValueError(f"Unknown MAIN action: {action}")

    def _end_turn(self):
        self.dev_bought_this_turn = []
        self.dev_played_this_turn = False
        self.current = (self.current + 1) % self.n
        self.phase = ROLL
        if self.victory_points(self.current) >= VP_TO_WIN:
            # note: normally you'd check the player who just acted, not the
            # next player; kept simple here since VP is checked continuously
            pass
        # actual win-check belongs after any VP-changing action; see _check_win()
        self._check_win()

    def _check_win(self):
        for p in range(self.n):
            if self.victory_points(p) >= VP_TO_WIN:
                self.phase = GAME_OVER
                return

    def _play_dev(self, action):
        p = self.current
        d = action["dev"]
        self.dev_hands[p][d] -= 1
        self.dev_played_this_turn = True

        if d == "KNIGHT":
            self.knights_played[p] += 1
            self._update_largest_army()
            self.phase = MOVE_ROBBER
        elif d == "ROAD_BUILDING":
            self.free_roads_remaining = 2
            self.phase = ROAD_BUILDING
        elif d == "YEAR_OF_PLENTY":
            for r in action["resources"]:
                self.hands[p][r] += 1
            # stays in MAIN
        elif d == "MONOPOLY":
            r = action["resource"]
            for other in range(self.n):
                if other == p:
                    continue
                self.hands[p][r] += self.hands[other][r]
                self.hands[other][r] = 0
            # stays in MAIN
        else:
            raise ValueError(f"Unknown dev card: {d}")

        self._check_win()

    '''dev draw chance node'''

    def _legal_dev_draw(self):
        total = sum(self.dev_deck.values())
        if total == 0:
            return []
        return [{"type": "DEV_DRAWN", "dev": d, "prob": qty / total}
                for d, qty in self.dev_deck.items() if qty > 0]

    def _apply_dev_draw(self, action):
        d = action["dev"]
        self.dev_deck[d] -= 1
        self.dev_hands[self.current][d] += 1
        self.dev_bought_this_turn.append(d)
        self.phase = MAIN
        self._check_win()

    '''road building dev card phase'''
    def _legal_road_building(self):
        p = self.current
        return [{"type": "BUILD_ROAD", "edge": e} for e in self.board.edges
                if e not in self.roads and _road_connected(self, e, p)]

    def _apply_road_building(self, action):
        p = self.current
        e = _canon_edge(self, *action["edge"])
        self.roads[e] = p  # free: no payment
        self.free_roads_remaining -= 1
        self._update_longest_road()
        if self.free_roads_remaining <= 0:
            self.phase = MAIN

     # -----------------------------------------------------------------
    # (kept for interface completeness; YEAR_OF_PLENTY/MONOPOLY are
    # currently resolved inline in _play_dev rather than as their own
    # phase, since they're single-shot choices with no board interaction.
    # These stay as no-op-shaped hooks in case you want to split them
    # into their own phase nodes later, e.g. for a cleaner MCTS action
    # boundary.)
    # -----------------------------------------------------------------

    def _legal_year_of_plenty(self):
        return []

    def _apply_year_of_plenty(self, action):
        raise RuntimeError("YEAR_OF_PLENTY is resolved inline via PLAY_DEV, not as its own phase")

    def _legal_monopoly(self):
        return []

    def _apply_monopoly(self, action):
        raise RuntimeError("MONOPOLY is resolved inline via PLAY_DEV, not as its own phase")

    # -----------------------------------------------------------------
    # Longest Road / Largest Army
    # -----------------------------------------------------------------

    def _update_largest_army(self):
        best_p, best_n = self.largest_army_holder, LARGEST_ARMY_MIN - 1
        if best_p is not None:
            best_n = self.knights_played[best_p]
        for p in range(self.n):
            if self.knights_played[p] >= LARGEST_ARMY_MIN and self.knights_played[p] > best_n:
                best_p, best_n = p, self.knights_played[p]
        self.largest_army_holder = best_p

    def _update_longest_road(self):
        best_p, best_len = self.longest_road_holder, LONGEST_ROAD_MIN - 1
        if best_p is not None:
            best_len = self._longest_road_length(best_p)
        for p in range(self.n):
            length = self._longest_road_length(p)
            if length >= LONGEST_ROAD_MIN and length > best_len:
                best_p, best_len = p, length
        self.longest_road_holder = best_p

    def _longest_road_length(self, player):
        """
        Longest simple path through `player`'s own roads, breaking at any
        vertex owned (settled) by an opponent. Brute-force DFS from every
        vertex touched by the player's roads — fine at Catan's scale
        (<=15 roads/player, degree <=3 per vertex).
        """
        edges = self._player_roads(player)
        if not edges:
            return 0

        adjacency = {}
        for a, b in edges:
            adjacency.setdefault(a, []).append(b)
            adjacency.setdefault(b, []).append(a)

        def blocked(v):
            owner = self.settlements.get(v, self.cities.get(v))
            return owner is not None and owner != player

        best = 0

        def dfs(v, visited_edges, length):
            nonlocal best
            best = max(best, length)
            if blocked(v) and length > 0:
                return  # can't continue building a path through an opponent's town
            for nxt in adjacency.get(v, []):
                e = _canon_edge(self, v, nxt)
                if e not in visited_edges:
                    visited_edges.add(e)
                    dfs(nxt, visited_edges, length + 1)
                    visited_edges.remove(e)

        for start in adjacency:
            dfs(start, set(), 0)

        return best