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
from .models import User, Movie, SavedMovie
from .services import get_movie_detailed, OnlySupportMovieException
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
            decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return decoded_token
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
    response={201: TokenSchema, frozenset({403, 404}): MessageResponseSchema},
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
        "token": jwt.encode(
            {"user_id": user.id, "iat": datetime.utcnow()},
            SECRET_KEY,
            algorithm="HS256",
        ),
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


@api.get("/movies", response={200: List[MovieSchema], 400: MessageResponseSchema})
def find_movies(request, name="", saved=False):
    try:
        if saved:
            user_id = request.auth["user_id"]
            user = User.objects.get(pk=user_id)
            movies_id = list(
                SavedMovie.objects.filter(user=user).values_list("movie_id", flat=True)
            )
            movies = Movie.objects.filter(pk__in=movies_id)
            if name:
                movies = movies.filter(title__icontains=name)

            return [MovieSchema(**m.__dict__) for m in movies]

        if not name:
            return []

        movies = Movie.objects.filter(title__icontains=name)
        if movies:
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
    "/movies/{imdb_id}",
    response={200: MovieDetailsSchema, frozenset({400, 404}): MessageResponseSchema},
)
def get_movie(request, imdb_id: str):
    try:
        db_movie = get_movie_detailed(imdb_id, verify_detailed=True)
        if db_movie:
            return MovieDetailsSchema(**db_movie.__dict__)

        return 404, MessageResponseSchema(message="Movie not found")
    except OnlySupportMovieException:
        return 400, MessageResponseSchema(message="We only support movies")
    except Exception as err:
        print(err)
        return 400, MessageResponseSchema(
            message="We had a problem, it's not was possible to get the movie"
        )


@api.post(
    "/movies/{imdb_id}/save",
    response={frozenset({200, 400, 404}): MessageResponseSchema},
)
def save_movie(request, imdb_id: str):
    try:
        user_id = request.auth["user_id"]
        user = User.objects.get(pk=user_id)
        movie = get_movie_detailed(imdb_id)
        if not movie:
            return 404, MessageResponseSchema(message="Movie not found")

        saved_movie = SavedMovie(user=user, movie=movie)
        saved_movie.save()

        return MessageResponseSchema(message="Movie saved to your list")
    except OnlySupportMovieException:
        return 400, MessageResponseSchema(message="We only support movies")
    except Exception:
        return 400, MessageResponseSchema(
            message="We had a problem, it's not was possible to get the movie"
        )
