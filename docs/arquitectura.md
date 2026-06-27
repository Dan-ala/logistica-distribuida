# Documento de Arquitectura

## Comparación: HTAP vs OLTP + Cola

### HTAP (Hybrid Transactional/Analytical Processing)

| Característica | HTAP |
|----------------|------|
| Unifica OLTP y OLAP | Sí |
| Latencia de escritura | Mayor (debe indexar para análisis) |
| Complejidad operativa | Alta (sintonización de motor híbrido) |
| Escalabilidad | Vertical principalmente |
| Adecuado para | Analytics en tiempo real sobre datos transaccionales |

### OLTP + Cola (Elección)

| Característica | OLTP + Cola |
|----------------|-------------|
| Separación transaccional/analítico | Sí |
| Latencia de escritura | Baja (escritura transaccional pura) |
| Complejidad operativa | Baja (cada servicio gestiona su DB) |
| Escalabilidad | Horizontal (cada servicio escala independientemente) |
| Adecuado para | Sistemas transaccionales de alta frecuencia |

### Por qué OLTP + Cola

El sistema de logística recibe ubicaciones de vehículos a alta frecuencia. Cada ubicación es una transacción que debe persistirse rápidamente. No se requieren análisis complejos en tiempo real sobre los datos de ubicación individuales. La cola de mensajes desacopla la recepción del procesamiento, permitiendo que los consumidores fallen y se recuperen sin pérdida de datos.

## Comparación: 2PC vs Saga

### Two-Phase Commit (2PC)

```
Fase 1: Prepare
  Coordinator -> Participant: "¿puedes commitear?"
  Participant -> Coordinator: "Sí/No"
Fase 2: Commit/Abort
  Coordinator -> Participant: "Commitea/Aborta"
```

Problemas:
- Bloqueante: si un participante falla en prepare, todos esperan
- Coordinator es单点故障 (single point of failure)
- No escala horizontalmente
- Latencias altas en sistemas distribuidos

### Saga (Coreografía) — Elección

```
Tracking Service publica LOCATION_UPDATED
  -> Notification Service recibe y procesa (independiente)
  -> Route Service recibe y procesa (independiente)
  -> Si un consumidor falla永久, publica LOCATION_FAILED
    -> Tracking Service recibe y marca la ubicación como FAILED
```

Ventajas:
- No bloqueante: cada servicio avanza independientemente
- Sin coordinador central
- Escala horizontalmente
- Recuperación natural: los eventos se re-procesan al recuperar el servicio
- Consistencia eventual aceptable para logística
- Compensaciones automáticas vía eventos de fallo

### Por qué Saga para logística en tiempo real

En un sistema de logística:
1. La disponibilidad es crítica (los vehículos siempre se mueven)
2. La consistencia inmediata no es necesaria (una notificación puede retrasarse segundos)
3. Los servicios deben escalar independientemente (más vehículos = más tracking, no necesariamente más notificaciones)
4. Los fallos son esperados (red móvil, reinicios de servicio)
5. Saga permite compensaciones automáticas: si un consumidor falla tras reintentos, publica un evento LOCATION_FAILED que el tracking-service consume para marcar la transacción como fallida

## Patrones implementados

### Outbox Pattern

Para garantizar que ningún evento se pierda si RabbitMQ falla:

```
1. POST /locations/update
2. Tracking Service inicia transacción:
   a. INSERT en locations (status=PENDING)
   b. INSERT en outbox (status=PENDING, body=evento JSON)
   c. INSERT en idempotency_keys
   d. COMMIT (atómico)
3. OutboxPoller (hilo separado):
   a. Lee outbox WHERE status=PENDING (cada 2s)
   b. Publica evento a RabbitMQ
   c. Si éxito → UPDATE outbox SET status=PUBLISHED
   d. Si falla → incrementa retry_count; tras 5 intentos → status=FAILED
4. Si RabbitMQ se cae, los eventos quedan en outbox y se publican cuando recupere
```

### Circuit Breaker

Cada conexión a RabbitMQ está protegida por un circuit breaker:

- **CLOSED**: funcionamiento normal, 3 fallos consecutivos → OPEN
- **OPEN**: rechaza llamadas inmediatamente por 30s → HALF_OPEN
- **HALF_OPEN**: permite 3 llamadas de prueba; si fallan → OPEN, si todas OK → CLOSED

### Compensaciones (Saga)

Cuando un consumidor agota los reintentos:

```
1. Notification o Route Service detecta que x-retry-count >= MAX_RETRIES (3)
2. Publica evento LOCATION_FAILED al exchange con routing_key "location.failed"
3. Incluye en el evento: original_event_id, vehicle_id, reason
4. CompensationConsumer en tracking-service recibe el evento
5. Busca Location por uuid_event_id
6. Actualiza status = "FAILED"
```

## Estrategia de Dead Letter Queue y Reintentos

