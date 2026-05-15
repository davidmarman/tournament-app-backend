from flask import jsonify, request
from models import Equipo, Inscripcion, db, Pertenece, Usuario
from services.equipo_service import EquipoService

class EquiposController:

    @staticmethod
    def get_mis_equipos(user_id):
        equipos = EquipoService.obtener_equipos_usuario(user_id)
        return jsonify(equipos), 200

    @staticmethod
    def get_detalle(id_equipo, user_id):
        equipo = Equipo.query.get_or_404(id_equipo)
        
        # Recopilamos toda la info usando el servicio
        proximo = EquipoService.obtener_proximo_partido(id_equipo)
        plantilla = EquipoService.obtener_plantilla(id_equipo)
        palmares = EquipoService.obtener_palmares(id_equipo)
        
        # Torneos inscritos (directo desde inscripciones)
        inscripciones = Inscripcion.query.filter_by(id_equipo=id_equipo).all()
        lista_torneos = [{
            "id": ins.torneo.id_torneo,
            "nombre": ins.torneo.nombre,
            "logo": ins.torneo.url_logo or "default_torneo.png"
        } for ins in inscripciones if ins.torneo]

        return jsonify({
            "id": equipo.id_equipo,
            "nombre": equipo.nombre,
            "logo": equipo.url_logo or "default_team.png",
            "id_capitan": equipo.id_capitan,
            "es_capitan": str(equipo.id_capitan) == str(user_id),
            "proximo_partido": proximo,
            "torneos": lista_torneos,
            "jugadores": plantilla,
            "palmares": palmares
        }), 200

    @staticmethod
    def crear(user_id):
        nombre = request.form.get('nombre')
        if not nombre: return jsonify({"error": "Falta nombre"}), 400
        
        logo = request.files.get('logo')
        nuevo = EquipoService.crear_equipo(nombre, user_id, logo)
        db.session.commit()
        return jsonify({"id": nuevo.id_equipo, "nombre": nuevo.nombre, "logo": nuevo.url_logo, "es_capitan": True}), 201

    @staticmethod
    def anadir_jugador(id_equipo, capitan_id):
        data = request.get_json()
        username = data.get('username')
        equipo = Equipo.query.get_or_404(id_equipo)
        
        if str(equipo.id_capitan) != str(capitan_id): return jsonify({"error": "No eres el capitán"}), 403
        
        usuario = Usuario.query.filter_by(username=username).first()
        if not usuario: return jsonify({"error": "Usuario no existe"}), 404
        
        if Pertenece.query.filter_by(id_usuario=usuario.id_usuario, id_equipo=id_equipo).first():
            return jsonify({"error": "Ya está en el equipo"}), 400
            
        db.session.add(Pertenece(id_usuario=usuario.id_usuario, id_equipo=id_equipo))
        db.session.commit()
        return jsonify({"msg": "Añadido"}), 201

    @staticmethod
    def expulsar(id_equipo, id_jugador, capitan_id):
        equipo = Equipo.query.get_or_404(id_equipo)
        if equipo.id_capitan != capitan_id: return jsonify({"error": "No autorizado"}), 403
        if capitan_id == id_jugador: return jsonify({"error": "No puedes expulsarte a ti mismo"}), 400
        
        vinculo = Pertenece.query.filter_by(id_equipo=id_equipo, id_usuario=id_jugador).first()
        if not vinculo: return jsonify({"error": "No está en el equipo"}), 404
        
        db.session.delete(vinculo)
        db.session.commit()
        return jsonify({"msg": "Expulsado"}), 200

    @staticmethod
    def salir(id_equipo, user_id):
        equipo = Equipo.query.get_or_404(id_equipo)
        if equipo.id_capitan == user_id: return jsonify({"error": "Capitán debe disolver"}), 400
        
        vinculo = Pertenece.query.filter_by(id_equipo=id_equipo, id_usuario=user_id).first()
        if not vinculo: return jsonify({"error": "No estás en el equipo"}), 404
        
        db.session.delete(vinculo)
        db.session.commit()
        return jsonify({"msg": "Has salido"}), 200

    @staticmethod
    def disolver(id_equipo, capitan_id):
        equipo = Equipo.query.get_or_404(id_equipo)
        if equipo.id_capitan != capitan_id: return jsonify({"error": "No autorizado"}), 403
        
        EquipoService.disolver_equipo_completo(equipo)
        db.session.commit()
        return jsonify({"msg": "Disuelto"}), 200

    @staticmethod
    def editar(id_equipo, capitan_id):
        equipo = Equipo.query.get_or_404(id_equipo)
        if equipo.id_capitan != capitan_id: return jsonify({"error": "No autorizado"}), 403
        
        nombre = request.form.get('nombre')
        if nombre: equipo.nombre = nombre
        
        if 'logo' in request.files:
            equipo.url_logo = EquipoService.guardar_logo_equipo(request.files['logo'])
            
        db.session.commit()
        return jsonify({"msg": "Actualizado"}), 200

    @staticmethod
    def ceder_capitania(id_equipo, capitan_id):
        data = request.get_json()
        nuevo_cap_id = data.get('nuevo_capitan_id')
        equipo = Equipo.query.get_or_404(id_equipo)
        
        if equipo.id_capitan != capitan_id: return jsonify({"error": "No autorizado"}), 403
        if not Pertenece.query.filter_by(id_equipo=id_equipo, id_usuario=nuevo_cap_id).first():
            return jsonify({"error": "El nuevo capitán debe estar en el equipo"}), 400
            
        equipo.id_capitan = nuevo_cap_id
        db.session.commit()
        return jsonify({"msg": "Capitanía cedida"}), 200