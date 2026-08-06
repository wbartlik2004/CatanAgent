def _vertex_neighbors(self, v):
    """All vertices adjacent to v via a board edge."""
    result = set()
    for a, b in self.board.edges:
        if a == v:
            result.add(b)
        elif b == v:
            result.add(a)
    return result

def _edges_at_vertex(self, v):
    """All board edges touching v."""
    return [e for e in self.board.edges if v in e]

def _tile_vertices(self, tile_id):
    for t in self.board.tiles:
        if t["id"] == tile_id:
            return t["vertices"]
    return []

def _is_occupied(self, v):
    return v in self.settlements or v in self.cities

def _distance_rule_ok(self, v):
    """No settlement/city may be built adjacent to an existing one."""
    if self._is_occupied(v):
        return False
    return all(not self._is_occupied(n) for n in self._vertex_neighbors(v))

def _player_road_vertices(self, player):
    """All vertices touched by player's own roads."""
    verts = set()
    for (a, b), owner in self.roads.items():
        if owner == player:
            verts.add(a)
            verts.add(b)
    return verts

def _settlement_connected(self, v, player):
    """Non-setup settlement placement must touch player's own road network."""
    return v in self._player_road_vertices(player)

def _road_connected(self, edge, player):
    """A new road must touch an existing road, settlement, or city of player's."""
    a, b = edge
    own_buildings = {vv for vv, owner in self.settlements.items() if owner == player}
    own_buildings |= {vv for vv, owner in self.cities.items() if owner == player}
    own_road_verts = self._player_road_vertices(player)
    return a in own_buildings or b in own_buildings or a in own_road_verts or b in own_road_verts

def _canon_edge(self, a, b):
    return (a, b) if a < b else (b, a)
