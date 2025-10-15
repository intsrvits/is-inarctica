from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.models.task import TaskMigration
from inarctica_migration.utils import CloudBitrixToken
from inarctica_migration.functions.task_migration.bx_rest_request import bx_tasks_task_list
from inarctica_migration.models.group import Group


def initialization_tasks_in_db():
    """"""
    bulk_data = []

    migrated_group_ids = dict(Group.objects.all().values_list("origin_id", "destination_id"))
    qs_initialized_tasks = TaskMigration.objects.all().values_list("cloud_id", flat=True)

    cloud_token = CloudBitrixToken()
    all_cloud_tasks = bx_tasks_task_list(cloud_token)

    try:
        for task in all_cloud_tasks:
            task_still_not_init: bool = task['id'] not in qs_initialized_tasks
            task_group_migrated: bool = int(task['groupId']) in migrated_group_ids

            if task_still_not_init:
                if task_group_migrated:
                    bulk_data.append(
                        TaskMigration(
                            cloud_id=int(task['id']),
                            cloud_parent_id=int(task['parentId']) if task['parentId'] else None,
                            group_is_sync=True,
                        )
                    )
                else:  # Если группа не была перенесена
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
                f"Всего в бд: {len(qs_initialized_tasks) + len(bulk_data)}"
            ),
            with_tags=False
        )

