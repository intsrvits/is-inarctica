import re

import requests
import pybase64

from inarctica_migration.models import LogMigration
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken

from inarctica_migration.models import User
from inarctica_migration.functions.helpers import execution_time_counter
from inarctica_migration.functions.log_migration.bx_rest_requests import bx_disk_attachedObject_get, bx_log_blogpost_get
from integration_utils.bitrix24.exceptions import BitrixApiError


# ==================================
#   Блок инициализации новых постов
# ==================================
def get_sorted_by_time_blogposts(
        token: CloudBitrixToken | BoxBitrixToken,
        dest=None
):
    # Получаем список всех существующих постов и сортируем их по дате (по айди создания)
    if dest:
        params = {
            "LOG_RIGHTS": [f"SG{dest}"]
        }

    else:
        params = {
            "LOG_RIGHTS": "UA"
        }

    blogposts_list = bx_log_blogpost_get(token, params)
    sorted_blogposts = sorted(blogposts_list, key=lambda item: int(item["ID"]))

    return sorted_blogposts


def init_blogpost_into_db(
        bitrix_sorted_blogposts: dict,
        blogposts_into_db: dict[int, bool],
        dest: str | None = None,
) -> dict[int, bool]:
    """"""

    blogposts_to_init = []
    for blogpost_id in bitrix_sorted_blogposts:
        if blogpost_id not in blogposts_into_db:
            blogposts_to_init.append(bitrix_sorted_blogposts[blogpost_id])

    # Сначала инициализируем новые посты - если они есть.
    if blogposts_to_init:
        new_blogposts = blogpost_initialization_process(blogposts_to_init, dest)
        blogposts_into_db = {**blogposts_into_db, **new_blogposts}

    return blogposts_into_db


@execution_time_counter
def blogpost_initialization_process(
        blogposts: list[dict],
        dest: str | None
):
    """"""
    bulk_data = []
    result = {}
    if not dest:
        dest = "UA"

    for blogpost in blogposts:
        cloud_id = blogpost["ID"]

        bulk_data.append(
            LogMigration(
                cloud_id=cloud_id,
                dest=dest
            )
        )

        result[cloud_id] = False

    LogMigration.objects.bulk_create(
        bulk_data,
    )

    return result


# ===============================
#   Блок обработки файлов
# ===============================
@execution_time_counter
def get_files_links(
        token: CloudBitrixToken,
        files_ids: list[str]
) -> list[tuple[str, str]]:
    """"""
    files_links = []
    for file_id in files_ids:
        try:
            get_file_result = bx_disk_attachedObject_get(
                token=token,
                params={"id": file_id}
            )
            files_links.append((get_file_result["result"]["NAME"], get_file_result["result"]["DOWNLOAD_URL"]))
        except BitrixApiError as exc:
            if exc.error == "ERROR_NOT_FOUND":
                pass
            else:
                raise

    return files_links


@execution_time_counter
def get_files_base64(files_attributes: list):
    """"""
    files_base64 = []
    for file_name, file_download_url in files_attributes:
        with requests.get(file_download_url) as response:
            response.raise_for_status()
            file_bytes = response.content

        file_b64 = pybase64.b64encode(file_bytes).decode("utf-8")

        files_base64.append([file_name, file_b64])
        del file_bytes, file_b64

    return files_base64


# ===============================
#   Блок отчистки текста
# ===============================
def _clean_text(text: str) -> str:
    text = re.sub(r"\[/?[A-Z]+[^\]]*\]", "", text)  # убираем [P], [B], [LIST], [/P] и т.п.
    text = re.sub(r"[*•\-]+", "", text)  # убираем маркеры списков
    text = re.sub(r"\s+", " ", text)  # схлопываем пробелы
    return text.strip().lower()


def _replace_user_id(match):
    cloud_id = int(match.group(1))  # вытащили число из [USER=123]

    user = User.objects.filter(origin_id=cloud_id).first()
    if user:
        box_id = user.destination_id
    else:
        box_id = 1

    return f"[USER={box_id}]"


def clean_detail_text(text: str) -> str:
    """"""
    text_without_tags = re.sub(r"\s*\[DISK FILE ID=n\d+\]\s*", "", text)
    prepared_text = re.sub(r'\[USER=(\d+)\]', _replace_user_id, text_without_tags)

    if not prepared_text.replace(" ", "").replace("\n", "").replace("\r", ""):
        return "Прикрепление файлов"

    return prepared_text


def clean_title(detail_text: str, title: str) -> str:
    """"""
    if clean_detail_text(detail_text) == "Прикрепление файлов" or (_clean_text(detail_text) == _clean_text(title)):
        return ""

    return title
