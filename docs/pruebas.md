# Guía de Pruebas — Sistema de Logística Distribuida

## Requisitos

- Docker y Docker Compose instalados
- Puertos libres: 8000 (tracking), 9090 (prometheus), 3000 (grafana), 5673/15673 (rabbitmq), 5433 (postgres)
- User en grupo `docker`

## 0. Preparación (solo la primera vez)

Si tienes problemas de permisos con Docker, verifica que tu usuario esté en el grupo `docker`:

```bash
groups
```

Si no apareces en `docker`, agrega y cierra sesión:

```bash
sudo usermod -aG docker $USER
```

> Si ves errores de `permission denied` al detener contenedores, asegúrate de no tener instalado Docker Snap junto con Docker apt. En Ubuntu 26.04, remueve el Snap: `sudo snap remove docker`

## 1. Iniciar el sistema

```bash
cd ~/Desktop/T.S/logistica-distribuida
docker compose up --build -d
```

Verificar que los contenedores estén corriendo:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

Salida esperada:

```
NAMES                    STATUS
logistica-route          Up X seconds
logistica-tracking       Up X seconds
logistica-notification   Up X seconds
logistica-postgres       Up X seconds (healthy)
logistica-rabbitmq       Up X seconds (healthy)
logistica-prometheus     Up X seconds
logistica-grafana        Up X seconds
```

> Si ves servicios en estado `Exited`, revisa los logs: `docker logs <container>`.

---

## 2. Prueba de flujo básico

### 2.1 Enviar ubicación de un vehículo que "llega a destino" (Bogotá)

```bash
curl -X POST http://localhost:8000/locations/update \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-flujo-001" \
  -d '{"vehicle_id":"CAR-001","latitude":4.7110,"longitude":-74.0721,"timestamp":"2026-06-26T12:00:00Z"}'
```

**Respuesta esperada:**

```json
{
  "event_id": "44ba935e-8911-4c1f-aa0d-0fdf1c3026da",
  "message": "Location for CAR-001 processed",
  "status": "PENDING"
}
```

`status: "PENDING"` indica que el evento está en outbox esperando ser publicado a RabbitMQ.

### 2.2 Enviar ubicación de un vehículo en tránsito (Fuera de Bogotá)

```bash
curl -X POST http://localhost:8000/locations/update \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-flujo-002" \
  -d '{"vehicle_id":"TRUCK-001","latitude":6.2476,"longitude":-75.5658,"timestamp":"2026-06-26T12:30:00Z"}'
```

### 2.3 Verificar datos en los 3 servicios

```bash
echo "=== TRACKING DB ==="
docker exec logistica-postgres psql -U logistica -d tracking_db -c 'SELECT vehicle_id, latitude, longitude, recorded_at, status FROM locations;'
echo ""
echo "=== NOTIFICATION DB ==="
docker exec logistica-postgres psql -U logistica -d notification_db -c 'SELECT vehicle_id, message, status, created_at FROM notifications;'
echo ""
echo "=== ROUTE DB ==="
docker exec logistica-postgres psql -U logistica -d route_db -c 'SELECT vehicle_id, round(distance::numeric,2) as distance_km, round(cost::numeric,2) as cost, status, updated_at FROM routes;'
```

**Salida esperada (tracking_db):**

```
 vehicle_id | latitude | longitude |    recorded_at    |  status
------------+----------+-----------+-------------------+----------
 CAR-001    |   4.711  | -74.0721  | 2026-06-26 12:00 | COMPLETED
 TRUCK-001  |   6.2476 | -75.5658  | 2026-06-26 12:30 | COMPLETED
```

> Las ubicaciones pueden aparecer como COMPLETED si el outbox ya publicó el evento, o PENDING si el poller aún no lo procesó (esperar ~2s).

**Salida esperada (notification_db):**

```
 vehicle_id |                       message                        |  status   |         created_at
------------+------------------------------------------------------+-----------+----------------------------
 CAR-001    | Vehículo CAR-001 llegó al punto de entrega en Bogotá | COMPLETED | 2026-06-26 ...
 TRUCK-001  | Vehículo TRUCK-001 transitando en coordenadas (...   | COMPLETED | 2026-06-26 ...
```

**Salida esperada (route_db):**

```
 vehicle_id | distance_km |   cost    |  status   |         updated_at
------------+-------------+-----------+-----------+----------------------------
 CAR-001    |        0.00 |      0.00 | COMPLETED | 2026-06-26 ...
 TRUCK-001  |      237.75 | 475500.00 | COMPLETED | 2026-06-26 ...
```

> Nota: TRUCK-001 está en Medellín, ~238 km desde Bogotá (fórmula Haversine). Costo = 238 × 2000 = 475,500.

---

## 3. Prueba de idempotencia

Enviar exactamente el mismo payload con el mismo Idempotency-Key:

