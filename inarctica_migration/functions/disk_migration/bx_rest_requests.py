from typing import Union

from inarctica_migration.functions.helpers import retry_decorator
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken


@retry_decorator(attempts=3, delay=30)
def bx_storage_getlist(token: CloudBitrixToken | BoxBitrixToken, fields=None) -> Union[list, dict]:
    """Запрос disk.storage.getlist к REST API"""

    return token.call_list_method("disk.storage.getlist", fields=fields, timeout=100)


@retry_decorator(attempts=3, delay=30)
def _bx_folder_getchildren(
        token: CloudBitrixToken | BoxBitrixToken,
        parent_id: int,
        filter: dict = None,
        select: list = None,
) -> Union[list, dict]:
    """Запрос disk.folder.getchildren к REST API"""
    return token.call_list_method("disk.folder.getchildren", {"id": parent_id, "filter": filter, "select": select})


@retry_decorator(attempts=3, delay=30)
def _bx_folder_addsubfolder(
        token: BoxBitrixToken,
        params: dict,
) -> dict:
    """Запрос disk.folder.addsubfolder к REST API"""
    return token.call_api_method("disk.folder.addsubfolder", params)


@retry_decorator(attempts=3, delay=30)
def _bx_folder_uploadfile(
        token: BoxBitrixToken,
        params: dict,
) -> dict:
    """"""
    return token.call_api_method("disk.folder.uploadFile", params, timeout=300)


@retry_decorator(attempts=3, delay=30)
def bx_disk_storage_uploadFile(
        token: BoxBitrixToken,
        params: dict | None = None,
):
    """"""
    return token.call_api_method("disk.storage.uploadFile", params, timeout=300)
