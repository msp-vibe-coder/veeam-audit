import { useState, useMemo } from "react";
import {
  HardDrive,
  Cloud,
  Trash2,
  Percent,
  DollarSign,
  AlertTriangle,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { fetchDashboard, fetchIssues } from "@/lib/api";
import KpiCard from "@/components/ui/KpiCard";
import StorageTrendChart from "@/components/charts/StorageTrendChart";
import CostAreaChart from "@/components/charts/CostAreaChart";
import IssuesSeverityChart from "@/components/charts/IssuesSeverityChart";
import DateRangePicker from "@/components/ui/DateRangePicker";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { DashboardData, Issue } from "@/types";

export default function Dashboard() {
  const today = new Date();
  const thirtyDaysAgo = new Date(today);
  thirtyDaysAgo.setDate(today.getDate() - 30);
  const fmt = (d: Date) => d.toISOString().slice(0, 10);

  const [dateFrom, setDateFrom] = useState(fmt(thirtyDaysAgo));
  const [dateTo, setDateTo] = useState(fmt(today));

  const { data: dashboard, loading: dashLoading, error: dashError } = useApi<DashboardData>(
    () =>
      fetchDashboard(
        dateFrom && dateTo ? { date_from: dateFrom, date_to: dateTo } : undefined,
      ),
    [dateFrom, dateTo],
  );

  const { data: issues } = useApi<Issue[]>(() => fetchIssues(), []);

  const storageTrendData = useMemo(() => {
    if (!dashboard?.daily_summaries) return [];
    return dashboard.daily_summaries.map((s) => ({
      date: s.report_date,
      veeam_tb: s.veeam_tb,
      wasabi_active_tb: s.wasabi_active_tb,
      wasabi_deleted_tb: s.wasabi_deleted_tb,
    }));
  }, [dashboard]);

  const costTrendData = useMemo(() => {
    if (!dashboard?.daily_summaries) return [];
    return dashboard.daily_summaries.map((s) => ({
      date: s.report_date,
      active_cost: s.active_cost,
      deleted_cost: s.deleted_cost,
    }));
  }, [dashboard]);

  const severityData = useMemo(() => {
    if (!issues) return [];
    const counts: Record<string, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    for (const issue of issues) {
      const sev = issue.severity.toUpperCase();
      if (sev in counts) {
        counts[sev] = (counts[sev] ?? 0) + 1;
      }
    }
    return Object.entries(counts).map(([severity, count]) => ({ severity, count }));
  }, [issues]);

  function handleDateApply(from: string, to: string) {
    setDateFrom(from);
    setDateTo(to);
  }

  if (dashLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <LoadingSpinner size="lg" message="Loading dashboard..." />
      </div>
    );
  }

  if (dashError) {
    return (
      <div className="flex h-96 flex-col items-center justify-center gap-2">
        <XCircle className="h-12 w-12 text-red-500" />
        <p className="text-lg font-medium text-gray-400">Failed to load dashboard</p>
        <p className="text-sm text-gray-500">{dashError}</p>
      </div>
    );
  }

  const kpis = dashboard?.kpis;
  const pipeline = dashboard?.latest_pipeline_run;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Backup audit overview and key metrics
          </p>
        </div>
        <DateRangePicker
          dateFrom={dateFrom}
          dateTo={dateTo}
          onApply={handleDateApply}
        />
      </div>

      {/* Pipeline Status */}
      {pipeline && (
        <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white
                        px-4 py-3 dark:border-gray-700/50 dark:bg-gray-800/50">
          <PipelineIcon status={pipeline.status} />
          <div className="flex-1">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Pipeline:{" "}
            </span>
            <span className="text-sm capitalize text-gray-500 dark:text-gray-400">
              {pipeline.status}
            </span>
          </div>
          {pipeline.completed_at && (
            <span className="text-xs text-gray-400">
              Last run: {new Date(pipeline.completed_at).toLocaleString()}
            </span>
          )}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">
        <KpiCard
          title="Total Veeam"
          value={`${(kpis?.total_veeam_tb ?? 0).toFixed(2)} TB`}
          icon={<HardDrive className="h-5 w-5" />}
          color="emerald"
        />
        <KpiCard
          title="Total Wasabi"
          value={`${(kpis?.total_wasabi_tb ?? 0).toFixed(2)} TB`}
          icon={<Cloud className="h-5 w-5" />}
          color="blue"
        />
        <KpiCard
          title="Wasabi Deleted"
          value={`${(kpis?.total_wasabi_deleted_tb ?? 0).toFixed(2)} TB`}
          icon={<Trash2 className="h-5 w-5" />}
          color="red"
        />
        <KpiCard
          title="Discrepancy"
          value={`${(kpis?.discrepancy_pct ?? 0).toFixed(1)}%`}
          icon={<Percent className="h-5 w-5" />}
          color={(kpis?.discrepancy_pct ?? 0) > 10 ? "red" : "amber"}
        />
        <KpiCard
          title="Total Cost"
          value={`$${(kpis?.total_cost ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          icon={<DollarSign className="h-5 w-5" />}
          color="emerald"
        />
        <KpiCard
          title="Active Issues"
          value={kpis?.active_issues ?? 0}
          icon={<AlertTriangle className="h-5 w-5" />}
          color={(kpis?.active_issues ?? 0) > 0 ? "red" : "emerald"}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <StorageTrendChart data={storageTrendData} />
        <CostAreaChart data={costTrendData} />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <IssuesSeverityChart data={severityData} />

        {/* Job Summary card */}
        {dashboard?.daily_summaries && dashboard.daily_summaries.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm
                          dark:border-gray-700/50 dark:bg-gray-800/50">
            <h3 className="mb-4 text-sm font-medium text-gray-500 dark:text-gray-400">
              Latest Job Summary
            </h3>
            {(() => {
              const latest = dashboard.daily_summaries[dashboard.daily_summaries.length - 1];
              if (!latest) return null;
              return (
                <div className="grid grid-cols-2 gap-4">
                  <Stat
                    label="Total Jobs"
                    value={latest.total_jobs}
                    icon={<Activity className="h-4 w-4 text-gray-400" />}
                  />
                  <Stat
                    label="Successful"
                    value={latest.successful_jobs}
                    icon={<CheckCircle2 className="h-4 w-4 text-emerald-500" />}
                  />
                  <Stat
                    label="Failed"
                    value={latest.failed_jobs}
                    icon={<XCircle className="h-4 w-4 text-red-500" />}
                  />
                  <Stat
                    label="Warnings"
                    value={latest.warning_jobs}
                    icon={<AlertTriangle className="h-4 w-4 text-amber-500" />}
                  />
                </div>
              );
            })()}
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg bg-gray-50 px-4 py-3 dark:bg-gray-700/30">
      {icon}
      <div>
        <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
        <p className="text-lg font-semibold text-gray-900 dark:text-white">{value}</p>
      </div>
    </div>
  );
}

function PipelineIcon({ status }: { status: string }) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-5 w-5 text-emerald-500" />;
    case "failed":
      return <XCircle className="h-5 w-5 text-red-500" />;
    case "running":
      return <Clock className="h-5 w-5 animate-pulse text-amber-500" />;
    default:
      return <Activity className="h-5 w-5 text-gray-400" />;
  }
}
