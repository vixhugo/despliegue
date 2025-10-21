from fastapi import APIRouter, HTTPException
from app.services.ml_models import MLModelsService
from typing import List, Dict, Any

router = APIRouter()
ml_service = MLModelsService()

@router.get("/models")
async def get_models():
    """Obtener todos los modelos entrenados desde la base de datos"""
    try:
        from app.database import db
        
        print(f"[RESULTS] Obteniendo modelos desde la base de datos...")
        
        query = """
        SELECT id, datos_limpiados_id, nombre_modelo, tipo_modelo, 
               metricas_entrenamiento, configuracion_modelo, estado, created_at
        FROM modelos_entrenados
        ORDER BY created_at DESC
        """
        
        models = db.execute_query(query)
        print(f"[RESULTS] Modelos encontrados: {len(models)}")
        
        result = []
        for model in models:
            model_dict = dict(model)
            metrics = model_dict.get('metricas_entrenamiento', {})
            
            print(f"[RESULTS] Procesando modelo: {model_dict['id']}")
            print(f"[RESULTS] Métricas: {metrics}")
            
            result.append({
                "id": model_dict["id"],
                "dataset_id": model_dict["datos_limpiados_id"],
                "datos_exportados": {
                    "model_path": f"models/model_{model_dict['id']}.joblib",
                    "model_type": model_dict["tipo_modelo"]
                },
                "metricas_entrenamiento": metrics,
                "fecha_entrenamiento": model_dict["created_at"].isoformat() if model_dict["created_at"] else None,
                "status": model_dict["estado"],
                "saved_to_db": True,
                "accuracy": metrics.get('accuracy', 0),
                "model_type": model_dict["tipo_modelo"]
            })
        
        print(f"[RESULTS] Devolviendo {len(result)} modelos")
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar modelos: {e}")

@router.get("/metrics/{model_id}")
async def get_model_metrics(model_id: str):
    """Obtener métricas de evaluación de un modelo desde Supabase"""
    try:
        from app.database import db
        
        query = """
        SELECT metricas_entrenamiento, confusion_matrix
        FROM modelos_entrenados
        WHERE id = %s
        """
        
        models = db.execute_query(query, (model_id,))
        
        if not models:
            raise HTTPException(status_code=404, detail="Modelo no encontrado")
        
        model_data = dict(models[0])
        return model_data['metricas_entrenamiento']
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar métricas: {e}")

@router.get("/training-history/{model_id}")
async def get_training_history(model_id: str):
    """Obtener historial de entrenamiento de un modelo"""
    # Buscar en modelos entrenados en memoria
    model_data = ml_service.trained_models.get(model_id)
    if model_data and 'metricas_entrenamiento' in model_data:
        # Para Random Forest, crear un historial simple basado en las métricas reales
        accuracy = model_data['metricas_entrenamiento'].get('accuracy', 0)
        return [
            {"epoch": 1, "accuracy": accuracy, "loss": 1 - accuracy}
        ]
    
    # Si no se encuentra, devolver error
    raise HTTPException(status_code=404, detail="Modelo no encontrado o no entrenado")

@router.get("/confusion-matrix/{model_id}")
async def get_confusion_matrix(model_id: str):
    """Obtener matriz de confusión de un modelo desde Supabase"""
    try:
        from app.database import db
        
        query = """
        SELECT confusion_matrix, configuracion_modelo
        FROM modelos_entrenados
        WHERE id = %s
        """
        
        models = db.execute_query(query, (model_id,))
        
        if not models:
            raise HTTPException(status_code=404, detail="Modelo no encontrado")
        
        model_data = dict(models[0])
        configuracion = model_data.get('configuracion_modelo', {})
        
        return {
            "confusion_matrix": model_data['confusion_matrix'],
            "class_labels": configuracion.get('class_labels', [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar matriz de confusión: {e}")

@router.get("/performance-comparison")
async def get_performance_comparison():
    """Obtener comparación de rendimiento entre modelos desde Supabase"""
    try:
        from app.database import db
        
        query = """
        SELECT id, nombre_modelo, tipo_modelo, metricas_entrenamiento, fecha_entrenamiento
        FROM modelos_entrenados
        ORDER BY fecha_entrenamiento DESC
        """
        
        models = db.execute_query(query)
        
        if not models:
            return []
        
        # Crear comparación con datos reales
        comparison = []
        for model in models:
            model_dict = dict(model)
            metrics = model_dict.get('metricas_entrenamiento', {})
            model_type = model_dict.get('tipo_modelo', 'Unknown')
            
            comparison.append({
                "model_name": model_type.replace('-', ' ').title(),
                "accuracy": metrics.get('accuracy', 0),
                "precision": metrics.get('precision', 0),
                "recall": metrics.get('recall', 0),
                "f1_score": metrics.get('f1_score', 0),
                "training_time": 0,  # No tenemos tiempo real de entrenamiento
                "model_id": model_dict.get('id', ''),
                "fecha_entrenamiento": model_dict.get('fecha_entrenamiento')
            })
        
        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar comparación: {e}")

@router.get("/models")
async def get_models():
    """Obtener lista de modelos entrenados desde Supabase (tabla modelos_entrenados)"""
    try:
        from app.database import db
        
        query = """
        SELECT me.id, me.nombre_modelo, me.tipo_modelo, me.metricas_entrenamiento, 
               me.configuracion_modelo, me.fecha_entrenamiento, me.estado, me.confusion_matrix,
               dl.nombre_archivo_limpio, dc.nombre_archivo as archivo_original
        FROM modelos_entrenados me
        LEFT JOIN datos_limpiados dl ON me.datos_limpiados_id = dl.id
        LEFT JOIN datos_cargados dc ON dl.datos_cargados_id = dc.id
        ORDER BY me.fecha_entrenamiento DESC
        """
        
        models = db.execute_query(query)
        
        formatted_models = []
        for model in models:
            model_dict = dict(model)
            metricas = model_dict.get('metricas_entrenamiento', {})
            
            formatted_model = {
                'id': model_dict['id'],
                'model_type': model_dict['tipo_modelo'],
                'accuracy': metricas.get('accuracy', 0),
                'precision': metricas.get('precision', 0),
                'recall': metricas.get('recall', 0),
                'f1_score': metricas.get('f1_score', 0),
                'fecha_entrenamiento': model_dict['fecha_entrenamiento'],
                'saved_to_db': True,  # Todos los modelos en esta tabla están guardados
                'dataset_id': model_dict.get('datos_limpiados_id'),
                'nombre_modelo': model_dict['nombre_modelo'],
                'archivo_original': model_dict.get('archivo_original'),
                'archivo_limpio': model_dict.get('nombre_archivo_limpio'),
                'estado': model_dict['estado']
            }
            formatted_models.append(formatted_model)
        
        return formatted_models
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar modelos: {e}")

@router.get("/export/{model_id}")
async def export_model_results(model_id: str):
    """Exportar resultados de un modelo"""
    try:
        # Simular exportación
        return {
            "message": f"Resultados del modelo {model_id} exportados exitosamente",
            "file_path": f"/exports/model_{model_id}_results.json",
            "download_url": f"/api/results/download/{model_id}",
            "exported_at": "2023-10-26T12:00:00Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al exportar resultados: {e}")