from django.contrib import admin

from .models import Experiment, RunBatch


@admin.register(RunBatch)
class RunBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'dataset', 'user', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('experiment_id', 'algorithm', 'status', 'progress_pct', 'best_objective', 'started_at', 'completed_at')
    list_filter = ('algorithm', 'status')
    search_fields = ('experiment_id',)
