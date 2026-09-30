import React from "react";
import { cn } from "@/lib/utils";

export interface MapLegendProps {
  title?: string;
  type?: "ndvi" | "outbreak";
  className?: string;
}

export function MapLegend({
  title = "Vegetation Vigour (NDVI)",
  type = "ndvi",
  className,
}: MapLegendProps) {
  return (
    <div
      className={cn(
        "p-3 bg-white/95 backdrop-blur-sm border border-border rounded-xl shadow-card text-xs text-text max-w-xs",
        className
      )}
    >
      <div className="font-semibold text-primary-dark mb-1.5">{title}</div>

      {type === "ndvi" ? (
        <div>
          {/* Continuous NDVI Color Ramp */}
          <div
            className="h-3.5 w-full rounded-md border border-border/60"
            style={{
              background:
                "linear-gradient(to right, #DC2626 0%, #F59E0B 25%, #FDE047 45%, #86EFAC 70%, #16A34A 85%, #14532D 100%)",
            }}
          />
          <div className="flex justify-between items-center text-[10px] text-text-muted mt-1 font-medium">
            <span>&lt;0.1 (Bare/Dry)</span>
            <span>0.4 (Moderate)</span>
            <span>&gt;0.8 (Dense)</span>
          </div>
        </div>
      ) : (
        <div className="space-y-1 mt-1 text-[11px]">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-status-healthy border border-white" />
            <span>Low / Controlled</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-status-watch border border-white" />
            <span>Moderate Spreading</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-status-risk border border-white" />
            <span>Outbreak Spike Alert</span>
          </div>
        </div>
      )}
    </div>
  );
}
