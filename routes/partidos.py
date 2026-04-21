from datetime import datetime, timedelta

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Partido, Pertenece, db
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