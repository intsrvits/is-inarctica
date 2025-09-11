from inarctica_migration.models import User
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken


def migrate_users():
    """"""
    cloud_token = CloudBitrixToken()
    box_token = BoxBitrixToken()


    migrated_users = User.objects.all()

    try:
        users = cloud_token.call_list_method('user.get', {'fields': ['*', 'UF_'], '!@FILTER:': list(migrated_users)})
        for user in users:
            ...
            # todo посмотреть какие поля приходят и добавляем

    except Exception as exc:
        ...
