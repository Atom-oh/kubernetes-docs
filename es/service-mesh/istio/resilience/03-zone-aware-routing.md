# Enrutamiento según la zona

> **Última actualización**: 11 de septiembre de 2026 · Istio 1.31. Este capítulo utiliza `localityLbSetting` para ponderar el tráfico por ubicación y configurar la conmutación ante fallos mediante prioridades. La API independiente `zoneAwareLbSetting` tiene otros requisitos y un comportamiento distinto; no combine los campos de ambas. Los ejemplos presuponen una malla con sidecars y presentan políticas alternativas para un mismo host. No se han desplegado ni sometido a pruebas de carga.

El enrutamiento según la zona optimiza el tráfico teniendo en cuenta las zonas de disponibilidad de Kubernetes. Al dar preferencia a la comunicación dentro de una misma AZ, reduce la latencia y los costes de transferencia entre zonas.

## Índice

1. [Descripción general](#overview)
2. [Funcionamiento](#how-it-works)
3. [Configuración básica](#basic-configuration)
4. [Configuración avanzada](#advanced-configuration)
5. [Configuración en AWS EKS](#configuration-on-aws-eks)
6. [Ejemplos prácticos](#practical-examples)
7. [Monitorización](#monitoring)
8. [Solución de problemas](#troubleshooting)

## Descripción general {#overview}

El enrutamiento según la zona ofrece las siguientes ventajas:


### Ventajas

1. **Menor latencia**: Reducir la latencia de red mediante la comunicación dentro de una misma AZ.
2. **Ahorro de costes**: Reducir la transferencia de datos entre AZ.
   - Calcule los bytes realmente facturables, la dirección del tráfico, la región y la ruta por los servicios de AWS. No existe una tarifa universal por GB aplicable a todas las solicitudes de EKS.
3. **Apoyo a la disponibilidad**: Requiere endpoints en buen estado y accesibles, además de capacidad de reserva en otras zonas.
4. **Optimización del rendimiento**: Aprovechar mejor el ancho de banda de la red.

## Funcionamiento {#how-it-works}

### Algoritmo de equilibrio de carga por localidad

Una política `distribute` con proporciones 80/10/10 envía tráfico normal a las tres zonas mientras estén en buen estado. Los dos tramos del 10% no son reservas que se activen únicamente ante un fallo. La conmutación por ubicación basada en prioridades es un modo distinto. La ponderación según el estado y la capacidad puede desviar tráfico antes de que fallen todos los hosts locales. Las letras de las AZ no indican proximidad física ni latencia.



### Jerarquía de localidad

Istio utiliza la siguiente jerarquía de ubicación:

```
Region/Zone/SubZone

Example:
us-east-1/us-east-1a/*
us-east-1/us-east-1b/*
us-west-2/us-west-2a/*
```

**Prioridades de localidad predeterminadas** (cuando está activa la conmutación por prioridades):

1. Misma región, zona y subzona.
2. Misma región y zona, pero distinta subzona.
3. Misma región, pero distinta zona.
4. Otras regiones, ordenadas según la política de conmutación regional, cuando exista una configurada.

### Funcionamiento sin etiquetas de AZ en los Pods

**Importante**: los propios Pods no necesitan etiquetas de AZ. Istio lee las **etiquetas de topología del nodo** para determinar automáticamente la localidad del Pod.

#### Funcionamiento

![El descubrimiento de servicios de Istiod lee la etiqueta topology.kubernetes.io/zone de cada Node para determinar la localidad del Pod sin necesitar etiquetas de zona en los propios pods, y luego genera EDS y envía esa información de localidad al proxy Envoy.](../../../.gitbook/assets/en-service-mesh-istio-resilience-03-zone-aware-routing-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-resilience-03-zone-aware-routing-2.html)

#### Proceso paso a paso

**Paso 1: Istiod recopila información de los Pods**

```bash
# Istiod queries Pod information via Kubernetes API
kubectl get pod <pod-name> -o json | jq '.spec.nodeName'
# Output: "ip-10-0-1-10.ec2.internal"
```

**Paso 2: consultar las etiquetas de topología del nodo que ejecuta el Pod**

```bash
# Query Node info using Pod's nodeName
kubectl get node ip-10-0-1-10.ec2.internal -o json | \
  jq '.metadata.labels."topology.kubernetes.io/zone"'
# Output: "us-east-1a"
```

**Paso 3: generar EDS (servicio de descubrimiento de endpoints)**

El siguiente ClusterLoadAssignment es una representación esquemática, no una salida capturada de la CLI. La información EDS real también incluye los pesos y las prioridades generados, junto con el estado de los endpoints:

```json
{
  "cluster_name": "outbound|8080||myapp.default.svc.cluster.local",
  "endpoints": [
    {
      "locality": {
        "region": "us-east-1",
        "zone": "us-east-1a"
      },
      "lb_endpoints": [
        {
          "endpoint": {
            "address": {
              "socket_address": {
                "address": "10.0.1.10",
                "port_value": 8080
              }
            }
          }
        }
      ]
    },
    {
      "locality": {
        "region": "us-east-1",
        "zone": "us-east-1b"
      },
      "lb_endpoints": [
        {
          "endpoint": {
            "address": {
              "socket_address": {
                "address": "10.0.2.20",
                "port_value": 8080
              }
            }
          }
        }
      ]
    }
  ]
}
```

**Paso 4: Envoy realiza el enrutamiento basado en localidad**

Para decidir el enrutamiento, Envoy compara su propia ubicación con la información EDS recibida:

```bash
# Check Envoy's Locality (based on node it's running on)
istioctl proxy-config bootstrap <pod-name> -n default -o json | \
  jq '.bootstrap.node.locality'

# Output:
# {
#   "region": "us-east-1",
#   "zone": "us-east-1a"
# }
```

#### Método de verificación

```bash
# 1. Check which Node the Pod is running on
kubectl get pod <pod-name> -o wide
# NAME        READY   STATUS    NODE
# myapp-abc   2/2     Running   ip-10-0-1-10.ec2.internal

# 2. Check the Node's Zone label
kubectl get node ip-10-0-1-10.ec2.internal \
  -o jsonpath='{.metadata.labels.topology\.kubernetes\.io/zone}'
# Output: us-east-1a

# 3. Check Endpoint Locality recognized by Envoy
istioctl proxy-config all <pod-name> -n default -o json | \
  jq '.configs[] | select(.["@type"] | endswith("EndpointsConfigDump")) |
      ((.dynamic_endpoint_configs // .dynamicEndpointConfigs // [])[] |
       (.endpoint_config // .endpointConfig)) |
      select((.cluster_name // .clusterName) == "outbound|8080||myapp.default.svc.cluster.local") |
      .endpoints[] | {locality, priority}'
```

#### Por qué no se necesitan etiquetas de Pod

Un Pod conserva el nodo que se le ha asignado durante toda la vida de su UID. Un controlador puede reemplazarlo por otro Pod con un UID nuevo en un nodo diferente. Istiod relaciona los endpoints con la topología de los nodos mediante el descubrimiento de Kubernetes; este mecanismo normal de enrutamiento no requiere etiquetas de zona adicionales en los Pods. Los mecanismos de seguimiento y caché de la API y la configuración de los proxies convergen de forma asíncrona. Compruebe la configuración efectiva, en lugar de dar por supuesto que los cambios se aplican inmediatamente. Añadir información personalizada a la telemetría es una tarea independiente.

```yaml
# Relevant existing Node metadata; do not overwrite actual cloud topology
metadata:
  labels:
    topology.kubernetes.io/zone: us-east-1a
    topology.kubernetes.io/region: us-east-1
```

#### Configuración automática de AWS EKS

AWS EKS añade automáticamente etiquetas de topología al crear nodos:

```bash
# Check EKS nodes
kubectl get nodes -L topology.kubernetes.io/zone,topology.kubernetes.io/region

# Example output:
# NAME                           ZONE         REGION
# ip-10-0-1-10.ec2.internal      us-east-1a   us-east-1
# ip-10-0-2-20.ec2.internal      us-east-1b   us-east-1
# ip-10-0-3-30.ec2.internal      us-east-1c   us-east-1
```

En los nodos sobre EC2, la integración con la nube y la configuración de arranque utilizan la información de ubicación de las instancias de AWS. `spec.providerID` identifica la instancia del proveedor, pero su valor completo no es un ID de instancia EC2. El acceso a IMDS desde una carga de trabajo puede estar restringido, e IMDSv2 requiere un token. Cuando corresponda, utilice el diagnóstico de EC2 de solo lectura que aparece más adelante. Los nodos Fargate necesitan diagnósticos propios de esa plataforma.

## Configuración básica {#basic-configuration}

### 1. Establecer etiquetas de topología en nodos de Kubernetes

AWS EKS añade automáticamente las siguientes etiquetas:

```yaml
topology.kubernetes.io/region: us-east-1
topology.kubernetes.io/zone: us-east-1a
```

**Verificación**:
```bash
kubectl get nodes -L topology.kubernetes.io/zone -L topology.kubernetes.io/region

# Example output:
# NAME                          ZONE         REGION
# ip-10-0-1-10.ec2.internal     us-east-1a   us-east-1
# ip-10-0-2-20.ec2.internal     us-east-1b   us-east-1
# ip-10-0-3-30.ec2.internal     us-east-1c   us-east-1
```

### 2. Habilitar el enrutamiento según la zona en DestinationRule

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

El ejemplo básico combina prioridades por ubicación con detección de endpoints que fallan. Su límite de expulsión del 100% permite excluir todos los endpoints en mal estado. Si no queda capacidad disponible, puede producirse el error «no healthy upstream». Es un ejemplo de configuración de conmutación ante fallos, no un límite seguro para cualquier entorno.

### 3. Configurar proporciones de distribución

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 10
        - from: us-east-1/us-east-1b/*
          to:
            us-east-1/us-east-1b/*: 80
            us-east-1/us-east-1a/*: 10
            us-east-1/us-east-1c/*: 10
        - from: us-east-1/us-east-1c/*
          to:
            us-east-1/us-east-1c/*: 80
            us-east-1/us-east-1a/*: 10
            us-east-1/us-east-1b/*: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

## Configuración avanzada {#advanced-configuration}

### Configuración de conmutación por error

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-failover
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

En `localityLbSetting`, `failoverPriority` puede comparar los metadatos de región y zona, como en el ejemplo anterior. En cambio, `failover` recibe **nombres de regiones**, no rutas `region/zone`, y no define un orden de zonas A→B→C. Elija una sola opción entre `distribute`, `failover` y `failoverPriority`. Estas reglas son distintas de las de la API independiente `zoneAwareLbSetting`.

### Uso con detección de endpoints que fallan

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-resilient
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 20
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

`minHealthPercent` establece el umbral de pánico del conjunto de endpoints, que puede permitir su uso ante fallos; no representa una capacidad mínima disponible por zona. El valor cero deshabilita ese umbral. La distribución ponderada 80/20 sigue enviando tráfico a ambas zonas mientras estén en buen estado. No mantiene una de ellas como reserva.

### Configuración multirregión

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-multi-region
  namespace: default
spec:
  host: myapp.default.svc.cluster.local
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/*
          to:
            us-east-1/*: 90
            us-west-2/*: 10
        - from: us-west-2/*
          to:
            us-west-2/*: 90
            us-east-1/*: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

El ejemplo 90/10 solo distribuye tráfico. Requiere una configuración real de clústeres y redes que exponga el servicio en ambas regiones; `myapp.global` no se crea automáticamente. Si necesita conmutación mediante prioridades, utilice en su lugar esta política alternativa y compruebe los endpoints y la conectividad reales:

```yaml
# Alternative to distribute: region-name priority failover
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-regional-failover
  namespace: default
spec:
  host: myapp.default.svc.cluster.local
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        failover:
        - from: us-east-1
          to: us-west-2
        - from: us-west-2
          to: us-east-1
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

## Configuración en AWS EKS {#configuration-on-aws-eks}

### 1. Crear grupos de nodos en varias AZ

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-east-1
  version: '1.36'
nodeGroups:
- name: ng-zone-a
  instanceType: t3.medium
  desiredCapacity: 2
  availabilityZones:
  - us-east-1a
  amiFamily: AmazonLinux2023
- name: ng-zone-b
  instanceType: t3.medium
  desiredCapacity: 2
  availabilityZones:
  - us-east-1b
  amiFamily: AmazonLinux2023
- name: ng-zone-c
  instanceType: t3.medium
  desiredCapacity: 2
  availabilityZones:
  - us-east-1c
  amiFamily: AmazonLinux2023
```

El archivo de eksctl muestra un diseño de clúster y grupos de nodos que genera costes. No se ejecutó en la revisión documentada. Fija Kubernetes 1.36 dentro del intervalo de compatibilidad documentado de Istio y EKS, y utiliza AL2023. Seleccione las subredes y AZ reales, la capacidad de las instancias y la configuración de acceso. Para un clúster existente, prepare un plan de cambios adecuado para sus grupos de nodos.

### 2. Distribuir Pods entre zonas

Sustituya la referencia de imagen, que deliberadamente no puede resolverse, por una imagen de aplicación probada que atienda HTTP en el puerto 8080. Configure también cómo se determina que está lista para recibir tráfico. El Service siguiente proporciona el destino `myapp` utilizado por las políticas. `maxSkew: 1` se aplica entre los dominios que cumplen los requisitos; no garantiza por sí solo que haya Pods en tres zonas. La afinidad de nodos, los taints, la capacidad disponible y `minDomains` también influyen en la programación.


```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: default
spec:
  replicas: 9
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: myapp
      containers:
      - name: myapp
        image: example.invalid/myapp:replace-with-tested-tag
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: 64Mi
            cpu: 100m
          limits:
            memory: 128Mi
            cpu: 200m
---
apiVersion: v1
kind: Service
metadata:
  name: myapp
  namespace: default
spec:
  selector:
    app: myapp
  ports:
  - name: http
    port: 8080
    targetPort: 8080
```

### 3. Habilitar el enrutamiento según la zona en Istio

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

## Ejemplos prácticos {#practical-examples}

### Ejemplo 1: cadena de microservicios

Los tres primeros documentos son **parches de plantillas de Pods** para Deployments existentes de frontend y backend y para una carga de trabajo de base de datos. No son recursos completos de Kubernetes. Incorpórelos a cargas con contenedores, selectores, Services y almacenamiento reales. La afinidad de la base de datos representa un volumen o una instancia que ya está vinculado a una zona. Colocar todas las réplicas de una base de datos en una misma AZ no es una recomendación de alta disponibilidad. El DestinationRule final presupone un Service `backend` real.


```yaml
spec:
  template:
    metadata:
      labels:
        app: frontend
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: frontend
---
spec:
  template:
    metadata:
      labels:
        app: backend
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: backend
---
spec:
  template:
    metadata:
      labels:
        app: database
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1a
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend
  namespace: default
spec:
  host: backend
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 90
            us-east-1/us-east-1b/*: 5
            us-east-1/us-east-1c/*: 5
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

### Ejemplo 2: optimización de costes

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: cost-optimized
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 95
            us-east-1/us-east-1b/*: 3
            us-east-1/us-east-1c/*: 2
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

La política 95/3/2 solo incluye a los clientes de zoneA. Defina otras ubicaciones de origen si las necesita. Concentrar el tráfico puede sobrecargar los endpoints locales. Compare los bytes facturables medidos y las tarifas del servicio correspondiente con la [guía de costes de red de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html). El número de solicitudes y los pesos configurados no bastan para calcular el coste.

### Ejemplo 3: alta disponibilidad

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: high-availability
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 34
            us-east-1/us-east-1b/*: 33
            us-east-1/us-east-1c/*: 33
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

## Monitorización {#monitoring}

### Métricas de Prometheus

`source_zone` y `destination_zone` **no son etiquetas estándar de las métricas de Istio**. Las consultas opcionales siguientes requieren una canalización de enriquecimiento implementada y validada por separado, que relacione ambos endpoints con sus zonas reales y conserve las etiquetas de servicio habituales. Este capítulo no despliega esa canalización. Etiquetar Nodes, habilitar el enrutamiento por ubicación o añadir un panel de Grafana no crea estas métricas. Cuando sea necesario, conserve también el contexto de clúster y cuenta: los nombres de AZ de AWS pueden representar zonas físicas distintas según la cuenta, mientras que los ID de AZ identifican una misma zona física.

Los ejemplos abarcan expresamente el tráfico entre us-east-1a, us-east-1b y us-east-1c dentro de un clúster y una cuenta. Las zonas desconocidas, otras regiones y otros destinos quedan fuera tanto del numerador como del denominador. PromQL no permite comparar dos valores de etiqueta dentro de un selector como `{source_zone=destination_zone}`. Utilice pares explícitos de zonas coincidentes, como en las consultas siguientes. Las tasas se expresan por segundo, y el resultado del tráfico dentro de una misma zona es un porcentaje entre 0 y 100.

```promql
sum by (source_zone, destination_zone) (rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]"}[5m]))

100 * sum(rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone="us-east-1a",destination_zone="us-east-1a"}[5m]) or rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone="us-east-1b",destination_zone="us-east-1b"}[5m]) or rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone="us-east-1c",destination_zone="us-east-1c"}[5m])) / sum(rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]"}[5m]))

sum by (destination_zone) (rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]",response_code=~"5.."}[5m])) / sum by (destination_zone) (rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]"}[5m]))
```

Trate por separado la ausencia de tráfico, la falta de enriquecimiento y los fallos de recopilación. Los informes del origen cuentan solicitudes, no bytes facturables. Los informes del destino omiten los fallos de las solicitudes que nunca llegaron al servicio. El número de conexiones activas del clúster no indica su zona de destino ni demuestra que el enrutamiento por ubicación funcione como se espera.

### Panel de Grafana

Este panel requiere el enriquecimiento descrito anteriormente y una fuente de datos con el UID `prometheus`. Aprovisione el objeto completo mediante el procedimiento del [capítulo de paneles](../observability/04-dashboards.md). Sin ese enriquecimiento, los paneles no permiten medir el tráfico entre AZ.

```json
{
  "uid": "istio-enriched-zone-traffic",
  "title": "Istio Enriched Zone Traffic",
  "panels": [
    {
      "id": 1,
      "title": "Enriched Request Rate by Zone",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "sum by (source_zone, destination_zone) (rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=~\"us-east-1[abc]\",destination_zone=~\"us-east-1[abc]\"}[5m]))",
          "legendFormat": "{{source_zone}} → {{destination_zone}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "reqps"
        }
      }
    },
    {
      "id": 2,
      "title": "Same-Zone Percentage (Known a/b/c Traffic)",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "100 * sum(rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=\"us-east-1a\",destination_zone=\"us-east-1a\"}[5m]) or rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=\"us-east-1b\",destination_zone=\"us-east-1b\"}[5m]) or rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=\"us-east-1c\",destination_zone=\"us-east-1c\"}[5m])) / sum(rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=~\"us-east-1[abc]\",destination_zone=~\"us-east-1[abc]\"}[5m]))",
          "legendFormat": "Same-zone %",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "percent"
        }
      }
    }
  ],
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s"
}
```

### Verificación en tiempo real

`proxy-config endpoints` permite consultar el estado de los hosts, pero presenta la información de otra forma que la asignación de ubicaciones de EDS. `proxy-config all -o json` incluye EDS; consulte el ClusterLoadAssignment correspondiente. La consulta admite nombres de campos JSON originales en snake_case y normalizados en camelCase. Su resultado muestra la configuración, no la distribución observada del tráfico.

```bash
istioctl proxy-config endpoints <pod-name> -n <namespace>

istioctl proxy-config all <pod-name> -n <namespace> -o json | \
  jq '.configs[] | select(.["@type"] | endswith("EndpointsConfigDump")) |
      ((.dynamic_endpoint_configs // .dynamicEndpointConfigs // [])[] |
       (.endpoint_config // .endpointConfig)) |
      select((.cluster_name // .clusterName) == "outbound|8080||myapp.default.svc.cluster.local") |
      .endpoints[] | {locality, priority}'
```

## Solución de problemas {#troubleshooting}

### El enrutamiento según la zona no funciona

Compruebe la topología real de la nube antes de corregir las etiquetas. Aplicar una misma etiqueta de zona a todos los nodos de forma arbitraria altera las decisiones de programación, almacenamiento y enrutamiento, y puede hacer que los metadatos no reflejen la realidad. El ejemplo requiere que la política prevista llegue al proxy del cliente y que puedan descubrirse los endpoints de destino.

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <name> -n <namespace>
istioctl analyze -n <namespace>
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn myapp.default.svc.cluster.local -o json
kubectl get pods -n <namespace> -l app=myapp -o wide
```

Consulte EDS mediante el comando anterior. En los clústeres de Kubernetes que utilizan EDS, `.loadAssignment` en la configuración del clúster no es la fuente de endpoints. Las etiquetas de zona no se copian automáticamente de los Nodes a los Pods; relacione ambos mediante `.spec.nodeName`.

### Alta proporción de tráfico hacia otras zonas

Compruebe el nodo asignado a cada Pod y si está listo para recibir tráfico, utilizando campos estructurados. Un Pod en estado Running puede no estar listo, y contar nodos no equivale a contar AZ. Durante un despliegue gradual, las dos instantáneas pueden corresponder a momentos diferentes.

```bash
kubectl get nodes -o json > /tmp/zone-nodes.json
kubectl get pods -n default -l app=myapp -o json > /tmp/zone-pods.json
jq -r --slurpfile nodes /tmp/zone-nodes.json '
  ($nodes[0].items | map({key: .metadata.name,
    value: .metadata.labels["topology.kubernetes.io/zone"]}) | from_entries) as $zones |
  .items[] | [.metadata.name, (.spec.nodeName // "unscheduled"),
    ($zones[(.spec.nodeName // "")] // "unknown"),
    ([.status.conditions[]? | select(.type == "Ready") | .status][0] // "Unknown")] | @tsv
' /tmp/zone-pods.json

istioctl x envoy-stats <pod-name> -n <namespace> --output prom | grep outlier_detection
```

Revise también el estado de los endpoints y las expulsiones, la coincidencia `from` de la ubicación de origen, la reutilización de conexiones, el volumen de tráfico y la capacidad de reserva de cada zona. La distribución ponderada envía deliberadamente parte del tráfico a otras zonas en buen estado. Que haya distinto número de réplicas por zona no redefine por sí solo los pesos configurados.

### Faltan etiquetas de topología en EKS

AWS Node Termination Handler responde a eventos de interrupción y terminación; instalarlo no corrige las etiquetas de topología. Revise la configuración de arranque del nodo EKS, su integración con la nube y la ubicación real de la instancia. El siguiente diagnóstico es **de solo lectura y exclusivo para nodos EC2**: extrae el ID de instancia de providerID y especifica la región del clúster. No cambia las etiquetas de los nodos. Para Fargate o un proveedor distinto de EC2, utilice el diagnóstico de la plataforma correspondiente.

```bash
CLUSTER_REGION=us-east-1
NODE_NAME=<node-name>
PROVIDER_ID=$(kubectl get node "$NODE_NAME" -o jsonpath='{.spec.providerID}')
INSTANCE_ID=${PROVIDER_ID##*/}
if [[ ! "$INSTANCE_ID" =~ ^i-([0-9a-f]{8}|[0-9a-f]{17})$ ]]; then
  echo "Expected an EC2 instance ID in providerID; inspect the node platform." >&2
  exit 1
fi
aws ec2 describe-instances --region "$CLUSTER_REGION" \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[].Instances[].{InstanceId:InstanceId,AZ:Placement.AvailabilityZone,State:State.Name}' \
  --output table
```

Confirme la cuenta, la región y la identidad real del nodo antes de aplicar una corrección revisada de arranque o etiquetas. No pase la URI completa `aws:///zone/i-...` a `--instance-ids`, ni dé por supuesto que puede acceder a IMDSv1 sin autenticación.

## Buenas prácticas

### 1. Distribución uniforme de Pods entre zonas

Incluya este fragmento en `spec`, dentro de una plantilla de Pod, y compruebe que el selector coincide con sus etiquetas. Las restricciones cuentan los dominios que cumplen los requisitos. Decida si, cuando una zona no esté disponible, la programación estricta debe dejar los Pods en estado Pending.


```yaml
# Use topologySpreadConstraints
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      app: myapp
```

### 2. Optimización de costes

```yaml
# Prioritize same zone (80% or more)
distribute:
- from: us-east-1/us-east-1a/*
  to:
    "us-east-1/us-east-1a/*": 80
    "us-east-1/us-east-1b/*": 10
    "us-east-1/us-east-1c/*": 10
```

### 3. Configurar la alta disponibilidad

Utilice prioridades por ubicación y detección de endpoints que fallan, con una capacidad de reserva que haya probado. Este fragmento se incluye en `trafficPolicy.loadBalancer.localityLbSetting`. El campo `failover` ordena regiones, no zonas, y se utiliza como alternativa a `distribute`.

```yaml
failover:
- from: us-east-1
  to: us-west-2
```

### 4. Almacenamiento y disponibilidad de cargas de trabajo con estado

Un volumen EBS y la instancia EC2 a la que está conectado deben estar en la misma AZ. Esa condición afecta a cada volumen y réplica, no obliga a colocar todas las réplicas de un StatefulSet en una sola zona. Diseñe la replicación y la conmutación de la base de datos entre dominios de fallo con almacenamiento y programación compatibles. El enrutamiento según la topología no puede elegir un primario que admita escrituras de forma segura. La afinidad siguiente solo corresponde a una carga vinculada expresamente a un volumen existente en zoneA; no recomienda agrupar todas las réplicas con estado en una misma AZ.


```yaml
# Pod-spec fragment for one existing zonal volume/replica
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: In
          values:
          - us-east-1a
```

Las indicaciones de topología y la distribución de tráfico de los Services de Kubernetes son mecanismos distintos del balanceo de carga de Envoy en Istio. Habilitar una anotación de Service no configura por sí solo la política de ubicación del sidecar del cliente.

## Referencias

- [Equilibrio de carga por localidad de Istio](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/)
- [Enrutamiento con reconocimiento de topología de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/topology-aware-routing/)
- [Resiliencia de AWS EKS](https://docs.aws.amazon.com/eks/latest/userguide/disaster-recovery-resiliency.html)
- [Optimización de costes de red de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)
- [Zonas de disponibilidad de volúmenes EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes.html)
- [ID de zonas de disponibilidad de AWS](https://docs.aws.amazon.com/global-infrastructure/latest/regions/az-ids.html)
