from django.core.exceptions import ValidationError
from django.db import models


class DataSource(models.Model):
    source_name = models.CharField(max_length=200)
    owner_name = models.CharField(max_length=200)
    official_url = models.TextField(null=True, blank=True)
    licence_terms = models.TextField(null=True, blank=True)
    approval_status = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "data_sources"
        ordering = ("source_name",)

    def clean(self):
        super().clean()
        self.source_name = (self.source_name or "").strip()
        self.owner_name = (self.owner_name or "").strip()
        if not self.source_name:
            raise ValidationError({"source_name": "Source name is required."})
        if not self.owner_name:
            raise ValidationError({"owner_name": "Owner name is required."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.source_name


class Dataset(models.Model):
    DATA_CLASS_CHOICES = (
        ("observed", "Observed"),
        ("derived", "Derived"),
        ("illustrative", "Illustrative"),
    )

    source = models.ForeignKey(
        DataSource,
        on_delete=models.PROTECT,
        related_name="datasets",
    )
    dataset_name = models.CharField(max_length=200)
    data_class = models.CharField(max_length=20, choices=DATA_CLASS_CHOICES)
    spatial_resolution = models.CharField(max_length=100)
    published_at = models.DateField(null=True, blank=True)
    coverage_start = models.DateField(null=True, blank=True)
    coverage_end = models.DateField(null=True, blank=True)
    retrieved_at = models.DateTimeField()
    file_hash = models.CharField(max_length=128, null=True, blank=True)
    transformation_notes = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = "datasets"
        ordering = ("-retrieved_at", "dataset_name")

    def clean(self):
        super().clean()
        self.dataset_name = (self.dataset_name or "").strip()
        self.spatial_resolution = (self.spatial_resolution or "").strip()
        if not self.dataset_name:
            raise ValidationError({"dataset_name": "Dataset name is required."})
        if not self.spatial_resolution:
            raise ValidationError(
                {"spatial_resolution": "Spatial resolution is required."}
            )
        if (
            self.coverage_start is not None
            and self.coverage_end is not None
            and self.coverage_start > self.coverage_end
        ):
            raise ValidationError(
                {"coverage_end": "Coverage end cannot precede coverage start."}
            )

    def __str__(self):
        return f"{self.dataset_name} ({self.data_class})"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
