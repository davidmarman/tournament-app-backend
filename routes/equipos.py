from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Equipo, Inscripcion, Palmares, Partido, Pertenece, Torneo, Usuario, db
from datetime import datetime
import os
import uuid
from controllers.equipos_controller import EquiposController

equipos_bp = Blueprint('equipos', __name__)

# Ruta para obtener la lista de equipos a los que pertenece el usuario
@equipos_bp.route('/mis-equipos', methods=['GET'])
@jwt_required()
def get_mis_equipos():
    return EquiposController.get_mis_equipos(get_jwt_identity())

# Ruta que nos da los detalles del equipo seleccionado
@equipos_bp.route('/<int:id_equipo>', methods=['GET'])
@jwt_required()
def get_detalle_equipo(id_equipo):
    return EquiposController.get_detalle(id_equipo, get_jwt_identity())

# Ruta para crear un nuevo equipo (con logo opcional)
@equipos_bp.route('/crear', methods=['POST'])
@jwt_required()
def crear_equipo():
    return EquiposController.crear(int(get_jwt_identity()))

# Ruta para que el capitán añada jugadores a su equipo
@equipos_bp.route('/<int:id_equipo>/anadir-jugador', methods=['POST'])
@jwt_required()
def anadir_jugador(id_equipo):
    return EquiposController.anadir_jugador(id_equipo, int(get_jwt_identity()))

# Ruta para que el capitán expulse jugadores de su equipo
@equipos_bp.route('/<int:id_equipo>/expulsar/<int:id_jugador>', methods=['DELETE'])
@jwt_required()
def expulsar_jugador(id_equipo, id_jugador):
    return EquiposController.expulsar(id_equipo, id_jugador, int(get_jwt_identity()))

# Ruta para salir del equipo (Jugador Normal)
@equipos_bp.route('/<int:id_equipo>/salir', methods=['DELETE'])
@jwt_required()
def salir_equipo(id_equipo):
    return EquiposController.salir(id_equipo, int(get_jwt_identity()))

# Ruta para disolver equipo (Capitán)
@equipos_bp.route('/<int:id_equipo>/disolver', methods=['DELETE'])
@jwt_required()
def disolver_equipo(id_equipo):
    return EquiposController.disolver(id_equipo, int(get_jwt_identity()))

# Ruta para editar equipo (Capitán)
@equipos_bp.route('/<int:id_equipo>/editar', methods=['PUT'])
@jwt_required()
def editar_equipo(id_equipo):
    return EquiposController.editar(id_equipo, int(get_jwt_identity()))


# Ruta para ceder la capitania de un equipo a otro jugador
@equipos_bp.route('/<int:id_equipo>/ceder-capitania', methods=['POST'])
@jwt_required()
def ceder_capitania(id_equipo):
    return EquiposController.ceder_capitania(id_equipo, int(get_jwt_identity()))

