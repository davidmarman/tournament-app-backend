from models import Palmares, db, Torneo, Partido, Clasificacion, Inscripcion, Usuario, Equipo, Administra, StatsJugador, PartidoEstadistica
import uuid
import os
import datetime as dt

class TorneoService:

    @staticmethod
    def obtener_mis_torneos(user_id):
        usuario = Usuario.query.get(user_id)
        ids_equipos = [v.id_equipo for v in usuario.equipos if v.equipo]
        
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
        return list(torneos_dict.values())

    @staticmethod
    def obtener_detalle_jornada(id_torneo, num_jornada):
        partidos_db = Partido.query.filter_by(
            id_torneo=id_torneo, numero_jornada=num_jornada
        ).all()
        
        return [{
            "id_partido": p.id_partido,
            "equipo_local": p.equipo_local.nombre,
            "logo_local": p.equipo_local.url_logo or "default_team.png",
            "equipo_visitante": p.equipo_visitante.nombre,
            "logo_visitante": p.equipo_visitante.url_logo or "default_team.png",
            "goles_local": p.goles_local,
            "goles_visit": p.goles_visit,
            "estado": p.estado,
            "fecha": p.fecha.strftime("%d/%m/%Y %H:%M") if p.fecha else "Sin fecha"
        } for p in partidos_db]

    @staticmethod
    def calcular_jornada_actual(id_torneo):
        siguiente = Partido.query.filter_by(
            id_torneo=id_torneo, estado='Pendiente'
        ).order_by(Partido.numero_jornada.asc()).first()
        return siguiente.numero_jornada if siguiente else 1

    @staticmethod
    def obtener_max_jornada(id_torneo):
        return db.session.query(db.func.max(Partido.numero_jornada)).filter_by(id_torneo=id_torneo).scalar() or 1

    @staticmethod
    def inscribir_equipo(id_torneo, id_equipo):
        # Verificar si ya está inscrito
        ya_inscrito = Inscripcion.query.filter_by(id_equipo=id_equipo, id_torneo=id_torneo).first()
        if ya_inscrito:
            return False, "El equipo ya está inscrito en este torneo"

        nueva_ins = Inscripcion(id_equipo=id_equipo, id_torneo=id_torneo)
        db.session.add(nueva_ins)

        # Si es liga, inicializamos clasificación
        torneo = Torneo.query.get(id_torneo)
        if torneo.tipo == "Liga":
            nueva_clasif = Clasificacion(id_torneo=id_torneo, id_equipo=id_equipo)
            db.session.add(nueva_clasif)
        
        return True, "Inscripción realizada"

    @staticmethod
    def crear_torneo_base(data, user_id, logo_file=None):
        codigo = f"TRN-{uuid.uuid4().hex[:6].upper()}"
        nuevo_torneo = Torneo(
            nombre=data['nombre'],
            tipo=data.get('tipo', 'Liga'),
            descripcion=data.get('descripcion', ''),
            codigo_acceso=codigo,
            fecha_inicio=data.get('fecha_inicio'),
            dias_juego=data.get('dias_juego'),
            horarios_juego=data.get('horarios_juego'),
            formato_partidos=data.get('formato_partidos', 'Ida')
        )

        if logo_file:
            ext = logo_file.filename.rsplit('.', 1)[1].lower() if '.' in logo_file.filename else 'png'
            nombre_logo = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join('uploads/torneos', nombre_logo)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            logo_file.save(filepath)
            nuevo_torneo.url_logo = nombre_logo

        db.session.add(nuevo_torneo)
        db.session.flush() 

        nuevo_admin = Administra(id_usuario=user_id, id_torneo=nuevo_torneo.id_torneo)
        db.session.add(nuevo_admin)
        
        return nuevo_torneo

    @staticmethod
    def eliminar_torneo_completo(torneo):
        Clasificacion.query.filter_by(id_torneo=torneo.id_torneo).delete()
        Inscripcion.query.filter_by(id_torneo=torneo.id_torneo).delete()
        Partido.query.filter_by(id_torneo=torneo.id_torneo).delete()
        Administra.query.filter_by(id_torneo=torneo.id_torneo).delete()
        db.session.delete(torneo)

    @staticmethod
    def generar_calendario_liga(id_torneo):
        torneo = Torneo.query.get(id_torneo)
        inscripciones = Inscripcion.query.filter_by(id_torneo=id_torneo).all()
        equipos = [ins.equipo for ins in inscripciones]

        # 1. Algoritmo Round-Robin
        if len(equipos) % 2 != 0:
            equipos.append(None)

        n = len(equipos)
        partidos_ida = []
        for jornada in range(1, n):
            for i in range(n // 2):
                local, visitante = equipos[i], equipos[n - 1 - i]
                if local and visitante:
                    partidos_ida.append({"jornada": jornada, "id_local": local.id_equipo, "id_visitante": visitante.id_equipo})
            equipos.insert(1, equipos.pop())

        # Si es Ida y Vuelta, generamos la segunda vuelta
        partidos_totales = partidos_ida.copy()
        if torneo.formato_partidos == 'Ida y Vuelta':
            for p in partidos_ida:
                partidos_totales.append({
                    "jornada": p["jornada"] + (n - 1), # Jornadas correlativas
                    "id_local": p["id_visitante"],    # Invertimos localía
                    "id_visitante": p["id_local"]
                })

        # 2. Lógica de Fechas y Horas
        dias_map = {"Lunes": 0, "Martes": 1, "Miercoles": 2, "Jueves": 3, "Viernes": 4, "Sabado": 5, "Domingo": 6}
        dias_permitidos = [dias_map[d.strip()] for d in torneo.dias_juego.split(",") if d.strip() in dias_map]
        horarios = [h.strip() for h in torneo.horarios_juego.split(",") if h.strip()]
        
        fecha_actual = torneo.fecha_inicio
        while fecha_actual.weekday() not in dias_permitidos:
            fecha_actual += dt.timedelta(days=1)

        hora_idx = 0
        for p_data in partidos_totales:
            hora_str = horarios[hora_idx].split("-")[0]
            hora_obj = dt.datetime.strptime(hora_str, "%H:%M").time()
            fecha_hora = dt.datetime.combine(fecha_actual, hora_obj)

            nuevo_p = Partido(
                id_torneo=id_torneo, id_local=p_data["id_local"],
                id_visitante=p_data["id_visitante"], numero_jornada=p_data["jornada"],
                fecha=fecha_hora, estado="Pendiente"
            )
            db.session.add(nuevo_p)

            hora_idx += 1
            if hora_idx >= len(horarios):
                hora_idx = 0
                fecha_actual += dt.timedelta(days=1)
                while fecha_actual.weekday() not in dias_permitidos:
                    fecha_actual += dt.timedelta(days=1)
        return len(partidos_totales)

    @staticmethod
    def finalizar_y_repartir_premios(id_torneo):
        torneo = Torneo.query.get(id_torneo)
        torneo.estado = 'Finalizado'
        
        # Clasificación (Podio)
        clasif = Clasificacion.query.filter_by(id_torneo=id_torneo).order_by(Clasificacion.puntos.desc(), Clasificacion.gf.desc()).all()
        tipos = ['Campeon', 'Subcampeon', 'Tercero']
        for i in range(min(len(clasif), 3)):
            db.session.add(Palmares(id_torneo=id_torneo, id_equipo=clasif[i].id_equipo, tipo_logro=tipos[i]))

        # Stats Individuales (Pichichi, Amarillas, Rojas)
        stats_map = {'goles': 'Pichichi', 'amarillas': 'Más Amarillas', 'rojas': 'Más Rojas'}
        for campo, nombre_logro in stats_map.items():
            top = StatsJugador.query.filter_by(id_torneo=id_torneo).order_by(db.text(f"{campo} DESC")).first()
            valor = getattr(top, campo) if top else 0
            if top and valor > 0:
                db.session.add(Palmares(id_torneo=id_torneo, id_usuario=top.id_usuario, tipo_logro=nombre_logro, valor_stats=valor))