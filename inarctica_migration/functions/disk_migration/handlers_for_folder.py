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

    # 1. Сливаем две модели для получения карты с полным представлением об имеющихся связях
    storage_relation_map: dict[int, int] = dict(Storage.objects.all().values_list("cloud_id", "box_id"))
    folders_relation_map: dict[int, int] = dict(Folder.objects.all().values_list("cloud_id", "box_id"))
    merged_relation_map = {**storage_relation_map, **folders_relation_map}

    # 2. Получаем структуру узла и списка ID его ближайших детей
    storage_tree_structure: dict[int, list[int]] = recursive_descent(
        token=cloud_token,
        object_type="folder",
        cloud_parent_id=cloud_storage_id,
    )

    # 3. Упорядоченный список используемых ID для указанного хранилища. (*Упорядочен от ближних узлов к более низким)
    # [1:] Потому что первый элемент есть наш cloud_storage_id
    origin_folder_id_list = ordered_hierarchy(storage_tree_structure)[1:]

    # 4.1 Забираем объект хранилища для статистик
    storage = Storage.objects.get(cloud_id=cloud_storage_id)

    # 4.2 Проверяем на возможную синхронизацию по кол-ву папок
    # (UPD: очень не надежно, но в контексте одноразовой миграции - ок)
    storage.folders_in_cloud = len(origin_folder_id_list)
    if storage.folders_in_box == storage.folders_in_cloud:
        storage.folders_sync = True
        storage.save()

        debug_point("✅ Создание папок в хранилищах _synchronize_folders_for_storage\n"
                    f"Создано | Всего (box) | Всего (cloud)\n"
                    f"{0:<15} | {storage.folders_in_box:<14} | {storage.folders_in_cloud:<17}\n\n"

                    f"boxID={storage.box_id}\n"
                    f"https://bitrix24.inarctica.com/bitrix/tools/disk/focus.php?folderId={storage.box_id}&action=openFolderList&ncc=1\n\n"
                    f"cloudID={storage.cloud_id}\n"
                    f"https://inarctica.bitrix24.ru/bitrix/tools/disk/focus.php?folderId={storage.cloud_id}&action=openFolderList&ncc=1\n\n",
                    with_tags=False,
                    )
        return

    folders_to_skip = []

    try:
        # 5. Забираем все папки облачного портала, которые будем переносить
        # 5.1 Подготовка к батчу
        # todo тут get все ломает - т.к берет ссылку на объект группового диска надо getchildren
        for folder_id in origin_folder_id_list:
            taking_methods.append((str(folder_id), "disk.folder.get", {"id": folder_id}))

        # 5.2 Батч
        all_cloud_storage_folders = cloud_token.batch_api_call(taking_methods)

        # 6. Перебор всех забранных папок и создание подобных на коробочном портале
        for folder_id, folder_attributes in all_cloud_storage_folders.successes.items():

            if folder_id in folders_to_skip:
                continue

            # 7. Проверки неприятных случаев
            # 7.1 Папка уже перенесена и её связи записаны в бд
            if int(folder_attributes["result"]["ID"]) in merged_relation_map:
                folders_to_skip = [*folders_to_skip, int(folder_id), *storage_tree_structure[int(folder_id)]]

                origin_folder_id_list = [
                    f_id for f_id in origin_folder_id_list if f_id not in [*storage_tree_structure[int(folder_id)], int(folder_id)]
                ]

                continue
                # try:
                #     origin_folder_id_list.remove(int(folder_id))
                #
                # except:
                #     box_parent_id = merged_relation_map[folder_attributes["result"]["REAL_OBJECT_ID"]]
                #     name = folder_attributes["result"]["NAME"]
                #     params = {"id": box_parent_id, "data": {"NAME": name}}
                #
                #     addsubfolder_result = _bx_folder_addsubfolder(box_token, params)
                #     added_box_folder_id = int(addsubfolder_result["result"]["REAL_OBJECT_ID"])
                #
                #     merged_relation_map[int(folder_attributes["result"]["ID"])] = added_box_folder_id
                #     bulk_data.append(
                #         Folder(
                #             cloud_id=folder_attributes["result"]["ID"],
                #             box_id=added_box_folder_id,
                #             parent_cloud_id=folder_attributes["result"]["PARENT_ID"],
                #             parent_box_id=box_parent_id,
                #         )
                #     )

            # 7.2 Папка не является диском группы
            elif folder_attributes["result"]["ID"] != folder_attributes["result"]["REAL_OBJECT_ID"]:
                # 7.2.1 Добавляем диск группы в папку и забываем про него и его дочерние папки
                # todo Групповый диск можно вложить в обычную папку - если так кто-то сделал нужно переписать логику

                folders_to_skip = [*folders_to_skip, *storage_tree_structure[int(folder_id)]]

                origin_folder_id_list = [
                    f_id for f_id in origin_folder_id_list if f_id not in [*storage_tree_structure[int(folder_id)], int(folder_id)]
                ]

                # 7.2.2 Подготавливаем статистику к выводу
                group_folders_cnt += 1 + len(storage_tree_structure[int(folder_id)])
                continue

            # 7.3 Поведение при всех вложенных папок
            else:
                cloud_id = int(folder_attributes["result"]["REAL_OBJECT_ID"])
                cloud_parent_id = int(folder_attributes["result"]["PARENT_ID"])

                # 7.3.1 Если у найденной папки не существует пары то скип её
                # todo дубль логики
                if merged_relation_map.get(cloud_parent_id):
                    box_parent_id = merged_relation_map[cloud_parent_id]
                else:
                    folders_to_skip = [*folders_to_skip, cloud_id],
                    origin_folder_id_list = origin_folder_id_list[1:]
                    continue

            name = folder_attributes["result"]["NAME"]
            origin_folder_id_list = origin_folder_id_list[1:]

            params = {"id": box_parent_id, "data": {"NAME": name}}

            addsubfolder_result = _bx_folder_addsubfolder(box_token, params)
            added_box_folder_id = int(addsubfolder_result["result"]["REAL_OBJECT_ID"])

            merged_relation_map[int(cloud_id)] = added_box_folder_id
            bulk_data.append(
                Folder(
                    cloud_id=cloud_id,
                    box_id=added_box_folder_id,
                    parent_cloud_id=cloud_parent_id,
                    parent_box_id=box_parent_id,
                )
            )

    except Exception as exc:
        debug_point(
            "Создание папок в хранилищах _synchronize_folders_for_storage\n"
            "❌ Произошла ошибка при синхронизации папок в хранилище synchronize_folders_for_storage \n"
            f"ID={storage.box_id}\n"
            f"https://bitrix24.inarctica.com/bitrix/tools/disk/focus.php?folderId={storage.box_id}&action=openFolderList&ncc=1\n\n"
            f"cloudID={storage.cloud_id}\n"
            f"https://inarctica.bitrix24.ru/bitrix/tools/disk/focus.php?folderId={storage.cloud_id}&action=openFolderList&ncc=1\n\n"
            f"{exc}",
        )
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
            ],
            update_conflicts=True,
        )

        storage.folders_in_box += len(bulk_data)
        if storage.folders_in_box == storage.folders_in_cloud:
            storage.folders_sync = True

        storage.save()

        debug_point("Создание папок в хранилищах _synchronize_folders_for_storage\n"
                    f"Создано | Всего (box) | Всего (cloud)\n"
                    f"{len(bulk_data):<15} | {storage.folders_in_box:<14} | {storage.folders_in_cloud:<17}\n\n"
                    f"Папок связанных с дисками групп: {group_folders_cnt}\n"
                    f"boxID={storage.box_id}\n"
                    f"https://bitrix24.inarctica.com/bitrix/tools/disk/focus.php?folderId={storage.box_id}&action=openFolderList&ncc=1\n\n"
                    f"cloudID={storage.cloud_id}\n"
                    f"https://inarctica.bitrix24.ru/bitrix/tools/disk/focus.php?folderId={storage.cloud_id}&action=openFolderList&ncc=1\n\n"
                    )
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
