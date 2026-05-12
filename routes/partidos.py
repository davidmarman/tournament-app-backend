from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Clasificacion, Clasificacion, Partido, PartidoEstadistica, Pertenece, StatsJugador, db
from sqlalchemy import or_

partidos_bp = Blueprint('partidos', __name__)

@partidos_bp.route('/mis-proximos', methods=['GET'])
@jwt_required() # <--- Esto obliga a que la app envíe el Token
def get_mis_proximos_partidos():
    # 1. Obtenemos el ID del usuario desde el Token
    user_id = get_jwt_identity()

    # 2. Buscamos los IDs de los equipos a los que pertenece este usuario
    # Asumiendo que tu tabla 'Pertenece' tiene id_usuario e id_equipo
    mis_vinculos = Pertenece.query.filter_by(id_usuario=user_id).all()
    ids_mis_equipos = [v.id_equipo for v in mis_vinculos]

    if not ids_mis_equipos:
        return jsonify([]), 200 # Si no tiene equipos, devolvemos lista vacía

    # 3. Filtramos los partidos:
    # El equipo local debe estar en 'ids_mis_equipos' O el visitante debe estar en 'ids_mis_equipos'
    hoy = datetime.now()
    dentro_de_30_dias = hoy + timedelta(days=30)
    partidos = Partido.query.filter(
        Partido.estado == 'Pendiente',
        Partido.fecha >= hoy,
        Partido.fecha <= dentro_de_30_dias,
        or_(
            Partido.id_local.in_(ids_mis_equipos),
            Partido.id_visitante.in_(ids_mis_equipos)
        )
    ).order_by(Partido.fecha.asc()).all()

    # 4. Formateamos la respuesta igual que antes
    resultado = []
    for p in partidos:
        resultado.append({
            "id_partido": p.id_partido,
            "equipo_local": p.equipo_local.nombre,
            "logo_local": p.equipo_local.url_logo if p.equipo_local.url_logo else "default_team.png",
            "equipo_visitante": p.equipo_visitante.nombre,
            "logo_visitante": p.equipo_visitante.url_logo if p.equipo_visitante.url_logo else "default_team.png",
            "goles_local": p.goles_local,
            "goles_visit": p.goles_visit,
            "estado": p.estado,
            "fecha": p.fecha.strftime("%d/%m/%Y %H:%M") if p.fecha else "Sin fecha",
            "nombre_torneo": p.torneo.nombre
        })

    return jsonify(resultado), 200

# =====================================================================
# RUTA 1: OBTENER LOS DATOS PARA RELLENAR EL ACTA EN ANDROID
# =====================================================================
@partidos_bp.route('/<int:id_partido>/acta', methods=['GET'])
@jwt_required()
def get_acta_partido(id_partido):
    partido = Partido.query.get_or_404(id_partido)
    
    # 1. Obtener jugadores del equipo local
    jugadores_local = []
    vinculos_local = Pertenece.query.filter_by(id_equipo=partido.id_local).all()
    for v in vinculos_local:
        u = v.usuario
        jugadores_local.append({
            "id_usuario": u.id_usuario,
            "nombre": f"{u.nombre} {u.apellido}",
            "imagen": u.imagen_perfil if u.imagen_perfil else "default.png"
        })

    # 2. Obtener jugadores del equipo visitante
    jugadores_visitante = []
    vinculos_visitante = Pertenece.query.filter_by(id_equipo=partido.id_visitante).all()
    for v in vinculos_visitante:
        u = v.usuario
        jugadores_visitante.append({
            "id_usuario": u.id_usuario,
            "nombre": f"{u.nombre} {u.apellido}",
            "imagen": u.imagen_perfil if u.imagen_perfil else "default.png"
        })

    # 3. Devolverlo todo empaquetado
    return jsonify({
        "id_partido": partido.id_partido,
        "torneo_nombre": partido.torneo.nombre,
        "jornada": partido.numero_jornada,
        "equipo_local": {
            "id": partido.id_local,
            "nombre": partido.equipo_local.nombre,
            "logo": partido.equipo_local.url_logo if partido.equipo_local.url_logo else "default_team.png",
            "capitan": partido.equipo_local.id_capitan,
            "jugadores": jugadores_local
        },
        "equipo_visitante": {
            "id": partido.id_visitante,
            "nombre": partido.equipo_visitante.nombre,
            "logo": partido.equipo_visitante.url_logo if partido.equipo_visitante.url_logo else "default_team.png",
            "capitan": partido.equipo_visitante.id_capitan,
            "jugadores": jugadores_visitante
        }
    }), 200


