from typing import List, Tuple, Any

import requests
import pybase64
from inarctica_migration.functions.helpers import execution_time_counter
from inarctica_migration.functions.log_migration.bx_rest_requests import bx_disk_attachedObject_get
from inarctica_migration.models import Group
from inarctica_migration.utils import CloudBitrixToken


def invite_user_in_projects(
        projects_list: list,
        user_id: int
):
    """Добавялет участника в группу без приглашения"""

    groups = Group.objects.all().values_list("")

    return ...


def get_all_logs():
    """"""
    pass


def get_files_links(
        token: CloudBitrixToken,
        files_ids: list[str]
) -> list[tuple[str, str]]:
    """"""
    files_links = []
    for file_id in files_ids:
        get_file_result = bx_disk_attachedObject_get(
            token=token,
            params={'id': file_id}
        )
        files_links.append((get_file_result['result']['NAME'], get_file_result['result']['DOWNLOAD_URL']))

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
