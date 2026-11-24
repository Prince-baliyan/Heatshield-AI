from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0002_assessmentrecommendation_rule_snapshot_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessmentrun",
            name="assessment_warnings",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
