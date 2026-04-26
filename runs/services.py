"""Solver subprocess orchestration: spawn, kill, and recover stale runs."""

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.utils import timezone

from .models import Experiment, RunBatch


REPO_ROOT = Path(settings.BASE_DIR)
SCRIPTS = {
    'Greedy': REPO_ROOT / 'individual_runs' / 'run_greedy.py',
    'HGA': REPO_ROOT / 'individual_runs' / 'run_hga.py',
    'MILP': REPO_ROOT / 'individual_runs' / 'run_milp.py',
}


def create_batch(*, dataset, user, session_key: str) -> RunBatch:
    return RunBatch.objects.create(
        dataset=dataset,
        user=user,
        session_key=session_key or '',
        status='pending',
    )


def create_experiments(*, batch: RunBatch, config: dict) -> list[Experiment]:
    """Create one Experiment per enabled algorithm in ``config`` (status='pending')."""
    created: list[Experiment] = []

    if config.get('run_greedy'):
        created.append(Experiment.objects.create(
            dataset=batch.dataset,
            run_batch=batch,
            algorithm='Greedy',
            seed=config.get('seed'),
            status='pending',
        ))
    if config.get('run_hga'):
        created.append(Experiment.objects.create(
            dataset=batch.dataset,
            run_batch=batch,
            algorithm='HGA',
            seed=config.get('seed'),
            population_size=config.get('population_size'),
            generations=config.get('generations'),
            mutation_rate=config.get('mutation_rate'),
            crossover_rate=config.get('crossover_rate'),
            status='pending',
        ))
    if config.get('run_milp'):
        created.append(Experiment.objects.create(
            dataset=batch.dataset,
            run_batch=batch,
            algorithm='MILP',
            time_limit=config.get('milp_time_limit'),
            status='pending',
        ))
    return created


def launch_subprocess(experiment: Experiment) -> int:
    """Spawn the solver subprocess and persist its PID. Returns the PID."""
    script = SCRIPTS[experiment.algorithm]
    creationflags = 0
    if os.name == 'nt':
        # New process group so Ctrl-C in the parent doesn't kill the child
        # and so we can target it with CTRL_BREAK if ever needed.
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    proc = subprocess.Popen(
        [sys.executable, str(script), '--experiment-id', str(experiment.experiment_id)],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    Experiment.objects.filter(pk=experiment.experiment_id).update(
        pid=proc.pid,
        status='running',
        started_at=timezone.now(),
    )
    return proc.pid


def launch_all(experiments: Iterable[Experiment]) -> None:
    for exp in experiments:
        try:
            launch_subprocess(exp)
        except Exception as e:
            Experiment.objects.filter(pk=exp.experiment_id).update(
                status='failed',
                completed_at=timezone.now(),
            )
            # Best-effort log line
            from src.experiment_tracker import ExperimentTracker
            ExperimentTracker().update_progress(
                experiment_id=exp.experiment_id,
                log_line=f'Failed to launch subprocess: {e}',
            )


def _pid_alive(pid: int) -> bool:
    if pid is None or pid <= 0:
        return False
    try:
        if os.name == 'nt':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if not handle:
                return False
            try:
                # WaitForSingleObject with 0 timeout: WAIT_TIMEOUT (0x102) means alive
                return kernel32.WaitForSingleObject(handle, 0) == 0x102
            finally:
                kernel32.CloseHandle(handle)
        else:
            os.kill(pid, 0)
            return True
    except OSError:
        return False


def terminate_experiment(experiment: Experiment) -> None:
    """Kill the underlying subprocess and mark the experiment ``killed``.

    Idempotent: if the process is already gone, only the DB row is updated.
    """
    pid = experiment.pid
    if pid:
        try:
            if os.name == 'nt':
                import ctypes
                PROCESS_TERMINATE = 0x0001
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
                if handle:
                    try:
                        kernel32.TerminateProcess(handle, 1)
                    finally:
                        kernel32.CloseHandle(handle)
            else:
                os.kill(pid, signal.SIGTERM)
        except OSError:
            pass

    Experiment.objects.filter(pk=experiment.experiment_id).update(
        status='killed',
        completed_at=timezone.now(),
    )


def mark_stale_experiments() -> int:
    """Set ``status='interrupted'`` for any ``running`` experiments whose PID is dead.

    Called from ``RunsConfig.ready()`` on app startup so a server restart in the
    middle of a run doesn't leave orphaned ``running`` rows.
    """
    interrupted = 0
    for exp in Experiment.objects.filter(status='running'):
        if not _pid_alive(exp.pid):
            Experiment.objects.filter(pk=exp.experiment_id).update(
                status='interrupted',
                completed_at=timezone.now(),
            )
            interrupted += 1
    return interrupted
