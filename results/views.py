"""Views for the results app: dashboard and per-experiment file downloads."""

import io
import json
import math

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


def _build_customer_orders(dataset_id):
    """Return {node_id: {name, orders: [{item_name, quantity, weight_per_unit, total_weight}], total_weight}}."""
    customers_qs = Customer.objects.filter(dataset_id=dataset_id).prefetch_related('orders__item')
    result = {}
    for c in customers_qs:
        orders_list = []
        for o in c.orders.all():
            item_name = o.item.name if o.item.name else o.item.item_id
            weight_per_unit = float(o.item.weight_kg)
            total_weight = o.quantity * weight_per_unit
            orders_list.append({
                'item_name': item_name,
                'quantity': o.quantity,
                'weight_per_unit': weight_per_unit,
                'total_weight': total_weight,
            })
        result[c.node_id] = {
            'name': c.name or c.customer_id,
            'orders': orders_list,
            'total_weight': sum(x['total_weight'] for x in orders_list),
        }
    return result


def _build_name_maps(dataset_id):
    """Return {'vehicle_name_map': ..., 'node_name_map': ...} for a dataset."""
    vehicles_qs = Vehicle.objects.filter(dataset_id=dataset_id)
    vehicle_name_map = {v.vehicle_id: v.name or v.vehicle_id for v in vehicles_qs}

    node_name_map = {}
    for d in Depot.objects.filter(dataset_id=dataset_id):
        if d.name:
            node_name_map[d.node_id] = d.name
    for c in Customer.objects.filter(dataset_id=dataset_id):
        if c.name:
            node_name_map[c.node_id] = c.name

    return {'vehicle_name_map': vehicle_name_map, 'node_name_map': node_name_map}


def _format_runtime(seconds):
    """Display runtime as seconds/minutes/hours."""
    if seconds is None:
        return 'N/A'
    if seconds < 60:
        return f'{seconds:.1f}s'
    if seconds < 3600:
        return f'{seconds / 60:.1f} min'
    return f'{seconds / 3600:.1f} hr'