```bash
curl -s -X POST http://localhost:8000/locations/update \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-idemp-001" \
  -d '{"vehicle_id":"CAR-003","latitude":4.6000,"longitude":-74.0500,"timestamp":"2026-06-26T13:00:00Z"}'

curl -s -X POST http://localhost:8000/locations/update \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-idemp-001" \
  -d '{"vehicle_id":"CAR-003","latitude":4.6000,"longitude":-74.0500,"timestamp":"2026-06-26T13:00:00Z"}'
```

**Resultado esperado:**

- Primer curl → HTTP 201 Created con `event_id` nuevo
- Segundo curl → HTTP 200 OK con el mismo `event_id` (idempotente)

Confirmar que solo hay un registro:

```bash
docker exec logistica-postgres psql -U logistica -d tracking_db -c "SELECT count(*) FROM locations WHERE vehicle_id='CAR-003';"
```

Debe mostrar `count: 1`.

---

## 4. Prueba de validación de datos

```bash
# Latitud inválida (> 90)
curl -s -X POST http://localhost:8000/locations/update \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id":"CAR-004","latitude":100,"longitude":-74.0,"timestamp":"2026-06-26T14:00:00Z"}'

# Sin campos requeridos
curl -s -X POST http://localhost:8000/locations/update \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id":"CAR-004"}'

# Timestamp inválido
curl -s -X POST http://localhost:8000/locations/update \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id":"CAR-004","latitude":4.7,"longitude":-74.0,"timestamp":"invalido"}'
```

Los 3 deben devolver HTTP 422.

---

## 5. Prueba de Saga (coreografía)

Verificar que no hay comunicación directa entre servicios. Cada uno debe reaccionar solo al evento de RabbitMQ.

```bash
echo "=== TRACKING SERVICE ==="
docker logs logistica-tracking --tail 10
echo ""
echo "=== NOTIFICATION SERVICE ==="
docker logs logistica-notification --tail 10
echo ""
echo "=== ROUTE SERVICE ==="
docker logs logistica-route --tail 10
```

**Lo que debes ver:**

| Servicio | Debe mostrar |
|----------|-------------|
| tracking-service | `Published event...` o `Outbox event ... published` |
| notification-service | `Received event...` → `Notification saved...` |
| route-service | `Received event...` → `Route saved...` |

Ningún servicio debe mostrar llamadas HTTP directas a otro servicio.

---

## 6. Prueba de manejo de fallos

### 6.1 Recuperación automática de eventos (Outbox)

```bash
# 1. Detener rabbitmq (simula fallo del broker)
docker stop logistica-rabbitmq

# 2. Enviar 3 ubicaciones (quedan en outbox)
for i in 1 2 3; do
  curl -s -X POST http://localhost:8000/locations/update \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: outbox-test-$i" \
    -d "{\"vehicle_id\":\"OUTBOX-$i\",\"latitude\":4.7$i,\"longitude\":-74.0,\"timestamp\":\"2026-06-26T15:0${i}:00Z\"}"
  echo ""
done

# 3. Verificar que están en outbox (PENDING)
echo "Eventos en outbox:"
docker exec logistica-postgres psql -U logistica -d tracking_db -c "SELECT event_id, status, retry_count FROM outbox;"

# 4. Reiniciar rabbitmq
docker start logistica-rabbitmq
sleep 5

# 5. Verificar que el outbox poller los publicó
echo "Después de reconectar:"
docker exec logistica-postgres psql -U logistica -d tracking_db -c "SELECT event_id, status, retry_count, published_at FROM outbox;"
```

### 6.2 Recuperación de consumidores con retry TTL

```bash
# 1. Detener route-service
docker stop logistica-route

# 2. Enviar 3 ubicaciones
for i in 1 2 3; do
  curl -s -X POST http://localhost:8000/locations/update \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: retry-test-$i" \
    -d "{\"vehicle_id\":\"RETRY-$i\",\"latitude\":4.7,\"longitude\":-74.0,\"timestamp\":\"2026-06-26T16:0${i}:00Z\"}"
  echo ""
done

# 3. Verificar que route-service NO tiene estos registros
echo "Antes de reiniciar:"
docker exec logistica-postgres psql -U logistica -d route_db -c 'SELECT vehicle_id FROM routes;'

# 4. Verificar que notification-service SÍ los procesó
echo "Notificaciones:"
docker exec logistica-postgres psql -U logistica -d notification_db -c 'SELECT vehicle_id, message FROM notifications ORDER BY created_at DESC LIMIT 3;'

# 5. Reiniciar route-service (procesa eventos acumulados en RabbitMQ)
docker start logistica-route
sleep 5

# 6. Verificar que route-service procesó los eventos pendientes
echo "Después de reiniciar:"
docker exec logistica-postgres psql -U logistica -d route_db -c 'SELECT vehicle_id, round(distance::numeric,2) as d, round(cost::numeric,2) as c FROM routes ORDER BY updated_at DESC LIMIT 3;'
```

