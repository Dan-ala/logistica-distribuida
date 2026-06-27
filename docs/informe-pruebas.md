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
| Fallos / Recuperación | |
| Carga (k6) | |

## Prueba de flujo básico

Ejecuta o revisa el paso 2 de `docs/pruebas.md` y completa:

- 1er curl: envía CAR-001 en Bogotá → ¿qué responde? _______
- 2do curl: envía TRUCK-001 en Medellín → ¿qué responde? _______

### ¿En qué tablas aparecen los datos después?

| Base de datos | ¿Qué registros aparecen? |
|---------------|--------------------------|
| tracking_db | |
| notification_db | |
| route_db | |

## Prueba de idempotencia

- Envía el mismo payload 2 veces:
  - 1ra vez: HTTP _____
  - 2da vez: HTTP _____
- ¿Por qué es importante esto?

## Prueba de validación

¿Qué códigos HTTP devuelven estos casos?

| Caso | HTTP |
|------|:----:|
| Latitud = 100 (>90) | |
| Faltan campos (latitude, longitude, timestamp) | |
| Timestamp inválido ("invalido") | |

## Prueba de fallos

Revisa el paso 6 de `docs/pruebas.md`:

- ¿Qué pasa si detienes `route-service` y envías ubicaciones?
- ¿Los datos se pierden? _______
- ¿Qué pasa cuando reinicias el servicio?

## Prueba de carga (k6)

Revisa `k6/load_test.js` y responde:

- ¿Cuántos usuarios virtuales simula? _______
- ¿Qué métricas mide? _______
- ¿Cuál es el máximo de fallos permitido? _______

## Trade-offs (compensaciones)

Completa con lo que aprendiste:

| Decisión | Ventaja | Desventaja |
|----------|---------|------------|
| Saga en vez de 2PC | | |
| Cada servicio con su BD | | |
| Usar RabbitMQ | | |
| Consistencia eventual | | |

## Conclusión

Escribe 3 cosas que aprendiste sobre pruebas en sistemas distribuidos:

1.
2.
3.
