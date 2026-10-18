# Cuestionario básico

> **Versión revisada**: Istio 1.31.0 **Versiones de EKS**: 1.34–1.36 **Última actualización**: 11 de septiembre de 2026

Este cuestionario evalúa su comprensión de los conceptos básicos y la arquitectura de Istio.

## Preguntas de opción múltiple (1–5)

### Pregunta 1: Definición de la malla de servicios

¿Cuál de estas afirmaciones sobre la malla de servicios (Service Mesh) **NO es correcta**?

A. Es una capa de infraestructura que gestiona la comunicación entre microservicios\
B. Solo se puede utilizar si se modifica el código de la aplicación\
C. Proporciona control del tráfico y observabilidad entre servicios\
D. Aplica seguridad y políticas en la capa de red

<details>

<summary>Mostrar la respuesta</summary>

**Respuesta: B**

Una de las ventajas principales de una malla de servicios es que puede controlar y observar la comunicación entre servicios **sin modificar el código de la aplicación**.

**Explicación:**

* A (Correcta): La malla de servicios es una capa de infraestructura dedicada a gestionar la comunicación entre servicios en una arquitectura de microservicios.
* B (Incorrecta): Se aplica de forma transparente mediante proxies sidecar o el modo ambient, sin modificar el código de la aplicación.
* C (Correcta): Controla el tráfico con recursos como VirtualService y DestinationRule, y expone métricas. Los logs y traces requieren configuración, y las aplicaciones deben propagar el contexto de trace.
* D (Correcta): Aplica políticas de seguridad en la capa de red con mTLS, AuthorizationPolicy y otros recursos.

**Referencia:**

* [Conceptos básicos de Istio](../../../service-mesh/istio/02-basic-concepts.md)
* [¿Qué es una malla de servicios?](../../../service-mesh/istio/README.md)

</details>

***

### Pregunta 2: Componentes de la arquitectura de Istio

En el plano de control de Istio, ¿qué componente centralizado se encarga del descubrimiento de servicios, la gestión de la configuración y la gestión de certificados?

A. Envoy\
B. Istiod\
C. Pilot\
D. Citadel

<details>

<summary>Mostrar la respuesta</summary>

**Respuesta: B**

**Istiod** es un binario único, introducido en Istio 1.5, que integra los componentes anteriores Pilot, Citadel y Galley.

**Explicación:**

* A (Incorrecta): Envoy es un proxy del plano de datos que se ejecuta como sidecar en cada Pod.
* B (Correcta): Istiod es el núcleo del plano de control y gestiona:
  * el descubrimiento de servicios;
  * la gestión de la configuración;
  * la gestión de certificados.
* C (Incorrecta): Pilot era un componente de las versiones de Istio anteriores a la 1.5; ahora está integrado en Istiod.
* D (Incorrecta): Citadel también era un componente de las versiones de Istio anteriores a la 1.5; ahora está integrado en Istiod.

**Funciones principales de Istiod:**

```yaml
# Configurations managed by Istiod
1. Service Discovery: Kubernetes Service -> Envoy Cluster
2. Config Distribution: VirtualService, DestinationRule -> Envoy Config
3. Certificate Issuance: Service Account -> mTLS Certificate
```

**Referencia:**

* [Componentes de Istio](../../../service-mesh/istio/03-architecture.md)
* [Descripción general de la arquitectura](../../../service-mesh/istio/README.md)

</details>

***

### Pregunta 3: Función del proxy Envoy

¿Cuál de las siguientes **NO** es una tarea del proxy Envoy del plano de datos?

A. Enrutar el tráfico y balancear la carga\
B. Cifrar el tráfico y autenticar mediante mTLS\
C. Validar y almacenar CRD de Kubernetes\
D. Recopilar métricas, logs y traces

<details>

<summary>Mostrar la respuesta</summary>

**Respuesta: C**

El servidor de API de Kubernetes almacena los recursos y aplica sus esquemas; Istiod también valida la configuración de Istio mediante webhooks de admisión. Envoy no almacena CRD de Kubernetes.

