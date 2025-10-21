import { useNavigate } from "react-router-dom";
import { Database, Droplet, Brain, BarChart3 } from "lucide-react";
import { StageCard } from "@/components/StageCard";
import { Card } from "@/components/ui/card";

const Index = () => {
  const navigate = useNavigate();

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
      description: "Configura y entrena modelos de machine learning",
      icon: Brain,
      status: "pending" as const,
      route: "/train-model",
    },
    {
      title: "Ver Resultados",
      description: "Analiza métricas y exporta modelos entrenados",
      icon: BarChart3,
      status: "pending" as const,
      route: "/results",
    },
  ];

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-2">
            Pipeline de Machine Learning
          </h1>
          <p className="text-lg text-muted-foreground">
            Sigue estos pasos para entrenar y evaluar tus modelos de ML
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {stages.map((stage, index) => (
            <StageCard
              key={index}
              title={stage.title}
              description={stage.description}
              icon={stage.icon}
              status={stage.status}
              onClick={() => navigate(stage.route)}
            />
          ))}
        </div>

        <Card className="p-6 mt-8">
          <h2 className="text-2xl font-bold text-foreground mb-4">
            Flujo de Trabajo
          </h2>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                1
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Cargar Dataset</h3>
                <p className="text-sm text-muted-foreground">
                  Sube tu archivo CSV y visualiza los datos
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                2
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Limpiar Datos</h3>
                <p className="text-sm text-muted-foreground">
                  Elimina nulos, duplicados y preprocesa los datos
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                3
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Entrenar Modelo</h3>
                <p className="text-sm text-muted-foreground">
                  Selecciona el tipo de modelo y parámetros
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                4
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Exportar Modelo</h3>
                <p className="text-sm text-muted-foreground">
                  Guarda el modelo entrenado en la base de datos
                </p>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Index;