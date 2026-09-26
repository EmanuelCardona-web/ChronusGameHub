# Chronos Gaming Hub & Cloud Services — Backend

Proyecto universitario (Arquitectura de Software II). Backend en **Flask +
Flask-SQLAlchemy**, base de datos **PostgreSQL en Supabase** y autenticación
con **Auth0** (login, registro y roles).

## Puesta en marcha

### Requisitos

- Python 3.8 o superior.
- Una base de datos PostgreSQL accesible. El proyecto está configurado para Supabase.
- Un tenant de Auth0 configurado según la sección [Configuración de Auth0](#configuración-de-auth0).

### Windows (PowerShell)

Desde la carpeta raíz del proyecto, crea el entorno virtual e instala las dependencias:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Copia `.env.example` como `.env` y completa tus valores. El `.env` está
excluido de Git; no guardes credenciales reales en el código fuente.

```powershell
Copy-Item .env.example .env
```

Inicia la aplicación:

```powershell
.\.venv\Scripts\python.exe app.py
```

Abre `http://localhost:5000`. Al iniciar, la aplicación crea las tablas que todavía no existan.

### macOS / Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env   # y complétalo
python app.py
```

## Configuración de Auth0

1. **Tenant**: crea una cuenta en <https://auth0.com> y un tenant (región US o EU). Su dominio (`xxx.us.auth0.com`) va en `AUTH0_DOMAIN` y en `AUTH0_AUDIENCE` (`https://xxx.us.auth0.com/api/v2/`).
2. **Aplicación de login** — *Applications → Create Application → Regular Web Applications*:
   - Copia *Client ID* y *Client Secret* a `AUTH0_CLIENT_ID` / `AUTH0_CLIENT_SECRET`.
   - *Allowed Callback URLs*: `http://localhost:5000/auth/callback`
   - *Allowed Logout URLs*: `http://localhost:5000/`
   - *Allowed Web Origins*: `http://localhost:5000`
   - *Advanced → Grant Types*: solo **Authorization Code** y **Refresh Token**.
   - *Credentials → Authentication Method*: **Client Secret (Post)**.
3. **Registro de usuarios** — *Authentication → Database → Username-Password-Authentication*: activa la conexión para la aplicación y deja **Disable Sign Ups** apagado. Opcional: *Social* → Google.
4. **Política de contraseñas** — en la misma conexión, *Password Policy*: **Good** o superior, con *Password History* y *Password Dictionary* activados.
5. **Protección de ataques** — *Security → Attack Protection*: activa *Brute-force Protection*, *Suspicious IP Throttling* y *Breached Password Detection*.
6. **Verificación de correo** — *Branding → Email Templates → Verification Email* activado (en producción configura un proveedor SMTP propio en *Branding → Email Provider*).
7. **MFA (recomendado para administradores)** — *Security → Multi-factor Auth*: activa *One-time Password*.
8. **Management API (sincronizar documento)** — *Applications → Create Application → Machine to Machine* → autoriza **Auth0 Management API** con los scopes `read:users` y `update:users`. Copia sus credenciales a `AUTH0_MGMT_CLIENT_ID` / `AUTH0_MGMT_CLIENT_SECRET`.
9. **Roles** — *User Management → Roles → Create Role*: `admin`. Asígnalo a los usuarios administradores.
10. **Action para enviar los roles al token** — *Actions → Library → Create Action → Build from scratch* (trigger *Login / Post Login*):

    ```js
    exports.onExecutePostLogin = async (event, api) => {
      const namespace = "https://chronosgaminghub";
      const roles = event.authorization ? event.authorization.roles : [];
      api.idToken.setCustomClaim(`${namespace}/roles`, roles);
    };
    ```

    Pulsa *Deploy* y luego en *Actions → Triggers → post-login* arrástrala al flujo y guarda.
11. **Branding del Universal Login** — *Branding → Universal Login*: logo, color primario `#5b4cf0` y fondo `#11131f` para que coincida con la aplicación.

Mientras configuras los roles, puedes dar acceso de administrador a tu correo
verificado con `ADMIN_EMAILS=tu-correo@dominio.com`.

## Estructura

- `app.py` — fábrica de la aplicación, landing, panel (`/dashboard`) y manejo de errores.
- `config.py` — configuración y variables de entorno (falla al iniciar si faltan `SECRET_KEY` o `DATABASE_URL`).
- `security.py` — cliente OIDC de Auth0, CSRF, decoradores `login_required` / `admin_required` y cabeceras de seguridad.
- `models.py` — modelos SQLAlchemy (`usuarios`, `licencias_juego`, `guardados_nube`, `insignias_usuario`).
- `routes/auth_routes.py` — acceso, login, registro, callback, completar perfil y logout; sincroniza `user_metadata` vía Management API v2.
- `routes/user_routes.py` — CRUD de usuarios (API + HTML), solo administradores.
- `routes/license_routes.py` — CRUD de licencias (API + HTML), solo administradores.
- `templates/` — vistas Jinja2 (landing, acceso, panel, administración).
- `static/` — sistema de diseño (CSS con tema claro/oscuro) y JS de la interfaz.

## Seguridad

- Login y registro delegados en Auth0 (Authorization Code Flow + OIDC): la app nunca ve contraseñas; Authlib valida `state`, `nonce` y la firma del ID token.
- La sesión solo guarda datos básicos del perfil (no tokens), se regenera al iniciar sesión y expira a las 8 horas. Cookies `HttpOnly` y `SameSite=Lax`; `Secure` con `SESSION_COOKIE_SECURE=true`.
- CSRF en todos los formularios y en las peticiones `fetch` (cabecera `X-CSRFToken`). El logout es `POST`.
- Content-Security-Policy estricta (sin scripts ni estilos inline), `X-Frame-Options: DENY`, `nosniff`, HSTS en HTTPS y `Cache-Control: no-store` en páginas autenticadas.
- Administración y API REST restringidas al rol `admin`.

## Notas de arquitectura

- `guardados_nube.snapshot_data` (JSON/JSONB) da soporte al patrón
  **Memento**: cada fila es un snapshot restaurable del estado de una partida.
- `insignias_usuario` da soporte al patrón **Observer**: se crea una fila
  cuando un evento del juego notifica el cumplimiento de un logro.
- En producción, reemplazar `db.create_all()` por migraciones con
  `Flask-Migrate` (ya incluido en `requirements.txt`) y servir con un
  servidor WSGI (p. ej. `waitress` en Windows o `gunicorn` en Linux) detrás de HTTPS.
