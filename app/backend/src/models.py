import enum

from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import *


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RequestStatus(str, enum.Enum):
    ABERTA = "aberta"
    EM_ANALISE = "em_analise"
    CANCELADA = "cancelada"
    FINALIZADA = "finalizada"


class RequestPriority(str, enum.Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    # tracks consecutive failures for the lockout policy
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None]

    requests: Mapped[list["ServiceRequest"]] = relationship(back_populates="owner")


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500))
    priority: Mapped[RequestPriority] = mapped_column(SAEnum(RequestPriority))
    status: Mapped[RequestStatus] = mapped_column(SAEnum(RequestStatus), default=RequestStatus.ABERTA)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    cancelled_at: Mapped[datetime | None]

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    owner: Mapped["User"] = relationship(back_populates="requests")
