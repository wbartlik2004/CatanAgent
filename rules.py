from state import (
    RESOURCES, DEV_TYPES, BUILDING_COSTS, DEV_CARD_COST, DEV_DECK_COUNTS,
    PIECE_LIMITS, BANK_TRADE_RATIO, DICE_PROB, DISCARD_LIMIT, VP_TO_WIN,
    LONGEST_ROAD_MIN, LARGEST_ARMY_MIN,
    SETUP_SETTLEMENT, SETUP_ROAD, ROLL, DISCARD, MOVE_ROBBER, STEAL, MAIN,
    DEV_DRAW, ROAD_BUILDING, GAME_OVER,
)
def _vertex_neighbors(s, v):
    return s.board.vertex_neighbors[v]

def _edges_at_vertex(s, v):
    return s.board.vertex_edges[v]

def _tile_vertices(s, tile_id):
    for t in s.board.tiles:
        if t["id"] == tile_id:
            return t["vertices"]
    return []

def _is_occupied(s, v):
    return v in s.settlements or v in s.cities

def _distance_rule_ok(s, v):
    """No settlement/city may be built adjacent to an existing one."""
    if _is_occupied(s, v):
        return False
    return all(not _is_occupied(s, n) for n in _vertex_neighbors(s, v))

def _player_road_vertices(s, player):
    """All vertices touched by player's own roads."""
    verts = set()
    for (a, b), owner in s.roads.items():
        if owner == player:
            verts.add(a)
            verts.add(b)
    return verts

def _settlement_connected(s, v, player):
    """Non-setup settlement placement must touch player's own road network."""
    return v in _player_road_vertices(s, player)

def _road_connected(s, edge, player):
    """A new road must touch an existing road, settlement, or city of player's."""
    a, b = edge
    own_buildings = {vv for vv, owner in s.settlements.items() if owner == player}
    own_buildings |= {vv for vv, owner in s.cities.items() if owner == player}
    own_road_verts = _player_road_vertices(s, player)
    return a in own_buildings or b in own_buildings or a in own_road_verts or b in own_road_verts

def _canon_edge(s, a, b):
    return (a, b) if a < b else (b, a)


# setup phase
def _legal_setup_settlement(s):
        free_vertices = [v for v in s.board.vertices if _distance_rule_ok(s, v)]
        return [{"type": "BUILD_SETTLEMENT", "vertex": v} for v in free_vertices]

def _apply_setup_settlement(s, action):
    v = action["vertex"]
    p = s.setup_order[s.setup_index]
    s.settlements[v] = p
    s.last_setup_vertex = v

    # second settlement of setup grants starting resources (standard rule)
    is_second_pass = s.setup_index >= s.n
    if is_second_pass:
        for tile in s.board.tiles:
            if v in tile["vertices"] and tile["resource"]:
                s.hands[p][tile["resource"]] += 1

    s.phase = SETUP_ROAD

def _legal_setup_road(s):
    v = s.last_setup_vertex
    options = []
    for e in _edges_at_vertex(s, v):
        if e not in s.roads:
            options.append({"type": "BUILD_ROAD", "edge": e})
    return options

def _apply_setup_road(s, action):
    p = s.setup_order[s.setup_index]
    e = _canon_edge(s, *action["edge"])
    s.roads[e] = p

    s.setup_index += 1
    if s.setup_index >= len(s.setup_order):
        # setup complete, real game begins with player 0's roll
        s.current = 0
        s.phase = ROLL
    else:
        s.current = s.setup_order[s.setup_index]
        s.phase = SETUP_SETTLEMENT


# roll phase
def _legal_roll(s):
        # chance node: the "actions" are the possible dice totals with their probabilities
        return [{"type": "ROLL_RESULT", "value": v, "prob": p} for v, p in DICE_PROB.items()]

def _apply_roll(s, action):
    total = action["value"]
    s.last_roll = total

    if total == 7:
        _start_discard_phase(s)
    else:
        _distribute_resources(s, total)
        s.phase = MAIN

def _distribute_resources(s, roll):
    for tile in s.board.tiles:
        if tile["number"] != roll or not tile["resource"] or tile["id"] == s.robber_tile:
            continue
        res = tile["resource"]
        for v in tile["vertices"]:
            if v in s.settlements:
                s.hands[s.settlements[v]][res] += 1
            elif v in s.cities:
                s.hands[s.cities[v]][res] += 2

