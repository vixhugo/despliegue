-- Habilitar la extensión para generar UUIDs aleatorios (si no está ya habilitada)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

----------------------------------------------------------------------------------
-- 1. TABLA 'datos_cargados' (Archivo original subido)

CREATE TABLE IF NOT EXISTS public.datos_cargados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    -- CLAVE DE SEGURIDAD: Conexión al usuario de Supabase Auth
    usuario_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    nombre_archivo VARCHAR(255) NOT NULL,
    ruta_archivo TEXT NOT NULL,
    tamano_archivo BIGINT,
    estado VARCHAR(50) DEFAULT 'cargado',
    metadatos JSONB
);

ALTER TABLE public.datos_cargados ENABLE ROW LEVEL SECURITY;
-- 
----------------------------------------------------------------------------------
-- 2. TABLA 'datos_limpiados' (Resultado de la limpieza del archivo original)

CREATE TABLE IF NOT EXISTS public.datos_limpiados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    
    -- Vínculo a la tabla padre. CASCADE asegura que se borre si se borra el original.
    datos_cargados_id UUID NOT NULL REFERENCES public.datos_cargados(id) ON DELETE CASCADE,
    
    nombre_archivo_original VARCHAR(255) NOT NULL,
    nombre_archivo_limpio VARCHAR(255) NOT NULL,
    ruta_archivo_limpio TEXT NOT NULL,
    estadisticas_limpieza JSONB,
    estado VARCHAR(50) DEFAULT 'limpiado'
    -- No se necesita usuario_id aquí, se obtiene a través de datos_cargados.
);

ALTER TABLE public.datos_limpiados ENABLE ROW LEVEL SECURITY;

----------------------------------------------------------------------------------
-- 3. TABLA 'modelos_entrenados' (Resultados del entrenamiento)

CREATE TABLE IF NOT EXISTS public.modelos_entrenados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    
    -- Vínculo a la tabla padre. CASCADE asegura que se borre si se borra el dato limpio.
    datos_limpiados_id UUID NOT NULL REFERENCES public.datos_limpiados(id) ON DELETE CASCADE,
    
    nombre_modelo VARCHAR(255) NOT NULL,
    tipo_modelo VARCHAR(100) NOT NULL,
    metricas_entrenamiento JSONB,
    configuracion_modelo JSONB,
    ruta_modelo TEXT,
    confusion_matrix JSONB,
    estado VARCHAR(50) DEFAULT 'entrenado'
);

ALTER TABLE public.modelos_entrenados ENABLE ROW LEVEL SECURITY;

----------------------------------------------------------------------------------
-- 4. TABLA 'predicciones' (Registro de predicciones)

CREATE TABLE IF NOT EXISTS public.predicciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    
    -- Vínculo al modelo padre. CASCADE asegura que se borre si se borra el modelo.
    modelo_id UUID NOT NULL REFERENCES public.modelos_entrenados(id) ON DELETE CASCADE,
    
    datos_entrada JSONB,
    prediccion JSONB,
    confianza DECIMAL(5,4)
);

ALTER TABLE public.predicciones ENABLE ROW LEVEL SECURITY;

----------------------------------------------------------------------------------
-- 5. TABLA 'pipeline_jobs' (Seguimiento de tareas)

CREATE TABLE IF NOT EXISTS public.pipeline_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    
    -- Vínculo a la tabla de origen. CASCADE asegura que se borre si se borra el original.
    datos_cargados_id UUID NOT NULL REFERENCES public.datos_cargados(id) ON DELETE CASCADE,
    
    tipo_tarea VARCHAR(50) NOT NULL,
    estado VARCHAR(50) DEFAULT 'pendiente',
    progreso DECIMAL(5,2) DEFAULT 0.00,
    mensaje_actual TEXT,
    metricas_parciales JSONB,
    fecha_inicio TIMESTAMP WITH TIME ZONE,
    fecha_fin TIMESTAMP WITH TIME ZONE
);

ALTER TABLE public.pipeline_jobs ENABLE ROW LEVEL SECURITY;