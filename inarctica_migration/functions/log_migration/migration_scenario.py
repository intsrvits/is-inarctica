from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.log_migration.handlers_for_common_log import init_cloud_blogposts
from inarctica_migration.functions.log_migration.helpers import get_files_base64, get_files_links
from inarctica_migration.models import LogMigration, User
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from inarctica_migration.functions.log_migration.bx_rest_requests import bx_log_blogpost_get, bx_log_blogpost_add


def common_log_migration():
    """"""
    bulk_data = []
    
    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    existed_logs: dict[int, bool] = dict(LogMigration.objects.all().values_list("cloud_id", "is_synced"))
    migrated_users: dict[int, int] = dict(User.objects.all().values_list("origin_id", "destination_id"))

    # Получаем
    cloud_common_blogposts = bx_log_blogpost_get(cloud_token)
    sorted_cloud_blogposts = sorted(cloud_common_blogposts, key=lambda item: int(item["ID"]))
    sorted_cloud_blogposts_map = {int(blogpost["ID"]): blogpost for blogpost in sorted_cloud_blogposts}

    # Выделяем новые посты, которые не были инициализированы ранее в БД
    blogposts_to_init = []
    for blogpost_id in sorted_cloud_blogposts_map:
        if blogpost_id not in existed_logs:
            blogposts_to_init.append(sorted_cloud_blogposts_map[blogpost_id])

    # Сначала инициализируем новые посты - если они есть.
    if blogposts_to_init:
        new_blogposts = init_cloud_blogposts(blogposts_to_init, "UA")
        existed_logs = {**existed_logs, **new_blogposts}

    try:
        for blogpost in sorted_cloud_blogposts:
            # Если этот пост не перенесён (синхронизирован)
            if not existed_logs[int(blogpost["ID"])]:
                cloud_author_id = int(blogpost["AUTHOR_ID"])
                box_author_id = migrated_users.get(cloud_author_id, 1)

                params = {
                    "USER_ID": box_author_id,
                    "POST_MESSAGE": blogpost["DETAIL_TEXT"],
                    "POST_TITLE": blogpost["TITLE"],
                    "DEST": ["UA"]
                }

                if blogpost.get("FILES"):
                    files_attributes: list[tuple[str, str]] = get_files_links(cloud_token, blogpost["FILES"])

                    params["FILES"] = get_files_base64(files_attributes)
            migration_result = bx_log_blogpost_add(box_token, params)

            bulk_data.append(
                LogMigration(
                    cloud_id=int(blogpost["ID"]),
                    box_id=int(migration_result["result"]),
                    dest='UA',
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


def project_log_migration():
    """"""
    pass
