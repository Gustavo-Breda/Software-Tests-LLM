"""Pydantic schemas — input validation mirrors the acceptance criteria.

US-02 (register): name 3-80, valid email, password >=8 with letter+number.
US-03 (create request): title 5-100, description 10-500, priority enum.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
from .models import RequestPriority, RequestStatus

import re


# ---------- Auth / Users ----------

class RegisterIn(BaseModel):
    name: str = Field(..., min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        # Must contain at least one letter and one number (US-02)
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("A senha deve conter ao menos uma letra e um número.")
        return v

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Nome não pode ser vazio.")
        return v.strip()


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Service Requests ----------

class RequestCreateIn(BaseModel):
    title: str = Field(..., min_length=5, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    priority: RequestPriority

    @field_validator("title", "description")
    @classmethod
    def strip_and_check(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Campo obrigatório.")
        return v


class RequestOut(BaseModel):
    id: int
    title: str
    description: str
    priority: RequestPriority
    status: RequestStatus
    created_at: datetime
    cancelled_at: Optional[datetime] = None
    owner_id: int

    class Config:
        from_attributes = True


class RequestListOut(BaseModel):
    items: List[RequestOut]
    total: int


# Forward ref fix for TokenOut
TokenOut.model_rebuild()
