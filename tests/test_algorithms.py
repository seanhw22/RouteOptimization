"""Regression smoke tests for MDVRPGreedy and MDVRPHGA on the tiny_problem fixture."""

import pytest

from algorithms.mdvrp_greedy import MDVRPGreedy
from algorithms.mdvrp_hga import MDVRPHGA


# ── Greedy ────────────────────────────────────────────────────────────────────

@pytest.fixture
def greedy_result(tiny_problem):
    depots, customers, vehicles, items, params = tiny_problem
    solver = MDVRPGreedy(depots, customers, vehicles, items, params, seed=42)
    solution, status = solver.solve(verbose=False)
    return solution, status, customers


def test_greedy_returns_feasible_status(greedy_result):
    _, status, _ = greedy_result
    assert status == 'feasible'


def test_greedy_covers_all_customers(greedy_result):
    solution, _, customers = greedy_result
    served = set()
    for route_data in solution['routes'].values():
        served.update(route_data['nodes'])
    assert set(customers).issubset(served)


def test_greedy_fitness_is_positive(greedy_result):
    solution, _, _ = greedy_result
    assert solution['fitness'] > 0


# ── HGA ───────────────────────────────────────────────────────────────────────

@pytest.fixture
def hga_result(tiny_problem):
    depots, customers, vehicles, items, params = tiny_problem
    solver = MDVRPHGA(
        depots, customers, vehicles, items, params,
        population_size=4, generations=2, seed=42,
    )
    solution, status = solver.solve(verbose=False)
    return solution, status, customers


def test_hga_returns_feasible_status(hga_result):
    _, status, _ = hga_result
    assert status == 'feasible'


def test_hga_covers_all_customers(hga_result):
    solution, _, customers = hga_result
    served = set()
    for route_data in solution['routes'].values():
        served.update(c for c in route_data['nodes'] if c is not None)
    assert set(customers).issubset(served)


def test_hga_fitness_is_positive(hga_result):
    solution, _, _ = hga_result
    assert solution['fitness'] > 0
