from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity
from models import db, Partido, Pertenece
from services.clasificacion_service import ClasificacionService
from datetime import datetime, timedelta
from sqlalchemy import or_

class PartidosController:

    @staticmethod
    def get_proximos_partidos():
        user_id = get_jwt_identity()
        mis_vinculos = Pertenece.query.filter_by(id_usuario=user_id).all()
        ids_mis_equipos = [v.id_equipo for v in mis_vinculos]

        if not ids_mis_equipos:
            return jsonify([]), 200

        hoy = datetime.now()
        dentro_de_30_dias = hoy + timedelta(days=30)
        
        partidos = Partido.query.filter(
            Partido.estado == 'Pendiente',
            Partido.fecha >= hoy,
            Partido.fecha <= dentro_de_30_dias,
            or_(
                Partido.id_local.in_(ids_mis_equipos),
                Partido.id_visitante.in_(ids_mis_equipos)
            )
        ).order_by(Partido.fecha.asc()).all()

        resultado = []
        for p in partidos:
            resultado.append({
                "id_partido": p.id_partido,
                "equipo_local": p.equipo_local.nombre,
                "logo_local": p.equipo_local.url_logo or "default_team.png",
                "equipo_visitante": p.equipo_visitante.nombre,
                "logo_visitante": p.equipo_visitante.url_logo or "default_team.png",
                "goles_local": p.goles_local,
                "goles_visit": p.goles_visit,
                "estado": p.estado,
                "fecha": p.fecha.strftime("%d/%m/%Y %H:%M") if p.fecha else "Sin fecha",
                "nombre_torneo": p.torneo.nombre
            })
        return jsonify(resultado), 200

    @staticmethod
    def get_acta(id_partido):
        partido = Partido.query.get_or_404(id_partido)
        
        def get_jugadores(id_equipo):
            vinculos = Pertenece.query.filter_by(id_equipo=id_equipo).all()
            return [{
                "id_usuario": v.usuario.id_usuario,
                "nombre": f"{v.usuario.nombre} {v.usuario.apellido}",
                "imagen": v.usuario.imagen_perfil or "default.png"
            } for v in vinculos]

        return jsonify({
            "id_partido": partido.id_partido,
            "torneo_nombre": partido.torneo.nombre,
            "jornada": partido.numero_jornada,
            "equipo_local": {
                "id": partido.id_local, "nombre": partido.equipo_local.nombre,
                "logo": partido.equipo_local.url_logo or "default_team.png",
                "capitan": partido.equipo_local.id_capitan, "jugadores": get_jugadores(partido.id_local)
            },
            "equipo_visitante": {
                "id": partido.id_visitante, "nombre": partido.equipo_visitante.nombre,
                "logo": partido.equipo_visitante.url_logo or "default_team.png",
                "capitan": partido.equipo_visitante.id_capitan, "jugadores": get_jugadores(partido.id_visitante)
            }
        }), 200

    @staticmethod
    def finalizar_partido(id_partido):
        partido = Partido.query.get_or_404(id_partido)
        data = request.get_json()
        
        g_local = data.get('goles_local', 0)
        g_visit = data.get('goles_visitante', 0)
        eventos = data.get('eventos', [])

        if partido.estado == 'Fin':
            ClasificacionService.revertir_estadisticas_partido(partido)

        partido.goles_local = g_local
        partido.goles_visit = g_visit
        partido.estado = 'Fin'

        ClasificacionService.aplicar_nuevas_estadisticas(partido, g_local, g_visit, eventos)

        db.session.commit()
        return jsonify({"msg": "Acta actualizada correctamente"}), 200