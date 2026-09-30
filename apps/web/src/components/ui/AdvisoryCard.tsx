import React from "react";
import { Sprout, Droplets, Sun, AlertTriangle } from "lucide-react";
import { Card } from "./Card";
import { StatusPill } from "./StatusPill";
import { VoiceButton } from "./VoiceButton";
import { cn } from "@/lib/utils";

export interface AdvisoryCardProps {
  title: string;
  category: "crop" | "practice" | "fertiliser" | "irrigation";
  suitabilityScore?: number;
  waterNeedMm?: number;
  riskLevel?: "low" | "medium" | "high";
  summary: string;
  readAloudText?: string;
  tags?: string[];
  className?: string;
}

export function AdvisoryCard({
  title,
  category,
  suitabilityScore,
  waterNeedMm,
  riskLevel,
  summary,
  readAloudText,
  tags = [],
  className,
}: AdvisoryCardProps) {
  return (
    <Card className={cn("p-6 flex flex-col justify-between space-y-4 hover:border-primary/60 transition-colors", className)}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-surface-soft text-text-muted border border-border">
              {category}
            </span>
            {riskLevel && (
              <StatusPill
                status={riskLevel === "low" ? "healthy" : riskLevel === "medium" ? "watch" : "risk"}
                label={`${riskLevel} climate risk`}
                size="sm"
              />
            )}
          </div>
          <h3 className="text-xl font-bold text-primary-dark">{title}</h3>
        </div>

        <VoiceButton
          mode="speak"
          textToSpeak={readAloudText || `${title}. ${summary}`}
          size="sm"
        />
      </div>

      <p className="text-sm text-text leading-relaxed">{summary}</p>

      {/* Metrics Row (Suitability / Water) */}
      <div className="pt-3 border-t border-border flex items-center justify-between gap-4 text-xs font-medium text-text-muted flex-wrap">
        {suitabilityScore !== undefined && (
          <div className="flex items-center gap-1.5">
            <Sprout className="h-4 w-4 text-primary" />
            <span>Suitability: <strong className="text-text">{suitabilityScore}%</strong></span>
          </div>
        )}
        {waterNeedMm !== undefined && (
          <div className="flex items-center gap-1.5">
            <Droplets className="h-4 w-4 text-[#0EA5E9]" />
            <span>Water Need: <strong className="text-text">{waterNeedMm} mm</strong></span>
          </div>
        )}
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {tags.map((tag, idx) => (
            <span
              key={idx}
              className="text-[11px] px-2 py-0.5 rounded-full bg-surface-soft text-primary-dark border border-border"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}
    </Card>
  );
}
