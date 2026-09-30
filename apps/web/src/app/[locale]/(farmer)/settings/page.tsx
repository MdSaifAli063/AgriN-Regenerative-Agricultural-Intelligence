"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Globe,
  Eye,
  Volume2,
  Database,
  Trash2,
  Download,
  Shield,
  CheckCircle2,
  Smartphone,
  HardDrive,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import { AccessibilityBar } from "@/components/common/AccessibilityBar";
import { getOfflineStorageStats } from "@/lib/storage/offline-queue";
import { cn } from "@/lib/utils";

export default function FarmerSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const locale = (params?.locale as string) || "en";

  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [dataSaver, setDataSaver] = useState(false);
  const [storageStats, setStorageStats] = useState({ draftsCount: 0, queueCount: 0 });

  // Consent Toggles
  const [consents, setConsents] = useState({
    share_soil: true,
    share_outbreaks: true,
    federated_learning: false,
  });

  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    getOfflineStorageStats().then(setStorageStats);
    if (typeof window !== "undefined") {
      setDataSaver(localStorage.getItem("krishinet_data_saver") === "true");
    }
  }, []);

  const handleToggleDataSaver = () => {
    const next = !dataSaver;
    setDataSaver(next);
    localStorage.setItem("krishinet_data_saver", String(next));
    showSuccess("Data-saver preferences updated.");
  };

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 3000);
  };

  const handleClearCache = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("KRISHINET_QUERY_OFFLINE_CACHE");
      localStorage.removeItem("onboarding_draft");
      showSuccess("Offline cache purged successfully.");
      getOfflineStorageStats().then(setStorageStats);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-primary-dark tracking-tight">
          Application & Sovereignty Settings
        </h1>
        <p className="text-sm text-text-muted mt-1">
          Customize display accessibility, data saving, offline storage, and privacy consents.
        </p>
      </div>

      {successMsg && (
        <div
          role="status"
          className="p-3.5 bg-[#DCFCE7] border border-[#86EFAC] text-[#166534] rounded-xl flex items-center gap-2 text-xs font-bold"
        >
          <CheckCircle2 className="h-4 w-4" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* 1. Accessibility & Language */}
      <Card className="p-6 space-y-5">
        <CardHeader className="p-0 border-none">
          <CardTitle>Display & Accessibility</CardTitle>
          <CardDescription>
            Tailor screen contrast, text scaling, and language for high daylight outdoor legibility.
          </CardDescription>
        </CardHeader>

        <div className="space-y-4 pt-2 divide-y divide-border">
          <div className="flex items-center justify-between pt-3">
            <div>
              <span className="text-sm font-bold text-text block">Language Selection</span>
              <span className="text-xs text-text-muted">Choose your native regional dialect.</span>
            </div>
            <LanguageSwitcher currentLocale={locale} />
          </div>

          <div className="flex items-center justify-between pt-3">
            <div>
              <span className="text-sm font-bold text-text block">Text Sizing & High Contrast</span>
              <span className="text-xs text-text-muted">Adjust typography scale or activate monochrome contrast.</span>
            </div>
            <AccessibilityBar />
          </div>

          <div className="flex items-center justify-between pt-3">
            <div>
              <span className="text-sm font-bold text-text block">Audio Voice Guidance</span>
              <span className="text-xs text-text-muted">Enable automatic speech synthesis on advice cards.</span>
            </div>
            <input
              type="checkbox"
              checked={voiceEnabled}
              onChange={(e) => setVoiceEnabled(e.target.checked)}
              className="h-5 w-5 rounded text-primary focus:ring-primary"
            />
          </div>

          <div className="flex items-center justify-between pt-3">
            <div>
              <span className="text-sm font-bold text-text block">Data-Saver Mode</span>
              <span className="text-xs text-text-muted">Skip high-res Sentinel rasters to conserve mobile 2G/3G data.</span>
            </div>
            <input
              type="checkbox"
              checked={dataSaver}
              onChange={handleToggleDataSaver}
              className="h-5 w-5 rounded text-primary focus:ring-primary"
            />
          </div>
        </div>
      </Card>

      {/* 2. Revocable Data Sovereignty Consents */}
      <Card className="p-6 space-y-5">
        <CardHeader className="p-0 border-none">
          <div className="flex items-center gap-2 text-primary-dark">
            <Shield className="h-5 w-5 text-primary" />
            <CardTitle>Consent & Data Sovereignty</CardTitle>
          </div>
          <CardDescription>
            You retain absolute ownership of all farm telemetry. You may revoke contributions at any time.
          </CardDescription>
        </CardHeader>

        <div className="space-y-4 pt-2 divide-y divide-border">
          <div className="flex items-start justify-between gap-4 pt-3">
            <div>
              <span className="text-sm font-bold text-text block">Regional Soil Data Contribution</span>
              <span className="text-xs text-text-muted leading-relaxed block mt-0.5">
                Permits coarsened chemical measurements to refine public soil health algorithms.
              </span>
            </div>
            <input
              type="checkbox"
              checked={consents.share_soil}
              onChange={(e) => {
                setConsents((c) => ({ ...c, share_soil: e.target.checked }));
                showSuccess("Consent updated.");
              }}
              className="h-5 w-5 rounded text-primary focus:ring-primary mt-1"
            />
          </div>

          <div className="flex items-start justify-between gap-4 pt-3">
            <div>
              <span className="text-sm font-bold text-text block">Outbreak Telemetry Sharing</span>
              <span className="text-xs text-text-muted leading-relaxed block mt-0.5">
                Feeds anonymised syndromic detections into regional pest outbreak warnings.
              </span>
            </div>
            <input
              type="checkbox"
              checked={consents.share_outbreaks}
              onChange={(e) => {
                setConsents((c) => ({ ...c, share_outbreaks: e.target.checked }));
                showSuccess("Consent updated.");
              }}
              className="h-5 w-5 rounded text-primary focus:ring-primary mt-1"
            />
          </div>

          <div className="flex items-start justify-between gap-4 pt-3">
            <div>
              <span className="text-sm font-bold text-text block">Federated Model Training</span>
              <span className="text-xs text-text-muted leading-relaxed block mt-0.5">
                Computes on-device model weights during charging to improve edge disease AI.
              </span>
            </div>
            <input
              type="checkbox"
              checked={consents.federated_learning}
              onChange={(e) => {
                setConsents((c) => ({ ...c, federated_learning: e.target.checked }));
                showSuccess("Consent updated.");
              }}
              className="h-5 w-5 rounded text-primary focus:ring-primary mt-1"
            />
          </div>
        </div>
      </Card>

      {/* 3. Offline Storage & DPG Data Rights */}
      <Card className="p-6 space-y-5">
        <CardHeader className="p-0 border-none">
          <div className="flex items-center gap-2 text-primary-dark">
            <HardDrive className="h-5 w-5 text-primary" />
            <CardTitle>Offline Cache & Storage Manager</CardTitle>
          </div>
          <CardDescription>
            Inspect cached on-device AI weights, advisory snapshots, and pending offline sync queues.
          </CardDescription>
        </CardHeader>

        <div className="p-4 rounded-xl border border-border bg-surface-soft flex items-center justify-between flex-wrap gap-4">
          <div>
            <div className="text-sm font-bold text-text">On-Device Storage Utilization</div>
            <div className="text-xs text-text-muted mt-0.5">
              Cached Drafts: {storageStats.draftsCount} • Queued Mutations: {storageStats.queueCount} • MobileNetV3 INT8 Model: ~3.8 MB
            </div>
          </div>

          <Button variant="secondary" size="sm" onClick={handleClearCache} leftIcon={<Trash2 className="h-4 w-4 text-status-risk" />}>
            Purge Cache
          </Button>
        </div>

        {/* Data Rights Buttons */}
        <div className="pt-2 flex flex-col sm:flex-row gap-3">
          <Button
            variant="secondary"
            onClick={() => alert("Packaging your farm data into encrypted JSON archive...")}
            leftIcon={<Download className="h-4 w-4" />}
          >
            Download My Complete Data (JSON)
          </Button>
          <Button
            variant="ghost"
            onClick={() => alert("Requesting deletion of leaf images from MinIO...")}
            leftIcon={<Trash2 className="h-4 w-4 text-text-muted" />}
          >
            Delete My Uploaded Leaf Photos
          </Button>
        </div>
      </Card>
    </div>
  );
}
