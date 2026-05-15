from flask import jsonify, request
from models import Usuario
from extensions import bcrypt
from flask_jwt_extended import create_access_token
from services.usuario_service import UsuarioService
from extensions import db

class AuthController:

    @staticmethod
    def register():
        data = request.form
        imagen = request.files.get('imagen_perfil')

        # Validaciones de existencia
        if Usuario.query.filter_by(email=data.get('email')).first() or \
           Usuario.query.filter_by(username=data.get('username')).first():
            return jsonify({"error": "Email o username ya en uso"}), 400

        try:
            UsuarioService.registrar_usuario(data, imagen)
            db.session.commit()
            return jsonify({"mensaje": "Usuario registrado con éxito"}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def login():
        data = request.get_json()
        usuario = Usuario.query.filter_by(email=data.get('email')).first()

        if usuario and bcrypt.check_password_hash(usuario.password, data.get('password')):
            access_token = create_access_token(
                identity=str(usuario.id_usuario), 
                additional_claims={"rol": usuario.rol}
            )
            return jsonify({
                "mensaje": "Login exitoso",
                "token": access_token,
                "rol": usuario.rol,
                "id_usuario": usuario.id_usuario
            }), 200
        
        return jsonify({"error": "Email o contraseña incorrectos"}), 401