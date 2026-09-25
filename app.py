"""
app.py
------
Fábrica de la aplicación Flask ("application factory") para
Chronos Gaming Hub & Cloud Services. Registra la base de datos
y los blueprints de rutas (auth, usuarios, licencias).
"""

from flask import Flask, render_template

from config import Config
from models import db, Usuario, LicenciaJuego

from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.license_routes import license_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(user_bp)
    app.register_blueprint(license_bp)

    @app.route("/")
    def index():
        usuarios = Usuario.query.order_by(Usuario.id_usuario.desc()).all()
        licencias = LicenciaJuego.query.order_by(LicenciaJuego.id_licencia.desc()).all()
        return render_template(
            "index.html",
            usuarios=usuarios,
            licencias=licencias,
            tipos_licencia=["ESTANDAR", "PREMIUM", "PASE_TEMPORADA"],
            estados_licencia=["ACTIVA", "EXPIRADA", "SUSPENDIDA"],
        )

    with app.app_context():
        # En producción usar Flask-Migrate / Alembic en lugar de create_all.
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
