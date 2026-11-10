"""Bounded live Gemini status probe; never prints the API key or response body."""
from __future__ import annotations

import asyncio

import httpx
from app.main import app


async def main() -> None:
    print("probe=GET /api/v1/ai/status", flush=True)
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://bridge.local",
            timeout=15,
        ) as client:
            response = await asyncio.wait_for(
                client.get("/api/v1/ai/status"), timeout=18
            )
        print(f"GET /api/v1/ai/status HTTP {response.status_code}")
        data = response.json()
        print(f"provider={data.get('provider')}")
        print(f"mode={data.get('mode')}")
        print(f"model={data.get('model')}")
        if data.get("last_error"):
            print(f"redacted_error={data['last_error']}")
    except asyncio.TimeoutError:
        print("redacted_error=Gemini status probe timed out (18s)")
    except httpx.TimeoutException:
        print("redacted_error=Gemini network timeout (15s)")
    except httpx.HTTPError:
        print("redacted_error=Gemini network request failed")


if __name__ == "__main__":
    asyncio.run(main())
