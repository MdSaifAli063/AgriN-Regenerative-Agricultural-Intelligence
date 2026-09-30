"use client";

import React, { useState } from "react";
import { Check, Calendar, Droplets, Sprout, Bug, Scissors } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ActionCalendarItem } from "@krishinet/shared";

export interface TimelineProps {
  items: ActionCalendarItem[];
  onItemToggle?: (id: string, isCompleted: boolean) => void;
  className?: string;
}

const categoryIcons = {
  irrigation: Droplets,
  fertilisation: Sprout,
  pest_scouting: Bug,
  harvesting: Scissors,
  sowing: Calendar,
};

export function Timeline({ items, onItemToggle, className }: TimelineProps) {
  const [completedMap, setCompletedMap] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    items.forEach((i) => {
      init[i.id] = i.is_completed;
    });
    return init;
  });

  const toggle = (id: string) => {
    const newVal = !completedMap[id];
    setCompletedMap((prev) => ({ ...prev, [id]: newVal }));
    if (onItemToggle) {
      onItemToggle(id, newVal);
    }
  };

  return (
    <div className={cn("relative pl-6 space-y-6 before:content-[''] before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-border", className)}>
      {items.map((item) => {
        const isDone = !!completedMap[item.id];
        const Icon = categoryIcons[item.category] || Calendar;

        return (
          <div key={item.id} className="relative flex items-start gap-4 group">
            {/* Timeline Marker Dot */}
            <button
              type="button"
              onClick={() => toggle(item.id)}
              aria-label={`Toggle action: ${item.action_text}`}
              className={cn(
                "absolute -left-6 mt-1 h-5 w-5 rounded-full border flex items-center justify-center transition-all focus:outline-none focus:ring-2 focus:ring-primary",
                isDone
                  ? "bg-primary border-primary text-white"
                  : "bg-white border-border hover:border-primary text-transparent"
              )}
            >
              <Check className="h-3 w-3 stroke-[3]" />
            </button>

            {/* Action Box */}
            <div
              onClick={() => toggle(item.id)}
              className={cn(
                "flex-1 p-4 rounded-xl border bg-white shadow-sm transition-all cursor-pointer select-none",
                isDone
                  ? "border-border bg-surface-soft/60 text-text-muted line-through"
                  : "border-border hover:border-primary text-text hover:shadow-card"
              )}
            >
              <div className="flex items-center justify-between gap-2 mb-1.5 flex-wrap">
                <span className="text-xs font-bold text-primary uppercase tracking-wider flex items-center gap-1">
                  <Icon className="h-3.5 w-3.5" />
                  Day +{item.day_offset} ({item.category})
                </span>
                {item.urgency === "urgent" && !isDone && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#FEE2E2] text-status-risk">
                    Urgent
                  </span>
                )}
              </div>
              <p className="text-sm font-medium leading-relaxed">
                {item.action_text}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
