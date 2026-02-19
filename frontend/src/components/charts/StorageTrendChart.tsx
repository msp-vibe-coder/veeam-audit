import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { format, parseISO } from "date-fns";
import Card from "@/components/ui/Card";

interface DataPoint {
  date: string;
  veeam_tb: number;
  wasabi_active_tb: number;
  wasabi_deleted_tb: number;
}

interface StorageTrendChartProps {
  data: DataPoint[];
  title?: string;
}

export default function StorageTrendChart({
  data,
  title = "Storage Trend",
}: StorageTrendChartProps) {
  const formatted = data.map((d) => ({
    ...d,
    dateLabel: (() => {
      try {
        return format(parseISO(d.date), "MMM d");
      } catch {
        return d.date;
      }
    })(),
  }));

  return (
    <Card>
      <h3 className="mb-4 text-sm font-medium text-gray-500 dark:text-gray-400">
        {title}
      </h3>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={formatted} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
            <XAxis
              dataKey="dateLabel"
              tick={{ fill: "#9ca3af", fontSize: 12 }}
              axisLine={{ stroke: "#4b5563" }}
              tickLine={{ stroke: "#4b5563" }}
            />
            <YAxis
              tick={{ fill: "#9ca3af", fontSize: 12 }}
              axisLine={{ stroke: "#4b5563" }}
              tickLine={{ stroke: "#4b5563" }}
              tickFormatter={(v: number) => `${v.toFixed(1)} TB`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1f2937",
                border: "1px solid #374151",
                borderRadius: "0.5rem",
                color: "#f3f4f6",
              }}
              labelStyle={{ color: "#9ca3af" }}
              formatter={(value: number, name: string) => [
                `${value.toFixed(2)} TB`,
                name === "veeam_tb" ? "Veeam" : name === "wasabi_active_tb" ? "Wasabi Active" : "Wasabi Deleted",
              ]}
            />
            <Legend
              wrapperStyle={{ color: "#9ca3af", fontSize: 12 }}
              formatter={(value: string) =>
                value === "veeam_tb" ? "Veeam TB" : value === "wasabi_active_tb" ? "Wasabi Active TB" : "Wasabi Deleted TB"
              }
            />
            <Line
              type="monotone"
              dataKey="veeam_tb"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="wasabi_active_tb"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="wasabi_deleted_tb"
              stroke="#f43f5e"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
