"""
Testes para auth.py — verificação de tokens Clerk via JWKS (RS256).
Usa mocks para isolar chamadas HTTP e operações JWT.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import auth


# ── _get_jwks ─────────────────────────────────────────────────────────────────

def test_get_jwks_returns_keys_on_success():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"keys": [{"kid": "key1", "kty": "RSA"}]}
    mock_resp.raise_for_status.return_value = None

    with patch("auth._requests.get", return_value=mock_resp):
        auth._jwks_cache = None  # reset cache
        jwks = auth._get_jwks()

    assert "keys" in jwks
    assert len(jwks["keys"]) == 1


def test_get_jwks_returns_empty_keys_on_network_failure():
    with patch("auth._requests.get", side_effect=Exception("connection refused")):
        auth._jwks_cache = None
        jwks = auth._get_jwks()

    assert jwks == {"keys": []}


def test_get_jwks_uses_cache_on_second_call():
    auth._jwks_cache = {"keys": [{"kid": "cached"}]}
    with patch("auth._requests.get") as mock_get:
        jwks = auth._get_jwks()
        mock_get.assert_not_called()

    assert jwks["keys"][0]["kid"] == "cached"


# ── _verify_clerk_token ───────────────────────────────────────────────────────

def test_verify_clerk_token_returns_claims_on_valid_token():
    fake_claims = {"sub": "user_abc123", "exp": 9999999999}
    auth._jwks_cache = {"keys": [{"kid": "k1"}]}

    with patch("auth.jwt.decode", return_value=fake_claims):
        result = auth._verify_clerk_token("valid.jwt.token")

    assert result == fake_claims


def test_verify_clerk_token_returns_none_on_invalid_token():
    from jose import JWTError
    auth._jwks_cache = {"keys": [{"kid": "k1"}]}

    with patch("auth.jwt.decode", side_effect=JWTError("bad token")):
        result = auth._verify_clerk_token("invalid.token")

    assert result is None


def test_verify_clerk_token_returns_none_when_no_keys():
    auth._jwks_cache = {"keys": []}
    result = auth._verify_clerk_token("any.token")
    assert result is None


# ── get_current_user ──────────────────────────────────────────────────────────

def test_get_current_user_returns_user_id_on_valid_token():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid.token")
    with patch("auth._verify_clerk_token", return_value={"sub": "user_123"}):
        user = auth.get_current_user(creds)
    assert user == {"clerk_user_id": "user_123"}


def test_get_current_user_raises_401_when_no_credentials():
    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(None)
    assert exc_info.value.status_code == 401


def test_get_current_user_raises_401_on_invalid_token():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token")
    with patch("auth._verify_clerk_token", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            auth.get_current_user(creds)
    assert exc_info.value.status_code == 401


def test_get_current_user_raises_401_when_token_has_no_sub():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token.no.sub")
    with patch("auth._verify_clerk_token", return_value={"exp": 9999}):
        with pytest.raises(HTTPException) as exc_info:
            auth.get_current_user(creds)
    assert exc_info.value.status_code == 401
    assert "user_id" in exc_info.value.detail


# ── get_optional_user ─────────────────────────────────────────────────────────

def test_get_optional_user_returns_none_when_no_credentials():
    result = auth.get_optional_user(None)
    assert result is None


def test_get_optional_user_returns_none_on_invalid_token():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token")
    with patch("auth._verify_clerk_token", return_value=None):
        result = auth.get_optional_user(creds)
    assert result is None


def test_get_optional_user_returns_user_on_valid_token():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid.token")
    with patch("auth._verify_clerk_token", return_value={"sub": "user_456"}):
        result = auth.get_optional_user(creds)
    assert result == {"clerk_user_id": "user_456"}


def test_get_optional_user_returns_none_when_token_has_no_sub():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token.no.sub")
    with patch("auth._verify_clerk_token", return_value={"exp": 9999}):
        result = auth.get_optional_user(creds)
    assert result is None
