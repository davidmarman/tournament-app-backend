from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity
from models import db, Usuario
from services.usuario_service import UsuarioService

class UsuariosController:

    @staticmethod
    def get_perfil(user_id_param):
        # Si no viene ID en la URL, usamos el del Token (nuestro perfil)
        if user_id_param is None:
            current_user_id = int(get_jwt_identity())
        else:
            current_user_id = user_id_param

        data = UsuarioService.obtener_perfil_data(current_user_id)
        if not data:
            return jsonify({"error": "Usuario no encontrado"}), 404

        return jsonify(data), 200

    @staticmethod
    def editar_perfil():
        user_id = int(get_jwt_identity())
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404

        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        file = request.files.get('imagen_perfil')

        UsuarioService.actualizar_perfil(usuario, nombre, apellido, file)
        db.session.commit()

        return jsonify({
            "msg": "Perfil actualizado",
            "usuario": {"nombre": usuario.nombre, "apellido": usuario.apellido, "imagen": usuario.imagen_perfil}
        }), 200