def _start_discard_phase(s):
    s.discards_needed = [0] * s.n
    s.pending_discards = []
    for p in range(s.n):
        total = sum(s.hands[p].values())
        if total > DISCARD_LIMIT:
            s.discards_needed[p] = total // 2
            s.pending_discards.append(p)
    if s.pending_discards:
        s.phase = DISCARD
    else:
        s.phase = MOVE_ROBBER

# discard
def _enumerate_discards(s, hand, need):
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

def _legal_discard(s):
    p = s.current_player()
    need = s.discards_needed[p]
    hand = s.hands[p]
    combos = _enumerate_discards(s, hand, need)
    return [{"type": "DISCARD", "player": p, "resources": combo} for combo in combos]

def _apply_discard(s, action):
    p = action["player"]
    to_discard = action["resources"]
    if to_discard is None:
        raise ValueError("DISCARD action must specify a concrete {resource: count} dict")
    needed = s.discards_needed[p]
    if sum(to_discard.values()) != needed:
        raise ValueError(f"Player {p} must discard exactly {needed} cards")
    for r, qty in to_discard.items():
        if s.hands[p][r] < qty:
            raise ValueError(f"Player {p} does not have {qty} {r} to discard")
        s.hands[p][r] -= qty

    s.discards_needed[p] = 0
    s.pending_discards.pop(0)
    if not s.pending_discards:
        s.phase = MOVE_ROBBER


# robber
def _legal_move_robber(s):
        options = []
        for tile in s.board.tiles:
            if tile["id"] == s.robber_tile:
                continue
            victims = set()
            for v in tile["vertices"]:
                owner = s.settlements.get(v, s.cities.get(v))
                if owner is not None and owner != s.current:
                    victims.add(owner)
            if victims:
                for victim in victims:
                    options.append({"type": "MOVE_ROBBER", "tile": tile["id"], "victim": victim})
            else:
                options.append({"type": "MOVE_ROBBER", "tile": tile["id"], "victim": None})
        return options

def _apply_move_robber(s, action):
    s.robber_tile = action["tile"]
    victim = action["victim"]
    if victim is not None and sum(s.hands[victim].values()) > 0:
        s.robber_victim_pending = victim
        s.phase = STEAL
    else:
        s.robber_victim_pending = None
        s.phase = MAIN

def _legal_steal(s):
    victim = s.robber_victim_pending
    hand = s.hands[victim]
    total = sum(hand.values())
    if total == 0:
        return []
    return [{"type": "STEAL_RESULT", "resource": r, "prob": qty / total}
            for r, qty in hand.items() if qty > 0]

def _apply_steal(s, action):
    victim = s.robber_victim_pending
    r = action["resource"]
    s.hands[victim][r] -= 1
    s.hands[s.current][r] += 1
    s.robber_victim_pending = None
    s.phase = MAIN

# main
def _can_afford(s, player, cost):
        return all(s.hands[player][r] >= qty for r, qty in cost.items())

def _pay(s, player, cost):
    for r, qty in cost.items():
        s.hands[player][r] -= qty

