# INFORME — Backend y Servicios

**Estudiante:** [Nombre]  
**Rol:** Back-end / Servicios  
**Escenario C:** Logística en Tiempo Real

---

## ¿Qué hace el sistema?

Revisa la carpeta del proyecto, lee el `README.md` y los archivos `main.py` de cada servicio. Explica con tus palabras:

- ¿Cuántos servicios hay?
- ¿Qué hace cada uno?
- ¿Cómo se comunican entre ellos?

## ¿Cómo funciona la transacción distribuida?

Cuando un cliente envía una ubicación, ¿qué pasa paso a paso?

1.
2.
3.
4.

## ¿Qué patrón se usó? (2PC o Saga)

- ¿Cuál se usó? _______
- ¿Por qué crees que se eligió ese y no el otro?
- ¿Qué ventaja tiene para un sistema de logística?

## Idempotencia

- ¿Qué pasa si envías la misma ubicación dos veces?
- ¿Cómo lo evita el sistema?
- ¿Qué códigos HTTP devuelve? (1er vez: ___, 2da vez: ___)

## Base de datos

Completa las tablas con lo que veas en los archivos `models.py`:

| Servicio | Tabla | Columnas importantes |
|----------|-------|----------------------|
| Tracking | locations | vehicle_id, latitude, longitude, event_id, ... |
| Notification | notifications | |
| Route | routes | |

## RabbitMQ / Colas

Responde viendo `shared/event_config.py`:

- ¿Cómo se llama el exchange? _______________
- ¿Cuántas colas tiene? _______________
- ¿Qué pasa si un servicio se cae? ¿Los mensajes se pierden?

## Conclusión

Escribe 3 cosas que aprendiste sobre sistemas distribuidos con este trabajo:

1.
2.
3.
