import datetime as dt
import os
import uuid

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Administra, Torneo, Equipo, Inscripcion, Usuario, Partido, Clasificacion, db

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

    # 5. ¡NUEVO! Añadirlo a la tabla de clasificación con 0 puntos
    # (Solo si es formato Liga, si en el futuro haces formato "Copa" esto no haría falta)
    if torneo.tipo == "Liga":
        nueva_clasif = Clasificacion(
            id_torneo=torneo.id_torneo,
            id_equipo=id_equipo,
            puntos=0,
            pj=0, pg=0, pe=0, pp=0
        )
        db.session.add(nueva_clasif)

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
        "descripcion": torneo.descripcion or "Sin descripción disponible.",
        "codigo": torneo.codigo_acceso 
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

# Ruta para crear Torneos (solo Admin)
@torneos_bp.route('/crear', methods=['POST'])
@jwt_required()
def crear_torneo():
    user_id = int(get_jwt_identity())
    
    # 1. Obtener datos básicos del formulario (Multipart)
    nombre = request.form.get('nombre')
    tipo = request.form.get('tipo', 'Liga') # Por defecto 'Liga'
    descripcion = request.form.get('descripcion', '')
    
    # Datos para el calendario dinámico
    fecha_inicio_str = request.form.get('fecha_inicio')
    dias_juego = request.form.get('dias_juego') # Ej: "Sabado,Domingo"
    horarios_juego = request.form.get('horarios_juego') # Ej: "16:00-17:00,18:00-19:00"

    if not nombre:
        return jsonify({"error": "El nombre del torneo es obligatorio"}), 400

    # 2. Procesar la fecha_inicio (Android nos la mandará en formato YYYY-MM-DD)
    fecha_inicio = None
    if fecha_inicio_str:
        try:
            fecha_inicio = dt.datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Formato de fecha inválido. Usa YYYY-MM-DD"}), 400

    # 3. Generar un código de acceso único (Ej: TRN-8F4A2B)
    codigo_acceso = f"TRN-{uuid.uuid4().hex[:6].upper()}"

    # 4. Construir el objeto Torneo
    nuevo_torneo = Torneo(
        nombre=nombre,
        tipo=tipo,
        descripcion=descripcion,
        codigo_acceso=codigo_acceso,
        fecha_inicio=fecha_inicio,
        dias_juego=dias_juego,
        horarios_juego=horarios_juego
    )

    # 5. Procesar la subida del Logo (si existe)
    if 'logo' in request.files:
        file = request.files['logo']
        if file and file.filename != '':
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
            nuevo_nombre_logo = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join('uploads/torneos', nuevo_nombre_logo)
            
            # Asegurarse de que la carpeta uploads/torneos existe
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            nuevo_torneo.url_logo = nuevo_nombre_logo

    # 6. Guardar en Base de Datos
    db.session.add(nuevo_torneo)
    
    # MAGIC TRICK: Hacemos un "flush" en lugar de un "commit". 
    # Esto asigna un ID real (nuevo_torneo.id_torneo) sin cerrar aún la transacción.
    db.session.flush() 

    # 7. Crear el vínculo como Administrador
    nuevo_admin = Administra(
        id_usuario=user_id,
        id_torneo=nuevo_torneo.id_torneo
    )
    db.session.add(nuevo_admin)

    # Ahora sí, guardamos el Torneo y el Admin al mismo tiempo
    db.session.commit()

    return jsonify({
        "msg": "Torneo creado con éxito",
        "torneo": {
            "id_torneo": nuevo_torneo.id_torneo,
            "nombre": nuevo_torneo.nombre,
            "codigo_acceso": nuevo_torneo.codigo_acceso
        }
    }), 201

@torneos_bp.route('/admin-dashboard', methods=['GET'])
@jwt_required()
def get_admin_dashboard():
    user_id = int(get_jwt_identity())
    
    admin_links = Administra.query.filter_by(id_usuario=user_id).all()
    ids_torneos = [link.id_torneo for link in admin_links]

    torneos_data = []
    partidos_data = []

    if ids_torneos:
        torneos = Torneo.query.filter(Torneo.id_torneo.in_(ids_torneos)).all()
        for t in torneos:
            torneos_data.append({
                "id": t.id_torneo,
                "nombre": t.nombre,
                "logo": t.url_logo if t.url_logo else "default_torneo.png",
                "codigo": t.codigo_acceso # El código secreto
            })

        partidos = Partido.query.filter(
            Partido.id_torneo.in_(ids_torneos),
            Partido.estado.in_(['Pendiente', 'En Juego'])
        ).order_by(Partido.fecha.asc()).limit(15).all()

        for p in partidos:
            partidos_data.append({
                "id_partido": p.id_partido,
                "torneo_nombre": p.torneo.nombre,
                "equipo_local": p.equipo_local.nombre,
                "logo_local": p.equipo_local.url_logo if p.equipo_local.url_logo else "default_team.png",
                "equipo_visitante": p.equipo_visitante.nombre,
                "logo_visitante": p.equipo_visitante.url_logo if p.equipo_visitante.url_logo else "default_team.png",
                "fecha": p.fecha.strftime("%d/%m/%Y %H:%M") if p.fecha else "Sin fecha",
                "estado": p.estado
            })

    return jsonify({
        "torneos": torneos_data,
        "proximos_partidos": partidos_data
    }), 200


@torneos_bp.route('/<int:id_torneo>', methods=['DELETE'])
@jwt_required()
def eliminar_torneo(id_torneo):
    user_id = int(get_jwt_identity())
    
    # 1. Verificar que el torneo existe
    torneo = Torneo.query.get_or_404(id_torneo)
    
    # 2. Verificar que el usuario es el administrador de este torneo
    es_admin = Administra.query.filter_by(id_usuario=user_id, id_torneo=id_torneo).first()
    if not es_admin:
        return jsonify({"error": "No tienes permiso para borrar este torneo"}), 403

    # 3. Limpiar datos relacionados (Orden crítico)
    try:
        # Borrar registros en Clasificacion
        Clasificacion.query.filter_by(id_torneo=id_torneo).delete()
        # Borrar registros en Inscripcion
        Inscripcion.query.filter_by(id_torneo=id_torneo).delete()
        # Borrar registros en Partido
        Partido.query.filter_by(id_torneo=id_torneo).delete()
        # Borrar el vínculo de administración
        Administra.query.filter_by(id_torneo=id_torneo).delete()
        
        # Por último, borrar el torneo
        db.session.delete(torneo)
        db.session.commit()
        
        return jsonify({"msg": "Torneo eliminado correctamente"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error al eliminar: {str(e)}"}), 500

        