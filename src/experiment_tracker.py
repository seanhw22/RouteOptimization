"""
Experiment tracking for MDVRP solver runs (Django ORM).

Tracks solver experiments, results, and routes in the database. The previous
SQLAlchemy implementation has been replaced; callers must run inside a Django
context (`django.setup()` if invoked from a standalone script).
"""

from typing import Any, Dict, Optional

from django.utils import timezone


class ExperimentTracker:
    """Handle experiment, results, and routes storage via Django ORM."""

    def __init__(self, db_session: Any = None) -> None:
        """db_session is accepted for backward compatibility but ignored."""
        self.db_session = db_session

    def create_experiment(self, metadata: Dict[str, Any]) -> int:
        """Create an experiment record and return its id.

        ``metadata`` requires ``dataset_id`` and ``algorithm``; optional fields
        are forwarded to the ``Experiment`` model (population_size, mutation_rate,
        crossover_rate, seed, run_batch, generations, time_limit).
        """
        from runs.models import Experiment

        if 'dataset_id' not in metadata or 'algorithm' not in metadata:
            raise ValueError("metadata must contain 'dataset_id' and 'algorithm'")

        exp = Experiment.objects.create(
            dataset_id=metadata['dataset_id'],
            algorithm=metadata['algorithm'],
            population_size=metadata.get('population_size'),
            mutation_rate=metadata.get('mutation_rate'),
            crossover_rate=metadata.get('crossover_rate'),
            seed=metadata.get('seed'),
            generations=metadata.get('generations'),
            time_limit=metadata.get('time_limit'),
            run_batch_id=metadata.get('run_batch_id') or metadata.get('run_batch'),
            status=metadata.get('status', 'pending'),
        )
        return exp.experiment_id

    def save_result_metrics(self, experiment_id: int, metrics: Dict[str, Any]) -> None:
        """Save aggregate metrics for an experiment (runtime, constraint_violation)."""
        from results.models import ResultMetrics

        if 'runtime' not in metrics:
            raise ValueError("metrics must contain 'runtime'")

        ResultMetrics.objects.update_or_create(
            experiment_id=experiment_id,
            defaults={
                'runtime': float(metrics['runtime']),
                'constraint_violation': metrics.get('constraint_violation'),
            },
        )

    def save_routes(
        self,
        experiment_id: int,
        routes: Dict[str, Dict[str, Any]],
        depot_for_vehicle: Optional[Dict[str, str]] = None,
        distance_lookup: Optional[Dict[str, Dict[str, float]]] = None,
        time_lookup: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None,
    ) -> None:
        """Persist route segments for an experiment.

        ``routes`` maps vehicle_id to ``{'nodes': [...], 'distance': ..., 'time': ...}``.
        Each route is segmented as depot -> n1 -> n2 -> ... -> depot, and one
        ``Route`` row is created per segment. Order is implicit in insertion
        order (segment chain reconstructs the sequence at read time).
        """
        from results.models import Route

        if not routes:
            return

        # Drop any prior segments for this experiment to keep saves idempotent.
        Route.objects.filter(experiment_id=experiment_id).delete()

        depot_for_vehicle = depot_for_vehicle or {}
        rows = []
        for vehicle_id, info in routes.items():
            nodes = [n for n in (info.get('nodes') or []) if n is not None]
            depot = depot_for_vehicle.get(vehicle_id)

            if not nodes:
                if depot is None:
                    continue
                rows.append(Route(
                    experiment_id=experiment_id,
                    vehicle_id=vehicle_id,
                    node_start_id=depot,
                    node_end_id=depot,
                    total_distance=0.0,
                    travel_time=0.0,
                ))
                continue

            chain = [depot] + nodes + [depot] if depot is not None else nodes
            for i in range(len(chain) - 1):
                a, b = chain[i], chain[i + 1]
                seg_distance = None
                seg_time = None
                if distance_lookup is not None:
                    seg_distance = distance_lookup.get(a, {}).get(b)
                if time_lookup is not None:
                    seg_time = time_lookup.get(vehicle_id, {}).get(a, {}).get(b)
                rows.append(Route(
                    experiment_id=experiment_id,
                    vehicle_id=vehicle_id,
                    node_start_id=a,
                    node_end_id=b,
                    total_distance=seg_distance,
                    travel_time=seg_time,
                ))

        if rows:
            Route.objects.bulk_create(rows)

    def load_routes(self, experiment_id: int) -> Dict[str, Dict[str, Any]]:
        """Reconstruct routes for an experiment by chaining segments depot->...->depot."""
        from results.models import Route

        segments_by_vehicle: Dict[str, list] = {}
        for r in Route.objects.filter(experiment_id=experiment_id).order_by('vehicle_id', 'route_id'):
            segments_by_vehicle.setdefault(r.vehicle_id, []).append(r)

        routes: Dict[str, Dict[str, Any]] = {}
        for vehicle_id, segments in segments_by_vehicle.items():
            # Build adjacency from start_id -> segment for chain traversal
            by_start = {s.node_start_id: s for s in segments}
            depots_seen = {s.node_start_id for s in segments if s.node_start_id == s.node_end_id}
            # Find the first segment originating from the starting depot.
            # Heuristic: the depot is the node_start_id that does not appear as
            # node_end_id of any other segment (the chain's tail also returns there,
            # so we fall back to the first segment's start when ambiguous).
            ends = {s.node_end_id for s in segments}
            starts = {s.node_start_id for s in segments}
            origin_candidates = [s for s in segments if s.node_start_id in (starts - ends)]
            origin = origin_candidates[0] if origin_candidates else segments[0]

            walk = [origin.node_start_id]
            cursor = origin
            visited = set()
            while cursor and id(cursor) not in visited:
                visited.add(id(cursor))
                walk.append(cursor.node_end_id)
                next_seg = by_start.get(cursor.node_end_id)
                if next_seg is None or id(next_seg) in visited:
                    break
                cursor = next_seg

            # Strip leading/trailing depot to expose the customer sequence
            depot = walk[0]
            inner = [n for n in walk[1:-1] if n != depot] if walk[-1] == depot else walk[1:]

            total_distance = sum(float(s.total_distance or 0) for s in segments)
            total_time = sum(float(s.travel_time or 0) for s in segments)
            routes[vehicle_id] = {
                'nodes': inner,
                'distance': total_distance,
                'time': total_time,
            }

        return routes

    def update_progress(
        self,
        experiment_id: int,
        status: Optional[str] = None,
        progress_pct: Optional[int] = None,
        best_objective: Optional[float] = None,
        log_line: Optional[str] = None,
    ) -> None:
        """Patch live progress fields on an experiment.

        Any argument left as None is not written. ``log_line`` is appended to
        ``progress_log`` and the array is capped at the most recent 100 entries.
        ``status`` transitions also update ``started_at``/``completed_at``.
        """
        from runs.models import Experiment

        # Refresh from DB to avoid clobbering writes from concurrent updates
        exp = Experiment.objects.get(pk=experiment_id)

        if status is not None:
            exp.status = status
            if status == 'running' and exp.started_at is None:
                exp.started_at = timezone.now()
            if status in Experiment.TERMINAL_STATUSES and exp.completed_at is None:
                exp.completed_at = timezone.now()

        if progress_pct is not None:
            exp.progress_pct = max(0, min(100, int(progress_pct)))

        if best_objective is not None:
            exp.best_objective = float(best_objective)

        if log_line:
            exp.append_log(log_line)

        exp.save()
