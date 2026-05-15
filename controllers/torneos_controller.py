from flask import jsonify, request
from models import Torneo, Clasificacion, db, Equipo, Administra, Partido
from services.torneo_service import TorneoService
import datetime as dt

class TorneosController:

    @staticmethod
    def get_mis_torneos(user_id):
        torneos = TorneoService.obtener_mis_torneos(user_id)
        return jsonify(torneos), 200

    @staticmethod
    def get_detalle(id_torneo):
        torneo = Torneo.query.get_or_404(id_torneo)
        jornada_solicitada = request.args.get('jornada', type=int)
        
        jornada_que_toca = TorneoService.calcular_jornada_actual(id_torneo)
        jornada_a_enviar = jornada_solicitada if jornada_solicitada else jornada_que_toca
        
        partidos = TorneoService.obtener_detalle_jornada(id_torneo, jornada_a_enviar)

        if jornada_solicitada:
            return jsonify({
                "jornada_mostrada": jornada_a_enviar,
                "partidos": partidos
            }), 200

        # Carga completa inicial
        max_j = TorneoService.obtener_max_jornada(id_torneo)
        clasif_db = Clasificacion.query.filter_by(id_torneo=id_torneo).order_by(Clasificacion.puntos.desc()).all()
        
        lista_clasif = [{
            "id_equipo": c.equipo.id_equipo,
            "nombre": c.equipo.nombre,
            "logo": c.equipo.url_logo or "default_team.png",
            "pts": c.puntos or 0, "gf": c.gf or 0, "gc": c.gc or 0,
            "pj": c.pj or 0, "pg": c.pg or 0, "pe": c.pe or 0, "pp": c.pp or 0
        } for c in clasif_db]

        return jsonify({
            "info": {
                "id": torneo.id_torneo,
                "nombre": torneo.nombre,
                "logo": torneo.url_logo or "default_torneo.png",
                "descripcion": torneo.descripcion,
                "codigo": torneo.codigo_acceso,
                "estado": torneo.estado
            },
            "clasificacion": lista_clasif,
            "jornada_actual": jornada_que_toca,
            "max_jornadas": max_j,
            "partidos": partidos
        }), 200
    

    @staticmethod
    def inscribir(user_id):
        data = request.get_json()
        codigo = data.get('codigo_acceso')
        id_equipo = data.get('id_equipo')

        torneo = Torneo.query.filter_by(codigo_acceso=codigo).first()
        if not torneo: return jsonify({"error": "Código inválido"}), 404

        equipo = Equipo.query.get(id_equipo)
        if not equipo: return jsonify({"error": "Equipo no existe"}), 404
        if str(equipo.id_capitan) != str(user_id):
            return jsonify({"error": "Solo el capitán puede inscribir"}), 403

        exito, msg = TorneoService.inscribir_equipo(torneo.id_torneo, id_equipo)
        if not exito: return jsonify({"error": msg}), 400

        db.session.commit()
        return jsonify({"msg": f"¡{equipo.nombre} inscrito!"}), 201

    @staticmethod
    def crear(user_id):
        nombre = request.form.get('nombre')
        if not nombre: return jsonify({"error": "Nombre obligatorio"}), 400

        # Preparar datos para el servicio
        data = request.form.to_dict()
        if data.get('fecha_inicio'):
            data['fecha_inicio'] = dt.datetime.strptime(data['fecha_inicio'], "%Y-%m-%d").date()

        logo = request.files.get('logo')
        nuevo_t = TorneoService.crear_torneo_base(data, user_id, logo)
        
        db.session.commit()
        return jsonify({"msg": "Creado", "id": nuevo_t.id_torneo}), 201

    @staticmethod
    def get_admin_dashboard(user_id):
        admin_links = Administra.query.filter_by(id_usuario=user_id).all()
        ids = [l.id_torneo for l in admin_links]
        
        torneos_data = []
        partidos_data = []

        if ids:
            torneos = Torneo.query.filter(Torneo.id_torneo.in_(ids)).all()
            torneos_data = [{"id": t.id_torneo, "nombre": t.nombre, "logo": t.url_logo or "default_torneo.png", "codigo": t.codigo_acceso} for t in torneos]

            partidos = Partido.query.filter(Partido.id_torneo.in_(ids), Partido.estado.in_(['Pendiente', 'En Juego'])).order_by(Partido.fecha.asc()).limit(15).all()
            partidos_data = [{
                "id_partido": p.id_partido, "torneo_nombre": p.torneo.nombre,
                "equipo_local": p.equipo_local.nombre, "logo_local": p.equipo_local.url_logo or "default_team.png",
                "equipo_visitante": p.equipo_visitante.nombre, "logo_visitante": p.equipo_visitante.url_logo or "default_team.png",
                "fecha": p.fecha.strftime("%d/%m/%Y %H:%M"), "estado": p.estado
            } for p in partidos]

        return jsonify({"torneos": torneos_data, "proximos_partidos": partidos_data}), 200

    @staticmethod
    def eliminar(id_torneo, user_id):
        torneo = Torneo.query.get_or_404(id_torneo)
        es_admin = Administra.query.filter_by(id_usuario=user_id, id_torneo=id_torneo).first()
        if not es_admin: return jsonify({"error": "No autorizado"}), 403

        try:
            TorneoService.eliminar_torneo_completo(torneo)
            db.session.commit()
            return jsonify({"msg": "Eliminado"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500
        
    @staticmethod
    def generar_calendario(id_torneo, user_id):
        es_admin = Administra.query.filter_by(id_usuario=user_id, id_torneo=id_torneo).first()
        if not es_admin: return jsonify({"error": "No autorizado"}), 403

        if Partido.query.filter_by(id_torneo=id_torneo).first():
            return jsonify({"error": "Calendario ya generado"}), 400

        try:
            total = TorneoService.generar_calendario_liga(id_torneo)
            db.session.commit()
            return jsonify({"msg": f"Calendario listo: {total} partidos"}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def finalizar(id_torneo, user_id):
        torneo = Torneo.query.get_or_404(id_torneo)
        if torneo.estado == 'Finalizado': return jsonify({"msg": "Ya finalizado"}), 400

        # Validar si es admin
        es_admin = Administra.query.filter_by(id_usuario=user_id, id_torneo=id_torneo).first()
        if not es_admin: return jsonify({"error": "No autorizado"}), 403

        TorneoService.finalizar_y_repartir_premios(id_torneo)
        db.session.commit()
        return jsonify({"msg": "Torneo cerrado y palmarés generado"}), 200