import asyncio
import os
import sys

# Ensure api directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine, AsyncSessionLocal
from app.models.user import User
from app.models.organisation import Organisation
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        orgs = (await session.execute(select(Organisation))).scalars().all()
        print(f"Organisations count: {len(orgs)}")
        for org in orgs:
            print(f"  Org: {org.name} ({org.slug}), id={org.id}")
        
        users = (await session.execute(select(User))).scalars().all()
        print(f"Users count: {len(users)}")
        for u in users:
            print(f"  User: {u.email}, role={u.role}, hash_len={len(u.hashed_password) if u.hashed_password else 0}, prefix={u.hashed_password[:10] if u.hashed_password else None}")

if __name__ == "__main__":
    asyncio.run(main())

