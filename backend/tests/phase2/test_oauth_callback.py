import pytest
from unittest.mock import patch, MagicMock

def test_google_oauth_callback_success():
    """Test successful Google OAuth callback."""
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        from app.db.session import SessionLocal
        from app.models.user import User, EmailVerification
        from app.models.google_drive import GoogleOAuthToken

        client = TestClient(app)
        db = SessionLocal()

        # Clean up any existing test user
        existing_user = db.query(User).filter(User.email == "oauthcallback@example.com").first()
        if existing_user:
            db.delete(existing_user)
            db.commit()

        with patch('app.services.email_service.email_service.send_verification_email') as mock_send:
            mock_send.return_value = True
            register_response = client.post(
                "/api/v1/register",
                json={
                    "email": "oauthcallback@example.com",
                    "password": "securepassword123"
                }
            )
            assert register_response.status_code == 201
            user_id = register_response.json()["id"]

            from app.models.user import EmailVerification
            verification = db.query(EmailVerification).filter(EmailVerification.user_id == user_id).first()
            if verification:
                client.get(f"/api/v1/verify-email?token={verification.token}")

            login_response = client.post(
                "/api/v1/login",
                json={
                    "email": "oauthcallback@example.com",
                    "password": "securepassword123"
                }
            )
            assert login_response.status_code == 200
            access_token = login_response.json()["access_token"]

            # Mock the OAuth token exchange
            token_data = {
                "access_token": "oauth_access_token",
                "refresh_token": "oauth_refresh_token",
                "expires_at": "2026-12-31T23:59:59Z"
            }

            with patch('app.api.v1.google_drive.GoogleDriveService.exchange_code_for_tokens') as mock_exchange:
                mock_exchange.return_value = token_data

                # Simulate OAuth callback with authorization code
                response = client.get(
                    "/api/v1/google/oauth/callback?code=auth_code_123&state=test_state",
                    headers={"Authorization": f"Bearer {access_token}"}
                )

                # These assertions will pass once endpoint is implemented
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Google Drive connected successfully"

                # Verify tokens were stored in database
                stored_token = db.query(GoogleOAuthToken).filter(GoogleOAuthToken.user_id == user_id).first()
                assert stored_token is not None
                assert stored_token.access_token == "oauth_access_token"
                assert stored_token.refresh_token == "oauth_refresh_token"

                # Clean up
                if stored_token:
                    db.delete(stored_token)
                    db.commit()

        # Clean up test user
        test_user = db.query(User).filter(User.email == "oauthcallback@example.com").first()
        if test_user:
            db.delete(test_user)
            db.commit()

        db.close()
    except (ImportError, AttributeError):
        assert False, "Application not implemented yet - endpoint /api/v1/google/oauth/callback not available"


def test_google_oauth_callback_missing_code():
    """Test Google OAuth callback fails with missing authorization code."""
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        from app.db.session import SessionLocal
        from app.models.user import User, EmailVerification

        client = TestClient(app)
        db = SessionLocal()

        # Clean up any existing test user
        existing_user = db.query(User).filter(User.email == "oauthmissing@example.com").first()
        if existing_user:
            db.delete(existing_user)
            db.commit()

        with patch('app.services.email_service.email_service.send_verification_email') as mock_send:
            mock_send.return_value = True
            register_response = client.post(
                "/api/v1/register",
                json={
                    "email": "oauthmissing@example.com",
                    "password": "securepassword123"
                }
            )
            assert register_response.status_code == 201
            user_id = register_response.json()["id"]

            from app.models.user import EmailVerification
            verification = db.query(EmailVerification).filter(EmailVerification.user_id == user_id).first()
            if verification:
                client.get(f"/api/v1/verify-email?token={verification.token}")

            login_response = client.post(
                "/api/v1/login",
                json={
                    "email": "oauthmissing@example.com",
                    "password": "securepassword123"
                }
            )
            assert login_response.status_code == 200
            access_token = login_response.json()["access_token"]

            # Call OAuth callback without code parameter
            response = client.get(
                "/api/v1/google/oauth/callback",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            # These assertions will pass once endpoint is implemented
            assert response.status_code == 422  # FastAPI validation error for missing required query param
            assert "code" in response.json()["detail"][0]["loc"]  # Check that the error is about the code parameter

        # Clean up test user
        test_user = db.query(User).filter(User.email == "oauthmissing@example.com").first()
        if test_user:
            db.delete(test_user)
            db.commit()

        db.close()
    except (ImportError, AttributeError):
        assert False, "Application not implemented yet - endpoint /api/v1/google/oauth/callback not available"


def test_google_oauth_callback_invalid_code():
    """Test Google OAuth callback fails with invalid authorization code."""
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        from app.db.session import SessionLocal
        from app.models.user import User, EmailVerification

        client = TestClient(app)
        db = SessionLocal()

        # Clean up any existing test user
        existing_user = db.query(User).filter(User.email == "oauthinvalid@example.com").first()
        if existing_user:
            db.delete(existing_user)
            db.commit()

        with patch('app.services.email_service.email_service.send_verification_email') as mock_send:
            mock_send.return_value = True
            register_response = client.post(
                "/api/v1/register",
                json={
                    "email": "oauthinvalid@example.com",
                    "password": "securepassword123"
                }
            )
            assert register_response.status_code == 201
            user_id = register_response.json()["id"]

            from app.models.user import EmailVerification
            verification = db.query(EmailVerification).filter(EmailVerification.user_id == user_id).first()
            if verification:
                client.get(f"/api/v1/verify-email?token={verification.token}")

            login_response = client.post(
                "/api/v1/login",
                json={
                    "email": "oauthinvalid@example.com",
                    "password": "securepassword123"
                }
            )
            assert login_response.status_code == 200
            access_token = login_response.json()["access_token"]

            # Mock the OAuth token exchange to raise an error
            with patch('app.api.v1.google_drive.GoogleDriveService.exchange_code_for_tokens') as mock_exchange:
                mock_exchange.side_effect = Exception("Invalid authorization code")

                response = client.get(
                    "/api/v1/google/oauth/callback?code=invalid_code&state=test_state",
                    headers={"Authorization": f"Bearer {access_token}"}
                )

                # These assertions will pass once endpoint is implemented
                assert response.status_code == 400
                assert "Failed to authenticate with Google Drive" in response.json()["detail"]

        # Clean up test user
        test_user = db.query(User).filter(User.email == "oauthinvalid@example.com").first()
        if test_user:
            db.delete(test_user)
            db.commit()

        db.close()
    except (ImportError, AttributeError):
        assert False, "Application not implemented yet - endpoint /api/v1/google/oauth/callback not available"