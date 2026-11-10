import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as s:
        res = await s.execute(text("SELECT typname FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace WHERE n.nspname = 'public' AND t.typtype = 'e'"))
        types = [r[0] for r in res.fetchall()]
        print(f"ENUM TYPES IN DB ({len(types)}):", types)

if __name__ == "__main__":
    asyncio.run(main())

