from typing import Self

from django.contrib import admin
from django.db import models


class User(models.Model):
    origin_id = models.IntegerField(unique=True)
    destination_id = models.IntegerField(blank=True, null=True)

    created_dt = models.DateTimeField(auto_now_add=True)
    is_user_migrated = models.BooleanField(default=False)

    class Admin(admin.ModelAdmin):
        list_display = ('origin_id', 'destination_id', 'created_dt', 'is_user_migrated')

    class QuerySet(models.QuerySet):

        def already_migrated(self) -> Self:
            return self.filter(is_user_migrated=True)

    objects = QuerySet.as_manager()
