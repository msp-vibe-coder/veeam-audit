import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Download } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { fetchSites } from "@/lib/api";
import DataTable, { type TableColumn } from "@/components/ui/DataTable";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { SiteListResponse, SiteMetric, SortDirection } from "@/types";

const PAGE_SIZE = 25;

export default function Sites() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("site_code");
  const [sortDir, setSortDir] = useState<SortDirection>("asc");
  const [page, setPage] = useState(0);

  const { data, loading, error } = useApi<SiteListResponse>(
    () =>
      fetchSites({
        search: search || undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
    [search, sortBy, sortDir, page],
  );

  const handleSort = useCallback(
    (key: string) => {
      if (sortBy === key) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortBy(key);
        setSortDir("asc");
      }
      setPage(0);
    },
    [sortBy],
  );

  function handleRowClick(row: SiteMetric) {
    navigate(`/sites/${row.site_code}`);
  }

  function handleExportCsv() {
    if (!data?.sites) return;
    const headers = [
      "Site Code",
      "Veeam TB",
      "Wasabi Active TB",
      "Wasabi Deleted TB",
      "Discrepancy %",
      "Success Rate %",
      "Total Jobs",
    ];
    const rows = data.sites.map((s) =>
      [
        s.site_code,
        s.veeam_tb.toFixed(4),
        s.wasabi_active_tb.toFixed(4),
        s.wasabi_deleted_tb.toFixed(4),
        s.discrepancy_pct.toFixed(2),
        s.success_rate_pct?.toFixed(2) ?? "",
        s.total_jobs,
      ].join(","),
    );
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sites-export.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  const columns: TableColumn<SiteMetric>[] = [
    { key: "site_code", label: "Site Code", sortable: true },
    {
      key: "veeam_tb",
      label: "Veeam TB",
      sortable: true,
      render: (v) => (v as number).toFixed(2),
    },
    {
      key: "wasabi_active_tb",
      label: "Wasabi Active TB",
      sortable: true,
      render: (v) => (v as number).toFixed(2),
    },
    {
      key: "wasabi_deleted_tb",
      label: "Wasabi Deleted TB",
      sortable: true,
      render: (v) => (v as number).toFixed(2),
    },
    {
      key: "discrepancy_pct",
      label: "Discrepancy %",
      sortable: true,
      render: (v) => {
        const val = v as number;
        return (
          <span
            className={
              val > 10
                ? "text-red-500 font-medium"
                : val > 5
                  ? "text-amber-500"
                  : "text-emerald-500"
            }
          >
            {val.toFixed(1)}%
          </span>
        );
      },
    },
    {
      key: "success_rate_pct",
      label: "Success Rate",
      sortable: true,
      render: (v) => {
        const val = v as number | null;
        if (val == null) return "-";
        return (
          <span
            className={
              val >= 95
                ? "text-emerald-500"
                : val >= 80
                  ? "text-amber-500"
                  : "text-red-500"
            }
          >
            {val.toFixed(1)}%
          </span>
        );
      },
    },
    { key: "total_jobs", label: "Total Jobs", sortable: true },
  ];

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Sites</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {data ? `${data.total} sites found` : "Loading..."}
          </p>
        </div>
        <button onClick={handleExportCsv} className="btn-secondary" disabled={!data?.sites?.length}>
          <Download className="h-4 w-4" />
          Export CSV
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Search sites..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(0);
          }}
          className="input-field pl-10"
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm
                      dark:border-gray-700/50 dark:bg-gray-800/50">
        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <LoadingSpinner message="Loading sites..." />
          </div>
        ) : error ? (
          <div className="flex h-64 items-center justify-center">
            <p className="text-red-500">{error}</p>
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={data?.sites ?? []}
            onSort={handleSort}
            sortBy={sortBy}
            sortDir={sortDir}
            onRowClick={handleRowClick}
          />
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Page {page + 1} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="btn-secondary"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="btn-secondary"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
