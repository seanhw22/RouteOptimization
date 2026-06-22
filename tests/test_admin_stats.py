"""Coverage for the admin statistics dashboard."""

import pytest

from runs.services import create_batch, create_experiments


@pytest.mark.django_db
def test_recent_experiments_link_to_the_dataset_owner(client, db_dataset, test_user):
    test_user.is_staff = True
    test_user.save(update_fields=['is_staff'])
    client.force_login(test_user)

    batch = create_batch(dataset=db_dataset, user=test_user, session_key='')
    create_experiments(
        batch=batch,
        config={'run_greedy': True, 'run_hga': False, 'run_milp': False},
    )

    response = client.get('/admin/stats/')
    body = response.content.decode()

    assert response.status_code == 200
    assert 'Started By' in body
    assert f'/admin/auth/user/{test_user.pk}/change/' in body
    assert test_user.username in body
