from django.contrib import admin
from django.db import models


class Folder(models.Model):
    """Модель дочерней папки (дискового хранилища считается корневой папкой)"""
    cloud_id = models.IntegerField("ID на облаке", unique=True)  # Используется поле ID
    box_id = models.IntegerField("ID на коробке", blank=True, null=True)  # Используется поле ID

    parent_cloud_id = models.IntegerField("PARENT_ID на облаке", blank=True, null=True)  # Используется поле ID
    parent_box_id = models.IntegerField("PARENT_ID на коробке", blank=True, null=True)  # Используется поле ID

    real_obj_cloud_id = models.IntegerField("REAL_OBJ_ID на облаке", blank=True, null=True)  # Используется поле REAL_OBJECT_ID
    real_obj_box_id = models.IntegerField("REAL_OBJ_ID на коробке", blank=True, null=True)  # Используется поле REAL_OBJECT_ID

    parent_real_obj_cloud_id = models.IntegerField("PARENT REAL_OBJ_ID на облаке", blank=True, null=True)  # Используется поле REAL_OBJECT_ID
    parent_real_obj_box_id = models.IntegerField("PARENT REAL_OBJ_ID на коробке", blank=True, null=True)  # Используется поле REAL_OBJECT_ID

    created_dt = models.DateTimeField("Время создания", auto_now_add=True)

    class Admin(admin.ModelAdmin):
        list_display = ("cloud_id", "parent_cloud_id", "box_id", "parent_box_id", "created_dt")


class Storage(models.Model):
    """Модель дискового хранилища"""
    cloud_id = models.IntegerField("ID на облаке", unique=True)  # Используется поле ID
    box_id = models.IntegerField("ID на коробке", blank=True, null=True)  # Используется поле ID

    folders_in_cloud = models.IntegerField("Папок на облаке", blank=True, null=True, default=0)
    folders_in_box = models.IntegerField("Папок на коробке", blank=True, null=True, default=0)

    files_in_cloud = models.IntegerField("Файлов на облаке", blank=True, null=True, default=0)
    files_in_box = models.IntegerField("Файлов на коробке", blank=True, null=True, default=0)

    folders_sync = models.BooleanField("Папки синхронизированы", default=False)
    files_sync = models.BooleanField("Файлы синхронизированы", default=False)

    class Admin(admin.ModelAdmin):
        list_display = ("cloud_id", "box_id", "folders_in_cloud", "folders_in_box", "folders_in_cloud", "folders_in_box", "folders_sync", "files_sync")
