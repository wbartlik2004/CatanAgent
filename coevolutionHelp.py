import random
from agent import CoEvolutionAgent, RandomAgent, play_game

class CoEvolutionTrainer:
    def __init__(self, population_size=8, n_generations=10, games_per_round=1,
                 elite_fraction=0.25, tournament_k=3, mutation_rate=0.2,
                 mutation_sigma=0.5, max_actions_per_game=4000, seed=None):
        self.population_size = population_size
        self.n_generations = n_generations
        self.games_per_round = games_per_round
        self.elite_fraction = elite_fraction
        self.tournament_k = tournament_k
        self.mutation_rate = mutation_rate
        self.mutation_sigma = mutation_sigma
        self.max_actions_per_game = max_actions_per_game
        self.rng = random.Random(seed)

        self.generation = 0
        self.population = [
            CoEvolutionAgent(f"G0_IND{i}", generation=0) for i in range(population_size)
        ]
        self.history = []  # one summary dict per generation

    '''eval'''
    def _play_one_round(self):
        """Shuffle the population into apirs of 2, play one game per, and record fitness for every CoEvolutionAgent"""
        pool = list(self.population)
        self.rng.shuffle(pool)

        groups = [pool[i:i + 2] for i in range(0, len(pool), 2)]
        for group in groups:
            gs = play_game(group, max_actions=self.max_actions_per_game,
                            seed=self.rng.randint(0, 2_000_000_000))
            winner = gs.winner()
            for idx, agent in enumerate(group):
                if isinstance(agent, CoEvolutionAgent):
                    agent.record_result(final_vp=gs.victory_points(idx), won=(winner == idx))

    '''select/reproduce'''
    def _tournament_select(self, ranked):
        contenders = self.rng.sample(ranked, min(self.tournament_k, len(ranked)))
        return max(contenders, key=lambda a: a.average_fitness())

    def _next_generation(self):
        ranked = sorted(self.population, key=lambda a: a.average_fitness(), reverse=True)
        n_elite = max(1, round(self.elite_fraction * len(ranked)))
        next_gen = []
        # Elites carry forward as fresh individuals: same genome, but a clean fitness_history
        for i, elite in enumerate(ranked[:n_elite]):
            next_gen.append(CoEvolutionAgent(
                f"G{self.generation + 1}_ELITE{i}",
                genome=dict(elite.genome),
                generation=self.generation + 1,
            ))

        while len(next_gen) < self.population_size:
            parent1 = self._tournament_select(ranked)
            parent2 = self._tournament_select(ranked)
            child = parent1.crossover(parent2)
            child = child.mutate(rate=self.mutation_rate, sigma=self.mutation_sigma)
            child.color = f"G{self.generation + 1}_IND{len(next_gen)}"
            next_gen.append(child)
        self.population = next_gen
        self.generation += 1

    '''run'''
    def run(self, verbose=True):
        for _ in range(self.n_generations):
            for _ in range(self.games_per_round):
                self._play_one_round()
            fitnesses = [a.average_fitness() for a in self.population]
            best = max(self.population, key=lambda a: a.average_fitness())
            stats = {
                "generation": self.generation,
                "best_fitness": best.average_fitness(),
                "mean_fitness": sum(fitnesses) / len(fitnesses),
                "best_genome": dict(best.genome),
            } 
            self.history.append(stats)
            if verbose:
                print(f"Gen {stats['generation']:3d} | best={stats['best_fitness']:.2f} "
                      f"mean={stats['mean_fitness']:.2f}")
            self._next_generation()
        return self.history

    def best_genome(self):
        """The best genome seen across all recorded generations."""
        if not self.history:
            return None
        return max(self.history, key=lambda h: h["best_fitness"])["best_genome"]