def _legal_main(s):
    p = s.current
    options: list[dict] = [{"type": "END_TURN"}]

    # --- build road ---
    if _can_afford(s, p, BUILDING_COSTS["ROAD"]) and len(_player_roads(s, p)) < PIECE_LIMITS["ROAD"]:
        for e in s.board.edges:
            if e not in s.roads and _road_connected(s, e, p):
                options.append({"type": "BUILD_ROAD", "edge": e})

    # --- build settlement ---
    n_settlements = sum(1 for o in s.settlements.values() if o == p)
    if _can_afford(s, p, BUILDING_COSTS["SETTLEMENT"]) and n_settlements < PIECE_LIMITS["SETTLEMENT"]:
        for v in s.board.vertices:
            if _distance_rule_ok(s, v) and _settlement_connected(s, v, p):
                options.append({"type": "BUILD_SETTLEMENT", "vertex": v})

    # --- build city (upgrade own settlement) ---
    n_cities = sum(1 for o in s.cities.values() if o == p)
    if _can_afford(s, p, BUILDING_COSTS["CITY"]) and n_cities < PIECE_LIMITS["CITY"]:
        for v, owner in s.settlements.items():
            if owner == p:
                options.append({"type": "BUILD_CITY", "vertex": v})

    # --- buy dev card ---
    if _can_afford(s, p, DEV_CARD_COST) and sum(s.dev_deck.values()) > 0:
        options.append({"type": "BUY_DEV"})

    # --- play dev card (max one per turn, can't play one bought this turn) ---
    if not s.dev_played_this_turn:
        for d in DEV_TYPES:
            if d == "VICTORY_POINT":
                continue  # never "played", just banked toward VP
            owned = s.dev_hands[p][d]
            bought_this_turn = s.dev_bought_this_turn.count(d)
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
        if s.hands[p][give] >= BANK_TRADE_RATIO:
            for get in RESOURCES:
                if get != give:
                    options.append({"type": "TRADE_BANK", "give": give, "get": get,
                                        "ratio": BANK_TRADE_RATIO})

    return options

def _player_roads(s, player):
    return [e for e, owner in s.roads.items() if owner == player]

def _apply_main(s, action):
    p = s.current
    t = action["type"]

    if t == "END_TURN":
        _end_turn(s)
        return

    if t == "BUILD_ROAD":
        e = _canon_edge(s, *action["edge"])
        _pay(s, p, BUILDING_COSTS["ROAD"])
        s.roads[e] = p
        _update_longest_road(s)
        return

    if t == "BUILD_SETTLEMENT":
        v = action["vertex"]
        _pay(s, p, BUILDING_COSTS["SETTLEMENT"])
        s.settlements[v] = p
        return

    if t == "BUILD_CITY":
        v = action["vertex"]
        _pay(s, p, BUILDING_COSTS["CITY"])
        del s.settlements[v]
        s.cities[v] = p
        return

    if t == "BUY_DEV":
        _pay(s, p, DEV_CARD_COST)
        s.phase = DEV_DRAW
        return

    if t == "PLAY_DEV":
        _play_dev(s, action)
        return

    if t == "TRADE_BANK":
        give, get, ratio = action["give"], action["get"], action["ratio"]
        s.hands[p][give] -= ratio
        s.hands[p][get] += 1
        return

    raise ValueError(f"Unknown MAIN action: {action}")

def _end_turn(s):
    s.dev_bought_this_turn = []
    s.dev_played_this_turn = False
    s.current = (s.current + 1) % s.n
    s.phase = ROLL
    # actual win-check belongs after any VP-changing action; see _check_win()
    _check_win(s)

def _check_win(s):
    for p in range(s.n):
        if s.victory_points(p) >= VP_TO_WIN:
            s.phase = GAME_OVER
            s.winner_id = p
            return

def _play_dev(s, action):
    p = s.current
    d = action["dev"]
    s.dev_hands[p][d] -= 1
    s.dev_played_this_turn = True

    if d == "KNIGHT":
        s.knights_played[p] += 1
        _update_largest_army(s)
        s.phase = MOVE_ROBBER
    elif d == "ROAD_BUILDING":
        s.free_roads_remaining = 2
        s.phase = ROAD_BUILDING
    elif d == "YEAR_OF_PLENTY":
        for r in action["resources"]:
            s.hands[p][r] += 1
        # stays in MAIN
    elif d == "MONOPOLY":
        r = action["resource"]
        for other in range(s.n):
            if other == p:
                continue
            s.hands[p][r] += s.hands[other][r]
            s.hands[other][r] = 0
        # stays in MAIN
    else:
        raise ValueError(f"Unknown dev card: {d}")

    _check_win(s)

def _legal_dev_draw(s):
        total = sum(s.dev_deck.values())
        if total == 0:
            return []
        return [{"type": "DEV_DRAWN", "dev": d, "prob": qty / total}
                for d, qty in s.dev_deck.items() if qty > 0]

def _apply_dev_draw(s, action):
    d = action["dev"]
    s.dev_deck[d] -= 1
    s.dev_hands[s.current][d] += 1
    s.dev_bought_this_turn.append(d)
    s.phase = MAIN
    _check_win(s)

