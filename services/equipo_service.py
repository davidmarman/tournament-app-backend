import os
import uuid
from flask import current_app
from models import Clasificacion, db, Equipo, Pertenece, Partido, Torneo, Inscripcion, Palmares

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
    def guardar_logo_equipo(file, archivo_antiguo = None):
        """Genera un nombre único y guarda el archivo del logo."""
        if file and file.filename != '':
            # ELIMINAR BASURA: Si había un logo anterior que no sea el por defecto, lo borramos del disco
            if archivo_antiguo and archivo_antiguo != 'default_team.png':
                ruta_antigua = os.path.join('uploads/equipos', archivo_antiguo)
                if os.path.exists(ruta_antigua):
                    try:
                        os.remove(ruta_antigua)
                    except Exception as e:
                        print(f"Error al borrar archivo basura: {e}")

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
        # 2. Buscamos si el equipo está inscrito en algún torneo activo o en fase de inscripción
        # Si el torneo NO está 'Finalizado', bloqueamos el borrado radicalmente
        torneo_activo = db.session.query(Torneo).join(Inscripcion).filter(
            Inscripcion.id_equipo == equipo.id_equipo,
            Torneo.estado != 'Finalizado'
        ).first()

        if torneo_activo:
            return False, f"No puedes disolver el equipo mientras participe en un torneo activo o en juego: '{torneo_activo.nombre}'"

        # 3. Si el torneo SÍ está finalizado (o no está apuntado a ninguno), pasamos el búnker de seguridad
        try:
            # Limpiamos los historiales de clasificación del equipo en torneos ya viejos
            Clasificacion.query.filter_by(id_equipo=equipo.id_equipo).delete()
            
            # Limpiamos las tablas intermedias
            Pertenece.query.filter_by(id_equipo=equipo.id_equipo).delete()
            Inscripcion.query.filter_by(id_equipo=equipo.id_equipo).delete()
            
            # Eliminamos su logo físico si no es el por defecto
            if equipo.url_logo and equipo.url_logo != 'default_team.png':
                ruta_logo = os.path.join('uploads/equipos', equipo.url_logo)
                if os.path.exists(ruta_logo):
                    try: os.remove(ruta_logo)
                    except Exception: pass

            # Por último, borramos el cascarón del equipo
            db.session.delete(equipo)
            return True, "Equipo disuelto correctamente"
            
        except Exception as e:
            return False, f"Error al disolver el equipo: {str(e)}"