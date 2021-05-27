from django.contrib import admin

from .models import User, Movie


class UserAdmin(admin.ModelAdmin):
    pass


admin.site.register(User, UserAdmin)


class MovieAdmin(admin.ModelAdmin):
    pass


admin.site.register(Movie, MovieAdmin)
