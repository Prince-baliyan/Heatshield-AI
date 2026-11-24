import os

from .base import WeatherDataProvider
from .demo import DemoWeatherProvider


def get_weather_provider(
    provider_name: str | None = None,
) -> WeatherDataProvider:
    """Return the configured weather data provider."""

    selected_provider = (
        provider_name or os.getenv("WEATHER_DATA_PROVIDER", "demo")
    ).strip().lower()

    if selected_provider == "demo":
        return DemoWeatherProvider()

    if selected_provider == "imd":
        raise ValueError(
            "The IMD weather provider is not implemented; "
            "use the clearly labelled demo provider instead."
        )

    raise ValueError(
        f"Unsupported weather provider: {selected_provider}"
    )
