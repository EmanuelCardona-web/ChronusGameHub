"""
config.py
---------
Configuración central de la aplicación: variables de entorno,
cadena de conexión a Supabase (PostgreSQL) y credenciales de Auth0.
"""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def _required(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} debe estar definido en el archivo .env")
    return value


def _bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _list(name):
    return [item.strip().lower() for item in os.getenv(name, "").split(",") if item.strip()]


class Config:
    # --- Flask ---
    SECRET_KEY = _required("SECRET_KEY")
    DEBUG = _bool("FLASK_DEBUG")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Sesión y cookies ---
    # SESSION_COOKIE_SECURE debe ser true en producción (HTTPS).
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE")
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # --- CSRF (Flask-WTF) ---
    WTF_CSRF_TIME_LIMIT = None  # el token vive lo que vive la sesión

    # --- Base de datos (Supabase / PostgreSQL) ---
    SQLALCHEMY_DATABASE_URI = _required("DATABASE_URL")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- Auth0 (aplicación "Regular Web Application") ---
    AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
    AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
    AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
    AUTH0_CALLBACK_URL = os.getenv("AUTH0_CALLBACK_URL", "http://localhost:5000/auth/callback")

    # --- Auth0 Management API (app M2M) ---
    # AUTH0_AUDIENCE es el identificador de la Management API: https://<dominio>/api/v2/
    AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
    AUTH0_MGMT_CLIENT_ID = os.getenv("AUTH0_MGMT_CLIENT_ID")
    AUTH0_MGMT_CLIENT_SECRET = os.getenv("AUTH0_MGMT_CLIENT_SECRET")

    # --- Autorización ---
    # Claim personalizado que una Auth0 Action agrega al ID token con los roles del usuario.
    AUTH0_ROLES_CLAIM = os.getenv("AUTH0_ROLES_CLAIM", "https://chronosgaminghub/roles")
    ADMIN_ROLE = os.getenv("ADMIN_ROLE", "admin")
    # Correos (verificados en Auth0) con acceso de administrador aunque no tengan el rol.
    ADMIN_EMAILS = _list("ADMIN_EMAILS")
