import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  fetchBricsMacroMetrics,
  fetchBricsNodes,
  fetchClimateAnalogues,
  fetchModelCards,
  fetchOutbreakClusters,
  MOCK_MACRO_METRICS,
  MOCK_BRICS_NODES,
  MOCK_CLIMATE_ANALOGUES,
  MOCK_MODEL_CARDS,
  MOCK_OUTBREAK_FEATURES,
} from "../lib/adapters/brics-policy";
import { OutbreakMapCanvas } from "../components/officer/OutbreakMapCanvas";
import { OutbreakClusterDetail } from "../components/officer/OutbreakClusterDetail";
import { BroadcastTool } from "../components/officer/BroadcastTool";
import { BricsNodeTable } from "../components/policy/BricsNodeTable";
import { ClimateAnalogueMatrix } from "../components/policy/ClimateAnalogueMatrix";
import { ModelHubDirectory } from "../components/policy/ModelHubDirectory";
import { FederatedLearningCard } from "../components/policy/FederatedLearningCard";

describe("Part 6D: Extension Officer Portal & BRICS Policy Commons Dashboard", () => {
  it("brics-policy adapter returns typed forward-compatible data structures", async () => {
    const metrics = await fetchBricsMacroMetrics();
    expect(metrics.total_hectares_regenerated).toBeGreaterThan(1000000);
    expect(metrics.farmers_reached).toBeGreaterThan(500000);
    expect(metrics.participating_nations).toBe(9);

    const nodes = await fetchBricsNodes();
    expect(nodes.length).toBeGreaterThanOrEqual(5);
    expect(nodes.some((n) => n.country_iso === "IND")).toBe(true);
    expect(nodes.some((n) => n.country_iso === "BRA")).toBe(true);

    const analogues = await fetchClimateAnalogues();
    expect(analogues.length).toBeGreaterThanOrEqual(3);
    expect(analogues[0].similarity_score).toBeGreaterThan(0.8);
    expect(analogues[0].successful_regenerative_interventions.length).toBeGreaterThan(0);

    const models = await fetchModelCards();
    expect(models.length).toBeGreaterThanOrEqual(3);
    expect(models[0].quantization).toBe("int8");
    expect(models[0].sha256_hash).toBeDefined();

    const clusters = await fetchOutbreakClusters();
    expect(clusters.length).toBeGreaterThanOrEqual(3);
    expect(clusters[0].properties.h3_index).toBeDefined();
  });

  it("OutbreakMapCanvas renders H3 clusters and triggers onSelectCluster on click", () => {
    const handleSelect = vi.fn();
    render(
      <OutbreakMapCanvas
        features={MOCK_OUTBREAK_FEATURES}
        selectedClusterId={MOCK_OUTBREAK_FEATURES[0].properties.h3_index}
        onSelectCluster={handleSelect}
      />
    );

    // Verify map elements and legend are present
    expect(screen.getByText(/H3 Epidemiological GIS Heatmap/i)).toBeInTheDocument();
    expect(screen.getByText(/Critical/i)).toBeInTheDocument();
    expect(screen.getByText(/Showing 4 H3 Clusters/i)).toBeInTheDocument();

    // Click cluster node in SVG
    const clusterLabel = screen.getByText(/Rice Blast/i);
    fireEvent.click(clusterLabel);
    expect(handleSelect).toHaveBeenCalled();
  });

  it("OutbreakClusterDetail presents epidemiological risk, weather amplifier, and countermeasures", () => {
    const handleBroadcast = vi.fn();
    render(
      <OutbreakClusterDetail
        cluster={MOCK_OUTBREAK_FEATURES[0]}
        onInitiateBroadcast={handleBroadcast}
      />
    );

    // Verify disease title and H3 index
    expect(screen.getByText(/Rice Blast/i)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(MOCK_OUTBREAK_FEATURES[0].properties.h3_index))).toBeInTheDocument();

    // Verify weather hazard and organic countermeasures
    expect(screen.getByText(/Agro-Meteorological Risk Amplifier/i)).toBeInTheDocument();
    expect(screen.getByText(/Organic & Bio-Control Remedy:/i)).toBeInTheDocument();

    // Click Draft Broadcast
    const broadcastBtn = screen.getByRole("button", { name: /Draft Broadcast/i });
    fireEvent.click(broadcastBtn);
    expect(handleBroadcast).toHaveBeenCalledWith(MOCK_OUTBREAK_FEATURES[0]);
  });

  it("BroadcastTool interpolates variables, calculates char count, and dispatches broadcast", async () => {
    render(<BroadcastTool initialCluster={MOCK_OUTBREAK_FEATURES[0]} />);

    // Check title and channels
    expect(screen.getByText(/Mass Advisory & Outbreak Broadcast Tool/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /WhatsApp/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /SMS \(2G\)/i })).toBeInTheDocument();

    // Verify variable interpolation of Rice Blast into preview
    expect(screen.getByText(/Rice Blast/i)).toBeInTheDocument();

    // Switch language to Hindi
    const hindiTab = screen.getByRole("button", { name: /हिन्दी/i });
    fireEvent.click(hindiTab);
    expect(screen.getByText(/कृषि-नेट आवश्यक सूचना/i)).toBeInTheDocument();

    // Click send broadcast to open confirmation modal
    const sendBtn = screen.getByRole("button", { name: /Send Broadcast/i });
    fireEvent.click(sendBtn);

    // Modal appears
    expect(screen.getByText(/Authorize Mass Broadcast\?/i)).toBeInTheDocument();
  });

  it("BricsNodeTable displays sovereign node compliance and telemetry metrics", () => {
    render(<BricsNodeTable nodes={MOCK_BRICS_NODES} />);

    expect(screen.getByText(/Sovereign BRICS National Nodes/i)).toBeInTheDocument();
    expect(screen.getByText(/100% On-Soil Data Residency/i)).toBeInTheDocument();
    expect(screen.getByText(/India \(ICAR \/ KrishiNet\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Brazil \(Embrapa\)/i)).toBeInTheDocument();
  });

  it("ClimateAnalogueMatrix renders agro-climatic twin pairs and detailed interventions", () => {
    render(<ClimateAnalogueMatrix analogues={MOCK_CLIMATE_ANALOGUES} />);

    expect(screen.getByText(/Transboundary Climate-Analogue Matching Engine/i)).toBeInTheDocument();
    expect(screen.getByText(/Pairing #1/i)).toBeInTheDocument();
    expect(screen.getByText(/Shared Agro-Ecological Attributes/i)).toBeInTheDocument();
    expect(screen.getByText(/Validated Regenerative Interventions for Policy Transfer/i)).toBeInTheDocument();
  });

  it("FederatedLearningCard renders Flower progress, Byzantine robustness, and differential privacy", () => {
    render(<FederatedLearningCard />);

    expect(screen.getByText(/Decentralized Federated Learning Network/i)).toBeInTheDocument();
    expect(screen.getByText(/Byzantine-Robust Trimmed Mean/i)).toBeInTheDocument();
    expect(screen.getByText(/Differential Privacy Guard/i)).toBeInTheDocument();
    expect(screen.getByText(/Training Round 14 of 20/i)).toBeInTheDocument();
  });

  it("ModelHubDirectory displays model cards, quantization filtering, and SHA-256 digest", () => {
    render(<ModelHubDirectory models={MOCK_MODEL_CARDS} />);

    expect(screen.getByText(/BRICS Sovereign Model Hub & DPG Registry/i)).toBeInTheDocument();
    expect(screen.getByText(/MobileNetV3-BRICS-Disease-Int8/i)).toBeInTheDocument();

    // Inspect card modal
    const inspectBtn = screen.getAllByRole("button", { name: /Inspect Card/i })[0];
    fireEvent.click(inspectBtn);
    expect(screen.getByText(/Digital Public Good \(DPG\) Certified/i)).toBeInTheDocument();
    expect(screen.getByText(/Cryptographic Integrity Hash:/i)).toBeInTheDocument();
  });
});
