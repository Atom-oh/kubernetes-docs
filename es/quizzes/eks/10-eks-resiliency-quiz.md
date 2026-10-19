# Cuestionario sobre alta disponibilidad y resiliencia de Amazon EKS

> **Base de API del ejemplo**: Kubernetes 1.36; las suposiciones de la fuente y del cuestionario coinciden con el [capítulo de origen](../../eks/10-eks-resiliency.md).
> **Última actualización**: 12 de septiembre de 2026

Los ejemplos de configuración y valores numéricos son ilustrativos. En esta revisión no se ejecutaron recursos en la nube, experimentos de caos, cargas de trabajo ni benchmarks. Utiliza un ámbito de pruebas bajo tu control y sustituye los valores de ejemplo antes de desplegar.

Este cuestionario evalúa la comprensión de la alta disponibilidad (HA) de clústeres de Amazon EKS, la resiliencia, los despliegues Multi-AZ, la arquitectura basada en celdas (Cell-Based Architecture), Chaos Engineering, PodDisruptionBudget y Topology Spread Constraints.

## Resumen del cuestionario
- Arquitectura y configuración Multi-AZ
- Patrones de arquitectura basada en celdas
- Principios y herramientas de Chaos Engineering
- Configuración de PodDisruptionBudget (PDB)
- Topology Spread Constraints
- Recuperación ante desastres y failover

## Preguntas de opción múltiple

### 1. ¿Cuál es el principal beneficio de resiliencia de las cargas de trabajo EKS Multi-AZ?

A. Reducción automática de costes
B. Un diseño que puede seguir prestando servicio tras perder una AZ, si se preparan la capacidad, los datos y el enrutamiento
C. Aumentar la latencia como objetivo
D. Eliminar la complejidad operativa

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Un diseño que puede seguir prestando servicio tras perder una AZ, si se preparan la capacidad, los datos y el enrutamiento**

Multi-AZ mejora el diseño de dominios de fallo, pero no garantiza el failover automático de cargas de trabajo/datos ni una disponibilidad del 99,99 %. Tampoco resuelve la pérdida de toda la región. Seis nodos con la misma capacidad distribuidos equitativamente entre tres AZ dejan cuatro tras perder una AZ; hay que inspeccionar la ubicación real de los pods y la capacidad. El siguiente ejemplo es un parámetro de aprovisionamiento, no un comando ejecutado. Kubernetes 1.36 es la base del capítulo: antes de crear recursos, verifica la compatibilidad regional actual de EKS y de la AMI.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: owned-ha-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-multi-az
  instanceType: m5.large
  desiredCapacity: 6
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
```

</details>

### 2. ¿Qué limita un PodDisruptionBudget?

A. El uso de CPU de los pods
B. Las expulsiones voluntarias compatibles, según la disponibilidad de la carga de trabajo
C. Todo el tráfico entre pods
D. Todas las causas de terminación de pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Las expulsiones voluntarias compatibles, según la disponibilidad de la carga de trabajo**

La admisión del PDB limita la Eviction API, que utilizan las operaciones de drain, mantenimiento y autoescalado que cooperan con ella. No protege frente a la eliminación directa de pods, las actualizaciones rolling/reducciones de escala de un Deployment ni los fallos involuntarios. Elige `minAvailable` o `maxUnavailable`; las etiquetas deben coincidir con la carga de trabajo del controlador prevista. Este ejemplo es una alternativa al PDB porcentual siguiente; no son dos políticas que se deban aplicar juntas.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: resilience-demo
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-app
```

</details>

### 3. ¿Qué hace `whenUnsatisfiable: DoNotSchedule`?

A. Programa el pod en cualquier sitio aunque no se cumpla esta restricción
B. Deja un pod nuevo sin programar si ningún nodo apto satisface la restricción de distribución
C. Ignora todas las restricciones de programación
D. Elimina pods existentes para restablecer el equilibrio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Deja un pod nuevo sin programar si ningún nodo apto satisface la restricción de distribución**

