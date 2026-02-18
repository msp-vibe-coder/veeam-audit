import clsx from "clsx";
import type { Severity } from "@/types";

interface BadgeProps {
  severity: Severity | string;
  className?: string;
}

const colorMap: Record<string, string> = {
  CRITICAL: "bg-red-500/10 text-red-500 border-red-500/20",
  HIGH: "bg-orange-500/10 text-orange-500 border-orange-500/20",
  MEDIUM: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  LOW: "bg-blue-500/10 text-blue-500 border-blue-500/20",
};

export default function Badge({ severity, className }: BadgeProps) {
  const upper = severity.toUpperCase();
  const colors = colorMap[upper] ?? "bg-gray-500/10 text-gray-500 border-gray-500/20";

  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        colors,
        className,
      )}
    >
      {severity}
    </span>
  );
}
