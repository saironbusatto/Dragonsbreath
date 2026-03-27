"""
auth.py — Verificação de tokens Clerk via JWKS (RS256)
Sem bcrypt, sem secret key local: a Clerk assina, nós verificamos.
"""
import os
import requests as _requests
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

CLERK_FRONTEND_API = os.environ.get(
    "CLERK_FRONTEND_API",
    "https://definite-firefly-91.clerk.accounts.dev",
)

_security = HTTPBearer(auto_error=False)

# Cache em memória do JWKS (reiniciado com o servidor)
_jwks_cache: dict | None = None


def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        try:
            resp = _requests.get(
                f"{CLERK_FRONTEND_API}/.well-known/jwks.json",
                timeout=5,
            )
            resp.raise_for_status()
            _jwks_cache = resp.json()
            print(f"[AUTH] JWKS carregado do Clerk ({len(_jwks_cache.get('keys', []))} chave(s))")
        except Exception as e:
            print(f"[AUTH] Falha ao carregar JWKS: {e}")
            _jwks_cache = {"keys": []}
    return _jwks_cache


def _verify_clerk_token(token: str) -> dict | None:
    """Verifica um Clerk session token e retorna os claims, ou None se inválido."""
    jwks = _get_jwks()
    if not jwks.get("keys"):
        return None
    try:
        claims = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return claims
    except JWTError as e:
        print(f"[AUTH] Token inválido: {e}")
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> dict:
    """FastAPI dependency — obrigatório. Lança 401 se não autenticado."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Não autenticado")
    claims = _verify_clerk_token(credentials.credentials)
    if not claims:
        raise HTTPException(status_code=401, detail="Token Clerk inválido ou expirado")
    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="Token sem user_id")
    return {"clerk_user_id": clerk_user_id}


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> dict | None:
    """FastAPI dependency — opcional. Retorna None se não autenticado."""
    if not credentials:
        return None
    claims = _verify_clerk_token(credentials.credentials)
    if not claims:
        return None
    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        return None
    return {"clerk_user_id": clerk_user_id}
