from django.contrib import admin
from django.utils.html import format_html

from results.models import ResultMetrics, Route
from .models import Experiment, RunBatch


class RouteInline(admin.TabularInline):
    model = Route
    extra = 0
    fields = ('route_id', 'vehicle', 'node_start', 'node_end', 'total_distance', 'travel_time')
    readonly_fields = fields
    can_delete = False
    max_num = 0


class ResultMetricsInline(admin.StackedInline):
    model = ResultMetrics
    extra = 0
    readonly_fields = ('runtime', 'constraint_violation')
    can_delete = False


class ExperimentInline(admin.TabularInline):
    model = Experiment
    extra = 0
    fields = ('algorithm', 'status', 'progress_pct', 'best_objective', 'weight_violated', 'started_at', 'completed_at')
    readonly_fields = fields
    show_change_link = True
    can_delete = False


@admin.register(RunBatch)
class RunBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'dataset', 'user', 'status', 'created_at', 'experiment_count', 'completed_count')
    list_filter = ('status', 'created_at')
    search_fields = ('dataset__name', 'user__username')
    list_select_related = ('dataset', 'user')
    readonly_fields = ('created_at', 'share_token', 'session_key')
    inlines = [ExperimentInline]

    @admin.display(description='Experiments')
    def experiment_count(self, obj):
        return obj.experiments.count()

    @admin.display(description='Completed')
    def completed_count(self, obj):
        return obj.experiments.filter(status='completed').count()


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = (
        'experiment_id', 'algorithm', 'dataset_link', 'status', 'progress_pct',
        'best_objective', 'weight_violated', 'runtime_display', 'violations_display',
        'route_count', 'started_at', 'completed_at',
    )
    list_filter = ('algorithm', 'status', 'weight_violated')
    search_fields = ('experiment_id', 'dataset__name', 'run_batch__id')
    list_select_related = ('dataset', 'run_batch')
    readonly_fields = (
        'experiment_id', 'dataset', 'run_batch', 'started_at', 'completed_at',
        'pid', 'progress_log',
    )
    fieldsets = (
        ('Run Info', {
            'fields': ('experiment_id', 'dataset', 'run_batch', 'algorithm', 'status', 'pid'),
        }),
        ('Progress', {
            'fields': ('progress_pct', 'best_objective', 'weight_violated', 'progress_log'),
        }),
        ('HGA Parameters', {
            'classes': ('collapse',),
            'fields': ('population_size', 'mutation_rate', 'crossover_rate', 'seed', 'generations', 'no_improve_limit', 'time_limit'),
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at'),
        }),
    )
    inlines = [ResultMetricsInline, RouteInline]

    @admin.display(description='Dataset', ordering='dataset__name')
    def dataset_link(self, obj):
        return format_html(
            '<a href="/admin/datasets/dataset/{}/change/">{}</a>',
            obj.dataset_id,
            obj.dataset,
        )

    @admin.display(description='Runtime (s)', ordering='metrics__runtime')
    def runtime_display(self, obj):
        try:
            return f'{obj.metrics.runtime:.2f}' if obj.metrics.runtime is not None else '—'
        except ResultMetrics.DoesNotExist:
            return '—'

    @admin.display(description='Violations', ordering='metrics__constraint_violation')
    def violations_display(self, obj):
        try:
            v = obj.metrics.constraint_violation
            return v if v is not None else '—'
        except ResultMetrics.DoesNotExist:
            return '—'

    @admin.display(description='Routes')
    def route_count(self, obj):
        return obj.routes.count()
