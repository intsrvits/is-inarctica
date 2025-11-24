from django.db import models


class BSonetLogComment(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    log = models.ForeignKey("b24.BSonetLog", db_column='LOG_ID', on_delete=models.DO_NOTHING)  # Field name made lowercase.
    entity_type = models.CharField(db_column='ENTITY_TYPE', max_length=50)  # Field name made lowercase.
    entity_id = models.IntegerField(db_column='ENTITY_ID')  # Field name made lowercase.
    event_id = models.CharField(db_column='EVENT_ID', max_length=50)  # Field name made lowercase.
    user_id = models.IntegerField(db_column='USER_ID', blank=True, null=True)  # Field name made lowercase.
    log_date = models.DateTimeField(db_column='LOG_DATE')  # Field name made lowercase.
    message = models.TextField(db_column='MESSAGE', blank=True, null=True)  # Field name made lowercase.
    text_message = models.TextField(db_column='TEXT_MESSAGE', blank=True, null=True)  # Field name made lowercase.
    module_id = models.CharField(db_column='MODULE_ID', max_length=50, blank=True, null=True)  # Field name made lowercase.
    source = models.ForeignKey("b24.BForumMessage", db_column='SOURCE_ID', blank=True, null=True, on_delete=models.DO_NOTHING)  # Field name made lowercase.
    url = models.CharField(db_column='URL', max_length=500, blank=True, null=True)  # Field name made lowercase.
    rating_type_id = models.CharField(db_column='RATING_TYPE_ID', max_length=50, blank=True, null=True)  # Field name made lowercase.
    rating_entity_id = models.IntegerField(db_column='RATING_ENTITY_ID', blank=True, null=True)  # Field name made lowercase.
    share_dest = models.TextField(db_column='SHARE_DEST', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'b_sonet_log_comment'
