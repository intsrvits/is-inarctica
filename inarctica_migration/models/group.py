from django.contrib import admin
from django.db import models


class Group(models.Model):
    origin_id = models.IntegerField(unique=True)
    destination_id = models.IntegerField(blank=True, null=True)

    created_dt = models.DateTimeField(auto_now_add=True)
    blogposts_cnt = models.IntegerField(blank=True, null=True)

    class Admin(admin.ModelAdmin):
        list_display = ('origin_id', 'destination_id', 'created_dt', 'blogposts_cnt')
