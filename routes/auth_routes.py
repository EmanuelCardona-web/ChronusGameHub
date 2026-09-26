"""
auth_routes.py
--------------
Flujo de autenticación con Auth0 (Authorization Code Flow + OIDC, vía Authlib):
  - /auth/acceso           -> página de acceso con las opciones de login y registro
  - /auth/login            -> redirige al Universal Login de Auth0
  - /auth/registro         -> redirige al Universal Login en la pantalla de registro
  - /auth/callback         -> valida state/nonce/ID token, crea o vincula el
                              usuario local y abre la sesión
  - /auth/complete-profile -> formulario post-registro (tipo y número de
                              documento) que se persiste localmente y se
                              sincroniza contra el user_metadata en Auth0
                              mediante la Management API v2
  - /auth/logout (POST)    -> cierra sesión local y en Auth0
"""

import re
import time
from urllib.parse import quote, urlencode

import requests
from authlib.integrations.base_client.errors import OAuthError
from flask import (
    Blueprint, current_app, flash, g, redirect, render_template,
    request, session, url_for,
)
from sqlalchemy import func

from models import db, Usuario, TIPOS_DOCUMENTO
from security import login_required, oauth

auth_bp = Blueprint("auth", __name__)

NUMERO_DOCUMENTO_RE = re.compile(r"^\d{5,15}$")
_mgmt_token_cache = {"token": None, "expires_at": 0}


def _auth0_configured():
    return oauth.create_client("auth0") is not None


def _safe_next_url(url):
    """Solo permite rutas relativas internas para evitar redirecciones abiertas."""
    if url and url.startswith("/") and not url.startswith("//") and "\\" not in url:
        return url
    return None


def _redirect_to_auth0(**extra_params):
    if not _auth0_configured():
        flash("El inicio de sesión no está disponible: Auth0 no está configurado.", "error")
        return redirect(url_for("auth.login_page"))
    try:
        return oauth.auth0.authorize_redirect(
            redirect_uri=current_app.config["AUTH0_CALLBACK_URL"], **extra_params
        )
    except requests.RequestException as exc:
        current_app.logger.error("No se pudo contactar a Auth0 (%s): %s", current_app.config["AUTH0_DOMAIN"], exc)
        flash("No se pudo conectar con Auth0. Revisa AUTH0_DOMAIN en el archivo .env.", "error")
        return redirect(url_for("auth.login_page"))


@auth_bp.route("/acceso")
def login_page():
    if g.get("user"):
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@auth_bp.route("/login")
def login():
    return _redirect_to_auth0()


@auth_bp.route("/registro")
def register():
    return _redirect_to_auth0(screen_hint="signup")


@auth_bp.route("/callback")
def callback():
    if request.args.get("error"):
        current_app.logger.warning(
            "Auth0 devolvió un error: %s - %s",
            request.args.get("error"), request.args.get("error_description"),
        )
        flash("No fue posible completar el inicio de sesión. Intenta de nuevo.", "error")
        return redirect(url_for("auth.login_page"))

    try:
        token = oauth.auth0.authorize_access_token()
    except (OAuthError, requests.RequestException) as exc:
        current_app.logger.warning("Fallo en el callback de Auth0: %s", exc)
        flash("La sesión de autenticación expiró o no es válida. Intenta de nuevo.", "error")
        return redirect(url_for("auth.login_page"))

    profile = token.get("userinfo") or {}
    if not profile.get("sub"):
        flash("Auth0 no devolvió un perfil válido.", "error")
        return redirect(url_for("auth.login_page"))

    usuario = _sync_local_user(profile)
    if usuario is None:
        flash(
            "Ya existe una cuenta con ese correo. Verifica tu correo en Auth0 "
            "para vincularla o contacta a un administrador.",
            "error",
        )
        return redirect(url_for("auth.login_page"))

    next_url = _safe_next_url(session.get("next_url"))

    # Sesión nueva tras autenticarse (evita fijación de sesión). No se guardan tokens.
    session.clear()
    session.permanent = True
    session["user"] = {
        "id_usuario": usuario.id_usuario,
        "sub": profile["sub"],
        "name": profile.get("name") or usuario.username,
        "email": profile.get("email") or usuario.email,
        "email_verified": bool(profile.get("email_verified")),
        "picture": profile.get("picture"),
        "roles": list(profile.get(current_app.config["AUTH0_ROLES_CLAIM"], [])),
    }

    if not usuario.tipo_documento or not usuario.numero_documento:
        return redirect(url_for("auth.complete_profile"))

    flash(f"Bienvenido de nuevo, {usuario.username}.", "success")
    return redirect(next_url or url_for("dashboard"))


