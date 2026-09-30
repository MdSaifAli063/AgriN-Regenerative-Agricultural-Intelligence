import React from "react";
import { CheckCircle2, AlertTriangle, AlertCircle, Info } from "lucide-react";
import { cn } from "@/lib/utils";

export type StatusType = "healthy" | "watch" | "risk" | "info";

export interface StatusPillProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: StatusType;
  label?: string;
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
}

const statusConfig: Record<
  StatusType,
  {
    defaultLabel: string;
    icon: React.ComponentType<{ className?: string }>;
    styles: string;
    iconStyles: string;
  }
> = {
  healthy: {
    defaultLabel: "Healthy",
    icon: CheckCircle2,
    styles: "bg-[#DCFCE7] text-[#166534] border-[#86EFAC]",
    iconStyles: "text-[#16A34A]",
  },
  watch: {
    defaultLabel: "Watch",
    icon: AlertTriangle,
    styles: "bg-[#FEF3C7] text-[#92400E] border-[#FCD34D]",
    iconStyles: "text-[#F59E0B]",
  },
  risk: {
    defaultLabel: "Risk Alert",
    icon: AlertCircle,
    styles: "bg-[#FEE2E2] text-[#991B1B] border-[#FCA5A5]",
    iconStyles: "text-[#DC2626]",
  },
  info: {
    defaultLabel: "Information",
    icon: Info,
    styles: "bg-[#E0F2FE] text-[#075985] border-[#BAE6FD]",
    iconStyles: "text-[#0EA5E9]",
  },
};

export function StatusPill({
  status,
  label,
  size = "md",
  showIcon = true,
  className,
  ...props
}: StatusPillProps) {
  const config = statusConfig[status] || statusConfig.info;
  const IconComponent = config.icon;
  const displayLabel = label || config.defaultLabel;

  return (
    <span
      role="status"
      className={cn(
        "inline-flex items-center font-medium border rounded-full select-none",
        config.styles,
        size === "sm" && "text-xs px-2 py-0.5 gap-1",
        size === "md" && "text-sm px-3 py-1 gap-1.5",
        size === "lg" && "text-base px-4 py-1.5 gap-2",
        className
      )}
      {...props}
    >
      {showIcon && (
        <IconComponent
          aria-hidden="true"
          className={cn(
            "flex-shrink-0",
            size === "sm" && "h-3.5 w-3.5",
            size === "md" && "h-4 w-4",
            size === "lg" && "h-5 w-5",
            config.iconStyles
          )}
        />
      )}
      <span>{displayLabel}</span>
    </span>
  );
}
