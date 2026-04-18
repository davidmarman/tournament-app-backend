from flask import Blueprint, request, jsonify
from extensions import db, bcrypt
from models import Usuario
from flask_jwt_extended import create_access_token

# Creamos el Blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    # Recibimos los datos en formato JSON desde Android
    data = request.get_json()

    # Comprobamos si el email ya existe
    if Usuario.query.filter_by(email=data.get('email')).first():
        return jsonify({"error": "El email ya está registrado"}), 400
    
    if Usuario.query.filter_by(username=data.get('username')).first():
        return jsonify({"error": "El username ya está registrado"}), 400

    # Encriptamos la contraseña
    hashed_password = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')

    # Creamos el nuevo usuario
    nuevo_usuario = Usuario(
        nombre=data.get('nombre'),
        apellido=data.get('apellido'),
        username=data.get('username'),
        email=data.get('email'),
        password=hashed_password,
        rol=data.get('rol', 'User') # Por defecto será 'User' si no nos envían nada
    )

    # Guardamos en la base de datos
    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify({"mensaje": "Usuario registrado exitosamente"}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # Buscamos al usuario por email
    usuario = Usuario.query.filter_by(email=data.get('email')).first()

    # Verificamos que existe y que la contraseña coincide
    if usuario and bcrypt.check_password_hash(usuario.password, data.get('password')):
        # Creamos el token de seguridad (JWT)
        # Metemos el id y el rol en el token para usarlos luego en Android
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
    else:
        return jsonify({"error": "Email o contraseña incorrectos"}), 401