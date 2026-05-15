from models import db, Clasificacion, StatsJugador, PartidoEstadistica

class ClasificacionService:
    
    @staticmethod
    def revertir_estadisticas_partido(partido):
        """Resta los puntos y goles de un partido que ya estaba finalizado."""
        clasif_local = Clasificacion.query.filter_by(id_torneo=partido.id_torneo, id_equipo=partido.id_local).first()
        clasif_visit = Clasificacion.query.filter_by(id_torneo=partido.id_torneo, id_equipo=partido.id_visitante).first()

        if clasif_local and clasif_visit:
            clasif_local.pj -= 1
            clasif_visit.pj -= 1
            clasif_local.gf -= partido.goles_local
            clasif_local.gc -= partido.goles_visit
            clasif_visit.gf -= partido.goles_visit
            clasif_visit.gc -= partido.goles_local

            if partido.goles_local > partido.goles_visit:
                clasif_local.pg -= 1
                clasif_local.puntos -= 3
                clasif_visit.pp -= 1
            elif partido.goles_visit > partido.goles_local:
                clasif_visit.pg -= 1
                clasif_visit.puntos -= 3
                clasif_local.pp -= 1
            else:
                clasif_local.pe -= 1
                clasif_visit.pe -= 1
                clasif_local.puntos -= 1
                clasif_visit.puntos -= 1

        # Revertir estadísticas individuales
        eventos_antiguos = PartidoEstadistica.query.filter_by(id_partido=partido.id_partido).all()
        for ev in eventos_antiguos:
            stats_gen = StatsJugador.query.filter_by(id_usuario=ev.id_usuario, id_torneo=partido.id_torneo).first()
            if stats_gen:
                stats_gen.goles -= (ev.goles or 0)
                stats_gen.amarillas -= (ev.amarillas or 0)
                stats_gen.rojas -= (ev.rojas or 0)
            db.session.delete(ev)
        
        db.session.flush()

    @staticmethod
    def aplicar_nuevas_estadisticas(partido, goles_local, goles_visit, eventos):
        """Suma los nuevos puntos y goles a la clasificación y stats de jugadores."""
        clasif_local = Clasificacion.query.filter_by(id_torneo=partido.id_torneo, id_equipo=partido.id_local).first()
        clasif_visit = Clasificacion.query.filter_by(id_torneo=partido.id_torneo, id_equipo=partido.id_visitante).first()

        if clasif_local and clasif_visit:
            clasif_local.pj = (clasif_local.pj or 0) + 1
            clasif_visit.pj = (clasif_visit.pj or 0) + 1
            clasif_local.gf = (clasif_local.gf or 0) + goles_local
            clasif_local.gc = (clasif_local.gc or 0) + goles_visit
            clasif_visit.gf = (clasif_visit.gf or 0) + goles_visit
            clasif_visit.gc = (clasif_visit.gc or 0) + goles_local

            if goles_local > goles_visit:
                clasif_local.pg = (clasif_local.pg or 0) + 1
                clasif_local.puntos = (clasif_local.puntos or 0) + 3
                clasif_visit.pp = (clasif_visit.pp or 0) + 1
            elif goles_visit > goles_local:
                clasif_visit.pg = (clasif_visit.pg or 0) + 1
                clasif_visit.puntos = (clasif_visit.puntos or 0) + 3
                clasif_local.pp = (clasif_local.pp or 0) + 1
            else:
                clasif_local.pe = (clasif_local.pe or 0) + 1
                clasif_visit.pe = (clasif_visit.pe or 0) + 1
                clasif_local.puntos = (clasif_local.puntos or 0) + 1
                clasif_visit.puntos = (clasif_visit.puntos or 0) + 1

        # Guardar eventos individuales
        for ev in eventos:
            id_usr = ev.get('id_usuario')
            g_ind = ev.get('goles', 0)
            a_ind = ev.get('amarillas', 0)
            r_ind = ev.get('rojas', 0)

            if g_ind == 0 and a_ind == 0 and r_ind == 0:
                continue

            nuevo_evento = PartidoEstadistica(
                id_partido=partido.id_partido, id_usuario=id_usr,
                goles=g_ind, amarillas=a_ind, rojas=r_ind
            )
            db.session.add(nuevo_evento)

            stats_gen = StatsJugador.query.filter_by(id_usuario=id_usr, id_torneo=partido.id_torneo).first()
            if not stats_gen:
                stats_gen = StatsJugador(id_usuario=id_usr, id_torneo=partido.id_torneo)
                db.session.add(stats_gen)
            
            stats_gen.goles = (stats_gen.goles or 0) + g_ind
            stats_gen.amarillas = (stats_gen.amarillas or 0) + a_ind
            stats_gen.rojas = (stats_gen.rojas or 0) + r_ind