Es un filtro de programación, no un rechazo del objeto Pod por parte del servidor de API. `ScheduleAnyway` convierte solo esta regla de distribución en una preferencia; siguen aplicándose los recursos, la afinidad, las taints y las restricciones de almacenamiento. El Deployment completo de abajo usa una imagen de ejemplo y rutas de health específicas de la aplicación; sustitúyelas antes de aplicarlo. `minDomains=2` permite el cálculo N-1 cuando quedan dos zonas aptas, pero no obliga a ocupar inicialmente las tres AZ ni crea capacidad.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
```

</details>

### 4. ¿Cuál NO es un objetivo de una arquitectura basada en celdas?

A. Despliegue y escalado independientes
B. Propagar el fallo de una celda a todo el sistema
C. Una unidad funcional autocontenida
D. Acoplamiento limitado con otras celdas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Propagar el fallo de una celda a todo el sistema**

El aislamiento es una propiedad de diseño que debe implementarse y probarse; no lo crean automáticamente las etiquetas de Namespace. Separa el enrutamiento/límites de admisión, la capacidad y las dependencias de datos; ten en cuenta los nodos, el plano de control, DNS y routers compartidos. Los dos namespaces de abajo solo expresan agrupación. ResourceQuota y NetworkPolicy requieren controles adicionales y no crean dominios físicos de fallo.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-a
  labels:
    cell: a
```
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-b
  labels:
    cell: b
```

</details>

### 5. ¿Qué es una hipótesis de estado estable en Chaos Engineering?

A. Mantener el servicio detenido
B. Una hipótesis medible sobre el comportamiento aceptable antes, durante y después de un fallo
C. Solo el comando que detiene un experimento
D. La carga máxima posible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Una hipótesis medible sobre el comportamiento aceptable antes, durante y después de un fallo**

Define métricas visibles para el usuario, ventanas, comportamiento ante datos ausentes y umbrales de aborto antes del experimento. Los valores originales —p99 < 200 ms, errores < 0,1 %, throughput > 1000 req/s y pods Ready > 99 %— son umbrales ilustrativos, no resultados observados. El porcentaje de pods Ready no equivale a la disponibilidad de solicitudes. `Litmus ChaosExperiment.spec.definition.steadyState` no es un campo del CRD del operador revisado. El JSON siguiente es un plan para revisión humana, no un recurso de Kubernetes.

```json
{
  "scenario": "one bounded test fault",
  "hypothesis": {
    "p99_latency_seconds": "<0.2",
    "error_percentage": "<0.1",
    "request_rate_per_second": ">1000",
    "ready_pod_percentage": ">99"
  },
  "required_observations": [
    "baseline",
    "during fault",
    "recovery",
    "missing data"
  ],
  "abort": "Set an independent measured threshold and recovery owner before execution"
}
```

</details>

### 6. ¿Qué campo de Service expresa la preferencia por la misma zona en la base de Kubernetes 1.36?

A. `spec.trafficDistribution: PreferSameZone`
B. `spec.zoneRouting: enabled`
C. `spec.localOnly: true`
D. `spec.crossZone: disabled`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. `spec.trafficDistribution: PreferSameZone`**

`PreferSameZone`/`PreferSameNode` son GA desde Kubernetes 1.35. Expresan preferencias, no aislamiento estricto ni ahorro garantizado. `PreferClose` es el alias anterior. La anotación antigua `topology-mode=Auto` sigue otra heurística de hints; `topology-aware-hints` es una guía heredada. Revisa la implementación del proxy, los EndpointSlices y la precedencia de la política de tráfico local.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  selector:
    app: web-app
  ports:
  - name: http
    port: 80
    targetPort: http
  trafficDistribution: PreferSameZone
```

</details>

### 7. Con ocho réplicas sanas, sin interrupciones en curso y `maxUnavailable: 25%`, ¿cuál es la tolerancia nominal de expulsiones?

A. 1
B. 2
C. 3
D. 4

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. 2**

