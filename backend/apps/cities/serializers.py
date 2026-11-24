from rest_framework import serializers

from .models import Area, City
from .readiness import compute_area_readiness


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name", "state_name", "country_code", "status")


class AreaSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    city_id = serializers.IntegerField(source="city.id", read_only=True)
    assessment_ready = serializers.SerializerMethodField()
    is_assessment_ready = serializers.SerializerMethodField()
    readiness_status = serializers.SerializerMethodField()
    readiness_reasons = serializers.SerializerMethodField()
    available_indicators = serializers.SerializerMethodField()
    missing_indicators = serializers.SerializerMethodField()
    latest_observation_period = serializers.SerializerMethodField()
    observation_age_days = serializers.SerializerMethodField()
    max_observation_age_days = serializers.SerializerMethodField()
    freshness_status = serializers.SerializerMethodField()
    geometry_limitation = serializers.SerializerMethodField()

    def _readiness(self, obj):
        cache = self.context.setdefault("_area_readiness", {})
        if obj.pk not in cache:
            cache[obj.pk] = compute_area_readiness(obj)
        return cache[obj.pk]

    def get_assessment_ready(self, obj):
        return self._readiness(obj)["assessment_ready"]

    def get_is_assessment_ready(self, obj):
        return self._readiness(obj)["is_assessment_ready"]

    def get_readiness_status(self, obj):
        return self._readiness(obj)["readiness_status"]

    def get_readiness_reasons(self, obj):
        return self._readiness(obj)["readiness_reasons"]

    def get_available_indicators(self, obj):
        return self._readiness(obj)["available_indicators"]

    def get_missing_indicators(self, obj):
        return self._readiness(obj)["missing_indicators"]

    def get_latest_observation_period(self, obj):
        return self._readiness(obj)["latest_observation_period"]

    def get_observation_age_days(self, obj):
        return self._readiness(obj)["observation_age_days"]

    def get_max_observation_age_days(self, obj):
        return self._readiness(obj)["max_observation_age_days"]

    def get_freshness_status(self, obj):
        return self._readiness(obj)["freshness_status"]

    def get_geometry_limitation(self, obj):
        if obj.latitude is None or obj.longitude is None:
            return "No verified representative coordinate is stored for this area."
        return (
            "Only a representative city-level point is available. Municipal or "
            "ward polygons are not stored and are not shown."
        )

    class Meta:
        model = Area
        fields = (
            "id",
            "city_id",
            "city",
            "area_code",
            "area_name",
            "area_type",
            "latitude",
            "longitude",
            "assessment_ready",
            "is_assessment_ready",
            "readiness_status",
            "readiness_reasons",
            "available_indicators",
            "missing_indicators",
            "latest_observation_period",
            "observation_age_days",
            "max_observation_age_days",
            "freshness_status",
            "geometry_limitation",
        )
