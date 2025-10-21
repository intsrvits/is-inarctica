from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from inarctica_migration.models import Group, TaskMigration, User

from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.task_migration.entity_matchers import match_users
from inarctica_migration.functions.task_migration.bx_rest_request import bx_tasks_task_list, bx_tasks_task_add
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

    bulk_data = []

    migrated_group_ids = dict(Group.objects.all().values_list("origin_id", "destination_id"))
    qs_initialized_tasks = TaskMigration.objects.all().values_list("cloud_id", flat=True)

    cloud_token = CloudBitrixToken()
    all_cloud_tasks = bx_tasks_task_list(cloud_token)

    processed_tasks_ids = set()
    for task in all_cloud_tasks["tasks"]:

        # Условие, чтобы не пропускать дублирующие сущности с теми же параметрами
        if task["id"] in processed_tasks_ids:
            continue

        group_id = int(task["groupId"]) if isinstance(task["groupId"], str) else None
        #  todo убрать это условие пока только с группами работаем
        if not group_id:
            continue


