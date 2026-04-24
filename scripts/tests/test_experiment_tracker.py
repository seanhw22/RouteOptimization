"""
Unit tests for ExperimentTracker class
"""

import pytest
from unittest.mock import Mock
from sqlalchemy import text


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = Mock()
    return session


def test_experiment_tracker_init(mock_db_session):
    """Test ExperimentTracker initialization"""
    from src.experiment_tracker import ExperimentTracker

    tracker = ExperimentTracker(mock_db_session)
    assert tracker.db_session == mock_db_session


def test_create_experiment_success(mock_db_session):
    """Test create_experiment returns experiment_id"""
    from src.experiment_tracker import ExperimentTracker

    # Mock successful INSERT returning experiment_id
    mock_db_session.execute.return_value.fetchone.return_value = [123]

    tracker = ExperimentTracker(mock_db_session)
    experiment_id = tracker.create_experiment({
        'dataset_id': 1,
        'algorithm': 'HGA',
        'population_size': 50,
        'mutation_rate': 0.2,
        'crossover_rate': 0.8,
        'seed': 42
    })

    assert experiment_id == 123
    mock_db_session.commit.assert_called_once()


def test_create_experiment_missing_required_fields(mock_db_session):
    """Test create_experiment raises ValueError on missing fields"""
    from src.experiment_tracker import ExperimentTracker

    tracker = ExperimentTracker(mock_db_session)

    with pytest.raises(ValueError, match="must contain"):
        tracker.create_experiment({'algorithm': 'HGA'})  # Missing dataset_id


def test_create_experiment_rollback_on_error(mock_db_session):
    """Test create_experiment rolls back on error"""
    from src.experiment_tracker import ExperimentTracker

    mock_db_session.execute.side_effect = Exception("Database error")
    mock_db_session.rollback = Mock()

    tracker = ExperimentTracker(mock_db_session)

    with pytest.raises(Exception, match="Failed to create experiment"):
        tracker.create_experiment({
            'dataset_id': 1,
            'algorithm': 'HGA'
        })

    mock_db_session.rollback.assert_called_once()


def test_save_result_metrics_success(mock_db_session):
    """Test save_result_metrics inserts row"""
    from src.experiment_tracker import ExperimentTracker

    tracker = ExperimentTracker(mock_db_session)

    tracker.save_result_metrics(123, {'runtime': 45.6})

    mock_db_session.execute.assert_called()
    mock_db_session.commit.assert_called_once()


def test_save_result_metrics_missing_runtime(mock_db_session):
    """Test save_result_metrics raises ValueError on missing runtime"""
    from src.experiment_tracker import ExperimentTracker

    tracker = ExperimentTracker(mock_db_session)

    with pytest.raises(ValueError, match="must contain 'runtime'"):
        tracker.save_result_metrics(123, {})


def test_save_routes_empty(mock_db_session):
    """Test save_routes with empty routes"""
    from src.experiment_tracker import ExperimentTracker

    tracker = ExperimentTracker(mock_db_session)

    # Should handle empty routes gracefully
    tracker.save_routes(123, {})

    # Verify execute was called (even if empty)
    mock_db_session.execute.assert_called()


def test_save_routes_with_data(mock_db_session):
    """Test save_routes inserts route segments"""
    from src.experiment_tracker import ExperimentTracker

    tracker = ExperimentTracker(mock_db_session)

    routes = {
        'V1': {'nodes': ['C1', 'C2', 'C3'], 'distance': 123.4},
        'V2': {'nodes': ['C4'], 'distance': 50.0}
    }

    tracker.save_routes(123, routes)

    # Verify execute was called for batch insert
    assert mock_db_session.execute.called
    mock_db_session.commit.assert_called_once()


def test_load_routes(mock_db_session):
    """Test load_routes reconstructs routes"""
    from src.experiment_tracker import ExperimentTracker

    # Mock query results
    mock_db_session.execute.return_value.fetchall.return_value = [
        ('V1', 'D1', 'C1', 10.5),
        ('V1', 'C1', 'C2', 15.3),
        ('V1', 'C2', 'D1', 12.1),
        ('V2', 'D1', 'C3', 8.9),
        ('V2', 'C3', 'D1', 8.9),
    ]

    tracker = ExperimentTracker(mock_db_session)
    routes = tracker.load_routes(123)

    # Should return reconstructed routes
    assert 'V1' in routes
    assert 'V2' in routes


def test_load_routes_error_handling(mock_db_session):
    """Test load_routes handles errors gracefully"""
    from src.experiment_tracker import ExperimentTracker

    mock_db_session.execute.side_effect = Exception("Database error")

    tracker = ExperimentTracker(mock_db_session)

    with pytest.raises(Exception, match="Failed to load routes"):
        tracker.load_routes(123)
