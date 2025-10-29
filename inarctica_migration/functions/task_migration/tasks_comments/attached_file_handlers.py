import re
import pybase64
import requests

from inarctica_migration.functions.disk_migration.bx_rest_requests import bx_disk_storage_uploadFile
from inarctica_migration.utils import BoxBitrixToken


def check_attachments_in_comment(comment) -> list:
    """Возвращает список прикрепленных к комментарию файлов."""
    attached_files_data = []
    bx_attached_objects = []
    if isinstance(comment.get("ATTACHED_OBJECTS"), list) and len(comment["ATTACHED_OBJECTS"]):
        bx_attached_objects = comment["ATTACHED_OBJECTS"]

    if isinstance(comment.get("ATTACHED_OBJECTS"), dict) and len(comment["ATTACHED_OBJECTS"].keys()):
        bx_attached_objects = comment["ATTACHED_OBJECTS"].values()

    if len(bx_attached_objects):
        for bx_attached_object in bx_attached_objects:
            attached_files_data.append({
                "NAME": bx_attached_object["NAME"],
                "URL": bx_attached_object["DOWNLOAD_URL"],
                "FILE_ID": bx_attached_object["FILE_ID"],
                "SIZE": bx_attached_object["SIZE"]
            })

    return attached_files_data


def get_file_content(name: str, url: str) -> list[str]:
    url = 'https://inarctica.bitrix24.ru' + url

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


def migrate_attached_files(token: BoxBitrixToken, storage_id: int, files: list, ):
    attachment_file_id_map = dict()
    for file in files:
        name = file["NAME"]
        url = file["URL"]
        cloud_attachment_file_id = int(file["FILE_ID"])
        file_content = get_file_content(name, url)

        params_to_upload = {
            "id": storage_id,
            "fileContent": file_content,
            "data": {"NAME": name},
            "generateUniqueName": True,
        }

        box_attachment_file_id = int(bx_disk_storage_uploadFile(token, params_to_upload)["result"]["ID"])
        attachment_file_id_map[cloud_attachment_file_id] = box_attachment_file_id

    return attachment_file_id_map

