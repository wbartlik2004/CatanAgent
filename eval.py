from state import RESOURCES, BUILDING_COSTS
from agent import DEFAULT_WEIGHTS



def evaluate_state(game_state, player_index, weights=DEFAULT_WEIGHTS):
    s = game_state
    hand = s.hands[player_index]

    n_settlements = sum(1 for owner in s.settlements.values() if owner == player_index)
    n_cities = sum(1 for owner in s.cities.values() if owner == player_index)
    n_roads = sum(1 for owner in s.roads.values() if owner == player_index)
    n_dev = sum(s.dev_hands[player_index].values())
    resource_total = sum(hand.values())
    resource_diversity = len(resource_diversity_func(s, player_index))   # NEW

    score = 0.0
    score += weights["victory_points"] * s.victory_points(player_index)
    score += weights["settlements"] * n_settlements
    score += weights["cities"] * n_cities
    score += weights["roads"] * n_roads
    score += weights["resource_total"] * resource_total
    score += weights["resource_diversity"] * resource_diversity
    score += weights["dev_cards"] * n_dev
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