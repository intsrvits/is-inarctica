from inarctica_migration.models import Folder
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken

from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.disk_migration.bx_rest_requests import _bx_folder_addsubfolder
from inarctica_migration.functions.disk_migration.descent_by_recursion import _folders_recursive_descent, ordered_hierarchy


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

            # Поведение если папка уже перенесена и её связи записаны в бд
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
