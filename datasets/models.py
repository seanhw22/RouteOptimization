"""ORM models for MDVRP datasets and their entities (nodes, depots, customers, vehicles, items, orders)."""

from django.conf import settings
from django.db import models


class Dataset(models.Model):
    dataset_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='datasets',
    )
    session_key = models.CharField(max_length=64, blank=True, default='')
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'datasets'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} (#{self.dataset_id})'

    @property
    def node_count(self):
        return self.nodes.count()

    @property
    def milp_available(self):
        return self.node_count <= 25


class Node(models.Model):
    node_id = models.CharField(max_length=50, primary_key=True)
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name='nodes', db_column='dataset_id'
    )
    x = models.FloatField()
    y = models.FloatField()

    class Meta:
        db_table = 'nodes'
        indexes = [models.Index(fields=['dataset'])]

    def __str__(self):
        return self.node_id


class Depot(models.Model):
    depot_id = models.CharField(max_length=50, primary_key=True)
    node = models.ForeignKey(
        Node, on_delete=models.CASCADE, related_name='depots', db_column='node_id'
    )
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name='depots', db_column='dataset_id'
    )

    class Meta:
        db_table = 'depots'
        indexes = [models.Index(fields=['dataset'])]

    def __str__(self):
        return self.depot_id


class Customer(models.Model):
    customer_id = models.CharField(max_length=50, primary_key=True)
    node = models.ForeignKey(
        Node, on_delete=models.CASCADE, related_name='customers', db_column='node_id'
    )
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name='customers', db_column='dataset_id'
    )
    deadline_hours = models.IntegerField()

    class Meta:
        db_table = 'customers'
        indexes = [models.Index(fields=['dataset'])]

    def __str__(self):
        return self.customer_id


class Vehicle(models.Model):
    vehicle_id = models.CharField(max_length=50, primary_key=True)
    depot = models.ForeignKey(
        Depot, on_delete=models.CASCADE, related_name='vehicles', db_column='depot_id'
    )
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name='vehicles', db_column='dataset_id'
    )
    vehicle_type = models.CharField(max_length=50, default='truck')
    capacity_kg = models.DecimalField(max_digits=8, decimal_places=2)
    max_operational_hrs = models.DecimalField(max_digits=8, decimal_places=2)
    speed_kmh = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        db_table = 'vehicles'
        indexes = [models.Index(fields=['dataset'])]

    def __str__(self):
        return self.vehicle_id


class Item(models.Model):
    item_id = models.CharField(max_length=50, primary_key=True)
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name='items', db_column='dataset_id'
    )
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2)
    expiry_hours = models.IntegerField()

    class Meta:
        db_table = 'items'
        indexes = [models.Index(fields=['dataset'])]

    def __str__(self):
        return self.item_id


class NodeDistance(models.Model):
    """Pre-computed distance/time cache between two nodes in the same dataset."""

    distance_id = models.AutoField(primary_key=True)
    node_start = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='distance_starts',
        db_column='node_start_id',
    )
    node_end = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='distance_ends',
        db_column='node_end_id',
    )
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name='node_distances', db_column='dataset_id'
    )
    distance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    travel_time = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    class Meta:
        db_table = 'node_distances'
        indexes = [
            models.Index(fields=['dataset']),
            models.Index(fields=['dataset', 'node_start', 'node_end']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['dataset', 'node_start', 'node_end'],
                name='uniq_node_distance_per_dataset',
            ),
        ]


class Order(models.Model):
    order_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name='orders', db_column='customer_id'
    )
    item = models.ForeignKey(
        Item, on_delete=models.CASCADE, related_name='orders', db_column='item_id'
    )
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name='orders', db_column='dataset_id'
    )
    quantity = models.IntegerField()

    class Meta:
        db_table = 'orders'
        indexes = [
            models.Index(fields=['dataset']),
            models.Index(fields=['customer']),
        ]
