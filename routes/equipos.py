from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Equipo, Inscripcion, Partido, Pertenece, Torneo, Usuario, db
from datetime import datetime
import os
import uuid

equipos_bp = Blueprint('equipos', __name__)

# Ruta para obtener la lista de equipos a los que pertenece el usuario
@equipos_bp.route('/mis-equipos', methods=['GET'])
@jwt_required()
def get_mis_equipos():
    # 1. ¿Quién me está pidiendo los equipos?
    user_id = get_jwt_identity()

    # 2. Buscamos en la tabla intermedia todos los vínculos de este usuario
    mis_vinculos = Pertenece.query.filter_by(id_usuario=user_id).all()

    # 3. Preparamos la respuesta
    lista_equipos = []
    for vinculo in mis_vinculos:
        equipo = vinculo.equipo
        if equipo:
            lista_equipos.append({
                "id": equipo.id_equipo,
                "nombre": equipo.nombre,
                # Si es nulo, mandamos el por defecto
                "logo": equipo.url_logo if equipo.url_logo else "default_team.png",
                # ¡EL FIX! Convertimos ambos a string para compararlos
                "es_capitan": str(equipo.id_capitan) == str(user_id) 
            })
    # Devolvemos la lista al móvil
    return jsonify(lista_equipos), 200

# Ruta que nos da los detalles del equipo seleccionado
@equipos_bp.route('/<int:id_equipo>', methods=['GET'])
@jwt_required()
def get_detalle_equipo(id_equipo):
    user_id = get_jwt_identity()
    equipo = Equipo.query.get_or_404(id_equipo)

    # 1. Buscar el PRÓXIMO partido (el primero cuya fecha sea hoy o futura)
    proximo_p = Partido.query.filter(
        ((Partido.id_local == id_equipo) | (Partido.id_visitante == id_equipo)),
        # Partido.fecha >= datetime.now(), # Descomenta esto cuando tengas fechas reales
        Partido.estado == 'Pendiente'
    ).order_by(Partido.fecha.asc()).first()

    info_partido = None
    if proximo_p:
        # Determinar quién es el rival
        es_local = proximo_p.id_local == id_equipo
        id_rival = proximo_p.id_visitante if es_local else proximo_p.id_local
        
        # 2. Buscamos los objetos reales por su ID
        rival = Equipo.query.get(id_rival)
        torneo_partido = Torneo.query.get(proximo_p.id_torneo)
        
        info_partido = {
            "rival_nombre": rival.nombre if rival else "Desconocido",
            "rival_logo": rival.url_logo if (rival and rival.url_logo) else "default_team.png",
            "torneo_nombre": torneo_partido.nombre if torneo_partido else "Desconocido",
            "fecha": proximo_p.fecha.strftime("%d/%m/%Y %H:%M")
        }

    # 2. Torneos en los que está inscrito (NUEVO MÉTODO LIMPIO)
    inscripciones = Inscripcion.query.filter_by(id_equipo=id_equipo).all()
    lista_torneos = [{"id": ins.torneo.id_torneo, 
                      "nombre": ins.torneo.nombre, 
                      "logo": ins.torneo.url_logo if ins.torneo.url_logo else "default_torneo.png"} for ins in inscripciones if ins.torneo]

    # 3. Jugadores del equipo (La Plantilla)
    # Buscamos en la tabla Pertenece todos los registros de este equipo
    vinculos_jugadores = Pertenece.query.filter_by(id_equipo=id_equipo).all()
    lista_jugadores = []
    
    for v in vinculos_jugadores:
        jugador = v.usuario
        if jugador:
            lista_jugadores.append({
                "id": jugador.id_usuario,
                # Podemos mostrar el username (ej. @zorin) o el nombre real
                "nombre": f"@{jugador.username}", 
                "logo": jugador.imagen_perfil if jugador.imagen_perfil else "default_profile.png"
            })

    # Ahora actualiza el return para incluir "jugadores"
    return jsonify({
        "id": equipo.id_equipo,
        "nombre": equipo.nombre,
        "logo": equipo.url_logo if equipo.url_logo else "default_team.png",
        "es_capitan": str(equipo.id_capitan) == str(user_id),
        "proximo_partido": info_partido,
        "torneos": lista_torneos,
        "jugadores": lista_jugadores, # ¡NUEVO CAMPO!
        "palmares": []
    }), 200

# Ruta para crear un nuevo equipo (con logo opcional)
@equipos_bp.route('/crear', methods=['POST'])
@jwt_required()
def crear_equipo():
    user_id = get_jwt_identity()
    
    # En peticiones Multipart, los textos vienen en request.form
    nombre = request.form.get('nombre')

    if not nombre:
        return jsonify({"error": "El nombre del equipo es obligatorio"}), 400

    logo_filename = "default_team.png" # Valor por defecto

    # Comprobamos si nos han enviado un archivo llamado 'logo'
    if 'logo' in request.files:
        file = request.files['logo']
        if file and file.filename != '':
            # Generamos un nombre único para que no se sobrescriban imágenes
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
            logo_filename = f"{uuid.uuid4().hex}.{ext}"
            
            # Guardamos la imagen físicamente en el servidor
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER_EQUIPOS'], logo_filename)
            file.save(filepath)

    # 1. Creamos el equipo (el creador es el capitán)
    nuevo_equipo = Equipo(
        nombre=nombre, 
        url_logo=logo_filename, 
        id_capitan=user_id
    )
    db.session.add(nuevo_equipo)
    db.session.flush() # Guardamos temporalmente para que se genere el ID del equipo

    # 2. Vinculamos al creador a la tabla Pertenece para que sea jugador
    vinculo = Pertenece(id_usuario=user_id, id_equipo=nuevo_equipo.id_equipo)
    db.session.add(vinculo)
    
    # 3. Guardamos todo de forma definitiva
    db.session.commit()

    # Devolvemos el mismo formato que usa tu lista para poder añadirlo directamente
    return jsonify({
        "id": nuevo_equipo.id_equipo,
        "nombre": nuevo_equipo.nombre,
        "logo": nuevo_equipo.url_logo,
        "es_capitan": True
    }), 201

