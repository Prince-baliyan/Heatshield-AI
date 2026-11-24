from datetime import datetime, timezone
from typing import Any

from .base import WeatherDataProvider


DEMO_SCENARIOS = {
    "standard": {
        "name": "Standard illustration",
        "temperature": 38.0,
        "humidity": 55.0,
        "rainfall": 0.0,
    },
    "hot_dry": {
        "name": "Hot and dry",
        "temperature": 42.0,
        "humidity": 25.0,
        "rainfall": 0.0,
    },
    "hot_humid": {
        "name": "Hot and humid",
        "temperature": 39.0,
        "humidity": 80.0,
        "rainfall": 2.0,
    },
    "moderate": {
        "name": "Moderate conditions",
        "temperature": 28.0,
        "humidity": 55.0,
        "rainfall": 5.0,
    },
    "heavy_rainfall": {
        "name": "Heavy rainfall illustration",
        "temperature": 26.0,
        "humidity": 90.0,
        "rainfall": 45.0,
    },
}


class DemoWeatherProvider(WeatherDataProvider):
    """Provides synthetic, clearly labelled demonstration scenarios."""

    def fetch_weather(
        self,
        location: str,
        *,
        scenario_id: str | None = None,
    ) -> dict[str, Any]:
        if not location or not location.strip():
            raise ValueError("Location is required.")
        selected_scenario = scenario_id or "standard"
        try:
            scenario = DEMO_SCENARIOS[selected_scenario]
        except KeyError as error:
            raise ValueError("Unsupported illustrative demo scenario.") from error

        return {
            "source": (
                "HeatShield-AI Synthetic Demonstration (Illustrative) — "
                f"{scenario['name']}"
            ),
            "data_class": "illustrative",
            "location": location.strip(),
            "spatial_resolution": "illustrative_city_level",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "scenario_id": selected_scenario,
            "scenario_name": scenario["name"],
            "observations": [
                {
                    "indicator_code": "AIR_TEMPERATURE",
                    "value": scenario["temperature"],
                    "unit": "degree_celsius",
                    "measurement_period": (
                        "illustrative_instantaneous_sample"
                        if selected_scenario == "standard"
                        else f"synthetic_{selected_scenario}_sample"
                    ),
                },
                {
                    "indicator_code": "RELATIVE_HUMIDITY",
                    "value": scenario["humidity"],
                    "unit": "percent",
                    "measurement_period": (
                        "illustrative_instantaneous_sample"
                        if selected_scenario == "standard"
                        else f"synthetic_{selected_scenario}_sample"
                    ),
                },
                {
                    "indicator_code": "RAINFALL_24H",
                    "value": scenario["rainfall"],
                    "unit": "mm",
                    "measurement_period": (
                        "illustrative_24h_sample"
                        if selected_scenario == "standard"
                        else f"synthetic_{selected_scenario}_24h_sample"
                    ),
                },
            ],
            "quality_status": "ILLUSTRATIVE_NOT_OBSERVED",
        }
