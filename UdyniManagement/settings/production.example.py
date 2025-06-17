# Production settings
# NOTE: when running Django rename to production.py and set the environment variable DJANGO_SETTINGS_MODULE=UdyniManagement.settings.production

from UdyniManagement.settings import *  # Import base settings from settings/__init__.py
from UdyniManagement.settings.production_logging import LOGGING  # Import logging configuration for production

# Secret key
SECRET_KEY = '*****************'  # Set this to a secure random value

# Disable debug
DEBUG = False

# LDAP password
AUTH_LDAP_BIND_PASSWORD = "*****************"

# Database password
DATABASES['default']['HOST'] = '<set to database host>'
DATABASES['default']['PASSWORD'] = '<set to database password>'

# SIGLA password
SIGLA_PASSWORD = "<set to sigla password>"

# Static root
STATIC_ROOT = '/home/www/static'

# Administrators (list of tuples: (name, email))
ADMINS = []

# Crispy forms
CRISPY_FAIL_SILENTLY = True
