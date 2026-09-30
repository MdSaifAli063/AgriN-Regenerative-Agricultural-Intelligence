"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Smartphone, Image as ImageIcon, MapPin, RefreshCw, MessageSquare, ShieldCheck, Zap } from "lucide-react";

interface Message {
  id: string;
  sender: "user" | "bot";
  text: string;
  type?: "text" | "location" | "image";
  segments?: number;
  encoding?: string;
  cost?: number;
  timestamp: string;
}

export default function ChatSimulatorPage() {
  const [channel, setChannel] = useState<"whatsapp" | "sms">("whatsapp");
  const [phone, setPhone] = useState("+919876543210");
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [fsmState, setFsmState] = useState("NEW");
  const [currentLang, setCurrentLang] = useState("en");
  const [totalCost, setTotalCost] = useState(0.0);
  const [totalSegments, setTotalSegments] = useState(0);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "init",
      sender: "bot",
      text: "🌾 *Welcome to KrishiNet-BRICS Agricultural Advisory!*\nOne field. Many nations. Shared intelligence.\n\nPlease select your preferred language:\n1. English\n2. हिन्दी (Hindi)\n3. मराठी (Marathi)\n4. Português\n5. More languages",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (
    customText?: string,
    msgType: "text" | "location" | "image" = "text",
    lat?: number,
    lon?: number
  ) => {
    const textToSend = customText !== undefined ? customText : inputText;
    if (!textToSend && msgType === "text") return;

    const userMsg: Message = {
      id: "u-" + Date.now(),
      sender: "user",
      text: textToSend,
      type: msgType,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (customText === undefined) setInputText("");
    setLoading(true);

    try {
      const res = await fetch("/api/v1/messaging/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          from_phone: phone,
          channel: channel,
          message_type: msgType,
          text: textToSend,
          latitude: lat,
          longitude: lon,
          media_url: msgType === "image" ? "https://cdn.krishinet.org/demo/leaf.jpg" : undefined,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setFsmState(data.state);
        setCurrentLang(data.language);
        setTotalCost((prev) => prev + (data.cost_estimate_usd || 0.005));
        setTotalSegments((prev) => prev + (data.segments_count || 1));

        const botMsg: Message = {
          id: "b-" + Date.now(),
          sender: "bot",
          text: data.reply_text,
          segments: data.segments_count,
          encoding: data.encoding,
          cost: data.cost_estimate_usd,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setMessages((prev) => [...prev, botMsg]);
      } else {
        // Fallback simulation response if backend unreachable
        throw new Error("Backend response error");
      }
    } catch {
      // Local fallback mock
      setTimeout(() => {
        const botMsg: Message = {
          id: "b-" + Date.now(),
          sender: "bot",
          text: "🌾 [Demo Mode Active]\nYour request has been received. Reply 1 for Today's Action Card, 2 for Leaf Doctor, 9 for Menu.\n\n⚠️ _AI guidance only._",
          segments: 1,
          encoding: "GSM-7",
          cost: channel === "sms" ? 0.0075 : 0.005,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setMessages((prev) => [...prev, botMsg]);
      }, 500);
    } finally {
      setLoading(false);
    }
  };

  const loadScenario = async (scenario: "cotton" | "soybean" | "maize") => {
    setMessages([]);
    setTotalCost(0);
    setTotalSegments(0);

    if (scenario === "cotton") {
      setChannel("sms");
      setPhone("+919820011223");
      sendMessage("नमस्ते, मुझे कपास की फसल के लिए सलाह चाहिए");
    } else if (scenario === "soybean") {
      setChannel("whatsapp");
      setPhone("+5545999887766");
      sendMessage("Olá KrishiNet, preciso de ajuda na lavoura de soja");
    } else {
      setChannel("whatsapp");
      setPhone("+27821234567");
      sendMessage("Hi KrishiNet, starting new maize planting cycle");
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-4 md:p-8 flex flex-col items-center">
      {/* Top Header */}
      <div className="w-full max-w-5xl mb-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="bg-emerald-500/20 text-emerald-400 text-xs px-2.5 py-1 rounded-full font-mono border border-emerald-500/30 flex items-center gap-1">
              <Zap className="w-3 h-3" /> DEMO_MODE: SIMULATOR ACTIVE
            </span>
            <span className="bg-blue-500/20 text-blue-400 text-xs px-2.5 py-1 rounded-full font-mono border border-blue-500/30">
              State: {fsmState}
            </span>
            <span className="bg-purple-500/20 text-purple-400 text-xs px-2.5 py-1 rounded-full font-mono border border-purple-500/30">
              Locale: {currentLang.toUpperCase()}
            </span>
          </div>
          <h1 className="text-2xl font-bold mt-2 text-white flex items-center gap-2">
            <Smartphone className="w-7 h-7 text-emerald-400" />
            Farmer WhatsApp & SMS Bot Simulator
          </h1>
          <p className="text-slate-400 text-sm">
            Zero-network testing of the multilingual regenerative advisory FSM engine with GSM-7/UCS-2 accounting.
          </p>
        </div>

        {/* Quick Replay Scenarios */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => loadScenario("cotton")}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-lg transition"
          >
            🇮🇳 Maharashtra Cotton (SMS)
          </button>
          <button
            onClick={() => loadScenario("soybean")}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-lg transition"
          >
            🇧🇷 Brazil Soybean (WA)
          </button>
          <button
            onClick={() => loadScenario("maize")}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-lg transition"
          >
            🇿🇦 Free State Maize (WA)
          </button>
        </div>
      </div>

      {/* Main Simulator Grid */}
      <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Phone Frame UI */}
        <div className="lg:col-span-7 flex justify-center">
          <div className="w-full max-w-[390px] h-[680px] bg-black rounded-[44px] p-3.5 shadow-2xl border-4 border-slate-700 flex flex-col relative overflow-hidden">
            {/* Phone Speaker Notch */}
            <div className="absolute top-2 left-1/2 -translate-x-1/2 w-32 h-4 bg-slate-800 rounded-full z-20 flex justify-center items-center">
              <div className="w-10 h-1 bg-slate-950 rounded-full" />
            </div>

            {/* In-app Screen */}
            <div
              className={`flex-1 rounded-[34px] flex flex-col overflow-hidden relative ${
                channel === "whatsapp" ? "bg-[#0b141a]" : "bg-slate-950"
              }`}
            >
              {/* Header */}
              <div
                className={`pt-7 pb-3 px-4 flex items-center justify-between z-10 ${
                  channel === "whatsapp"
                    ? "bg-[#202c33] text-slate-100"
                    : "bg-slate-900 border-b border-slate-800 text-slate-200"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center font-bold text-xs text-white">
                    🌾
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold leading-tight">
                      {channel === "whatsapp" ? "KrishiNet Advisory" : "KrishiNet SMS"}
                    </h2>
                    <p className="text-[10px] text-emerald-400">
                      {channel === "whatsapp" ? "Verified Sovereign Public Good" : phone}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-slate-400">
                  <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700">
                    {channel}
                  </span>
                </div>
              </div>

              {/* Chat Messages Body */}
              <div className="flex-1 overflow-y-auto p-3 space-y-3 font-sans text-xs">
                {messages.map((m) => (
                  <div
                    key={m.id}
                    className={`flex flex-col ${m.sender === "user" ? "items-end" : "items-start"}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl p-2.5 shadow-sm leading-relaxed whitespace-pre-wrap ${
                        m.sender === "user"
                          ? channel === "whatsapp"
                            ? "bg-[#005c4b] text-[#e9edef] rounded-tr-none"
                            : "bg-blue-600 text-white rounded-tr-none"
                          : channel === "whatsapp"
                          ? "bg-[#202c33] text-[#e9edef] rounded-tl-none border border-slate-700/40"
                          : "bg-slate-800 text-slate-100 rounded-tl-none border border-slate-700"
                      }`}
                    >
                      {m.type === "location" && <p className="font-bold mb-1 flex items-center gap-1">📍 Shared Location Pin</p>}
                      {m.type === "image" && <p className="font-bold mb-1 flex items-center gap-1">📸 Photo Attached</p>}
                      {m.text}

                      <div className="flex items-center justify-end gap-1 mt-1 text-[9px] text-slate-400">
                        <span>{m.timestamp}</span>
                        {m.sender === "user" && <span className="text-emerald-400">✓✓</span>}
                      </div>
                    </div>

                    {/* Bot Segment Badge */}
                    {m.sender === "bot" && m.segments && (
                      <div className="text-[9px] text-slate-400 mt-0.5 px-1 font-mono">
                        {m.encoding} • {m.segments} {m.segments === 1 ? "seg" : "segs"} (${(m.cost || 0).toFixed(4)})
                      </div>
                    )}
                  </div>
                ))}
                {loading && (
                  <div className="flex items-center gap-1.5 text-xs text-slate-400 p-2">
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                    <span>KrishiNet is typing...</span>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Quick Reply Toolbar */}
              <div className="px-2 py-1.5 bg-slate-900/90 border-t border-slate-800/60 flex items-center gap-1 overflow-x-auto">
                <span className="text-[10px] text-slate-400 font-mono pl-1">Key:</span>
                {["1", "2", "3", "0", "9"].map((keyVal) => (
                  <button
                    key={keyVal}
                    onClick={() => sendMessage(keyVal)}
                    disabled={loading}
                    className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] rounded border border-slate-700 font-mono transition"
                  >
                    {keyVal === "0" ? "0 (Back)" : keyVal === "9" ? "9 (Menu)" : keyVal}
                  </button>
                ))}
                <button
                  onClick={() => sendMessage("Sending farm pin", "location", 21.15, 79.09)}
                  disabled={loading}
                  className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] rounded border border-slate-700 flex items-center gap-1 transition"
                  title="Simulate WhatsApp Location Pin"
                >
                  <MapPin className="w-3 h-3 text-red-400" /> Pin
                </button>
                <button
                  onClick={() => sendMessage("Uploaded leaf photo", "image")}
                  disabled={loading}
                  className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] rounded border border-slate-700 flex items-center gap-1 transition"
                  title="Simulate Leaf Photo"
                >
                  <ImageIcon className="w-3 h-3 text-emerald-400" /> Photo
                </button>
              </div>

              {/* Input Bar */}
              <div className="p-2.5 bg-[#202c33] border-t border-slate-700/50 flex items-center gap-2">
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                  placeholder={channel === "whatsapp" ? "Type a message..." : "Type SMS message..."}
                  className="flex-1 bg-[#2a3942] text-slate-100 placeholder-slate-400 text-xs px-3 py-2 rounded-full outline-none focus:ring-1 focus:ring-emerald-500"
                />
                <button
                  onClick={() => sendMessage()}
                  disabled={loading || !inputText.trim()}
                  className="w-8 h-8 rounded-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white flex items-center justify-center transition"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Settings, Metrics & Accounting */}
        <div className="lg:col-span-5 space-y-6">
          {/* Controls Card */}
          <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-emerald-400" />
              Channel & Delivery Parameters
            </h3>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1.5 font-medium">Channel Protocol</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setChannel("whatsapp")}
                    className={`py-2 px-3 text-xs rounded-xl font-medium border flex items-center justify-center gap-2 transition ${
                      channel === "whatsapp"
                        ? "bg-emerald-600/20 text-emerald-300 border-emerald-500/50"
                        : "bg-slate-900 border-slate-700 text-slate-400 hover:bg-slate-700"
                    }`}
                  >
                    💬 WhatsApp Cloud
                  </button>
                  <button
                    onClick={() => setChannel("sms")}
                    className={`py-2 px-3 text-xs rounded-xl font-medium border flex items-center justify-center gap-2 transition ${
                      channel === "sms"
                        ? "bg-blue-600/20 text-blue-300 border-blue-500/50"
                        : "bg-slate-900 border-slate-700 text-slate-400 hover:bg-slate-700"
                    }`}
                  >
                    📱 SMS (Feature Phone)
                  </button>
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1.5 font-medium">Farmer Phone (E.164)</label>
                <input
                  type="text"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs font-mono text-slate-200 outline-none focus:border-emerald-500"
                />
              </div>
            </div>
          </div>

          {/* Session Metrics & Cost Accounting */}
          <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-purple-400" />
              Session Telemetry & Cost Accounting
            </h3>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-700/50">
                <span className="text-[11px] text-slate-400 block">Total Segments</span>
                <span className="text-lg font-bold text-white font-mono">{totalSegments}</span>
                <span className="text-[10px] text-slate-400 block mt-0.5">GSM-7 & UCS-2</span>
              </div>
              <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-700/50">
                <span className="text-[11px] text-slate-400 block">Session Spend</span>
                <span className="text-lg font-bold text-emerald-400 font-mono">${totalCost.toFixed(4)}</span>
                <span className="text-[10px] text-slate-400 block mt-0.5">Under budget guard</span>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-700/60 text-[11px] text-slate-400 space-y-1">
              <p>• <strong>Data Minimisation:</strong> Phone stored as salted SHA-256 hash.</p>
              <p>• <strong>Retention Policy:</strong> Message bodies purged after 30 days.</p>
              <p>• <strong>Quiet Hours:</strong> Enforced between 21:00 and 06:00 local time.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
