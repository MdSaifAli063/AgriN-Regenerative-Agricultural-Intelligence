"use client";

import React from "react";
import {
  ShieldAlert,
  Flame,
  CloudRain,
  Thermometer,
  Sprout,
  Send,
  Calendar,
  Layers,
  CheckCircle2,
  ExternalLink,
} from "lucide-react";
import type { GeoJsonOutbreakFeature } from "@krishinet/shared";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusPill } from "@/components/ui/StatusPill";

interface OutbreakClusterDetailProps {
  cluster: GeoJsonOutbreakFeature | null;
  onInitiateBroadcast: (cluster: GeoJsonOutbreakFeature) => void;
  className?: string;
}

export function OutbreakClusterDetail({
  cluster,
  onInitiateBroadcast,
  className,
}: OutbreakClusterDetailProps) {
  if (!cluster) {
    return (
      <Card className="p-8 text-center bg-white border border-border">
        <div className="mx-auto h-12 w-12 rounded-xl bg-surface-soft flex items-center justify-center text-text-muted mb-3">
          <Layers className="h-6 w-6" />
        </div>
        <h3 className="text-base font-bold text-text">No Cluster Selected</h3>
        <p className="text-xs text-text-muted mt-1 max-w-xs mx-auto">
          Click an H3 hexagonal cluster on the map or select a village from the list to inspect epidemiological risk metrics.
        </p>
      </Card>
    );
  }

  const { properties, geometry } = cluster;
  const isCritical = properties.severity === "critical" || properties.severity === "high";

  // Synthesize agro-ecological counter-measures based on disease label
  const getRemedies = (label: string) => {
    switch (label.toLowerCase()) {
      case "rice_blast":
        return {
          primaryOrganic: "Foliar spray of Pseudomonas fluorescens (20g/L) + Neem Seed Kernel Extract (5%)",
          quarantine: "Withhold excess nitrogenous top-dressing; maintain 5cm standing water buffer.",
          weatherHazard: "Relative Humidity > 85%, temperature 24–28°C accelerating blast conidia sporulation.",
        };
      case "soybean_rust":
        return {
          primaryOrganic: "Trichoderma harzianum soil and foliar drench (50g/10L water) at first sign of pustules.",
          quarantine: "Erect 10m barrier perimeter; prohibit inter-farm tractor transit without power wash.",
          weatherHazard: "Prolonged leaf wetness (>6 hrs) with nocturnal dew promotes rapid urediniospore spread.",
        };
      case "wheat_rust_yellow":
        return {
          primaryOrganic: "Bio-priming with Bacillus subtilis broth + fermented cow dung slurry (Jeevamrit 10%).",
          quarantine: "Inspect adjacent fields within 5km wind-vector corridor; destroy rogue alternate hosts.",
          weatherHazard: "Cool temperatures (10–15°C) combined with morning mist accelerate stripe rust expansion.",
        };
      case "cotton_leaf_curl":
        return {
          primaryOrganic: "Yellow sticky traps (25/ha) + Verticillium lecanii entomopathogen against whitefly vector.",
          quarantine: "Uproot and bury severely stunted plants; install sorghum border crop to slow vector drift.",
          weatherHazard: "Warm dry spells trigger exponential whitefly reproduction and trans-field viral hopping.",
        };
      default:
        return {
          primaryOrganic: "Biological foliar bio-fungicide (Trichoderma viride @ 5g/L) paired with 2% neem oil.",
          quarantine: "Maintain sanitary field perimeter; restrict machinery movement until foliage dries.",
          weatherHazard: "Humid micro-climate and dense canopy airflow obstruction amplifying pathogen pressure.",
        };
    }
  };

  const remedies = getRemedies(properties.disease_label);

  return (
    <Card className="p-6 bg-white border border-border shadow-card space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-mono text-xs text-text-muted bg-surface-soft px-2 py-0.5 rounded border border-border">
              H3: {properties.h3_index}
            </span>
            <StatusPill
              status={isCritical ? "risk" : "watch"}
              label={properties.severity.toUpperCase()}
              size="sm"
            />
            {properties.is_spike && (
              <span className="inline-flex items-center gap-1 text-[11px] font-bold text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full animate-pulse">
                <Flame className="h-3 w-3" />
                RAPID SPIKE
              </span>
            )}
          </div>
          <h2 className="text-xl font-extrabold text-primary-dark tracking-tight">
            {properties.disease_name}
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Centroid: {geometry.coordinates[1].toFixed(4)}°N, {geometry.coordinates[0].toFixed(4)}°E • Resolution 6 Hex
          </p>
        </div>

        {/* Quick Broadcast Button */}
        <Button
          variant="primary"
          onClick={() => onInitiateBroadcast(cluster)}
          leftIcon={<Send className="h-4 w-4" />}
          className="shrink-0"
        >
          Draft Broadcast
        </Button>
      </div>

      {/* Epidemiology Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <div className="p-3 bg-surface-soft rounded-xl border border-border">
          <span className="text-[11px] font-bold uppercase text-text-muted block">
            Reported Cases
          </span>
          <span className="text-2xl font-black text-text mt-0.5 block">
            {properties.reported_cases}
          </span>
          <span className="text-[10px] text-text-muted">Validated AI scans in cluster</span>
        </div>

        <div className="p-3 bg-surface-soft rounded-xl border border-border">
          <span className="text-[11px] font-bold uppercase text-text-muted block">
            Estimated Farms at Risk
          </span>
          <span className="text-2xl font-black text-primary-dark mt-0.5 block">
            {properties.reported_cases * 6 + 14}
          </span>
          <span className="text-[10px] text-text-muted">Within 8km dispersal radius</span>
        </div>

        <div className="p-3 bg-surface-soft rounded-xl border border-border col-span-2 sm:col-span-1">
          <span className="text-[11px] font-bold uppercase text-text-muted block">
            Surveillance Window
          </span>
          <div className="flex items-center gap-1.5 text-xs font-semibold text-text mt-2">
            <Calendar className="h-3.5 w-3.5 text-primary" />
            <span>Last 7 Days</span>
          </div>
          <span className="text-[10px] text-emerald-600 font-bold mt-0.5 block">
            Active Outbreak Surveillance
          </span>
        </div>
      </div>

      {/* Micro-Climate Weather Amplifiers */}
      <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/60 space-y-2">
        <div className="flex items-center gap-2 text-xs font-bold text-amber-900 uppercase tracking-wide">
          <Thermometer className="h-4 w-4 text-amber-700" />
          <span>Agro-Meteorological Risk Amplifier</span>
        </div>
        <p className="text-xs text-amber-900 leading-relaxed font-medium">
          {remedies.weatherHazard}
        </p>
      </div>

      {/* Biological & Quarantine Countermeasures */}
      <div className="space-y-3">
        <h4 className="text-xs font-bold uppercase text-text-muted tracking-wider flex items-center gap-1.5">
          <Sprout className="h-4 w-4 text-primary" />
          <span>Recommended Officer Countermeasures</span>
        </h4>

        <div className="p-3.5 rounded-xl border border-primary/30 bg-primary-light/30 space-y-1">
          <span className="text-xs font-bold text-primary-dark block">
            Organic & Bio-Control Remedy:
          </span>
          <p className="text-xs text-text leading-relaxed">
            {remedies.primaryOrganic}
          </p>
        </div>

        <div className="p-3.5 rounded-xl border border-border bg-surface-soft space-y-1">
          <span className="text-xs font-bold text-text-muted block">
            Containment & Farm Hygiene:
          </span>
          <p className="text-xs text-text leading-relaxed">
            {remedies.quarantine}
          </p>
        </div>
      </div>
    </Card>
  );
}
