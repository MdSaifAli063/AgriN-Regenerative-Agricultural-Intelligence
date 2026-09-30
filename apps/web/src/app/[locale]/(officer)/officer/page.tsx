"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useParams } from "next/navigation";
import {
  ShieldAlert,
  Users,
  Radio,
  Filter,
  Search,
  Flame,
  Layers,
  MapPin,
  RefreshCw,
  Send,
  AlertTriangle,
  Building,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { MetricTile } from "@/components/ui/MetricTile";
import { StatusPill } from "@/components/ui/StatusPill";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { OutbreakMapCanvas } from "@/components/officer/OutbreakMapCanvas";
import { OutbreakClusterDetail } from "@/components/officer/OutbreakClusterDetail";
import { BroadcastTool } from "@/components/officer/BroadcastTool";
import { apiClient } from "@/lib/api/client";
import { fetchOutbreakClusters } from "@/lib/adapters/brics-policy";
import { useAuthStore } from "@/lib/auth/store";
import type { GeoJsonOutbreakFeature, Provenance } from "@krishinet/shared";
import { cn } from "@/lib/utils";

export default function ExtensionOfficerDashboardPage() {
  const params = useParams();
  const locale = (params?.locale as string) || "en";
  const { user, role } = useAuthStore();

  const [clusters, setClusters] = useState<GeoJsonOutbreakFeature[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<GeoJsonOutbreakFeature | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [provenance, setProvenance] = useState<Provenance>({
    source: "FastAPI /v1/disease/outbreak/feed",
    mode: "live",
    fetched_at: new Date().toISOString(),
    ttl: 300,
    confidence: 0.94,
    notes: "H3 privacy-coarsened epidemiological clusters",
  });

  // Filter States
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [spikesOnly, setSpikesOnly] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeTab, setActiveTab] = useState<"surveillance" | "broadcast">("surveillance");

  // Load outbreak data from API with adapter fallback
  const loadOutbreaks = async () => {
    setIsLoading(true);
    try {
      const res = await apiClient<{ type: string; features: GeoJsonOutbreakFeature[] }>(
        "disease/outbreak/feed?country_iso=IND&since_days=30",
        { timeoutMs: 4000 }
      );
      if (res && res.features && res.features.length > 0) {
        setClusters(res.features);
        setSelectedCluster(res.features[0]);
        setProvenance({
          source: "FastAPI /v1/disease/outbreak/feed",
          mode: "live",
          fetched_at: new Date().toISOString(),
          ttl: 300,
          confidence: 0.96,
        });
      } else {
        throw new Error("Empty feed");
      }
    } catch {
      // Graceful fallback to Phase 7 / Demo adapter
      const mockFeatures = await fetchOutbreakClusters();
      setClusters(mockFeatures);
      setSelectedCluster(mockFeatures[0]);
      setProvenance({
        source: "KrishiNet Outbreak Adapter (Offline / Demo Fallback)",
        mode: "demo",
        fetched_at: new Date().toISOString(),
        ttl: 600,
        confidence: 0.92,
        notes: "Differential privacy k=5 synthetic simulation",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadOutbreaks();
  }, []);

  // Filtered clusters
  const filteredClusters = useMemo(() => {
    return clusters.filter((feat) => {
      const p = feat.properties;
      if (severityFilter !== "all" && p.severity.toLowerCase() !== severityFilter) {
        return false;
      }
      if (spikesOnly && !p.is_spike) {
        return false;
      }
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const matchDisease = p.disease_name.toLowerCase().includes(term);
        const matchHex = p.h3_index.toLowerCase().includes(term);
        if (!matchDisease && !matchHex) return false;
      }
      return true;
    });
  }, [clusters, severityFilter, spikesOnly, searchTerm]);

  // Aggregate Metrics
  const totalCases = clusters.reduce((acc, c) => acc + c.properties.reported_cases, 0);
  const criticalCount = clusters.filter(
    (c) => c.properties.severity === "critical" || c.properties.severity === "high"
  ).length;
  const spikeCount = clusters.filter((c) => c.properties.is_spike).length;

  const handleInitiateBroadcast = (cluster: GeoJsonOutbreakFeature) => {
    setSelectedCluster(cluster);
    setActiveTab("broadcast");
  };

  return (
    <div className="min-h-screen bg-surface-soft pb-16">
      {/* Top Officer Command Header */}
      <div className="bg-white border-b border-border shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-extrabold uppercase tracking-wider text-primary bg-primary-light px-2.5 py-0.5 rounded-full">
                  District Command Center
                </span>
                <ProvenanceBadge provenance={provenance} size="sm" />
              </div>
              <h1 className="text-2xl sm:text-3xl font-black text-primary-dark tracking-tight">
                Extension Officer Outbreak & Advisory Portal
              </h1>
              <p className="text-xs sm:text-sm text-text-muted mt-0.5">
                Wardha Agricultural Block, Maharashtra (Node IND) • 420 Registered Smallholders
              </p>
            </div>

            {/* Quick Action Tabs */}
            <div className="flex items-center gap-2">
              <div className="bg-surface-soft p-1 rounded-xl border border-border flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setActiveTab("surveillance")}
                  className={cn(
                    "px-3.5 py-2 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5",
                    activeTab === "surveillance"
                      ? "bg-white text-primary-dark shadow-sm"
                      : "text-text-muted hover:text-text"
                  )}
                >
                  <Layers className="h-4 w-4" />
                  Surveillance GIS
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("broadcast")}
                  className={cn(
                    "px-3.5 py-2 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5",
                    activeTab === "broadcast"
                      ? "bg-white text-primary-dark shadow-sm"
                      : "text-text-muted hover:text-text"
                  )}
                >
                  <Send className="h-4 w-4" />
                  Mass Broadcast
                </button>
              </div>

              <Button
                variant="secondary"
                size="sm"
                onClick={loadOutbreaks}
                isLoading={isLoading}
                leftIcon={<RefreshCw className="h-4 w-4" />}
                className="shrink-0"
              >
                Refresh Feed
              </Button>
            </div>
          </div>

          {/* Metric Tiles Row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
            <MetricTile
              title="Active Outbreak Clusters"
              value={clusters.length}
              subtitle="H3 Resolution 6 Hexagons"
              trend={clusters.length > 5 ? "up" : "neutral"}
              icon={<ShieldAlert className="h-5 w-5" />}
            />
            <MetricTile
              title="High / Critical Risks"
              value={criticalCount}
              subtitle="Requiring Field Investigation"
              status={criticalCount > 0 ? "risk" : "healthy"}
              icon={<AlertTriangle className="h-5 w-5 text-red-600" />}
            />
            <MetricTile
              title="Rapid Spreading Spikes"
              value={spikeCount}
              subtitle="Velocity > 20% week-on-week"
              status={spikeCount > 0 ? "watch" : "healthy"}
              icon={<Flame className="h-5 w-5 text-orange-600" />}
            />
            <MetricTile
              title="Validated Cases"
              value={totalCases}
              subtitle="Farmer Edge Scans"
              status="healthy"
              icon={<Users className="h-5 w-5" />}
            />
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-6 space-y-6">
        {activeTab === "surveillance" ? (
          <div className="space-y-6">
            {/* Filter Bar */}
            <div className="bg-white p-4 rounded-xl border border-border shadow-xs flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-bold uppercase text-text-muted flex items-center gap-1">
                  <Filter className="h-3.5 w-3.5" />
                  <span>Severity:</span>
                </span>
                {(["all", "critical", "high", "medium"] as const).map((sev) => (
                  <button
                    key={sev}
                    type="button"
                    onClick={() => setSeverityFilter(sev)}
                    className={cn(
                      "px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors capitalize",
                      severityFilter === sev
                        ? "bg-primary text-white border-primary"
                        : "bg-surface-soft text-text border-border hover:bg-slate-100"
                    )}
                  >
                    {sev}
                  </button>
                ))}

                {/* Spikes Only Toggle */}
                <button
                  type="button"
                  onClick={() => setSpikesOnly(!spikesOnly)}
                  className={cn(
                    "ml-2 px-3 py-1.5 text-xs font-bold rounded-lg border flex items-center gap-1.5 transition-colors",
                    spikesOnly
                      ? "bg-red-600 text-white border-red-600 shadow-xs"
                      : "bg-surface-soft text-text-muted border-border hover:text-text"
                  )}
                >
                  <Flame className="h-3.5 w-3.5" />
                  Spikes Only
                </button>
              </div>

              {/* Search Bar */}
              <div className="relative w-full sm:w-64">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-text-muted" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search disease or H3 index..."
                  className="w-full pl-9 pr-4 py-1.5 text-xs bg-surface-soft border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            {/* Master-Detail 2-Column Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Interactive Map & Master List (7 cols) */}
              <div className="lg:col-span-7 space-y-6">
                {/* Outbreak Map Canvas */}
                <OutbreakMapCanvas
                  features={filteredClusters}
                  selectedClusterId={selectedCluster?.properties.h3_index || null}
                  onSelectCluster={(feat) => setSelectedCluster(feat)}
                />

                {/* Master Cluster List */}
                <Card className="p-4 bg-white border border-border shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-bold text-text">
                      Outbreak Cluster Registry ({filteredClusters.length})
                    </CardTitle>
                    <span className="text-[11px] text-text-muted">Click row to inspect</span>
                  </div>

                  <div className="divide-y divide-border/60 max-h-72 overflow-y-auto">
                    {filteredClusters.map((feat) => {
                      const isSelected = selectedCluster?.properties.h3_index === feat.properties.h3_index;
                      const isCritical = feat.properties.severity === "critical" || feat.properties.severity === "high";

                      return (
                        <div
                          key={feat.properties.h3_index}
                          onClick={() => setSelectedCluster(feat)}
                          className={cn(
                            "py-3 px-3 rounded-lg flex items-center justify-between gap-4 cursor-pointer transition-colors text-xs",
                            isSelected
                              ? "bg-primary-light/40 border border-primary/30"
                              : "hover:bg-surface-soft"
                          )}
                        >
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-text">{feat.properties.disease_name}</span>
                              {feat.properties.is_spike && (
                                <span className="text-[10px] font-bold text-red-600 bg-red-50 px-1.5 py-0.5 rounded flex items-center gap-0.5">
                                  <Flame className="h-2.5 w-2.5" />
                                  SPIKE
                                </span>
                              )}
                            </div>
                            <span className="font-mono text-[11px] text-text-muted block">
                              H3: {feat.properties.h3_index}
                            </span>
                          </div>

                          <div className="flex items-center gap-3 shrink-0">
                            <div className="text-right">
                              <span className="font-bold text-text block">
                                {feat.properties.reported_cases} cases
                              </span>
                              <span className="text-[10px] text-text-muted">Validated AI scans</span>
                            </div>
                            <StatusPill
                              status={isCritical ? "risk" : "watch"}
                              label={feat.properties.severity.toUpperCase()}
                              size="sm"
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              </div>

              {/* Right Column: Detailed Epidemiology & Actions (5 cols) */}
              <div className="lg:col-span-5 space-y-6">
                <OutbreakClusterDetail
                  cluster={selectedCluster}
                  onInitiateBroadcast={handleInitiateBroadcast}
                />
              </div>
            </div>
          </div>
        ) : (
          /* Mass Broadcast View */
          <div className="max-w-4xl mx-auto">
            <BroadcastTool initialCluster={selectedCluster} />
          </div>
        )}
      </div>
    </div>
  );
}
