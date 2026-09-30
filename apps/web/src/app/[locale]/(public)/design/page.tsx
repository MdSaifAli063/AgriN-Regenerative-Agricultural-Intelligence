"use client";

import React, { useState } from "react";
import {
  Sprout,
  Droplets,
  CloudRain,
  Flame,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Calendar,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { IconButton } from "@/components/ui/IconButton";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { StatusPill } from "@/components/ui/StatusPill";
import { MetricTile } from "@/components/ui/MetricTile";
import { ActionCard } from "@/components/ui/ActionCard";
import { AdvisoryCard } from "@/components/ui/AdvisoryCard";
import { ConfidenceMeter } from "@/components/ui/ConfidenceMeter";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { MapLegend } from "@/components/ui/MapLegend";
import { VoiceButton } from "@/components/ui/VoiceButton";
import { SyncStatusChip } from "@/components/ui/SyncStatusChip";
import { Stepper } from "@/components/ui/Stepper";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { CardSkeleton, MetricSkeleton } from "@/components/ui/Skeletons";
import { DataTable } from "@/components/ui/DataTable";
import { ChartCard } from "@/components/ui/ChartCard";
import { Timeline } from "@/components/ui/Timeline";
import { DisclaimerFooter } from "@/components/common/DisclaimerFooter";
import { DemoRibbon } from "@/components/common/DemoRibbon";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import { AccessibilityBar } from "@/components/common/AccessibilityBar";

export default function DesignSystemPage() {
  const [activeStep, setActiveStep] = useState(1);
  const [voiceResult, setVoiceResult] = useState("");

  const demoAction = {
    headline: "Apply Neem Biopesticide Before Morning Dew Clears",
    summary:
      "High relative humidity (84%) combined with daytime warmth has created conditions for fungal spore germination. Organic foliar spray is recommended.",
    urgency: "urgent" as const,
    recommended_actions: [
      "Mix 5ml neem oil with 1 litre of water and organic soap surfactant",
      "Spray undersides of leaves where early lesions concentrate",
      "Avoid spraying during peak noon heat to prevent foliar scorching",
    ],
    read_aloud_text:
      "Action for today: Apply neem biopesticide before morning dew clears to stop fungal germination.",
  };

  const demoTimeline = [
    {
      id: "act-1",
      day_offset: 1,
      date_iso: new Date().toISOString(),
      action_text: "Foliar application of bio-fungicide in low-wind conditions",
      category: "pest_scouting" as const,
      is_completed: true,
      urgency: "urgent" as const,
    },
    {
      id: "act-2",
      day_offset: 3,
      date_iso: new Date().toISOString(),
      action_text: "Drip irrigation run: 22mm based on soil moisture deficit",
      category: "irrigation" as const,
      is_completed: false,
      urgency: "normal" as const,
    },
    {
      id: "act-3",
      day_offset: 7,
      date_iso: new Date().toISOString(),
      action_text: "Apply vermicompost top-dress around root zone (100 kg/ha)",
      category: "fertilisation" as const,
      is_completed: false,
      urgency: "flexible" as const,
    },
  ];

  const demoTableData = [
    { id: "FLD-101", field_name: "North Orchard", crop: "Mango", ndvi: 0.74, status: "Healthy" },
    { id: "FLD-102", field_name: "Lower Terrace", crop: "Wheat", ndvi: 0.42, status: "Watch" },
    { id: "FLD-103", field_name: "Canal Field", crop: "Rice", ndvi: 0.28, status: "Risk Alert" },
  ];

  const demoColumns = [
    { key: "id", header: "Field ID", sortable: true },
    { key: "field_name", header: "Field Name", sortable: true },
    { key: "crop", header: "Crop", sortable: true },
    { key: "ndvi", header: "NDVI", sortable: true },
    {
      key: "status",
      header: "Status",
      render: (item: any) => (
        <StatusPill
          status={item.status === "Healthy" ? "healthy" : item.status === "Watch" ? "watch" : "risk"}
          label={item.status}
          size="sm"
        />
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-background text-text flex flex-col">
      <DemoRibbon nodeCountry="IND" />

      {/* Header bar */}
      <header className="border-b border-border bg-white sticky top-0 z-30 px-6 py-4 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center text-white font-bold">
              K
            </div>
            <h1 className="text-xl font-extrabold text-primary-dark tracking-tight">
              KrishiNet-BRICS
            </h1>
          </div>
          <p className="text-xs text-text-muted mt-0.5">
            Strict Green & White Living Style Guide
          </p>
        </div>

        <div className="flex items-center gap-3">
          <AccessibilityBar />
          <LanguageSwitcher currentLocale="en" />
          <SyncStatusChip state="online" />
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10 space-y-14 flex-1 w-full">
        {/* Intro */}
        <section className="space-y-3">
          <h2 className="text-3xl font-extrabold text-primary-dark">
            Green & White Design System
          </h2>
          <p className="text-base text-text-muted max-w-2xl leading-relaxed">
            Clean, airy, trustworthy design for low-literacy smallholders and policy command centers. Monochromatic green identity with semantic-only status indicators.
          </p>
        </section>

        {/* 1. Color Palette Tokens */}
        <section className="space-y-5">
          <h3 className="text-xl font-bold text-primary-dark border-b border-border pb-2">
            1. Brand & Semantic Color Tokens
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            <div className="p-3 rounded-card bg-primary text-white space-y-1 shadow-sm">
              <div className="font-bold text-sm">--primary</div>
              <div className="text-xs opacity-90">#16A34A</div>
              <div className="text-[11px] opacity-75">Brand Solid</div>
            </div>
            <div className="p-3 rounded-card bg-primary-dark text-white space-y-1 shadow-sm">
              <div className="font-bold text-sm">--primary-dark</div>
              <div className="text-xs opacity-90">#166534</div>
              <div className="text-[11px] opacity-75">Headings & Hover</div>
            </div>
            <div className="p-3 rounded-card bg-primary-deep text-white space-y-1 shadow-sm">
              <div className="font-bold text-sm">--primary-deep</div>
              <div className="text-xs opacity-90">#14532D</div>
              <div className="text-[11px] opacity-75">Officer Chrome</div>
            </div>
            <div className="p-3 rounded-card bg-primary-light text-primary-dark border border-border space-y-1">
              <div className="font-bold text-sm">--primary-light</div>
              <div className="text-xs opacity-80">#DCFCE7</div>
              <div className="text-[11px] opacity-70">Hero Tints</div>
            </div>
            <div className="p-3 rounded-card bg-surface-soft text-text border border-border space-y-1">
              <div className="font-bold text-sm">--surface-soft</div>
              <div className="text-xs text-text-muted">#F4FAF5</div>
              <div className="text-[11px] text-text-muted">Card Background</div>
            </div>
            <div className="p-3 rounded-card bg-white text-text border border-border space-y-1">
              <div className="font-bold text-sm">--border</div>
              <div className="text-xs text-text-muted">#DCEBDD</div>
              <div className="text-[11px] text-text-muted">1px Dividers</div>
            </div>
          </div>

          <div className="pt-2">
            <h4 className="text-sm font-bold text-text-muted mb-2">
              Semantic Status Only (Non-brand)
            </h4>
            <div className="flex flex-wrap gap-3">
              <StatusPill status="healthy" label="Healthy Crop (92%)" />
              <StatusPill status="watch" label="Watch Alert (Mild Deficit)" />
              <StatusPill status="risk" label="Critical Pest Outbreak" />
              <StatusPill status="info" label="Satellite Pass in 4h" />
            </div>
          </div>
        </section>

        {/* 2. Interactive Buttons */}
        <section className="space-y-4">
          <h3 className="text-xl font-bold text-primary-dark border-b border-border pb-2">
            2. Button System (Min 48px Target)
          </h3>
          <div className="flex flex-wrap gap-4 items-center">
            <Button variant="primary" leftIcon={<Sprout className="h-5 w-5" />}>
              Primary Green Button
            </Button>
            <Button variant="secondary">Secondary White Button</Button>
            <Button variant="outline">Outline Button</Button>
            <Button variant="ghost">Ghost Button</Button>
            <Button variant="danger">Escalation Danger</Button>
            <Button isLoading>Processing...</Button>
            <IconButton
              icon={<Calendar className="h-5 w-5 text-primary" />}
              aria-label="View Calendar"
            />
          </div>
        </section>

        {/* 3. Hero Action Card */}
        <section className="space-y-4">
          <h3 className="text-xl font-bold text-primary-dark border-b border-border pb-2">
            3. Hero Action Card ("What Should I Do Today?")
          </h3>
          <ActionCard actionData={demoAction} />
        </section>

        {/* 4. Metric Tiles */}
        <section className="space-y-4">
          <h3 className="text-xl font-bold text-primary-dark border-b border-border pb-2">
            4. Metric Tiles & Provenance Badges
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricTile
              title="Vegetation Index (NDVI)"
              value="0.78"
              status="healthy"
              statusLabel="Peak Vigour"
              trend="up"
              trendLabel="+6% vs 30d"
              icon={<Sprout className="h-5 w-5" />}
            />
            <MetricTile
              title="Soil Health Score"
              value="82"
              unit="/ 100"
              status="healthy"
              statusLabel="High SOC"
              icon={<Droplets className="h-5 w-5" />}
            />
            <MetricTile
              title="Rain Expected (7d)"
              value="34"
              unit="mm"
              status="watch"
              statusLabel="High Humidity"
              trend="up"
              trendLabel="Scouting needed"
              icon={<CloudRain className="h-5 w-5" />}
            />
            <MetricTile
              title="Heat Stress Index"
              value="28°C"
              status="healthy"
              statusLabel="Optimal Temp"
              icon={<Flame className="h-5 w-5" />}
            />
          </div>

          <div className="flex items-center gap-4 pt-2">
            <span className="text-sm font-semibold text-text-muted">Provenance Badges:</span>
            <ProvenanceBadge
              provenance={{
                source: "Copernicus Sentinel-2 L2A",
                mode: "live",
                fetched_at: new Date().toISOString(),
                ttl: 3600,
                confidence: 0.94,
              }}
            />
            <ProvenanceBadge
              provenance={{
                source: "ISRIC SoilGrids v2.0",
                mode: "cache",
                fetched_at: new Date(Date.now() - 86400000).toISOString(),
                ttl: 86400,
                confidence: 0.88,
              }}
            />
            <ProvenanceBadge
              provenance={{
                source: "Synthetic Outbreak Aggregator",
                mode: "demo",
                fetched_at: new Date().toISOString(),
                ttl: 300,
                confidence: 0.75,
              }}
            />
          </div>
        </section>

        {/* 5. Diagnostic Confidence & Escalation */}
        <section className="space-y-4">
          <h3 className="text-xl font-bold text-primary-dark border-b border-border pb-2">
            5. Confidence Meter & Escalation Banners
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="p-5">
              <ConfidenceMeter score={0.88} level="high" />
            </Card>
            <Card className="p-5">
              <ConfidenceMeter score={0.62} level="medium" />
            </Card>
            <Card className="p-5">
              <ConfidenceMeter
                score={0.34}
                level="low"
                onContactOfficer={() => alert("Connecting to extension agent hotline...")}
              />
            </Card>
          </div>
        </section>

        {/* 6. Stepper & Onboarding */}
        <section className="space-y-4">
          <h3 className="text-xl font-bold text-primary-dark border-b border-border pb-2">
            6. Onboarding Stepper (4 Steps Max)
          </h3>
          <Card className="p-6">
            <Stepper
              steps={[
                { id: 1, label: "Language" },
                { id: 2, label: "GPS & Field" },
                { id: 3, label: "Crop & Irrigation" },
                { id: 4, label: "Consents" },
              ]}
              currentStep={activeStep}
              onStepClick={setActiveStep}
            />
            <div className="mt-6 flex justify-between">
              <Button
                variant="secondary"
                disabled={activeStep === 0}
                onClick={() => setActiveStep((s) => Math.max(0, s - 1))}
              >
                Previous Step
              </Button>
              <Button
                onClick={() => setActiveStep((s) => Math.min(3, s + 1))}
              >
                {activeStep === 3 ? "Complete Onboarding" : "Next Step"}
              </Button>
            </div>
          </Card>
        </section>

        {/* 7. Map Legends & Voice Controls */}
        <section className="space-y-4">
          <h3 className="text-xl font-bold text-primary-dark border-b border-border pb-2">
            7. Map Legend & Voice Controls
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 items-start">
            <MapLegend type="ndvi" />
            <div className="p-5 rounded-card border border-border bg-white shadow-card space-y-3">
              <h4 className="font-semibold text-primary-dark text-sm">
                Web Speech Voice Assistant
              </h4>
              <div className="flex items-center gap-3">
                <VoiceButton
                  mode="listen"
                  label="Speak Query"
                  onSpeechResult={(text) => setVoiceResult(text)}
                />
                <VoiceButton
                  mode="speak"
                  label="Listen to Audio Summary"
                  textToSpeak="Welcome to KrishiNet-BRICS sovereign agricultural intelligence."
                />
              </div>
              {voiceResult && (
                <div className="p-3 bg-surface-soft rounded-lg text-xs font-medium border border-border">
                  Heard: "{voiceResult}"
                </div>
              )}
            </div>
          </div>
        </section>

        {/* 8. 30-Day Timeline */}
        <section className="space-y-4">
          <h3 className="text-xl font-bold text-primary-dark border-b border-border pb-2">
            8. Regenerative 30-Day Action Calendar
          </h3>
          <Card className="p-6">
            <Timeline items={demoTimeline} />
          </Card>
        </section>

        {/* 9. Data Table with Accessible CSV Export */}
        <section className="space-y-4">
          <h3 className="text-xl font-bold text-primary-dark border-b border-border pb-2">
            9. Accessible Data Table
          </h3>
          <DataTable data={demoTableData} columns={demoColumns} />
        </section>

        {/* 10. Error Envelope & Skeletons */}
        <section className="space-y-4">
          <h3 className="text-xl font-bold text-primary-dark border-b border-border pb-2">
            10. Standard Error Envelope & Loading Skeletons
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ErrorState
              error={{
                code: "FIELD_GEOMETRY_INVALID",
                message: "Polygon area is 0.004 ha, below minimum threshold of 0.01 ha.",
                request_id: "req-c8d9-2026",
              }}
              onRetry={() => alert("Retrying request...")}
            />
            <CardSkeleton />
          </div>
        </section>
      </main>

      <DisclaimerFooter />
    </div>
  );
}
