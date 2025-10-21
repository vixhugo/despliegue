from fastapi import APIRouter, HTTPException
from app.services.ml_models import MLModelsService
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

router = APIRouter()
ml_service = MLModelsService()

class TrainFileRequest(BaseModel):
    filename: str
    model_type: str
    target_column: str
    test_size: float = 0.2
    parameters: Optional[Dict[str, Any]] = None

class TrainCleanedFileRequest(BaseModel):
    filename: str
    model_type: str
    target_column: str
    test_size: float = 0.2
    cleaned_file_id: str
    parameters: Optional[Dict[str, Any]] = None



@router.post("/train-cleaned-file")
async def train_model_with_cleaned_file(request: TrainCleanedFileRequest):
    """Entrenar un modelo con un archivo limpiado desde la base de datos"""
    try:
        from pathlib import Path
        from app.database import db
        
        print(f"[TRAIN] Iniciando entrenamiento con archivo limpiado: {request.filename}")
        
        # Obtener información del archivo limpiado desde la BD
        query = """
        SELECT id, nombre_archivo_limpio, ruta_archivo_limpio, estadisticas_limpieza
        FROM datos_limpiados
        WHERE id = %s
        """
        files = db.execute_query(query, (request.cleaned_file_id,))
        
        if not files:
            raise HTTPException(status_code=404, detail="Archivo limpiado no encontrado en la base de datos")
        
        file_data = dict(files[0])
        file_path = file_data["ruta_archivo_limpio"]
        
        print(f"[TRAIN] Archivo encontrado en: {file_path}")
        
        if not Path(file_path).exists():
            raise HTTPException(status_code=404, detail=f"Archivo no encontrado en disco: {file_path}")
        
        print(f"[TRAIN] Iniciando entrenamiento del modelo...")
        
        # Entrenar modelo con archivo real
        model_result = ml_service.train_model(
            dataset_path=file_path,
            model_type=request.model_type,
            target_column=request.target_column,
            test_size=request.test_size,
            parameters=request.parameters or {}
        )
        
        print(f"[TRAIN] Modelo entrenado exitosamente: {model_result.get('id')}")
        
        # Guardar modelo en base de datos
        from datetime import datetime
        import json
        import uuid
        
        model_id = str(uuid.uuid4())
        
        # Clean metrics for JSON serialization
        def clean_for_json(obj):
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif hasattr(obj, 'item'):  # numpy scalars
                return obj.item()
            elif hasattr(obj, 'tolist'):  # numpy arrays
                return obj.tolist()
            else:
                return obj
        
        print(f"[TRAIN] Model result keys: {list(model_result.keys())}")
        print(f"[TRAIN] Metricas disponibles: {model_result.get('metricas_entrenamiento', {})}")
        
        cleaned_metrics = clean_for_json(model_result.get('metricas_entrenamiento', {}))
        print(f"[TRAIN] Métricas limpiadas: {cleaned_metrics}")
        
        insert_query = """
        INSERT INTO modelos_entrenados (id, datos_limpiados_id, nombre_modelo, tipo_modelo, metricas_entrenamiento, configuracion_modelo, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        db.execute_insert(insert_query, (
            model_id,
            request.cleaned_file_id,
            f"Modelo_{request.model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            request.model_type,
            json.dumps(cleaned_metrics),
            json.dumps(request.parameters or {}),
            'entrenado'
        ))
        
        print(f"Modelo guardado en BD con ID: {model_id}")
        
        # Clean the response for JSON serialization
        cleaned_model_result = clean_for_json(model_result)
        
        return {
            "message": "Modelo entrenado y guardado en Supabase",
            "model_result": cleaned_model_result,
            "model_id": model_id,
            "saved_to_db": True,
            "cleaned_file_id": request.cleaned_file_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TRAIN] Error en entrenamiento: {e}")
        import traceback
        print(f"[TRAIN] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error entrenando modelo: {e}")

@router.post("/train-file")
async def train_model_with_file(request: TrainFileRequest):
    """Entrenar un modelo con un archivo subido (sin BD) - DEPRECATED"""
    try:
        from pathlib import Path
        
        print(f"Recibida petición de entrenamiento: {request.filename}, {request.model_type}, {request.target_column}")
        
        file_path = Path.cwd() / "uploads" / request.filename
        print(f"Buscando archivo en: {file_path}")
        
        if not file_path.exists():
            print(f"Archivo no encontrado: {file_path}")
            raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {request.filename}")
        
        print(f"Archivo encontrado, iniciando entrenamiento...")
        
        # Entrenar modelo con archivo real
        model_result = ml_service.train_model(
            dataset_path=str(file_path),
            model_type=request.model_type,
            target_column=request.target_column,
            test_size=request.test_size,
            parameters=request.parameters or {}
        )
        
        print(f"Modelo entrenado exitosamente: {model_result.get('id')}")
        
        # NO guardar automáticamente en BD - solo entrenar en memoria
        return {
            "message": "Modelo entrenado correctamente (pendiente de guardar en BD)",
            "model_result": model_result,
            "model_id": model_result.get('id'),
            "saved_to_db": False
        }
    except Exception as e:
        print(f"Error en train_model_with_file: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/train-cleaned/{cleaned_file_id}")
async def train_model_with_cleaned_data(cleaned_file_id: str, request: TrainFileRequest):
    """Entrenar un modelo usando datos limpiados desde Supabase"""
    try:
        from app.database import db
        from pathlib import Path
        
        print(f"Entrenando modelo con datos limpiados ID: {cleaned_file_id}")
        
        # Obtener datos limpiados desde BD
        query = """
        SELECT dl.id, dl.nombre_archivo_limpio, dl.ruta_archivo_limpio, dl.estadisticas_limpieza,
               dc.nombre_archivo as archivo_original
        FROM datos_limpiados dl
        LEFT JOIN datos_cargados dc ON dl.datos_cargados_id = dc.id
        WHERE dl.id = %s
        """
        files = db.execute_query(query, (cleaned_file_id,))
        
        if not files:
            raise HTTPException(status_code=404, detail="Archivo limpio no encontrado en la base de datos")
        
        file_data = dict(files[0])
        file_path = file_data["ruta_archivo_limpio"]
        
        if not Path(file_path).exists():
            raise HTTPException(status_code=404, detail=f"Archivo limpio no encontrado en disco: {file_path}")
        
        print(f"Archivo limpio encontrado: {file_path}")
        
        # Entrenar modelo con datos limpios
        model_result = ml_service.train_model(
            dataset_path=file_path,
            model_type=request.model_type,
            target_column=request.target_column,
            test_size=request.test_size,
            parameters=request.parameters or {}
        )
        
        print(f"Modelo entrenado exitosamente: {model_result.get('id')}")
        
        # Guardar automáticamente en tabla modelos_entrenados
        import uuid
        model_id = str(uuid.uuid4())
        
        # Preparar métricas para guardar
        metricas_entrenamiento = {
            "accuracy": model_result.get("metricas_entrenamiento", {}).get("accuracy", 0),
            "precision": model_result.get("metricas_entrenamiento", {}).get("precision", 0),
            "recall": model_result.get("metricas_entrenamiento", {}).get("recall", 0),
            "f1_score": model_result.get("metricas_entrenamiento", {}).get("f1_score", 0)
        }
        
        configuracion_modelo = {
            "model_type": request.model_type,
            "target_column": request.target_column,
            "test_size": request.test_size,
            "parameters": request.parameters or {}
        }
        
        # Guardar modelo en carpeta models
        models_dir = Path.cwd() / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        model_filename = f"model_{model_id}.joblib"
        model_path = models_dir / model_filename
        
        # Copiar el modelo entrenado a la carpeta models
        import shutil
        original_model_path = model_result.get("datos_exportados", {}).get("model_path")
        if original_model_path and Path(original_model_path).exists():
            shutil.copy2(original_model_path, model_path)
        
        insert_query = """
        INSERT INTO modelos_entrenados (id, nombre_modelo, tipo_modelo, datos_limpiados_id, 
                                       metricas_entrenamiento, configuracion_modelo, ruta_modelo, confusion_matrix)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        db.execute_insert(insert_query, (
            model_id,
            f"Modelo_{request.model_type}_{file_data['nombre_archivo_limpio']}",
            request.model_type,
            cleaned_file_id,
            metricas_entrenamiento,
            configuracion_modelo,
            str(model_path),
            model_result.get("confusion_matrix", {})
        ))
        
        print(f"Modelo guardado en BD con ID: {model_id}")
        
        return {
            "message": "Modelo entrenado y guardado en Supabase",
            "model_result": model_result,
            "model_id": model_id,
            "saved_to_db": True,
            "cleaned_file_id": cleaned_file_id
        }
    except Exception as e:
        print(f"Error en train_model_with_cleaned_data: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/model-types")
