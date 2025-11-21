from typing import Dict, List

from django.utils.dateparse import parse_datetime

from b24.models.b_forum_message import BForumMessage
from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.log_migration.handlers import get_sorted_by_time_blogposts
from inarctica_migration.models import LogMigration, CommentMigration, TaskMigration
from inarctica_migration.utils import CloudBitrixToken

from b24.models.b_blog_post import BBlogPost

from inarctica_migration.functions.task_migration.tasks_comments.handlers import get_comments_to_migration


def update_blogposts_dt():
    """Обновляем дату создания полей в бд, в соответствии с хронологическим порядок на облачном портале"""
    bulk_data = []

    blogpost_map: Dict[int, int] = dict(LogMigration.objects.filter(is_synced=True).values_list("box_id", "cloud_id"))

    cloud_token = CloudBitrixToken()
    all_cloud_blogs = get_sorted_by_time_blogposts(cloud_token)
    all_cloud_blogs_by_id = {int(blog["ID"]): blog for blog in all_cloud_blogs}

    box_posts = BBlogPost.objects.using("shhtunnel_db").filter(id__in=blogpost_map.keys())
    for post in box_posts:
        cloud_post_id = blogpost_map[post.id]

        if cloud_post_id not in all_cloud_blogs_by_id:
            debug_point(f"REST не отдал блогпост с коробочным ID={post.id}!!!")
            continue

        dt = parse_datetime(all_cloud_blogs_by_id[cloud_post_id]["DATE_PUBLISH"])

        post.date_create = dt
        post.date_publish = dt

        bulk_data.append(post)

    BBlogPost.objects.using("shhtunnel_db").bulk_update(bulk_data, ["date_create", "date_publish"])
    debug_point(f"Обновлено {len(bulk_data)} блогпостов."
                f" Всего на облаке: {len(all_cloud_blogs_by_id)}."
                f" Всего на коробке: {len(box_posts)}")


def update_comments_dt():
    """Обновляем дату создания полей в бд, в соответствии с хронологическим порядок на облачном портале"""
    bulk_data = []

    all_cloud_tasks: List[int] = list(TaskMigration.objects.filter(is_synced=True).values_list("cloud_id", flat=True))
    comments_map: Dict[int, int] = dict(CommentMigration.objects.values_list("box_id", "cloud_id"))

    cloud_token = CloudBitrixToken()
    all_cloud_comments_by_id: Dict[int, dict] = dict()
    for cloud_task_id in all_cloud_tasks:
        task_comments: Dict[int, dict] = get_comments_to_migration(cloud_token, cloud_task_id)
        all_cloud_comments_by_id |= task_comments

    skipped = 0
    box_comments = BForumMessage.objects.using("shhtunnel_db").all()
    for comment in box_comments:
        cloud_comment_id = comments_map.get(comment.id, 0)
        if cloud_comment_id not in all_cloud_comments_by_id:
            skipped += 1
            continue

        dt = parse_datetime(all_cloud_comments_by_id[cloud_comment_id]["POST_DATE"])

        comment.post_date = dt
        comment.edit_date = dt

        bulk_data.append(comment)

    BForumMessage.objects.using("shhtunnel_db").bulk_update(bulk_data, ["post_date", "edit_date"])
    debug_point(f"Обновлено {len(bulk_data)} блогпостов."
                f" Всего на облаке: {len(all_cloud_comments_by_id)}."
                f" Всего на коробке: {len(comments_map)} BForumMessage {len(box_comments)}\n"
                f" Пропущено = {skipped}")
