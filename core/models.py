from django.db import models


class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, unique=True)
    password = models.EmailField(max_length=100)
    recovery_question = models.CharField(max_length=100)
    recovery_answer = models.CharField(max_length=100)


class Movie(models.Model):
    imdb_id = models.CharField(unique=True, max_length=20)
    title = models.CharField(max_length=50)
    kind = models.CharField(max_length=50)
    year = models.IntegerField()
    cover_url = models.CharField(max_length=250)
    rating = models.FloatField(null=True)
    genres = models.JSONField(null=True)
    directors = models.JSONField(null=True)
    synopsis = models.TextField(blank=True)


class SavedMovie(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
