# INFORME — Pruebas, Observabilidad y Rendimiento

**Estudiante:** [Nombre]  
**Rol:** Observabilidad & Pruebas  
**Escenario C:** Logística en Tiempo Real

---

## ¿Qué se probó?

Revisa `docs/pruebas.md` y escribe qué tipos de prueba hay:

| Tipo de prueba | ¿En qué consiste? |
|----------------|-------------------|
| Flujo básico | |
| Idempotencia | |
| Validación | |
| Outbox / Recuperación | |
| Fallos DLQ / Compensación | |
| Carga (k6) | |

## Prueba de flujo básico

- ¿Qué respuesta da el POST al enviar CAR-001 en Bogotá?
- ¿Qué valor tiene `status` en la respuesta?
- ¿En qué tablas aparecen los datos después? (tracking_db, notification_db, route_db)

## Prueba de idempotencia

- Envía el mismo payload con el mismo `Idempotency-Key` 2 veces:
  - 1ra vez: HTTP _____
  - 2da vez: HTTP _____
- ¿Por qué es importante la idempotencia en un sistema distribuido?
- ¿Qué diferencia hay entre la idempotencia por `Idempotency-Key` y la del par `vehicle_id + timestamp`?

## Prueba de validación

¿Qué códigos HTTP devuelven estos casos?

| Caso | HTTP |
|------|:----:|
| Latitud = 100 (>90) | |
| Faltan campos | |
| Timestamp inválido | |

## Prueba de fallos

- **Outbox**: ¿qué pasa si detienes RabbitMQ y envías ubicaciones? ¿Se pierden?
- **Retry TTL**: ¿cuántos reintentos hace un consumidor antes de enviar a DLQ?
- ¿Cuánto tiempo espera entre reintentos?
- ¿Qué evento de compensación se publica cuando se agotan los reintentos?
- ¿Qué servicio consume ese evento?
- ¿Qué cambia en el tracking service cuando recibe una compensación?

## Observabilidad

### Logs

- ¿En qué formato están los logs?
- Busca un ejemplo en los archivos del proyecto.

### Métricas Prometheus

- ¿Qué URL expone las métricas?
- Nombra 3 métricas disponibles
- ¿Qué información da el histograma `http_request_duration_seconds`?

### Grafana

- ¿En qué URL está Grafana?
- ¿Qué datasource está configurado?

## Prueba de carga (k6)

Revisa `k6/load_test.js`:

- ¿Cuántos VUs máximos simula?
- ¿Qué endpoints prueba?
- ¿Qué thresholds tiene configurados?
- ¿Qué prueba adicional de idempotencia incluye?

## Trade-offs (compensaciones)

Completa con lo que aprendiste:

| Decisión | Ventaja | Desventaja |
|----------|---------|------------|
| Saga en vez de 2PC | | |
| Cada servicio con su BD | | |
| Outbox Pattern | | |
| RabbitMQ con retry TTL | | |
| Circuit Breaker | | |
| Consistencia eventual | | |

## Conclusión

Escribe 3 cosas que aprendiste sobre pruebas y observabilidad en sistemas distribuidos:

1.
2.
3.
