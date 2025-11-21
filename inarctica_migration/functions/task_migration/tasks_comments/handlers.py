import re

from inarctica_migration.functions.task_migration.bx_rest_request import bx_task_commentitem_getlist
from inarctica_migration.functions.task_migration.fields import SYSTEM_COMMNETS
from inarctica_migration.models import User
from inarctica_migration.utils import CloudBitrixToken
from integration_utils.bitrix24.exceptions import BitrixApiError


def _is_system_comment(text: str) -> bool:
    """
    Проверяет, является ли текст системным комментарием.

    Извлекает первую часть сообщения до точки или двоеточия и сравнивает
    её с известными системными комментариями.

    :param text: Текст комментария для проверки.
    :return: True, если текст является системным комментарием, иначе False.
    """

    # Нас интересует только первая часть сообщения
    comment = re.split(r"[.:]", text)[0]

    return any(system_comment in comment.lower() for system_comment in SYSTEM_COMMNETS)


def get_comments_to_migration(cloud_token: CloudBitrixToken, task_id: int) -> dict[int, dict]:
    """
    Извлекает и возвращает пользовательские комментарии к задаче для миграции.

    Получает все комментарии, связанные с указанной задачей, в порядке их создания.
    Отфильтровывает системные комментарии, чтобы они не входили в возвращаемый результат.

    :param cloud_token: Объект CloudBitrixToken, необходимый для аутентификации.
    :param task_id: Идентификатор задачи, для которой запрашиваются комментарии.
    :return: Словарь, где ключи – идентификаторы комментариев, а значения – сами комментарии.
    """

    params = {"TASK_ID": task_id, "ORDER": {"ID": "ASC"}}
    try:
        all_comments = bx_task_commentitem_getlist(cloud_token, params)
    except BitrixApiError as exc:
        if exc.error_description == "TASKS_ERROR_EXCEPTION_#8; Action failed; 8/TE/ACTION_FAILED_TO_BE_PROCESSED<br>":
            return dict()
        else:
            raise

    # Получаем только пользовательские комментарии (без системных)
    comments_to_migrate: dict[int, dict] = dict()
    for comment in all_comments:
        if not (_is_system_comment(comment["POST_MESSAGE"])):
            comment_id = int(comment["ID"])
            comments_to_migrate[comment_id] = comment

    return comments_to_migrate


def _replace_user_id(match: re.Match) -> str:
    """Заменяет [USER=cloud_id] на [USER=box_id]."""
    cloud_id = int(match.group(1))
    user = User.objects.filter(origin_id=cloud_id).first()
    box_id = user.destination_id if user else 1
    return f"[USER={box_id}]"


def clean_post_message(text: str, attachment_file_id_map: dict | None) -> str:
    """
    Подготавливает текст поста:
    - заменяет [USER=cloud_id] → [USER=box_id]
    - заменяет [DISK FILE ID=n123] → [DISK FILE ID=<новый_id>] по словарю
    - если текст пустой — возвращает "Прикрепление файлов"
    """

    # Замена пользователей
    prepared_text = re.sub(r'\[USER=(\d+)\]', _replace_user_id, text)

    # Замена файлов, если передан словарь
    if attachment_file_id_map:
        def _replace_disk_id(match: re.Match) -> str:
            disk_id = int(match.group(1)[1:])
            new_id = attachment_file_id_map.get(disk_id)
            if new_id:
                return f"[DISK FILE ID=n{new_id}]"
            # если не найдено в словаре — можно удалить тег
            return ""

        prepared_text = re.sub(r'\[DISK FILE ID=(n\d+)\]', _replace_disk_id, prepared_text)

    # Если после замены остался только "пустой" текст
    if not prepared_text.strip():
        return "Прикрепление файлов"

    return prepared_text
