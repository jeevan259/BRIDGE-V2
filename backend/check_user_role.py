import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as s:
        res = await s.execute(text("SELECT typname, nspname FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace WHERE t.typname = 'user_role'"))
        print('user_role found:', res.fetchall())

if __name__ == "__main__":
    asyncio.run(main())

