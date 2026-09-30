"use client";

import React, { useState, useMemo } from "react";
import { ArrowUpDown, Download, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./Button";
import { cn } from "@/lib/utils";

export interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (item: T) => React.ReactNode;
  sortable?: boolean;
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  searchPlaceholder?: string;
  searchKey?: keyof T;
  pageSize?: number;
  filename?: string;
  className?: string;
}

export function DataTable<T extends Record<string, any>>({
  data,
  columns,
  searchPlaceholder = "Search records...",
  searchKey,
  pageSize = 10,
  filename = "krishinet-export.csv",
  className,
}: DataTableProps<T>) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortAsc, setSortAsc] = useState(true);
  const [page, setPage] = useState(1);

  // 1. Search filter
  const filtered = useMemo(() => {
    if (!search.trim()) return data;
    const term = search.toLowerCase();
    return data.filter((item) => {
      if (searchKey) {
        return String(item[searchKey]).toLowerCase().includes(term);
      }
      return Object.values(item).some((v) =>
        String(v).toLowerCase().includes(term)
      );
    });
  }, [data, search, searchKey]);

  // 2. Sort
  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    return [...filtered].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal === bVal) return 0;
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      const res = aVal > bVal ? 1 : -1;
      return sortAsc ? res : -res;
    });
  }, [filtered, sortKey, sortAsc]);

  // 3. Paginate
  const totalPages = Math.ceil(sorted.length / pageSize) || 1;
  const paginated = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sorted.slice(start, start + pageSize);
  }, [sorted, page, pageSize]);

  const toggleSort = (key: string) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  const handleExportCsv = () => {
    if (!data.length) return;
    const headers = columns.map((c) => `"${c.header}"`).join(",");
    const rows = sorted.map((row) =>
      columns
        .map((c) => {
          const val = row[c.key as string];
          return `"${String(val ?? "").replace(/"/g, '""')}"`;
        })
        .join(",")
    );
    const csvContent = [headers, ...rows].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className={cn("space-y-4", className)}>
      {/* Search and Export Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
          <input
            type="search"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder={searchPlaceholder}
            className="w-full pl-10 pr-4 py-2 text-sm bg-white border border-border rounded-btn focus:outline-none focus:ring-2 focus:ring-primary text-text"
          />
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={handleExportCsv}
          leftIcon={<Download className="h-4 w-4" />}
        >
          Export CSV ({sorted.length})
        </Button>
      </div>

      {/* Table Element */}
      <div className="overflow-x-auto border border-border rounded-card bg-white shadow-sm">
        <table className="w-full text-left text-sm text-text">
          <thead className="bg-surface-soft border-b border-border text-xs font-bold text-primary-dark">
            <tr>
              {columns.map((col) => (
                <th key={col.key as string} className="px-5 py-3 select-none">
                  {col.sortable ? (
                    <button
                      type="button"
                      onClick={() => toggleSort(col.key as string)}
                      className="inline-flex items-center gap-1.5 hover:text-primary focus:outline-none font-bold"
                    >
                      <span>{col.header}</span>
                      <ArrowUpDown className="h-3 w-3 text-text-muted" />
                    </button>
                  ) : (
                    <span>{col.header}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {paginated.length > 0 ? (
              paginated.map((item, idx) => (
                <tr key={idx} className="hover:bg-surface-soft/40 transition-colors">
                  {columns.map((col) => (
                    <td key={col.key as string} className="px-5 py-3 text-sm">
                      {col.render ? col.render(item) : String(item[col.key as string] ?? "-")}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-5 py-8 text-center text-text-muted text-sm"
                >
                  No records matching search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-text-muted pt-1">
          <span>
            Showing page <strong>{page}</strong> of <strong>{totalPages}</strong> ({sorted.length} total items)
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
