import os
import json
import logging
from typing import Dict, Any, Optional
from app.database import db

logger = logging.getLogger(__name__)

class SupabaseRealtimeService:
    """Servicio para manejar actualizaciones en tiempo real con Supabase"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase credentials not found. Realtime operations will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            self.headers = {
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json",
                "apikey": self.supabase_key
            }
    
    def update_job_progress(self, job_id: str, progress: float, message: str, metrics: Optional[Dict] = None) -> bool:
        """Actualizar progreso de un job en la base de datos"""
        try:
            update_query = """
            UPDATE pipeline_jobs 
            SET progreso = %s, mensaje_actual = %s, metricas_parciales = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """
            
            db.execute_update(update_query, (
                progress,
                message,
                json.dumps(metrics) if metrics else None,
                job_id
            ))
            
            logger.info(f"Job {job_id} updated: {progress}% - {message}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating job {job_id}: {e}")
            return False
    
    def update_job(self, job_id: str, progress: float, message: str, metrics: Optional[Dict] = None, estado: str = None) -> bool:
        """Actualizar trabajo con progreso, mensaje y opcionalmente estado"""
        try:
            update_query = """
            UPDATE pipeline_jobs 
            SET progreso = %s, mensaje_actual = %s, metricas_parciales = %s, updated_at = CURRENT_TIMESTAMP
            """
            params = [progress, message, json.dumps(metrics) if metrics else None]
            
            if estado:
                update_query += ", estado = %s"
                params.append(estado)
            
            update_query += " WHERE id = %s"
            params.append(job_id)
            
            db.execute_update(update_query, tuple(params))
            logger.info(f"Job {job_id} updated: {progress}% - {message}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating job {job_id}: {e}")
            return False
    
    def complete_job(self, job_id: str, message: str = "Tarea completada exitosamente", metrics: Dict = None) -> bool:
        """Marcar un trabajo como completado con métricas finales"""
        try:
            update_query = """
            UPDATE pipeline_jobs 
            SET estado = %s, progreso = %s, mensaje_actual = %s, metricas_parciales = %s, fecha_fin = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """
            
            metrics_json = json.dumps(metrics) if metrics else None
            
            db.execute_update(update_query, (
                "completado",
                100.0,
                message,
                metrics_json,
                job_id
            ))
            
            logger.info(f"Job {job_id} completed: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing job {job_id}: {e}")
            return False
    
    def fail_job(self, job_id: str, error_message: str) -> bool:
        """Marcar un trabajo como fallido"""
        try:
            update_query = """
            UPDATE pipeline_jobs 
            SET estado = %s, mensaje_actual = %s, fecha_fin = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """
            
            db.execute_update(update_query, (
                "fallido",
                f"Error: {error_message}",
                job_id
            ))
            
            logger.error(f"Job {job_id} failed: {error_message}")
            return True
            
        except Exception as e:
            logger.error(f"Error failing job {job_id}: {e}")
            return False
    
    def create_job(self, datos_cargados_id: str, tipo_tarea: str) -> Optional[str]:
        """Crear un nuevo trabajo y devolver su ID"""
        try:
            # Verificar conexión a la base de datos
            if not db.connection:
                logger.warning("No hay conexión a la base de datos - no se puede crear trabajo")
                return None
                
            import uuid
            from datetime import datetime
            
            job_id = str(uuid.uuid4())
            
            insert_query = """
            INSERT INTO pipeline_jobs (id, datos_cargados_id, tipo_tarea, estado, progreso, mensaje_actual, fecha_inicio)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            db.execute_insert(insert_query, (
                job_id,
                datos_cargados_id,
                tipo_tarea,
                "pendiente",
                0.0,
                "Job creado, esperando inicio...",
                datetime.now()
            ))
            
            logger.info(f"Trabajo creado: {job_id} para archivo {datos_cargados_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error creando trabajo: {e}")
            return None

# Instancia global
realtime_service = SupabaseRealtimeService()