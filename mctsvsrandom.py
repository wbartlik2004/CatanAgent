"""
Benchmark: MCTS vs Random over N games.

Returns two pngs: Win total per agent, poimt accumulation per agent
Seats are rotated (seed % 2)
"""

import random
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from board import Board
from state import GameState
import rules
from mcts import MCTSAgent, WILL_DEFAULT_WEIGHTS
from randomagent import RandomAgent


# ---- config ----
N = 50
SIMS = 60
C = 1.5
ROLLOUT_DEPTH = 50


def play(agents, seed):
    """Play one full game; return the terminal GameState."""
    rng = random.Random(seed)
    gs = GameState(Board(), len(agents))
    while not gs.is_terminal():
        acts = rules.legal_actions(gs)
        if gs.is_chance_node():
            a = rng.choices(acts, weights=[x["prob"] for x in acts])[0]
        else:
            p = gs.current_player()
            a = agents[p].choose_action(gs, p)
        gs = rules.apply(gs, a)
    return gs

def vp_breakdown(gs, p):
    s  = sum(1 for o in gs.settlements.values() if o == p)
    c  = sum(2 for o in gs.cities.values()      if o == p)
    lr = 2 if gs.longest_road_holder == p else 0
    la = 2 if gs.largest_army_holder == p else 0
    dev = gs.dev_hands[p]["VICTORY_POINT"]
    return f"tot={gs.victory_points(p)} [settle={s} city={c} lroad={lr} larmy={la} devVP={dev}]"


def main():
    mcts_wins = 0
    rand_wins = 0

    # running totals for the cumulative line chart
    mcts_cum = []
    rand_cum = []
    mcts_running = 0
    rand_running = 0

    t0 = time.time()
    for seed in range(N):
        seat = seed % 2
        m = MCTSAgent("M", SIMS, C, ROLLOUT_DEPTH, WILL_DEFAULT_WEIGHTS, seed)
        r = RandomAgent("R", seed)
        agents = [m, r] if seat == 0 else [r, m]
        mcts_p, rand_p = (0, 1) if seat == 0 else (1, 0)

        gs = play(agents, seed)
        w = gs.winner()
        print(f"g{seed+1}: winner={w} | MCTS {vp_breakdown(gs, mcts_p)} | RAND {vp_breakdown(gs, rand_p)}")

        if w == mcts_p:
            mcts_wins += 1
        elif w == rand_p:
            rand_wins += 1

        mcts_running += gs.victory_points(mcts_p)
        rand_running += gs.victory_points(rand_p)
        mcts_cum.append(mcts_running)
        rand_cum.append(rand_running)

        print(f"game {seed+1:>3}/{N}: "
              f"{'MCTS' if w == mcts_p else 'RAND'} won   "
              f"({time.time()-t0:.0f}s elapsed)")

    # ---- results ----
    print(f"\n=== after {N} games ({SIMS} sims/move) ===")
    print(f"WINS -> MCTS {mcts_wins} | Random {rand_wins}")
    print(f"VP   -> MCTS {mcts_running} | Random {rand_running} "
          f"(avg {mcts_running/N:.1f} vs {rand_running/N:.1f})")

    # ---- figure 1: wins bar chart ----
    plt.figure(figsize=(6, 5))
    plt.bar(["MCTS", "Random"], [mcts_wins, rand_wins],
            color=["#2a78d6", "#888780"])
    plt.ylabel("Games won")
    plt.title(f"MCTS vs Random — wins over {N} games ({SIMS} sims/move)")
    for i, v in enumerate([mcts_wins, rand_wins]):
        plt.text(i, v + 0.5, str(v), ha="center", fontweight="bold")
    plt.ylim(0, N)
    plt.tight_layout()
    plt.savefig("wins.png", dpi=150)
    print("saved wins.png")

    # ---- figure 2: cumulative VP line chart ----
    games = range(1, N + 1)
    plt.figure(figsize=(7, 5))
    plt.plot(games, mcts_cum, label="MCTS", color="#2a78d6", linewidth=2)
    plt.plot(games, rand_cum, label="Random", color="#888780", linewidth=2)
    plt.xlabel("Game")
    plt.ylabel("Cumulative victory points")
    plt.title(f"Cumulative VP over {N} games")
    plt.legend()
    plt.tight_layout()
    plt.savefig("cumulative_vp.png", dpi=150)
    print("saved cumulative_vp.png")


if __name__ == "__main__":
    main()