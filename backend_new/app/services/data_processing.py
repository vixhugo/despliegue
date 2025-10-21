import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable
import io
import os
import time

class DataProcessor:
    """Servicio de procesamiento de datos usando pandas y numpy"""

    def __init__(self):
        self.data = None
        self.quality_metrics = {}
        self.progress_callback: Optional[Callable] = None
        self.job_id: Optional[str] = None

    def set_progress_callback(self, callback: Callable, job_id: str):
        """Configurar callback para actualizar progreso en tiempo real"""
        self.progress_callback = callback
        self.job_id = job_id

    def _update_progress(self, progress: float, message: str, metrics: Optional[Dict] = None):
        """Actualizar progreso del job si hay callback configurado"""
        if self.progress_callback and self.job_id:
            self.progress_callback(
                job_id=self.job_id,
                progress=progress,
                message=message,
                metrics=metrics
            )

    def load_csv(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Cargar datos CSV y devolver información básica"""
        try:
            # Validar que el archivo no esté vacío
            if len(file_content) == 0:
                raise ValueError("El archivo está vacío")
            
            # Intentar decodificar el contenido
            try:
                content_str = file_content.decode('utf-8')
            except UnicodeDecodeError:
                # Intentar con diferentes encodings
                try:
                    content_str = file_content.decode('latin-1')
                except UnicodeDecodeError:
                    content_str = file_content.decode('cp1252')
            
            # Cargar el CSV
            self.data = pd.read_csv(io.StringIO(content_str))
            
            # Validar que el DataFrame no esté vacío
            if self.data.empty:
                raise ValueError("El archivo CSV no contiene datos")
            
            info = {
                "filename": filename,
                "rows": len(self.data),
                "columns": len(self.data.columns),
                "column_names": list(self.data.columns),
                "data_types": self.data.dtypes.astype(str).to_dict(),
                "preview": self.data.head().to_dict('records')
            }
            return info
        except pd.errors.EmptyDataError:
            raise ValueError("El archivo CSV está vacío o no tiene datos válidos")
        except pd.errors.ParserError as e:
            raise ValueError(f"Error al parsear el CSV: {str(e)}")
        except Exception as e:
            raise Exception(f"Error cargando CSV: {str(e)}")

    def load_csv_from_path(self, file_path: str) -> Dict[str, Any]:
        """Cargar CSV directamente desde una ruta en disco y devolver información básica"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

            self.data = pd.read_csv(file_path)

            if self.data.empty:
                raise ValueError("El archivo CSV no contiene datos")

            info = {
                "filename": os.path.basename(file_path),
                "rows": len(self.data),
                "columns": len(self.data.columns),
                "column_names": list(self.data.columns),
                "data_types": self.data.dtypes.astype(str).to_dict(),
                "preview": self.data.head().to_dict('records')
            }
            return info
        except pd.errors.EmptyDataError:
            raise ValueError("El archivo CSV está vacío o no tiene datos válidos")
        except pd.errors.ParserError as e:
            raise ValueError(f"Error al parsear el CSV: {str(e)}")
        except Exception as e:
            raise Exception(f"Error cargando CSV desde ruta: {str(e)}")

    def analyze_data_quality(self) -> Dict[str, Any]:
        """Analizar métricas de calidad de datos"""
        if self.data is None:
            raise Exception("No hay datos cargados")
        
        # Calcular métricas reales
        null_count = self.data.isnull().sum().sum()
        duplicate_count = self.data.duplicated().sum()
        
        completeness = ((len(self.data) - null_count) / (len(self.data) * len(self.data.columns))) * 100
        
        self.quality_metrics = {
            "completeness": round(completeness, 2),
            "consistency": 88.0,  # Simulado
            "accuracy": 92.0,      # Simulado
            "null_values": int(null_count),
            "duplicates": int(duplicate_count),
            "outliers": 5          # Simulado
        }
        return self.quality_metrics

    def clean_data(self) -> Dict[str, Any]:
        """Limpiar los datos y devolver reporte de limpieza con progreso en tiempo real"""
        if self.data is None:
            raise Exception("No hay datos cargados")
        
        original_rows = len(self.data)
        self._update_progress(
            10.0,
            "Iniciando limpieza de datos...",
            {
                "rows_total": original_rows,
                "columns": list(self.data.columns),
                "preview": self.data.head(10).to_dict('records')
            }
        )
        
        # Paso 1: Análisis de valores nulos más inteligente
        self._update_progress(25.0, "Analizando valores nulos...")
        null_count_before = self.data.isnull().sum().sum()
        
        # Estrategia inteligente de relleno de nulos
        nulls_filled = 0
        nulls_removed = 0
        
        print(f"[DEBUG] Total de nulos antes del procesamiento: {self.data.isnull().sum().sum()}")
        print(f"[DEBUG] Filas antes del procesamiento: {len(self.data)}")
        print(f"[DEBUG] Columnas del dataset: {list(self.data.columns)}")
        
        for column in self.data.columns:
            nulls_in_col = self.data[column].isnull().sum()
            print(f"[DEBUG] Columna {column}: {nulls_in_col} nulos, tipo: {self.data[column].dtype}")
            if nulls_in_col > 0:
                print(f"[DEBUG] Procesando nulos en columna {column}...")
                if self.data[column].dtype in ['int64', 'float64']:
                    # Para columnas numéricas, rellenar con la media
                    mean_value = self.data[column].mean()
                    if not pd.isna(mean_value):
                        self.data[column].fillna(mean_value, inplace=True)
                        nulls_filled += nulls_in_col
                        print(f"[DEBUG] Rellenados {nulls_in_col} nulos en {column} con media: {mean_value:.2f}")
                        self._update_progress(
                            30.0,
                            f"Rellenando {nulls_in_col} valores nulos en {column} con media: {mean_value:.2f}"
                        )
                    else:
                        print(f"[DEBUG] No se puede calcular media para {column} (todos los valores son NaN)")
                else:
                    # Para columnas categóricas, rellenar con la moda
                    mode_value = self.data[column].mode()
                    if not mode_value.empty:
                        self.data[column].fillna(mode_value[0], inplace=True)
                        nulls_filled += nulls_in_col
                        print(f"[DEBUG] Rellenados {nulls_in_col} nulos en {column} con moda: {mode_value[0]}")
                        self._update_progress(
                            30.0,
                            f"Rellenando {nulls_in_col} valores nulos en {column} con moda: {mode_value[0]}"
                        )
                    else:
                        print(f"[DEBUG] No se puede calcular moda para {column} (todos los valores son NaN)")
            else:
                print(f"[DEBUG] Columna {column} no tiene nulos")
        
        # Solo eliminar filas que tengan TODOS los valores nulos (filas completamente vacías)
        rows_before = len(self.data)
        print(f"[DEBUG] Filas antes de eliminar completamente vacías: {rows_before}")
        self.data = self.data.dropna(how='all')
        rows_after = len(self.data)
        nulls_removed = rows_before - rows_after
        print(f"[DEBUG] Filas después de eliminar completamente vacías: {rows_after}")
        print(f"[DEBUG] Filas vacías eliminadas: {nulls_removed}")
        print(f"[DEBUG] Total nulos rellenados: {nulls_filled}")
        
        self._update_progress(
            40.0,
            f"Valores nulos procesados: {nulls_filled} rellenados, {nulls_removed} filas vacías eliminadas",
            {
                "nulls_filled": int(nulls_filled),
                "nulls_removed": int(nulls_removed),
                "columns": list(self.data.columns),
                "preview": self.data.head(10).to_dict('records')
            }
        )
        
        # Paso 2: Eliminar duplicados
        self._update_progress(50.0, "Eliminando duplicados...")
        duplicate_count_before = self.data.duplicated().sum()
        self.data = self.data.drop_duplicates()
        duplicate_count_after = self.data.duplicated().sum()
        self._update_progress(
            60.0,
            f"Duplicados eliminados: {duplicate_count_before - duplicate_count_after}",
            {
                "duplicates_removed": int(duplicate_count_before - duplicate_count_after),
                "columns": list(self.data.columns),
                "preview": self.data.head(10).to_dict('records')
            }
        )
        
        # Paso 3: Detección y manejo de outliers
        self._update_progress(70.0, "Detectando outliers...")
        outliers_removed = 0
        numeric_columns = self.data.select_dtypes(include=[np.number]).columns
        
        for column in numeric_columns:
            Q1 = self.data[column].quantile(0.25)
            Q3 = self.data[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = (self.data[column] < lower_bound) | (self.data[column] > upper_bound)
            outliers_count = outliers.sum()
            if outliers_count > 0:
                # En lugar de eliminar, reemplazar outliers con valores límite
                self.data.loc[self.data[column] < lower_bound, column] = lower_bound
                self.data.loc[self.data[column] > upper_bound, column] = upper_bound
                outliers_removed += outliers_count
        
        self._update_progress(
            80.0,
            f"Outliers procesados: {outliers_removed}",
            {
                "outliers_removed": int(outliers_removed),
                "columns": list(self.data.columns),
                "preview": self.data.head(10).to_dict('records')
            }
        )
        
        # Paso 4: Normalización mejorada
        self._update_progress(85.0, "Aplicando normalización...")
        normalized_columns = []
        for column in numeric_columns:
            if self.data[column].std() > 0:  # Solo normalizar si hay variación
                # Normalización Min-Max
                min_val = self.data[column].min()
                max_val = self.data[column].max()
                if max_val != min_val:  # Evitar división por cero
                    self.data[column] = (self.data[column] - min_val) / (max_val - min_val)
                    normalized_columns.append(column)
        
        self._update_progress(
            95.0,
            "Finalizando limpieza...",
            {
                "normalized_columns": normalized_columns,
                "columns": list(self.data.columns),
                "preview": self.data.head(10).to_dict('records')
            }
        )
        
        cleaned_rows = len(self.data)
        rows_removed = original_rows - cleaned_rows
        
        cleaning_report = {
            "null_values_filled": int(nulls_filled),
            "duplicates_removed": int(duplicate_count_before - duplicate_count_after),
            "nulls_removed": int(nulls_removed),  # Solo filas completamente vacías
            "outliers_removed": int(outliers_removed),
            "normalized_columns": normalized_columns,
            "final_rows": cleaned_rows,
            "rows_removed": int(rows_removed),
            "original_rows": original_rows,
            "cleaned_rows": cleaned_rows,
            "preview": self.data.head(10).to_dict('records')
        }
        
        # Añadir última vista previa al reporte final
        cleaning_report["columns"] = list(self.data.columns)
        
        # Convertir valores NaN a None para compatibilidad JSON
        preview_data = self.data.head(10).to_dict('records')
        for row in preview_data:
            for key, value in row.items():
                if pd.isna(value):
                    row[key] = None
                elif isinstance(value, (np.integer, np.floating)):
                    # Convertir numpy types a Python types para JSON
                    if np.isnan(value) or np.isinf(value):
                        row[key] = None
                    else:
                        row[key] = float(value) if isinstance(value, np.floating) else int(value)
        
        cleaning_report["preview"] = preview_data
        self._update_progress(100.0, "Limpieza completada exitosamente", cleaning_report)
        return cleaning_report

    def get_cleaned_data(self) -> pd.DataFrame:
        """Obtener datos limpios"""
        return self.data

    def get_data_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de los datos"""
        if self.data is None:
            raise Exception("No hay datos cargados")
        
        return {
            "shape": self.data.shape,
            "columns": list(self.data.columns),
            "dtypes": self.data.dtypes.astype(str).to_dict(),
            "describe": self.data.describe().to_dict()
        }