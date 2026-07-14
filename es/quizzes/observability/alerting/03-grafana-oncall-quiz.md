# Cuestionario de Grafana OnCall

Un cuestionario para evaluar tu comprensión de Grafana OnCall.

---

1. ¿Cuál NO es una característica clave de Grafana OnCall?
   - A) Gestión de calendarios de guardia
   - B) Configuración de cadenas de escalamiento
   - C) Recopilación y almacenamiento de métricas
   - D) Integración con ChatOps (Slack, Teams)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Recopilación y almacenamiento de métricas**

**Explicación:**
Grafana OnCall es una herramienta de gestión de guardias y respuesta a incidentes que proporciona las siguientes características:
- Gestión de calendarios de guardia (rotaciones, sustituciones)
- Configuración de cadenas de escalamiento
- Agrupación y enrutamiento de alertas
- Integración con ChatOps (Slack, MS Teams, Telegram)
- Notificaciones de aplicaciones móviles

La recopilación y el almacenamiento de métricas son funciones de otras herramientas como Prometheus o Grafana Mimir. OnCall recibe y procesa las alertas generadas por estas herramientas.

</details>

---

2. ¿Cuál es la función del tipo `wait` en la política de escalamiento de Grafana OnCall?
   - A) Esperar la recopilación de datos antes de enviar alertas
   - B) Esperar antes de pasar al siguiente paso de escalamiento
   - C) Esperar la respuesta del usuario y luego resolver automáticamente
   - D) Esperar la agrupación de alertas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Esperar antes de pasar al siguiente paso de escalamiento**

**Explicación:**
En las cadenas de escalamiento, el tipo `wait` establece un tiempo de espera entre el paso actual y el siguiente. Por ejemplo:
1. Paso 1: Notificar a la persona responsable de guardia actual
2. Paso 2: esperar 900 segundos (15 minutos)
3. Paso 3: Si no hay respuesta, notificar a la persona responsable secundaria

Esto da tiempo a la persona responsable principal para responder, y el escalamiento solo continúa si no hay respuesta.

</details>

---

3. ¿Qué es un "Override" en el calendario de guardia de Grafana OnCall?
   - A) Eliminar y recrear completamente el calendario
   - B) Cambiar temporalmente a la persona responsable durante un período específico en el calendario existente
   - C) Cambiar la zona horaria del calendario
   - D) Modificar el ciclo de rotación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cambiar temporalmente a la persona responsable durante un período específico en el calendario existente**

**Explicación:**
Override es una característica que cambia temporalmente a la persona responsable durante un período específico en un calendario de guardia regular. Casos de uso principales:
- Sustitución de la persona responsable debido a vacaciones
- Cambio temporal debido a situaciones de emergencia
- Intercambio temporal debido a capacitaciones/reuniones

Override designa a una persona responsable diferente durante un período específico mientras mantiene el calendario existente.

</details>

---

4. ¿Qué método se utiliza al integrar Grafana OnCall con Alertmanager?
   - A) Alertmanager recopila directamente las métricas de OnCall
   - B) Enviar alertas a OnCall mediante los webhook_configs de Alertmanager
   - C) OnCall consulta periódicamente la API de Alertmanager
   - D) Ambos sistemas comparten una base de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Enviar alertas a OnCall mediante los webhook_configs de Alertmanager**

**Explicación:**
La integración de Alertmanager y Grafana OnCall se realiza mediante webhooks:
```yaml
receivers:
  - name: 'grafana-oncall'
    webhook_configs:
      - url: 'https://oncall.example.com/api/v1/webhook/<integration-id>/'
        send_resolved: true
```

Cuando Alertmanager dispara una alerta, envía una solicitud HTTP POST a la URL de webhook configurada, y OnCall la recibe y procesa.

</details>

---

5. ¿Cuál es el propósito principal de la agrupación de alertas en Grafana OnCall?
   - A) Ordenar las alertas por hora
   - B) Agrupar las alertas relacionadas en una sola para reducir la fatiga de alertas
   - C) Clasificar las alertas por gravedad
   - D) Eliminar automáticamente las alertas duplicadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Agrupar las alertas relacionadas en una sola para reducir la fatiga de alertas**

**Explicación:**
La agrupación de alertas gestiona como un único grupo varias alertas causadas por el mismo problema. Por ejemplo, si se producen varias alertas de Pod debido a un fallo de nodo, se agrupan para que la persona responsable reciba una alerta agrupada en lugar de decenas de alertas individuales. Se define una clave de agrupación (por ejemplo, alertname + namespace) para determinar qué alertas se agrupan.

</details>

---

6. ¿Qué sucede cuando el indicador `important` es true para `notify_on_call_from_schedule` en la política de escalamiento de Grafana OnCall?
   - A) La alerta se marca como de máxima prioridad
   - B) La alerta se envía mediante todos los canales configurados (teléfono, SMS, push, etc.)
   - C) La cadena de escalamiento se omite y la alerta se envía inmediatamente al supervisor
   - D) La alerta se almacena permanentemente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La alerta se envía mediante todos los canales configurados (teléfono, SMS, push, etc.)**

