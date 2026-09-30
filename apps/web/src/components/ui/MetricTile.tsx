import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Card } from "./Card";
import { StatusPill, type StatusType } from "./StatusPill";
import { cn } from "@/lib/utils";

export interface MetricTileProps {
  title: string;
  value: string | number;
  unit?: string;
  subtitle?: string;
  status?: StatusType;
  statusLabel?: string;
  trend?: "up" | "down" | "neutral";
  trendLabel?: string;
  icon?: React.ReactNode;
  className?: string;
}

export function MetricTile({
  title,
  value,
  unit,
  subtitle,
  status,
  statusLabel,
  trend,
  trendLabel,
  icon,
  className,
}: MetricTileProps) {
  return (
    <Card
      className={cn(
        "p-5 flex flex-col justify-between hover:border-primary/50 transition-colors",
        className
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-text-muted">{title}</span>
        {icon && (
          <div className="h-9 w-9 rounded-btn bg-surface-soft border border-border flex items-center justify-center text-primary-dark">
            {icon}
          </div>
        )}
      </div>

      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="text-3xl font-bold tracking-tight text-text">
          {value}
        </span>
        {unit && (
          <span className="text-sm font-semibold text-text-muted">{unit}</span>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between pt-2 border-t border-border/50 text-xs">
        {status ? (
          <StatusPill status={status} label={statusLabel} size="sm" />
        ) : subtitle ? (
          <span className="text-text-muted">{subtitle}</span>
        ) : (
          <span />
        )}

        {trend && (
          <div
            className={cn(
              "flex items-center gap-1 font-medium",
              trend === "up" && "text-primary",
              trend === "down" && "text-status-risk",
              trend === "neutral" && "text-text-muted"
            )}
          >
            {trend === "up" && <TrendingUp className="h-3.5 w-3.5" />}
            {trend === "down" && <TrendingDown className="h-3.5 w-3.5" />}
            {trend === "neutral" && <Minus className="h-3.5 w-3.5" />}
            {trendLabel && <span>{trendLabel}</span>}
          </div>
        )}
      </div>
    </Card>
  );
}