def _sync_local_user(profile):
    """Busca el usuario local por `sub`; si no existe, lo vincula por correo
    verificado o lo crea. Devuelve None si el correo pertenece a otra cuenta."""

    sub = profile["sub"]
    email = (profile.get("email") or "").strip().lower()

    usuario = Usuario.query.filter_by(auth0_sub=sub).first()
    if usuario is not None:
        return usuario

    existente = (
        Usuario.query.filter(func.lower(Usuario.email) == email).first() if email else None
    )
    if existente is not None:
        if profile.get("email_verified") and existente.auth0_sub is None:
            existente.auth0_sub = sub
            db.session.commit()
            return existente
        return None

    usuario = Usuario(
        username=_unique_username(profile.get("nickname") or profile.get("name") or "jugador"),
        email=email or f"{re.sub(r'[^a-zA-Z0-9]', '', sub)[:60]}@sin-email.chronos",
        auth0_sub=sub,
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario


def _unique_username(base):
    base = re.sub(r"\s+", "_", base.strip())[:70] or "jugador"
    candidate, n = base, 2
    while Usuario.query.filter_by(username=candidate).first() is not None:
        candidate = f"{base}_{n}"
        n += 1
    return candidate


@auth_bp.route("/complete-profile", methods=["GET", "POST"])
@login_required
def complete_profile():
    """Formulario post-registro: captura tipo_documento y numero_documento
    y los sincroniza con el user_metadata del usuario en Auth0."""

    usuario = db.get_or_404(Usuario, g.user["id_usuario"])

    if request.method == "POST":
        tipo_documento = request.form.get("tipo_documento")
        numero_documento = (request.form.get("numero_documento") or "").strip()
        if tipo_documento not in TIPOS_DOCUMENTO:
            flash("El tipo de documento debe ser C.C o T.I.", "error")
            return redirect(url_for("auth.complete_profile"))
        if not NUMERO_DOCUMENTO_RE.match(numero_documento):
            flash("El número de documento debe tener entre 5 y 15 dígitos.", "error")
            return redirect(url_for("auth.complete_profile"))

        usuario.tipo_documento = tipo_documento
        usuario.numero_documento = numero_documento
        db.session.commit()

        try:
            _sync_user_metadata_auth0(usuario.auth0_sub, tipo_documento, numero_documento)
        except (requests.RequestException, KeyError) as exc:
            current_app.logger.error("Falló la sincronización con Auth0: %s", exc)
            flash("Perfil guardado. La sincronización con Auth0 se reintentará más tarde.", "warning")
        else:
            flash("Perfil completado correctamente.", "success")

        return redirect(url_for("dashboard"))

    return render_template(
        "post_register.html",
        usuario=usuario,
        tipos_documento=TIPOS_DOCUMENTO,
    )


def _get_management_token():
    """Obtiene (y cachea hasta su expiración) un token para la Auth0
    Management API v2 usando el flujo Client Credentials de la app M2M."""

    if _mgmt_token_cache["token"] and time.time() < _mgmt_token_cache["expires_at"]:
        return _mgmt_token_cache["token"]

    domain = current_app.config["AUTH0_DOMAIN"]
    resp = requests.post(
        f"https://{domain}/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": current_app.config["AUTH0_MGMT_CLIENT_ID"],
            "client_secret": current_app.config["AUTH0_MGMT_CLIENT_SECRET"],
            "audience": current_app.config["AUTH0_AUDIENCE"] or f"https://{domain}/api/v2/",
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    _mgmt_token_cache["token"] = data["access_token"]
    _mgmt_token_cache["expires_at"] = time.time() + data.get("expires_in", 3600) - 60
    return data["access_token"]


def _sync_user_metadata_auth0(auth0_sub, tipo_documento, numero_documento):
    """Actualiza el user_metadata del usuario en Auth0 mediante
    PATCH /api/v2/users/{id} de la Management API."""

    if not auth0_sub or not current_app.config["AUTH0_MGMT_CLIENT_ID"]:
        raise requests.RequestException("Management API de Auth0 no configurada.")

    domain = current_app.config["AUTH0_DOMAIN"]
    resp = requests.patch(
        f"https://{domain}/api/v2/users/{quote(auth0_sub, safe='')}",
        headers={"Authorization": f"Bearer {_get_management_token()}"},
        json={
            "user_metadata": {
                "tipo_documento": tipo_documento,
                "numero_documento": numero_documento,
            }
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    domain = current_app.config["AUTH0_DOMAIN"]
    if not domain:
        return redirect(url_for("index"))
    params = {
        "client_id": current_app.config["AUTH0_CLIENT_ID"],
        "returnTo": url_for("index", _external=True),
    }
    return redirect(f"https://{domain}/v2/logout?{urlencode(params)}")
