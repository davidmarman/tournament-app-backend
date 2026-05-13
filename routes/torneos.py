import datetime as dt
import os
import uuid

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Administra, Palmares, StatsJugador, Torneo, Equipo, Inscripcion, Usuario, Partido, Clasificacion, db

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

    # Miramos si el front nos pide alguna jornada especifica
    jornada_solicitada = request.args.get('jornada', type=int)

    # Logica para calcular la jornada que toca jugar 
    siguiente_partido = Partido.query.filter_by(
        id_torneo=id_torneo, estado='Pendiente'
    ).order_by(Partido.numero_jornada.asc()).first()

    jornada_que_toca = siqguiente_partido.numero_jornada if siguiente_partido else 1

    # Si nos piden una jornada, usamos esa. Si no, la que toca.
    jornada_a_enviar = jornada_solicitada if jornada_solicitada else jornada_que_toca

    partidos_db = Partido.query.filter_by(
        id_torneo=id_torneo, numero_jornada=jornada_a_enviar
    ).all()

    lista_partidos = []
    for p in partidos_db:
        lista_partidos.append({
            "id_partido": p.id_partido,
            "equipo_local": p.equipo_local.nombre,
            "logo_local": p.equipo_local.url_logo or "default_team.png",
            "equipo_visitante": p.equipo_visitante.nombre,
            "logo_visitante": p.equipo_visitante.url_logo or "default_team.png",
            "goles_local": p.goles_local,
            "goles_visit": p.goles_visit,
            "estado": p.estado,
            "fecha": p.fecha.strftime("%d/%m/%Y %H:%M") if p.fecha else "Sin fecha"
        })

    # 4. RESPUESTA INTELIGENTE
    # Si jornada_solicitada existe, es que el usuario está navegando: enviamos SOLO partidos.
    if jornada_solicitada:
        return jsonify({
            "jornada_mostrada": jornada_a_enviar,
            "partidos": lista_partidos
        }), 200

    # Si NO hay jornada_solicitada, es la carga inicial: enviamos TODO.
    # Pero añadimos el campo "max_jornadas" para que Android sepa el límite.
    max_jornada = db.session.query(db.func.max(Partido.numero_jornada)).filter_by(id_torneo=id_torneo).scalar() or 1
    
    clasificaciones = Clasificacion.query.filter_by(id_torneo=id_torneo).order_by(Clasificacion.puntos.desc()).all()
    lista_clasificacion = [{
        "id_equipo": c.equipo.id_equipo,
        "nombre": c.equipo.nombre,
        "logo": c.equipo.url_logo or "default_team.png",
        "pts": (c.puntos or 0), "gf": (c.gf or 0), "gc": (c.gc or 0),
        "pj": (c.pj or 0), "pg": (c.pg or 0), "pe": (c.pe or 0), "pp": (c.pp or 0)
    } for c in clasificaciones]

    return jsonify({
        "info": {
            "id": torneo.id_torneo,
            "nombre": torneo.nombre,
            "logo": torneo.url_logo or "default_torneo.png",
            "descripcion": torneo.descripcion,
            "codigo": torneo.codigo_acceso,
            "estado": torneo.estado
        },
        "clasificacion": lista_clasificacion,
        "jornada_actual": jornada_que_toca,
        "max_jornadas": max_jornada,
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


# Ruta para la pantalla de administración del torneo (solo Admin)
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

# Ruta para eliminar un torneo (solo Admin)
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


# Ruta para generar el calendario de partidos automáticamente (solo Admin)
@torneos_bp.route('/<int:id_torneo>/generar-calendario', methods=['POST'])
@jwt_required()
def generar_calendario(id_torneo):
    user_id = int(get_jwt_identity())
    
    # 1. Validaciones iniciales
    torneo = Torneo.query.get_or_404(id_torneo)
    es_admin = Administra.query.filter_by(id_usuario=user_id, id_torneo=id_torneo).first()
    
    if not es_admin:
        return jsonify({"error": "No tienes permiso para generar el calendario"}), 403

    # Comprobar si ya hay partidos (para no duplicar el calendario por accidente)
    if Partido.query.filter_by(id_torneo=id_torneo).first():
        return jsonify({"error": "El calendario ya ha sido generado previamente."}), 400

    # Obtener todos los equipos inscritos
    inscripciones = Inscripcion.query.filter_by(id_torneo=id_torneo).all()
    equipos = [ins.equipo for ins in inscripciones]

    if len(equipos) < 2:
        return jsonify({"error": "Se necesitan al menos 2 equipos inscritos para generar un calendario."}), 400

    # 2. ALGORITMO ROUND-ROBIN (Emparejamientos)
    if len(equipos) % 2 != 0:
        equipos.append(None) # Añadimos un "Fantasma" para el equipo que descansa en cada jornada

    n = len(equipos)
    partidos_generados = []

    # El algoritmo genera (n - 1) jornadas
    for jornada in range(1, n):
        for i in range(n // 2):
            local = equipos[i]
            visitante = equipos[n - 1 - i]
            
            # Si ninguno de los dos es el equipo fantasma, hay partido real
            if local is not None and visitante is not None:
                partidos_generados.append({
                    "jornada": jornada,
                    "id_local": local.id_equipo,
                    "id_visitante": visitante.id_equipo
                })
        
        # Rotar equipos (El índice 0 se queda fijo, los demás rotan como las agujas del reloj)
        equipos.insert(1, equipos.pop())

    # 3. ASIGNACIÓN DINÁMICA DE FECHAS Y HORAS
    # Convertimos el texto "Lunes,Martes" a números que Python entienda (Lunes=0, Domingo=6)
    dias_map = {"Lunes": 0, "Martes": 1, "Miercoles": 2, "Jueves": 3, "Viernes": 4, "Sabado": 5, "Domingo": 6}
    dias_permitidos = [dias_map[d.strip()] for d in torneo.dias_juego.split(",") if d.strip() in dias_map]
    
    # Lista de horarios ["16:00-17:00", "18:00-19:00"]
    horarios = [h.strip() for h in torneo.horarios_juego.split(",") if h.strip()]
    
    fecha_actual = torneo.fecha_inicio
    hora_idx = 0

    # Buscar el primer día en el calendario que coincida con los días permitidos
    while fecha_actual.weekday() not in dias_permitidos:
        fecha_actual += dt.timedelta(days=1)

    # 4. Guardado en Base de Datos
    for p_data in partidos_generados:
        # Extraer la hora de inicio del String (Ej: Coger "16:00" de "16:00-17:00")
        hora_str = horarios[hora_idx].split("-")[0]
        hora_obj = dt.datetime.strptime(hora_str, "%H:%M").time()
        
        # Combinamos el día actual con la hora exacta
        fecha_hora_partido = dt.datetime.combine(fecha_actual, hora_obj)

        nuevo_partido = Partido(
            id_torneo=id_torneo,
            id_local=p_data["id_local"],
            id_visitante=p_data["id_visitante"],
            numero_jornada=p_data["jornada"],
            fecha=fecha_hora_partido,
            estado="Pendiente"
        )
        db.session.add(nuevo_partido)

        # Avanzamos un hueco horario
        hora_idx += 1
        
        # Si ya hemos llenado todos los horarios de hoy, pasamos al siguiente día válido
        if hora_idx >= len(horarios):
            hora_idx = 0
            fecha_actual += dt.timedelta(days=1)
            while fecha_actual.weekday() not in dias_permitidos:
                fecha_actual += dt.timedelta(days=1)

    db.session.commit()
    return jsonify({"msg": f"¡Calendario generado con éxito! Se crearon {len(partidos_generados)} partidos."}), 201


# Ruta para finalizar un torneo y declarar un ganador (solo Admin)
@torneos_bp.route('/<int:id_torneo>/finalizar', methods=['POST'])
@jwt_required()
def finalizar_torneo(id_torneo):
    # 1. Verificar que el usuario sea Admin (puedes usar tu tabla Administra)
    torneo = Torneo.query.get_or_404(id_torneo)
    
    if torneo.estado == 'Finalizado':
        return jsonify({"msg": "Este torneo ya está finalizado"}), 400

    # 2. Obtener los 3 mejores de la Clasificación
    clasif = Clasificacion.query.filter_by(id_torneo=id_torneo).order_by(Clasificacion.puntos.desc(), Clasificacion.gf.desc()).all()
    
    logros = []
    if len(clasif) >= 1:
        logros.append(Palmares(id_torneo=id_torneo, id_equipo=clasif[0].id_equipo, tipo_logro='Campeon'))
    if len(clasif) >= 2:
        logros.append(Palmares(id_torneo=id_torneo, id_equipo=clasif[1].id_equipo, tipo_logro='Subcampeon'))
    if len(clasif) >= 3:
        logros.append(Palmares(id_torneo=id_torneo, id_equipo=clasif[2].id_equipo, tipo_logro='Tercero'))

    # 3. Obtener el Pichichi (Máximo goleador)
    pichichi = StatsJugador.query.filter_by(id_torneo=id_torneo).order_by(StatsJugador.goles.desc()).first()
    if pichichi and pichichi.goles > 0:
        logros.append(Palmares(id_torneo=id_torneo, id_usuario=pichichi.id_usuario, tipo_logro='Pichichi', valor_stats=pichichi.goles))

    # Obtenemos el jugador con mas amarillas
    mas_amarillas = StatsJugador.query.filter_by(id_torneo=id_torneo).order_by(StatsJugador.amarillas.desc()).first()
    if mas_amarillas and mas_amarillas.amarillas > 0:
        logros.append(Palmares(id_torneo=id_torneo, id_usuario=mas_amarillas.id_usuario, tipo_logro='Más Amarillas', valor_stats=mas_amarillas.amarillas))

    # Obtenemos el jugador con mas rojas
    mas_rojas = StatsJugador.query.filter_by(id_torneo=id_torneo).order_by(StatsJugador.rojas.desc()).first()
    if mas_rojas and mas_rojas.rojas > 0:
        logros.append(Palmares(id_torneo=id_torneo, id_usuario=mas_rojas.id_usuario, tipo_logro='Más Rojas', valor_stats=mas_rojas.rojas))

    # 4. Guardar todo y cerrar torneo
    torneo.estado = 'Finalizado'
    for logro in logros:
        db.session.add(logro)
    
    db.session.commit()
    return jsonify({"msg": "Torneo finalizado con éxito y palmarés generado"}), 200