from inarctica_migration.models import Folder, Storage
from inarctica_migration.utils import CloudBitrixToken, BoxBitrixToken

from inarctica_migration.functions.helpers import debug_point
from inarctica_migration.functions.disk_migration.bx_rest_requests import _bx_folder_addsubfolder
from inarctica_migration.functions.disk_migration.descent_by_recursion import ordered_hierarchy, recursive_descent


def synchronize_files_for_storage(
        cloud_token: CloudBitrixToken,
        box_token: BoxBitrixToken,
        cloud_storage_id: int,
        storage_relation_map: dict[int, int]
):
    """"""

    taking_methods = []
    adding_methods = []

    bulk_data = []

    try:
        pass
    except:
        pass