`ceil(8×0.25)=2`. Las dos variantes porcentuales del PDB redondean hacia ARRIBA, no hacia abajo: para tres réplicas, `maxUnavailable: 25%` da `ceil(0,75)=1`, mientras que `minAvailable: 75%` exige `ceil(2,25)=3` pods sanos. Los pods no sanos y las interrupciones en curso consumen el presupuesto; esto no garantiza que siempre haya seis pods en ejecución durante cualquier fallo.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb-percentage
  namespace: resilience-demo
spec:
  selector:
    matchLabels:
      app: web-app
  maxUnavailable: 25%
```

</details>

### 8. ¿Qué afirmación es incorrecta para el operador/catálogo de Litmus revisado?

A. `pod-delete` es un fallo del catálogo
B. `node-drain` es distinto de terminar una instancia
C. `pod-network-loss` es un fallo del catálogo
D. `cluster-delete` es un fallo estándar que elimina todo un clúster EKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. `cluster-delete` es un fallo estándar que elimina todo un clúster EKS**

El catálogo revisado contiene exactamente esos nombres de fallos de pod/nodo; no contiene el supuesto fallo `cluster-delete`. No des por válidos identificadores genéricos como `network-loss` o `ec2-terminate`. El catálogo AWS actual incluye `aws-az-chaos`, `ebs-loss-by-id/by-tag` y `ec2-stop-by-id/by-tag`. Revisa la definición real del fallo, los permisos RBAC requeridos y la imagen del runner. Instalar un operador no instala todos los experimentos; el operador 3.31.0 no define `ChaosHub` ni `ChaosSchedule`.

</details>

### 9. ¿Quién gestiona la disponibilidad regional del plano de control de EKS?

A. Los usuarios colocan manualmente los servidores de API
B. AWS gestiona el plano de control regional entre tres AZ
C. Siempre es un plano de control de una sola AZ
D. Los usuarios deben implementar el failover de etcd en EKS administrado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. AWS gestiona el plano de control regional entre tres AZ**

EKS regional distribuye su plano de control administrado entre tres AZ; el requisito del cliente de usar subredes en al menos dos AZ es distinto. El plano de control estándar tiene un SLA mensual de endpoint del 99,95 % y el plano de control aprovisionado del 99,99 %, con condiciones de créditos de servicio e intervalos de medición diferentes. No garantizan la disponibilidad de la aplicación ni proporcionan una copia de seguridad administrada por el cliente de las cargas de trabajo o PV. El cliente sigue siendo responsable de la colocación del plano de datos/cargas de trabajo, la recuperación de datos y la medición del SLO.

</details>

### 10. Con `DoNotSchedule`, ¿qué limita `maxSkew` al colocar un pod?

A. El número total máximo de pods
B. El recuento del dominio candidato comparado con el mínimo global
C. El número mínimo de nodos
D. El máximo de pods por nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. El recuento del dominio candidato comparado con el mínimo global**

Los dominios aptos y `minDomains` determinan el mínimo global; si quedan menos dominios aptos que `minDomains`, el mínimo es cero. Un recuento 2/2 en dos zonas aptas puede bloquear los reemplazos cuando `minDomains=3` y `maxSkew=1`. Una distribución 2/2/2 es un ejemplo sano, no una invariante permanente; 3/2/1 ilustra un skew de 2, mientras que añadir pods a un desequilibrio 4/1/1 puede fallar. Los pods existentes no se reequilibran ni se eliminan automáticamente.

</details>

## Preguntas de respuesta corta

### 1. ¿Qué campo debe usar un Service de Kubernetes 1.36 para preferir la misma zona?

<details>
<summary>Mostrar respuesta</summary>

`spec.trafficDistribution: PreferSameZone`. Es una preferencia; mide el enrutamiento y el coste. La anotación heredada `topology-aware-hints` no es la respuesta actual. Revisa las políticas de tráfico local y la implementación que sirve realmente este Service.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  selector:
    app: web-app
  ports:
  - name: http
    port: 80
    targetPort: http
  trafficDistribution: PreferSameZone
```