**Explicación:**
El significado del indicador `important`:
- `important: true`: Enviar una alerta mediante todos los canales de notificación configurados por el usuario (teléfono, SMS, push móvil, Slack, etc.)
- `important: false`: Enviar una alerta solo mediante los canales predeterminados (por ejemplo, Slack)

Esto permite ajustar la intensidad de las alertas según la gravedad. Las alertas críticas se pueden configurar con important=true para incluir teléfono/SMS, mientras que Warning se puede configurar con important=false para usar solo Slack.

</details>

---

7. ¿Cuál NO es un comando disponible al usar la integración de Slack con Grafana OnCall?
   - A) /oncall ack (reconocer alerta)
   - B) /oncall resolve (resolver alerta)
   - C) /oncall deploy (ejecutar Deployment)
   - D) /oncall silence 2h (silenciar durante 2 horas)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) /oncall deploy (ejecutar Deployment)**

**Explicación:**
Comandos de Grafana OnCall para Slack:
- `/oncall` - Consultar la persona responsable de guardia actual
- `/oncall schedule` - Ver el calendario
- `/oncall ack` - Reconocer alerta
- `/oncall resolve` - Resolver alerta
- `/oncall silence 2h` - Silenciar durante 2 horas
- `/oncall unsilence` - Quitar el silencio
- `/oncall escalate` - Escalar alerta

La ejecución de Deployment no es una característica de OnCall. OnCall se centra en la gestión de alertas y de guardias.

</details>

---

8. ¿Cuál NO es una ventaja de Grafana OnCall en comparación con PagerDuty/OpsGenie?
   - A) Código abierto y puede alojarse de forma autogestionada
   - B) Integración nativa con el stack de Grafana
   - C) Compatibilidad con más de 700 integraciones
   - D) Uso gratuito (versión OSS)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Compatibilidad con más de 700 integraciones**

**Explicación:**
Más de 700 integraciones es una ventaja de PagerDuty. Comparación:
- **Grafana OnCall**: más de 30 integraciones, código abierto, posibilidad de alojamiento autogestionado, integración nativa con Grafana, gratuito (OSS)
- **PagerDuty**: más de 700 integraciones, solo SaaS, analítica/informes avanzados, características de AIOps
- **OpsGenie**: más de 200 integraciones, solo SaaS, integración con el ecosistema de Atlassian

OnCall es una opción rentable para entornos que utilizan el stack de Grafana, pero PagerDuty puede ser más adecuado cuando se necesitan integraciones con diversos sistemas externos.

</details>

---

9. ¿Cuál es la configuración recomendada para alta disponibilidad en un Deployment de producción de Grafana OnCall?
   - A) Una sola instancia es suficiente
   - B) Aumentar el número de réplicas del servidor API y de los workers de Celery, y utilizar PostgreSQL/Redis externos
   - C) Deployment distribuido en varios clusters
   - D) Agregar únicamente réplicas de solo lectura

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aumentar el número de réplicas del servidor API y de los workers de Celery, y utilizar PostgreSQL/Redis externos**

**Explicación:**
Configuración de HA de producción para Grafana OnCall:
- **Servidor API**: más de 3 réplicas, configuración de Pod Anti-Affinity
- **Workers de Celery**: más de 3 réplicas, configuración de Pod Anti-Affinity
- **PostgreSQL**: Usar una DB administrada externa (AWS RDS, etc.)
- **Redis**: Usar Redis administrado externo (AWS ElastiCache, etc.)

Esta configuración elimina los puntos únicos de fallo y permite que el servicio siga funcionando incluso cuando fallan componentes individuales.

</details>

---

10. ¿Cuál es el propósito principal de configurar rutas en Grafana OnCall?
    - A) Distribución del tráfico de red
    - B) Aplicar diferentes cadenas de escalamiento según las condiciones de alerta
    - C) Optimización de consultas de bases de datos
    - D) Configuración de la ruta de autenticación de usuarios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplicar diferentes cadenas de escalamiento según las condiciones de alerta**

**Explicación:**
Las rutas conectan las alertas entrantes con las cadenas de escalamiento adecuadas según sus atributos (labels, gravedad, equipo, etc.):
- `severity=critical` -> Cadena de escalamiento crítica (incluye teléfono/SMS)
- `team=infra` -> Cadena de escalamiento del equipo de infraestructura
- `namespace=production` -> Calendario de guardia de producción

Las reglas de enrutamiento se definen mediante expresiones regulares y realizan coincidencias según el contenido de la carga útil de la alerta. Esto permite aplicar las personas responsables y políticas de escalamiento adecuadas para los diferentes tipos de alerta.

</details>

---

## Recursos de aprendizaje adicionales

- [Documentación de Grafana OnCall](https://grafana.com/docs/oncall/latest/)
- [GitHub de Grafana OnCall](https://github.com/grafana/oncall)
- [Helm Chart de Grafana OnCall](https://github.com/grafana/helm-charts/tree/main/charts/oncall)
- [Grafana IRM (Gestión de respuesta a incidentes)](https://grafana.com/products/cloud/irm/)
