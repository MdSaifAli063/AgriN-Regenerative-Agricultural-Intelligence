"use client";

import React, { useState } from "react";
import {
  GitCompare,
  ArrowRight,
  Sparkles,
  Download,
  CheckCircle2,
  Sprout,
  Compass,
  FileText,
} from "lucide-react";
import type { ClimateAnalogue } from "@krishinet/shared";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusPill } from "@/components/ui/StatusPill";
import { cn } from "@/lib/utils";

interface ClimateAnalogueMatrixProps {
  analogues: ClimateAnalogue[];
  className?: string;
}

export function ClimateAnalogueMatrix({ analogues, className }: ClimateAnalogueMatrixProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  const activeAnalogue = analogues[selectedIndex] || analogues[0];

  const handleExportBrief = () => {
    setDownloadSuccess(true);
    setTimeout(() => setDownloadSuccess(false), 4000);
  };

  return (
    <Card className="p-6 bg-white border border-border shadow-card space-y-6">
      <CardHeader className="p-0 border-none">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <CardTitle className="text-lg font-extrabold text-primary-dark flex items-center gap-2">
              <GitCompare className="h-5 w-5 text-primary" />
              <span>Transboundary Climate-Analogue Matching Engine</span>
            </CardTitle>
            <CardDescription>
              Pairing vulnerable farming districts with existing climate analogues across BRICS to transfer tested regenerative solutions.
            </CardDescription>
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={handleExportBrief}
            leftIcon={downloadSuccess ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <Download className="h-4 w-4" />}
          >
            {downloadSuccess ? "Brief Exported (PDF)" : "Export Policy Brief"}
          </Button>
        </div>
      </CardHeader>

      {/* District Pair Selector Tabs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {analogues.map((item, idx) => {
          const isSelected = selectedIndex === idx;
          const scorePercent = Math.round(item.similarity_score * 100);

          return (
            <button
              key={`${item.source_district}-${item.matched_district}`}
              type="button"
              onClick={() => setSelectedIndex(idx)}
              className={cn(
                "p-4 rounded-xl border text-left transition-all duration-200 space-y-2 relative overflow-hidden",
                isSelected
                  ? "bg-primary-light/40 border-primary shadow-sm"
                  : "bg-surface-soft/60 border-border hover:bg-slate-100"
              )}
            >
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-text-muted uppercase text-[10px]">
                  Pairing #{idx + 1}
                </span>
                <span className="font-mono font-bold text-primary px-2 py-0.5 rounded-full bg-white border border-primary/20 text-xs">
                  {scorePercent}% Match
                </span>
              </div>

              <div className="space-y-1">
                <div className="font-extrabold text-sm text-text flex items-center gap-1.5 flex-wrap">
                  <span>{item.source_district}</span>
                  <span className="text-text-muted text-xs">({item.source_country})</span>
                </div>
                <div className="flex items-center gap-1 text-primary-dark font-bold text-xs">
                  <ArrowRight className="h-3.5 w-3.5 shrink-0" />
                  <span>{item.matched_district}</span>
                  <span className="text-text-muted text-[11px] font-normal">
                    ({item.matched_country})
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Selected Analogue Deep Dive Breakdown */}
      {activeAnalogue && (
        <div className="p-5 rounded-2xl bg-surface-soft border border-border space-y-5">
          {/* Header match summary */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
            <div>
              <span className="text-[11px] font-bold uppercase text-primary tracking-wider block">
                Agro-Climatic Twin Match Analysis
              </span>
              <h3 className="text-base font-extrabold text-primary-dark mt-0.5">
                {activeAnalogue.source_district} ({activeAnalogue.source_country}) ↔ {activeAnalogue.matched_district} ({activeAnalogue.matched_country})
              </h3>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right">
                <span className="text-xs text-text-muted block">Bioclimatic Vector Similarity</span>
                <span className="text-lg font-black text-primary font-mono">
                  {(activeAnalogue.similarity_score * 100).toFixed(1)}%
                </span>
              </div>
              <StatusPill status="healthy" label="STRONG ANALOGUE" size="sm" />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Shared Attributes */}
            <div className="p-4 bg-white rounded-xl border border-border space-y-3">
              <span className="text-xs font-bold uppercase text-text-muted flex items-center gap-1.5">
                <Compass className="h-4 w-4 text-primary" />
                <span>Shared Agro-Ecological Attributes</span>
              </span>
              <ul className="space-y-2 text-xs text-text">
                {activeAnalogue.key_shared_attributes.map((attr, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary mt-1.5 shrink-0" />
                    <span>{attr}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Proven Regenerative Interventions */}
            <div className="p-4 bg-emerald-50/60 rounded-xl border border-emerald-200 space-y-3">
              <span className="text-xs font-bold uppercase text-emerald-900 flex items-center gap-1.5">
                <Sprout className="h-4 w-4 text-emerald-700" />
                <span>Validated Regenerative Interventions for Policy Transfer</span>
              </span>
              <ul className="space-y-2 text-xs text-emerald-950 font-medium">
                {activeAnalogue.successful_regenerative_interventions.map((sol, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" />
                    <span>{sol}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
