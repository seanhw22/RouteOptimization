"""Admin-only stats dashboard view."""

from datetime import timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from datasets.models import Dataset
from runs.models import Experiment, RunBatch


def stats_dashboard(request):
    User = get_user_model()
    thirty_days_ago = timezone.now() - timedelta(days=30)

    # --- Usage stats ---
    total_users = User.objects.count()
    total_datasets = Dataset.objects.count()
    total_batches = RunBatch.objects.count()
    total_experiments = Experiment.objects.count()
    recent_experiments = Experiment.objects.filter(
        started_at__gte=thirty_days_ago
    ).count()

    # --- Status breakdown ---
    status_counts = list(
        Experiment.objects
        .values('status')
        .annotate(count=Count('experiment_id'))
        .order_by('status')
    )

    # --- Algorithm comparison ---
    algo_stats = list(
        Experiment.objects
        .values('algorithm')
        .annotate(
            total=Count('experiment_id'),
            completed=Count('experiment_id', filter=Q(status='completed')),
            failed=Count(
                'experiment_id',
                filter=Q(status__in=['failed', 'killed', 'interrupted']),
            ),
            avg_objective=Avg('best_objective', filter=Q(status='completed')),
            avg_runtime=Avg('metrics__runtime', filter=Q(status='completed')),
            total_violations=Sum(
                'metrics__constraint_violation',
                filter=Q(status='completed'),
            ),
        )
        .order_by('algorithm')
    )

    for row in algo_stats:
        total = row['total'] or 1
        row['success_pct'] = round(row['completed'] / total * 100)
        row['avg_objective'] = round(row['avg_objective'], 2) if row['avg_objective'] is not None else None
        row['avg_runtime'] = round(row['avg_runtime'], 2) if row['avg_runtime'] is not None else None

    # --- Dataset stats ---
    datasets_qs = Dataset.objects.annotate(nc=Count('nodes'))
    dataset_avg_nodes = datasets_qs.aggregate(avg=Avg('nc'))['avg']
    dataset_milp_eligible = datasets_qs.filter(nc__lte=25).count()

    # --- Recent experiments ---
    recent_list = list(
        Experiment.objects
        .select_related('dataset__user', 'metrics')
        .order_by('-experiment_id')[:10]
    )

    context = {
        **admin.site.each_context(request),
        'title': 'Stats Dashboard',
        'total_users': total_users,
        'total_datasets': total_datasets,
        'total_batches': total_batches,
        'total_experiments': total_experiments,
        'recent_experiments': recent_experiments,
        'status_counts': status_counts,
        'algo_stats': algo_stats,
        'dataset_avg_nodes': round(dataset_avg_nodes, 1) if dataset_avg_nodes else 0,
        'dataset_milp_eligible': dataset_milp_eligible,
        'recent_list': recent_list,
    }
    return render(request, 'admin/stats_dashboard.html', context)
