import base64
import os
import re

import requests

from integration_utils.bitrix24.exceptions import BitrixApiException, BitrixApiError

from inarctica_migration.functions.helpers import retry_decorator, debug_point
from inarctica_migration.models import User, Department
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken


@retry_decorator(3, exceptions=(BitrixApiException,), delay=10)
def _add_user(but, params):
    return but.call_api_method('user.add', params)['result']


def _get_file_pair(url: str):
    """
    Функция позволяет взять необходимую пару атрибутов файла, для добавления в Битрикс, по его расположению.
    Возвращает список с вложенным списком.
    """
    if url is None:
        return None

    response = requests.get(url)

    file_name = os.path.basename(url)
    base64_bytestring = base64.b64encode(response.content)
    attached_file = [file_name, base64_bytestring]
    return attached_file


def _validate_personal_phone(phone: str | None = None):
    """"""
    if phone:
        if len(phone) <= 20:
            return phone
        else:
            match = re.findall(r"\+7[\d\s-]+", phone)
            if match:
                return match[0].strip()

    return None


def _department_matcher(departments: list[str]):
    """"""
    origin_destination_department_map: dict[int, int] = dict(Department.objects.all().values_list("origin_id", "destination_id"))
    matched_departments = []

    for department in departments:
        matched_departments.append(origin_destination_department_map[int(department)])

    return matched_departments


def migrate_users():
    """"""
    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    bulk_data = []

    try:
        # {origin_id : destination_id}
        origin_destination_map: dict[int, int] = dict(User.objects.all().values_list('origin_id', 'destination_id'))

        cloud_users = cloud_token.call_list_method('user.get', {'filter': {'ACTIVE': 1, '!USER_TYPE': 'extranet'}, 'ADMIN_MODE': 1})
        box_users = box_token.call_list_method('user.get', {'ADMIN_MODE': 1})
        box_user_ids = set([int(user['ID']) for user in box_users])

        # {}
        email_destination_id_map = {user.get('EMAIL').replace('@russaquaculture.ru', '@inarctica.com'): int(user['ID']) for user in box_users}

        for idx, user in enumerate(cloud_users, start=1):
            if not user.get('EMAIL'):
                continue

            email = user.get('EMAIL').replace('@russaquaculture.ru', '@inarctica.com')

            if origin_destination_map.get(int(user["ID"])) not in box_user_ids:
                params = {
                    "EMAIL": email,
                    "NAME": user.get('NAME'),
                    "LAST_NAME": user.get('LAST_NAME'),
                    "SECOND_NAME": user.get('SECOND_NAME'),
                    "PERSONAL_GENDER": user.get('PERSONAL_GENDER'),
                    "PERSONAL_PROFESSION": user.get('PERSONAL_PROFESSION'),
                    "PERSONAL_WWW": user.get('PERSONAL_WWW'),
                    "PERSONAL_PHOTO": _get_file_pair(user.get('PERSONAL_PHOTO')),
                    "PERSONAL_ICQ": user.get('PERSONAL_ICQ'),
                    "PERSONAL_PHONE": user.get('PERSONAL_PHONE'),
                    "PERSONAL_FAX": user.get('PERSONAL_FAX'),
                    "PERSONAL_MOBILE": _validate_personal_phone(user.get('PERSONAL_MOBILE')),
                    "PERSONAL_PAGER": user.get('PERSONAL_PAGER'),
                    "PERSONAL_STREET": user.get('PERSONAL_STREET'),
                    "PERSONAL_CITY": user.get('PERSONAL_CITY'),
                    "PERSONAL_STATE": user.get('PERSONAL_STATE'),
                    "PERSONAL_ZIP": user.get('PERSONAL_ZIP'),
                    "PERSONAL_COUNTRY": user.get('PERSONAL_COUNTRY'),
                    "PERSONAL_MAILBOX": user.get('PERSONAL_MAILBOX'),
                    "PERSONAL_NOTES": user.get('PERSONAL_NOTES'),
                    "WORK_PHONE": user.get('WORK_PHONE'),
                    "WORK_COMPANY": user.get('WORK_COMPANY'),
                    "WORK_POSITION": user.get('WORK_POSITION'),
                    "WORK_DEPARTMENT": user.get('WORK_DEPARTMENT'),
                    "WORK_WWW": user.get('WORK_WWW'),
                    "WORK_FAX": user.get('WORK_FAX'),
                    "WORK_PAGER": user.get('WORK_PAGER'),
                    "WORK_STREET": user.get('WORK_STREET'),
                    "WORK_MAILBOX": user.get('WORK_MAILBOX'),
                    "WORK_CITY": user.get('WORK_CITY'),
                    "WORK_STATE": user.get('WORK_STATE'),
                    "WORK_ZIP": user.get('WORK_ZIP'),
                    "WORK_COUNTRY": user.get('WORK_COUNTRY'),
                    "WORK_PROFILE": user.get('WORK_PROFILE'),
                    "WORK_LOGO": user.get('WORK_LOGO'),
                    "WORK_NOTES": user.get('WORK_NOTES'),
                    "UF_SKYPE_LINK": user.get('UF_SKYPE_LINK'),
                    "UF_ZOOM": user.get('UF_ZOOM'),
                    "UF_DEPARTMENT": _department_matcher(user.get("UF_DEPARTMENT")),
                    "UF_INTERESTS": user.get('UF_INTERESTS'),
                    "UF_SKILLS": user.get('UF_SKILLS'),
                    "UF_WEB_SITES": user.get('UF_WEB_SITES'),
                    "UF_XING": user.get('UF_XING'),
                    "UF_LINKEDIN": user.get('UF_LINKEDIN'),
                    "UF_FACEBOOK": user.get('UF_FACEBOOK'),
                    "UF_TWITTER": user.get('UF_TWITTER'),
                    "UF_SKYPE": user.get('UF_SKYPE'),
                    "UF_DISTRICT": user.get('UF_DISTRICT'),
                    "UF_PHONE_INNER": user.get('UF_PHONE_INNER'),
                }

                if email in email_destination_id_map:
                    destination_id = email_destination_id_map[email]
                else:
                    destination_id = _add_user(box_token, params)

                bulk_data.append(User(
                    origin_id=int(user['ID']),
                    destination_id=int(destination_id),
                    is_user_migrated=True,
                ))

        User.objects.bulk_create(
            bulk_data,
            unique_fields=["origin_id"],
            update_fields=["destination_id", "is_user_migrated"],
            update_conflicts=True,
        )

        return (f"Создано {idx} user, всего  {len(cloud_users)} ")

    except Exception as exc:
        User.objects.bulk_create(
            bulk_data,
            unique_fields=["origin_id"],
            update_fields=["destination_id", "is_user_migrated"],
            update_conflicts=True,
        )

        raise


