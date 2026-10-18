# Cuestionario de planificación de capacidad para eventos

> **Documento relacionado**: [Planificación de capacidad para eventos](../../ops/12-event-capacity-planning.md)

## 1. ¿Cómo se usan varias métricas de KEDA para determinar el objetivo?

- A) Sumar todos los valores
- B) HPA combina las recomendaciones por métrica mediante el máximo y aplica el comportamiento y los límites mínimo y máximo
- C) Cron garantiza que haya Pods en estado Ready
- D) Las métricas siempre definen el límite superior

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Cron proporciona un mínimo programado de demanda; `maxReplicaCount` y otras restricciones lo limitan. Comprueba por separado que las réplicas estén listas.

</details>

## 2. ¿Qué hay que tener en cuenta al usar un Cron de cinco campos para un evento con fecha?

- A) El año se agrega implícitamente
- B) Se elimina solo después de ejecutarse una vez
- C) Puede repetirse el año siguiente y requiere comprobar la zona horaria y el horario de verano
- D) Siempre usa únicamente UTC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El ejemplo comprueba la recurrencia anual y sus límites temporales. Después, elimina o actualiza la configuración del evento.

</details>

## 3. ¿Qué configuración describe un NodePool estático de Karpenter?

- A) Un peso más alto, por sí solo, crea capacidad estática
- B) Usar réplicas sin peso y restringir `limits.nodes`
- C) Quitar las réplicas en cualquier momento para cambiar al modo dinámico
- D) Las operaciones de escalado siempre quedan bloqueadas por todos los presupuestos de NodePool

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Distingue los modos estático y dinámico. El escalado estático omite los presupuestos de interrupción de NodePool, pero respeta los PDB.

</details>

## 4. ¿Qué puede ocurrir si el recuento deseado del Deployment de marcadores no cambia después del traspaso?

- A) Siempre se mantiene sin costo adicional
- B) Los marcadores recreados pueden provocar que se aprovisionen nodos adicionales
- C) Karpenter establece automáticamente el recuento deseado en cero
- D) La aplicación real siempre queda lista inmediatamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Valida conjuntamente la retención y caducidad, la eliminación de la demanda de marcadores y la disponibilidad real de la aplicación.

</details>

## 5. ¿Agregar un 30 % de capacidad garantiza sobrevivir a la pérdida de una zona de disponibilidad?

- A) Siempre
- B) Sí, si se usa On-Demand
- C) No; calcula la ubicación y el rendimiento que queda disponible
- D) Sí, siempre que exista un PDB

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

En el ejemplo de 15 y 11 nodos, no se alcanza la demanda máxima de referencia después de perder la zona más grande. También valida con mediciones las hipótesis de entrada.

</details>

## 6. ¿Qué significa una Capacity Reservation dirigida?

- A) Una ACL de seguridad restringida a un NodePool
- B) Las instancias la seleccionan explícitamente y deben cumplir los criterios coincidentes
- C) Se aplica automáticamente a todas las instancias existentes
- D) Un producto de descuento On-Demand

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Comprueba IAM y el uso compartido, la zona de disponibilidad, el tipo, la plataforma, la tenencia y el consumo real. Es distinta de una instancia reservada (RI).

</details>

## 7. ¿Qué ocurre si se crea una reserva inmediata en D-30 con solo un `end_date` futuro?

- A) Espera sin costo hasta el evento
- B) `end_date` define un inicio futuro
- C) La capacidad activa que no se usa puede generar cargos
- D) La capacidad ocupada siempre se cobra dos veces

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Incluye en el modelo de costos todo el intervalo activo y evita contar dos veces las instancias que ocupan las reservas.

</details>

## 8. ¿Qué afirmación sobre `metricStat` y `minMetricValue` del escalador de CloudWatch es correcta?

- A) El campo correcto es `metricStatType`
- B) `minMetricValue` siempre es el umbral de activación
- C) `metricStat` selecciona la estadística; `minMetricValue` es el valor alternativo para NoData, salvo que lo anule `ignoreNullValues=false`
- D) `Sum` sirve para todas las métricas expresadas como tasa

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Distingue los incrementos y recuentos de las tasas y los contadores acumulativos. Verifica también el periodo, la ventana de recopilación y la demora de publicación.

</details>

## 9. ¿Cómo se debe manejar una carga de trabajo administrada por KEDA cuando se retrasan las métricas?

- A) Los cambios directos de Deployment siempre se conservan
- B) El HPA siempre tiene el mismo nombre que el Deployment
- C) Revisar el mínimo de ScaledObject dentro de los límites aprobados y respetar la propiedad de GitOps
- D) Crear un NodePool sin límite

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

La reconciliación puede sobrescribir los cambios directos de HPA o Deployment. Registra la configuración original y restáurala.

</details>

## 10. ¿Qué afirmación sobre la preparación y la limpieza es correcta?

- A) Todas las imágenes admiten `sh` y `echo`, y conservan la caché indefinidamente
- B) Siempre es seguro eliminar un NodePool después de treinta minutos
- C) Validar las restricciones de la aplicación y de la caché, los desencadenantes de referencia y la limpieza real de nodos y reservas
- D) Eliminar un ScaledObject siempre restaura las réplicas originales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El inicio, la recolección de basura, la arquitectura y los permisos varían. La limpieza debe tener en cuenta los controladores propietarios y el ciclo de eliminación de recursos.

</details>
