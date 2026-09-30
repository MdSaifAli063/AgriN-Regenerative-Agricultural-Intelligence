"use client";

import React, { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Layers,
  Plus,
  MapPin,
  Sprout,
  Droplets,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { StatusPill } from "@/components/ui/StatusPill";
import { CardSkeleton } from "@/components/ui/Skeletons";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { apiClient } from "@/lib/api/client";
import { formatDateTime } from "@/lib/utils";
import type { FieldSummary } from "@krishinet/shared";

export default function MyFieldsPage() {
  const router = useRouter();
  const params = useParams();
  const locale = (params?.locale as string) || "en";

  const {
    data: fields,
    isLoading,
    error,
    refetch,
  } = useQuery<FieldSummary[]>({
    queryKey: ["farmer-fields"],
    queryFn: () => apiClient<FieldSummary[]>("fields"),
  });

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-4">
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
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-border">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-primary-dark tracking-tight">
            My Registered Fields
          </h1>
          <p className="text-sm text-text-muted mt-1">
            Spatial parcels tracked via Copernicus Sentinel-2 STAC and local soil grids.
          </p>
        </div>

        <Button
          variant="primary"
          onClick={() => router.push(`/${locale}/onboarding`)}
          leftIcon={<Plus className="h-5 w-5" />}
        >
          Add New Field
        </Button>
      </div>

      {/* Fields List */}
      {fields && fields.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {fields.map((field) => (
            <Card
              key={field.id}
              className="p-6 flex flex-col justify-between hover:border-primary transition-all hover:shadow-card-hover group"
            >
              <div className="space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-xl font-bold text-primary-dark group-hover:text-primary transition-colors">
                      {field.name}
                    </h3>
                    <div className="flex items-center gap-1.5 text-xs text-text-muted mt-1">
                      <MapPin className="h-3.5 w-3.5 text-primary" />
                      <span>
                        {field.centroid_lat.toFixed(4)}, {field.centroid_lon.toFixed(4)}
                      </span>
                    </div>
                  </div>

                  <StatusPill status={field.health_status} size="sm" />
                </div>

                {/* Key Metrics */}
                <div className="grid grid-cols-3 gap-2 p-3 rounded-xl bg-surface-soft border border-border text-center">
                  <div>
                    <span className="text-[11px] text-text-muted block">Area</span>
                    <span className="text-sm font-extrabold text-text">
                      {field.area_ha} ha
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-text-muted block">Crop</span>
                    <span className="text-sm font-extrabold text-primary-dark">
                      {field.crop_type}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-text-muted block">NDVI</span>
                    <span className="text-sm font-extrabold text-primary">
                      {field.latest_ndvi ?? 0.72}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <div className="pt-4 border-t border-border mt-4 flex items-center justify-between">
                <span className="text-xs text-text-muted">
                  Indexed: {formatDateTime(field.created_at)}
                </span>

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    router.push(`/${locale}/fields/${field.id}/intelligence`)
                  }
                  rightIcon={<ChevronRight className="h-4 w-4" />}
                >
                  View Intelligence
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No Fields Registered"
          description="Register your first field in under 60 seconds with GPS or map boundary."
          actionLabel="Register Farm & Field"
          onAction={() => router.push(`/${locale}/onboarding`)}
        />
      )}
    </div>
  );
}
