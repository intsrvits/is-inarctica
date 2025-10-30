from collections import defaultdict

from inarctica_migration.functions.disk_migration.bx_rest_requests import bx_storage_getlist
from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.task_migration.bx_rest_request import bx_tasks_task_list, bx_task_commentitem_add
from inarctica_migration.functions.task_migration.fields import task_user_fields_in_upper, task_fields_in_upper
from inarctica_migration.functions.task_migration.tasks_comments import check_attachments_in_comment
from inarctica_migration.models import Group, TaskMigration, User, CommentMigration
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken

from inarctica_migration.functions.task_migration.tasks_comments.handlers import get_comments_to_migration, clean_post_message
from inarctica_migration.functions.task_migration.tasks_comments.attached_file_handlers import migrate_attached_files


def migrate_task_comments():
    """"""
    bulk_data = []

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    params = {"filter": {"ENTITY_TYPE": "user"}}

    # Связь хранилищ на двух порталах
    storages_map: dict[int, int] = {}

    migrated_comments_map: dict[int, int] = dict(CommentMigration.objects.values_list("cloud_id", "box_id"))

    # Box {user_id: storage}
    user_storages = bx_storage_getlist(box_token, params)
    user_id_storage_map: dict[int, dict] = {int(storage["ENTITY_ID"]): storage for storage in user_storages}

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

        # Обрабатываем каждую из списка задач группы. group_tasks - это список кортежей, где кортеж (cloud_task_id, box_task_id)
        for cloud_task_id, box_task_id in group_tasks:
            try:
                current_task = TaskMigration.objects.filter(cloud_id=cloud_task_id).first()

                if current_task.comm_sync:
                    continue

                comments_to_migration: dict[int, dict] = get_comments_to_migration(cloud_token, cloud_task_id)
                comment_ids_in_chrono: list[int] = sorted(comments_to_migration.keys())

                bulk_data = []
                for comment_id in comment_ids_in_chrono:

                    if comment_id in migrated_comments_map:
                        continue

                    current_comment = comments_to_migration[comment_id]
                    author_id = user_map.get(int(current_comment["AUTHOR_ID"]), 1)  # Если пользователь не найден, то используем админа
                    box_storage_id = user_id_storage_map.get(author_id)['ID'] if user_id_storage_map.get(author_id, {}).get('ID') else 1

                    attachment_file_id_map = None
                    uf_forum_message_doc = []
                    # Проверяем, есть ли прикреплённые к комментарию файлы, если да переносим их
                    attached_files = check_attachments_in_comment(comments_to_migration[comment_id])

                    if attached_files:
                        attachment_file_id_map = migrate_attached_files(box_token, box_storage_id, attached_files)
                        uf_forum_message_doc = [f"n{box_file_id}" for box_file_id in attachment_file_id_map.values()]

                    params_to_create = {
                        "TASKID": box_task_id,
                        "FIELDS": {
                            "POST_MESSAGE": clean_post_message(current_comment["POST_MESSAGE"], attachment_file_id_map),
                            "AUTHOR_ID": author_id,
                            "POST_DATE": current_comment["POST_DATE"],
                            "UF_FORUM_MESSAGE_DOC": uf_forum_message_doc,
                        }
                    }

                    box_comment_id = int(bx_task_commentitem_add(box_token, params_to_create))

                    migrated_comments_map[comment_id] = box_comment_id

                    bulk_data.append(CommentMigration(
                        cloud_id=comment_id,
                        box_id=box_comment_id,
                        cloud_task_id=cloud_task_id,
                        box_task_id=box_task_id,
                        with_files=bool(uf_forum_message_doc),
                    ))

                current_task.comm_cloud_cnt = len(comment_ids_in_chrono)
                current_task.comm_box_cnt = (current_task.comm_box_cnt or 0) + len(bulk_data)

                CommentMigration.objects.bulk_create(
                    bulk_data,
                    unique_fields=["cloud_id"],
                    update_fields=["box_id", "cloud_task_id", "box_task_id", "with_files"],
                    update_conflicts=True,
                )

                if current_task.comm_cloud_cnt == current_task.comm_box_cnt:
                    current_task.comm_sync = True
                    current_task.save()

                debug_point(f"Перенесено {len(bulk_data)} комментариев из {len(comment_ids_in_chrono)}\n"
                            f"CloudTaskId: {cloud_task_id}\n"
                            f"https://inarctica.bitrix24.ru/workgroups/group/379/tasks/task/view/{cloud_task_id}/\n\n"
                            f"BoxTaskId: {box_task_id}\n"
                            f"https://bitrix24.inarctica.com/company/personal/user/1/tasks/task/view/{box_task_id}/\n\n",
                            with_tags=False,
                            )

            except Exception as exc:
                debug_point("❌ Произошла ошибка при переносе комментариев\n"
                            f"CloudTaskId: {cloud_task_id}\n"
                            f"https://inarctica.bitrix24.ru/workgroups/group/379/tasks/task/view/{cloud_task_id}/\n\n"
                            f"BoxTaskId: {box_task_id}\n"
                            f"https://bitrix24.inarctica.com/company/personal/user/1/tasks/task/view/{box_task_id}/\n\n"
                            f"{exc}")

            finally:
                current_task.save()

                CommentMigration.objects.bulk_create(
                    bulk_data,
                    unique_fields=["cloud_id"],
                    update_fields=["box_id", "cloud_task_id", "box_task_id", "with_files"],
                    update_conflicts=True,
                )

        debug_point("Перенос комментариев завершён\n")
