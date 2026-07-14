# Cuestionario de instalación de Linkerd

Este cuestionario evalúa su comprensión de la instalación y configuración de Linkerd.

## Preguntas del cuestionario

### 1. ¿Cuál es el comando correcto para instalar la CLI de Linkerd?

A. `apt-get install linkerd`
B. `curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh`
C. `kubectl install linkerd`
D. `helm install linkerd`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh`**

**Explicación:**
La CLI de Linkerd se instala mediante el script de instalación oficial. Este script detecta el sistema operativo y descarga el binario adecuado. También se puede usar Homebrew (`brew install linkerd`) o Chocolatey (`choco install linkerd2`), pero el script oficial es el método más común.

</details>

### 2. ¿Qué comando verifica los requisitos del clúster antes de la instalación de Linkerd?

A. `linkerd check`
B. `linkerd check --pre`
C. `linkerd verify`
D. `linkerd install --dry-run`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `linkerd check --pre`**

**Explicación:**
El comando `linkerd check --pre` verifica que el clúster cumpla los requisitos antes de la instalación de Linkerd. Valida la accesibilidad de la API de Kubernetes, la compatibilidad de versiones y los permisos necesarios. Después de la instalación, use `linkerd check` para verificar el estado completo.

</details>

### 3. ¿Qué se debe proporcionar al instalar Linkerd con Helm?

A. Imagen de proxy Envoy
B. Certificados de Trust Anchor e Identity Issuer
C. Archivo de configuración de Prometheus
D. Información de la versión de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Certificados de Trust Anchor e Identity Issuer**

**Explicación:**
A diferencia de la instalación mediante CLI, la instalación con Helm no genera certificados automáticamente. Los usuarios deben crear y proporcionar por sí mismos los certificados de Trust Anchor (Root CA) e Identity Issuer (Intermediate CA). Esto permite un mejor control sobre la gestión de certificados en entornos de producción.

</details>

### 4. ¿Cuál es el número recomendado de réplicas de control plane para una instalación HA de Linkerd?

A. 1
B. 2
C. 3
D. 5

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. 3**

**Explicación:**
La configuración HA recomienda 3 réplicas cada una para Destination, Identity y Proxy Injector. Tres réplicas pueden mantener el quórum incluso si una falla y garantizar la disponibilidad durante las actualizaciones continuas.

</details>

### 5. ¿Cuál NO es una característica principal de la extensión Viz?

A. Panel web
B. Recopilación de métricas de Prometheus
C. Despliegue canary automático
D. Tap de tráfico en tiempo real

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Despliegue canary automático**

**Explicación:**
La extensión Viz proporciona un panel web, recopilación de métricas basada en Prometheus, paneles de Grafana y funcionalidad de tap de tráfico en tiempo real. El despliegue canary automático se implementa mediante herramientas independientes como Flagger.

</details>

### 6. ¿Qué tipo de load balancer se recomienda para el gateway Multicluster en EKS?

A. Classic Load Balancer
B. Application Load Balancer (ALB)
C. Network Load Balancer (NLB)
D. Internal Load Balancer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Network Load Balancer (NLB)**

**Explicación:**
NLB está optimizado para tráfico TCP/TLS, lo que lo hace adecuado para el tráfico de gateway mTLS de Linkerd. ALB está optimizado para HTTP/HTTPS y, dado que el gateway de Linkerd funciona en el nivel TCP, se recomienda NLB.

</details>

### 7. ¿Cuál es el orden correcto para la actualización de Linkerd?

A. Data plane → CRD → Control plane
B. CRD → Control plane → Data plane
C. Control plane → CRD → Data plane
D. CRD → Data plane → Control plane

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. CRD → Control plane → Data plane**

**Explicación:**
El orden correcto de actualización es: 1) actualización de la CLI, 2) actualización de CRD, 3) actualización de control plane, 4) actualización de data plane (proxy). Los CRD deben actualizarse primero para usar las nuevas versiones de la API.

</details>

### 8. ¿Cuál es el propósito del comando `linkerd install --crds`?

A. Instalar la CLI de Linkerd
B. Instalar Custom Resource Definitions
C. Generar certificados
D. Inyectar proxies

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Instalar Custom Resource Definitions**

**Explicación:**
`linkerd install --crds` instala únicamente los CRD (Custom Resource Definitions) utilizados por Linkerd. Esto incluye CRD para ServiceProfile, Server, ServerAuthorization, etc. El control plane se instala por separado con `linkerd install`.

</details>

### 9. ¿Cuál es el comando para instalar la extensión Jaeger?

A. `linkerd install jaeger`
B. `linkerd jaeger install | kubectl apply -f -`
C. `kubectl apply -f jaeger.yaml`
D. `helm install jaeger linkerd/jaeger`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `linkerd jaeger install | kubectl apply -f -`**

**Explicación:**
Las extensiones de Linkerd generan manifiestos en el formato `linkerd <extension> install` y los aplican con kubectl. La extensión Jaeger proporciona funcionalidad de tracing distribuido.

</details>

### 10. ¿Cuál es el orden correcto para eliminar completamente Linkerd?

A. Control plane → Extensions → CRD
B. Extensions → Control plane → CRD
C. CRD → Control plane → Extensions
D. Todos se pueden eliminar simultáneamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Extensions → Control plane → CRD**

**Explicación:**
El orden de eliminación es el inverso de la instalación: 1) eliminar extensiones como Viz, Jaeger y Multicluster, 2) eliminar control plane, 3) eliminar CRD. Esto se debe a que las extensiones dependen del control plane y el control plane depende de los CRD.

</details>

### 11. ¿Qué NO verifica el comando `linkerd check`?

A. Conexión con la API de Kubernetes
B. Validez de certificados
C. Lógica de negocio de la aplicación
D. Estado de los Pods de control plane

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Lógica de negocio de la aplicación**

**Explicación:**
`linkerd check` solo verifica el estado de la infraestructura de Linkerd: conexión con la API de Kubernetes, validez de certificados, estado de los Pods de control plane, estado de los proxies, etc. No verifica la lógica de negocio ni la funcionalidad de la aplicación.

</details>

### 12. ¿Qué annotation se debe agregar a un namespace para la inyección automática de proxy?

A. `linkerd.io/inject: enabled`
B. `linkerd.io/proxy: true`
C. `sidecar.linkerd.io/inject: true`
D. `linkerd/auto-inject: yes`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. `linkerd.io/inject: enabled`**

**Explicación:**
Agregar la annotation `linkerd.io/inject: enabled` a un namespace inyecta automáticamente linkerd-proxy en todos los Pods nuevos de ese namespace. La misma annotation se puede usar en Pods individuales.

</details>
