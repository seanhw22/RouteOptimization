import uuid

from django.db import migrations


def backfill_share_tokens(apps, schema_editor):
    RunBatch = apps.get_model('runs', 'RunBatch')
    for batch in RunBatch.objects.filter(user__isnull=True, share_token__isnull=True):
        batch.share_token = uuid.uuid4()
        batch.save(update_fields=['share_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('runs', '0002_runbatch_share_token'),
    ]

    operations = [
        migrations.RunPython(backfill_share_tokens, migrations.RunPython.noop),
    ]
