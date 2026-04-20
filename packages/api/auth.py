from __future__ import annotations

import os
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=True)

TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"
TEST_USER_ID = os.environ.get("TEST_USER_ID", "00000000-0000-0000-0000-000000000001")


def _decode_supabase_token(token: str) -> dict:
    unverified_header = jwt.get_unverified_header(token)
    algorithm = unverified_header.get("alg", "")

    # Supabase projects with asymmetric signing (RS256/ES256) must be verified via JWKS.
    if algorithm in {"RS256", "ES256"}:
        supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        if not supabase_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server misconfiguration: SUPABASE_URL not set",
            )
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        jwk_client = jwt.PyJWKClient(jwks_url)
        signing_key = jwk_client.get_signing_key_from_jwt(token).key
        expected_issuer = f"{supabase_url}/auth/v1"
        return jwt.decode(
            token,
            signing_key,
            algorithms=[algorithm],
            issuer=expected_issuer,
            options={"verify_aud": False},
        )

    # Legacy HS256 projects can still verify using SUPABASE_JWT_SECRET.
    secret = os.environ.get("SUPABASE_JWT_SECRET", "")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfiguration: SUPABASE_JWT_SECRET not set",
        )
    return jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> str:
    token = credentials.credentials

    if TEST_MODE:
        return TEST_USER_ID

    try:
        payload = _decode_supabase_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return str(user_id)


CurrentUser = Annotated[str, Depends(get_current_user)]
