# Cuestionario básico

> **Versión compatible**: Istio 1.28.0 **Versión de EKS**: 1.34 (Kubernetes 1.28+) **Última actualización**: February 23, 2026

Este cuestionario evalúa tu comprensión de los conceptos básicos y la arquitectura de Istio.

## Preguntas de opción múltiple (1-5)

### Pregunta 1: Definición de Service Mesh

¿Cuál afirmación sobre Service Mesh **NO es correcta**?

A. Es una capa de infraestructura que gestiona la comunicación entre microservicios B. Solo puede utilizarse modificando el código de la aplicación C. Proporciona control de tráfico y observabilidad entre servicios D. Aplica seguridad y políticas a nivel de red

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B**

Una de las ventajas principales de Service Mesh es que puede controlar y observar la comunicación entre servicios **sin cambiar el código de la aplicación**.

**Explicación:**

* A (O): Service Mesh es una capa de infraestructura dedicada responsable de la comunicación entre servicios en una arquitectura de microservicios
* B (X): Se aplica de forma transparente mediante proxies Sidecar o Ambient Mode sin cambiar el código de la aplicación
* C (O): Controla el tráfico con VirtualService, DestinationRule, etc., y recopila automáticamente métricas/registros/trazas
* D (O): Aplica políticas de seguridad a nivel de red con mTLS, Authorization Policy, etc.

**Referencia:**

