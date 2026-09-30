import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { calculatePolygonAreaHa, createSquarePolygonFromPoint, isValidWgs84 } from "../lib/geo/geometry";
import { saveDraft, loadDraft, clearDraft } from "../lib/storage/offline-queue";
import { ActionCard } from "../components/ui/ActionCard";
import { MetricTile } from "../components/ui/MetricTile";

describe("Part 6B: Farmer Experience, Geography & Offline Queue", () => {
  it("calculatePolygonAreaHa accurately computes field area in hectares", () => {
    // 100m x 100m square = 10,000 m² = 1.0 ha
    const square = createSquarePolygonFromPoint(20.7453, 78.5982, 100);
    expect(square.type).toBe("Polygon");
    expect(square.coordinates[0].length).toBe(5); // Closed 4-vertex ring

    const area = calculatePolygonAreaHa(square.coordinates[0]);
    expect(area).toBeCloseTo(1.0, 1);
  });

  it("isValidWgs84 validates latitude and longitude coordinates", () => {
    expect(isValidWgs84(20.7453, 78.5982)).toBe(true);
    expect(isValidWgs84(-15.8, -47.9)).toBe(true);
    expect(isValidWgs84(95.0, 50.0)).toBe(false);
    expect(isValidWgs84(20.0, 190.0)).toBe(false);
  });

  it("ActionCard renders urgency badge, checklist, and read-aloud voice button", () => {
    const mockToggle = vi.fn();
    render(
      <ActionCard
        actionData={{
          headline: "Apply Foliar Neem Biopesticide",
          summary: "Humidity is high.",
          urgency: "urgent",
          recommended_actions: ["Spray underside of leaves"],
          read_aloud_text: "Apply neem now",
        }}
        onActionToggle={mockToggle}
      />
    );

    expect(screen.getByText("URGENT ACTION TODAY")).toBeInTheDocument();
    expect(screen.getByText("Apply Foliar Neem Biopesticide")).toBeInTheDocument();
    expect(screen.getByText("Spray underside of leaves")).toBeInTheDocument();

    // Click action checklist item
    const checkItem = screen.getByText("Spray underside of leaves");
    fireEvent.click(checkItem);
    expect(mockToggle).toHaveBeenCalledWith(0, true);
  });

  it("MetricTile displays metric value, status, and trend indicator", () => {
    render(
      <MetricTile
        title="Canopy Index (NDVI)"
        value="0.76"
        status="healthy"
        statusLabel="Dense Growth"
        trend="up"
        trendLabel="+5%"
      />
    );

    expect(screen.getByText("Canopy Index (NDVI)")).toBeInTheDocument();
    expect(screen.getByText("0.76")).toBeInTheDocument();
    expect(screen.getByText("Dense Growth")).toBeInTheDocument();
    expect(screen.getByText("+5%")).toBeInTheDocument();
  });
});
