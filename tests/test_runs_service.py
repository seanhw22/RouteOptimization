"""Smoke tests for runs.services: create_batch, create_experiments."""

import pytest

from runs.services import create_batch, create_experiments


# ── create_batch ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_batch_authenticated_user(db_dataset, test_user):
    batch = create_batch(dataset=db_dataset, user=test_user, session_key='')
    assert batch.status == 'pending'
    assert batch.dataset_id == db_dataset.dataset_id
    assert batch.user_id == test_user.pk


@pytest.mark.django_db
def test_create_batch_guest(db_dataset):
    batch = create_batch(dataset=db_dataset, user=None, session_key='guest-sess-key')
    assert batch.share_token is not None
    assert batch.session_key == 'guest-sess-key'


# ── create_experiments ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_experiments_greedy_and_hga(db_dataset, test_user):
    batch = create_batch(dataset=db_dataset, user=test_user, session_key='')
    config = {
        'run_greedy': True,
        'run_hga': True,
        'run_milp': False,
        'seed': 42,
        'population_size': 10,
        'generations': 5,
        'mutation_rate': 0.1,
        'crossover_rate': 0.8,
    }
    experiments = create_experiments(batch=batch, config=config)
    assert len(experiments) == 2
    assert {e.algorithm for e in experiments} == {'Greedy', 'HGA'}


@pytest.mark.django_db
def test_create_experiments_hga_params_stored(db_dataset, test_user):
    batch = create_batch(dataset=db_dataset, user=test_user, session_key='')
    config = {
        'run_greedy': False,
        'run_hga': True,
        'run_milp': False,
        'seed': 42,
        'population_size': 10,
        'generations': 5,
        'mutation_rate': 0.1,
        'crossover_rate': 0.8,
    }
    experiments = create_experiments(batch=batch, config=config)
    hga = experiments[0]
    assert hga.algorithm == 'HGA'
    assert hga.population_size == 10
    assert hga.generations == 5
    assert hga.mutation_rate == pytest.approx(0.1)
    assert hga.crossover_rate == pytest.approx(0.8)


@pytest.mark.django_db
def test_create_experiments_no_algorithms(db_dataset, test_user):
    batch = create_batch(dataset=db_dataset, user=test_user, session_key='')
    experiments = create_experiments(batch=batch, config={'run_greedy': False, 'run_hga': False, 'run_milp': False})
    assert experiments == []
