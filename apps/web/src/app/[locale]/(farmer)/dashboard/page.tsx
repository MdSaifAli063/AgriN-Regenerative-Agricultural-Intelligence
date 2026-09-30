"use client";

import React, { useState } from "react";
import Link from "next/navigation";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sprout,
  Droplets,
  CloudRain,
  Flame,
  Camera,
  Calendar,
  Layers,
  ChevronRight,
  Sun,
  Cloud,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
} from "lucide-react";
import { ActionCard } from "@/components/ui/ActionCard";
import { MetricTile } from "@/components/ui/MetricTile";
import { StatusPill } from "@/components/ui/StatusPill";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { CardSkeleton, MetricSkeleton } from "@/components/ui/Skeletons";
import { ErrorState } from "@/components/ui/ErrorState";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { apiClient } from "@/lib/api/client";
import { cn, formatDateTime } from "@/lib/utils";
import type { AdvisoryResponse, FieldSummary } from "@krishinet/shared";

export default function FarmerDashboardPage() {
  const params = useParams();
  const router = useRouter();
  const locale = (params?.locale as string) || "en";
  const queryClient = useQueryClient();

  const [selectedFieldId, setSelectedFieldId] = useState<string>("fld-001");

  // 1. Fetch Farmer Fields
  const {
    data: fields,
    isLoading: fieldsLoading,
    error: fieldsError,
  } = useQuery<FieldSummary[]>({
    queryKey: ["farmer-fields"],
    queryFn: () => apiClient<FieldSummary[]>("fields"),
  });

  // 2. Fetch Latest Advisory
  const {
    data: advisory,
    isLoading: advisoryLoading,
    error: advisoryError,
    refetch: refetchAdvisory,
    isFetching: isRefreshingAdvisory,
  } = useQuery<AdvisoryResponse>({
    queryKey: ["advisory-current", selectedFieldId],
    queryFn: () => apiClient<AdvisoryResponse>("advisories/current"),
  });

  // 3. Action Done Toggle Mutation (Optimistic)
  const toggleActionMutation = useMutation({
    mutationFn: async ({ actionId, isDone }: { actionId: string; isDone: boolean }) => {
      // In real backend: PATCH /advisories/{id}/actions/{actionId}
      return { success: true, actionId, isDone };
    },
    onMutate: async ({ actionId, isDone }) => {
      await queryClient.cancelQueries({ queryKey: ["advisory-current", selectedFieldId] });
      const previous = queryClient.getQueryData<AdvisoryResponse>([
        "advisory-current",
        selectedFieldId,
      ]);

      if (previous) {
        queryClient.setQueryData<AdvisoryResponse>(
          ["advisory-current", selectedFieldId],
          {
            ...previous,
            timeline_30d: previous.timeline_30d.map((item) =>
              item.id === actionId ? { ...item, is_completed: isDone } : item
            ),
          }
        );
      }
      return { previous };
    },
  });

  const activeField =
    fields?.find((f) => f.id === selectedFieldId) || fields?.[0];

  // Weather 7-Day Forecast mock items
  const weatherStrip = [
    { day: "Today", temp: "31° / 22°", rain: "0 mm", icon: Sun, spray: "Ideal" },
    { day: "Thu", temp: "30° / 23°", rain: "2 mm", icon: Cloud, spray: "Good" },
    { day: "Fri", temp: "28° / 21°", rain: "14 mm", icon: CloudRain, spray: "Risk (Rain)" },
    { day: "Sat", temp: "27° / 20°", rain: "18 mm", icon: CloudRain, spray: "Do Not Spray" },
    { day: "Sun", temp: "29° / 21°", rain: "5 mm", icon: Cloud, spray: "Moderate" },
    { day: "Mon", temp: "32° / 22°", rain: "0 mm", icon: Sun, spray: "Ideal" },
    { day: "Tue", temp: "33° / 23°", rain: "0 mm", icon: Sun, spray: "Ideal" },
  ];

  if (fieldsLoading || advisoryLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        <CardSkeleton />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <MetricSkeleton />
          <MetricSkeleton />
          <MetricSkeleton />
          <MetricSkeleton />
        </div>
      </div>
    );
  }

  if (advisoryError || fieldsError) {
    const err = (advisoryError || fieldsError) as any;
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <ErrorState
          error={err}
          onRetry={() => {
            queryClient.invalidateQueries({ queryKey: ["farmer-fields"] });
            refetchAdvisory();
          }}
        />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      {/* Field Selector & Health Status Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-primary-dark tracking-tight">
              {activeField?.name || "Main Field"}
            </h1>
            <StatusPill
              status={activeField?.health_status || "healthy"}
              label={
                activeField?.health_status === "healthy"
                  ? "Optimal Growth"
                  : activeField?.health_status === "watch"
                  ? "Watch Needed"
                  : "Outbreak Risk"
              }
            />
          </div>
          <p className="text-xs text-text-muted mt-1">
            Standing Crop: <strong>{activeField?.crop_type || "Cotton"}</strong> • Area: {activeField?.area_ha || 1.85} ha
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => refetchAdvisory()}
            isLoading={isRefreshingAdvisory}
            leftIcon={<RotateCw className="h-4 w-4" />}
          >
            Refresh Advisory
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => router.push(`/${locale}/scan`)}
            leftIcon={<Camera className="h-4 w-4" />}
          >
            Scan a Leaf
          </Button>
        </div>
      </div>

      {/* Hero Action Card: "What Should I Do Today?" */}
      {advisory?.what_to_do_today && (
        <ActionCard
          actionData={advisory.what_to_do_today}
          onActionToggle={(idx, done) => {
            // Local optimistic handled inside ActionCard
          }}
        />
      )}

      {/* 4 Metric Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricTile
          title="Vegetation Index (NDVI)"
          value="0.72"
          status="healthy"
          statusLabel="High Canopy"
          trend="up"
          trendLabel="+4% this week"
          icon={<Sprout className="h-5 w-5" />}
        />
        <MetricTile
          title="Soil Health Score"
          value="84"
          unit="/ 100"
          status="healthy"
          statusLabel="Optimal SOC"
          icon={<Droplets className="h-5 w-5" />}
        />
        <MetricTile
          title="Rain Next 7 Days"
          value="39"
          unit="mm"
          status="watch"
          statusLabel="Spore risk"
          trend="up"
          trendLabel="Monitor blight"
          icon={<CloudRain className="h-5 w-5" />}
        />
        <MetricTile
          title="Heat Stress Index"
          value="31°C"
          status="healthy"
          statusLabel="Optimal temp"
          icon={<Flame className="h-5 w-5" />}
        />
      </div>

      {/* 7-Day Weather Forecast & Spray Window Strip */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-border flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <CloudRain className="h-5 w-5 text-primary" />
            <h3 className="font-bold text-lg text-primary-dark">
              7-Day Agro-Weather & Spray Windows
            </h3>
          </div>
          {advisory?.provenance && (
            <ProvenanceBadge provenance={advisory.provenance} size="sm" />
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2.5 pt-2">
          {weatherStrip.map((item, idx) => {
            const Icon = item.icon;
            const isFavorable = item.spray.includes("Ideal") || item.spray.includes("Good");

            return (
              <div
                key={idx}
                className={cn(
                  "p-3 rounded-xl border flex flex-col items-center text-center space-y-1.5 transition-colors",
                  idx === 0
                    ? "bg-primary-light/40 border-primary shadow-sm"
                    : "bg-surface-soft border-border"
                )}
              >
                <span className="text-xs font-bold text-text-muted">{item.day}</span>
                <Icon className="h-6 w-6 text-primary my-0.5" />
                <span className="text-xs font-bold text-text">{item.temp}</span>
                <span className="text-[11px] text-text-muted">{item.rain}</span>
                <span
                  className={cn(
                    "text-[10px] font-bold px-1.5 py-0.5 rounded-full select-none mt-1",
                    isFavorable
                      ? "bg-[#DCFCE7] text-[#166534]"
                      : "bg-[#FEE2E2] text-status-risk"
                  )}
                >
                  {item.spray}
                </span>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Next 3 Upcoming Actions with Done Toggle */}
      {advisory?.timeline_30d && advisory.timeline_30d.length > 0 && (
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-primary" />
              <h3 className="font-bold text-lg text-primary-dark">
                Upcoming Regenerative Field Schedule
              </h3>
            </div>
            <button
              type="button"
              onClick={() => router.push(`/${locale}/advisory`)}
              className="text-xs font-bold text-primary hover:text-primary-dark inline-flex items-center gap-1"
            >
              <span>Full 30-Day Plan</span>
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-3 pt-2">
            {advisory.timeline_30d.slice(0, 3).map((item) => (
              <div
                key={item.id}
                onClick={() =>
                  toggleActionMutation.mutate({
                    actionId: item.id,
                    isDone: !item.is_completed,
                  })
                }
                className={cn(
                  "flex items-start gap-3.5 p-4 rounded-xl border transition-all cursor-pointer select-none",
                  item.is_completed
                    ? "bg-surface-soft/60 border-border text-text-muted line-through"
                    : "bg-white border-border hover:border-primary shadow-sm text-text"
                )}
              >
                <div
                  className={cn(
                    "mt-0.5 h-6 w-6 rounded-md border flex items-center justify-center flex-shrink-0 transition-colors",
                    item.is_completed
                      ? "bg-primary border-primary text-white"
                      : "border-border bg-surface-soft"
                  )}
                >
                  {item.is_completed && <CheckCircle2 className="h-4 w-4" />}
                </div>

                <div className="flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-primary uppercase">
                      Day +{item.day_offset} • {item.category}
                    </span>
                    {item.urgency === "urgent" && !item.is_completed && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#FEE2E2] text-status-risk uppercase">
                        Urgent
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-medium mt-1">{item.action_text}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Quick Action Navigation Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
        <button
          type="button"
          onClick={() => router.push(`/${locale}/scan`)}
          className="p-5 rounded-card border border-border bg-white shadow-card hover:border-primary hover:shadow-card-hover transition-all text-left group"
        >
          <div className="h-10 w-10 rounded-btn bg-primary-light flex items-center justify-center text-primary-dark mb-3 group-hover:scale-105 transition-transform">
            <Camera className="h-5 w-5 text-primary" />
          </div>
          <h4 className="text-base font-bold text-primary-dark">Diagnose Disease</h4>
          <p className="text-xs text-text-muted mt-1">
            Offline on-device AI + Gemini Vision leaf analysis
          </p>
        </button>

        <button
          type="button"
          onClick={() => router.push(`/${locale}/advisory`)}
          className="p-5 rounded-card border border-border bg-white shadow-card hover:border-primary hover:shadow-card-hover transition-all text-left group"
        >
          <div className="h-10 w-10 rounded-btn bg-primary-light flex items-center justify-center text-primary-dark mb-3 group-hover:scale-105 transition-transform">
            <Sprout className="h-5 w-5 text-primary" />
          </div>
          <h4 className="text-base font-bold text-primary-dark">Full Advisory Plan</h4>
          <p className="text-xs text-text-muted mt-1">
            Crop suitability, regenerative practices & organic nutrition
          </p>
        </button>

        <button
          type="button"
          onClick={() => router.push(`/${locale}/fields`)}
          className="p-5 rounded-card border border-border bg-white shadow-card hover:border-primary hover:shadow-card-hover transition-all text-left group"
        >
          <div className="h-10 w-10 rounded-btn bg-primary-light flex items-center justify-center text-primary-dark mb-3 group-hover:scale-105 transition-transform">
            <Layers className="h-5 w-5 text-primary" />
          </div>
          <h4 className="text-base font-bold text-primary-dark">My Fields & Soil</h4>
          <p className="text-xs text-text-muted mt-1">
            Satellite timeseries, soil health cards & boundaries
          </p>
        </button>
      </div>
    </div>
  );
}
