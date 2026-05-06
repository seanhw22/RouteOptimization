import uuid

from django.db import migrations


def backfill_share_tokens(apps, schema_editor):
    Dataset = apps.get_model('datasets', 'Dataset')
    for ds in Dataset.objects.filter(user__isnull=True, share_token__isnull=True):
        ds.share_token = uuid.uuid4()
        ds.save(update_fields=['share_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0003_dataset_share_token'),
    ]

    operations = [
        migrations.RunPython(backfill_share_tokens, migrations.RunPython.noop),
    ]
