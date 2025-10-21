import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Play, Settings } from "lucide-react";
import { toast } from "sonner";
import { modelsApi, dataApi } from "@/services/api";
import { useMutation, useQuery } from "@tanstack/react-query";

export default function TrainModel() {
  const [isTraining, setIsTraining] = useState(false);
  const [trainingProgress, setTrainingProgress] = useState(0);
  const [modelType, setModelType] = useState("random-forest");
  const [selectedDataset, setSelectedDataset] = useState<any>(null);
  const [testSize, setTestSize] = useState(0.2);
  const [nEstimators, setNEstimators] = useState(100);

  // Fetch cleaned files from database
  const { data: cleanedFiles = [], isLoading: cleanedFilesLoading } = useQuery({
    queryKey: ['cleaned-files'],
    queryFn: dataApi.getCleanedFiles,
  });

  // Training mutation
  const trainMutation = useMutation({
    mutationFn: (data: any) => modelsApi.trainModelWithFile(data),
    onSuccess: (data) => {
      setIsTraining(false);
      setTrainingProgress(100);
      toast.success("Entrenamiento completado exitosamente");
      // Export to database after training
      toast.info("Modelo exportado a la base de datos");
    },
    onError: (error) => {
      setIsTraining(false);
      setTrainingProgress(0);
      toast.error("Error durante el entrenamiento");
    },
  });

  const handleTrain = () => {
    if (!selectedDataset) {
      toast.error("Selecciona un dataset limpio para entrenar.");
      return;
    }

    if (cleanedFiles.length === 0) {
      toast.error("No hay archivos limpios disponibles. Limpia un archivo primero.");
      return;
    }

    setIsTraining(true);
    setTrainingProgress(0);
    
    // Simulate progress
    const interval = setInterval(() => {
      setTrainingProgress((prev) => {
        if (prev >= 90) {
          clearInterval(interval);
          return prev;
        }
        return prev + 5;
      });
    }, 200);

    // Start training with selected file
    const targetColumn = selectedDataset.target_column || selectedDataset.columnas?.[0];
    
    if (!targetColumn) {
      toast.error("Selecciona una columna objetivo válida");
      return;
    }
    
    trainMutation.mutate({
      filename: selectedDataset.nombre_limpio,
      model_type: modelType,
      target_column: targetColumn,
      test_size: testSize,
      cleaned_file_id: selectedDataset.id,
      // Parámetros dinámicos del modelo:
      parameters: {
          n_estimators: nEstimators,
          max_depth: 5,
          random_state: 42
      }
    });
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold text-foreground mb-2">Entrenar Modelo</h1>
        <p className="text-lg text-muted-foreground mb-8">
          Configura parámetros y entrena tu modelo de Machine Learning
        </p>

        {/* Cleaned Files Selection */}
        <Card className="p-6 mb-8">
          <h3 className="text-lg font-semibold text-foreground mb-4">Seleccionar Archivo Limpio</h3>
          {cleanedFilesLoading ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground">Cargando archivos limpiados...</p>
            </div>
          ) : cleanedFiles.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground">No hay archivos limpios disponibles</p>
              <p className="text-sm text-muted-foreground">Ve a "Limpiar Datos" para procesar un archivo</p>
            </div>
          ) : (
            <div className="grid gap-3">
              {cleanedFiles.map((file) => (
                <div
                  key={file.id}
                  className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                    selectedDataset?.id === file.id
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50'
                  }`}
                  onClick={() => setSelectedDataset(file)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-foreground">{file.nombre_limpio}</h4>
                      <p className="text-sm text-muted-foreground">
                        Original: {file.nombre_original}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Estado: {file.estado}
                      </p>
                    </div>
                    {selectedDataset?.id === file.id && (
                      <div className="w-5 h-5 rounded-full bg-primary" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <Settings className="w-6 h-6 text-primary" />
                <h3 className="text-xl font-semibold text-foreground">Configuración del Modelo</h3>
              </div>

              <div className="space-y-6">
                <div>
                  <Label htmlFor="model-type" className="text-foreground mb-2 block">
                    Tipo de Modelo
                  </Label>
                  <Select value={modelType} onValueChange={setModelType}>
                    <SelectTrigger id="model-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="random-forest">Random Forest (Scikit-learn)</SelectItem>
                      <SelectItem value="svm">SVM (Scikit-learn)</SelectItem>
                      <SelectItem value="gradient-boost">Gradient Boosting</SelectItem>
                      <SelectItem value="pytorch-neural-network">Red Neuronal (PyTorch)</SelectItem> 
                    </SelectContent>
                  </Select>
                </div>
                
                
                {/* Campo dinámico para n_estimators */}
                {modelType === 'random-forest' && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <Label className="text-foreground">Número de Estimadores (n_estimators)</Label>
                      <span className="text-sm font-medium text-primary">{nEstimators}</span> 
                    </div>
                    <input
                      type="range"
                      min="10"
                      max="500"
                      step="10"
                      value={nEstimators}
                      onChange={(e) => setNEstimators(parseInt(e.target.value))}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
                      style={{
                        background: `linear-gradient(to right, hsl(var(--primary)) 0%, hsl(var(--primary)) ${((nEstimators - 10) / (500 - 10)) * 100}%, #e5e7eb ${((nEstimators - 10) / (500 - 10)) * 100}%, #e5e7eb 100%)`
                      }}
                    />
                    <div className="flex justify-between text-xs text-muted-foreground mt-1">
                      <span>10</span>
                      <span>500</span>
                    </div>
                  </div>
                )}
                
                {/* Campo para seleccionar columna objetivo */}
                <div>
                  <Label htmlFor="target-column" className="text-foreground mb-2 block">
                    Columna Objetivo (Variable Y)
                  </Label>
                  <Select 
                    value={selectedDataset?.target_column || (selectedDataset?.columnas?.[0] || undefined)} 
                    onValueChange={(value) => {
                      if (selectedDataset && value !== "no-file") {
                        setSelectedDataset({...selectedDataset, target_column: value});
                      }
                    }}
                  >
                    <SelectTrigger id="target-column">
                      <SelectValue placeholder="Selecciona una columna objetivo" />
                    </SelectTrigger>
                    <SelectContent>
                      {selectedDataset && selectedDataset.columnas ? (
                        selectedDataset.columnas.map((col: string) => (
                          <SelectItem key={col} value={col}>{col}</SelectItem>
                        ))
                      ) : (
                        <SelectItem value="no-file" disabled>Selecciona un archivo primero</SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Button
                onClick={handleTrain}
                disabled={isTraining || !selectedDataset}
                className="w-full mt-6"
                size="lg"
              >
                <Play className="w-5 h-5 mr-2" />
                {isTraining ? "Entrenando..." : "Iniciar Entrenamiento"}
              </Button>
            </Card>

            {isTraining && (
              <Card className="p-6">
                <h3 className="text-lg font-semibold text-foreground mb-4">
                  Progreso del Entrenamiento
                </h3>
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-muted-foreground">Progreso General</span>
                      <span className="text-sm font-bold text-primary">{trainingProgress}%</span>
                    </div>
                    <Progress value={trainingProgress} className="h-3" />
                  </div>
                  <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">Modelo Actual</p>
                      <p className="text-2xl font-bold text-foreground">
                        {modelType === 'random-forest' ? 'Random Forest' : '...'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">Estado</p>
                      <p className="text-2xl font-bold text-foreground">
                        {trainingProgress < 90 ? 'Procesando' : 'Evaluando'}
                      </p>
                    </div>
                  </div>
                </div>
              </Card>
            )}
          </div>

          <div className="space-y-6">
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4">Dataset Split</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-foreground">Tamaño del Conjunto de Prueba</Label>
                    <span className="text-sm font-medium text-primary">{(testSize * 100).toFixed(0)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.1"
                    max="0.5"
                    step="0.05"
                    value={testSize}
                    onChange={(e) => setTestSize(parseFloat(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
                    style={{
                      background: `linear-gradient(to right, hsl(var(--primary)) 0%, hsl(var(--primary)) ${((testSize - 0.1) / (0.5 - 0.1)) * 100}%, #e5e7eb ${((testSize - 0.1) / (0.5 - 0.1)) * 100}%, #e5e7eb 100%)`
                    }}
                  />
                  <div className="flex justify-between text-xs text-muted-foreground mt-1">
                    <span>10%</span>
                    <span>50%</span>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-primary/10">
                    <span className="text-sm font-medium text-foreground">Entrenamiento</span>
                    <span className="text-sm font-bold text-primary">{((1 - testSize) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-success/10">
                    <span className="text-sm font-medium text-foreground">Prueba</span>
                    <span className="text-sm font-bold text-success">{(testSize * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4">Entorno</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Librería</span>
                  <span className="text-sm font-medium text-foreground">
                    {modelType === 'random-forest' ? 'Scikit-learn' : 
                     modelType === 'svm' ? 'Scikit-learn' : 
                     modelType === 'gradient-boost' ? 'Scikit-learn' : 'Scikit-learn'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Modelo</span>
                  <span className="text-sm font-medium text-foreground">
                    {modelType === 'random-forest' ? 'Random Forest' : 
                     modelType === 'svm' ? 'SVM' : 
                     modelType === 'gradient-boost' ? 'Gradient Boosting' : modelType}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Estimadores</span>
                  <span className="text-sm font-medium text-foreground">{nEstimators}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Tipo de Problema</span>
                  <span className="text-sm font-medium text-foreground">
                    {selectedDataset?.target_column === 'Total' ? 'Regresión' : 'Clasificación'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Archivo Seleccionado</span>
                  <span className="text-sm font-medium text-foreground truncate max-w-32">
                    {selectedDataset?.nombre_limpio || 'Ninguno'}
                  </span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}