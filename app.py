# app.py
from flask import Flask, jsonify, send_from_directory
from extensions import db, migrate, bcrypt, jwt
import os
import models

def create_app():
    app = Flask(__name__)
    
    # Configuración básica
    # Ruta para base de datos en MySql: mysql+pymsql://usuario:contraseña@servidor/nombre_base_datos
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://flask_user:rayo7enero@localhost/tournament_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config["JWT_SECRET_KEY"] = "super-secreta-clave-para-torneos" # Cambiaremos esto luego

    # Configuración para subir imágenes 
    # Donde se guardarán las imágenes de perfil
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads/perfiles')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Asegura que la carpeta exista
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    # Inicializamos extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)


    # Registro del blueprint de autenticacion
    from routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    # Registro del blueprint de partidos
    from routes.partidos import partidos_bp
    app.register_blueprint(partidos_bp, url_prefix='/api/partidos')

    # Ruta para servir imágenes de perfil
    @app.route('/uploads/perfiles/<filename>')
    def obtener_perfil_image(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Ruta de prueba para verificar que el servidor levanta
    @app.route('/')
    def index():
        return jsonify({"mensaje": "¡TournamentApp API funcionando perfectamente!"})

    return app

# Arrancamos la app
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)