</details>

### 2. Indica tres operaciones que pueden usar la expulsión voluntaria compatible con PDB y distingue los casos que la omiten.

<details>
<summary>Mostrar respuesta</summary>

Ejemplos: `kubectl drain` mediante Eviction, un flujo de actualización que drene mediante Eviction y la reducción de escala de un autoescalador de nodos cooperante. Verifica la implementación específica y las opciones `force`. Las actualizaciones de Deployment/StatefulSet, `kubectl delete pod` directo y algunos cambios de capacidad deseada de la nube no utilizan la admisión del PDB del mismo modo. `cordon` por sí solo impide nueva programación, pero no expulsa los pods existentes. Un fallo de hardware, un kernel panic y un OOM no se pueden evitar con PDB.

</details>

### 3. Describe cuatro controles para que un experimento de caos sea útil.

<details>
<summary>Mostrar respuesta</summary>

Define una hipótesis de estado estable medible; elige un fallo realista y acotado; usa un entorno representativo y una autorización explícita para producción si esta fuera necesaria; limita el radio de impacto con observación independiente, umbrales de parada y una persona responsable de la recuperación. La automatización y el análisis posterior mejoran la repetibilidad, pero ninguno hace obligatorio probar en producción ni restaura datos automáticamente.

</details>

### 4. ¿Por qué usar tres AZ para esta carga de trabajo y es ese un mínimo del grupo de nodos de EKS?

<details>
<summary>Mostrar respuesta</summary>

Tres zonas con la misma capacidad dejan dos tercios de la capacidad existente tras perder una zona, si las cargas de trabajo y sus dependencias también están distribuidas. Es una elección de diseño, no un mínimo universal de la API del grupo de nodos. Las subredes del clúster EKS requieren al menos dos AZ; su plano de control regional administrado abarca tres. Las AZ de los grupos de nodos del cliente no determinan dónde se ubica etcd administrado por EKS. Elige zonas disponibles para la región, los tipos de instancia, el almacenamiento y las restricciones de las cargas de trabajo.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: owned-ha-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-multi-az
  instanceType: m5.large
  desiredCapacity: 6
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
```

</details>

### 5. ¿Cómo debe una capa de enrutamiento asignar el tráfico a una celda?

<details>
<summary>Mostrar respuesta</summary>

Usa una identidad de tenant de confianza y un hash estable, una asignación explícita o una asignación regional. El router debe validar la autorización, la capacidad y la ubicación de los datos; no confíes en un `x-cell-id` arbitrario del cliente como autorización del tenant. El ejemplo del mesh presupone Services de destino registrados y políticas compatibles. Los ID de celda desconocidos/no confiables necesitan una política explícita de rechazo o valor predeterminado. Dos namespaces o un ConfigMap de enrutamiento no implementan por sí solos el aislamiento ni el failover.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: cell-routing-example
  namespace: resilience-demo
spec:
  hosts:
  - cell-router.resilience-demo.svc.cluster.local
  http:
  - match:
    - headers:
        x-cell-id:
          exact: cell-a
    route:
    - destination:
        host: app.cell-a.svc.cluster.local
  - match:
    - headers:
        x-cell-id:
          exact: cell-b
    route:
    - destination:
        host: app.cell-b.svc.cluster.local
```

</details>

## Ejercicios prácticos

### 1. Escribe `api-server-pdb` para `app=api-server`, de modo que las expulsiones compatibles con PDB requieran tres réplicas disponibles.

<details>
<summary>Mostrar respuesta</summary>

