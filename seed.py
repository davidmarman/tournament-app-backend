from app import create_app
from extensions import db
from models import Usuario, Equipo, Torneo, Partido, Pertenece, Inscripcion
from datetime import datetime, timedelta, date

# Creamos la aplicación para tener acceso a la base de datos
app = create_app()

def poblar_base_de_datos():
    with app.app_context():
        print("Iniciando el poblado de la base de datos...")

        # 1. Buscar al usuario que creaste (Cambia el email si no es este)
        mi_usuario = Usuario.query.filter_by(email="davidmartinm.dmm@gmail.com").first()
        
        if not mi_usuario:
            print("❌ Error: No se encontró el usuario. Revisa el email en el script.")
            return

        print(f"✅ Usuario encontrado: {mi_usuario.nombre}")

        # 2. CREAR UN TORNEO
        nuevo_torneo = Torneo(
            nombre="Liga de Campeones Zorin",
            tipo="Liga",
            fechas=datetime(2026, 9, 1),
            codigo_acceso="ZORIN-2026", # Añadido
            descripcion="Los partidos de la fase de grupos se jugarán los viernes por la tarde en el Polideportivo Central." # Añadido
        )
        db.session.add(nuevo_torneo)
        db.session.commit() # Guardamos para que se genere su ID
        print("✅ Torneo creado.")

        # 3. Crear dos Equipos (¡AHORA CON CAPITÁN!)
        mi_equipo = Equipo(
            nombre="F.C. Los Desarrolladores", 
            id_capitan=mi_usuario.id_usuario
        )
        equipo_rival = Equipo(
            nombre="Atlético de Bugs", 
            id_capitan=mi_usuario.id_usuario
        )
        db.session.add_all([mi_equipo, equipo_rival])
        db.session.commit()
        print("✅ Equipos creados.")

        # 4. Vincular MI USUARIO a MI EQUIPO en la tabla Pertenece
        vinculo = Pertenece(id_usuario=mi_usuario.id_usuario, id_equipo=mi_equipo.id_equipo)
        db.session.add(vinculo)
        db.session.commit()
        print("✅ Usuario vinculado a su equipo.")

        # 5. Crear el Partido (Para dentro de 2 días)
        fecha_partido = datetime.now() + timedelta(days=2)
        nuevo_partido = Partido(
            id_local=mi_equipo.id_equipo,
            id_visitante=equipo_rival.id_equipo,
            id_torneo=nuevo_torneo.id_torneo,
            fecha=fecha_partido,
            estado='Pendiente'
        )
        db.session.add(nuevo_partido)
        db.session.commit()
        print("✅ Partido programado.")

        # 6. INSCRIBIR A LOS EQUIPOS EN EL TORNEO
        inscripcion_local = Inscripcion(id_equipo=mi_equipo.id_equipo, id_torneo=nuevo_torneo.id_torneo)
        inscripcion_visitante = Inscripcion(id_equipo=equipo_rival.id_equipo, id_torneo=nuevo_torneo.id_torneo)
        
        db.session.add_all([inscripcion_local, inscripcion_visitante])
        db.session.commit()
        print("✅ Equipos inscritos en el torneo.")

        print("🎉 ¡Base de datos poblada con éxito!")

if __name__ == '__main__':
    poblar_base_de_datos()