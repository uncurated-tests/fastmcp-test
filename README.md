# Open-Meteo MCP

A small FastMCP server that wraps the public Open-Meteo geocoding and forecast APIs.

## Tools

- `search_locations`: search for cities or postal codes and get coordinates back
- `get_current_weather`: fetch current conditions for latitude and longitude
- `get_daily_forecast`: fetch a 1-7 day forecast for latitude and longitude

## Requirements

- Python 3.11+
- `uv`

## Install

```bash
uv sync
```

## Run locally

STDIO transport:

```bash
uv run openmeteo-mcp
```

HTTP transport:

```bash
uv run fastmcp run src/openmeteo_mcp/server.py:mcp --transport http --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Test

```bash
uv run pytest
```

## Example client call

```bash
uv run python - <<'PY'
import asyncio
from fastmcp import Client

async def main() -> None:
    async with Client("http://127.0.0.1:8000/mcp") as client:
        locations = await client.call_tool("search_locations", {"name": "Berlin"})
        print(locations.data)

asyncio.run(main())
PY
```
