"use client";

import React, { useState, useEffect } from "react";
import {
  Send,
  MessageSquare,
  PhoneCall,
  Smartphone,
  Globe,
  CheckCircle2,
  Users,
  AlertCircle,
  Clock,
  Sparkles,
  Info,
} from "lucide-react";
import type { GeoJsonOutbreakFeature } from "@krishinet/shared";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusPill } from "@/components/ui/StatusPill";
import { cn } from "@/lib/utils";

interface BroadcastToolProps {
  initialCluster?: GeoJsonOutbreakFeature | null;
  className?: string;
}

interface BroadcastHistoryItem {
  id: string;
  sentAt: string;
  channel: "whatsapp" | "sms" | "ivr";
  recipientsCount: number;
  templateTitle: string;
  status: "delivered" | "sending" | "failed";
}

const TEMPLATES = [
  {
    id: "urgent_outbreak",
    title: "Urgent Outbreak Alert & Bio-Remedy",
    textTemplates: {
      en: "URGENT KRISHINET ALERT: {disease_name} detected in your cluster ({village}). Apply {remedy_action} immediately. Inspect underside of leaves. Do not over-irrigate. Support: 1800-AGRI-NET",
      hi: "कृषि-नेट आवश्यक सूचना: आपके क्षेत्र ({village}) में {disease_name} का प्रकोप पाया गया है। तुरंत {remedy_action} का छिड़काव करें। पत्तों के नीचे जांचें। हेल्पलाइन: 1800-AGRI-NET",
      mr: "कृषी-नेट महत्त्वाची सूचना: आपल्या परिसरात ({village}) {disease_name} चा प्रादुर्भाव आढळला आहे. त्वरित {remedy_action} वापरा. पाने तपासा. मदत: 1800-AGRI-NET",
      pt: "ALERTA KRISHINET: {disease_name} detectado no seu setor ({village}). Aplique {remedy_action} imediatamente. Inspecione a folhagem. Linha direta: 1800-AGRI-NET",
      sw: "TAARIFA YA DHARURA YA KRISHINET: {disease_name} imegunduliwa katika eneo lako ({village}). Tumia {remedy_action} mara moja. Ukaguzi wa majani. Msaada: 1800-AGRI-NET",
    },
  },
  {
    id: "bio_depot",
    title: "Subsidized Bio-Pesticide Depot Notice",
    textTemplates: {
      en: "GOVT ADVISORY: Subsidized Trichoderma and Neem biopesticides now available at your Gram Panchayat depot. 50% regenerative subsidy for registered smallholders.",
      hi: "सरकारी सूचना: ग्राम पंचायत डिपो पर 50% अनुदान पर ट्राइकोडर्मा और जैविक नीम कीटनाशक उपलब्ध हैं। कृपया अपना किसान पंजीकरण कार्ड लेकर आएं।",
      mr: "शासकीय सूचना: ग्रामपंचायत केंद्रावर 50% अनुदानावर ट्रायकोडर्मा आणि सेंद्रिय औषधे उपलब्ध आहेत. नोंदणीकृत शेतकऱ्यांनी लाभ घ्यावा.",
      pt: "AVISO GOVERNAMENTAL: Bioinsumos subsidiados (Trichoderma) disponíveis no posto local de assistência agrícola.",
      sw: "TANGAZO LA SERIKALI: Dawa za mimea zenye ruzuku ya 50% zinapatikana sasa katika kituo cha kilimo.",
    },
  },
  {
    id: "weather_hazard",
    title: "Monsoon Humidity Disease Warning",
    textTemplates: {
      en: "WEATHER HAZARD: Heavy humidity (>85%) forecasted next 72 hrs. Spore dispersal risk is HIGH for standing crops. Clear drainage channels to prevent fungal rotting.",
      hi: "मौसम चेतावनी: आगामी 72 घंटों में अत्यधिक नमी (>85%) का अनुमान है। फंगल रोगों का खतरा बढ़ गया है। खेतों में जलभराव न होने दें।",
      mr: "हवामान इशारा: पुढील 72 तासांत जास्त आर्द्रता (>85%) राहण्याची शक्यता आहे. बुरशीजन्य रोगांचा धोका टाळण्यासाठी पाण्याचा निचरा करा.",
      pt: "AVISO CLIMÁTICO: Umidade elevada (>85%) prevista nas próximas 72 horas. Risco alto de dispersão de esporos.",
      sw: "ONYO LA HALI YA HEWA: Unyevu mwingi (>85%) unatarajiwa kwa saa 72 zijazo. Hatari kubwa ya magonjwa ya ukungu.",
    },
  },
];

