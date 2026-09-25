"""
models.py
---------
Modelos relacionales SQLAlchemy para Chronos Gaming Hub & Cloud Services.

Tablas:
    usuarios          -> cuentas de la plataforma
    licencias_juego   -> licencias de juegos asociadas a un usuario
    guardados_nube    -> snapshots de partidas guardadas (patrón Memento)
    insignias_usuario -> insignias/logros otorgados (patrón Observer)
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum as SAEnum

db = SQLAlchemy()
TIPOS_DOCUMENTO = ("C.C", "T.I")


class TipoLicencia:
    ESTANDAR = "ESTANDAR"
    PREMIUM = "PREMIUM"
    PASE_TEMPORADA = "PASE_TEMPORADA"

    ALL = [ESTANDAR, PREMIUM, PASE_TEMPORADA]


class EstadoLicencia:
    ACTIVA = "ACTIVA"
    EXPIRADA = "EXPIRADA"
    SUSPENDIDA = "SUSPENDIDA"

    ALL = [ACTIVA, EXPIRADA, SUSPENDIDA]


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id_usuario = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    puntos_totales = db.Column(db.Integer, default=0, nullable=False)

    # Datos capturados post-registro vía Auth0 (user_metadata)
    tipo_documento = db.Column(db.String(20), nullable=True)
    numero_documento = db.Column(db.String(50), nullable=True)
    auth0_sub = db.Column(db.String(120), unique=True, nullable=True)

    licencias = db.relationship(
        "LicenciaJuego", backref="usuario", cascade="all, delete-orphan", lazy=True
    )
    guardados = db.relationship(
        "GuardadoNube", backref="usuario", cascade="all, delete-orphan", lazy=True
    )
    insignias = db.relationship(
        "InsigniaUsuario", backref="usuario", cascade="all, delete-orphan", lazy=True
    )

    def to_dict(self):
        return {
            "id_usuario": self.id_usuario,
            "username": self.username,
            "email": self.email,
            "fecha_registro": self.fecha_registro.isoformat() if self.fecha_registro else None,
            "puntos_totales": self.puntos_totales,
            "tipo_documento": self.tipo_documento,
            "numero_documento": self.numero_documento,
        }


class LicenciaJuego(db.Model):
    __tablename__ = "licencias_juego"

    id_licencia = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    tipo_licencia = db.Column(
        SAEnum(*TipoLicencia.ALL, name="tipo_licencia_enum"), nullable=False
    )
    codigo_activacion = db.Column(db.String(64), unique=True, nullable=False)
    estado = db.Column(
        SAEnum(*EstadoLicencia.ALL, name="estado_licencia_enum"),
        default=EstadoLicencia.ACTIVA,
        nullable=False,
    )

    def to_dict(self):
        return {
            "id_licencia": self.id_licencia,
            "id_usuario": self.id_usuario,
            "tipo_licencia": self.tipo_licencia,
            "codigo_activacion": self.codigo_activacion,
            "estado": self.estado,
        }


class GuardadoNube(db.Model):
    """Soporte del patrón Memento: cada fila es un snapshot restaurable."""

    __tablename__ = "guardados_nube"

    id_guardado = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    fecha_guardado = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    nivel_alcanzado = db.Column(db.Integer, default=1, nullable=False)
    snapshot_data = db.Column(db.JSON, nullable=True)

    def to_dict(self):
        return {
            "id_guardado": self.id_guardado,
            "id_usuario": self.id_usuario,
            "fecha_guardado": self.fecha_guardado.isoformat() if self.fecha_guardado else None,
            "nivel_alcanzado": self.nivel_alcanzado,
            "snapshot_data": self.snapshot_data,
        }


class InsigniaUsuario(db.Model):
    """Soporte del patrón Observer: se crea una insignia cuando un evento
    del juego (observado) notifica el cumplimiento de un logro."""

    __tablename__ = "insignias_usuario"

    id_insignia = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    nombre_insignia = db.Column(db.String(100), nullable=False)
    puntos_otorgados = db.Column(db.Integer, default=0, nullable=False)
    fecha_desbloqueo = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id_insignia": self.id_insignia,
            "id_usuario": self.id_usuario,
            "nombre_insignia": self.nombre_insignia,
            "puntos_otorgados": self.puntos_otorgados,
            "fecha_desbloqueo": self.fecha_desbloqueo.isoformat()
            if self.fecha_desbloqueo
            else None,
        }
