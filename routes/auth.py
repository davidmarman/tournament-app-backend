from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import or_
from extensions import db, bcrypt
from models import Partido, Torneo, Usuario
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
import os
import time
from werkzeug.utils import secure_filename

# Creamos el Blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    # 1. Leemos el texto de request.form y el archivo de request.files
    data = request.form
    imagen = request.files.get('imagen_perfil')

    nombre = data.get('nombre')
    apellido = data.get('apellido')
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    rol = data.get('rol', 'User')

    # Validaciones básicas
    if not email or not password or not username:
        return jsonify({"error": "Faltan datos obligatorios"}), 400

    if Usuario.query.filter_by(email=email).first() or Usuario.query.filter_by(username=username).first():
        return jsonify({"error": "El email o el username ya están en uso"}), 400

    # 2. PROCESAMOS LA IMAGEN (Si el usuario ha enviado una)
    nombre_archivo = 'default.png' # Imagen por defecto
    
    if imagen and imagen.filename != '':
        # Limpiamos el nombre original del archivo por seguridad
        nombre_seguro = secure_filename(imagen.filename)
        # Le añadimos el timestamp (la hora actual) para que nunca haya dos fotos con el mismo nombre
        nombre_archivo = f"{int(time.time())}_{nombre_seguro}"
        
        # Guardamos el archivo físico en la carpeta que configuramos en app.py
        ruta_guardado = os.path.join(current_app.config['UPLOAD_FOLDER'], nombre_archivo)
        imagen.save(ruta_guardado)

    # 3. Guardamos en la base de datos (igual que antes)
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    nuevo_usuario = Usuario(
        nombre=nombre,
        apellido=apellido,
        username=username,
        email=email,
        password=hashed_password,
        rol=rol,
        imagen_perfil=nombre_archivo  # ¡Guardamos el nombre del archivo!
    )

    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify({"mensaje": "Usuario registrado con éxito"}), 201


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