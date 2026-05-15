from flask import Blueprint
from flask_jwt_extended import jwt_required
from controllers.usuarios_controller import UsuariosController

usuario_bp = Blueprint('usuario', __name__)

@usuario_bp.route('/perfil', defaults={'user_id': None}, methods=['GET'])
@usuario_bp.route('/perfil/<int:user_id>', methods=['GET'])
@jwt_required()
def get_perfil_completo(user_id):
    return UsuariosController.get_perfil(user_id)

@usuario_bp.route('/editar', methods=['PUT'])
@jwt_required()
def editar_perfil():
    return UsuariosController.editar_perfil()