# =====================================================================
# RUTA 2: RECIBIR RESULTADOS Y ACTUALIZAR CLASIFICACIÓN
# =====================================================================
@partidos_bp.route('/<int:id_partido>/finalizar', methods=['POST'])
@jwt_required()
def finalizar_partido(id_partido):
    partido = Partido.query.get_or_404(id_partido)
    
    if partido.estado == 'Fin':
        return jsonify({"error": "Este partido ya fue finalizado"}), 400

    data = request.get_json()
    goles_local = data.get('goles_local', 0)
    goles_visit = data.get('goles_visitante', 0)
    eventos = data.get('eventos', []) # Lista de jugadores que han hecho algo

    # 1. ACTUALIZAR EL PARTIDO
    partido.goles_local = goles_local
    partido.goles_visit = goles_visit
    partido.estado = 'Fin'

    # 2. ACTUALIZAR LA CLASIFICACIÓN
    clasif_local = Clasificacion.query.filter_by(id_torneo=partido.id_torneo, id_equipo=partido.id_local).first()
    clasif_visit = Clasificacion.query.filter_by(id_torneo=partido.id_torneo, id_equipo=partido.id_visitante).first()

    if clasif_local and clasif_visit:
        # Magia defensiva: (variable or 0) asegura que si es None, use 0.
        clasif_local.pj = (clasif_local.pj or 0) + 1
        clasif_visit.pj = (clasif_visit.pj or 0) + 1
        
        clasif_local.gf = (clasif_local.gf or 0) + goles_local
        clasif_local.gc = (clasif_local.gc or 0) + goles_visit
        
        clasif_visit.gf = (clasif_visit.gf or 0) + goles_visit
        clasif_visit.gc = (clasif_visit.gc or 0) + goles_local

        # Aseguramos el resto de variables antes de operar
        clasif_local.puntos = (clasif_local.puntos or 0)
        clasif_local.pg = (clasif_local.pg or 0)
        clasif_local.pe = (clasif_local.pe or 0)
        clasif_local.pp = (clasif_local.pp or 0)
        
        clasif_visit.puntos = (clasif_visit.puntos or 0)
        clasif_visit.pg = (clasif_visit.pg or 0)
        clasif_visit.pe = (clasif_visit.pe or 0)
        clasif_visit.pp = (clasif_visit.pp or 0)

        if goles_local > goles_visit:
            clasif_local.pg += 1
            clasif_local.puntos += 3
            clasif_visit.pp += 1
        elif goles_visit > goles_local:
            clasif_visit.pg += 1
            clasif_visit.puntos += 3
            clasif_local.pp += 1
        else:
            clasif_local.pe += 1
            clasif_visit.pe += 1
            clasif_local.puntos += 1
            clasif_visit.puntos += 1

    # 3. GUARDAR ESTADÍSTICAS INDIVIDUALES (Goles y Tarjetas)
    for ev in eventos:
        id_usr = ev.get('id_usuario')
        goles = ev.get('goles', 0)
        amarillas = ev.get('amarillas', 0)
        rojas = ev.get('rojas', 0)

        # Si el jugador no hizo nada, nos lo saltamos
        if goles == 0 and amarillas == 0 and rojas == 0:
            continue

        # A) Guardar en el acta del partido
        nuevo_evento = PartidoEstadistica(
            id_partido=partido.id_partido,
            id_usuario=id_usr,
            goles=goles,
            amarillas=amarillas,
            rojas=rojas
        )
        db.session.add(nuevo_evento)

        # B) Acumular en las estadísticas generales del torneo
        stats_gen = StatsJugador.query.filter_by(id_usuario=id_usr, id_torneo=partido.id_torneo).first()
        if not stats_gen:
            stats_gen = StatsJugador(id_usuario=id_usr, id_torneo=partido.id_torneo)
            db.session.add(stats_gen)
        
        # Magia defensiva contra valores nulos
        stats_gen.goles = (stats_gen.goles or 0) + goles
        stats_gen.amarillas = (stats_gen.amarillas or 0) + amarillas
        stats_gen.rojas = (stats_gen.rojas or 0) + rojas

    # 4. Aceptar los cambios
    db.session.commit()
    return jsonify({"msg": "Partido finalizado y clasificación actualizada"}), 200