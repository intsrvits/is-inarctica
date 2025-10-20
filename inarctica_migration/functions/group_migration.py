from inarctica_migration.models import Group, User
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken


def _create_groups(cloud_token: CloudBitrixToken, box_token: BoxBitrixToken):
    """Создаёт группы, которые есть на cloud-портале, но нет на box-портале"""

    bulk_data = []

    try:
        # {origin_id : destination_id}
        group_origin_destination_map: dict[int, int] = dict(Group.objects.all().values_list("origin_id", "destination_id"))
        user_origin_destination_map: dict[int, int] = dict(User.objects.all().values_list("origin_id", "destination_id"))

        origin_groups = cloud_token.call_list_method("sonet_group.get", {"IS_ADMIN": "Y"})
        destination_groups = box_token.call_list_method("sonet_group.get", {"IS_ADMIN": "Y"})

        box_group_ids = set(int(group["ID"]) for group in destination_groups)

        for group in origin_groups:

            if group_origin_destination_map.get(int(group["ID"])) not in box_group_ids:

                params_to_migrate = {
                    "NAME": group.get("NAME"),
                    "DESCRIPTION": group.get("DESCRIPTION"),
                    "VISIBLE": group.get("VISIBLE"),
                    "OPENED": group.get("OPENED"),
                    "KEYWORDS": group.get("KEYWORDS"),
                    "INITIATE_PERMS": "A",
                    "ACTIVE": group.get("ACTIVE"),
                    "PROJECT": group.get("PROJECT"),
                    "CLOSED": group.get("CLOSED"),
                    "OWNER_ID": user_origin_destination_map.get(int(group["OWNER_ID"]), 1),
                }

                try:
                    destination_id = box_token.call_api_method("sonet_group.create", params_to_migrate)["result"]
                    bulk_data.append(Group(origin_id=int(group["ID"]), destination_id=destination_id))
                except Exception as exc:
                    print(f"Ошибка при создании с параметрами {params_to_migrate}: {exc}")

        Group.objects.bulk_create(
            bulk_data,
            unique_fields=["origin_id"],
            update_fields=["destination_id"],
            update_conflicts=True,
        )

    except Exception as exc:
        Group.objects.bulk_create(
            bulk_data,
            unique_fields=["origin_id"],
            update_fields=["destination_id"],
            update_conflicts=True,
        )

        print(f"Произошла ошибка во время создания групп: {str(exc)}")
        raise


def _add_users(cloud_token: CloudBitrixToken, box_token: BoxBitrixToken):
    """Добавляет в группы пользователей и обновляет им роль"""

    methods_to_get, methods_to_add, methods_to_update = [], [], []

    try:
        # {origin_id : destination_id}
        group_origin_destination_map: dict[int, int] = dict(Group.objects.all().values_list("origin_id", "destination_id"))
        user_origin_destination_map: dict[int, int] = dict(User.objects.all().values_list("origin_id", "destination_id"))

        # Забираем всех информацию о пользователях из всех групп
        for origin_group_id in group_origin_destination_map:
            methods_to_get.append((str(origin_group_id), "sonet_group.user.get", {"ID": origin_group_id}))

        # {"group_id": [{"USER_ID1": "USER_ROLE1", ...}], ...}
        batch_taking_users = cloud_token.batch_api_call(methods_to_get)

        # Проходимся по всем группам и заполняем methods для батча на добавление и на обновление.
        for group_id, attributes in batch_taking_users.successes.items():
            destination_group_id = group_origin_destination_map.get(int(group_id))
            users_in_cloud_group = attributes['result']

            for user in users_in_cloud_group:
                destination_user_id = user_origin_destination_map.get(int(user["USER_ID"]))
                methods_to_add.append(("sonet_group.user.add", {"GROUP_ID": destination_group_id, "USER_ID": destination_user_id}))
                methods_to_update.append(("sonet_group.user.update", {"GROUP_ID": destination_group_id, "USER_ID": destination_user_id, "ROLE": user["ROLE"]}))

        box_token.batch_api_call(methods_to_add)
        box_token.batch_api_call(methods_to_update)

    except Exception as exc:
        print(f"Произошла ошибка во время добавления пользователей в группы: {str(exc)}")


def migrate_group():
    """Полный цикл миграции групп"""

    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    # Создаём группы
    _create_groups(cloud_token, box_token)

    # Добавляем пользователей в группы и задаём им роли
    _add_users(cloud_token, box_token)

    return "success"
