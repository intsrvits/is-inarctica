from django.contrib.postgres.aggregates import ArrayAgg

from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from inarctica_migration.models import Group, TaskMigration, StageMigration

from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.task_migration.bx_rest_request import bx_tasks_task_list, bx_task_stages_get
from inarctica_migration.functions.task_migration.fields import task_user_fields_in_upper, task_fields_in_upper


def initialization_tasks_in_db():
    """Инициализируем задачи в БД"""
    bulk_data = []

    migrated_group_ids = dict(Group.objects.all().values_list("origin_id", "destination_id"))
    qs_initialized_tasks = TaskMigration.objects.all().values_list("cloud_id", flat=True)

    cloud_token = CloudBitrixToken()
    params = {
        "select": ["ID", *task_fields_in_upper, *task_user_fields_in_upper]
    }
    all_cloud_tasks = bx_tasks_task_list(cloud_token, params=params)

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


def initialization_stages_in_db():
    """Инициализируем стадии канбана для групп в БД (включая уникальные стадии с обеих порталов)."""
    bulk_data = []
    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    # соответствие origin_id -> destination_id
    migrated_group_ids = dict(Group.objects.all().values_list("origin_id", "destination_id"))

    # {cloud_id: [cloud_group_ids...]} для исключения уже существующих связей
    stage_group_map = StageMigration.objects.values('cloud_id').annotate(
        groups=ArrayAgg('cloud_group_id', distinct=True)
    )
    stage_group_map = {row['cloud_id']: row['groups'] for row in stage_group_map}

    try:
        for cloud_group_id, box_group_id in migrated_group_ids.items():
            # Получаем стадии обеих порталов
            cloud_stages = bx_task_stages_get(cloud_token, {"entityId": cloud_group_id, "isAdmin": "Y"}) or {}
            box_stages = bx_task_stages_get(box_token, {"entityId": box_group_id, "isAdmin": "Y"}) or {}

            # Формируем {title -> id}
            cloud_title_id_map = {v["TITLE"]: int(k) for k, v in cloud_stages.items()}
            box_title_id_map = {v["TITLE"]: int(k) for k, v in box_stages.items()}

            # Все возможные названия стадий (объединение)
            all_titles = set(cloud_title_id_map) | set(box_title_id_map)

            for title in all_titles:
                cloud_id = cloud_title_id_map.get(title)
                box_id = box_title_id_map.get(title)

                # Проверим, не записано ли уже это cloud_id для этой группы
                if cloud_id and cloud_id in stage_group_map:
                    if cloud_group_id in stage_group_map[cloud_id]:
                        continue

                bulk_data.append(
                    StageMigration(
                        cloud_id=cloud_id,  # может быть None
                        box_id=box_id,  # может быть None
                        cloud_group_id=cloud_group_id,
                        box_group_id=box_group_id,
                    )
                )

    except Exception as exc:
        debug_point(
            "initialization_stages_in_db\n"
            "Ошибка при инициализации стадий:\n\n"
            f"{exc}"
        )

    finally:
        if bulk_data:
            StageMigration.objects.bulk_create(bulk_data, ignore_conflicts=True)

        debug_point(
            "initialization_stages_in_db\n"
            f"Проинициализировано: {len(bulk_data)} стадий\n"
            f"Всего в бд: {StageMigration.objects.count()} стадий\n"
        )
