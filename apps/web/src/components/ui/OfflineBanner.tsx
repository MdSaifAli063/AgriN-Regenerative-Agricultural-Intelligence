"use client";

import React, { useEffect, useState } from "react";
import { WifiOff, RefreshCw, X } from "lucide-react";
import { cn } from "@/lib/utils";

export function OfflineBanner() {
  const [isOffline, setIsOffline] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleOnline = () => {
      setIsOffline(false);
      setIsDismissed(false);
    };
    const handleOffline = () => {
      setIsOffline(true);
      setIsDismissed(false);
    };

    setIsOffline(!navigator.onLine);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (!isOffline || isDismissed) return null;

  return (
    <div
      role="alert"
      className="bg-[#FEF3C7] border-b border-[#FCD34D] text-[#92400E] px-4 py-2 text-sm flex items-center justify-between shadow-sm animate-in slide-in-from-top-2 duration-200"
    >
      <div className="flex items-center gap-2.5 mx-auto">
        <WifiOff className="h-4 w-4 text-[#F59E0B] flex-shrink-0" />
        <span className="font-medium">
          Offline Mode Active – Viewing cached agronomic data. Local scans and actions are saved and will sync automatically when connection restores.
        </span>
      </div>
      <button
        type="button"
        onClick={() => setIsDismissed(true)}
        aria-label="Dismiss offline banner"
        className="p-1 rounded-md hover:bg-[#FDE68A] text-[#92400E]"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
