from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Equipo, Inscripcion, Partido, Pertenece, Torneo, db
from datetime import datetime

equipos_bp = Blueprint('equipos', __name__)

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

    return jsonify({
        "id": equipo.id_equipo,
        "nombre": equipo.nombre,
        "logo": equipo.url_logo if equipo.url_logo else "default_team.png",
        "es_capitan": str(equipo.id_capitan) == str(user_id),
        "proximo_partido": info_partido,
        "torneos": lista_torneos,
        "palmares": []
    }), 200