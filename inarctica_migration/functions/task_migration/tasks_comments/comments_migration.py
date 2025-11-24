from collections import defaultdict
from typing import List, Dict, Tuple

from inarctica_migration.functions.disk_migration.bx_rest_requests import bx_storage_getlist
from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.task_migration.bx_rest_request import bx_tasks_task_list, bx_task_commentitem_add
from inarctica_migration.functions.task_migration.fields import task_user_fields_in_upper, task_fields_in_upper
from inarctica_migration.functions.task_migration.tasks_comments import check_attachments_in_comment
from inarctica_migration.models import Group, TaskMigration, User, CommentMigration
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken

from inarctica_migration.functions.task_migration.tasks_comments.handlers import get_comments_to_migration, clean_post_message, _is_system_comment
from inarctica_migration.functions.task_migration.tasks_comments.attached_file_handlers import migrate_attached_files


def get_all_comments_by_tasks(token: CloudBitrixToken, task_ids) -> Dict[int, Dict]:
    methods = []

    all_comments: Dict[int, Dict] = dict()
    for task_id in task_ids:
        methods.append((str(task_id), "task.commentitem.getlist", {"TASK_ID": task_id, "ORDER": {"ID": "ASC"}}))
    batch_result = token.batch_api_call(methods, timeout=25)
    for task_id, batch_data in batch_result.successes.items():
        task_comments = batch_data["result"]
        # Если комментариев в задаче > 50 (таких случае несколько)
        if len(task_comments) >= 50:
            task_comments = token.call_list_method("task.commentitem.getlist", {"TASK_ID": task_id, "ORDER": {"ID": "ASC"}})

        all_comments[int(task_id)] = task_comments

    return all_comments


def get_structure_by_comment_ids(all_comments_by_tasks: Dict[int, Dict]):
    """"""

    result = dict()
    for task_id, comments in all_comments_by_tasks.items():
        for comment in comments:

            if _is_system_comment(comment["POST_MESSAGE"]):
                continue

            result[int(comment["ID"])] = (task_id, comment)

    return result


def migrate_task_comments():
    """"""
    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    migrated_users_map: Dict[int, int] = dict(User.objects.all().values_list("origin_id", "destination_id"))
    migrated_task_map: Dict[int, int] = dict(TaskMigration.objects.filter(is_synced=True).values_list("cloud_id", "box_id"))
    migrated_comments_ids = list(CommentMigration.objects.all().values_list("cloud_id", flat=True))

    # Связь пользователя с его хранилищем на коробке
    # {user_id: storage}
    user_storages = bx_storage_getlist(box_token, {"filter": {"ENTITY_TYPE": "user"}})
    user_id_storage_map: dict[int, dict] = {int(storage["ENTITY_ID"]): storage for storage in user_storages}

    all_comments_by_tasks = get_all_comments_by_tasks(cloud_token, migrated_task_map.keys())
    prepared_comments: Dict[int, Tuple[int, Dict]] = get_structure_by_comment_ids(all_comments_by_tasks)
    for comment_id in sorted(prepared_comments.keys()):
        if comment_id in migrated_comments_ids:
            continue

        task_id, current_comment = prepared_comments[comment_id]

        author_id = migrated_users_map.get(int(current_comment["AUTHOR_ID"]), 1)  # Если пользователь не найден, то используем админа
        box_storage_id = user_id_storage_map.get(author_id)['ID'] if user_id_storage_map.get(author_id, {}).get('ID') else 1

        attachment_file_id_map = None
        uf_forum_message_doc = []

        attached_files = check_attachments_in_comment(current_comment)
        if attached_files:
            attachment_file_id_map = migrate_attached_files(box_token, box_storage_id, attached_files)
            uf_forum_message_doc = [f"n{box_file_id}" for box_file_id in attachment_file_id_map.values()]

        params_to_create = {
            "TASKID": migrated_task_map[task_id],
            "FIELDS": {
                "POST_MESSAGE": clean_post_message(current_comment["POST_MESSAGE"], attachment_file_id_map),
                "AUTHOR_ID": author_id,
                "POST_DATE": current_comment["POST_DATE"],
                "UF_FORUM_MESSAGE_DOC": uf_forum_message_doc,
            }
        }

        box_comment_id = int(bx_task_commentitem_add(box_token, params_to_create))
        CommentMigration.objects.create(
            cloud_id=comment_id,
            box_id=box_comment_id,
            cloud_task_id=task_id,
            box_task_id=migrated_task_map[task_id],
            with_files=bool(attached_files),
        )

        debug_point(f"(XYZ) Перенесен коммент из: \n"
                    f"CloudTaskId: {task_id}\n"
                    f"https://inarctica.bitrix24.ru/workgroups/group/379/tasks/task/view/{task_id}/\n\n"
                    f"BoxTaskId: {migrated_task_map[task_id]}\n"
                    f"https://bitrix24.inarctica.com/company/personal/user/1/tasks/task/view/{migrated_task_map[task_id]}/\n\n",
                    with_tags=False,
                    )

    debug_point(f"Перенесено {CommentMigration.objects.all().count()} комментариев из {len(prepared_comments)}\n")


def delete_box_comments():
    """"""
    methods = []

    box_token = BoxBitrixToken()
    box_comments = CommentMigration.objects.all()

    # debug_point(f"На коробке сейчас: {box_comments.count()} комментариев")
    for comment in box_comments:
        methods.append((str(comment.pk), "task.commentitem.delete", {"TASKID": comment.box_task_id, "ITEMID": comment.box_id}))
    batch_result = box_token.batch_api_call(methods)

    # debug_point(f"Удалено с портала: {len(batch_result.successes)}")

    for k, v in batch_result.successes.items():
        CommentMigration.objects.filter(pk=int(k)).delete()

    # debug_point(f"Осталось в БД и на портале: {CommentMigration.objects.all().count()}")
    return batch_result
