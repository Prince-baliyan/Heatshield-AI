from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("indicators", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="indicatorobservation",
            constraint=models.UniqueConstraint(
                fields=(
                    "area",
                    "dataset",
                    "indicator_code",
                    "period_start",
                    "period_end",
                ),
                name="uq_obs_area_dataset_period",
            ),
        ),
    ]
