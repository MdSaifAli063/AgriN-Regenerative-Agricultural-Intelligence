"use client";

import React, { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import {
  Globe,
  ShieldCheck,
  Cpu,
  Layers,
  FileCode2,
  GitCompare,
  Sprout,
  Droplets,
  CloudRain,
  Trees,
  AlertTriangle,
  RefreshCw,
  FileCheck,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { MetricTile } from "@/components/ui/MetricTile";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { BricsNodeTable } from "@/components/policy/BricsNodeTable";
import { ClimateAnalogueMatrix } from "@/components/policy/ClimateAnalogueMatrix";
import { FederatedLearningCard } from "@/components/policy/FederatedLearningCard";
import { ModelHubDirectory } from "@/components/policy/ModelHubDirectory";
import { EgressAuditPanel } from "@/components/policy/EgressAuditPanel";
import { ConsentLedgerPanel } from "@/components/policy/ConsentLedgerPanel";
import {
  fetchBricsMacroMetrics,
  fetchBricsNodes,
  fetchClimateAnalogues,
  fetchModelCards,
  type BricsMacroMetrics,
} from "@/lib/adapters/brics-policy";
import type {
  BricsNodeSummary,
  ClimateAnalogue,
  ModelCardSummary,
  Provenance,
} from "@krishinet/shared";
import { cn } from "@/lib/utils";

export default function BricsPolicyDashboardPage() {
  const params = useParams();
  const locale = (params?.locale as string) || "en";

  const [metrics, setMetrics] = useState<BricsMacroMetrics | null>(null);
  const [nodes, setNodes] = useState<BricsNodeSummary[]>([]);
  const [analogues, setAnalogues] = useState<ClimateAnalogue[]>([]);
  const [models, setModels] = useState<ModelCardSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"nodes" | "analogues" | "federated" | "models" | "egress" | "consent">("nodes");

  const [provenance] = useState<Provenance>({
    source: "BRICS Agricultural Commons Forward Adapter",
    mode: "demo",
    fetched_at: new Date().toISOString(),
    ttl: 3600,
    confidence: 0.98,
    notes: "Phase 7 Forward-Compatible Contract (Zero frontend changes when backend routes activate)",
  });

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [m, n, a, mdl] = await Promise.all([
        fetchBricsMacroMetrics(),
        fetchBricsNodes(),
        fetchClimateAnalogues(),
        fetchModelCards(),
      ]);
      setMetrics(m);
      setNodes(n);
      setAnalogues(a);
      setModels(mdl);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="min-h-screen bg-surface-soft pb-16">
      {/* Top BRICS Analytical Command Header */}
      <div className="bg-white border-b border-border shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-extrabold uppercase tracking-wider text-emerald-800 bg-emerald-100 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                  <Globe className="h-3.5 w-3.5" />
                  Sovereign BRICS Agro-Commons
                </span>
                <ProvenanceBadge provenance={provenance} size="sm" />
              </div>
              <h1 className="text-2xl sm:text-3xl font-black text-primary-dark tracking-tight">
                BRICS Regenerative Agricultural Intelligence Network
              </h1>
              <p className="text-xs sm:text-sm text-text-muted mt-0.5">
                Analytical Command Center • Cross-Border Food Security & Climate Resilience (IND • BRA • ZAF • CHN • RUS)
              </p>
            </div>

            <Button
              variant="secondary"
              size="sm"
              onClick={loadData}
              isLoading={isLoading}
              leftIcon={<RefreshCw className="h-4 w-4" />}
            >
              Sync Node Telemetry
            </Button>
          </div>

          {/* Macro-KPI Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-6 gap-3 pt-2">
            <MetricTile
              title="Regenerated Land"
              value={metrics ? `${(metrics.total_hectares_regenerated / 1000000).toFixed(2)}M` : "1.42M"}
              unit="ha"
              subtitle="Active Soil Regeneration"
              status="healthy"
              icon={<Trees className="h-4 w-4 text-emerald-600" />}
            />
            <MetricTile
              title="Farmers Connected"
              value={metrics ? `${(metrics.farmers_reached / 1000).toFixed(0)}k` : "512k"}
              subtitle="Smallholder Coverage"
              status="healthy"
              icon={<Sprout className="h-4 w-4 text-primary" />}
            />
            <MetricTile
              title="Water Conserved"
              value={metrics ? metrics.water_saved_megalitres.toLocaleString() : "8,940"}
              unit="ML"
              subtitle="Precision Irrigation"
              status="healthy"
              icon={<Droplets className="h-4 w-4 text-blue-600" />}
            />
            <MetricTile
              title="CO₂e Sequestered"
              value={metrics ? `${(metrics.carbon_sequestered_tonnes / 1000).toFixed(0)}k` : "218k"}
              unit="t"
              subtitle="Soil Carbon Stock"
              status="healthy"
              icon={<ShieldCheck className="h-4 w-4 text-emerald-700" />}
            />
            <MetricTile
              title="Transboundary Alerts"
              value={metrics ? metrics.active_disease_alerts : 14}
              subtitle="Surveillance Radar"
              status="watch"
              icon={<AlertTriangle className="h-4 w-4 text-amber-600" />}
            />
            <MetricTile
              title="Federated AI Models"
              value={metrics ? metrics.models_federated : 8}
              subtitle="Edge & DPG Hub"
              status="healthy"
              icon={<Cpu className="h-4 w-4 text-primary" />}
            />
          </div>
        </div>
      </div>

      {/* Navigation Tabs Bar */}
      <div className="bg-white border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <nav className="flex space-x-6 overflow-x-auto py-3 text-xs font-bold" aria-label="Policy Tabs">
            <button
              onClick={() => setActiveTab("nodes")}
              className={cn(
                "pb-2 border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap",
                activeTab === "nodes"
                  ? "border-primary text-primary-dark font-extrabold"
                  : "border-transparent text-text-muted hover:text-text"
              )}
            >
              <Globe className="h-4 w-4" />
              Sovereign National Nodes ({nodes.length})
            </button>

            <button
              onClick={() => setActiveTab("analogues")}
              className={cn(
                "pb-2 border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap",
                activeTab === "analogues"
                  ? "border-primary text-primary-dark font-extrabold"
                  : "border-transparent text-text-muted hover:text-text"
              )}
            >
              <GitCompare className="h-4 w-4" />
              Climate-Analogue Matrix ({analogues.length})
            </button>

            <button
              onClick={() => setActiveTab("federated")}
              className={cn(
                "pb-2 border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap",
                activeTab === "federated"
                  ? "border-primary text-primary-dark font-extrabold"
                  : "border-transparent text-text-muted hover:text-text"
              )}
            >
              <Cpu className="h-4 w-4" />
              Federated Learning (Round 14)
            </button>

            <button
              onClick={() => setActiveTab("models")}
              className={cn(
                "pb-2 border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap",
                activeTab === "models"
                  ? "border-primary text-primary-dark font-extrabold"
                  : "border-transparent text-text-muted hover:text-text"
              )}
            >
              <FileCode2 className="h-4 w-4" />
              Model Hub & DPG Registry ({models.length})
            </button>

            <button
              onClick={() => setActiveTab("egress")}
              className={cn(
                "pb-2 border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap",
                activeTab === "egress"
                  ? "border-primary text-primary-dark font-extrabold"
                  : "border-transparent text-text-muted hover:text-text"
              )}
            >
              <ShieldCheck className="h-4 w-4" />
              Sovereign Egress Audit & Passport
            </button>

            <button
              onClick={() => setActiveTab("consent")}
              className={cn(
                "pb-2 border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap",
                activeTab === "consent"
                  ? "border-primary text-primary-dark font-extrabold"
                  : "border-transparent text-text-muted hover:text-text"
              )}
            >
              <FileCheck className="h-4 w-4" />
              Consent Ledger & Kantara Receipts
            </button>
          </nav>
        </div>
      </div>

      {/* Main Tab Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-6">
        {activeTab === "nodes" && <BricsNodeTable nodes={nodes} />}
        {activeTab === "analogues" && <ClimateAnalogueMatrix analogues={analogues} />}
        {activeTab === "federated" && <FederatedLearningCard />}
        {activeTab === "models" && <ModelHubDirectory models={models} />}
        {activeTab === "egress" && <EgressAuditPanel />}
        {activeTab === "consent" && <ConsentLedgerPanel />}
      </div>
    </div>
  );
}
