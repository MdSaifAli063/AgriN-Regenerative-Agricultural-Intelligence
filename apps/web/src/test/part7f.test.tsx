import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  simulateFederatedLearning,
  fetchEgressReport,
  fetchConsentLedger,
  verifyConsentLedger,
} from "../lib/adapters/brics-policy";
import { EgressAuditPanel } from "../components/policy/EgressAuditPanel";
import { ConsentLedgerPanel } from "../components/policy/ConsentLedgerPanel";
import { FederatedLearningCard } from "../components/policy/FederatedLearningCard";
import BricsPolicyDashboardPage from "../app/[locale]/(policy)/brics/page";

describe("Part 7F: Frontend Wiring, Sovereign Audit Panels & Federated Learning Live Demo", () => {
  it("brics-policy adapter exposes typed federation endpoints for simulation, egress and consent", async () => {
    // 1. Simulation
    const sim = await simulateFederatedLearning(3, 0.50);
    expect(sim.simulation_id).toBeDefined();
    expect(sim.rounds_executed).toBe(3);
    expect(sim.zero_raw_data_transferred).toBe(true);
    expect(sim.total_epsilon_consumed).toBeLessThanOrEqual(1.0);
    expect(sim.participating_nodes.length).toBeGreaterThanOrEqual(3);

    // 2. Egress report
    const egress = await fetchEgressReport();
    expect(egress.node_id).toBeDefined();
    expect(egress.zero_pii_confirmed).toBe(true);
    expect(egress.passed_events_count).toBeGreaterThan(0);
    expect(egress.recent_audit_records.length).toBeGreaterThan(0);

    // 3. Consent ledger & verify
    const ledger = await fetchConsentLedger();
    expect(ledger.length).toBeGreaterThanOrEqual(2);
    expect(ledger[0].block_hash).toBeDefined();
    expect(ledger[0].receipt_id).toBeDefined();

    const verify = await verifyConsentLedger();
    expect(verify.is_valid).toBe(true);
    expect(verify.integrity_status).toContain("VERIFIED");
  });

  it("EgressAuditPanel renders Sovereign Perimeter guarantees and immutable audit records", async () => {
    render(<EgressAuditPanel />);

    // Header
    expect(screen.getByText(/Sovereign Egress Gateway/i)).toBeInTheDocument();
    expect(screen.getByText(/What Leaves My Country/i)).toBeInTheDocument();

    // 4 Guarantees
    expect(screen.getByText(/Zero Raw PII/i)).toBeInTheDocument();
    expect(screen.getByText(/k-Anonymity Guard/i)).toBeInTheDocument();
    expect(screen.getByText(/Data Sharing Agreements/i)).toBeInTheDocument();
    expect(screen.getByText(/Audit Trail/i)).toBeInTheDocument();

    // Recent egress records
    await waitFor(() => {
      expect(screen.getByText(/Recent Transboundary Egress Events/i)).toBeInTheDocument();
    });
  });

  it("ConsentLedgerPanel displays Kantara-compliant hash chain and verifies cryptographic integrity", async () => {
    render(<ConsentLedgerPanel />);

    expect(screen.getByText(/Kantara-Compliant Consent Ledger & Receipts/i)).toBeInTheDocument();
    expect(screen.getByText(/Append-Only Cryptographic Block Chain/i)).toBeInTheDocument();

    // Run verification trigger
    const verifyBtn = screen.getByRole("button", { name: /Verify Chain Integrity/i });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(screen.getByText(/VERIFIED_TAMPER_EVIDENT/i)).toBeInTheDocument();
      expect(screen.getByText(/UNBROKEN HASH CHAIN/i)).toBeInTheDocument();
    });
  });

  it("FederatedLearningCard supports interactive simulation trigger with live convergence metrics", async () => {
    render(<FederatedLearningCard />);

    expect(screen.getByText(/Decentralized Federated Learning Network/i)).toBeInTheDocument();
    expect(screen.getByText(/Byzantine-Robust Trimmed Mean/i)).toBeInTheDocument();

    // Click trigger simulation
    const triggerBtn = screen.getByRole("button", { name: /Trigger Simulation Round/i });
    fireEvent.click(triggerBtn);

    await waitFor(() => {
      expect(screen.getByText(/SIMULATION COMPLETE/i)).toBeInTheDocument();
      expect(screen.getByText(/Federated Cycle Completed/i)).toBeInTheDocument();
      expect(screen.getByText(/Zero Raw Data Transferred: 100% Sovereign/i)).toBeInTheDocument();
    });
  });

  it("BricsPolicyDashboardPage coordinates all 6 sovereign policy tabs", async () => {
    render(<BricsPolicyDashboardPage />);

    // Verify main header and macro KPIs
    expect(screen.getByText(/BRICS Regenerative Agricultural Intelligence Network/i)).toBeInTheDocument();
    expect(screen.getByText(/Regenerated Land/i)).toBeInTheDocument();
    expect(screen.getByText(/Farmers Connected/i)).toBeInTheDocument();

    // Verify tabs
    const egressTab = screen.getByRole("button", { name: /Sovereign Egress Audit/i });
    fireEvent.click(egressTab);
    expect(screen.getByText(/What Leaves My Country/i)).toBeInTheDocument();

    const consentTab = screen.getByRole("button", { name: /Consent Ledger & Kantara/i });
    fireEvent.click(consentTab);
    expect(screen.getByText(/Kantara-Compliant Consent Ledger/i)).toBeInTheDocument();
  });
});
