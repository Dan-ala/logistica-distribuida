import http from "k6/http";
import { check, sleep, group } from "k6";
import { Rate, Trend } from "k6/metrics";

const failureRate = new Rate("failed_requests");
const latencyTrend = new Trend("request_duration");

export const options = {
  stages: [
    { duration: "10s", target: 10 },
    { duration: "20s", target: 50 },
    { duration: "10s", target: 100 },
    { duration: "30s", target: 100 },
    { duration: "10s", target: 0 },
  ],
  thresholds: {
    failed_requests: ["rate<0.05"],
    http_req_duration: ["p(95)<2000"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

const VEHICLES = ["CAR-001", "CAR-002", "CAR-003", "TRUCK-001", "TRUCK-002"];

function generatePayload(vehicle) {
  return JSON.stringify({
    vehicle_id: vehicle,
    latitude: 4.6 + Math.random() * 0.3,
    longitude: -74.2 + Math.random() * 0.3,
    timestamp: new Date().toISOString(),
  });
}

function testHealth() {
  const res = http.get(`${BASE_URL}/health`);
  check(res, {
    "health status is 200": (r) => r.status === 200,
    "health returns ok": (r) => r.json("status") === "ok",
  });
}

function testMetrics() {
  const res = http.get(`${BASE_URL}/metrics`);
  check(res, {
    "metrics status is 200": (r) => r.status === 200,
  });
}

function testLocationUpdate(idempotencyKey) {
  const vehicle = VEHICLES[Math.floor(Math.random() * VEHICLES.length)];
  const payload = generatePayload(vehicle);

  const params = {
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey || "",
    },
  };

  const res = http.post(`${BASE_URL}/locations/update`, payload, params);
  latencyTrend.add(res.timings.duration);

  const isSuccess = check(res, {
    "status is 201 or 409": (r) => r.status === 201 || r.status === 409,
    "has valid response": (r) => r.json("event_id") !== undefined || r.status === 409,
  });

  if (!isSuccess) {
    failureRate.add(1);
  }

  return res.status === 201;
}

function testIdempotency() {
  const idempotencyKey = `k6-test-${__VU}-${__ITER}`;
  const vehicle = VEHICLES[__VU % VEHICLES.length];
  const payload = JSON.stringify({
    vehicle_id: vehicle,
    latitude: 4.7110,
    longitude: -74.0721,
    timestamp: new Date().toISOString(),
  });

  const params = {
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    },
  };

  const res1 = http.post(`${BASE_URL}/locations/update`, payload, params);
  check(res1, {
    "first request returns 201": (r) => r.status === 201,
  });

  const res2 = http.post(`${BASE_URL}/locations/update`, payload, params);
  check(res2, {
    "duplicate returns 200 with same idempotency-key": (r) => r.status === 200 || r.status === 201,
  });

  const res3 = http.post(`${BASE_URL}/locations/update`, payload, params);
  check(res3, {
    "third duplicate also returns success": (r) => r.status === 200 || r.status === 201,
  });
}

function testInvalidData() {
  const invalidPayloads = [
    JSON.stringify({ vehicle_id: "", latitude: 100, longitude: 200, timestamp: "invalid" }),
    JSON.stringify({}),
    JSON.stringify({ vehicle_id: "CAR-001" }),
    "not json",
  ];

  for (const payload of invalidPayloads) {
    const params = { headers: { "Content-Type": "application/json" } };
    const res = http.post(`${BASE_URL}/locations/update`, payload, params);
    check(res, {
      "invalid data returns 422": (r) => r.status === 422,
    });
  }
}

export default function () {
  group("Health Check", () => {
    testHealth();
  });

  group("Metrics Endpoint", () => {
    testMetrics();
  });

  group("Location Update", () => {
    testLocationUpdate(`${__VU}-${__ITER}-${Date.now()}`);
    sleep(0.5);
  });

  if (__ITER === 0 && __VU === 0) {
    group("Idempotency Test", () => {
      testIdempotency();
    });

    group("Invalid Data Test", () => {
      testInvalidData();
    });
  }

  sleep(1);
}
