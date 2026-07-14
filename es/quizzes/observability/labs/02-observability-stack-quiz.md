# Laboratorio de Observability, parte 2: cuestionario sobre el stack de observability

> **Última actualización**: February 22, 2026

Pon a prueba tu comprensión de los conceptos del stack de observability tratados en el Laboratorio integral de Observability, parte 2.

---

1. ¿Cuál es la diferencia clave entre los patrones de despliegue DaemonSet y Gateway para OpenTelemetry Collector?
   - A) El patrón DaemonSet está obsoleto y Gateway es el único enfoque recomendado
   - B) DaemonSet ejecuta un collector en cada node para la recopilación local, mientras que Gateway centraliza la recopilación para el procesamiento entre nodes
   - C) El patrón Gateway no puede manejar metrics, solo traces
   - D) El patrón DaemonSet requiere más ancho de banda de red entre clusters

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) DaemonSet ejecuta un collector en cada node para la recopilación local, mientras que Gateway centraliza la recopilación para el procesamiento entre nodes**

**Explicación:**
El patrón DaemonSet despliega un Pod de OTel Collector en cada node, recopilando telemetría localmente con baja latencia y reduciendo los saltos de red. El patrón Gateway utiliza un despliegue centralizado (Deployment o StatefulSet) que recibe telemetría de todas las fuentes, lo que permite el procesamiento entre nodes, como el sampling basado en tail. A menudo se combinan ambos patrones: los collectors DaemonSet recopilan datos locales y los reenvían a un Gateway para su agregación y exportación a backends.

</details>

---

2. ¿Cómo organiza el flujo de datos la arquitectura de pipeline de OpenTelemetry Collector?
   - A) Exporter → Processor → Receiver
   - B) Receiver → Processor → Exporter
   - C) Processor → Receiver → Exporter
   - D) Todos los componentes se ejecutan en paralelo sin orden

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Receiver → Processor → Exporter**

**Explicación:**
El pipeline de OTel Collector sigue un flujo de datos claro: los Receivers ingieren datos de telemetría de varias fuentes (OTLP, Prometheus, Jaeger, etc.), los Processors transforman, filtran o enriquecen los datos (batching, manipulación de atributos, sampling) y los Exporters envían los datos procesados a backends (Prometheus, Jaeger, servicios cloud). Se pueden definir varios pipelines para diferentes tipos de señales (metrics, traces, logs), y pueden compartir componentes.

</details>

---

3. ¿Cómo funciona la autenticación al configurar Prometheus remote write para Amazon Managed Prometheus (AMP)?
   - A) Nombre de usuario y contraseña almacenados en Kubernetes secrets
   - B) IRSA proporciona credenciales IAM y la extensión SigV4 firma las solicitudes con AWS Signature Version 4
   - C) API keys generadas en la consola de AMP
   - D) Certificados mTLS emitidos por AWS Certificate Manager

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) IRSA proporciona credenciales IAM y la extensión SigV4 firma las solicitudes con AWS Signature Version 4**

**Explicación:**
AMP utiliza AWS IAM para la autenticación. El componente remote write (Prometheus, OTel Collector o Grafana Agent) usa IRSA para obtener credenciales IAM temporales. La extensión o proxy SigV4 (AWS Signature Version 4) firma cada solicitud con estas credenciales. Este enfoque aprovecha la infraestructura de identidad de AWS, elimina la necesidad de gestionar credenciales de larga duración y proporciona registros de auditoría mediante CloudTrail.

</details>

---

4. ¿Cómo es VictoriaMetrics compatible con Prometheus?
   - A) Requiere herramientas de migración de datos para importar datos de Prometheus
   - B) Implementa la API de Prometheus remote write/read y admite PromQL para las consultas
   - C) Solo funciona como un sidecar de Prometheus
   - D) La compatibilidad requiere una licencia enterprise de pago

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Implementa la API de Prometheus remote write/read y admite PromQL para las consultas**

**Explicación:**
VictoriaMetrics está diseñado como un reemplazo directo para el almacenamiento de Prometheus. Implementa las API de Prometheus remote write y remote read, lo que permite que cualquier cliente compatible con Prometheus envíe metrics y que cualquier herramienta compatible con PromQL las consulte. Amplía PromQL con MetricsQL para ofrecer funciones adicionales. Esta compatibilidad significa que los dashboards existentes de Grafana, las reglas de alerting y las reglas de recording funcionan sin modificaciones.

</details>

---

5. ¿Qué caracteriza el modo single binary de Grafana Mimir?
   - A) Solo admite despliegues single-tenant
   - B) Todos los componentes de Mimir (ingester, querier, compactor, etc.) se ejecutan en un único proceso para simplificar el despliegue
   - C) No puede escalar horizontalmente
   - D) El modo single binary deshabilita el almacenamiento a largo plazo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Todos los componentes de Mimir (ingester, querier, compactor, etc.) se ejecutan en un único proceso para simplificar el despliegue**

**Explicación:**
El modo single binary de Mimir (modo monolítico) ejecuta todos los componentes—distributor, ingester, querier, query-frontend, compactor, store-gateway y ruler—en un único proceso. Esto simplifica el despliegue y las operaciones en entornos más pequeños. A pesar de ejecutarse en un proceso, aún puede escalar horizontalmente ejecutando varias réplicas. Para despliegues más grandes, los componentes pueden separarse en modo microservices para un escalado independiente.

</details>

---

