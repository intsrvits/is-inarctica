from inarctica_migration.models import Group, User
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken
from integration_utils.bitrix24.bitrix_token import BitrixToken

SELECT_FIELDS = ("ID", "ACTIVE", "SITE_ID", "SUBJECT_ID", "SUBJECT_DATA", "NAME", "DESCRIPTION", "KEYWORDS", "CLOSED", "VISIBLE",
                 "OPENED", "PROJECT", "LANDING", "DATE_CREATE", "DATE_UPDATE", "DATE_ACTIVITY", "IMAGE_ID", "AVATAR",  "AVATAR_TYPE", "AVATAR_TYPES",
                 "OWNER_ID", "OWNER_DATA", "NUMBER_OF_MEMBERS", "NUMBER_OF_MODERATORS", "INITIATE_PERMS", "PROJECT_DATE_START",
                 "PROJECT_DATE_FINISH", "SEARCH_INDEX", "SCRUM_OWNER_ID", "SCRUM_MASTER_ID", "SCRUM_SPRINT_DURATION",
                 "SCRUM_TASK_RESPONSIBLE", "TYPE", "UF_SG_DEPT", "TAGS", "ACTIONS", "USER_DATA")


def _create_groups(cloud_token: BitrixToken, box_token: BitrixToken):
    """Создаёт группы, которые есть на cloud-портале, но нет на box-портале"""

    bulk_data = []
    try:
        # {origin_id : destination_id}
        group_origin_destination_map: dict[int, int] = dict(Group.objects.all().values_list("origin_id", "destination_id"))
        user_origin_destination_map: dict[int, int] = dict(User.objects.all().values_list("origin_id", "destination_id"))

        params_to_select = {
            "IS_ADMIN": "Y",
            "select": [
                "ID",
                "NAME",
                "DESCRIPTION"
                "VISIBLE",
                "OPENED",
                "KEYWORDS",
                "INITIATE_PERMS",
                "CLOSED",
                "SPAM_PERMS",
                "PROJECT",
                "PROJECT_DATE_FINISH",
                "PROJECT_DATE_START",
                "SCRUM_MASTER_ID",
                "OWNER_ID",
            ]
        }

        origin_groups = cloud_token.call_list_method("socialnetwork.api.workgroup.list", params_to_select)["workgroups"]
        destination_groups = box_token.call_list_method("socialnetwork.api.workgroup.list", params_to_select)["workgroups"]

        box_group_ids = set(int(group["id"]) for group in destination_groups)
        for group in origin_groups:
            _SCRUM_MASTER_ID = None

            if group_origin_destination_map.get(int(group["id"])) not in box_group_ids:

                if group.get("scrumMasterId"):
                    _SCRUM_MASTER_ID = user_origin_destination_map[int(group.get("scrumMasterId"))]

                params_to_migrate = {
                    "NAME": group.get("name"),
                    "DESCRIPTION": group.get("description"),
                    "VISIBLE": group.get("visible"),
                    "OPENED": group.get("opened"),
                    "KEYWORDS": group.get("keywords"),
                    "INITIATE_PERMS": group.get("initiatePerms"),
                    "CLOSED": group.get("closed"),
                    "SPAM_PERMS": group.get("spamPerms"),
                    "PROJECT": group.get("project"),
                    "PROJECT_DATE_FINISH": group.get("projectDateFinish"),
                    "PROJECT_DATE_START": group.get("projectDateStart"),
                    "OWNER_ID": user_origin_destination_map.get(int(group["ownerId"]), 1),
                    "SCRUM_MASTER_ID": _SCRUM_MASTER_ID,
                }

                destination_id = box_token.call_api_method("sonet_group.create", params_to_migrate)["result"]
                bulk_data.append(Group(origin_id=int(group["id"]), destination_id=destination_id))

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


def migrate_group():
    """Полный цикл миграции групп"""
    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()

    # Создаём группы
    _create_groups(cloud_token, box_token)

    return "success"
