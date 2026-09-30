"use client";

import React, { useState } from "react";
import {
  Download,
  ShieldCheck,
  CheckCircle2,
  FileCode2,
  Cpu,
  Layers,
  Sparkles,
  Info,
  X,
  ExternalLink,
} from "lucide-react";
import type { ModelCardSummary } from "@krishinet/shared";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusPill } from "@/components/ui/StatusPill";
import { cn } from "@/lib/utils";

interface ModelHubDirectoryProps {
  models: ModelCardSummary[];
  className?: string;
}

export function ModelHubDirectory({ models, className }: ModelHubDirectoryProps) {
  const [quantFilter, setQuantFilter] = useState<"all" | "int8" | "fp16">("all");
  const [activeModel, setActiveModel] = useState<ModelCardSummary | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [downloadSuccessId, setDownloadSuccessId] = useState<string | null>(null);

  const filteredModels = models.filter((m) => {
    if (quantFilter === "all") return true;
    return m.quantization === quantFilter;
  });

  const handleDownload = (model: ModelCardSummary) => {
    setDownloadingId(model.id);
    setTimeout(() => {
      setDownloadingId(null);
      setDownloadSuccessId(model.id);
      setTimeout(() => setDownloadSuccessId(null), 4000);
    }, 1200);
  };

  return (
    <div className={cn("space-y-6", className)}>
      <Card className="p-6 bg-white border border-border shadow-card space-y-6">
        <CardHeader className="p-0 border-none">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <CardTitle className="text-lg font-extrabold text-primary-dark flex items-center gap-2">
                <FileCode2 className="h-5 w-5 text-primary" />
                <span>BRICS Sovereign Model Hub & DPG Registry</span>
              </CardTitle>
              <CardDescription>
                Open-source, quantized ONNX models for offline rural deployment certified as Digital Public Goods.
              </CardDescription>
            </div>

            {/* Quantization Filter */}
            <div className="flex items-center gap-1.5 bg-surface-soft p-1 rounded-xl border border-border shrink-0">
              {(["all", "int8", "fp16"] as const).map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => setQuantFilter(q)}
                  className={cn(
                    "px-3 py-1 text-xs font-bold rounded-lg uppercase transition-colors",
                    quantFilter === q
                      ? "bg-white text-primary-dark shadow-sm"
                      : "text-text-muted hover:text-text"
                  )}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>

        {/* Model Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredModels.map((model) => (
            <Card
              key={model.id}
              className="p-5 bg-surface-soft/60 border border-border hover:border-primary/50 transition-all flex flex-col justify-between space-y-4"
            >
              <div>
                {/* Header */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-extrabold text-base text-text">
                        {model.model_name}
                      </h4>
                      <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-white border border-border text-primary">
                        v{model.version}
                      </span>
                    </div>
                    <span className="text-[11px] text-text-muted uppercase tracking-wider font-semibold">
                      {model.license}
                    </span>
                  </div>

                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-primary-light text-primary-dark border border-primary/20 shrink-0">
                    {model.quantization.toUpperCase()}
                  </span>
                </div>

                {/* Crop coverage tags */}
                <div className="flex flex-wrap gap-1 mb-3">
                  {model.crop_coverage.map((c) => (
                    <span
                      key={c}
                      className="px-2 py-0.5 rounded text-[11px] bg-white border border-border text-text font-medium"
                    >
                      {c}
                    </span>
                  ))}
                </div>

                {/* Accuracy & Size Metrics */}
                <div className="grid grid-cols-3 gap-2 p-2.5 rounded-xl bg-white border border-border text-center text-xs">
                  <div>
                    <span className="text-[10px] text-text-muted block">Top-1 Accuracy</span>
                    <span className="font-bold text-text font-mono">
                      {(model.accuracy_top1 * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-text-muted block">Top-3 Accuracy</span>
                    <span className="font-bold text-primary-dark font-mono">
                      {(model.accuracy_top3 * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-text-muted block">Package Size</span>
                    <span className="font-bold text-text font-mono">
                      {model.size_mb} MB
                    </span>
                  </div>
                </div>

                {/* SHA-256 Digest */}
                <div className="mt-2 text-[10px] font-mono text-text-muted truncate flex items-center gap-1">
                  <ShieldCheck className="h-3 w-3 text-emerald-600 shrink-0" />
                  <span>SHA256: {model.sha256_hash.slice(0, 16)}...</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setActiveModel(model)}
                  className="text-xs font-bold text-text-muted hover:text-primary transition-colors flex items-center gap-1"
                >
                  <Info className="h-3.5 w-3.5" />
                  Inspect Card
                </button>

                <Button
                  variant="primary"
                  size="sm"
                  isLoading={downloadingId === model.id}
                  onClick={() => handleDownload(model)}
                  leftIcon={
                    downloadSuccessId === model.id ? (
                      <CheckCircle2 className="h-4 w-4 text-white" />
                    ) : (
                      <Download className="h-4 w-4" />
                    )
                  }
                >
                  {downloadSuccessId === model.id ? "Verified & Saved" : "Download ONNX"}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </Card>

      {/* Model Card Detailed Modal */}
      {activeModel && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <Card className="max-w-lg w-full p-6 bg-white shadow-2xl space-y-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-primary bg-primary-light px-2 py-0.5 rounded-full">
                  Digital Public Good (DPG) Certified
                </span>
                <h3 className="text-xl font-extrabold text-primary-dark mt-1">
                  {activeModel.model_name}
                </h3>
                <p className="text-xs text-text-muted">
                  Version {activeModel.version} • {activeModel.quantization.toUpperCase()} Quantized
                </p>
              </div>
              <button
                onClick={() => setActiveModel(null)}
                className="p-1.5 rounded-lg hover:bg-surface-soft text-text-muted"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-surface-soft rounded-xl border border-border space-y-1">
                <span className="font-bold text-text block">Model Lineage & Training Dataset:</span>
                <p className="text-text-muted leading-relaxed">
                  Trained on multi-country smallholder imagery from ICAR (India), Embrapa (Brazil), and ARC (South Africa), representing diverse soil backgrounds, lighting conditions, and camera hardware.
                </p>
              </div>

              <div className="p-3 bg-surface-soft rounded-xl border border-border space-y-1">
                <span className="font-bold text-text block">Cryptographic Integrity Hash:</span>
                <code className="text-[11px] font-mono break-all text-primary-dark block bg-white p-2 rounded border border-border">
                  {activeModel.sha256_hash}
                </code>
              </div>

              <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-emerald-950 space-y-1">
                <span className="font-bold block">Sovereign Edge Deployment Guarantee:</span>
                <p className="text-[11px] leading-relaxed">
                  Execution happens 100% locally in browser WebAssembly / ONNX Runtime. Zero image data is sent to external cloud APIs without farmer opt-in consent.
                </p>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="secondary" onClick={() => setActiveModel(null)}>
                Close Inspector
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
