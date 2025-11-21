from typing import Dict, Tuple, List

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

def left_from_all_groups():
    """"""
    methods = []

    cloud_token = CloudBitrixToken()
    all_groups = cloud_token.call_list_method("sonet_group.user.groups")
    for group in all_groups:
        methods.append((str(group['GROUP_ID']), 'sonet_group.user.delete', {"GROUP_ID": group['GROUP_ID'], "USER_ID": 1897}))

    batch_result = cloud_token.batch_api_call(methods)
    return batch_result


def join_in_all_groups():
    methods = []

    cloud_token = CloudBitrixToken()
    all_groups = Group.objects.all()
    for group in all_groups:
        methods.append((str(group.origin_id), 'sonet_group.user.add', {"GROUP_ID": group.origin_id, "USER_ID": 1897}))

    batch_result = cloud_token.batch_api_call(methods, timeout=30)
    return batch_result


def get_all_blogposts_by_dest(token: CloudBitrixToken, group_ids) -> Dict[str, Dict]:
    """Возвращает словарь, где ключ это S{group_id} или UA, а значение словарь с блог постами"""
    all_blogposts: Dict[str, Dict] = dict()
    for group_id in group_ids:
        group_blogposts = token.call_list_method("log.blogpost.get", {"LOG_RIGHTS": [f"SG{group_id}"]})
        if group_blogposts:
            all_blogposts[str(group_id)] = group_blogposts

    ua_blogposts = token.call_list_method("log.blogpost.get", {"LOG_RIGHTS": "UA"})
    all_blogposts["UA"] = ua_blogposts

    return all_blogposts


def get_structure_by_blogpost_ids(all_blogposts_by_dest):
    """Вернет словарь, где ключ это blogpost ID, а значение это кортеж из blogpost_data и месте назначения т.е группа или UA"""
    result = dict()
    blogpost_in_groups = []
    for group_id, blogposts in all_blogposts_by_dest.items():
        if group_id == "UA":
            continue

        for blogpost in blogposts:
            result[int(blogpost["ID"])] = (group_id, blogpost)
            blogpost_in_groups.append(int(blogpost["ID"]))

    ua_blogposts = all_blogposts_by_dest["UA"]
    for blogpost in ua_blogposts:
        if int(blogpost["ID"]) in blogpost_in_groups:
            continue

        result[int(blogpost["ID"])] = ("UA", blogpost)

    return result


def migrate_blogposts():
    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    migrated_users_map: Dict[int, int] = dict(User.objects.all().values_list("origin_id", "destination_id"))
    migrated_group_map: Dict[int, int] = dict(Group.objects.all().values_list("origin_id", "destination_id"))
    migrated_blogposts_ids: List[int] = list(LogMigration.objects.filter(is_synced=True).values_list("cloud_id", flat=True))

    all_blogposts_by_dest: Dict[str, dict] = get_all_blogposts_by_dest(cloud_token, migrated_group_map.keys())
    prepared_blog_posts: Dict[int, Tuple[int, Dict]] = get_structure_by_blogpost_ids(all_blogposts_by_dest)

    for blogpost_id in sorted(prepared_blog_posts.keys()):
        if blogpost_id in migrated_blogposts_ids:
            continue

        current_blogpost = prepared_blog_posts[blogpost_id][1]
        cloud_dest = prepared_blog_posts[blogpost_id][0]  # Либо "UA", либо ID группы

        cloud_author_id = current_blogpost["AUTHOR_ID"]
        box_author_id = migrated_users_map.get(int(cloud_author_id), 1)

        if cloud_dest == "UA":
            dest = "UA"
        else:
            dest = f"SG{migrated_group_map[cloud_dest]}"

        params = {
            "USER_ID": box_author_id,
            "POST_MESSAGE": clean_detail_text(current_blogpost["DETAIL_TEXT"]),
            "POST_TITLE": clean_title(current_blogpost["DETAIL_TEXT"], current_blogpost["TITLE"]),
            "DEST": [dest],
        }

        # Если обнаружены прикрепленные файлы в облачном посте, то подготавливаем их к переносу
        if current_blogpost.get("FILES"):
            files_attributes: list[tuple[str, str]] = get_files_links(cloud_token, current_blogpost["FILES"])
            params["FILES"] = get_files_base64(files_attributes)

        migrated_blogpost_box_id = int(bx_log_blogpost_add(box_token, params)["result"])
        LogMigration.objects.create(
            cloud_id=blogpost_id,
            box_id=migrated_blogpost_box_id,
            dest=dest,
            is_synced=True,
        )

    debug_point("Миграция блогпостов окончена\n"
                f"На облаке {len(prepared_blog_posts)}"
                f"На коробке {len(LogMigration.objects.all().count())}")
