import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as s:
        await s.execute(text("CREATE TYPE user_role AS ENUM ('administrator', 'brand_manager', 'reviewer', 'creator', 'auditor')"))
        await s.commit()
        print('MANUAL CREATE TYPE user_role OK')
        await s.execute(text("DROP TYPE user_role"))
        await s.commit()
        print('MANUAL DROP TYPE user_role OK')

if __name__ == "__main__":
    asyncio.run(main())

