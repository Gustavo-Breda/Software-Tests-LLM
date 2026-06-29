"""Auth router — US-01 (login + lockout) and US-02 (register)."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import User
from ..schemas import RegisterIn, LoginIn, TokenOut, UserOut
from ..security import (
    hash_password, verify_password, create_access_token,
    MAX_FAILED_ATTEMPTS, LOCKOUT_SECONDS,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------- US-02: Register ----------------
@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        # US-02: reject duplicate email
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado.",
        )
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------------- US-01: Login + lockout ----------------
@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    INVALID_CREDS = "E-mail ou senha inválidos."
    now = datetime.utcnow()

    user = db.query(User).filter(User.email == payload.email).first()

    # If the user exists and is currently locked, refuse without checking password.
    # Wording is specific so tests can assert the lockout branch.
    if user and user.locked_until and user.locked_until > now:
        retry_after = int((user.locked_until - now).total_seconds()) + 1
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Conta bloqueada. Tente novamente em {retry_after} segundos.",
            headers={"Retry-After": str(retry_after)},
        )

    # Treat non-existent email and wrong password identically (no enumeration).
    # We still increment the counter when the user exists so the lockout works.
    if not user or not verify_password(payload.password, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = now + timedelta(seconds=LOCKOUT_SECONDS)
                user.failed_login_attempts = 0  # counter resets after lock starts
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDS,
        )

    # Success — clear counters and issue token.
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    token = create_access_token(subject=str(user.id))
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)) -> User:
    return current
