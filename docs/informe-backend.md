# INFORME — Backend y Servicios

**Estudiante:** [Nombre]  
**Rol:** Back-end / Servicios  
**Escenario C:** Logística en Tiempo Real

---

## ¿Qué hace el sistema?

Revisa la carpeta del proyecto, lee el `README.md` y los archivos `main.py`, `consumer.py` y `services.py` de cada servicio. Explica con tus palabras:

- ¿Cuántos servicios hay?
- ¿Qué hace cada uno?
- ¿Cómo se comunican entre ellos?

## ¿Cómo funciona la transacción distribuida?

Cuando un cliente envía una ubicación, ¿qué pasa paso a paso?

1.
2.
3.
4.
5.
6.

## ¿Qué patrón se usó? (2PC o Saga)

- ¿Cuál se usó? _______
- ¿Por qué crees que se eligió ese y no el otro?
- ¿Qué ventaja tiene para un sistema de logística?
- ¿Cómo funciona la compensación cuando un consumidor falla?

## Idempotencia

- ¿Qué header HTTP se usa para idempotencia?
- ¿Qué pasa si envías la misma ubicación con el mismo Idempotency-Key?
- ¿Qué códigos HTTP devuelve? (1er vez: ___, 2da vez: ___)
- ¿Dónde se almacenan las claves de idempotencia?

## Outbox Pattern

- ¿Qué pasa si RabbitMQ se cae justo después de guardar la ubicación?
- ¿Cómo evita el Outbox Pattern la pérdida de eventos?
- ¿Qué tabla almacena los eventos pendientes?

## Base de datos

Completa las tablas con lo que veas en los archivos `models.py`:

| Servicio | Tablas | Columnas importantes |
|----------|--------|----------------------|
| Tracking | locations | vehicle_id, latitude, longitude, event_id, uuid_event_id, status, ... |
| Tracking | idempotency_keys | |
| Tracking | outbox | |
| Notification | notifications | |
| Route | routes | |

## RabbitMQ / Colas

Responde viendo `shared/event_config.py`:

- ¿Cómo se llama el exchange? _______________
- ¿Qué tipos de colas hay? (principales, retry, DLQ)
- ¿Cuántos reintentos tiene un evento antes de ir a DLQ?
- ¿Cuánto tiempo espera entre reintentos?
- ¿Qué pasa si un servicio se cae? ¿Los mensajes se pierden?

## Conclusión

Escribe 3 cosas que aprendiste sobre sistemas distribuidos con este trabajo:

1.
2.
3.
