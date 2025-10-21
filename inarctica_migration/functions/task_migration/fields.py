# Поля задач, приведенные в camel-case (Для чтения битрикс-респонса)
task_fields_in_camel = [
    "parentId", "title", "description",
    "mark", "priority", "multitask",
    "notViewed", "replicate", "groupId",
    "createdDate", "changedDate", "closedDate",
    "activityDate", "dateStart", "deadline",
    "timeEstimate", "timeSpentInLogs", "matchWorkTime",
    "startDatePlan", "allowChangeDeadline", "allowTimeTracking",
    "taskControl", "addInReport", "isMuted",
    "isPinned", "isPinnedInGroup", "descriptionInBbcode",
    "status", "statusChangedDate", "durationPlan",
    "durationType", "favorite",
]

# Поля задач, связанные с пользователем, приведенные в camel-case (Для чтения битрикс-респонса)
task_user_fields_in_camel = [
    "createdBy", "responsibleId", "statusChangedBy",
    "closedBy", "auditors", "accomplices",
]

# Поля задач, приведенные в upper_case (Для отправки запросов на битрикс)
task_fields_in_upper = [
    "PARENT_ID", "TITLE", "DESCRIPTION",
    "MARK", "PRIORITY", "MULTITASK",
    "NOT_VIEWED", "REPLICATE", "GROUP_ID",
    "CREATED_DATE", "CHANGED_DATE", "CLOSED_DATE",
    "ACTIVITY_DATE", "DATE_START", "DEADLINE",
    "TIME_ESTIMATE", "TIME_SPENT_IN_LOGS", "MATCH_WORK_TIME",
    "START_DATE_PLAN", "ALLOW_CHANGE_DEADLINE", "ALLOW_TIME_TRACKING",
    "TASK_CONTROL", "ADD_IN_REPORT", "IS_MUTED",
    "IS_PINNED", "IS_PINNED_IN_GROUP", "DESCRIPTION_IN_BBCODE",
    "STATUS", "STATUS_CHANGED_DATE", "DURATION_PLAN",
    "DURATION_TYPE", "FAVORITE",
]

# Поля задач, связанные с пользователем, приведенные в upper_case (Для отправки запросов на битрикс)
task_user_fields_in_upper = [
    "CREATED_BY", "RESPONSIBLE_ID", "STATUS_CHANGED_BY",
    "CLOSED_BY", "AUDITORS", "ACCOMPLICES",
]

task_fields_map = {
    "parentId": "PARENT_ID",
    "title": "TITLE",
    "description": "DESCRIPTION",
    "mark": "MARK",
    "priority": "PRIORITY",
    "multitask": "MULTITASK",
    "notViewed": "NOT_VIEWED",
    "replicate": "REPLICATE",
    "groupId": "GROUP_ID",
    "createdDate": "CREATED_DATE",
    "changedDate": "CHANGED_DATE",
    "closedDate": "CLOSED_DATE",
    "activityDate": "ACTIVITY_DATE",
    "dateStart": "DATE_START",
    "deadline": "DEADLINE",
    "timeEstimate": "TIME_ESTIMATE",
    "timeSpentInLogs": "TIME_SPENT_IN_LOGS",
    "matchWorkTime": "MATCH_WORK_TIME",
    "startDatePlan": "START_DATE_PLAN",
    "allowChangeDeadline": "ALLOW_CHANGE_DEADLINE",
    "allowTimeTracking": "ALLOW_TIME_TRACKING",
    "taskControl": "TASK_CONTROL",
    "addInReport": "ADD_IN_REPORT",
    "isMuted": "IS_MUTED",
    "isPinned": "IS_PINNED",
    "isPinnedInGroup": "IS_PINNED_IN_GROUP",
    "descriptionInBbcode": "DESCRIPTION_IN_BBCODE",
    "status": "STATUS",
    "statusChangedDate": "STATUS_CHANGED_DATE",
    "durationPlan": "DURATION_PLAN",
    "durationType": "DURATION_TYPE",
    "favorite": "FAVORITE",
}

task_user_fields_map = {
    "createdBy": "CREATED_BY",
    "responsibleId": "RESPONSIBLE_ID",
    "statusChangedBy": "STATUS_CHANGED_BY",
    "closedBy": "CLOSED_BY",
    "auditors": "AUDITORS",
    "accomplices": "ACCOMPLICES",
}