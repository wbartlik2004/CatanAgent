from state import RESOURCES, BUILDING_COSTS

DEFAULT_WEIGHTS = {
    "victory_points": 10.0,
    "settlements": 2.0,
    "cities": 3.0,
    "roads": 0.3,
    "resource_total": 0.2,
    "resource_diversity": 5,   # number of distinct resource types held
    "dev_cards": 0.4,
    "longest_road_bonus": 1.5,   # extra credit for HOLDING longest road
    "largest_army_bonus": 1.5,   # extra credit for HOLDING largest army
}

def evaluate_state(game_state, player_index, weights=DEFAULT_WEIGHTS):
    s = game_state
    hand = s.hands[player_index]

    n_settlements = sum(1 for owner in s.settlements.values() if owner == player_index)
    n_cities = sum(1 for owner in s.cities.values() if owner == player_index)
    n_roads = sum(1 for owner in s.roads.values() if owner == player_index)
    n_dev = sum(s.dev_hands[player_index].values())
    resource_total = sum(hand.values())
    resource_diversity = sum(1 for r in RESOURCES if hand[r] > 0)

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