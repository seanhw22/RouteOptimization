import pytest


@pytest.mark.django_db
def test_language_switcher_persists_indonesian_for_landing_page(client):
    response = client.post('/i18n/setlang/', {'language': 'id', 'next': '/'})
    assert response.status_code == 302
    assert response['Location'] == '/'

    response = client.get('/')
    content = response.content.decode()
    assert response.status_code == 200
    assert 'lang="id"' in content
    assert 'Optimalkan Rute Distribusi Multi-Depot' in content
    assert 'Cara Kerja' in content
    assert 'Cakupan masalah meliputi:' in content
    assert 'name="language" value="en"' in content
    assert 'name="language" value="id"' in content


@pytest.mark.django_db
def test_indonesian_switcher_appears_on_application_navbar(auth_client):
    auth_client.post('/i18n/setlang/', {'language': 'id', 'next': '/datasets/'})
    response = auth_client.get('/datasets/')
    content = response.content.decode()
    assert response.status_code == 200
    assert 'Dataset Anda' in content
    assert 'class="language-switcher"' in content


@pytest.mark.django_db
def test_indonesian_form_validation_renders(client):
    client.post('/i18n/setlang/', {'language': 'id', 'next': '/accounts/register/'})
    response = client.post('/accounts/register/', {'email': 'bad', 'password1': '', 'password2': ''})
    assert response.status_code == 200
    assert 'lang="id"' in response.content.decode()
