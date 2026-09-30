"use client";

import React, { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import {
  Layers,
  Sprout,
  Droplets,
  CloudRain,
  ArrowLeft,
  Info,
  CheckCircle2,
  AlertTriangle,
  Flame,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { ChartCard } from "@/components/ui/ChartCard";
import { StatusPill } from "@/components/ui/StatusPill";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { MapLegend } from "@/components/ui/MapLegend";
import { CardSkeleton } from "@/components/ui/Skeletons";
import { ErrorState } from "@/components/ui/ErrorState";
import { apiClient } from "@/lib/api/client";
import { cn } from "@/lib/utils";

export default function FieldIntelligencePage() {
  const params = useParams();
  const router = useRouter();
  const locale = (params?.locale as string) || "en";
  const fieldId = (params?.id as string) || "fld-001";

  const [activeTab, setActiveTab] = useState<"satellite" | "soil" | "weather">("satellite");

  // Fetch Full Field Intelligence
  const { data: intelligence, isLoading, error, refetch } = useQuery<any>({
    queryKey: ["field-intelligence", fieldId],
    queryFn: () => apiClient<any>(`fields/${fieldId}/intelligence`),
  });

  // Mock 90-day timeseries data (matching backend Sentinel-2 schema)
  const timeseriesData = [
    { date: "Jul 05", ndvi: 0.38, ndwi: 0.12, evi: 0.28, ndmi: 0.18 },
    { date: "Jul 15", ndvi: 0.44, ndwi: 0.18, evi: 0.33, ndmi: 0.22 },
    { date: "Jul 25", ndvi: 0.52, ndwi: 0.24, evi: 0.41, ndmi: 0.29 },
    { date: "Aug 04", ndvi: 0.58, ndwi: 0.27, evi: 0.46, ndmi: 0.31 },
    { date: "Aug 14", ndvi: 0.65, ndwi: 0.31, evi: 0.53, ndmi: 0.36 },
    { date: "Aug 24", ndvi: 0.70, ndwi: 0.34, evi: 0.57, ndmi: 0.38 },
    { date: "Sep 03", ndvi: 0.74, ndwi: 0.36, evi: 0.61, ndmi: 0.40 },
    { date: "Sep 13", ndvi: 0.76, ndwi: 0.35, evi: 0.63, ndmi: 0.39 },
    { date: "Sep 23", ndvi: 0.72, ndwi: 0.32, evi: 0.59, ndmi: 0.37 },
  ];

  // Soil Chemical Profile
  const soilComponents = [
    { name: "Organic Carbon (SOC)", value: 0.82, unit: "%", status: "healthy" as const, range: "0.75 - 1.2%" },
    { name: "Available Nitrogen (N)", value: 185, unit: "kg/ha", status: "watch" as const, range: "280 - 560 kg/ha" },
    { name: "Available Phosphorus (P)", value: 16.5, unit: "kg/ha", status: "healthy" as const, range: "11 - 22 kg/ha" },
    { name: "Available Potassium (K)", value: 340, unit: "kg/ha", status: "healthy" as const, range: "140 - 280 kg/ha" },
    { name: "Soil pH (1:2.5 H2O)", value: 7.4, unit: "pH", status: "healthy" as const, range: "6.5 - 7.8 (Optimal)" },
    { name: "Clay Content", value: 44, unit: "%", status: "healthy" as const, range: "Black Vertisol Clay" },
  ];

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <ErrorState error={error as any} onRetry={() => refetch()} />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      {/* Header with Back and Field Summary */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-border">
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => router.push(`/${locale}/dashboard`)}
            aria-label="Back to dashboard"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-primary-dark tracking-tight">
                Field Intelligence Hub
              </h1>
              <StatusPill status="healthy" label="90-day Vigour Baseline Safe" />
            </div>
            <p className="text-xs text-text-muted mt-0.5">
              Field ID: <code className="font-mono text-text">{fieldId}</code> • Copernicus Sentinel-2 L2A + ISRIC SoilGrids
            </p>
          </div>
        </div>

        <ProvenanceBadge
          provenance={{
            source: "Copernicus Sentinel-2 & ISRIC SoilGrids",
            mode: "demo",
            fetched_at: new Date().toISOString(),
            ttl: 3600,
            confidence: 0.91,
          }}
        />
      </div>

      {/* Tabs Row */}
      <div className="flex border-b border-border gap-2">
        <button
          type="button"
          onClick={() => setActiveTab("satellite")}
          className={cn(
            "px-4 py-2.5 text-sm font-bold border-b-2 transition-colors select-none flex items-center gap-2",
            activeTab === "satellite"
              ? "border-primary text-primary-dark bg-surface-soft/60"
              : "border-transparent text-text-muted hover:text-text"
          )}
        >
          <Layers className="h-4 w-4" />
          <span>Satellite Vegetation Indices (90d)</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("soil")}
          className={cn(
            "px-4 py-2.5 text-sm font-bold border-b-2 transition-colors select-none flex items-center gap-2",
            activeTab === "soil"
              ? "border-primary text-primary-dark bg-surface-soft/60"
              : "border-transparent text-text-muted hover:text-text"
          )}
        >
          <Droplets className="h-4 w-4" />
          <span>Soil Chemistry & Carbon Score</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("weather")}
          className={cn(
            "px-4 py-2.5 text-sm font-bold border-b-2 transition-colors select-none flex items-center gap-2",
            activeTab === "weather"
              ? "border-primary text-primary-dark bg-surface-soft/60"
              : "border-transparent text-text-muted hover:text-text"
          )}
        >
          <CloudRain className="h-4 w-4" />
          <span>Agro-Meteorology & Risk</span>
        </button>
      </div>

      {/* TAB 1: SATELLITE INTELLIGENCE */}
      {activeTab === "satellite" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* NDVI 90-Day Time Series Chart */}
          <ChartCard
            title="90-Day Multi-Spectral Trajectory (NDVI / EVI / NDWI)"
            description="Continuous Sentinel-2 observation tracking vegetative vigour, chlorophyll absorption, and canopy moisture."
            tableData={timeseriesData}
          >
            <div className="h-72 w-full pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={timeseriesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#DCEBDD" />
                  <XAxis dataKey="date" stroke="#4B6B57" fontSize={11} />
                  <YAxis domain={[0, 1]} stroke="#4B6B57" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#FFFFFF",
                      borderColor: "#DCEBDD",
                      borderRadius: "12px",
                      fontSize: "12px",
                      boxShadow: "0 4px 12px rgba(22,163,74,0.1)",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="ndvi"
                    name="NDVI (Canopy Vigour)"
                    stroke="#16A34A"
                    strokeWidth={3}
                    dot={{ fill: "#16A34A", r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="evi"
                    name="EVI (Enhanced Vigour)"
                    stroke="#86EFAC"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="ndwi"
                    name="NDWI (Water Index)"
                    stroke="#0EA5E9"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          {/* Spatial Heatmap Simulation Card & Legend */}
          <Card className="p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-border flex-wrap gap-2">
              <div>
                <h3 className="text-lg font-bold text-primary-dark">
                  High-Resolution Zonal Vigour Map (~30m Cells)
                </h3>
                <p className="text-xs text-text-muted">
                  Spatial within-field variation based on latest cloudless Sentinel-2 overpass.
                </p>
              </div>
              <MapLegend type="ndvi" />
            </div>

            {/* Simulated Satellite Grid Canvas */}
            <div className="h-64 w-full rounded-xl border border-border bg-gradient-to-br from-[#86EFAC]/30 via-[#16A34A]/40 to-[#14532D]/50 relative overflow-hidden flex items-center justify-center">
              <div className="absolute inset-0 bg-[radial-gradient(#16A34A_1px,transparent_1px)] [background-size:16px_16px] opacity-30" />
              <div className="p-4 bg-white/90 backdrop-blur-md rounded-xl border border-border shadow-sm text-center max-w-sm">
                <span className="text-xs font-bold uppercase text-primary tracking-wide block">
                  Field Canopy Uniformity
                </span>
                <span className="text-2xl font-extrabold text-primary-dark block mt-1">
                  88% Homogeneous
                </span>
                <span className="text-xs text-text-muted mt-1 block">
                  No anomalous spatial dry patches or nitrogen-deficiency streaks detected.
                </span>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* TAB 2: SOIL CHEMISTRY */}
      {activeTab === "soil" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Soil Health Score Gauge & Chemistry Profile */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Score Card */}
            <Card className="p-6 flex flex-col justify-between items-center text-center bg-surface-soft border-primary/30">
              <span className="text-xs font-bold uppercase tracking-wider text-text-muted">
                Composite Soil Health Score
              </span>
              <div className="my-6 relative flex items-center justify-center">
                <div className="h-32 w-32 rounded-full border-8 border-primary-light flex items-center justify-center">
                  <div className="text-center">
                    <span className="text-4xl font-extrabold text-primary-dark block">
                      84
                    </span>
                    <span className="text-xs font-semibold text-primary">/ 100</span>
                  </div>
                </div>
              </div>
              <StatusPill status="healthy" label="Tier-1 Regenerative Soil" />
              <p className="text-xs text-text-muted mt-3">
                High microbial respiration and cation exchange capacity (CEC: 38 cmol/kg).
              </p>
            </Card>

            {/* Limiting Factors & Improvement Hints */}
            <Card className="p-6 md:col-span-2 space-y-4">
              <CardTitle>Limiting Factors & Regenerative Amendments</CardTitle>
              <div className="space-y-3 pt-1">
                <div className="p-3.5 rounded-xl border border-[#FCD34D] bg-[#FEF3C7] text-xs text-[#92400E] space-y-1">
                  <div className="flex items-center gap-2 font-bold">
                    <AlertTriangle className="h-4 w-4 text-[#F59E0B]" />
                    <span>Primary Limiting Factor: Available Nitrogen (N) Deficit</span>
                  </div>
                  <p>
                    Available Nitrogen is at 185 kg/ha against the 280 kg/ha baseline. Biological nitrogen-fixing intercrop (Chickpea or Cowpea) or vermicompost top-dressing advised.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl border border-primary/30 bg-[#DCFCE7]/60 text-xs text-[#166534] space-y-1">
                  <div className="flex items-center gap-2 font-bold">
                    <CheckCircle2 className="h-4 w-4 text-primary" />
                    <span>High Organic Carbon & Clay Retention</span>
                  </div>
                  <p>
                    Soil Organic Carbon (0.82%) provides excellent water retention. Retaining crop residues will sustain this trajectory.
                  </p>
                </div>
              </div>
            </Card>
          </div>

          {/* Component Chemical Bar Grid */}
          <Card className="p-6 space-y-4">
            <CardTitle>ISRIC 250m Soil Chemical Profile</CardTitle>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              {soilComponents.map((comp, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl border border-border bg-surface-soft flex items-center justify-between"
                >
                  <div>
                    <span className="text-xs font-bold text-text-muted block">
                      {comp.name}
                    </span>
                    <span className="text-lg font-extrabold text-text mt-0.5 block">
                      {comp.value} {comp.unit}
                    </span>
                    <span className="text-[11px] text-text-muted/80">
                      Optimal: {comp.range}
                    </span>
                  </div>
                  <StatusPill status={comp.status} size="sm" />
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* TAB 3: AGRO-WEATHER */}
      {activeTab === "weather" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="p-5">
              <span className="text-xs font-bold text-text-muted uppercase">
                Expected Rainfall (7d)
              </span>
              <div className="text-3xl font-extrabold text-primary-dark mt-2">
                39 mm
              </div>
              <p className="text-xs text-text-muted mt-2">
                +14% above 10-year monsoon seasonal average.
              </p>
            </Card>

            <Card className="p-5">
              <span className="text-xs font-bold text-text-muted uppercase">
                Irrigation Requirement
              </span>
              <div className="text-3xl font-extrabold text-[#0EA5E9] mt-2">
                0 mm
              </div>
              <p className="text-xs text-text-muted mt-2">
                Rainfall fully satisfies standing crop evapotranspiration.
              </p>
            </Card>

            <Card className="p-5">
              <span className="text-xs font-bold text-text-muted uppercase">
                Drought Severity Index
              </span>
              <div className="text-3xl font-extrabold text-status-healthy mt-2">
                0.08 (Safe)
              </div>
              <p className="text-xs text-text-muted mt-2">
                Root-zone moisture adequate through next 10 days.
              </p>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
