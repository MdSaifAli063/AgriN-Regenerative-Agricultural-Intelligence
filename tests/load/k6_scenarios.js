import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 25 },   // Ramp up to 25 virtual users
    { duration: '1m', target: 100 },   // Peak load at 100 concurrent users
    { duration: '30s', target: 100 },  // Sustain peak load
    { duration: '20s', target: 0 },    // Graceful ramp-down
  ],
  thresholds: {
    // Quality Gate: 95% of requests must complete below 500ms
    http_req_duration: ['p(95)<500'],
    // Quality Gate: Error rate must strictly be under 1%
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

export default function () {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer demo-token-perf',
  };

  // 1. Health check read
  const healthRes = http.get(`${BASE_URL}/health/ready`);
  check(healthRes, {
    'health check status is 200': (r) => r.status === 200,
  });

  // 2. Messaging Webhook burst simulation
  const simPayload = JSON.stringify({
    from_phone: '+919876543210',
    channel: 'whatsapp',
    message_type: 'text',
    text: '1',
  });
  const simRes = http.post(`${BASE_URL}/api/v1/messaging/simulate`, simPayload, { headers });
  check(simRes, {
    'messaging simulation status is 200': (r) => r.status === 200,
    'messaging returns reply': (r) => r.json('reply_text') !== undefined,
  });

  sleep(1);
}