Este es el nombre de una etiqueta de tu aplicación, no el servidor de API de Kubernetes administrado por AWS. El namespace y la carga de trabajo del controlador con la etiqueta coincidente deben existir previamente. Con cinco réplicas Ready y sin interrupciones en curso, el presupuesto ilustrativo sería dos; con tres réplicas no habría tolerancia a expulsiones saludables. Inspecciona el estado real en lugar de suponer que se observó la salida de ejemplo.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-server-pdb
  namespace: resilience-demo
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app: api-server
```
```bash
# Prerequisite: the owned test namespace and matching application already exist.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods -l app=api-server
# MUTATION: apply only this reviewed PDB file.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f api-server-pdb.yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo describe pdb api-server-pdb
```

</details>

### 2. Escribe `web-frontend` con seis réplicas y una regla de distribución por zona; explica la compensación al perder una AZ.

<details>
<summary>Mostrar respuesta</summary>

El ejemplo completo usa `maxSkew=1` y `minDomains=2` para el escenario N-1. La distribución inicial entre tres zonas y la capacidad de las zonas supervivientes deben verificarse por separado. No reequilibra automáticamente ni mueve los PVC zonales. Sustituye la imagen de ejemplo y las rutas de health por las de la aplicación; los recursos son ilustrativos. Después de una aplicación controlada, usa el informe de Python siguiente en vez de suponer que cada pod tiene nombre de nodo/etiqueta de zona.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  namespace: resilience-demo
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-frontend
```
```bash
# MUTATION: replace the image/health contract and review this exact file first.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f web-frontend.yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout status deployment/web-frontend --timeout=5m
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods -l app=web-frontend -o json > frontend-pods.json
kubectl --context "$KUBE_CONTEXT" get nodes -o json > frontend-nodes.json
```
```python
import collections, json
from pathlib import Path
pods = json.loads(Path("frontend-pods.json").read_text())["items"]
nodes = json.loads(Path("frontend-nodes.json").read_text())["items"]
zones = {n["metadata"]["name"]: n["metadata"].get("labels", {}).get("topology.kubernetes.io/zone", "<unlabeled>") for n in nodes}
counts, ready = collections.Counter(), collections.Counter()
for pod in pods:
    if pod["metadata"].get("deletionTimestamp"):
        continue
    node = pod.get("spec", {}).get("nodeName")
    zone = zones.get(node, "<unknown-node>") if node else "<unscheduled>"
    counts[zone] += 1
    if any(c.get("type") == "Ready" and c.get("status") == "True" for c in pod.get("status", {}).get("conditions", [])):
        ready[zone] += 1
print(json.dumps({"activePodsByZone": dict(counts), "readyPodsByZone": dict(ready)}, indent=2))
```

</details>

### 3. Prepara un experimento de eliminación de pods de Litmus detenido, de 30 segundos y limitado a un pod de prueba revisado.

<details>
<summary>Mostrar respuesta</summary>

Usa una carga de prueba propia del servicio de pagos en `resilience-demo`, no un selector amplio de producción. Sustituye `TARGET_PODS` por un nombre actual exacto tras comprobar su UID y propietario. El operador, el `ChaosExperiment` `pod-delete`, las imágenes de runner/helper verificadas y el RBAC acotado deben estar revisados previamente. La duración/el intervalo pueden provocar intentos repetidos de eliminación; esto no demuestra exactamente una eliminación en 30 segundos. Si necesitas una única acción de eliminación seleccionada, usa el ejemplo `COUNT(1)` de FIS del capítulo, con sus requisitos IAM/RBAC independientes. Aquí no se ejecuta ningún fallo.

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: payment-pod-delete-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=payment-service,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: pod-delete-sa
  experiments:
  - name: pod-delete
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '30'
        - name: CHAOS_INTERVAL
          value: '10'
        - name: FORCE
          value: 'false'
        - name: TARGET_PODS
          value: REPLACE_WITH_ONE_REVIEWED_POD_NAME
        - name: PODS_AFFECTED_PERC
          value: '100'