**Explicación:**

* A (Correcta): Envoy enruta el tráfico y balancea la carga según las reglas de VirtualService.
* B (Correcta): Envoy cifra automáticamente la comunicación entre servicios con mTLS y valida los certificados.
* C (Incorrecta): La validación y el almacenamiento de CRD corresponden al servidor de API de Kubernetes e Istiod.
* D (Correcta): Envoy recopila métricas (Prometheus), logs (access logs) y traces (Jaeger), según la configuración de registro y muestreo de traces.

**Referencia:**

* [Estructura del plano de datos](../../../service-mesh/istio/03-architecture.md#data-plane-envoy-proxy)

</details>

***

### Pregunta 4: Perfiles de instalación de Istio

¿Qué perfil se recomienda como punto de partida al instalar Istio en un entorno de producción de Amazon EKS?

A. default\
B. demo\
C. minimal\
D. production

<details>

<summary>Mostrar la respuesta</summary>

**Respuesta: A**

`default` es el perfil inicial recomendado para una instalación sidecar en este entorno. No existe un perfil integrado `production`. Configure explícitamente las réplicas, las solicitudes de recursos, la ubicación de las cargas, los PDB y las políticas de seguridad; elegir `default` por sí solo no proporciona alta disponibilidad.

| Perfil | Uso |
|---|---|
| default | Configuración inicial para producción; personalícela según la carga de trabajo |
| demo | Demostraciones; telemetría detallada, no pruebas de rendimiento |
| minimal | Solo el plano de control |
| production | No es un perfil integrado |

```bash
istioctl install --set profile=default
```

**Lista de comprobación para producción:**

* ✅ Alta disponibilidad del plano de control (al menos 3 réplicas)
* ✅ mTLS en modo STRICT
* ✅ PodDisruptionBudget configurado
* ✅ Límites de recursos y HPA configurados
* ✅ Stack de monitorización preparado

**Referencia:**

* [Guía de instalación](../../../service-mesh/istio/01-installation.md)
* [Prácticas recomendadas](../../../service-mesh/istio/best-practices.md#production-checklist)

</details>

***

### Pregunta 5: CRD de Istio (Custom Resource Definition)

¿Cuál de estos recursos **NO** pertenece a la categoría de gestión del tráfico de Istio?

A. VirtualService\
B. DestinationRule\
C. PeerAuthentication\
D. Gateway

<details>

<summary>Mostrar la respuesta</summary>

**Respuesta: C**

**PeerAuthentication** es un recurso de seguridad.

**Explicación:**

**Clasificación de los CRD de Istio:**

**1. Gestión del tráfico:**

* VirtualService: define reglas de enrutamiento.
* DestinationRule: configura el balanceo de carga y define subconjuntos.
* Gateway: proporciona un punto de entrada para el tráfico externo.
* ServiceEntry: define un servicio externo.
* Sidecar: limita el alcance de la configuración de Envoy.

**2. Seguridad:**

* PeerAuthentication: autentica servicios entre sí (mTLS).
* RequestAuthentication: autentica a los usuarios finales (JWT).
* AuthorizationPolicy: controla el acceso.

**3. Observabilidad:**

* Telemetry: configura métricas, logs y traces.

**Ejemplo:**

```yaml
# Traffic Management
apiVersion: networking.istio.io/v1
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
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**Referencia:**

* [Gestión del tráfico](../../../service-mesh/istio/traffic-management/README.md)
* [Seguridad](../../../service-mesh/istio/security/README.md)

</details>

***

## Preguntas de respuesta corta (6–10)

### Pregunta 6: Mecanismos de inyección de sidecars

Explique dos métodos para inyectar automáticamente un sidecar Envoy en los Pods de Istio y compare las ventajas y desventajas de cada uno.

<details>

<summary>Mostrar la respuesta</summary>

**Respuesta:**

Istio inyecta sidecars automáticamente mediante dos métodos:

**1. Inyección automática a nivel de namespace:**

```bash
# Add label to Namespace
kubectl label namespace default istio-injection=enabled

# All Pods deployed afterward will have automatic injection
kubectl apply -f deployment.yaml
```

**Ventajas:**

* Se puede aplicar a todo un namespace de una vez.
* Es fácil de administrar.
* Reduce la probabilidad de omisiones accidentales.

**Desventajas:**

* Se aplica a todos los Pods del namespace, por lo que hay que excluir algunos de forma selectiva.
* Es necesario reiniciar los Pods existentes.

**2. Inyección selectiva a nivel de Pod:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
        sidecar.istio.io/inject: "true"  # or "false"
    spec:
      containers:
      - name: myapp
        image: myapp:latest
```

**Ventajas:**

* Permite inyectar el sidecar solo en determinados Pods.
* Ofrece un control más granular.
* No requiere una etiqueta en el namespace.

**Desventajas:**

* Hay que configurar cada Deployment.
* Aumenta el número de puntos de administración.
* Existe riesgo de omisiones accidentales.

**Comparación:**

| Aspecto | Nivel de namespace | Nivel de Pod |
|---|---|---|
| Alcance | Todo el namespace | Un Pod |
| Complejidad de administración | Baja | Alta |
| Selectividad | Baja (hay que excluir Pods) | Alta |
| Uso recomendado | Entornos de producción | Entornos mixtos |

**Recomendación para producción:**

* Use la inyección a nivel de namespace como opción predeterminada.
* Establezca `sidecar.istio.io/inject: "false"` solo en los Pods que deban excluirse.

**Referencia:**

* [Inyección de sidecars](../../../service-mesh/istio/advanced/07-sidecar-injection.md)

</details>

***

### Pregunta 7: Optimización del uso de recursos de Istio

Calcule y compare el **uso estimado de recursos** de los modos sidecar y ambient en un clúster de Kubernetes a gran escala con 1000 Pods. Suponga que ztunnel está desplegado en 10 nodos y que hay un waypoint.

<details>

<summary>Mostrar la respuesta</summary>

**Respuesta:**

Estos datos son valores inventados para un ejercicio aritmético; no son requisitos de recursos medidos de Istio ni una recomendación de dimensionamiento. Use de forma coherente MB/GB decimales. Suponga 0,1 vCPU por sidecar, 0,1 vCPU por ztunnel y 0,5 vCPU para el waypoint.

**Supuestos:**

* Número de Pods: 1000
* Número de nodos: 10
* Memoria de sidecar: 50 MB/Pod
* Memoria de ztunnel: 50 MB/nodo
* Memoria del waypoint: 200 MB

**1. Uso de recursos del modo sidecar:**

```
Memory Usage = Number of Pods × Sidecar Memory
             = 1000 × 50MB
             = 50,000MB
             = 50GB

CPU Usage = Number of Pods × Sidecar CPU
          = 1000 × 0.1 vCPU
          = 100 vCPU
```

**2. Uso de recursos del modo ambient:**

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

| Recurso | Modo sidecar | Modo ambient | Ahorro | Porcentaje de ahorro |
|---|---|---|---|---|
| **Memoria** | 50 GB | 0,7 GB | 49,3 GB | **98,6 %** |
| **CPU** | 100 vCPU | 1,5 vCPU | 98,5 vCPU | **98,5 %** |

**Interpretación:**

Con los supuestos indicados, la reducción es del 98,6 % en memoria y del 98,5 % en CPU, y se refiere únicamente al total de recursos de los proxies. No implica una reducción del 96 % en la factura de AWS ni que un clúster de 10 nodos y 1000 Pods pueda ejecutarse en una sola instancia. No se incluyen los recursos de las aplicaciones, los límites de Pods/IP, la alta disponibilidad, las réplicas, el rendimiento ni la capacidad del waypoint. Mida la topología real antes de dimensionar o estimar costes. Las funciones principales de ambient son GA desde Istio 1.24.

**Referencia:**

* [Modo ambient](../../../service-mesh/istio/advanced/01-ambient-mode.md#resource-usage-comparison)
* [Optimización de costes](../../../service-mesh/istio/best-practices.md#cost-optimization)

</details>

***

### Pregunta 8: Funcionamiento de mTLS

Explique paso a paso cómo funciona mTLS cuando se comunican dos servicios (`service-a` y `service-b`) en Istio. Incluya las funciones de Istiod, Envoy y el certificado.

<details>

<summary>Mostrar la respuesta</summary>

**Respuesta:**

**Proceso de funcionamiento de mTLS (Mutual TLS):**

**Paso 1: Emisión del certificado (bootstrap)**

* Al iniciarse el Pod, el agente de Istio crea una clave privada y una CSR, y se autentica ante Istiod con credenciales de carga de trabajo. Envoy recibe el certificado y la clave del agente local mediante SDS.
* Istiod valida la ServiceAccount y emite un certificado X.509.
* El certificado contiene el identificador de la ServiceAccount (por ejemplo, `cluster.local/ns/default/sa/service-a`).
* Validez del certificado: 24 horas de forma predeterminada; se renueva automáticamente.

**Paso 2: Comunicación entre servicios (negociación mTLS)**

```
Service A → Envoy A → [mTLS] → Envoy B → Service B
```

**Proceso detallado:**

```text
1. The source app sends HTTP; configured redirection sends it through Envoy A.
2. Auto mTLS/DestinationRule determines outbound TLS; destination PeerAuthentication
   determines whether Envoy B requires inbound mTLS.
3. ClientHello and ServerHello negotiate TLS parameters/key exchange.
   Certificates are sent in Certificate messages, not in ClientHello/ServerHello.
   The server requests the client certificate; each peer validates the other
   certificate and proof of key possession against the configured trust chain.
4. Envoy B applies authorization and forwards the decrypted request to Service B.
5. The response travels over the established TLS connection.
```

**Funciones de cada componente:**

**Istiod:**

* Actúa como autoridad de certificación (CA); puede usar una autoridad intermedia subordinada a una raíz externa.
* Emite certificados basados en la ServiceAccount.
* Firma solicitudes de renovación antes de que caduque el certificado; la duración del certificado se puede configurar.
* Distribuye las políticas PeerAuthentication.

**Sidecar Envoy:**

* Recibe certificados del agente de Istio mediante SDS.
* Realiza la negociación TLS.
* Cifra y descifra el tráfico.
* Valida certificados.

**Certificado:**

* Formato X.509.
* Subject Alternative Name (SAN): URI de la ServiceAccount.
* Validez predeterminada: 24 horas.
* Renovación automática.

**Ejemplo de configuración:**

```yaml
# PeerAuthentication - STRICT mTLS
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Force all communication to mTLS
```

**Verificación del certificado:**

```bash
# Inspect certificate validity/status; private keys are not shown as plaintext
istioctl proxy-config secret <pod-name> -n <namespace>
istioctl proxy-config secret <pod-name> -n <namespace> -o json
```

**Ventajas de seguridad:**

1. **Confidencialidad:** se cifra toda la comunicación.
2. **Integridad:** se evita la manipulación de los datos.
3. **Autenticación:** se verifican las identidades en ambos sentidos.
4. **Automatización:** se aplica sin modificar el código.

**Referencia:**

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [Gestión de certificados](../../../service-mesh/istio/03-architecture.md#3-certificate-management-citadel-functionality)

</details>

***

### Pregunta 9: Diagnóstico de Istio

Describa un procedimiento de diagnóstico paso a paso para investigar por qué un servicio recién desplegado no puede comunicarse dentro de la malla de Istio. Incluya al menos cinco pasos.

<details>

<summary>Mostrar la respuesta</summary>

**Respuesta:**

**Lista de comprobación para diagnosticar la comunicación entre servicios de Istio:**

**Paso 1: Comprobar el estado del Pod y del sidecar**

```bash
# Check if Pod is running normally
kubectl get pods -n <namespace>

# Check if Sidecar is injected (should have 2 containers)
kubectl get pods <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].name}{" "}{.spec.initContainers[*].name}'
# Expected output: myapp istio-proxy

# Detailed Sidecar injection check
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Containers:"

# Check Pod logs
kubectl logs <pod-name> -n <namespace> -c myapp        # Application logs
kubectl logs <pod-name> -n <namespace> -c istio-proxy  # Envoy logs
```

**Diagnóstico:**

* Compruebe si `istio-proxy` aparece entre los contenedores o en `initContainers` como sidecar nativo; las cargas de trabajo ambient no tienen un sidecar inyectado.
* Si el Pod está en `CrashLoopBackOff`, ha fallado la inicialización de la aplicación o del sidecar.

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

**Paso 2: Comprobar el Service y los endpoints**

```bash
# Check Service exists
kubectl get svc <service-name> -n <namespace>

# Check Service Endpoint (is Pod IP registered)
kubectl get endpointslices -n <namespace> -l kubernetes.io/service-name=<service-name>

# Service details
kubectl describe svc <service-name> -n <namespace>
```

**Diagnóstico:**

* Si la lista de endpoints está vacía, es posible que el selector del Service no coincida con las etiquetas del Pod.
* Compruebe si el puerto del Service coincide con el puerto del Pod.

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
kubectl get gateways.networking.istio.io -n <namespace>

# Validate Istio configuration
istioctl analyze -n <namespace>
```

**Diagnóstico:**

* Revise los mensajes de error de `istioctl analyze`.
* Compruebe si el host de VirtualService coincide con el nombre del Service.
* Compruebe si las etiquetas de los subconjuntos de DestinationRule coinciden con las etiquetas de los Pods.

**Resolución:**

```bash
# Auto-detect configuration errors
istioctl analyze -n <namespace>

# Example output:
# Error [IST0101] (VirtualService reviews.default)
# Referenced gateway not found: missing-gateway
```

***

**Paso 4: Comprobar mTLS y las políticas de seguridad**

```bash
# Check PeerAuthentication policies
kubectl get peerauthentication -A

# Check mTLS mode for specific Pod
istioctl proxy-config secret <pod-name> -n <namespace>
istioctl proxy-config clusters <pod-name> -n <namespace> -o json
istioctl x authz check <pod-name> -n <namespace>

# Check AuthorizationPolicy
kubectl get authorizationpolicy -n <namespace>
```

**Diagnóstico:**

* Compruebe si llega tráfico de cliente en texto sin cifrar a un destino STRICT, si hay certificados caducados o si la confianza entre certificados es incompatible.
* Compruebe si AuthorizationPolicy bloquea el tráfico.

**Resolución:**

Inspeccione las políticas efectivas, la identidad de la carga de trabajo, los certificados y los logs de denegación de Envoy. Los servidores STRICT y PERMISSIVE pueden aceptar clientes de la malla que utilicen mTLS. Pruebe los cambios de política en un namespace de prueba aislado; eliminar políticas de autorización activas o relajar mTLS no es una medida de diagnóstico predeterminada.



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

* Si el servicio de destino no aparece entre los clusters, Istiod podría no estar reconociendo el servicio.
* Si no hay listeners, puede haber un error de configuración de puertos.
* Si los endpoints están `UNHEALTHY`, es posible que el Pod no esté preparado.

***

**Paso 6: Probar la conexión de red**

```bash
# Test directly from inside Pod
kubectl exec -it <source-pod> -n <namespace> -- curl http://<target-service>:<port>

# Compare Pod-IP routing; this does not bypass the sidecar interception
kubectl exec -it <source-pod> -n <namespace> -- curl http://<pod-ip>:<port>

# Check DNS resolution
kubectl exec -it <source-pod> -n <namespace> -- nslookup <service-name>

# Check statistics via Envoy Admin API
istioctl dashboard envoy <pod-name> -n <namespace>
```

***

**Paso 7: Comprobar los logs de Istiod**

```bash
# Check Istiod logs (configuration push errors)
kubectl logs -n istio-system -l app=istiod --tail=100

# Check xDS configuration push status
istioctl proxy-status

# Specific Pod synchronization status
istioctl proxy-status <pod-name>.<namespace>
```

***

**Paso 8: Comprobar las métricas y los traces**

Los complementos de telemetría deben instalarse por separado. Ejecute cada port-forward bloqueante en su propia terminal; sustituya los nombres por el servicio y el namespace reales de su collector.

```bash
# Check metrics in Prometheus
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# Check traces in Jaeger
kubectl port-forward -n istio-system svc/tracing 16686:16686

# Check topology in Kiali
istioctl dashboard kiali
```

***

**Diagrama de flujo de diagnóstico:**

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
   ├─ NO → Inspect identity, certificates, and denial logs
   └─ YES → Step 5

5. Envoy configuration normal?
   ├─ NO → Inspect xDS status and istiod logs
   └─ YES → Step 6

6. Network connection normal?
   ├─ NO → Check NetworkPolicy
   └─ YES → Analyze logs/metrics
```

**Referencia:**

* [Guía de diagnóstico de Istio](https://istio.io/latest/docs/ops/diagnostic-tools/)

</details>

***

### Pregunta 10: Estrategia de actualización de Istio

Explique cómo realizar una actualización canary de Istio 1.30.4 a 1.31.0 en un clúster de EKS compatible. Incluya la migración de las cargas de trabajo, el tratamiento de los gateways, la verificación y las condiciones para revertir.

<details>
<summary>Mostrar la respuesta</summary>

Mantenga el plano de control antiguo hasta que se hayan migrado todas las cargas de trabajo y todos los gateways, y haya finalizado el periodo de reversión. Este ejemplo usa sidecars administrados por `istioctl`; las instalaciones con Helm y ambient tienen procedimientos de actualización propios. Los nombres de revisión siguientes son ejemplos y deben coincidir con la instalación real.

**1. Preparación y copia de seguridad**

Compruebe las matrices de compatibilidad de Istio/EKS y las notas de la versión. Conserve el archivo de instalación existente, las versiones de los charts si corresponde, los recursos de la malla y los secretos de CA/TLS, tal como se describe en el capítulo de prácticas recomendadas. Descargue `istioctl` de la versión de destino y ejecute su comprobación previa:

```bash
curl -fsSL https://istio.io/downloadIstio | ISTIO_VERSION=1.31.0 sh -
cd istio-1.31.0
export PATH="$PWD/bin:$PATH"
istioctl version
istioctl x precheck
```

**2. Instalar el plano de control canary**

Prepare `canary-install.yaml` a partir de la configuración existente y conserve la identidad de la malla, la confianza y los ajustes de recursos. Establezca la revisión `1-31-0` y use `minimal` para instalar solo el plano de control canary, sin habilitar componentes de gateway. Genere y revise la configuración antes de instalar:

```bash
istioctl manifest generate -f canary-install.yaml > canary-rendered.yaml
istioctl install -f canary-install.yaml
kubectl rollout status deployment/istiod-1-31-0 -n istio-system
```

No existe un perfil `production`. Una etiqueta de revisión no selecciona la versión del binario; esa versión depende de `istioctl` y de la configuración de destino.

**3. Verificar un namespace de prueba**

```bash
kubectl create namespace istio-upgrade-test
kubectl label namespace istio-upgrade-test istio.io/rev=1-31-0
kubectl apply -n istio-upgrade-test -f samples/curl/curl.yaml
kubectl apply -n istio-upgrade-test -f samples/httpbin/httpbin.yaml
kubectl rollout status deployment/curl -n istio-upgrade-test
kubectl rollout status deployment/httpbin -n istio-upgrade-test
kubectl exec -n istio-upgrade-test deploy/curl -c curl -- curl -fsS http://httpbin:8000/headers
istioctl proxy-status
istioctl analyze -n istio-upgrade-test
```

Antes de continuar, verifique las versiones reales de las imágenes proxy, el estado de sincronización, el comportamiento de mTLS y de autorización, los errores y la latencia.

**4. Migrar primero staging y, después, un namespace de producción a la vez**

Quite `istio-injection`, que tiene prioridad sobre la etiqueta de revisión. Reinicie los controladores para crear Pods con el nuevo proxy; incluya StatefulSets, DaemonSets y futuros Jobs cuando corresponda.

```bash
kubectl label namespace staging istio-injection- istio.io/rev=1-31-0 --overwrite
kubectl rollout restart deployment -n staging
kubectl rollout status deployment -n staging
istioctl proxy-status
```

Repita el proceso solo después de que las pruebas funcionales de la aplicación finalicen correctamente y haya transcurrido un periodo de observación adecuado para la carga de trabajo. Esperar un intervalo fijo no es un criterio de salud.

**5. Migrar los gateways antes de retirar el plano de control antiguo**

Actualice los gateways mediante la configuración de `istioctl` o Helm que los administra, incluidos la imagen proxy, la revisión y los ajustes de balanceadores de carga externos. En un gateway con una imagen antigua especificada explícitamente, no basta con cambiar la etiqueta de un Deployment. Verifique el rollout, las solicitudes externas y el estado de los proxies. El perfil predeterminado de `istioctl` puede actualizar gateways compartidos en el mismo lugar; planifique este comportamiento explícitamente.

**6. Completar la actualización o revertirla**

Después de comprobar que todos los proxies, incluidos los de gateways y cargas que no sean Deployments, han dejado la revisión antigua, elimínela mediante la herramienta de instalación. No elimine manualmente los webhooks de validación compartidos:

```bash
istioctl proxy-status
istioctl uninstall --revision=1-30-4
```

Antes de retirar la revisión antigua, para revertir la actualización vuelva a etiquetar los namespaces afectados con la revisión antigua que sigue activa, reinicie sus cargas de trabajo, restaure los gateways actualizados con la configuración de la versión antigua y valide el tráfico. Retire la revisión nueva solo cuando ningún proxy dependa de ella. Si ya eliminó la revisión antigua, vuelva a instalarla y validarla antes de volver a etiquetar las cargas de trabajo.

**Referencias:**

- [Actualización canary](https://istio.io/latest/docs/setup/upgrade/canary/)
- [Orientación sobre copias de seguridad y operaciones](../../../service-mesh/istio/best-practices.md)

</details>

***

## Cálculo de la puntuación

* Opción múltiple, preguntas 1–5: 10 puntos cada una (total: 50 puntos)
* Respuesta corta, preguntas 6–10: 10 puntos cada una (total: 50 puntos)
* **Total: 100 puntos**

**Criterios de evaluación:**

* 90–100 puntos: Excelente (dominio de los conceptos básicos de Istio)
* 80–89 puntos: Bueno (capacidad para realizar operaciones básicas)
* 70–79 puntos: Promedio (se recomienda ampliar el aprendizaje)
* 60–69 puntos: Por debajo del promedio (conviene repasar los conceptos básicos)
* 0–59 puntos: Es necesario volver a estudiar el material

## Recursos de aprendizaje

* [Guía de instalación de Istio](../../../service-mesh/istio/01-installation.md)
* [Conceptos básicos](../../../service-mesh/istio/02-basic-concepts.md)
* [Componentes](../../../service-mesh/istio/03-architecture.md)
* [Documentación oficial de Istio](https://istio.io/latest/docs/)

* [Perfiles de configuración de instalación](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
* [Instalación del sidecar](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
* [Seguridad](https://istio.io/latest/docs/concepts/security/)
* [Grupo de trabajo de ingeniería de Internet (IETF), E. Rescorla](https://www.rfc-editor.org/rfc/rfc8446.html)
* [Actualizaciones canary](https://istio.io/latest/docs/setup/upgrade/canary/)
* [istioctl](https://istio.io/latest/docs/reference/commands/istioctl/)
* [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
* [Anuncio de Istio 1.24.0](https://istio.io/latest/news/releases/1.24.x/announcing-1.24/)
* [Rendimiento y escalabilidad](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
