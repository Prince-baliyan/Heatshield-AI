from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


country_code_validator = RegexValidator(
    regex=r"^[A-Z]{2}$",
    message="Country code must be a two-letter uppercase ISO 3166-1 alpha-2 code.",
)


class City(models.Model):
    name = models.CharField(max_length=150)
    state_name = models.CharField(max_length=150)
    country_code = models.CharField(
        max_length=2,
        validators=[country_code_validator],
    )
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cities"
        constraints = [
            models.UniqueConstraint(
                fields=("name", "state_name", "country_code"),
                name="uq_city_identity",
            )
        ]
        ordering = ("country_code", "state_name", "name")

    def clean(self):
        super().clean()
        self.name = self.name.strip()
        self.state_name = self.state_name.strip()
        self.country_code = self.country_code.upper()
        self.status = (self.status or "").strip()
        if not self.name:
            raise ValidationError({"name": "City name is required."})
        if not self.state_name:
            raise ValidationError({"state_name": "State name is required."})
        if not self.status:
            raise ValidationError({"status": "City status is required."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}, {self.state_name}"


class Area(models.Model):
    AREA_TYPE_CHOICES = (
        ("city", "City"),
        ("ward", "Ward"),
    )

    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name="areas",
    )
    area_code = models.CharField(max_length=80, null=True, blank=True)
    area_name = models.CharField(max_length=180)
    area_type = models.CharField(
        max_length=50,
        choices=AREA_TYPE_CHOICES,
        null=True,
        blank=True,
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "areas"
        constraints = [
            models.UniqueConstraint(
                fields=("city", "area_name"),
                name="uq_area_name_in_city",
            ),
            models.UniqueConstraint(
                fields=("city", "area_code"),
                name="uq_area_code_in_city",
            ),
        ]
        indexes = [
            models.Index(fields=("city",), name="ix_area_city"),
        ]
        ordering = ("city", "area_name")

    def clean(self):
        super().clean()
        self.area_name = self.area_name.strip()
        if not self.area_name:
            raise ValidationError({"area_name": "Area name is required."})
        if self.area_type is not None:
            self.area_type = self.area_type.strip().lower() or None
            if self.area_type not in {"city", "ward"}:
                raise ValidationError(
                    {"area_type": "Area type must be either 'city' or 'ward'."}
                )
        if self.latitude is not None and not -90 <= self.latitude <= 90:
            raise ValidationError({"latitude": "Latitude must be between -90 and 90."})
        if self.longitude is not None and not -180 <= self.longitude <= 180:
            raise ValidationError({"longitude": "Longitude must be between -180 and 180."})
        if self.area_code is not None:
            self.area_code = self.area_code.strip() or None

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.area_name} ({self.city.name})"
