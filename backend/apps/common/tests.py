from django.test import TestCase
from django.urls import reverse

class HealthEndpointTests(TestCase):
    def test_health_endpoint_returns_service_payload(self):
        response = self.client.get("/api/v1/health/")
        self.assertIn(response.status_code, (200, 503))
        self.assertIn("service", response.json())
        self.assertIn("database", response.json())