### 6.3 Dead Letter Queue y Compensación (3 reintentos + LOCATION_FAILED)

```bash
# 1. Enviar una ubicación con datos que forzarán error en notification
# (Esto se logra deteniendo notification-service y esperando que los reintentos se agoten)

docker stop logistica-notification

# 2. Enviar ubicación
curl -s -X POST http://localhost:8000/locations/update \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: dlq-test" \
  -d '{"vehicle_id":"DLQ-TEST","latitude":4.7,"longitude":-74.0,"timestamp":"2026-06-26T17:00:00Z"}'

# 3. Esperar a que se agoten los reintentos (> 15s para 3 reintentos con TTL 5s)
sleep 20

# 4. Ver eventos en Dead Letter Queue
echo "Abrir http://localhost:15673"
echo "User: logistica | Pass: logistica123"
echo "Ir a Queues → failed.events.queue → Get messages"

# 5. Verificar compensación: la location debe estar FAILED
docker exec logistica-postgres psql -U logistica -d tracking_db -c "SELECT vehicle_id, uuid_event_id, status FROM locations WHERE vehicle_id='DLQ-TEST';"

# 6. Reiniciar notification-service
docker start logistica-notification
```

### 6.4 Recuperación de PostgreSQL

```bash
# Detener y reiniciar PostgreSQL (los datos persisten en volumen)
docker stop logistica-postgres
docker start logistica-postgres
sleep 3

# Verificar que los datos siguen ahí
docker exec logistica-postgres psql -U logistica -d tracking_db -c 'SELECT count(*) as total_locations FROM locations;'
```

---

## 7. Prueba de carga con k6

```bash
# Ejecutar prueba de carga (hasta 100 usuarios virtuales concurrentes)
docker run --network host -i grafana/k6 run - <k6/load_test.js
```

**Criterios de éxito:**
- Tasa de fallos < 5%
- P95 de latencia < 2000ms
- Endpoint /health y /metrics responden correctamente
- Idempotencia funciona bajo carga

Para verificar después de la prueba:

```bash
echo "Total locations:"
docker exec logistica-postgres psql -U logistica -d tracking_db -c 'SELECT count(*) FROM locations;'
echo "Total notifications:"
docker exec logistica-postgres psql -U logistica -d notification_db -c 'SELECT count(*) FROM notifications;'
echo "Total routes:"
docker exec logistica-postgres psql -U logistica -d route_db -c 'SELECT count(*) FROM routes;'
```

---

## 8. Monitoreo con Prometheus y Grafana

### Prometheus (métricas)

```
URL:   http://localhost:9090
Query: http_requests_total
Query: http_request_duration_seconds
Query: outbox_size
```

### Grafana (dashboard)

```
URL:   http://localhost:3000
User:  admin
Pass:  logistica123
```

Dashboards pre-configurados disponibles en `Infrastructure` → `Logistica`.

### RabbitMQ Management

```
URL:   http://localhost:15673
User:  logistica
Pass:  logistica123
```

**Qué revisar:**
- **Exchanges** → `location.exchange` (tipo topic, bindings a ambas colas)
- **Queues**:
  - `notification.service.queue` — mensajes pendientes (0 en estado normal)
  - `route.service.queue` — mensajes pendientes (0 en estado normal)
  - `notification.service.queue.retry` — mensajes en retry (TTL 5s)
  - `route.service.queue.retry` — mensajes en retry (TTL 5s)
  - `failed.events.queue` — mensajes fallidos tras 3 reintentos
- **Channels** — conexiones activas de los servicios

---

## 9. Limpieza entre pruebas

Para borrar los registros de las 3 BD entre ejecuciones de prueba sin detener el sistema:

```bash
docker exec logistica-postgres psql -U logistica -d tracking_db -c 'DELETE FROM locations; DELETE FROM idempotency_keys; DELETE FROM outbox;'
docker exec logistica-postgres psql -U logistica -d notification_db -c 'DELETE FROM notifications;'
docker exec logistica-postgres psql -U logistica -d route_db -c 'DELETE FROM routes;'
```

Verificar que todas quedaron vacías:

```bash
echo "Tracking:" && docker exec logistica-postgres psql -U logistica -d tracking_db -c 'SELECT count(*) FROM locations;'
echo "Notifications:" && docker exec logistica-postgres psql -U logistica -d notification_db -c 'SELECT count(*) FROM notifications;'
echo "Routes:" && docker exec logistica-postgres psql -U logistica -d route_db -c 'SELECT count(*) FROM routes;'
```

---

## 10. Limpieza total

```bash
# Detener todo y eliminar volúmenes (borra TODOS los datos)
docker compose down -v

# Verificar que no quedan contenedores
docker ps -a | grep logistica
```
