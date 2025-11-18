from typing import Dict, List

from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.log_migration.handlers import get_sorted_by_time_blogposts
from inarctica_migration.models import LogMigration, CommentMigration, TaskMigration
from inarctica_migration.utils import CloudBitrixToken

from inarctica_migration.functions.task_migration.tasks_comments.handlers import get_comments_to_migration


def update_blogposts_dt():
    """Обновляем дату создания полей в бд, в соответствии с хронологическим порядок на облачном портале"""

    cloud_token = CloudBitrixToken()

    blogpost_map: Dict[int, int] = LogMigration.objects.filter(is_synced=True).values_list("box_id", "cloud_id")

    all_cloud_blogs = get_sorted_by_time_blogposts(cloud_token)
    all_cloud_blogs_by_id = {int(blog["ID"]): blog for blog in all_cloud_blogs}

    #blog_posts = BBlogPost.objects.all()
    blog_posts = []

    for index, blog_post in enumerate(blog_posts):
        try:
            blog_post_box_id = blog_post.id
            blog_post_cloud_id = blogpost_map[blog_post_box_id]

            if blog_post.id not in all_cloud_blogs_by_id:
                debug_point(f"REST не отдал блог с коробочным ID={blog_post_box_id}!!!")

            original_blog_post = all_cloud_blogs_by_id[blog_post_cloud_id]

            blog_post.date_create = original_blog_post["DATE_PUBLISH"]
            blog_post.date_publish = original_blog_post["DATE_PUBLISH"]

            blog_post.save()
            debug_point(f"Успешное сохранение поста с ID={blog_post.id}\n"
                        f"{index}/{len(blog_posts)}")

        except Exception as exc:
            debug_point(f"Произошла ошибка во время обновления блога с коробочным ID={blog_post.id}\n\n"
                        f"{exc}")
        finally:
            blog_post.save()

    def update_comments_dt():
        """Обновляем дату создания полей в бд, в соответствии с хронологическим порядок на облачном портале"""

        cloud_token = CloudBitrixToken()

        comments_map: Dict[int, int] = CommentMigration.objects.filter(is_synced=True).values_list("box_id", "cloud_id")
        all_cloud_tasks: List[int] = list(TaskMigration.objects.filter(is_synced=True).values_list("cloud_id", flat=True))

        #db_comments = BForumMessage.objects.all()
        db_comments_map = {db_comment.id: db_comment for db_comment in db_comments}
        for cloud_task_id in all_cloud_tasks:
            try:
                comments_to_updating = get_comments_to_migration(cloud_token, cloud_task_id)
                comment_ids_in_chrono: list[int] = sorted(comments_to_updating.keys())

                bulk_data = []
                for comment_id in comment_ids_in_chrono:
                    current_comment = comments_to_updating[comment_id]

                    post_date = current_comment["POST_DATE"]
                    commet_box_id = comments_map.get(comment_id)
                    if commet_box_id:
                        processed_comment = db_comments_map[commet_box_id]
                        processed_comment.post_date = post_date
                        processed_comment.save()
                        debug_point("Обновлён комментарий с box_id = ")

            except Exception as exc:
                debug_point("Произошла ошибка при обновлении dt-полей комментариев\n"
                            f"CLOUD TASK ID: {cloud_task_id}"
                            f"CLOUD COM ID: {comment_id}"
                            )

