# Development settings
# NOTE: when running Django rename to development.py and set the environment variable DJANGO_SETTINGS_MODULE=UdyniManagement.settings.development

from UdyniManagement.settings import *  # Import base settings from settings/__init__.py
from UdyniManagement.settings.development_logging import LOGGING  # Import logging configuration for production

# Secret key
SECRET_KEY = 'django-insecure-#m^ta)8wnr+v=@o*t5#n&coip**2brq!!j@b8i8-=_+j$3zo9='

# Enable debug
DEBUG = True

# LDAP password
AUTH_LDAP_BIND_PASSWORD = "*************"

# Database password
DATABASES['default']['HOST'] = 'localhost'
DATABASES['default']['PASSWORD'] = '<set to database password>'

# SIGLA password
SIGLA_PASSWORD = "<set to sigla password>"

# Email directly through SendInBlue
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp-relay.sendinblue.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = '<sendinblue account email>'
EMAIL_HOST_PASSWORD = '<sendinblue account password>'
