const API_BASE_URL = 'http://localhost:8005/api';


export interface UploadedFile {
  id: string;
  filename: string;
  path: string;
  size: number;
  modified: number;
  estado: string;
  metadatos: any;
}


export interface Model {
  id: string;
  dataset_id: string;
  datos_exportados: any;
  metricas_entrenamiento: any;
  fecha_entrenamiento: string;
  status: string;
}


export interface CleanedFile {
  id: string;
  nombre_original: string;
  nombre_limpio: string;
  path: string;
  modified: number;
  estado: string;
  estadisticas: any;
}

export interface PipelineJob {
  id: string;
  datos_cargados_id: string;
  tipo_tarea: string;
  estado: string;
  progreso: number;
  mensaje_actual: string | null;
  metricas_parciales: any;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  created_at: string;
  updated_at: string;
  archivo_nombre?: string;
}

export interface TrainCleanedRequest {
  filename: string;
  model_type: string;
  target_column: string;
  test_size?: number;
  cleaned_file_id: string;
  parameters?: Record<string, any>;
}


export const dataApi = {
  async uploadFile(file: File): Promise<{ dataset_id: number; data_info: any }> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE_URL}/data/upload`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const text = await response.text();
      let serverDetail = text;
      try {
        const json = JSON.parse(text);
        serverDetail = JSON.stringify(json);
      } catch (_) {}
      throw new Error(`Failed to upload file: ${response.status} ${response.statusText} - ${serverDetail}`);
    }

    return response.json();
  },

  async getUploadedFiles(): Promise<UploadedFile[]> {
    const response = await fetch(`${API_BASE_URL}/data/uploaded-files`);
    if (!response.ok) throw new Error('Failed to fetch uploaded files');
    return response.json();
  },

  async deleteDataset(id: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/data/delete-file/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete dataset');
    return response.json();
  },

  async cleanDataFromDatabase(fileId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/data/clean-data/${fileId}`, { method: 'POST' });
    if (!response.ok) throw new Error('Failed to clean data from database');
    return response.json();
  },

  // ✅ NUEVO MÉTODO: obtener lista de archivos limpiados
  async getCleanedFiles(): Promise<CleanedFile[]> {
    const response = await fetch(`${API_BASE_URL}/data/cleaned-files`);
    if (!response.ok) throw new Error('Failed to fetch cleaned files');
    return response.json();
  },

  async getFilePreview(filename: string, limit: number = 10): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/data/preview-file/${filename}?limit=${limit}`);
    if (!response.ok) {
      console.warn(`⚠️ preview-file falló (${response.status}), intentando preview-cleaned...`);
      const cleanedResponse = await fetch(`${API_BASE_URL}/data/preview-cleaned/${filename}?limit=${limit}`);
      if (!cleanedResponse.ok) {
        throw new Error('Failed to fetch file preview (neither original nor cleaned)');
      }
      return cleanedResponse.json();
    }
    return response.json();
  },

  async getCleanedFilePreview(filename: string, limit: number = 10): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/data/preview-cleaned/${filename}?limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch cleaned file preview');
    return response.json();
  },

  async startCleanDataJob(fileId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/data/jobs/clean-data/${fileId}`, { method: 'POST' });
    if (!response.ok) throw new Error('Failed to start clean data job');
    return response.json();
  },

  async getJobStatus(jobId: string): Promise<PipelineJob> {
    const response = await fetch(`${API_BASE_URL}/data/jobs/${jobId}`);
    if (!response.ok) throw new Error('Failed to fetch job status');
    return response.json();
  },

  async getJobsByFile(fileId: string): Promise<PipelineJob[]> {
    const response = await fetch(`${API_BASE_URL}/data/jobs/file/${fileId}`);
    if (!response.ok) throw new Error('Failed to fetch jobs by file');
    return response.json();
  },

  async getAllJobs(): Promise<PipelineJob[]> {
    const response = await fetch(`${API_BASE_URL}/data/jobs`);
    if (!response.ok) throw new Error('Failed to fetch all jobs');
    return response.json();
  },

  async deleteJob(jobId: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/data/jobs/${jobId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to delete job');
    return response.json();
  },
};

// Models API
export const modelsApi = {

  async trainModelWithFile(data: {
    filename: string;
    model_type: string;
    target_column: string;
    test_size?: number;
    cleaned_file_id?: string;
    parameters?: Record<string, any>;
  }): Promise<any> {
    const endpoint = data.cleaned_file_id ? '/models/train-cleaned-file' : '/models/train-file';
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      // Try to extract useful error details from the response body
      const text = await response.text();
      let serverDetail = text;
      try {
        const json = JSON.parse(text);
        serverDetail = JSON.stringify(json);
      } catch (_) {
        // not JSON, keep raw text
      }
      throw new Error(`Failed to train model with file: ${response.status} ${response.statusText} - ${serverDetail}`);
    }
    
    return response.json();
  },

  async trainModelWithCleanedData(cleanedFileId: string, data: TrainCleanedRequest): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/models/train-cleaned/${cleanedFileId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const text = await response.text();
      let serverDetail = text;
      try {
        const json = JSON.parse(text);
        serverDetail = JSON.stringify(json);
      } catch (_) {
        // not JSON, keep raw text
      }
      throw new Error(`Failed to train model with cleaned data: ${response.status} ${response.statusText} - ${serverDetail}`);
    }
    
    return response.json();
  },

  async getModels(): Promise<Model[]> {
    const response = await fetch(`${API_BASE_URL}/results/models`);
    if (!response.ok) {
      throw new Error('Failed to fetch models');
    }
    return response.json();
  },


  async exportModel(modelId: string): Promise<{ file_path: string; download_url: string }> {
    const response = await fetch(`${API_BASE_URL}/models/${modelId}/export`, {
      method: 'POST',
    });
    
    if (!response.ok) {
      const text = await response.text();
      let serverDetail = text;
      try {
        const json = JSON.parse(text);
        serverDetail = JSON.stringify(json);
      } catch (_) {
      }
      throw new Error(`Failed to export model: ${response.status} ${response.statusText} - ${serverDetail}`);
    }
    
    return response.json();
  },
};

// Results API
export const resultsApi = {
  async getModels(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/results/models`);
    if (!response.ok) {
      throw new Error('Failed to fetch models');
    }
    return response.json();
  },

  async getModelMetrics(modelId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/results/metrics/${modelId}`);
    if (!response.ok) {
      throw new Error('Failed to fetch model metrics');
    }
    return response.json();
  },

  async getTrainingHistory(modelId: string): Promise<TrainingResult[]> {
    const response = await fetch(`${API_BASE_URL}/results/training-history/${modelId}`);
    if (!response.ok) {
      throw new Error('Failed to fetch training history');
    }
    return response.json();
  },

  async getConfusionMatrix(modelId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/results/confusion-matrix/${modelId}`);
    if (!response.ok) {
      throw new Error('Failed to fetch confusion matrix');
    }
    return response.json();
  },

  async getPerformanceComparison(): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/results/performance-comparison`);
    if (!response.ok) {
      throw new Error('Failed to fetch performance comparison');
    }
    return response.json();
  },

  async exportModelResults(modelId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/results/export/${modelId}`);
    if (!response.ok) {
      throw new Error('Failed to export model results');
    }
    return response.json();
  },
};

