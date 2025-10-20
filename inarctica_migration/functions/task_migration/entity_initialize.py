from inarctica_migration.utils import CloudBitrixToken
from inarctica_migration.models import Group, TaskMigration

from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.task_migration.bx_rest_request import bx_tasks_task_list


def initialization_tasks_in_db():
    """Инициализируем задачи в БД"""
    bulk_data = []

    migrated_group_ids = dict(Group.objects.all().values_list("origin_id", "destination_id"))
    qs_initialized_tasks = TaskMigration.objects.all().values_list("cloud_id", flat=True)

    cloud_token = CloudBitrixToken()
    all_cloud_tasks = bx_tasks_task_list(cloud_token)

    try:
        for task in all_cloud_tasks:
            task_still_not_init: bool = task['id'] not in qs_initialized_tasks
            task_group_migrated: bool = int(task['groupId']) in migrated_group_ids

            if task_still_not_init:  # Задача не инициализирована
                if task_group_migrated:  # Группа у задачи синхронизована
                    bulk_data.append(
                        TaskMigration(
                            cloud_id=int(task['id']),
                            cloud_parent_id=int(task['parentId']) if task['parentId'] else None,
                            group_is_sync=True,
                        )
                    )
                else:  # Группа у задачи не синхронизована
                    bulk_data.append(
                        TaskMigration(
                            cloud_id=int(task['id']),
                            cloud_parent_id=int(task['parentId']) if task['parentId'] else None,
                            group_is_sync=False,
                        )
                    )

    except Exception as exc:
        debug_point(
            message=(
                "❌ Произошла ошибка при инициализации задач\n"
                f"ID задачи: {task['id']}\n\n"
                f"{exc}"
            )
        )

    finally:
        # Избавляемся от дублей в bulk_data (Битрикс может отдавать две сущности с одинаковым ID)
        unique_bulk_data = {}
        for obj in bulk_data:
            unique_bulk_data[obj.cloud_id] = obj

        bulk_data = list(unique_bulk_data.values())

        # Обновляем данные в БД
        TaskMigration.objects.bulk_create(
            bulk_data,
            batch_size=1000,
            unique_fields=["cloud_id"],
            update_fields=["cloud_parent_id"],
            update_conflicts=True,
        )

        debug_point(
            message=(
                "Инициализация задач закончена.\n\n"
                f"Всего на облачном портале: {len(all_cloud_tasks)}\n"
                f"Перенесено сейчас: {len(bulk_data)}\n"
                f"Всего в бд: {TaskMigration.objects.all().count()}"
            ),
            with_tags=False
        )
