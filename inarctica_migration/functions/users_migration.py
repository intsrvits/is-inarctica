import base64
import os
import re

import requests

from integration_utils.bitrix24.exceptions import BitrixApiException

from inarctica_migration.functions.helpers import retry_decorator
from inarctica_migration.models import User, Department
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken


@retry_decorator(3, exceptions=(BitrixApiException,), delay=10)
def _add_user(but, params):
    return but.call_api_method('user.add', params)


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

        cloud_users = cloud_token.call_list_method('user.get', {'ACTIVE': 1})
        box_users = box_token.call_list_method('user.get')
        box_user_ids = set([int(user['ID']) for user in box_users])

        i = 0
        for user in cloud_users:
            if origin_destination_map.get(int(user["ID"])) not in box_user_ids:
                i += 1
                params = {
                    "EMAIL": user.get('EMAIL').replace('@russaquaculture.ru', '@inarctica.com'),
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

                destination_id = box_token.call_api_method('user.add', params)['result']

                bulk_data.append(User(
                    origin_id=int(user['ID']),
                    destination_id=int(destination_id),
                ))

        User.objects.bulk_create(
            bulk_data,
            unique_fields=["origin_id"],
            update_fields=["destination_id"],
            update_conflicts=True,
        )

        return (f"Создано {i} user, всего блоы {len(cloud_users)} ")

    except Exception as exc:
        User.objects.bulk_create(
            bulk_data,
            unique_fields=["origin_id"],
            update_fields=["destination_id"],
            update_conflicts=True,
        )

        raise
