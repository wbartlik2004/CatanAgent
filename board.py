import random


TILE_AXIAL = {
    0: (0, -2), 1: (1, -2), 2: (2, -2),
    3: (-1, -1), 4: (0, -1), 5: (1, -1), 6: (2, -1),
    7: (-2, 0), 8: (-1, 0), 9: (0, 0), 10: (1, 0), 11: (2, 0),
    12: (-2, 1), 13: (-1, 1), 14: (0, 1), 15: (1, 1),
    16: (-2, 2), 17: (-1, 2), 18: (0, 2),
}

# tile_id -> the 6 vertex IDs at that tile's corners, in consistent order.
TILE_VERTICES = {
    0: (0, 1, 2, 3, 4, 5), 1: (6, 7, 8, 1, 0, 9),
    2: (10, 11, 12, 7, 6, 13), 3: (2, 14, 15, 16, 17, 3),
    4: (8, 18, 19, 14, 2, 1), 5: (12, 20, 21, 18, 8, 7),
    6: (22, 23, 24, 20, 12, 11), 7: (15, 25, 26, 27, 28, 16),
    8: (19, 29, 30, 25, 15, 14), 9: (21, 31, 32, 29, 19, 18),
    10: (24, 33, 34, 31, 21, 20), 11: (35, 36, 37, 33, 24, 23),
    12: (30, 38, 39, 40, 26, 25), 13: (32, 41, 42, 38, 30, 29),
    14: (34, 43, 44, 41, 32, 31), 15: (37, 45, 46, 43, 34, 33),
    16: (42, 47, 48, 49, 39, 38), 17: (44, 50, 51, 47, 42, 41),
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
HEX_RESOURCE_MAP = {
    "FOREST":    "WOOD",
    "HILLS":     "BRICK",
    "PASTURE":   "SHEEP",
    "FIELDS":    "WHEAT",
    "MOUNTAINS": "ORE",
    "DESERT":    None,
}

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
ALL_VERTICES = frozenset(v for verts in TILE_VERTICES.values() for v in verts) # TILE VERTICES becomes ALL_VERTICES
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
        # claude recommended to help game speed
        self._build_adjacency()

    def _build_adjacency(self):
        self.vertex_neighbors = {v: set() for v in self.vertices}
        self.vertex_edges = {v: [] for v in self.vertices}
        for e in self.edges:
            a, b = e
            self.vertex_neighbors[a].add(b)
            self.vertex_neighbors[b].add(a)
            self.vertex_edges[a].append(e)
            self.vertex_edges[b].append(e)

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