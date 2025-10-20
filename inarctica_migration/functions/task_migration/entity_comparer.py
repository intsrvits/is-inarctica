from inarctica_migration.models import User


def compare_tasks(task_ids: int | list):
    """Сопоставляет задачи с облака и коробки на основе данных БД"""
    if isinstance(task_ids, int):
        user = []
        ...
    else:
        ...
def comapare_users(user_ids: int | list, users_qs):
    """Сопоставляет пользователей с облака и коробки на основе данных БД"""
    if isinstance(user_ids, int):
        t = []
        ...
    else:
        ...