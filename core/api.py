from django.contrib.auth.hashers import make_password, check_password

from pydantic import Field

from ninja import NinjaAPI, Schema
from ninja.orm import create_schema
from ninja.errors import HttpError

from .models import User

api = NinjaAPI()



@api.get("/hello")
def hello(request):
    return "Hello, world"


BaseCreateUserScheme = create_schema(User, exclude=['id'])
class CreateUserScheme(BaseCreateUserScheme):
    password: str = Field(min_length=8)

PublicUserScheme = create_schema(User, fields=['name', 'email'])
UserCredentialsScheme = create_schema(User, fields=['email', 'password'])
    


@api.post("/users")
def create_user(request, user: CreateUserScheme) -> PublicUserScheme:
    created_user = User(**{
        **user.dict(),
        "password": make_password(user.password)
    })
    created_user.save()
    return PublicUserScheme(**created_user.__dict__)

@api.get("/users")
def list_users(request):
    # TODO: REMOVE
    """
    return [
        PublicUserScheme(**user.__dict__)
        for user in User.objects.all()
    ]
    """
    return [
        BaseCreateUserScheme(**user.__dict__)
        for user in User.objects.all()
    ]

@api.post("/auth/generateToken")
def generate_token(request, credentials: UserCredentialsScheme):
    user = User.objects.filter(email=credentials.email)
    if not user:
        raise HttpError(404, "User not found")

    is_authenticated = check_password(credentials.password, user[0].password)

    if not is_authenticated:
        raise HttpError(403, "Invalid password")

    return "some_very_secure_token"

