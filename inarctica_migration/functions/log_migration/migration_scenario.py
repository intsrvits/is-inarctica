from inarctica_migration.functions.log_migration.debug_messages import error_log_message, success_log_message
from inarctica_migration.models import LogMigration, User, Group
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken

from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.log_migration.bx_rest_requests import bx_log_blogpost_add
from inarctica_migration.functions.log_migration.handlers import (
    init_blogpost_into_db,
    get_sorted_by_time_blogposts,
    get_files_base64,
    get_files_links,
)


def common_log_migration():
    """"""
    bulk_data = []

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    existed_logs: dict[int, bool] = dict(LogMigration.objects.all().values_list("cloud_id", "is_synced"))
    migrated_users: dict[int, int] = dict(User.objects.all().values_list("origin_id", "destination_id"))

    # Получаем список всех облачных постов, отсортированный по дате созданию
    sorted_cloud_blogposts = get_sorted_by_time_blogposts(cloud_token)
    sorted_cloud_blogposts_map = {int(blogpost["ID"]): blogpost for blogpost in sorted_cloud_blogposts}

    # Обновляем список известных постов
    existed_logs = init_blogpost_into_db(sorted_cloud_blogposts_map, existed_logs)

    try:
        # Обрабатываем все найденные посты
        for cloud_blogpost_id, is_synced in existed_logs.items():

            # Если уже синхронизовано, то пропускаем
            if is_synced:
                continue

            current_blogpost = sorted_cloud_blogposts_map[cloud_blogpost_id]
            cloud_author_id = current_blogpost["AUTHOR_ID"]
            box_author_id = migrated_users.get(cloud_author_id, 1)

            params = {
                "USER_ID": box_author_id,
                "POST_MESSAGE": current_blogpost["DETAIL_TEXT"],
                "POST_TITLE": current_blogpost["TITLE"],
                "DEST": ["UA"]
            }

            # Если обнаружены прикрепленные файлы в облачном посте, то подготавливаем их к переносу
            if current_blogpost.get("FILES"):
                files_attributes: list[tuple[str, str]] = get_files_links(cloud_token, current_blogpost["FILES"])

                params["FILES"] = get_files_base64(files_attributes)

            migration_result = bx_log_blogpost_add(box_token, params)

            bulk_data.append(
                LogMigration(
                    cloud_id=int(current_blogpost["ID"]),
                    box_id=int(migration_result["result"]),
                    dest="UA",
                    is_synced=True,
                )
            )

    except Exception as exc:
        ...

    finally:

        LogMigration.objects.bulk_create(
            bulk_data,
            batch_size=1000,
            unique_fields=["cloud_id"],
            update_fields=["box_id", "dest", "is_synced"],
            update_conflicts=True,
        )


def _migrate_blogposts_for_feed(
        existed_logs: dict[int, bool],
        migrated_users: dict[int, int],
        migrated_groups: dict[int, int],
        cloud_group_id: int = None,
) -> dict[int, bool]:
    """"""
    bulk_data = []

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    already_migrated_blogposts = 0

    # Получаем список всех облачных постов, отсортированный по дате созданию
    sorted_cloud_blogposts = get_sorted_by_time_blogposts(cloud_token, dest=cloud_group_id)
    sorted_cloud_blogposts_map = {int(blogpost["ID"]): blogpost for blogpost in sorted_cloud_blogposts}

    # Обновляем список известных постов
    existed_logs = init_blogpost_into_db(sorted_cloud_blogposts_map, existed_logs)

    try:
        # Обрабатываем все найденные посты
        for cloud_blogpost_id, is_synced in existed_logs.items():

            # Если уже синхронизовано, то пропускаем
            if is_synced:
                already_migrated_blogposts += 1
                continue

            current_blogpost = sorted_cloud_blogposts_map[int(cloud_blogpost_id)]
            cloud_author_id = current_blogpost["AUTHOR_ID"]
            box_author_id = migrated_users.get(int(cloud_author_id), 1)

            params = {
                "USER_ID": box_author_id,
                "POST_MESSAGE": current_blogpost["DETAIL_TEXT"],
                "POST_TITLE": current_blogpost["TITLE"],
                "DEST": [f"SG{migrated_groups[cloud_group_id]}"]
            }

            # Если обнаружены прикрепленные файлы в облачном посте, то подготавливаем их к переносу
            if current_blogpost.get("FILES"):
                files_attributes: list[tuple[str, str]] = get_files_links(cloud_token, current_blogpost["FILES"])

                params["FILES"] = get_files_base64(files_attributes)

            migration_result = bx_log_blogpost_add(box_token, params)

            bulk_data.append(
                LogMigration(
                    cloud_id=int(current_blogpost["ID"]),
                    box_id=int(migration_result["result"]),
                    dest=f"SG{cloud_group_id}",
                    is_synced=True,
                )
            )

        debug_point(success_log_message(total_found=len(sorted_cloud_blogposts), migrated=len(bulk_data) + already_migrated_blogposts, dest=cloud_group_id))

    except Exception as exc:
        debug_point(error_log_message(exc, total_found=len(sorted_cloud_blogposts), migrated=len(bulk_data) + already_migrated_blogposts, dest=cloud_group_id))

    finally:
        LogMigration.objects.bulk_create(
            bulk_data,
            batch_size=1000,
            unique_fields=["cloud_id"],
            update_fields=["box_id", "dest", "is_synced"],
            update_conflicts=True,
        )

        return existed_logs


def migrate_blogposts_for_portals():
    """"""

    existed_logs: dict[int, bool] = dict(LogMigration.objects.all().values_list("cloud_id", "is_synced"))
    migrated_users: dict[int, int] = dict(User.objects.all().values_list("origin_id", "destination_id"))
    migrated_groups: dict[int, int] = dict(Group.objects.all().values_list("origin_id", "destination_id"))

    # Перенос для постов в лентах групп
    for cloud_group_id in migrated_groups:
        existed_logs = _migrate_blogposts_for_feed(
            existed_logs=existed_logs,
            migrated_users=migrated_users,
            migrated_groups=migrated_groups,
            cloud_group_id=cloud_group_id,
        )
