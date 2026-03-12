from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import httpx

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
SOURCE = {
    "provider": "Open-Meteo",
    "docs": "https://open-meteo.com/en/docs",
    "license": "https://open-meteo.com/en/licence",
}
CURRENT_FIELDS = (
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "is_day",
)
DAILY_FIELDS = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "sunrise",
    "sunset",
)
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class OpenMeteoError(RuntimeError):
    pass


class OpenMeteoClient:
    def __init__(
        self,
        http_client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._http_client = http_client
        self._timeout = timeout

    def search_locations(
        self,
        name: str,
        count: int = 5,
        language: str = "en",
        country_code: str | None = None,
    ) -> dict[str, Any]:
        query = name.strip()
        if len(query) < 2:
            raise OpenMeteoError("Location searches need at least 2 characters.")

        params: dict[str, Any] = {
            "name": query,
            "count": count,
            "language": language,
            "format": "json",
        }
        if country_code:
            params["countryCode"] = country_code.upper()

        payload = self._request_json(GEOCODING_URL, params)
        results = payload.get("results") or []

        normalized_results = [self._normalize_location(result) for result in results]
        summary = (
            f"Found {len(normalized_results)} matching location(s) for '{query}'."
            if normalized_results
            else f"No matching locations found for '{query}'."
        )

        return {
            "summary": summary,
            "query": query,
            "results": normalized_results,
            "source": SOURCE,
        }

    def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        timezone: str = "auto",
        temperature_unit: str = "celsius",
        wind_speed_unit: str = "kmh",
    ) -> dict[str, Any]:
        payload = self._request_json(
            FORECAST_URL,
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": ",".join(CURRENT_FIELDS),
                "timezone": timezone,
                "temperature_unit": temperature_unit,
                "wind_speed_unit": wind_speed_unit,
            },
        )

        current = dict(payload.get("current") or {})
        if not current:
            raise OpenMeteoError("Open-Meteo did not return current weather data.")

        current["weather_description"] = describe_weather_code(
            current.get("weather_code")
        )
        units = dict(payload.get("current_units") or {})
        temperature = current.get("temperature_2m")
        temperature_unit_label = units.get("temperature_2m", "")
        summary = (
            f"Current weather is {temperature:g}{temperature_unit_label} and "
            f"{current['weather_description'].lower()}."
            if isinstance(temperature, (int, float))
            else f"Current weather data is available for {latitude}, {longitude}."
        )

        return {
            "summary": summary,
            "location": self._forecast_location(payload, latitude, longitude),
            "units": units,
            "current": current,
            "source": SOURCE,
        }

    def get_daily_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 3,
        timezone: str = "auto",
        temperature_unit: str = "celsius",
        wind_speed_unit: str = "kmh",
    ) -> dict[str, Any]:
        payload = self._request_json(
            FORECAST_URL,
            {
                "latitude": latitude,
                "longitude": longitude,
                "daily": ",".join(DAILY_FIELDS),
                "forecast_days": days,
                "timezone": timezone,
                "temperature_unit": temperature_unit,
                "wind_speed_unit": wind_speed_unit,
            },
        )

        daily = payload.get("daily") or {}
        times = daily.get("time") or []
        if not times:
            raise OpenMeteoError("Open-Meteo did not return daily forecast data.")

        forecast_days: list[dict[str, Any]] = []
        for index, date in enumerate(times):
            weather_code = _value_at(daily, "weather_code", index)
            forecast_days.append(
                _drop_none(
                    {
                        "date": date,
                        "weather_code": weather_code,
                        "weather_description": describe_weather_code(weather_code),
                        "temperature_max": _value_at(
                            daily, "temperature_2m_max", index
                        ),
                        "temperature_min": _value_at(
                            daily, "temperature_2m_min", index
                        ),
                        "precipitation_probability_max": _value_at(
                            daily,
                            "precipitation_probability_max",
                            index,
                        ),
                        "sunrise": _value_at(daily, "sunrise", index),
                        "sunset": _value_at(daily, "sunset", index),
                    }
                )
            )

        summary = f"Prepared a {len(forecast_days)}-day forecast."

        return {
            "summary": summary,
            "location": self._forecast_location(payload, latitude, longitude),
            "units": dict(payload.get("daily_units") or {}),
            "forecast_days": forecast_days,
            "source": SOURCE,
        }

    def _request_json(self, url: str, params: Mapping[str, Any]) -> dict[str, Any]:
        try:
            response = self._get(url, params)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise OpenMeteoError(
                "Open-Meteo timed out while handling the request."
            ) from exc
        except httpx.HTTPStatusError as exc:
            reason = _extract_error_reason(exc.response)
            raise OpenMeteoError(
                f"Open-Meteo returned HTTP {exc.response.status_code}: {reason}"
            ) from exc
        except httpx.HTTPError as exc:
            raise OpenMeteoError(f"Open-Meteo request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise OpenMeteoError("Open-Meteo returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise OpenMeteoError("Open-Meteo returned an unexpected response shape.")
        if payload.get("error"):
            raise OpenMeteoError(
                str(payload.get("reason") or "Open-Meteo returned an error.")
            )

        return payload

    def _get(self, url: str, params: Mapping[str, Any]) -> httpx.Response:
        if self._http_client is not None:
            return self._http_client.get(url, params=params, timeout=self._timeout)

        with httpx.Client(timeout=self._timeout) as client:
            return client.get(url, params=params)

    def _normalize_location(self, result: Mapping[str, Any]) -> dict[str, Any]:
        label = _label(
            result.get("name"),
            result.get("admin1"),
            result.get("country"),
        )
        return _drop_none(
            {
                "name": result.get("name"),
                "label": label,
                "country": result.get("country"),
                "country_code": result.get("country_code"),
                "admin1": result.get("admin1"),
                "admin2": result.get("admin2"),
                "admin3": result.get("admin3"),
                "latitude": result.get("latitude"),
                "longitude": result.get("longitude"),
                "elevation": result.get("elevation"),
                "timezone": result.get("timezone"),
                "population": result.get("population"),
                "feature_code": result.get("feature_code"),
            }
        )

    def _forecast_location(
        self,
        payload: Mapping[str, Any],
        requested_latitude: float,
        requested_longitude: float,
    ) -> dict[str, Any]:
        return _drop_none(
            {
                "requested": {
                    "latitude": requested_latitude,
                    "longitude": requested_longitude,
                },
                "resolved": {
                    "latitude": payload.get("latitude"),
                    "longitude": payload.get("longitude"),
                },
                "elevation": payload.get("elevation"),
                "timezone": payload.get("timezone"),
                "timezone_abbreviation": payload.get("timezone_abbreviation"),
            }
        )


def describe_weather_code(code: Any) -> str:
    if isinstance(code, bool):
        return "Unknown conditions"
    if isinstance(code, float) and code.is_integer():
        code = int(code)
    if isinstance(code, int):
        return WEATHER_CODES.get(code, "Unknown conditions")
    return "Unknown conditions"


def _drop_none(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item not in (None, "", [], {})}


def _label(*parts: Any) -> str:
    seen: set[str] = set()
    ordered_parts: list[str] = []
    for part in parts:
        if not isinstance(part, str):
            continue
        normalized = part.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered_parts.append(normalized)
    return ", ".join(ordered_parts)


def _value_at(values: Mapping[str, Any], key: str, index: int) -> Any:
    series = values.get(key)
    if (
        isinstance(series, Sequence)
        and not isinstance(series, (str, bytes))
        and index < len(series)
    ):
        return series[index]
    return None


def _extract_error_reason(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, Mapping):
        reason = payload.get("reason")
        if isinstance(reason, str) and reason.strip():
            return reason.strip()

    return response.text.strip() or "Unknown upstream error"
