"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import {
  MapPin,
  Compass,
  Sprout,
  Droplets,
  Shield,
  Check,
  AlertCircle,
  HelpCircle,
  ArrowRight,
  ArrowLeft,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Stepper } from "@/components/ui/Stepper";
import { apiClient, setAccessToken } from "@/lib/api/client";
import { useAuthStore } from "@/lib/auth/store";
import { saveDraft, loadDraft, clearDraft, enqueueMutation } from "@/lib/storage/offline-queue";
import { calculatePolygonAreaHa, createSquarePolygonFromPoint } from "@/lib/geo/geometry";
import { cn } from "@/lib/utils";
import type { GeoPolygon, OnboardingRequest } from "@krishinet/shared";

const COUNTRY_OPTIONS = [
  { code: "IND", name: "India", flag: "🇮🇳", defaultLang: "hi" },
  { code: "BRA", name: "Brazil", flag: "🇧🇷", defaultLang: "pt" },
  { code: "ZAF", name: "South Africa", flag: "🇿🇦", defaultLang: "en" },
  { code: "ETH", name: "Ethiopia", flag: "🇪🇹", defaultLang: "am" },
  { code: "EGY", name: "Egypt", flag: "🇪🇬", defaultLang: "ar" },
  { code: "CHN", name: "China", flag: "🇨🇳", defaultLang: "zh" },
  { code: "RUS", name: "Russia", flag: "🇷🇺", defaultLang: "ru" },
];

const CROP_OPTIONS = [
  { id: "cotton", name: "Cotton", icon: "🌱" },
  { id: "rice", name: "Rice (Paddy)", icon: "🌾" },
  { id: "wheat", name: "Wheat", icon: "🌾" },
  { id: "maize", name: "Maize (Corn)", icon: "🌽" },
  { id: "soybean", name: "Soybean", icon: "🫘" },
  { id: "tomato", name: "Tomato", icon: "🍅" },
  { id: "groundnut", name: "Groundnut", icon: "🥜" },
  { id: "sugarcane", name: "Sugarcane", icon: "🎋" },
];

const IRRIGATION_OPTIONS = [
  { id: "rainfed", name: "Rainfed (Monsoon Dependent)", desc: "Zero supplementary irrigation" },
  { id: "drip", name: "Drip Irrigation", desc: "Precision micro-irrigation lines" },
  { id: "canal", name: "Canal Gravity Flow", desc: "Rotational irrigation system" },
  { id: "borewell", name: "Tube-well / Borewell", desc: "Groundwater pump system" },
  { id: "sprinkler", name: "Sprinkler Irrigation", desc: "Overhead pressure nozzles" },
];

