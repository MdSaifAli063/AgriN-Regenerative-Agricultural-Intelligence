"use client";

import React, { useState } from "react";
import { AlertTriangle, ZoomIn, ZoomOut, RotateCcw, ShieldAlert, Flame } from "lucide-react";
import type { GeoJsonOutbreakFeature } from "@krishinet/shared";
import { cn } from "@/lib/utils";

interface OutbreakMapCanvasProps {
  features: GeoJsonOutbreakFeature[];
  selectedClusterId: string | null;
  onSelectCluster: (cluster: GeoJsonOutbreakFeature) => void;
  className?: string;
}

export function OutbreakMapCanvas({
  features,
  selectedClusterId,
  onSelectCluster,
  className,
}: OutbreakMapCanvasProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  // Map coordinates normalization for demo district canvas
  // Central focus on Indian agro-corridor (Maharashtra / Vidarbha, 78°E, 20°N) and transboundary
  const getCoordinates = (coords: [number, number], index: number) => {
    // Generate deterministic relative SVG layout coordinates (0-800 x 0-500)
    // Scale longitude and latitude to canvas space with slight jitter fallback for demo
    const [lon, lat] = coords;
    
    // Default district bounds around Central India / BRICS demo hubs
    // If coords are global, project gracefully onto SVG viewbox
    let x = ((lon - 70) / 25) * 800;
    let y = ((30 - lat) / 20) * 500;

    // Fallback bounds clamp to ensure visibility on the canvas
    if (x < 60 || x > 740 || y < 60 || y > 440) {
      // Deterministic spread based on feature index for transboundary demo nodes
      x = 100 + (index % 5) * 140;
      y = 100 + Math.floor(index / 5) * 110;
    }

    return { x, y };
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return { fill: "#EF4444", stroke: "#B91C1C", pulse: true, label: "Critical" };
      case "high":
        return { fill: "#F97316", stroke: "#C2410C", pulse: false, label: "High" };
      case "medium":
      case "moderate":
        return { fill: "#FBBF24", stroke: "#D97706", pulse: false, label: "Medium" };
      default:
        return { fill: "#10B981", stroke: "#047857", pulse: false, label: "Low" };
    }
  };

  return (
    <div
      className={cn(
        "relative w-full h-[460px] bg-slate-900 rounded-2xl overflow-hidden border border-slate-800 select-none shadow-inner",
        className
      )}
    >
      {/* Map Header / District Overlay */}
      <div className="absolute top-3 left-3 z-10 bg-slate-800/90 backdrop-blur-md px-3 py-2 rounded-xl border border-slate-700/80 text-white shadow-lg pointer-events-none">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            H3 Epidemiological GIS Heatmap
          </span>
        </div>
        <div className="text-[11px] text-slate-400 mt-0.5">
          Resolution 6 Coarsening • Differential Privacy k=5
        </div>
      </div>

      {/* Map Controls */}
      <div className="absolute top-3 right-3 z-10 flex flex-col gap-1.5 bg-slate-800/90 backdrop-blur-md p-1 rounded-xl border border-slate-700 shadow-lg">
        <button
          onClick={() => setZoom((z) => Math.min(z + 0.25, 2.5))}
          className="p-2 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="h-4 w-4" />
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(z - 0.25, 0.75))}
          className="p-2 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="h-4 w-4" />
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
          className="p-2 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition-colors"
          title="Reset View"
        >
          <RotateCcw className="h-4 w-4" />
        </button>
      </div>

      {/* Map SVG Canvas */}
      <svg
        viewBox="0 0 800 500"
        className="w-full h-full cursor-grab active:cursor-grabbing transition-transform duration-200"
        style={{
          transform: `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)`,
        }}
      >
        <defs>
          {/* Subtle topo grid pattern */}
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path
              d="M 40 0 L 0 0 0 40"
              fill="none"
              stroke="rgba(255, 255, 255, 0.04)"
              strokeWidth="1"
            />
          </pattern>
          {/* Pulsing glow filter */}
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Background Grid */}
        <rect width="100%" height="100%" fill="url(#grid)" />

        {/* Mock Agro-Climatic Ecological Zone Polygons */}
        <path
          d="M 80 120 Q 240 70, 420 140 T 720 220 L 760 380 Q 520 440, 360 410 T 60 340 Z"
          fill="rgba(16, 185, 129, 0.05)"
          stroke="rgba(16, 185, 129, 0.2)"
          strokeWidth="1.5"
          strokeDasharray="4 4"
        />
        <path
          d="M 180 200 Q 320 160, 480 230 T 640 320 L 580 410 Q 380 430, 240 380 Z"
          fill="rgba(245, 158, 11, 0.04)"
          stroke="rgba(245, 158, 11, 0.15)"
          strokeWidth="1"
        />

        {/* Zone Labels */}
        <text x="120" y="160" fill="rgba(255,255,255,0.2)" fontSize="12" fontWeight="600">
          Vertisol Cotton-Soybean Belt
        </text>
        <text x="440" y="360" fill="rgba(255,255,255,0.2)" fontSize="12" fontWeight="600">
          Canal-Irrigated Agro-Zone
        </text>

        {/* H3 Outbreak Cluster Nodes */}
        {features.map((feat, idx) => {
          const { x, y } = getCoordinates(feat.geometry.coordinates, idx);
          const isSelected = selectedClusterId === feat.properties.h3_index;
          const style = getSeverityColor(feat.properties.severity);

          return (
            <g
              key={feat.properties.h3_index || idx}
              onClick={() => onSelectCluster(feat)}
              className="cursor-pointer group"
            >
              {/* Outer pulsing ring for critical/spiking clusters */}
              {(style.pulse || feat.properties.is_spike) && (
                <circle
                  cx={x}
                  cy={y}
                  r="34"
                  fill="none"
                  stroke={style.fill}
                  strokeWidth="1.5"
                  className="animate-ping opacity-60"
                />
              )}

              {/* H3 Hexagonal boundary representation */}
              <polygon
                points={`
                  ${x},${y - 24}
                  ${x + 20},${y - 12}
                  ${x + 20},${y + 12}
                  ${x},${y + 24}
                  ${x - 20},${y + 12}
                  ${x - 20},${y - 12}
                `}
                fill={isSelected ? `${style.fill}44` : `${style.fill}22`}
                stroke={isSelected ? "#FFFFFF" : style.stroke}
                strokeWidth={isSelected ? 3 : 1.5}
                filter={isSelected ? "url(#glow)" : undefined}
                className="transition-all duration-200 group-hover:stroke-white"
              />

              {/* Core Node Circle */}
              <circle
                cx={x}
                cy={y}
                r={isSelected ? "13" : "10"}
                fill={style.fill}
                stroke="#FFFFFF"
                strokeWidth="2"
                className="transition-all duration-200"
              />

              {/* Reported Cases Count Badge */}
              <text
                x={x}
                y={y + 3.5}
                textAnchor="middle"
                fill="#FFFFFF"
                fontSize="10"
                fontWeight="bold"
                className="pointer-events-none select-none"
              >
                {feat.properties.reported_cases}
              </text>

              {/* Spike Indicator Icon */}
              {feat.properties.is_spike && (
                <g transform={`translate(${x + 12}, ${y - 18})`}>
                  <circle cx="6" cy="6" r="8" fill="#EF4444" stroke="#FFFFFF" strokeWidth="1.5" />
                  <Flame className="h-3 w-3 text-white" x="1.5" y="1.5" />
                </g>
              )}

              {/* Node Label Tooltip Overlay */}
              <g
                transform={`translate(${x}, ${y - 32})`}
                className={cn(
                  "pointer-events-none transition-opacity duration-200",
                  isSelected ? "opacity-100" : "opacity-80 group-hover:opacity-100"
                )}
              >
                <rect
                  x="-75"
                  y="-18"
                  width="150"
                  height="20"
                  rx="6"
                  fill="rgba(15, 23, 42, 0.9)"
                  stroke={isSelected ? style.fill : "rgba(255,255,255,0.2)"}
                  strokeWidth="1"
                />
                <text
                  x="0"
                  y="-4"
                  textAnchor="middle"
                  fill="#FFFFFF"
                  fontSize="10"
                  fontWeight="600"
                >
                  {feat.properties.disease_name.split("(")[0]}
                </text>
              </g>
            </g>
          );
        })}
      </svg>

      {/* Map Legend Footer */}
      <div className="absolute bottom-3 left-3 right-3 z-10 flex flex-wrap items-center justify-between gap-3 bg-slate-900/90 backdrop-blur-md px-4 py-2.5 rounded-xl border border-slate-800 text-xs text-slate-300">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Risk Severity:
          </span>
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full bg-red-500" />
            <span>Critical (&gt;25 cases)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full bg-orange-500" />
            <span>High (15-25)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full bg-amber-400" />
            <span>Medium (5-14)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full bg-emerald-500" />
            <span>Low (&lt;5)</span>
          </div>
          <div className="flex items-center gap-1.5 text-red-400 font-semibold">
            <Flame className="h-3.5 w-3.5 text-red-500" />
            <span>Outbreak Spike Alert</span>
          </div>
        </div>
        <div className="text-[11px] text-slate-400 font-mono">
          Showing {features.length} H3 Clusters
        </div>
      </div>
    </div>
  );
}
