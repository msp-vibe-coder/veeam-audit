import { useState, useMemo, useCallback } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceDot,
} from "recharts";
import { format, parseISO } from "date-fns";
import { useApi } from "@/hooks/useApi";
import { fetchTrendsDaily, fetchTrendsSites, fetchAnomalies } from "@/lib/api";
import Card from "@/components/ui/Card";
import DateRangePicker from "@/components/ui/DateRangePicker";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { DailySummary, SiteMetric, Anomaly } from "@/types";

type MetricKey = "storage" | "cost" | "discrepancy" | "success_rate";

const metricOptions: { value: MetricKey; label: string }[] = [
  { value: "storage", label: "Storage (TB)" },
  { value: "cost", label: "Cost ($)" },
  { value: "discrepancy", label: "Discrepancy (%)" },
  { value: "success_rate", label: "Success Rate (%)" },
];

const siteColors = [
  "#10b981",
  "#3b82f6",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
  "#84cc16",
  "#f97316",
  "#6366f1",
];

export default function Trends() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [metric, setMetric] = useState<MetricKey>("storage");
  const [selectedSites, setSelectedSites] = useState<Set<string>>(new Set());

  const { data: dailyData, loading: dailyLoading } = useApi<DailySummary[]>(
    () =>
      fetchTrendsDaily(
        dateFrom && dateTo ? { date_from: dateFrom, date_to: dateTo } : undefined,
      ),
    [dateFrom, dateTo],
  );

  const { data: sitesData } = useApi<SiteMetric[]>(() => fetchTrendsSites(), []);

  const { data: anomalies } = useApi<Anomaly[]>(
    () =>
      fetchAnomalies(
        dateFrom && dateTo ? { date_from: dateFrom, date_to: dateTo } : undefined,
      ),
    [dateFrom, dateTo],
  );

  // Get unique site codes from site data
  const allSiteCodes = useMemo(() => {
    if (!sitesData) return [];
    return [...new Set(sitesData.map((s) => s.site_code))].sort();
  }, [sitesData]);

  const toggleSite = useCallback((code: string) => {
    setSelectedSites((prev) => {
      const next = new Set(prev);
      if (next.has(code)) {
        next.delete(code);
      } else {
        next.add(code);
      }
      return next;
    });
  }, []);

  // Build chart data based on metric selection
  const chartData = useMemo(() => {
    if (!dailyData) return [];
    return dailyData.map((d) => {
      const point: Record<string, unknown> = {
        date: d.report_date,
        dateLabel: (() => {
          try {
            return format(parseISO(d.report_date), "MMM d");
          } catch {
            return d.report_date;
          }
        })(),
      };

      switch (metric) {
        case "storage":
          point.veeam_tb = d.veeam_tb;
          point.wasabi_active_tb = d.wasabi_active_tb;
          break;
        case "cost":
          point.total_cost = d.total_cost;
          break;
        case "discrepancy":
          point.discrepancy_pct = d.discrepancy_pct;
          break;
        case "success_rate":
          if (d.total_jobs > 0) {
            point.success_rate = ((d.successful_jobs / d.total_jobs) * 100);
          }
          break;
      }

      return point;
    });
  }, [dailyData, metric]);

  // Find anomaly markers that match the current date range
  const anomalyMarkers = useMemo(() => {
    if (!anomalies || !chartData.length) return [];
    return anomalies
      .filter((a) =>
        chartData.some((d) => d.date === a.report_date),
      )
      .slice(0, 20); // Limit markers for readability
  }, [anomalies, chartData]);

  function handleDateApply(from: string, to: string) {
    setDateFrom(from);
    setDateTo(to);
  }

  function getYAxisLabel(): string {
    switch (metric) {
      case "storage":
        return "TB";
      case "cost":
        return "$";
      case "discrepancy":
      case "success_rate":
        return "%";
    }
  }

  function formatYTick(v: number): string {
    switch (metric) {
      case "storage":
        return `${v.toFixed(1)} TB`;
      case "cost":
        return `$${v.toLocaleString()}`;
      case "discrepancy":
      case "success_rate":
        return `${v.toFixed(0)}%`;
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Trends</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Analyze storage, cost, and performance trends over time
          </p>
        </div>
        <DateRangePicker
          dateFrom={dateFrom}
          dateTo={dateTo}
          onApply={handleDateApply}
        />
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Metric selector */}
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
            Metric
          </label>
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value as MetricKey)}
            className="input-field w-48"
          >
            {metricOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Site Selector */}
      {allSiteCodes.length > 0 && (
        <Card>
          <h3 className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400">
            Overlay Sites
          </h3>
          <div className="flex flex-wrap gap-2">
            {allSiteCodes.map((code, idx) => (
              <label
                key={code}
                className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5
                  text-xs font-medium cursor-pointer transition-colors duration-150
                  ${
                    selectedSites.has(code)
                      ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-500"
                      : "border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-600"
                  }`}
              >
                <input
                  type="checkbox"
                  checked={selectedSites.has(code)}
                  onChange={() => toggleSite(code)}
                  className="sr-only"
                />
                <div
                  className="h-2.5 w-2.5 rounded-full"
                  style={{
                    backgroundColor: siteColors[idx % siteColors.length],
                  }}
                />
                {code}
              </label>
            ))}
          </div>
        </Card>
      )}

      {/* Chart */}
      <Card>
        <h3 className="mb-4 text-sm font-medium text-gray-500 dark:text-gray-400">
          {metricOptions.find((m) => m.value === metric)?.label ?? "Trend"} Over Time
        </h3>
        {dailyLoading ? (
          <div className="flex h-72 items-center justify-center">
            <LoadingSpinner message="Loading trend data..." />
          </div>
        ) : (
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
              >
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
                  tickFormatter={formatYTick}
                  label={{
                    value: getYAxisLabel(),
                    angle: -90,
                    position: "insideLeft",
                    fill: "#9ca3af",
                  }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1f2937",
                    border: "1px solid #374151",
                    borderRadius: "0.5rem",
                    color: "#f3f4f6",
                  }}
                  labelStyle={{ color: "#9ca3af" }}
                />
                <Legend wrapperStyle={{ color: "#9ca3af", fontSize: 12 }} />

                {/* Main metric lines */}
                {metric === "storage" && (
                  <>
                    <Line
                      type="monotone"
                      dataKey="veeam_tb"
                      name="Veeam TB"
                      stroke="#10b981"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="wasabi_active_tb"
                      name="Wasabi Active TB"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={false}
                    />
                  </>
                )}
                {metric === "cost" && (
                  <Line
                    type="monotone"
                    dataKey="total_cost"
                    name="Total Cost"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={false}
                  />
                )}
                {metric === "discrepancy" && (
                  <Line
                    type="monotone"
                    dataKey="discrepancy_pct"
                    name="Discrepancy %"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    dot={false}
                  />
                )}
                {metric === "success_rate" && (
                  <Line
                    type="monotone"
                    dataKey="success_rate"
                    name="Success Rate %"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={false}
                  />
                )}

                {/* Anomaly markers */}
                {anomalyMarkers.map((a) => {
                  const matchPoint = chartData.find(
                    (d) => d.date === a.report_date,
                  );
                  if (!matchPoint) return null;

                  let yKey = "veeam_tb";
                  if (metric === "cost") yKey = "total_cost";
                  if (metric === "discrepancy") yKey = "discrepancy_pct";
                  if (metric === "success_rate") yKey = "success_rate";

                  const yVal = matchPoint[yKey];
                  if (yVal == null) return null;

                  return (
                    <ReferenceDot
                      key={a.id}
                      x={matchPoint.dateLabel as string}
                      y={yVal as number}
                      r={5}
                      fill="#ef4444"
                      stroke="#ef4444"
                      strokeWidth={2}
                    />
                  );
                })}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      {/* Anomaly List */}
      {anomalies && anomalies.length > 0 && (
        <Card>
          <h3 className="mb-4 text-sm font-medium text-gray-500 dark:text-gray-400">
            Detected Anomalies ({anomalies.length})
          </h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {anomalies.slice(0, 20).map((a) => (
              <div
                key={a.id}
                className="flex items-start gap-3 rounded-lg bg-gray-50 px-4 py-3
                           dark:bg-gray-700/30"
              >
                <div
                  className={`mt-0.5 h-2.5 w-2.5 rounded-full flex-shrink-0 ${
                    a.severity === "CRITICAL"
                      ? "bg-red-500"
                      : a.severity === "HIGH"
                        ? "bg-orange-500"
                        : a.severity === "MEDIUM"
                          ? "bg-yellow-500"
                          : "bg-blue-500"
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-700 dark:text-gray-300 truncate">
                    {a.description ?? `${a.type}: ${a.metric ?? "unknown metric"}`}
                  </p>
                  <p className="text-xs text-gray-400">
                    {a.report_date} | {a.severity} | {a.type}
                    {a.change_pct != null && ` | ${a.change_pct.toFixed(1)}% change`}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
