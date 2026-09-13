# Enrutamiento con reconocimiento de zonas

> **Última actualización**: September 11, 2026 · Istio 1.31. Este capítulo utiliza `localityLbSetting` para ponderación por localidad/conmutación por prioridades. La API independiente `zoneAwareLbSetting` tiene requisitos y semántica diferentes; no mezcle sus campos. Los ejemplos presuponen una malla con sidecars y alternativas de políticas independientes para el mismo host. No se han desplegado ni probado bajo carga.

El enrutamiento con reconocimiento de zonas es una función que optimiza el tráfico al reconocer las zonas de disponibilidad de Kubernetes. Reduce la latencia y los costes de transferencia de datos entre AZ al priorizar la comunicación dentro de la misma AZ.

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

El enrutamiento con reconocimiento de zonas ofrece las siguientes ventajas:


### Ventajas

1. **Menor latencia**: minimizar la latencia de red mediante comunicación dentro de la misma AZ
2. **Ahorro de costes**: reducir los costes de transferencia de datos entre AZ
   - Estime los bytes facturables reales, la dirección, la región y la ruta de servicios de AWS; no existe un precio universal por GB para todas las solicitudes de EKS.
3. **Apoyo a la disponibilidad**: requiere endpoints sanos y accesibles y capacidad de reserva en otras zonas.
4. **Optimización del rendimiento**: ancho de banda de red optimizado

## Funcionamiento {#how-it-works}

### Algoritmo de equilibrio de carga por localidad

Una política `distribute` 80/10/10 envía tráfico normal a las tres zonas sanas; las porciones del 10% no son una reserva para conmutación por error. La conmutación por localidad basada en prioridades es un modo independiente. La ponderación por estado/capacidad puede desviar tráfico antes de que fallen todos los hosts locales. Las letras de AZ no codifican proximidad física ni latencia.



### Jerarquía de localidad

Istio utiliza la siguiente jerarquía de localidad:

```
Region/Zone/SubZone

Example:
us-east-1/us-east-1a/*
us-east-1/us-east-1b/*
us-west-2/us-west-2a/*
```

**Prioridades de localidad predeterminadas** (cuando está activa la conmutación por prioridades):

1. Misma región, zona y subzona.
2. Misma región/zona, distinta subzona.
3. Misma región, distinta zona.
4. Otras regiones, ordenadas por la política de conmutación regional configurada cuando se proporciona.

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

Lo siguiente es un ClusterLoadAssignment esquemático, no una salida capturada de la CLI. El EDS real también incluye pesos/prioridades generados y estado de salud:

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

Envoy compara su propia localidad con la información EDS recibida para enrutar:

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

Un Pod programado permanece en su nodo durante la vida de ese UID de Pod; un controlador puede sustituirlo por un Pod nuevo en otro nodo. Istiod asocia endpoints con la topología de nodos mediante el descubrimiento de Kubernetes. Esta ruta normal de enrutamiento por localidad no requiere etiquetas de zona adicionales en los Pods. Las observaciones/cachés de API y la configuración de proxies convergen de forma asíncrona; inspeccione la configuración efectiva en vez de suponer una actualización inmediata. El enriquecimiento personalizado de telemetría es una cuestión independiente.

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

Para nodos basados en EC2, la integración de nube/arranque utiliza información de ubicación de instancias de AWS. `spec.providerID` identifica la instancia del proveedor; no es en sí un ID de instancia EC2. El acceso a IMDS desde una carga de trabajo puede estar restringido e IMDSv2 requiere un token; utilice el diagnóstico EC2 de solo lectura siguiente cuando corresponda. Los nodos Fargate necesitan sus propios diagnósticos de plataforma.

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

### 2. Habilitar el enrutamiento con reconocimiento de zonas en DestinationRule

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

El ejemplo básico utiliza prioridades de localidad junto con detección de valores atípicos. Su límite de expulsión del 100% permite excluir todos los endpoints no sanos, lo que puede producir «no hay hosts ascendentes sanos» si no sobrevive capacidad. Es un ajuste ilustrativo de conmutación, no un límite seguro universal.

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

Para `localityLbSetting`, `failoverPriority` puede comparar metadatos de región/zona como arriba. En cambio, el campo `failover` recibe **nombres de regiones**, no rutas `region/zone`; no expresa un orden de zonas A→B→C. Utilice aquí uno de `distribute`, `failover` o `failoverPriority`. Estas reglas difieren de las de la API independiente `zoneAwareLbSetting`.

### Uso con detección de valores atípicos

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

`minHealthPercent` es un umbral de pánico/apertura ante fallos del grupo, no una capacidad sana mínima por zona. Cero deshabilita ese umbral. La distribución ponderada 80/20 sigue utilizando ambas zonas sanas; no es una conmutación a una reserva.

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

