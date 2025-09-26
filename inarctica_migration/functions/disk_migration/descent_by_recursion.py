from typing import Union

from inarctica_migration.utils import CloudBitrixToken
from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.disk_migration.bx_rest_requests import _bx_folder_getchildren


def _recursive_descent(
        cloud_token: CloudBitrixToken,
        object_type: str,  # todo сделать аннотацию и переписать докстринг
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
            filter={"type": object_type},
            select=["ID", "REAL_OBJECT_ID", "PARENT_ID"]
        )

        # Добавляем прямых детей
        child_ids = [int(folder["ID"]) for folder in nested_folders]
        result[cloud_parent_id] = child_ids

        # Рекурсия для детей
        for folder in nested_folders:
            folder_id = int(folder["ID"])
            _recursive_descent(cloud_token, object_type, folder_id, result)

        return result

    except Exception as exc:

        debug_point(f"Ошибка в _recursive_descent для корневой папки с облачным ID={cloud_parent_id}: {exc}", with_tags=True)
        raise


def ordered_hierarchy(
        cloud_token: CloudBitrixToken,
        object_type: str,
        cloud_parent_id: int,
) -> list[int]:

    structure = _recursive_descent(cloud_token, object_type, cloud_parent_id)

    result = []
    for parent_id, children_id in structure.items():
        if not parent_id in result:
            result.append(parent_id)

        for child_id in children_id:
            if not child_id in result:
                result.append(child_id)

    return result
