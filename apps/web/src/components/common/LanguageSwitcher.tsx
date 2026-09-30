"use client";

import React, { useState } from "react";
import { Globe, Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface LocaleOption {
  code: string;
  name: string;
  nativeName: string;
  flag: string;
  dir: "ltr" | "rtl";
}

export const SUPPORTED_LOCALES: LocaleOption[] = [
  { code: "en", name: "English", nativeName: "English", flag: "🌐", dir: "ltr" },
  { code: "hi", name: "Hindi", nativeName: "हिन्दी", flag: "🇮🇳", dir: "ltr" },
  { code: "pt", name: "Portuguese", nativeName: "Português", flag: "🇧🇷", dir: "ltr" },
  { code: "mr", name: "Marathi", nativeName: "मराठी", flag: "🇮🇳", dir: "ltr" },
  { code: "ar", name: "Arabic", nativeName: "العربية", flag: "🇪🇬", dir: "rtl" },
  { code: "fa", name: "Persian", nativeName: "فارسی", flag: "🇮🇷", dir: "rtl" },
  { code: "ru", name: "Russian", nativeName: "Русский", flag: "🇷🇺", dir: "ltr" },
  { code: "zh", name: "Chinese", nativeName: "中文", flag: "🇨🇳", dir: "ltr" },
  { code: "am", name: "Amharic", nativeName: "አማርኛ", flag: "🇪🇹", dir: "ltr" },
  { code: "sw", name: "Swahili", nativeName: "Kiswahili", flag: "🇰🇪", dir: "ltr" },
  { code: "zu", name: "Zulu", nativeName: "isiZulu", flag: "🇿🇦", dir: "ltr" },
  { code: "af", name: "Afrikaans", nativeName: "Afrikaans", flag: "🇿🇦", dir: "ltr" },
];

export function LanguageSwitcher({
  currentLocale = "en",
  onLocaleChange,
  className,
}: {
  currentLocale?: string;
  onLocaleChange?: (locale: string) => void;
  className?: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [selected, setSelected] = useState(currentLocale);

  const current =
    SUPPORTED_LOCALES.find((l) => l.code === selected) || SUPPORTED_LOCALES[0];

  const handleSelect = (code: string) => {
    setSelected(code);
    setIsOpen(false);
    if (typeof window !== "undefined") {
      localStorage.setItem("krishinet_locale", code);
      // If running with Next-intl routing, redirect or trigger callback
      if (onLocaleChange) {
        onLocaleChange(code);
      } else {
        const path = window.location.pathname;
        const segments = path.split("/").filter(Boolean);
        if (segments.length > 0 && SUPPORTED_LOCALES.some((l) => l.code === segments[0])) {
          segments[0] = code;
          window.location.pathname = "/" + segments.join("/");
        } else {
          window.location.pathname = `/${code}`;
        }
      }
    }
  };

  return (
    <div className={cn("relative inline-block text-left", className)}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label="Select language"
        className="inline-flex items-center gap-2 px-3 py-2 text-sm font-semibold rounded-btn bg-white border border-border hover:border-primary text-text shadow-sm focus:outline-none focus:ring-2 focus:ring-primary min-h-[44px]"
      >
        <Globe className="h-4 w-4 text-primary" />
        <span className="text-base mr-0.5">{current.flag}</span>
        <span className="hidden sm:inline">{current.nativeName}</span>
        <span className="sm:hidden uppercase">{current.code}</span>
        <ChevronDown className="h-3.5 w-3.5 text-text-muted" />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <ul
            role="listbox"
            aria-label="Available languages"
            className="absolute right-0 mt-2 w-56 max-h-72 overflow-y-auto bg-white border border-border rounded-xl shadow-card-hover z-50 py-1.5 focus:outline-none divide-y divide-border/40 text-sm"
          >
            {SUPPORTED_LOCALES.map((locale) => {
              const isSelected = locale.code === selected;
              return (
                <li
                  key={locale.code}
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => handleSelect(locale.code)}
                  className={cn(
                    "flex items-center justify-between px-3.5 py-2.5 cursor-pointer transition-colors select-none",
                    isSelected
                      ? "bg-primary-light text-primary-dark font-bold"
                      : "hover:bg-surface-soft text-text"
                  )}
                >
                  <div className="flex items-center gap-2.5">
                    <span className="text-lg">{locale.flag}</span>
                    <div>
                      <div className="font-medium">{locale.nativeName}</div>
                      <div className="text-[11px] text-text-muted">
                        {locale.name} {locale.dir === "rtl" ? "• RTL" : ""}
                      </div>
                    </div>
                  </div>
                  {isSelected && <Check className="h-4 w-4 text-primary stroke-[3]" />}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}
