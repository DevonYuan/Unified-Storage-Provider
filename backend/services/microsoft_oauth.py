"""Microsoft OAuth service for OmniDrive - handles OneDrive authentication flow."""

import secrets
import time
from typing import Optional, Dict, Any
from urllib.parse import urlencode

import httpx
import keyring

from config import get_config


# Simple in-memory state cache with 10-minute TTL (prefixed "ms:" to avoid collisions)
_oauth_state_cache: Dict[str, Dict[str, Any]] = {}
_STATE_TTL = 600  # 10 minutes


def _cleanup_expired_states():
    """Remove expired state entries from cache."""
    now = time.time()
    expired = [state for state, data in _oauth_state_cache.items() if now - data["created_at"] > _STATE_TTL]
    for state in expired:
        del _oauth_state_cache[state]


def build_authorization_url(redirect_uri: str, frontend_url: str = "") -> tuple[str, str]:
    """
    Build Microsoft Azure AD OAuth authorization URL.

    Returns:
        Tuple of (auth_url, state)
    """
    config = get_config()
    ms_config = config.microsoft_oauth

    # Generate secure state parameter
    state = secrets.token_urlsafe(32)

    # Store state with redirect URI and frontend URL for validation later
    _cleanup_expired_states()
    _oauth_state_cache[state] = {
        "redirect_uri": redirect_uri,
        "frontend_url": frontend_url,
        "created_at": time.time(),
    }

    params = {
        "client_id": ms_config.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(ms_config.scopes),
        "response_mode": "query",
        "state": state,
    }

    auth_url = f"{ms_config.auth_uri}?{urlencode(params)}"
    return auth_url, state


def validate_state(state: str) -> Optional[dict]:
    """
    Validate OAuth state parameter and return stored data dict.

    Returns:
        dict with redirect_uri, frontend_url if valid, None if invalid or expired
    """
    _cleanup_expired_states()
    return _oauth_state_cache.pop(state, None)


async def exchange_code_for_tokens(code: str, redirect_uri: str) -> Dict[str, Any]:
    """
    Exchange authorization code for access/refresh tokens.

    Returns:
        Dict with access_token, refresh_token, expires_in, token_type, scope
    """
    config = get_config()
    ms_config = config.microsoft_oauth

    data = {
        "client_id": ms_config.client_id,
        "client_secret": ms_config.client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            ms_config.token_uri,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error_description', error_data.get('error', 'Unknown error'))
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise MicrosoftOAuthError(
                f"Token exchange failed: {error_msg}"
            )

        try:
            return response.json()
        except Exception:
            raise MicrosoftOAuthError("Token exchange returned invalid JSON")


async def get_user_info(access_token: str) -> Dict[str, Any]:
    """
    Get user profile information from Microsoft Graph.

    Returns:
        Dict with id, displayName, mail (or userPrincipalName)
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise MicrosoftOAuthError(
                f"User info request failed: {error_msg}"
            )

        try:
            return response.json()
        except Exception:
            raise MicrosoftOAuthError("User info response is not valid JSON")


async def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """
    Refresh access token using refresh token.

    Returns:
        Dict with access_token, expires_in, token_type, scope
    """
    config = get_config()
    ms_config = config.microsoft_oauth

    data = {
        "client_id": ms_config.client_id,
        "client_secret": ms_config.client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            ms_config.token_uri,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error_description', error_data.get('error', 'Unknown error'))
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise MicrosoftOAuthError(
                f"Token refresh failed: {error_msg}"
            )

        try:
            return response.json()
        except Exception:
            raise MicrosoftOAuthError("Token refresh returned invalid JSON")


def store_refresh_token(keyring_key: str, refresh_token: str) -> None:
    """Store refresh token securely in system keyring."""
    keyring.set_password("omnidrive", keyring_key, refresh_token)


def get_refresh_token(keyring_key: str) -> Optional[str]:
    """Retrieve refresh token from system keyring."""
    return keyring.get_password("omnidrive", keyring_key)


def get_keyring_key(user_id: str) -> str:
    """Generate keyring key for a Microsoft user ID."""
    return f"onedrive:{user_id}"


class MicrosoftOAuthError(Exception):
    """Microsoft OAuth related errors."""
    pass
