board.py     # topology tables, Board, adjacency, tile generation
Game.py     #Game takes in all players (individual player classes like RandomAgent CoEvoAgent MCTSAgent), and takes in board (Concete). #next turn and checkWinner functions, game class will also have a field such that the field to equal to one long vector that represents all game inf
#


state.py     # Game State + Action types: legal_actions / apply / copy  etc
rules.py     # placement legality, robber, bank trade, VP scoring
agents/      # random.py, greedy.py, mcts.py, etc
eval.py      # evaluation functions + features
tests/       # topology, rules, determinism
main.py      # game sim
docs/        # design notes, code review


N-player capable code, 2-player eval/training?
Bank only trading

NEED game state/action interface so agents can decide X at state Y:
current_player, legal_actions, do(action), copy() (for search alg state expansion), is_terminal_state( boolean ), winner() (for assigning reward values to moves)


state.py
    class GameState:
        __init__(...)        # the fields, unchanged
        copy(self)           # return copy.deepcopy(self)
    # constants (RESOURCES, phases, costs) stay here or in constants.py

state_functions.py
    initial_state(board, n)
    current_player(state) / is_chance_node(state) / is_terminal(state) / winner(state)
    victory_points(state, p) + assoc
    legal_actions(state)
    chance_outcomes(state)
    apply_action(state, action)       # mutates; caller copied first
        _build_settlement / _build_road / _pay / _move_robber / _recompute_* / _end_turn

