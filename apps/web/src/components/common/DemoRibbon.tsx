"use client";

import React, { useState } from "react";
import { Sparkles, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface DemoRibbonProps {
  nodeCountry?: string;
  className?: string;
}

export function DemoRibbon({ nodeCountry = "IND", className }: DemoRibbonProps) {
  const [isDismissed, setIsDismissed] = useState(false);

  if (isDismissed) return null;

  return (
    <div
      role="status"
      className={cn(
        "bg-primary-deep text-white px-4 py-1.5 text-xs flex items-center justify-between shadow-inner select-none font-medium",
        className
      )}
    >
      <div className="flex items-center gap-2 mx-auto">
        <Sparkles className="h-3.5 w-3.5 text-status-watch animate-pulse" />
        <span>
          <strong>DEMO MODE ACTIVE</strong> • Connected to Sovereign Node [{nodeCountry}] • Live Copernicus/ISRIC Fallbacks Simulated
        </span>
      </div>

      <button
        type="button"
        onClick={() => setIsDismissed(true)}
        aria-label="Dismiss demo ribbon"
        className="p-0.5 rounded text-white/80 hover:text-white"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
