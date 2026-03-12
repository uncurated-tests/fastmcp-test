from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

try:
    from .open_meteo import OpenMeteoClient, OpenMeteoError
except ImportError:
    from openmeteo_mcp.open_meteo import OpenMeteoClient, OpenMeteoError

READ_ONLY_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}


def create_server(weather_client: OpenMeteoClient | None = None) -> FastMCP:
    api = weather_client or OpenMeteoClient()
    mcp = FastMCP(
        name="Open-Meteo MCP",
        instructions=(
            "Use search_locations when you only have a place name. "
            "Use the returned coordinates with the weather tools."
        ),
    )

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "open-meteo-mcp"})

    @mcp.tool(
        name="search_locations",
        description="Search cities or postal codes with the Open-Meteo geocoding API.",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    def search_locations(
        name: Annotated[
            str,
            Field(description="City name or postal code to search for.", min_length=2),
        ],
        count: Annotated[
            int,
            Field(description="Maximum number of results to return.", ge=1, le=10),
        ] = 5,
        language: Annotated[
            str,
            Field(
                description="Language code for translated place names.", min_length=2
            ),
        ] = "en",
        country_code: Annotated[
            str | None,
            Field(
                description="Optional 2-letter ISO country code filter.",
                min_length=2,
                max_length=2,
            ),
        ] = None,
    ) -> dict[str, Any]:
        try:
            return api.search_locations(
                name=name,
                count=count,
                language=language,
                country_code=country_code,
            )
        except OpenMeteoError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="get_current_weather",
        description="Get current weather conditions for a set of coordinates.",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    def get_current_weather(
        latitude: Annotated[
            float,
            Field(description="Latitude in WGS84 decimal degrees.", ge=-90, le=90),
        ],
        longitude: Annotated[
            float,
            Field(description="Longitude in WGS84 decimal degrees.", ge=-180, le=180),
        ],
        timezone: Annotated[
            str,
            Field(
                description="Timezone name or 'auto' to resolve from the coordinates."
            ),
        ] = "auto",
        temperature_unit: Annotated[
            Literal["celsius", "fahrenheit"],
            Field(description="Unit for temperature values."),
        ] = "celsius",
        wind_speed_unit: Annotated[
            Literal["kmh", "ms", "mph", "kn"],
            Field(description="Unit for wind speed values."),
        ] = "kmh",
    ) -> dict[str, Any]:
        try:
            return api.get_current_weather(
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
                temperature_unit=temperature_unit,
                wind_speed_unit=wind_speed_unit,
            )
        except OpenMeteoError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="get_daily_forecast",
        description="Get a multi-day weather forecast for a set of coordinates.",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    def get_daily_forecast(
        latitude: Annotated[
            float,
            Field(description="Latitude in WGS84 decimal degrees.", ge=-90, le=90),
        ],
        longitude: Annotated[
            float,
            Field(description="Longitude in WGS84 decimal degrees.", ge=-180, le=180),
        ],
        days: Annotated[
            int,
            Field(description="Number of forecast days to return.", ge=1, le=7),
        ] = 3,
        timezone: Annotated[
            str,
            Field(
                description="Timezone name or 'auto' to resolve from the coordinates."
            ),
        ] = "auto",
        temperature_unit: Annotated[
            Literal["celsius", "fahrenheit"],
            Field(description="Unit for temperature values."),
        ] = "celsius",
        wind_speed_unit: Annotated[
            Literal["kmh", "ms", "mph", "kn"],
            Field(description="Unit for wind speed values."),
        ] = "kmh",
    ) -> dict[str, Any]:
        try:
            return api.get_daily_forecast(
                latitude=latitude,
                longitude=longitude,
                days=days,
                timezone=timezone,
                temperature_unit=temperature_unit,
                wind_speed_unit=wind_speed_unit,
            )
        except OpenMeteoError as exc:
            raise ToolError(str(exc)) from exc

    return mcp


mcp = create_server()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
