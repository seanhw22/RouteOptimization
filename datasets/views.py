"""Views for the datasets app: upload, list, detail."""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.permissions import (
    get_owned_dataset_or_404,
    is_guest,
)

from .forms import DatasetUploadForm
from .models import Dataset
from .services import DatasetValidationError, parse_uploaded, save_dataset, validate_frames


def _require_session(request):
    """Authenticated users + guests both proceed; otherwise bounce to login."""
    if request.user.is_authenticated or is_guest(request):
        return None
    return redirect('accounts:login')


@require_http_methods(['GET', 'POST'])
def upload(request):
    bounce = _require_session(request)
    if bounce:
        return bounce

    if request.method == 'POST':
        form = DatasetUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                frames = parse_uploaded(request.FILES)
                validate_frames(frames)
            except DatasetValidationError as e:
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
                return redirect('datasets:detail', dataset_id=dataset.dataset_id)
    else:
        form = DatasetUploadForm()

    return render(request, 'datasets/upload.html', {'form': form})


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
    vehicles = list(dataset.vehicles.all())
    items = list(dataset.items.all())
    orders = list(dataset.orders.all())

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
        run_batches = dataset.run_batches.filter(session_key=request.session.session_key)
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
    })
