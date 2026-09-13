# Cuestionario de Prometheus Alertmanager

> **Última actualización**: September 13, 2026

---

1. Cuando una regla de alerta de Prometheus tiene una duración `for` positiva, ¿qué estado precede a Firing?
   - A) Active
   - B) Pending
   - C) Warning
   - D) Waiting

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Pending**

Pending pertenece a la evaluación de reglas de Prometheus, no a una etapa de evaluación de Alertmanager. La condición debe permanecer presente en evaluaciones sucesivas durante la duración configurada. Sin `for` (o con valor cero), puede activarse en la primera evaluación coincidente. La agrupación de notificaciones añade retrasos independientes; `keep_firing_for` puede mantener Firing después de que la expresión deje de coincidir.

</details>

---

2. ¿Qué afirmación sobre los temporizadores de agrupación es correcta?
   - A) `group_wait` retrasa la primera notificación de un grupo nuevo.
   - B) `group_interval` es solo el intervalo de repetición para alertas sin cambios.
   - C) `repeat_interval` es el primer retraso para alertas recién añadidas.
   - D) Los tres temporizadores son idénticos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) `group_wait` retrasa la primera notificación de un grupo nuevo.**

`group_interval` programa comprobaciones posteriores del grupo, incluidos los cambios y las alertas resueltas. `repeat_interval` controla las notificaciones repetidas de alertas Firing sin cambios, comprobadas en los intervalos del grupo; use un múltiplo de `group_interval`. La retención del registro de notificaciones puede provocar una repetición anterior. Estos temporizadores son independientes del `for` de una regla de Prometheus.

</details>

---

3. ¿Qué hace la inhibición?
   - A) Ignora cada alerta durante una ventana de tiempo.
   - B) Suprime las notificaciones de destino coincidentes mientras haya una alerta de origen coincidente activa.
   - C) Cambia automáticamente la gravedad de la alerta.
   - D) Elimina alertas duplicadas de Prometheus.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Suprime las notificaciones de destino coincidentes mientras haya una alerta de origen coincidente activa.**

La inhibición cambia la idoneidad para recibir notificaciones, no la condición de alerta subyacente. Los matchers de origen/destino y las etiquetas de igualdad deben representar la dependencia prevista. Las etiquetas de igualdad ausentes se comparan como valores vacíos, por lo que se deben exigir etiquetas de correlación no vacías, como `cluster` y `node`, para evitar suprimir alertas no relacionadas. El orden de la lista de reglas no es un sistema de prioridades.

</details>

---

4. ¿Qué significa el `for` de esta regla?

   ```yaml
   - alert: HighCPU
     expr: 100 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100 > 80
     for: 5m
     labels:
       severity: warning
   ```
   - A) Notifica inmediatamente cuando la CPU supera el 80 %.
   - B) Entra en Firing después de que la condición persista durante cinco minutos a lo largo de las evaluaciones.
   - C) Evalúa la CPU solo una vez cada cinco minutos.
   - D) Garantiza la entrega exactamente cinco minutos después del aumento físico de la CPU.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Entra en Firing después de que la condición persista durante cinco minutos a lo largo de las evaluaciones.**

Esto supone contadores de CPU de node-exporter recopilados y un intervalo de evaluación adecuado. `for` no establece el intervalo de recopilación/evaluación ni garantiza un plazo de entrega. Un conjunto de etiquetas modificado identifica una alerta diferente; la recuperación restablece Pending a menos que se aplique un comportamiento independiente de retención de Firing. El ejemplo de CrashLoop primero usa una ventana de observación de cinco minutos y luego `for: 10m`: esto cubre los intervalos entre reintentos y descarta una espera aislada, con un retraso de limpieza relacionado con el período de búsqueda retrospectiva.

</details>

---

5. ¿Qué habilita `send_resolved: true`?
   - A) Notificaciones de resolución para esa integración.
   - B) Instrucciones de remediación automática.
   - C) Cambiar la condición de alerta a saludable.
   - D) Permiso para que el receptor repare el cluster.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Notificaciones de resolución para esa integración.**

Controla las notificaciones de resolución para la integración elegida; los valores predeterminados difieren según el receptor. Resolved es un estado del ciclo de vida de una alerta, no una prueba independiente de que un Service se haya recuperado. Los cambios en la expresión, la falta de datos o el comportamiento de actualización/expiración del cliente también pueden afectar a ese estado.

</details>

---

6. ¿Qué protocolo se utiliza para la sincronización del estado del cluster de Alertmanager?
   - A) Raft
   - B) Paxos
   - C) Gossip
   - D) gRPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Gossip**

