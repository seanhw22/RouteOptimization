"""Shared pytest fixtures for the mdvrp_web test suite."""

import math

import pandas as pd
import pytest


# ── Minimal dataset frames (no DB required) ───────────────────────────────────

@pytest.fixture
def minimal_frames():
    """Valid MDVRP dataset as DataFrames: 2 depots, 3 customers, 2 vehicles, 1 item."""
    return {
        'depots': pd.DataFrame({
            'depot_id': ['D1', 'D2'],
            'x':        [0.0,  10.0],
            'y':        [0.0,   0.0],
        }),
        'customers': pd.DataFrame({
            'customer_id':   ['C1', 'C2', 'C3'],
            'x':             [3.0,   7.0,   5.0],
            'y':             [2.0,   3.0,   8.0],
            'deadline_hours': [8,     8,    12],
        }),
        'vehicles': pd.DataFrame({
            'vehicle_id':         ['V1',   'V2'],
            'depot_id':           ['D1',   'D2'],
            'vehicle_type':       ['truck','truck'],
            'capacity_kg':        [100.0,  100.0],
            'max_operational_hrs':[8.0,    8.0],
            'speed_kmh':          [60.0,   60.0],
        }),
        'items': pd.DataFrame({
            'item_id':      ['I1'],
            'weight_kg':    [5.0],
            'expiry_hours': [24],
        }),
        'orders': pd.DataFrame({
            'customer_id': ['C1', 'C2', 'C3'],
            'item_id':     ['I1', 'I1', 'I1'],
            'quantity':    [2,    3,    1],
        }),
    }


# ── DB fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def test_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
    )


@pytest.fixture
def db_dataset(db, minimal_frames, test_user):
    """Dataset owned by test_user, created via the service layer."""
    from datasets.services import save_dataset
    return save_dataset(
        name='Smoke Test Dataset',
        user=test_user,
        session_key='',
        is_guest=False,
        frames=minimal_frames,
    )


@pytest.fixture
def guest_dataset(db, minimal_frames):
    """Dataset owned by a guest session (expires in 3 days, has share_token)."""
    from datasets.services import save_dataset
    return save_dataset(
        name='Guest Dataset',
        user=None,
        session_key='guest-test-key',
        is_guest=True,
        frames=minimal_frames,
    )


# ── Client fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def auth_client(client, test_user, db_dataset):
    """Django test client logged in as test_user, who owns db_dataset."""
    client.force_login(test_user)
    return client


@pytest.fixture
def guest_client(client, guest_dataset):
    """Django test client with a guest session that owns guest_dataset."""
    session = client.session
    session['is_guest'] = True
    session['guest_datasets'] = [guest_dataset.dataset_id]
    session.save()
    return client


# ── Algorithm fixture ─────────────────────────────────────────────────────────

@pytest.fixture
def tiny_problem():
    """
    Minimal MDVRP problem for algorithm smoke tests.
    2 depots · 3 customers · 2 vehicles · 1 item — dict-based params (no NumPy path).
    All constraints are loose so every solver should find a feasible solution.
    """
    depots    = ['D1', 'D2']
    customers = ['C1', 'C2', 'C3']
    vehicles  = ['V1', 'V2']
    items     = ['I1']
    nodes     = depots + customers

    coords = {
        'D1': (0.0,  0.0),
        'D2': (10.0, 0.0),
        'C1': (3.0,  2.0),
        'C2': (7.0,  3.0),
        'C3': (5.0,  8.0),
    }
    speed_kmh = 60.0

    dist = {
        a: {b: math.dist(coords[a], coords[b]) for b in nodes}
        for a in nodes
    }
    T = {
        v: {a: {b: dist[a][b] / speed_kmh for b in nodes} for a in nodes}
        for v in vehicles
    }

    params = {
        'dist':             dist,
        'T':                T,
        'Q':                {'V1': 100.0, 'V2': 100.0},
        'T_max':            {'V1': 8.0,   'V2': 8.0},
        'L':                {'C1': 8,     'C2': 8,   'C3': 12},
        'w':                {'I1': 5.0},
        'r':                {'C1': {'I1': 2}, 'C2': {'I1': 3}, 'C3': {'I1': 1}},
        'expiry':           {'I1': 24},
        'depot_for_vehicle': {'V1': 'D1', 'V2': 'D2'},
    }

    return depots, customers, vehicles, items, params
