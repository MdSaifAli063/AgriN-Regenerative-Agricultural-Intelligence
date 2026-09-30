import React from "react";
import { cn } from "@/lib/utils";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "skeleton-shimmer rounded-md bg-[#DCFCE7]/40 select-none",
        className
      )}
      {...props}
    />
  );
}

export function CardSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "p-6 rounded-card border border-border bg-white shadow-card space-y-4",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-32 rounded" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <Skeleton className="h-8 w-48 rounded" />
      <div className="space-y-2 pt-2">
        <Skeleton className="h-4 w-full rounded" />
        <Skeleton className="h-4 w-3/4 rounded" />
      </div>
    </div>
  );
}

export function MetricSkeleton() {
  return (
    <div className="p-5 rounded-card border border-border bg-white shadow-card space-y-3">
      <Skeleton className="h-4 w-24 rounded" />
      <Skeleton className="h-9 w-36 rounded" />
      <Skeleton className="h-4 w-20 rounded" />
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="p-6 rounded-card border border-border bg-white shadow-card space-y-4">
      <div className="flex justify-between items-center">
        <Skeleton className="h-6 w-44 rounded" />
        <Skeleton className="h-6 w-24 rounded" />
      </div>
      <Skeleton className="h-56 w-full rounded-lg" />
    </div>
  );
}
