# Cuestionario de Prometheus Alertmanager

Un cuestionario para poner a prueba tu comprensión de Prometheus Alertmanager.

---

1. ¿Cuál es el estado intermedio por el que pasa una alerta antes de activarse en Alertmanager?
   - A) Activa
   - B) Pendiente
   - C) Advertencia
   - D) En espera

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Pendiente**

**Explicación:**
Las alertas de Prometheus tienen tres estados: Inactive, Pending y Firing. Cuando se cumple la condición (expr) de una regla de alerta, primero pasa al estado Pending y, si la condición persiste durante el período especificado en la cláusula `for`, pasa al estado Firing y se envía a Alertmanager. Este mecanismo evita alertas innecesarias provocadas por picos temporales.

</details>

---

2. ¿Qué afirmación describe correctamente las funciones de `group_wait`, `group_interval` y `repeat_interval` en la configuración de enrutamiento de Alertmanager?
   - A) group_wait: Tiempo de espera antes de enviar la primera notificación de un grupo de alertas
   - B) group_interval: Intervalo para reenviar alertas idénticas
   - C) repeat_interval: Tiempo de espera cuando se agregan nuevas alertas a un grupo
   - D) Todas realizan la misma función

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) group_wait: Tiempo de espera antes de enviar la primera notificación de un grupo de alertas**

**Explicación:**
- `group_wait`: Tiempo de espera después de crear un nuevo grupo de alertas antes de enviar la primera notificación. Durante este período, se recopilan otras alertas que pertenecen al mismo grupo y se envían juntas.
- `group_interval`: Tiempo de espera antes de enviar la siguiente notificación cuando se agregan nuevas alertas al mismo grupo.
- `repeat_interval`: Intervalo para reenviar la misma alerta cuando aún no se ha resuelto.

</details>

---

3. ¿Qué afirmación describe correctamente la funcionalidad Inhibition de Alertmanager?
   - A) Una funcionalidad para ignorar todas las alertas durante un período específico
   - B) Una funcionalidad para suprimir alertas relacionadas cuando se activa una alerta específica
   - C) Una funcionalidad para reducir automáticamente la severidad de las alertas
   - D) Una funcionalidad para fusionar alertas duplicadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una funcionalidad para suprimir alertas relacionadas cuando se activa una alerta específica**

**Explicación:**
Inhibition es una funcionalidad que suprime las alertas relacionadas (target) cuando se activa una alerta de condición específica (source). Por ejemplo, cuando un nodo deja de funcionar, se pueden suprimir todas las alertas relacionadas con Pod de ese nodo para evitar tormentas de alertas. Silencing es una funcionalidad independiente que ignora las alertas durante un período específico.

</details>

---

4. ¿Qué significa la siguiente regla de alerta en el CRD PrometheusRule?
   ```yaml
   - alert: HighCPU
     expr: node_cpu_usage > 80
     for: 5m
     labels:
       severity: warning
   ```
   - A) La alerta se activa inmediatamente cuando el uso de CPU supera el 80 %
   - B) La alerta se activa cuando el uso de CPU supera el 80 % de forma continua durante 5 minutos
   - C) El uso de CPU se comprueba cada 5 minutos y la alerta se activa si supera el 80 %
   - D) La notificación de alerta se envía 5 minutos después de que la CPU supere el 80 %

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La alerta se activa cuando el uso de CPU supera el 80 % de forma continua durante 5 minutos**

**Explicación:**
La configuración `for: 5m` significa que la condición de alerta (expr) debe cumplirse de forma continua durante 5 minutos antes de pasar al estado Firing. Cuando se cumple la condición por primera vez, el estado se vuelve Pending y, si continúa cumpliéndose durante 5 minutos, pasa a Firing y se envía a Alertmanager. Esto evita alertas innecesarias provocadas por picos temporales.

</details>

---

5. ¿Qué significa `send_resolved: true` en la configuración de receiver de Alertmanager?
   - A) Enviar también las alertas resueltas al receiver
   - B) Incluir el método de resolución en el mensaje de alerta
   - C) Cambiar automáticamente la alerta al estado resuelto
   - D) Conceder al receiver permiso para resolver alertas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Enviar también las alertas resueltas al receiver**

**Explicación:**
La configuración `send_resolved: true` envía una notificación de resolución al receiver cuando se resuelve una alerta (cuando ya no se cumple la condición). Esto permite que quienes responden sepan que el problema se ha resuelto. El valor predeterminado varía según el tipo de receiver, pero generalmente se recomienda habilitarlo.

