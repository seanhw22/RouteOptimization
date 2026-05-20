from django.contrib import admin

from .models import ResultMetrics, Route


@admin.register(ResultMetrics)
class ResultMetricsAdmin(admin.ModelAdmin):
    list_display = ('result_id', 'experiment', 'algorithm', 'dataset', 'runtime', 'constraint_violation')
    list_filter = ('experiment__algorithm', 'experiment__status')
    search_fields = ('experiment__experiment_id', 'experiment__dataset__name')
    list_select_related = ('experiment', 'experiment__dataset')
    readonly_fields = ('result_id', 'experiment')

    @admin.display(description='Algorithm', ordering='experiment__algorithm')
    def algorithm(self, obj):
        return obj.experiment.algorithm

    @admin.display(description='Dataset', ordering='experiment__dataset__name')
    def dataset(self, obj):
        return obj.experiment.dataset

    @admin.display(description='Algorithm', ordering='experiment__algorithm')
    def algorithm(self, obj):
        return obj.experiment.algorithm

    @admin.display(description='Dataset', ordering='experiment__dataset__name')
    def dataset(self, obj):
        return obj.experiment.dataset


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('route_id', 'experiment', 'vehicle', 'node_start', 'node_end', 'total_distance', 'travel_time')
    list_filter = ('experiment__algorithm',)
    search_fields = ('experiment__experiment_id', 'vehicle__vehicle_id')
    list_select_related = ('experiment', 'vehicle', 'node_start', 'node_end')
