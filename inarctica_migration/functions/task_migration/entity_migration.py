from inarctica_migration.utils import CloudBitrixToken
from inarctica_migration.models import Group, TaskMigration

from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.task_migration.bx_rest_request import bx_tasks_task_list


def _params_for_tasks(input_params: dict):
    """Преобразует поля, полученные из метода list для метода add"""
    output_params = dict()

    fields = [
        "parentId", "title", "description",
        "mark", "priority", "multitask",
        "notViewed", "replicate", "createdBy",
        "createdDate", "responsibleId", "changedDate",
        "statusChangedBy", "closedBy", "closedDate",
        "activityDate", "dateStart", "deadline",
        "startDatePlan", "allowChangeDeadline", "allowTimeTracking",
        "taskControl", "addInReport", "isMuted",
        "isPinned", "isPinnedInGroup", "descriptionInBbcode",
        "status", "statusChangedDate", "durationPlan",
        "durationType", "favorite", "auditors", "accomplices"
    ]

    for field in fields:
        output_params["fields"][field] = input_params[field]

    #todo дописать логику обработки

    return output_params

def migration_tasks_to_box():
    """"""

    bulk_data = []

    migrated_group_ids = dict(Group.objects.all().values_list("origin_id", "destination_id"))
    qs_initialized_tasks = TaskMigration.objects.all().values_list("cloud_id", flat=True)

    cloud_token = CloudBitrixToken()
    all_cloud_tasks = bx_tasks_task_list(cloud_token)

    processed_tasks_ids = set()
    for task in all_cloud_tasks["tasks"]:

        # Условие, чтобы не пропускать дублирующие сущности с теми же параметрами
        if task["id"] in processed_tasks_ids:
            continue

        group_id = int(task["groupId"]) if isinstance(task["groupId"], str) else None
        #  todo убрать это условие пока только с группами работаем
        if not group_id:
            continue