export function BroadcastTool({ initialCluster, className }: BroadcastToolProps) {
  const [channel, setChannel] = useState<"whatsapp" | "sms" | "ivr">("whatsapp");
  const [selectedTemplateId, setSelectedTemplateId] = useState("urgent_outbreak");
  const [selectedLang, setSelectedLang] = useState<"en" | "hi" | "mr" | "pt" | "sw">("en");
  const [targetAudience, setTargetAudience] = useState<"cluster" | "district" | "crop">("cluster");
  const [targetCrop, setTargetCrop] = useState("all");
  const [customMessage, setCustomMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const [history, setHistory] = useState<BroadcastHistoryItem[]>([
    {
      id: "bcast-001",
      sentAt: "Yesterday, 14:30",
      channel: "whatsapp",
      recipientsCount: 284,
      templateTitle: "Urgent Outbreak Alert & Bio-Remedy",
      status: "delivered",
    },
    {
      id: "bcast-002",
      sentAt: "3 days ago",
      channel: "sms",
      recipientsCount: 512,
      templateTitle: "Subsidized Bio-Pesticide Depot Notice",
      status: "delivered",
    },
  ]);

  // Interpolate variables into message template
  const currentTemplate = TEMPLATES.find((t) => t.id === selectedTemplateId) || TEMPLATES[0];
  const rawText = currentTemplate.textTemplates[selectedLang];

  const diseaseName = initialCluster?.properties.disease_name || "Leaf Rust";
  const villageName = initialCluster ? `Sector H3-${initialCluster.properties.h3_index.slice(-4)}` : "Wardha Central";
  const remedyAction = "Bio-Foliar Trichoderma spray";

  const interpolatedText = rawText
    .replace("{disease_name}", diseaseName)
    .replace("{village}", villageName)
    .replace("{remedy_action}", remedyAction);

  const activeMessage = customMessage.trim() ? customMessage : interpolatedText;
  const charCount = activeMessage.length;
  const smsSegments = Math.ceil(charCount / 160) || 1;

  // Estimated recipients based on target audience
  const estimatedRecipients =
    targetAudience === "cluster"
      ? initialCluster
        ? initialCluster.properties.reported_cases * 6 + 18
        : 45
      : targetAudience === "district"
      ? 640
      : 320;

  const handleSendBroadcast = async () => {
    setIsSending(true);
    setShowConfirmModal(false);

    // Simulate broadcast dispatch with realistic latency
    await new Promise((resolve) => setTimeout(resolve, 1200));

    const newRecord: BroadcastHistoryItem = {
      id: `bcast-${Date.now()}`,
      sentAt: "Just now",
      channel,
      recipientsCount: estimatedRecipients,
      templateTitle: currentTemplate.title,
      status: "delivered",
    };

    setHistory([newRecord, ...history]);
    setIsSending(false);
    setSuccessToast(
      `Broadcast successfully queued to ${estimatedRecipients} smallholders via ${channel.toUpperCase()}!`
    );

    setTimeout(() => {
      setSuccessToast(null);
    }, 5000);
  };

  return (
    <div className={cn("space-y-6", className)}>
      <Card className="p-6 bg-white border border-border shadow-card space-y-6">
        <CardHeader className="p-0 border-none">
          <div className="flex items-center justify-between gap-4">
            <div>
              <CardTitle className="text-xl font-extrabold text-primary-dark">
                Mass Advisory & Outbreak Broadcast Tool
              </CardTitle>
              <CardDescription>
                Dispatch multi-channel alerts to smallholders in vulnerable H3 clusters or entire agricultural blocks.
              </CardDescription>
            </div>
            <div className="h-10 w-10 rounded-xl bg-primary-light flex items-center justify-center text-primary-dark shrink-0">
              <Send className="h-5 w-5" />
            </div>
          </div>
        </CardHeader>

        {/* Success Alert Toast */}
        {successToast && (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-900 flex items-center gap-3 animate-fadeIn">
            <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
            <span className="text-sm font-bold">{successToast}</span>
          </div>
        )}

        {/* Step 1: Audience & Delivery Channels */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Target Audience */}
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase text-text-muted flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5" />
              <span>Target Broadcast Audience</span>
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setTargetAudience("cluster")}
                className={cn(
                  "p-2.5 rounded-btn text-xs font-bold border transition-colors text-center",
                  targetAudience === "cluster"
                    ? "bg-primary text-white border-primary"
                    : "bg-surface-soft text-text border-border hover:bg-slate-100"
                )}
              >
                Selected Hex
              </button>
              <button
                type="button"
                onClick={() => setTargetAudience("crop")}
                className={cn(
                  "p-2.5 rounded-btn text-xs font-bold border transition-colors text-center",
                  targetAudience === "crop"
                    ? "bg-primary text-white border-primary"
                    : "bg-surface-soft text-text border-border hover:bg-slate-100"
                )}
              >
                By Crop Type
              </button>
              <button
                type="button"
                onClick={() => setTargetAudience("district")}
                className={cn(
                  "p-2.5 rounded-btn text-xs font-bold border transition-colors text-center",
                  targetAudience === "district"
                    ? "bg-primary text-white border-primary"
                    : "bg-surface-soft text-text border-border hover:bg-slate-100"
                )}
              >
                Entire District
              </button>
            </div>
            <div className="text-[11px] text-text-muted mt-1">
              Estimated reach: <strong className="text-primary-dark">{estimatedRecipients} active farmers</strong>
            </div>
          </div>

          {/* Delivery Channel */}
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase text-text-muted flex items-center gap-1.5">
              <Smartphone className="h-3.5 w-3.5" />
              <span>Dissemination Medium</span>
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setChannel("whatsapp")}
                className={cn(
                  "p-2.5 rounded-btn text-xs font-bold border flex items-center justify-center gap-1.5 transition-colors",
                  channel === "whatsapp"
                    ? "bg-emerald-600 text-white border-emerald-600 shadow-sm"
                    : "bg-surface-soft text-text border-border hover:bg-slate-100"
                )}
              >
                <MessageSquare className="h-4 w-4" />
                WhatsApp
              </button>
              <button
                type="button"
                onClick={() => setChannel("sms")}
                className={cn(
                  "p-2.5 rounded-btn text-xs font-bold border flex items-center justify-center gap-1.5 transition-colors",
                  channel === "sms"
                    ? "bg-primary text-white border-primary shadow-sm"
                    : "bg-surface-soft text-text border-border hover:bg-slate-100"
                )}
              >
                <Smartphone className="h-4 w-4" />
                SMS (2G)
              </button>
              <button
                type="button"
                onClick={() => setChannel("ivr")}
                className={cn(
                  "p-2.5 rounded-btn text-xs font-bold border flex items-center justify-center gap-1.5 transition-colors",
                  channel === "ivr"
                    ? "bg-primary text-white border-primary shadow-sm"
                    : "bg-surface-soft text-text border-border hover:bg-slate-100"
                )}
              >
                <PhoneCall className="h-4 w-4" />
                IVR Voice
              </button>
            </div>
            <div className="text-[11px] text-text-muted mt-1">
              {channel === "whatsapp" && "Rich media card with inline image guide."}
              {channel === "sms" && "GSM-7 compliant for non-smartphone feature phones."}
              {channel === "ivr" && "Automated text-to-speech dial-out in local dialect."}
            </div>
          </div>
        </div>

        {/* Step 2: Template Selection & Language Preview */}
        <div className="space-y-3">
          <label className="text-xs font-bold uppercase text-text-muted">
            Agronomic Advisory Template
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {TEMPLATES.map((tmpl) => (
              <button
                key={tmpl.id}
                type="button"
                onClick={() => {
                  setSelectedTemplateId(tmpl.id);
                  setCustomMessage("");
                }}
                className={cn(
                  "p-3 rounded-xl border text-left text-xs transition-colors",
                  selectedTemplateId === tmpl.id
                    ? "border-primary bg-primary-light/40 font-bold text-primary-dark"
                    : "border-border bg-white text-text hover:bg-surface-soft"
                )}
              >
                {tmpl.title}
              </button>
            ))}
          </div>
        </div>

        {/* Language Preview Tabs */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase text-text-muted flex items-center gap-1">
              <Globe className="h-3.5 w-3.5" />
              <span>Language Translation Preview</span>
            </span>
            <div className="flex items-center gap-1 bg-surface-soft p-0.5 rounded-lg border border-border">
              {(
                [
                  { code: "en", label: "English" },
                  { code: "hi", label: "हिन्दी" },
                  { code: "mr", label: "मराठी" },
                  { code: "pt", label: "Português" },
                  { code: "sw", label: "Kiswahili" },
                ] as const
              ).map((lang) => (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => setSelectedLang(lang.code)}
                  className={cn(
                    "px-2.5 py-1 text-xs rounded-md font-semibold transition-colors",
                    selectedLang === lang.code
                      ? "bg-white text-primary-dark shadow-sm"
                      : "text-text-muted hover:text-text"
                  )}
                >
                  {lang.label}
                </button>
              ))}
            </div>
          </div>

          {/* Message Preview Bubble */}
          <div className="p-4 rounded-2xl bg-surface-soft border border-border space-y-3">
            <div className="flex items-center justify-between text-xs text-text-muted">
              <span>Farmer Screen Preview:</span>
              <span className="font-mono text-[11px]">
                {charCount} chars • {smsSegments} SMS {smsSegments > 1 ? "parts" : "part"}
              </span>
            </div>

            <div
              className={cn(
                "p-4 rounded-xl max-w-lg shadow-sm text-sm leading-relaxed",
                channel === "whatsapp"
                  ? "bg-[#E7FCE8] border border-[#B7F4BA] text-[#113B13] rounded-tl-none font-sans"
                  : "bg-white border border-border text-text font-mono text-xs"
              )}
            >
              {activeMessage}
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-2 flex items-center justify-between gap-4">
          <div className="text-xs text-text-muted">
            All mass communications are recorded in the sovereign audit log for traceability.
          </div>
          <Button
            variant="primary"
            size="lg"
            isLoading={isSending}
            onClick={() => setShowConfirmModal(true)}
            leftIcon={<Send className="h-5 w-5" />}
          >
            Send Broadcast ({estimatedRecipients} Farmers)
          </Button>
        </div>
      </Card>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <Card className="max-w-md w-full p-6 bg-white shadow-2xl space-y-5">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
                <AlertCircle className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-text">Authorize Mass Broadcast?</h3>
                <p className="text-xs text-text-muted">Extension Officer Sign-Off</p>
              </div>
            </div>

            <div className="p-3 bg-surface-soft rounded-xl text-xs space-y-1.5 border border-border">
              <div>
                <span className="text-text-muted">Target Group: </span>
                <strong className="text-text uppercase">{targetAudience}</strong>
              </div>
              <div>
                <span className="text-text-muted">Estimated Recipients: </span>
                <strong className="text-primary-dark">{estimatedRecipients} Smallholders</strong>
              </div>
              <div>
                <span className="text-text-muted">Medium: </span>
                <strong className="text-text uppercase">{channel}</strong>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                variant="secondary"
                onClick={() => setShowConfirmModal(false)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleSendBroadcast}
                leftIcon={<CheckCircle2 className="h-4 w-4" />}
              >
                Confirm & Dispatch
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Recent Broadcast Activity Log */}
      <Card className="p-6 bg-white border border-border shadow-card space-y-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-bold text-text">
            Recent District Broadcast History
          </CardTitle>
          <span className="text-xs font-mono text-text-muted">Last 30 Days</span>
        </div>

        <div className="divide-y divide-border/60">
          {history.map((item) => (
            <div key={item.id} className="py-3 flex items-center justify-between gap-4 text-xs">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-text">{item.templateTitle}</span>
                  <span className="uppercase text-[10px] font-bold px-1.5 py-0.5 rounded bg-surface-soft border border-border text-text-muted">
                    {item.channel}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-text-muted text-[11px]">
                  <Clock className="h-3 w-3" />
                  <span>{item.sentAt}</span>
                  <span>•</span>
                  <span>{item.recipientsCount} Smallholders Reached</span>
                </div>
              </div>
              <StatusPill status="healthy" label="DELIVERED" size="sm" />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
