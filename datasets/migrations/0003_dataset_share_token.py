from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0002_nodedistance'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='share_token',
            field=models.UUIDField(blank=True, null=True),
        ),
    ]
