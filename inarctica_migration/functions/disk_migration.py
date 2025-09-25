from typing import Union

from inarctica_migration.functions.helpers import retry_decorator, async_debug_point, debug_point
from inarctica_migration.models import Storage, Folder
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken


@retry_decorator(attempts=3, delay=30)
def _bx_storage_getlist(token: CloudBitrixToken | BoxBitrixToken) -> Union[list, dict]:
    """Запрос disk.storage.getlist к REST API"""

    return token.call_list_method("disk.storage.getlist", timeout=100)


@retry_decorator(attempts=3, delay=30)
def _bx_folder_getchildren(
        token: CloudBitrixToken | BoxBitrixToken,
        parent_id: int,
        filter: dict = None,
        select: list = None,
) -> Union[list, dict]:
    """Запрос disk.folder.getchildren к REST API"""
    return token.call_list_method("disk.folder.getchildren", {"id": parent_id, "filter": filter, "select": select}, timeout=100)


@retry_decorator(attempts=3, delay=30)
def _bx_folder_addsubfolder(
        token: BoxBitrixToken,
        params: dict,
) -> dict:
    """Запрос disk.folder.addsubfolder к REST API"""
    return token.call_api_method("disk.folder.addsubfolder", params)


def _synchronize_storages(
        cloud_token: CloudBitrixToken,
        box_token: BoxBitrixToken
) -> dict:
    """
    Функция ищет и записывает в БД связи между одинаковыми по названию хранилищами

    После завершения работы в бд появляются записи об одинаковых хранилищах: origin_id, destination_id
    """
    cloud_storage_obj_id, box_storage_obj_id = None, None

    bulk_data = []

    storage_relation_map: dict[int, int] = dict(Storage.objects.all().values_list("origin_id", "destination_id"))

    try:
        current_cloud_storages = _bx_storage_getlist(cloud_token)
        current_box_storages = _bx_storage_getlist(box_token)

        # Сравниваем все хранилища облака со всеми хранилищами коробки для нахождения идентичных
        for cloud_storage in current_cloud_storages:
            for box_storage in current_box_storages:

                cloud_storage_obj_id = int(cloud_storage["ROOT_OBJECT_ID"])
                box_storage_obj_id = int(box_storage["ROOT_OBJECT_ID"])

                # Работаем только с несуществующими связями
                if storage_relation_map.get(cloud_storage_obj_id) is None:
                    if cloud_storage["NAME"] == box_storage["NAME"]:
                        bulk_data.append(
                            Storage(
                                origin_id=cloud_storage_obj_id,
                                destination_id=box_storage_obj_id,
                            )
                        )

                        storage_relation_map[cloud_storage_obj_id] = box_storage_obj_id

    except Exception as exc:
        debug_point(f"Произошла ошибка во время синхронизации облачного хранилища с ID {cloud_storage_obj_id} и коробочного с ID {box_storage_obj_id}: {exc}", with_tags=True)
        raise

    finally:
        unique_bulk_data = {
            storage.origin_id: storage
            for storage in bulk_data
        }.values()

        Storage.objects.bulk_create(
            unique_bulk_data,
            batch_size=1000,
            unique_fields=["origin_id"],
            update_fields=["destination_id"],
            update_conflicts=True,
        )

        debug_point(f"Обработано (создано) {len(unique_bulk_data)} связей между хранилищами. Всего связей {len(storage_relation_map)}", with_tags=False)
        return storage_relation_map

def _folders_recursive_descent(
        cloud_token: CloudBitrixToken,
        cloud_parent_id: int,
        result: Union[dict, None] = None
) -> dict[int, list]:
    """
    Рекурсивно получает структуру, где ключи это (все дочерние папки для cloud_parent_id и сама эта папка с cloud_parent_id),
    а значения это список всех дочерних папок для каждой из папок. Если папка не содержит в себе дочерней, то её список пуст []

    {
    cloud_parent_id: [child_id1, child_id2, ...],
    parent1_id: [],
    parent2_id: [],
    }
    """

    # Если дошли до конца, т.е у папки нет дочерних папок
    if result is None:
        result = {}

    try:
        nested_folders = _bx_folder_getchildren(
            cloud_token,
            cloud_parent_id,
            filter={"type": "folder"},
            select=["ID", "REAL_OBJECT_ID", "PARENT_ID"]
        )

        # Добавляем прямых детей
        child_ids = [int(folder["ID"]) for folder in nested_folders]
        result[cloud_parent_id] = child_ids

        # Рекурсия для детей
        for folder in nested_folders:
            folder_id = int(folder["ID"])
            _folders_recursive_descent(cloud_token, folder_id, result)

        return result

    except Exception as exc:

        debug_point(f"Ошибка в _folders_recursive_descent для корневой папки с облачным ID={cloud_parent_id}: {exc}", with_tags=True)
        raise


