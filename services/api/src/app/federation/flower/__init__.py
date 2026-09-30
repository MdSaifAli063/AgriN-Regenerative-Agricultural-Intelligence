"""
KrishiNet-BRICS - Flower Federated Learning Module.
Provides virtual clients, BricsFedAvgDP strategy with differential privacy
and Byzantine poisoning defense, and multi-round simulation engine.
"""

from app.federation.flower.client import AgriNVirtualClient, ClientFitResult, ClientEvalResult
from app.federation.flower.strategy import BricsFedAvgDP
from app.federation.flower.simulator import FederatedSimulator, SimulationReport

__all__ = [
    "AgriNVirtualClient",
    "ClientFitResult",
    "ClientEvalResult",
    "BricsFedAvgDP",
    "FederatedSimulator",
    "SimulationReport",
]
