"use client";

import React, { useState } from "react";
import { Table, LineChart, Info } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "./Card";
import { ProvenanceBadge } from "./ProvenanceBadge";
import { Button } from "./Button";
import { cn } from "@/lib/utils";
import type { Provenance } from "@krishinet/shared";

export interface ChartCardProps {
  title: string;
  description?: string;
  provenance?: Provenance;
  tableData?: Array<Record<string, any>>;
  children: React.ReactNode;
  className?: string;
}

export function ChartCard({
  title,
  description,
  provenance,
  tableData,
  children,
  className,
}: ChartCardProps) {
  const [showTable, setShowTable] = useState(false);

  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardHeader className="flex flex-row items-start justify-between pb-3 flex-wrap gap-2">
        <div>
          <CardTitle>{title}</CardTitle>
          {description && <CardDescription>{description}</CardDescription>}
        </div>

        <div className="flex items-center gap-2">
          {tableData && tableData.length > 0 && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowTable(!showTable)}
              aria-label={showTable ? "Switch to chart view" : "Switch to accessible data table view"}
              leftIcon={showTable ? <LineChart className="h-4 w-4" /> : <Table className="h-4 w-4" />}
            >
              {showTable ? "Chart View" : "Data Table"}
            </Button>
          )}

          {provenance && <ProvenanceBadge provenance={provenance} size="sm" />}
        </div>
      </CardHeader>

      <CardContent className="pt-2">
        {showTable && tableData && tableData.length > 0 ? (
          <div className="overflow-x-auto max-h-80 border rounded-xl border-border">
            <table className="w-full text-left text-xs text-text">
              <thead className="bg-surface-soft border-b border-border sticky top-0 font-semibold text-primary-dark">
                <tr>
                  {Object.keys(tableData[0]).map((key) => (
                    <th key={key} className="px-4 py-2.5 capitalize">
                      {key.replace(/_/g, " ")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {tableData.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-surface-soft/50">
                    {Object.values(row).map((val, cIdx) => (
                      <td key={cIdx} className="px-4 py-2 font-mono">
                        {String(val)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="w-full min-h-[220px]">{children}</div>
        )}
      </CardContent>
    </Card>
  );
}
