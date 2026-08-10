import rules
from state import RESOURCES, BUILDING_COSTS, DICE_PROB
from agent import _RESOURCE_WEIGHT_KEY, DEFAULT_WEIGHTS



def evaluate_state(game_state, player_index, weights=DEFAULT_WEIGHTS):
    s = game_state
    hand = s.hands[player_index]

    n_settlements = sum(1 for owner in s.settlements.values() if owner == player_index)
    n_cities = sum(1 for owner in s.cities.values() if owner == player_index)
    n_roads = sum(1 for owner in s.roads.values() if owner == player_index)
    n_dev = sum(s.dev_hands[player_index].values())
    n_resource_types = len(_player_tile_resources(s, player_index))   # fixed name
    hand_value = _hand_resource_value(hand, weights)

    score = 0.0
    score += weights["victory_points"] * s.victory_points(player_index)
    score += weights["settlements"] * n_settlements
    score += weights["cities"] * n_cities
    score += weights["roads"] * n_roads
    score += weights["resource_total"] * hand_value
    score += weights["dev_cards"] * n_dev
    score += weights["resource_diversity"] * n_resource_types
    if s.longest_road_holder == player_index:
        score += weights["longest_road_bonus"]
    if s.largest_army_holder == player_index:
        score += weights["largest_army_bonus"]
    return score

def resource_diversity_func(self, player):
    resources = set()
    for tile in self.board.tiles:
        if not tile["resource"]:
            continue
        for v in tile["vertices"]:
            owner = self.settlements.get(v, self.cities.get(v))
            if owner == player:
                resources.add(tile["resource"])
                break
    return resources

def _player_pip_value(s, player):
    total = 0.0
    for tile in s.board.tiles:
        if not tile["resource"] or tile["number"] is None:
            continue
        prob = DICE_PROB.get(tile["number"], 0)
        for v in tile["vertices"]:
            if s.settlements.get(v) == player:
                total += prob
            elif s.cities.get(v) == player:
                total += 2 * prob
    return total

def _tile_production_value(tile, weights):
    if not tile["resource"] or tile["number"] is None:
        return 0.0
    prob = DICE_PROB.get(tile["number"], 0.0)
    weight_key = _RESOURCE_WEIGHT_KEY.get(tile["resource"])
    type_value = weights.get(weight_key, 1.0) if weight_key else 1.0
    return prob * type_value


def _hand_resource_value(hand, weights):
    total = 0.0
    for resource, count in hand.items():
        weight_key = _RESOURCE_WEIGHT_KEY.get(resource)
        type_value = weights.get(weight_key, 1.0) if weight_key else 1.0
        total += count * type_value
    return total

def _player_tile_resources(s, player):
    """Set of distinct resource types touching any of player's settlements
    or cities."""
    resources = set()
    for tile in s.board.tiles:
        if not tile["resource"]:
            continue
        for v in tile["vertices"]:
            owner = s.settlements.get(v, s.cities.get(v))
            if owner == player:
                resources.add(tile["resource"])
                break
    return resources