from typing import List
from datetime import datetime
import json

from pydantic import Field
import jwt

from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ObjectDoesNotExist
from ninja import NinjaAPI
from ninja.orm import create_schema
from ninja.errors import HttpError
from ninja.security import HttpBearer
from ninja.responses import codes_4xx
from imdb import IMDb

from django.conf.global_settings import SECRET_KEY
from .models import User, Movie
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
    MovieSchema,
    MovieDetailsSchema,
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
    return "entrou | ESTA ROTA SERÁ DESATIVADA"


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
        "iat": datetime.utcnow(),
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


# add movies search
@api.get("/movies", response={200: List[MovieSchema], 400: MessageResponseSchema})
def find_movies(request, name=""):
    if not name:
        return []

    try:
        movies = Movie.objects.filter(title__icontains=name)
        if movies and movies.count() >= 10:
            return [MovieSchema(**m.__dict__) for m in movies]

        imdb_api = IMDb()
        movies = imdb_api.search_movie(name)
        movies_dict = []
        for m in movies:
            try:
                movie_schema = MovieSchema(
                    title=m["title"],
                    kind=m["kind"],
                    year=m["year"],
                    cover_url=m["full-size cover url"],
                    imdb_id=m.getID(),
                )
                if movie_schema.kind != "movie":
                    # we only support movie
                    continue

                movies_dict.append(movie_schema)
                db_movie = Movie(**movie_schema.dict())
                db_movie.save()
            except KeyError:
                continue

        return movies_dict
    except Exception:
        return 400, MessageResponseSchema(
            message="We had a problem, it's not was possible to find the movie"
        )


@api.get(
    "/movies/{imdb_id}", response={200: MovieDetailsSchema, 400: MessageResponseSchema}
)
def get_movie(request, imdb_id: str):
    try:
        db_movie = Movie.objects.get(imdb_id=imdb_id)
        if db_movie and db_movie.rating:
            return MovieDetailsSchema(**db_movie.__dict__)

        imdb_api = IMDb()
        movie = imdb_api.get_movie(imdb_id)

        if movie["kind"] != "movie":
            return 400, MessageResponseSchema(message="We only support movies")

        movie_detail = MovieDetailsSchema(
            title=movie["title"],
            kind=movie["kind"],
            year=movie["year"],
            cover_url=movie["full-size cover url"],
            rating=movie["rating"],
            genres=movie["genre"],
            directors=[d["name"] for d in movie["director"]],
            synopsis=movie["synopsis"][0],
            imdb_id=movie.getID(),
        )

        if db_movie:
            Movie.objects.filter(imdb_id=imdb_id).update(**movie_detail.dict())
        else:
            db_movie = Movie(**movie_detail.dict())
            db_movie.save()

        return movie_detail
    except ObjectDoesNotExist:
        return MessageResponseSchema(message="Movie not found")
    except Exception:
        return 400, MessageResponseSchema(
            message="We had a problem, it's not was possible to get the movie"
        )
