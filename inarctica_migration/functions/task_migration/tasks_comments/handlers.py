import re

from inarctica_migration.functions.task_migration.bx_rest_request import bx_task_commentitem_getlist
from inarctica_migration.functions.task_migration.fields import SYSTEM_COMMNETS
from inarctica_migration.models import User
from inarctica_migration.utils import CloudBitrixToken


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
    all_comments = bx_task_commentitem_getlist(cloud_token, params)

    # Получаем только пользовательские комментарии (без системных)
    comments_to_migrate: dict[int, dict] = dict()
    for comment in all_comments:
        if not (_is_system_comment(comment["POST_MESSAGE"])):
            comment_id = int(comment["ID"])
            comments_to_migrate[comment_id] = comment

    return comments_to_migrate


def _replace_user_id(match):
    cloud_id = int(match.group(1))  # вытащили число из [USER=208]

    user = User.objects.filter(origin_id=cloud_id).first()
    if user:
        box_id = user.destination_id
    else:
        box_id = 1

    return f"[USER={box_id}]"


def clean_post_message(text: str) -> str:
    """"""
    #text_without_tags = re.sub(r"\s*\[DISK FILE ID=n\d+\]\s*", "", text)
    prepared_text = re.sub(r'\[USER=(\d+)\]', _replace_user_id, text)

    if not prepared_text.replace(" ", "").replace("\n", "").replace("\r", ""):
        return "Прикрепление файлов"

    return prepared_text
