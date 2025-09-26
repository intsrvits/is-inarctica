from inarctica_migration.models import User, Group
from inarctica_migration.models.disk import Storage

from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.disk_migration.bx_rest_requests import _bx_storage_getlist


def _synchronize_storages(
        cloud_token: CloudBitrixToken,
        box_token: BoxBitrixToken
) -> dict:
    """
    Функция ищет и записывает в БД связи между одинаковыми по названию хранилищами, entity_type и entity_id

    После завершения работы в бд появляются записи об одинаковых хранилищах: origin_id, destination_id
    """
    cloud_storage_obj_id, box_storage_obj_id = None, None

    bulk_data = []

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
                same_name_condition: bool = cloud_storage["NAME"] == box_storage["NAME"]
                same_entity_type_condition: bool = cloud_storage['ENTITY_TYPE'] == box_storage['ENTITY_TYPE']

                if not all([same_name_condition, same_entity_type_condition]):
                    continue

                same_entity_condition: bool = False

                if cloud_storage['ENTITY_TYPE'] == 'user':
                    same_entity_condition = users_cloud_box_map.get(int(cloud_storage['ENTITY_ID'])) == int(box_storage['ENTITY_ID'])
                    #same_entity_condition = False #todo хардкод
                elif cloud_storage['ENTITY_TYPE'] == 'group':
                    same_entity_condition = groups_cloud_box_map.get(int(cloud_storage['ENTITY_ID'])) == int(box_storage['ENTITY_ID'])
                elif cloud_storage['ENTITY_TYPE'] == 'common':
                    same_entity_condition = True

                if not same_entity_condition:
                    continue

                cloud_storage_obj_id = int(cloud_storage["ROOT_OBJECT_ID"])
                # Работаем только с несуществующими связями
                if storage_relation_map.get(cloud_storage_obj_id) is None:


                    box_storage_obj_id = int(box_storage["ROOT_OBJECT_ID"])

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

        # возвращаем только те которые не синхронизированы
        storage_not_sync_folders = dict(Storage.objects.filter(folders_sync=False).values_list("cloud_id", "box_id"))

        return storage_relation_map, storage_not_sync_folders
