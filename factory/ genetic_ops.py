"""
Genetic operations — crossover, mutation, selection.
Used by AgentFactory for evolution cycles.
"""
import random
import copy
from typing import List
from agents.base_agent import AgentDNA


def tournament_selection(population: List[AgentDNA], k: int = 3) -> AgentDNA:
    """Pick k random DNA, return the one with highest fitness."""
    tournament = random.sample(population, min(k, len(population)))
    return max(tournament, key=lambda d: d.fitness)


def uniform_crossover(parent_a: AgentDNA, parent_b: AgentDNA) -> AgentDNA:
    """Each param has 50% chance of coming from either parent."""
    child_params = {}
    for key in parent_a.params:
        if key in parent_b.params:
            # For dict params, mix values
            if isinstance(parent_a.params[key], dict) and isinstance(parent_b.params[key], dict):
                mixed = {}
                all_keys = set(parent_a.params[key].keys()) | set(parent_b.params[key].keys())
                for sk in all_keys:
                    if sk in parent_a.params[key] and sk in parent_b.params[key]:
                        mixed[sk] = random.choice([parent_a.params[key][sk], parent_b.params[key][sk]])
                    elif sk in parent_a.params[key]:
                        mixed[sk] = parent_a.params[key][sk]
                    else:
                        mixed[sk] = parent_b.params[key][sk]
                child_params[key] = mixed
            else:
                child_params[key] = random.choice([parent_a.params[key], parent_b.params[key]])
        else:
            child_params[key] = parent_a.params[key]
    
    return AgentDNA(
        params=child_params,
        parent_ids=[parent_a.agent_id, parent_b.agent_id],
        generation=max(parent_a.generation, parent_b.generation) + 1,
    )


def gaussian_mutation(dna: AgentDNA, rate: float = 0.15, sigma: float = 0.1) -> AgentDNA:
    """Add Gaussian noise to numeric params."""
    mutated = AgentDNA(
        params=copy.deepcopy(dna.params),
        parent_ids=[dna.agent_id],
        generation=dna.generation + 1,
    )
    for key, value in mutated.params.items():
        if isinstance(value, (int, float)) and random.random() < rate:
            mutated.params[key] = float(value) * (1 + random.gauss(0, sigma))
            mutated.params[key] = max(1e-4, mutated.params[key])
        elif isinstance(value, dict) and random.random() < rate:
            for sk in value:
                if isinstance(value[sk], (int, float)):
                    value[sk] = value[sk] * (1 + random.gauss(0, sigma))
                    value[sk] = max(0.0, min(1.0, value[sk]))
    return mutated


def evaluate_population(population: List[AgentDNA], fitness_func) -> List[AgentDNA]:
    """Run fitness function on each DNA."""
    for dna in population:
        try:
            dna.fitness = fitness_func(dna)
        except Exception:
            dna.fitness = -1000
    return population


def evolve_generation(
    population: List[AgentDNA],
    elite_count: int = 10,
    crossover_rate: float = 0.7,
    mutation_rate: float = 0.15,
) -> List[AgentDNA]:
    """One generation of evolution."""
    population.sort(key=lambda d: d.fitness, reverse=True)
    
    new_population = []
    new_population.extend(population[:elite_count])  # elitism
    
    while len(new_population) < len(population):
        if random.random() < crossover_rate:
            parent_a = tournament_selection(population)
            parent_b = tournament_selection(population)
            child = uniform_crossover(parent_a, parent_b)
        else:
            child = random.choice(population)
        child = gaussian_mutation(child, rate=mutation_rate)
        new_population.append(child)
    
    return new_population
