"""
app.py
------
Fábrica de la aplicación Flask ("application factory") para
Chronos Gaming Hub & Cloud Services. Registra la base de datos,
la capa de seguridad y los blueprints de rutas (auth, usuarios, licencias).
"""

from urllib.parse import urlparse

from flask import Flask, flash, g, jsonify, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError
from sqlalchemy import func

from config import Config
from models import db, Usuario, LicenciaJuego, EstadoLicencia
from security import init_security, is_admin, login_required

from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.license_routes import license_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    init_security(app)

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(user_bp)
    app.register_blueprint(license_bp)

    @app.route("/")
    def index():
        if g.get("user"):
            return redirect(url_for("dashboard"))
        return render_template("index.html")

    @app.route("/dashboard")
    @login_required
    def dashboard():
        usuario = db.session.get(Usuario, g.user["id_usuario"])
        if usuario is None:
            # La cuenta local fue eliminada mientras la sesión seguía abierta.
            return redirect(url_for("auth.login_page"))

        context = {"usuario": usuario}
        if is_admin():
            por_estado = dict(
                db.session.query(LicenciaJuego.estado, func.count())
                .group_by(LicenciaJuego.estado)
                .all()
            )
            context.update(
                total_usuarios=Usuario.query.count(),
                total_licencias=sum(por_estado.values()),
                licencias_por_estado={e: por_estado.get(e, 0) for e in EstadoLicencia.ALL},
                ultimos_usuarios=Usuario.query.order_by(Usuario.id_usuario.desc()).limit(5).all(),
                ultimas_licencias=LicenciaJuego.query.order_by(
                    LicenciaJuego.id_licencia.desc()
                ).limit(5).all(),
            )
        return render_template("dashboard.html", **context)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Token CSRF inválido o ausente."}), 400
        flash("Tu sesión del formulario expiró. Vuelve a intentarlo.", "error")
        referrer = request.referrer
        if referrer and urlparse(referrer).netloc == request.host:
            return redirect(referrer)
        return redirect(url_for("index"))

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Recurso no encontrado."}), 404
        return render_template("error.html", code=404, message="La página que buscas no existe."), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        if request.path.startswith("/api/"):
            return jsonify({"error": "Error interno del servidor."}), 500
        return render_template("error.html", code=500, message="Algo salió mal. Intenta de nuevo."), 500

    with app.app_context():
        # En producción usar Flask-Migrate / Alembic en lugar de create_all.
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"], port=5000)