Gossip comparte los silences y el estado del registro de notificaciones con consistencia eventual. Envíe las mismas alertas a cada réplica; la capa Gossip no reemplaza esa distribución. La deduplicación se realiza según el mejor esfuerzo, y las particiones de red pueden producir duplicados. No se trata de una entrega exactamente una vez ni de una garantía contra toda pérdida de notificaciones.

</details>

---

7. Para `severity=critical, team=infra`, ¿qué ruta se selecciona a continuación?

   ```yaml
   route:
     receiver: default
     routes:
       - matchers: ['severity="critical"']
         receiver: critical-receiver
       - matchers: ['team="infra"']
         receiver: infra-team
   ```
   - A) default
   - B) critical-receiver
   - C) infra-team
   - D) Ambas rutas secundarias

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) critical-receiver**

Con el valor predeterminado `continue: false`, el primer elemento hermano coincidente detiene el recorrido de los elementos hermanos. Establezca `continue: true` en él para considerar elementos hermanos posteriores. Esto solo prueba el enrutamiento de etiquetas: una ruta inactiva/silenciada aún puede detener el recorrido, por lo que el comportamiento de las ventanas de tiempo requiere comprobaciones independientes. Varias integraciones dentro de un receptor no requieren `continue`. Las reglas de destino del proveedor siguen siendo aplicables: las URL de webhook entrante de Slack están vinculadas a un canal, por lo que los canales normales y críticos requieren archivos de webhook/claves de Secret distintos, no una anulación de canal.

</details>

---

8. ¿Qué habilita AlertmanagerConfig propiedad de un namespace?
   - A) Omitir automáticamente todas las restricciones de namespace.
   - B) Gestionar rutas/receptores estructurados seleccionados por una instancia de Alertmanager.
   - C) Definir reglas de registro y de alerta de PromQL.
   - D) Reemplazar la configuración de pares Gossip.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Gestionar rutas/receptores estructurados seleccionados por una instancia de Alertmanager.**

El Operator debe seleccionar las etiquetas y el namespace del objeto, y los Secrets referenciados deben existir en el namespace requerido. Su estrategia de matchers controla la aplicación de namespace. El chart revisado de Operator 0.93.1 sirve `v1alpha1`; no invente una actualización de API obligatoria. El uso de configuración global es una opción independiente, y la coincidencia de etiquetas de namespace no autentica a los remitentes de alertas.

</details>

---

9. ¿Cuál no es un propósito adecuado para un Silence?
   - A) Mantenimiento planificado.
   - B) Una ventana de investigación limitada.
   - C) Deshabilitar permanentemente una regla de alerta.
   - D) Una ventana de despliegue revisada.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Deshabilitar permanentemente una regla de alerta.**

Un silence requiere una hora de finalización finita y afecta a las notificaciones. La expiración termina la supresión; no es una eliminación inmediata del historial de silences almacenado. Los cambios permanentes de reglas/enrutamiento requieren una revisión independiente. Registre el propietario, el motivo y el alcance aprobado; los recordatorios de expiración necesitan un flujo de trabajo configurado explícitamente.

</details>

---

10. ¿Qué expresión tiene una sintaxis no válida de plantilla Go?
   - A) `{{ .CommonLabels.alertname }}`
   - B) `{{ if eq .Status "firing" }}Danger{{ end }}`
   - C) `{{ range .Alerts }}{{ .Labels.severity }}{{ end }}`
   - D) `{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) `{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}`**

Las plantillas Go no admiten esta expresión ternaria. En la raíz, Alertmanager proporciona Data con CommonLabels/CommonAnnotations; Labels/Annotations/StartsAt pertenecen a una Alert individual dentro de `range .Alerts`. El ejemplo siguiente da formato a un máximo de 100 runas por descripción, evitando un corte de bytes que podría dividir texto coreano. Se trata de formato de salida, no de enmascaramiento de datos sensibles.

```text
{{ range .Alerts }}
{{ printf "%.100s" .Annotations.description }}
{{ end }}
```

</details>

---

## Recursos de aprendizaje adicionales

- [Configuración de Alertmanager 0.34](https://github.com/prometheus/alertmanager/blob/v0.34.0/docs/configuration.md)
- [Referencia de plantillas de notificación](https://github.com/prometheus/alertmanager/blob/v0.34.0/docs/notifications.md)
- [Alertas de Prometheus Operator](https://prometheus-operator.dev/docs/developer/alerting/)

[Volver a la guía](../../../observability/alerting/01-alertmanager.md)
