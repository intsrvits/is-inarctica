import re
from inarctica_migration.functions.task_migration.bx_rest_request import bx_task_commentitem_getlist
from inarctica_migration.functions.task_migration.fields import SYSTEM_COMMNETS
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from inarctica_migration.models import Group


def _get_group_storage_relationship():
    """"""
    group_map: dict[int, int] = dict(Group.objects.all().values_list("origin_id", "destination_id"))
    cloud_storages_list = CloudBitrixToken().call_list_method("disk.storage.getlist", {"filter": {"ENTITY_TYPE": "group"}})
    box_storages_list = BoxBitrixToken().call_list_method("disk.storage.getlist", {"filter": {"ENTITY_TYPE": "group"}})

    cloud_relationship = dict()
    for cloud_storage in cloud_storages_list:
        if int(cloud_storage["ENTITY_ID"]) in group_map:
            cloud_relationship[int(cloud_storage["ENTITY_ID"])] = int(cloud_storage["ID"])

    box_relationship = dict()
    for box_storage in box_storages_list:
        if int(box_storage["ENTITY_ID"]) in group_map.values():
            box_relationship[int(box_storage["ENTITY_ID"])] = int(box_storage["ID"])

    return cloud_relationship, box_relationship


def _migrate_attached_files(files, ) -> dict:
    """
    Переносит прикрепленные файлы на box-портал.
    Возвращает словарь связей между FILE_ID.
    """
    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    return {}


def _check_attachments_in_comment(comment) -> list:
    """Возвращает список прикрепленных к комментарию файлов."""
    attached_files_data = []
    bx_attached_objects = []
    if isinstance(comment.get("ATTACHED_OBJECTS"), list) and len(comment["ATTACHED_OBJECTS"]):
        bx_attached_objects = comment["ATTACHED_OBJECTS"]

    if isinstance(comment.get("ATTACHED_OBJECTS"), dict) and len(comment["ATTACHED_OBJECTS"].keys()):
        bx_attached_objects = comment["ATTACHED_OBJECTS"].values()

    if len(bx_attached_objects):
        for bx_attached_object in bx_attached_objects:
            attached_files_data.append({
                "NAME": bx_attached_object["NAME"],
                "URL": bx_attached_object["DOWNLOAD_URL"],
                "FILE_ID": bx_attached_object["FILE_ID"],
                "SIZE": bx_attached_object["SIZE"]
            })

    return attached_files_data


def _is_system_comment(text: str) -> bool:
    """Проверяет, является ли комментарий системным"""
    # Нас интересует только первая часть сообщения
    comment = re.split(r"[.:]", text)[0]

    return any(system_comment in comment.lower() for system_comment in SYSTEM_COMMNETS)


def comment_handler(cloud_token: CloudBitrixToken, task_id: int):
    """
    Получает все комментарии к задаче.
    Фильтрует системные комментарии и выстраивает хронологический порядок
    """

    cloud_token = CloudBitrixToken()
    params = {"TASK_ID": task_id, "ORDER": {"ID": "ASC"}}
    all_comments = bx_task_commentitem_getlist(cloud_token, params)

    # Получаем только пользовательские комментарии (без системных)
    comments_to_migrate: dict[int: dict] = dict()
    for comment in all_comments:
        if not (_is_system_comment(comment["POST_MESSAGE"])):
            comment_id = int(comment["ID"])
            comments_to_migrate[comment_id] = comment

    for comment in comments_to_migrate:
        attached_files_data = _check_attachments_in_comment

        #return _check_attachemnts_in_comment(comments_to_migrate)
    return comments_to_migrate
