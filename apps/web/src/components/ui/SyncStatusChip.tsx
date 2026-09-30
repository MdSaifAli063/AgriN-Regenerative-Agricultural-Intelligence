"use client";

import React, { useState, useEffect } from "react";
import { CheckCircle2, RefreshCw, AlertCircle, CloudOff } from "lucide-react";
import { cn } from "@/lib/utils";

export type SyncState = "online" | "offline" | "syncing" | "failed";

export interface SyncStatusChipProps {
  state?: SyncState;
  pendingCount?: number;
  onRetry?: () => void;
  className?: string;
}

export function SyncStatusChip({
  state: overrideState,
  pendingCount = 0,
  onRetry,
  className,
}: SyncStatusChipProps) {
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setIsOnline(navigator.onLine);
    const setOn = () => setIsOnline(true);
    const setOff = () => setIsOnline(false);
    window.addEventListener("online", setOn);
    window.addEventListener("offline", setOff);
    return () => {
      window.removeEventListener("online", setOn);
      window.removeEventListener("offline", setOff);
    };
  }, []);

  const currentState: SyncState =
    overrideState || (!isOnline ? "offline" : pendingCount > 0 ? "syncing" : "online");

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border select-none transition-colors",
        currentState === "online" &&
          "bg-[#DCFCE7] text-[#166534] border-[#86EFAC]",
        currentState === "offline" &&
          "bg-[#F3F4F6] text-[#4B5563] border-[#D1D5DB]",
        currentState === "syncing" &&
          "bg-[#FEF3C7] text-[#92400E] border-[#FCD34D]",
        currentState === "failed" &&
          "bg-[#FEE2E2] text-[#991B1B] border-[#FCA5A5]",
        className
      )}
    >
      {currentState === "online" && (
        <>
          <span className="h-2 w-2 rounded-full bg-[#16A34A]" />
          <span>Synced</span>
        </>
      )}

      {currentState === "offline" && (
        <>
          <CloudOff className="h-3 w-3 text-[#6B7280]" />
          <span>Offline{pendingCount > 0 ? ` (${pendingCount} queued)` : ""}</span>
        </>
      )}

      {currentState === "syncing" && (
        <>
          <RefreshCw className="h-3 w-3 text-[#F59E0B] animate-spin" />
          <span>Syncing ({pendingCount})</span>
        </>
      )}

      {currentState === "failed" && (
        <>
          <AlertCircle className="h-3 w-3 text-[#DC2626]" />
          <span>Sync Failed</span>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="ml-1 underline font-bold hover:text-red-900"
            >
              Retry
            </button>
          )}
        </>
      )}
    </div>
  );
}
