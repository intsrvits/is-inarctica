from inarctica_migration.functions.disk_migration.bx_rest_requests import bx_disk_attachedObject_get, bx_storage_getlist, bx_disk_storage_uploadFile
from inarctica_migration.functions.disk_migration.handlers_for_file import get_file_content
from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.task_migration.bx_rest_request import bx_tasks_task_list
from inarctica_migration.functions.task_migration.tasks_comments.handlers import clean_post_message
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from inarctica_migration.models import TaskMigration, TaskAttachedFiles, User


def _initialize_file_availability(cloud_tasks_by_id: dict[int, dict]):
    """
    Инициализирует наличие прикрепленных файлов для задач, которые были
    перенесены без синхронизации файлов. Обновляет объекты TaskMigration
    с количеством прикрепленных файлов на основе данных от Bitrix.
    """

    bulk_data = []

    # Берём задачи - которые были перенесены, но без синхронизации прикрепленных файлов
    initialized_in_db_task: list[int] = list(TaskMigration.objects.filter(box_group_id__isnull=False, file_synced=False).values_list("cloud_id", flat=True))

    try:
        for cloud_task_id, task_data in cloud_tasks_by_id.items():
            # Если задача не перенесена, то пропускаем
            if cloud_task_id not in initialized_in_db_task:
                continue

            # При отсутствии файлов в респонсе битрикс не отдаёт это поле, либо отдаёт False. Иначе отдаёт массив с ID
            if task_data.get("ufTaskWebdavFiles"):
                bulk_data.append(TaskMigration(
                    cloud_id=cloud_task_id,
                    attached_files=len(task_data.get("ufTaskWebdavFiles")),
                ))
                continue

            bulk_data.append(TaskMigration(
                cloud_id=cloud_task_id,
                file_synced=True,
            ))

    except Exception as exc:
        debug_point(
            "initialize_file_availability\n"
            "Произошла ошибка при инициализации задач с прикрепленными файлами\n\n"
            f"{exc}"
        )
        raise

    finally:
        TaskMigration.objects.bulk_create(
            bulk_data,
            unique_fields=["cloud_id"],
            update_fields=["attached_files", "file_synced"],
            update_conflicts=True,
        )
        debug_point(
            "initialize_file_availability\n"
            f"Найдено {len(bulk_data)} не синхронизованных по файлам задач\n\n"
        )


def migrate_tasks_files():
    """"""
    bulk_data = []

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    params = {"filter": {"ENTITY_TYPE": "user"}}

    # Box {user_id: storage}
    user_storages = bx_storage_getlist(box_token, params)
    user_id_storage_map: dict[int, dict] = {int(storage["ENTITY_ID"]): storage for storage in user_storages}

    user_map: dict[int, int] = dict(User.objects.all().values_list("origin_id", "destination_id"))

    params = {
        "select": ["ID", "UF_TASK_WEBDAV_FILES"]
    }

    all_cloud_tasks = bx_tasks_task_list(cloud_token, params)
    cloud_tasks_by_id = {int(task['id']): task for task in all_cloud_tasks}

    _initialize_file_availability(cloud_tasks_by_id)

    tasks_for_process_qs = TaskMigration.objects.filter(box_group_id__isnull=False, file_synced=False)

    for task in tasks_for_process_qs:
        task_cloud_id = task.cloud_id
        task_box_id = task.box_id

        if task.file_synced:
            continue

        try:
            if task_cloud_id in cloud_tasks_by_id:
                attached_files = cloud_tasks_by_id[task_cloud_id]["ufTaskWebdavFiles"]
                for file_id in attached_files:
                    cloud_attached_file = bx_disk_attachedObject_get(cloud_token, {"id": file_id})
                    file_content = get_file_content(cloud_attached_file["NAME"], cloud_attached_file["DOWNLOAD_URL"])

                    cloud_file_creator_id = int(cloud_attached_file["CREATED_BY"])
                    cloud_creator_id = user_map.get(cloud_file_creator_id) if user_map.get(cloud_file_creator_id) else 1

                    storage_to_upload = user_id_storage_map[cloud_creator_id] if user_id_storage_map.get(cloud_creator_id) else 1
                    box_storage_id = storage_to_upload["ID"]

                    params_to_upload = {
                        "id": box_storage_id,
                        "fileContent": file_content,
                        "data": {"NAME": cloud_attached_file["NAME"]},
                        "generateUniqueName": True,
                    }

                    box_attachment_file_id = int(bx_disk_storage_uploadFile(box_token, params_to_upload)["result"]["ID"])

                    bulk_data.append(TaskAttachedFiles(
                        cloud_id=cloud_attached_file["ID"],
                        box_id=box_attachment_file_id,
                        cloud_obj_id=cloud_attached_file["OBJECT_ID"],
                        cloud_task_id=task_cloud_id,
                        box_task_id=task_box_id,
                    ))

                debug_point(f"Перенесено {len(attached_files)} в хранилища"
                            f"cloudIf={task_cloud_id}"
                            f"boxId={task_box_id}",
                            with_tags=False)

            task.file_synced = True
            task.save()

        except Exception as exc:
            debug_point("Произошла ошибка при переносе файлов для задачи\n"
                        f"cloudId: {task_cloud_id}\n"
                        f"boxId: {task_box_id}\n\n"
                        f"{exc}")

        finally:
            TaskAttachedFiles.objects.bulk_create(
                bulk_data,
                unique_fields=["cloud_id"],
                update_fields=["box_id", "cloud_obj_id", "cloud_task_id", "box_task_id"],
                update_conflicts=True,
            )

            debug_point(f"Перенесено {len(bulk_data)} файлов в хранилища")


