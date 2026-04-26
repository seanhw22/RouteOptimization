"""ORM models for solver results: routes and aggregate metrics."""

from django.db import models

from datasets.models import Node
from runs.models import Experiment


class Route(models.Model):
    route_id = models.AutoField(primary_key=True)
    experiment = models.ForeignKey(
        Experiment, on_delete=models.CASCADE, related_name='routes', db_column='experiment_id'
    )
    vehicle_id = models.CharField(max_length=50)
    node_start = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='route_starts',
        db_column='node_start_id',
    )
    node_end = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='route_ends',
        db_column='node_end_id',
    )
    total_distance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    travel_time = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    class Meta:
        db_table = 'routes'
        ordering = ['experiment', 'vehicle_id', 'route_id']
        indexes = [
            models.Index(fields=['experiment']),
            models.Index(fields=['experiment', 'vehicle_id']),
        ]


class ResultMetrics(models.Model):
    result_id = models.AutoField(primary_key=True)
    experiment = models.OneToOneField(
        Experiment, on_delete=models.CASCADE, related_name='metrics', db_column='experiment_id'
    )
    runtime = models.FloatField(null=True, blank=True, db_column='runtime_id')
    constraint_violation = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'result_metrics'
