from typing import Union

from inarctica_migration.functions.disk_migration.handlers_for_folder import _synchronize_folders_for_storage, delete_folders_for_storage
from inarctica_migration.functions.disk_migration.handlers_for_storage import _synchronize_storages
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken


def clear_all_storages():
    """
    Пайплайн удаления всех папок:

    !!! Перед запуском migrate_disk стоит почистить БД, т.к удаление происходит только на Битриксе !!!
    """

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()



    # Настройка связей между хранилищами
    # {origin_id: destination_id, ...}
    storage_relation_map: dict[int, int] = _synchronize_storages(cloud_token=cloud_token, box_token=box_token)

    # Удаление всех папок хранилища папок
    for storage_relation in storage_relation_map:

        delete_folders_for_storage(box_token, storage_relation_map[storage_relation])


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
    storage_relation_map, storage_not_sync_folders = _synchronize_storages(cloud_token=cloud_token, box_token=box_token)

    # Воссоздание структуры папок для КАЖДОГО из хранилищ
    for storage_relation in storage_not_sync_folders:
        if storage_relation in [19, 67]:
        #todo убрать хардкод (пока тестим на своих дисках)
            _synchronize_folders_for_storage(
                cloud_token=cloud_token,
                box_token=box_token,
                cloud_storage_id=storage_relation,
            )
