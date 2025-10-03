from typing import Union

from inarctica_migration.functions.helpers import retry_decorator
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken


@retry_decorator(attempts=3, delay=30)
def bx_log_blogpost_get(
        token: CloudBitrixToken | BoxBitrixToken,
        params: dict = None,
) -> Union[list, dict]:
    """
    Запрос log.blogpost.get к REST API
    https://apidocs.bitrix24.ru/api-reference/log/log-blogpost-get.html
    """

    return token.call_list_method("log.blogpost.get", params, timeout=100)


@retry_decorator(attempts=3, delay=30)
def bx_log_blogpost_add(
        token: BoxBitrixToken,
        params: dict,
) -> Union[list, dict]:
    """
    Запрос log.blogpost.add к REST API
    https://apidocs.bitrix24.ru/api-reference/log/log-blogpost-add.html
    """

    return token.call_api_method("log.blogpost.add", params, timeout=100)


@retry_decorator(attempts=3, delay=30)
def bx_disk_attachedObject_get(
        token: CloudBitrixToken | BoxBitrixToken,
        params: dict,
) -> Union[list, dict]:
    """
    Запрос disk.attachedObject.get к REST API
    https://apidocs.bitrix24.ru/api-reference/disk/attached-object/disk-attached-object-get
    """

    return token.call_api_method("disk.attachedObject.get", params, timeout=100)
