"""FastAPI dependencies: DB session and authenticated user resolution."""
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import User
from .security import decode_access_token


# tokenUrl is purely informational here (clients send the token directly).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise creds_exc
    subject = decode_access_token(token)
    if not subject:
        raise creds_exc
    try:
        user_id = int(subject)
    except ValueError:
        raise creds_exc
    user = db.get(User, user_id)
    if not user:
        raise creds_exc
    return user
