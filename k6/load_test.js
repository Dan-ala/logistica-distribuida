import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

const failureRate = new Rate("failed_requests");

export const options = {
  stages: [
    { duration: "10s", target: 10 },
    { duration: "20s", target: 50 },
    { duration: "10s", target: 0 },
  ],
  thresholds: {
    failed_requests: ["rate<0.05"],
    http_req_duration: ["p(95)<2000"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

const VEHICLES = ["CAR-001", "CAR-002", "CAR-003", "TRUCK-001", "TRUCK-002"];

export default function () {
  const vehicle = VEHICLES[Math.floor(Math.random() * VEHICLES.length)];

  const payload = JSON.stringify({
    vehicle_id: vehicle,
    latitude: 4.6 + Math.random() * 0.3,
    longitude: -74.2 + Math.random() * 0.3,
    timestamp: new Date().toISOString(),
  });

  const params = {
    headers: {
      "Content-Type": "application/json",
    },
  };

  const res = http.post(`${BASE_URL}/locations/update`, payload, params);

  check(res, {
    "status is 201": (r) => r.status === 201,
    "has event_id": (r) => r.json("event_id") !== undefined,
  }) || failureRate.add(1);

  sleep(1);
}
