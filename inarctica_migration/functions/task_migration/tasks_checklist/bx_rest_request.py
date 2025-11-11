from inarctica_migration.functions.helpers import retry_decorator
from inarctica_migration.utils import CloudBitrixToken


@retry_decorator(attempts=3, delay=30)
def bx_task_checklistitem_getlist(
        token: CloudBitrixToken,
        params: dict = None,
):
    """
    Запрос task.checklistitem.getlist к REST API
    https://apidocs.bitrix24.ru/api-reference/tasks/checklist-item/task-checklist-item-get-list.html
    """

    return token.call_list_method("task.checklistitem.getlist", params, timeout=100)


@retry_decorator(attempts=3, delay=30)
def bx_task_checklistitem_add(
        token,
        params: dict = None,
):
    """
    Запрос task.checklistitem.add к REST API
    https://apidocs.bitrix24.ru/api-reference/tasks/checklist-item/task-checklist-item-add.html
    """

    return token.call_api_method("task.checklistitem.add", params, timeout=100)["result"]
