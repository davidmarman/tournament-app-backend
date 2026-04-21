import uuid

from flask import Blueprint, jsonify, request
import os
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Usuario, Inscripcion, db 

usuario_bp = Blueprint('usuario', __name__)

@usuario_bp.route('/perfil', defaults={'user_id': None}, methods=['GET'])
@usuario_bp.route('/perfil/<int:user_id>', methods=['GET'])
@jwt_required()
def get_perfil_completo(user_id):
    if user_id is None:
        identity = get_jwt_identity()
        current_user_id = int(identity)
    else:
        current_user_id = user_id

    u = Usuario.query.get(current_user_id)
    
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
        "id": u.id_usuario,
        "nombre": f"{u.nombre}",
        "apellido": f"{u.apellido}",
        "username": f"{u.username}",
        "imagen": u.imagen_perfil,
        "equipos": equipos,
        "torneos": torneos,
        "stats": {"goles": goles, "faltas": faltas}
    }), 200


@usuario_bp.route('/editar', methods=['PUT'])
@jwt_required()
def editar_perfil():
    user_id = get_jwt_identity()
    usuario = Usuario.query.get(user_id)
    
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # 1. Obtener datos de texto
    nombre = request.form.get('nombre')
    apellido = request.form.get('apellido')

    if nombre: usuario.nombre = nombre
    if apellido: usuario.apellido = apellido

    # 2. Obtener imagen si existe (Usando tu lógica de UUID)
    if 'imagen_perfil' in request.files:
        file = request.files['imagen_perfil']
        if file and file.filename != '':
            # Generamos un nombre único
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
            nuevo_nombre = f"{uuid.uuid4().hex}.{ext}"
            
            # Guardamos la imagen físicamente (asegúrate de que la ruta coincida con tu config)
            filepath = os.path.join('uploads/perfiles', nuevo_nombre)
            file.save(filepath)
            usuario.imagen_perfil = nuevo_nombre

    db.session.commit()

    return jsonify({
        "msg": "Perfil actualizado con éxito",
        "usuario": {
            "nombre": usuario.nombre,
            "apellido": usuario.apellido,
            "imagen_perfil": usuario.imagen_perfil
        }
    }), 200