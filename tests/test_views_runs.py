"""HTTP smoke tests for runs views."""

from unittest.mock import patch

import pytest

from runs.models import Experiment
from runs.services import create_batch


@pytest.mark.django_db
def test_configure_get_returns_200(auth_client, db_dataset):
    response = auth_client.get(f'/runs/configure/{db_dataset.dataset_id}/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_configure_post_creates_batch_and_redirects(auth_client, db_dataset):
    form_data = {
        'run_greedy': 'on',
        'generations': 100,
        'population_size': 50,
        'mutation_rate': 0.1,
        'crossover_rate': 0.8,
        'no_improve_limit': 20,
        'seed': 42,
        'milp_time_limit': 3600,
    }
    with patch('runs.views.launch_all') as mock_launch:
        response = auth_client.post(f'/runs/configure/{db_dataset.dataset_id}/', data=form_data)

    assert db_dataset.run_batches.exists()
    mock_launch.assert_called_once()
    assert response.status_code == 302


@pytest.mark.django_db
def test_status_returns_correct_json_shape(auth_client, db_dataset, test_user):
    batch = create_batch(dataset=db_dataset, user=test_user, session_key='')
    response = auth_client.get(f'/runs/{batch.pk}/status/')
    assert response.status_code == 200
    data = response.json()
    assert 'batch_status' in data
    assert 'experiments' in data
    assert isinstance(data['experiments'], list)


@pytest.mark.django_db
def test_kill_returns_ok_and_sets_killed_status(auth_client, db_dataset, test_user):
    batch = create_batch(dataset=db_dataset, user=test_user, session_key='')
    exp = Experiment.objects.create(
        dataset=db_dataset,
        run_batch=batch,
        algorithm='Greedy',
        status='running',
    )
    response = auth_client.post(f'/runs/{batch.pk}/experiments/{exp.pk}/kill/')
    assert response.status_code == 200
    assert response.json()['ok'] is True
    exp.refresh_from_db()
    assert exp.status == 'killed'
