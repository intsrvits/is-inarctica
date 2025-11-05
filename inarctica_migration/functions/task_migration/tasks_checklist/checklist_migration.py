from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.models import TaskMigration, ChecklistPoints
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from typing import List, Dict


def _get_task_checklist_map(batch_successes: dict) -> dict[int, dict[int, dict]]:
    """
    type(batch_result): dict_items

    Возвращает структуру, к которой удобно обращаться по ключам:
    task_id -> checklist_id -> checklist_data
    """
    result = {}
    for cloud_task_id, cloud_checklist in batch_successes.items():
        task_id = int(cloud_task_id)
        checklists = cloud_checklist["result"]

        # Превращаем список чеклистов в словарь по ID
        checklist_dict = {
            int(item["ID"]): item
            for item in checklists
            if "ID" in item
        }

        result[task_id] = checklist_dict

    return result


def _get_all_checklists(token: CloudBitrixToken, task_ids: List[int]):
    """"""
    batch_to_get = []

    for task_id in task_ids:
        batch_to_get.append((str(task_id), "task.checklistitem.getlist", {"TASKID": task_id}))

    batch_get_result = token.batch_api_call(batch_to_get)

    # if not batch_get_result.all_ok:
    #     debug_point(f"Произошла ошибка во время batch запроса: {batch_get_result.errors}")
    #     raise

    return batch_get_result.successes


def migrate_checklists():
    """"""
    batch_to_get = []
    batch_to_add = []

    bulk_data = []

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    cloud_box_task_map: Dict[int, int] = dict(TaskMigration.objects.filter(is_synced=True, checklist_cnt__gt=0).values_list("cloud_id", "box_id"))
    cloud_box_task_map |= {0: 0}

    # initialized_checklists_qs = ChecklistPoints.objects.filter(is_synced=False, with_files=False).values_list("cloud_task_id", "cloud_id", "parent_cloud_id")  #fixme убрать with_files
    initialized_checklists_qs = ChecklistPoints.objects.filter(is_synced=False, with_files=False)  #fixme убрать with_files

    # cloud_id: box_id
    checklist_id_map: Dict[int, int] = dict(ChecklistPoints.objects.filter(is_synced=False, with_files=False, box_id__isnull=False).values_list("cloud_id", "box_id"))

    cloud_id_checklists: set[int] = set(ChecklistPoints.objects.filter(is_synced=True, with_files=False).values_list("cloud_id", flat=True))  #fixme убрать with_files

    task_checklists_map = _get_all_checklists(cloud_token, list(cloud_box_task_map))
    task_checklists_map: Dict[int, dict[int, dict]] = _get_task_checklist_map(task_checklists_map)

    for initialized_checklist in initialized_checklists_qs:
        cloud_task_id = initialized_checklist.cloud_task_id
        cloud_checklist_id = initialized_checklist.cloud_id
        cloud_parent_checklist_id = initialized_checklist.parent_cloud_id

        if initialized_checklist.is_synced:
            continue

        if cloud_task_id != 24123:
            continue

        box_parent_checklist_id = cloud_box_task_map.get(cloud_parent_checklist_id, None)
        if box_parent_checklist_id:
            checklist = task_checklists_map[cloud_task_id][cloud_checklist_id]

            params_to_add = {
                "TASKID": cloud_box_task_map[cloud_task_id],  # box_task_id
                "FIELDS": {
                    "TITLE": checklist["TITLE"],
                    "SORT_INDEX": checklist["SORT_INDEX"],
                    "IS_COMPLETE": checklist["IS_COMPLETE"],
                    "IS_IMPORTANT": checklist["IS_IMPORTANT"],
                    "PARENT_ID": box_parent_checklist_id,
                }
            }

        # if not ((cloud_parent_checklist_id in cloud_id_checklists) or (cloud_parent_checklist_id == 0)):
        #     continue

            batch_to_add.append((checklist["ID"], "task.checklistitem.add", params_to_add))

    batch_add_result = box_token.batch_api_call(batch_to_add).successes

    for cloud_id, box_id in batch_add_result.items():
        bulk_data.append(ChecklistPoints(
            cloud_id=int(cloud_id),
            box_id=int(box_id['result']),
            parent_box_id=checklist_id_map.get(int(cloud_id)),
            is_synced=True,
        ))

    ChecklistPoints.objects.bulk_create(
        bulk_data,
        unique_fields=["cloud_id"],
        update_fields=["box_id", "parent_box_id", "is_synced"],
        update_conflicts=True
    )

    debug_point(f"Создано {len(bulk_data)} чеклистов")
    return batch_add_result
