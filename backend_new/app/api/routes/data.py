from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.services.data_processing import DataProcessor
from app.database import db
from typing import List, Dict, Any
import os
import logging
import traceback
import json
import pandas as pd
from pathlib import Path
from app.api.routes.schemas import PipelineJobCreate, PipelineJobUpdate, PipelineJobResponse
from app.services.supabase_realtime import realtime_service
from app.services.async_processor import async_processor
import uuid
from datetime import datetime
import asyncio

router = APIRouter()

class CleanFileRequest(BaseModel):
    filename: str

# Configurar logger simple para este módulo
logger = logging.getLogger("app.api.routes.data")
if not logger.handlers:
    # Configuración básica: escribir a un archivo de logs bajo la raíz del proyecto
    logs_dir = Path.cwd() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(logs_dir / "server.log")
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # También agregar un handler stdout para visibilidad inmediata en consola
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    logger.setLevel(logging.INFO)

# Funciones auxiliares para gestión de trabajos
def create_pipeline_job(datos_cargados_id: str, tipo_tarea: str) -> str:
    """Crear un nuevo pipeline job y devolver su ID"""
    job_id = str(uuid.uuid4())
    
    insert_query = """
    INSERT INTO pipeline_jobs (id, datos_cargados_id, tipo_tarea, estado, progreso, mensaje_actual, fecha_inicio)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    db.execute_insert(insert_query, (
        job_id,
        datos_cargados_id,
        tipo_tarea,
        "en_progreso",
        0.0,
        "Iniciando tarea...",
        datetime.now()
    ))
    
    logger.info(f"Pipeline job creado: {job_id} para archivo {datos_cargados_id}")
    return job_id

def update_pipeline_job(job_id: str, progress: float, message: str, metrics: Dict = None, estado: str = None):
    """Actualizar el progreso de un pipeline job"""
    update_query = """
    UPDATE pipeline_jobs 
    SET progreso = %s, mensaje_actual = %s, metricas_parciales = %s, updated_at = %s
    """
    params = [progress, message, json.dumps(metrics) if metrics else None, datetime.now()]
    
    if estado:
        update_query += ", estado = %s"
        params.append(estado)
    
    update_query += " WHERE id = %s"
    params.append(job_id)
    
    db.execute_update(update_query, tuple(params))
    logger.info(f"Job {job_id} actualizado: {progress}% - {message}")

def complete_pipeline_job(job_id: str, message: str = "Tarea completada exitosamente"):
    """Marcar un pipeline job como completado"""
    update_query = """
    UPDATE pipeline_jobs 
    SET estado = %s, progreso = %s, mensaje_actual = %s, fecha_fin = %s, updated_at = %s
    WHERE id = %s
    """
    
    db.execute_update(update_query, (
        "completado",
        100.0,
        message,
        datetime.now(),
        datetime.now(),
        job_id
    ))
    logger.info(f"Job {job_id} completado: {message}")

def fail_pipeline_job(job_id: str, error_message: str):
    """Marcar un pipeline job como fallido"""
    update_query = """
    UPDATE pipeline_jobs 
    SET estado = %s, mensaje_actual = %s, fecha_fin = %s, updated_at = %s
    WHERE id = %s
    """
    
    db.execute_update(update_query, (
        "fallido",
        f"Error: {error_message}",
        datetime.now(),
        datetime.now(),
        job_id
    ))
    logger.error(f"Job {job_id} falló: {error_message}")

@router.post("/upload")
async def upload_data(file: UploadFile = File(...)):
    """Subir datos CSV y guardar en disco y base de datos"""
    logger.info(f"[UPLOAD] Iniciando upload de archivo: {file.filename}")
    
    if not file.filename.endswith('.csv'):
        logger.error(f"[UPLOAD] Archivo no es CSV: {file.filename}")
        raise HTTPException(status_code=400, detail="Solo archivos CSV")
    
    try:
        # Leer contenido del archivo
        logger.info(f"[UPLOAD] Leyendo contenido del archivo...")
        content = await file.read()
        logger.info(f"[UPLOAD] Contenido leído: {len(content)} bytes")
        
        # Procesar datos CSV
        logger.info(f"[UPLOAD] Procesando CSV...")
        processor = DataProcessor()
        data_info = processor.load_csv(content, file.filename)
        logger.info(f"[UPLOAD] CSV procesado: {data_info.get('rows', 0)} filas, {data_info.get('columns', 0)} columnas")

        # Generar ID único para el archivo
        file_id = str(uuid.uuid4())
        
        # Crear directorio de uploads si no existe
        uploads_dir = Path.cwd() / "uploads" / "original"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # Guardar archivo en disco
        saved_path = uploads_dir / file.filename
        with open(saved_path, "wb") as f:
            f.write(content)
        
        # Verificar que se guardó correctamente
        if not os.path.exists(saved_path):
            raise Exception(f"No se pudo guardar el archivo en {saved_path}")
        
        # Preparar metadatos
        metadatos = {
            "rows": data_info.get("rows", 0),
            "columns": data_info.get("columns", 0),
            "file_size": len(content),
            "upload_timestamp": datetime.now().isoformat(),
            "storage_url": str(saved_path)
        }
        
        # Guardar en base de datos (usando solo las columnas que existen)
        logger.info(f"[UPLOAD] Guardando en base de datos...")
        logger.info(f"[UPLOAD] Conexión a BD: {db.connection is not None}")
        
        if not db.connection:
            logger.error(f"[UPLOAD] No hay conexión a la base de datos")
            raise HTTPException(status_code=500, detail="No hay conexión a la base de datos")
        
        insert_query = """
        INSERT INTO datos_cargados (id, nombre_archivo, ruta_archivo, tamano_archivo, metadatos, estado)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        db.execute_insert(insert_query, (
            file_id,
            file.filename,
            str(saved_path),
            len(content),
            json.dumps(metadatos),
            'cargado'
        ))
        logger.info(f"[UPLOAD] Guardado en BD exitosamente")
        
        logger.info(f"Archivo '{file.filename}' subido y guardado correctamente con ID: {file_id}")
        
        return {
            "message": "Archivo subido correctamente",
            "data_info": data_info,
            "file_id": file_id,
            "storage_url": str(saved_path),
            "status": "uploaded"
        }

    except Exception as e:
        logger.error(f"[UPLOAD] Error en upload_data: {e}")
        import traceback
        logger.error(f"[UPLOAD] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error procesando archivo: {e}")


