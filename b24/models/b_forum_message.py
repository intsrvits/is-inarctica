from django.db import models


class BForumMessage(models.Model):
    """
    Здесь хранятся комментарии к задачам
    """

    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    forum_id = models.IntegerField(db_column='FORUM_ID')  # Field name made lowercase.
    #topic_id = models.BigIntegerField(db_column='TOPIC_ID')  # Field name made lowercase.
    # topic = models.ForeignKey('BForumTopic', db_column='TOPIC_ID', on_delete=models.PROTECT)  # Field name made lowercase.
    use_smiles = models.CharField(db_column='USE_SMILES', max_length=1)  # Field name made lowercase.
    new_topic = models.CharField(db_column='NEW_TOPIC', max_length=1)  # Field name made lowercase.
    approved = models.CharField(db_column='APPROVED', max_length=1)  # Field name made lowercase.
    source_id = models.CharField(db_column='SOURCE_ID', max_length=255)  # Field name made lowercase.
    post_date = models.DateTimeField(db_column='POST_DATE')  # Field name made lowercase.
    post_message = models.TextField(db_column='POST_MESSAGE', blank=True, null=True)  # Field name made lowercase.
    post_message_html = models.TextField(db_column='POST_MESSAGE_HTML', blank=True, null=True)  # Field name made lowercase.
    post_message_filter = models.TextField(db_column='POST_MESSAGE_FILTER', blank=True, null=True)  # Field name made lowercase.
    post_message_check = models.CharField(db_column='POST_MESSAGE_CHECK', max_length=32, blank=True, null=True)  # Field name made lowercase.
    attach_img = models.IntegerField(db_column='ATTACH_IMG', blank=True, null=True)  # Field name made lowercase.
    param1 = models.CharField(db_column='PARAM1', max_length=2, blank=True, null=True)  # Field name made lowercase.
    param2 = models.IntegerField(db_column='PARAM2', blank=True, null=True)  # Field name made lowercase.
    #author_id = models.IntegerField(db_column='AUTHOR_ID', blank=True, null=True)  # Field name made lowercase.
    # author = models.ForeignKey('b24_itsolution.BUser', on_delete=models.PROTECT, blank=True, null=True)  # Field name made lowercase.
    author_name = models.CharField(db_column='AUTHOR_NAME', max_length=255, blank=True, null=True)  # Field name made lowercase.
    author_email = models.CharField(db_column='AUTHOR_EMAIL', max_length=255, blank=True, null=True)  # Field name made lowercase.
    author_ip = models.CharField(db_column='AUTHOR_IP', max_length=255, blank=True, null=True)  # Field name made lowercase.
    author_real_ip = models.CharField(db_column='AUTHOR_REAL_IP', max_length=128, blank=True, null=True)  # Field name made lowercase.
    guest_id = models.IntegerField(db_column='GUEST_ID', blank=True, null=True)  # Field name made lowercase.
    editor_id = models.IntegerField(db_column='EDITOR_ID', blank=True, null=True)  # Field name made lowercase.
    editor_name = models.CharField(db_column='EDITOR_NAME', max_length=255, blank=True, null=True)  # Field name made lowercase.
    editor_email = models.CharField(db_column='EDITOR_EMAIL', max_length=255, blank=True, null=True)  # Field name made lowercase.
    edit_reason = models.TextField(db_column='EDIT_REASON', blank=True, null=True)  # Field name made lowercase.
    edit_date = models.DateTimeField(db_column='EDIT_DATE', blank=True, null=True)  # Field name made lowercase.

    # TASK_183933 - значит что комментарии к задаче 183933
    xml_id = models.CharField(db_column='XML_ID', max_length=255, blank=True, null=True)  # Field name made lowercase.
    html = models.TextField(db_column='HTML', blank=True, null=True)  # Field name made lowercase.
    mail_header = models.TextField(db_column='MAIL_HEADER', blank=True, null=True)  # Field name made lowercase.
    service_type = models.IntegerField(db_column='SERVICE_TYPE', blank=True, null=True)  # Field name made lowercase.
    service_data = models.TextField(db_column='SERVICE_DATA', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'b_forum_message'

    # @property
    # def task_id(self):
    #     """
    #     Ссылка на задачу хранится странно в поле xml_id
    #     Но бывают случаи когда пустой xml_id, но есть выше в топике xml_id
    #     """
    #     xml_id = self.xml_id if self.xml_id else self.topic.xml_id
    #     return int(xml_id.split('TASK_')[1])
    #
    # @property
    # def task(self):
    #     return BTasks.objects.get(id=self.task_id)
