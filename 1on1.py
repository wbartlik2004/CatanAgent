import random
from coevolutionHelp import playEvol  # Uses your game execution function
from agent import RandomAgent, HeuristicAgent, CoEvolutionAgent
from mctsCoEvo import CoEvolutionMCTSAgent

def play_1v1_matchup(agent1, agent2, num_games=10, max_actions=2000, verbose=False):
    a1_wins = 0
    a1_win_draws = 0
    a2_wins = 0
    a2_win_draws = 0
    draws = 0
    a1_vps = []
    a2_vps = []
    name1 = getattr(agent1, "color", "Agent 1")
    name2 = getattr(agent2, "color", "Agent 2")
    print(f"\n==========================================")
    print(f"   1v1 SERIES: {name1} vs {name2} ({num_games} Games)")
    print(f"==========================================")
    for i in range(num_games):
        seed = random.randint(0, 2_000_000_000)
        # Alternate turn order every game (P0 vs P1)
        if i % 2 == 0:
            agents = [agent1, agent2]
            idx1, idx2 = 0, 1
        else:
            agents = [agent2, agent1]
            idx1, idx2 = 1, 0
        gs = playEvol(agents, seed=seed, verbose=verbose, max_actions=max_actions)
        winner = gs.winner()
        vp1 = gs.victory_points(idx1)
        vp2 = gs.victory_points(idx2)
        a1_vps.append(vp1)
        a2_vps.append(vp2)
        if winner == idx1:
            a1_wins += 1
            result = f"{name1} WIN"
        elif winner == idx2:
            a2_wins += 1
            result = f"{name2} WIN"
        else:
            # Neither hit VP target before action cap
            if vp1 > vp2:
                a1_win_draws += 1
                result = f"{name1} WIN_DRAW"
            elif vp2 > vp1:
                a2_win_draws += 1
                result = f"{name2} WIN_DRAW"
            else:
                draws += 1
                result = "TRUE DRAW"
        pos_str = f"{name1}=P{idx1}"
        print(
            f"Game {i+1:2d} ({pos_str:<14}): {result:<20} | "
            f"{name1} VP: {vp1:2d}  vs  {name2} VP: {vp2:2d}"
        )
    # Summary Metrics
    total_a1_victories = a1_wins + a1_win_draws
    total_a2_victories = a2_wins + a2_win_draws
    win_rate1 = (total_a1_victories / num_games) * 100
    win_rate2 = (total_a2_victories / num_games) * 100
    avg_vp1 = sum(a1_vps) / num_games
    avg_vp2 = sum(a2_vps) / num_games
    print(f"------------------------------------------")
    print(f"SUMMARY ({name1} vs {name2}):")
    print(f"  {name1:<16} Total Wins: {total_a1_victories:2d}/{num_games} ({win_rate1:5.1f}%) | "
        f"Direct Wins: {a1_wins}, Win_Draws: {a1_win_draws} | Avg VP: {avg_vp1:.2f}")
    print(f"  {name2:<16} Total Wins: {total_a2_victories:2d}/{num_games} ({win_rate2:5.1f}%) | "
        f"Direct Wins: {a2_wins}, Win_Draws: {a2_win_draws} | Avg VP: {avg_vp2:.2f}")
    if draws > 0:
        print(f"  True Tied Draws:  {draws}")
    print(f"==========================================\n")
    return {
        "agent1_direct_wins": a1_wins,
        "agent1_win_draws": a1_win_draws,
        "agent2_direct_wins": a2_wins,
        "agent2_win_draws": a2_win_draws,
        "draws": draws,
        "avg_vp1": avg_vp1,
        "avg_vp2": avg_vp2,
    }

agent_random = RandomAgent(color="RandomBot", seed=42)
agent_heuristic = HeuristicAgent(color="StandardHeuristic")
sample_genome = {
    'victory_points': 8.61,
    'settlements': 4.1,
    'cities': 8.75,
    'roads': 4.28,
    'resource_total': 0.067,
    'dev_cards': 1.02,
    'longest_road_bonus': 1.68,
    'largest_army_bonus': 2.14,
    'resource_diversity': 0.8,
    'value_wood': 1.0,
    'value_brick': 1.1,
    'value_sheep': 0.84,
    'value_wheat': 1.3,
    'value_ore': 1.1
}

agent_coevo_greedy = CoEvolutionAgent(
    color="GreedyCoEvo",
    genome=sample_genome
)

agent_coevo_mcts = CoEvolutionMCTSAgent(
    color="MCTSCoEvo",
    n_simulations=25,    # Number of tree iterations per action choice
    c=1.4,               # UCT exploration parameter (sqrt(2) ~ 1.41)
    rollout_depth=5,    # Depth cap for rollouts
    genome=sample_genome
)

if __name__ == "__main__":
    play_1v1_matchup(agent_coevo_greedy, agent_coevo_mcts, num_games=40)