```
```bash
# Read-only: resolve an exact current Pod name/UID before filling TARGET_PODS.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods \
  -l 'app=payment-service,experiment-approved=true' -o wide
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosexperiment pod-delete
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get serviceaccount pod-delete-sa
# MUTATION: this reviewed file must still have engineState: stop.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f payment-pod-delete-review.yaml
```
```bash
# Read-only observation; no experiment is started by these commands.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosengine payment-pod-delete-review -o yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosresult
```

</details>

## Preguntas avanzadas

### 1. Diseña una carga de trabajo de servicios financieros con un SLO de disponibilidad del 99,99 % e identifica qué se debe demostrar.

<details>
<summary>Mostrar respuesta</summary>

Un objetivo del 99,99 % es un SLO de la carga de trabajo, no una garantía que generen los recursos siguientes. Para una ventana temporal de 365 días, el presupuesto aritmético es 52,56 minutos al año (la aproximación anterior era «unos 52 minutos»); el SLA de EKS es un compromiso distinto de créditos de servicio mensual. La disponibilidad basada en solicitudes usa otro denominador. Define cada recorrido de usuario crítico, los fallos parciales, la ventana de medición, RTO/RPO y las alertas.

Prepara regiones principal/secundaria con datos utilizables de forma independiente, identidad, DNS, enrutamiento, observabilidad y capacidad. Prueba la demora de replicación, la promoción/conflictos de escritura y quién es responsable de la recuperación; ni Multi-AZ ni Active-Active garantizan por sí solos la pérdida cero de datos. Los siguientes valores originales de recursos son ilustraciones de diseño, no capacidad medida ni un despliegue ejecutado.

#### Parámetros de nodos Multi-AZ y recursos de celdas

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: finance-primary-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-critical
  instanceType: m5.xlarge
  desiredCapacity: 9
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
  labels:
    criticality: high
```
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: finance-cell
  labels:
    cell: finance
```
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-quota
  namespace: finance-cell
spec:
  hard:
    requests.cpu: '100'
    requests.memory: 200Gi
    limits.cpu: '200'
    limits.memory: 400Gi
```
La cuota no reserva nodos ni aísla dependencias compartidas. Añade los límites de router/red/datos revisados en el capítulo. Para la anti-afinidad estricta por hostname siguiente, nueve réplicas requieren nueve nodos aptos con `criticality=high`; escalar a 30 exige capacidad de nodo equivalente. La colocación estricta puede dejar pods en Pending deliberadamente. Sustituye la imagen de ejemplo y el contrato de health, y confirma primero la disponibilidad de la región/versión/instancia elegida.

#### Colocación y presupuesto de expulsión

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-api
  namespace: finance-cell
spec:
  replicas: 9
  selector:
    matchLabels:
      app: payment-api
  template:
    metadata:
      labels:
        app: payment-api
        tier: critical
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: payment-api
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: payment-api
      nodeSelector:
        criticality: high
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: payment-api
            topologyKey: kubernetes.io/hostname
```
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-service-pdb
  namespace: finance-cell
spec:
  minAvailable: 80%
  selector:
    matchLabels:
      app: payment-api
```
Con nueve réplicas sanas, `minAvailable: 80%` redondea hacia arriba a ocho; antes de otras deducciones, el presupuesto nominal es una expulsión saludable. No limita todos los rollouts, reducciones de escala de la nube ni fallos de AZ. `minDomains=2` permite el cálculo de colocación N-1 descrito, no la evacuación automática ni la migración de datos.

