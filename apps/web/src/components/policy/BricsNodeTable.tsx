"use client";

import React from "react";
import { Building2, ShieldCheck, CheckCircle2, RefreshCw, Globe, Server } from "lucide-react";
import type { BricsNodeSummary } from "@krishinet/shared";
import { StatusPill } from "@/components/ui/StatusPill";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";

interface BricsNodeTableProps {
  nodes: BricsNodeSummary[];
  className?: string;
}

export function BricsNodeTable({ nodes, className }: BricsNodeTableProps) {
  return (
    <Card className="p-6 bg-white border border-border shadow-card space-y-4">
      <CardHeader className="p-0 border-none">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <CardTitle className="text-lg font-extrabold text-primary-dark flex items-center gap-2">
              <Globe className="h-5 w-5 text-primary" />
              <span>Sovereign BRICS National Nodes</span>
            </CardTitle>
            <CardDescription>
              Decentralized agricultural intelligence stations operating under strict national data sovereignty boundaries.
            </CardDescription>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-primary font-bold bg-primary-light px-3 py-1 rounded-full shrink-0">
            <ShieldCheck className="h-4 w-4" />
            <span>100% On-Soil Data Residency</span>
          </div>
        </div>
      </CardHeader>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-border bg-surface-soft/60 text-text-muted uppercase text-[10px] font-bold">
              <th className="py-3 px-3">Sovereign Node & Institution</th>
              <th className="py-3 px-3">Node Status</th>
              <th className="py-3 px-3 text-right">Smallholders</th>
              <th className="py-3 px-3 text-right">Hectares Regenerated</th>
              <th className="py-3 px-3 text-right">Water Saved (ML)</th>
              <th className="py-3 px-3 text-right">CO₂e Sequestered</th>
              <th className="py-3 px-3 text-center">Federated Models</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {nodes.map((node) => (
              <tr key={node.country_iso} className="hover:bg-surface-soft/40 transition-colors">
                <td className="py-3.5 px-3">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-xs font-bold px-1.5 py-0.5 rounded bg-surface-soft border border-border">
                      {node.country_iso}
                    </span>
                    <div>
                      <span className="font-bold text-text text-sm block">
                        {node.country_name}
                      </span>
                      <span className="text-[10px] text-text-muted flex items-center gap-1">
                        <Server className="h-2.5 w-2.5" />
                        Keycloak Sovereign OIDC Realm Active
                      </span>
                    </div>
                  </div>
                </td>
                <td className="py-3.5 px-3">
                  <StatusPill
                    status={node.status === "active" ? "healthy" : "watch"}
                    label={node.status.toUpperCase()}
                    size="sm"
                  />
                </td>
                <td className="py-3.5 px-3 text-right font-mono font-semibold text-text">
                  {node.farmers_count.toLocaleString()}
                </td>
                <td className="py-3.5 px-3 text-right font-mono font-semibold text-text">
                  {node.hectares_regenerated.toLocaleString()} ha
                </td>
                <td className="py-3.5 px-3 text-right font-mono font-semibold text-primary">
                  {node.water_saved_megalitres.toLocaleString()} ML
                </td>
                <td className="py-3.5 px-3 text-right font-mono font-semibold text-emerald-700">
                  {node.co2e_sequestered_tonnes.toLocaleString()} t
                </td>
                <td className="py-3.5 px-3 text-center">
                  <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-primary-light text-primary-dark font-mono font-bold text-xs">
                    {node.participating_models}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