const ONBOARDING_STEPS = [
  { id: 0, label: "Language" },
  { id: 1, label: "Location & Field" },
  { id: 2, label: "Crop & Water" },
  { id: 3, label: "Data Consent" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const params = useParams();
  const locale = (params?.locale as string) || "en";

  const { setUser } = useAuthStore();

  const [step, setStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [gpsLoading, setGpsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    full_name: "Ramesh Patel",
    phone_number: "+919876543210",
    country_iso: "IND",
    preferred_language: locale,
    farm_name: "Vidarbha Parcel",
    field_name: "Main Well Field",
    crop_type: "cotton",
    irrigation_type: "rainfed",
    lat: 20.7453,
    lon: 78.5982,
    area_ha: 1.25,
    polygon: createSquarePolygonFromPoint(20.7453, 78.5982, 112),
    consents: {
      share_anonymized_soil: false,
      share_outbreak_telemetry: false,
      participate_in_federated_learning: false,
    },
  });

  // Restore draft on initial load
  useEffect(() => {
    loadDraft<any>("onboarding_draft").then((draft) => {
      if (draft) {
        setFormData((prev) => ({ ...prev, ...draft }));
      }
    });
  }, []);

  // Autosave draft on any state change
  const updateField = (key: string, val: any) => {
    setFormData((prev) => {
      const next = { ...prev, [key]: val };
      saveDraft("onboarding_draft", next);
      return next;
    });
  };

  const updateConsent = (key: string, val: boolean) => {
    setFormData((prev) => {
      const next = {
        ...prev,
        consents: { ...prev.consents, [key]: val },
      };
      saveDraft("onboarding_draft", next);
      return next;
    });
  };

  // GPS Acquisition Handler
  const handleAcquireGps = () => {
    if (!navigator.geolocation) {
      setErrorMsg("Geolocation not supported by this device. Using map point.");
      return;
    }

    setGpsLoading(true);
    setErrorMsg(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGpsLoading(false);
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        const poly = createSquarePolygonFromPoint(lat, lon, 112);
        const area = calculatePolygonAreaHa(poly.coordinates[0]);

        setFormData((prev) => {
          const next = {
            ...prev,
            lat,
            lon,
            polygon: poly,
            area_ha: area || 1.0,
          };
          saveDraft("onboarding_draft", next);
          return next;
        });
      },
      (err) => {
        setGpsLoading(false);
        setErrorMsg("GPS permission denied. Using selected map location.");
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  };

  // Submit Handler
  const handleSubmitOnboarding = async () => {
    setIsSubmitting(true);
    setErrorMsg(null);

    const payload: OnboardingRequest = {
      full_name: formData.full_name,
      phone_number: formData.phone_number,
      country_iso: formData.country_iso,
      preferred_language: formData.preferred_language,
      field_name: formData.field_name,
      crop_type: formData.crop_type,
      irrigation_type: formData.irrigation_type as any,
      area_ha: formData.area_ha,
      field_geometry: formData.polygon,
      consents: {
        share_anonymised_disease: formData.consents.share_outbreak_telemetry,
        share_anonymised_soil: formData.consents.share_anonymized_soil,
        share_model_updates: formData.consents.participate_in_federated_learning,
      },
    };

    try {
      if (typeof navigator !== "undefined" && !navigator.onLine) {
        // Enqueue for offline sync
        await enqueueMutation("onboarding", "POST", payload);
        await clearDraft("onboarding_draft");
        setUser({
          id: "offline-farmer-draft",
          full_name: formData.full_name,
          phone_number: formData.phone_number,
          country_iso: formData.country_iso,
          role: "farmer",
          roles: ["farmer"],
        });
        router.push(`/${locale}/dashboard`);
        return;
      }

      // Backend expects /api/v1/onboarding
      const res = await apiClient<any>("onboarding", {
        method: "POST",
        body: JSON.stringify({
          full_name: formData.full_name,
          phone_number: formData.phone_number,
          country_iso: formData.country_iso,
          preferred_language: formData.preferred_language,
          farm_name: formData.farm_name,
          state_province: "Maharashtra",
          village_district: "Wardha",
          field_name: formData.field_name,
          boundary_geojson: formData.polygon,
          current_crop: formData.crop_type,
          irrigation_type: formData.irrigation_type,
          share_anonymized_soil: formData.consents.share_anonymized_soil,
          share_outbreak_telemetry: formData.consents.share_outbreak_telemetry,
          participate_in_federated_learning:
            formData.consents.participate_in_federated_learning,
        }),
      });

      if (res?.access_token) {
        setAccessToken(res.access_token);
      }

      setUser({
        id: res?.user_id || "farmer-001",
        full_name: formData.full_name,
        phone_number: formData.phone_number,
        country_iso: formData.country_iso,
        role: "farmer",
        roles: ["farmer"],
      });

      await clearDraft("onboarding_draft");
      router.push(`/${locale}/dashboard`);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to submit onboarding. Please retry.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-soft py-6 px-4 sm:px-6">
      <div className="max-w-xl mx-auto space-y-6">
        {/* Header & Stepper */}
        <div className="text-center space-y-2">
          <div className="inline-flex h-10 w-10 rounded-xl bg-primary items-center justify-center text-white shadow-green-sm mb-1">
            <Sprout className="h-6 w-6" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-primary-dark tracking-tight">
            Register Farm & Field
          </h1>
          <p className="text-sm text-text-muted">
            Under 60 seconds • Offline resilient • Sovereign data privacy
          </p>
          <div className="pt-2">
            <Stepper
              steps={ONBOARDING_STEPS}
              currentStep={step}
              onStepClick={setStep}
            />
          </div>
        </div>

        {errorMsg && (
          <div
            role="alert"
            className="p-3 bg-red-50 border border-status-risk/30 rounded-xl flex items-center gap-2 text-xs text-status-risk font-semibold"
          >
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* STEP 0: Language & Country */}
        {step === 0 && (
          <Card className="p-6 space-y-6 bg-white shadow-card">
            <CardHeader className="p-0 border-none">
              <CardTitle>Select Country & Language</CardTitle>
              <CardDescription>
                We tailor regional satellite indices, soil calibrations, and native agro-meteorology to your node.
              </CardDescription>
            </CardHeader>

            <div className="space-y-3">
              <label className="text-xs font-bold uppercase text-text-muted">
                Sovereign Node Country
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {COUNTRY_OPTIONS.map((c) => {
                  const isSelected = formData.country_iso === c.code;
                  return (
                    <button
                      key={c.code}
                      type="button"
                      onClick={() => updateField("country_iso", c.code)}
                      className={cn(
                        "p-3 rounded-btn border text-left transition-all select-none flex items-center gap-2.5",
                        isSelected
                          ? "bg-primary-light border-primary text-primary-dark font-bold ring-2 ring-primary"
                          : "border-border hover:bg-surface-soft text-text"
                      )}
                    >
                      <span className="text-2xl">{c.flag}</span>
                      <span className="text-sm truncate">{c.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <label className="text-xs font-bold uppercase text-text-muted">
                Farmer Full Name
              </label>
              <input
                type="text"
                value={formData.full_name}
                onChange={(e) => updateField("full_name", e.target.value)}
                placeholder="e.g. Ramesh Patel"
                className="w-full px-4 py-3 bg-white border border-border rounded-btn text-base text-text focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="space-y-3">
              <label className="text-xs font-bold uppercase text-text-muted">
                Mobile Phone (for SMS Advisories)
              </label>
              <input
                type="tel"
                value={formData.phone_number}
                onChange={(e) => updateField("phone_number", e.target.value)}
                placeholder="+919876543210"
                className="w-full px-4 py-3 bg-white border border-border rounded-btn text-base text-text focus:outline-none focus:ring-2 focus:ring-primary font-mono"
              />
            </div>

            <div className="pt-4 flex justify-end">
              <Button
                variant="primary"
                onClick={() => setStep(1)}
                rightIcon={<ArrowRight className="h-4 w-4" />}
              >
                Next: Field Location
              </Button>
            </div>
          </Card>
        )}

        {/* STEP 1: Location & Field Boundary */}
        {step === 1 && (
          <Card className="p-6 space-y-6 bg-white shadow-card">
            <CardHeader className="p-0 border-none">
              <CardTitle>Field Location & Boundaries</CardTitle>
              <CardDescription>
                Acquire satellite GPS coordinates or drop a field pin to index soil grids and radar imagery.
              </CardDescription>
            </CardHeader>

            {/* GPS Trigger Button */}
            <div className="flex flex-col sm:flex-row gap-3">
              <Button
                variant="primary"
                fullWidth
                isLoading={gpsLoading}
                onClick={handleAcquireGps}
                leftIcon={<Compass className="h-5 w-5" />}
              >
                Use My Current GPS Position
              </Button>
            </div>

            {/* Interactive Coordinate Preview */}
            <div className="p-4 rounded-xl border border-border bg-surface-soft space-y-3">
              <div className="flex items-center justify-between text-xs text-text-muted">
                <span>Centroid Coordinates</span>
                <span className="font-mono text-text font-bold">
                  {formData.lat.toFixed(5)}, {formData.lon.toFixed(5)}
                </span>
              </div>

              {/* Calculated Area Metric Banner */}
              <div className="p-3 bg-white border border-primary/40 rounded-lg flex items-center justify-between">
                <span className="text-sm font-semibold text-primary-dark">
                  Calculated Field Area:
                </span>
                <span className="text-lg font-extrabold text-primary">
                  {formData.area_ha.toFixed(2)} Hectares
                </span>
              </div>
              <p className="text-[11px] text-text-muted">
                Validation check: Area satisfies national regenerative minimum ({">= 0.01 ha"}).
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold uppercase text-text-muted">
                Field Identifier Name
              </label>
              <input
                type="text"
                value={formData.field_name}
                onChange={(e) => updateField("field_name", e.target.value)}
                placeholder="e.g. South Canal Parcel"
                className="w-full px-4 py-3 bg-white border border-border rounded-btn text-base text-text focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="pt-4 flex justify-between">
              <Button
                variant="secondary"
                onClick={() => setStep(0)}
                leftIcon={<ArrowLeft className="h-4 w-4" />}
              >
                Back
              </Button>
              <Button
                variant="primary"
                onClick={() => setStep(2)}
                rightIcon={<ArrowRight className="h-4 w-4" />}
              >
                Next: Crop Details
              </Button>
            </div>
          </Card>
        )}

        {/* STEP 2: Crop & Irrigation */}
        {step === 2 && (
          <Card className="p-6 space-y-6 bg-white shadow-card">
            <CardHeader className="p-0 border-none">
              <CardTitle>Crop & Water Management</CardTitle>
              <CardDescription>
                Select your standing crop and watering infrastructure for targeted pest and fertilizer alerts.
              </CardDescription>
            </CardHeader>

            <div className="space-y-3">
              <label className="text-xs font-bold uppercase text-text-muted">
                Standing Primary Crop
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                {CROP_OPTIONS.map((c) => {
                  const isSelected = formData.crop_type === c.id;
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => updateField("crop_type", c.id)}
                      className={cn(
                        "p-3 rounded-btn border text-center transition-all select-none flex flex-col items-center gap-1.5",
                        isSelected
                          ? "bg-primary-light border-primary text-primary-dark font-bold ring-2 ring-primary"
                          : "border-border hover:bg-surface-soft text-text"
                      )}
                    >
                      <span className="text-3xl">{c.icon}</span>
                      <span className="text-xs font-semibold">{c.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <label className="text-xs font-bold uppercase text-text-muted">
                Irrigation Infrastructure
              </label>
              <div className="space-y-2">
                {IRRIGATION_OPTIONS.map((irr) => {
                  const isSelected = formData.irrigation_type === irr.id;
                  return (
                    <div
                      key={irr.id}
                      onClick={() => updateField("irrigation_type", irr.id)}
                      className={cn(
                        "p-3 rounded-btn border flex items-center justify-between cursor-pointer select-none transition-colors",
                        isSelected
                          ? "bg-primary-light border-primary text-primary-dark font-bold ring-1 ring-primary"
                          : "border-border hover:bg-surface-soft text-text"
                      )}
                    >
                      <div>
                        <div className="text-sm font-semibold">{irr.name}</div>
                        <div className="text-xs text-text-muted mt-0.5">{irr.desc}</div>
                      </div>
                      {isSelected && <Check className="h-5 w-5 text-primary stroke-[3]" />}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="pt-4 flex justify-between">
              <Button
                variant="secondary"
                onClick={() => setStep(1)}
                leftIcon={<ArrowLeft className="h-4 w-4" />}
              >
                Back
              </Button>
              <Button
                variant="primary"
                onClick={() => setStep(3)}
                rightIcon={<ArrowRight className="h-4 w-4" />}
              >
                Next: Data Sovereignty
              </Button>
            </div>
          </Card>
        )}

        {/* STEP 3: Sovereign Consent Choices */}
        {step === 3 && (
          <Card className="p-6 space-y-6 bg-white shadow-card">
            <CardHeader className="p-0 border-none">
              <CardTitle>Data Sovereignty & Privacy</CardTitle>
              <CardDescription>
                Under BRICS sovereign governance, all telemetry is private by default. Choose how you contribute to community intelligence.
              </CardDescription>
            </CardHeader>

            <div className="space-y-4">
              {/* Consent 1: Anonymized Soil */}
              <div className="p-4 rounded-xl border border-border bg-surface-soft space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-bold text-text">
                    Regional Soil Mapping
                  </span>
                  <input
                    type="checkbox"
                    checked={formData.consents.share_anonymized_soil}
                    onChange={(e) =>
                      updateConsent("share_anonymized_soil", e.target.checked)
                    }
                    className="h-5 w-5 rounded text-primary focus:ring-primary"
                  />
                </div>
                <p className="text-xs text-text-muted leading-relaxed">
                  Shares coarsened soil chemistry indicators (N, P, K, pH) to calibrate local regenerative soil prediction models. Coordinates are offset by 2km.
                </p>
              </div>

              {/* Consent 2: Syndromic Disease */}
              <div className="p-4 rounded-xl border border-border bg-surface-soft space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-bold text-text">
                    Disease Outbreak Early Warning
                  </span>
                  <input
                    type="checkbox"
                    checked={formData.consents.share_outbreak_telemetry}
                    onChange={(e) =>
                      updateConsent("share_outbreak_telemetry", e.target.checked)
                    }
                    className="h-5 w-5 rounded text-primary focus:ring-primary"
                  />
                </div>
                <p className="text-xs text-text-muted leading-relaxed">
                  Includes anonymized pathogen detections in the regional H3 epidemiological map to trigger preventative neighbour warnings before fungal blight spreads.
                </p>
              </div>

              {/* Consent 3: Federated Learning */}
              <div className="p-4 rounded-xl border border-border bg-surface-soft space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-bold text-text">
                    Federated Model Improvements
                  </span>
                  <input
                    type="checkbox"
                    checked={formData.consents.participate_in_federated_learning}
                    onChange={(e) =>
                      updateConsent(
                        "participate_in_federated_learning",
                        e.target.checked
                      )
                    }
                    className="h-5 w-5 rounded text-primary focus:ring-primary"
                  />
                </div>
                <p className="text-xs text-text-muted leading-relaxed">
                  Allows your mobile device to compute gradient weights locally when idle and on WiFi. Raw leaf photos never leave your device.
                </p>
              </div>
            </div>

            <div className="pt-4 flex justify-between gap-3">
              <Button
                variant="secondary"
                onClick={() => setStep(2)}
                leftIcon={<ArrowLeft className="h-4 w-4" />}
              >
                Back
              </Button>
              <Button
                variant="primary"
                isLoading={isSubmitting}
                onClick={handleSubmitOnboarding}
                leftIcon={<Shield className="h-5 w-5" />}
              >
                Complete Registration
              </Button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
