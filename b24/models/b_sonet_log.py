from django.db import models


class BSonetLog(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    entity_type = models.CharField(db_column='ENTITY_TYPE', max_length=50)  # Field name made lowercase.
    entity_id = models.IntegerField(db_column='ENTITY_ID')  # Field name made lowercase.
    event_id = models.CharField(db_column='EVENT_ID', max_length=50)  # Field name made lowercase.
    user_id = models.IntegerField(db_column='USER_ID', blank=True, null=True)  # Field name made lowercase.
    log_date = models.DateTimeField(db_column='LOG_DATE')  # Field name made lowercase.
    site_id = models.CharField(db_column='SITE_ID', max_length=2, blank=True, null=True)  # Field name made lowercase.
    title_template = models.CharField(db_column='TITLE_TEMPLATE', max_length=250, blank=True, null=True)  # Field name made lowercase.
    title = models.CharField(db_column='TITLE', max_length=250)  # Field name made lowercase.
    message = models.TextField(db_column='MESSAGE', blank=True, null=True)  # Field name made lowercase.
    text_message = models.TextField(db_column='TEXT_MESSAGE', blank=True, null=True)  # Field name made lowercase.
    url = models.CharField(db_column='URL', max_length=500, blank=True, null=True)  # Field name made lowercase.
    module_id = models.CharField(db_column='MODULE_ID', max_length=50, blank=True, null=True)  # Field name made lowercase.
    callback_func = models.CharField(db_column='CALLBACK_FUNC', max_length=250, blank=True, null=True)  # Field name made lowercase.
    external_id = models.CharField(db_column='EXTERNAL_ID', max_length=250, blank=True, null=True)  # Field name made lowercase.
    params = models.TextField(db_column='PARAMS', blank=True, null=True)  # Field name made lowercase.
    tmp_id = models.IntegerField(db_column='TMP_ID', blank=True, null=True)  # Field name made lowercase.
    source_id = models.IntegerField(db_column='SOURCE_ID', blank=True, null=True)  # Field name made lowercase.
    log_update = models.DateTimeField(db_column='LOG_UPDATE')  # Field name made lowercase.
    comments_count = models.IntegerField(db_column='COMMENTS_COUNT', blank=True, null=True)  # Field name made lowercase.
    enable_comments = models.CharField(db_column='ENABLE_COMMENTS', max_length=1, blank=True, null=True)  # Field name made lowercase.
    rating_type_id = models.CharField(db_column='RATING_TYPE_ID', max_length=50, blank=True, null=True)  # Field name made lowercase.
    rating_entity_id = models.IntegerField(db_column='RATING_ENTITY_ID', blank=True, null=True)  # Field name made lowercase.
    source_type = models.CharField(db_column='SOURCE_TYPE', max_length=50, blank=True, null=True)  # Field name made lowercase.
    transform = models.CharField(db_column='TRANSFORM', max_length=1, blank=True, null=True)  # Field name made lowercase.
    inactive = models.CharField(db_column='INACTIVE', max_length=1, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'b_sonet_log'
