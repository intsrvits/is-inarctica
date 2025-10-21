from inarctica_migration.models import User


def match_tasks(task_ids: int | list):
    """Сопоставляет задачи с облака и коробки на основе данных БД"""
    if isinstance(task_ids, int):
        user = []
        ...
    else:
        ...


def match_users(user_ids: int | list, users_map: dict):
    """Сопоставляет пользователей с облака и коробки на основе данных БД"""
    if isinstance(user_ids, int):
        # Если не найден (например уволен), то возвращаем системного пользователя
        return users_map.get(user_ids, 1)

    else:
        return list(set([match_users(int(user_id), users_map) for user_id in user_ids]))
