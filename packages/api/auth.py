from __future__ import annotations

import os
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=True)

TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"
TEST_USER_ID = os.environ.get("TEST_USER_ID", "00000000-0000-0000-0000-000000000001")


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> str:
    token = credentials.credentials

    if TEST_MODE:
        return TEST_USER_ID

    secret = os.environ.get("SUPABASE_JWT_SECRET", "")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfiguration: SUPABASE_JWT_SECRET not set",
        )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return str(user_id)


CurrentUser = Annotated[str, Depends(get_current_user)]
