from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

class PipelineJobBase(BaseModel):
    """Modelo base para pipeline jobs"""
    datos_cargados_id: str
    tipo_tarea: str
    estado: str = "pendiente"
    progreso: float = 0.0
    mensaje_actual: Optional[str] = None
    metricas_parciales: Optional[Dict[str, Any]] = None

class PipelineJobCreate(PipelineJobBase):
    """Modelo para crear un nuevo pipeline job"""
    pass

class PipelineJobUpdate(BaseModel):
    """Modelo para actualizar un pipeline job"""
    estado: Optional[str] = None
    progreso: Optional[float] = None
    mensaje_actual: Optional[str] = None
    metricas_parciales: Optional[Dict[str, Any]] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None

class PipelineJobResponse(PipelineJobBase):
    """Modelo de respuesta para pipeline jobs"""
    id: str
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CleanFileRequest(BaseModel):
    """Modelo para solicitud de limpieza de archivo"""
    filename: str

class TrainFileRequest(BaseModel):
    """Modelo para solicitud de entrenamiento de modelo"""
    filename: str
    model_type: str
    target_column: str
    test_size: float = 0.2
    parameters: Optional[Dict[str, Any]] = None