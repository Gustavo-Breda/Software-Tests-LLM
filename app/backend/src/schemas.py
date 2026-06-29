import re

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .models import *


class RegisterIn(BaseModel):
    name: str = Field(..., min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("A senha deve conter ao menos uma letra e um número.")
        return v

    @field_validator("name")
    @classmethod
    def name_stripped(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Nome não pode ser vazio.")
        return v.strip()


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RequestCreateIn(BaseModel):
    title: str = Field(..., min_length=5, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    priority: RequestPriority

    @field_validator("title", "description")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Campo obrigatório.")
        return v


class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    priority: RequestPriority
    status: RequestStatus
    created_at: datetime
    cancelled_at: datetime | None = None
    owner_id: int


class RequestListOut(BaseModel):
    items: list[RequestOut]
    total: int
