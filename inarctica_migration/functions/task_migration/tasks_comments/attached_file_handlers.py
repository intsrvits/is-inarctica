def check_attachments_in_comment(comment) -> list:
    """Возвращает список прикрепленных к комментарию файлов."""
    attached_files_data = []
    bx_attached_objects = []
    if isinstance(comment.get("ATTACHED_OBJECTS"), list) and len(comment["ATTACHED_OBJECTS"]):
        bx_attached_objects = comment["ATTACHED_OBJECTS"]

    if isinstance(comment.get("ATTACHED_OBJECTS"), dict) and len(comment["ATTACHED_OBJECTS"].keys()):
        bx_attached_objects = comment["ATTACHED_OBJECTS"].values()

    if len(bx_attached_objects):
        for bx_attached_object in bx_attached_objects:
            attached_files_data.append({
                "NAME": bx_attached_object["NAME"],
                "URL": bx_attached_object["DOWNLOAD_URL"],
                "FILE_ID": bx_attached_object["FILE_ID"],
                "SIZE": bx_attached_object["SIZE"]
            })

    return attached_files_data