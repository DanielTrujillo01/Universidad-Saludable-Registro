from pathlib import Path
import os
from datetime import timedelta
import dj_database_url 

# Carga variables locales si existe .env (para desarrollo)
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# 1. SEGURIDAD
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-cambia-esto-en-produccion')

DEBUG = 'RENDER' not in os.environ

# 2. HOSTS PERMITIDOS
# Permitimos todo ('*') temporalmente para que Render asigne su URL,
# o leemos una lista desde variables de entorno.
ALLOWED_HOSTS = ['*'] 

# 3. CORS ROBUSTO (Conexión con Vercel)
# Si la variable existe, la convertimos en lista. Si no, lista vacía para no romper el código.
# --- BUSCA ESTA PARTE Y REEMPLÁZALA ---

# Leemos la variable de entorno
CORS_ALLOWED_ORIGINS_ENV = os.environ.get("CORS_ALLOWED_ORIGINS", "")

# Lógica inteligente:
if CORS_ALLOWED_ORIGINS_ENV == '*':
    # Si la variable es exactamente un asterisco, activamos el modo "permitir todo"
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOWED_ORIGINS = [] # Vaciamos la lista para evitar conflictos
else:
    # Si no es un asterisco, asumimos que es una lista de URLs
    CORS_ALLOW_ALL_ORIGINS = False
    if CORS_ALLOWED_ORIGINS_ENV:
        CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS_ENV.split(",")
    else:
        # Fallback para desarrollo local si no hay variable
        CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]

# --------------------------------------

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders', 
    'rest_framework',
    'rest_framework_simplejwt',
    'core',
    'django_filters',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'backend.wsgi.application'

# 4. BASE DE DATOS (Supabase)
# Usamos dj_database_url para parsear la URL completa que da Supabase
# settings.py
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',  # fallback
        conn_max_age=0,                  # 🔹 IMPORTANTE para desarrollo
        ssl_require=False                # 🔹 Supabase maneja SSL por URL
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# 5. ARCHIVOS ESTÁTICOS (WhiteNoise)
# Esto es obligatorio para que Render sirva CSS
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') 
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# JWT (Tiempos muy cortos, asegúrate que esto es lo que quieres)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5), 
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=10), 
    'ROTATE_REFRESH_TOKENS': True, 
    'BLACKLIST_AFTER_ROTATION': True,
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny', 
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
}