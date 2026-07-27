"""Google OAuth service for OmniDrive - handles Google Drive authentication flow."""

import secrets
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

import httpx
import keyring
from cachetools import TTLCache

from config import get_config


# OAuth state cache with 10-minute TTL
_oauth_state_cache = TTLCache(maxsize=100, ttl=600)


@dataclass
class OAuthStateData:
    """Data stored with OAuth state parameter."""
    redirect_uri: str
    created_at: float


@dataclass
class TokenResponse:
    """OAuth token response from Google."""
    access_token: str
    refresh_token: Optional[str]
    expires_in: int
    token_type: str
    scope: str


@dataclass
class UserInfo:
    """Google user info response."""
    id: str
    email: str
    name: str
    picture: Optional[str] = None


class GoogleOAuthError(Exception):
    """Google OAuth related errors."""
    pass


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
    _oauth_state_cache[state] = OAuthStateData(
        redirect_uri=redirect_uri,
        created_at=time.time()
    )

    params = {
        "client_id": google_config.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(google_config.scopes),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }

    auth_url = f"{google_config.auth_uri}?{urlencode(params)}"
    return auth_url, state


def validate_state(state: str) -> Optional[str]:
    """
    Validate OAuth state and return associated redirect URI.

    Returns:
        Redirect URI if state is valid, None otherwise
    """
    state_data = _oauth_state_cache.get(state)
    if not state_data:
        return None

    # Remove state after use (one-time use)
    _oauth_state_cache.pop(state, None)
    return state_data.redirect_uri


async def exchange_code_for_tokens(code: str, redirect_uri: str) -> TokenResponse:
    """
    Exchange authorization code for access and refresh tokens.

    Args:
        code: Authorization code from Google
        redirect_uri: Must match the redirect URI used in authorization request

    Returns:
        TokenResponse with access token, refresh token, and metadata
    """
    config = get_config()
    google_config = config.google_oauth

    data = {
        "code": code,
        "client_id": google_config.client_id,
        "client_secret": google_config.client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(google_config.token_uri, data=data)

        if response.status_code != 200:
            error_data = response.json()
            raise GoogleOAuthError(
                f"Token exchange failed: {error_data.get('error_description', 'Unknown error')}"
            )

        token_data = response.json()

        return TokenResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_in=token_data["expires_in"],
            token_type=token_data["token_type"],
            scope=token_data.get("scope", ""),
        )


async def get_user_info(access_token: str) -> UserInfo:
    """
    Fetch user information from Google using access token.

    Args:
        access_token: Valid Google access token

    Returns:
        UserInfo with user's Google account details
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if response.status_code != 200:
            raise GoogleOAuthError("Failed to fetch user info from Google")

        user_data = response.json()

        return UserInfo(
            id=user_data["sub"],
            email=user_data["email"],
            name=user_data.get("name", user_data["email"]),
            picture=user_data.get("picture"),
        )


async def refresh_access_token(refresh_token: str) -> TokenResponse:
    """
    Refresh an expired access token using refresh token.

    Args:
        refresh_token: Valid Google refresh token

    Returns:
        New TokenResponse with fresh access token
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
        response = await client.post(google_config.token_uri, data=data)

        if response.status_code != 200:
            error_data = response.json()
            raise GoogleOAuthError(
                f"Token refresh failed: {error_data.get('error_description', 'Unknown error')}"
            )

        token_data = response.json()

        return TokenResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", refresh_token),
            expires_in=token_data["expires_in"],
            token_type=token_data["token_type"],
            scope=token_data.get("scope", ""),
        )


def get_keyring_key(google_user_id: str) -> str:
    """Generate keyring key for storing Google refresh token."""
    return f"omnidrive:google:{google_user_id}"


def store_refresh_token(keyring_key: str, refresh_token: str) -> None:
    """Store refresh token in OS credential store."""
    keyring.set_password("OmniDrive", keyring_key, refresh_token)


def get_refresh_token(keyring_key: str) -> Optional[str]:
    """Retrieve refresh token from OS credential store."""
    return keyring.get_password("OmniDrive", keyring_key)


def delete_refresh_token(keyring_key: str) -> None:
    """Delete refresh token from OS credential store."""
    try:
        keyring.delete_password("OmniDrive", keyring_key)
    except keyring.errors.PasswordDeleteError:
        pass  # Token already deleted or doesn't exist