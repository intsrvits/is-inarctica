from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.task_migration.tasks_checklist.bx_rest_request import bx_task_checklistitem_add
from inarctica_migration.functions.task_migration.tasks_checklist.helpers import get_all_checklists, get_task_checklist_map
from inarctica_migration.models import TaskMigration, ChecklistPoints, Group
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from typing import List, Dict


def _creation_cycle_for_task_checklists(task_ids: tuple, cloud_checklists: Dict[int, Dict]):
    """"""
    bulk_data = []

    box_token = BoxBitrixToken()

    cloud_task_id, box_task_id = task_ids

    # Уже перенесённые чеклисты
    checklist_ids_map: Dict[int, int] = dict(ChecklistPoints.objects.filter(cloud_task_id=cloud_task_id).values_list("cloud_id", "box_id"))

    to_process = dict(cloud_checklists)

    progress = True
    while progress and to_process:
        progress = False

        for cloud_id, checklist in list(to_process.items()):
            try:

                # Пропускаем уже созданные
                if cloud_id in checklist_ids_map:
                    del to_process[cloud_id]
                    progress = True
                    continue

                cloud_parent_id = int(checklist["PARENT_ID"])

                # Создаём только если это root или родитель уже создан
                if cloud_parent_id == 0 or (cloud_parent_id in checklist_ids_map):
                    box_parent_id = checklist_ids_map.get(cloud_parent_id, 0)

                    params_to_add = {
                        "TASKID": box_task_id,
                        "FIELDS": {
                            "TITLE": checklist["TITLE"],
                            "SORT_INDEX": checklist["SORT_INDEX"],
                            "IS_COMPLETE": checklist["IS_COMPLETE"],
                            "IS_IMPORTANT": checklist["IS_IMPORTANT"],
                            "PARENT_ID": box_parent_id,
                        }
                    }

                    box_id = int(bx_task_checklistitem_add(box_token, params_to_add))

                    checklist_ids_map[cloud_id] = box_id

                    bulk_data.append(ChecklistPoints(
                        cloud_task_id=cloud_task_id,
                        cloud_id=cloud_id,
                        box_id=box_id,
                        parent_cloud_id=cloud_parent_id,
                        parent_box_id=box_parent_id,
                        with_files=bool(checklist["ATTACHMENTS"]),
                        is_synced=not bool(checklist["ATTACHMENTS"]),
                    ))

                    del to_process[cloud_id]

                    progress = True

            except Exception as exc:
                debug_point(f"Произошла ошибка при переносе чеклиста {checklist}\n"
                            f"Для задачи с cloudID = {cloud_task_id}\n"
                            f"https://inarctica.bitrix24.ru/workgroups/group/379/tasks/task/view/{cloud_task_id}/\n\n"
                            f"Для задачи с boxID = {box_task_id}\n"
                            f"https://bitrix24.inarctica.com/company/personal/user/1/tasks/task/view/{box_task_id}/\n\n"
                            f"{exc}")

        if to_process:
            debug_point(f"Не удалось построить дерево. Остались узлы: {to_process.keys()}")
            break

    already_migrated_checklists = ChecklistPoints.objects.filter(cloud_task_id=cloud_task_id).count()
    ChecklistPoints.objects.bulk_create(
        bulk_data,
        unique_fields=["cloud_id"],
        update_fields=["cloud_task_id", "box_id", "parent_cloud_id", "parent_box_id", "with_files", "is_synced"],
        update_conflicts=True,
    )

    debug_point(f"Перенесено {len(bulk_data)}. Всего {already_migrated_checklists + len(bulk_data)} из {len(cloud_checklists)} чеклистов\n\n"
                f"Для задачи с cloudID = {cloud_task_id}\n"
                f"https://inarctica.bitrix24.ru/workgroups/group/379/tasks/task/view/{cloud_task_id}/\n\n"
                f"Для задачи с boxID = {box_task_id}\n"
                f"https://bitrix24.inarctica.com/company/personal/user/1/tasks/task/view/{box_task_id}/\n\n",
                with_tags=False)


