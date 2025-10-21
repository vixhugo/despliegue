import { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StageCardProps {
  title: string;
  description: string;
  icon: LucideIcon;
  status: "pending" | "active" | "completed";
  onClick?: () => void;
}

export function StageCard({ title, description, icon: Icon, status, onClick }: StageCardProps) {
  return (
    <Card
      className={cn(
        "p-6 cursor-pointer transition-all duration-300 hover:shadow-lg",
        status === "completed" && "border-success bg-success/5",
        status === "active" && "border-primary bg-primary/5 shadow-md",
        status === "pending" && "border-border hover:border-primary/50"
      )}
      onClick={onClick}
    >
      <div className="flex items-start gap-4">
        <div
          className={cn(
            "w-12 h-12 rounded-xl flex items-center justify-center",
            status === "completed" && "bg-success text-success-foreground",
            status === "active" && "bg-primary text-primary-foreground",
            status === "pending" && "bg-muted text-muted-foreground"
          )}
        >
          <Icon className="w-6 h-6" />
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-lg text-foreground mb-1">{title}</h3>
          <p className="text-sm text-muted-foreground">{description}</p>
          {/* AquÃ­ es donde estaba el div con el estado, ha sido eliminado */}
        </div>
      </div>
    </Card>
  );
}