El ejemplo 90/10 es solo distribución. Requiere una configuración real multiclúster/red que exponga ese servicio en ambas regiones; `myapp.global` no es un servicio creado automáticamente. Para conmutación por prioridades, utilice en su lugar esta política independiente y verifique los endpoints/conectividad reales:

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

El archivo eksctl es un ejemplo de diseño de clúster/grupos de nodos facturable, no un comando ejecutado por esta auditoría. Fija Kubernetes 1.36 dentro del rango de compatibilidad documentado de Istio/EKS y utiliza AL2023. Seleccione subredes/AZ reales, capacidad de instancias y ajustes de acceso; los clústeres existentes necesitan un plan apropiado de cambios en los grupos de nodos.

### 2. Distribuir Pods entre zonas

Sustituya la referencia de imagen deliberadamente no resoluble por la imagen de aplicación probada que atiende HTTP8080 y configure su comportamiento de disponibilidad. El Service siguiente proporciona el destino `myapp` utilizado por las políticas. `maxSkew: 1` se aplica entre dominios elegibles, no como garantía incondicional de tres zonas; la afinidad de nodos, las restricciones taint, la capacidad de recursos y `minDomains` afectan a la programación.


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

### 3. Habilitar el enrutamiento con reconocimiento de zonas en Istio

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

Los primeros tres documentos son **parches de plantillas de Pod** para Deployments frontend/backend existentes y una carga de trabajo de base de datos, no recursos de Kubernetes completos. Combínelos con cargas de trabajo que tengan contenedores, selectores, Services y almacenamiento reales. La afinidad de la base de datos ilustra un volumen/instancia ya asociado a una zona; colocar todas las réplicas de base de datos en una AZ no es una recomendación de alta disponibilidad. El DestinationRule final presupone un Service `backend` real.


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

La política 95/3/2 cubre únicamente a los clientes de zoneA; defina otras localidades de origen si es necesario. La concentración puede sobrecargar los endpoints locales. Compare los bytes facturables medidos y los precios específicos del servicio con la [guía de costes de red de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html); los recuentos/pesos de solicitudes por sí solos no son un cálculo de costes.

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

`source_zone` y `destination_zone` **no son etiquetas de métricas estándar de Istio**. Las siguientes consultas opcionales requieren una canalización de enriquecimiento implementada y validada por separado que asocie ambos endpoints con sus zonas reales conservando las etiquetas de servicio normales. Este capítulo no despliega esa canalización. Etiquetar Nodes, habilitar enrutamiento por localidad o añadir un panel de Grafana por sí solo no crea estas métricas. Conserve el contexto de clúster/cuenta cuando sea necesario; los nombres de AZ de AWS pueden corresponder a zonas distintas entre cuentas, mientras que los ID de AZ identifican la misma zona física.

Los ejemplos cubren explícitamente el tráfico entre us-east-1a/b/c en un clúster/cuenta. Las zonas desconocidas, otras regiones y otros destinos se excluyen tanto del numerador como del denominador. PromQL no puede comparar dos valores de etiqueta dentro de un selector como `{source_zone=destination_zone}`; utilice pares coincidentes explícitos como a continuación. Las tasas son por segundo y el resultado de misma zona es un porcentaje de 0–100.

```promql
sum by (source_zone, destination_zone) (rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]"}[5m]))

100 * sum(rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone="us-east-1a",destination_zone="us-east-1a"}[5m]) or rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone="us-east-1b",destination_zone="us-east-1b"}[5m]) or rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone="us-east-1c",destination_zone="us-east-1c"}[5m])) / sum(rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]"}[5m]))

sum by (destination_zone) (rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]",response_code=~"5.."}[5m])) / sum by (destination_zone) (rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]"}[5m]))
```

Gestione por separado la ausencia de tráfico, la falta de enriquecimiento y los fallos de recopilación. Los informes de origen cuentan solicitudes, no bytes facturables; los informes de destino omiten los fallos que nunca llegaron al servicio. Las conexiones activas del clúster no revelan su zona de destino y no demuestran la eficacia de la localidad.

### Panel de Grafana

Este panel requiere el enriquecimiento anterior y el UID de fuente de datos `prometheus`. Aprovisione el objeto completo mediante el [capítulo de paneles](../observability/04-dashboards.md). Sin enriquecimiento, estos paneles no son una medición funcional del tráfico de AZ.

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

`proxy-config endpoints` es útil para el estado de los hosts, pero su presentación difiere de la asignación de localidad EDS. `proxy-config all -o json` incluye EDS; inspeccione el ClusterLoadAssignment correspondiente. La consulta acepta nombres de campos JSON originales en snake_case y normalizados en camelCase. Esto es evidencia de configuración, no de distribución observada del tráfico.

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

