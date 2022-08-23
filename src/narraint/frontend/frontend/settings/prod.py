from .base import *

# Build paths inside the project like this: os.path.join(DJANGO_PROJ_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '4o5h94sf8#+e_$a7*szdfcyf!uhf2er)0kg#qp3r*nac$%pp6q'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "134.169.32.177",
    "www.narrative.pubpharm.de",
    "narrative.pubpharm.de"
]

STATIC_ROOT = "/var/www/static"
