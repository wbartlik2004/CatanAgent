import random
from Player import Player
from board import Board

class CatanGame:
    def __init__(self, colors=["RED", "BLUE", "WHITE", "GREEN"]):
        self.board = Board()
        self.players = [Player(c) for c in colors]
        self.turn = 0
        self.current_player_idx = 0

    def roll_dice(self):
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        total = d1 + d2
        print(f"\n🎲 Rolled {d1} + {d2} = {total}")

        if total == 7:
            print("🚨 7 Rolled! Robber activated.") #turn this into a RobberPlacement Function
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