def _resolve_dataset_path(raw_path: str) -> str:
    """Resolve a dataset path stored in DB. Accepts absolute paths or relative paths like '/uploads/file.csv' or 'uploads/file.csv'."""
    # If already exists, return
    if os.path.exists(raw_path):
        return raw_path

    # Strip leading slash and try relative to cwd
    candidate = raw_path.lstrip('/\\')
    candidate_path = Path.cwd() / candidate
    if candidate_path.exists():
        return str(candidate_path)

    # Try as-is (maybe windows drive path with leading /)
    alt = raw_path.lstrip('/')
    if os.path.exists(alt):
        return alt

    # Not found — return original so caller can raise a clear error
    return raw_path



@router.get("/test")
async def test_endpoint():
    """Endpoint de prueba"""
    return {"message": "Servidor funcionando correctamente", "status": "ok"}

@router.get("/uploaded-files")
async def get_uploaded_files():
    """Obtener archivos subidos desde la base de datos, incluyendo los limpiados"""
    try:
        # Verificar conexión a la base de datos
        if not db.connection:
            logger.warning("No hay conexión a la base de datos - devolviendo lista vacía")
            return []
            
        query = """
        SELECT id, nombre_archivo, ruta_archivo, tamano_archivo, created_at, estado, metadatos
        FROM datos_cargados
        WHERE estado IN ('cargado', 'limpiado')
        ORDER BY created_at DESC
        """
        files = db.execute_query(query)
        
        logger.info(f"Archivos encontrados en BD: {len(files)}")
        
        result = []
        for file in files:
            file_dict = dict(file)
            logger.info(f"Procesando archivo: {file_dict['nombre_archivo']} - Ruta: {file_dict['ruta_archivo']}")

            ruta = file_dict["ruta_archivo"]

            # Si no existe en la ruta original, intentar buscar en carpetas conocidas
            if not os.path.exists(ruta):
                alt_paths = [
                    os.path.join("uploads", "original", file_dict["nombre_archivo"]),
                    os.path.join("uploads", "cleaned", file_dict["nombre_archivo"]),
                ]
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        ruta = alt_path
                        break

            # ✅ Siempre devolvemos el registro, incluso si no está el archivo en disco
            if not os.path.exists(ruta):
                logger.warning(f"⚠️ Archivo no encontrado en disco: {ruta}")
            
            result.append({
                "id": file_dict["id"],
                "filename": file_dict["nombre_archivo"],
                "path": ruta,
                "size": file_dict["tamano_archivo"],
                "modified": file_dict["created_at"].timestamp(),
                "estado": file_dict["estado"],
                "metadatos": file_dict["metadatos"]
            })
            
            logger.info(f"Archivo agregado a resultado: {file_dict['nombre_archivo']} (estado={file_dict['estado']})")
        
        logger.info(f"Total archivos devueltos: {len(result)}")
        return result

    except Exception as e:
        logger.error(f"Error en get_uploaded_files: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []





@router.post("/clean-data/{file_id}")
async def clean_data_from_database(file_id: str):
    """Limpiar datos desde tabla datos_cargados y guardar en datos_limpiados"""
    try:
        # Obtener archivo desde datos_cargados
        query = """
        SELECT id, nombre_archivo, ruta_archivo, metadatos
        FROM datos_cargados
        WHERE id = %s
        """
        files = db.execute_query(query, (file_id,))
        
        if not files:
            raise HTTPException(status_code=404, detail="Archivo no encontrado en la base de datos")
        
        file_data = dict(files[0])
        file_path = file_data["ruta_archivo"]
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Archivo no encontrado en disco: {file_path}")
        
        # Cargar y limpiar datos
        processor = DataProcessor()
        processor.load_csv_from_path(file_path)
        cleaning_report = processor.clean_data()
        
        # Generar nombre de archivo limpio con formato: cleaned_ventas_35#eti.csv
        import re
        original_name = file_data["nombre_archivo"]
        name_without_ext = original_name.replace('.csv', '')
        # Crear hash corto para el nombre
        short_hash = str(uuid.uuid4())[:8]
        cleaned_filename = f"cleaned_{name_without_ext}_{short_hash}.csv"
        
        # Guardar en carpeta cleaned
        cleaned_dir = Path.cwd() / "uploads" / "cleaned"
        cleaned_dir.mkdir(parents=True, exist_ok=True)
        cleaned_path = cleaned_dir / cleaned_filename
        
        cleaned_data = processor.get_cleaned_data()
        cleaned_data.to_csv(cleaned_path, index=False)
        
        # Guardar en tabla datos_limpiados
        import uuid
        cleaned_id = str(uuid.uuid4())
        
        estadisticas_limpieza = {
            "duplicados_eliminados": cleaning_report.get("duplicates_removed", 0),
            "nulos_eliminados": cleaning_report.get("nulls_removed", 0),
            "filas_originales": cleaning_report.get("original_rows", 0),
            "filas_limpias": cleaning_report.get("cleaned_rows", 0),
            "columnas": cleaning_report.get("columns", 0)
        }
        
        insert_query = """
        INSERT INTO datos_limpiados (id, nombre_archivo_original, nombre_archivo_limpio, ruta_archivo_limpio, datos_cargados_id, estadisticas_limpieza)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        db.execute_insert(insert_query, (
            cleaned_id,
            file_data["nombre_archivo"],
            cleaned_filename,
            str(cleaned_path),
            file_id,
            json.dumps(estadisticas_limpieza)  # Convertir dict a JSON string
        ))
        
        logger.info(f"Datos limpiados guardados con ID: {cleaned_id}")
        return {
            "message": "Datos limpiados y guardados en Supabase",
            "cleaning_report": cleaning_report,
            "cleaned_file": cleaned_filename,
            "cleaned_path": str(cleaned_path),
            "cleaned_id": cleaned_id,
            "estadisticas": estadisticas_limpieza
        }
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error en clean_data_from_database: {e}\n{tb}")
        raise HTTPException(status_code=500, detail=f"Error limpiando datos: {e}")

@router.get("/cleaned-files")
async def get_cleaned_files():
    """Obtener archivos limpiados desde la base de datos (tabla datos_limpiados)"""
    try:
        query = """
        SELECT dl.id,
               dl.datos_cargados_id,  -- 👈 Agregado: relación con el archivo original
               dl.nombre_archivo_original,
               dl.nombre_archivo_limpio,
               dl.ruta_archivo_limpio,
               dl.created_at,
               dl.estadisticas_limpieza,
               dl.estado,
               dc.nombre_archivo AS archivo_original
        FROM datos_limpiados dl
        LEFT JOIN datos_cargados dc ON dl.datos_cargados_id = dc.id
        ORDER BY dl.created_at DESC
        """
        files = db.execute_query(query)
        
        result = []
        for file in files:
            file_dict = dict(file)
            
            # Obtener columnas del archivo
            columnas = []
            try:
                import pandas as pd
                file_path = file_dict["ruta_archivo_limpio"]
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path, nrows=0)  # Solo leer headers
                    columnas = df.columns.tolist()
            except Exception as e:
                logger.warning(f"No se pudieron obtener columnas del archivo {file_dict['nombre_limpio']}: {e}")
                columnas = []
            
            result.append({
                "id": file_dict["id"],
                "datos_cargados_id": file_dict["datos_cargados_id"],  # 👈 necesario para el frontend
                "nombre_original": file_dict["nombre_archivo_original"],
                "nombre_limpio": file_dict["nombre_archivo_limpio"],
                "path": file_dict["ruta_archivo_limpio"],
                "modified": file_dict["created_at"].timestamp(),
                "estado": file_dict.get("estado", "limpiado"),
                "estadisticas": file_dict["estadisticas_limpieza"],
                "columnas": columnas  # 👈 Agregar columnas disponibles
            })
        
        return result
    except Exception as e:
        logger.error(f"Error al listar archivos limpiados: {e}")
        raise HTTPException(status_code=500, detail=f"Error al listar archivos limpiados: {e}")

@router.get("/preview-file/{filename}")
async def get_file_preview(filename: str, limit: int = 10):
    """
    Obtener vista previa de un archivo CSV.
    Busca primero en 'uploads/original', luego en 'uploads/cleaned'.
    """
    try:
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        uploads_dir = base_dir / "uploads"
        original_path = uploads_dir / "original" / filename
        cleaned_path = uploads_dir / "cleaned" / filename

        print(f"[DEBUG] Buscando archivo: {filename}")
        print(f"[DEBUG] Ruta original: {original_path}")
        print(f"[DEBUG] Ruta cleaned:  {cleaned_path}")

        # Verificar existencia en ambas rutas
        if original_path.exists():
            file_path = original_path
            print(f"[DEBUG] Archivo encontrado en ORIGINAL")
        elif cleaned_path.exists():
            file_path = cleaned_path
            print(f"[DEBUG] Archivo encontrado en CLEANED")
        else:
            print(f"[ERROR] Archivo no encontrado en ninguna ruta")
            raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {filename}")

        # Leer CSV
        data = pd.read_csv(file_path)
        preview_data = data.head(limit).to_dict("records")

        print(f"[DEBUG] Vista previa generada correctamente ({len(preview_data)} filas)")

        return {
            "filename": filename,
            "rows": len(data),
            "columns": len(data.columns),
            "preview": preview_data,
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {filename}")
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail=f"Archivo vacío o corrupto: {filename}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en preview: {str(e)}")

@router.get("/preview-cleaned/{filename}")
async def get_cleaned_file_preview(filename: str, limit: int = 10):
    """Obtener vista previa de un archivo limpiado (carpeta uploads/cleaned)"""
    try:
        file_path = Path.cwd() / "uploads" / "cleaned" / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Archivo limpio no encontrado: {filename}")

        import pandas as pd
        data = pd.read_csv(file_path)

        preview_data = data.head(limit).to_dict('records')

        return {
            "filename": filename,
            "rows": len(data),
            "columns": len(data.columns),
            "preview": preview_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en preview de limpio: {str(e)}")



@router.delete("/delete-file/{file_id}")
async def delete_uploaded_file(file_id: str):
    """
    Eliminar un dataset original (tabla datos_cargados) sin afectar sus copias limpiadas.
    """
    try:
        logger.info(f"Iniciando eliminación de dataset: {file_id}")
        
        # Buscar el dataset en la tabla datos_cargados
        query = """
        SELECT id, nombre_archivo, ruta_archivo
        FROM datos_cargados
        WHERE id = %s
        """
        files = db.execute_query(query, (file_id,))
        
        if not files:
            raise HTTPException(status_code=404, detail="Dataset no encontrado")
        
        dataset = dict(files[0])
        file_path = dataset["ruta_archivo"]

        # Eliminar dependencias relacionadas primero (para evitar violación de FK)
        # Usar una transacción para asegurar que todas las eliminaciones se ejecuten correctamente
        try:
            with db.connection.cursor() as cursor:
                # 1. Eliminar jobs relacionados
                jobs_delete_query = "DELETE FROM pipeline_jobs WHERE datos_cargados_id = %s"
                cursor.execute(jobs_delete_query, (file_id,))
                jobs_deleted = cursor.rowcount
                logger.info(f"Jobs relacionados eliminados: {jobs_deleted}")
                
                # 2. Eliminar datos limpiados relacionados
                cleaned_delete_query = "DELETE FROM datos_limpiados WHERE datos_cargados_id = %s"
                cursor.execute(cleaned_delete_query, (file_id,))
                cleaned_deleted = cursor.rowcount
                logger.info(f"Datos limpiados relacionados eliminados: {cleaned_deleted}")
                
                # 3. Eliminar el registro principal
                delete_query = "DELETE FROM datos_cargados WHERE id = %s"
                cursor.execute(delete_query, (file_id,))
                main_deleted = cursor.rowcount
                logger.info(f"Registro principal eliminado: {main_deleted}")
                
                # Confirmar todas las operaciones
                db.connection.commit()
                logger.info(f"Transacción completada exitosamente para dataset: {file_id}")
                
        except Exception as e:
            logger.error(f"Error en transacción de eliminación: {e}")
            db.connection.rollback()
            raise HTTPException(status_code=500, detail=f"Error eliminando dataset: {e}")

        # Eliminar el archivo físico si existe
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Archivo físico eliminado: {file_path}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar el archivo físico: {file_path} ({e})")
        
        logger.info(f"Dataset eliminado correctamente: {dataset['nombre_archivo']} ({file_id})")
        return {"message": f"Dataset '{dataset['nombre_archivo']}' eliminado correctamente"}

    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error al eliminar dataset: {e}\n{tb}")
        raise HTTPException(status_code=500, detail=f"Error al eliminar dataset: {str(e)}")

# ===== ENDPOINTS PARA GESTIÓN DE JOBS =====

@router.post("/jobs/clean-data/{file_id}")
async def start_clean_data_job(file_id: str):
    """Iniciar limpieza de datos"""
    try:
        # Verificar que el archivo existe
        query = """
        SELECT id, nombre_archivo, ruta_archivo, metadatos
        FROM datos_cargados
        WHERE id = %s
        """
        files = db.execute_query(query, (file_id,))

        if not files:
            raise HTTPException(status_code=404, detail="Archivo no encontrado en la base de datos")

        file_data = dict(files[0])
        file_path = file_data["ruta_archivo"]

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Archivo no encontrado en disco: {file_path}")

        # Crear job de limpieza
        job_id = create_pipeline_job(file_id, "limpieza")
        logger.info(f"Job de limpieza creado: {job_id} para archivo: {file_data['nombre_archivo']}")

        # Iniciar procesamiento asíncrono
        asyncio.create_task(async_processor.process_cleaning_job(file_id, job_id))

        return {
            "message": "Limpieza iniciada",
            "job_id": job_id,
            "file_id": file_id,
            "status": "processing"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en start_clean_data_job: {e}")
        raise HTTPException(status_code=500, detail=f"Error en limpieza: {str(e)}")

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Obtener el estado actual de un job"""
    try:
        query = """
        SELECT id, datos_cargados_id, tipo_tarea, estado, progreso, mensaje_actual, 
               metricas_parciales, fecha_inicio, fecha_fin, created_at, updated_at
        FROM pipeline_jobs
        WHERE id = %s
        """
        jobs = db.execute_query(query, (job_id,))
        
        if not jobs:
            raise HTTPException(status_code=404, detail="Job no encontrado")
        
        job = dict(jobs[0])
        return PipelineJobResponse(**job)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo job: {e}")

@router.get("/jobs/file/{file_id}")
async def get_jobs_by_file(file_id: str):
    """Obtener todos los jobs de un archivo específico"""
    try:
        query = """
        SELECT id, datos_cargados_id, tipo_tarea, estado, progreso, mensaje_actual, 
               metricas_parciales, fecha_inicio, fecha_fin, created_at, updated_at
        FROM pipeline_jobs
        WHERE datos_cargados_id = %s
        ORDER BY created_at DESC
        """
        jobs = db.execute_query(query, (file_id,))
        
        return [PipelineJobResponse(**dict(job)) for job in jobs]
        
    except Exception as e:
        logger.error(f"Error obteniendo jobs para archivo {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo jobs: {e}")

@router.get("/jobs")
async def get_all_jobs():
    """Obtener todos los jobs del sistema"""
    try:
        query = """
        SELECT pj.id, pj.datos_cargados_id, pj.tipo_tarea, pj.estado, pj.progreso, pj.mensaje_actual, 
               pj.metricas_parciales, pj.fecha_inicio, pj.fecha_fin, pj.created_at, pj.updated_at,
               dc.nombre_archivo
        FROM pipeline_jobs pj
        LEFT JOIN datos_cargados dc ON pj.datos_cargados_id = dc.id
        ORDER BY pj.created_at DESC
        """
        jobs = db.execute_query(query)
        
        result = []
        for job in jobs:
            job_dict = dict(job)
            result.append({
                **job_dict,
                "archivo_nombre": job_dict.get("nombre_archivo", "Desconocido")
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error obteniendo todos los jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo jobs: {e}")

@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Eliminar un job específico"""
    try:
        query = "DELETE FROM pipeline_jobs WHERE id = %s"
        result = db.execute_update(query, (job_id,))
        
        if result == 0:
            raise HTTPException(status_code=404, detail="Job no encontrado")
        
        return {"message": f"Job {job_id} eliminado correctamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error eliminando job: {e}")

