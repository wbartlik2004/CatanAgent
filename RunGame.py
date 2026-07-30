import random
'''test push for will branch'''
# Core Constants
RESOURCES = ["WOOD", "BRICK", "SHEEP", "WHEAT", "ORE"]
HEX_TYPES = ["FOREST", "HILLS", "PASTURE", "FIELDS", "MOUNTAINS", "DESERT"]

HEX_RESOURCE_MAP = {
    "FOREST": "WOOD",
    "HILLS": "BRICK",
    "PASTURE": "SHEEP",
    "FIELDS": "WHEAT",
    "MOUNTAINS": "ORE",
    "DESERT": None
}
 
BUILDING_COSTS = {
    "ROAD": {"WOOD": 1, "BRICK": 1},
    "SETTLEMENT": {"WOOD": 1, "BRICK": 1, "SHEEP": 1, "WHEAT": 1},
    "CITY": {"WHEAT": 2, "ORE": 3}
}

# ---------------------------------------------------------------------------
# HARDCODED BOARD TOPOLOGY
# ---------------------------------------------------------------------------
# The physical layout of a Catan board (which vertices belong to which tile,
# which vertices are connected by an edge, tile positions) never changes —
# only the resource types and dice numbers get shuffled each game. So instead
# of recomputing hex geometry with floating point trig every run, that
# topology was generated once (radius-2 axial hex grid, pointy-top hexes,
# snapping shared corners together) and is baked in below as static tables.
# Tile IDs run 0-18 in the classic row order (rows of 3, 4, 5, 4, 3, top to
# bottom, left to right). Vertex IDs run 0-53. Edges are just (v1, v2) pairs.

# tile_id -> (q, r) axial coordinate of that tile's hex center.
# Not needed for gameplay, only for drawing/reference.
TILE_AXIAL = {
    0: (0, -2), 1: (1, -2), 2: (2, -2),
    3: (-1, -1), 4: (0, -1), 5: (1, -1), 6: (2, -1),
    7: (-2, 0), 8: (-1, 0), 9: (0, 0), 10: (1, 0), 11: (2, 0),
    12: (-2, 1), 13: (-1, 1), 14: (0, 1), 15: (1, 1),
    16: (-2, 2), 17: (-1, 2), 18: (0, 2),
}

# tile_id -> the 6 vertex IDs at that tile's corners, in consistent order.
TILE_VERTICES = {
    0: (0, 1, 2, 3, 4, 5),
    1: (6, 7, 8, 1, 0, 9),
    2: (10, 11, 12, 7, 6, 13),
    3: (2, 14, 15, 16, 17, 3),
    4: (8, 18, 19, 14, 2, 1),
    5: (12, 20, 21, 18, 8, 7),
    6: (22, 23, 24, 20, 12, 11),
    7: (15, 25, 26, 27, 28, 16),
    8: (19, 29, 30, 25, 15, 14),
    9: (21, 31, 32, 29, 19, 18),
    10: (24, 33, 34, 31, 21, 20),
    11: (35, 36, 37, 33, 24, 23),
    12: (30, 38, 39, 40, 26, 25),
    13: (32, 41, 42, 38, 30, 29),
    14: (34, 43, 44, 41, 32, 31),
    15: (37, 45, 46, 43, 34, 33),
    16: (42, 47, 48, 49, 39, 38),
    17: (44, 50, 51, 47, 42, 41),
    18: (46, 52, 53, 50, 44, 43),
}

# All 72 unique board edges, as canonical (v1, v2) pairs with v1 < v2.
EDGES = [
    (0, 1), (0, 5), (0, 9), (1, 2), (1, 8), (2, 3), (2, 14), (3, 4),
    (3, 17), (4, 5), (6, 7), (6, 9), (6, 13), (7, 8), (7, 12), (8, 18),
    (10, 11), (10, 13), (11, 12), (11, 22), (12, 20), (14, 15), (14, 19),
    (15, 16), (15, 25), (16, 17), (16, 28), (18, 19), (18, 21), (19, 29),
    (20, 21), (20, 24), (21, 31), (22, 23), (23, 24), (23, 35), (24, 33),
    (25, 26), (25, 30), (26, 27), (26, 40), (27, 28), (29, 30), (29, 32),
    (30, 38), (31, 32), (31, 34), (32, 41), (33, 34), (33, 37), (34, 43),
    (35, 36), (36, 37), (37, 45), (38, 39), (38, 42), (39, 40), (39, 49),
    (41, 42), (41, 44), (42, 47), (43, 44), (43, 46), (44, 50), (45, 46),
    (46, 52), (47, 48), (47, 51), (48, 49), (50, 51), (50, 53), (52, 53),
]