#### HPA con un objetivo real y contrato de métricas

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: critical-service-hpa
  namespace: finance-cell
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment-api
  minReplicas: 9
  maxReplicas: 30
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```
La métrica de recursos de CPU necesita Metrics Server operativo y solicitudes de CPU en los contenedores pertinentes. Aumentar las réplicas no arregla una fuga, una base de datos agotada ni una restricción de volumen zonal. Mantén coherente quién es dueño del campo de réplicas/GitOps/HPA.

Para los game days periódicos, usa un scheduler propio o un flujo aprobado que invoque experimentos individuales revisados, registre su destino/ID exacto, vigile señales de aborto y compruebe la restauración antes del siguiente fallo. El fragmento antiguo `ChaosSchedule` de 2024 estaba obsoleto y no era un CRD de Litmus 3.31.0; cambiarle solo las fechas no lo corregiría. Una afirmación del 99,99 % requiere evidencia SLI y ejercicios reales, no solo un calendario semanal.

</details>

### 2. Planifica un escenario de tráfico de Black Friday 10×, con escalado anticipado y recuperación de fallos acotada.

<details>
<summary>Mostrar respuesta</summary>

10× es un objetivo de prueba, no un resultado medido. Modela la mezcla de solicitudes, CPU/memoria, calentamiento, conexiones, colas, base de datos y cuotas de servicios externos. Presupuesta la pérdida de una AZ mientras se atiende ese tráfico objetivo. Los límites de NodePool son **topes de aprovisionamiento, no capacidad precreada ni reservada**. El `EC2NodeClass`, AMI/IAM, subredes/IP y tipos de instancia seleccionados deben admitir este diseño. Un presupuesto de interrupciones voluntarias de cero no bloquea interrupciones, reparaciones ni toda terminación forzada.

#### Parámetros de capacidad que hay que validar

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: blackfriday-example
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: reviewed-test-class
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.2xlarge
        - m5.4xlarge
        - c5.2xlarge
        - c5.4xlarge
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - us-west-2a
        - us-west-2b
        - us-west-2c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
  limits:
    cpu: 2000
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
    - nodes: '0'
```
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: product-catalog-hpa
  namespace: resilience-demo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: product-catalog
  minReplicas: 50
  maxReplicas: 500
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  behavior:
    scaleDown:
      selectPolicy: Disabled
```
Los valores normales originales de 10/mínimo 50/máximo 500 son ilustrativos: multiplicar por cinco el mínimo de réplicas no demuestra diez veces más throughput. Este HPA presupone un Deployment `product-catalog` existente, solicitudes de CPU y métricas operativas. Deshabilitar `scaleDown` impide que HPA reduzca la escala, pero permite aumentarla; no pausa por completo HPA. Antes del evento, verifica los pods Ready, endpoints sanos y la capacidad/headroom de nodos ya disponible; después, restaura la política normal revisada.

Antes del evento, ejecuta los experimentos revisados por separado en condiciones de prueba representativas: un fallo de pod acotado, un escenario controlado de desplazamiento zonal/red y latencia de dependencia. No describas `node-drain` como una interrupción de toda una AZ, no pases un selector de etiquetas como `TARGET_PODS` ni combines fallos no revisados en un engine de producción activo. Registra resultados, incluidos fallos/datos ausentes y la restauración real.

#### Plan de respuesta al escenario

| Escenario | Evidencia | Respuesta revisada |
| --- | --- | --- |
| Incidencia de AZ | Salud de endpoints/clientes, estado de nodos, disponibilidad de datos | Cambio de tráfico ARC/manual autorizado y capacidad superviviente demostrada; Topology Spread no evacúa pods por sí solo |
| Latencia de base de datos | Métricas de consultas/conexiones/replicación | Limitar reintentos/concurrencia; seguir el runbook/promoción del escritor si hace falta, no cambiar a ciegas a cualquier réplica de lectura |
| OOM/crecimiento de memoria | Límite, working set, reinicios y evidencia de la aplicación | Diagnosticar/corregir recursos o aplicación; HPA basado en CPU no repara automáticamente un OOM |
| Pico de tráfico | Mezcla de solicitudes, backlog, saturación y errores de cliente | Control de admisión/tasa y escalado probado; usar caché solo para datos con semántica pública/personalización segura |

#### Circuit breaker y métricas

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: product-catalog-circuit-breaker
  namespace: resilience-demo
spec:
  host: product-catalog.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 1000
        http2MaxRequests: 2000
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 30
      splitExternalLocalOriginErrors: true
```
Los límites de pool del proxy y la detección de outliers no reservan capacidad de backend. Ajusta conforme a las reglas de timeout/idempotencia del capítulo fuente. Las consultas siguientes requieren **instrumentación de tu aplicación** que exponga los contadores/métricas de histograma clásico indicados y las etiquetas job/namespace/status, además de kube-state-metrics. Inicializa las series de estado pertinentes y verifica la cobertura de scraping; EKS no proporciona estas métricas automáticamente. Un denominador de solicitudes cero/sin muestras no es evidencia disponible, no equivale a un éxito del 100 %. El indicador de pods excluye deliberadamente los pods completados/en eliminación y no es el SLI de la aplicación.

