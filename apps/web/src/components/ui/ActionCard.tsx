"use client";

import React, { useState } from "react";
import { Check, Sparkles, AlertCircle, Clock, CheckCircle } from "lucide-react";
import { Card } from "./Card";
import { VoiceButton } from "./VoiceButton";
import { cn } from "@/lib/utils";
import type { WhatToDoToday } from "@krishinet/shared";

export interface ActionCardProps {
  actionData: WhatToDoToday;
  onActionToggle?: (index: number, completed: boolean) => void;
  className?: string;
}

const urgencyConfig = {
  urgent: {
    label: "URGENT ACTION TODAY",
    badgeStyles: "bg-status-risk text-white",
    borderStyles: "border-status-risk/40",
    icon: AlertCircle,
  },
  attention: {
    label: "ATTENTION NEEDED",
    badgeStyles: "bg-status-watch text-white",
    borderStyles: "border-status-watch/40",
    icon: Clock,
  },
  optimal: {
    label: "OPTIMAL WINDOW",
    badgeStyles: "bg-primary text-white",
    borderStyles: "border-primary/40",
    icon: Sparkles,
  },
  routine: {
    label: "ROUTINE CARE",
    badgeStyles: "bg-surface-soft text-text-muted border border-border",
    borderStyles: "border-border",
    icon: CheckCircle,
  },
};

export function ActionCard({
  actionData,
  onActionToggle,
  className,
}: ActionCardProps) {
  const [completedItems, setCompletedItems] = useState<Record<number, boolean>>({});
  const config = urgencyConfig[actionData.urgency] || urgencyConfig.routine;
  const UrgencyIcon = config.icon;

  const toggleItem = (idx: number) => {
    const updated = !completedItems[idx];
    setCompletedItems((prev) => ({ ...prev, [idx]: updated }));
    if (onActionToggle) {
      onActionToggle(idx, updated);
    }
  };

  return (
    <Card
      variant="hero"
      className={cn(
        "p-6 sm:p-7 relative overflow-hidden border-2 transition-shadow hover:shadow-card-hover",
        config.borderStyles,
        className
      )}
    >
      {/* Top Bar with Urgency Tag and Voice Speaker */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <span
          className={cn(
            "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold tracking-wide uppercase select-none",
            config.badgeStyles
          )}
        >
          <UrgencyIcon className="h-3.5 w-3.5" />
          {config.label}
        </span>

        <VoiceButton
          mode="speak"
          textToSpeak={actionData.read_aloud_text || actionData.headline}
          size="sm"
          label="Listen"
        />
      </div>

      {/* Main Headline */}
      <div className="mt-4">
        <h2 className="text-2xl sm:text-3xl font-extrabold text-primary-dark leading-tight">
          {actionData.headline}
        </h2>
        <p className="mt-2 text-base sm:text-lg text-text leading-relaxed font-normal">
          {actionData.summary}
        </p>
      </div>

      {/* Recommended Action Checklist */}
      {actionData.recommended_actions && actionData.recommended_actions.length > 0 && (
        <div className="mt-6 space-y-3 pt-5 border-t border-primary-dark/10">
          <h4 className="text-xs font-bold uppercase tracking-wider text-text-muted">
            Step-by-Step Field Checklist
          </h4>
          <ul className="space-y-2.5">
            {actionData.recommended_actions.map((act, idx) => {
              const isDone = !!completedItems[idx];
              return (
                <li
                  key={idx}
                  onClick={() => toggleItem(idx)}
                  className={cn(
                    "flex items-start gap-3.5 p-3.5 rounded-xl border transition-all cursor-pointer select-none",
                    isDone
                      ? "bg-white/90 border-primary text-text-muted line-through opacity-80"
                      : "bg-white border-border hover:border-primary text-text shadow-sm"
                  )}
                >
                  <button
                    type="button"
                    aria-label={`Mark action ${idx + 1} as ${isDone ? "incomplete" : "completed"}`}
                    className={cn(
                      "mt-0.5 h-6 w-6 rounded-md border flex items-center justify-center flex-shrink-0 transition-colors",
                      isDone
                        ? "bg-primary border-primary text-white"
                        : "border-border hover:border-primary bg-surface-soft"
                    )}
                  >
                    {isDone && <Check className="h-4 w-4 stroke-[3]" />}
                  </button>
                  <span className="text-base font-medium leading-snug">
                    {act}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </Card>
  );
}