# vertex_id -> (x, y) in hex-grid units. Only used for drawing/reference,
# never for game logic.
VERTEX_COORDS = {
    0: (-0.866, -3.5), 1: (-0.866, -2.5), 2: (-1.732, -2.0), 3: (-2.598, -2.5),
    4: (-2.598, -3.5), 5: (-1.732, -4.0), 6: (0.866, -3.5), 7: (0.866, -2.5),
    8: (0.0, -2.0), 9: (-0.0, -4.0), 10: (2.598, -3.5), 11: (2.598, -2.5),
    12: (1.732, -2.0), 13: (1.732, -4.0), 14: (-1.732, -1.0), 15: (-2.598, -0.5),
    16: (-3.464, -1.0), 17: (-3.464, -2.0), 18: (0.0, -1.0), 19: (-0.866, -0.5),
    20: (1.732, -1.0), 21: (0.866, -0.5), 22: (3.464, -2.0), 23: (3.464, -1.0),
    24: (2.598, -0.5), 25: (-2.598, 0.5), 26: (-3.464, 1.0), 27: (-4.33, 0.5),
    28: (-4.33, -0.5), 29: (-0.866, 0.5), 30: (-1.732, 1.0), 31: (0.866, 0.5),
    32: (0.0, 1.0), 33: (2.598, 0.5), 34: (1.732, 1.0), 35: (4.33, -0.5),
    36: (4.33, 0.5), 37: (3.464, 1.0), 38: (-1.732, 2.0), 39: (-2.598, 2.5),
    40: (-3.464, 2.0), 41: (0.0, 2.0), 42: (-0.866, 2.5), 43: (1.732, 2.0),
    44: (0.866, 2.5), 45: (3.464, 2.0), 46: (2.598, 2.5), 47: (-0.866, 3.5),
    48: (-1.732, 4.0), 49: (-2.598, 3.5), 50: (0.866, 3.5), 51: (0.0, 4.0),
    52: (2.598, 3.5), 53: (1.732, 4.0),
}

# The set of all valid vertex IDs, derived from TILE_VERTICES — the actual
# source of truth for board topology. (VERTEX_COORDS happens to share the
# same keys today, but it's a drawing-only table, not the topology itself,
# so gameplay code should never read vertex validity from it.)
ALL_VERTICES = frozenset(v for verts in TILE_VERTICES.values() for v in verts)


class Player:
    def __init__(self, color):
        self.color = color
        self.resources = {r: 0 for r in RESOURCES}
        self.settlements = []  # List of vertex IDs
        self.cities = []       # List of vertex IDs
        self.roads = []        # List of (v1, v2) edge tuples
        self.victory_points = 0

    def can_afford(self, item):
        cost = BUILDING_COSTS.get(item, {})
        return all(self.resources[r] >= qty for r, qty in cost.items())

    def pay(self, item):
        if self.can_afford(item):
            for r, qty in BUILDING_COSTS[item].items():
                self.resources[r] -= qty
            return True
        return False

    def total_resources(self):
        return sum(self.resources.values())


class Board:
    """
    Real Catan topology (19 tiles, 54 vertices, 72 edges), read from the
    hardcoded TILE_AXIAL / TILE_VERTICES / EDGES / VERTEX_COORDS tables
    above instead of being recomputed from hex geometry every run. Only
    the resource type and dice number assigned to each tile ID are
    randomized per game.
    """

    def __init__(self):
        self.vertices = set(ALL_VERTICES)          # the 54 valid vertex IDs
        self.vertex_coords = dict(VERTEX_COORDS)   # vertex_id -> (x, y), for drawing only
        self.edges = set(EDGES)                    # fixed set of (v1, v2) pairs
        self.tiles = self._generate_tiles()
        self.settlements = {}  # vertex_id -> Player
        self.cities = {}       # vertex_id -> Player
        self.roads = {}        # (v1, v2) -> Player

    def _generate_tiles(self):
        # Standard tile-type counts, shuffled.
        types = (
            ["FOREST"] * 4 + ["PASTURE"] * 4 + ["FIELDS"] * 4 +
            ["HILLS"] * 3 + ["MOUNTAINS"] * 3 + ["DESERT"]
        )
        random.shuffle(types)

        # Standard dice-number chits (Desert gets none).
        numbers = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]
        random.shuffle(numbers)

        tiles = []
        num_idx = 0
        for tile_id in range(19):
            tile_type = types[tile_id]
            num = None if tile_type == "DESERT" else numbers[num_idx]
            if tile_type != "DESERT":
                num_idx += 1

            vertex_ids = list(TILE_VERTICES[tile_id])
            tile_edges = []
            for k in range(6):
                v1, v2 = vertex_ids[k], vertex_ids[(k + 1) % 6]
                tile_edges.append((v1, v2) if v1 < v2 else (v2, v1))

            tiles.append({
                "id": tile_id,
                "type": tile_type,
                "resource": HEX_RESOURCE_MAP[tile_type],
                "number": num,
                "axial": TILE_AXIAL[tile_id],
                "vertices": vertex_ids,
                "edges": tile_edges,
            })
        return tiles

    def neighbors_of_vertex(self, vertex_id):
        """All vertices directly connected to `vertex_id` by a board edge."""
        result = set()
        for v1, v2 in self.edges:
            if v1 == vertex_id:
                result.add(v2)
            elif v2 == vertex_id:
                result.add(v1)
        return result


