"""Views for the results app: dashboard and per-experiment file downloads."""

import io
import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from accounts.permissions import get_owned_batch_or_404
from datasets.models import Customer, Depot, Node, Vehicle
from results.models import Route
from runs.models import Experiment
from src.experiment_tracker import ExperimentTracker
from src.exporter import MDVRPExporter


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_solution(experiment_id, dataset_id):
    """Reconstruct a solution dict from ORM for a completed experiment."""
    tracker = ExperimentTracker()
    routes = tracker.load_routes(experiment_id)

    # Depot for each vehicle: the first segment (lowest route_id) starts at depot.
    first_segs = {}
    for seg in Route.objects.filter(experiment_id=experiment_id).order_by('vehicle_id', 'route_id'):
        if seg.vehicle_id not in first_segs:
            first_segs[seg.vehicle_id] = seg.node_start_id

    vehicles_qs = Vehicle.objects.filter(dataset_id=dataset_id)
    vehicle_speed = {v.vehicle_id: float(v.speed_kmh) for v in vehicles_qs}

    solution = {
        'routes': routes,
        'depot_for_vehicle': first_segs,
        'vehicle_speed': vehicle_speed,
    }

    try:
        exp = Experiment.objects.get(pk=experiment_id)
        if hasattr(exp, 'metrics') and exp.metrics.runtime is not None:
            solution['runtime'] = exp.metrics.runtime
    except Experiment.DoesNotExist:
        pass

    return solution


def _build_coordinates(dataset_id):
    """Return {node_id: (lat, lon)} treating Node.y as lat, Node.x as lon."""
    return {n.node_id: (n.y, n.x) for n in Node.objects.filter(dataset_id=dataset_id)}


def _build_problem_data(dataset_id):
    """Build problem_data dict expected by MDVRPExporter.export_pdf."""
    nodes_qs = Node.objects.filter(dataset_id=dataset_id)
    vehicles_qs = Vehicle.objects.filter(dataset_id=dataset_id)
    depots_qs = Depot.objects.filter(dataset_id=dataset_id)
    customers_qs = Customer.objects.filter(dataset_id=dataset_id)

    return {
        'depots': {d.depot_id: {'id': d.depot_id} for d in depots_qs},
        'customers': {c.customer_id: {'id': c.customer_id} for c in customers_qs},
        'vehicles': {v.vehicle_id: {'id': v.vehicle_id} for v in vehicles_qs},
        'vehicle_capacity': {v.vehicle_id: float(v.capacity_kg) for v in vehicles_qs},
        'vehicle_speed': {v.vehicle_id: float(v.speed_kmh) for v in vehicles_qs},
        'coordinates': {n.node_id: (n.y, n.x) for n in nodes_qs},
    }


