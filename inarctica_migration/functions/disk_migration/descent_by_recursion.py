from typing import Union

from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.disk_migration.bx_rest_requests import _bx_folder_getchildren


def recursive_descent(
        token: Union[CloudBitrixToken, BoxBitrixToken],
        object_type: str,
        cloud_parent_id: int,
        result: Union[dict, None] = None
) -> dict[int, list]:
    """
    Рекурсивно получает структуру, где ключи это все папки хранилища, а значения - это список id их ближайших детей.
    Если папка не содержит в себе дочерней, то её список пуст []

    {
    cloud_parent_id: [child_id1, child_id2, ...],
    child_id1: [child_id11, child_id12],
    child_id2: [],
    }
    """

    # Если дошли до конца, т.е у папки нет дочерних папок
    if result is None:
        result = {}

    try:
        nested_folders = _bx_folder_getchildren(
            token,
            cloud_parent_id,
            filter={"type": object_type},
            select=["ID", "REAL_OBJECT_ID", "PARENT_ID"]
        )

        # Добавляем прямых детей
        child_ids = [int(folder["ID"]) for folder in nested_folders]
        result[cloud_parent_id] = child_ids

        # Рекурсия для детей
        for folder in nested_folders:
            folder_id = int(folder["ID"])
            recursive_descent(token, object_type, folder_id, result)

        return result

    except Exception as exc:

        debug_point(f"Ошибка в _recursive_descent для корневой папки с облачным ID={cloud_parent_id}: {exc}")
        raise


def file_recursive_descent(
        token: Union[CloudBitrixToken, BoxBitrixToken],
        object_type: str,
        cloud_parent_id: int,
        result: Union[dict, None] = None
) -> dict[int, list]:
    # Если дошли до конца, т.е у папки нет дочерних папок
    if result is None:
        result = {}

    try:
        nested_entity = _bx_folder_getchildren(
            token,
            cloud_parent_id,
            select=["ID", "NAME", "REAL_OBJECT_ID", "PARENT_ID", "DOWNLOAD_URL"]
        )

        nested_folders = []
        nested_files = []

        for entity in nested_entity:
            if entity["TYPE"] == 'file':
                nested_files.append(entity)

            elif entity["TYPE"] == 'folder':
                nested_folders.append(entity)

        # Добавляем прямых детей
        files_tuple = ([(file['ID'], file['NAME'], file['DOWNLOAD_URL']) for file in nested_files])
        result[cloud_parent_id] = files_tuple

        # Рекурсия для детей
        for folder in nested_folders:
            folder_id = int(folder["ID"])
            file_recursive_descent(token, object_type, folder_id, result)

        return result

    except Exception as exc:

        debug_point(f"Ошибка в _recursive_descent для корневой папки с облачным ID={cloud_parent_id}: {exc}")
        raise


def ordered_hierarchy(
        structure: dict[int, list],
) -> list[int]:
    """
    Превращает структуру в последовательный список ID.

    :param structure: древовидная структура с указанием узла и его детей
    :return: list[int]
    """
    result = []
    for parent_id, children_id in structure.items():
        if parent_id not in result:
            result.append(parent_id)

        for child_id in children_id:
            if child_id not in result:
                result.append(child_id)

    return result
