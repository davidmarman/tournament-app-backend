from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Usuario, Partido, Torneo
from sqlalchemy import or_

usuario_bp = Blueprint('usuario', __name__)

@usuario_bp.route('/perfil', methods=['GET'])
@jwt_required()
def get_perfil_completo():
    user_id = get_jwt_identity()
    u = Usuario.query.get(user_id)
    
    if not u:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # 1. Recopilamos sus equipos
    equipos = []
    for vinculo in u.equipos:
        # Asumiendo que vinculo.equipo accede a la tabla Equipo
        if vinculo.equipo:
            equipos.append({
                "id": vinculo.equipo.id_equipo, 
                "nombre": vinculo.equipo.nombre, 
                "logo": vinculo.equipo.url_logo if vinculo.equipo.url_logo else "default_team.png"
            })

    # 2. Recopilamos sus torneos
    ids_equipos = [v.id_equipo for v in u.equipos]
    torneos = []
    
    if ids_equipos:
        partidos = Partido.query.filter(
            or_(Partido.id_local.in_(ids_equipos), Partido.id_visitante.in_(ids_equipos))
        ).all()
        
        ids_torneos = list(set([p.id_torneo for p in partidos]))
        if ids_torneos:
            torneos_db = Torneo.query.filter(Torneo.id_torneo.in_(ids_torneos)).all()
            torneos = [{"id": t.id_torneo, 
                        "nombre": t.nombre, 
                        "logo": t.url_logo if t.url_logo else "default_torneo.png"} for t in torneos_db]

    # 3. Estadísticas
    goles = sum([s.goles for s in u.estadisticas]) if u.estadisticas else 0
    faltas = sum([s.faltas for s in u.estadisticas]) if u.estadisticas else 0

    # Retornamos el JSON gigante que Android espera
    return jsonify({
        "nombre": u.nombre + " " + u.apellido,
        "username": "@" + u.username,
        "imagen": u.imagen_perfil,
        "equipos": equipos,
        "torneos": torneos,
        "stats": {"goles": goles, "faltas": faltas}
    }), 200