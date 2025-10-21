import os
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Cargar el archivo .env desde la raíz del backend
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

print("Leyendo variables de entorno...")
print("DATABASE_URL:", os.getenv("DATABASE_URL"))

class Database:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Conectar a Supabase PostgreSQL (Transaction Pooler)"""
        try:
            db_url = os.getenv("DATABASE_URL")
            if db_url:
                self.connection = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
                print("Conectado exitosamente a Supabase (Transaction Pooler)")
            else:
                print("DATABASE_URL no configurada - modo simulación")
                self.connection = None
        except Exception as e:
            print(f"Error conectando a Supabase: {e}")
            print("Continuando en modo simulación...")
            self.connection = None
    
    def execute_query(self, query: str, params: tuple = None):
        if not self.connection:
            print("No hay conexion a la base de datos - devolviendo datos simulados")
            return []
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except psycopg2.OperationalError as e:
            print(f"Error de conexion a la base de datos: {e}")
            self.connect()  # Intentar reconectar
            return []
        except psycopg2.ProgrammingError as e:
            print(f"Error en la consulta SQL: {e}")
            self.connection.rollback()  # Rollback en caso de error
            raise
        except Exception as e:
            print(f"Error ejecutando consulta: {e}")
            self.connection.rollback()  # Rollback en caso de error
            raise
    
    def execute_insert(self, query: str, params: tuple = None):
        # Requiere una conexión real a la BD para inserts en producción/desarrollo.
        if not self.connection:
            raise ConnectionError("No hay conexión a la base de datos. No se puede ejecutar INSERT.")
        try:
            print(f"Ejecutando INSERT: {query} | params={params}")
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                self.connection.commit()
                return None
        except Exception as e:
            print(f"Error ejecutando insert: {e}")
            self.connection.rollback()
            raise
    
    def execute_update(self, query: str, params: tuple = None):
        if not self.connection:
            return 1
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                self.connection.commit()
                return cursor.rowcount
        except Exception as e:
            print(f"Error ejecutando update: {e}")
            self.connection.rollback()
            raise
    
    def close(self):
        if self.connection:
            self.connection.close()

# Instancia global
db = Database()