</details>

---

6. ¿Qué protocolo se utiliza para sincronizar el estado entre los miembros del clúster en la configuración de alta disponibilidad de Alertmanager?
   - A) Raft
   - B) Paxos
   - C) Gossip
   - D) gRPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Gossip**

**Explicación:**
Los clústeres de Alertmanager utilizan el protocolo Gossip para sincronizar el estado entre los miembros. Esto permite compartir la información de Silence y los registros de notificaciones (nflog) entre todas las instancias, evitando notificaciones de alerta duplicadas. Al configurar un clúster, utiliza la opción `--cluster.peer` para especificar otros miembros.

</details>

---

7. En la siguiente configuración de enrutamiento de Alertmanager, ¿a qué receiver se enviará una alerta con `severity=critical` y `team=infra`?
   ```yaml
   route:
     receiver: 'default'
     routes:
       - match:
           severity: critical
         receiver: 'critical-receiver'
       - match:
           team: infra
         receiver: 'infra-team'
   ```
   - A) default
   - B) critical-receiver
   - C) infra-team
   - D) Ambos critical-receiver e infra-team

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) critical-receiver**

**Explicación:**
El enrutamiento de Alertmanager funciona como una estructura de árbol y, de forma predeterminada, el procesamiento termina en la primera ruta coincidente. En este caso, la condición `severity=critical` coincide primero, por lo que la alerta se envía a `critical-receiver`. Para enviar a varias rutas, se requiere la configuración `continue: true`.

</details>

---

8. ¿Cuál es el propósito principal del CRD AlertmanagerConfig?
   - A) Definir la configuración global de Alertmanager
   - B) Separar la configuración de alertas por namespace
   - C) Definir reglas de alerta de Prometheus
   - D) Configurar el clúster de Alertmanager

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Separar la configuración de alertas por namespace**

**Explicación:**
El CRD AlertmanagerConfig es un recurso proporcionado por Prometheus Operator que permite gestionar la configuración de Alertmanager (receivers, rutas, reglas de inhibition, etc.) por separado según el namespace. Esto permite que cada equipo gestione de forma independiente la configuración de alertas en su propio namespace.

</details>

---

9. ¿Cuál NO es un caso de uso adecuado para crear un Silence en Alertmanager?
   - A) Suprimir alertas durante mantenimiento planificado
   - B) Evitar alertas repetidas de problemas conocidos
   - C) Deshabilitar permanentemente alertas específicas
   - D) Suprimir alertas durante un deployment

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Deshabilitar permanentemente alertas específicas**

**Explicación:**
Silence es una funcionalidad que suprime temporalmente las alertas y siempre debe especificar una hora de finalización. Para deshabilitar alertas de forma permanente, debes modificar o eliminar la propia regla de alerta. Los casos de uso principales de Silence son situaciones temporales como mantenimiento, deployment o la investigación de problemas conocidos.

</details>

---

10. ¿Cuál de las siguientes NO es una sintaxis válida de plantilla Go que puede utilizarse en las plantillas de Alertmanager?
    - A) <code v-pre>{{ .Labels.alertname }}</code>
    - B) <code v-pre>{{ if eq .Status "firing" }}Danger{{ end }}</code>
    - C) <code v-pre>{{ range .Alerts }}{{ .Labels.severity }}{{ end }}</code>
    - D) <code v-pre>{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}</code>

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) <code v-pre>{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}</code>**

**Explicación:**
Las plantillas Go no admiten el operador ternario (`? :`). En su lugar, debes utilizar sentencias <code v-pre>{{ if }}</code>. La sintaxis correcta sería:
```
{{ if gt (len .Annotations.description) 100 }}
  {{ slice .Annotations.description 0 100 }}...
{{ else }}
  {{ .Annotations.description }}
{{ end }}
```
Las plantillas Go admiten pipes (`|`), condicionales (`if`/`else`), bucles (`range`), funciones integradas, etc.

</details>

---

## Recursos adicionales de aprendizaje

- [Documentación de alertas de Prometheus](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Configuración de Alertmanager](https://prometheus.io/docs/alerting/latest/configuration/)
- [Prometheus Operator - AlertmanagerConfig](https://prometheus-operator.dev/docs/user-guides/alerting/)
