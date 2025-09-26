from inarctica_migration.models.disk import Storage

from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.disk_migration.bx_rest_requests import _bx_storage_getlist


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

    storage_relation_map: dict[int, int] = dict(Storage.objects.all().values_list("cloud_id", "box_id"))

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
                                cloud_id=cloud_storage_obj_id,
                                box_id=box_storage_obj_id,
                            )
                        )

                        storage_relation_map[cloud_storage_obj_id] = box_storage_obj_id

    except Exception as exc:
        debug_point(f"Произошла ошибка во время синхронизации облачного хранилища с ID {cloud_storage_obj_id} и коробочного с ID {box_storage_obj_id}: {exc}", with_tags=True)
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

        print(f"Создано {len(unique_bulk_data)} связей между хранилищами. Всего связей {len(storage_relation_map)}")
        debug_point(f"Создано {len(unique_bulk_data)} связей между хранилищами. Всего связей {len(storage_relation_map)}", with_tags=False)
        return storage_relation_map
