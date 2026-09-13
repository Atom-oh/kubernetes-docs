# Cuestionario de Grafana OnCall

> **Última actualización**: September 13, 2026

Este cuestionario cubre la revisión/migración de instalaciones archivadas de OnCall OSS.

Un cuestionario para evaluar tu comprensión de Grafana OnCall.

**Cloud Connection finalizó el 2026-03-24.** Las notificaciones push móviles de OSS mediante la aplicación Grafana IRM y las notificaciones por SMS/voz que dependen de Cloud Connection ya no funcionan. Los servicios de notificación de Twilio u otros configurados por separado son vías distintas; esto no significa que todos los mecanismos de teléfono/SMS autoalojados hayan finalizado.

---

1. ¿Cuál NO es una característica principal de Grafana OnCall?
   - A) Gestión de horarios de guardia
   - B) Configuración de cadenas de escalamiento
   - C) Recopilación y almacenamiento de métricas
   - D) Integración con ChatOps (Slack, Teams)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Recopilación y almacenamiento de métricas**

**Explicación:**
OnCall recibe y gestiona alertas, horarios, enrutamiento y acciones de los respondedores; no es una base de datos de métricas. OSS se archivó el 2026-03-24. La disponibilidad de canales/API en una instalación existente debe comprobarse por separado de Cloud IRM mantenido.

</details>

---

2. ¿Cuál es la función del tipo `wait` en la política de escalamiento de Grafana OnCall?
   - A) Esperar la recopilación de datos antes de enviar alertas
   - B) Esperar antes de avanzar al siguiente paso de escalamiento
   - C) Esperar la respuesta del usuario y luego resolver automáticamente
   - D) Esperar la agrupación de alertas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Esperar antes de avanzar al siguiente paso de escalamiento**

**Explicación:**
Un paso de espera retrasa el siguiente paso de escalamiento. No reconoce ni resuelve un incidente. El serializador público inspeccionado acepta esperas de entre un minuto y 24 horas, en segundos; el comportamiento real de detención o nueva notificación depende de la cadena y del estado del grupo de alertas.

</details>

---

3. ¿Qué es una "Override" en el horario de guardia de Grafana OnCall?
   - A) Eliminar y volver a crear por completo el horario
   - B) Cambiar temporalmente el respondedor durante un período específico en el horario existente
   - C) Cambiar la zona horaria del horario
   - D) Modificar el ciclo de rotación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cambiar temporalmente el respondedor durante un período específico en el horario existente**

**Explicación:**
Una override cambia la cobertura durante un período definido. En la API inspeccionada es de tipo on_call_shifts, con una zona horaria explícita y la asociación obligatoria con el horario previsto. Verifica los ID de turnos existentes, las prioridades, las brechas y los respondedores finales; no supongas que existe el antiguo endpoint anidado de overrides.

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
Usa webhook_configs con la URL generada para el tipo de integración real, almacenada en un url_file protegido cuando sea conveniente. Define cada receiver al que se haga referencia y usa matchers actuales. La autenticación mediante raw token de la API pública es independiente de una URL de webhook; send_resolved no hace que OnCall actualice la regla de origen.

</details>

---

5. ¿Cuál es el objetivo principal de la agrupación de alertas en Grafana OnCall?
   - A) Ordenar alertas por hora
   - B) Agrupar alertas relacionadas en una sola para reducir la fatiga por alertas
   - C) Clasificar alertas por gravedad
   - D) Eliminar automáticamente alertas duplicadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Agrupar alertas relacionadas en una sola para reducir la fatiga por alertas**

**Explicación:**
La agrupación puede reducir el trabajo duplicado de los respondedores, pero debe utilizar una clave limitada al dominio del incidente. Demasiadas pocas etiquetas combinan incidentes no relacionados; los ID sin límites fragmentan los grupos. La temporización de Alertmanager de origen y las plantillas de agrupación/resolución de OnCall son diferentes, y la entrega no está garantizada exactamente una vez.

</details>

---

6. ¿Qué sucede cuando el indicador `important` es verdadero para `notify_on_call_from_schedule` en la política de escalamiento de Grafana OnCall?
   - A) La alerta se marca como de máxima prioridad
   - B) Se selecciona el conjunto configurado por el usuario de reglas de notificación importantes
   - C) Se omite la cadena de escalamiento y la alerta se envía inmediatamente al supervisor
   - D) La alerta se almacena de forma permanente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se selecciona el conjunto configurado por el usuario de reglas de notificación importantes**

