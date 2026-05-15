from flask import Blueprint
from flask_jwt_extended import jwt_required
from controllers.partidos_controller import PartidosController

partidos_bp = Blueprint('partidos', __name__)

@partidos_bp.route('/mis-proximos', methods=['GET'])
@jwt_required()
def get_mis_proximos_partidos():
    return PartidosController.get_proximos_partidos()

@partidos_bp.route('/<int:id_partido>/acta', methods=['GET'])
@jwt_required()
def get_acta_partido(id_partido):
    return PartidosController.get_acta(id_partido)

@partidos_bp.route('/<int:id_partido>/finalizar', methods=['POST'])
@jwt_required()
def finalizar_partido(id_partido):
    return PartidosController.finalizar_partido(id_partido)