def ordered_hierarchy(structure):
    result = []
    for parent_id, children_id in structure.items():
        if not parent_id in result:
            result.append(parent_id)
        for child_id in children_id:
            if not child_id in result:
                result.append(child_id)

    return result

def _synchronize_folders_for_storage(
        cloud_token: CloudBitrixToken,
        box_token: BoxBitrixToken,
        cloud_storage_id: int,
        storage_relation_map: dict[int, int]
):
    """


    """
    taking_methods = []
    bulk_data = []

    folders_relation_map: dict[int, int] = dict(Folder.objects.all().values_list("origin_id", "destination_id"))

    folder_tree_structure: dict = _folders_recursive_descent(cloud_token, cloud_storage_id)
    origin_folder_id_list: list[int] = ordered_hierarchy(folder_tree_structure)

    try:
        # Забираем все найденные в хранилище папки (в т.ч. вложенные)
        for folder_id in origin_folder_id_list:
            taking_methods.append((str(folder_id), "disk.folder.get", {'id': folder_id}))

        all_cloud_storage_folders = cloud_token.batch_api_call(taking_methods)

        # Для всех папок создаём подобные на бокс портале
        for folder_id, folder_attributes in all_cloud_storage_folders.successes.items():
            cloud_real_object_id = folder_attributes["result"]["REAL_OBJECT_ID"]

            # Поведение если папка уже перенесенна и её связи записаны в бд
            if int(folder_attributes["result"]["REAL_OBJECT_ID"]) in folders_relation_map:
                origin_folder_id_list = origin_folder_id_list[1:]
                continue

            # Поведение при папка-хранилище (самой верхней папке в хранилище)
            if not folder_attributes["result"]["PARENT_ID"]:
                folders_relation_map[int(cloud_real_object_id)] = storage_relation_map[int(cloud_real_object_id)]
                origin_folder_id_list = origin_folder_id_list[1:]
                continue

            # Поведение при всех вложенных папок
            else:

                cloud_parent_id = int(folder_attributes["result"]["PARENT_ID"])
                box_parent_id = folders_relation_map[cloud_parent_id]


            name = all_cloud_storage_folders.successes[str(origin_folder_id_list[0])]['result']['NAME']
            origin_folder_id_list = origin_folder_id_list[1:]

            params = {"id": box_parent_id, "data": {"NAME": name}}

            addsubfolder_result = _bx_folder_addsubfolder(box_token, params)
            added_box_folder_id = addsubfolder_result["result"]["REAL_OBJECT_ID"]

            folders_relation_map[int(cloud_real_object_id)] = added_box_folder_id
            bulk_data.append(
                Folder(
                    origin_id=folder_id,
                    destination_id=added_box_folder_id,
                    parent_origin_id=cloud_parent_id,
                    parent_destination_id=box_parent_id,
                )
            )

    except Exception as exc:
        Folder.objects.bulk_create(
            bulk_data,
            unique_fields=["origin_id"],
            update_fields=["destination_id", "parent_origin_id", "parent_destination_id"],
            update_conflicts=True,
        )
        debug_point(f"Произошла ошибка в _synchronize_folders_for_storage (при синхронизации) : {exc}")
        raise

    finally:
        Folder.objects.bulk_create(
            bulk_data,
            unique_fields=["origin_id"],
            update_fields=["destination_id", "parent_origin_id", "parent_destination_id"],
            update_conflicts=True,
        )

        # len(folder_tree_structure) - 1 (Потому что мы не учитываем само хранилище, которое отдаётся нам как папка при запросе в битрикс)
        print(f"Создано новых {len(bulk_data)} папок. Всего папок на в этом хранилище: {len(folder_tree_structure) - 1}")
        return


def migrate_disk():
    """
    Пайплайн полной синхронизации дисков:
    1) Настройка связей между хранилищами
    2) Перенос структуры папок
    3) Перенос файлов
    """

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    # Настройка связей между хранилищами
    # {origin_id: destination_id, ...}
    storage_relation_map: dict[int, int] = _synchronize_storages(cloud_token=cloud_token, box_token=box_token)

    # Воссоздание структуры папок для КАЖДОГО из хранилищ
    for storage_relation in storage_relation_map:
        #todo убрать хардкод (пока тестим на своих дисках)
        if storage_relation != 19:
            continue

        _synchronize_folders_for_storage(
            cloud_token=cloud_token,
            box_token=box_token,
            cloud_storage_id=storage_relation,
            storage_relation_map=storage_relation_map,
        )
