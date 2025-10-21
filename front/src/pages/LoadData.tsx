import { useState, useRef } from "react";
import { Upload, FileText, CheckCircle2, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { dataApi, Dataset } from "@/services/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export default function LoadData() {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [fileToDelete, setFileToDelete] = useState<string | null>(null);
  const [fileNameToDelete, setFileNameToDelete] = useState<string>("");
  const [dataLoaded, setDataLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [fileName, setFileName] = useState("");
  const [currentDataset, setCurrentDataset] = useState<Dataset | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  // Fetch uploaded files
  const { data: uploadedFiles, isLoading: filesLoading } = useQuery({
    queryKey: ["uploaded-files"],
    queryFn: dataApi.getUploadedFiles,
  });

  // Fetch preview
  const { data: previewData = [], isLoading: previewLoading } = useQuery({
    queryKey: ["file-preview", currentDataset?.nombre_archivo],
    queryFn: async () => {
      if (!currentDataset || !currentDataset.nombre_archivo) return [];
      const res = await dataApi.getFilePreview(currentDataset.nombre_archivo);
      return Array.isArray(res.preview) ? res.preview : [];
    },
    enabled: !!currentDataset && !!currentDataset?.nombre_archivo,
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: dataApi.uploadFile,
    onSuccess: (data) => {
      setCurrentDataset({
        id: data.file_id || data.filename,
        nombre_archivo: data.filename,
        tipo_archivo: "text/csv",
        estado_procesamiento: "SUBIDO",
        created_at: new Date().toISOString(),
        user_id: "current-user",
      });
      setDataLoaded(true);
      setIsLoading(false);
      setLoadingProgress(100);
      toast.success(`Dataset cargado exitosamente - ${data.data_info.rows} filas procesadas`);
      queryClient.invalidateQueries({ queryKey: ["uploaded-files"] });
    },
    onError: () => {
      setIsLoading(false);
      setLoadingProgress(0);
      toast.error("Error al cargar el dataset");
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: dataApi.deleteDataset,
    onSuccess: (data) => {
      toast.success(data.message || "Dataset eliminado correctamente");
      queryClient.invalidateQueries({ queryKey: ["uploaded-files"] });
      // Limpia selección actual si era el dataset eliminado
      if (currentDataset && data.message?.includes(currentDataset.nombre_archivo)) {
        setCurrentDataset(null);
      }
    },
    onError: (error) => {
      console.error(error);
      toast.error("Error al eliminar el dataset");
    },
  });


  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.name.endsWith(".csv")) {
      toast.error("Por favor selecciona un archivo CSV");
      return;
    }
    setFileName(file.name);
    handleUpload(file);
  };

  const handleButtonClick = (event: React.MouseEvent) => {
  event.stopPropagation();
  fileInputRef.current?.click();
  };

  const handleUpload = (file: File) => {
    setIsLoading(true);
    setLoadingProgress(0);
    toast.info("Cargando dataset...");

    const interval = setInterval(() => {
      setLoadingProgress((prev) => {
        if (prev >= 90) {
          clearInterval(interval);
          return prev;
        }
        return prev + 10;
      });
    }, 150);

    uploadMutation.mutate(file);
  };

  // 🔥 Reusable dynamic preview table
  const renderPreviewTable = () => (
    <Table>
      <TableHeader>
        <TableRow>
          {previewData.length > 0 &&
            Object.keys(previewData[0])
              .slice(0, 6)
              .map((col) => <TableHead key={col}>{col}</TableHead>)}
        </TableRow>
      </TableHeader>
      <TableBody>
        {previewLoading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <TableRow key={i} className="animate-pulse">
              <TableCell>...</TableCell>
              <TableCell>...</TableCell>
              <TableCell>...</TableCell>
              <TableCell>...</TableCell>
              <TableCell>...</TableCell>
              <TableCell>...</TableCell>
            </TableRow>
          ))
        ) : (
          previewData.slice(0, 10).map((row: any, index: number) => (
            <TableRow key={index}>
              {Object.values(row)
                .slice(0, 6)
                .map((value, i) => (
                  <TableCell key={i}>{String(value)}</TableCell>
                ))}
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold text-foreground mb-2">Cargar Datos</h1>
        <p className="text-lg text-muted-foreground mb-8">
          Importa tus datasets para comenzar el análisis
        </p>

        {isLoading ? (
          <div className="space-y-6">
            <Card className="p-8">
              <div className="flex flex-col items-center justify-center text-center">
                <Loader2 className="w-16 h-16 text-primary animate-spin mb-4" />
                <h3 className="text-xl font-semibold text-foreground mb-2">
                  Cargando Dataset...
                </h3>
                <p className="text-muted-foreground mb-6">
                  Procesando y validando datos de {fileName}
                </p>
                <div className="w-full max-w-md space-y-2">
                  <Progress value={loadingProgress} className="h-3" />
                  <p className="text-sm text-muted-foreground">
                    {loadingProgress}% completado
                  </p>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-primary" />
                Vista Previa (Cargando...)
              </h3>
              <div className="rounded-lg border overflow-hidden opacity-70">
                {renderPreviewTable()}
              </div>
            </Card>
          </div>
        ) : !dataLoaded ? (
          <Card
            className="p-12 border-dashed border-2 hover:border-primary transition-colors cursor-pointer"
            onClick={handleButtonClick}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileSelect}
              className="hidden"
            />
            <div className="flex flex-col items-center justify-center text-center">
              <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <Upload className="w-10 h-10 text-primary" />
              </div>
              <h3 className="text-xl font-semibold text-foreground mb-2">
                Arrastra tus archivos aquí o haz clic para seleccionar
              </h3>
              <p className="text-muted-foreground mb-6">
                Soporta archivos CSV (máximo 20MB)
              </p>
              <Button onClick={handleButtonClick} size="lg" disabled={isLoading}>
                Seleccionar Archivo CSV
              </Button>
            </div>
          </Card>
        ) : (
          <div className="space-y-6">
            <Card className="p-6 bg-success/5 border-success">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-6 h-6 text-success" />
                <div>
                  <h3 className="font-semibold text-foreground">
                    {currentDataset?.nombre_archivo || fileName}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {currentDataset
                      ? `Estado: ${currentDataset.estado_procesamiento || "Procesado"}`
                      : "Cargando..."}
                  </p>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4">
                Vista Previa de Datos
              </h3>
              <div className="rounded-lg border overflow-hidden">{renderPreviewTable()}</div>
            </Card>

            <div className="grid gap-6 md:grid-cols-3">
              <Card className="p-6">
                <div className="flex items-center gap-3 mb-2">
                  <FileText className="w-5 h-5 text-primary" />
                  <h4 className="font-semibold text-foreground">Total Registros</h4>
                </div>
                <p className="text-3xl font-bold text-foreground">
                  {uploadMutation.data?.data_info?.rows || 0}
                </p>
              </Card>

              <Card className="p-6">
                <div className="flex items-center gap-3 mb-2">
                  <FileText className="w-5 h-5 text-accent" />
                  <h4 className="font-semibold text-foreground">Features</h4>
                </div>
                <p className="text-3xl font-bold text-foreground">
                  {uploadMutation.data?.data_info?.columns
                    ? uploadMutation.data.data_info.columns
                    : 0}
                </p>
              </Card>

              <Card className="p-6">
                <div className="flex items-center gap-3 mb-2">
                  <FileText className="w-5 h-5 text-success" />
                  <h4 className="font-semibold text-foreground">Clases</h4>
                </div>
                <p className="text-3xl font-bold text-foreground">3</p>
              </Card>
            </div>
          </div>
        )}

        {!isLoading && (
          <Card className="p-6 mt-8">
            <h3 className="text-lg font-semibold text-foreground mb-4">
              Archivos Subidos
            </h3>
            {filesLoading ? (
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Cargando archivos...</span>
              </div>
            ) : uploadedFiles && uploadedFiles.length > 0 ? (
              <div className="grid gap-3">
                {uploadedFiles.map((file) => (
                  <div
                    key={file.id}
                    className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                      currentDataset?.nombre_archivo === file.filename
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/50"
                    }`}
                    onClick={() =>
                      setCurrentDataset({
                        id: file.id,
                        nombre_archivo: file.filename,
                        tipo_archivo: "text/csv",
                        estado_procesamiento: file.estado,
                        created_at: new Date(file.modified).toISOString(),
                        user_id: "current-user",
                      })
                    }
                  >
                    <div className="flex items-center justify-between">
                      {/* Información del archivo */}
                      <div>
                        <h4 className="font-medium text-foreground">{file.filename}</h4>
                        <p className="text-sm text-muted-foreground">
                          Tamaño: {(file.size / 1024).toFixed(1)} KB
                        </p>
                      </div>

                      {/* Botón + icono check alineados a la derecha */}
                      <div className="flex items-center gap-3">
                        {/* Ícono de selección con transición suave */}
                        <CheckCircle2
                          className={`w-5 h-5 transition-opacity duration-200 ${
                            currentDataset?.nombre_archivo === file.filename
                              ? "opacity-100 text-primary"
                              : "opacity-0"
                          }`}
                        />

                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            setFileToDelete(file.id);
                            setFileNameToDelete(file.filename);
                            setShowDeleteModal(true);
                          }}
                        >
                          Eliminar
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-muted-foreground">No hay archivos subidos</p>
                <p className="text-sm text-muted-foreground">
                  Sube un archivo CSV para comenzar
                </p>
              </div>
            )}
          </Card>
        )}
      </div>
        {showDeleteModal && (
            <div className="fixed inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm z-50">
              <Card className="p-6 max-w-sm w-full bg-background border border-border shadow-lg">
                <h3 className="text-lg font-semibold text-foreground mb-4">
                  Confirmar eliminación
                </h3>
                <p className="text-muted-foreground mb-6">
                  ¿Seguro que deseas eliminar{" "}
                  <span className="font-medium text-foreground">"{fileNameToDelete}"</span>?  
                  Esta acción no se puede deshacer.
                </p>
                <div className="flex justify-end gap-3">
                  <Button
                    variant="outline"
                    onClick={() => setShowDeleteModal(false)}
                  >
                    Cancelar
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => {
                      if (fileToDelete) {
                        deleteMutation.mutate(fileToDelete);
                      }
                      setShowDeleteModal(false);
                    }}
                  >
                    Eliminar
                  </Button>
                </div>
              </Card>
            </div>
          )}
    </div>
  );
}