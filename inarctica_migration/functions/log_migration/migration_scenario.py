from inarctica_migration.functions.log_migration.debug_messages import error_log_message, success_log_message
from inarctica_migration.models import LogMigration, User, Group
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken

from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.log_migration.bx_rest_requests import bx_log_blogpost_add
from inarctica_migration.functions.log_migration.handlers import (
    init_blogpost_into_db,
    get_sorted_by_time_blogposts,
    get_files_base64,
    get_files_links, clean_title, clean_detail_text,
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

            current_blogpost = sorted_cloud_blogposts_map[int(cloud_blogpost_id)]
            cloud_author_id = current_blogpost["AUTHOR_ID"]
            box_author_id = migrated_users.get(int(cloud_author_id), 1)

            params = {
                "USER_ID": box_author_id,
                "POST_MESSAGE": clean_detail_text(current_blogpost["DETAIL_TEXT"]),
                "POST_TITLE": clean_title(current_blogpost["DETAIL_TEXT"], current_blogpost["TITLE"]),
                "DEST": ["UA"]
            }

            # Если обнаружены прикрепленные файлы в облачном посте, то подготавливаем их к переносу
            if current_blogpost.get("FILES"):
                try:
                    files_attributes: list[tuple[str, str]] = get_files_links(cloud_token, current_blogpost["FILES"])

                    params["FILES"] = get_files_base64(files_attributes)
                except:
                    pass

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
        debug_point(error_log_message(exc, cloud_blogpost_cnt=len(sorted_cloud_blogposts), box_blogpost_cnt=192+len(bulk_data), migrated_now=len(bulk_data)))

    finally:

        LogMigration.objects.bulk_create(
            bulk_data,
            batch_size=1000,
            unique_fields=["cloud_id"],
            update_fields=["box_id", "dest", "is_synced"],
            update_conflicts=True,
        )

        debug_point(success_log_message(cloud_blogpost_cnt=len(sorted_cloud_blogposts), box_blogpost_cnt=192+len(bulk_data), migrated_now=len(bulk_data)))


def _migrate_blogposts_for_feed(
        existed_logs: dict[int, bool],
        migrated_users: dict[int, int],
        migrated_groups: dict[int, int],
        cloud_group_id: int = None,
) -> dict[int, bool]:
    """"""

    dest = f"SG{cloud_group_id}" if cloud_group_id else None

    bulk_data = []

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    current_group = Group.objects.filter(origin_id=cloud_group_id).first()

    migrated_blogpost_cnt = 0
    if not current_group.blogposts_cnt:
        current_group.blogposts_cnt = 0

    # Получаем список всех облачных постов, отсортированный по дате созданию
    sorted_cloud_blogposts = get_sorted_by_time_blogposts(cloud_token, dest=cloud_group_id)
    sorted_cloud_blogposts_map = {int(blogpost["ID"]): blogpost for blogpost in sorted_cloud_blogposts}

    if len(sorted_cloud_blogposts) == 0:
        current_group.save()
        debug_point(success_log_message(cloud_blogpost_cnt=len(sorted_cloud_blogposts), box_blogpost_cnt=current_group.blogposts_cnt, migrated_now=0, cloud_dest=cloud_group_id, box_dest=migrated_groups[cloud_group_id]))

        return existed_logs

    # Обновляем список известных постов
    existed_logs = init_blogpost_into_db(sorted_cloud_blogposts_map, existed_logs, dest)

    try:
        # Обрабатываем все найденные посты
        for cloud_blogpost_id, is_synced in existed_logs.items():

            # Если уже синхронизовано, то пропускаем
            if is_synced:
                continue

            current_blogpost = sorted_cloud_blogposts_map[int(cloud_blogpost_id)]
            cloud_author_id = current_blogpost["AUTHOR_ID"]
            box_author_id = migrated_users.get(int(cloud_author_id), 1)

            params = {
                "USER_ID": box_author_id,
                "POST_MESSAGE": clean_detail_text(current_blogpost["DETAIL_TEXT"]),
                "POST_TITLE": clean_title(current_blogpost["DETAIL_TEXT"], current_blogpost["TITLE"]),
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
                    dest=dest if dest else "UA",
                    is_synced=True,
                )
            )

        current_group.blogposts_cnt += len(bulk_data)
        debug_point(success_log_message(cloud_blogpost_cnt=len(sorted_cloud_blogposts), box_blogpost_cnt=current_group.blogposts_cnt, migrated_now=len(bulk_data), cloud_dest=cloud_group_id, box_dest=migrated_groups[cloud_group_id]))

    except Exception as exc:
        debug_point(error_log_message(exc, cloud_blogpost_cnt=len(sorted_cloud_blogposts), box_blogpost_cnt=current_group.blogposts_cnt, migrated_now=len(bulk_data), cloud_dest=cloud_group_id, box_dest=migrated_groups[cloud_group_id]))

    finally:

        LogMigration.objects.bulk_create(
            bulk_data,
            batch_size=1000,
            unique_fields=["cloud_id"],
            update_fields=["box_id", "dest", "is_synced"],
            update_conflicts=True,
        )

        current_group.save()

        return existed_logs


def migrate_blogposts_for_portals():
    """"""

    existed_logs: dict[int, bool] = dict(LogMigration.objects.all().values_list("cloud_id", "is_synced"))
    migrated_users: dict[int, int] = dict(User.objects.all().values_list("origin_id", "destination_id"))
    migrated_groups: dict[int, int] = dict(Group.objects.all().values_list("origin_id", "destination_id"))

    # Перенос для постов в лентах групп
    for cloud_group_id in migrated_groups:
        # a = [225, 322, 227, 229, 231, 265, 171, 267, 269, 107, 241, 243, 346, 219, 221, 350, 223]
        # for cloud_group_id in a:

        existed_logs = _migrate_blogposts_for_feed(
            existed_logs=existed_logs,
            migrated_users=migrated_users,
            migrated_groups=migrated_groups,
            cloud_group_id=cloud_group_id,
        )

    debug_point("Миграция групповых новостных лент окончена")


def left_from_all_groups():
    """"""
    methods = []

    cloud_token = CloudBitrixToken()
    all_groups = cloud_token.call_list_method("sonet_group.user.groups")
    for group in all_groups:
        methods.append((str(group['GROUP_ID']), 'sonet_group.user.delete', {"GROUP_ID": group['GROUP_ID'], "USER_ID": 1897}))

    batch_result = cloud_token.batch_api_call(methods)
    return batch_result


def migrate_common_blogposts():
    existed_logs: dict[int, bool] = dict(LogMigration.objects.all().values_list("cloud_id", "is_synced"))
    migrated_users: dict[int, int] = dict(User.objects.all().values_list("origin_id", "destination_id"))
    migrated_groups: dict[int, int] = dict(Group.objects.all().values_list("origin_id", "destination_id"))

    existed_logs = _migrate_blogposts_for_feed(
        existed_logs=existed_logs,
        migrated_users=migrated_users,
        migrated_groups=migrated_groups,
    )

    debug_point("Миграция групповых новостных лент окончена")
