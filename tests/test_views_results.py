"""HTTP smoke tests for results views: dashboard and download endpoints."""

import pytest

from runs.models import Experiment
from runs.services import create_batch


# ── Dashboard ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_dashboard_owner_returns_200(auth_client, db_dataset, test_user):
    batch = create_batch(dataset=db_dataset, user=test_user, session_key='')
    response = auth_client.get(f'/results/{batch.pk}/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_dashboard_non_owner_returns_404(client, db_dataset, test_user):
    from django.contrib.auth import get_user_model
    batch = create_batch(dataset=db_dataset, user=test_user, session_key='')
    User = get_user_model()
    other = User.objects.create_user(username='other2', password='pass')
    client.force_login(other)
    response = client.get(f'/results/{batch.pk}/')
    assert response.status_code == 404


@pytest.mark.django_db
def test_dashboard_anonymous_returns_404(client, db_dataset, test_user):
    batch = create_batch(dataset=db_dataset, user=test_user, session_key='')
    response = client.get(f'/results/{batch.pk}/')
    assert response.status_code == 404


@pytest.mark.django_db
def test_dashboard_shared_via_token_returns_200(client, db_dataset, test_user):
    batch = create_batch(dataset=db_dataset, user=test_user, session_key='')
    batch.share_token = '00000000-0000-0000-0000-000000000001'
    batch.save()
    response = client.get(f'/results/{batch.pk}/?token={batch.share_token}')
    assert response.status_code == 200


# ── Downloads (non-completed experiment → 400) ────────────────────────────────

@pytest.fixture
def pending_experiment(db_dataset, test_user):
    batch = create_batch(dataset=db_dataset, user=test_user, session_key='')
    return Experiment.objects.create(
        dataset=db_dataset,
        run_batch=batch,
        algorithm='Greedy',
        status='pending',
    ), batch


@pytest.mark.django_db
def test_download_csv_not_completed_returns_400(auth_client, pending_experiment):
    exp, batch = pending_experiment
    response = auth_client.get(f'/results/{batch.pk}/{exp.pk}/csv/')
    assert response.status_code == 400


@pytest.mark.django_db
def test_download_pdf_not_completed_returns_400(auth_client, pending_experiment):
    exp, batch = pending_experiment
    response = auth_client.get(f'/results/{batch.pk}/{exp.pk}/pdf/')
    assert response.status_code == 400


@pytest.mark.django_db
def test_download_geojson_not_completed_returns_400(auth_client, pending_experiment):
    exp, batch = pending_experiment
    response = auth_client.get(f'/results/{batch.pk}/{exp.pk}/geojson/')
    assert response.status_code == 400
