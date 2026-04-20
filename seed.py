from app import create_app
from extensions import db
from models import Usuario, Equipo, Torneo, Partido, Pertenece, Inscripcion, Clasificacion, PartidoEstadistica
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

app = create_app()

def poblar_base_de_datos():
    with app.app_context():
        print("Iniciando el poblado MASIVO de la base de datos...")

        # 1. BUSCAR TU USUARIO PRINCIPAL
        mi_usuario = Usuario.query.filter_by(email="davidmartinm.dmm@gmail.com").first()
        if not mi_usuario:
            print("❌ Error: No se encontró tu usuario. Revisa el email.")
            return
        print(f"✅ Usuario principal: {mi_usuario.nombre}")

        # 2. CREAR USUARIOS DUMMY (Capitanes de otros equipos)
        pass_hash = generate_password_hash("123456")
        u2 = Usuario(nombre="Carlos", apellido="Bug", username="carlos_bug", email="carlos@test.com", password=pass_hash, rol="User")
        u3 = Usuario(nombre="Ana", apellido="Zorin", username="ana_z", email="ana@test.com", password=pass_hash, rol="User")
        u4 = Usuario(nombre="Luis", apellido="Py", username="luis_py", email="luis@test.com", password=pass_hash, rol="User")
        
        db.session.add_all([u2, u3, u4])
        db.session.commit()
        print("✅ 3 Usuarios Dummy creados.")

        # 3. CREAR EQUIPOS
        t1 = Equipo(nombre="F.C. Los Desarrolladores", id_capitan=mi_usuario.id_usuario)
        t2 = Equipo(nombre="Atlético de Bugs", id_capitan=u2.id_usuario)
        t3 = Equipo(nombre="Zorin Utd", id_capitan=u3.id_usuario)
        t4 = Equipo(nombre="Python City", id_capitan=u4.id_usuario)
        
        db.session.add_all([t1, t2, t3, t4])
        db.session.commit()
        print("✅ 4 Equipos creados.")

        # 4. VINCULAR CAPITANES A SUS EQUIPOS (Plantillas)
        db.session.add_all([
            Pertenece(id_usuario=mi_usuario.id_usuario, id_equipo=t1.id_equipo),
            Pertenece(id_usuario=u2.id_usuario, id_equipo=t2.id_equipo),
            Pertenece(id_usuario=u3.id_usuario, id_equipo=t3.id_equipo),
            Pertenece(id_usuario=u4.id_usuario, id_equipo=t4.id_equipo),
            # ¡Metemos a Ana también en tu equipo para que tengas un compañero en la vista "Plantilla"!
            Pertenece(id_usuario=u3.id_usuario, id_equipo=t1.id_equipo) 
        ])
        db.session.commit()

        # 5. CREAR TORNEO E INSCRIBIRLOS
        torneo = Torneo(
            nombre="Superliga Zorin 2026", 
            tipo="Liga", 
            codigo_acceso="ZORIN-2026", 
            descripcion="La liga más competitiva del desarrollo de software. Los partidos se juegan los sábados en el campo de césped artificial."
        )
        db.session.add(torneo)
        db.session.commit()

        db.session.add_all([
            Inscripcion(id_equipo=t1.id_equipo, id_torneo=torneo.id_torneo),
            Inscripcion(id_equipo=t2.id_equipo, id_torneo=torneo.id_torneo),
            Inscripcion(id_equipo=t3.id_equipo, id_torneo=torneo.id_torneo),
            Inscripcion(id_equipo=t4.id_equipo, id_torneo=torneo.id_torneo)
        ])
        db.session.commit()
        print("✅ Torneo creado y equipos inscritos.")

        # 6. CREAR PARTIDOS (Jornada 1 Finalizada, Jornada 2 Pendiente)
        hace_una_semana = datetime.now() - timedelta(days=7)
        dentro_de_dos_dias = datetime.now() + timedelta(days=2)

        # Jornada 1
        p1 = Partido(id_torneo=torneo.id_torneo, id_local=t1.id_equipo, id_visitante=t2.id_equipo, goles_local=2, goles_visit=1, estado="Fin", numero_jornada=1, fecha=hace_una_semana)
        p2 = Partido(id_torneo=torneo.id_torneo, id_local=t3.id_equipo, id_visitante=t4.id_equipo, goles_local=0, goles_visit=0, estado="Fin", numero_jornada=1, fecha=hace_una_semana)
        
        # Jornada 2
        p3 = Partido(id_torneo=torneo.id_torneo, id_local=t1.id_equipo, id_visitante=t3.id_equipo, goles_local=0, goles_visit=0, estado="Pendiente", numero_jornada=2, fecha=dentro_de_dos_dias)
        p4 = Partido(id_torneo=torneo.id_torneo, id_local=t4.id_equipo, id_visitante=t2.id_equipo, goles_local=0, goles_visit=0, estado="Pendiente", numero_jornada=2, fecha=dentro_de_dos_dias)
        
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        # 7. GENERAR LA CLASIFICACIÓN (Basado en la Jornada 1)
        # T1 ganó (3 pts), T3 y T4 empataron (1 pt), T2 perdió (0 pts)
        db.session.add_all([
            Clasificacion(id_torneo=torneo.id_torneo, id_equipo=t1.id_equipo, puntos=3, pj=1, pg=1, pe=0, pp=0),
            Clasificacion(id_torneo=torneo.id_torneo, id_equipo=t3.id_equipo, puntos=1, pj=1, pg=0, pe=1, pp=0),
            Clasificacion(id_torneo=torneo.id_torneo, id_equipo=t4.id_equipo, puntos=1, pj=1, pg=0, pe=1, pp=0),
            Clasificacion(id_torneo=torneo.id_torneo, id_equipo=t2.id_equipo, puntos=0, pj=1, pg=0, pe=0, pp=1)
        ])
        
        # 8. ESTADÍSTICAS SÚPER DETALLADAS
        # Simulamos que tú marcaste los 2 goles en la Jornada 1
        db.session.add(PartidoEstadistica(id_partido=p1.id_partido, id_usuario=mi_usuario.id_usuario, goles=2))
        db.session.commit()

        print("🎉 ¡Base de datos poblada masivamente con éxito!")

if __name__ == '__main__':
    poblar_base_de_datos()