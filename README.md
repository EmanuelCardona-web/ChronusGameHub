# Chronos Gaming Hub & Cloud Services — Backend

Proyecto universitario (Arquitectura de Software II). Backend en **Flask +
Flask-SQLAlchemy**, base de datos **PostgreSQL en Supabase** y autenticación
con **Auth0**.

## Puesta en marcha

### Requisitos

- Python 3.8 o superior.
- Una base de datos PostgreSQL accesible. El proyecto está configurado para Supabase.
- Credenciales de Auth0 para usar el inicio de sesión y completar perfiles.

### Windows (PowerShell)

Desde la carpeta raíz del proyecto, crea el entorno virtual e instala las dependencias:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz del proyecto y completa tus propios valores:

```dotenv
SECRET_KEY=cambia-este-valor
DATABASE_URL=postgresql+pg8000://USUARIO:CONTRASENA@HOST:5432/postgres
AUTH0_DOMAIN=tu-tenant.auth0.com
AUTH0_CLIENT_ID=tu-client-id
AUTH0_CLIENT_SECRET=tu-client-secret
AUTH0_CALLBACK_URL=http://localhost:5000/auth/callback
AUTH0_AUDIENCE=tu-audience
AUTH0_MGMT_CLIENT_ID=tu-management-client-id
AUTH0_MGMT_CLIENT_SECRET=tu-management-client-secret
```

No dejes los valores de ejemplo al ejecutar la aplicación. Si la contraseña de la base de datos contiene caracteres especiales, codifícala para usarla en la URL. El `.env` está excluido de Git; no guardes credenciales reales en el código fuente.

Inicia la aplicación:

```powershell
.\.venv\Scripts\python.exe app.py
```

Abre `http://localhost:5000`. Al iniciar, la aplicación crea las tablas que todavía no existan. La base de datos debe estar accesible; el login y la sincronización de perfiles requieren además las credenciales de Auth0.

### macOS / Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Antes de iniciar, crea y completa el mismo archivo `.env` descrito arriba.

## Estructura

- `app.py` — fábrica de la aplicación y registro de blueprints.
- `config.py` — configuración y variables de entorno.
- `models.py` — modelos SQLAlchemy (`usuarios`, `licencias_juego`,
  `guardados_nube`, `insignias_usuario`).
- `routes/auth_routes.py` — login/callback con Auth0 y sincronización de
  `user_metadata` vía Management API v2.
- `routes/user_routes.py` — CRUD de usuarios (API + HTML).
- `routes/license_routes.py` — CRUD de licencias (API + HTML).
- `templates/` — vistas Jinja2 del panel de bienvenida y administración.
- `static/` — CSS y JS del panel de control.

## Notas de arquitectura

- `guardados_nube.snapshot_data` (JSON/JSONB) da soporte al patrón
  **Memento**: cada fila es un snapshot restaurable del estado de una partida.
- `insignias_usuario` da soporte al patrón **Observer**: se crea una fila
  cuando un evento del juego notifica el cumplimiento de un logro.
- En producción, reemplazar `db.create_all()` por migraciones con
  `Flask-Migrate` (ya incluido en `requirements.txt`).
