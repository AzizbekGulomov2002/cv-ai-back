"""
Django settings for AI CV System project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Loyiha ildizi (config/ dan bir pog‘ona yuqori) — har doim shu yerdagi .env o‘qiladi.
# Sukutdagi load_dotenv() faqat joriy CWD dan qidiradi; PythonAnywhere / WSGI da CWD
# boshqa bo‘lishi mumkin, shuning uchun kalitlar topilmas edi.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['*']


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    
    # Local apps
    'apps.users',
    'apps.candidates',
    'apps.jobs',
    'apps.ranking',
    'apps.ai',
    'apps.audit',
    'apps.stats',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
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
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# API auth: default TRUE — login required.
# register/login endpoints are always AllowAny.
_API_REQUIRE_AUTH = os.getenv('API_REQUIRE_AUTH', 'true').lower() in ('1', 'true', 'yes')

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
        if _API_REQUIRE_AUTH
        else 'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    # Explicit parsers: JSON + multipart (form-data for file/image uploads)
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# CORS settings for frontend integration (django-cors-headers)
# Vite default dev server: http://localhost:5173 — must be listed or browser blocks the request.
_default_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://cvaianalyse.netlify.app",
    "https://cvaianalyser.netlify.app"
]
# PythonAnywhere / production: set e.g. CORS_ALLOWED_ORIGINS=https://myapp.vercel.app,https://username.pythonanywhere.com
_extra_cors = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
if _extra_cors:
    CORS_ALLOWED_ORIGINS = list(
        dict.fromkeys(
            _default_cors_origins
            + [o.strip() for o in _extra_cors.split(",") if o.strip()]
        )
    )
else:
    CORS_ALLOWED_ORIGINS = _default_cors_origins

CORS_ALLOW_CREDENTIALS = True

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# CV fayl (PDF/DOCX) — Responses API + input_file; tavsiya: gpt-4o
OPENAI_CV_MODEL = os.getenv('OPENAI_CV_MODEL', 'gpt-4o')

# Google Gemini (AI Studio) — quota tugaganda yoki faqat Gemini: CV fayl pipeline
# https://aistudio.google.com/apikey
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')  # ba'zan bir xil kalit nomi
# 1.5 qisqa nomlari (gemini-1.5-flash) ko‘pincha 404 — rasmiy: gemini-2.5-flash yoki gemini-flash-latest
GEMINI_CV_MODEL = os.getenv('GEMINI_CV_MODEL', 'gemini-2.5-flash')
# auto | openai | gemini — auto: avval OpenAI, 429/quota bo'lsa Gemini
CV_EXTRACT_PROVIDER = os.getenv('CV_EXTRACT_PROVIDER', 'auto')

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE

# Email (SMTP) Configuration
# .env: EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_USE_SSL, EMAIL_HOST_USER,
#       EMAIL_HOST_PASSWORD, optional DEFAULT_FROM_EMAIL, optional EMAIL_BACKEND.
# Agar EMAIL_BACKEND berilmasa va user+parol to‘ldirilgan bo‘lsa — real yuborish uchun SMTP ishlatiladi.
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() in ('1', 'true', 'yes')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'false').lower() in ('1', 'true', 'yes')
EMAIL_HOST_USER = (os.getenv('EMAIL_HOST_USER') or '').strip()
_raw_email_password = os.getenv('EMAIL_HOST_PASSWORD') or ''
# Gmail app password ko‘pincha 4x4 bo‘shliq bilan nusxalanadi; SMTP uchun bo‘shliqsiz 16 belgi kerak.
EMAIL_HOST_PASSWORD = ''.join(_raw_email_password.split())

_default_from = (os.getenv('DEFAULT_FROM_EMAIL') or '').strip()
if _default_from:
    DEFAULT_FROM_EMAIL = _default_from
elif EMAIL_HOST_USER:
    DEFAULT_FROM_EMAIL = f'AI CV System <{EMAIL_HOST_USER}>'
else:
    DEFAULT_FROM_EMAIL = 'noreply@cv-ai.local'

_email_backend = (os.getenv('EMAIL_BACKEND') or '').strip()
if _email_backend:
    EMAIL_BACKEND = _email_backend
elif EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Optional: absolute URL of the frontend (included in emails)
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'ai_cv_system.log',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'ai_cv_system': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}