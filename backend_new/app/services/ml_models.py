import pandas as pd
import numpy as np
from typing import Dict, Any, List
from pathlib import Path


class MLModelsService:
    """Servicio para entrenamiento y evaluación de modelos de ML usando scikit-learn.

    Este servicio espera que el dataset ya esté guardado en disco y disponible en `datasets.ruta_almacenamiento`.
    """

    def __init__(self):
        self.trained_models: Dict[str, Dict[str, Any]] = {}
        self.model_metrics: Dict[str, Dict[str, float]] = {}
        self.training_history: Dict[str, List[Dict[str, Any]]] = {}
        self.confusion_matrices: Dict[str, Dict[str, Any]] = {}
        
        # Cargar modelos existentes al inicializar
        self._load_models_from_disk()

    def _prepare_features(self, df: pd.DataFrame, target_column: str):
        print(f"Preparando features para columna objetivo: {target_column}")
        if target_column not in df.columns:
            print(f"Columnas disponibles: {list(df.columns)}")
            raise ValueError(f"La columna objetivo '{target_column}' no existe en el dataset")

        X = df.drop(columns=[target_column])
        y = df[target_column]
        print(f"Features shape: {X.shape}, Target shape: {y.shape}")

        # One-hot encode categorical features
        X = pd.get_dummies(X, drop_first=True)
        X = X.fillna(0)
        
        # Ensure all features are numeric
        X = X.astype(float)
        print(f"Features finales shape: {X.shape}")

        # For target, if categorical, leave as-is; caller handles label encoding if needed
        return X, y

    def train_model(self, dataset_path: str, model_type: str, target_column: str, test_size: float = 0.2, parameters: Dict = None) -> Dict[str, Any]:
        """Entrena un modelo real usando scikit-learn y devuelve metadatos.

        - dataset_path: ruta al CSV en disco
        - model_type: 'random-forest' | 'svm' | 'gradient-boost'
        - target_column: nombre de la columna objetivo
        - parameters: dict con parámetros como n_estimators
        """
        import uuid
        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.svm import SVC
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
        import joblib
        import json

        model_id = str(uuid.uuid4())
        print(f"Entrenando modelo {model_type} con archivo: {dataset_path}")

        # Load dataset
        try:
            df = pd.read_csv(dataset_path)
            print(f"Dataset cargado: {df.shape[0]} filas, {df.shape[1]} columnas")
            print(f"Columnas disponibles: {list(df.columns)}")
        except Exception as e:
            print(f"Error cargando dataset: {e}")
            raise

        X, y = self._prepare_features(df, target_column)

        # If y is categorical, encode with pandas factorize
        if y.dtype == 'object' or str(y.dtype).startswith('category'):
            y_encoded, uniques = pd.factorize(y)
            class_labels = list(uniques.astype(str))
        else:
            y_encoded = y.values
            class_labels = []

        X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=test_size, random_state=42)

        # Choose model - detect if target is continuous or categorical
        params = parameters or {}
        
        # Check if target is continuous (regression) or categorical (classification)
        is_continuous = pd.api.types.is_numeric_dtype(y) and len(y.unique()) > 10
        
        if model_type == 'random-forest':
            if is_continuous:
                from sklearn.ensemble import RandomForestRegressor
                clf = RandomForestRegressor(n_estimators=params.get('n_estimators', 100), random_state=42)
            else:
                clf = RandomForestClassifier(n_estimators=params.get('n_estimators', 100), random_state=42)
        elif model_type == 'svm':
            if is_continuous:
                from sklearn.svm import SVR
                clf = SVR()
            else:
                clf = SVC(probability=True, random_state=42)
        elif model_type == 'gradient-boost':
            if is_continuous:
                from sklearn.ensemble import GradientBoostingRegressor
                clf = GradientBoostingRegressor(random_state=42)
            else:
                clf = GradientBoostingClassifier(random_state=42)
        else:
            raise ValueError(f"model_type desconocido: {model_type}")

        clf.fit(X_train, y_train)

        preds = clf.predict(X_test)

        # Calculate metrics based on problem type
        if is_continuous:
            # Regression metrics
            from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
            mse = float(mean_squared_error(y_test, preds))
            mae = float(mean_absolute_error(y_test, preds))
            r2 = float(r2_score(y_test, preds))
            
            # For regression, we'll use R² as the main accuracy metric
            accuracy = r2
            precision = None
            recall = None
            f1 = None
            cm = None
        else:
            # Classification metrics
            accuracy = float(accuracy_score(y_test, preds))
            precision = float(precision_score(y_test, preds, average='weighted', zero_division=0))
            recall = float(recall_score(y_test, preds, average='weighted', zero_division=0))
            f1 = float(f1_score(y_test, preds, average='weighted', zero_division=0))
            cm = confusion_matrix(y_test, preds).tolist()

        # Calcular métricas adicionales
        from sklearn.metrics import classification_report, roc_auc_score
        import numpy as np
        
        if is_continuous:
            # Regression additional metrics
            report = None
            auc_score = None
        else:
            # Classification report
            report = classification_report(y_test, preds, output_dict=True, zero_division=0)
            
            # ROC AUC (solo si es problema de clasificación binaria)
            try:
                if len(np.unique(y_test)) == 2:
                    auc_score = float(roc_auc_score(y_test, preds))
                else:
                    auc_score = None
            except:
                auc_score = None
        
        # Prepare base metrics - ensure all values are JSON serializable
        metricas_entrenamiento = {
            'accuracy': float(accuracy) if accuracy is not None else None,
            'precision': float(precision) if precision is not None else None,
            'recall': float(recall) if recall is not None else None,
            'f1_score': float(f1) if f1 is not None else None,
            'auc_score': float(auc_score) if auc_score is not None else None,
            'model_type': str(model_type),
            'target_column': str(target_column),
            'test_size': float(test_size),
            'parameters': {k: float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v for k, v in params.items()},
            'problem_type': 'regression' if is_continuous else 'classification',
            'dataset_info': {
                'total_samples': int(len(df)),
                'features_count': int(len(X.columns)),
                'train_samples': int(len(X_train)),
                'test_samples': int(len(X_test)),
                'class_distribution': dict(y.value_counts()) if hasattr(y, 'value_counts') and not is_continuous else None
            },
            'classification_report': report,
            'confusion_matrix': cm if cm is not None else None
        }
        
        # Add regression-specific metrics
        if is_continuous:
            metricas_entrenamiento.update({
                'mse': float(mse),
                'mae': float(mae),
                'r2_score': float(r2),
                'rmse': float(np.sqrt(mse))
            })

        # Save model
        models_dir = Path.cwd() / 'models'
        models_dir.mkdir(parents=True, exist_ok=True)
        model_path = models_dir / f"model_{model_id}.joblib"
        joblib.dump(clf, model_path)

        datos_exportados = {
            'model_path': str(model_path),
            'model_type': model_type,
            'target_column': target_column,
            'features': X.columns.tolist(),
            'class_labels': class_labels
        }

        # Persist in-memory (NO guardado en BD por defecto)
        self.trained_models[model_id] = {
            'id': model_id,
            'dataset_path': dataset_path,
            'datos_exportados': datos_exportados,
            'metricas_entrenamiento': metricas_entrenamiento,
            'fecha_entrenamiento': pd.Timestamp.now().isoformat(),
            'status': 'completed',
            'confusion_matrix': cm,
            'saved_to_db': False,  # No guardado en BD por defecto
            'dataset_id': None
        }

        self.model_metrics[model_id] = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1
        }

        self.confusion_matrices[model_id] = {'class_labels': class_labels, 'confusion_matrix': cm}

        self.training_history[model_id] = [{'epoch': 1, 'loss': None, 'accuracy': accuracy}]

        # Guardar modelos en disco para persistencia
        self._save_models_to_disk()

        return self.trained_models[model_id]

    def get_models(self) -> List[Dict[str, Any]]:
        """Obtener todos los modelos entrenados"""
        return list(self.trained_models.values())

    def get_model_metrics(self, model_id: str) -> Dict[str, Any]:
        """Obtener métricas de un modelo específico"""
        print(f"Buscando métricas para modelo: {model_id}")
        print(f"Métricas disponibles: {list(self.model_metrics.keys())}")
        
        # Si no hay métricas en memoria, intentar cargar desde la BD
        if model_id not in self.model_metrics:
            print(f"Modelo {model_id} no encontrado en memoria, cargando desde BD...")
            self._load_model_from_db(model_id)
        
        metrics = self.model_metrics.get(model_id, {})
        print(f"Métricas encontradas: {metrics}")
        return metrics

    def get_training_history(self, model_id: str) -> List[Dict[str, Any]]:
        """Obtener historial de entrenamiento de un modelo"""
        return self.training_history.get(model_id, [])

    def get_confusion_matrix(self, model_id: str) -> Dict[str, Any]:
        """Obtener matriz de confusión de un modelo"""
        return self.confusion_matrices.get(model_id, {})
    
    def _load_model_from_db(self, model_id: str):
        """Cargar modelo desde la base de datos"""
        try:
            from app.database import db
            query = """
            SELECT metricas_entrenamiento, confusion_matrix, fecha_entrenamiento, status
            FROM datasets 
            WHERE id = %s AND estado_procesamiento = 'MODELO_ENTRENADO'
            """
            results = db.execute_query(query, (model_id,))
            
            if results:
                model_data = dict(results[0])
                metrics = model_data.get('metricas_entrenamiento', {})
                confusion_matrix = model_data.get('confusion_matrix', [])
                
                # Cargar métricas
                self.model_metrics[model_id] = {
                    'accuracy': metrics.get('accuracy', 0),
                    'precision': metrics.get('precision', 0),
                    'recall': metrics.get('recall', 0),
                    'f1_score': metrics.get('f1_score', 0)
                }
                
                # Cargar matriz de confusión
                self.confusion_matrices[model_id] = {
                    'confusion_matrix': confusion_matrix,
                    'class_labels': []  # Se puede mejorar más adelante
                }
                
                # Cargar historial de entrenamiento
                self.training_history[model_id] = [{
                    'epoch': 1,
                    'accuracy': metrics.get('accuracy', 0),
                    'loss': None
                }]
                
                print(f"Modelo {model_id} cargado desde BD exitosamente")
            else:
                print(f"Modelo {model_id} no encontrado en BD")
        except Exception as e:
            print(f"Error cargando modelo desde BD: {e}")
    
    def _save_models_to_disk(self):
        """Guardar modelos en disco para persistencia"""
        try:
            import json
            models_file = Path.cwd() / 'models' / 'trained_models.json'
            models_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(models_file, 'w') as f:
                json.dump({
                    'trained_models': self.trained_models,
                    'model_metrics': self.model_metrics,
                    'training_history': self.training_history,
                    'confusion_matrices': self.confusion_matrices
                }, f, indent=2)
            print(f"Modelos guardados en {models_file}")
        except Exception as e:
            print(f"Error guardando modelos: {e}")
    
    def _load_models_from_disk(self):
        """Cargar modelos desde disco"""
        try:
            import json
            models_file = Path.cwd() / 'models' / 'trained_models.json'
            
            if models_file.exists():
                with open(models_file, 'r') as f:
                    data = json.load(f)
                    self.trained_models = data.get('trained_models', {})
                    self.model_metrics = data.get('model_metrics', {})
                    self.training_history = data.get('training_history', {})
                    self.confusion_matrices = data.get('confusion_matrices', {})
                print(f"Modelos cargados desde {models_file}")
                print(f"Modelos cargados: {len(self.trained_models)}")
                print(f"IDs de modelos: {list(self.trained_models.keys())}")
            else:
                print("No hay modelos guardados en disco")
        except Exception as e:
            print(f"Error cargando modelos: {e}")

    def export_model(self, model_id: str) -> Dict[str, Any]:
        """Exportar un modelo entrenado"""
        if model_id not in self.trained_models:
            raise Exception("Modelo no encontrado")
        return {"message": f"Modelo {model_id} exportado exitosamente", "path": self.trained_models[model_id]['datos_exportados']}