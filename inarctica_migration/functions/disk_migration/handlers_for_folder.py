from inarctica_migration.models import Folder, Storage
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken

from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.disk_migration.bx_rest_requests import _bx_folder_addsubfolder
from inarctica_migration.functions.disk_migration.descent_by_recursion import ordered_hierarchy, recursive_descent


def _synchronize_folders_for_storage(
        cloud_token: CloudBitrixToken,
        box_token: BoxBitrixToken,
        cloud_storage_id: int,
):
    """


    """
    group_folders_cnt = 0
    taking_methods = []
    bulk_data = []

    storage_relation_map: dict[int, int] = dict(Storage.objects.all().values_list("cloud_id", "box_id"))
    folders_relation_map: dict[int, int] = dict(Folder.objects.all().values_list("real_obj_cloud_id", "real_obj_box_id"))
    merged_relation_map = {**storage_relation_map, **folders_relation_map}

    origin_folder_id_list: list[int] = ordered_hierarchy(cloud_token, 'folder', cloud_storage_id)[1:]
    storage = Storage.objects.get(cloud_id=cloud_storage_id)

    # len(origin_folder_id_list) - 1 (Потому что мы не учитываем само хранилище, которое отдаётся нам как папка при запросе в битрикс)
    storage.folders_in_cloud = len(origin_folder_id_list) - 1

    try:
        # Забираем все найденные в хранилище папки (в т.ч. вложенные)
        for folder_id in origin_folder_id_list:
            taking_methods.append((str(folder_id), "disk.folder.get", {'id': folder_id}))

        all_cloud_storage_folders = cloud_token.batch_api_call(taking_methods)

        # Для всех папок создаём подобные на бокс портале
        for folder_id, folder_attributes in all_cloud_storage_folders.successes.items():
            cloud_real_object_id = folder_attributes["result"]["REAL_OBJECT_ID"]

            # Поведение если папка уже перенесена и её связи записаны в бд
            if int(folder_attributes["result"]["REAL_OBJECT_ID"]) in merged_relation_map:
                origin_folder_id_list = origin_folder_id_list[1:]
                continue

            # Поведение при папка-хранилище (самой верхней папке в хранилище)
            if not folder_attributes["result"]["PARENT_ID"]:
                merged_relation_map[int(cloud_real_object_id)] = storage_relation_map[int(cloud_real_object_id)]
                origin_folder_id_list = origin_folder_id_list[1:]
                continue

            # Поведение при всех вложенных папок
            else:
                cloud_parent_id = int(folder_attributes["result"]["PARENT_ID"])
                box_parent_id = merged_relation_map[cloud_parent_id]

            name = all_cloud_storage_folders.successes[str(origin_folder_id_list[0])]['result']['NAME']
            origin_folder_id_list = origin_folder_id_list[1:]

            params = {"id": box_parent_id, "data": {"NAME": name}}

            if folder_attributes["result"]["ID"] != folder_attributes["result"]["REAL_OBJECT_ID"]:
                group_folders_cnt += 1
                continue

            addsubfolder_result = _bx_folder_addsubfolder(box_token, params)
            added_box_folder_id = addsubfolder_result["result"]["REAL_OBJECT_ID"]

            merged_relation_map[int(cloud_real_object_id)] = added_box_folder_id
            bulk_data.append(
                Folder(
                    cloud_id=folder_id,
                    box_id=int(addsubfolder_result["result"]["ID"]),
                    parent_cloud_id=cloud_parent_id,
                    parent_box_id=box_parent_id,
                    real_obj_cloud_id=cloud_real_object_id,
                    real_obj_box_id=added_box_folder_id,
                    parent_real_obj_cloud_id=folder_attributes["result"]["REAL_OBJECT_ID"],
                    parent_real_obj_box_id=merged_relation_map[int(folder_attributes["result"]["REAL_OBJECT_ID"])],
                )
            )

    except Exception as exc:
        debug_point(f"Произошла ошибка в при синхронизации папок в хранилище с boxRealObjID {storage.box_id:<5} : {exc}", with_tags=True)
        raise

    finally:
        Folder.objects.bulk_create(
            bulk_data,
            batch_size=1000,
            unique_fields=["cloud_id"],
            update_fields=[
                "box_id",
                "parent_cloud_id",
                "parent_box_id",
                "real_obj_cloud_id",
                "real_obj_box_id",
                "parent_real_obj_cloud_id",
                "parent_real_obj_box_id",
            ],
            update_conflicts=True,
        )

        storage.folders_in_box += len(bulk_data)
        if storage.folders_in_box == storage.folders_in_cloud:
            storage.folders_sync = True

        storage.save()

        debug_point(f"Создание папок. Хранилище с boxRealObjID {storage.box_id:<5} | Cоздано новых: {len(bulk_data):<3} | Сейчас на коробке: {storage.folders_in_box + len(bulk_data):<3} | Всего на облаке {storage.folders_in_cloud:<3} | Системных {group_folders_cnt}", with_tags=False)
        return


def delete_folders_for_storage(
        box_token: BoxBitrixToken,
        box_storage_id: int,
):
    """"""
    group_folders_cnt = 0
    taking_methods = []
    deleting_methods = []

    folders_hierarchy_map: dict[int, list[int]] = recursive_descent(box_token, 'folder', box_storage_id)
    folder_ids_to_delete: list[int] = list(folders_hierarchy_map.values())[0]

    try:
        for folder_id in folder_ids_to_delete:
            taking_methods.append((str(folder_id), "disk.folder.get", {'id': folder_id}))

        selected_folders = box_token.batch_api_call(taking_methods)

        for folder_id, folder_attributes in selected_folders.successes.items():
            box_id = folder_attributes["result"]["ID"]
            box_real_obj_id = selected_folders.successes[folder_id]['result']['REAL_OBJECT_ID']

            # Ловим случаи когда у нас подключен диск проекта (Их нельзя удалить) и пропускаем их
            if box_id != box_real_obj_id:
                group_folders_cnt += 1
                continue

            deleting_methods.append((str(folder_id), "disk.folder.deletetree", {'id': box_real_obj_id}))

        delete_result = box_token.batch_api_call(deleting_methods)

        if len(deleting_methods) > 0 or len(folder_ids_to_delete) > 0:
            debug_point(f"Удалено {len(deleting_methods)} ближайших к хранилищу с boxRealObjID={box_storage_id} папок. Всего было обнаружено: {len(folder_ids_to_delete)}. Групповых папок: {group_folders_cnt}", with_tags=False)

    except Exception as exc:
        debug_point(f"Произошла ошибка во время удаления папок из хранилища c boxRealObjID={box_storage_id}: {exc}", with_tags=True)

