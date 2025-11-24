from typing import Union

from inarctica_migration.functions.helpers import retry_decorator
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken


@retry_decorator(attempts=3, delay=30)
def bx_tasks_task_list(
        token: CloudBitrixToken | BoxBitrixToken,
        params: dict = None,
) -> Union[list, dict]:
    """
    Запрос tasks.task.list к REST API
    https://apidocs.bitrix24.ru/api-reference/tasks/tasks-task-list.html
    """

    return token.call_list_method("tasks.task.list", params, timeout=100)['tasks']


@retry_decorator(attempts=3, delay=30)
def bx_tasks_task_add(
        token: CloudBitrixToken | BoxBitrixToken,
        params: dict = None,
) -> Union[list, dict]:
    """
    Запрос tasks.task.list к REST API
    https://apidocs.bitrix24.ru/api-reference/tasks/tasks-task-add.html
    """

    return token.call_list_method("tasks.task.add", params, timeout=100)


@retry_decorator(attempts=3, delay=30)
def bx_tasks_task_add(
        token: CloudBitrixToken | BoxBitrixToken,
        params: dict = None,
) -> Union[list, dict]:
    """
    Запрос tasks.task.list к REST API
    https://apidocs.bitrix24.ru/api-reference/tasks/tasks-task-add.html
    """

    return token.call_list_method("tasks.task.add", params, timeout=100)


@retry_decorator(attempts=3, delay=30)
def bx_task_stages_get(
        token: CloudBitrixToken | BoxBitrixToken,
        params: dict = None,
) -> Union[list, dict]:
    """
        Запрос task.stages.get к REST API
        https://apidocs.bitrix24.ru/api-reference/tasks/stages/task-stages-get.html
    """

    return token.call_list_method("task.stages.get", params, timeout=100)


@retry_decorator(attempts=3, delay=30)
def bx_task_stages_add(
        token: CloudBitrixToken | BoxBitrixToken,
        params: dict = None,
) -> Union[list, dict]:
    """
        Запрос task.stages.add к REST API
        https://apidocs.bitrix24.ru/api-reference/tasks/stages/task-stages-add.html
    """

    return token.call_list_method("task.stages.add", params, timeout=100)


@retry_decorator(attempts=3, delay=30)
def bx_task_stages_update(
        token: CloudBitrixToken | BoxBitrixToken,
        params: dict = None,
) -> Union[list, dict]:
    """
        Запрос task.stages.update к REST API
        https://apidocs.bitrix24.ru/api-reference/tasks/stages/task-stages-update.html#parametr-fields
    """

    return token.call_list_method("task.stages.update", params, timeout=100)


@retry_decorator(attempts=3, delay=30)
def bx_task_commentitem_getlist(
        token: CloudBitrixToken,
        params: dict = None,
):
    """
    Запрос task.commentitem.getlist к REST API
    https://apidocs.bitrix24.ru/api-reference/tasks/comment-item/task-comment-item-get-list.html
    """

    return token.call_list_method("task.commentitem.getlist", params, timeout=100)


@retry_decorator(attempts=3, delay=30)
def bx_task_commentitem_add(
        token: BoxBitrixToken,
        params: dict = None,
):
    """
    Запрос task.commentitem.add к REST API
    https://apidocs.bitrix24.ru/api-reference/tasks/comment-item/task-comment-item-add.html
    """

    return token.call_api_method("task.commentitem.add", params, timeout=100)["result"]
