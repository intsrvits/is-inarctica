# ================================================================================

DEBUG = True
SECRET_KEY = '$k-l2-qyy4)741%^j$=24!z-vhnvq5$5nSECRET_KEYi1'

# ================================================================================

CLOUD_WEBHOOK_SETTINGS = '...'
CLOUD_WEBHOOK_DOMAIN = '...'

BOX_WEBHOOK_SETTINGS = '...'
BOX_WEBHOOK_DOMAIN = '...'

# ================================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': '...',  # Or path to database file if using sqlite3.
        'USER': '...',  # Not used with sqlite3.
        'PASSWORD': '...',  # Not used with sqlite3.
        'HOST': '...',
        'PORT': '...',
    },
}

CSRF_TRUSTED_ORIGINS = [
    "https://xxx.devprox.it-solution.ru",
]

