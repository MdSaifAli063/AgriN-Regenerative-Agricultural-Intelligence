import React from "react";
import { ShieldCheck, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export function DisclaimerFooter({ className }: { className?: string }) {
  return (
    <footer
      className={cn(
        "mt-12 py-8 px-4 border-t border-border bg-surface-soft/60 text-xs text-text-muted leading-relaxed",
        className
      )}
    >
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-start justify-between gap-6">
        <div className="space-y-2 max-w-2xl">
          <div className="flex items-center gap-2 text-primary-dark font-bold text-sm">
            <ShieldCheck className="h-4 w-4 text-primary" />
            <span>Sovereign Digital Public Good (DPG) Notice</span>
          </div>
          <p>
            KrishiNet-BRICS AI recommendations are algorithmic agronomic guidance designed to assist smallholder farming communities. They do <strong>not</strong> substitute certified agricultural extension officer consultations, chemical pesticide regulatory guidelines, or official national agro-meteorological directives.
          </p>
          <p className="text-[11px] text-text-muted/80">
            Open Standards: STAC 1.0.0 | OGC GeoJSON | W3C JSON-LD / FAO AGROVOC | OpenAPI 3.1
          </p>
        </div>

        <div className="text-right sm:text-right space-y-1 text-[11px]">
          <div className="font-semibold text-text">KrishiNet-BRICS Alliance</div>
          <div>India • Brazil • South Africa</div>
          <div className="text-primary font-medium">Licensed under MIT / Apache-2.0</div>
        </div>
      </div>
    </footer>
  );
}
