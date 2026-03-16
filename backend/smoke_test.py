import os
import asyncio
import pathlib
import httpx


os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./smoke_test.db"


async def main() -> None:
    db_path = pathlib.Path(__file__).with_name("smoke_test.db")
    if db_path.exists():
        db_path.unlink()

    from app.main import app

    await app.router.startup()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"x-user-id": "smoke-user"}

            r = await client.get("/api/me", headers=headers)
            r.raise_for_status()

            r = await client.get("/api/cases")
            r.raise_for_status()
            case_id = r.json()[0]["id"]

            r = await client.post(f"/api/me/cases/{case_id}/session", headers=headers)
            r.raise_for_status()
            session_id = r.json()["session_id"]

            r = await client.get(f"/api/sessions/{session_id}/stage", headers=headers)
            r.raise_for_status()

            graph_state = {"nodes": {"n1": {"x": 1, "y": 2}}, "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}}
            r = await client.post(
                f"/api/sessions/{session_id}/graph-state",
                headers=headers,
                json={"graph_state": graph_state},
            )
            r.raise_for_status()

            r = await client.get(f"/api/sessions/{session_id}/graph-state", headers=headers)
            r.raise_for_status()
            assert r.json()["graph_state"]["nodes"]["n1"]["x"] == 1

            r = await client.get("/api/me/cases", headers=headers)
            r.raise_for_status()
            assert isinstance(r.json(), list)
    finally:
        await app.router.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
