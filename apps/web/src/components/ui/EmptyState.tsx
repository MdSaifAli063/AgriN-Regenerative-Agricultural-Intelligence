import React from "react";
import { Sprout } from "lucide-react";
import { Button } from "./Button";
import { cn } from "@/lib/utils";

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({
  title,
  description,
  icon,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-card bg-surface-soft border border-dashed border-border",
        className
      )}
    >
      <div className="h-16 w-16 rounded-full bg-primary-light flex items-center justify-center text-primary-dark mb-4 shadow-sm">
        {icon || <Sprout className="h-8 w-8 text-primary" />}
      </div>
      <h3 className="text-xl font-bold text-primary-dark">{title}</h3>
      <p className="mt-2 text-sm text-text-muted max-w-sm leading-relaxed">
        {description}
      </p>
      {actionLabel && onAction && (
        <div className="mt-6">
          <Button onClick={onAction}>{actionLabel}</Button>
        </div>
      )}
    </div>
  );
}
