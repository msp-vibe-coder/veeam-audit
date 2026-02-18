import { useState, useCallback } from "react";
import { FileSpreadsheet, Download, Plus, X, Loader2 } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { fetchReports, generateReport, downloadReportUrl } from "@/lib/api";
import Card from "@/components/ui/Card";
import DataTable, { type TableColumn } from "@/components/ui/DataTable";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { GeneratedReport } from "@/types";

export default function Reports() {
  const [showGenerate, setShowGenerate] = useState(false);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [genSuccess, setGenSuccess] = useState(false);

  const { data: reports, loading, error, refetch } = useApi<GeneratedReport[]>(
    () => fetchReports(),
    [],
  );

  const handleGenerate = useCallback(async () => {
    if (!dateFrom || !dateTo) return;
    setGenerating(true);
    setGenError(null);
    setGenSuccess(false);
    try {
      await generateReport({ date_from: dateFrom, date_to: dateTo });
      setGenSuccess(true);
      setShowGenerate(false);
      setDateFrom("");
      setDateTo("");
      refetch();
      // Clear success message after 3 seconds
      setTimeout(() => setGenSuccess(false), 3000);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setGenError(err.message);
      } else {
        setGenError("Failed to generate report");
      }
    } finally {
      setGenerating(false);
    }
  }, [dateFrom, dateTo, refetch]);

  const columns: TableColumn<GeneratedReport>[] = [
    {
      key: "filename",
      label: "Filename",
      render: (v) => (
        <span className="font-medium text-gray-900 dark:text-white">
          {v as string}
        </span>
      ),
    },
    {
      key: "report_type",
      label: "Type",
      render: (v) => (v as string | null) ?? "audit",
    },
    {
      key: "date_from",
      label: "Date Range",
      render: (_v, row) => {
        const r = row as unknown as GeneratedReport;
        if (!r.date_from || !r.date_to) return "-";
        return `${r.date_from} - ${r.date_to}`;
      },
    },
    { key: "download_count", label: "Downloads" },
    {
      key: "created_at",
      label: "Created",
      render: (v) => {
        try {
          return new Date(v as string).toLocaleString();
        } catch {
          return v as string;
        }
      },
    },
    {
      key: "id",
      label: "Actions",
      render: (v) => (
        <a
          href={downloadReportUrl(v as number)}
          className="inline-flex items-center gap-1 rounded-lg bg-emerald-600/10
                     px-3 py-1.5 text-xs font-medium text-emerald-500
                     hover:bg-emerald-600/20 transition-colors"
          download
        >
          <Download className="h-3.5 w-3.5" />
          Download
        </a>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Reports</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Generate and download audit reports
          </p>
        </div>
        <button
          onClick={() => setShowGenerate((v) => !v)}
          className="btn-primary"
        >
          {showGenerate ? (
            <>
              <X className="h-4 w-4" />
              Cancel
            </>
          ) : (
            <>
              <Plus className="h-4 w-4" />
              Generate Report
            </>
          )}
        </button>
      </div>

      {/* Success message */}
      {genSuccess && (
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3">
          <p className="text-sm font-medium text-emerald-500">
            Report generated successfully!
          </p>
        </div>
      )}

      {/* Generate Report Form */}
      {showGenerate && (
        <Card>
          <h3 className="mb-4 text-sm font-medium text-gray-500 dark:text-gray-400">
            Generate New Report
          </h3>
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Date From
              </label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="input-field w-44"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Date To
              </label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="input-field w-44"
              />
            </div>
            <button
              onClick={handleGenerate}
              className="btn-primary"
              disabled={!dateFrom || !dateTo || generating}
            >
              {generating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <FileSpreadsheet className="h-4 w-4" />
                  Generate
                </>
              )}
            </button>
          </div>
          {genError && (
            <p className="mt-3 text-sm text-red-500">{genError}</p>
          )}
        </Card>
      )}

      {/* Reports Table */}
      <Card padding={false}>
        <div className="px-6 pt-6 pb-2">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Generated Reports ({reports?.length ?? 0})
          </h3>
        </div>
        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <LoadingSpinner message="Loading reports..." />
          </div>
        ) : error ? (
          <div className="flex h-64 items-center justify-center">
            <p className="text-red-500">{error}</p>
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={reports ?? []}
            emptyMessage="No reports generated yet. Click 'Generate Report' to create one."
          />
        )}
      </Card>
    </div>
  );
}
