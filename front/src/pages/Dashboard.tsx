import { useNavigate } from "react-router-dom";
import { Database, Droplet, Brain, BarChart3 } from "lucide-react";
import { StageCard } from "@/components/StageCard";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi, DashboardStats } from "@/services/api";

export default function Dashboard() {
  const navigate = useNavigate();

  // Fetch dashboard stats
  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApi.getStats,
  });

  const stages = [
    {
      title: "Cargar Datos",
      description: "Importa y visualiza tus datasets para el análisis",
      icon: Database,
      status: "completed" as const,
      route: "/load-data",
    },
    {
      title: "Limpiar Datos",
      description: "Preprocesa y transforma datos para entrenamiento",
      icon: Droplet,
      status: "active" as const,
      route: "/clean-data",
    },
    {
      title: "Entrenar Modelo",
      description: "Configura y entrena modelos de Machine Learning",
      icon: Brain,
      status: "pending" as const,
      route: "/train-model",
    },
    {
      title: "Ver Resultados",
      description: "Analiza métricas y rendimiento del modelo",
      icon: BarChart3,
      status: "pending" as const,
      route: "/results",
    },
  ];

  const progressPercentage = stats ? Math.round((stats.completed_models / Math.max(stats.models_trained, 1)) * 100) : 50;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto p-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-2">
            Pipeline de Machine Learning
          </h1>
          <p className="text-lg text-muted-foreground">
            Sistema completo para procesamiento de datos y entrenamiento de modelos
          </p>
        </div>

        <Card className="p-6 mb-8 bg-gradient-to-r from-primary/10 to-accent/10 border-primary/20">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-foreground">Progreso del Pipeline</h3>
              <p className="text-sm text-muted-foreground">
                {stats ? `${stats.completed_models} de ${stats.models_trained} modelos completados` : 'Cargando...'}
              </p>
            </div>
            <div className="text-3xl font-bold text-primary">
              {statsLoading ? '...' : `${progressPercentage}%`}
            </div>
          </div>
          <Progress value={progressPercentage} className="h-3" />
        </Card>

        <div className="grid gap-6 md:grid-cols-2 mb-8">
          {stages.map((stage) => (
            <StageCard
              key={stage.title}
              {...stage}
              onClick={() => navigate(stage.route)}
            />
          ))}
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-muted-foreground">Datasets Cargados</h4>
              <Database className="w-5 h-5 text-primary" />
            </div>
            <p className="text-3xl font-bold text-foreground">
              {statsLoading ? '...' : stats?.datasets_loaded || 0}
            </p>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-muted-foreground">Modelos Entrenados</h4>
              <Brain className="w-5 h-5 text-accent" />
            </div>
            <p className="text-3xl font-bold text-foreground">
              {statsLoading ? '...' : stats?.models_trained || 0}
            </p>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-muted-foreground">Precisión Promedio</h4>
              <BarChart3 className="w-5 h-5 text-success" />
            </div>
            <p className="text-3xl font-bold text-foreground">
              {statsLoading ? '...' : `${stats?.average_accuracy || 0}%`}
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}
