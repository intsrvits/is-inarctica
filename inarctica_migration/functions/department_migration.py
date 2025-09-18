from inarctica_migration.models import Department, User
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from integration_utils.bitrix24.bitrix_token import BitrixToken


def _create_departments(cloud_token: BitrixToken, box_token: BitrixToken) -> list[dict]:
    """"""

    methods = []

    try:
        # {origin_id : destination_id}
        origin_destination_map: dict[int, int] = dict(Department.objects.all().values_list("origin_id", "destination_id"))

        origin_departments = cloud_token.call_list_method("department.get")
        destination_departments = box_token.call_list_method("department.get")
        box_department_ids = set(int(department['ID']) for department in destination_departments)

        for department in origin_departments:
            if origin_destination_map.get(int(department["ID"])) not in box_department_ids:
                params = {
                    "NAME": department["NAME"],
                    "SORT": department.get("SORT"),
                    "PARENT": 1,
                }

                methods.append((str(department["ID"]), "department.add", params))

        batch_and_result = box_token.batch_api_call(methods)

        # {origin_id: destination_id}
        origin_destintaion_map: dict[str, str] = {str(cloud_id): str(box_entity["result"]) for cloud_id, box_entity in batch_and_result.successes.items()}

        bulk_data = [Department(origin_id=cloud_id, destination_id=destination_id) for cloud_id, destination_id in origin_destintaion_map.items()]
        Department.objects.bulk_create(
            bulk_data,
            unique_fields=["origin_id"],
            update_fields=["destination_id"],
            update_conflicts=True,
        )

    except Exception as exc:
        print(f"Произошла ошибка во время создания департаментов: {str(exc)}")
        raise

    return origin_departments


def _structure_departments(box_token: BitrixToken, origin_departments: list[dict]):
    """Синхронизация структуры и руководителей отделов"""
    origin_destination_user_map: dict[int, int] = dict(User.objects.all().values_list("origin_id", "destination_id"))
    origin_destination_department_map: dict[int, int] = dict(Department.objects.all().values_list("origin_id", "destination_id"))

    methods = []

    try:
        for department in origin_departments:

            # В корневой отдел установить руководителя нужно вручную!
            if department.get("PARENT") and department.get("UF_HEAD") and origin_destination_user_map.get(int(department.get("UF_HEAD"))):
                params = {
                    "ID": origin_destination_department_map[int(department["ID"])],
                    "PARENT": origin_destination_department_map[int(department.get("PARENT"))],
                    "UF_HEAD": origin_destination_user_map[int(department.get("UF_HEAD"))],
                }

                methods.append((department["ID"], "department.update", params))

        batch_and_result = box_token.batch_api_call(methods)

    except Exception as exc:
        print(f"Произошла ошибка во время структурирования: {str(exc)}")
        raise

    return dict(success=f"Успешно структурировано: {batch_and_result.successes}")


def migrate_departments():
    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    origin_departments = _create_departments(cloud_token=cloud_token, box_token=box_token)
    _structure_departments(box_token=box_token, origin_departments=origin_departments)

    return 'success'
