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

# from django.db import models
# from mptt.models import MPTTModel, TreeForeignKey
#
# class Folder(MPTTModel):
#     origin_id = models.PositiveIntegerField(primary_key=True)
#     destination_id = models.PositiveIntegerField(blank=True, null=True)
#     name = models.CharField(max_length=255, blank=True)
#     origin_parent = TreeForeignKey(
#         'self',
#         on_delete=models.PROTECT,
#         null=True,
#         blank=True,
#         related_name='children'
#     )
#     origin_parent_parent = TreeForeignKey()
#     class MPTTMeta:
#         order_insertion_by = ['name']
#
#     def __str__(self):
#         return f"{self.name} ({self.bx_id})"
