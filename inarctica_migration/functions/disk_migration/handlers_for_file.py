import requests
import pybase64

from inarctica_migration.models import Folder, Storage
from inarctica_migration.models.disk import File
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken

from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.disk_migration.bx_rest_requests import _bx_folder_addsubfolder, _bx_folder_uploadfile
from inarctica_migration.functions.disk_migration.descent_by_recursion import ordered_hierarchy, recursive_descent, file_recursive_descent


from inarctica_migration.utils.func_helpers import timer


@timer
def get_file_content(name: str, url: str) -> list[str]:
    with requests.get(url, stream=True) as response:
        response.raise_for_status()

        # создаём буфер для base64
        encoder = pybase64.b64encode

        # собираем все куски
        chunks = []
        chunks_cnt = 1
        print('Получили респонс')
        for chunk in response.iter_content(chunk_size=None):
            print(f"Отработано {chunks_cnt} чанков")
            chunks_cnt += 1

            if chunk:  # пропускаем пустые keep-alive
                chunks.append(encoder(chunk))
                del chunk

        # склеиваем в один base64-стринг
        file_b64 = b"".join(chunks).decode("utf-8")
        del chunks

    return [name, file_b64]


def synchronize_files_for_storage(
        cloud_token: CloudBitrixToken,
        box_token: BoxBitrixToken,
        cloud_storage_id: int,
):
    """"""
    # Для ведения статистик
    storage = Storage.objects.get(cloud_id=cloud_storage_id)
    box_storage_files_cnt = storage.files_in_box
    uploaded_files_cnt = 0

    bulk_data = []

    # 0. Получаем структуру узла и всех закрепленных за ним файлов
    folder_and_files = file_recursive_descent(
        token=cloud_token,
        object_type="file",
        cloud_parent_id=cloud_storage_id,
    )

    all_cloud_files_cnt = 0
    for file_in_folder in folder_and_files.values():
        all_cloud_files_cnt += len(file_in_folder)

    storage.files_in_cloud = all_cloud_files_cnt
    storage.save()

    # 1. Сливаем две модели для получения карты связей папок и хранилищ
    storage_relation_map: dict[int, int] = dict(Storage.objects.all().values_list("cloud_id", "box_id"))
    folders_relation_map: dict[int, int] = dict(Folder.objects.all().values_list("cloud_id", "box_id"))
    merged_relation_map = {**storage_relation_map, **folders_relation_map}

    files_relation_map: dict[int, int] = dict(File.objects.all().values_list("cloud_id", "box_id"))
    folders = Folder.objects.all()

    for folder, files in folder_and_files.items():
        folder_id = int(folder)
        if folder_id not in merged_relation_map:
            continue

        box_folder_id = merged_relation_map[folder_id]

        for file in files:
            try:
                file_cloud_id = int(file[0])
                file_name = file[1]
                file_url = file[2]
                file_byte_size = int(file[3])

                # if file_byte_size > 111137542421:
                #     continue

                if file_cloud_id in files_relation_map:
                    continue

                file_content = get_file_content(file_name, file_url)
                params = {
                    'id': box_folder_id,
                    'data': {'NAME': file_name},
                    'fileContent': file_content,
                    'generateUniqueName': True
                }

                uploadfile_result = _bx_folder_uploadfile(box_token, params)
                uploaded_file_box_id = int(uploadfile_result["result"]["ID"])

                bulk_data.append(
                    File(
                        cloud_id=file_cloud_id,
                        box_id=uploaded_file_box_id,
                        parent_cloud_id=folder_id,
                        parent_box_id=box_folder_id,
                    )
                )

                uploaded_files_cnt += 1

            except MemoryError:
                debug_point(
                    "❌ Не хватает памяти на перенос файла\n"
                    f"{locals().get('file_name'), file_byte_size}"
                    f"cloudID={cloud_storage_id}\n cloudFileId={file_cloud_id}\n"
                    f"boxID={box_folder_id}\n\n"
                )
                # можно continue, чтобы пропустить проблемный файл
                continue

            except Exception as exc:
                debug_point(
                    "❌ Ошибка при переносе файла\n"
                    f"{locals().get('file_name'), file_byte_size}"
                    f"boxID={box_folder_id}\n boxFileId={locals().get('uploaded_file_box_id')}\n"
                    f"cloudID={cloud_storage_id}\n cloudFileId={file_cloud_id}\n"
                    f"{exc}"
                )
                # пропускаем файл и идём дальше
                continue

        storage.files_in_box += uploaded_files_cnt

        if storage.files_in_cloud == storage.files_in_box:
            storage.files_sync = True

        else:
            storage.files_sync = False

        File.objects.bulk_create(
            bulk_data,
            batch_size=1000,
            unique_fields=["cloud_id"],
            update_fields=["box_id", "parent_cloud_id", "parent_box_id"],
            update_conflicts=True,
        )

        storage.save()

        debug_point("✅ Создание файлов в хранилище synchronize_files_for_storage\n"
                    f"Создано | Всего (box) | Всего (cloud)\n"
                    f"{uploaded_files_cnt} | {storage.files_in_box} | {storage.files_in_cloud:<17}\n\n"

                    f"boxID={box_folder_id}\n"
                    f"https://bitrix24.inarctica.com/bitrix/tools/disk/focus.php?folderId={box_folder_id}&action=openFolderList&ncc=1\n\n"
                    f"cloudID={cloud_storage_id}\n"
                    f"https://inarctica.bitrix24.ru/bitrix/tools/disk/focus.php?folderId={cloud_storage_id}&action=openFolderList&ncc=1\n\n",
                    )
        return
