from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Usuario, Inscripcion, db 

usuario_bp = Blueprint('usuario', __name__)

@usuario_bp.route('/perfil', methods=['GET'])
@jwt_required()
def get_perfil_completo():
    user_id = get_jwt_identity()
    u = Usuario.query.get(user_id)
    
    if not u:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # 1. Recopilamos sus equipos y guardamos los IDs para el paso 2
    equipos = []
    ids_equipos = []
    for vinculo in u.equipos:
        if vinculo.equipo:
            equipos.append({
                "id": vinculo.equipo.id_equipo, 
                "nombre": vinculo.equipo.nombre, 
                "logo": vinculo.equipo.url_logo if vinculo.equipo.url_logo else "default_team.png"
            })
            ids_equipos.append(vinculo.equipo.id_equipo)

    # 2. Recopilamos sus torneos
    torneos = []
    if ids_equipos:
        # Buscamos todas las inscripciones de los equipos del usuario
        inscripciones = Inscripcion.query.filter(Inscripcion.id_equipo.in_(ids_equipos)).all()
        
        # Usamos un diccionario para evitar que un torneo salga repetido
        torneos_dict = {}
        for ins in inscripciones:
            t = ins.torneo
            if t and t.id_torneo not in torneos_dict:
                torneos_dict[t.id_torneo] = {
                    "id": t.id_torneo, 
                    "nombre": t.nombre, 
                    "logo": t.url_logo if t.url_logo else "default_torneo.png"
                }
        
        # Convertimos el diccionario a la lista que Android espera
        torneos = list(torneos_dict.values())

    # 3. Estadísticas
    goles = sum([s.goles for s in u.estadisticas]) if u.estadisticas else 0
    faltas = sum([s.faltas for s in u.estadisticas]) if u.estadisticas else 0

    # Retornamos el JSON
    return jsonify({
        "nombre": f"{u.nombre} {u.apellido}",
        "username": f"@{u.username}",
        "imagen": u.imagen_perfil,
        "equipos": equipos,
        "torneos": torneos,
        "stats": {"goles": goles, "faltas": faltas}
    }), 200