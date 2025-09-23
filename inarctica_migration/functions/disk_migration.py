from typing import Union

from inarctica_migration.functions.helpers import retry_decorator
from inarctica_migration.models import Group, User, Storage
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from integration_utils.bitrix24.bitrix_token import BitrixToken

_MAIN_DISK_STORAGE_ID = 19


@retry_decorator(attempts=3, delay=30)
def _bx_storage_getlist(token: CloudBitrixToken | BoxBitrixToken) -> Union[list, dict]:
    """"""

    return token.call_list_method("disk.storage.getlist", timeout=100)


@retry_decorator(attempts=3, delay=30)
def _bx_folder_getchildren(token: CloudBitrixToken | BoxBitrixToken, parent_id: int) -> Union[list, dict]:
    """"""

    return token.call_list_method("disk.folder.getchildren", {"id": parent_id, "filter": {"type": "folder"}, "select": ["ID", "PARENT_ID"]}, timeout=100)


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


def _folders_recursive_descent(cloud_token: CloudBitrixToken, cloud_parent_id: int, root: bool = False):
    """"""
    try:
        nested_folders = _bx_folder_getchildren(cloud_token, cloud_parent_id)

        if not nested_folders:
            return {}

        children = {}
        for folder in nested_folders:
            folder_id = int(folder["ID"])
            children[folder_id] = _folders_recursive_descent(cloud_token, folder_id)

        if root:
            return {cloud_parent_id: children}
        return children

    except Exception as exc:
        print(f"Произошла ошибка в _folders_recursive_descent (при построении древовидной структуры): {exc}")
        raise

def _extract_keys(tree: dict) -> list[int]:
    """"""
    try:
        keys = []

        for key, value in tree.items():
            keys.append(key)
            if isinstance(value, dict):
                keys.extend(_extract_keys(value))

        return keys

    except Exception as exc:
        print(f"Произошла ошибка в функции _extract_keys (при преобразовании древовидной структуры в плоский список): {exc}")
        raise

def _synchronize_folders_for_storage(cloud_token: CloudBitrixToken, box_token: BoxBitrixToken, cloud_storage_id: int, storage_relation_map: dict[int, int]):
    """Создаём недостающие папки"""

    folder_tree_structure:dict = _folders_recursive_descent(cloud_token, cloud_storage_id, root=True)
    origin_folder_list:list[int] = _extract_keys(folder_tree_structure)

    for folder in folder_tree_structure:
        ...


    return folder_tree_structure, origin_folder_list
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
        #todo убрать хардкод пока берем только 19ый (общий диск)
        if storage_relation != 19:
            continue

        res = _synchronize_folders_for_storage(
            cloud_token=cloud_token,
            box_token=box_token,
            cloud_storage_id=storage_relation,
            storage_relation_map=storage_relation_map,
        )

    print(res)
    return res
