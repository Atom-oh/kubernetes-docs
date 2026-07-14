# Cuestionario sobre el stack de observabilidad

> **Documento relacionado**: [Stack de observabilidad](../../ops/09-observability-stack.md)

## Preguntas de opción múltiple

### 1. ¿Cuáles son los componentes del stack de observabilidad LGTM?

- A) Linux, Git, Terminal, Make
- B) Loki (registros), Grafana (visualización), Tempo (trazas), Mimir/Prometheus (métricas)
- C) Lambda, Gateway, Transit, Monitor
- D) Balanceador de carga, Gateway, TLS, Mesh

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Loki (registros), Grafana (visualización), Tempo (trazas), Mimir/Prometheus (métricas)**

**Explicación:**
LGTM es un stack de observabilidad de Grafana Labs compuesto por Loki para la agregación de registros, Grafana para visualización y dashboards, Tempo para trazado distribuido, y Mimir (o Prometheus) para métricas. Estos componentes se integran sin problemas.

</details>

### 2. ¿Cuál es la diferencia entre los modos de despliegue SimpleScalable y Distributed de Loki?

- A) SimpleScalable es solo para pruebas
- B) SimpleScalable separa las rutas de lectura/escritura; Distributed añade una separación de componentes más granular
- C) Distributed está obsoleto
- D) Son idénticos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) SimpleScalable separa las rutas de lectura/escritura; Distributed añade una separación de componentes más granular**

**Explicación:**
El modo SimpleScalable divide Loki en rutas de lectura y escritura que pueden escalar de forma independiente. El modo Distributed separa aún más los componentes (ingesters, distributors, queriers, etc.) para lograr máxima escalabilidad y flexibilidad operativa a gran escala.

</details>

### 3. ¿Cuál es el propósito del muestreo basado en cola en Tempo?

- A) Muestrear el final de los archivos de registro
- B) Tomar decisiones de muestreo después de ver la traza completa
- C) Reducir la latencia de las consultas
- D) Comprimir datos de trazas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Tomar decisiones de muestreo después de ver la traza completa**

**Explicación:**
El muestreo basado en cola espera hasta que una traza esté completa antes de decidir si almacenarla. Esto permite conservar todas las trazas con errores o trazas lentas mientras se muestrean las trazas normales, algo que el muestreo basado en cabecera no puede hacer porque decide al inicio de la traza.

</details>

### 4. ¿Qué función cumple OTEL Collector en el stack de observabilidad?

- A) Almacenar métricas a largo plazo
- B) Recibir, procesar y exportar datos de telemetría desde aplicaciones
- C) Crear dashboards de Grafana
- D) Gestionar la autenticación de usuarios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Recibir, procesar y exportar datos de telemetría desde aplicaciones**

**Explicación:**
OpenTelemetry Collector actúa como un pipeline de telemetría, recibiendo trazas, métricas y registros de las aplicaciones, procesándolos (agrupación en lotes, filtrado, enriquecimiento) y exportándolos a backends como Tempo, Prometheus y Loki.

</details>

### 5. ¿Cómo se integra Amazon Managed Prometheus (AMP) con Prometheus?

- A) Reemplaza por completo a Prometheus
- B) Prometheus usa remote_write para enviar métricas a AMP para almacenamiento
- C) AMP se ejecuta como un sidecar de Prometheus
- D) AMP solo funciona con CloudWatch

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Prometheus usa remote_write para enviar métricas a AMP para almacenamiento**

**Explicación:**
AMP proporciona un backend de almacenamiento gestionado y escalable para las métricas de Prometheus. Prometheus continúa recopilando métricas y evaluando reglas localmente, pero usa `remote_write` para enviar métricas a AMP. Luego Grafana consulta AMP usando PromQL.

</details>

### 6. ¿Cuál es la estrategia recomendada de diseño de etiquetas en Loki?

- A) Usar tantas etiquetas como sea posible para mayor flexibilidad
- B) Usar etiquetas acotadas y de baja cardinalidad para evitar la explosión del índice
- C) Evitar usar cualquier etiqueta
- D) Usar solo etiquetas de timestamp

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar etiquetas acotadas y de baja cardinalidad para evitar la explosión del índice**

**Explicación:**
Las etiquetas de alta cardinalidad (como IDs de usuario o IDs de solicitud) crean demasiados streams y aumentan excesivamente el índice. Las etiquetas deben ser de baja cardinalidad (namespace, app, environment), mientras que los datos de alta cardinalidad van en el contenido del registro para filtrarlos con LogQL.

</details>

### 7. ¿Cuál es la diferencia entre Promtail y Grafana Alloy para la recolección de registros?

- A) Promtail solo recopila métricas
- B) Alloy es un agente unificado que admite registros, métricas y trazas; Promtail es específico de Loki
- C) Promtail es más nuevo que Alloy
- D) Alloy no admite Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Alloy es un agente unificado que admite registros, métricas y trazas; Promtail es específico de Loki**

**Explicación:**
Promtail está diseñado específicamente para enviar registros a Loki. Grafana Alloy (anteriormente Agent) es un collector unificado que maneja registros, métricas y trazas usando OpenTelemetry y receptores nativos, lo que reduce el número de agentes necesarios.

</details>

### 8. ¿Cómo configuras el enlace de datasources de Grafana entre Loki y Tempo?

- A) Se enlazan automáticamente sin configuración
- B) Configurar campos derivados en la datasource de Loki apuntando a la datasource de Tempo
- C) Instalar un plugin de enlace separado
- D) Exportar datos a una base de datos común

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar campos derivados en la datasource de Loki apuntando a la datasource de Tempo**

**Explicación:**
En la configuración de la datasource Loki de Grafana, configura campos derivados con una expresión regular para extraer trace IDs de los registros y enlazarlos con la datasource Tempo. Esto crea enlaces clicables desde las líneas de registro hacia las trazas asociadas.

</details>

### 9. ¿Cuál es el propósito del componente compactor de Tempo?

- A) Comprimir el tráfico de red
- B) Fusionar bloques de trazas y gestionar la retención
- C) Compilar consultas TraceQL
- D) Reducir el tiempo de carga del dashboard

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Fusionar bloques de trazas y gestionar la retención**

**Explicación:**
El compactor fusiona bloques de trazas más pequeños en bloques más grandes para mejorar la eficiencia de almacenamiento y aplica políticas de retención eliminando datos expirados. Se ejecuta como un proceso separado en modo distributed o dentro del binario monolítico.

</details>

### 10. Al configurar procesadores de OTEL Collector, ¿qué hace el procesador batch?

- A) Asigna IDs de lote a las trazas
- B) Agrupa la telemetría en lotes antes de exportarla para mejorar la eficiencia
- C) Procesa operaciones batch de base de datos
- D) Crea batch jobs en Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Agrupa la telemetría en lotes antes de exportarla para mejorar la eficiencia**

**Explicación:**
El procesador batch acumula datos de telemetría y los envía en lotes según umbrales de tamaño o timeout. Esto reduce el número de solicitudes salientes, mejora la compresión y disminuye la carga en los backends receptores.

</details>
