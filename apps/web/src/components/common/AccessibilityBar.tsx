"use client";

import React, { useState, useEffect } from "react";
import { Eye, Type, Contrast } from "lucide-react";
import { cn } from "@/lib/utils";

export function AccessibilityBar({ className }: { className?: string }) {
  const [fontScale, setFontScale] = useState<"a" | "a-plus" | "a-plus-plus">("a");
  const [highContrast, setHighContrast] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const storedScale = localStorage.getItem("krishinet_font_scale") as any;
    const storedContrast = localStorage.getItem("krishinet_contrast") === "true";

    if (storedScale) {
      setFontScale(storedScale);
      applyFontScale(storedScale);
    }
    if (storedContrast) {
      setHighContrast(true);
      document.documentElement.classList.add("high-contrast");
    }
  }, []);

  const applyFontScale = (scale: "a" | "a-plus" | "a-plus-plus") => {
    document.documentElement.classList.remove("font-scale-a", "font-scale-a-plus", "font-scale-a-plus-plus");
    document.documentElement.classList.add(`font-scale-${scale}`);
    localStorage.setItem("krishinet_font_scale", scale);
  };

  const handleScaleChange = (scale: "a" | "a-plus" | "a-plus-plus") => {
    setFontScale(scale);
    applyFontScale(scale);
  };

  const toggleContrast = () => {
    const next = !highContrast;
    setHighContrast(next);
    if (next) {
      document.documentElement.classList.add("high-contrast");
    } else {
      document.documentElement.classList.remove("high-contrast");
    }
    localStorage.setItem("krishinet_contrast", String(next));
  };

  return (
    <div
      aria-label="Accessibility settings"
      className={cn("flex items-center gap-1.5 text-xs text-text", className)}
    >
      {/* High Contrast Toggle */}
      <button
        type="button"
        onClick={toggleContrast}
        aria-pressed={highContrast}
        aria-label="Toggle high contrast mode"
        title="High Contrast Mode"
        className={cn(
          "px-2.5 py-1.5 rounded-btn border text-xs font-bold inline-flex items-center gap-1 transition-colors min-h-[38px]",
          highContrast
            ? "bg-black text-white border-black"
            : "bg-white border-border text-text hover:border-primary"
        )}
      >
        <Contrast className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">Contrast</span>
      </button>

      {/* Font Size Step Toggles (A / A+ / A++) */}
      <div
        role="group"
        aria-label="Text sizing"
        className="inline-flex rounded-btn border border-border bg-white p-0.5 shadow-sm"
      >
        <button
          type="button"
          onClick={() => handleScaleChange("a")}
          aria-label="Standard text size"
          aria-pressed={fontScale === "a"}
          className={cn(
            "px-2.5 py-1 rounded text-xs font-bold transition-all min-h-[34px]",
            fontScale === "a"
              ? "bg-primary text-white"
              : "text-text hover:bg-surface-soft"
          )}
        >
          A
        </button>
        <button
          type="button"
          onClick={() => handleScaleChange("a-plus")}
          aria-label="Large text size"
          aria-pressed={fontScale === "a-plus"}
          className={cn(
            "px-2.5 py-1 rounded text-sm font-bold transition-all min-h-[34px]",
            fontScale === "a-plus"
              ? "bg-primary text-white"
              : "text-text hover:bg-surface-soft"
          )}
        >
          A+
        </button>
        <button
          type="button"
          onClick={() => handleScaleChange("a-plus-plus")}
          aria-label="Extra large text size"
          aria-pressed={fontScale === "a-plus-plus"}
          className={cn(
            "px-2.5 py-1 rounded text-base font-extrabold transition-all min-h-[34px]",
            fontScale === "a-plus-plus"
              ? "bg-primary text-white"
              : "text-text hover:bg-surface-soft"
          )}
        >
          A++
        </button>
      </div>
    </div>
  );
}
