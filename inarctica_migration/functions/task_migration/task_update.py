from typing import Dict

from inarctica_migration.functions.task_migration.bx_rest_request import bx_tasks_task_list
from inarctica_migration.functions.task_migration.constants import CLOUD_TASK_USERFIELDS, TASK_USERFIELDS_MAP, BOX_TASK_USERFIELDS
from inarctica_migration.models import TaskMigration
from inarctica_migration.utils import BoxBitrixToken, CloudBitrixToken


def update_task():
    """Обновляет пользовательские поля для перенесенных задач"""
    get_methods = []
    update_methods = []

    box_token = BoxBitrixToken()
    migrated_tasks: Dict[int, int] = dict(TaskMigration.objects.filter(is_synced=True).values_list("cloud_id", "box_id"))

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()
    migrated_tasks: Dict[int, int] = dict(TaskMigration.objects.filter(is_synced=True).values_list("cloud_id", "box_id"))

    all_cloud_tasks = bx_tasks_task_list(cloud_token, params={"select": ["ID", *list(CLOUD_TASK_USERFIELDS.keys())]})

    for cloud_task in all_cloud_tasks:
        box_task_id = migrated_tasks.get(int(cloud_task["id"]))
        if not box_task_id:
            continue
        params = {"taskId": box_task_id, "fields": dict()}
        for cloud_task_userfield, box_task_userfield in TASK_USERFIELDS_MAP.items():
            params["fields"][BOX_TASK_USERFIELDS[box_task_userfield]] = cloud_task.get(cloud_task_userfield)

        update_methods.append((str(box_task_id), "task.item.update", params))

    update_batch_result = box_token.batch_api_call(update_methods)
    return update_batch_result
