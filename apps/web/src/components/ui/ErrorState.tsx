"use client";

import React, { useState } from "react";
import { AlertCircle, RefreshCw, Copy, Check } from "lucide-react";
import { Button } from "./Button";
import { Card } from "./Card";
import { cn } from "@/lib/utils";
import type { ApiErrorDetail } from "@krishinet/shared";

export interface ErrorStateProps {
  error: ApiErrorDetail | { code?: string; message: string; request_id?: string; details?: any };
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({ error, onRetry, className }: ErrorStateProps) {
  const [copied, setCopied] = useState(false);
  const code = error.code || "UNKNOWN_ERROR";
  const message = error.message || "An unexpected error occurred.";
  const requestId = error.request_id || "N/A";

  const handleCopyRequestId = () => {
    if (navigator?.clipboard && requestId !== "N/A") {
      navigator.clipboard.writeText(requestId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Card
      role="alert"
      className={cn(
        "p-6 sm:p-8 bg-[#FFF5F5] border-status-risk/30 shadow-card text-text",
        className
      )}
    >
      <div className="flex items-start gap-4">
        <div className="h-12 w-12 rounded-btn bg-[#FEE2E2] border border-[#FCA5A5] flex items-center justify-center text-status-risk flex-shrink-0">
          <AlertCircle className="h-6 w-6" />
        </div>

        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-lg font-bold text-status-risk">
              Service Request Failed
            </h3>
            <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-[#FEE2E2] text-[#991B1B]">
              {code}
            </span>
          </div>

          <p className="text-sm text-text leading-relaxed font-medium">
            {message}
          </p>

          {/* Request ID envelope metadata for support & auditing */}
          <div className="flex items-center gap-2 pt-2 text-xs text-text-muted">
            <span>Trace ID:</span>
            <code className="bg-white px-2 py-0.5 rounded border border-border font-mono text-[11px] text-text">
              {requestId}
            </code>
            {requestId !== "N/A" && (
              <button
                type="button"
                onClick={handleCopyRequestId}
                aria-label="Copy request ID"
                className="p-1 text-text-muted hover:text-text rounded"
              >
                {copied ? (
                  <Check className="h-3.5 w-3.5 text-primary" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
              </button>
            )}
          </div>

          {onRetry && (
            <div className="pt-4">
              <Button
                variant="primary"
                size="sm"
                onClick={onRetry}
                leftIcon={<RefreshCw className="h-4 w-4" />}
              >
                Retry Request
              </Button>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
