from pydantic import Field

from ninja import Schema
from ninja.orm import create_schema

from .models import User

BaseCreateUserScheme = create_schema(User, exclude=["id"])
PublicUserScheme = create_schema(User, fields=["name", "email"])
UserCredentialsScheme = create_schema(User, fields=["email", "password"])


class RecoveryPasswordRequestScheme(Schema):
    email: str
    recovery_answer: str
    new_password: str = Field(min_length=8)


class CreateUserScheme(BaseCreateUserScheme):
    password: str = Field(min_length=8)


class TokenScheme(Schema):
    token: str


class MessageResponseScheme(Schema):
    message: str
