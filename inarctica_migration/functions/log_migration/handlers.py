import requests
import pybase64

from inarctica_migration.models import LogMigration
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken

from inarctica_migration.functions.helpers import execution_time_counter
from inarctica_migration.functions.log_migration.bx_rest_requests import bx_disk_attachedObject_get, bx_log_blogpost_get


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
) -> dict[int, bool]:
    blogposts_to_init = []
    for blogpost_id in bitrix_sorted_blogposts:
        if blogpost_id not in blogposts_into_db:
            blogposts_to_init.append(bitrix_sorted_blogposts[blogpost_id])

    # Сначала инициализируем новые посты - если они есть.
    if blogposts_to_init:
        new_blogposts = blogpost_initialization_process(blogposts_to_init, "UA")
        blogposts_into_db = {**blogposts_into_db, **new_blogposts}

    return blogposts_into_db

@execution_time_counter
def blogpost_initialization_process(
        blogposts: list[dict],
        dest: str
):
    """"""
    bulk_data = []
    result = {}

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
        get_file_result = bx_disk_attachedObject_get(
            token=token,
            params={"id": file_id}
        )
        files_links.append((get_file_result["result"]["NAME"], get_file_result["result"]["DOWNLOAD_URL"]))

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