6. ¿Cuáles son los componentes del modo de despliegue SimpleScalable de Grafana Loki?
   - A) Solo un único Pod de lectura y escritura
   - B) Componentes independientes de lectura, escritura y backend que pueden escalar de forma independiente
   - C) Solo ingester y querier, con un compactor externo
   - D) Modo monolítico con sharding automático

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Componentes independientes de lectura, escritura y backend que pueden escalar de forma independiente**

**Explicación:**
El modo SimpleScalable de Loki (también llamado Simple Scalable Deployment o SSD) divide los componentes en tres targets: Write (distributor, ingester), Read (query-frontend, querier) y Backend (compactor, index-gateway, ruler). Esto permite el escalado independiente: la ruta de escritura escala con el volumen de ingesta y la ruta de lectura escala con la carga de consultas. Es un punto intermedio entre los modos monolítico (single binary) y microservices (totalmente distribuido), equilibrando la simplicidad operativa con la escalabilidad.

</details>

---

7. ¿Cuáles son las ventajas de usar ClickHouse como almacén de logs en comparación con las soluciones tradicionales?
   - A) ClickHouse solo admite logs JSON estructurados
   - B) Almacenamiento orientado a columnas, alta compresión y consultas analíticas rápidas sobre grandes volúmenes de logs
   - C) Requiere menos almacenamiento, pero tiene un rendimiento de consultas más lento
   - D) ClickHouse está diseñado principalmente para metrics, no para logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Almacenamiento orientado a columnas, alta compresión y consultas analíticas rápidas sobre grandes volúmenes de logs**

**Explicación:**
ClickHouse es una base de datos OLAP orientada a columnas optimizada para consultas analíticas. Para el almacenamiento de logs, esto significa: excelentes ratios de compresión (a menudo 10 veces mejores que los almacenes basados en filas) porque los datos similares en columnas se comprimen bien, consultas de agregación extremadamente rápidas sobre miles de millones de entradas de logs y filtrado eficiente en columnas específicas sin leer filas completas. Estas características lo hacen rentable para el almacenamiento de logs de gran volumen con un rendimiento de consultas interactivo.

</details>

---

8. ¿Cuáles son las diferencias clave entre FluentBit y Grafana Alloy para la recopilación de logs?
   - A) FluentBit está escrito en Go, mientras que Alloy está escrito en C
   - B) FluentBit es ligero y se centra en el reenvío de logs, mientras que Alloy es un collector de telemetría unificado que admite metrics, logs, traces y profiles
   - C) Alloy solo admite backends de Grafana, mientras que FluentBit es independiente del proveedor
   - D) FluentBit requiere más memoria que Alloy para cargas de trabajo equivalentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) FluentBit es ligero y se centra en el reenvío de logs, mientras que Alloy es un collector de telemetría unificado que admite metrics, logs, traces y profiles**

**Explicación:**
FluentBit es un procesador y reenviador de logs ligero y de alto rendimiento escrito en C, diseñado para entornos con recursos limitados. Grafana Alloy (evolución de Grafana Agent) es un collector de observability unificado que maneja todas las señales de telemetría—metrics, logs, traces y profiles. Alloy utiliza un modelo de configuración basado en componentes y se integra estrechamente con el ecosistema de Grafana. Elige FluentBit para el reenvío de logs con una huella mínima; elige Alloy para la recopilación unificada en todos los tipos de señales.

</details>

---

9. ¿Cómo se configura la correlación de campos derivados TraceID de Tempo-Loki?
   - A) La correlación es automática y no requiere configuración
   - B) Configura un campo derivado en la data source de Loki que extraiga TraceID de los logs y enlace con Tempo mediante el trace ID
   - C) Instala un servicio de correlación independiente entre Tempo y Loki
   - D) La correlación TraceID solo funciona con Jaeger, no con Tempo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configura un campo derivado en la data source de Loki que extraiga TraceID de los logs y enlace con Tempo mediante el trace ID**

**Explicación:**
En la configuración de la data source de Loki de Grafana, configuras campos derivados que utilizan regex para extraer trace IDs de las líneas de logs. El campo derivado especifica un enlace interno a la data source de Tempo, utilizando el trace ID extraído como variable. Al visualizar logs, aparecen enlaces en los que se puede hacer clic junto a las líneas de logs que contienen trace IDs, lo que permite la navegación directa desde una entrada de log a su trace distribuido correspondiente en Tempo.

</details>

---

10. ¿Cómo se configura Alertmanager para enviar notificaciones a AWS SNS?
    - A) Alertmanager tiene soporte nativo para SNS y solo requiere el ARN del topic
    - B) Configura un receiver de SNS con el ARN del topic, la región y autenticación IAM mediante IRSA o access keys
    - C) La integración con SNS requiere un servicio proxy de webhook
    - D) Alertmanager no puede enviar a SNS; utiliza CloudWatch Alarms en su lugar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configura un receiver de SNS con el ARN del topic, la región y autenticación IAM mediante IRSA o access keys**

**Explicación:**
Alertmanager admite SNS como un tipo de receiver nativo. La configuración requiere el ARN del topic de SNS, la región de AWS y las credenciales de autenticación. Para despliegues de EKS, utiliza IRSA configurando la service account con un rol IAM que tenga el permiso `sns:Publish`. La configuración del receiver incluye ajustes `sigv4` para la autenticación de AWS. Esto permite la entrega directa de alertas a SNS, que luego puede distribuirlas a suscriptores de correo electrónico, SMS, Lambda, SQS u otros suscriptores de SNS.

</details>
