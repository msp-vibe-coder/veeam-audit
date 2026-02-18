import clsx from "clsx";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import Card from "./Card";

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  color?: "emerald" | "blue" | "amber" | "red" | "gray";
}

const colorClasses: Record<string, { bg: string; text: string; icon: string }> = {
  emerald: {
    bg: "bg-emerald-500/10",
    text: "text-emerald-500",
    icon: "text-emerald-500",
  },
  blue: {
    bg: "bg-blue-500/10",
    text: "text-blue-500",
    icon: "text-blue-500",
  },
  amber: {
    bg: "bg-amber-500/10",
    text: "text-amber-500",
    icon: "text-amber-500",
  },
  red: {
    bg: "bg-red-500/10",
    text: "text-red-500",
    icon: "text-red-500",
  },
  gray: {
    bg: "bg-gray-500/10",
    text: "text-gray-500",
    icon: "text-gray-500",
  },
};

function TrendIcon({ trend }: { trend?: "up" | "down" | "neutral" }) {
  if (!trend) return null;
  if (trend === "up") return <TrendingUp className="h-4 w-4 text-emerald-500" />;
  if (trend === "down") return <TrendingDown className="h-4 w-4 text-red-500" />;
  return <Minus className="h-4 w-4 text-gray-400" />;
}

export default function KpiCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  color = "emerald",
}: KpiCardProps) {
  const c = colorClasses[color] ?? colorClasses["emerald"]!;

  return (
    <Card>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
          <div className="mt-2 flex items-baseline gap-2">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
            <TrendIcon trend={trend} />
          </div>
          {subtitle && (
            <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">{subtitle}</p>
          )}
        </div>
        {icon && c && (
          <div className={clsx("rounded-lg p-2.5", c.bg)}>
            <div className={c.icon}>{icon}</div>
          </div>
        )}
      </div>
    </Card>
  );
}
