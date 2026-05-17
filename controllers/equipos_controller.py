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

        # Comprobamos si es miembro del equipo para mostrar el detalle completo
        es_miembro = Pertenece.query.filter_by(id_equipo=id_equipo, id_usuario=user_id).first() is not None
        
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

        # 2. CÁLCULO DE LÍDERES INTERNOS DEL EQUIPO
        from models import PartidoEstadistica, Usuario, db
        # Sacamos los IDs de los jugadores de la plantilla
        ids_plantilla = [j['id'] for j in plantilla]
        
        lider_goles = {"username": "Ninguno", "goles": 0}
        lider_amarillas = {"username": "Ninguno", "amarillas": 0}
        lider_rojas = {"username": "Ninguno", "rojas": 0}

        if ids_plantilla:
            # Pichichi del equipo
            top_g = db.session.query(Usuario.username, db.func.sum(PartidoEstadistica.goles).label('total')).\
                join(PartidoEstadistica).filter(PartidoEstadistica.id_usuario.in_(ids_plantilla)).\
                group_by(Usuario.id_usuario).order_by(db.text('total DESC')).first()
            if top_g and top_g.total > 0: lider_goles = {"username": f"@{top_g.username}", "goles": int(top_g.total)}

            # Más amarillas
            top_a = db.session.query(Usuario.username, db.func.sum(PartidoEstadistica.amarillas).label('total')).\
                join(PartidoEstadistica).filter(PartidoEstadistica.id_usuario.in_(ids_plantilla)).\
                group_by(Usuario.id_usuario).order_by(db.text('total DESC')).first()
            if top_a and top_a.total > 0: lider_amarillas = {"username": f"@{top_a.username}", "amarillas": int(top_a.total)}

            # Más rojas
            top_r = db.session.query(Usuario.username, db.func.sum(PartidoEstadistica.rojas).label('total')).\
                join(PartidoEstadistica).filter(PartidoEstadistica.id_usuario.in_(ids_plantilla)).\
                group_by(Usuario.id_usuario).order_by(db.text('total DESC')).first()
            if top_r and top_r.total > 0: lider_rojas = {"username": f"@{top_r.username}", "rojas": int(top_r.total)}

        return jsonify({
            "id": equipo.id_equipo,
            "nombre": equipo.nombre,
            "logo": equipo.url_logo or "default_team.png",
            "id_capitan": equipo.id_capitan,
            "es_capitan": str(equipo.id_capitan) == str(user_id),
            "soy_miembro": es_miembro,
            "proximo_partido": proximo,
            "torneos": lista_torneos,
            "jugadores": plantilla,
            "palmares": palmares,
            "lider_goles": lider_goles, 
            "lider_amarillas": lider_amarillas, 
            "lider_rojas": lider_rojas          
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
        
        # 1. Verificar que quien lo pide es el capitán
        if equipo.id_capitan != capitan_id: 
            return jsonify({"error": "No autorizado"}), 403
        
        # 2. Llamamos al servicio para comprobar si está jugando un torneo activo
        exito, msg = EquipoService.disolver_equipo_completo(equipo)
        
        # Si exito es False, el servicio nos devuelve el porqué (ej: "No puedes disolver...")
        if not exito:
            return jsonify({"error": msg}), 400

        # Si pasa el filtro del servicio con éxito, guardamos en la BD
        db.session.commit()
        return jsonify({"msg": msg}), 200

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