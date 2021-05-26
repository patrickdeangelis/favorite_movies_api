from datetime import datetime

from pydantic import Field
import jwt

from django.contrib.auth.hashers import make_password, check_password
from ninja import NinjaAPI
from ninja.orm import create_schema
from ninja.errors import HttpError
from ninja.security import HttpBearer
from ninja.responses import codes_4xx

from django.conf.global_settings import SECRET_KEY
from .models import User
from .schemas import (
    BaseCreateUserSchema,
    CreateUserSchema,
    PublicUserSchema,
    UserCredentialsSchema,
    TokenSchema,
    MessageResponseSchema,
    RecoveryPasswordRequestSchema,
    GetRecoveryQuestionRequestSchema,
    RecoveryQuestionSchema,
)


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return token
        except jwt.ExpiredSignatureError:
            pass


api = NinjaAPI(title="Favorite Movies API", version="1.0.0", auth=AuthBearer())


@api.get("/test_auth")
def auth_route(request):
    return "entrou"


@api.post("/users", response=PublicUserSchema, auth=None)
def create_user(request, user: CreateUserSchema):
    created_user = User(**{**user.dict(), "password": make_password(user.password)})
    created_user.save()
    return PublicUserSchema(**created_user.__dict__)


@api.post(
    "/auth/generate-token",
    auth=None,
    response={201: TokenSchema, frozenset({401, 403}): MessageResponseSchema},
)
def generate_token(request, credentials: UserCredentialsSchema):
    users = User.objects.filter(email=credentials.email)
    if not users:
        return 404, MessageResponseSchema(message="User not found")

    user = users[0]
    is_authenticated = check_password(credentials.password, user.password)

    if not is_authenticated:
        return 403, MessageResponseSchema(message="Invalid password")

    return 201, {
        "token": jwt.encode({"user_id": user.id}, SECRET_KEY, algorithm="HS256"),
        "iat": datetime.utcnow()
    }


@api.post(
    "/auth/recovery-password",
    auth=None,
    response={frozenset({200, 400, 404}): MessageResponseSchema},
)
def recovery_password(request, payload: RecoveryPasswordRequestSchema):
    users = User.objects.filter(email=payload.email)
    if not users:
        return 404, MessageResponseSchema(message="User not found")

    user = users[0]
    if user.recovery_answer != payload.recovery_answer:
        return 400, MessageResponseSchema(message="Wrong answer")

    user.password = make_password(payload.new_password)
    user.save()

    return 200, MessageResponseSchema(message="Password reseted")


@api.get(
    "/auth/get-recovery-question",
    auth=None,
    response={200: RecoveryQuestionSchema, 404: MessageResponseSchema},
)
def get_recovery_question(request, payload: GetRecoveryQuestionRequestSchema):
    users = User.objects.filter(email=payload.email)
    if not users:
        return 404, MessageResponseSchema(message="User not found")

    user = users[0]

    return RecoveryQuestionSchema(recovery_question=user.recovery_question)
