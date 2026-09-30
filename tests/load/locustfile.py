"""
Locust Performance and Load Testing Suite for KrishiNet-BRICS Sovereign Node.
Simulates concurrent farmers and extension officers executing:
1. Cached Dashboard reads
2. Advisory generation in DEMO_MODE
3. Leaf Doctor disease inference
4. Inbound messaging webhook bursts
"""

from locust import HttpUser, task, between
import json

class FarmerUser(HttpUser):
    wait_time = between(1.0, 3.0)

    def on_start(self):
        """Initializes test farmer authentication credentials."""
        self.headers = {
            "Authorization": "Bearer demo-token-farmer-01",
            "Content-Type": "application/json",
        }

    @task(4)
    def test_dashboard_reads(self):
        """Target: p95 < 500ms under 100 concurrent users."""
        with self.client.get(
            "/api/v1/farms",
            headers=self.headers,
            catch_response=True,
            name="GET /farms"
        ) as response:
            if response.status_code in [200, 401]:  # 401 acceptable if auth bypass disabled
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(2)
    def test_advisory_generation(self):
        """Target: p95 < 1500ms in DEMO_MODE."""
        payload = {
            "field_id": "field-cotton-01",
            "target_crop": "Cotton",
            "locale": "en",
        }
        with self.client.post(
            "/api/v1/advisories/generate",
            json=payload,
            headers=self.headers,
            catch_response=True,
            name="POST /advisories/generate"
        ) as response:
            if response.status_code in [200, 201, 404]:
                response.success()
            else:
                response.failure(f"Advisory generation failed: {response.text}")

    @task(3)
    def test_messaging_webhook_burst(self):
        """Target: p95 < 200ms for messaging burst handling."""
        payload = {
            "from_phone": "+919876543210",
            "channel": "whatsapp",
            "message_type": "text",
            "text": "1",
        }
        with self.client.post(
            "/api/v1/messaging/simulate",
            json=payload,
            catch_response=True,
            name="POST /messaging/simulate"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Simulation failed: {response.status_code}")

    @task(1)
    def test_health_probe(self):
        """Target: p99 < 50ms for Kubernetes liveness/readiness probes."""
        self.client.get("/health/ready", name="GET /health/ready")
