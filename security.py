"""
security.py
-----------
Piezas transversales de seguridad:
  - Cliente OAuth/OIDC de Auth0 (Authlib): valida state, nonce y firma del ID token.
  - Protección CSRF (Flask-WTF) para formularios y peticiones fetch.
  - Decoradores login_required / admin_required.
  - Cabeceras HTTP de seguridad (CSP, anti-clickjacking, etc.).
"""

from functools import wraps

from authlib.integrations.flask_client import OAuth
from flask import current_app, flash, g, jsonify, redirect, request, session, url_for
from flask_wtf.csrf import CSRFProtect

oauth = OAuth()
csrf = CSRFProtect()

def _content_security_policy(auth0_domain):
    # form-action incluye Auth0 porque el logout (POST) termina redirigiendo a su dominio.
    form_action = "'self'" + (f" https://{auth0_domain}" if auth0_domain else "")
    return "; ".join([
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data: https:",  # avatares de Auth0 / Gravatar / Google
        "font-src 'self'",
        "connect-src 'self'",
        f"form-action {form_action}",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "object-src 'none'",
    ])


def init_security(app):
    csrf.init_app(app)
    oauth.init_app(app)

    domain = app.config.get("AUTH0_DOMAIN")
    csp = _content_security_policy(domain)
    if domain:
        oauth.register(
            "auth0",
            client_id=app.config["AUTH0_CLIENT_ID"],
            client_secret=app.config["AUTH0_CLIENT_SECRET"],
            server_metadata_url=f"https://{domain}/.well-known/openid-configuration",
            client_kwargs={
                "scope": "openid profile email",
                "token_endpoint_auth_method": "client_secret_post",
            },
        )
    else:
        app.logger.warning("AUTH0_DOMAIN no está configurado: el inicio de sesión no funcionará.")

    @app.before_request
    def load_current_user():
        g.user = session.get("user")

    @app.context_processor
    def inject_user():
        return {"current_user": g.get("user"), "is_admin": is_admin()}

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        if g.get("user"):
            # Las páginas con datos personales no deben quedar en caché del navegador.
            response.headers.setdefault("Cache-Control", "no-store")
        return response


def is_admin():
    user = g.get("user")
    if not user:
        return False
    if current_app.config["ADMIN_ROLE"] in user.get("roles", []):
        return True
    return bool(
        user.get("email_verified")
        and user.get("email", "").lower() in current_app.config["ADMIN_EMAILS"]
    )


def _wants_json():
    return request.path.startswith("/api/")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.get("user"):
            if _wants_json():
                return jsonify({"error": "Autenticación requerida."}), 401
            session["next_url"] = request.full_path if request.method == "GET" else None
            flash("Inicia sesión para continuar.", "warning")
            return redirect(url_for("auth.login_page"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not is_admin():
            if _wants_json():
                return jsonify({"error": "No tienes permisos para esta acción."}), 403
            flash("Esta sección es solo para administradores.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)

    return wrapped