* [Conceptos básicos de Istio](../../../service-mesh/istio/02-basic-concepts.md)
* [¿Qué es Service Mesh?](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/02-istio.md#introduction)

</details>

***

### Pregunta 2: Componentes de la arquitectura de Istio

En el Control Plane de Istio, ¿cuál es el componente **centralizado** responsable del descubrimiento de servicios, la gestión de configuración y la gestión de certificados?

A. Envoy B. Istiod C. Pilot D. Citadel

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Istiod** es un único binario introducido en Istio 1.5 que integra los componentes anteriores Pilot, Citadel y Galley.

**Explicación:**

* A (X): Envoy es un proxy de Data Plane que se ejecuta como Sidecar en cada Pod
* B (O): Istiod es el núcleo del Control Plane y gestiona:
  * Descubrimiento de servicios
  * Gestión de configuración
  * Gestión de certificados
* C (X): Pilot era un componente de las versiones de Istio anteriores a 1.5; ahora está integrado en Istiod
* D (X): Citadel también era un componente de las versiones de Istio anteriores a 1.5; ahora está integrado en Istiod

**Funciones clave de Istiod:**

```yaml
# Configurations managed by Istiod
1. Service Discovery: Kubernetes Service -> Envoy Cluster
2. Config Distribution: VirtualService, DestinationRule -> Envoy Config
3. Certificate Issuance: Service Account -> mTLS Certificate
```

**Referencia:**

* [Componentes de Istio](../../../service-mesh/istio/03-architecture.md)
* [Descripción general de la arquitectura](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/02-istio.md#architecture-overview)

</details>

***

### Pregunta 3: Función del proxy Envoy

¿Cuál **NO** es una tarea realizada por el proxy Envoy del Data Plane?

A. Enrutamiento de tráfico y balanceo de carga B. Cifrado y autenticación mTLS C. Validación y almacenamiento de Kubernetes CRD D. Recopilación de métricas, registros y trazas

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

La validación y el almacenamiento de Kubernetes CRD son funciones del Control Plane (Istiod).

**Explicación:**

* A (O): Envoy enruta el tráfico y realiza balanceo de carga según las reglas de VirtualService
* B (O): Envoy cifra automáticamente la comunicación entre servicios con mTLS y valida certificados
* C (X): La validación y el almacenamiento de CRD son funciones de Kubernetes API Server e Istiod
* D (O): Envoy recopila métricas (Prometheus), registros (Access Log) y trazas (Jaeger) para todas las solicitudes

**Referencia:**

* [Estructura del Data Plane](../../../service-mesh/istio/03-architecture.md#data-plane-envoy-proxy)

</details>

***

### Pregunta 4: Perfiles de instalación de Istio

¿Qué perfil se **recomienda** al instalar Istio en un entorno de producción de Amazon EKS?

A. default B. demo C. minimal D. production

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D**

Para entornos de producción, se debe utilizar el perfil **production**.

**Explicación:**

**Comparación de perfiles de instalación de Istio:**

| Perfil        | Propósito             | Características                           |
| -------------- | ------------------- | ----------------------------------------- |
| **default**    | Desarrollo/pruebas | Configuración predeterminada, recursos medios   |
| **demo**       | Demostración/aprendizaje       | Todas las funciones habilitadas, alto uso de recursos |
| **minimal**    | Configuración mínima       | Solo Control Plane                        |
| **production** | Producción          | Configuración HA, alta disponibilidad       |

**Características del perfil de producción:**

```bash
# Production profile installation
istioctl install --set profile=production -y

# Key characteristics:
# - Istiod replica: 3 (HA)
# - PodDisruptionBudget configured
# - Resource limits properly set
# - Ingress/Egress Gateway included
```

**Lista de verificación de producción:**

* ✅ Control Plane HA (réplica ≥ 3)
* ✅ Modo mTLS STRICT
* ✅ PodDisruptionBudget configurado
* ✅ Límites de recursos y HPA configurados
* ✅ Stack de monitoreo listo

**Referencia:**

* [Guía de instalación](../../../service-mesh/istio/01-installation.md)
* [Prácticas recomendadas](../../../service-mesh/istio/best-practices.md#production-checklist)

</details>

***

### Pregunta 5: Istio CRD (Custom Resource Definition)

¿Cuál de los siguientes **NO** es un CRD para la **gestión de tráfico** de Istio?

A. VirtualService B. DestinationRule C. PeerAuthentication D. Gateway

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

**PeerAuthentication** es un CRD relacionado con la seguridad.

**Explicación:**

**Clasificación de CRD de Istio:**

**1. Gestión de tráfico:**

* VirtualService: Define reglas de enrutamiento
* DestinationRule: Balanceo de carga, definición de subconjuntos
* Gateway: Punto de entrada de tráfico externo
* ServiceEntry: Definición de servicio externo
* Sidecar: Limita el alcance de configuración de Envoy

**2. Seguridad:**

* PeerAuthentication: Autenticación entre servicios (mTLS)
* RequestAuthentication: Autenticación de usuario final (JWT)
* AuthorizationPolicy: Control de acceso

**3. Observabilidad:**

* Telemetry: Configuración de métricas, registros y trazas

**Ejemplo:**

```yaml
# Traffic Management
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1

---
# Security
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**Referencia:**

* [Gestión de tráfico](../../../service-mesh/istio/traffic-management/)
* [Seguridad](../../../service-mesh/istio/security/)

</details>

***

## Preguntas de respuesta corta (6-10)

### Pregunta 6: Mecanismo de inyección de Sidecar

Explica dos métodos para inyectar automáticamente Envoy Sidecar en Pods en Istio y compara las ventajas y desventajas de cada uno.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

Istio inyecta automáticamente Sidecars mediante dos métodos:

**1. Inyección automática a nivel de Namespace:**

```bash
# Add label to Namespace
kubectl label namespace default istio-injection=enabled

# All Pods deployed afterward will have automatic injection
kubectl apply -f deployment.yaml
```

**Ventajas:**

* Puede aplicarse a todo el Namespace de una vez
* Gestión sencilla
* Baja probabilidad de omisión accidental

**Desventajas:**

* Se aplica a todos los Pods del Namespace (se requiere exclusión selectiva)
* Los Pods existentes deben reiniciarse

**2. Inyección selectiva a nivel de Pod:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    metadata:
      labels:
        sidecar.istio.io/inject: "true"  # or "false"
    spec:
      containers:
      - name: myapp
        image: myapp:latest
```

**Ventajas:**

* Permite inyectar selectivamente solo Pods específicos
* Es posible un control granular
* No se requiere etiqueta de Namespace

**Desventajas:**

* Se necesita configuración para cada Deployment
* Aumentan los puntos de gestión
* Posibilidad de omisión accidental

**Tabla comparativa:**

| Elemento                  | Nivel de Namespace         | Nivel de Pod          |
| --------------------- | ----------------------- | ------------------ |
| Alcance                 | Todo el Namespace        | Pod individual     |
| Complejidad de gestión | Baja                     | Alta               |
| Selectividad           | Baja (se necesita exclusión)  | Alta               |
| Uso recomendado       | Entornos de producción | Entornos mixtos |

**Recomendación para producción:**

* Utiliza el nivel de Namespace de forma predeterminada
* Solo establece `sidecar.istio.io/inject: "false"` para Pods que requieran exclusión

**Referencia:**

* [Inyección de Sidecar](../../../service-mesh/istio/advanced/07-sidecar-injection.md)

</details>

***

### Pregunta 7: Optimización del uso de recursos de Istio

Calcula y compara el **uso de recursos esperado** al utilizar Istio en un clúster de Kubernetes a gran escala con 1000 Pods entre Sidecar Mode y Ambient Mode. (Supón que ztunnel se implementa en 10 nodos y hay 1 waypoint)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Suposiciones:**

* Número de Pods: 1000
* Número de Nodes: 10
* Memoria de Sidecar: 50MB/Pod
* Memoria de ztunnel: 50MB/Node
* Memoria de waypoint: 200MB

**1. Uso de recursos de Sidecar Mode:**

```
Memory Usage = Number of Pods × Sidecar Memory
             = 1000 × 50MB
             = 50,000MB
             = 50GB

CPU Usage = Number of Pods × Sidecar CPU
          = 1000 × 0.1 vCPU
          = 100 vCPU
```

**2. Uso de recursos de Ambient Mode:**

```
Memory Usage = (Number of Nodes × ztunnel Memory) + waypoint Memory
             = (10 × 50MB) + 200MB
             = 500MB + 200MB
             = 700MB

CPU Usage = (Number of Nodes × ztunnel CPU) + waypoint CPU
          = (10 × 0.1 vCPU) + 0.5 vCPU
          = 1.5 vCPU
```

**3. Comparación y ahorro:**

| Elemento       | Sidecar Mode | Ambient Mode | Ahorro   | Porcentaje de ahorro |
| ---------- | ------------ | ------------ | --------- | ------------ |
| **Memoria** | 50GB         | 0.7GB        | 49.3GB    | **98.6%**    |
| **CPU**    | 100 vCPU     | 1.5 vCPU     | 98.5 vCPU | **98.5%**    |

**Cálculo de costos (base de AWS EKS):**

```
# r5.xlarge: 4 vCPU, 32GB RAM, $0.252/hour

Sidecar Mode:
- CPU: 100 vCPU → 25 instances needed
- Memory: 50GB → 2 instances needed
- Required instances: max(25, 2) = 25
- Monthly cost: 25 × $0.252 × 24 × 30 = $4,536

Ambient Mode:
- CPU: 1.5 vCPU → 1 instance sufficient
- Memory: 0.7GB → 1 instance sufficient
- Required instances: 1
- Monthly cost: 1 × $0.252 × 24 × 30 = $181

Monthly cost savings: $4,536 - $181 = $4,355 (96%)
```

**Conclusión:**

* Ambient Mode proporciona un **ahorro de costos del 96% o más** en clústeres a gran escala
* A una escala de 1000 Pods, aproximadamente **$4,300 de ahorro mensual**
* El uso de recursos se reduce en **más del 98%**

**Notas:**

* Se necesitan waypoints adicionales cuando se requieren funciones L7
* Ambient Mode es una función beta en Istio 1.28+

**Referencia:**

* [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md#resource-usage-comparison)
* [Optimización de costos](../../../service-mesh/istio/best-practices.md#cost-optimization)

</details>

***

### Pregunta 8: Mecanismo de operación de mTLS

Explica paso a paso cómo funciona mTLS cuando dos servicios (service-a y service-b) se comunican en Istio. Incluye los roles de Istiod, Envoy y Certificate.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Proceso de operación de mTLS (Mutual TLS):**

**Paso 1: Emisión de Certificate (Bootstrap)**

* Cuando un Pod se inicia, Envoy solicita un certificado (CSR) a Istiod mediante su Service Account
* Istiod valida la Service Account y emite un certificado X.509
* El certificado contiene el ID de la Service Account (por ejemplo, `cluster.local/ns/default/sa/service-a`)
* Validez del certificado: 24 horas de forma predeterminada (renovación automática)

**Paso 2: Comunicación entre servicios (handshake mTLS)**

```
Service A → Envoy A → [mTLS] → Envoy B → Service B
```

**Proceso detallado:**

```yaml
# Service A calls Service B
1. Service A → Envoy A (localhost:outbound)
   - Application sends plaintext HTTP request

2. Envoy A: Outbound Processing
   - Check configuration received from Istiod
   - Check PeerAuthentication policy (STRICT mTLS)
   - Start connection to Service B's Envoy B

3. TLS Handshake (Envoy A ↔ Envoy B)
   a. Envoy A → Envoy B: ClientHello
      - Present own certificate
      - Present supported encryption algorithms

   b. Envoy B → Envoy A: ServerHello
      - Present own certificate
      - Selected encryption algorithm

   c. Mutual Certificate Validation
      - Envoy A: Validate Service B's certificate
      - Envoy B: Validate Service A's certificate
      - Verify signature with Istiod's Root CA

   d. Generate Encrypted Session Key
      - Create TLS 1.3 encrypted channel

4. Envoy B → Service B (localhost:inbound)
   - Deliver decrypted plaintext HTTP request

5. Service B → Envoy B → [mTLS] → Envoy A → Service A
   - Response uses same encrypted channel
```

**Roles de cada componente:**

**Istiod:**

* Actúa como Root CA (firma de certificados)
* Emite certificados basados en Service Account
* Renueva automáticamente certificados (cada 24 horas)
* Distribuye políticas de PeerAuthentication

**Envoy Sidecar:**

* Solicita y renueva certificados
* Realiza el handshake TLS
* Cifra/descifra el tráfico
* Valida certificados

**Certificate:**

* Formato de certificado X.509
* Subject Alternative Name (SAN): URI de Service Account
* Validez: 24 horas (predeterminado)
* Renovación automática

**Ejemplo de configuración:**

```yaml
# PeerAuthentication - STRICT mTLS
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Force all communication to mTLS
```

**Verificación de Certificate:**

```bash
# Check Pod's certificate
istioctl proxy-config secret <pod-name> -o json

# Example output:
{
  "name": "default",
  "tlsCertificate": {
    "certificateChain": "...",
    "privateKey": "...",
    "subjectAltNames": [
      "spiffe://cluster.local/ns/default/sa/service-a"
    ]
  }
}
```

**Beneficios de seguridad:**

1. **Confidencialidad**: Toda la comunicación cifrada
2. **Integridad**: Prevención de manipulación de datos
3. **Autenticación**: Verificación de identidad bidireccional
4. **Automatización**: Aplicada sin cambios de código

**Referencia:**

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [Gestión de certificados](../../../service-mesh/istio/03-architecture.md#certificate-management)

</details>

***

### Pregunta 9: Depuración de Istio

Escribe un método de depuración paso a paso para diagnosticar problemas cuando un servicio recién implementado no puede comunicarse en el mesh de Istio. (Al menos 5 pasos)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Lista de verificación para depurar la comunicación de servicios de Istio:**

**Paso 1: Comprobar el estado de Pod y Sidecar**

```bash
# Check if Pod is running normally
kubectl get pods -n <namespace>

# Check if Sidecar is injected (should have 2 containers)
kubectl get pods <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].name}'
# Expected output: myapp istio-proxy

# Detailed Sidecar injection check
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Containers:"

# Check Pod logs
kubectl logs <pod-name> -n <namespace> -c myapp        # Application logs
kubectl logs <pod-name> -n <namespace> -c istio-proxy  # Envoy logs
```

**Diagnóstico:**

* Si solo hay 1 contenedor → Sidecar no se inyectó
* Si el Pod está en CrashLoopBackOff → Falló la inicialización de la aplicación o de Sidecar

**Resolución:**

```bash
# Check Namespace injection label
kubectl get namespace <namespace> --show-labels

# Add label if missing
kubectl label namespace <namespace> istio-injection=enabled

# Restart Pod
kubectl rollout restart deployment/<deployment-name> -n <namespace>
```

***

**Paso 2: Comprobar Service y Endpoint**

```bash
# Check Service exists
kubectl get svc <service-name> -n <namespace>

# Check Service Endpoint (is Pod IP registered)
kubectl get endpoints <service-name> -n <namespace>

# Service details
kubectl describe svc <service-name> -n <namespace>
```

**Diagnóstico:**

* Si Endpoint está vacío → No coinciden el Service Selector y la Pod Label
* No coinciden el puerto de Service y el puerto de Pod

**Resolución:**

```bash
# Check Pod labels
kubectl get pods <pod-name> -n <namespace> --show-labels

# Check Service Selector
kubectl get svc <service-name> -n <namespace> -o yaml | grep -A 3 selector
```

***

**Paso 3: Comprobar la configuración de Istio**

```bash
# Check VirtualService
kubectl get virtualservice -n <namespace>
kubectl describe virtualservice <vs-name> -n <namespace>

# Check DestinationRule
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <dr-name> -n <namespace>

# Check Gateway (for external access)
kubectl get gateway -n <namespace>

# Validate Istio configuration
istioctl analyze -n <namespace>
```

**Diagnóstico:**

* Comprueba los mensajes de error de `istioctl analyze`
* Si el host de VirtualService coincide con el nombre de Service
* Si las etiquetas de subconjunto de DestinationRule coinciden con las Pod Labels

**Resolución:**

```bash
# Auto-detect configuration errors
istioctl analyze -n <namespace>

# Example output:
# Error [IST0101] (VirtualService reviews.default)
# Referenced host not found: reviews
```

***

**Paso 4: Comprobar mTLS y las políticas de seguridad**

```bash
# Check PeerAuthentication policies
kubectl get peerauthentication -A

# Check mTLS mode for specific Pod
istioctl authn tls-check <pod-name>.<namespace> <service-name>.<namespace>.svc.cluster.local

# Check AuthorizationPolicy
kubectl get authorizationpolicy -n <namespace>
```

**Diagnóstico:**

* No coinciden los modos de mTLS (STRICT frente a PERMISSIVE)
* AuthorizationPolicy bloquea el tráfico

**Resolución:**

```bash
# Temporarily change to PERMISSIVE mode (for debugging)
kubectl apply -f - <<EOF
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: <namespace>
spec:
  mtls:
    mode: PERMISSIVE
EOF

# Temporarily delete AuthorizationPolicy
kubectl delete authorizationpolicy <policy-name> -n <namespace>
```

***

**Paso 5: Comprobar la configuración de Envoy**

```bash
# Check Envoy cluster configuration (service discovery)
istioctl proxy-config clusters <pod-name> -n <namespace>

# Check Envoy listener configuration (inbound/outbound)
istioctl proxy-config listeners <pod-name> -n <namespace>

# Check Envoy route configuration
istioctl proxy-config routes <pod-name> -n <namespace>

# Check Envoy endpoints
istioctl proxy-config endpoints <pod-name> -n <namespace>
```

**Diagnóstico:**

* Si el servicio de destino no está en los clusters → Istiod no reconoce el servicio
* Si no hay listeners → Error de configuración de puertos
* Si los endpoints están UNHEALTHY → Pod no está listo

***

**Paso 6: Prueba de conexión de red**

```bash
# Test directly from inside Pod
kubectl exec -it <source-pod> -n <namespace> -- curl http://<target-service>:<port>

# Test directly without going through Envoy (by Pod IP)
kubectl exec -it <source-pod> -n <namespace> -- curl http://<pod-ip>:<port>

# Check DNS resolution
kubectl exec -it <source-pod> -n <namespace> -- nslookup <service-name>

# Check statistics via Envoy Admin API
kubectl exec -it <pod-name> -n <namespace> -c istio-proxy -- curl localhost:15000/stats | grep <service-name>
```

***

**Paso 7: Comprobar los registros de Istiod**

```bash
# Check Istiod logs (configuration push errors)
kubectl logs -n istio-system -l app=istiod --tail=100

# Check xDS configuration push status
istioctl proxy-status

# Specific Pod synchronization status
istioctl proxy-status <pod-name>.<namespace>
```

***

**Paso 8: Comprobar métricas y trazas**

```bash
# Check metrics in Prometheus
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# Check traces in Jaeger
kubectl port-forward -n istio-system svc/tracing 16686:16686

# Check topology in Kiali
istioctl dashboard kiali
```

***

**Diagrama de flujo para resolución de problemas:**

```
1. Pod/Sidecar normal?
   ├─ NO → Check Sidecar injection
   └─ YES → Step 2

2. Service/Endpoint normal?
   ├─ NO → Check Selector
   └─ YES → Step 3

3. Istio configuration normal?
   ├─ NO → Run istioctl analyze
   └─ YES → Step 4

4. mTLS/policies normal?
   ├─ NO → Test PERMISSIVE mode
   └─ YES → Step 5

5. Envoy configuration normal?
   ├─ NO → Restart Istiod
   └─ YES → Step 6

6. Network connection normal?
   ├─ NO → Check NetworkPolicy
   └─ YES → Analyze logs/metrics
```

**Referencia:**

* [Guía de depuración de Istio](https://istio.io/latest/docs/ops/diagnostic-tools/)

</details>

***

### Pregunta 10: Estrategia de actualización de Istio

Explica la estrategia de **Canary Upgrade** para actualizar Istio de 1.27.0 a 1.28.0 en un entorno de producción. Incluye comandos paso a paso y métodos de verificación.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Estrategia de Canary Upgrade de Istio:**

Canary Upgrade es un enfoque de actualización seguro que ejecuta simultáneamente versiones antiguas y nuevas del Control Plane y migra gradualmente los workloads.

***

**Preparación:**

```bash
# 1. Check current version
istioctl version

# 2. Create backup
kubectl get istiooperator -A -o yaml > istio-1.27-backup.yaml
kubectl get vs,dr,gw,se,pa,ra,ap -A -o yaml > istio-config-backup.yaml

# 3. Download new version
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.28.0 sh -
cd istio-1.28.0
export PATH=$PWD/bin:$PATH

# 4. Check compatibility
istioctl x precheck
```

***

**Paso 1: Instalar el nuevo Control Plane (mediante revision)**

```bash
# Install new version Control Plane using Revision
istioctl install --set revision=1-28-0 --set profile=production -y

# Verify installation
kubectl get pods -n istio-system -l app=istiod
# Example output:
# istiod-1-27-0-xxxx  (old version)
# istiod-1-28-0-xxxx  (new version)

# Check Revision
kubectl get mutatingwebhookconfigurations | grep istio
# Output:
# istio-sidecar-injector-1-27-0
# istio-sidecar-injector-1-28-0
```

**Importante:** En este momento, **dos Control Planes** se ejecutan simultáneamente.

***

**Paso 2: Validación Canary con Namespace de prueba**

```bash
# Create test namespace
kubectl create namespace istio-upgrade-test

# Label for new version
kubectl label namespace istio-upgrade-test istio.io/rev=1-28-0

# Deploy test application
kubectl apply -n istio-upgrade-test -f samples/sleep/sleep.yaml
kubectl apply -n istio-upgrade-test -f samples/httpbin/httpbin.yaml

# Check Sidecar version (should be 1.28.0)
kubectl get pods -n istio-upgrade-test -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}'

# Test communication
kubectl exec -n istio-upgrade-test deploy/sleep -- curl http://httpbin:8000/headers

# Check Envoy configuration
istioctl proxy-config clusters deploy/sleep.istio-upgrade-test
```

**Lista de verificación de validación:**

* ✅ ¿Se inyecta Sidecar con la versión 1.28.0?
* ✅ ¿La comunicación entre servicios funciona normalmente?
* ✅ ¿mTLS funciona correctamente?
* ✅ ¿Se recopilan las métricas?

***

**Paso 3: Migrar el Namespace de staging**

```bash
# Switch staging namespace to new version
kubectl label namespace staging istio.io/rev=1-28-0 --overwrite

# Remove existing label (if present)
kubectl label namespace staging istio-injection-

# Restart Pods (inject new version Sidecar)
kubectl rollout restart deployment -n staging

# Monitor restart status
kubectl rollout status deployment -n staging

# Verify version
kubectl get pods -n staging -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}'
```

**Verificación:**

```bash
# Check metrics
kubectl exec -n staging <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | grep istio_build

# Test communication
kubectl exec -n staging <pod-name> -- curl http://<service-name>

# Visual confirmation with Kiali
istioctl dashboard kiali
```

**Monitorea durante 24-48 horas:**

* Comprueba las métricas de Prometheus
* Compara las tasas de error y la latencia
* Comprueba el uso de recursos de Istiod

***

**Paso 4: Migración gradual de Namespaces de producción**

```bash
# List of production Namespaces
PROD_NAMESPACES="prod-api prod-web prod-worker"

# Migrate one at a time gradually
for ns in $PROD_NAMESPACES; do
  echo "Upgrading namespace: $ns"

  # Update label
  kubectl label namespace $ns istio.io/rev=1-28-0 --overwrite

  # Restart Pods
  kubectl rollout restart deployment -n $ns

  # Wait for completion
  kubectl rollout status deployment -n $ns

  # Verify
  echo "Verifying namespace: $ns"
  kubectl exec -n $ns <pod-name> -- curl http://<service-name>

  # Wait before next Namespace migration (observation)
  echo "Waiting 1 hour before next namespace..."
  sleep 3600
done
```

**Verificación paso a paso:**

```bash
# After each Namespace migration
# 1. Golden Signals
kubectl port-forward -n istio-system svc/prometheus 9090:9090
# Query in Prometheus:
# - istio_requests_total
# - istio_request_duration_milliseconds
# - istio_request_bytes

# 2. Control Plane status
istioctl proxy-status | grep $ns

# 3. Error logs
kubectl logs -n istio-system -l app=istiod,istio.io/rev=1-28-0 --tail=100
```

***

**Paso 5: Eliminar la versión anterior**

```bash
# Verify all Namespaces have migrated to new version
kubectl get namespace -L istio.io/rev

# Verify no Pods using old version
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}' | grep 1.27

# Remove old version Control Plane
istioctl uninstall --revision=1-27-0 -y

# Verify removal
kubectl get pods -n istio-system -l app=istiod

# Cleanup
kubectl delete mutatingwebhookconfigurations istio-sidecar-injector-1-27-0
kubectl delete validatingwebhookconfigurations istio-validator-1-27-0-istio-system
```

***

**Paso 6: Actualización de Gateway (opcional)**

```bash
# Upgrade Gateway separately
kubectl patch deployment istio-ingressgateway -n istio-system \
  -p '{"spec":{"template":{"metadata":{"labels":{"istio.io/rev":"1-28-0"}}}}}'

kubectl rollout restart deployment istio-ingressgateway -n istio-system
kubectl rollout status deployment istio-ingressgateway -n istio-system
```

***

**Plan de rollback:**

```bash
# Immediate rollback if issues occur
# 1. Change Namespace label to old version
kubectl label namespace <namespace> istio.io/rev=1-27-0 --overwrite

# 2. Restart Pods
kubectl rollout restart deployment -n <namespace>

# 3. Remove new version Control Plane
istioctl uninstall --revision=1-28-0 -y
```

***

**Prácticas recomendadas:**

1. **Enfoque por fases:**
   * Avanza por etapas: Prueba → Staging → Producción
   * Migra un Namespace a la vez
   * Permite suficiente tiempo de observación en cada etapa
2. **Monitoreo:**
   * Monitorea Golden Signals (latencia, tráfico, errores, saturación)
   * Comprueba el uso de recursos de Istiod
   * Observa durante 24-48 horas en cada etapa
3. **Automatización:**
   * Intégralo en la canalización de CI/CD
   * Automatiza Smoke Tests
   * Prepara scripts de rollback
4. **Comunicación:**
   * Comparte el calendario de actualización con el equipo
   * Revisa las notas de la versión
   * Documenta los cambios

**Referencia:**

* [Canary Upgrade](https://istio.io/latest/docs/setup/upgrade/canary/)
* [Estrategia de actualización](../../../service-mesh/istio/best-practices.md#upgrade-strategy)

</details>

***

## Cálculo de puntuación

* Opción múltiple 1-5: 10 puntos cada una (Total: 50 puntos)
* Respuesta corta 6-10: 10 puntos cada una (Total: 50 puntos)
* **Total: 100 puntos**

**Criterios de evaluación:**

* 90-100 puntos: Excelente (Comprensión perfecta de los conceptos básicos de Istio)
* 80-89 puntos: Bueno (Capaz de realizar operaciones básicas)
* 70-79 puntos: Regular (Se recomienda aprendizaje adicional)
* 60-69 puntos: Por debajo del promedio (Se necesita repasar los conceptos básicos)
* 0-59 puntos: Se necesita volver a aprender

## Recursos de aprendizaje

* [Guía de instalación de Istio](../../../service-mesh/istio/01-installation.md)
* [Conceptos básicos](../../../service-mesh/istio/02-basic-concepts.md)
* [Componentes](../../../service-mesh/istio/03-architecture.md)
* [Documentación oficial de Istio](https://istio.io/latest/docs/)
