"""Helpers for enforcing dataset and run-batch ownership across views."""

from functools import wraps

from django.http import Http404
from django.shortcuts import get_object_or_404


def is_guest(request) -> bool:
    return bool(request.session.get('is_guest'))


def owns_dataset(request, dataset) -> bool:
    """Return True if the request is allowed to access ``dataset``."""
    if request.user.is_authenticated:
        return dataset.user_id == request.user.id
    # Guest: must be in their session's allow-list
    guest_ids = request.session.get('guest_datasets', [])
    return dataset.dataset_id in guest_ids


def owns_run_batch(request, batch) -> bool:
    """Return True if the request is allowed to access ``batch``."""
    if request.user.is_authenticated:
        return batch.user_id == request.user.id
    if not request.session.session_key:
        return False
    return batch.session_key == request.session.session_key


def get_owned_dataset_or_404(request, dataset_id):
    """Fetch a dataset and 404 unless the request owns it."""
    from datasets.models import Dataset
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    if not owns_dataset(request, dataset):
        raise Http404('Dataset not found')
    return dataset


def get_owned_batch_or_404(request, batch_id):
    """Fetch a run batch and 404 unless the request owns it."""
    from runs.models import RunBatch
    batch = get_object_or_404(RunBatch, pk=batch_id)
    if not owns_run_batch(request, batch):
        raise Http404('Run batch not found')
    return batch


def require_dataset_ownership(view_func):
    """Decorator that injects ``dataset`` from the URL ``dataset_id`` kwarg."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        dataset_id = kwargs.pop('dataset_id', None)
        dataset = get_owned_dataset_or_404(request, dataset_id)
        return view_func(request, *args, dataset=dataset, **kwargs)

    return wrapper


def require_batch_ownership(view_func):
    """Decorator that injects ``batch`` from the URL ``batch_id`` kwarg."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        batch_id = kwargs.pop('batch_id', None)
        batch = get_owned_batch_or_404(request, batch_id)
        return view_func(request, *args, batch=batch, **kwargs)

    return wrapper
