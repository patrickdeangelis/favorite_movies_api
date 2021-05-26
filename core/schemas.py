from pydantic import Field

from ninja import Schema
from ninja.orm import create_schema

from .models import User

BaseCreateUserSchema = create_schema(User, exclude=["id"])
PublicUserSchema = create_schema(User, fields=["name", "email"])
UserCredentialsSchema = create_schema(User, fields=["email", "password"])
GetRecoveryQuestionRequestSchema = create_schema(User, fields=["email"])
RecoveryQuestionSchema = create_schema(User, fields=["recovery_question"])


class RecoveryPasswordRequestSchema(Schema):
    email: str
    recovery_answer: str
    new_password: str = Field(min_length=8)


class CreateUserSchema(BaseCreateUserSchema):
    password: str = Field(min_length=8)


class TokenSchema(Schema):
    token: str


class MessageResponseSchema(Schema):
    message: str
