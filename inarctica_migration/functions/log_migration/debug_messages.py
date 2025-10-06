def error_log_message(
        exc,
        total_found,
        migrated,
        dest=None
) -> str:
    """"""
    if dest:
        message = ("Произошла ошибка при переносе групповой ленты\n"
                   f"ID группы: {dest}\n\n")
    else:
        message = "Произошла ошибка при переносе общей ленты\n\n"

    message += (f"Всего найдено: {total_found}\n"
                f"Перенесено: {migrated}\n\n"
                f"{exc}")

    return message


def success_log_message(

        total_found,
        migrated,
        dest=None
) -> str:
    """"""
    if dest:
        message = ("Успешно перенесена групповая лента\n"
                   f"ID группы: {dest}\n\n")
    else:
        message = "Произошла ошибка при переносе общей ленты\n\n"

    message += (f"Всего найдено: {total_found}\n"
                f"Перенесено: {migrated}\n\n")

    return message
