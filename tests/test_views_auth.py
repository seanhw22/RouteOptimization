"""HTTP smoke tests for accounts views: login, register, logout, guest."""

import pytest


# ── Root redirect ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_root_anonymous_renders_landing_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Optimize Multi-Depot Distribution Routes' in response.content


@pytest.mark.django_db
def test_root_authenticated_renders_landing_page(auth_client):
    response = auth_client.get('/')
    assert response.status_code == 200
    assert b'My Datasets' in response.content


# ── Login ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_login_get_returns_200(client):
    response = client.get('/accounts/login/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_authenticated_redirects(auth_client):
    # EmailLoginView has redirect_authenticated_user = True
    response = auth_client.get('/accounts/login/')
    assert response.status_code == 302
    assert 'datasets' in response['Location']


@pytest.mark.django_db
def test_login_valid_credentials_redirects(client, test_user):
    response = client.post('/accounts/login/', data={
        'email': 'test@example.com',
        'password': 'testpass123',
    })
    assert response.status_code == 302


@pytest.mark.django_db
def test_login_invalid_credentials_returns_200(client, test_user):
    response = client.post('/accounts/login/', data={
        'email': 'test@example.com',
        'password': 'wrongpassword',
    })
    assert response.status_code == 200


# ── Register ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_register_get_returns_200(client):
    response = client.get('/accounts/register/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_register_authenticated_redirects(auth_client):
    response = auth_client.get('/accounts/register/')
    assert response.status_code == 302
    assert 'datasets' in response['Location']


@pytest.mark.django_db
def test_register_valid_post_creates_user_and_redirects(client):
    from django.contrib.auth import get_user_model
    response = client.post('/accounts/register/', data={
        'email': 'newuser@example.com',
        'password1': 'StrongPass99!',
        'password2': 'StrongPass99!',
    })
    assert response.status_code == 302
    User = get_user_model()
    assert User.objects.filter(email='newuser@example.com').exists()


@pytest.mark.django_db
def test_register_duplicate_email_returns_200(client, test_user):
    response = client.post('/accounts/register/', data={
        'email': 'test@example.com',  # already taken by test_user
        'password1': 'StrongPass99!',
        'password2': 'StrongPass99!',
    })
    assert response.status_code == 200


# ── Logout ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_logout_redirects_to_login(auth_client):
    response = auth_client.post('/accounts/logout/')
    assert response.status_code == 302
    assert 'login' in response['Location']


# ── Guest ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_guest_sets_session_and_redirects_to_upload(client):
    response = client.get('/accounts/guest/')
    assert response.status_code == 302
    assert 'upload' in response['Location']
    assert client.session.get('is_guest') is True
