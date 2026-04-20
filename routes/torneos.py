from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Torneo, Equipo, Inscripcion, db

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