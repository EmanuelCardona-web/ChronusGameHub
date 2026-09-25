"""
license_routes.py
------------------
CRUD completo de `licencias_juego`, expuesto como:
  - API JSON REST bajo /api/licencias
  - Vistas HTML (formularios) bajo /licencias
"""

import uuid

from flask import Blueprint, jsonify, request, redirect, url_for, flash, render_template

from models import db, LicenciaJuego, TipoLicencia, EstadoLicencia, Usuario

license_bp = Blueprint("licenses", __name__)


def _has_other_active_license(id_usuario, exclude_id=None):
    query = LicenciaJuego.query.filter_by(
        id_usuario=id_usuario,
        estado=EstadoLicencia.ACTIVA,
    )
    if exclude_id is not None:
        query = query.filter(LicenciaJuego.id_licencia != exclude_id)
    return query.first() is not None


# ---------------------------------------------------------------------
# API JSON REST
# ---------------------------------------------------------------------
@license_bp.route("/api/licencias", methods=["GET"])
def api_list_licencias():
    licencias = LicenciaJuego.query.order_by(LicenciaJuego.id_licencia).all()
    return jsonify([l.to_dict() for l in licencias])


@license_bp.route("/api/licencias/<int:id_licencia>", methods=["GET"])
def api_get_licencia(id_licencia):
    licencia = LicenciaJuego.query.get_or_404(id_licencia)
    return jsonify(licencia.to_dict())


@license_bp.route("/api/licencias", methods=["POST"])
def api_create_licencia():
    data = request.get_json(force=True)

    tipo_licencia = data.get("tipo_licencia", TipoLicencia.ESTANDAR)
    if tipo_licencia not in TipoLicencia.ALL:
        return jsonify({"error": f"tipo_licencia inválido. Use uno de {TipoLicencia.ALL}"}), 400

    id_usuario = data.get("id_usuario")
    estado = data.get("estado", EstadoLicencia.ACTIVA)
    if not Usuario.query.get(id_usuario):
        return jsonify({"error": "El usuario indicado no existe."}), 400
    if estado not in EstadoLicencia.ALL:
        return jsonify({"error": f"estado inválido. Use uno de {EstadoLicencia.ALL}"}), 400
    if estado == EstadoLicencia.ACTIVA and _has_other_active_license(id_usuario):
        return jsonify({"error": "El usuario ya cuenta con una licencia activa."}), 409

    licencia = LicenciaJuego(
        id_usuario=id_usuario,
        tipo_licencia=tipo_licencia,
        codigo_activacion=data.get("codigo_activacion") or str(uuid.uuid4()),
        estado=estado,
    )
    db.session.add(licencia)
    db.session.commit()
    return jsonify(licencia.to_dict()), 201


@license_bp.route("/api/licencias/<int:id_licencia>", methods=["PUT", "PATCH"])
def api_update_licencia(id_licencia):
    licencia = LicenciaJuego.query.get_or_404(id_licencia)
    data = request.get_json(force=True)
    id_usuario = data.get("id_usuario", licencia.id_usuario)
    estado = data.get("estado", licencia.estado)

    if "estado" in data and estado not in EstadoLicencia.ALL:
        return jsonify({"error": f"estado inválido. Use uno de {EstadoLicencia.ALL}"}), 400
    tipo_licencia = data.get("tipo_licencia", licencia.tipo_licencia)
    if tipo_licencia not in TipoLicencia.ALL:
        return jsonify({"error": f"tipo_licencia inválido. Use uno de {TipoLicencia.ALL}"}), 400
    if "id_usuario" in data and not Usuario.query.get(id_usuario):
        return jsonify({"error": "El usuario indicado no existe."}), 400
    if estado == EstadoLicencia.ACTIVA and _has_other_active_license(
        id_usuario, exclude_id=licencia.id_licencia
    ):
        return jsonify({"error": "El usuario ya cuenta con una licencia activa."}), 409
    licencia.id_usuario = id_usuario
    licencia.estado = estado
    licencia.tipo_licencia = tipo_licencia

    if "codigo_activacion" in data:
        licencia.codigo_activacion = data["codigo_activacion"]

    db.session.commit()
    return jsonify(licencia.to_dict())


@license_bp.route("/api/licencias/<int:id_licencia>", methods=["DELETE"])
def api_delete_licencia(id_licencia):
    licencia = LicenciaJuego.query.get_or_404(id_licencia)
    db.session.delete(licencia)
    db.session.commit()
    return jsonify({"message": "Licencia eliminada", "id_licencia": id_licencia})


