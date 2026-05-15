from extensions import db, bcrypt
from flask import current_app
from werkzeug.utils import secure_filename
import time
import os
import uuid
from models import db, Usuario, Inscripcion, Palmares

class UsuarioService:

    @staticmethod
    def registrar_usuario(data, imagen):
        # 1. Procesar imagen
        nombre_archivo = 'default.png'
        if imagen and imagen.filename != '':
            nombre_seguro = secure_filename(imagen.filename)
            nombre_archivo = f"{int(time.time())}_{nombre_seguro}"
            ruta_guardado = os.path.join(current_app.config['UPLOAD_FOLDER_PERFILES'], nombre_archivo)
            os.makedirs(os.path.dirname(ruta_guardado), exist_ok=True)
            imagen.save(ruta_guardado)

        # 2. Hashear password y crear objeto
        hashed_pw = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
        nuevo_usuario = Usuario(
            nombre=data.get('nombre'),
            apellido=data.get('apellido'),
            username=data.get('username'),
            email=data.get('email'),
            password=hashed_pw,
            rol=data.get('rol', 'User'),
            imagen_perfil=nombre_archivo
        )

        db.session.add(nuevo_usuario)
        return nuevo_usuario

    @staticmethod
    def obtener_perfil_data(user_id):
        u = Usuario.query.get(user_id)
        if not u:
            return None

        # 1. Equipos
        equipos = []
        ids_equipos = []
        for vinculo in u.equipos:
            if vinculo.equipo:
                equipos.append({
                    "id": vinculo.equipo.id_equipo, 
                    "nombre": vinculo.equipo.nombre, 
                    "logo": vinculo.equipo.url_logo or "default_team.png",
                    "idCapitan": vinculo.equipo.id_capitan
                })
                ids_equipos.append(vinculo.equipo.id_equipo)

        # 2. Torneos (evitando repetidos)
        torneos_dict = {}
        if ids_equipos:
            inscripciones = Inscripcion.query.filter(Inscripcion.id_equipo.in_(ids_equipos)).all()
            for ins in inscripciones:
                t = ins.torneo
                if t and t.id_torneo not in torneos_dict:
                    torneos_dict[t.id_torneo] = {
                        "id": t.id_torneo, 
                        "nombre": t.nombre, 
                        "logo": t.url_logo or "default_torneo.png"
                    }

        # 3. Palmarés Mixto
        palmares_lista = []
        # Individuales
        logros_ind = Palmares.query.filter_by(id_usuario=user_id).all()
        for p in logros_ind:
            palmares_lista.append({
                "id_palmares": p.id_palmares, "tipo_logro": p.tipo_logro,
                "torneo_nombre": p.torneo.nombre, "fecha_logro": p.fecha_logro.strftime("%Y"),
                "es_individual": True
            })
        # De equipo
        if ids_equipos:
            logros_eq = Palmares.query.filter(Palmares.id_equipo.in_(ids_equipos)).all()
            for p in logros_eq:
                palmares_lista.append({
                    "id_palmares": p.id_palmares, "tipo_logro": p.tipo_logro,
                    "torneo_nombre": f"{p.torneo.nombre} (con {p.equipo.nombre})",
                    "fecha_logro": p.fecha_logro.strftime("%Y"), "es_individual": False
                })

        # 4. Estadísticas sumadas
        stats = {
            "goles": sum([s.goles for s in u.estadisticas]) if u.estadisticas else 0,
            "amarillas": sum([s.amarillas for s in u.estadisticas]) if u.estadisticas else 0,
            "rojas": sum([s.rojas for s in u.estadisticas]) if u.estadisticas else 0
        }

        return {
            "id": u.id_usuario, "nombre": u.nombre, "apellido": u.apellido,
            "username": u.username, "imagen": u.imagen_perfil,
            "equipos": equipos, "torneos": list(torneos_dict.values()),
            "palmares": palmares_lista, "stats": stats
        }

    @staticmethod
    def actualizar_perfil(usuario, nombre, apellido, file):
        if nombre: usuario.nombre = nombre
        if apellido: usuario.apellido = apellido

        if file and file.filename != '':
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
            nuevo_nombre = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join('uploads/perfiles', nuevo_nombre)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            usuario.imagen_perfil = nuevo_nombre
        
        return usuario