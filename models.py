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

class Inscripcion(db.Model):
    __tablename__ = 'inscripcion'
    id_inscripcion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_equipo = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), nullable=False)
    id_torneo = db.Column(db.Integer, db.ForeignKey('torneo.id_torneo'), nullable=False)
    fecha_inscripcion = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones para navegar fácilmente
    equipo = db.relationship('Equipo', backref=db.backref('inscripciones', lazy=True))
    torneo = db.relationship('Torneo', backref=db.backref('inscripciones', lazy=True))

class Clasificacion(db.Model):
    __tablename__ = 'clasificacion'
    id_torneo = db.Column(db.Integer, db.ForeignKey('torneo.id_torneo'), primary_key=True)
    id_equipo = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), primary_key=True)
    puntos = db.Column(db.Integer, default=0)
    pj = db.Column(db.Integer, default=0) # Partidos Jugados
    pg = db.Column(db.Integer, default=0) # Partidos Ganados
    pe = db.Column(db.Integer, default=0) # Partidos Empatados
    pp = db.Column(db.Integer, default=0) # Partidos Perdidos
    gf = db.Column(db.Integer, default=0) # Goles a Favor
    gc = db.Column(db.Integer, default=0) # Goles en Contra

class StatsJugador(db.Model):
    __tablename__ = 'stats_jugador'
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), primary_key=True)
    id_torneo = db.Column(db.Integer, db.ForeignKey('torneo.id_torneo'), primary_key=True)
    goles = db.Column(db.Integer, default=0)
    amarillas = db.Column(db.Integer, default=0)
    rojas = db.Column(db.Integer, default=0)

class PartidoEstadistica(db.Model):
    __tablename__ = 'partido_estadistica'
    id_stats_partido = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_partido = db.Column(db.Integer, db.ForeignKey('partido.id_partido'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)
    goles = db.Column(db.Integer, default=0)
    amarillas = db.Column(db.Integer, default=0)
    rojas = db.Column(db.Integer, default=0)

# ¡NUEVA TABLA! Para los administradores de los torneos
class Administra(db.Model):
    __tablename__ = 'administra'
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), primary_key=True)
    id_torneo = db.Column(db.Integer, db.ForeignKey('torneo.id_torneo'), primary_key=True)
    fecha_asignacion = db.Column(db.DateTime, default=datetime.utcnow)

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

    # Relaciones
    equipos = db.relationship('Pertenece', backref='usuario', lazy=True)
    estadisticas = db.relationship('StatsJugador', backref='usuario', lazy=True)
    torneos_administrados = db.relationship('Administra', backref='usuario', lazy=True)

class Equipo(db.Model):
    __tablename__ = 'equipo'
    id_equipo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    url_logo = db.Column(db.String(255), nullable=True)
    id_capitan = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)

    # Relaciones
    jugadores = db.relationship('Pertenece', backref='equipo', lazy=True)
    clasificaciones = db.relationship('Clasificacion', backref='equipo', lazy=True)

class Torneo(db.Model):
    __tablename__ = 'torneo'
    id_torneo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.Enum('Liga', 'Eliminatoria', name='tipo_torneo'), nullable=False)
    url_logo = db.Column(db.String(255), nullable=True, default='default_torneo.png')
    codigo_acceso = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    
    # ¡MODIFICADO! Para soportar franjas múltiples
    fecha_inicio = db.Column(db.Date, nullable=True)
    dias_juego = db.Column(db.String(100), nullable=True) # Ej: "Sabado,Domingo"
    horarios_juego = db.Column(db.Text, nullable=True)    # Ej: "16:00-17:00,17:00-18:00,20:00-21:00"

    # Relaciones
    partidos = db.relationship('Partido', backref='torneo', lazy=True)
    clasificaciones = db.relationship('Clasificacion', backref='torneo', lazy=True)
    estadisticas_jugadores = db.relationship('StatsJugador', backref='torneo', lazy=True)
    administradores = db.relationship('Administra', backref='torneo', lazy=True)

class Partido(db.Model):
    __tablename__ = 'partido'
    id_partido = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_torneo = db.Column(db.Integer, db.ForeignKey('torneo.id_torneo'), nullable=False)
    id_local = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), nullable=False)
    id_visitante = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), nullable=False)
    goles_local = db.Column(db.Integer, default=0)
    goles_visit = db.Column(db.Integer, default=0)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # ¡AÑADIDO "En Juego"!
    estado = db.Column(db.Enum('Pendiente', 'En Juego', 'Fin', name='estado_partido'), default='Pendiente', nullable=False)
    numero_jornada = db.Column(db.Integer, default=1, nullable=False)

    equipo_local = db.relationship('Equipo', foreign_keys=[id_local])
    equipo_visitante = db.relationship('Equipo', foreign_keys=[id_visitante])