### El enrutamiento con reconocimiento de zonas no funciona

Compruebe la topología real de la nube antes de reparar etiquetas. Aplicar arbitrariamente una etiqueta de zona a todos los nodos cambia las decisiones de programación/almacenamiento/enrutamiento y puede falsear los metadatos. El ejemplo de enrutamiento necesita que la política prevista llegue al proxy cliente y que los endpoints de destino puedan descubrirse.

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <name> -n <namespace>
istioctl analyze -n <namespace>
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn myapp.default.svc.cluster.local -o json
kubectl get pods -n <namespace> -l app=myapp -o wide
```

Lea EDS con el comando anterior. Para los clústeres EDS de Kubernetes, `.loadAssignment` en la configuración del clúster no es la fuente de endpoints. Las etiquetas de zona de los Pods no se copian automáticamente de los Nodes; relacione mediante `.spec.nodeName`.

### Alta proporción de tráfico hacia otras zonas

Inspeccione la ubicación de Pods en nodos y la disponibilidad usando campos estructurados. Un Pod Running puede no estar listo, y un resumen del número de nodos no es un resumen del número de AZ. Estas dos instantáneas pueden diferir en el tiempo durante los despliegues.

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

Inspeccione también el estado de endpoints/expulsiones, la coincidencia `from` de la localidad de origen, la reutilización de conexiones, el volumen de tráfico y la capacidad zonal de reserva. La distribución ponderada envía deliberadamente parte del tráfico sano a otras zonas; los números desiguales de réplicas no redefinen por sí solos los pesos de zona configurados.

### Faltan etiquetas de topología en EKS

AWS Node Termination Handler responde a eventos de interrupción/terminación; instalarlo no repara las etiquetas de topología. Inspeccione la integración de arranque/nube del nodo EKS y la ubicación real de la instancia. El siguiente diagnóstico es **de solo lectura y únicamente para nodos EC2**; extrae el ID de instancia de providerID y proporciona la región del clúster. No cambia las etiquetas de los nodos. Utilice los diagnósticos de plataforma apropiados para Fargate o un proveedor distinto de EC2.

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

Confirme la cuenta/región y la identidad real del nodo antes de aplicar una reparación revisada de arranque o etiquetas. No pase la URI completa `aws:///zone/i-...` a `--instance-ids`, ni suponga que el acceso IMDSv1 sin autenticación funciona.

## Buenas prácticas

### 1. Distribución uniforme de Pods entre zonas

Coloque este fragmento bajo el `spec` de una plantilla de Pod y asegúrese de que su selector coincida con las etiquetas del Pod. Las restricciones cuentan dominios elegibles; considere si la programación estricta debería dejar Pods Pending cuando una zona no esté disponible.


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

### 3. Garantizar alta disponibilidad

Utilice prioridades de localidad y detección de valores atípicos con capacidad de reserva probada. Este fragmento pertenece a `trafficPolicy.loadBalancer.localityLbSetting`; `failover` ordena regiones, no zonas, y es una alternativa a `distribute`.

```yaml
failover:
- from: us-east-1
  to: us-west-2
```

### 4. Almacenamiento y disponibilidad de cargas de trabajo con estado

Un volumen EBS y la instancia EC2 a la que está conectado deben estar en la misma AZ. Esto restringe un volumen/réplica individual, no todas las réplicas de un StatefulSet. Diseñe la replicación/conmutación de la base de datos entre dominios de fallo con almacenamiento y programación compatibles; el enrutamiento con reconocimiento de topología no puede elegir un primario con escritura seguro. La afinidad siguiente es solo para una carga de trabajo ligada deliberadamente a un volumen existente en zoneA. No es una recomendación general de colocar todas las réplicas con estado en una AZ.


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

Las indicaciones de topología/distribución de tráfico de Service de Kubernetes y el equilibrio de carga Envoy de Istio son mecanismos distintos. No suponga que habilitar una anotación de Service configura la política de localidad del sidecar cliente.

## Referencias

- [Equilibrio de carga por localidad de Istio](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/)
- [Enrutamiento con reconocimiento de topología de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/topology-aware-routing/)
- [Resiliencia de AWS EKS](https://docs.aws.amazon.com/eks/latest/userguide/disaster-recovery-resiliency.html)
- [Optimización de costes de red de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)
- [Zonas de disponibilidad de volúmenes EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes.html)
- [ID de zonas de disponibilidad de AWS](https://docs.aws.amazon.com/global-infrastructure/latest/regions/az-ids.html)
