from django.contrib import admin
from django.db import models


class Folder(models.Model):
    origin_id = models.IntegerField(unique=True)
    destination_id = models.IntegerField(blank=True, null=True)

    parent_origin_id = models.IntegerField(blank=True, null=True)
    parent_destination_id = models.IntegerField(blank=True, null=True)

    created_dt = models.DateTimeField(auto_now_add=True)

    class Admin(admin.ModelAdmin):
        list_display = ('origin_id', 'parent_origin_id', 'destination_id', 'parent_destination_id', 'created_dt')


class Storage(models.Model):
    origin_id = models.IntegerField(unique=True)
    destination_id = models.IntegerField(blank=True, null=True)

    class Admin(admin.ModelAdmin):
        list_display = ('origin_id', 'destination_id')
