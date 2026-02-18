import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import clsx from "clsx";
import type { SortDirection } from "@/types";

export interface TableColumn<T> {
  key: string;
  label: string;
  sortable?: boolean;
  render?: (value: unknown, row: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: TableColumn<T>[];
  data: T[];
  onSort?: (key: string) => void;
  sortBy?: string;
  sortDir?: SortDirection;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default function DataTable<T extends Record<string, any>>({
  columns,
  data,
  onSort,
  sortBy,
  sortDir,
  onRowClick,
  emptyMessage = "No data available",
}: DataTableProps<T>) {
  function getSortIcon(key: string) {
    if (sortBy !== key) return <ArrowUpDown className="h-3.5 w-3.5 text-gray-400" />;
    return sortDir === "asc" ? (
      <ArrowUp className="h-3.5 w-3.5 text-emerald-500" />
    ) : (
      <ArrowDown className="h-3.5 w-3.5 text-emerald-500" />
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            {columns.map((col) => (
              <th
                key={col.key}
                className={clsx(
                  "px-4 py-3 text-left text-xs font-medium uppercase tracking-wider",
                  "text-gray-500 dark:text-gray-400",
                  col.sortable && "cursor-pointer select-none hover:text-gray-700 dark:hover:text-gray-200",
                  col.className,
                )}
                onClick={() => col.sortable && onSort?.(col.key)}
              >
                <div className="flex items-center gap-1">
                  {col.label}
                  {col.sortable && getSortIcon(col.key)}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-700/50">
          {data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-12 text-center text-gray-400"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, idx) => (
              <tr
                key={idx}
                onClick={() => onRowClick?.(row)}
                className={clsx(
                  "transition-colors duration-100",
                  onRowClick
                    ? "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/30"
                    : "",
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={clsx(
                      "whitespace-nowrap px-4 py-3 text-gray-700 dark:text-gray-300",
                      col.className,
                    )}
                  >
                    {col.render
                      ? col.render(row[col.key], row)
                      : String(row[col.key] ?? "-")}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
