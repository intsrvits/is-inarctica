from inarctica_migration.models import LogMigration
from inarctica_migration.functions.helpers import execution_time_counter


@execution_time_counter
def init_cloud_blogposts(blogposts: list[dict], dest: str):
    """"""
    bulk_data = []
    result = {}

    for blogpost in blogposts:
        cloud_id = blogpost['ID']

        bulk_data.append(
            LogMigration(
                cloud_id=cloud_id,
                dest=dest
            )
        )

        result[cloud_id] = False

    LogMigration.objects.bulk_create(
        bulk_data,
    )

    return result