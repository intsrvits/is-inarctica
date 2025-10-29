from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from inarctica_migration.models import Group

from inarctica_migration.functions.helpers import debug_point


def descripton_handler(description: str, cloud_attached_ids: list):
    """
    Принимает описание задачи с cloud-портала, ищет теги [DISK FILE ID=n].
    Запрашивает информацию о прикрепленных файлах, сопоставляет attachedId с objectId (objectId указан в теге)
    Прикрепляет файлы к задаче на бокс портале,
    :param description:
    :param cloud_attached_ids:
    :return:
    """

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()


def delete_box_stages():
    """Удаляет все возможные стадии с коробочного портала"""
    methods_to_get, methods_to_delete = [], []
    batch_get_result, batch_delete_result = None, None

    box_token = BoxBitrixToken()

    box_group_ids = (Group.objects.all().values_list("destination_id", flat=True))
    try:
        for group_id in box_group_ids:
            params = {
                "entityId": group_id,
                "isAdmin": "Y",
            }

            methods_to_get.append((str(group_id), "task.stages.get", params))

        batch_get_result = box_token.batch_api_call(methods_to_get)
        for group_id, result_for_group in batch_get_result.successes.items():
            for stage_id in result_for_group['result']:
                params = {
                    "id": int(stage_id),
                    "isAdmin": "Y",
                }
                methods_to_delete.append((str(stage_id), "task.stages.delete", params))

        batch_delete_result = box_token.batch_api_call(methods_to_delete)

    except Exception as exc:
        debug_point("delete_box_stages\n"
                    "Произошла ошибка во время удаления стадий\n\n"
                    f"{exc}")

    finally:
        debug_point("delete_box_stages\n"
                    f"Успешно удалено {len(batch_delete_result.successes)} стадий\n"
                    f"На портале осталось: {len(methods_to_delete) - len(batch_delete_result.successes)}")
        return batch_delete_result
