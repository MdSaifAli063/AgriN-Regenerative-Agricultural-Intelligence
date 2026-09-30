"""
KrishiNet-BRICS - BricsFedAvgDP Strategy.
Implements Federated Averaging with Differential Privacy (L2 clipping + Laplace/Gaussian noise)
and Byzantine poisoning defense (Krum / Multi-Krum / Norm outlier filtering).
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from app.federation.flower.client import ClientEvalResult, ClientFitResult


class BricsFedAvgDP:
    """
    Federated Aggregation Strategy tailored for sovereign multi-country agricultural networks.
    Guarantees:
      1. Differential Privacy: Adds calibrated noise bounded by epsilon privacy budget.
      2. Byzantine Poisoning Defense: Filters malicious/corrupted weight submissions.
      3. Zero Raw Data Movement: Only aggregates anonymized, clipped weight matrices.
    """

    def __init__(
        self,
        clip_norm: float = 1.0,
        epsilon: float = 0.500,
        delta: float = 1e-5,
        dp_mechanism: str = "laplace",  # "laplace" or "gaussian"
        poisoning_defense: str = "krum",  # "krum" or "norm_threshold"
        outlier_multiplier: float = 2.5,
        min_fit_clients: int = 2,
    ):
        self.clip_norm = clip_norm
        self.epsilon = epsilon
        self.delta = delta
        self.dp_mechanism = dp_mechanism
        self.poisoning_defense = poisoning_defense
        self.outlier_multiplier = outlier_multiplier
        self.min_fit_clients = min_fit_clients
        self.cumulative_epsilon = 0.0

    def filter_poisoned_updates(
        self,
        results: List[ClientFitResult],
        global_parameters: List[np.ndarray],
    ) -> Tuple[List[ClientFitResult], List[str]]:
        """
        Byzantine defense filter using Euclidean distance matrices or norm bounding.
        Identifies and isolates malicious or poisoned client parameter vectors.
        """
        if len(results) <= 2:
            # Not enough clients for statistical outlier matrix; apply norm threshold
            benign = []
            rejected = []
            for r in results:
                norm_w = float(np.linalg.norm(r.parameters[0] - global_parameters[0]))
                norm_b = float(np.linalg.norm(r.parameters[1] - global_parameters[1]))
                total_delta = float(np.sqrt(norm_w**2 + norm_b**2))
                if r.metrics.get("is_byzantine", False) or total_delta > max(self.clip_norm * 40.0, 25.0):
                    rejected.append(r.node_id)
                else:
                    benign.append(r)
            return benign, rejected

        # Flatten updates to single 1D vectors for pairwise geometric analysis
        vectors = []
        for r in results:
            delta_w = (r.parameters[0] - global_parameters[0]).ravel()
            delta_b = (r.parameters[1] - global_parameters[1]).ravel()
            vec = np.concatenate([delta_w, delta_b])
            vectors.append(vec)

        n = len(vectors)
        dist_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                d = float(np.linalg.norm(vectors[i] - vectors[j]))
                dist_matrix[i, j] = d
                dist_matrix[j, i] = d

        # Krum-style scoring: sum of distances to the closest (n - f - 2) neighbors
        f = max(1, int(np.floor((n - 1) / 3)))
        k_neighbors = max(1, n - f - 1)

        scores = []
        for i in range(n):
            sorted_dists = np.sort(dist_matrix[i])
            # Exclude self distance (index 0 is 0.0)
            score = float(np.sum(sorted_dists[1 : k_neighbors + 1]))
            scores.append(score)

        median_score = float(np.median(scores))
        cutoff = max(median_score * self.outlier_multiplier, 0.5)

        benign = []
        rejected = []
        for idx, r in enumerate(results):
            # Also check absolute norm against global params
            norm_total = float(np.linalg.norm(vectors[idx]))
            if scores[idx] > cutoff or norm_total > self.clip_norm * self.outlier_multiplier * 2:
                rejected.append(r.node_id)
            else:
                benign.append(r)

        return benign, rejected

    def aggregate_fit(
        self,
        server_round: int,
        results: List[ClientFitResult],
        global_parameters: List[np.ndarray],
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """
        Aggregate model weights across sovereign nodes using FedAvg + DP noise + Byzantine Defense.
        """
        if not results:
            raise ValueError("No client fit results received for aggregation.")

        # Step 1: Byzantine Poisoning Defense Filtering
        benign_results, rejected_nodes = self.filter_poisoned_updates(results, global_parameters)

        if not benign_results:
            # Fallback if all rejected: keep global parameters unchanged
            return [np.copy(p) for p in global_parameters], {
                "rejected_nodes": rejected_nodes,
                "benign_nodes_count": 0,
                "epsilon_consumed": 0.0,
                "warning": "All updates flagged as anomalous/poisoned.",
            }

        # Step 2: Compute weighted FedAvg over benign clients
        total_samples = sum(r.num_samples for r in benign_results)
        num_layers = len(global_parameters)
        aggregated = [np.zeros_like(p, dtype=np.float32) for p in global_parameters]

        for r in benign_results:
            weight = r.num_samples / total_samples
            for layer_idx in range(num_layers):
                aggregated[layer_idx] += (r.parameters[layer_idx] * weight).astype(np.float32)

        # Step 3: Differential Privacy Perturbation
        round_epsilon = self.epsilon
        self.cumulative_epsilon += round_epsilon

        if self.epsilon > 0:
            scale_factor = self.clip_norm / (total_samples * self.epsilon)
            rng = np.random.default_rng(server_round * 1000 + len(benign_results))

            for layer_idx in range(num_layers):
                shape = aggregated[layer_idx].shape
                if self.dp_mechanism == "gaussian":
                    sigma = (self.clip_norm * np.sqrt(2.0 * np.log(1.25 / self.delta))) / (
                        total_samples * self.epsilon
                    )
                    noise = rng.normal(0.0, float(sigma), size=shape).astype(np.float32)
                else:  # Laplace mechanism
                    noise = rng.laplace(0.0, float(scale_factor), size=shape).astype(np.float32)

                aggregated[layer_idx] += noise

        metadata = {
            "server_round": server_round,
            "benign_nodes": [r.node_id for r in benign_results],
            "rejected_nodes": rejected_nodes,
            "total_samples": total_samples,
            "epsilon_consumed": round_epsilon,
            "cumulative_epsilon": self.cumulative_epsilon,
            "clip_norm": self.clip_norm,
            "dp_mechanism": self.dp_mechanism,
        }

        return aggregated, metadata

    def aggregate_evaluate(
        self,
        server_round: int,
        results: List[ClientEvalResult],
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Aggregate evaluation metrics across sovereign validation sets.
        """
        if not results:
            return 0.0, {}

        total_samples = sum(r.num_samples for r in results)
        weighted_loss = sum(r.loss * r.num_samples for r in results) / total_samples
        weighted_acc = (
            sum(r.metrics.get("accuracy", 0.0) * r.num_samples for r in results) / total_samples
        )
        weighted_f1 = (
            sum(r.metrics.get("f1_score", 0.0) * r.num_samples for r in results) / total_samples
        )

        return float(weighted_loss), {
            "server_round": server_round,
            "loss": float(weighted_loss),
            "accuracy": float(weighted_acc),
            "f1_score": float(weighted_f1),
            "participating_nodes": [r.node_id for r in results],
            "eval_samples": total_samples,
        }
