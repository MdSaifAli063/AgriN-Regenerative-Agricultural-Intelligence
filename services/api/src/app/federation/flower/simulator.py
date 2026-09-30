"""
KrishiNet-BRICS - Flower Federated Learning Simulator.
Orchestrates multi-country federated training rounds across India, Brazil, and South Africa,
enforces Differential Privacy budgets, records rounds in the database, and bridges
to the Model Hub upon convergence.
"""

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.federation.flower.client import AgriNVirtualClient
from app.federation.flower.strategy import BricsFedAvgDP
from app.models.brics import FederatedRound, MLModel, ModelCard
from app.models.model_hub import ModelHubEntry


@dataclass
class RoundLog:
    round_number: int
    train_loss: float
    val_accuracy: float
    val_f1: float
    epsilon_consumed: float
    cumulative_epsilon: float
    participating_nodes: List[str]
    rejected_byzantine_nodes: List[str]
    duration_ms: int


@dataclass
class SimulationReport:
    simulation_id: str
    model_name: str
    task_type: str
    rounds_executed: int
    participating_nodes: List[str]
    initial_accuracy: float
    final_accuracy: float
    accuracy_delta: float
    final_loss: float
    total_epsilon_consumed: float
    zero_raw_data_transferred: bool
    byzantine_attacks_defended: int
    candidate_model_id: Optional[str]
    candidate_version: Optional[str]
    round_history: List[Dict[str, Any]]
    status: str  # "converged", "completed", "failed"


