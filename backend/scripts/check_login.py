import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import AsyncSessionLocal
from app.models.user import User
from app.services.auth import authenticate_user, verify_password, hash_password
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        users = (await session.execute(select(User))).scalars().all()
        for u in users:
            match = verify_password("password123", u.hashed_password)
            print(f"{u.email}: password123 match={match}")
            auth_user = await authenticate_user(session, u.email, "password123")
            print(f"  authenticate_user: {auth_user is not None}")

if __name__ == "__main__":
    asyncio.run(main())

