import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";
import Card from "@/components/ui/Card";

interface SeverityData {
  severity: string;
  count: number;
}

interface IssuesSeverityChartProps {
  data: SeverityData[];
  title?: string;
}

const severityColors: Record<string, string> = {
  CRITICAL: "#ef4444",
  HIGH: "#f97316",
  MEDIUM: "#eab308",
  LOW: "#3b82f6",
};

export default function IssuesSeverityChart({
  data,
  title = "Issues by Severity",
}: IssuesSeverityChartProps) {
  return (
    <Card>
      <h3 className="mb-4 text-sm font-medium text-gray-500 dark:text-gray-400">
        {title}
      </h3>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
            <XAxis
              dataKey="severity"
              tick={{ fill: "#9ca3af", fontSize: 12 }}
              axisLine={{ stroke: "#4b5563" }}
              tickLine={{ stroke: "#4b5563" }}
            />
            <YAxis
              tick={{ fill: "#9ca3af", fontSize: 12 }}
              axisLine={{ stroke: "#4b5563" }}
              tickLine={{ stroke: "#4b5563" }}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1f2937",
                border: "1px solid #374151",
                borderRadius: "0.5rem",
                color: "#f3f4f6",
              }}
              labelStyle={{ color: "#9ca3af" }}
              formatter={(value: number) => [value, "Count"]}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {data.map((entry, index) => (
                <Cell
                  key={index}
                  fill={severityColors[entry.severity] ?? "#6b7280"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
