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
```

Ventajas:
- No bloqueante: cada servicio avanza independientemente
- Sin coordinador central
- Escala horizontalmente
- Recuperación natural: los eventos se re-procesan al recuperar el servicio
- Consistencia eventual aceptable para logística

### Por qué Saga para logística en tiempo real

En un sistema de logística:
1. La disponibilidad es crítica (los vehículos siempre se mueven)
2. La consistencia inmediata no es necesaria (una notificación puede retrasarse segundos)
3. Los servicios deben escalar independientemente (más vehículos = más tracking, no necesariamente más notificaciones)
4. Los fallos son esperados (red móvil, reinicios de servicio)
5. Saga permite compensaciones naturales (si un servicio no procesa, el evento se reintenta o va a DLQ)

## Estrategia de Dead Letter Queue

```
Evento nuevo
  -> Cola principal (location.updated.queue)
  -> Consumidor procesa
    -> Éxito: ACK
    -> Falla (1er intento): NACK + header retry_count=1
    -> Falla (2do intento): NACK + header retry_count=2
    -> Falla (3er intento): NACK + header retry_count=3
      -> Mensaje enviado a DLX (dlx.exchange)
      -> Almacenado en DLQ (failed.events.queue)
      -> Análisis manual o reprocesamiento
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
| event_id | VARCHAR(100) | Unique para idempotencia |
| created_at | TIMESTAMP | Fecha de creación |

### notification_db.notifications

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | UUID | PK |
| vehicle_id | VARCHAR(50) | Identificador del vehículo |
| message | VARCHAR(500) | Mensaje de notificación |
| created_at | TIMESTAMP | Fecha de creación |

### route_db.routes

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | UUID | PK |
| vehicle_id | VARCHAR(50) | Identificador del vehículo |
| distance | FLOAT | Distancia calculada (km) |
| cost | FLOAT | Costo calculado (distance * 2000) |
| updated_at | TIMESTAMP | Fecha de actualización |

## Diagrama de infraestructura

```
Docker Compose
  |
  +-- postgres:16 (volumen: postgres_data)
  |     Databases: tracking_db, notification_db, route_db
  |
  +-- rabbitmq:3.13 (volumen: rabbitmq_data)
  |     Exchanges: location.exchange, dlx.exchange
  |     Queues: notification.service.queue, route.service.queue, failed.events.queue
  |
  +-- tracking-service (FastAPI, puerto 8000)
  |     Dependencias: postgres, rabbitmq
  |
  +-- notification-service (Consumer Python)
  |     Dependencias: postgres, rabbitmq
  |
  +-- route-service (Consumer Python)
      Dependencias: postgres, rabbitmq
```
