"""Google OAuth service for OmniDrive - handles Google Drive authentication flow."""

import secrets
import time
from typing import Optional, Dict, Any
from urllib.parse import urlencode

import httpx
import keyring

from config import get_config


# Simple in-memory state cache with 10-minute TTL
_oauth_state_cache: Dict[str, Dict[str, Any]] = {}
_STATE_TTL = 600  # 10 minutes


def _cleanup_expired_states():
    """Remove expired state entries from cache."""
    now = time.time()
    expired = [state for state, data in _oauth_state_cache.items() if now - data["created_at"] > _STATE_TTL]
    for state in expired:
        del _oauth_state_cache[state]


def build_authorization_url(redirect_uri: str) -> tuple[str, str]:
    """
    Build Google OAuth authorization URL.

    Returns:
        Tuple of (auth_url, state)
    """
    config = get_config()
    google_config = config.google_oauth

    # Generate secure state parameter
    state = secrets.token_urlsafe(32)

    # Store state with redirect URI for validation later
    _cleanup_expired_states()
    _oauth_state_cache[state] = {
        "redirect_uri": redirect_uri,
        "created_at": time.time(),
    }

    params = {
        "client_id": google_config.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(google_config.scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }

    auth_url = f"{google_config.auth_uri}?{urlencode(params)}"
    return auth_url, state


def validate_state(state: str) -> Optional[str]:
    """
    Validate OAuth state parameter and return associated redirect URI.

    Returns:
        redirect_uri if valid, None if invalid or expired
    """
    _cleanup_expired_states()
    data = _oauth_state_cache.get(state)
    if data:
        return data["redirect_uri"]
    return None


async def exchange_code_for_tokens(code: str, redirect_uri: str) -> Dict[str, Any]:
    """
    Exchange authorization code for access/refresh tokens.

    Returns:
        Dict with access_token, refresh_token, expires_in, token_type, scope
    """
    config = get_config()
    google_config = config.google_oauth

    data = {
        "client_id": google_config.client_id,
        "client_secret": google_config.client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            google_config.token_uri,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error_description', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise GoogleOAuthError(f"Token exchange failed: {error_msg}")

        try:
            return response.json()
        except Exception:
            raise GoogleOAuthError("Token exchange returned invalid JSON")


async def get_user_info(access_token: str) -> Dict[str, Any]:
    """
    Get user info from Google using access token.

    Returns:
        Dict with id, email, name, picture
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise GoogleOAuthError(f"User info request failed: {error_msg}")

        try:
            return response.json()
        except Exception:
            raise GoogleOAuthError("User info response is not valid JSON")


async def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """
    Refresh access token using refresh token.

    Returns:
        Dict with access_token, expires_in, token_type, scope
    """
    config = get_config()
    google_config = config.google_oauth

    data = {
        "client_id": google_config.client_id,
        "client_secret": google_config.client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            google_config.token_uri,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error_description', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise GoogleOAuthError(f"Token refresh failed: {error_msg}")

        try:
            return response.json()
        except Exception:
            raise GoogleOAuthError("Token refresh returned invalid JSON")


def store_refresh_token(keyring_key: str, refresh_token: str) -> None:
    """Store refresh token securely in system keyring."""
    keyring.set_password("omnidrive", keyring_key, refresh_token)


def get_refresh_token(keyring_key: str) -> Optional[str]:
    """Retrieve refresh token from system keyring."""
    return keyring.get_password("omnidrive", keyring_key)


def get_keyring_key(google_user_id: str) -> str:
    """Generate keyring key for a Google user ID."""
    return f"google_drive:{google_user_id}"


class GoogleOAuthError(Exception):
    """Google OAuth related errors."""
    pass