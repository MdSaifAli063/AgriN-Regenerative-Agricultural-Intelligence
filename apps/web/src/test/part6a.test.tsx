import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusPill } from "../components/ui/StatusPill";
import { ConfidenceMeter } from "../components/ui/ConfidenceMeter";
import { ErrorState } from "../components/ui/ErrorState";
import { apiClient, setAccessToken, getAccessToken, ApiClientError } from "../lib/api/client";
import { useAuthStore } from "../lib/auth/store";

describe("Part 6A: Design System Components & Contracts", () => {
  it("StatusPill renders label, icon, and role='status' (never color alone)", () => {
    render(<StatusPill status="healthy" label="Optimum Vigour" />);
    const pill = screen.getByRole("status");
    expect(pill).toBeInTheDocument();
    expect(pill).toHaveTextContent("Optimum Vigour");
    // Verify svg icon exists inside pill
    expect(pill.querySelector("svg")).toBeTruthy();
  });

  it("ConfidenceMeter renders score and context banners based on thresholds", () => {
    const { rerender } = render(<ConfidenceMeter score={0.92} level="high" />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "92");
    expect(screen.getByText("92%")).toBeInTheDocument();

    // Medium threshold banner
    rerender(<ConfidenceMeter score={0.65} level="medium" />);
    expect(screen.getByText(/Moderate Confidence/i)).toBeInTheDocument();

    // Low threshold escalation banner + action
    const mockOfficerCall = vi.fn();
    rerender(
      <ConfidenceMeter score={0.35} level="low" onContactOfficer={mockOfficerCall} />
    );
    expect(screen.getByText(/Uncertain Diagnosis – Escalation Required/i)).toBeInTheDocument();
    const contactBtn = screen.getByText(/Contact Local Extension Officer/i);
    contactBtn.click();
    expect(mockOfficerCall).toHaveBeenCalledTimes(1);
  });

  it("ErrorState renders the API error envelope code, message, and request_id", () => {
    render(
      <ErrorState
        error={{
          code: "FIELD_GEOMETRY_INVALID",
          message: "Field area is below 0.01 ha.",
          request_id: "req-trace-abc-123",
        }}
      />
    );
    expect(screen.getByText("FIELD_GEOMETRY_INVALID")).toBeInTheDocument();
    expect(screen.getByText("Field area is below 0.01 ha.")).toBeInTheDocument();
    expect(screen.getByText("req-trace-abc-123")).toBeInTheDocument();
  });

  it("apiClient attaches in-memory access token and calls endpoint via MSW", async () => {
    setAccessToken("test-token-xyz");
    expect(getAccessToken()).toBe("test-token-xyz");

    const health = await apiClient<any>("health/demo-mode");
    expect(health.demo_mode).toBe(true);
    expect(health.country).toBe("IND");
  });

  it("useAuthStore logs in with dev credentials and updates authentication state", async () => {
    const store = useAuthStore.getState();
    await store.loginWithDev({
      role: "farmer",
      country_iso: "IND",
      full_name: "Ramesh Patel",
      phone_number: "+919876543210",
    });

    const updated = useAuthStore.getState();
    expect(updated.isAuthenticated).toBe(true);
    expect(updated.role).toBe("farmer");
    expect(updated.user?.full_name).toBe("Ramesh Patel");
  });
});
