"""SQLAlchemy models for the PoC.

Two tables: users and service_requests.
The ``failed_login_attempts`` and ``locked_until`` columns on User implement
the lockout policy from US-01 (5 consecutive failures → 60s lock).
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
import enum

from .database import Base


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

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Lockout policy (US-01)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    requests = relationship("ServiceRequest", back_populates="owner")


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    priority = Column(SAEnum(RequestPriority), nullable=False)
    status = Column(SAEnum(RequestStatus), default=RequestStatus.ABERTA, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    cancelled_at = Column(DateTime, nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="requests")
