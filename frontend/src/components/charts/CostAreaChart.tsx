import {
  ResponsiveContainer,
  AreaChart,
  Area,
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
  active_cost: number;
  deleted_cost: number;
}

interface CostAreaChartProps {
  data: DataPoint[];
  title?: string;
}

export default function CostAreaChart({
  data,
  title = "Monthly Cost Trend",
}: CostAreaChartProps) {
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
          <AreaChart data={formatted} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <defs>
              <linearGradient id="activeGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="deletedGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
            </defs>
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
              tickFormatter={(v: number) => `$${v.toLocaleString()}`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1f2937",
                border: "1px solid #374151",
                borderRadius: "0.5rem",
                color: "#f3f4f6",
              }}
              labelStyle={{ color: "#9ca3af" }}
              formatter={(value: number, name: string) => {
                const label = name === "active_cost" ? "Active Storage" : "Deleted Storage";
                return [
                  `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                  label,
                ];
              }}
              itemSorter={() => -1}
            />
            <Legend
              formatter={(value: string) =>
                value === "active_cost" ? "Active Storage Cost" : "Deleted Storage Cost"
              }
              wrapperStyle={{ color: "#9ca3af", fontSize: 12 }}
            />
            <Area
              type="monotone"
              dataKey="active_cost"
              stackId="cost"
              stroke="#10b981"
              strokeWidth={2}
              fill="url(#activeGradient)"
            />
            <Area
              type="monotone"
              dataKey="deleted_cost"
              stackId="cost"
              stroke="#f59e0b"
              strokeWidth={2}
              fill="url(#deletedGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
