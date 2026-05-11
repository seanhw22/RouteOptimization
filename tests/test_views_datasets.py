"""HTTP smoke tests for dataset views."""

import pytest


@pytest.mark.django_db
def test_upload_authenticated_returns_200(auth_client):
    response = auth_client.get('/datasets/upload/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_upload_anonymous_redirects(client):
    response = client.get('/datasets/upload/')
    assert response.status_code == 302
    assert 'login' in response['Location']


@pytest.mark.django_db
def test_dataset_list_authenticated_returns_200(auth_client):
    response = auth_client.get('/datasets/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_dataset_detail_owner_returns_200(auth_client, db_dataset):
    response = auth_client.get(f'/datasets/{db_dataset.dataset_id}/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_dataset_detail_non_owner_returns_404(client, db_dataset):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    other_user = User.objects.create_user(username='other', password='pass')
    client.force_login(other_user)
    response = client.get(f'/datasets/{db_dataset.dataset_id}/')
    assert response.status_code == 404
