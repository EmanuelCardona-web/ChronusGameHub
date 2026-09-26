"""
user_routes.py
--------------
CRUD completo de `usuarios`, expuesto como:
  - API JSON REST bajo /api/usuarios
  - Vistas HTML (formularios) bajo /usuarios
Todas las rutas requieren una sesión con rol de administrador.
"""

from flask import Blueprint, jsonify, request, redirect, url_for, flash, render_template
from sqlalchemy.exc import IntegrityError

from models import db, Usuario, TIPOS_DOCUMENTO
from security import admin_required

user_bp = Blueprint("users", __name__)

DUPLICADO_MSG = "Ya existe un usuario con ese username o email."


def _commit_or_rollback():
    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        return False


# ---------------------------------------------------------------------
# API JSON REST
# ---------------------------------------------------------------------
@user_bp.route("/api/usuarios", methods=["GET"])
@admin_required
def api_list_usuarios():
    usuarios = Usuario.query.order_by(Usuario.id_usuario).all()
    return jsonify([u.to_dict() for u in usuarios])


@user_bp.route("/api/usuarios/<int:id_usuario>", methods=["GET"])
@admin_required
def api_get_usuario(id_usuario):
    usuario = db.get_or_404(Usuario, id_usuario)
    return jsonify(usuario.to_dict())


@user_bp.route("/api/usuarios", methods=["POST"])
@admin_required
def api_create_usuario():
    data = request.get_json(silent=True) or {}
    if not data.get("username") or not data.get("email"):
        return jsonify({"error": "username y email son obligatorios."}), 400
    tipo_documento = data.get("tipo_documento") or None
    if tipo_documento not in (None, *TIPOS_DOCUMENTO):
        return jsonify({"error": "tipo_documento debe ser C.C o T.I."}), 400

    usuario = Usuario(
        username=data["username"],
        email=data["email"],
        puntos_totales=data.get("puntos_totales", 0),
        tipo_documento=tipo_documento,
        numero_documento=data.get("numero_documento"),
    )
    db.session.add(usuario)
    if not _commit_or_rollback():
        return jsonify({"error": DUPLICADO_MSG}), 409
    return jsonify(usuario.to_dict()), 201


@user_bp.route("/api/usuarios/<int:id_usuario>", methods=["PUT", "PATCH"])
@admin_required
def api_update_usuario(id_usuario):
    usuario = db.get_or_404(Usuario, id_usuario)
    data = request.get_json(silent=True) or {}
    if "tipo_documento" in data and data["tipo_documento"] not in (None, "", *TIPOS_DOCUMENTO):
        return jsonify({"error": "tipo_documento debe ser C.C o T.I."}), 400

    for field in ("username", "email", "puntos_totales", "tipo_documento", "numero_documento"):
        if field in data:
            value = data[field]
            if field == "tipo_documento":
                value = value or None
            setattr(usuario, field, value)

    if not _commit_or_rollback():
        return jsonify({"error": DUPLICADO_MSG}), 409
    return jsonify(usuario.to_dict())


@user_bp.route("/api/usuarios/<int:id_usuario>", methods=["DELETE"])
@admin_required
def api_delete_usuario(id_usuario):
    usuario = db.get_or_404(Usuario, id_usuario)
    db.session.delete(usuario)
    db.session.commit()
    return jsonify({"message": "Usuario eliminado", "id_usuario": id_usuario})


# ---------------------------------------------------------------------
# Vistas HTML (panel de control)
# ---------------------------------------------------------------------
@user_bp.route("/administraciones/usuarios")
@admin_required
def admin_usuarios():
    usuarios = Usuario.query.order_by(Usuario.id_usuario.desc()).all()
    return render_template(
        "admin_usuarios.html",
        usuarios=usuarios,
        tipos_documento=TIPOS_DOCUMENTO,
    )


@user_bp.route("/usuarios/crear", methods=["POST"])
@admin_required
def html_create_usuario():
    tipo_documento = request.form.get("tipo_documento") or None
    if tipo_documento not in (None, *TIPOS_DOCUMENTO):
        flash("El tipo de documento debe ser C.C o T.I.", "error")
        return redirect(url_for("users.admin_usuarios"))

    usuario = Usuario(
        username=request.form["username"],
        email=request.form["email"],
        puntos_totales=request.form.get("puntos_totales", 0, type=int),
        tipo_documento=tipo_documento,
        numero_documento=request.form.get("numero_documento") or None,
    )
    db.session.add(usuario)
    if _commit_or_rollback():
        flash("Usuario creado correctamente.", "success")
    else:
        flash(DUPLICADO_MSG, "error")
    return redirect(url_for("users.admin_usuarios"))


@user_bp.route("/usuarios/<int:id_usuario>/editar", methods=["POST"])
@admin_required
def html_update_usuario(id_usuario):
    usuario = db.get_or_404(Usuario, id_usuario)
    tipo_documento = request.form.get("tipo_documento") or None
    if tipo_documento not in (None, *TIPOS_DOCUMENTO):
        flash("El tipo de documento debe ser C.C o T.I.", "error")
        return redirect(url_for("users.admin_usuarios"))

    usuario.username = request.form.get("username", usuario.username)
    usuario.email = request.form.get("email", usuario.email)
    usuario.puntos_totales = request.form.get(
        "puntos_totales", usuario.puntos_totales, type=int
    )
    usuario.tipo_documento = tipo_documento
    usuario.numero_documento = request.form.get("numero_documento") or None
    if _commit_or_rollback():
        flash("Usuario actualizado correctamente.", "success")
    else:
        flash(DUPLICADO_MSG, "error")
    return redirect(url_for("users.admin_usuarios"))


@user_bp.route("/usuarios/<int:id_usuario>/eliminar", methods=["POST"])
@admin_required
def html_delete_usuario(id_usuario):
    usuario = db.get_or_404(Usuario, id_usuario)
    db.session.delete(usuario)
    db.session.commit()
    flash("Usuario eliminado correctamente.", "success")
    return redirect(url_for("users.admin_usuarios"))
