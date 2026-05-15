import os
import uuid
from flask import current_app
from models import db, Equipo, Pertenece, Partido, Torneo, Inscripcion, Palmares

class EquipoService:

    @staticmethod
    def obtener_equipos_usuario(user_id):
        mis_vinculos = Pertenece.query.filter_by(id_usuario=user_id).all()
        return [{
            "id": v.equipo.id_equipo,
            "nombre": v.equipo.nombre,
            "logo": v.equipo.url_logo or "default_team.png",
            "es_capitan": str(v.equipo.id_capitan) == str(user_id)
        } for v in mis_vinculos if v.equipo]

    @staticmethod
    def obtener_proximo_partido(id_equipo):
        proximo = Partido.query.filter(
            ((Partido.id_local == id_equipo) | (Partido.id_visitante == id_equipo)),
            Partido.estado == 'Pendiente'
        ).order_by(Partido.fecha.asc()).first()

        if not proximo:
            return None

        id_rival = proximo.id_visitante if proximo.id_local == id_equipo else proximo.id_local
        rival = Equipo.query.get(id_rival)
        
        return {
            "rival_nombre": rival.nombre if rival else "Desconocido",
            "rival_logo": rival.url_logo or "default_team.png",
            "torneo_nombre": proximo.torneo.nombre if proximo.torneo else "Desconocido",
            "fecha": proximo.fecha.strftime("%d/%m/%Y %H:%M")
        }

    @staticmethod
    def obtener_plantilla(id_equipo):
        vinculos = Pertenece.query.filter_by(id_equipo=id_equipo).all()
        return [{
            "id": v.usuario.id_usuario,
            "nombre": f"@{v.usuario.username}",
            "logo": v.usuario.imagen_perfil or "default_profile.png"
        } for v in vinculos if v.usuario]

    @staticmethod
    def obtener_palmares(id_equipo):
        trofeos = Palmares.query.filter_by(id_equipo=id_equipo).all()
        return [{
            "id_palmares": t.id_palmares,
            "torneo_nombre": t.torneo.nombre,
            "tipo_logro": t.tipo_logro,
            "fecha_logro": t.fecha_logro.strftime("%Y")
        } for t in trofeos]
    
    @staticmethod
    def guardar_logo_equipo(file):
        """Genera un nombre único y guarda el archivo del logo."""
        if file and file.filename != '':
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join('uploads/equipos', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            return filename
        return "default_team.png"

    @staticmethod
    def crear_equipo(nombre, id_capitan, logo_file):
        logo_filename = EquipoService.guardar_logo_equipo(logo_file) if logo_file else "default_team.png"
        
        nuevo_equipo = Equipo(nombre=nombre, url_logo=logo_filename, id_capitan=id_capitan)
        db.session.add(nuevo_equipo)
        db.session.flush()

        vinculo = Pertenece(id_usuario=id_capitan, id_equipo=nuevo_equipo.id_equipo)
        db.session.add(vinculo)
        return nuevo_equipo

    @staticmethod
    def disolver_equipo_completo(equipo):
        Pertenece.query.filter_by(id_equipo=equipo.id_equipo).delete()
        Inscripcion.query.filter_by(id_equipo=equipo.id_equipo).delete()
        db.session.delete(equipo)