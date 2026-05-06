from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('runs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='runbatch',
            name='share_token',
            field=models.UUIDField(blank=True, null=True),
        ),
    ]
