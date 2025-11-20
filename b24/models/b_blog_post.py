from django.db import models


class BBlogPost(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    title = models.CharField(db_column='TITLE', max_length=255)  # Field name made lowercase.
    blog_id = models.IntegerField(db_column='BLOG_ID')  # Field name made lowercase.
    author_id = models.IntegerField(db_column='AUTHOR_ID')  # Field name made lowercase.
    preview_text = models.TextField(db_column='PREVIEW_TEXT', blank=True, null=True)  # Field name made lowercase.
    preview_text_type = models.CharField(db_column='PREVIEW_TEXT_TYPE', max_length=4)  # Field name made lowercase.
    detail_text = models.TextField(db_column='DETAIL_TEXT')  # Field name made lowercase.
    detail_text_type = models.CharField(db_column='DETAIL_TEXT_TYPE', max_length=4)  # Field name made lowercase.
    date_create = models.DateTimeField(db_column='DATE_CREATE')  # Field name made lowercase.
    date_publish = models.DateTimeField(db_column='DATE_PUBLISH')  # Field name made lowercase.
    keywords = models.CharField(db_column='KEYWORDS', max_length=255, blank=True, null=True)  # Field name made lowercase.
    publish_status = models.CharField(db_column='PUBLISH_STATUS', max_length=1)  # Field name made lowercase.
    category_id = models.CharField(db_column='CATEGORY_ID', max_length=255, blank=True, null=True)  # Field name made lowercase.
    atribute = models.CharField(db_column='ATRIBUTE', max_length=255, blank=True, null=True)  # Field name made lowercase.
    enable_trackback = models.CharField(db_column='ENABLE_TRACKBACK', max_length=1)  # Field name made lowercase.
    enable_comments = models.CharField(db_column='ENABLE_COMMENTS', max_length=1)  # Field name made lowercase.
    attach_img = models.IntegerField(db_column='ATTACH_IMG', blank=True, null=True)  # Field name made lowercase.
    num_comments = models.IntegerField(db_column='NUM_COMMENTS')  # Field name made lowercase.
    num_trackbacks = models.IntegerField(db_column='NUM_TRACKBACKS')  # Field name made lowercase.
    views = models.IntegerField(db_column='VIEWS', blank=True, null=True)  # Field name made lowercase.
    favorite_sort = models.IntegerField(db_column='FAVORITE_SORT', blank=True, null=True)  # Field name made lowercase.
    path = models.CharField(db_column='PATH', max_length=255, blank=True, null=True)  # Field name made lowercase.
    code = models.CharField(db_column='CODE', max_length=255, blank=True, null=True)  # Field name made lowercase.
    micro = models.CharField(db_column='MICRO', max_length=1)  # Field name made lowercase.
    has_images = models.CharField(db_column='HAS_IMAGES', max_length=1, blank=True, null=True)  # Field name made lowercase.
    has_props = models.CharField(db_column='HAS_PROPS', max_length=1, blank=True, null=True)  # Field name made lowercase.
    has_tags = models.CharField(db_column='HAS_TAGS', max_length=1, blank=True, null=True)  # Field name made lowercase.
    has_comment_images = models.CharField(db_column='HAS_COMMENT_IMAGES', max_length=1, blank=True, null=True)  # Field name made lowercase.
    has_socnet_all = models.CharField(db_column='HAS_SOCNET_ALL', max_length=1, blank=True, null=True)  # Field name made lowercase.
    seo_title = models.CharField(db_column='SEO_TITLE', max_length=255, blank=True, null=True)  # Field name made lowercase.
    seo_tags = models.CharField(db_column='SEO_TAGS', max_length=255, blank=True, null=True)  # Field name made lowercase.
    seo_description = models.TextField(db_column='SEO_DESCRIPTION', blank=True, null=True)  # Field name made lowercase.
    num_comments_all = models.IntegerField(db_column='NUM_COMMENTS_ALL')  # Field name made lowercase.
    background_code = models.CharField(db_column='BACKGROUND_CODE', max_length=100, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'b_blog_post'
