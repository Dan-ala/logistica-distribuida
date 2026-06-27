# Guía Rápida — Logística Distribuida

Léanla completa para responder los informes. No necesitan instalar ni ejecutar nada.

---

## 1. Servicios (Backend)

Hay **3 servicios** que se ejecutan en contenedores Docker:

| Servicio | Rol | Tecnología |
|----------|-----|------------|
| **tracking-service** | Recibe ubicaciones vía HTTP POST, las guarda en BD y publica eventos | FastAPI (Python) |
| **notification-service** | Escucha eventos y guarda notificaciones | Python consumer |
| **route-service** | Escucha eventos, calcula distancia y costo de ruta | Python consumer |

Se comunican **sin llamadas HTTP directas**. Usan **RabbitMQ** como intermediario asíncrono (Saga coreografiada).

---

## 2. Transacción distribuida paso a paso

1. Cliente → `POST /locations/update` al **tracking-service** con header `Idempotency-Key`
2. Tracking service inicia una **transacción SQL** que guarda 3 cosas a la vez:
   - La ubicación en tabla `locations` (con `status = PENDING`)
   - Un evento en tabla `outbox` (con `status = PENDING`)
   - La clave de idempotencia en tabla `idempotency_keys`
3. **OutboxPoller** (hilo aparte) cada 2 segundos revisa eventos `PENDING` en `outbox` y los publica a RabbitMQ
4. RabbitMQ entrega el evento a las colas de **notification-service** y **route-service**
5. Cada consumidor procesa el evento y guarda en su propia BD
6. Si un consumidor **falla permanentemente** (3 reintentos), publica un evento `LOCATION_FAILED` que el tracking-service consume para marcar la ubicación como `FAILED` (compensación)

---

## 3. Saga coreografiada vs 2PC

Se eligió **Saga Coreografiada** porque:
- Cada servicio es independiente (no espera a los demás)
- No hay coordinador central que pueda fallar
- Escala horizontalmente
- Consistencia eventual es aceptable (no necesitamos que la notificación sea instantánea)
- Permite compensaciones cuando algo falla

---

## 4. Idempotencia

- Se usa el header HTTP **`Idempotency-Key`**
- **1ra vez** con una key nueva → HTTP **201** (Created)
- **2da vez** con la misma key → HTTP **200** (OK, mismo event_id)
- Las claves se guardan en la tabla `idempotency_keys` de tracking_db
- Además hay una constraint `UNIQUE` en la BD para `vehicle_id + timestamp` como respaldo

---

## 5. Outbox Pattern

- Si RabbitMQ se cae justo después de recibir una ubicación, el evento **NO se pierde**
- Queda en la tabla `outbox` con `status = PENDING`
- Cuando RabbitMQ se recupera, el OutboxPoller lo publica automáticamente
- Máximo 5 reintentos de publicación, luego el outbox se marca como `FAILED`

---

## 6. RabbitMQ y colas

Basado en `shared/event_config.py`:

| Elemento | Nombre |
|----------|--------|
| Exchange principal | `location.exchange` |
| Routing key (éxito) | `location.updated` |
| Routing key (fallo) | `location.failed` |
| Cola notification | `notification.service.queue` |
| Cola route | `route.service.queue` |
| Colas de retry | `notification.service.queue.retry` y `route.service.queue.retry` |
| Dead Letter Queue | `failed.events.queue` |
| Exchange de retry | `retry.exchange` |
| Exchange de DLQ | `dlx.exchange` (fanout) |

- **Máximo 3 reintentos** por evento
- **TTL de 5 segundos** entre reintentos (el mensaje espera 5s en la cola de retry)
- Si se agotan los reintentos → el evento va a `failed.events.queue` (DLQ) y se publica `LOCATION_FAILED`

---

## 7. Modelo de datos

### tracking_db

**Tabla `locations`**: id (UUID), vehicle_id, latitude, longitude, recorded_at, event_id (único), uuid_event_id, status (PENDING/COMPLETED/FAILED), created_at

**Tabla `idempotency_keys`**: id (UUID), idempotency_key (único), response_status, response_body, created_at

**Tabla `outbox`**: id (UUID), event_id (único), event_type, routing_key, body (JSON), status (PENDING/PUBLISHED/FAILED), retry_count, created_at, published_at

### notification_db

**Tabla `notifications`**: id (UUID), vehicle_id, message, event_id, status (COMPLETED), created_at

### route_db

**Tabla `routes`**: id (UUID), vehicle_id, distance, cost, event_id, status (COMPLETED), updated_at

---

## 8. Observabilidad

- **Logs**: formato JSON en todos los servicios: `{"timestamp": "...", "level": "INFO", "logger": "...", "message": "..."}`
- **Métricas Prometheus**: endpoint `GET /metrics` en tracking-service (puerto 8000)
- **Métricas principales**: `http_requests_total`, `http_request_duration_seconds` (histograma de latencia), `events_published_total`, `events_consumed_total`, `events_failed_total`, `circuit_breaker_state`, `outbox_size`
- **Prometheus** corre en puerto 9090
- **Grafana** corre en puerto 3000 (admin / logistica123)

---

## 9. Prueba de carga con k6

Basado en `k6/load_test.js`:

- **Máximo 100 usuarios virtuales** concurrentes
- **Endpoints probados**: `GET /health`, `GET /metrics`, `POST /locations/update`
- **Escenarios**: flujo normal, idempotencia (misma key 3 veces), datos inválidos (422 esperado)
- **Thresholds**:
  - Tasa de fallos < 5%
  - P95 de latencia < 2000ms
- **Fases**: rampa 0→10 VUs (10s), 10→50 VUs (20s), 50→100 VUs (10s), sostén 100 VUs (30s), descenso (10s)

---

## 10. Compensaciones

Los informes usan como referencia lo que encontraron en la carpeta del proyecto en GitHub / el ZIP que les compartieron. No necesitan Docker ni Linux para leer los archivos `.py`, `.md`, `.js` y `.yml`.
