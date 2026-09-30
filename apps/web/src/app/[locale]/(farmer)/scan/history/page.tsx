"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Clock,
  Camera,
  Filter,
  CheckCircle2,
  AlertTriangle,
  WifiOff,
  ChevronRight,
  Trash2,
  ArrowLeft,
  Search,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusPill } from "@/components/ui/StatusPill";
import { EmptyState } from "@/components/ui/EmptyState";
import { apiClient } from "@/lib/api/client";
import {
  getLocalDiagnoses,
  clearLocalDiagnoses,
  type StoredDiagnosis,
} from "@/lib/storage/offline-queue";

interface HistoryItem {
  id: string;
  field_id?: string;
  crop: string;
  disease_name: string;
  severity_level: "mild" | "moderate" | "severe";
  ensemble_confidence: number;
  created_at: string;
  status: "synced" | "pending_sync";
  image_url?: string;
}

export default function DiagnosticHistoryPage() {
  const params = useParams();
  const locale = (params?.locale as string) || "en";

  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCrop, setSelectedCrop] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDetail, setSelectedDetail] = useState<HistoryItem | null>(null);

  useEffect(() => {
    async function loadAllHistory() {
      setLoading(true);
      try {
        // 1. Get locally saved scans from IndexedDB
        const localItems = await getLocalDiagnoses();

        // 2. Fetch server records
        let serverItems: any[] = [];
        try {
          const res = await apiClient.get<any[]>("/disease/history");
          const itemsList = Array.isArray(res) ? res : (res as any)?.data || [];
          if (Array.isArray(itemsList)) {
            serverItems = itemsList.map((item: any) => ({
              id: item.detection_id || `det-${Math.random()}`,
              field_id: item.field_id,
              crop: item.crop || "Cotton",
              disease_name: item.disease_name || "Leaf condition",
              severity_level: item.severity_level || "moderate",
              ensemble_confidence: item.ensemble_confidence || 0.8,
              created_at: item.created_at || new Date().toISOString(),
              status: "synced" as const,
              image_url: item.image_s3_uri,
            }));
          }
        } catch (e) {
          console.warn("Could not fetch remote disease history, relying on local records:", e);
        }

        // Merge, de-duplicate by ID, and sort newest first
        const combinedMap = new Map<string, HistoryItem>();
        for (const local of localItems) {
          combinedMap.set(local.id, {
            id: local.id,
            field_id: local.field_id,
            crop: local.crop,
            disease_name: local.disease_name,
            severity_level: local.severity_level,
            ensemble_confidence: local.ensemble_confidence,
            created_at: local.created_at,
            status: local.status,
            image_url: local.image_data_url,
          });
        }
        for (const srv of serverItems) {
          if (!combinedMap.has(srv.id)) {
            combinedMap.set(srv.id, srv);
          }
        }

        const sorted = Array.from(combinedMap.values()).sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );

        setHistoryItems(sorted);
      } finally {
        setLoading(false);
      }
    }

    loadAllHistory();
  }, []);

  const handleClearLocal = async () => {
    if (confirm("Clear offline scans from this device? (Synced scans remain safe in the cloud).")) {
      await clearLocalDiagnoses();
      setHistoryItems((prev) => prev.filter((it) => it.status === "synced"));
    }
  };

  // Filter items
  const filteredItems = historyItems.filter((item) => {
    if (selectedCrop !== "all" && item.crop.toLowerCase() !== selectedCrop.toLowerCase()) {
      return false;
    }
    if (selectedStatus !== "all" && item.status !== selectedStatus) {
      return false;
    }
    if (searchQuery.trim() !== "") {
      const q = searchQuery.toLowerCase();
      return (
        item.disease_name.toLowerCase().includes(q) ||
        item.crop.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            <Link href={`/${locale}/scan`} className="hover:text-[var(--primary)] flex items-center gap-1">
              <ArrowLeft className="w-3.5 h-3.5" />
              Scanner
            </Link>
            <span>/</span>
            <span className="text-[var(--text)]">Diagnostic History</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text)] mt-1">
            Plant Health Log & Scans
          </h1>
          <p className="text-sm text-[var(--text-muted)]">
            Review past disease detections, recovery progress, and offline synchronization status.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link href={`/${locale}/scan`}>
            <Button className="gap-2">
              <Camera className="w-4 h-4" />
              New Scan
            </Button>
          </Link>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2">
          {/* Crop Filter */}
          <div className="flex items-center gap-1 text-xs">
            <Filter className="w-3.5 h-3.5 text-[var(--text-muted)] mr-1" />
            {["all", "cotton", "soybean", "rice", "wheat"].map((crop) => (
              <button
                key={crop}
                onClick={() => setSelectedCrop(crop)}
                className={`px-2.5 py-1 rounded-full capitalize text-xs transition-colors ${
                  selectedCrop === crop
                    ? "bg-[var(--primary)] text-white font-medium"
                    : "bg-[var(--surface-soft)] text-[var(--text-muted)] hover:bg-[var(--border)]"
                }`}
              >
                {crop}
              </button>
            ))}
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1 text-xs pl-2 border-l border-[var(--border)]">
            {["all", "synced", "pending_sync"].map((st) => (
              <button
                key={st}
                onClick={() => setSelectedStatus(st)}
                className={`px-2.5 py-1 rounded-full text-xs transition-colors ${
                  selectedStatus === st
                    ? "bg-slate-800 text-white font-medium"
                    : "bg-[var(--surface-soft)] text-[var(--text-muted)] hover:bg-[var(--border)]"
                }`}
              >
                {st === "pending_sync" ? "Offline Only" : st === "synced" ? "Synced" : "All Sync"}
              </button>
            ))}
          </div>
        </div>

        {/* Search & Clear actions */}
        <div className="flex items-center gap-3">
          <div className="relative w-full sm:w-60">
            <Search className="w-4 h-4 absolute left-2.5 top-2.5 text-[var(--text-muted)]" />
            <input
              type="text"
              placeholder="Search diseases..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-lg text-xs bg-[var(--surface-soft)] border border-[var(--border)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
            />
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearLocal}
            title="Clear offline storage"
            className="text-[var(--text-muted)] hover:text-rose-600 gap-1"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear Local
          </Button>
        </div>
      </div>

      {/* List of Records */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-4 animate-pulse h-20 bg-[var(--surface-soft)]" />
          ))}
        </div>
      ) : filteredItems.length === 0 ? (
        <EmptyState
          title="No Diagnostic Scans Found"
          description="You haven't scanned any crops matching this criteria yet. Capture your first leaf to track disease progression."
          actionLabel="Scan First Leaf"
          onAction={() => {
            window.location.href = `/${locale}/scan`;
          }}
        />
      ) : (
        <div className="space-y-3">
          {filteredItems.map((item) => (
            <Card
              key={item.id}
              className="p-4 hover:border-[var(--primary)] transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              onClick={() => setSelectedDetail(item)}
            >
              <div className="flex items-start sm:items-center gap-3">
                {/* Visual Leaf Thumbnail / Icon */}
                <div className="w-12 h-12 rounded-lg bg-[var(--surface-soft)] border border-[var(--border)] flex items-center justify-center shrink-0 overflow-hidden text-[var(--primary)] font-bold text-xs">
                  {item.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={item.image_url}
                      alt={item.disease_name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <span>{item.crop.slice(0, 2).toUpperCase()}</span>
                  )}
                </div>

                {/* Disease & Crop Info */}
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-bold text-[var(--text)]">
                      {item.disease_name}
                    </h2>
                    <StatusPill
                      status={
                        item.severity_level === "severe"
                          ? "risk"
                          : item.severity_level === "moderate"
                          ? "watch"
                          : "healthy"
                      }
                      label={item.severity_level}
                    />
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--text-muted)]">
                    <span className="capitalize">Crop: <strong className="text-[var(--text)]">{item.crop}</strong></span>
                    <span>•</span>
                    <span>
                      Confidence:{" "}
                      <strong className="text-[var(--text)]">
                        {Math.round(item.ensemble_confidence * 100)}%
                      </strong>
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(item.created_at).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                </div>
              </div>

              {/* Status and Action Arrow */}
              <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0 pt-2 sm:pt-0 border-t sm:border-0 border-[var(--border)]">
                {item.status === "synced" ? (
                  <span className="text-[11px] text-[var(--primary)] bg-[var(--primary-light)]/40 px-2 py-0.5 rounded-full flex items-center gap-1 font-medium">
                    <CheckCircle2 className="w-3 h-3 text-[var(--primary)]" />
                    Cloud Synced
                  </span>
                ) : (
                  <span className="text-[11px] text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full flex items-center gap-1 font-medium">
                    <WifiOff className="w-3 h-3" />
                    Pending Sync
                  </span>
                )}
                <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Detail Modal Dialog */}
      {selectedDetail && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 animate-in fade-in"
          onClick={() => setSelectedDetail(null)}
        >
          <Card
            className="w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Detection Summary
                </span>
                <h3 className="text-lg font-bold text-[var(--text)] mt-1">
                  {selectedDetail.disease_name}
                </h3>
              </div>
              <button
                onClick={() => setSelectedDetail(null)}
                className="text-[var(--text-muted)] hover:text-[var(--text)] text-sm font-semibold p-1"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-[var(--surface-soft)] border border-[var(--border)]">
                <span className="text-[var(--text-muted)]">Target Crop</span>
                <div className="font-bold text-[var(--text)] capitalize mt-0.5">
                  {selectedDetail.crop}
                </div>
              </div>

              <div className="p-3 rounded-lg bg-[var(--surface-soft)] border border-[var(--border)]">
                <span className="text-[var(--text-muted)]">Model Confidence</span>
                <div className="font-bold text-[var(--primary)] mt-0.5">
                  {Math.round(selectedDetail.ensemble_confidence * 100)}%
                </div>
              </div>

              <div className="p-3 rounded-lg bg-[var(--surface-soft)] border border-[var(--border)]">
                <span className="text-[var(--text-muted)]">Severity Rating</span>
                <div className="font-bold text-[var(--text)] capitalize mt-0.5">
                  {selectedDetail.severity_level}
                </div>
              </div>

              <div className="p-3 rounded-lg bg-[var(--surface-soft)] border border-[var(--border)]">
                <span className="text-[var(--text-muted)]">Sync Status</span>
                <div className="font-bold text-[var(--text)] mt-0.5">
                  {selectedDetail.status === "synced" ? "Synced to Cloud" : "Stored on Device"}
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-[var(--border)]">
              <Button variant="outline" size="sm" onClick={() => setSelectedDetail(null)}>
                Close
              </Button>
              <Link href={`/${locale}/scan`}>
                <Button size="sm" className="gap-1.5">
                  <Camera className="w-3.5 h-3.5" />
                  New Scan
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
