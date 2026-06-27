# Sistema de Logística en Tiempo Real (MVP)

Sistema distribuido de logística basado en eventos que procesa ubicaciones de vehículos en tiempo real mediante microservicios, RabbitMQ y PostgreSQL.

## Arquitectura

```
Cliente
  |
  v
Tracking Service  (API REST /locations/update)
  |
  | LOCATION_UPDATED Event
  v
RabbitMQ  (location.exchange)
  |
  +----------------+----------------+
  |                |                |
  v                v                v
Notification    Route          Dead Letter
Service         Service         Queue
(consumidor)    (consumidor)    (fallos)
  |                |
  v                v
PostgreSQL      PostgreSQL
(notifications) (routes)
```

## Flujo de eventos

1. Cliente envía ubicación vía `POST /locations/update`
2. Tracking Service valida, guarda en PostgreSQL y publica evento `LOCATION_UPDATED`
3. RabbitMQ distribuye el evento a las colas de los suscriptores
4. Notification Service crea una notificación (ej: "Vehículo CAR-001 llegó al punto de entrega")
5. Route Service calcula distancia y costo de ruta
6. Ambos servicios guardan en sus respectivas bases de datos

## Patrón Saga (Coreografía)

No existen llamadas directas entre servicios. Cada servicio reacciona al evento de forma independiente:

- Tracking Service publica el evento `LOCATION_UPDATED`
- Notification Service escucha y genera notificaciones
- Route Service escucha y actualiza rutas

### Consistencia eventual

Cada servicio tiene su propia base de datos. La consistencia se logra de forma eventual a través de los eventos. Si un servicio falla, los eventos quedan encolados hasta que se recupere.

### Recuperación

- RabbitMQ persiste los mensajes en disco
- Cada cola tiene una Dead Letter Queue (DLX) para eventos fallidos
- Máximo 3 reintentos por evento antes de enviar a DLQ
- Reconexión automática a RabbitMQ y PostgreSQL

## Decisiones técnicas

| Decisión | Alternativa | Elección | Motivo |
|----------|-------------|----------|--------|
| Persistencia | HTAP (Hypertable) | OLTP + Cola | Los datos son transaccionales, no analíticos. La cola desacopla servicios. |
| Transacciones distribuidas | 2PC | Saga (Coreografía) | 2PC es bloqueante y no escala. Saga permite recuperación gradual. |
| Comunicación | Síncrona (HTTP) | Asíncrona (RabbitMQ) | Desacoplamiento total, tolerancia a fallos, escalabilidad horizontal. |

### OLTP + Cola vs HTAP

HTAP unifica OLTP y OLAP en un solo motor, pero introduce latencia y complejidad innecesarias para un sistema transaccional de logística. OLTP + cola ofrece:
- Menor latencia en escrituras
- Desacoplamiento de servicios
- Escalabilidad independiente
- Manejo de fallos granular

### 2PC vs Saga

2PC (Two-Phase Commit) garantiza consistencia inmediata pero es bloqueante: si un participante falla, todo se bloquea. Saga:
- No bloquea recursos
- Permite compensaciones
- Escala horizontalmente
- Adecuado para sistemas de logística en tiempo real donde la disponibilidad es crítica

## Tecnologías

- Python 3.12 + FastAPI
- SQLAlchemy + PostgreSQL
- RabbitMQ (Pika)
- Docker + Docker Compose
- Pytest
- k6 (carga)

## Cómo ejecutar

### Requisitos

- Docker y Docker Compose

### Levantar el sistema

```bash
docker compose up --build
```

Esto inicia:
- PostgreSQL (puerto 5432)
- RabbitMQ (puertos 5672, 15672)
- Tracking Service (puerto 8000)
- Notification Service
- Route Service

### Enviar una ubicación

```bash
curl -X POST http://localhost:8000/locations/update \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "CAR-001",
    "latitude": 4.7110,
    "longitude": -74.0721,
    "timestamp": "2026-06-26T12:00:00Z"
  }'
```

### Ver RabbitMQ Management

http://localhost:15672 (user: logistica, pass: logistica123)

## Pruebas

### Unitarias

```bash
# Tracking Service
cd tracking-service && pip install -r requirements.txt && PYTHONPATH=. pytest tests/

# Notification Service
cd notification-service && pip install -r requirements.txt && PYTHONPATH=. pytest tests/

# Route Service
cd route-service && pip install -r requirements.txt && PYTHONPATH=. pytest tests/
```

### Carga

```bash
docker run --network host -i grafana/k6 run - <k6/load_test.js
```

## Simulación de fallos

1. Detener un servicio: `docker compose stop route-service`
2. Enviar ubicaciones: se encolan en RabbitMQ
3. Reiniciar el servicio: `docker compose start route-service`
4. El servicio procesa los eventos pendientes automáticamente

Eventos fallidos tras 3 reintentos se almacenan en la cola `failed.events.queue`.
