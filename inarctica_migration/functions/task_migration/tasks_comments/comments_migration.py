from collections import defaultdict

from inarctica_migration.functions.task_migration.bx_rest_request import bx_tasks_task_list, bx_task_commentitem_add
from inarctica_migration.functions.task_migration.fields import task_user_fields_in_upper, task_fields_in_upper
from inarctica_migration.functions.task_migration.tasks_comments import check_attachments_in_comment
from inarctica_migration.models import Group, TaskMigration, User
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken

from inarctica_migration.functions.task_migration.tasks_comments.handlers import get_comments_to_migration, clean_post_message


def migrate_task_comments():
    """"""

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    user_map: dict[int, int] = dict(User.objects.all().values_list("origin_id", "destination_id"))

    params = {
        "select": ["ID", *task_fields_in_upper, *task_user_fields_in_upper],
        "filter": {"!GROUP_ID": "0"}
    }
    all_cloud_tasks = bx_tasks_task_list(cloud_token, params=params)

    # {box_id: cloud_id, ...}
    migrated_groups: dict[int, int] = dict(Group.objects.all().values_list("destination_id", "origin_id"))

    # [(cloud_task_id, box_task_id, box_group_id), ...]
    migrated_tasks: list[tuple] = list(TaskMigration.objects.filter(is_synced=True).values_list("cloud_id", "box_id", "box_group_id"))

    # Собираем словарь с информацией о группе на коробочном портале и её перенесенных задачах с cloud и box портала
    # {int(box_group_id_1): list((cloud_task_id_1, box_task_id_1), ... (cloud_task_id_10, box_task_id_10))
    #   ...
    # int(box_group_id_n): list((cloud_task_id_n, box_task_id_n), ...(cloud_task_id_i, box_task_id_j))}
    tasks_by_box_group_map = defaultdict(list)
    for cloud_id, box_id, box_group_id in migrated_tasks:
        tasks_by_box_group_map[box_group_id].append((cloud_id, box_id))

    for box_group_id, group_tasks in tasks_by_box_group_map.items():
        # todo убрать после тестирования
        if box_group_id != 63:
            continue

        # Обрабатываем каждую из списка задач группы. group_tasks - это список кортежей, где кортеж (cloud_task_id, box_task_id)
        for cloud_task_id, box_task_id in group_tasks:
            comments_to_migration: dict[int, dict] = get_comments_to_migration(cloud_token, cloud_task_id)
            comment_ids_in_chrono: list[int] = sorted(comments_to_migration.keys())

            for comment_id in comment_ids_in_chrono:
                current_comment = comments_to_migration[comment_id]

                # Проверяем, есть ли прикреплённые к комментарию файлы, если да переносим их
                attached_files = check_attachments_in_comment(comments_to_migration[comment_id])
                if attached_files:
                    # Логика с переносом файлов на диск-пользователя
                    continue

                params_to_create = {
                    "TASKID": box_task_id,
                    "FIELDS": {
                        "POST_MESSAGE": clean_post_message(current_comment["POST_MESSAGE"]),
                        "AUTHOR_ID": user_map.get(int(current_comment["AUTHOR_ID"]), 1),
                        "POST_DATE": current_comment["POST_DATE"],
                        "UF_FORUM_MESSAGE_DOC": [],  # todo
                    }
                }

                #fixme
                return bx_task_commentitem_add(box_token, params_to_create)

            ...

    return tasks_by_box_group_map
