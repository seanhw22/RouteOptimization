"""ORM models for solver run batches and individual experiments."""

from django.conf import settings
from django.db import models

from datasets.models import Dataset


class RunBatch(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('partial', 'Partial'),
    ]

    id = models.AutoField(primary_key=True)
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name='run_batches'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='run_batches',
    )
    session_key = models.CharField(max_length=64, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        db_table = 'run_batches'
        ordering = ['-created_at']

    def __str__(self):
        return f'Batch #{self.id} ({self.status})'


class Experiment(models.Model):
    ALGORITHM_CHOICES = [
        ('Greedy', 'Greedy'),
        ('HGA', 'HGA'),
        ('MILP', 'MILP'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('killed', 'Killed'),
        ('failed', 'Failed'),
        ('interrupted', 'Interrupted'),
    ]
    TERMINAL_STATUSES = ('completed', 'killed', 'failed', 'interrupted')

    experiment_id = models.AutoField(primary_key=True)
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name='experiments', db_column='dataset_id'
    )
    run_batch = models.ForeignKey(
        RunBatch,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='experiments',
    )
    algorithm = models.CharField(max_length=100, choices=ALGORITHM_CHOICES)

    # Algorithm-specific params (HGA uses these; Greedy/MILP leave NULL)
    population_size = models.IntegerField(null=True, blank=True)
    mutation_rate = models.FloatField(null=True, blank=True)
    crossover_rate = models.FloatField(null=True, blank=True)
    seed = models.IntegerField(null=True, blank=True)
    generations = models.IntegerField(null=True, blank=True)
    time_limit = models.IntegerField(null=True, blank=True)

    # Lifecycle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    pid = models.IntegerField(null=True, blank=True)
    progress_pct = models.IntegerField(default=0)
    best_objective = models.FloatField(null=True, blank=True)
    progress_log = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'experiments'
        ordering = ['experiment_id']
        indexes = [
            models.Index(fields=['dataset']),
            models.Index(fields=['run_batch']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'Experiment #{self.experiment_id} {self.algorithm} ({self.status})'

    @property
    def is_terminal(self):
        return self.status in self.TERMINAL_STATUSES

    def append_log(self, line, max_lines=100):
        """Append a log line, truncating to the most recent ``max_lines``."""
        log = list(self.progress_log or [])
        log.append(line)
        if len(log) > max_lines:
            log = log[-max_lines:]
        self.progress_log = log
