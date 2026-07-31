from RunGame import RESOURCES, BUILDING_COSTS

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