def migrate_all_task_checklists():
    """"""

    cloud_token = CloudBitrixToken()

    migrated_tasks: Dict[int, int] = dict(TaskMigration.objects.filter(is_synced=True, comm_sync=True, box_group_id=0).values_list("cloud_id", "box_id"))
    box_all_checklists = get_all_checklists(cloud_token, list(migrated_tasks.keys()))

    # Получаем структуру task_id -> checklist_id -> checklist_data
    box_checklists_by_tasks: Dict[int, Dict[int, Dict]] = get_task_checklist_map(box_all_checklists)

    for task_id, checklists_dict in box_checklists_by_tasks.items():

        # # fixme test
        # if task_id != 545:
        #     continue

        task_ids = (task_id, migrated_tasks[task_id])  # Кортеж айдишников задачи с разных порталов

        _creation_cycle_for_task_checklists(task_ids, checklists_dict)
        TaskMigration.objects.filter(cloud_id=int(task_id)).update(checklist_cnt=len(checklists_dict))
#
#
#
#
# def get_task_checklist_map(batch_successes: dict) -> dict[int, dict[int, dict]]:
#     """
#     type(batch_result): dict_items
#
#     Возвращает структуру, к которой удобно обращаться по ключам:
#     task_id -> checklist_id -> checklist_data
#     """
#     result = {}
#     for cloud_task_id, cloud_checklist in batch_successes.items():
#         task_id = int(cloud_task_id)
#         checklists = cloud_checklist["result"]
#
#         # Превращаем список чеклистов в словарь по ID
#         checklist_dict = {
#             int(item["ID"]): item
#             for item in checklists
#             if "ID" in item
#         }
#
#         result[task_id] = checklist_dict
#
#     return result
#
#
# def get_all_checklists(token: CloudBitrixToken, task_ids: List[int]):
#     """Возвращает результат батча при взятии чеклистов у задач"""
#     batch_to_get = []
#
#     for task_id in task_ids:
#         batch_to_get.append((str(task_id), "task.checklistitem.getlist", {"TASKID": task_id}))
#
#     batch_get_result = token.batch_api_call(batch_to_get, timeout=20)
#
#     # if not batch_get_result.all_ok:
#     #     debug_point(f"Произошла ошибка во время batch запроса: {batch_get_result.errors}")
#     #     raise
#
#     return batch_get_result.successes
#
#
# def migrate_checklists2():
#     """"""
#
#     cloud_token = CloudBitrixToken()
#     box_token = BoxBitrixToken()
#
#
# def migrate_checklists():
#     """"""
#     batch_to_get = []
#     batch_to_add = []
#
#     bulk_data = []
#
#     cloud_token = CloudBitrixToken()
#     box_token = BoxBitrixToken()
#
#     cloud_box_task_map: Dict[int, int] = dict(TaskMigration.objects.filter(is_synced=True, checklist_cnt__gt=0).values_list("cloud_id", "box_id"))
#     # cloud_box_task_map |= {0: 0}
#
#     # migrated_groups = Dict[int, int] = dict(Group.objects.filter(is_synced=True).values_list("destination_id", "origin_id"))
#     task_checklists_cnt_map: Dict[int, int] = dict(TaskMigration.objects.filter(is_synced=True, checklist_cnt__gt=0).values_list("cloud_id", "checklist_cnt"))
#
#     # initialized_checklists_qs = ChecklistPoints.objects.filter(is_synced=False, with_files=False).values_list("cloud_task_id", "cloud_id", "parent_cloud_id")  #fixme убрать with_files
#     initialized_checklists_qs = ChecklistPoints.objects.filter(is_synced=False, with_files=False)  #fixme убрать with_files
#
#     #
#     cloud_checklist_map = dict(ChecklistPoints.objects.values_list("cloud_id", "parent_cloud_id"))
#
#     migrated_tasks: Dict[int, int] = dict(TaskMigration.objects.filter(is_synced=True).values_list("cloud_id", "box_id"))
#     migrated_checklist: Dict[int, int] = dict(ChecklistPoints.objects.filter(is_synced=True).values_list("cloud_id", "box_id"))
#     migrated_checklist |= {0: 0}
#     # cloud_id: box_id
#
#     # box_checklist_and_parent: Dict[int, int] = dict(ChecklistPoints.objects.filter(box_id__isnull=False, parent_box_id__isnull=False))
#     # checklist_id_map: Dict[int, int] = dict(ChecklistPoints.objects.filter(is_synced=False, with_files=False, box_id__isnull=False).values_list("cloud_id", "box_id"))
#
#     # cloud_id_checklists: set[int] = set(ChecklistPoints.objects.filter(is_synced=True, with_files=False).values_list("cloud_id", flat=True))  #fixme убрать with_files
#
#     task_checklists_map = _get_all_checklists(cloud_token, list(cloud_box_task_map))
#     task_checklists_map: Dict[int, dict[int, dict]] = _get_task_checklist_map(task_checklists_map)
#
#     try:
#         for initialized_checklist in initialized_checklists_qs:
#
#             cloud_task_id = initialized_checklist.cloud_task_id
#
#             cloud_checklist_id = initialized_checklist.cloud_id
#
#             if cloud_task_id not in task_checklists_cnt_map:
#                 continue
#
#             if initialized_checklist.is_synced:
#                 continue
#
#             checklist = task_checklists_map[cloud_task_id][cloud_checklist_id]
#             cloud_parent_checklist_id = int(checklist["PARENT_ID"])
#             box_parent_checklist_id = migrated_checklist.get(cloud_parent_checklist_id, None)
#
#             if box_parent_checklist_id or (box_parent_checklist_id == 0):
#                 params_to_add = {
#                     "TASKID": cloud_box_task_map[cloud_task_id],  # box_task_id
#                     "FIELDS": {
#                         "TITLE": checklist["TITLE"],
#                         "SORT_INDEX": checklist["SORT_INDEX"],
#                         "IS_COMPLETE": checklist["IS_COMPLETE"],
#                         "IS_IMPORTANT": checklist["IS_IMPORTANT"],
#                         "PARENT_ID": box_parent_checklist_id,
#                     }
#                 }
#
#                 batch_to_add.append((checklist["ID"], "task.checklistitem.add", params_to_add))
#
#             initialized_checklist.is_synced = True
#             initialized_checklist.save()
#
#         batch_add_result = box_token.batch_api_call(batch_to_add).successes
#
#         debug_point(
#             f"Создано {len(batch_add_result)} чеклистов\n"
#             # f"Для задачи с cloudID = {task_id}\n"
#             # f"https://inarctica.bitrix24.ru/workgroups/group/379/tasks/task/view/{task_id}/\n\n"
#             # f"Для задачи с boxID = {migrated_tasks[task_id]}\n"
#             # f"https://bitrix24.inarctica.com/company/personal/user/1/tasks/task/view/{migrated_tasks[task_id]}/\n\n",
#         )
#
#         for cloud_id, box_id in batch_add_result.items():
#             bulk_data.append(ChecklistPoints(
#                 cloud_id=int(cloud_id),
#                 box_id=int(box_id['result']),
#                 parent_box_id=migrated_checklist[cloud_checklist_map[int(cloud_id)]],
#                 is_synced=True,
#             ))
#
#     except Exception as exc:
#         debug_point(f"Произошла ошибка при создании чеклистов {exc}")
#
#     finally:
#         ChecklistPoints.objects.bulk_create(
#             bulk_data,
#             unique_fields=["cloud_id"],
#             update_fields=["box_id", "parent_box_id", "is_synced"],
#             update_conflicts=True
#         )
