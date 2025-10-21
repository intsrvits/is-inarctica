from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from inarctica_migration.models import Group, TaskMigration, User

from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.task_migration.entity_matchers import match_users
from inarctica_migration.functions.task_migration.bx_rest_request import bx_tasks_task_list
from inarctica_migration.functions.task_migration.fields import (task_fields_map,
                                                                 task_user_fields_map,
                                                                 task_fields_in_upper,
                                                                 task_user_fields_in_upper, )


def _params_for_tasks(input_params: dict, users_map: dict, group_map):
    """Преобразует поля, полученные из метода list для метода add"""
    output_params = {"fields": {}}

    for field_camel, field_upper in task_fields_map.items():
        output_params["fields"][field_upper] = input_params[field_camel]

    for field_camel, field_upper in task_user_fields_map.items():
        if isinstance(input_params[field_camel], list):
            user_ids_to_match = list(map(int, input_params[field_camel]))
            output_params["fields"][field_upper] = match_users(user_ids_to_match, users_map)

        else:  # В остальных случаях в респонсе должен быть str
            output_params["fields"][field_upper] = match_users((int(input_params[field_camel])), users_map)

    # Перезаписываем поле GROUP_ID на его группу-двойника с коробки.
    # Если в респонсе пришёл groupId="0" или None, то оставляем задач без привязки к группе.
    output_params["fields"]["GROUP_ID"] = group_map[int(input_params["groupId"])] if (input_params["groupId"] and input_params["groupId"] != "0") else None

    return output_params


def migration_tasks_to_box():
    """"""
    methods = []
    bulk_data = []

    box_token = BoxBitrixToken()

    migrated_group_ids = dict(Group.objects.all().values_list("origin_id", "destination_id"))
    qs_tasks = TaskMigration.objects.filter(is_synced=True).values_list("cloud_id", "box_id", "is_synced")

    synced_task_ids = [cloud_id for cloud_id, box_id, is_synced in qs_tasks if is_synced]
    tasks_cloud_box_id_map = {cloud_id: box_id for cloud_id, box_id, is_synced in qs_tasks}

    user_map = dict(User.objects.all().values_list("origin_id", "destination_id"))

    cloud_token = CloudBitrixToken()
    params = {
        "select": ["ID", *task_fields_in_upper, *task_user_fields_in_upper]
    }
    all_cloud_tasks = bx_tasks_task_list(cloud_token, params=params)

    batch_result = None
    processed_tasks_ids = set()
    try:
        for task in all_cloud_tasks:
            # Условие, чтобы пропускать дублирующие сущности с теми же параметрами. Работает в рамках одной миграции
            is_processed = int(task["id"] in processed_tasks_ids)
            is_synced = int(task["id"]) in synced_task_ids  # Отбрасываем, те что уже перенесли

            if is_processed or is_synced:
                continue

            # Если пытаемся добавить задачу, но родительская при этом ещё не была перенесена (пропускаем)
            if task["parentId"] and task["parentId"] != "0":
                if not (tasks_cloud_box_id_map[int(task["parentId"])]):
                    continue

            params = _params_for_tasks(task, user_map, migrated_group_ids)
            methods.append((str(task['id']), "tasks.task.add", params))

        if methods:
            batch_result = box_token.batch_api_call(
                methods,
                halt=1
            )

            for task_cloud_id, task_data in batch_result.successes.items():
                box_task_id: int = int(task_data["result"]["task"]["id"])
                # Обработка случая когда parentId или groupId "0" или None
                box_parent_task_id: int = int(task_data["result"]["task"]["parentId"] if (task_data["result"]["task"]["parentId"] and task_data["result"]["task"]["parentId"] != "0") else 0)
                box_group_id: int = int(task_data["result"]["task"]["groupId"] if (task_data["result"]["task"]["groupId"] and task_data["result"]["task"]["groupId"] != "0") else 0)

                bulk_data.append(TaskMigration(
                    cloud_id=int(task_cloud_id),
                    box_id=box_task_id,
                    box_group_id=box_group_id,
                    box_parent_id=box_parent_task_id,
                    is_synced=True,
                ))

    except Exception as exc:
        debug_point(
            message=(
                "❌ Произошла ошибка при переносе задач\n"
                f"{exc}"
            )
        )

    finally:
        TaskMigration.objects.bulk_create(
            bulk_data,
            unique_fields=["cloud_id"],
            update_fields=["box_id", "box_group_id", "box_parent_id", "is_synced"],
            update_conflicts=True,
        )

        if batch_result:
            debug_point(
                message=(
                    "migration_tasks_to_box\n"
                    "✅ Перенос задач отработал без ошибок \n\n"
                    f"Создано {len(batch_result.successes)}\n\n"
                    f"Всего в бд: {TaskMigration.objects.all().count()}\n"
                    f"Синхронизировано (по бд): {TaskMigration.objects.filter(is_synced=True).count()}\n"
                    f"Осталось синхронизовать: {TaskMigration.objects.filter(is_synced=False).count()}\n"
                )
            )

        else:
            debug_point(
                message=(
                    "migration_tasks_to_box\n"
                    "✅ Не найдено групп для переноса \n\n"
                    f"Всего в бд: {TaskMigration.objects.all().count()}\n"
                    f"Синхронизировано (по бд): {TaskMigration.objects.filter(is_synced=True).count() + len(bulk_data)}\n"
                    f"Осталось синхронизовать: {TaskMigration.objects.filter(is_synced=False).count() - len(bulk_data)}\n"
                )
            )
