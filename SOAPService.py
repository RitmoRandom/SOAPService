from spyne import Application, rpc, ServiceBase, Integer, Unicode, Date, Iterable
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
import sqlite3
import os
from datetime import datetime, timedelta, date

db_path = 'availability.db'
# Configuración inicial para SQLite
def init_db():
    if not os.path.exists(db_path):
        return "Base de datos no encontrada."
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS availability (
                room_id INTEGER NOT NULL,
                room_type TEXT NOT NULL,
                available_date DATE NOT NULL,
                status TEXT NOT NULL,
                CHECK (room_id > 0)
            )
        ''')
        conn.commit()

    

# Inicializamos la base de datos
init_db()

# Definición del servicio SOAP
class AvailabilityService(ServiceBase):

    @rpc(Integer, Unicode, _returns=Unicode)
    def add_availability(ctx, room_id, room_type):
        """
        Agrega una nueva entrada a la tabla availability.
        """
        try:
            if not os.path.exists(db_path):
                return "Base de datos no encontrada."
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                today = datetime.now().date()
                for i in range(15):
                    available_date = today + timedelta(days=i)
                    # Insertar registro para cada día
                    cursor.execute("""
                        INSERT INTO availability (room_id, room_type, available_date, status)
                        VALUES (?, ?, ?, ?)
                    """, (room_id, room_type, available_date, 'available'))
                
                conn.commit()
            return "Disponibilidad agregada exitosamente."
        except Exception as e:
            return f"Error al agregar disponibilidad: {str(e)}"

    @rpc(Unicode, Date, Date, _returns=Iterable(Unicode))
    def get_availability(ctx, tipo, fecha_inicio, fecha_fin):
        """
        Obtiene disponibilidad
        """
        try:
            fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d') if isinstance(fecha_inicio, date) else fecha_inicio
            fecha_fin_str = fecha_fin.strftime('%Y-%m-%d') if isinstance(fecha_fin, date) else fecha_fin
            if not os.path.exists(db_path):
                return "Base de datos no encontrada."
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                total_dias = (fecha_fin - fecha_inicio).days + 1
                cursor.execute("""
                    SELECT room_id, room_type FROM availability WHERE status = 'available' AND room_type = ? AND available_date BETWEEN ? AND ? GROUP BY room_id, room_type HAVING COUNT(DISTINCT available_date) = ?
                """, (tipo,fecha_inicio_str, fecha_fin_str,total_dias))
                rows = cursor.fetchall()
            if not rows:
                return ["No hay habitaciones disponibles."]
            return [f"Room ID: {row[0]}, Room Type: {row[1]}" for row in rows]
        except Exception as e:
            return [f"Error al obtener disponibilidad: {str(e)}"]

    @rpc(Integer, Date, Date, Unicode, _returns=Unicode)
    def update_status(ctx, room_id, fecha_inicio, fecha_fin, accion):
        """
        Actualiza el estado de disponibilidad para una fecha específica y un room_id.
        """
        try:
            fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d') if isinstance(fecha_inicio, date) else fecha_inicio
            fecha_fin_str = fecha_fin.strftime('%Y-%m-%d') if isinstance(fecha_fin, date) else fecha_fin
            if not os.path.exists(db_path):
                return "Base de datos no encontrada."
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE availability
                    SET status = ?
                    WHERE room_id = ? AND available_date BETWEEN ? AND ?
                """, (accion,room_id, fecha_inicio_str, fecha_fin_str))
                conn.commit()
            if cursor.rowcount == 0:
                return "No se encontró el registro para actualizar."
            return "Estado actualizado exitosamente."
        except Exception as e:
            return f"Error al actualizar estado: {str(e)}"

# Configuración de la aplicación SOAP
application = Application([
    AvailabilityService
],
    tns="spyne.examples.availability",
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

# Servidor WSGI
if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    wsgi_app = WsgiApplication(application)
    server = make_server('0.0.0.0', 5000, wsgi_app)
    print("Servidor SOAP corriendo en http://localhost:5000")
    server.serve_forever()
