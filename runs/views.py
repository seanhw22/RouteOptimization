"""Views for the runs app: configure, launch, monitor, kill."""

import time

from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.permissions import (
    get_owned_batch_or_404,
    get_owned_dataset_or_404,
)

from .forms import SolverConfigForm
from .models import Experiment, RunBatch
from .services import create_batch, create_experiments, launch_all, terminate_experiment


@require_http_methods(['GET', 'POST'])
def configure(request, dataset_id):
    """Show solver-config form for a dataset; on submit, create batch + spawn subprocesses."""
    dataset = get_owned_dataset_or_404(request, dataset_id)
    milp_available = dataset.node_count <= 25

    if request.method == 'POST':
        form = SolverConfigForm(request.POST, milp_available=milp_available)
        if form.is_valid():
            user = request.user if request.user.is_authenticated else None
            session_key = request.session.session_key or ''
            batch = create_batch(dataset=dataset, user=user, session_key=session_key)
            experiments = create_experiments(batch=batch, config=form.cleaned_data)
            launch_all(experiments)
            RunBatch.objects.filter(pk=batch.pk).update(status='running')
            return redirect('runs:viewer', batch_id=batch.pk)
    else:
        form = SolverConfigForm(milp_available=milp_available)

    return render(request, 'runs/configure.html', {
        'dataset': dataset,
        'form': form,
        'milp_available': milp_available,
    })


@require_http_methods(['GET'])
def viewer(request, batch_id):
    """Live run viewer page (the polling JS lives in the template)."""
    batch = get_owned_batch_or_404(request, batch_id)
    experiments = list(batch.experiments.all().order_by('experiment_id'))
    return render(request, 'runs/viewer.html', {
        'batch': batch,
        'experiments': experiments,
    })


@require_http_methods(['GET'])
def status(request, batch_id):
    """JSON polling endpoint consumed by the live run viewer."""
    batch = get_owned_batch_or_404(request, batch_id)
    experiments = list(batch.experiments.all().order_by('experiment_id'))

    now = timezone.now()
    payload_experiments = []
    all_done = True
    for exp in experiments:
        if not exp.is_terminal:
            all_done = False
        if exp.started_at:
            end = exp.completed_at or now
            elapsed = max(0, int((end - exp.started_at).total_seconds()))
        else:
            elapsed = 0
        payload_experiments.append({
            'experiment_id': exp.experiment_id,
            'algorithm': exp.algorithm,
            'status': exp.status,
            'progress_pct': exp.progress_pct,
            'best_objective': exp.best_objective,
            'elapsed_seconds': elapsed,
            'log_tail': (exp.progress_log or [])[-20:],
            'is_terminal': exp.is_terminal,
        })

    if all_done and batch.status == 'running':
        # Mark batch complete (best-effort; ok if another request beat us)
        any_completed = any(e.status == 'completed' for e in experiments)
        new_status = 'completed' if any_completed else 'partial'
        RunBatch.objects.filter(pk=batch.pk, status='running').update(status=new_status)
        batch.refresh_from_db()

    return JsonResponse({
        'batch_status': {
            'id': batch.pk,
            'status': batch.status,
            'all_complete': all_done,
        },
        'experiments': payload_experiments,
    })


@require_POST
def kill(request, batch_id, exp_id):
    batch = get_owned_batch_or_404(request, batch_id)
    try:
        exp = batch.experiments.get(pk=exp_id)
    except Experiment.DoesNotExist:
        raise Http404('Experiment not found in this batch')

    if exp.status == 'completed':
        return JsonResponse({'ok': False, 'error': 'Experiment already completed'}, status=400)

    terminate_experiment(exp)
    return JsonResponse({'ok': True, 'experiment_id': exp.pk, 'status': 'killed'})