def update_user():
    """
    Обновляет поля пользователя
    Функция возникла в результате доработок проекта."""
    methods = []
    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    migrated_users_map: dict[int, int] = dict(User.objects.filter(is_user_migrated=True).values_list("origin_id", "destination_id"))
    cloud_users = cloud_token.call_list_method('user.get', {'filter': {'ACTIVE': 1, '!USER_TYPE': 'extranet'}, 'ADMIN_MODE': 1})

    for cloud_user in cloud_users:
        box_user_id: int = migrated_users_map.get(int(cloud_user['ID']), 0)

        if box_user_id:
            params_to_update = {
                "ID": box_user_id,
                "PERSONAL_BIRTHDAY": cloud_user["PERSONAL_BIRTHDAY"],
                # "UF_EMPLOYMENT_DATE": cloud_user["UF_EMPLOYMENT_DATE"][:10],
                "UF_SKYPE_LINK": cloud_user.get("UF_SKYPE_LINK"),
                "UF_SKYPE": cloud_user.get("UF_SKYPE"),
            }
            methods.append((cloud_user['ID'], "user.update", params_to_update))
            if cloud_user.get("UF_SKYPE_LINK") or cloud_user.get("UF_SKYPE"):
                debug_point(f"https://inarctica.bitrix24.ru/company/personal/user/{cloud_user['ID']}/"
                            f"https://bitrix24.inarctica.com/company/personal/user/{box_user_id}/")
    batch_result = box_token.batch_api_call(methods)

    debug_point("Обновление полей пользователя (update_user)\n"
                f"Всего перенесенных пользователей: {len(migrated_users_map)}"
                f"Обновлено: {len(batch_result.successes)}")

    return batch_result