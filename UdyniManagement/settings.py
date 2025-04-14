"""
Django settings for UdyniManagement project.

Generated by 'django-admin startproject' using Django 3.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from pathlib import Path
import os
import logging
import ldap
from django_auth_ldap.config import LDAPSearch, PosixGroupType


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '********** TO BE REPLACED **********'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'AccountManagement.apps.AccountmanagementConfig',
    'FinancialReporting.apps.FinancialreportingConfig',  ## Old financial reporting app
    'Reporting.apps.ReportingConfig',
    'Projects.apps.ProjectsConfig',
    'Accounting.apps.AccountingConfig',
    'Tags.apps.TagsConfig',
    'LabLogbook.apps.LablogbookConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'mptt',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# LDAP authentication
AUTH_LDAP_SERVER_URI = "ldaps://storage.udyni.lab"
AUTH_LDAP_USER_DN_TEMPLATE = "uid=%(user)s,ou=People,dc=udyni,dc=lab"
AUTH_LDAP_CACHE_TIMEOUT = 60

# Account to search into ldap server
AUTH_LDAP_BIND_DN = "cn=authbot,dc=udyni,dc=lab"
AUTH_LDAP_BIND_PASSWORD = "********"

# Search for users
AUTH_LDAP_USER_SEARCH = LDAPSearch(
    "ou=People,dc=udyni,dc=lab", ldap.SCOPE_SUBTREE, "(uid=%(user)s)"
)

# Search for groups
AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
    "ou=Groups,dc=udyni,dc=lab", ldap.SCOPE_SUBTREE, "(objectClass=posixGroup)"
)

# Group type
AUTH_LDAP_GROUP_TYPE = PosixGroupType()

# LDAP connection options for TLS
AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_X_TLS_CACERTFILE: r"/etc/ssl/certs/udyniCA.pem",
    ldap.OPT_X_TLS_REQUIRE_CERT: ldap.OPT_X_TLS_ALLOW,
    ldap.OPT_X_TLS_NEWCTX: 0,
}

# User attribute map
AUTH_LDAP_USER_ATTR_MAP = {
    "first_name": "givenName",
    "last_name": "sn",
    "email": "mail",
}

# Associations between ldap and django groups
AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    "is_active": "cn=Domain Users,ou=Groups,dc=udyni,dc=lab",
    "is_staff": "cn=Administrators,ou=Groups,dc=udyni,dc=lab",
    "is_superuser": "cn=Administrators,ou=Groups,dc=udyni,dc=lab"
}

#AUTH_LDAP_PROFILE_FLAGS_BY_GROUPS = {
#    "is_awesome": ["cn=awesome,ou=groups,dc=whiteqube"]
#}

AUTHENTICATION_BACKENDS = [
    "django_auth_ldap.backend.LDAPBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Enable debug for ldap server connection
# logger = logging.getLogger('django_auth_ldap')
# logger.addHandler(logging.StreamHandler())
# logger.setLevel(logging.DEBUG)


ROOT_URLCONF = 'UdyniManagement.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'UdyniManagement.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'management',
        'USER' : 'management',
        'PASSWORD' : '********',
        'HOST' : 'storage.udyni.lab',
        'PORT' : '5432',
        'OPTIONS': {'sslmode': 'require'},
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 10,
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'CET'

USE_I18N = False

USE_L10N = False

USE_TZ = True

DATE_INPUT_FORMATS = ['%d/%m/%Y', '%Y-%m-%d']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'http_static')
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'root'),
)

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy forms template pack
CRISPY_TEMPLATE_PACK = 'bootstrap4'
CRISPY_FAIL_SILENTLY = not DEBUG

# SIGLA
SIGLA_USERNAME = "app.ifn"
SIGLA_PASSWORD = "********"

# Default email configuration
DEFAULT_FROM_EMAIL = 'UDynI Management <no-reply@udyni.lab>'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
SERVER_EMAIL = 'UDynI Management <no-reply@udyni.lab>'

# Email configuration (smtp.udyni.lab)
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.udyni.lab'
EMAIL_PORT = 25

# Email configuration (smtp-relay.sendinblue.com)
# EMAIL_USE_TLS = True
# EMAIL_HOST = 'smtp-relay.sendinblue.com'
# EMAIL_PORT = 587
# EMAIL_HOST_USER = 'udynilabs@gmail.com'
# EMAIL_HOST_PASSWORD = '********'
