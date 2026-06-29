from collections.abc import Iterator

from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .models import *
from .security import *
from .database import *

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise exc
    subject = decode_access_token(token)
    if not subject:
        raise exc
    try:
        user_id = int(subject)
    except ValueError:
        raise exc
    user = db.get(User, user_id)
    if not user:
        raise exc
    return user
