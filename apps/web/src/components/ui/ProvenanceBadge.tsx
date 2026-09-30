"use client";

import React, { useState } from "react";
import { Database, Wifi, ShieldAlert, Clock, HelpCircle } from "lucide-react";
import { cn, formatDateTime } from "@/lib/utils";
import type { Provenance, ProvenanceMode } from "@krishinet/shared";

export interface ProvenanceBadgeProps {
  provenance: Provenance;
  className?: string;
  size?: "sm" | "md";
}

const modeConfig: Record<
  ProvenanceMode,
  {
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    styles: string;
    dotColor: string;
  }
> = {
  live: {
    label: "LIVE DATA",
    icon: Wifi,
    styles: "bg-[#DCFCE7] text-[#166534] border-[#86EFAC]",
    dotColor: "bg-[#16A34A]",
  },
  cache: {
    label: "CACHED",
    icon: Database,
    styles: "bg-[#FEF3C7] text-[#92400E] border-[#FCD34D]",
    dotColor: "bg-[#F59E0B]",
  },
  demo: {
    label: "SYNTHETIC DEMO",
    icon: ShieldAlert,
    styles: "bg-[#E0F2FE] text-[#075985] border-[#BAE6FD]",
    dotColor: "bg-[#0EA5E9]",
  },
};

export function ProvenanceBadge({
  provenance,
  className,
  size = "md",
}: ProvenanceBadgeProps) {
  const [isOpen, setIsOpen] = useState(false);
  const config = modeConfig[provenance.mode] || modeConfig.demo;
  const Icon = config.icon;

  return (
    <div className={cn("relative inline-block", className)}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label={`Data provenance: ${config.label}. Click for details.`}
        className={cn(
          "inline-flex items-center gap-1.5 font-semibold tracking-wider rounded-md border transition-all duration-150 select-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary",
          config.styles,
          size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs"
        )}
      >
        <span
          className={cn("h-1.5 w-1.5 rounded-full animate-pulse", config.dotColor)}
        />
        <Icon className="h-3 w-3" />
        <span>{config.label}</span>
        <HelpCircle className="h-2.5 w-2.5 opacity-60 ml-0.5" />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-30"
            onClick={() => setIsOpen(false)}
          />
          <div
            role="dialog"
            aria-label="Provenance Metadata"
            className="absolute right-0 mt-1.5 w-72 p-3.5 bg-white border border-border rounded-xl shadow-card-hover z-40 text-xs text-text animate-in fade-in zoom-in-95 duration-150"
          >
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <span className="font-semibold text-primary-dark">
                Data Provenance Trace
              </span>
              <span
                className={cn(
                  "px-1.5 py-0.5 rounded text-[10px] font-bold uppercase",
                  config.styles
                )}
              >
                {provenance.mode}
              </span>
            </div>

            <div className="mt-2.5 space-y-2 text-text-muted">
              <div>
                <span className="font-medium text-text">Source:</span>{" "}
                <span className="text-text">{provenance.source}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-primary" />
                <span>
                  <strong className="text-text">Fetched:</strong>{" "}
                  {formatDateTime(provenance.fetched_at)}
                </span>
              </div>
              <div>
                <span className="font-medium text-text">TTL:</span>{" "}
                {provenance.ttl}s
              </div>
              {provenance.confidence !== undefined && (
                <div>
                  <span className="font-medium text-text">
                    Engine Confidence:
                  </span>{" "}
                  {Math.round(provenance.confidence * 100)}%
                </div>
              )}
              {provenance.notes && (
                <div className="p-2 bg-surface-soft rounded text-[11px] text-text border border-border/60">
                  {provenance.notes}
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="mt-3 w-full py-1 text-center font-medium text-primary hover:text-primary-dark text-[11px] border-t border-border pt-1.5"
            >
              Close
            </button>
          </div>
        </>
      )}
    </div>
  );
}