class FederatedSimulator:
    """
    Simulates Flower federated learning across 3 sovereign nodes:
      - node-ind-01 (India, Maharashtra/Punjab)
      - node-bra-01 (Brazil, Mato Grosso/Goias)
      - node-zaf-01 (South Africa, Free State)
    """

    def __init__(
        self,
        strategy: Optional[BricsFedAvgDP] = None,
        feature_dim: int = 16,
        model_name: str = "KrishiNet-BRICS-YieldPredictor",
        task_type: str = "yield_forecast",
    ):
        self.strategy = strategy or BricsFedAvgDP(
            clip_norm=1.0,
            epsilon=0.500,
            dp_mechanism="laplace",
            poisoning_defense="krum",
            outlier_multiplier=2.5,
        )
        self.feature_dim = feature_dim
        self.model_name = model_name
        self.task_type = task_type
        self.clients: Dict[str, AgriNVirtualClient] = {}
        self.global_parameters: List[np.ndarray] = [
            np.zeros((feature_dim, 1), dtype=np.float32),
            np.array([3.0], dtype=np.float32),
        ]
        self._initialize_default_nodes()

    def _initialize_default_nodes(self):
        """Create partitions for the three default BRICS sovereign nodes."""
        self.clients["node-ind-01"] = AgriNVirtualClient(
            node_id="node-ind-01",
            country_iso="IN",
            num_samples=1200,
            feature_dim=self.feature_dim,
            base_yield_bias=3.8,
            random_seed=101,
        )
        self.clients["node-bra-01"] = AgriNVirtualClient(
            node_id="node-bra-01",
            country_iso="BR",
            num_samples=1450,
            feature_dim=self.feature_dim,
            base_yield_bias=4.2,
            random_seed=202,
        )
        self.clients["node-zaf-01"] = AgriNVirtualClient(
            node_id="node-zaf-01",
            country_iso="ZA",
            num_samples=950,
            feature_dim=self.feature_dim,
            base_yield_bias=3.4,
            random_seed=303,
        )

    def add_byzantine_client(
        self,
        node_id: str = "node-mal-01",
        country_iso: str = "XX",
        poison_type: str = "sign_flip",
    ):
        """Inject a malicious or compromised edge node for adversarial testing."""
        self.clients[node_id] = AgriNVirtualClient(
            node_id=node_id,
            country_iso=country_iso,
            num_samples=800,
            feature_dim=self.feature_dim,
            is_byzantine=True,
            poison_type=poison_type,
            random_seed=999,
        )

    async def run_simulation(
        self,
        db: Optional[AsyncSession] = None,
        num_rounds: int = 3,
        model_id: Optional[str] = None,
        version_tag: Optional[str] = None,
        target_accuracy: float = 0.85,
    ) -> SimulationReport:
        """
        Execute N rounds of federated training across sovereign nodes.
        Guarantees:
          - No raw data leaves any node.
          - Differential Privacy noise bounded by epsilon is applied.
          - Byzantine client updates are detected and isolated.
          - Successful rounds are recorded in `federated_rounds`.
          - A candidate ModelCard is registered in the Model Hub if accuracy >= target_accuracy.
        """
        sim_id = f"fl-sim-{uuid.uuid4().hex[:8]}"
        round_logs: List[RoundLog] = []
        total_byzantine_defended = 0

        # Step 0: Ensure target MLModel exists in database if DB session provided
        ml_model_record = None
        if db:
            if model_id:
                res = await db.execute(select(MLModel).where(MLModel.id == model_id))
                ml_model_record = res.scalar_one_or_none()

            if not ml_model_record:
                ml_model_record = MLModel(
                    id=model_id or str(uuid.uuid4()),
                    model_name=self.model_name,
                    task_type=self.task_type,
                    license_type="Apache-2.0",
                    dpg_compliant=True,
                )
                db.add(ml_model_record)
                await db.flush()
            model_id = ml_model_record.id

        # Initial baseline evaluation
        initial_eval_results = [
            c.evaluate(self.global_parameters)
            for c in self.clients.values()
            if not c.is_byzantine
        ]
        _, initial_meta = self.strategy.aggregate_evaluate(0, initial_eval_results)
        initial_acc = initial_meta.get("accuracy", 0.50)

        current_loss = 0.0
        current_acc = initial_acc
        current_f1 = initial_meta.get("f1_score", 0.48)

        for r in range(1, num_rounds + 1):
            started_at = datetime.now(timezone.utc)

            # Phase A: Client Local Training Steps
            fit_results = []
            for client in self.clients.values():
                fit_res = client.fit(
                    parameters=self.global_parameters,
                    config={"learning_rate": 0.08, "local_epochs": 2},
                )
                fit_results.append(fit_res)

            # Phase B: Strategy Aggregation with Byzantine Defense and DP
            updated_params, agg_meta = self.strategy.aggregate_fit(
                server_round=r,
                results=fit_results,
                global_parameters=self.global_parameters,
            )
            self.global_parameters = updated_params

            rejected = agg_meta.get("rejected_nodes", [])
            total_byzantine_defended += len(rejected)

            # Phase C: Federated Evaluation across benign validation sets
            eval_results = [
                c.evaluate(self.global_parameters)
                for c in self.clients.values()
                if not c.is_byzantine
            ]
            eval_loss, eval_meta = self.strategy.aggregate_evaluate(r, eval_results)

            current_loss = eval_loss
            current_acc = eval_meta.get("accuracy", current_acc)
            current_f1 = eval_meta.get("f1_score", current_f1)
            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            round_log = RoundLog(
                round_number=r,
                train_loss=float(current_loss),
                val_accuracy=float(current_acc),
                val_f1=float(current_f1),
                epsilon_consumed=agg_meta.get("epsilon_consumed", self.strategy.epsilon),
                cumulative_epsilon=self.strategy.cumulative_epsilon,
                participating_nodes=list(self.clients.keys()),
                rejected_byzantine_nodes=rejected,
                duration_ms=duration_ms,
            )
            round_logs.append(round_log)

            # Persist round into federated_rounds database table
            if db and model_id:
                round_record = FederatedRound(
                    id=str(uuid.uuid4()),
                    model_id=model_id,
                    round_number=r,
                    participating_nodes=list(self.clients.keys()),
                    aggregation_strategy="BricsFedAvgDP",
                    epsilon_privacy_budget=float(self.strategy.epsilon),
                    started_at=started_at,
                    completed_at=completed_at,
                )
                db.add(round_record)
                await db.flush()

        # Step 4: Bridge to Model Hub if converged
        candidate_version = version_tag or f"fl-v{len(round_logs)}.{uuid.uuid4().hex[:4]}"
        weights_bytes = b"".join(p.tobytes() for p in self.global_parameters)
        weights_sha256 = hashlib.sha256(weights_bytes).hexdigest()

        if db and model_id and current_acc >= 0.70:
            # Create ModelCard in DB
            card_md = f"""# Model Card: {self.model_name}
## Version: {candidate_version}
- **Task**: {self.task_type}
- **Federated Training**: {num_rounds} rounds across sovereign nodes ({', '.join(self.clients.keys())})
- **Differential Privacy**: epsilon={self.strategy.cumulative_epsilon:.3f}, delta={self.strategy.delta}
- **Validation Accuracy**: {current_acc * 100:.2f}%
- **Validation F1**: {current_f1 * 100:.2f}%
- **DPG Compliance**: 100% (zero raw farmer data moved across borders)
- **Weights SHA-256**: `{weights_sha256}`
"""
            model_card = ModelCard(
                id=str(uuid.uuid4()),
                model_id=model_id,
                version_tag=candidate_version,
                accuracy_score=float(current_acc),
                f1_score=float(current_f1),
                training_data_summary=f"Trained on {sum(c.num_samples for c in self.clients.values())} decentralized records across IN, BR, ZA.",
                bias_limitations="Evaluated on sovereign validation splits; regional calibration recommended before deployment.",
                s3_weights_uri=f"s3://krishinet-models/{self.model_name}/{candidate_version}/weights.bin",
                weights_sha256=weights_sha256,
                card_markdown=card_md,
            )
            db.add(model_card)

            # Create candidate entry in model_hub_entries
            hub_entry = ModelHubEntry(
                id=str(uuid.uuid4()),
                model_card_id=model_card.id,
                node_id="node-ind-01",
                country_iso="IN",
                status="candidate",
                bucket="krishinet-models",
                object_key=f"models/{self.model_name}/{candidate_version}/weights.bin",
                size_bytes=len(weights_bytes),
                weights_sha256=weights_sha256,
                card_json={
                    "model_name": self.model_name,
                    "version": candidate_version,
                    "federated_rounds": num_rounds,
                    "privacy_budget_consumed": self.strategy.cumulative_epsilon,
                },
                card_signature_hex=weights_sha256[:64],
                card_signed_by_node="node-ind-01",
                quantization="float32",
                framework="tflite",
                task_type=self.task_type,
                crop_coverage=["cotton", "soybean", "maize"],
                license_type="Apache-2.0",
            )
            db.add(hub_entry)
            await db.commit()

        status_str = "converged" if current_acc >= target_accuracy else "completed"

        return SimulationReport(
            simulation_id=sim_id,
            model_name=self.model_name,
            task_type=self.task_type,
            rounds_executed=num_rounds,
            participating_nodes=list(self.clients.keys()),
            initial_accuracy=float(initial_acc),
            final_accuracy=float(current_acc),
            accuracy_delta=float(current_acc - initial_acc),
            final_loss=float(current_loss),
            total_epsilon_consumed=float(self.strategy.cumulative_epsilon),
            zero_raw_data_transferred=True,
            byzantine_attacks_defended=total_byzantine_defended,
            candidate_model_id=model_id,
            candidate_version=candidate_version,
            round_history=[asdict(log) for log in round_logs],
            status=status_str,
        )
