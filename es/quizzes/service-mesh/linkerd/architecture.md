# Cuestionario de arquitectura de Linkerd

Este cuestionario evalúa tu comprensión de la arquitectura de Linkerd.

## Preguntas del cuestionario

### 1. ¿Cuál NO es un componente central del control plane de Linkerd?

A. Destination Controller
B. Identity Controller
C. Proxy Injector
D. Envoy Proxy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Envoy Proxy**

**Explicación:**
El control plane de Linkerd consta de Destination, Identity y Proxy Injector. Envoy es el proxy de data plane de Istio; Linkerd usa su propio linkerd2-proxy, escrito en Rust.

</details>

### 2. ¿En qué lenguaje de programación está escrito linkerd2-proxy?

A. Go
B. C++
C. Rust
D. Java

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Rust**

**Explicación:**
linkerd2-proxy está escrito en Rust, lo que proporciona seguridad de memoria y alto rendimiento. Usa solo alrededor de 10 MB de memoria y añade menos de 1 ms de latencia p99.

</details>

### 3. ¿Cuál NO es una función principal del Destination Controller?

A. Descubrimiento de Service
B. Emisión de certificados
C. Entrega de información de ServiceProfile
D. Actualizaciones de Endpoint

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Emisión de certificados**

**Explicación:**
La emisión de certificados es la función del Identity Controller. El Destination Controller se encarga del descubrimiento de Service, las actualizaciones de Endpoint y la distribución de políticas de ServiceProfile y TrafficSplit.

</details>

### 4. ¿Qué se encuentra en la parte superior de la jerarquía de certificados de Linkerd?

A. Workload Certificate
B. Identity Issuer
C. Trust Anchor
D. Proxy Certificate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Trust Anchor**

**Explicación:**
La jerarquía de certificados es Trust Anchor (Root CA) → Identity Issuer (Intermediate CA) → Workload Certificate. El Trust Anchor es la raíz de la PKI y la base de confianza para todas las cadenas de certificados.

</details>

### 5. ¿Cuál es el período de validez predeterminado de los certificados de workload?

A. 1 hora
B. 24 horas
C. 7 días
D. 30 días

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. 24 horas**

**Explicación:**
Los certificados de workload de Linkerd tienen un período de validez predeterminado de 24 horas. Los proxies renuevan automáticamente los certificados antes de su vencimiento. Los períodos de validez cortos minimizan el riesgo en caso de que un certificado se vea comprometido.

</details>

### 6. ¿Qué mecanismo de Kubernetes utiliza el Proxy Injector?

A. DaemonSet
B. CronJob
C. Admission Webhook
D. Custom Controller

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Admission Webhook**

**Explicación:**
El Proxy Injector funciona como un Mutating Admission Webhook. Intercepta las solicitudes de creación de Pod e inyecta automáticamente el sidecar linkerd-proxy y el init container linkerd-init.

</details>

### 7. ¿Cuál es la función del contenedor linkerd-init?

A. Descargar la configuración del proxy
B. Configurar reglas de iptables
C. Generar certificados
D. Recopilar métricas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Configurar reglas de iptables**

**Explicación:**
linkerd-init se ejecuta como un Init container para configurar reglas de iptables. Estas reglas redirigen todo el tráfico entrante/saliente a linkerd-proxy.

</details>

### 8. ¿Cuál es el puerto de entrada del proxy de Linkerd?

A. 4140
B. 4143
C. 4191
D. 8080

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. 4143**

**Explicación:**
Puertos del proxy de Linkerd: 4143 (entrante), 4140 (saliente), 4191 (admin/métricas). El puerto de entrada recibe tráfico de otros Services.

</details>

### 9. ¿Cuál es el formato correcto de ID SPIFFE?

A. `spiffe://cluster/namespace/service`
B. `spiffe://trust-domain/ns/namespace/sa/service-account`
C. `https://linkerd.io/identity/namespace/pod`
D. `urn:linkerd:identity:namespace:pod`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `spiffe://trust-domain/ns/namespace/sa/service-account`**

**Explicación:**
El ID SPIFFE de Linkerd sigue el formato `spiffe://<trust-domain>/ns/<namespace>/sa/<service-account>`. Ejemplo: `spiffe://root.linkerd.cluster.local/ns/production/sa/web-server`

</details>

### 10. ¿Cuál NO es una característica de linkerd2-proxy en comparación con Envoy de Istio?

A. Menor uso de memoria
B. Compatibilidad con extensiones Wasm
C. Menor latencia
D. Menor tamaño del binario

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Compatibilidad con extensiones Wasm**

**Explicación:**
linkerd2-proxy no admite extensiones Wasm (extensibilidad limitada). En cambio, es más ligero, con ~10 MB de memoria (Envoy ~50-100 MB), <1 ms de latencia p99 (Envoy 2-5 ms) y un binario de ~10 MB (Envoy ~60 MB).

</details>

### 11. ¿Qué verifica el Identity Controller antes de emitir un certificado?

A. Dirección IP del Pod
B. Token de ServiceAccount
C. Etiquetas de Namespace
D. Configuración de ConfigMap

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Token de ServiceAccount**

**Explicación:**
El Identity Controller verifica el token de ServiceAccount enviado junto con la CSR presentada por el proxy. Esto confirma que la identidad del proxy (ID SPIFFE) coincide con el workload real.

</details>

### 12. ¿Qué NO proporciona el puerto de administración del proxy de Linkerd (4191)?

A. Métricas de Prometheus
B. Endpoints de comprobación de estado
C. Configuración de enrutamiento de tráfico
D. Información sobre la versión del proxy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Configuración de enrutamiento de tráfico**

**Explicación:**
El puerto de administración (4191) proporciona métricas de Prometheus (/metrics), comprobaciones de estado (/ready, /live) e información del proxy. La configuración de enrutamiento de tráfico se entrega a los proxies mediante gRPC desde el Destination Controller.

</details>
