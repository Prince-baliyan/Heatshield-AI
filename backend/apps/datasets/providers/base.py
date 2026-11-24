from abc import ABC, abstractmethod
from typing import Any


class WeatherDataProvider(ABC):
    """Common interface for all HeatShield-AI weather data providers."""

    @abstractmethod
    def fetch_weather(
        self,
        location: str,
        *,
        scenario_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch weather information for a location.

        Expected response:
        {
            "source": str,
            "data_class": str,
            "location": str,
            "spatial_resolution": str,
            "retrieved_at": str,
            "scenario_id": str | None,
            "scenario_name": str | None,
            "observations": list,
            "quality_status": str,
        }
        """
        raise NotImplementedError
