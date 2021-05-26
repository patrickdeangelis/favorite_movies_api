from django.contrib.auth.hashers import make_password, check_password

from pydantic import Field
import jwt

from ninja import NinjaAPI
from ninja.orm import create_schema
from ninja.errors import HttpError
from ninja.security import HttpBearer
from ninja.responses import codes_4xx

from django.conf.global_settings import SECRET_KEY
from .models import User
from .schemas import (
    BaseCreateUserScheme,
    CreateUserScheme,
    PublicUserScheme,
    UserCredentialsScheme,
    TokenScheme,
    MessageResponseScheme,
    RecoveryPasswordRequestScheme,
)


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return token
        except jwt.ExpiredSignatureError:
            pass


api = NinjaAPI(version="1.0.0", auth=AuthBearer())


@api.get("/test_auth")
def auth_route(request):
    return "entrou"


@api.post("/users", response=PublicUserScheme, auth=None)
def create_user(request, user: CreateUserScheme) -> PublicUserScheme:
    created_user = User(**{**user.dict(), "password": make_password(user.password)})
    created_user.save()
    return PublicUserScheme(**created_user.__dict__)


@api.post(
    "/auth/generate-token",
    auth=None,
    response={201: TokenScheme, frozenset({401, 403}): MessageResponseScheme},
)
def generate_token(request, credentials: UserCredentialsScheme):
    users = User.objects.filter(email=credentials.email)
    if not users:
        return 404, MessageResponseScheme(message="User not found")

    user = users[0]
    is_authenticated = check_password(credentials.password, user.password)

    if not is_authenticated:
        return 403, MessageResponseScheme(message="Invalid password")

    return 201, {
        "token": jwt.encode({"user_id": user.id}, SECRET_KEY, algorithm="HS256")
    }


@api.post(
    "/auth/recovery-password",
    response={frozenset({200, 400, 404}): MessageResponseScheme},
)
def recovery_password(request, payload: RecoveryPasswordRequestScheme):
    users = User.objects.filter(email=payload.email)
    if not users:
        return 404, MessageResponseScheme(message="User not found")

    user = users[0]
    if user.recovery_answer != payload.recovery_answer:
        return 400, MessageResponseScheme(message="Wrong answer")

    user.password = make_password(payload.new_password)
    user.save()

    return 200, MessageResponseScheme(message="Password reseted")