# ---------------------------------------------------------------------
# Vistas HTML (panel de control)
# ---------------------------------------------------------------------
@license_bp.route("/administraciones/licencias")
def admin_licencias():
    licencias = LicenciaJuego.query.order_by(LicenciaJuego.id_licencia.desc()).all()
    usuarios = Usuario.query.order_by(Usuario.username).all()
    activas_por_usuario = {}
    for id_usuario, in db.session.query(LicenciaJuego.id_usuario).filter_by(
        estado=EstadoLicencia.ACTIVA
    ).all():
        activas_por_usuario[id_usuario] = activas_por_usuario.get(id_usuario, 0) + 1

    usuarios_disponibles = [
        usuario for usuario in usuarios
        if activas_por_usuario.get(usuario.id_usuario, 0) == 0
    ]
    usuarios_por_licencia = {}
    for licencia in licencias:
        usuarios_por_licencia[licencia.id_licencia] = [
            usuario for usuario in usuarios
            if activas_por_usuario.get(usuario.id_usuario, 0) == 0
            or usuario.id_usuario == licencia.id_usuario
        ]

    return render_template(
        "admin_licencias.html",
        licencias=licencias,
        usuarios=usuarios,
        usuarios_disponibles=usuarios_disponibles,
        usuarios_por_licencia=usuarios_por_licencia,
        tipos_licencia=TipoLicencia.ALL,
        estados_licencia=EstadoLicencia.ALL,
    )


@license_bp.route("/licencias/crear", methods=["POST"])
def html_create_licencia():
    id_usuario = request.form.get("id_usuario", type=int)
    tipo_licencia = request.form.get("tipo_licencia")
    estado = request.form.get("estado", EstadoLicencia.ACTIVA)
    if not Usuario.query.get(id_usuario):
        flash("Selecciona un usuario válido.", "error")
        return redirect(url_for("licenses.admin_licencias"))
    if tipo_licencia not in TipoLicencia.ALL or estado not in EstadoLicencia.ALL:
        flash("Tipo o estado de licencia inválido.", "error")
        return redirect(url_for("licenses.admin_licencias"))
    if estado == EstadoLicencia.ACTIVA and _has_other_active_license(id_usuario):
        flash("El usuario ya cuenta con una licencia activa.", "error")
        return redirect(url_for("licenses.admin_licencias"))

    licencia = LicenciaJuego(
        id_usuario=id_usuario,
        tipo_licencia=tipo_licencia,
        codigo_activacion=request.form.get("codigo_activacion") or str(uuid.uuid4()),
        estado=estado,
    )
    db.session.add(licencia)
    db.session.commit()
    flash("Licencia creada correctamente.", "success")
    return redirect(url_for("licenses.admin_licencias"))


@license_bp.route("/licencias/<int:id_licencia>/editar", methods=["POST"])
def html_update_licencia(id_licencia):
    licencia = LicenciaJuego.query.get_or_404(id_licencia)
    id_usuario = request.form.get("id_usuario", type=int)
    tipo_licencia = request.form.get("tipo_licencia")
    estado = request.form.get("estado")
    if (
        not Usuario.query.get(id_usuario)
        or tipo_licencia not in TipoLicencia.ALL
        or estado not in EstadoLicencia.ALL
    ):
        flash("Tipo o estado de licencia inválido.", "error")
        return redirect(url_for("licenses.admin_licencias"))
    if estado == EstadoLicencia.ACTIVA and _has_other_active_license(
        id_usuario, exclude_id=licencia.id_licencia
    ):
        flash("El usuario ya cuenta con otra licencia activa.", "error")
        return redirect(url_for("licenses.admin_licencias"))

    licencia.id_usuario = id_usuario
    licencia.tipo_licencia = tipo_licencia
    licencia.codigo_activacion = request.form.get("codigo_activacion", licencia.codigo_activacion)
    licencia.estado = estado
    db.session.commit()
    flash("Licencia actualizada correctamente.", "success")
    return redirect(url_for("licenses.admin_licencias"))


@license_bp.route("/licencias/<int:id_licencia>/estado", methods=["POST"])
def html_update_estado_licencia(id_licencia):
    licencia = LicenciaJuego.query.get_or_404(id_licencia)
    nuevo_estado = request.form.get("estado")
    if nuevo_estado in EstadoLicencia.ALL:
        if nuevo_estado == EstadoLicencia.ACTIVA and _has_other_active_license(
            licencia.id_usuario, exclude_id=licencia.id_licencia
        ):
            flash("El usuario ya cuenta con otra licencia activa.", "error")
            return redirect(url_for("licenses.admin_licencias"))
        licencia.estado = nuevo_estado
        db.session.commit()
        flash("Estado de la licencia actualizado.", "success")
    else:
        flash("Estado inválido.", "error")
    return redirect(url_for("licenses.admin_licencias"))


@license_bp.route("/licencias/<int:id_licencia>/eliminar", methods=["POST"])
def html_delete_licencia(id_licencia):
    licencia = LicenciaJuego.query.get_or_404(id_licencia)
    db.session.delete(licencia)
    db.session.commit()
    flash("Licencia eliminada correctamente.", "success")
    return redirect(url_for("licenses.admin_licencias"))
