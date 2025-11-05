from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.task_migration.bx_rest_request import bx_tasks_task_list
from inarctica_migration.functions.task_migration.tasks_checklist.bx_rest_request import bx_task_checklistitem_getlist
from inarctica_migration.models import TaskMigration, ChecklistPoints
from inarctica_migration.utils import CloudBitrixToken


def get_number_of_checklists(token, task_id):
    """"""
    params = {"TASKID": task_id}
    task_checklists = bx_task_checklistitem_getlist(token, params)

    return len(task_checklists)


def fill_db_checklist_cnt_field():
    """
    Обновляет поле checklist_cnt в таблице TaskMigration для всех задач,
    у которых существует box_group_id.

    Алгоритм:
    1. Извлекает список задач из облачного Bitrix (через batch API),
       включая количество чеклистов.
    2. Сопоставляет cloud_id с количеством чеклистов.
    3. Обновляет базу данных через bulk_create.
    """

    bulk_data = []
    batch_data = []

    cloud_token = CloudBitrixToken()

    task_to_process = TaskMigration.objects.filter(box_group_id__isnull=False)
    try:
        for task in task_to_process:
            task_cloud_id = task.cloud_id
            task_box_id = task.box_id

            # #fixme
            # if task_cloud_id != 24123:
            #     continue

            batch_data.append((str(task_cloud_id), "task.checklistitem.getlist", {"TASKID": task_cloud_id}))  # Через лист почему-то не получается селект чеклистов сделать - поэтому батч

        batch_result = cloud_token.batch_api_call(batch_data, timeout=30)
        pass
        # return batch_result

        # if not batch_result.all_ok:
        #     debug_point(f"Произошла ошибка во время batch запроса: {batch_result.errors}")

    except Exception as exc:
        debug_point(f"Произошла ошибка (1):\n"
                    f"{exc}")
        raise

    try:
        for cloud_task_id, task_result in batch_result.successes.items():
            cloud_task_id = int(cloud_task_id)

            bulk_data.append(TaskMigration(
                cloud_id=cloud_task_id,
                checklist_cnt=len(task_result["result"]),
            ))

    except Exception as exc:
        debug_point(f"Произошла ошибка (2):\n"
                    f"{exc}")

    finally:
        TaskMigration.objects.bulk_create(
            bulk_data,
            unique_fields=["cloud_id"],
            update_fields=["checklist_cnt"],
            update_conflicts=True,
        )

        debug_point(f"Установлено число чеклистов у {len(bulk_data)} из {len(task_to_process)} задач")


def initialize_checklists_points():
    """"""

    bulk_data = []
    batch_data = []

    cloud_token = CloudBitrixToken()
    # params = {
    #     "select": ["ID", "CHECKLIST", "checklist", "CHECKLIST"]
    # }
    # cloud_tasks = bx_tasks_task_list(cloud_token, params)
    # checklists_cnt_by_id = {int(task['id']): len(task.get('checklist', [])) for task in cloud_tasks}

    task_to_process = TaskMigration.objects.filter(box_group_id__isnull=False, checklist_cnt__gt=0)
    try:
        for task in task_to_process:
            task_cloud_id = task.cloud_id
            batch_data.append((str(task_cloud_id), "task.checklistitem.getlist", {"TASKID": task_cloud_id}))

        batch_result = cloud_token.batch_api_call(batch_data, timeout=30)

        if not batch_result.all_ok:
            debug_point(f"Произошла ошибка во время batch запроса: {batch_result.error}")

    except Exception as exc:
        debug_point(f"Произошла ошибка (1):\n"
                    f"{exc}")
        raise

    try:
        for cloud_task_id, task_checklist_result in batch_result.successes.items():
            task_checklists = task_checklist_result["result"]
            for checklist in task_checklists:
                with_files = bool(checklist['ATTACHMENTS'])

                bulk_data.append(ChecklistPoints(
                    cloud_id=int(checklist['ID']),
                    cloud_task_id=int(cloud_task_id),
                    parent_cloud_id=int(checklist['PARENT_ID']),
                    with_files=with_files,
                ))

    except Exception as exc:
        debug_point(f"Произошла ошибка (2):\n"
                    f"{exc}")

    finally:
        ChecklistPoints.objects.bulk_create(
            bulk_data,
            unique_fields=["cloud_id"],
            update_fields=["cloud_task_id", "parent_cloud_id", "with_files"],
            update_conflicts=True,
        )

        debug_point(f"Проинициализировано {len(bulk_data)} элементов чек-листов")

# def comp():
#     fill_db_checklist_cnt_field()
#     initialize_checklists_points()
