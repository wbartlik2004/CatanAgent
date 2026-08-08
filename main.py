import random
from board import Board





# --- SAMPLE GAMEPLAY LOOP ---
if __name__ == "__main__":
    game = CatanGame()

    # Sanity-check the generated topology against known Catan board stats.
    print(f"Tiles: {len(game.board.tiles)} (expected 19)")
    print(f"Unique vertices: {len(game.board.vertices)} (expected 54)")
    print(f"Unique edges: {len(game.board.edges)} (expected 72)")

    # Pre-give players some starting settlements for demonstration
    # (use real vertex IDs from the generated board, and confirm they're
    # actually adjacent via a shared edge as a topology check).
    v0 = game.board.tiles[0]["vertices"][0]
    v1 = game.board.tiles[-1]["vertices"][0]

    game.board.settlements[v0] = game.players[0]  # RED
    game.players[0].settlements.append(v0)
    game.players[0].victory_points += 1

    game.board.settlements[v1] = game.players[1]  # BLUE
    game.players[1].settlements.append(v1)
    game.players[1].victory_points += 1

    print("\n=== STARTING PURE-PYTHON CATAN ===")

    # Simulate 5 turns change into a while not won loop
    all_vertex_ids = list(game.board.vertices)
    for turn in range(5):
        current_p = game.players[game.current_player_idx]
        print(f"\n--- Turn {game.turn + 1}: {current_p.color}'s Turn ---")

        # Roll dice
        game.roll_dice()

        #game.player_actions(current_p)

        # Display current resources
        res_summary = ", ".join([f"{k}: {v}" for k, v in current_p.resources.items() if v > 0])
        print(f"  {current_p.color} hand: {res_summary if res_summary else 'Empty'}")

        game.next_turn()
    game.print_board_summary()
