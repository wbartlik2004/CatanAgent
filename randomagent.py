# thanks

import random
import rules

class RandomAgent:
    def __init__(self, player, seed=None):
        self.player = player
        self.rng = random.Random(seed)

    def choose_action(self, gs, player_index):
        return self.rng.choice(rules.legal_actions(gs))