def _build_conclusion(algo_results, node_count):
    """Return interpretive HTML paragraph + recommendation for comparison conclusion.

    algo_results: list of dicts {algorithm, distance, runtime (seconds|None), violations (int)}
    node_count:   total node count for the dataset
    """
    if not algo_results:
        return ''

    algos = {r['algorithm']: r for r in algo_results}
    has_milp = 'MILP' in algos
    has_hga = 'HGA' in algos
    has_greedy = 'Greedy' in algos
    milp = algos.get('MILP')
    hga = algos.get('HGA')
    greedy = algos.get('Greedy')

    best = min(algo_results, key=lambda r: r['distance'])
    worst = max(algo_results, key=lambda r: r['distance'])
    all_tied = best['distance'] == worst['distance']

    parts = []

    if len(algo_results) == 1:
        r = algo_results[0]
        rt = _format_runtime(r.get('runtime'))
        if r['algorithm'] == 'Greedy':
            parts.append(
                f'Greedy provides a quick baseline solution at <strong>{r["distance"]} km</strong>, '
                f'computed in {rt}. Running HGA or MILP would enable comparison and may yield shorter routes.'
            )
        elif r['algorithm'] == 'HGA':
            parts.append(
                f'HGA produced a solution at <strong>{r["distance"]} km</strong> in {rt}. '
                f'Adding Greedy or MILP would provide reference points for comparison.'
            )
        else:
            parts.append(
                f'MILP found a solution at <strong>{r["distance"]} km</strong> in {rt}. '
                f'Running Greedy or HGA would provide heuristic reference points.'
            )

    elif has_milp and has_hga and has_greedy:
        milp_d = milp['distance']
        hga_d = hga['distance']
        greedy_d = greedy['distance']
        milp_rt = _format_runtime(milp.get('runtime'))
        hga_rt = _format_runtime(hga.get('runtime'))
        greedy_rt = _format_runtime(greedy.get('runtime'))

        if all_tied:
            parts.append(
                f'All three algorithms found the same total distance of <strong>{milp_d} km</strong>, '
                f'indicating the instance is simple enough that all methods converge to the same solution. '
                f'Greedy reached this in {greedy_rt}, HGA in {hga_rt}, and MILP in {milp_rt}.'
            )
        elif best['algorithm'] != 'MILP':
            heur_best = min([hga, greedy], key=lambda r: r['distance'])
            gap = round((milp_d - heur_best['distance']) / milp_d * 100, 1) if milp_d > 0 else 0
            parts.append(
                f'MILP returned <strong>{milp_d} km</strong> but was outperformed by {heur_best["algorithm"]} '
                f'({heur_best["distance"]} km, {gap}% better). This typically happens when MILP hits its time limit '
                f'before finding a better solution — {heur_best["algorithm"]} achieved this in '
                f'{_format_runtime(heur_best.get("runtime"))} vs MILP\'s {milp_rt}.'
            )
        else:
            hga_gap = round((hga_d - milp_d) / milp_d * 100, 1) if milp_d > 0 else 0
            greedy_gap = round((greedy_d - milp_d) / milp_d * 100, 1) if milp_d > 0 else 0
            parts.append(
                f'MILP found the optimal solution at <strong>{milp_d} km</strong> in {milp_rt}. '
                f'HGA was {hga_gap}% above at {hga_d} km (in {hga_rt}), while Greedy was '
                f'{greedy_gap}% above at {greedy_d} km ({greedy_rt}). '
                f'HGA\'s faster runtime makes it the practical choice at scale despite the small gap.'
            )

    elif has_greedy and has_hga:
        greedy_d = greedy['distance']
        hga_d = hga['distance']
        greedy_rt = _format_runtime(greedy.get('runtime'))
        hga_rt = _format_runtime(hga.get('runtime'))

        if all_tied:
            parts.append(
                f'Both Greedy and HGA produced the same total distance of <strong>{greedy_d} km</strong>. '
                f'This instance is simple enough that the greedy baseline suffices — HGA adds no improvement here. '
                f'Greedy computed in {greedy_rt}, HGA in {hga_rt}.'
            )
        elif hga_d < greedy_d:
            gap = round((greedy_d - hga_d) / greedy_d * 100, 1) if greedy_d > 0 else 0
            parts.append(
                f'HGA improved over Greedy by <strong>{gap}%</strong> — from {greedy_d} km down to {hga_d} km. '
                f'HGA took {hga_rt} vs Greedy\'s {greedy_rt}; the extra runtime is justified by the quality gain.'
            )
        else:
            gap = round((hga_d - greedy_d) / hga_d * 100, 1) if hga_d > 0 else 0
            parts.append(
                f'Greedy outperformed HGA: {greedy_d} km vs {hga_d} km ({gap}% better). '
                f'This may indicate a parameter tuning issue with HGA. '
                f'Greedy computed in {greedy_rt}, HGA in {hga_rt}.'
            )

    elif has_greedy and has_milp:
        greedy_d = greedy['distance']
        milp_d = milp['distance']
        greedy_rt = _format_runtime(greedy.get('runtime'))
        milp_rt = _format_runtime(milp.get('runtime'))

        if milp_d <= greedy_d:
            gap = round((greedy_d - milp_d) / milp_d * 100, 1) if milp_d > 0 else 0
            parts.append(
                f'MILP provides the optimal reference at <strong>{milp_d} km</strong> (in {milp_rt}). '
                f'Greedy is {gap}% above at {greedy_d} km ({greedy_rt}). '
                f'Running HGA would show whether a heuristic can close this gap efficiently.'
            )
        else:
            gap = round((milp_d - greedy_d) / milp_d * 100, 1) if milp_d > 0 else 0
            parts.append(
                f'Greedy outperformed MILP: {greedy_d} km vs {milp_d} km ({gap}% better). '
                f'MILP was likely stopped early by the time limit ({milp_rt}) before finding a better solution.'
            )

    elif has_hga and has_milp:
        hga_d = hga['distance']
        milp_d = milp['distance']
        hga_rt = _format_runtime(hga.get('runtime'))
        milp_rt = _format_runtime(milp.get('runtime'))

        if milp_d <= hga_d:
            gap = round((hga_d - milp_d) / milp_d * 100, 1) if milp_d > 0 else 0
            parts.append(
                f'MILP found the optimal solution at <strong>{milp_d} km</strong> in {milp_rt}. '
                f'HGA is {gap}% above at {hga_d} km (in {hga_rt}), making it a strong near-optimal '
                f'alternative with faster runtime for larger instances.'
            )
        else:
            gap = round((milp_d - hga_d) / hga_d * 100, 1) if hga_d > 0 else 0
            parts.append(
                f'HGA outperformed MILP: {hga_d} km vs {milp_d} km ({gap}% better). '
                f'MILP hit its time limit ({milp_rt}) before finding a better solution. '
                f'HGA is the best practical choice here ({hga_rt}); MILP would likely improve with a longer time limit.'
            )

    # Violation context
    violators = [r for r in algo_results if r.get('violations') and r['violations'] > 0]
    if violators:
        viol_strs = [
            f'{r["algorithm"]} ({r["violations"]} violation{"s" if r["violations"] != 1 else ""})'
            for r in violators
        ]
        parts.append(
            f'<strong>Capacity note:</strong> {", ".join(viol_strs)} exceeded vehicle weight capacity constraints. '
            f'These routes may not be operationally feasible without adjustments.'
        )
    else:
        parts.append('All solutions respect vehicle capacity constraints.')

    # Recommendation based on dataset size
    if node_count <= 25:
        parts.append(
            '<strong>Recommendation:</strong> For this dataset size (≤25 nodes), MILP is recommended '
            'for its optimality guarantee. HGA is a fast alternative when time is limited.'
        )
    else:
        parts.append(
            f'<strong>Recommendation:</strong> For larger datasets ({node_count} nodes), HGA offers '
            f'the best quality-to-speed tradeoff. Greedy provides a quick initial estimate.'
        )

    return '<br><br>'.join(parts)


