from django.db import models

# from b24_itsolution.models import BTasks


class BForumTopic(models.Model):
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    forum_id = models.IntegerField(db_column='FORUM_ID')  # Field name made lowercase.
    topic_id = models.BigIntegerField(db_column='TOPIC_ID', blank=True, null=True)  # Field name made lowercase.
    title = models.CharField(db_column='TITLE', max_length=255)  # Field name made lowercase.
    title_seo = models.CharField(db_column='TITLE_SEO', max_length=255, blank=True, null=True)  # Field name made lowercase.
    tags = models.CharField(db_column='TAGS', max_length=255, blank=True, null=True)  # Field name made lowercase.
    description = models.CharField(db_column='DESCRIPTION', max_length=255, blank=True, null=True)  # Field name made lowercase.
    icon_id = models.IntegerField(db_column='ICON_ID', blank=True, null=True)  # Field name made lowercase.
    state = models.CharField(db_column='STATE', max_length=1)  # Field name made lowercase.
    approved = models.CharField(db_column='APPROVED', max_length=1)  # Field name made lowercase.
    sort = models.IntegerField(db_column='SORT')  # Field name made lowercase.
    views = models.IntegerField(db_column='VIEWS')  # Field name made lowercase.
    user_start_id = models.IntegerField(db_column='USER_START_ID', blank=True, null=True)  # Field name made lowercase.
    user_start_name = models.CharField(db_column='USER_START_NAME', max_length=255, blank=True, null=True)  # Field name made lowercase.
    start_date = models.DateTimeField(db_column='START_DATE')  # Field name made lowercase.
    posts = models.IntegerField(db_column='POSTS')  # Field name made lowercase.
    last_poster_id = models.IntegerField(db_column='LAST_POSTER_ID', blank=True, null=True)  # Field name made lowercase.
    last_poster_name = models.CharField(db_column='LAST_POSTER_NAME', max_length=255)  # Field name made lowercase.
    last_post_date = models.DateTimeField(db_column='LAST_POST_DATE')  # Field name made lowercase.
    last_message_id = models.BigIntegerField(db_column='LAST_MESSAGE_ID', blank=True, null=True)  # Field name made lowercase.
    posts_unapproved = models.IntegerField(db_column='POSTS_UNAPPROVED', blank=True, null=True)  # Field name made lowercase.
    abs_last_poster_id = models.IntegerField(db_column='ABS_LAST_POSTER_ID', blank=True, null=True)  # Field name made lowercase.
    abs_last_poster_name = models.CharField(db_column='ABS_LAST_POSTER_NAME', max_length=255, blank=True, null=True)  # Field name made lowercase.
    abs_last_post_date = models.DateTimeField(db_column='ABS_LAST_POST_DATE', blank=True, null=True)  # Field name made lowercase.
    abs_last_message_id = models.BigIntegerField(db_column='ABS_LAST_MESSAGE_ID', blank=True, null=True)  # Field name made lowercase.
    xml_id = models.CharField(db_column='XML_ID', max_length=255, blank=True, null=True)  # Field name made lowercase.
    html = models.TextField(db_column='HTML', blank=True, null=True)  # Field name made lowercase.
    socnet_group_id = models.IntegerField(db_column='SOCNET_GROUP_ID', blank=True, null=True)  # Field name made lowercase.
    owner_id = models.IntegerField(db_column='OWNER_ID', blank=True, null=True)  # Field name made lowercase.
    icon = models.CharField(db_column='ICON', max_length=255, blank=True, null=True)  # Field name made lowercase.
    posts_service = models.IntegerField(db_column='POSTS_SERVICE')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'b_forum_topic'

    # @property
    # def task(self):
    #     return BTasks.objects.get(id=self.xml_id.split('TASK_')[1])
    #
    # # def assistant_str(self):
    # #     return f"Задача: {self.task.title} {self.task.link}\nКомментарий: {self.post_message}\n"
    #
    # class QuerySet(models.QuerySet):
    #
    #     def qs_tasks_topics(qs):
    #         """
    #         Отфильтрует комментарии к задаче по id форума 11 ( нашел в табилце b_forum 11=Intranet Tasks)
    #         """
    #         qs = qs.filter(forum_id=11)
    #         return qs
    #
    # objects = QuerySet.as_manager()