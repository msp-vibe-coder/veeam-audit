import { useState, useCallback, useMemo } from "react";
import { Search } from "lucide-react";
import clsx from "clsx";
import { useApi } from "@/hooks/useApi";
import { fetchIssues } from "@/lib/api";
import DataTable, { type TableColumn } from "@/components/ui/DataTable";
import Badge from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { Issue, SortDirection } from "@/types";

const severityFilters = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;

export default function Issues() {
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("report_date");
  const [sortDir, setSortDir] = useState<SortDirection>("desc");

  const apiSeverity = severityFilter === "ALL" ? undefined : severityFilter;

  const { data: issues, loading, error } = useApi<Issue[]>(
    () => fetchIssues({ severity: apiSeverity, type: typeFilter || undefined }),
    [apiSeverity, typeFilter],
  );

  // Get unique types from the data for the type filter
  const issueTypes = useMemo(() => {
    if (!issues) return [];
    const types = new Set(issues.map((i) => i.type));
    return [...types].sort();
  }, [issues]);

  // Client-side search and sort
  const filteredIssues = useMemo(() => {
    let result = issues ?? [];

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (i) =>
          i.description?.toLowerCase().includes(q) ||
          i.site_code?.toLowerCase().includes(q) ||
          i.type.toLowerCase().includes(q),
      );
    }

    // Sort
    result = [...result].sort((a, b) => {
      const aVal = a[sortBy as keyof Issue];
      const bVal = b[sortBy as keyof Issue];

      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;

      const cmp = String(aVal).localeCompare(String(bVal));
      return sortDir === "asc" ? cmp : -cmp;
    });

    return result;
  }, [issues, searchQuery, sortBy, sortDir]);

  const handleSort = useCallback(
    (key: string) => {
      if (sortBy === key) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortBy(key);
        setSortDir("desc");
      }
    },
    [sortBy],
  );

  const columns: TableColumn<Issue>[] = [
    { key: "report_date", label: "Date", sortable: true },
    {
      key: "site_code",
      label: "Site",
      sortable: true,
      render: (v) => (v as string | null) ?? "-",
    },
    {
      key: "severity",
      label: "Severity",
      sortable: true,
      render: (v) => <Badge severity={v as string} />,
    },
    { key: "type", label: "Type", sortable: true },
    {
      key: "description",
      label: "Description",
      render: (v) => (
        <span className="block max-w-md truncate" title={v as string}>
          {(v as string | null) ?? "-"}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Issues</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {filteredIssues.length} issues found
        </p>
      </div>

      {/* Severity Filter Buttons */}
      <div className="flex flex-wrap items-center gap-2">
        {severityFilters.map((sev) => (
          <button
            key={sev}
            onClick={() => setSeverityFilter(sev)}
            className={clsx(
              "rounded-lg px-4 py-2 text-sm font-medium transition-colors duration-150",
              severityFilter === sev
                ? sev === "ALL"
                  ? "bg-emerald-600 text-white"
                  : sev === "CRITICAL"
                    ? "bg-red-600 text-white"
                    : sev === "HIGH"
                      ? "bg-orange-600 text-white"
                      : sev === "MEDIUM"
                        ? "bg-yellow-600 text-white"
                        : "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700",
            )}
          >
            {sev}
          </button>
        ))}
      </div>

      {/* Filters row */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search issues..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field pl-10"
          />
        </div>

        {/* Type filter */}
        {issueTypes.length > 0 && (
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="input-field w-48"
          >
            <option value="">All Types</option>
            {issueTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Table */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm
                      dark:border-gray-700/50 dark:bg-gray-800/50">
        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <LoadingSpinner message="Loading issues..." />
          </div>
        ) : error ? (
          <div className="flex h-64 items-center justify-center">
            <p className="text-red-500">{error}</p>
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={filteredIssues}
            onSort={handleSort}
            sortBy={sortBy}
            sortDir={sortDir}
            emptyMessage="No issues found matching your filters"
          />
        )}
      </div>
    </div>
  );
}
