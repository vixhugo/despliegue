import asyncio
import pandas as pd
from pathlib import Path
import uuid
import json
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from app.services.data_processing import DataProcessor
from app.services.supabase_realtime import realtime_service
from app.database import db

logger = logging.getLogger(__name__)

class AsyncDataProcessor:
    """Procesador asíncrono de datos con seguimiento en tiempo real"""
    
    def __init__(self):
        self.active_jobs: Dict[str, Dict] = {}
    
    async def process_cleaning_job(self, file_id: str, job_id: str) -> Dict[str, Any]:
        """Procesar job de limpieza de forma asíncrona"""
        try:
            # 1. Obtener información del archivo
            file_info = await self._get_file_info(file_id)
            if not file_info:
                realtime_service.fail_job(job_id, "Archivo no encontrado")
                return {"error": "Archivo no encontrado"}
            
            # 2. Actualizar estado a "en_progreso"
            realtime_service.update_job(job_id, 5.0, "Iniciando descarga del archivo...", None, "en_progreso")
            
            # 3. Usar archivo local directamente
            local_path = file_info["local_path"]
            if not local_path or not Path(local_path).exists():
                realtime_service.fail_job(job_id, "Archivo local no encontrado")
                return {"error": "Archivo local no encontrado"}
            
            # 4. Procesar datos con callbacks de progreso
            realtime_service.update_job_progress(job_id, 10.0, "Cargando datos en memoria...")
            
            processor = DataProcessor()
            processor.load_csv_from_path(local_path)
            
            # Configurar callback para actualizar progreso
            def progress_callback(job_id: str, progress: float, message: str, metrics: Dict = None):
                adjusted_progress = 10 + (progress * 0.8)
                realtime_service.update_job(job_id, adjusted_progress, message, metrics, "en_progreso")
            
            processor.set_progress_callback(progress_callback, job_id)
            
            # 5. Ejecutar limpieza
            cleaning_report = processor.clean_data()
            
            # 6. Guardar archivo limpio
            realtime_service.update_job_progress(job_id, 85.0, "Guardando archivo limpio...")
            
            cleaned_file_info = await self._save_cleaned_file(
                processor.get_cleaned_data(),
                file_info["nombre_archivo"],
                file_id
            )
            
            # 7. Registrar en base de datos el archivo limpio
            realtime_service.update_job_progress(job_id, 90.0, "Registrando resultados...")
            
            cleaned_id = await self._register_cleaned_data(
                file_id,
                file_info["nombre_archivo"],
                cleaned_file_info,
                cleaning_report
            )
            
            # 8. Actualizar estado del archivo original (mantenerlo en disco)
            try:
                db.execute_update("""
                    UPDATE datos_cargados
                    SET estado = 'limpiado',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (file_id,))
                logger.info(f"Archivo original marcado como 'limpiado': {file_info['nombre_archivo']}")
            except Exception as e:
                logger.warning(f"No se pudo actualizar el estado del archivo original: {e}")
            
            # 9. Completar job incluyendo metadatos útiles para el frontend
            frontend_metrics = {
                "cleaned_id": cleaned_id,
                "cleaned_filename": cleaned_file_info.get("filename"),
                "cleaned_path": cleaned_file_info.get("storage_url"),
                "original_filename": file_info.get("nombre_archivo"),
                "original_file_id": file_id,
            }
            
            if cleaning_report:
                frontend_metrics.update({
                    "filas_originales": cleaning_report.get("original_rows", 0),
                    "filas_limpias": cleaning_report.get("final_rows", 0),
                    "duplicados_eliminados": cleaning_report.get("duplicates_removed", 0),
                    "nulos_eliminados": cleaning_report.get("nulls_removed", 0),
                    "nulls_filled": cleaning_report.get("null_values_filled", 0),  # ← AGREGADO
                    "outliers_removed": cleaning_report.get("outliers_removed", 0),  # ← AGREGADO
                    "columnas": len(processor.get_cleaned_data().columns),
                    "preview": cleaning_report.get("preview", [])
                })
            
            realtime_service.complete_job(
                job_id,
                "Limpieza completada exitosamente",
                metrics=frontend_metrics
            )
            
            # 10. Retornar resultado
            return {
                "job_id": job_id,
                "cleaned_id": cleaned_id,
                "cleaning_report": cleaning_report,
                "cleaned_file": cleaned_file_info["filename"],
                "storage_url": cleaned_file_info["storage_url"]
            }
            
        except Exception as e:
            logger.error(f"Error processing cleaning job {job_id}: {e}")
            realtime_service.fail_job(job_id, str(e))
            return {"error": str(e)}
    
    async def _get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Obtener información del archivo desde la base de datos"""
        try:
            query = """
            SELECT id, nombre_archivo, ruta_archivo, metadatos
            FROM datos_cargados
            WHERE id = %s
            """
            files = db.execute_query(query, (file_id,))
            
            if not files:
                return None
            
            file_data = dict(files[0])
            
            return {
                "id": file_data["id"],
                "nombre_archivo": file_data["nombre_archivo"],
                "storage_path": None,
                "local_path": file_data["ruta_archivo"]
            }
                
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None
    
    async def _save_cleaned_file(self, cleaned_data: pd.DataFrame, original_filename: str, file_id: str) -> Dict[str, str]:
        """Guardar archivo limpio en carpeta 'uploads/cleaned'"""
        try:
            name_without_ext = original_filename.replace('.csv', '')
            short_hash = str(uuid.uuid4())[:8]
            cleaned_filename = f"cleaned_{name_without_ext}_{short_hash}.csv"
            
            cleaned_dir = Path.cwd() / "uploads" / "cleaned"
            cleaned_dir.mkdir(parents=True, exist_ok=True)
            final_path = cleaned_dir / cleaned_filename
            cleaned_data.to_csv(final_path, index=False)
            
            return {
                "filename": cleaned_filename,
                "storage_path": str(final_path),
                "storage_url": str(final_path)
            }
            
        except Exception as e:
            logger.error(f"Error saving cleaned file: {e}")
            return {"filename": "", "storage_path": "", "storage_url": ""}
    
    async def _register_cleaned_data(self, file_id: str, original_filename: str, cleaned_file_info: Dict, cleaning_report: Dict) -> str:
        """Registrar datos limpiados en la base de datos"""
        try:
            cleaned_id = str(uuid.uuid4())
            
            estadisticas_limpieza = {
                "duplicados_eliminados": cleaning_report.get("duplicates_removed", 0),
                "nulos_eliminados": cleaning_report.get("nulls_removed", 0),
                "filas_originales": cleaning_report.get("original_rows", 0),
                "filas_limpias": cleaning_report.get("final_rows", 0),
                "columnas": cleaning_report.get("normalized_columns", [])
            }
            
            insert_query = """
            INSERT INTO datos_limpiados (id, nombre_archivo_original, nombre_archivo_limpio, ruta_archivo_limpio, datos_cargados_id, estadisticas_limpieza)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            db.execute_insert(insert_query, (
                cleaned_id,
                original_filename,
                cleaned_file_info["filename"],
                cleaned_file_info["storage_url"],
                file_id,
                json.dumps(estadisticas_limpieza)
            ))
            
            return cleaned_id
            
        except Exception as e:
            logger.error(f"Error registering cleaned data: {e}")
            return ""

# Instancia global
async_processor = AsyncDataProcessor()
