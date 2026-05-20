"""Views for the datasets app: upload, list, detail."""

import uuid

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from accounts.permissions import (
    get_owned_dataset_or_404,
    is_guest,
)

from .forms import DatasetUploadForm
from .models import Dataset
from .services import DatasetValidationError, parse_uploaded, save_dataset, validate_frames

_SAMPLE_DATASETS = {
    '5':   ('5nodes',   'Sample 5 nodes'),
    '10':  ('10nodes',  'Sample 10 nodes'),
    '15':  ('15nodes',  'Sample 15 nodes'),
    '50':  ('50nodes',  'Sample 50 nodes'),
    '100': ('100nodes', 'Sample 100 nodes'),
    '200': ('200nodes', 'Sample 200 nodes'),
}


def _require_session(request):
    """Authenticated users + guests both proceed; otherwise bounce to login."""
    if request.user.is_authenticated or is_guest(request) or request.GET.get('token'):
        return None
    return redirect('accounts:login')


@require_http_methods(['GET', 'POST'])
def upload(request):
    bounce = _require_session(request)
    if bounce:
        return bounce

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = DatasetUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                frames = parse_uploaded(request.FILES)
                validate_frames(frames)
            except DatasetValidationError as e:
                if is_ajax:
                    return JsonResponse(
                        {'ok': False, 'errors': {'__all__': [{'message': str(e)}]}},
                        status=422,
                    )
                form.add_error(None, str(e))
            else:
                if not request.session.session_key:
                    request.session.create()
                user = request.user if request.user.is_authenticated else None
                dataset = save_dataset(
                    name=form.cleaned_data['name'],
                    user=user,
                    session_key=request.session.session_key or '',
                    is_guest=is_guest(request) and not request.user.is_authenticated,
                    frames=frames,
                )
                if not request.user.is_authenticated:
                    guest_ids = list(request.session.get('guest_datasets', []))
                    guest_ids.append(dataset.dataset_id)
                    request.session['guest_datasets'] = guest_ids
                messages.success(request, f'Dataset "{dataset.name}" uploaded.')
                url = reverse('datasets:detail', args=[dataset.dataset_id])
                if is_ajax:
                    return JsonResponse({'ok': True, 'redirect': url})
                return redirect('datasets:detail', dataset_id=dataset.dataset_id)

        if is_ajax:
            return JsonResponse({'ok': False, 'errors': form.errors.get_json_data()}, status=422)
    else:
        form = DatasetUploadForm()

    sample_datasets = [
        (key, label, int(key) <= 25)
        for key, (_, label) in _SAMPLE_DATASETS.items()
    ]
    return render(request, 'datasets/upload.html', {'form': form, 'sample_datasets': sample_datasets})


@require_http_methods(['GET'])
def dataset_list(request):
    bounce = _require_session(request)
    if bounce:
        return bounce

    if request.user.is_authenticated:
        qs = Dataset.objects.filter(user=request.user)
    else:
        ids = request.session.get('guest_datasets', [])
        qs = Dataset.objects.filter(dataset_id__in=ids)
    qs = qs.order_by('-created_at')

    return render(request, 'datasets/list.html', {'datasets': qs})


@require_http_methods(['GET'])
def detail(request, dataset_id):
    bounce = _require_session(request)
    if bounce:
        return bounce
    dataset = get_owned_dataset_or_404(request, dataset_id)

    depots = list(dataset.depots.select_related('node').all())
    customers = list(dataset.customers.select_related('node').all())
    vehicles = list(dataset.vehicles.select_related('depot').all())
    items = list(dataset.items.all())
    orders = list(dataset.orders.select_related('customer', 'item').all())

    counts = {
        'depots': len(depots),
        'customers': len(customers),
        'vehicles': len(vehicles),
        'items': len(items),
        'orders': len(orders),
        'nodes': len(depots) + len(customers),
    }

    if request.user.is_authenticated:
        run_batches = dataset.run_batches.filter(user=request.user)
    else:
        # Ownership already verified; show all batches for this guest dataset
        run_batches = dataset.run_batches.all()
    run_batches = run_batches.prefetch_related('experiments').order_by('-created_at')

    return render(request, 'datasets/detail.html', {
        'dataset': dataset,
        'counts': counts,
        'depots': depots[:50],
        'customers': customers[:50],
        'vehicles': vehicles[:50],
        'items': items[:50],
        'orders': orders[:50],
        'milp_available': counts['nodes'] <= 25,
        'run_batches': run_batches,
        'share_token': str(dataset.share_token) if dataset.share_token else '',
        'has_depot_names': any(d.name for d in depots),
        'has_customer_names': any(c.name for c in customers),
        'has_vehicle_names': any(v.name for v in vehicles),
        'has_item_names': any(it.name for it in items),
    })


@require_POST
def generate_share_link(request, dataset_id):
    dataset = get_owned_dataset_or_404(request, dataset_id)
    if not dataset.share_token:
        dataset.share_token = uuid.uuid4()
        dataset.save(update_fields=['share_token'])
    return redirect('datasets:detail', dataset_id=dataset_id)


@require_POST
def rename_dataset(request, dataset_id):
    dataset = get_owned_dataset_or_404(request, dataset_id)
    new_name = request.POST.get('name', '').strip()
    if new_name:
        dataset.name = new_name
        dataset.save(update_fields=['name'])
        messages.success(request, f'Dataset renamed to "{new_name}".')
    else:
        messages.error(request, 'Name cannot be empty.')
    return redirect('datasets:detail', dataset_id=dataset_id)


@require_POST
def delete_dataset(request, dataset_id):
    dataset = get_owned_dataset_or_404(request, dataset_id)
    name = dataset.name
    dataset.delete()
    if not request.user.is_authenticated:
        guest_ids = list(request.session.get('guest_datasets', []))
        if dataset_id in guest_ids:
            guest_ids.remove(dataset_id)
            request.session['guest_datasets'] = guest_ids
    messages.success(request, f'Dataset "{name}" deleted.')
    return redirect('datasets:list')


@require_POST
def load_sample(request):
    bounce = _require_session(request)
    if bounce:
        return bounce

    key = request.POST.get('sample', '')
    if key not in _SAMPLE_DATASETS:
        messages.error(request, 'Unknown sample dataset.')
        return redirect('datasets:upload')

    label, display_name = _SAMPLE_DATASETS[key]
    xlsx_path = settings.BASE_DIR / 'dataset_for_use' / f'data_{label}' / f'dataset_{label}.xlsx'

    try:
        with open(xlsx_path, 'rb') as f:
            frames = parse_uploaded({'xlsx': f})
        validate_frames(frames)
    except (DatasetValidationError, OSError) as e:
        messages.error(request, f'Could not load sample dataset: {e}')
        return redirect('datasets:upload')

    if not request.session.session_key:
        request.session.create()
    user = request.user if request.user.is_authenticated else None
    dataset = save_dataset(
        name=display_name,
        user=user,
        session_key=request.session.session_key or '',
        is_guest=is_guest(request) and not request.user.is_authenticated,
        frames=frames,
    )
    if not request.user.is_authenticated:
        guest_ids = list(request.session.get('guest_datasets', []))
        guest_ids.append(dataset.dataset_id)
        request.session['guest_datasets'] = guest_ids

    messages.success(request, f'Sample dataset "{dataset.name}" loaded.')
    return redirect('datasets:detail', dataset_id=dataset.dataset_id)
