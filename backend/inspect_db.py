import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as s:
        v = await s.execute(text("SELECT version_num FROM alembic_version"))
        print("ALEMBIC_VERSION:", [r[0] for r in v.fetchall()])
        t = await s.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"))
        rows = [r[0] for r in t.fetchall()]
        print(f"TABLES ({len(rows)}):", rows)

if __name__ == "__main__":
    asyncio.run(main())

