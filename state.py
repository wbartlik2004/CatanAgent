"""
state.py
game state interface that
currently:
game data
future:
rules of game
"""
import copy

### CONSTANTS ###
# resource/dev card types to key player hands; hand[player]["resource"]
RESOURCES = ["WOOD", "BRICK", "SHEEP", "WHEAT", "ORE"]
DEV_TYPES = ["KNIGHT", "VICTORY_POINT", "ROAD_BUILDING", "YEAR_OF_PLENTY", "MONOPOLY"]

DEV_DECK_COUNTS = {"KNIGHT": 14, "VICTORY_POINT": 5, "ROAD_BUILDING": 2, "YEAR_OF_PLENTY": 2,
                    "MONOPOLY": 2}

# die for MCTS chance nodes implementation
DICE_PROB = {2: 1/36, 3: 2/36, 4: 3/36, 5: 4/36, 6: 5/36, 7: 6/36,
             8: 5/36, 9: 4/36, 10: 3/36, 11: 2/36, 12: 1/36}

# necessary value limits for turns
VP_TO_WIN = 10
DISCARD_LIMIT = 6
LONGEST_ROAD_MIN = 5
LARGEST_ARMY_MIN = 3

# TURN PHASES #
# each of these phases will be one phase node of one turn

# 1. opening turn phases
SETUP_SETTLEMENT = "SETUP_SETTLEMENT"
SETUP_ROAD       = "SETUP_ROAD"
ROLL             = "ROLL"   # chance; what was rolled?
DISCARD          = "DISCARD"    # 7 rolled, player must discard
MOVE_ROBBER      = "MOVE_ROBBER"    # choose robber tile + steal victim
STEAL            = "STEAL"  # chance; which card was stolen?
MAIN             = "MAIN"   # build / trade / buy dev / play dev / end
DEV_DRAW         = "DEV_DRAW"   # chance; which dev card was drawn?
ROAD_BUILDING    = "ROAD_BUILDING"      # 2 free roads to place from dev card
YEAR_OF_PLENTY   = "YEAR_OF_PLENTY"     # 2 free resources to add to hand from dev card
MONOPOLY         = "MONOPOLY"           # name the resource to steal all of

