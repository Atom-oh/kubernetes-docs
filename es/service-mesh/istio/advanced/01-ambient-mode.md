# Modo Ambient

> **Última actualización**: September 11, 2026 · Istio 1.31. Este laboratorio presupone nodos Linux compatibles, permisos del agente de nodo/CNI y un espacio de nombres de demostración nuevo. Esta auditoría no ejecutó comandos de despliegue.

Ambient se presentó como una versión preliminar experimental en 2022, se incluyó por primera vez como Alpha en Istio 1.18, alcanzó Beta en 1.22 y la disponibilidad general (GA) de sus funciones principales en 1.24. La versión preliminar no era una función de disponibilidad general de la versión principal 1.15. El ahorro de recursos y la seguridad de la migración dependen de la topología, las políticas y el tráfico reales.

## Índice

1. [Descripción general](#overview)
2. [Modo Sidecar frente a modo Ambient](#sidecar-mode-vs-ambient-mode)
3. [Arquitectura](#architecture)
4. [Instalación y configuración](#installation-and-configuration)
5. [Migración](#migration)
6. [Comparación del rendimiento](#performance-comparison)
7. [Casos de uso](#use-cases)
8. [Solución de problemas](#troubleshooting)

## Descripción general {#overview}


El modo Ambient es un nuevo enfoque que proporciona funciones de malla de servicios sin inyectar proxies Sidecar en los pods de aplicaciones. El modo Ambient consta de una **arquitectura por capas**:

1. **Capa de superposición segura (L4)**: mTLS y telemetría básica mediante ztunnel
2. **Capa de procesamiento L7**: gestión avanzada del tráfico mediante el proxy Waypoint

### ¿Por qué se necesita el modo Ambient?

Limitaciones del modelo Sidecar tradicional:
- **Alto consumo adicional de recursos**: cada pod requiere un proxy Envoy (mida el consumo real del proxy)
- **Complejidad operativa**: los reinicios de pods, la gestión de versiones y las actualizaciones graduales son complejos
- **Coordinación del inicio**: es necesario coordinar la disponibilidad del proxy y de la aplicación
- **Funcionalidad excesiva**: algunas cargas de trabajo solo necesitan funciones L4 de la malla

Soluciones del modo Ambient:
- Proxies de nodo compartidos más los waypoints necesarios: mida el consumo total de recursos
- La incorporación puede evitar reiniciar los Pods que no pertenecen a la malla; eliminar sidecars y cambiar políticas requiere un despliegue controlado
- Adopción gradual: amplíe de L4 a L7 según sea necesario
- El transporte L4 puede ser transparente; el contexto de trazas y los contratos de tiempo de espera/idempotencia de la aplicación siguen siendo relevantes

### Conceptos básicos

El waypoint opcional de estas figuras se selecciona mediante la configuración/incorporación. Ztunnel no analiza cada solicitud HTTP para decidir si debe desviarla por L7. Aún es necesario validar las conexiones existentes, la disponibilidad y las transiciones de políticas.


![Diagrama que contrasta el modo Sidecar, donde cada pod combina su aplicación con un sidecar Envoy, con el modo Ambient, donde los pods envían tráfico de forma transparente a un ztunnel del nodo con una ruta Waypoint configurada opcional para el procesamiento L7.](../../../.gitbook/assets/en-service-mesh-istio-advanced-01-ambient-mode-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-01-ambient-mode-0.html)

### Ventajas del modo Ambient

1. **Modelo de recursos compartidos**: proxies de nodo más las réplicas de waypoint necesarias
2. **Despliegue sencillo**: incorporar Pods ajenos a la malla no exige reiniciarlos; eliminar un sidecar sí
3. **Transporte L4 transparente**: se mantienen los requisitos de trazas/plazos/idempotencia de la aplicación
4. **Funciones L7 flexibles**: utilice un waypoint solo cuando lo necesite

## Modo Sidecar frente a modo Ambient {#sidecar-mode-vs-ambient-mode}

### Comparación de arquitecturas

#### Modo Sidecar

![Diagrama de arquitectura con tres pods, cada uno con un contenedor de aplicación y su propio proxy sidecar Envoy, que negocian TLS mutuo directamente entre los sidecars.](../../../.gitbook/assets/en-service-mesh-istio-advanced-01-ambient-mode-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-01-ambient-mode-1.html)

**Características**:
- Proxy Envoy inyectado en cada pod
- Funciones L4/L7 maduras; verifique la versión elegida
- Alto consumo de recursos
- Requiere reiniciar los pods

#### Modo Ambient

![Diagrama de arquitectura con muchos pods de aplicaciones que envían tráfico de forma transparente a un ztunnel del nodo, que atiende directamente al servicio de destino para tráfico L4 y utiliza la ruta waypoint opcional cuando el recurso está incorporado a ella.](../../../.gitbook/assets/en-service-mesh-istio-advanced-01-ambient-mode-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-01-ambient-mode-2.html)

**Características**:
- Un ztunnel por nodo
- Funciones L4 proporcionadas de forma predeterminada
- Las funciones L7 requieren un waypoint
- Incorporar Pods ajenos a la malla no exige reiniciarlos; eliminar un sidecar sí

### Tabla de comparación detallada

| Aspecto | Modo Sidecar | Modo Ambient |
|------|-------------|--------------|
| **Método de despliegue** | Inyección de un sidecar en el pod | ztunnel del nodo + waypoint opcional |
| **Cómputo de recursos** | Envoy por Pod + plano de control | ztunnels de los nodos + todas las réplicas de waypoint + plano de control; mida bajo carga |
| **Recreación de Pods** | Necesaria para añadir/eliminar un proxy inyectado | Normalmente no es necesaria para incorporar Pods ajenos a la malla; sí para eliminar un sidecar |
| **Coordinación del inicio** | Ciclo de vida y disponibilidad del proxy/aplicación | Captura del CNI y disponibilidad de ztunnel |
| **Funciones L4** | Compatibles | Compatibles |
| **Funciones L7** | Compatibilidad específica de cada versión | Requieren waypoint y una API compatible; no todas las extensiones son GA |
| **mTLS** | Automático | Automático |
| **Telemetría** | Detallada | Básica (L4), detallada (L7 con waypoint) |
| **Disyuntor** | Compatible | Requiere Waypoint |
| **Reintentos/tiempos de espera** | Compatibles | Requieren Waypoint |
| **Manipulación de cabeceras** | Compatible | Requiere Waypoint |
| **Sobrecarga de rendimiento** | Depende de la carga de trabajo/configuración | Depende de la ruta/identidad/waypoint/carga; compare políticas equivalentes |
| **Ámbito operativo** | Ciclo de vida del proxy por carga de trabajo | Ciclo de vida del nodo/CNI y del waypoint compartido |
| **Preparación para producción** | Madura | GA (Istio 1.24+) |

### Comparación del consumo de recursos {#resource-usage-comparison}

El cálculo de 100 Pods que figura a continuación es un ejemplo hipotético de planificación, no una prueba comparativa oficial. Cuente todas las réplicas de nodo/waypoint y compare requisitos equivalentes de seguridad, telemetría y enrutamiento antes de estimar ahorros de recursos o de facturación.

## Arquitectura {#architecture}


El plano de datos del modo Ambient consta de dos componentes principales: **ztunnel** y **proxy Waypoint**.

### ztunnel (Zero Trust Tunnel)


ztunnel es el componente central del modo Ambient, un **proxy L4 ligero que se ejecuta en el nodo**. Se ejecuta como DaemonSet en nodos Linux aptos y gestiona el tráfico compatible de las cargas de trabajo incorporadas. Esto no incluye todo el tráfico de todos los Pods; para cargas de trabajo con red del host/excluidas y protocolos de aplicación distintos de TCP hay que comprobar la compatibilidad actual.

#### Funcionamiento de ztunnel

1. **Captura del tráfico**: intercepta de forma transparente el tráfico de red del pod mediante reglas netfilter/iptables de Istio CNI dentro del pod y la transferencia del espacio de nombres de red
2. **Aplicación de mTLS**: aplica automáticamente cifrado mTLS mediante identidades basadas en SPIFFE
3. **Equilibrio de carga**: realiza equilibrio de carga L4 entre endpoints
4. **Recopilación de telemetría**: recopila métricas y registros de conexiones
5. **Reenvío**: reenvía el tráfico al ztunnel de destino o a Waypoint

**Pila tecnológica de ztunnel**:
- **Lenguaje**: Rust (alto rendimiento, bajo consumo de memoria)
- **Protocolo**: HBONE (HTTP-Based Overlay Network Environment)
- **Identidad**: identidades de cargas de trabajo SPIFFE; CA de Istiod de forma predeterminada, integración independiente para SPIRE
- **CNI**: integración estrecha con el plugin Istio CNI

#### Función de ztunnel

![Diagrama de una conexión TCP desde un pod de aplicación que pasa por el cifrado mTLS integrado, la recopilación de telemetría L4, la verificación de identidad y el equilibrio de carga L4 de ztunnel antes de llegar al servicio de destino.](../../../.gitbook/assets/en-service-mesh-istio-advanced-01-ambient-mode-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-01-ambient-mode-3.html)

**Características de ztunnel**:
- Escrito en Rust (optimizado para el rendimiento)
- Desplegado como DaemonSet
- Integrado con el plugin CNI
- Redirección netfilter/iptables dentro del pod coordinada con Istio CNI

#### Despliegue de ztunnel

Utilice la instalación y los charts publicados de ambient. El DaemonSet mínimo original omitía los montajes de token/CA/socket y utilizaba ajustes hostNetwork/privileged incorrectos. El chart 1.31 proporciona capacidades específicas y acceso al espacio de nombres del pod; no establece `hostNetwork: true` ni `privileged: true`. No copie ni reduzca los privilegios sin el contexto completo del chart y de la plataforma.

```bash
# Offline inspection; use the same reviewed values as the actual installation
istioctl manifest generate --set profile=ambient > ambient-rendered.yaml
# Inspect a deployed resource if a mesh already exists
kubectl get daemonset ztunnel -n istio-system -o yaml
```

### Proxy Waypoint


Waypoint es un **proxy opcional que se utiliza cuando se necesitan funciones L7**. Un waypoint configurado se sitúa en la ruta del tráfico de los recursos incorporados para proporcionar funciones avanzadas de gestión del tráfico.

#### Características principales de Waypoint

1. **Despliegue selectivo**: se utiliza solo para los servicios que necesitan funciones L7, no para todos
2. **Proxy compartido**: varias cargas de trabajo comparten un único Waypoint (según la incorporación de espacios de nombres/Service/Pod)
3. **Basado en Envoy**: utiliza el mismo proxy Envoy que Sidecar tradicional, con compatibilidad de API L7 específica de la versión
4. **Bajo demanda**: puede añadirse/eliminarse dinámicamente durante la ejecución

#### Unidades de despliegue de Waypoint

Un ServiceAccount proporciona la identidad de la carga de trabajo; etiquetarlo **no** selecciona un waypoint. Utilice `istio.io/use-waypoint` en un Namespace, Service o Pod, con un Gateway cuyo tipo de tráfico `istio.io/waypoint-for` coincida con el tráfico previsto.

| Incorporación | Ámbito |
|---|---|
|Namespace|Selección de waypoint predeterminada para los recursos aptos de ese espacio de nombres|
|Service|Tráfico a ese Service; el tipo de waypoint predeterminado es `service`|
|Pod|Tráfico directo a la carga de trabajo/IP del Pod con un waypoint `workload` o `all`|

Las etiquetas de Deployment por sí solas no etiquetan los Pods existentes; utilice etiquetas de la plantilla del Pod para incorporar cargas de trabajo. Un waypoint `service` no cubre automáticamente el tráfico directo a la IP del Pod.

#### Función de Waypoint


**Características de Waypoint**:
- Se despliega como Gateway y luego se selecciona mediante la incorporación de recursos compatibles
- Basado en el proxy Envoy
- Verifique la compatibilidad de cada API; los parches EnvoyFilter arbitrarios no son una API de waypoint compatible
- Uso selectivo solo para los servicios que lo requieren

#### Despliegue de Waypoint

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: reviews-waypoint
  namespace: ambient-demo
  labels:
    istio.io/waypoint-for: service
spec:
  gatewayClassName: istio-waypoint
  listeners:
  - name: mesh
    port: 15008
    protocol: HBONE
```

La clase predeterminada `istio-waypoint` utiliza Envoy. La disponibilidad general de las funciones principales de ambient no convierte todas las API en GA: la documentación actual describe VirtualService en ambient como Alpha y prohíbe mezclarlo con rutas de Gateway API. Utilice HTTPRoute aquí. EnvoyFilter no es una extensión de waypoint compatible. Las políticas L7 protegen el tráfico que llega al waypoint; exigir que el tráfico lo atraviese también requiere la protección de autorización de ztunnel documentada y una incorporación/disponibilidad correctas.

### Flujo de tráfico completo

El siguiente diagrama integral muestra cómo fluye el tráfico en el modo Ambient **sin Sidecars**:

![Diagrama de secuencia de una solicitud desde una aplicación cliente sin sidecar a través de los ztunnels del cliente y del servidor por la ruta L4 simple y, en una rama opcional, a través de un proxy waypoint para el enrutamiento L7 antes de llegar a la aplicación servidor.](../../../.gitbook/assets/en-service-mesh-istio-advanced-01-ambient-mode-6.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-01-ambient-mode-6.html)

**Análisis del flujo de tráfico**:

1. **Ruta solo L4** (utilizando únicamente ztunnel):
   - Mida la latencia de la ruta bajo una carga representativa
   - mTLS se aplica automáticamente
   - Telemetría básica
   - Adecuada cuando los requisitos reales son únicamente L4

2. **Ruta L7** (ztunnel + Waypoint):
   - Enrutamiento basado en cabeceras
   - Disyuntores
   - Reintentos/tiempos de espera
   - Cuando se necesitan políticas de tráfico complejas

### Protocolo HBONE


**HBONE (HTTP-Based Overlay Network Environment)** es el protocolo de túnel utilizado en el modo Ambient:

- **Basado en HTTP/2**: compatibilidad con la infraestructura existente
- **mTLS integrado**: comunicación segura
- **Multiplexación**: los flujos TCP comparten túneles para el mismo par de identidades de origen/destino
- **Política de red**: HBONE utiliza habitualmente TCP15008; permita explícitamente la ruta de la malla necesaria

![Diagrama del tráfico TCP simple de una aplicación encapsulado en un túnel HBONE HTTP/2 con mTLS por el ztunnel de origen, transportado por la red y desencapsulado de nuevo a TCP simple por el ztunnel de destino antes de llegar a la aplicación de destino.](../../../.gitbook/assets/en-service-mesh-istio-advanced-01-ambient-mode-7.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-01-ambient-mode-7.html)

HBONE en esta guía transporta flujos TCP. Ese túnel no transporta el UDP de la aplicación; la captura/proxy de DNS es una función independiente. El flujo local de la aplicación puede permanecer en texto sin cifrar mientras el transporte de la malla entre proxies está cifrado.

## Instalación y configuración {#installation-and-configuration}

El laboratorio necesita nodos Linux compatibles y los DaemonSets Istio CNI/ztunnel requeridos. EKS Fargate no puede ejecutar estos DaemonSets de nodo; utilice ubicaciones compatibles basadas en EC2 y revise la plataforma real de nodos/CNI. Los [requisitos previos de la plataforma](https://istio.io/latest/docs/ambient/install/platform-prerequisites/) cubren rutas del CNI, permisos y sondas de estado. El uso de enlaces troncales de ENI de Pods de VPC CNI con SecurityGroupPolicy puede requerir el modo de aplicación estándar o sondas exec adecuadas; evalúe las implicaciones para las políticas. GKE, OpenShift, k3s y otras plataformas pueden necesitar ajustes diferentes.

Istio 1.31 admite Kubernetes 1.32–1.36; consulte la [guía de instalación](../01-installation.md) para conocer la compatibilidad con EKS. Gateway API 1.6.0, utilizado a continuación, coincide con la dependencia de Istio 1.31 y el tutorial oficial de ambient. Compruebe la compatibilidad de un paquete existente; no rebaje la versión de un paquete más reciente compatible solo para copiar el ejemplo.

### 1. Instalación de Istio (modo Ambient)

Utilice este comando de instalación únicamente para una malla de laboratorio nueva después de revisar el instalador y los ajustes de la plataforma. Conserve el método de instalación y los valores de una malla existente mediante el procedimiento de migración.

```bash
curl -fsSL https://istio.io/downloadIstio -o download-istio.sh
ISTIO_VERSION=1.31.0 sh download-istio.sh
cd istio-1.31.0
export PATH="$PWD/bin:$PATH"

# Fresh cluster without Gateway API; review an existing bundle separately
if ! kubectl get crd gateways.gateway.networking.k8s.io >/dev/null 2>&1; then
  kubectl apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.0/experimental-install.yaml
fi
kubectl wait --for=condition=Established crd/gateways.gateway.networking.k8s.io --timeout=60s
kubectl get crd httproutes.gateway.networking.k8s.io

# Fresh lab mesh only; include required platform-specific values
istioctl install --set profile=ambient -y
kubectl get pods,daemonsets -n istio-system
```

### 2. Habilitar el modo Ambient y desplegar la aplicación

Utilice un espacio de nombres nuevo y desechable sin anulaciones de inyección de sidecars/revisión. Añadir la etiqueta ambient no convierte los Pods que ya tienen sidecars. El manifiesto Bookinfo completo de la distribución 1.31 proporciona el Service reviews, las etiquetas de versión, los ServiceAccounts y la dependencia ratings que faltaban en el antiguo ejemplo de un solo Deployment; utiliza imágenes Bookinfo 1.20.3.

```bash
kubectl create namespace ambient-demo
kubectl label namespace ambient-demo istio.io/dataplane-mode=ambient
kubectl get namespace ambient-demo -L istio-injection,istio.io/rev,istio.io/dataplane-mode
kubectl apply -n ambient-demo -f samples/bookinfo/platform/kube/bookinfo.yaml
kubectl apply -n ambient-demo -f samples/curl/curl.yaml
for deployment in reviews-v1 reviews-v2 ratings-v1 curl; do
  kubectl rollout status "deployment/$deployment" -n ambient-demo --timeout=120s
done
istioctl ztunnel-config workloads --workload-namespace ambient-demo
```

### 3. Desplegar y seleccionar un waypoint

La CLI actual recibe un nombre de waypoint y un tipo de tráfico, no una opción de incorporación de ServiceAccount. Espere a que esté listo e incorpore explícitamente el Service.

```bash
istioctl waypoint apply --name reviews-waypoint --for service -n ambient-demo --wait
kubectl label service reviews -n ambient-demo istio.io/use-waypoint=reviews-waypoint --overwrite
kubectl get gateways.gateway.networking.k8s.io reviews-waypoint -n ambient-demo
kubectl get service reviews -n ambient-demo --show-labels
```

### 4. Utilizar funciones L7

Cree Services de backend específicos para cada versión y asocie un HTTPRoute al Service reviews incorporado. Esto demuestra el enrutamiento GET/por cabeceras; la cabecera no es una identidad autenticada. No combine el antiguo VirtualService con esta ruta de Gateway API. Las llamadas directas a otro Service/IP de Pod constituyen una ruta independiente.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: reviews-v1
  namespace: ambient-demo
spec:
  selector:
    app: reviews
    version: v1
  ports:
  - name: http
    port: 9080
    targetPort: 9080
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v2
  namespace: ambient-demo
spec:
  selector:
    app: reviews
    version: v2
  ports:
  - name: http
    port: 9080
    targetPort: 9080
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: reviews
  namespace: ambient-demo
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: reviews
    port: 9080
  rules:
  - matches:
    - method: GET
      headers:
      - name: end-user
        type: Exact
        value: jason
    backendRefs:
    - name: reviews-v2
      port: 9080
  - matches:
    - method: GET
    backendRefs:
    - name: reviews-v1
      port: 9080
```

```bash
kubectl describe httproutes.gateway.networking.k8s.io reviews -n ambient-demo
kubectl exec -n ambient-demo deploy/curl -c curl -- \
  curl -sS --max-time 5 -H "end-user: jason" http://reviews:9080/reviews/0
```

Compruebe las condiciones Accepted/ResolvedRefs y el backend seleccionado mediante registros/telemetría. El éxito HTTP por sí solo no demuestra ni mTLS ni el paso obligatorio por el waypoint. La autorización L7 necesita los `targetRefs` apropiados; el paso obligatorio también requiere la protección de autorización de ztunnel documentada. Consulte la [asociación de políticas al waypoint](https://istio.io/latest/docs/ambient/usage/l7-features/).

## Migración {#migration}

### Del modo Sidecar al modo Ambient

La migración es un despliegue de políticas/cargas de trabajo, no un simple cambio de etiqueta. Conserve la revisión instalada, la CA/confianza, los gateways, las opciones del CNI y la configuración declarativa de las cargas de trabajo. Los sidecars existentes tienen prioridad sobre la incorporación a ambient. Prepare el enrutamiento/autorización L7 compatibles y waypoints listos antes de eliminar los sidecars de las cargas de trabajo que requieren esas políticas.

#### Paso 1: instalar los componentes de Ambient

Utilice el método de instalación existente y valores revisados para añadir compatibilidad con ambient en una versión compatible. No sobrescriba una malla gestionada por Helm con un comando independiente `istioctl install --set profile=ambient` sin relación con ella. Renderice/compare la configuración prevista y verifique los agentes de nodo CNI/ztunnel.

#### Paso 2: aplicar al espacio de nombres de prueba

Esta prueba independiente de ambient despliega tanto el cliente como el servidor de la distribución 1.31. El Service httpbin expone 8000 y apunta a 8080.

```bash
kubectl create namespace test-ambient
kubectl label namespace test-ambient istio.io/dataplane-mode=ambient
kubectl apply -n test-ambient -f samples/curl/curl.yaml
kubectl apply -n test-ambient -f samples/httpbin/httpbin.yaml
kubectl rollout status deployment/curl -n test-ambient --timeout=120s
kubectl rollout status deployment/httpbin -n test-ambient --timeout=120s
kubectl exec -n test-ambient deploy/curl -c curl -- \
  curl -sS --max-time 5 http://httpbin:8000/headers
```

#### Paso 3: verificación

La columna HBONE de la carga de trabajo muestra el transporte previsto. Para el tráfico real, inspeccione las identidades de origen/destino esperadas en los registros de ztunnel del nodo correcto, o las métricas TCP con `connection_security_policy="mutual_tls"`. El éxito HTTP por sí solo no demuestra mTLS. La incorporación HBONE no rechaza a todos los clientes en texto sin cifrar; utilice PeerAuthentication STRICT si lo requiere. Consulte la [verificación de mTLS](https://istio.io/latest/docs/ambient/usage/verify-mtls-enabled/).

```bash
istioctl ztunnel-config workloads --workload-namespace test-ambient
source_pod=$(kubectl get pod -n test-ambient -l app=curl -o jsonpath='{.items[0].metadata.name}')
source_node=$(kubectl get pod "$source_pod" -n test-ambient -o jsonpath='{.spec.nodeName}')
ztunnel_pod=$(kubectl get pod -n istio-system -l app=ztunnel \
  --field-selector "spec.nodeName=$source_node" -o jsonpath='{.items[0].metadata.name}')
kubectl logs "$ztunnel_pod" -n istio-system --since=5m
```

#### Paso 4: cambiar las cargas de trabajo seleccionadas

El siguiente ejemplo presupone un espacio de nombres existente e independiente `migration-demo` que contiene únicamente Deployments curl/httpbin revisados, con inyección a nivel de espacio de nombres y requisitos solo L4. Compruebe si hay anulaciones de inyección en las plantillas de Pod o proxies inyectados manualmente; estos comandos no los eliminan. Para cargas de trabajo L7, valide primero la incorporación al waypoint y la traducción de políticas, incluidos `targetRefs` y cualquier protección de paso obligatorio. Planifique la coexistencia de políticas durante la migración; una política L7 basada en selectores aplicada por ztunnel puede denegar el tráfico por seguridad.

```bash
# Reference snapshots, not manifests to blindly reapply with stale server metadata
kubectl get namespace migration-demo -o json > migration-namespace-before.json
kubectl get deployment curl httpbin -n migration-demo -o yaml > migration-workloads-before.yaml

kubectl label namespace migration-demo istio.io/dataplane-mode=ambient --overwrite
kubectl label namespace migration-demo istio-injection- istio.io/rev-
kubectl get namespace migration-demo -L istio-injection,istio.io/rev,istio.io/dataplane-mode
for deployment in curl httpbin; do
  kubectl rollout restart "deployment/$deployment" -n migration-demo
  kubectl rollout status "deployment/$deployment" -n migration-demo --timeout=120s
done

# Check both classic containers and native-sidecar initContainers
kubectl get pods -n migration-demo -o json | jq -r '
  .items[] | [.metadata.name,
    any((.spec.containers + (.spec.initContainers // []))[]; .name == "istio-proxy")] | @tsv'
istioctl ztunnel-config workloads --workload-namespace migration-demo
```

#### Paso 5: validar la ruta de datos elegida

Repita las pruebas de disponibilidad, conectividad, identidad y políticas de las cargas de trabajo indicadas. Para un grupo L7, inspeccione la incorporación real de Namespace/Service/Pod, el tipo de tráfico y la disponibilidad del Gateway y la asociación de rutas/políticas; no cree un waypoint por ServiceAccount. Utilice criterios de detención/reversión específicos de cada carga de trabajo. Esta secuencia de laboratorio no garantiza una producción sin interrupciones.

### Estrategia de reversión

Restaure el modo de inyección registrado y la configuración original de plantillas de Pod/políticas. El código siguiente solo cubre el caso de inyección a nivel de espacio de nombres anterior; la revisión antigua debe seguir existiendo y estar en buen estado. Un grupo con waypoints necesita restaurar sus políticas de incorporación/enrutamiento como parte de la reversión revisada. Elimine únicamente un waypoint identificado específicamente, sin referencias y creado para ese grupo; nunca todos los Gateways de un espacio de nombres.

```bash
original_revision=$(jq -r '.metadata.labels["istio.io/rev"] // ""' migration-namespace-before.json)
original_injection=$(jq -r '.metadata.labels["istio-injection"] // ""' migration-namespace-before.json)

# Restore the recorded namespace-injection mode; do not invent a revision
if [ "$original_injection" = "enabled" ]; then
  kubectl label namespace migration-demo istio-injection=enabled --overwrite
elif [ -n "$original_revision" ]; then
  kubectl label namespace migration-demo "istio.io/rev=$original_revision" --overwrite
else
  echo "No supported namespace-injection mode recorded; restore the original workload configuration." >&2
  exit 1
fi
kubectl label namespace migration-demo istio.io/dataplane-mode-
for deployment in curl httpbin; do
  kubectl rollout restart "deployment/$deployment" -n migration-demo
  kubectl rollout status "deployment/$deployment" -n migration-demo --timeout=120s
done
```

## Comparación del rendimiento {#performance-comparison}

### Resultados de las pruebas comparativas

La URL eliminada de `perf.png` devolvía 404 y no respaldaba la antigua tabla de «pruebas comparativas oficiales». Ninguna fuente establecía sus porcentajes de CPU/memoria por Pod, latencia o rendimiento. Utilice los [resultados de rendimiento publicados](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/) con sus condiciones originales de versión, carga, contenido, hardware y políticas; no presente mediciones históricas como una prueba de la versión actual.

| Medida | Mantener comparables |
|---|---|
|Memoria/CPU|Número de aplicaciones, identidades/conexiones, número de nodos, todas las réplicas de waypoint y políticas equivalentes|
|Latencia P50/P99|Tamaño/tasa de solicitudes, reutilización de conexiones, mTLS, políticas L7, telemetría y condiciones de sobrecarga|
|Rendimiento|La misma capacidad de aplicación/backend y definición de error|
|Coste|Capacidad aprovisionada real, utilización y facturación; reducir las solicitudes/uso de recursos por sí solo no reduce la factura|

### Cálculo del ahorro de recursos

El cálculo original de 100 Pods se conserva a continuación únicamente como un **modelo presupuestario hipotético**. Sus valores de 50MB/0.1CPU y de waypoint son entradas supuestas, no solicitudes/límites recomendados ni costes medidos. Incluya cada réplica de waypoint/ztunnel, la ubicación para alta disponibilidad y los recursos del plano de control en una comparación real. Las réplicas adicionales de waypoint cambian el resultado.

```python
# Hypothetical planning inputs, not measured resource consumption or billing
sidecar_memory = 100 * 50       # MB, decimal
sidecar_cpu = 100 * 0.1        # vCPU
ambient_memory = 10 * 50 + 200  # 10 ztunnels + one assumed waypoint budget
ambient_cpu = 10 * 0.1 + 0.5

memory_saved = sidecar_memory - ambient_memory  # 4300 MB, 86% of assumed baseline
cpu_saved = sidecar_cpu - ambient_cpu           # 8.5 vCPU, 85% of assumed baseline
```

## Casos de uso {#use-cases}

### ¿Cuándo debería elegir el modo Ambient?


**Escenarios recomendados para el modo Ambient**:
- Cientos de microservicios o más
- La optimización del coste de recursos es importante
- La mayoría de los servicios solo necesitan comunicación sencilla
- Solo algunos servicios necesitan enrutamiento avanzado
- Minimizar la complejidad operativa

**Escenarios recomendados para el modo Sidecar**:
- Las API/extensiones requeridas o el comportamiento de la plataforma solo son compatibles con la configuración sidecar elegida
- Necesidad de una solución madura y probada
- Necesidad de control detallado por servicio
- Gestión independiente de la versión del proxy por pod

### 1. Cuando solo se necesitan funciones L4

Para cargas de trabajo TCP existentes compatibles, incorpore un espacio de nombres después de verificar los requisitos de plataforma, políticas y captura. Este Namespace no es un despliegue completo de base de datos; la replicación/almacenamiento/alta disponibilidad de la base de datos deben diseñarse por separado.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: backend
  labels:
    istio.io/dataplane-mode: ambient
```

### 2. Uso selectivo de funciones L7

La demostración selecciona el waypoint reviews listo a nivel de Service. La incorporación del espacio de nombres y de cargas de trabajo directas son ámbitos compatibles independientes; una etiqueta ServiceAccount no es un selector.

```bash
kubectl label service reviews -n ambient-demo istio.io/use-waypoint=reviews-waypoint --overwrite
```

Los requisitos L7 no exigen automáticamente sidecars: compare las API y extensiones compatibles de waypoint con las necesidades reales de la aplicación. A la inversa, la disponibilidad general de las funciones principales no implica paridad de funciones para todas las API avanzadas.

### 3. Migración gradual

Primero inventaríe la inyección y la incorporación, y luego migre un grupo revisado con criterios explícitos de disponibilidad/seguridad/reversión. No etiquete a ciegas todos los espacios de nombres de desarrollo/preproducción/producción ni suponga que el cambio convierte los sidecars existentes.

```bash
kubectl get namespaces -L istio-injection,istio.io/rev,istio.io/dataplane-mode,istio.io/use-waypoint
```

## Solución de problemas {#troubleshooting}

### ztunnel no funciona

```bash
# Check ztunnel status
kubectl get daemonset -n istio-system ztunnel
kubectl logs -n istio-system -l app=ztunnel

# Check CNI
kubectl get daemonset -n istio-system istio-cni-node
kubectl logs -n istio-system -l k8s-app=istio-cni-node
```

### El tráfico no llega al waypoint

```bash
# Check Waypoint status
kubectl get gateways.gateway.networking.k8s.io -n <namespace>

# Check supported enrollment scopes and Gateway readiness
kubectl get namespace <namespace> -L istio.io/use-waypoint
kubectl get services -n <namespace> -L istio.io/use-waypoint
istioctl waypoint list -n <namespace>
istioctl ztunnel-config services

# Check Envoy configuration
istioctl proxy-config clusters <waypoint-pod> -n <namespace>
```

## Referencias

### Documentación oficial actual

- [Descripción general de Ambient](https://istio.io/latest/docs/ambient/overview/)
- [Primeros pasos](https://istio.io/latest/docs/ambient/getting-started/)
- [Redirección de tráfico dentro del pod](https://istio.io/latest/docs/ambient/architecture/traffic-redirection/)
- [HBONE](https://istio.io/latest/docs/ambient/architecture/hbone/)
- [Incorporación a waypoint](https://istio.io/latest/docs/ambient/usage/waypoint/)
- [Compatibilidad de API L7 y asociación de políticas](https://istio.io/latest/docs/ambient/usage/l7-features/)
- [Metodología/resultados de rendimiento](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
- [Código fuente de ztunnel](https://github.com/istio/ztunnel)
- [Comunidad de Istio y acceso a Slack](https://istio.io/latest/get-involved/)

### Presentaciones históricas

Estas páginas de 2022 describen la versión preliminar experimental, no la instalación actual ni los comandos de ServiceAccount-waypoint.

- [Presentación de ambient mesh (2022)](https://istio.io/latest/blog/2022/introducing-ambient-mesh/)
- [Arquitectura de seguridad experimental (2022)](https://istio.io/latest/blog/2022/ambient-security/)
- [Primeros pasos experimentales (2022)](https://istio.io/latest/blog/2022/get-started-ambient/)

### Hitos verificados y límites actuales

| Hito | Evidencia |
|---|---|
|Versión preliminar de 2022|Se anunció una implementación experimental; no era la versión principal de funciones 1.15|
|1.18 Alpha (2023)|Primera versión de Istio que incluía ambient|
|1.22 Beta (2024)|Hito Beta|
|1.24 GA de las funciones principales (2024)|Hito de ztunnel/waypoint/API principales; las funciones individuales mantienen su propio estado|

La [documentación actual de ambient multiclúster](https://istio.io/latest/docs/ambient/install/multicluster/) describe compatibilidad **Beta con múltiples primarios y múltiples redes**. La configuración primario/remoto no es compatible y los despliegues de una sola red no se han probado; los nombres/configuración de waypoints y el ámbito de los servicios deben coordinarse entre clústeres. La antigua hoja de ruta 1.26/1.27 y los ahorros empresariales sin atribución no demuestran un comportamiento compatible ni una reducción de costes garantizada.

## Resumen

Ambient separa el transporte L4 compartido del procesamiento L7 mediante waypoints seleccionados. Puede simplificar la incorporación de cargas de trabajo ajenas a la malla y la gestión del ciclo de vida de los proxies, pero el ahorro de recursos, la conservación de políticas y la disponibilidad requieren mediciones con políticas equivalentes y un plan de migración validado. Tenga en cuenta las restricciones de Linux/CNI/plataforma, la conectividad TCP15008 y el estado de las funciones de cada API.
