import { useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, HardDrive, Cloud, Percent, Briefcase } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { fetchSiteDetail, fetchSiteBdrs, fetchSiteBuckets } from "@/lib/api";
import Card from "@/components/ui/Card";
import KpiCard from "@/components/ui/KpiCard";
import DataTable, { type TableColumn } from "@/components/ui/DataTable";
import StorageTrendChart from "@/components/charts/StorageTrendChart";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { SiteDetailResponse, BdrMetric, BucketMetric } from "@/types";

export default function SiteDetail() {
  const { code } = useParams<{ code: string }>();

  const { data: detail, loading: detailLoading, error: detailError } =
    useApi<SiteDetailResponse>(() => fetchSiteDetail(code!), [code]);

  const { data: bdrs } = useApi<BdrMetric[]>(() => fetchSiteBdrs(code!), [code]);
  const { data: buckets } = useApi<BucketMetric[]>(() => fetchSiteBuckets(code!), [code]);

  const storageTrendData = useMemo(() => {
    if (!detail?.history) return [];
    return detail.history.map((h) => ({
      date: h.report_date,
      veeam_tb: h.veeam_tb,
      wasabi_active_tb: h.wasabi_active_tb,
    }));
  }, [detail]);

  const bdrColumns: TableColumn<BdrMetric>[] = [
    { key: "bdr_server", label: "BDR Server", sortable: false },
    {
      key: "backup_size_tb",
      label: "Backup Size (TB)",
      render: (v) => (v as number).toFixed(4),
    },
    {
      key: "disk_free_tb",
      label: "Disk Free (TB)",
      render: (v) => (v as number).toFixed(4),
    },
    {
      key: "disk_free_pct",
      label: "Disk Free %",
      render: (v) => {
        const val = v as number;
        return (
          <span
            className={
              val < 10
                ? "text-red-500 font-medium"
                : val < 25
                  ? "text-amber-500"
                  : "text-emerald-500"
            }
          >
            {val.toFixed(1)}%
          </span>
        );
      },
    },
  ];

  const bucketColumns: TableColumn<BucketMetric>[] = [
    { key: "bucket_name", label: "Bucket Name", sortable: false },
    {
      key: "active_tb",
      label: "Active (TB)",
      render: (v) => (v as number).toFixed(4),
    },
    {
      key: "deleted_tb",
      label: "Deleted (TB)",
      render: (v) => (v as number).toFixed(4),
    },
    {
      key: "active_cost",
      label: "Active Cost",
      render: (v) => `$${(v as number).toFixed(2)}`,
    },
    {
      key: "deleted_cost",
      label: "Deleted Cost",
      render: (v) => `$${(v as number).toFixed(2)}`,
    },
    {
      key: "total_cost",
      label: "Total Cost",
      render: (v) => `$${(v as number).toFixed(2)}`,
    },
  ];

  if (detailLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <LoadingSpinner size="lg" message={`Loading site ${code}...`} />
      </div>
    );
  }

  if (detailError || !detail) {
    return (
      <div className="flex h-96 flex-col items-center justify-center gap-4">
        <p className="text-lg text-gray-400">
          {detailError ?? `Site "${code}" not found`}
        </p>
        <Link to="/sites" className="btn-secondary">
          <ArrowLeft className="h-4 w-4" />
          Back to Sites
        </Link>
      </div>
    );
  }

  const current = detail.current;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/sites"
          className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600
                     dark:hover:bg-gray-800 dark:hover:text-gray-200 transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {detail.site_name ?? detail.site_code}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Site Code: {detail.site_code} | Report Date: {current.report_date}
          </p>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Veeam Storage"
          value={`${current.veeam_tb.toFixed(2)} TB`}
          icon={<HardDrive className="h-5 w-5" />}
          color="emerald"
        />
        <KpiCard
          title="Wasabi Active"
          value={`${current.wasabi_active_tb.toFixed(2)} TB`}
          icon={<Cloud className="h-5 w-5" />}
          color="blue"
        />
        <KpiCard
          title="Discrepancy"
          value={`${current.discrepancy_pct.toFixed(1)}%`}
          icon={<Percent className="h-5 w-5" />}
          color={current.discrepancy_pct > 10 ? "red" : "amber"}
        />
        <KpiCard
          title="Total Jobs"
          value={current.total_jobs}
          subtitle={
            current.success_rate_pct != null
              ? `${current.success_rate_pct.toFixed(1)}% success rate`
              : undefined
          }
          icon={<Briefcase className="h-5 w-5" />}
          color="gray"
        />
      </div>

      {/* Job Type Breakdown */}
      <Card>
        <h3 className="mb-4 text-sm font-medium text-gray-500 dark:text-gray-400">
          Job Type Breakdown
        </h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
          <JobTypeItem label="Increment" count={current.increment_jobs} color="bg-emerald-500" />
          <JobTypeItem
            label="Reverse Increment"
            count={current.reverse_increment_jobs}
            color="bg-blue-500"
          />
          <JobTypeItem label="Gold" count={current.gold_jobs} color="bg-yellow-500" />
          <JobTypeItem label="Silver" count={current.silver_jobs} color="bg-gray-400" />
          <JobTypeItem label="Bronze" count={current.bronze_jobs} color="bg-orange-600" />
        </div>
      </Card>

      {/* Storage Trend */}
      <StorageTrendChart
        data={storageTrendData}
        title={`${detail.site_code} - Storage History`}
      />

      {/* BDR Servers */}
      <Card padding={false}>
        <div className="px-6 pt-6 pb-2">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
            BDR Servers ({bdrs?.length ?? 0})
          </h3>
        </div>
        <DataTable
          columns={bdrColumns}
          data={bdrs ?? []}
          emptyMessage="No BDR servers found for this site"
        />
      </Card>

      {/* Buckets */}
      <Card padding={false}>
        <div className="px-6 pt-6 pb-2">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Wasabi Buckets ({buckets?.length ?? 0})
          </h3>
        </div>
        <DataTable
          columns={bucketColumns}
          data={buckets ?? []}
          emptyMessage="No buckets found for this site"
        />
      </Card>
    </div>
  );
}

function JobTypeItem({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg bg-gray-50 px-4 py-3 dark:bg-gray-700/30">
      <div className={`h-3 w-3 rounded-full ${color}`} />
      <div>
        <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
        <p className="text-lg font-semibold text-gray-900 dark:text-white">{count}</p>
      </div>
    </div>
  );
}
