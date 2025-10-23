from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from inarctica_migration.models import Group, TaskMigration, User, StageMigration

from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.task_migration.entity_matchers import match_users
from inarctica_migration.functions.task_migration.bx_rest_request import bx_tasks_task_list, bx_task_stages_get, bx_task_stages_update, bx_task_stages_add
from inarctica_migration.functions.task_migration.fields import (task_fields_map,
                                                                 task_user_fields_map,
                                                                 task_fields_in_upper,
                                                                 task_user_fields_in_upper, )


def _safe_int(value, default=0):
    """Безопасно приводит значение к int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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
            output_params["fields"][field_upper] = match_users((_safe_int(input_params[field_camel])), users_map)

    # Перезаписываем поле GROUP_ID на его группу-двойника с коробки.
    # Если в респонсе пришёл groupId="0" или None, то оставляем задач без привязки к группе.
    output_params["fields"]["GROUP_ID"] = group_map[int(input_params["groupId"])] if (input_params["groupId"] and input_params["groupId"] != "0") else None

    return output_params


def migration_tasks_to_box():
    """"""
    methods = []
    bulk_data = []

    box_token = BoxBitrixToken()

    migrated_group_ids: dict[int, int] = dict(Group.objects.all().values_list("origin_id", "destination_id"))
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
        i = 0
        for task in all_cloud_tasks:
            i += 1
            # Условие, чтобы пропускать дублирующие сущности с теми же параметрами. Работает в рамках одной миграции
            is_processed: bool = int(task["id"]) in processed_tasks_ids
            group_is_not_migrated: bool = not bool(migrated_group_ids.get(int(task["groupId"]) if (task["groupId"] and task["groupId"] != "0") else 0))
            is_synced: bool = int(task["id"]) in synced_task_ids  # Отбрасываем, те что уже перенесли

            if is_processed or is_synced or group_is_not_migrated:
                continue

            # Если пытаемся добавить задачу, но родительская при этом ещё не была перенесена (пропускаем)
            if task["parentId"] and task["parentId"] != "0":
                if not (tasks_cloud_box_id_map.get(int(task["parentId"]))):
                    continue

            params = _params_for_tasks(task, user_map, migrated_group_ids)
            methods.append((str(task['id']), "tasks.task.add", params))

            if i == 6:
                break

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


def stage_migration():
    """"""
    bulk_data = []

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    # соответствие origin_id -> destination_id
    migrated_group_ids = dict(Group.objects.all().values_list("origin_id", "destination_id"))
    try:
        for cloud_group_id, box_group_id in migrated_group_ids.items():

            # Берём все стадии с облака и с коробки для этой группы
            cloud_stages_in_current_group = bx_task_stages_get(cloud_token, {"entityId": cloud_group_id, "isAdmin": "Y"})
            box_stages_in_current_group = bx_task_stages_get(box_token, {"entityId": box_group_id, "isAdmin": "Y"})

            cloud_stages_list = list(cloud_stages_in_current_group.values())
            box_stages_list = list(box_stages_in_current_group.values())

            last_box_stage_id = None

            # Обновляем существующие box-стадии по данным cloud
            for cloud_stage, box_stage in zip(cloud_stages_list, box_stages_list):
                bx_task_stages_update(box_token, {
                    "id": box_stage["ID"],
                    "fields": {
                        "TITLE": cloud_stage["TITLE"],
                        "COLOR": cloud_stage.get("COLOR", "gray"),
                    },
                    "isAdmin": "Y"
                })

                bulk_data.append(StageMigration(
                    cloud_id=int(cloud_stage["ID"]),
                    box_id=int(box_stage["ID"]),
                    is_synced=True,
                ))
                last_box_stage_id = box_stage["ID"]

            # Создаём недостающие стадии (если на облаке больше)
            if len(cloud_stages_list) > len(box_stages_list):
                for cloud_stage in cloud_stages_list[len(box_stages_list):]:
                    last_box_stage_id = bx_task_stages_add(box_token, {
                        "fields": {
                            "TITLE": cloud_stage["TITLE"],
                            "COLOR": cloud_stage.get("COLOR", "gray"),
                            "ENTITY_ID": box_group_id,
                            "AFTER_ID": last_box_stage_id,  # вставляем после последней
                        },
                        "isAdmin": "Y",
                    })

                    bulk_data.append(StageMigration(
                        cloud_id=int(cloud_stage["ID"]),
                        box_id=int(last_box_stage_id),
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

        StageMigration.objects.bulk_create(
            bulk_data,
            unique_fields=["cloud_id"],
            update_fields=["box_id", "is_synced"],
            update_conflicts=True,
        )

        debug_point(f"✅ Создано/Обновлено {len(bulk_data)} стадий \n\n")
