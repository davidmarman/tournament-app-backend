from extensions import db
from datetime import date, datetime

# =====================================================================
# 1. TABLAS INTERMEDIAS (Relaciones con datos adicionales)
# =====================================================================

class Pertenece(db.Model):
    __tablename__ = 'pertenece'
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), primary_key=True)
    id_equipo = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), primary_key=True)
    fecha_alta = db.Column(db.Date, default=date.today)

class Clasificacion(db.Model):
    __tablename__ = 'clasificacion'
    id_torneo = db.Column(db.Integer, db.ForeignKey('torneo.id_torneo'), primary_key=True)
    id_equipo = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), primary_key=True)
    puntos = db.Column(db.Integer, default=0)
    pj = db.Column(db.Integer, default=0) # Partidos Jugados
    pg = db.Column(db.Integer, default=0) # Partidos Ganados
    pe = db.Column(db.Integer, default=0) # Partidos Empatados
    pp = db.Column(db.Integer, default=0) # Partidos Perdidos

class StatsJugador(db.Model):
    __tablename__ = 'stats_jugador'
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), primary_key=True)
    id_torneo = db.Column(db.Integer, db.ForeignKey('torneo.id_torneo'), primary_key=True)
    goles = db.Column(db.Integer, default=0)
    faltas = db.Column(db.Integer, default=0)


# =====================================================================
# 2. TABLAS PRINCIPALES (Entidades base)
# =====================================================================

class Usuario(db.Model):
    __tablename__ = 'usuario'
    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.Enum('Admin', 'User', name='rol_types'), default='User', nullable=False)
    imagen_perfil = db.Column(db.String(255), nullable=True, default='default.png')

    # Relaciones para acceder fácilmente a sus datos desde Python
    equipos = db.relationship('Pertenece', backref='usuario', lazy=True)
    estadisticas = db.relationship('StatsJugador', backref='usuario', lazy=True)

class Equipo(db.Model):
    __tablename__ = 'equipo'
    id_equipo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    url_logo = db.Column(db.String(255), nullable=True)

    # Relaciones
    jugadores = db.relationship('Pertenece', backref='equipo', lazy=True)
    clasificaciones = db.relationship('Clasificacion', backref='equipo', lazy=True)

class Torneo(db.Model):
    __tablename__ = 'torneo'
    id_torneo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.Enum('Liga', 'Eliminatoria', name='tipo_torneo'), nullable=False)
    fechas = db.Column(db.Date, nullable=True)

    # Relaciones
    partidos = db.relationship('Partido', backref='torneo', lazy=True)
    clasificaciones = db.relationship('Clasificacion', backref='torneo', lazy=True)
    estadisticas_jugadores = db.relationship('StatsJugador', backref='torneo', lazy=True)

class Partido(db.Model):
    __tablename__ = 'partido'
    id_partido = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_torneo = db.Column(db.Integer, db.ForeignKey('torneo.id_torneo'), nullable=False)
    id_local = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), nullable=False)
    id_visitante = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), nullable=False)
    goles_local = db.Column(db.Integer, default=0)
    goles_visit = db.Column(db.Integer, default=0)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    estado = db.Column(db.Enum('Pendiente', 'Fin', name='estado_partido'), default='Pendiente', nullable=False)

    # Para poder saber quién es el local y quién el visitante sin confundir a SQLAlchemy
    equipo_local = db.relationship('Equipo', foreign_keys=[id_local])
    equipo_visitante = db.relationship('Equipo', foreign_keys=[id_visitante])