'''road building dev card phase'''
def _legal_road_building(s):
    p = s.current
    return [{"type": "BUILD_ROAD", "edge": e} for e in s.board.edges
            if e not in s.roads and _road_connected(s, e, p)]

def _apply_road_building(s, action):
    p = s.current
    e = _canon_edge(s, *action["edge"])
    s.roads[e] = p  # free: no payment
    s.free_roads_remaining -= 1
    _update_longest_road(s)
    if s.free_roads_remaining <= 0:
        s.phase = MAIN



# -----------------------------------------------------------------
# Longest Road / Largest Army
# -----------------------------------------------------------------

def _update_largest_army(s):
    best_p, best_n = s.largest_army_holder, LARGEST_ARMY_MIN - 1
    if best_p is not None:
        best_n = s.knights_played[best_p]
    for p in range(s.n):
        if s.knights_played[p] >= LARGEST_ARMY_MIN and s.knights_played[p] > best_n:
            best_p, best_n = p, s.knights_played[p]
    s.largest_army_holder = best_p

def _update_longest_road(s):
    best_p, best_len = s.longest_road_holder, LONGEST_ROAD_MIN - 1
    if best_p is not None:
        best_len = _longest_road_length(s, best_p)
    for p in range(s.n):
        length = _longest_road_length(s, p)
        if length >= LONGEST_ROAD_MIN and length > best_len:
            best_p, best_len = p, length
    s.longest_road_holder = best_p

def _longest_road_length(s, player):
    """
    Longest simple path through `player`'s own roads, breaking at any
    vertex owned (settled) by an opponent. Brute-force DFS from every
    vertex touched by the player's roads — fine at Catan's scale
    (<=15 roads/player, degree <=3 per vertex).
    """
    edges = _player_roads(s, player)
    if not edges:
        return 0

    adjacency = {}
    for a, b in edges:
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)

    def blocked(v):
        owner = s.settlements.get(v, s.cities.get(v))
        return owner is not None and owner != player

    best = 0

    def dfs(v, visited_edges, length):
        nonlocal best
        best = max(best, length)
        if blocked(v) and length > 0:
            return  # can't continue building a path through an opponent's town
        for nxt in adjacency.get(v, []):
            e = _canon_edge(s, v, nxt)
            if e not in visited_edges:
                visited_edges.add(e)
                dfs(nxt, visited_edges, length + 1)
                visited_edges.remove(e)

    for start in adjacency:
        dfs(start, set(), 0)

    return best

### legal actions/apply ###
def legal_actions(s):
    if s.phase == SETUP_SETTLEMENT: return _legal_setup_settlement(s)
    if s.phase == SETUP_ROAD:       return _legal_setup_road(s)
    if s.phase == ROLL:             return _legal_roll(s)
    if s.phase == DISCARD:          return _legal_discard(s)
    if s.phase == MOVE_ROBBER:      return _legal_move_robber(s)
    if s.phase == STEAL:            return _legal_steal(s)
    if s.phase == MAIN:             return _legal_main(s)
    if s.phase == DEV_DRAW:         return _legal_dev_draw(s)
    if s.phase == ROAD_BUILDING:    return _legal_road_building(s)
    if s.phase == GAME_OVER:        return []
    raise ValueError(f"Unknown phase: {s.phase}")

def apply(s, action):
    s = s.copy()
    if s.phase == SETUP_SETTLEMENT: _apply_setup_settlement(s, action)
    elif s.phase == SETUP_ROAD:     _apply_setup_road(s, action)
    elif s.phase == ROLL:           _apply_roll(s, action)
    elif s.phase == DISCARD:        _apply_discard(s, action)
    elif s.phase == MOVE_ROBBER:    _apply_move_robber(s, action)
    elif s.phase == STEAL:          _apply_steal(s, action)
    elif s.phase == MAIN:           _apply_main(s, action)
    elif s.phase == DEV_DRAW:       _apply_dev_draw(s, action)
    elif s.phase == ROAD_BUILDING:  _apply_road_building(s, action)
    else:
        raise ValueError(f"Unknown phase: {s.phase}")
    if s.phase != GAME_OVER:        # don't overwrite a win already set by a handler
        _check_win(s)
    return s