# Ruta para que el capitán añada jugadores a su equipo
@equipos_bp.route('/<int:id_equipo>/anadir-jugador', methods=['POST'])
@jwt_required()
def anadir_jugador(id_equipo):
    capitan_id = get_jwt_identity()
    data = request.get_json()
    username_objetivo = data.get('username')

    # 1. Verificar que el equipo existe y que quien pide es el capitán
    equipo = Equipo.query.get_or_404(id_equipo)
    if str(equipo.id_capitan) != str(capitan_id):
        return jsonify({"error": "Solo el capitán puede añadir jugadores"}), 403

    # 2. Buscar al usuario por username
    usuario_a_anadir = Usuario.query.filter_by(username=username_objetivo).first()
    if not usuario_a_anadir:
        return jsonify({"error": f"El usuario @{username_objetivo} no existe"}), 404

    # 3. Verificar si ya pertenece al equipo
    ya_pertenece = Pertenece.query.filter_by(
        id_usuario=usuario_a_anadir.id_usuario, 
        id_equipo=id_equipo
    ).first()
    
    if ya_pertenece:
        return jsonify({"error": "Este jugador ya está en tu equipo"}), 400

    # 4. Crear el vínculo
    nuevo_miembro = Pertenece(
        id_usuario=usuario_a_anadir.id_usuario, 
        id_equipo=id_equipo
    )
    db.session.add(nuevo_miembro)
    db.session.commit()

    return jsonify({"msg": f"@{username_objetivo} ha sido añadido con éxito"}), 201

# Ruta para que el capitán expulse jugadores de su equipo
@equipos_bp.route('/<int:id_equipo>/expulsar/<int:id_jugador>', methods=['DELETE'])
@jwt_required()
def expulsar_jugador(id_equipo, id_jugador):
    user_id = int(get_jwt_identity())
    equipo = Equipo.query.get_or_404(id_equipo)
    
    # 1. Seguridad: Solo el capitán puede expulsar
    if equipo.id_capitan != user_id:
        return jsonify({"error": "Solo el capitán puede expulsar jugadores"}), 403
        
    # 2. Seguridad: No puedes expulsarte a ti mismo (para eso haremos otra ruta)
    if user_id == id_jugador:
        return jsonify({"error": "No puedes expulsarte a ti mismo de esta forma."}), 400
        
    # 3. Buscar el vínculo y eliminarlo
    vinculo = Pertenece.query.filter_by(id_equipo=id_equipo, id_usuario=id_jugador).first()
    if not vinculo:
        return jsonify({"error": "El jugador no pertenece a este equipo"}), 404
        
    db.session.delete(vinculo)
    db.session.commit()
    
    return jsonify({"msg": "Jugador expulsado con éxito"}), 200


# 1. SALIR DEL EQUIPO (Jugador Normal)
@equipos_bp.route('/<int:id_equipo>/salir', methods=['DELETE'])
@jwt_required()
def salir_equipo(id_equipo):
    user_id = int(get_jwt_identity())
    equipo = Equipo.query.get_or_404(id_equipo)
    
    if equipo.id_capitan == user_id:
        return jsonify({"error": "Como capitán, debes 'Disolver' el equipo, no puedes simplemente salir."}), 400
        
    vinculo = Pertenece.query.filter_by(id_equipo=id_equipo, id_usuario=user_id).first()
    if not vinculo:
        return jsonify({"error": "No estás en este equipo"}), 404
        
    db.session.delete(vinculo)
    db.session.commit()
    return jsonify({"msg": "Has salido del equipo correctamente"}), 200

# 2. DISOLVER EQUIPO (Capitán)
@equipos_bp.route('/<int:id_equipo>/disolver', methods=['DELETE'])
@jwt_required()
def disolver_equipo(id_equipo):
    user_id = int(get_jwt_identity())
    equipo = Equipo.query.get_or_404(id_equipo)
    
    if equipo.id_capitan != user_id:
        return jsonify({"error": "Solo el capitán puede disolver el equipo"}), 403
        
    # Limpiamos primero las tablas hijas para evitar errores SQL
    Pertenece.query.filter_by(id_equipo=id_equipo).delete()
    Inscripcion.query.filter_by(id_equipo=id_equipo).delete()
    
    db.session.delete(equipo)
    db.session.commit()
    return jsonify({"msg": "Equipo disuelto para siempre"}), 200

# 3. EDITAR EQUIPO (Capitán)
@equipos_bp.route('/<int:id_equipo>/editar', methods=['PUT'])
@jwt_required()
def editar_equipo(id_equipo):
    user_id = int(get_jwt_identity())
    equipo = Equipo.query.get_or_404(id_equipo)
    
    if equipo.id_capitan != user_id:
        return jsonify({"error": "Solo el capitán puede editar el equipo"}), 403

    nombre = request.form.get('nombre')
    if nombre: equipo.nombre = nombre

    if 'logo' in request.files:
        file = request.files['logo']
        if file and file.filename != '':
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
            nuevo_nombre = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join('uploads/equipos', nuevo_nombre)
            file.save(filepath)
            equipo.url_logo = nuevo_nombre

    db.session.commit()
    return jsonify({"msg": "Equipo actualizado correctamente"}), 200