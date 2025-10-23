from django.contrib import admin
from django.db import models


class TaskMigration(models.Model):
    """Модель переноса задач"""
    cloud_id = models.IntegerField("ID на облаке", unique=True)
    box_id = models.IntegerField("ID на коробке", blank=True, null=True)

    box_group_id = models.IntegerField("ID группы на коробке", blank=True, null=True)
    group_is_sync = models.BooleanField("Группа синхронизована", default=False)

    cloud_parent_id = models.IntegerField("ID родительской задачи на коробке", blank=True, null=True)
    box_parent_id = models.IntegerField("ID родительской задачи на коробке", blank=True, null=True)

    is_synced = models.BooleanField("Запись синхронизирована", default=False)

    class Admin(admin.ModelAdmin):
        list_display = ("cloud_id", "box_id", "box_group_id", "group_is_sync", "cloud_parent_id", "box_parent_id", "is_synced")


class StageMigration(models.Model):
    """"""

    cloud_id = models.IntegerField("ID на облаке", unique=True)
    box_id = models.IntegerField("ID на коробке", blank=True, null=True)

    cloud_group_id = models.IntegerField("ID группы на облаке", blank=True, null=True)
    box_group_id = models.IntegerField("ID группы на коробке", blank=True, null=True)

    is_synced = models.BooleanField("Стадия синхронизирована", default=False)

    class Admin(admin.ModelAdmin):
        list_display = ("cloud_id", "box_id", "cloud_group_id", "box_group_id")