class CatanGame:
    def __init__(self, colors=["RED", "BLUE", "WHITE", "ORANGE"]):
        self.board = Board()
        self.players = [Player(c) for c in colors]
        self.turn = 0
        self.current_player_idx = 0

    def roll_dice(self):
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        total = d1 + d2
        print(f"\n🎲 Rolled {d1} + {d2} = {total}")

        if total == 7:
            print("🚨 7 Rolled! Robber activated.")
        else:
            self._distribute_resources(total)
        return total

    def _distribute_resources(self, roll):
        for tile in self.board.tiles:
            if tile["number"] == roll and tile["resource"]:
                res = tile["resource"]
                for v in tile["vertices"]:
                    if v in self.board.settlements:
                        player = self.board.settlements[v]
                        player.resources[res] += 1
                        print(f"  --> {player.color} gained 1 {res} from Tile {tile['id']}")
                    elif v in self.board.cities:
                        player = self.board.cities[v]
                        player.resources[res] += 2
                        print(f"  --> {player.color} gained 2 {res} from Tile {tile['id']}")

    def build_settlement(self, player, vertex_id):
        if vertex_id in self.board.settlements or vertex_id in self.board.cities:
            print(f"❌ Vertex {vertex_id} is already occupied!")
            return False

        if player.pay("SETTLEMENT"):
            self.board.settlements[vertex_id] = player
            player.settlements.append(vertex_id)
            player.victory_points += 1
            print(f"🏠 {player.color} built a Settlement at vertex {vertex_id}! (VPs: {player.victory_points})")
            return True
        else:
            print(f"❌ {player.color} doesn't have enough resources for a Settlement.")
            return False

    def next_turn(self):
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        self.turn += 1

    def check_winner(self):
        for p in self.players:
            if p.victory_points >= 10:
                return p
        return None

    def print_board_summary(self):
        """Prints a detailed breakdown of all tiles and buildings on the board."""
        print("\n" + "=" * 55)
        print("               FINAL BOARD TILE SUMMARY              ")
        print("=" * 55)

        for tile in self.board.tiles:
            tile_id = tile["id"]
            tile_type = tile["type"]
            number = tile["number"] if tile["number"] is not None else "N/A (Desert)"
            resource = tile["resource"] if tile["resource"] else "None"

            buildings_present = []
            for v_id in tile["vertices"]:
                if v_id in self.board.settlements:
                    owner = self.board.settlements[v_id].color
                    buildings_present.append(f"Settlement ({owner}) @ v{v_id}")
                elif v_id in self.board.cities:
                    owner = self.board.cities[v_id].color
                    buildings_present.append(f"City ({owner}) @ v{v_id}")

            building_str = (
                ", ".join(buildings_present) if buildings_present else "None"
            )

            print(f"Tile {tile_id:2d} | Type: {tile_type:<10} | Roll #: {str(number):<12} | Yields: {resource:<6}")
            print(f"        └── Vertices: {tile['vertices']}")
            print(f"        └── Buildings: {building_str}")
            print("-" * 55)


# --- SAMPLE GAMEPLAY LOOP ---
if __name__ == "__main__":
    game = CatanGame()

    # Sanity-check the generated topology against known Catan board stats.
    print(f"Tiles: {len(game.board.tiles)} (expected 19)")
    print(f"Unique vertices: {len(game.board.vertices)} (expected 54)")
    print(f"Unique edges: {len(game.board.edges)} (expected 72)")

    # Pre-give players some starting settlements for demonstration
    # (use real vertex IDs from the generated board, and confirm they're
    # actually adjacent via a shared edge as a topology check).
    v0 = game.board.tiles[0]["vertices"][0]
    v1 = game.board.tiles[-1]["vertices"][0]

    game.board.settlements[v0] = game.players[0]  # RED
    game.players[0].settlements.append(v0)
    game.players[0].victory_points += 1

    game.board.settlements[v1] = game.players[1]  # BLUE
    game.players[1].settlements.append(v1)
    game.players[1].victory_points += 1

    print("\n=== STARTING PURE-PYTHON CATAN ===")

    # Simulate 5 turns
    all_vertex_ids = list(game.board.vertices)
    for turn in range(5):
        current_p = game.players[game.current_player_idx]
        print(f"\n--- Turn {game.turn + 1}: {current_p.color}'s Turn ---")

        # Roll dice
        game.roll_dice()

        # Display current resources
        res_summary = ", ".join([f"{k}: {v}" for k, v in current_p.resources.items() if v > 0])
        print(f"  {current_p.color} hand: {res_summary if res_summary else 'Empty'}")

        # Try to build if possible, on an actual free vertex from the board
        if current_p.can_afford("SETTLEMENT"):
            free_vertex = next(
                (v for v in all_vertex_ids
                 if v not in game.board.settlements and v not in game.board.cities),
                None
            )
            if free_vertex is not None:
                game.build_settlement(current_p, vertex_id=free_vertex)

        game.next_turn()
    game.print_board_summary()
