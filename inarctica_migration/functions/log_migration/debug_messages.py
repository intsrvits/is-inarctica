def error_log_message(
        exc,
        cloud_blogpost_cnt,
        box_blogpost_cnt,
        migrated_now,
        dest=None
) -> str:
    """"""
    if dest:
        message = ("❌ Произошла ошибка при переносе групповой ленты\n"
                   f"ID группы: {dest}\n\n")
    else:
        message = "❌ Произошла ошибка при переносе общей ленты\n\n"

    message += (f"Всего на облаке: {cloud_blogpost_cnt}\n"
                f"Всего на коробке: {box_blogpost_cnt}\n\n"
                f"Пересено сейчас: {migrated_now}"
                f"{exc}")

    return message


def success_log_message(
        cloud_blogpost_cnt,
        box_blogpost_cnt,
        migrated_now,
        cloud_dest=None,
        box_dest=None,
) -> str:
    """"""
    if cloud_blogpost_cnt == box_blogpost_cnt:
        message = "✅"
    else:
        message = "⚠️"
    if cloud_dest:
        message += ("Успешно перенесена групповая лента\n"
                    f"ID группы на облаке: {cloud_dest} https://inarctica.bitrix24.ru/workgroups/group/{cloud_dest}/general/\n"
                    f"ID группы на коробке: {box_dest} https://bitrix24.inarctica.com/workgroups/group/{box_dest}/general/\n\n"
                    )
    else:
        message += "Произошла ошибка при переносе общей ленты\n\n"

    message += (f"Всего на облаке: {cloud_blogpost_cnt}\n"
                f"Всего на коробке: {box_blogpost_cnt}\n\n"
                f"Пересено сейчас: {migrated_now}"
                )

    return message
