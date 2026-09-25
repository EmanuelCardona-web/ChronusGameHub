"""
config.py
---------
Configuración central de la aplicación: variables de entorno,
cadena de conexión a Supabase (PostgreSQL) y credenciales de Auth0.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # --- Flask ---
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Base de datos (Supabase / PostgreSQL) ---
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError("DATABASE_URL debe estar definido en el archivo .env")

    # --- Auth0 ---
    AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
    AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
    AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
    AUTH0_CALLBACK_URL = os.getenv("AUTH0_CALLBACK_URL", "http://localhost:5000/auth/callback")
    AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")

    # --- Auth0 Management API (app M2M) ---
    AUTH0_MGMT_CLIENT_ID = os.getenv("AUTH0_MGMT_CLIENT_ID")
    AUTH0_MGMT_CLIENT_SECRET = os.getenv("AUTH0_MGMT_CLIENT_SECRET")
