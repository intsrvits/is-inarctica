from typing import Dict, List

from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.task_migration.tasks_checklist.helpers import get_all_checklists, get_task_checklist_map
from inarctica_migration.models import TaskMigration, ChecklistPoints
from inarctica_migration.utils import BoxBitrixToken


def __clear_db():
    """Полностью зачищает БД с чеклистами"""
    ChecklistPoints.objects.all().delete()

def _append_batch_to_delete_checklists(task_id: int, task_checklists: Dict[int, Dict], batch_to_delete: List):
    """Заполняет список для удаления записей батчем (сам процесс удаления прописан в delete_all_task_checklists)"""

    # Удаляем только с PARENT_ID = 0 (они корневые, остальные удалятся вслед за ними)
    for checklist_id, checklist_data in task_checklists.items():
        if int(checklist_data["PARENT_ID"]) == 0:
            params_to_delete = {
                "TASKID": task_id,
                "ITEMID": checklist_id,
            }

            batch_to_delete.append((str(checklist_id), "task.checklistitem.delete", params_to_delete))


def delete_all_task_checklists():
    """Удаляет все чеклисты с бокс-портала и чистит БД"""
    token = BoxBitrixToken()

    migrated_tasks: Dict[int, int] = dict(TaskMigration.objects.filter(is_synced=True, checklist_cnt__gt=0).values_list("cloud_id", "box_id"))
    box_all_checklists = get_all_checklists(token, list(migrated_tasks.values()))

    # Получаем структуру task_id -> checklist_id -> checklist_data
    box_checklists_by_tasks: Dict[int, Dict[int, Dict]] = get_task_checklist_map(box_all_checklists)

    batch_to_delete = []
    for task_id, checklists_dict in box_checklists_by_tasks.items():
        # Дополняем batch_to_delete:
        _append_batch_to_delete_checklists(task_id, checklists_dict, batch_to_delete)

    delete_result = token.batch_api_call(batch_to_delete)

    if delete_result.all_ok:
        # Чистка БД после удаления
        __clear_db()

    debug_point(f"С коробочного портала удалено {len(delete_result.successes)}")
