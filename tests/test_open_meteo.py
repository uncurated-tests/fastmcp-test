from __future__ import annotations

import httpx

from openmeteo_mcp.open_meteo import OpenMeteoClient


def test_search_locations_formats_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/search"
        assert request.url.params["name"] == "Berlin"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "name": "Berlin",
                        "country": "Germany",
                        "country_code": "DE",
                        "admin1": "Berlin",
                        "latitude": 52.52437,
                        "longitude": 13.41053,
                        "timezone": "Europe/Berlin",
                        "population": 3426354,
                        "feature_code": "PPLC",
                    }
                ]
            },
        )

    client = OpenMeteoClient(httpx.Client(transport=httpx.MockTransport(handler)))
    result = client.search_locations("Berlin")

    assert result["summary"] == "Found 1 matching location(s) for 'Berlin'."
    assert result["results"][0]["label"] == "Berlin, Germany"
    assert result["results"][0]["timezone"] == "Europe/Berlin"


def test_get_current_weather_formats_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/forecast"
        assert request.url.params["latitude"] == "52.52"
        return httpx.Response(
            200,
            json={
                "latitude": 52.52,
                "longitude": 13.41,
                "elevation": 38.0,
                "timezone": "Europe/Berlin",
                "timezone_abbreviation": "CET",
                "current_units": {
                    "temperature_2m": "°C",
                    "wind_speed_10m": "km/h",
                },
                "current": {
                    "temperature_2m": 6.2,
                    "apparent_temperature": 3.8,
                    "relative_humidity_2m": 75,
                    "precipitation": 0.0,
                    "weather_code": 3,
                    "wind_speed_10m": 14.1,
                    "wind_direction_10m": 218,
                    "wind_gusts_10m": 25.0,
                    "is_day": 1,
                },
            },
        )

    client = OpenMeteoClient(httpx.Client(transport=httpx.MockTransport(handler)))
    result = client.get_current_weather(52.52, 13.41)

    assert result["current"]["weather_description"] == "Overcast"
    assert result["location"]["timezone"] == "Europe/Berlin"
    assert result["summary"] == "Current weather is 6.2°C and overcast."


def test_get_daily_forecast_builds_rows() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/forecast"
        assert request.url.params["forecast_days"] == "2"
        return httpx.Response(
            200,
            json={
                "latitude": 52.52,
                "longitude": 13.41,
                "timezone": "Europe/Berlin",
                "timezone_abbreviation": "CET",
                "daily_units": {
                    "temperature_2m_max": "°C",
                    "temperature_2m_min": "°C",
                    "precipitation_probability_max": "%",
                },
                "daily": {
                    "time": ["2026-03-12", "2026-03-13"],
                    "weather_code": [1, 61],
                    "temperature_2m_max": [9.5, 8.1],
                    "temperature_2m_min": [2.3, 1.8],
                    "precipitation_probability_max": [5, 68],
                    "sunrise": ["2026-03-12T06:22", "2026-03-13T06:20"],
                    "sunset": ["2026-03-12T17:58", "2026-03-13T18:00"],
                },
            },
        )

    client = OpenMeteoClient(httpx.Client(transport=httpx.MockTransport(handler)))
    result = client.get_daily_forecast(52.52, 13.41, days=2)

    assert result["summary"] == "Prepared a 2-day forecast."
    assert result["forecast_days"][0]["weather_description"] == "Mainly clear"
    assert result["forecast_days"][1]["precipitation_probability_max"] == 68