async def get_model_types():
    """Obtener tipos de modelos disponibles"""
    model_types = [
        {
            "id": "random-forest",
            "name": "Random Forest",
            "description": "Ensemble de árboles de decisión",
            "framework": "scikit-learn",
            "best_for": "Clasificación y regresión general"
        },
        {
            "id": "svm",
            "name": "Support Vector Machine",
            "description": "Máquinas de vectores de soporte",
            "framework": "scikit-learn",
            "best_for": "Clasificación con datos de alta dimensión"
        },
        {
            "id": "gradient-boost",
            "name": "Gradient Boosting",
            "description": "Boosting con gradientes",
            "framework": "scikit-learn",
            "best_for": "Alta precisión en clasificación"
        },
        {
            "id": "neural-network",
            "name": "Neural Network (sklearn)",
            "description": "Red neuronal multicapa básica",
            "framework": "scikit-learn",
            "best_for": "Problemas de clasificación simples"
        },
        {
            "id": "pytorch-neural-network",
            "name": "Deep Neural Network",
            "description": "Red neuronal profunda con PyTorch",
            "framework": "pytorch",
            "best_for": "Problemas complejos de clasificación"
        },
        {
            "id": "pytorch-cnn-lstm",
            "name": "CNN-LSTM",
            "description": "Red convolucional con LSTM",
            "framework": "pytorch",
            "best_for": "Series temporales y secuencias"
        }
    ]
    return model_types
