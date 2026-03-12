from __future__ import annotations

import asyncio

import httpx

from fastmcp import Client
from openmeteo_mcp.open_meteo import OpenMeteoClient
from openmeteo_mcp.server import create_server


def test_server_exposes_tools_and_calls_them() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "geocoding-api.open-meteo.com":
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
                        }
                    ]
                },
            )

        return httpx.Response(
            200,
            json={
                "latitude": 52.52,
                "longitude": 13.41,
                "timezone": "Europe/Berlin",
                "timezone_abbreviation": "CET",
                "current_units": {"temperature_2m": "°C"},
                "current": {
                    "temperature_2m": 6.2,
                    "weather_code": 2,
                    "apparent_temperature": 4.4,
                    "relative_humidity_2m": 75,
                    "precipitation": 0.0,
                    "wind_speed_10m": 11.3,
                    "wind_direction_10m": 180,
                    "wind_gusts_10m": 19.1,
                    "is_day": 1,
                },
            },
        )

    weather_client = OpenMeteoClient(
        httpx.Client(transport=httpx.MockTransport(handler))
    )
    server = create_server(weather_client)

    async def exercise_server() -> None:
        async with Client(server) as client:
            tools = await client.list_tools()
            tool_names = {tool.name for tool in tools}
            assert tool_names == {
                "search_locations",
                "get_current_weather",
                "get_daily_forecast",
            }

            search_result = await client.call_tool(
                "search_locations", {"name": "Berlin"}
            )
            assert search_result.data["results"][0]["name"] == "Berlin"

            weather_result = await client.call_tool(
                "get_current_weather",
                {"latitude": 52.52, "longitude": 13.41},
            )
            assert (
                weather_result.data["current"]["weather_description"] == "Partly cloudy"
            )

    asyncio.run(exercise_server())