def _build_geojson(solution, coordinates):
    """Return a GeoJSON FeatureCollection dict built from solution + coordinates."""
    from geojson import Feature, FeatureCollection, LineString, Point

    routes = solution['routes']
    depot_for_vehicle = solution.get('depot_for_vehicle', {})
    route_colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
        '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788',
    ]

    features = []

    for node_id, (lat, lon) in coordinates.items():
        raw = node_id.split('_', 1)[-1] if '_' in node_id else node_id
        is_depot = raw.upper().startswith('D')
        features.append(Feature(
            geometry=Point((lon, lat)),
            properties={
                'id': node_id,
                'type': 'depot' if is_depot else 'customer',
                'marker-color': '#2C3E50' if is_depot else '#27AE60',
                'marker-size': 'large' if is_depot else 'medium',
            }
        ))

    for i, (vehicle_id, info) in enumerate(routes.items()):
        nodes = info.get('nodes', [])
        depot = depot_for_vehicle.get(vehicle_id)
        color = route_colors[i % len(route_colors)]
        chain = ([depot] + nodes + [depot]) if depot else nodes
        coords = []
        for nid in chain:
            if nid in coordinates:
                lat, lon = coordinates[nid]
                coords.append((lon, lat))
        if len(coords) > 1:
            features.append(Feature(
                geometry=LineString(coords),
                properties={
                    'vehicle_id': vehicle_id,
                    'type': 'route',
                    'distance_km': round(info.get('distance', 0), 2),
                    'time_hours': round(info.get('time', 0), 2),
                    'stroke': color,
                    'stroke-width': 4,
                    'stroke-opacity': 0.8,
                }
            ))

    return dict(FeatureCollection(features))


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def dashboard(request, batch_id):
    batch = get_owned_batch_or_404(request, batch_id)
    experiments = list(batch.experiments.all().order_by('experiment_id'))
    dataset_id = batch.dataset_id
    coordinates = _build_coordinates(dataset_id)

    algo_items = []
    chart_labels = []
    chart_values = []

    for exp in experiments:
        item = {
            'algorithm': exp.algorithm,
            'experiment_id': exp.experiment_id,
            'status': exp.status,
            'best_objective': exp.best_objective,
            'geojson_json': 'null',
            'routes': [],
            'total_distance': None,
        }

        if exp.status == 'completed':
            solution = _build_solution(exp.experiment_id, dataset_id)
            geojson_dict = _build_geojson(solution, coordinates)
            item['geojson_json'] = json.dumps(geojson_dict)

            all_customer_nodes = set()
            for info in solution['routes'].values():
                all_customer_nodes.update(info.get('nodes', []))
            customers_qs = Customer.objects.filter(
                node_id__in=all_customer_nodes, dataset_id=dataset_id
            ).prefetch_related('orders__item')
            customer_weights = {
                c.node_id: sum(float(o.quantity) * float(o.item.weight_kg) for o in c.orders.all())
                for c in customers_qs
            }

            route_rows = []
            total_dist = 0.0
            for v_id, info in solution['routes'].items():
                nodes = info.get('nodes', [])
                depot = solution['depot_for_vehicle'].get(v_id, '')
                stops_list = ([depot] + nodes + [depot]) if depot else nodes
                dist = float(info.get('distance', 0))
                total_dist += dist
                route_rows.append({
                    'vehicle_id': v_id,
                    'stops': ' → '.join(str(n) for n in stops_list),
                    'distance': round(dist, 2),
                    'time': round(float(info.get('time', 0)), 2),
                    'weight': round(sum(customer_weights.get(n, 0) for n in nodes), 2),
                })

            item['routes'] = route_rows
            item['total_distance'] = round(total_dist, 2)
            chart_labels.append(exp.algorithm)
            chart_values.append(round(total_dist, 2))

        algo_items.append(item)

    days_remaining = None
    if request.session.get('is_guest') and batch.dataset.expires_at:
        delta = batch.dataset.expires_at - timezone.now()
        days_remaining = max(0, delta.days)

    return render(request, 'results/dashboard.html', {
        'batch': batch,
        'experiments': experiments,
        'algo_items': algo_items,
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
        'days_remaining': days_remaining,
    })


def download_csv(request, batch_id, exp_id):
    batch = get_owned_batch_or_404(request, batch_id)
    exp = get_object_or_404(Experiment, pk=exp_id, run_batch=batch)
    if exp.status != 'completed':
        return HttpResponse('Experiment not completed', status=400)

    solution = _build_solution(exp_id, batch.dataset_id)
    buf = io.StringIO()
    MDVRPExporter().export_csv(solution, buf)
    buf.seek(0)
    response = HttpResponse(buf.read(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="routes_{exp.algorithm}.csv"'
    return response


def download_pdf(request, batch_id, exp_id):
    batch = get_owned_batch_or_404(request, batch_id)
    exp = get_object_or_404(Experiment, pk=exp_id, run_batch=batch)
    if exp.status != 'completed':
        return HttpResponse('Experiment not completed', status=400)

    solution = _build_solution(exp_id, batch.dataset_id)
    problem_data = _build_problem_data(batch.dataset_id)
    buf = io.BytesIO()
    MDVRPExporter().export_pdf(solution, problem_data, buf, algorithm_name=exp.algorithm)
    buf.seek(0)
    response = HttpResponse(buf.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="report_{exp.algorithm}.pdf"'
    return response


def download_geojson(request, batch_id, exp_id):
    batch = get_owned_batch_or_404(request, batch_id)
    exp = get_object_or_404(Experiment, pk=exp_id, run_batch=batch)
    if exp.status != 'completed':
        return HttpResponse('Experiment not completed', status=400)

    solution = _build_solution(exp_id, batch.dataset_id)
    coordinates = _build_coordinates(batch.dataset_id)
    geojson_dict = _build_geojson(solution, coordinates)
    response = HttpResponse(
        json.dumps(geojson_dict, indent=2),
        content_type='application/geo+json',
    )
    response['Content-Disposition'] = f'attachment; filename="routes_{exp.algorithm}.geojson"'
    return response
