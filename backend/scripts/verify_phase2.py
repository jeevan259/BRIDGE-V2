import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import AsyncSessionLocal
from app.api.v1.auth import guest_login
from starlette.requests import Request
from starlette.responses import Response
from app.services.auth import decode_access_token
from app.services.audit import verify_audit_chain
from app.models.organisation import Organisation
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        # Build mock request
        scope = {
            "type": "http",
            "method": "POST",
            "headers": [(b"x-forwarded-for", b"203.0.113.195")],
            "client": ("203.0.113.195", 12345),
        }
        req = Request(scope)
        res = Response()

        token_res = await guest_login(request=req, response=res, db=session)
        await session.commit()

        print(f"Guest login success!")
        print(f"  Access token generated (len={len(token_res.access_token)})")
        
        # Verify token contents
        payload = decode_access_token(token_res.access_token)
        print(f"  Token claims: sub={payload.get('sub')}, org={payload.get('org')}")
        
        # Verify cookie was set
        cookies = [h for h in res.raw_headers if h[0].lower() == b"set-cookie"]
        print(f"  Set-Cookie headers set: {len(cookies)}")
        
        # Verify audit chain integrity with the guest login event
        org = (await session.execute(
            select(Organisation).where(Organisation.slug == "aurora-outdoors")
        )).scalar_one()
        audit_res = await verify_audit_chain(session, org.id)
        print(f"  Audit Chain status: valid={audit_res['is_valid']}, total_events={audit_res['total_events']}")
        assert audit_res["is_valid"] is True

    print("\nPHASE 2 GUEST AUTH ACCEPTANCE CHECKS PASSED!")

if __name__ == "__main__":
    asyncio.run(main())
