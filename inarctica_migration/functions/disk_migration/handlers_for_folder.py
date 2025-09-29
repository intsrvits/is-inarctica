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
        folder_ids_map: dict[int, int],
):
    """
    Функция отчищает всё root-папку (хранилище) от всех её дочерних, кроме дочерних в виде ссылок на диск группы.

    :param box_token: Токен портала на котором работаем.
    :param folder_ids_map: REAL_OBJECT_IDs папок, которые нужно зачистить.
    """
    storage_applicant_id = ""
    taking_methods = []

    # Собираем методы для батч-запроса на взятие всех ближайших детей для root-папок (хранилищ)
    for folder_id in folder_ids_map.keys():
        taking_methods.append((str(folder_id), "disk.folder.getchildren", {"id": folder_id}))

    try:
        applicants_for_removal = box_token.batch_api_call(taking_methods)
        if applicants_for_removal.errors:
            debug_point("Удаление папок delete_folders_for_storage\n"
                        "❌ Произошла ошибка во время батч-запроса\n"
                        f"{applicants_for_removal.errors}",
                        )
            raise

        # Для каждого хранилища и его ближайших детей выполняем рекурсивное очищение
        for storage_applicant_id, applicant_data in applicants_for_removal.successes.items():
            group_trees_cnt, deleted_trees_cnt = 0, 0
            all_subfolders = applicant_data["result"]

            # Если хранилище имеет вложенные папки
            if all_subfolders:
                for folder in all_subfolders:
                    folder_applicant_id = folder["ID"]
                    applicant_object_id = folder["REAL_OBJECT_ID"]

                    # Пропускаем тех, которые являются ссылками на диски групп и проектов
                    if folder_applicant_id != applicant_object_id:
                        group_trees_cnt += 1
                        continue

                    box_token.call_api_method("disk.folder.deletetree", {"id": folder_applicant_id})
                    deleted_trees_cnt += 1
            
            if len(all_subfolders) - deleted_trees_cnt != 0:
                debug_point("Удаление папок delete_folders_for_storage\n"
                            f"Удалено {deleted_trees_cnt}\n\n"
                            "⚠️ Удалены не все папки \n"
                            f"Удалено | Всего | Групповых папок\n"
                            f"{deleted_trees_cnt:<15} | {len(all_subfolders):<8} | {group_trees_cnt:<17}\n\n"
                            f"boxID={storage_applicant_id}\n"
                            f"https://bitrix24.inarctica.com/bitrix/tools/disk/focus.php?folderId={storage_applicant_id}&action=openFolderList&ncc=1\n\n"
                            f"cloudID={folder_ids_map[int(storage_applicant_id)]}\n"
                            f"https://inarctica.bitrix24.ru/bitrix/tools/disk/focus.php?folderId={folder_ids_map[int(storage_applicant_id)]}&action=openFolderList&ncc=1\n\n"
                            )

    except Exception as exc:
        debug_point("Удаление папок delete_folders_for_storage\n"
                    "❌ Произошла ошибка во время обработки коробочного хранилища\n"
                    f"boxID={storage_applicant_id}\n"
                    f"https://bitrix24.inarctica.com/bitrix/tools/disk/focus.php?folderId={storage_applicant_id}&action=openFolderList&ncc=1\n\n"
                    f"cloudID={folder_ids_map[int(storage_applicant_id)]}\n"
                    f"https://inarctica.bitrix24.ru/bitrix/tools/disk/focus.php?folderId={folder_ids_map[int(storage_applicant_id)]}&action=openFolderList&ncc=1\n\n"
                    f"{exc}"
                    )