def attach_file_to_task():
    """"""
    bulk_files_data = []

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    # Берём задачи с прикрепленными файлами
    task_to_process_qs = TaskMigration.objects.filter(box_group_id__isnull=False, file_synced=False)
    file_ids_map = dict(TaskAttachedFiles.objects.values_list("cloud_id", "box_id"))

    params = {
        "select": ["ID", "UF_TASK_WEBDAV_FILES"]
    }

    all_cloud_tasks = bx_tasks_task_list(cloud_token, params)
    cloud_tasks_by_id = {int(task['id']): task for task in all_cloud_tasks}

    try:
        # Прикрепляем к задаче файлы (ранее перенесенные на диск)
        for task in task_to_process_qs:
            cloud_task_id = task.cloud_id
            box_task_id = task.box_id
            # if cloud_task_id != 35:
            #     continue

            cloud_attached_files = cloud_tasks_by_id[cloud_task_id]["ufTaskWebdavFiles"]
            box_attached_files = []
            for file_id in cloud_attached_files:
                box_file_id = file_ids_map[file_id]
                box_attached_files.append(box_file_id)
                box_attached_file_id = box_token.call_api_method("tasks.task.files.attach", {"taskId": box_task_id, "fileId": box_file_id})["result"]["attachmentId"]
                bulk_files_data.append(TaskAttachedFiles(
                    cloud_id=file_id,
                    box_obj_id=int(box_attached_file_id)
                ))

            task.file_synced = True
            task.save()

    except Exception as exc:
        debug_point(f"Произошла ошибка при переносе файлов:\n"
                    f"{exc}")

    finally:

        TaskAttachedFiles.objects.bulk_create(
            bulk_files_data,
            unique_fields=["cloud_id"],
            update_fields=["box_obj_id"],
            update_conflicts=True,
        )
        debug_point(f"В задачи добавлено {len(bulk_files_data)} файлов")


def update_tasks_descriptions():
    """После прикрепления файлов к задаче - обновляет BBкоды в описании задач"""
    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    # Берём те задачи у которых есть прикрепленные файлы - но описание не было изменено
    tasks_to_update = TaskMigration.objects.filter(attached_files__gt=0, desc_updated=False)

    params = {
        "select": ["ID", "DESCRIPTION"]
    }

    all_cloud_tasks = bx_tasks_task_list(cloud_token, params)
    cloud_tasks_by_id = {int(task['id']): task for task in all_cloud_tasks}

    replace_file_id_map = dict(TaskAttachedFiles.objects.values_list("cloud_obj_id", "box_id"))
    try:
        for task in tasks_to_update:
            cloud_task_id = task.cloud_id
            box_task_id = task.box_id
            # if box_task_id != 228:
            #     continue
            task_description = cloud_tasks_by_id[cloud_task_id]['description']

            prepared_descripton = clean_post_message(task_description, replace_file_id_map)
            box_token.call_api_method("tasks.task.update", {"taskId": box_task_id, "fields": {"DESCRIPTION": prepared_descripton}})
            task.desc_updated = True
            task.save()

            debug_point("Обновлён комментарий в задача:\n\n"
                        f"cloudId: {cloud_task_id}\n"
                        f"https://inarctica.bitrix24.ru/workgroups/group/379/tasks/task/view/{cloud_task_id}/\n\n"
                        f"boxId: {box_task_id}\n\n"
                        f"https://bitrix24.inarctica.com/company/personal/user/1/tasks/task/view/{box_task_id}/\n\n",
                        with_tags=False)

    except Exception as exc:
        debug_point("Ошибка при обновлении описания\n"
                    f"cloudId: {cloud_task_id}\n"
                    f"https://inarctica.bitrix24.ru/workgroups/group/379/tasks/task/view/{cloud_task_id}/\n\n"
                    f"boxId: {box_task_id}\n\n"
                    f"https://bitrix24.inarctica.com/company/personal/user/1/tasks/task/view/{box_task_id}/\n\n",
                    f"{exc}")