**Explicación:**
Important selecciona el conjunto personal de reglas de notificación importantes del usuario. El orden, las esperas, los canales y la disponibilidad de las reglas configuradas siguen aplicándose. No envía automáticamente a través de todos los canales; las reglas predeterminadas no son exclusivamente de Slack en todos los casos.

</details>

---

7. ¿Cuál es la forma correcta de usar acciones de Slack con una instalación existente de OnCall?
   - A) Suponer que todas las instalaciones admiten /oncall ack
   - B) Tratar los comandos de barra como Bash
   - C) Verificar los comandos, permisos y botones de acción de la aplicación instalada
   - D) Suponer que el reconocimiento resuelve el monitor de origen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Verificar los comandos, permisos y botones de acción de la aplicación instalada**

**Explicación:**
Comprueba el comando raíz/la ayuda reales y los botones de acción autorizados de la aplicación de Slack instalada. El código fuente inspeccionado utiliza un comando raíz configurable y ejemplos con /grafana, no el antiguo catálogo de comandos /oncall que se afirmaba. Acknowledge, Resolve y Silence son acciones diferentes; no se implica la ejecución del despliegue.

</details>

---

8. ¿Cuál es la base adecuada para decidir sobre una nueva herramienta de guardia o una migración?
   - A) Elegir solo según los antiguos recuentos de integraciones
   - B) Suponer que OSS no tiene coste operativo
   - C) Comprobar el mantenimiento, las características requeridas, el coste real y la migración/recuperación
   - D) Instalar OnCall OSS archivado de forma predeterminada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Comprobar el mantenimiento, las características requeridas, el coste real y la migración/recuperación**

**Explicación:**
Utiliza el mantenimiento/ciclo de vida actual, las características requeridas, el coste operativo y los contratos. Los antiguos recuentos fijos de integraciones o precios por usuario son insuficientes. OnCall OSS está archivado; Opsgenie tiene un fin de servicio/soporte anunciado para el 2027-04-05. Revisa un destino mantenido y prueba la migración/recuperación.

</details>

---

9. ¿Qué se debe verificar para la disponibilidad de un Deployment de OnCall existente?
   - A) Tres réplicas de API garantizan la disponibilidad
   - B) Dependencias, estado, entrega y comportamiento ante fallos y recuperación
   - C) Solo el número de clústeres
   - D) Solo una réplica de base de datos de solo lectura

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Dependencias, estado, entrega y comportamiento ante fallos y recuperación**

**Explicación:**
El número de réplicas por sí solo no elimina todos los puntos de fallo. Las instalaciones existentes requieren validación de dependencias, broker/cache/base de datos, programador, claves, TLS, entrega y recuperación. OSS archivado no es una opción predeterminada para producción nueva; en esta revisión no se probó ningún despliegue de HA.

</details>

---

10. ¿Cuál es el objetivo principal de configurar rutas en Grafana OnCall?
    - A) Distribución del tráfico de red
    - B) Aplicar diferentes cadenas de escalamiento según las condiciones de las alertas
    - C) Optimización de consultas de base de datos
    - D) Configuración de la ruta de autenticación de usuarios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplicar diferentes cadenas de escalamiento según las condiciones de las alertas**

**Explicación:**
Las rutas seleccionan el comportamiento de escalamiento/notificación mediante la carga útil real de la integración, el modo de coincidencia, el orden y la alternativa de respaldo. El serializador inspeccionado utiliza slack.channel_id/enabled anidado. Prueba los campos ausentes o en conflicto; la coincidencia arbitraria de expresiones regulares del texto de mensajes no es un contrato universal de proveedor.

</details>

---

## Recursos de aprendizaje adicionales

- [Documentación de Grafana OnCall](https://grafana.com/docs/oncall/latest/)
- [Grafana OnCall en GitHub](https://github.com/grafana-cold-storage/oncall)
- [Helm Chart de Grafana OnCall](https://github.com/grafana-cold-storage/oncall/tree/af0fbd40558c9a63bcf438589894c440fc434a54/helm/oncall)
- [Grafana IRM (Gestión de respuesta a incidentes)](https://grafana.com/products/cloud/irm/)

- [Guía](../../../observability/alerting/03-grafana-oncall.md)
