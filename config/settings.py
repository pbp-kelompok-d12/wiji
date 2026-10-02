"""Pengaturan Django buat Wiji. Yang rahasia dibaca dari .env (lihat .env.example)."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_list(name, default=''):
    return [item.strip() for item in os.environ.get(name, default).split(',') if item.strip()]


# Key default ini cuma buat lokal. Pas deploy, isi DJANGO_SECRET_KEY.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-only-insecure-key-change-me')

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# Default-nya sudah termasuk domain PWS biar website langsung bisa dibuka. Bisa ditimpa lewat env var.
PWS_HOST = 'muhammad-osman-wiji.pws.cs.ui.ac.id'
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', f'localhost,127.0.0.1,{PWS_HOST}')
# Perlu buat form (login, daftar) lewat HTTPS, kalau nggak kena error CSRF
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS', f'https://{PWS_HOST}')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise nyajiin file static (CSS, JS, gambar) di server tanpa Nginx. Harus tepat setelah SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # templates/ isinya base, navbar, footer. Template tiap app ada di <app>/templates/<app>/
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# User punya kolom role. Jangan diganti lagi setelah migrasi pertama.
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'accounts:login'
# Dashboard belum ada, jadi habis login atau logout baliknya ke landing page.
LOGIN_REDIRECT_URL = 'core:landing'
LOGOUT_REDIRECT_URL = 'core:landing'


LANGUAGE_CODE = 'id'

# Biar aturan tanggal ngikut waktu lokal.
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True


STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Biar WhiteNoise bisa nyajiin file dari folder static/ langsung, jadi nggak wajib jalanin collectstatic dulu
WHITENOISE_USE_FINDERS = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
