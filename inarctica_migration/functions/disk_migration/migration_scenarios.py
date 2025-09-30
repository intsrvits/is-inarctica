from inarctica_migration.functions.disk_migration.handlers_for_file import synchronize_files_for_storage
from inarctica_migration.functions.disk_migration.handlers_for_folder import _synchronize_folders_for_storage, delete_folders_for_storage
from inarctica_migration.functions.disk_migration.handlers_for_storage import synchronize_storages
from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.models import Storage
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken


def clear_all_storages():
    """
    Пайплайн удаления всех папок:

    !!! Перед запуском migrate_disk стоит почистить БД, т.к удаление происходит только на Битриксе !!!
    """
    storage_relation_map: dict[int, int] = {}

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    entity_types = [
        "group",
        "common",
        "user",
    ]

    # # Настройка связей между хранилищами определённых типов
    # for entity_type in entity_types:

    # Настройка связей между хранилищами
    # {cloud_id: box_id, ...}
    storage_relation_map: dict[int, int] = synchronize_storages(
        cloud_token=cloud_token,
        box_token=box_token,
    )

    # Меняем ключи и значения местами. Получается связь box_id - cloud_id
    inv_storage_relation_map: dict[int, int] = {value: key for key, value in storage_relation_map.items()}

    # Чистка каждой из root-папки (хранилища) среди найденных и сопоставленных
    delete_folders_for_storage(box_token, inv_storage_relation_map)


def migrate_disk():
    """
    Пайплайн полной синхронизации дисков:
    1) Настройка связей между хранилищами
    2) Перенос структуры папок
    3) Перенос файлов
    """

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    entity_types = [
        "group",
        "common",
        "user",
    ]

    # Миграция всех перечисленных типов хранилищ
    for entity_type in entity_types:
        debug_point(f"Миграция хранилищ с ENTITY_TYPE={entity_type} ")

        # Настройка связей между хранилищами
        # {origin_id: destination_id, ...}
        entity_storage_relation_map = synchronize_storages(
            cloud_token=cloud_token,
            box_token=box_token,
            entity_type=entity_type
        )

        storage_ids = list(Storage.objects.filter(entity_type=entity_type).values_list('cloud_id', flat=True))

        for storage_relation in storage_ids:

            _synchronize_folders_for_storage(
                cloud_token=cloud_token,
                box_token=box_token,
                cloud_storage_id=storage_relation,
            )

        debug_point(f"Синхронизация {entity_type} завершена. Обработано {len(entity_storage_relation_map)} отношений", with_tags=False)

    debug_point("Синхронизация завершена", with_tags=False)


def migrate_files():
    """"""
    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    storages = dict(Storage.objects.filter(cloud_id=67).values_list('cloud_id', 'box_id'))
    for storage in storages:
        synchronize_files_for_storage(
            cloud_token=cloud_token,
            box_token=box_token,
            cloud_storage_id=storage,
        )
