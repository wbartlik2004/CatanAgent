import random
from mcts import MCTSAgent, WILL_DEFAULT_WEIGHTS


class CoEvolutionMCTSAgent(MCTSAgent):
    def __init__(self, color, n_simulations=200, c=1.4, rollout_depth=40,genome=None, generation=0, seed=None):
        genome = dict(genome) if genome else {k: v * random.uniform(0.9, 1.1) for k, v in WILL_DEFAULT_WEIGHTS.items()}
        super().__init__(player=color, n_simulations=n_simulations, c=c,
                          rollout_depth=rollout_depth, rollout_weights=genome,
                          seed=seed)
        self.color = color
        self.genome = genome
        self.generation = generation
        self.games_played = 0
        self.fitness_history = []

    def record_result(self, final_vp, won):
        """Call once per completed game to feed the evolutionary loop."""
        self.games_played += 1
        self.fitness_history.append({"vp": final_vp, "won": won})

    def average_fitness(self):
        if not self.fitness_history:
            return 0.0
        return sum(g["vp"] for g in self.fitness_history) / len(self.fitness_history)

    def mutate(self, rate=0.3, sigma=0.25):
        """Return a NEW CoEvolutionMCTSAgent with a perturbed genome
        (doesn't mutate self)."""
        child_genome = dict(self.genome)
        for k in child_genome:
            if random.random() < rate:
                multiplier = 1 + random.gauss(0, sigma)
                child_genome[k] = max(0.0, child_genome[k] * multiplier)
        return CoEvolutionMCTSAgent(
            self.color, n_simulations=self.n_simulations, c=self.c,
            rollout_depth=self.rollout_depth, genome=child_genome,
            generation=self.generation + 1,
        )

    def crossover(self, other):
        """Uniform crossover over rollout_weights keys."""
        child_genome = {}
        for k in self.genome:
            child_genome[k] = self.genome[k] if random.random() < 0.5 else other.genome[k]
        return CoEvolutionMCTSAgent(
            self.color, n_simulations=self.n_simulations, c=self.c,
            rollout_depth=self.rollout_depth, genome=child_genome,
            generation=max(self.generation, other.generation) + 1,
        )