from __future__ import annotations

import asyncio

import httpx

from app import app


def test_vercel_entrypoint_serves_health() -> None:
    async def exercise() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "open-meteo-mcp"}

    asyncio.run(exercise())
