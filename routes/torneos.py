from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Torneo, Equipo, Inscripcion, Usuario, Partido, Clasificacion, db

torneos_bp = Blueprint('torneos', __name__)

@torneos_bp.route('/inscribir', methods=['POST'])
@jwt_required()
def inscribir_equipo():
    user_id = get_jwt_identity()
    data = request.get_json()

    codigo = data.get('codigo_acceso')
    id_equipo = data.get('id_equipo')

    if not codigo or not id_equipo:
        return jsonify({"error": "Faltan datos"}), 400

    # 1. Buscar torneo por el código secreto
    torneo = Torneo.query.filter_by(codigo_acceso=codigo).first()
    if not torneo:
        return jsonify({"error": "El código de torneo no es válido"}), 404

    # 2. Verificar que el equipo existe y que el usuario es el capitán
    equipo = Equipo.query.get(id_equipo)
    if not equipo:
        return jsonify({"error": "Equipo no encontrado"}), 404
        
    if str(equipo.id_capitan) != str(user_id):
        return jsonify({"error": "Solo el capitán puede inscribir al equipo en un torneo"}), 403

    # 3. Verificar si el equipo ya está inscrito
    ya_inscrito = Inscripcion.query.filter_by(id_equipo=id_equipo, id_torneo=torneo.id_torneo).first()
    if ya_inscrito:
        return jsonify({"error": f"Tu equipo ya está inscrito en {torneo.nombre}"}), 400

    # 4. Crear la inscripción
    nueva_inscripcion = Inscripcion(id_equipo=id_equipo, id_torneo=torneo.id_torneo)
    db.session.add(nueva_inscripcion)
    db.session.commit()

    return jsonify({"msg": f"¡{equipo.nombre} ha sido inscrito en {torneo.nombre} con éxito!"}), 201


# Ruta para obtener los torneos en los que participa el usuario
@torneos_bp.route('/mis-torneos', methods=['GET'])
@jwt_required()
def get_mis_torneos():
    user_id = get_jwt_identity()
    usuario = Usuario.query.get(user_id)
    
    # Sacamos los IDs de los equipos del usuario
    ids_equipos = [v.id_equipo for v in usuario.equipos if v.equipo]
    
    torneos_dict = {}
    if ids_equipos:
        # Buscamos las inscripciones de esos equipos
        inscripciones = Inscripcion.query.filter(Inscripcion.id_equipo.in_(ids_equipos)).all()
        for ins in inscripciones:
            t = ins.torneo
            if t and t.id_torneo not in torneos_dict:
                torneos_dict[t.id_torneo] = {
                    "id": t.id_torneo,
                    "nombre": t.nombre,
                    "logo": t.url_logo if t.url_logo else "default_torneo.png"
                }
                
    # Devolvemos la lista de torneos
    return jsonify(list(torneos_dict.values())), 200


# Ruta para obtener el detalle de un torneo específico (clasificación + próxima jornada)
@torneos_bp.route('/<int:id_torneo>/detalle', methods=['GET'])
@jwt_required()
def get_detalle_torneo(id_torneo):
    torneo = Torneo.query.get_or_404(id_torneo)

    # 1. INFO BÁSICA (Cabecera)
    info_basica = {
        "id": torneo.id_torneo,
        "nombre": torneo.nombre,
        "logo": torneo.url_logo if torneo.url_logo else "default_torneo.png",
        "descripcion": torneo.descripcion or "Sin descripción disponible."
    }

    # 2. CLASIFICACIÓN (Bloque central)
    clasificaciones = Clasificacion.query.filter_by(id_torneo=id_torneo).order_by(Clasificacion.puntos.desc()).all()
    lista_clasificacion = []
    
    for c in clasificaciones:
        equipo = c.equipo
        lista_clasificacion.append({
            "id_equipo": equipo.id_equipo,
            "nombre": equipo.nombre,
            "logo": equipo.url_logo if equipo.url_logo else "default_team.png",
            "pts": c.puntos,
            "gf": 0, # De momento enviamos 0, lo rellenaremos cuando el Admin suba resultados
            "gc": 0
        })

    # 3. PRÓXIMA JORNADA (Bloque inferior)
    # Buscamos el primer partido pendiente para saber por qué jornada vamos
    siguiente_partido = Partido.query.filter_by(
        id_torneo=id_torneo, estado='Pendiente'
    ).order_by(Partido.numero_jornada.asc()).first()

    # Si no hay partidos pendientes, asumimos la jornada 1 o la última jugada
    jornada_actual = siguiente_partido.numero_jornada if siguiente_partido else 1

    partidos_jornada = Partido.query.filter_by(
        id_torneo=id_torneo, numero_jornada=jornada_actual
    ).all()

    lista_partidos = []
    for p in partidos_jornada:
        lista_partidos.append({
            "id_partido": p.id_partido,
            "equipo_local": p.equipo_local.nombre,
            "logo_local": p.equipo_local.url_logo if p.equipo_local.url_logo else "default_team.png",
            "equipo_visitante": p.equipo_visitante.nombre,
            "logo_visitante": p.equipo_visitante.url_logo if p.equipo_visitante.url_logo else "default_team.png",
            "goles_local": p.goles_local,
            "goles_visit": p.goles_visit,
            "estado": p.estado,
            "fecha": p.fecha.strftime("%d/%m/%Y %H:%M") if p.fecha else "Sin fecha"
        })

    # Ensamblamos y enviamos el JSON gigante
    return jsonify({
        "info": info_basica,
        "clasificacion": lista_clasificacion,
        "jornada_actual": jornada_actual,
        "partidos": lista_partidos
    }), 200