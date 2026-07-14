# Cuestionario de Datadog

Un cuestionario para evaluar tu comprensión de Datadog.

---

1. ¿Cuál es el modelo de despliegue principal de Datadog?
   - A) Solo autohospedado
   - B) SaaS (Software as a Service)
   - C) Solo on-premises
   - D) Híbrido obligatorio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) SaaS (Software as a Service)**

**Explicación:**
Datadog es una plataforma de observabilidad unificada proporcionada como un modelo SaaS. Los usuarios solo necesitan desplegar el Datadog Agent, mientras que el almacenamiento, el procesamiento y la visualización de datos son gestionados por la infraestructura cloud de Datadog. Esto permite utilizar potentes capacidades de monitorización sin sobrecarga operativa.

</details>

---

2. ¿Cuál es el rol de Datadog Cluster Agent?
   - A) Recopilación de logs de contenedores
   - B) Recopilación de métricas y eventos a nivel de clúster
   - C) Procesamiento de trazas de APM
   - D) Renderizado de dashboards

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Recopilación de métricas y eventos a nivel de clúster**

**Explicación:**
Datadog Cluster Agent recopila métricas y eventos a nivel de clúster de los clústeres de Kubernetes. También proporciona un rol de servidor de métricas personalizado para HPA (Horizontal Pod Autoscaler) y la inyección automática de instrumentación de APM mediante Admission Controller.

</details>

---

3. ¿Cómo se habilita la instrumentación automática de APM en Datadog?
   - A) Se requiere modificar el código de la aplicación
   - B) Usar Admission Controller y labels de Pod
   - C) Desplegar un servidor de APM independiente
   - D) Inyectar bibliotecas manualmente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar Admission Controller y labels de Pod**

**Explicación:**
Cuando Datadog Admission Controller está habilitado, las bibliotecas de instrumentación de APM se inyectan automáticamente en los Pods con el label `admission.datadoghq.com/enabled: "true"`. Admite lenguajes principales, incluidos Java, Python, Node.js, .NET y Ruby, lo que permite comenzar el tracing sin modificaciones de código.

</details>

---

4. ¿Cuál es el rol de DogStatsD?
   - A) Recopilación de logs
   - B) Recopilación de métricas personalizadas (compatible con StatsD)
   - C) Creación de dashboards
   - D) Enrutamiento de alertas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Recopilación de métricas personalizadas (compatible con StatsD)**

**Explicación:**
DogStatsD es un daemon de recopilación de métricas compatible con StatsD incluido en Datadog Agent. Las aplicaciones pueden enviar métricas personalizadas (contadores, gauges, histogramas, distribuciones) mediante UDP. Es compatible con el protocolo StatsD con funcionalidad de tags añadida.

</details>

---

5. ¿Cómo se conectan las trazas y los logs en Datadog?
   - A) Cargar archivos de logs manualmente
   - B) Incluir trace_id y span_id en los logs
   - C) Desplegar un servicio de conexión independiente
   - D) Hacer coincidir las marcas de tiempo de logs y trazas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Incluir trace_id y span_id en los logs**

**Explicación:**
Para conectar trazas y logs en Datadog, los logs deben incluir `dd.trace_id` y `dd.span_id`. Las bibliotecas de Datadog APM pueden inyectar automáticamente esta información mediante MDC (Mapped Diagnostic Context). Esto permite ver los logs relacionados directamente desde APM.

</details>

---

6. ¿Cuál es la unidad de facturación para la monitorización de infraestructura en la estructura de costes de Datadog?
   - A) Número de métricas
   - B) Número de hosts
   - C) Número de llamadas a la API
   - D) Volumen de transferencia de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Número de hosts**

**Explicación:**
La monitorización de infraestructura de Datadog se factura según el número de hosts. Cada nodo, instancia y host de contenedores es un elemento facturable. APM, la gestión de logs y otras funcionalidades tienen estructuras de facturación independientes, y la facturación basada en hosts facilita la previsión de costes.

</details>

---

7. ¿Cuál es la función de Datadog Watchdog?
   - A) Configuración manual de alertas
   - B) Detección automática de anomalías basada en IA
   - C) Búsqueda de logs
   - D) Creación de dashboards

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Detección automática de anomalías basada en IA**

**Explicación:**
Watchdog es la funcionalidad de detección automática de anomalías basada en IA/ML de Datadog. Detecta automáticamente patrones anómalos en datos de infraestructura, APM y logs, y genera alertas. Puedes identificar anomalías sin establecer umbrales manualmente.

</details>

---

8. ¿Cómo se recopilan métricas de Prometheus con Datadog Agent?
   - A) Se requiere un servidor de Prometheus independiente
   - B) Configurar el descubrimiento automático con anotaciones de Pod
   - C) Registrar manualmente cada endpoint
   - D) Reemplazar Prometheus con Datadog

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar el descubrimiento automático con anotaciones de Pod**

**Explicación:**
Datadog Agent utiliza las anotaciones `ad.datadoghq.com/<container>.checks` para descubrir y recopilar automáticamente endpoints de métricas de Prometheus. La configuración es similar a los ajustes de scrape de Prometheus, y las métricas se pueden recopilar sin un servidor de Prometheus independiente.

</details>

---

9. ¿Qué tipos de métricas se pueden utilizar al configurar un SLO (Service Level Objective) en Datadog?
   - A) Solo eventos de logs
   - B) Basadas en métricas, basadas en monitores, basadas en intervalos de tiempo
   - C) Solo trazas de APM
   - D) Solo métricas de infraestructura

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Basadas en métricas, basadas en monitores, basadas en intervalos de tiempo**

**Explicación:**
Datadog SLO admite tres tipos: basado en métricas (recuentos de éxito/error), basado en monitores (estado de monitores existentes) y basado en intervalos de tiempo (estado por intervalo de tiempo). Se pueden utilizar diversas fuentes de datos, incluidas las trazas de APM, las métricas personalizadas y las métricas basadas en logs.

</details>

---

10. ¿Cuál NO es una estrategia válida de optimización de costes de Datadog?
    - A) Ajustar la tasa de muestreo de trazas de APM
    - B) Filtrar logs innecesarios
    - C) Recopilar todas las métricas con la máxima resolución
    - D) Gestionar la cardinalidad de las métricas personalizadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Recopilar todas las métricas con la máxima resolución**

**Explicación:**
Para la optimización de costes de Datadog, son importantes el muestreo de trazas de APM, el filtrado de logs y la gestión de la cardinalidad de las métricas personalizadas. Recopilar todas las métricas con la máxima resolución hace que los costes se disparen. Recopila selectivamente solo las métricas necesarias y aplica el muestreo adecuado.

</details>
