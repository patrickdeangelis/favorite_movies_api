from typing import Optional

from django.core.exceptions import ObjectDoesNotExist
from imdb import IMDb

from .models import Movie
from .schemas import MovieDetailsSchema


class MovieNotDetailedException(Exception):
    pass


class OnlySupportMovieException(Exception):
    pass


def get_movie_detailed(imdb_id: str, *, verify_detailed=False) -> Optional[Movie]:
    movie = None
    try:
        movie = Movie.objects.get(imdb_id=imdb_id)
        if verify_detailed and not movie.rating:
            raise MovieNotDetailedException

    except (ObjectDoesNotExist, MovieNotDetailedException):
        imdb_api = IMDb()
        api_movie = imdb_api.get_movie(imdb_id)
        if not api_movie:
            return None

        if api_movie["kind"] != "movie":
            raise OnlySupportMovieException

        movie_detail = MovieDetailsSchema(
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

        movie = Movie(**movie_detail.dict())
        if movie:
            Movie.objects.filter(imdb_id=imdb_id).update(**movie_detail.dict())
        else:
            movie.save()

    return movie
