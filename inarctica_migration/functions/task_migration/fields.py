# Поля задач, приведенные в camel-case (Для чтения битрикс-респонса)
task_fields_in_camel = [
    "parentId", "title", "description",
    "mark", "priority", "multitask",
    "notViewed", "replicate",
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
    "NOT_VIEWED", "REPLICATE",
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