```
Evento nuevo
  -> Cola principal (notification.service.queue / route.service.queue)
  -> Consumidor procesa
    -> Éxito: ACK
    -> Falla:
      -> Si retries < MAX_RETRIES (3):
        -> Publica mensaje a RETRY_EXCHANGE con routing_key = queue_name
        -> Cola de retry (queue.retry) con TTL = 5000ms
        -> DLX de la cola de retry apunta al exchange original
        -> Mensaje vuelve a la cola principal tras 5s con x-retry-count+1
      -> Si retries >= MAX_RETRIES:
        -> NACK con requeue=False
        -> RabbitMQ envía a DLX (dlx.exchange, fanout)
        -> Almacenado en DLQ (failed.events.queue)
        -> Publica LOCATION_FAILED como compensación
```

## Modelo de datos

### tracking_db.locations

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | UUID | PK |
| vehicle_id | VARCHAR(50) | Identificador del vehículo |
| latitude | FLOAT | Latitud |
| longitude | FLOAT | Longitud |
| recorded_at | TIMESTAMP | Timestamp del evento |
| event_id | VARCHAR(100) | Unique para idempotencia (vehicle_id + timestamp) |
| uuid_event_id | VARCHAR(100) | UUID del evento para matching de compensación |
| status | VARCHAR(20) | PENDING, COMPLETED, FAILED |
| created_at | TIMESTAMP | Fecha de creación |

### tracking_db.idempotency_keys

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | UUID | PK |
| idempotency_key | VARCHAR(255) | Header Idempotency-Key del cliente (unique) |
| response_status | INTEGER | HTTP status de la respuesta original |
| response_body | TEXT | event_id de la respuesta original |
| created_at | TIMESTAMP | Fecha de creación |

### tracking_db.outbox

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | UUID | PK |
| event_id | VARCHAR(100) | UUID del evento (unique) |
| event_type | VARCHAR(50) | LOCATION_UPDATED |
| routing_key | VARCHAR(100) | Routing key para RabbitMQ |
| body | TEXT | Payload JSON del evento |
| status | VARCHAR(20) | PENDING, PUBLISHED, FAILED |
| retry_count | INTEGER | Número de reintentos de publicación |
| created_at | TIMESTAMP | Fecha de creación |
| published_at | TIMESTAMP | Fecha de publicación exitosa |

### notification_db.notifications

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | UUID | PK |
| vehicle_id | VARCHAR(50) | Identificador del vehículo |
| message | VARCHAR(500) | Mensaje de notificación |
| event_id | VARCHAR(100) | UUID del evento original |
| status | VARCHAR(20) | COMPLETED |
| created_at | TIMESTAMP | Fecha de creación |

### route_db.routes

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | UUID | PK |
| vehicle_id | VARCHAR(50) | Identificador del vehículo |
| distance | FLOAT | Distancia calculada (km) |
| cost | FLOAT | Costo calculado (distance * 2000) |
| event_id | VARCHAR(100) | UUID del evento original |
| status | VARCHAR(20) | COMPLETED |
| updated_at | TIMESTAMP | Fecha de actualización |

## Observabilidad

### Logs estructurados (JSON)

Cada servicio produce logs en formato JSON con timestamp, level, logger y message:

```json
{"timestamp": "2026-06-27T12:00:00Z", "level": "INFO", "logger": "tracking-service", "message": "Location saved for vehicle CAR-001"}
```

### Métricas Prometheus (endpoint /metrics)

| Métrica | Tipo | Labels |
|---------|------|--------|
| http_requests_total | Counter | service, method, endpoint, status |
| http_request_duration_seconds | Histogram | service, method, endpoint |
| events_published_total | Counter | service, exchange, status |
| events_consumed_total | Counter | service, queue, status |
| events_failed_total | Counter | service, queue |
| db_operations_total | Counter | service, operation, status |
| circuit_breaker_state | Gauge | service, name (0=closed, 1=half_open, 2=open) |
| outbox_size | Gauge | service |

### Stack de monitoreo

- Prometheus (puerto 9090): recolecta métricas del tracking-service
- Grafana (puerto 3000): dashboards pre-configurados con datasource Prometheus

## Diagrama de infraestructura

```
Docker Compose
  |
  +-- postgres:16 (volumen: postgres_data)
  |     Databases: tracking_db, notification_db, route_db
  |     Tables: locations, idempotency_keys, outbox, notifications, routes
  |
  +-- rabbitmq:3.13 (volumen: rabbitmq_data)
  |     Exchanges: location.exchange, dlx.exchange, retry.exchange
  |     Queues: notification.service.queue, route.service.queue,
  |             notification.service.queue.retry, route.service.queue.retry,
  |             failed.events.queue
  |
  +-- tracking-service (FastAPI, puerto 8000)
  |     Dependencias: postgres, rabbitmq
  |     Threads: API (main), OutboxPoller, CompensationConsumer
  |
  +-- notification-service (Consumer Python)
  |     Dependencias: postgres, rabbitmq
  |     Patrones: retry con TTL, compensación vía LOCATION_FAILED
  |
  +-- route-service (Consumer Python)
  |     Dependencias: postgres, rabbitmq
  |     Patrones: retry con TTL, compensación vía LOCATION_FAILED
  |
  +-- prometheus (puerto 9090)
  |     Recolecta métricas de tracking-service
  |
  +-- grafana (puerto 3000)
        Dashboards pre-configurados con métricas
```
