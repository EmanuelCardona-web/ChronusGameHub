"""
auth_routes.py
--------------
Flujo de autenticación con Auth0 (Authorization Code Flow):
  - /auth/login      -> redirige al Universal Login de Auth0
  - /auth/callback    -> intercambia el "code" por tokens y crea/actualiza
                          el usuario local
  - /auth/complete-profile -> formulario post-registro (tipo y número de
                          documento) que se persiste localmente y se
                          sincroniza contra el user_metadata en Auth0
                          mediante la Management API v2
  - /auth/logout      -> cierra sesión local y en Auth0
"""

from urllib.parse import urlencode

import requests
from flask import (
    Blueprint, current_app, redirect, render_template,
    request, session, url_for, flash,
)

from models import db, Usuario, TIPOS_DOCUMENTO

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login")
def login():
    params = {
        "response_type": "code",
        "client_id": current_app.config["AUTH0_CLIENT_ID"],
        "redirect_uri": current_app.config["AUTH0_CALLBACK_URL"],
        "scope": "openid profile email",
    }
    domain = current_app.config["AUTH0_DOMAIN"]
    return redirect(f"https://{domain}/authorize?{urlencode(params)}")


@auth_bp.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        flash("Autenticación cancelada o inválida.", "error")
        return redirect(url_for("index"))

    domain = current_app.config["AUTH0_DOMAIN"]

    # 1. Intercambiar "code" por tokens
    token_resp = requests.post(
        f"https://{domain}/oauth/token",
        json={
            "grant_type": "authorization_code",
            "client_id": current_app.config["AUTH0_CLIENT_ID"],
            "client_secret": current_app.config["AUTH0_CLIENT_SECRET"],
            "code": code,
            "redirect_uri": current_app.config["AUTH0_CALLBACK_URL"],
        },
        timeout=10,
    )
    token_resp.raise_for_status()
    tokens = token_resp.json()

    # 2. Obtener perfil del usuario
    userinfo_resp = requests.get(
        f"https://{domain}/userinfo",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        timeout=10,
    )
    userinfo_resp.raise_for_status()
    profile = userinfo_resp.json()

    session["access_token"] = tokens.get("access_token")
    session["profile"] = profile

    # 3. Crear o recuperar el usuario local
    usuario = Usuario.query.filter_by(auth0_sub=profile["sub"]).first()
    if usuario is None:
        usuario = Usuario(
            username=profile.get("nickname") or profile.get("name") or profile["sub"],
            email=profile.get("email", f"{profile['sub']}@sin-email.chronos"),
            auth0_sub=profile["sub"],
        )
        db.session.add(usuario)
        db.session.commit()

    session["id_usuario"] = usuario.id_usuario

    if not usuario.tipo_documento or not usuario.numero_documento:
        return redirect(url_for("auth.complete_profile"))

    return redirect(url_for("index"))


@auth_bp.route("/complete-profile", methods=["GET", "POST"])
def complete_profile():
    """Formulario post-registro: captura tipo_documento y numero_documento
    y los sincroniza con el user_metadata del usuario en Auth0."""

    id_usuario = session.get("id_usuario")
    if not id_usuario:
        return redirect(url_for("auth.login"))

    usuario = Usuario.query.get_or_404(id_usuario)

    if request.method == "POST":
        tipo_documento = request.form.get("tipo_documento")
        numero_documento = request.form.get("numero_documento")
        if tipo_documento not in TIPOS_DOCUMENTO:
            flash("El tipo de documento debe ser C.C o T.I.", "error")
            return redirect(url_for("auth.complete_profile"))

        usuario.tipo_documento = tipo_documento
        usuario.numero_documento = numero_documento
        db.session.commit()

        try:
            _sync_user_metadata_auth0(
                usuario.auth0_sub, tipo_documento, numero_documento
            )
        except requests.RequestException as exc:
            flash(f"Perfil guardado localmente, pero falló la sincronización con Auth0: {exc}", "warning")
        else:
            flash("Perfil completado y sincronizado con Auth0 correctamente.", "success")

        return redirect(url_for("index"))

    return render_template(
        "post_register.html",
        usuario=usuario,
        tipos_documento=TIPOS_DOCUMENTO,
    )


def _get_management_token():
    """Obtiene un token de acceso para la Auth0 Management API v2
    usando el flujo Client Credentials de la app M2M autorizada."""

    domain = current_app.config["AUTH0_DOMAIN"]
    resp = requests.post(
        f"https://{domain}/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": current_app.config["AUTH0_MGMT_CLIENT_ID"],
            "client_secret": current_app.config["AUTH0_MGMT_CLIENT_SECRET"],
            "audience": current_app.config["AUTH0_AUDIENCE"],
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _sync_user_metadata_auth0(auth0_sub, tipo_documento, numero_documento):
    """Actualiza el user_metadata del usuario en Auth0 mediante
    PATCH /api/v2/users/{id} de la Management API."""

    domain = current_app.config["AUTH0_DOMAIN"]
    mgmt_token = _get_management_token()

    resp = requests.patch(
        f"https://{domain}/api/v2/users/{auth0_sub}",
        headers={
            "Authorization": f"Bearer {mgmt_token}",
            "Content-Type": "application/json",
        },
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


@auth_bp.route("/logout")
def logout():
    session.clear()
    domain = current_app.config["AUTH0_DOMAIN"]
    params = {
        "client_id": current_app.config["AUTH0_CLIENT_ID"],
        "returnTo": url_for("index", _external=True),
    }
    return redirect(f"https://{domain}/v2/logout?{urlencode(params)}")