def _bearing(lat1, lon1, lat2, lon2):
    """Compass bearing in degrees (0 = North, clockwise) from point 1 to point 2."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _build_geojson(solution, coordinates, node_name_map=None, vehicle_name_map=None,
                   include_arrows=False, include_legend=False):
    """Return a GeoJSON FeatureCollection dict built from solution + coordinates."""
    from geojson import Feature, FeatureCollection, LineString, Point
    if node_name_map is None:
        node_name_map = {}
    if vehicle_name_map is None:
        vehicle_name_map = {}

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

    legend_routes = []

    for i, (vehicle_id, info) in enumerate(routes.items()):
        nodes = info.get('nodes', [])
        depot = depot_for_vehicle.get(vehicle_id)
        color = route_colors[i % len(route_colors)]
        v_label = vehicle_name_map.get(vehicle_id, vehicle_id)
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
                    'vehicle_id': v_label,
                    'depot_id': node_name_map.get(depot, depot) if depot else '',
                    'type': 'route',
                    'distance_km': round(info.get('distance', 0), 2),
                    'time_hours': round(info.get('time', 0), 2),
                    'stroke': color,
                    'stroke-width': 4,
                    'stroke-opacity': 0.8,
                }
            ))

            if include_arrows:
                for j in range(len(chain) - 1):
                    nid1, nid2 = chain[j], chain[j + 1]
                    if nid1 in coordinates and nid2 in coordinates:
                        lat1, lon1 = coordinates[nid1]
                        lat2, lon2 = coordinates[nid2]
                        mid_lat = (lat1 + lat2) / 2
                        mid_lon = (lon1 + lon2) / 2
                        brng = _bearing(lat1, lon1, lat2, lon2)
                        from_label = node_name_map.get(nid1, nid1)
                        to_label = node_name_map.get(nid2, nid2)
                        features.append(Feature(
                            geometry=Point((mid_lon, mid_lat)),
                            properties={
                                'type': 'direction',
                                'vehicle': v_label,
                                'from': from_label,
                                'to': to_label,
                                'stop_sequence': j + 1,
                                'bearing': round(brng, 1),
                                'marker-color': color,
                                'marker-size': 'small',
                                'marker-symbol': 'triangle',
                                'title': f'Stop {j + 1}: {from_label} → {to_label}',
                            }
                        ))

        if include_legend:
            depot_label = node_name_map.get(depot, depot) if depot else ''
            legend_routes.append({
                'type': 'route',
                'color': color,
                'label': v_label,
                'depot': depot_label,
                'stops': len(nodes),
                'distance_km': round(info.get('distance', 0), 2),
            })

    result = dict(FeatureCollection(features))

    if include_legend:
        result['legend'] = [
            {'type': 'depot', 'color': '#2C3E50', 'marker-size': 'large', 'label': 'Depot'},
            {'type': 'customer', 'color': '#27AE60', 'marker-size': 'medium', 'label': 'Customer'},
            {'type': 'direction', 'color': '#888888', 'marker-size': 'small',
             'marker-symbol': 'triangle', 'label': 'Direction arrow (bearing = compass degrees)'},
            *legend_routes,
        ]

    return result


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def dashboard(request, batch_id):
    batch = get_owned_batch_or_404(request, batch_id)
    experiments = list(batch.experiments.all().select_related('metrics').order_by('experiment_id'))
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

            runtime = None
            violations = 0
            try:
                if hasattr(exp, 'metrics'):
                    runtime = exp.metrics.runtime
                    violations = exp.metrics.constraint_violation or 0
            except Exception:
                pass
            item['runtime'] = runtime
            item['violations'] = violations

            chart_labels.append(exp.algorithm)
            chart_values.append(round(total_dist, 2))

        algo_items.append(item)

    days_remaining = None
    if batch.dataset.user is None and batch.dataset.expires_at:
        delta = batch.dataset.expires_at - timezone.now()
        days_remaining = max(0, delta.days)

    node_count = Node.objects.filter(dataset_id=dataset_id).count()

    comparison_table = [
        {
            'algorithm': item['algorithm'],
            'distance': item['total_distance'],
            'runtime': _format_runtime(item.get('runtime')),
            'violations': item.get('violations', 0),
        }
        for item in algo_items
        if item['status'] == 'completed'
    ]

    algo_results = [
        {
            'algorithm': item['algorithm'],
            'distance': item['total_distance'],
            'runtime': item.get('runtime'),
            'violations': item.get('violations', 0),
        }
        for item in algo_items
        if item['status'] == 'completed'
    ]

    comparison_text = _build_conclusion(algo_results, node_count)

    return render(request, 'results/dashboard.html', {
        'batch': batch,
        'experiments': experiments,
        'algo_items': algo_items,
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
        'vehicle_names_json': json.dumps(vehicle_name_map),
        'days_remaining': days_remaining,
        'share_token': str(batch.share_token) if batch.share_token else '',
        'comparison_table': comparison_table,
        'comparison_text': comparison_text,
    })


def download_csv(request, batch_id, exp_id):
    batch = get_owned_batch_or_404(request, batch_id)
    exp = get_object_or_404(Experiment, pk=exp_id, run_batch=batch)
    if exp.status != 'completed':
        return HttpResponse('Experiment not completed', status=400)

    solution = _build_solution(exp_id, batch.dataset_id)
    name_maps = _build_name_maps(batch.dataset_id)
    buf = io.StringIO()
    MDVRPExporter().export_csv(solution, buf, name_maps=name_maps)
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
    name_maps = _build_name_maps(batch.dataset_id)
    customer_orders = _build_customer_orders(batch.dataset_id)
    buf = io.BytesIO()
    MDVRPExporter().export_pdf(solution, problem_data, buf, algorithm_name=exp.algorithm,
                               name_maps=name_maps, customer_orders=customer_orders)
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
    name_maps = _build_name_maps(batch.dataset_id)
    geojson_dict = _build_geojson(
        solution, coordinates,
        node_name_map=name_maps['node_name_map'],
        vehicle_name_map=name_maps['vehicle_name_map'],
        include_arrows=True,
        include_legend=True,
    )
    response = HttpResponse(
        json.dumps(geojson_dict, indent=2),
        content_type='application/geo+json',
    )
    response['Content-Disposition'] = f'attachment; filename="routes_{exp.algorithm}.geojson"'
    return response
