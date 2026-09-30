import React from "react";
import { ShieldCheck, AlertTriangle, AlertOctagon, PhoneCall } from "lucide-react";
import { Button } from "./Button";
import { cn } from "@/lib/utils";

export interface ConfidenceMeterProps {
  score: number; // 0.0 to 1.0 or 0 to 100
  level?: "high" | "medium" | "low";
  threshold?: number;
  onContactOfficer?: () => void;
  className?: string;
}

export function ConfidenceMeter({
  score,
  level: explicitLevel,
  threshold = 0.42,
  onContactOfficer,
  className,
}: ConfidenceMeterProps) {
  const normalizedScore = score > 1 ? score / 100 : score;
  const percent = Math.round(normalizedScore * 100);

  // Derive level if not explicitly provided
  const level =
    explicitLevel ||
    (normalizedScore >= 0.75
      ? "high"
      : normalizedScore >= threshold
      ? "medium"
      : "low");

  return (
    <div className={cn("space-y-3", className)}>
      {/* Top Header: Score & Badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {level === "high" && (
            <ShieldCheck className="h-5 w-5 text-primary" />
          )}
          {level === "medium" && (
            <AlertTriangle className="h-5 w-5 text-status-watch" />
          )}
          {level === "low" && (
            <AlertOctagon className="h-5 w-5 text-status-risk" />
          )}
          <span className="text-sm font-semibold text-text">
            Diagnostic Confidence
          </span>
        </div>
        <span
          className={cn(
            "text-base font-bold",
            level === "high" && "text-primary",
            level === "medium" && "text-status-watch",
            level === "low" && "text-status-risk"
          )}
        >
          {percent}%
        </span>
      </div>

      {/* Progress Track */}
      <div
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Confidence score: ${percent}%`}
        className="h-3 w-full bg-surface-soft border border-border rounded-full overflow-hidden"
      >
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            level === "high" && "bg-primary",
            level === "medium" && "bg-status-watch",
            level === "low" && "bg-status-risk"
          )}
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* Contextual Warning / Guidance Banners */}
      {level === "medium" && (
        <div className="p-3.5 bg-[#FEF3C7] border border-[#FCD34D] rounded-xl flex items-start gap-2.5 text-xs text-[#92400E]">
          <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5 text-[#F59E0B]" />
          <div>
            <strong className="font-semibold block">Moderate Confidence</strong>
            Symptoms share features with multiple conditions. Cross-reference
            with cultural history or verify with an extension worker.
          </div>
        </div>
      )}

      {level === "low" && (
        <div className="p-4 bg-[#FEE2E2] border border-[#FCA5A5] rounded-xl space-y-2 text-xs text-[#991B1B]">
          <div className="flex items-start gap-2.5">
            <AlertOctagon className="h-4 w-4 flex-shrink-0 mt-0.5 text-[#DC2626]" />
            <div>
              <strong className="font-semibold block text-sm">
                Uncertain Diagnosis – Escalation Required
              </strong>
              The confidence score is below threshold ({Math.round(threshold * 100)}%).
              Do NOT apply irreversible synthetic chemical sprays without manual verification.
            </div>
          </div>
          {onContactOfficer && (
            <div className="pt-2">
              <Button
                variant="danger"
                size="sm"
                onClick={onContactOfficer}
                leftIcon={<PhoneCall className="h-4 w-4" />}
              >
                Contact Local Extension Officer
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
