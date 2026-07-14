# Cuestionario de Dynatrace

Pon a prueba tus conocimientos sobre Dynatrace.

---

1. ¿Cuál NO es una característica de la tecnología principal de Dynatrace, OneAgent?
   - A) Monitorización full-stack con un único agente
   - B) Instrumentación automática de código
   - C) Configuración manual obligatoria
   - D) Detección automática de procesos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Configuración manual obligatoria**

**Explicación:**
Las características principales de OneAgent son la detección automática y la instrumentación automática. Tras la instalación, detecta y monitoriza automáticamente los procesos, Services y aplicaciones del host sin configuración manual adicional. Esto refleja la filosofía de «Zero-configuration» de Dynatrace.

</details>

---

2. ¿Cuál es la forma recomendada de desplegar Dynatrace en EKS?
   - A) Desplegar directamente con kubectl apply
   - B) Usar Dynatrace Operator
   - C) Desplegar solo OneAgent con Helm
   - D) Desplegar con una función Lambda

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar Dynatrace Operator**

**Explicación:**
Dynatrace Operator gestiona automáticamente el ciclo de vida de los componentes de Dynatrace (OneAgent, ActiveGate, etc.) en entornos Kubernetes. Configura de forma declarativa mediante el DynaKube CR, proporcionando actualizaciones automáticas, despliegues graduales y monitorización de estado.

</details>

---

3. ¿Cuál NO es una característica principal del motor Davis AI?
   - A) Aprendizaje automático de líneas de base
   - B) Detección de anomalías
   - C) Corrección automática de código
   - D) Análisis de la causa raíz

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Corrección automática de código**

**Explicación:**
Davis AI aprende automáticamente las líneas de base, detecta anomalías y analiza las causas raíz de los problemas. Sin embargo, no corrige código automáticamente. Davis diagnostica problemas y sugiere vías de resolución, pero los desarrolladores deben realizar las correcciones de código reales.

</details>

---

4. ¿Cuál es la diferencia entre los modos de despliegue Cloud Native Full Stack y Classic Full Stack en Dynatrace?
   - A) Cloud Native solo es compatible con Windows
   - B) Cloud Native utiliza inyección de módulos de código
   - C) Classic no se puede utilizar en entornos cloud
   - D) Ambos modos ofrecen funcionalidad idéntica

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cloud Native utiliza inyección de módulos de código**

**Explicación:**
Cloud Native Full Stack es un enfoque ligero que inyecta módulos de código en Pods mediante CSI Driver. Classic Full Stack despliega el OneAgent completo en cada nodo como un DaemonSet. Cloud Native tiene un menor uso de recursos y permite un control detallado a nivel de Pod, pero presenta limitaciones para la monitorización a nivel de host.

</details>

---

5. ¿Qué funcionalidad proporciona la tecnología PurePath de Dynatrace?
   - A) Compresión de logs
   - B) Trazado distribuido a nivel de código
   - C) Captura de paquetes de red
   - D) Copia de seguridad de base de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Trazado distribuido a nivel de código**

**Explicación:**
PurePath es la tecnología propietaria de trazado distribuido de Dynatrace que rastrea la ruta completa de las solicitudes a través del sistema hasta el nivel de código. Registra detalladamente no solo las llamadas de Service a Service, sino también las llamadas a métodos dentro de cada Service, las consultas de base de datos y las llamadas a API externas.

</details>

---

6. ¿Cuál es la fórmula correcta para calcular Dynatrace Host Units?
   - A) vCPU + Memory(GB)
   - B) max(Memory(GB) / 16, vCPU / 1.5)
   - C) vCPU * Memory(GB) / 100
   - D) (vCPU + Memory(GB)) / 2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) max(Memory(GB) / 16, vCPU / 1.5)**

**Explicación:**
Las Dynatrace Host Units se calculan según el valor mayor entre la memoria y la CPU. 16GB de memoria o 1.5 vCPU equivalen a 1 Host Unit. Por ejemplo, un host con 8 vCPU y 32GB de RAM es max(2, 5.33) = 5.33 Host Units.

</details>

---

7. ¿Cuál NO es una función de Dynatrace ActiveGate?
   - A) Enrutamiento de datos
   - B) Monitorización de la API de Kubernetes
   - C) Almacenamiento de datos a largo plazo
   - D) Separación de zonas de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Almacenamiento de datos a largo plazo**

**Explicación:**
ActiveGate gestiona el enrutamiento de datos entre OneAgent y Dynatrace SaaS, la monitorización de la API de Kubernetes y las funciones de proxy en entornos aislados de la red. El almacenamiento de datos a largo plazo se gestiona mediante el lakehouse de datos Grail de Dynatrace; ActiveGate no almacena datos, solo los reenvía.

</details>

---

8. ¿Cuál es el propósito de usar namespaceSelector en Dynatrace?
   - A) Crear namespaces
   - B) Monitorizar solo namespaces específicos
   - C) Bloquear la comunicación entre namespaces
   - D) Establecer cuotas de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Monitorizar solo namespaces específicos**

**Explicación:**
El uso de namespaceSelector en el DynaKube CR permite especificar como objetivos de monitorización únicamente los namespaces con etiquetas específicas. Esto permite monitorizar solo entornos de producción o monitorizar selectivamente namespaces de equipos específicos para optimizar los costes.

</details>

---

9. ¿Qué protocolo se utiliza al integrar Dynatrace con OpenTelemetry?
   - A) Solo se admite gRPC
   - B) Solo se admite HTTP
   - C) OTLP (gRPC and HTTP)
   - D) Solo se admite protocolo propietario

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) OTLP (gRPC and HTTP)**

**Explicación:**
Dynatrace admite de forma nativa OpenTelemetry Protocol (OTLP). Con el exportador otlphttp de OTEL Collector, puedes enviar trazas, métricas y logs al endpoint de la API de Dynatrace. Se admiten tanto gRPC como HTTP.

</details>

---

10. ¿Qué funcionalidad proporciona Smartscape de Dynatrace?
    - A) Filtrado inteligente de alertas
    - B) Mapeo de topología en tiempo real
    - C) Autoescalado
    - D) Revisión de código

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mapeo de topología en tiempo real**

**Explicación:**
Smartscape es la tecnología de mapeo de topología en tiempo real de Dynatrace. Detecta y visualiza automáticamente las relaciones entre la infraestructura (hosts, contenedores), los procesos, los Services y las aplicaciones. Esto ayuda a comprender las dependencias del sistema e identificar el alcance del impacto de los problemas.

</details>

---
