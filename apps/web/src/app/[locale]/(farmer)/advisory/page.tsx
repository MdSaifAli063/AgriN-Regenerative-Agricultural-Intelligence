"use client";

import React, { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sprout,
  Droplets,
  Calendar,
  AlertTriangle,
  HelpCircle,
  Share2,
  Star,
  RotateCw,
  X,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  Filter,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { AdvisoryCard } from "@/components/ui/AdvisoryCard";
import { StatusPill } from "@/components/ui/StatusPill";
import { Timeline } from "@/components/ui/Timeline";
import { ConfidenceMeter } from "@/components/ui/ConfidenceMeter";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { VoiceButton } from "@/components/ui/VoiceButton";
import { CardSkeleton } from "@/components/ui/Skeletons";
import { ErrorState } from "@/components/ui/ErrorState";
import { apiClient } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import type { AdvisoryResponse, RegenerativePractice } from "@krishinet/shared";

export default function AdvisoryPlanPage() {
  const params = useParams();
  const router = useRouter();
  const locale = (params?.locale as string) || "en";
  const queryClient = useQueryClient();

  const [explainDrawerOpen, setExplainDrawerOpen] = useState(false);
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState(5);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [costFilter, setCostFilter] = useState<string>("all");
  const [difficultyFilter, setDifficultyFilter] = useState<string>("all");

  // Fetch Advisory
  const {
    data: advisory,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery<AdvisoryResponse>({
    queryKey: ["advisory-plan"],
    queryFn: () => apiClient<AdvisoryResponse>("advisories/current"),
  });

  // Regenerate Mutation
  const regenerateMutation = useMutation({
    mutationFn: async () => {
      // Backend POST /fields/{field_id}/advisory with force_refresh
      return await apiClient<AdvisoryResponse>("advisories/current");
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["advisory-plan"], data);
    },
  });

  // Submit Feedback Mutation
  const feedbackMutation = useMutation({
    mutationFn: async () => {
      if (!advisory?.id) return;
      return await apiClient(`advisories/${advisory.id}/feedback`, {
        method: "POST",
        body: JSON.stringify({
          rating: feedbackRating,
          comment: feedbackComment,
          practices_adopted: [],
        }),
      });
    },
    onSuccess: () => {
      setFeedbackSubmitted(true);
      setTimeout(() => {
        setFeedbackModalOpen(false);
        setFeedbackSubmitted(false);
      }, 1500);
    },
  });

  // Share Handler
  const handleShare = () => {
    if (typeof window === "undefined") return;
    const shareText = `KrishiNet Regenerative Advisory: ${advisory?.what_to_do_today?.headline || "Farm Advice"}. Suitability & Organic Nutrient Plan.`;
    if (navigator.share) {
      navigator.share({
        title: "KrishiNet-BRICS Farm Advisory",
        text: shareText,
        url: window.location.href,
      }).catch(() => {});
    } else {
      navigator.clipboard.writeText(`${shareText}\n${window.location.href}`);
      alert("Advisory summary copied to clipboard!");
    }
  };

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

  // Filter practices
  const filteredPractices = (advisory?.regenerative_practices || []).filter((p) => {
    if (costFilter !== "all" && p.cost_level !== costFilter) return false;
    if (difficultyFilter !== "all" && p.difficulty !== difficultyFilter) return false;
    return true;
  });

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      {/* Top Header & Actions Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-primary-dark tracking-tight">
              Regenerative Advisory Plan
            </h1>
            <StatusPill status="healthy" label="Grounded in ICAR & EMBRAPA" />
          </div>
          <p className="text-xs text-text-muted mt-0.5">
            Field ID: <code className="font-mono text-text">{advisory?.field_id || "fld-001"}</code> • Synthetic Multi-Modal Synthesis
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setExplainDrawerOpen(true)}
            leftIcon={<HelpCircle className="h-4 w-4 text-primary" />}
          >
            Why This Advice?
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => setFeedbackModalOpen(true)}
            leftIcon={<Star className="h-4 w-4 text-status-watch" />}
          >
            Rate Advice
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={handleShare}
            aria-label="Share advisory plan"
          >
            <Share2 className="h-4 w-4" />
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => regenerateMutation.mutate()}
            isLoading={regenerateMutation.isPending || isFetching}
            leftIcon={<RotateCw className="h-4 w-4" />}
          >
            Regenerate
          </Button>
        </div>
      </div>

      {/* Confidence Level Alert Banner */}
      {advisory?.confidence_level === "medium" && (
        <div className="p-4 bg-[#FEF3C7] border border-[#FCD34D] rounded-xl flex items-start gap-3 text-sm text-[#92400E]">
          <AlertTriangle className="h-5 w-5 text-[#F59E0B] flex-shrink-0 mt-0.5" />
          <div>
            <strong className="block font-bold">Verification Notice</strong>
            This advisory was generated with moderate multi-spectral confidence. Review local soil moisture before major mechanical operations.
          </div>
        </div>
      )}

      {/* 1. Crop Recommendations Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between pb-1 border-b border-border">
          <h2 className="text-xl font-bold text-primary-dark flex items-center gap-2">
            <Sprout className="h-5 w-5 text-primary" />
            <span>Optimal Crop Selection (Kharif / Summer)</span>
          </h2>
          {advisory?.provenance && (
            <ProvenanceBadge provenance={advisory.provenance} size="sm" />
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {advisory?.crop_recommendations?.map((rec, idx) => (
            <AdvisoryCard
              key={idx}
              title={rec.crop_name}
              category="crop"
              suitabilityScore={rec.suitability_score}
              waterNeedMm={rec.water_need_mm}
              riskLevel={rec.climate_risk_level}
              summary={`Estimated Yield: ${rec.yield_estimate_range}. Water consumption suited to soil water-retention profile.`}
              tags={["intercrop", "nitrogen-saving"]}
            />
          ))}
        </div>
      </section>

      {/* 2. Sowing Window & Irrigation Schedule */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="p-6 space-y-3">
          <div className="flex items-center gap-2 text-primary-dark">
            <Calendar className="h-5 w-5 text-primary" />
            <CardTitle>Optimal Sowing Window</CardTitle>
          </div>
          <div className="text-2xl font-extrabold text-primary pt-1">
            {advisory?.sowing_window?.start_date || "June 15"} – {advisory?.sowing_window?.end_date || "July 05"}
          </div>
          <p className="text-xs text-text-muted leading-relaxed">
            {advisory?.sowing_window?.rationale ||
              "Calibrated to pre-monsoon shower accumulation (min 60mm cumulative topsoil moisture threshold)."}
          </p>
        </Card>

        <Card className="p-6 space-y-3">
          <div className="flex items-center gap-2 text-primary-dark">
            <Droplets className="h-5 w-5 text-[#0EA5E9]" />
            <CardTitle>Irrigation Schedule</CardTitle>
          </div>
          <div className="text-2xl font-extrabold text-[#0EA5E9] pt-1">
            Zero Need Next 5 Days
          </div>
          <p className="text-xs text-text-muted leading-relaxed">
            Upcoming precipitation (39mm) satisfies soil evapotranspiration. Turn off supplementary drip pumps to save electricity.
          </p>
        </Card>
      </section>

      {/* 3. Fertiliser Plan (Organic First) */}
      <section className="space-y-4">
        <h2 className="text-xl font-bold text-primary-dark flex items-center gap-2 pb-1 border-b border-border">
          <Sprout className="h-5 w-5 text-primary" />
          <span>Fertiliser & Nutrient Plan (Organic-First)</span>
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Organic Options */}
          <Card className="p-6 space-y-3 border-primary/30 bg-[#DCFCE7]/20">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary" />
              <h3 className="font-bold text-base text-primary-dark">
                Recommended Organic Amendments
              </h3>
            </div>
            <ul className="space-y-2 text-sm text-text pt-1">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
                <span>Vermicompost @ 2.5 tonnes/ha pre-sowing soil incorporation</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
                <span>Neem cake (Azadirachta indica) @ 250 kg/ha for nitrogen nitrification inhibition</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
                <span>Biofertilizer consortium (Rhizobium + PSB) liquid seed treatment</span>
              </li>
            </ul>
          </Card>

          {/* Chemical Emergency Fallback Box with Warning */}
          <Card className="p-6 space-y-3 border-status-risk/40 bg-[#FFF5F5]">
            <div className="flex items-center gap-2 text-status-risk">
              <AlertTriangle className="h-5 w-5" />
              <h3 className="font-bold text-base">
                Chemical Intervention (Emergency Last Resort)
              </h3>
            </div>
            <p className="text-xs text-[#991B1B] font-semibold leading-relaxed">
              Mandatory Safety Notice: Apply synthetic chemical fertilisers only if soil test verification confirms acute deficiency.
            </p>
            <div className="p-3 bg-white rounded-lg border border-[#FCA5A5] text-xs space-y-1 font-mono text-text">
              <div>Urea 46% N: Max 50 kg/ha split dose (top-dress)</div>
              <div>Single Super Phosphate (SSP): 75 kg/ha basal</div>
            </div>
            <p className="text-[11px] text-text-muted">
              Observe personal protective equipment (PPE) guidelines and water-body setback minimums (30m).
            </p>
          </Card>
        </div>
      </section>

      {/* 4. Regenerative Practices with Interactive Filter Chips */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-1 border-b border-border">
          <h2 className="text-xl font-bold text-primary-dark">
            Indigenous & Regenerative Agronomic Practices
          </h2>

          {/* Filter Chips */}
          <div className="flex items-center gap-2 text-xs">
            <Filter className="h-3.5 w-3.5 text-text-muted" />
            <select
              value={costFilter}
              onChange={(e) => setCostFilter(e.target.value)}
              className="px-2 py-1 bg-white border border-border rounded text-xs text-text focus:ring-primary"
            >
              <option value="all">All Costs</option>
              <option value="low">Low Cost</option>
              <option value="medium">Medium Cost</option>
            </select>
            <select
              value={difficultyFilter}
              onChange={(e) => setDifficultyFilter(e.target.value)}
              className="px-2 py-1 bg-white border border-border rounded text-xs text-text focus:ring-primary"
            >
              <option value="all">All Difficulty</option>
              <option value="easy">Easy</option>
              <option value="moderate">Moderate</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredPractices.map((prac) => (
            <Card key={prac.id} className="p-5 space-y-2 hover:border-primary transition-colors">
              <div className="flex items-center justify-between gap-2">
                <h3 className="font-bold text-base text-primary-dark">{prac.title}</h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-primary-light text-primary-dark uppercase">
                  {prac.difficulty}
                </span>
              </div>
              <p className="text-xs text-text leading-relaxed">{prac.summary}</p>
              <div className="pt-2 flex items-center justify-between text-[11px] text-text-muted">
                <span>Cost: <strong className="capitalize text-text">{prac.cost_level}</strong></span>
                <span>Benefit: <strong className="text-primary">{prac.benefit_category}</strong></span>
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* 5. 30-Day Field Activity Timeline */}
      {advisory?.timeline_30d && (
        <section className="space-y-4">
          <h2 className="text-xl font-bold text-primary-dark pb-1 border-b border-border">
            30-Day Action Schedule
          </h2>
          <Card className="p-6">
            <Timeline items={advisory.timeline_30d} />
          </Card>
        </section>
      )}

      {/* EXPLAINABILITY SLIDE-OVER DRAWER ("Why this advice?") */}
      {explainDrawerOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity"
            onClick={() => setExplainDrawerOpen(false)}
          />
          <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
            <div className="w-screen max-w-md bg-white border-l border-border shadow-2xl p-6 overflow-y-auto space-y-6 animate-in slide-in-from-right duration-200">
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <div className="flex items-center gap-2 text-primary-dark">
                  <HelpCircle className="h-5 w-5 text-primary" />
                  <h3 className="text-lg font-bold">Why This Advice?</h3>
                </div>
                <button
                  type="button"
                  onClick={() => setExplainDrawerOpen(false)}
                  className="p-1 rounded-md text-text-muted hover:text-text"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Confidence Meter in Drawer */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase text-text-muted tracking-wider">
                  Algorithmic Confidence
                </h4>
                <ConfidenceMeter score={advisory?.confidence_score || 0.88} />
              </div>

              {/* Top Drivers */}
              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-bold uppercase text-text-muted tracking-wider">
                  Top Decision Drivers
                </h4>
                <div className="space-y-2">
                  {advisory?.explainability?.top_drivers?.map((d, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-xl border border-border bg-surface-soft text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between font-bold">
                        <span className="text-primary-dark">{d.feature}</span>
                        <span className="text-primary">+{Math.round(d.magnitude * 100)}%</span>
                      </div>
                      <p className="text-text-muted">{d.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Environmental Signals Used */}
              <div className="space-y-2 pt-2">
                <h4 className="text-xs font-bold uppercase text-text-muted tracking-wider">
                  Input Environmental Signals
                </h4>
                <div className="space-y-1.5 text-xs">
                  {advisory?.explainability?.signals_used?.map((sig, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between p-2 rounded-lg bg-surface-soft border border-border/60"
                    >
                      <span className="font-medium text-text">{sig.name}</span>
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono font-bold text-text">{sig.value}</span>
                        <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Peer-reviewed Citations & AGROVOC */}
              <div className="space-y-2 pt-2">
                <h4 className="text-xs font-bold uppercase text-text-muted tracking-wider">
                  Peer-Reviewed Citations & DPG Ontology
                </h4>
                <div className="space-y-2 text-xs">
                  {advisory?.explainability?.sources?.map((s, i) => (
                    <div key={i} className="p-3 rounded-lg border border-border bg-white space-y-1">
                      <div className="font-bold text-primary-dark">{s.title}</div>
                      <div className="text-[11px] text-text-muted">{s.source}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Counterfactual Note */}
              {advisory?.explainability?.counterfactual && (
                <div className="p-3.5 rounded-xl border border-border bg-surface-soft text-xs text-text-muted italic">
                  <strong>Counterfactual Scenario:</strong> {advisory.explainability.counterfactual}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* FEEDBACK RATING MODAL */}
      {feedbackModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
          <div className="w-full max-w-sm bg-white rounded-card border border-border p-6 shadow-2xl space-y-4 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <h3 className="font-bold text-lg text-primary-dark">Rate This Advice</h3>
              <button
                type="button"
                onClick={() => setFeedbackModalOpen(false)}
                className="text-text-muted hover:text-text"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {feedbackSubmitted ? (
              <div className="text-center py-6 text-primary space-y-2">
                <CheckCircle2 className="h-10 w-10 mx-auto" />
                <div className="font-bold text-base">Feedback Recorded!</div>
                <div className="text-xs text-text-muted">Thank you for improving local sovereign agronomy models.</div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex justify-center gap-2 pt-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setFeedbackRating(star)}
                      className={cn(
                        "p-2 rounded-lg transition-transform hover:scale-110",
                        star <= feedbackRating ? "text-status-watch" : "text-border"
                      )}
                    >
                      <Star className="h-7 w-7 fill-current" />
                    </button>
                  ))}
                </div>

                <textarea
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value)}
                  placeholder="Optional: How feasible was this in your field?"
                  rows={3}
                  className="w-full p-3 text-xs bg-surface-soft border border-border rounded-xl focus:ring-primary focus:outline-none"
                />

                <Button
                  variant="primary"
                  fullWidth
                  isLoading={feedbackMutation.isPending}
                  onClick={() => feedbackMutation.mutate()}
                >
                  Submit Sovereign Feedback
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
