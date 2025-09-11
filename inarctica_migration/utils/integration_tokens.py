from integration_utils.bitrix24.bitrix_token import BitrixToken
from django.conf import settings


class CloudBitrixToken(BitrixToken):
    def __init__(self):
        super().__init__(
            web_hook_auth=settings.CLOUD_WEBHOOK_SETTINGS,
            domain=settings.CLOUD_WEBHOOK_DOMAIN
        )


class BoxBitrixToken(BitrixToken):
    def __init__(self):
        super().__init__(
            web_hook_auth=settings.BOX_WEBHOOK_SETTINGS,
            domain=settings.BOX_WEBHOOK_DOMAIN
        )
