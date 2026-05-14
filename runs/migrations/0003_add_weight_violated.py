from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('runs', '0002_add_no_improve_limit'),
    ]

    operations = [
        migrations.AddField(
            model_name='experiment',
            name='weight_violated',
            field=models.BooleanField(default=False),
        ),
    ]
