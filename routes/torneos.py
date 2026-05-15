import datetime as dt
import os
import uuid
from controllers.torneos_controller import TorneosController
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Administra, Palmares, StatsJugador, Torneo, Equipo, Inscripcion, Usuario, Partido, Clasificacion, db

torneos_bp = Blueprint('torneos', __name__)

@torneos_bp.route('/inscribir', methods=['POST'])
@jwt_required()
def inscribir_equipo():
    return TorneosController.inscribir(get_jwt_identity())


@torneos_bp.route('/mis-torneos', methods=['GET'])
@jwt_required()
def get_mis_torneos():
    return TorneosController.get_mis_torneos(get_jwt_identity())

@torneos_bp.route('/<int:id_torneo>/detalle', methods=['GET'])
@jwt_required()
def get_detalle_torneo(id_torneo):
    return TorneosController.get_detalle(id_torneo)

@torneos_bp.route('/crear', methods=['POST'])
@jwt_required()
def crear_torneo():
    return TorneosController.crear(int(get_jwt_identity()))


# Ruta para la pantalla de administración del torneo (solo Admin)
@torneos_bp.route('/admin-dashboard', methods=['GET'])
@jwt_required()
def get_admin_dashboard():
    return TorneosController.get_admin_dashboard(int(get_jwt_identity()))

# Ruta para eliminar un torneo (solo Admin)
@torneos_bp.route('/<int:id_torneo>', methods=['DELETE'])
@jwt_required()
def eliminar_torneo(id_torneo):
    return TorneosController.eliminar(id_torneo, int(get_jwt_identity()))


# Ruta para generar el calendario de partidos automáticamente (solo Admin)
@torneos_bp.route('/<int:id_torneo>/generar-calendario', methods=['POST'])
@jwt_required()
def generar_calendario(id_torneo):
    return TorneosController.generar_calendario(id_torneo, int(get_jwt_identity()))


# Ruta para finalizar un torneo y declarar un ganador (solo Admin)
@torneos_bp.route('/<int:id_torneo>/finalizar', methods=['POST'])
@jwt_required()
def finalizar_torneo(id_torneo):
    return TorneosController.finalizar(id_torneo, int(get_jwt_identity()))