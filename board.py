from main import ALL_VERTICES, EDGES, TILE_AXIAL, TILE_VERTICES, HEX_RESOURCE_MAP, VERTEX_COORDS
import Player
import random

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