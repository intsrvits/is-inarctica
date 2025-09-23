from typing import Union

from inarctica_migration.functions.helpers import retry_decorator
from inarctica_migration.models import Group, User, Storage, Folder
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from integration_utils.bitrix24.bitrix_token import BitrixToken


@retry_decorator(attempts=3, delay=30)
def _bx_storage_getlist(token: CloudBitrixToken | BoxBitrixToken) -> Union[list, dict]:
    """"""

    return token.call_list_method("disk.storage.getlist", timeout=100)


@retry_decorator(attempts=3, delay=30)
def _bx_folder_getchildren(
        token: CloudBitrixToken | BoxBitrixToken,
        parent_id: int,
        filter: dict = None,
        select: list = None,
) -> Union[list, dict]:
    """"""

    return token.call_list_method("disk.folder.getchildren", {"id": parent_id, "filter": filter, "select": select}, timeout=100)


@retry_decorator(attempts=3, delay=30)
def _bx_folder_get(
        token: CloudBitrixToken,
        filter: dict = None,
        select: list = None,
) -> Union[list, dict]:
    """"""

    return token.call_list_method("disk.folder.get")


def _synchronize_storages(cloud_token: CloudBitrixToken, box_token: BoxBitrixToken):
    """Создаём связи или обновляем их для одинаковых по названию хранилища"""
    bulk_data = []

    try:
        current_cloud_storages = _bx_storage_getlist(cloud_token)
        current_box_storages = _bx_storage_getlist(box_token)

        for cloud_storage in current_cloud_storages:
            for box_storage in current_box_storages:

                if cloud_storage["NAME"] == box_storage["NAME"]:
                    bulk_data.append(
                        Storage(
                            origin_id=int(cloud_storage["ROOT_OBJECT_ID"]),
                            destination_id=int(box_storage["ROOT_OBJECT_ID"]),
                        )
                    )

    except Exception as exc:
        print(f"Произошла ошибка во время синхронизации хранилищ: {exc}")
        raise

    finally:
        unique_bulk_data = {
            storage.origin_id: storage
            for storage in bulk_data
        }.values()

        Storage.objects.bulk_create(
            unique_bulk_data,
            unique_fields=["origin_id"],
            update_fields=["destination_id"],
            update_conflicts=True,
        )

        print(f"Обработано (создано/обновлено) {len(unique_bulk_data)} связей между хранилищами")
        return unique_bulk_data


def _folders_recursive_descent(cloud_token: CloudBitrixToken, cloud_parent_id: int, result: Union[dict, None] = None):
    """
    Рекурсивно строит плоскую структуру вида:
    {parent_id: [child_id1, child_id2, ...]}
    """
    if result is None:
        result = {}

    try:
        nested_folders = _bx_folder_getchildren(
            cloud_token,
            cloud_parent_id,
            filter={"type": "folder"},
            select=["ID", "PARENT_ID"]
        )

        # добавляем прямых детей
        child_ids = [int(folder["ID"]) for folder in nested_folders]
        result[cloud_parent_id] = child_ids

        # рекурсия для детей
        for folder in nested_folders:
            folder_id = int(folder["ID"])
            _folders_recursive_descent(cloud_token, folder_id, result)

        return result

    except Exception as exc:
        print(f"Ошибка в _folders_recursive_descent: {exc}")
        raise


def _synchronize_folders_for_storage(cloud_token: CloudBitrixToken, box_token: BoxBitrixToken, cloud_storage_id: int, storage_relation_map: dict[int, int]):
    """Создаём недостающие папки"""
    taking_methods = []
    adding_methods = []

    # folders_to_add: dict[str, list] = dict()

    folders_relation_map: dict[int, int] = dict(Folder.objects.all().values_list("origin_id", "destination_id", ))

    folder_tree_structure: dict = _folders_recursive_descent(cloud_token, cloud_storage_id)
    origin_folder_id_list: list[int] = list(folder_tree_structure.keys())

    # Те которые мы создаём в процессе чтобы не грузить бд на каждом цикле
    dynamic_created_folders: dict = folders_relation_map
    try:
        #todo делать пропуск если в бд уже естановлена связь для foldов
        for folder_id in origin_folder_id_list:
            taking_methods.append((str(folder_id), "disk.folder.get", {'id': folder_id}))

        batch_result = cloud_token.batch_api_call(taking_methods)

        for folder_id, folder_attributes in batch_result.successes.items():

            if not folder_attributes["result"]["PARENT_ID"]:
                dynamic_created_folders[int(folder_id)] = storage_relation_map[int(folder_id)]
                continue

            else:
                parent_id = dynamic_created_folders[int(folder_attributes["result"]["PARENT_ID"])]
                origin_folder_id_list = origin_folder_id_list[1:]

            name = batch_result.successes[str(origin_folder_id_list[0])]['result']['NAME']
            params = {"id": parent_id, "data": {"NAME": name}}
            result = box_token.call_api_method("disk.folder.addsubfolder", params)
            dynamic_created_folders[int(folder_id)] = result["result"]['ID']

            # if storage_relation_map.get(int(folder_id)):
            #     origin_folder_id_list = origin_folder_id_list[1:]
            #     name = batch_result.successes[str(origin_folder_id_list[0])]['result']['NAME']
            #     origin_folder_id_list = origin_folder_id_list[1:]
            #     params = {"id": storage_relation_map[int(folder_id)], "data": {"NAME": name}}
            #
            # else:
            #     name = batch_result.successes[str(origin_folder_id_list[0])]['result']['NAME']
            #     origin_folder_id_list = origin_folder_id_list[1:]
            #     params = {"id": dynamic_created_folders[int(folder_id)], "data": {"NAME": name}}
            #
            # result = box_token.call_api_method("disk.folder.addsubfolder", params)

            # print(folder_id, {"id": storage_relation_map[folder_id], "data": {"NAME": folder_attributes['result']["NAME"]}})
            # folders_to_add = []

        return result

    except Exception as exc:
        print(f"Произошла ошибка в _synchronize_folders_for_storage (при синхронизации) : {exc}")
        raise

    # for folder in folder_tree_structure:
    #     ...

    # return folder_tree_structure, origin_folder_list
    # Сначала создать все папки которые существуют на облаке

    # Затем пробежаться по их parent и расставить в правильном порядке


def migrate_main(cloud_token: CloudBitrixToken, box_token: BoxBitrixToken):
    """"""
    #_recursive_descent(cloud_token, _MAIN_DISK_STORAGE_ID)


def migrate_disk():
    """"""
    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    _synchronize_storages(cloud_token=cloud_token, box_token=box_token)

    # {origin_id: destination_id, ...}
    storage_relation_map: dict[int, int] = dict(Storage.objects.all().values_list("origin_id", "destination_id"))

    for storage_relation in storage_relation_map:
        #todo убрать хардкод (пока тестим на своих дисках)
        if storage_relation != 25893:
            continue

        res = _synchronize_folders_for_storage(
            cloud_token=cloud_token,
            box_token=box_token,
            cloud_storage_id=storage_relation,
            storage_relation_map=storage_relation_map,
        )

        return res
