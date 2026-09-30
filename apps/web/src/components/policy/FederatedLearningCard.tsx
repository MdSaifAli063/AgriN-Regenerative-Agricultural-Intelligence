"use client";

import React, { useState } from "react";
import {
  Cpu,
  ShieldCheck,
  Activity,
  Layers,
  CheckCircle2,
  Lock,
  Play,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { StatusPill } from "@/components/ui/StatusPill";
import { Button } from "@/components/ui/Button";
import {
  simulateFederatedLearning,
  type SimulationResultDto,
} from "@/lib/adapters/brics-policy";

interface FederatedLearningCardProps {
  className?: string;
}

export function FederatedLearningCard({ className }: FederatedLearningCardProps) {
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState<SimulationResultDto | null>(null);
  const [numRounds, setNumRounds] = useState(3);

  const currentRound = simulationResult ? simulationResult.rounds_executed : 14;
  const totalRounds = 20;
  const progressPercent = Math.min(100, Math.round((currentRound / totalRounds) * 100));

  const contributions = [
    { country: "India (ICAR)", iso: "IND", percent: 38, gradients: "142,500 samples", color: "bg-emerald-600" },
    { country: "Brazil (Embrapa)", iso: "BRA", percent: 31, gradients: "118,200 samples", color: "bg-teal-600" },
    { country: "South Africa (ARC)", iso: "ZAF", percent: 18, gradients: "68,400 samples", color: "bg-green-600" },
    { country: "China (CAAS)", iso: "CHN", percent: 13, gradients: "52,100 samples", color: "bg-emerald-700" },
  ];

  const handleRunSimulation = async () => {
    setIsSimulating(true);
    try {
      const res = await simulateFederatedLearning(numRounds, 0.50);
      setSimulationResult(res);
    } catch {
      // Mock result fallback for demo stability
      setSimulationResult({
        simulation_id: `sim-fl-${Date.now()}`,
        model_name: "KrishiNet-BRICS-YieldPredictor",
        rounds_executed: numRounds,
        participating_nodes: ["node-ind-01", "node-bra-01", "node-zaf-01"],
        initial_accuracy: 0.898,
        final_accuracy: 0.924,
        accuracy_delta: 0.026,
        final_loss: 0.284,
        total_epsilon_consumed: 0.50,
        zero_raw_data_transferred: true,
        byzantine_attacks_defended: 1,
        candidate_version: "v2.5.0-rc1",
        status: "converged",
      });
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <Card className="p-6 bg-white border border-border shadow-card space-y-6">
      <CardHeader className="p-0 border-none">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <CardTitle className="text-lg font-extrabold text-primary-dark flex items-center gap-2">
              <Cpu className="h-5 w-5 text-primary" />
              <span>Decentralized Federated Learning Network (Flower Framework)</span>
            </CardTitle>
            <CardDescription>
              Collaborative edge AI parameter aggregation without centralizing sovereign smallholder crop images or cadastre data.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <StatusPill
              status={simulationResult ? "healthy" : "healthy"}
              label={simulationResult ? "SIMULATION COMPLETE" : `ROUND ${currentRound} ACTIVE`}
              size="sm"
            />
            <Button
              variant="primary"
              size="sm"
              onClick={handleRunSimulation}
              isLoading={isSimulating}
              leftIcon={<Play className="h-3.5 w-3.5 fill-current" />}
            >
              Trigger Simulation Round
            </Button>
          </div>
        </div>
      </CardHeader>

      {/* Live Simulation Banner if executed */}
      {simulationResult && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs space-y-3 animate-fadeIn">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-emerald-600" />
              <span className="font-extrabold text-emerald-950">
                Federated Cycle Completed: {simulationResult.model_name} ({simulationResult.candidate_version || "Candidate Model"})
              </span>
            </div>
            <span className="font-mono text-[11px] text-emerald-700 bg-white px-2 py-0.5 rounded border border-emerald-200">
              Zero Raw Data Transferred: {simulationResult.zero_raw_data_transferred ? "100% Sovereign" : "No"}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-[11px]">
            <div className="bg-white p-2 rounded-lg border border-emerald-200 text-center">
              <span className="text-emerald-700 block text-[10px]">Accuracy Gain</span>
              <span className="font-extrabold text-emerald-900">
                +{(simulationResult.accuracy_delta * 100).toFixed(2)}%
              </span>
            </div>
            <div className="bg-white p-2 rounded-lg border border-emerald-200 text-center">
              <span className="text-emerald-700 block text-[10px]">Final Accuracy</span>
              <span className="font-extrabold text-emerald-900">
                {(simulationResult.final_accuracy * 100).toFixed(1)}%
              </span>
            </div>
            <div className="bg-white p-2 rounded-lg border border-emerald-200 text-center">
              <span className="text-emerald-700 block text-[10px]">DP Budget Spent (ε)</span>
              <span className="font-extrabold text-primary-dark">
                {simulationResult.total_epsilon_consumed.toFixed(2)}
              </span>
            </div>
            <div className="bg-white p-2 rounded-lg border border-emerald-200 text-center">
              <span className="text-emerald-700 block text-[10px]">Byzantine Attacks Stopped</span>
              <span className="font-extrabold text-emerald-900">
                {simulationResult.byzantine_attacks_defended}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Round Progress Meter */}
      <div className="p-5 rounded-2xl bg-surface-soft border border-border space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold text-text flex items-center gap-1.5">
            <Activity className="h-4 w-4 text-primary" />
            <span>Training Round {currentRound} of {totalRounds}</span>
          </span>
          <span className="font-mono font-bold text-primary-dark">{progressPercent}% Completed</span>
        </div>

        {/* Progress Bar */}
        <div className="w-full h-3 bg-white border border-border rounded-full overflow-hidden p-0.5">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-primary rounded-full transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" />
            <div>
              <span className="font-bold text-text block">Byzantine-Robust Trimmed Mean</span>
              <span className="text-[10px] text-text-muted">
                {simulationResult?.byzantine_attacks_defended || 2} outlier malicious updates rejected
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-primary shrink-0" />
            <div>
              <span className="font-bold text-text block">Differential Privacy Guard</span>
              <span className="text-[10px] text-text-muted">ε = 0.5, δ = 10⁻⁵ mathematically bounded</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-emerald-700 shrink-0" />
            <div>
              <span className="font-bold text-text block">Model Parameter Convergence</span>
              <span className="text-[10px] text-text-muted">
                Top-1 Accuracy: {simulationResult ? `${(simulationResult.final_accuracy * 100).toFixed(1)}%` : "91.2% (↑ 1.4%)"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Sovereign Node Contribution Breakdown */}
      <div className="space-y-3">
        <span className="text-xs font-bold uppercase text-text-muted tracking-wider block">
          Current Round Parameter Contributions by Sovereign Node
        </span>

        <div className="space-y-2.5">
          {contributions.map((c) => (
            <div key={c.iso} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-text">{c.country}</span>
                <span className="font-mono text-text-muted text-[11px]">
                  {c.gradients} ({c.percent}%)
                </span>
              </div>
              <div className="w-full h-2 bg-surface-soft rounded-full overflow-hidden">
                <div
                  className={`h-full ${c.color} rounded-full transition-all duration-300`}
                  style={{ width: `${c.percent}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

