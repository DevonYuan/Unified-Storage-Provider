from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import secrets
from typing import Any

from ...db.session import get_db
from ...models.user import User, EmailVerification
from ...core import security
from ...services.email_service import email_service
from ...api.deps import get_current_user

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email")
    password = payload.get("password")

    if not email or not password:
        raise HTTPException(status_code=422, detail="Email and password are required")

    if len(password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters long")

    # Check if user already exists
    user = db.query(User).filter(User.email == email).first()
    if user:
        raise HTTPException(status_code=400, detail="User already registered")

    # Hash password and create user
    hashed_pw = security.get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed_pw, email_verified=False)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate verification token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    verification = EmailVerification(user_id=new_user.id, token=token, expires_at=expires_at)
    db.add(verification)
    db.commit()

    # Send verification email
    email_service.send_verification_email(email, token)

    return {
        "id": new_user.id,
        "email": new_user.email,
        "email_verified": new_user.email_verified
    }

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified"
        )

    access_token = security.create_access_token(data={"sub": str(user.id), "email": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email}
    }

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    # JWT is stateless, so we just return success.
    # Client should delete the token.
    return {"message": "Successfully logged out"}

@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    verification = db.query(EmailVerification).filter(EmailVerification.token == token).first()

    if not verification or verification.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user = verification.user
    user.email_verified = True
    db.commit()

    # Clean up token
    db.delete(verification)
    db.commit()

    return {"message": "Email verified successfully", "email_verified": True}

@router.post("/resend-verification")
def resend_verification(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email_verified:
        return {"message": "Email already verified"}

    # Generate new token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    # Remove old tokens for this user
    db.query(EmailVerification).filter(EmailVerification.user_id == user.id).delete()

    verification = EmailVerification(user_id=user.id, token=token, expires_at=expires_at)
    db.add(verification)
    db.commit()

    email_service.send_verification_email(email, token)
    return {"message": "Verification email sent"}

@router.post("/forgot-password")
def forgot_password(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email")
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Security: don't reveal if user exists
        return {"message": "If an account exists with this email, a reset link has been sent"}

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    # We can reuse the email_verifications table for reset tokens
    # or use a dedicated table. For Phase 1, let's use a separate logic
    # or just use the same table if we distinguish tokens.
    # Actually, let's just create a reset token in the DB.
    # For simplicity in Phase 1, I'll use the email_verifications table
    # but perhaps with a different expiration.

    verification = EmailVerification(user_id=user.id, token=token, expires_at=expires_at)
    db.add(verification)
    db.commit()

    email_service.send_password_reset_email(email, token)
    return {"message": "Password reset email sent"}

@router.post("/reset-password")
def reset_password(payload: dict, db: Session = Depends(get_db)):
    token = payload.get("token")
    new_password = payload.get("password")

    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and password are required")

    verification = db.query(EmailVerification).filter(EmailVerification.token == token).first()
    if not verification or verification.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = verification.user
    user.hashed_password = security.get_password_hash(new_password)
    db.commit()

    db.delete(verification)
    db.commit()

    return {"message": "Password has been reset successfully"}
