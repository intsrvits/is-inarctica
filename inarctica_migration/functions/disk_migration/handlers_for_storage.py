from inarctica_migration.models import User, Group
from inarctica_migration.models.disk import Storage

from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.disk_migration.bx_rest_requests import _bx_storage_getlist


def synchronize_storages(
        cloud_token: CloudBitrixToken,
        box_token: BoxBitrixToken,
        entity_type: list[str] | str = None,
) -> dict:
    """
    Функция ищет и записывает в БД связи между одинаковыми по названию хранилищами, entity_type и entity_id

    После завершения работы в бд появляются записи об одинаковых хранилищах: origin_id, destination_id
    """
    cloud_storage_id, box_storage_id = None, None

    bulk_data = []

    if isinstance(entity_type, list):
        storage_relation_map: dict[int, int] = dict(Storage.objects.filter(entity_type__in=entity_type).values_list("cloud_id", "box_id"))
    elif isinstance(entity_type, str):
        storage_relation_map: dict[int, int] = dict(Storage.objects.filter(entity_type__in=[entity_type]).values_list("cloud_id", "box_id"))
    else:
        storage_relation_map: dict[int, int] = dict(Storage.objects.all().values_list("cloud_id", "box_id"))

    users_cloud_box_map: dict[int, int] = dict(User.objects.all().values_list("origin_id", "destination_id"))
    groups_cloud_box_map: dict[int, int] = dict(Group.objects.all().values_list("origin_id", "destination_id"))

    try:
        current_cloud_storages = _bx_storage_getlist(cloud_token)
        current_box_storages = _bx_storage_getlist(box_token)

        # Сравниваем все хранилища облака со всеми хранилищами коробки для нахождения идентичных
        for cloud_storage in current_cloud_storages:
            for box_storage in current_box_storages:

                # Составляем пространство условий на идентичность хранилищ
                # 1. Одинаковое название
                same_name_condition: bool = cloud_storage["NAME"] == box_storage["NAME"]

                # 2. Одинаковый тип
                if entity_type:
                    same_entity_type_condition: bool = cloud_storage['ENTITY_TYPE'] == box_storage['ENTITY_TYPE'] == entity_type

                else:
                    same_entity_type_condition: bool = cloud_storage['ENTITY_TYPE'] == box_storage['ENTITY_TYPE']
                    entity_type = cloud_storage['ENTITY_TYPE']

                if not all([same_name_condition, same_entity_type_condition]):
                    continue

                # 3. Идентичные ENTITY_ID
                entity_checkers = {
                    "user": lambda c, b: users_cloud_box_map.get(int(c["ENTITY_ID"])) == int(b["ENTITY_ID"]),
                    "group": lambda c, b: groups_cloud_box_map.get(int(c["ENTITY_ID"])) == int(b["ENTITY_ID"]),
                    "common": lambda c, b: True,
                }
                same_entity_condition = entity_checkers.get(entity_type, lambda *_: False)(cloud_storage, box_storage)

                if not same_entity_condition:
                    continue

                cloud_storage_id = int(cloud_storage["ROOT_OBJECT_ID"])

                # Работаем только с несуществующими связями
                if storage_relation_map.get(cloud_storage_id) is None:
                    box_storage_id = int(box_storage["ROOT_OBJECT_ID"])

                    bulk_data.append(
                        Storage(
                            cloud_id=cloud_storage_id,
                            box_id=box_storage_id,
                            entity_type=entity_type,
                        )
                    )

                    storage_relation_map[cloud_storage_id] = box_storage_id

    except Exception as exc:
        debug_point(
            "❌ Произошла ошибка при cихнронизации хранилища synchronize_storages\n"
            f"boxID={box_storage_id}\n"
            f"https://bitrix24.inarctica.com/bitrix/tools/disk/focus.php?folderId={box_storage_id}&action=openFolderList&ncc=1\n\n"
            f"cloudID={cloud_storage_id}\n"
            f"https://inarctica.bitrix24.ru/bitrix/tools/disk/focus.php?folderId={cloud_storage_id}&action=openFolderList&ncc=1\n\n"
            f"{exc}",
        )
        raise

    finally:
        unique_bulk_data = {
            storage.cloud_id: storage
            for storage in bulk_data
        }.values()

        Storage.objects.bulk_create(
            unique_bulk_data,
            batch_size=1000,
            unique_fields=["cloud_id"],
            update_fields=["box_id"],
            update_conflicts=True,
        )

        debug_point(f"Создано {len(unique_bulk_data)} связей между хранилищами. Всего связей {len(storage_relation_map)}", with_tags=False)

        return storage_relation_map
