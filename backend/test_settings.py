import logging

from backend.settings import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3')
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

if '--no-logs' in sys.argv:
    sys.argv.remove('--no-logs')
    logging.disable(logging.CRITICAL)
