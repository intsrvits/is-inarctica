from django.contrib import admin
from django.db import models


class LogMigration(models.Model):
    """Модель дискового хранилища"""
    cloud_id = models.IntegerField("ID на облаке", unique=True)
    box_id = models.IntegerField("ID на коробке", blank=True, null=True)

    dest = models.CharField("Назначение", blank=True, null=True)

    is_synced = models.BooleanField("Запись синхронизирована", default=False)

    class Admin(admin.ModelAdmin):
        list_display = ("cloud_id", "box_id", "dest", "is_synced")


class BlogPostsUpdating(models.Model):
    """"""
    success = models.BooleanField(default=False),
    id_was = models.IntegerField("ID которое было на коробке", blank=True, null=True)
    id_become = models.IntegerField("ID которое стало на коробке", unique=True)
    cloud_id = models.IntegerField("ID которое есть на облаке", blank=True, null=True)

    class Admin(admin.ModelAdmin):
        list_display = ("success", "id_was", "id_become", "cloud_id")
