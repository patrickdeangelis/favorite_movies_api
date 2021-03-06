from typing import List, Optional

from django.contrib.auth.hashers import make_password
from pydantic import Field
from ninja import Schema
from ninja.orm import create_schema
from imdb import Movie

from .models import User

BaseCreateUserSchema = create_schema(User, exclude=["id"])
PublicUserSchema = create_schema(User, fields=["name", "email"])
UserSchema = create_schema(User, exclude=["id", "password", "recovery_answer"])
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


class MovieSchema(Schema):
    title: str
    kind: str
    year: int
    cover_url: str
    imdb_id: str


class MovieDetailsSchema(MovieSchema):
    rating: float
    genres: List[str]
    directors: List[str]
    synopsis: str

    def from_api_movie(cls, api_movie: Movie) -> "MovieDetailsSchema":
        return MovieDetailsSchema(
            title=api_movie["title"],
            kind=api_movie["kind"],
            year=api_movie["year"],
            cover_url=api_movie["full-size cover url"],
            rating=api_movie["rating"],
            genres=api_movie["genre"],
            directors=[d["name"] for d in api_movie["director"]],
            synopsis=api_movie["synopsis"][0],
            imdb_id=api_movie.getID(),
        )


class UpdateUserRequestSchema(Schema):
    name: Optional[str]
    email: Optional[str]
    password: Optional[str]
    recovery_question: Optional[str]
    recovery_answer: Optional[str]

    def get_not_none_fields_dict(self):
        return {k: v for k, v in self.dict().items() if v}

    def encrypt_password(self):
        self.password = make_password(self.password)
