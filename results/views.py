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
    return {n.node_id: (n.x, n.y) for n in Node.objects.filter(dataset_id=dataset_id)}


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


def _build_geojson(solution, coordinates, node_name_map=None):
    """Return a GeoJSON FeatureCollection dict built from solution + coordinates."""
    from geojson import Feature, FeatureCollection, LineString, Point
    if node_name_map is None:
        node_name_map = {}

    routes = solution['routes']
    depot_for_vehicle = solution.get('depot_for_vehicle', {})
    route_colors = [
        '#E63946', '#F4A261', '#2A9D8F', '#9B5DE5', '#FFB703',
        '#3A86FF', '#F72585', '#06D6A0', '#FB5607', '#8AC926',
    ]
    depot_colors = [
        '#2C3E50', '#6D4C41', '#1565C0', '#558B2F', '#6A1B9A',
        '#00838F', '#AD1457', '#E65100', '#37474F', '#4527A0',
    ]

    depot_ids = sorted({
        nid for nid in coordinates
        if (nid.split('_', 1)[-1] if '_' in nid else nid).upper().startswith('D')
    })
    depot_color_map = {nid: depot_colors[i % len(depot_colors)] for i, nid in enumerate(depot_ids)}

    features = []

    for node_id, (lat, lon) in coordinates.items():
        raw = node_id.split('_', 1)[-1] if '_' in node_id else node_id
        is_depot = raw.upper().startswith('D')
        color = depot_color_map.get(node_id, '#2C3E50') if is_depot else '#27AE60'
        features.append(Feature(
            geometry=Point((lon, lat)),
            properties={
                'id': node_id,
                'name': node_name_map.get(node_id, node_id),
                'type': 'depot' if is_depot else 'customer',
                'marker-color': color,
                'marker-size': 'large' if is_depot else 'medium',
                **(({'depot-color': color}) if is_depot else {}),
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
                    'depot_id': depot or '',
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

    vehicles_qs      = list(Vehicle.objects.filter(dataset_id=dataset_id))
    vehicle_capacity = {v.vehicle_id: float(v.capacity_kg) for v in vehicles_qs}
    vehicle_name_map = {v.vehicle_id: v.name or v.vehicle_id for v in vehicles_qs}

    node_name_map = {}
    for d in Depot.objects.filter(dataset_id=dataset_id):
        if d.name:
            node_name_map[d.node_id] = d.name
    for c in Customer.objects.filter(dataset_id=dataset_id):
        if c.name:
            node_name_map[c.node_id] = c.name

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
            geojson_dict = _build_geojson(solution, coordinates, node_name_map)
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
                weight = round(sum(customer_weights.get(n, 0) for n in nodes), 2)
                capacity = vehicle_capacity.get(v_id)
                route_rows.append({
                    'vehicle_id': v_id,
                    'vehicle_name': vehicle_name_map.get(v_id, v_id),
                    'stops': ' → '.join(node_name_map.get(n, n) for n in stops_list),
                    'distance': round(dist, 2),
                    'time': round(float(info.get('time', 0)), 2),
                    'weight': weight,
                    'capacity': round(capacity, 2) if capacity is not None else None,
                    'weight_exceeded': capacity is not None and weight > capacity,
                })

            item['routes'] = route_rows
            item['total_distance'] = round(total_dist, 2)
            item['weight_violated'] = exp.weight_violated
            chart_labels.append(exp.algorithm)
            chart_values.append(round(total_dist, 2))

        algo_items.append(item)

    days_remaining = None
    if batch.dataset.user is None and batch.dataset.expires_at:
        delta = batch.dataset.expires_at - timezone.now()
        days_remaining = max(0, delta.days)

    return render(request, 'results/dashboard.html', {
        'batch': batch,
        'experiments': experiments,
        'algo_items': algo_items,
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
        'vehicle_names_json': json.dumps(vehicle_name_map),
        'days_remaining': days_remaining,
        'share_token': str(batch.share_token) if batch.share_token else '',
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
