from django.contrib import admin

from .models import ResultMetrics, Route


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('route_id', 'experiment', 'vehicle_id', 'node_start', 'node_end', 'total_distance')
    list_filter = ('vehicle_id',)


@admin.register(ResultMetrics)
class ResultMetricsAdmin(admin.ModelAdmin):
    list_display = ('result_id', 'experiment', 'runtime', 'constraint_violation')
