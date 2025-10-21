import { useEffect, useState, useRef } from 'react';
import { PipelineJob } from '@/services/api';

export function useSupabaseRealtime(jobId: string | null) {
  const [job, setJob] = useState<PipelineJob | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      return;
    }
    
    setJob(null);
    setError(null);

    // Usar polling simple a través del backend
    setIsConnected(true);
    setError(null);

    const pollJob = async () => {
      try {
        const response = await fetch(`http://localhost:8002/api/data/jobs/${jobId}`);
        if (response.ok) {
          const jobData = await response.json();
          setJob(jobData);
          setIsConnected(true);
          
          // Parar polling si el job está completado o fallido
          if (jobData.estado === 'completado' || jobData.estado === 'fallido') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            return;
          }
        }
      } catch (err) {
        console.error('Error polling job status:', err);
        setError('Error connecting to backend');
        setIsConnected(false);
      }
    };
    
    // Hacer un poll inmediato y luego cada 5s
    void pollJob();
    // Iniciar polling cada 5 segundos
    pollIntervalRef.current = setInterval(pollJob, 5000);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [jobId]);

  return {
    job,
    isConnected,
    error,
    progress: job?.progreso || 0,
    status: job?.estado || 'pending',
    message: job?.mensaje_actual || '',
    metrics: job?.metricas_parciales || null,
  };
}