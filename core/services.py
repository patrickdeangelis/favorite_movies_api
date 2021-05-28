from typing import Optional

from django.core.exceptions import ObjectDoesNotExist
from imdb import IMDb

from .models import Movie
from .schemas import MovieDetailsSchema


def get_movie_detailed(imdb_id: str) -> Optional[Movie]:
    try:
        movie = Movie.objects.get(imdb_id=imdb_id)
    except ObjectDoesNotExist:
        imdb_api = IMDb()
        api_movie = imdb_api.get_movie(imdb_id)
        if not api_movie:
            return None

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
        movie.save()

    return movie
