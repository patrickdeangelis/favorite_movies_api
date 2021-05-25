from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    password = models.EmailField(max_length=100)
    recovery_question = models.CharField(max_length=100)
    recovery_answer = models.CharField(max_length=100)

