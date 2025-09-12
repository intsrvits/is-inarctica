from settings import DEBUG_BOT_TOKEN, DEBUG_CHAT_ID

from integration_utils.bitrix24.models import BitrixUserToken

import requests
import time
import traceback
from functools import wraps
from threading import Thread
from typing import Callable, Optional, Text, Tuple

USERNAMES = "@iis_itsolution, @lra710\n\n"


def debug_point(message: Text, with_tags: bool = True, exc_info: Optional[Text] = None):
    if with_tags:
        message = USERNAMES + message

    exc_info = exc_info or traceback.format_exc()

    if exc_info and not exc_info.startswith("NoneType: None"):
        message += f"\n\n{exc_info}"

    telegram_message = ""

    for row in message.split("\n"):
        if len(telegram_message + row) < 4096:  # максимальная длина сообщения в тг = 4096
            telegram_message += "\n" + row
        else:
            requests.post(f"https://api.telegram.org/bot{DEBUG_BOT_TOKEN}/sendMessage", data={"chat_id": DEBUG_CHAT_ID, "text": telegram_message})
            telegram_message = ""

    if telegram_message.strip():
        requests.post(f"https://api.telegram.org/bot{DEBUG_BOT_TOKEN}/sendMessage", data={"chat_id": DEBUG_CHAT_ID, "text": telegram_message})


def async_debug_point(message: Text, with_tags: bool = True):
    exc_info = traceback.format_exc()
    Thread(target=debug_point, args=(message, with_tags, exc_info)).start()


def retry_decorator(attempts: int, exceptions: Tuple = (Exception,), delay: int = 1):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    async_debug_point(f"Попытка {attempt} вызова {func.__name__} не удалась: {exc}. Повтор...", with_tags=False)
                    if attempt == attempts:
                        raise
                    last_exception = exc
                    time.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


def get_admin_token() -> BitrixUserToken:
    """ Получение токена по авторизации с нужными скоупами """
    return BitrixUserToken.objects.filter(user__is_admin=True, user__user_is_active=True).last()