Tasa de solicitudes

```promql
sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m]))
```

Porcentaje de errores 5xx

```promql
100 * sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo",status=~"5.."}[5m]))
/ sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m]))
and on() (sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m])) > 0)
```

p99 de histograma clásico en segundos

```promql
histogram_quantile(0.99,
  sum by (le) (rate(http_request_duration_seconds_bucket{job="product-catalog",namespace="resilience-demo"}[5m]))
)
```

Porcentaje de pods Ready del namespace de prueba activo; no es disponibilidad de solicitudes

```promql
100 *
sum(
  kube_pod_status_ready{namespace="resilience-demo",condition="true"}
  and on (namespace,pod)
  (kube_pod_status_phase{namespace="resilience-demo",phase=~"Pending|Running|Unknown"} == 1)
  unless on (namespace,pod) kube_pod_deletion_timestamp{namespace="resilience-demo"}
)
/
count(
  (kube_pod_status_phase{namespace="resilience-demo",phase=~"Pending|Running|Unknown"} == 1)
  unless on (namespace,pod) kube_pod_deletion_timestamp{namespace="resilience-demo"}
)
```

#### Rollback de la carga de trabajo y controles revisados por separado

```bash
# MUTATION: workload revision rollback only, after data/schema and GitOps review.
set -euo pipefail
: "${KUBE_CONTEXT:?Set the verified owned context}"
: "${REVIEWED_REVISION:?Set an inspected compatible Deployment revision}"
[[ "$REVIEWED_REVISION" =~ ^[1-9][0-9]*$ ]]
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout history deployment/product-catalog
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout undo deployment/product-catalog \
  --to-revision="$REVIEWED_REVISION"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout status deployment/product-catalog --timeout=5m
```
Coordina la propiedad de GitOps y HPA antes del rollback; deshacer un rollout no revierte una base de datos/PVC ni degrada el plano de control de EKS. Subir `minReplicas` a 100 no pausa HPA. Si hace falta, utiliza la política de comportamiento de HPA y un plan de restauración registrado. Las feature flags requieren tu API/SDK de gestión autenticada y real y una flag objetivo auditada; no se presupone una URL genérica de desactivación sin autenticación.

Para CloudFront, recupera primero la configuración completa existente y su ETag en un archivo privado:

```bash
# Read-only preparation; output can include sensitive origin configuration.
set -euo pipefail
umask 077
: "${CF_DIST_ID:?Set the exact owned CloudFront distribution ID}"
test ! -e cloudfront-current-private.json
aws cloudfront get-distribution-config --id "$CF_DIST_ID" > cloudfront-current-private.json
```
Revisa la política de caché, cookies, autorización y contenido personalizado. Un cambio requiere el `DistributionConfig` completo y válido y el ETag `IfMatch` correspondiente; `update-distribution` no tiene un atajo `--default-cache-behavior`. Prepara y revisa la configuración completa por separado, espera el despliegue y conserva un plan de restauración. No apliques un TTL general de 24 horas a respuestas transaccionales o específicas de usuario.

El calendario original de pruebas básicas D-14, game day D-7, verificación/escalado previo final D-3 y monitorización D-Day sigue siendo una ilustración de planificación; aquí no se han verificado resultados de ejecución.

[API de actualización de CloudFront](https://docs.aws.amazon.com/cli/latest/reference/cloudfront/update-distribution.html) · [Comportamiento de HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/) · [Métricas de pods de kube-state-metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)

</details>
