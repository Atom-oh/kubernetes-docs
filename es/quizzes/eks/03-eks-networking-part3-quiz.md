# EKS Networking Quiz - Part 3

Este quiz evalúa tu comprensión de conceptos avanzados de networking en Amazon EKS, incluidos service mesh, VPC endpoints, networking multi-cluster y seguridad de red.

## Multiple Choice Questions

### 1. What is the main architectural change that occurs when implementing a service mesh (e.g., AWS App Mesh, Istio) in Amazon EKS?

A. Toda la comunicación pod-to-pod se enruta fuera de la VPC B. Se agrega un sidecar proxy a cada pod para mediar la comunicación service-to-service C. Los objetos Kubernetes Service ya no se usan D. Todo el tráfico de red se enruta a través de AWS Transit Gateway

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. Se agrega un sidecar proxy a cada pod para mediar la comunicación service-to-service**

**Explicación:** El cambio arquitectónico más significativo al implementar un service mesh es que se agrega un sidecar proxy (normalmente Envoy) a cada pod. Este sidecar proxy intercepta y procesa todo el tráfico entrante y saliente del pod, mediando la comunicación service-to-service.

**Características clave:**

1. **Patrón Sidecar**: Un proxy container se despliega junto a cada application container. Este proxy maneja toda la comunicación de red.
2. **Cambios en el flujo de tráfico**:
   * Tradicional: Client → Service → Target Pod
   * Service Mesh: Client → Client Sidecar → Service → Target Sidecar → Target Pod
3. **Data Plane y Control Plane**:
   * Data Plane: Colección de sidecar proxies
   * Control Plane: Componente central que administra la configuración de los proxies y aplica políticas
4. **Sin cambios en el código de la aplicación**: Uno de los principales beneficios de un service mesh es la capacidad de agregar funciones avanzadas de networking sin cambiar el código de la aplicación.

**Ejemplo de implementación de Service Mesh (AWS App Mesh):**

```yaml
# App Mesh sidecar injection example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example-app
  labels:
    app: example
spec:
  replicas: 3
  selector:
    matchLabels:
      app: example
  template:
    metadata:
      labels:
        app: example
      annotations:
        appmesh.k8s.aws/mesh: my-mesh  # App Mesh mesh name
        appmesh.k8s.aws/virtualNode: example-vn  # Virtual node name
    spec:
      containers:
      - name: example
        image: example:latest
        ports:
        - containerPort: 8080
```

**Características proporcionadas por Service Mesh:**

* Administración de tráfico (routing, load balancing, circuit breaking)
* Seguridad (mTLS, authentication, authorization)
* Observabilidad (metrics, logs, distributed tracing)
* Aplicación de políticas

Problemas con las otras opciones:

* **A. Toda la comunicación pod-to-pod se enruta fuera de la VPC**: Service mesh normalmente opera dentro del cluster y no enruta tráfico fuera de la VPC.
* **C. Los objetos Kubernetes Service ya no se usan**: Service mesh complementa, en lugar de reemplazar, los objetos Kubernetes Service.
* **D. Todo el tráfico de red se enruta a través de AWS Transit Gateway**: Service mesh no está relacionado con AWS Transit Gateway y administra la comunicación service-to-service dentro del cluster.

</details>

### 2. What is the main benefit of using VPC endpoints to privately access AWS services in Amazon EKS?

A. Proporciona ancho de banda ilimitado a todos los AWS services B. Permite acceso privado a AWS services sin un internet gateway C. Reduce los costos de uso de AWS services en un 50% D. Proporciona authentication automática a todos los AWS services

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. Permite acceso privado a AWS services sin un internet gateway**

**Explicación:** El principal beneficio de usar VPC endpoints en Amazon EKS es la capacidad de acceder de forma privada a AWS services sin un internet gateway. Esto mejora la seguridad y reduce los costos de transferencia de datos.

**Tipos de VPC Endpoint:**

1. **Interface Endpoints (AWS PrivateLink)**:
   * Proporciona conectividad privada a la mayoría de los AWS services
   * Crea endpoint network interfaces (ENIs) en cada subnet
   * Ejemplos: ECR, CloudWatch, SNS, SQS, etc.
2. **Gateway Endpoints**:
   * Proporciona conectividad privada a S3 y DynamoDB
   * Agrega routes a route tables
   * Sin costo adicional

**Ejemplo de configuración de VPC Endpoint para EKS:**

```yaml
# CloudFormation example
Resources:
  S3GatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.s3
      VpcId: !Ref VPC
      RouteTableIds:
        - !Ref PrivateRouteTable
      VpcEndpointType: Gateway

  ECRApiEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.ecr.api
      VpcId: !Ref VPC
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2
      SecurityGroupIds:
        - !Ref EndpointSecurityGroup
      PrivateDnsEnabled: true
      VpcEndpointType: Interface
```

**AWS Services clave que requieren VPC Endpoints para EKS:**

* Amazon ECR (pulling container images)
* Amazon S3 (archivos de configuración, backups, etc.)
* AWS KMS (encryption keys)
* Amazon CloudWatch (logging and monitoring)
* AWS STS (asumir IAM roles)

**Beneficios de usar VPC Endpoints:**

1. **Seguridad mejorada**: El tráfico no atraviesa internet público
2. **Costos de red reducidos**: Menores costos de transferencia de datos hacia AWS services
3. **Latencia reducida**: Routing directo dentro de la red de AWS
4. **Compliance**: Cumple requisitos regulatorios y de soberanía de datos

**Configuración de EKS Node en Private Subnets:**

```bash
# Create node group in private subnets with eksctl
eksctl create nodegroup \
  --cluster my-cluster \
  --name private-ng \
  --node-private-networking \
  --vpc-private-subnets subnet-0123456789abcdef0,subnet-0123456789abcdef1
```

Problemas con las otras opciones:

* **A. Proporciona ancho de banda ilimitado a todos los AWS services**: VPC endpoints no proporcionan ancho de banda ilimitado; puede haber límites de ancho de banda según el servicio y la región.
* **C. Reduce los costos de uso de AWS services en un 50%**: VPC endpoints pueden reducir los costos de transferencia de datos, pero no reducen los costos de uso de AWS services en un 50%.
* **D. Proporciona authentication automática a todos los AWS services**: VPC endpoints no automatizan la authentication; aún se requieren permisos IAM adecuados.

</details>

### 3. What is the most effective method for implementing multi-cluster networking in Amazon EKS?

A. Usar public load balancers en cada cluster para la comunicación inter-cluster B. Usar AWS Transit Gateway para conectar múltiples VPCs y configurar routing inter-cluster C. Desplegar todos los clusters en una sola VPC para reducir la complejidad de red D. Usar NAT gateways en cada cluster para la comunicación inter-cluster

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar AWS Transit Gateway para conectar múltiples VPCs y configurar routing inter-cluster**

**Explicación:** El método más efectivo para implementar networking multi-cluster en Amazon EKS es usar AWS Transit Gateway para conectar múltiples VPCs y configurar routing inter-cluster. Este enfoque proporciona escalabilidad, seguridad y facilidad de administración.

**Networking Multi-Cluster con AWS Transit Gateway:**

1. **Resumen de arquitectura**:
   * Cada EKS cluster se despliega en una VPC separada
   * Transit Gateway conecta todas las VPCs
   * La comunicación inter-cluster se enruta a través de Transit Gateway
2.  **Pasos de configuración**:

    ```bash
    # 1. Create Transit Gateway
    aws ec2 create-transit-gateway --description "EKS Multi-Cluster TGW"

    # 2. Attach VPC to Transit Gateway
    aws ec2 create-transit-gateway-vpc-attachment \
      --transit-gateway-id tgw-0123456789abcdef0 \
      --vpc-id vpc-0123456789abcdef0 \
      --subnet-ids subnet-0123456789abcdef0 subnet-0123456789abcdef1

    # 3. Update routing tables
    aws ec2 create-route \
      --route-table-id rtb-0123456789abcdef0 \
      --destination-cidr-block 10.1.0.0/16 \
      --transit-gateway-id tgw-0123456789abcdef0
    ```
3. **Planificación de CIDR**:
   * Asigna bloques CIDR no superpuestos a cada cluster/VPC
   * Ejemplo: Cluster1: 10.0.0.0/16, Cluster2: 10.1.0.0/16, Cluster3: 10.2.0.0/16

**Opciones de Multi-Cluster Service Discovery:**

1.  **AWS Cloud Map**:

    ```bash
    # Create namespace
    aws servicediscovery create-private-dns-namespace \
      --name multi-cluster.local \
      --vpc vpc-0123456789abcdef0

    # Register service
    aws servicediscovery register-instance \
      --service-id srv-0123456789abcdef0 \
      --instance-id api-service-cluster1 \
      --attributes AWS_INSTANCE_IPV4=10.0.1.123
    ```
2.  **Configuración personalizada de CoreDNS**:

    ```yaml
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: coredns
      namespace: kube-system
    data:
      Corefile: |
        .:53 {
            errors
            health
            kubernetes cluster.local in-addr.arpa ip6.arpa {
               pods insecure
               upstream
               fallthrough in-addr.arpa ip6.arpa
            }
            forward . /etc/resolv.conf
            cache 30
            loop
            reload
            loadbalance
        }
        cluster2.svc.local:53 {
            errors
            cache 30
            forward . 10.1.0.2
        }
    ```

**Consideraciones de seguridad para Networking Multi-Cluster:**

1. **Control de tráfico Inter-VPC**:
   * Usa Transit Gateway security groups y routing tables para restringir el tráfico
   * Permite solo los puertos y protocolos necesarios
2.  **Network Policies**:

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-cross-cluster
    spec:
      podSelector:
        matchLabels:
          app: api-service
      ingress:
      - from:
        - ipBlock:
            cidr: 10.1.0.0/16  # Cluster2's CIDR
      egress:
      - to:
        - ipBlock:
            cidr: 10.1.0.0/16  # Cluster2's CIDR
    ```

**Opciones de Multi-Cluster Service Mesh:**

1. **Istio Multi-Cluster**:
   * Administra múltiples clusters con un solo control plane
   * Cross-cluster service discovery y load balancing
2. **AWS App Mesh**:
   * Crea un mesh que abarca múltiples clusters
   * Service discovery mediante AWS Cloud Map

**Consideraciones de optimización de costos:**

* Considera los cargos por hora y de procesamiento de datos de Transit Gateway
* Minimiza la transferencia de datos cross-cluster
* Comunícate dentro de la misma availability zone cuando sea posible

Problemas con las otras opciones:

* **A. Usar public load balancers en cada cluster para la comunicación inter-cluster**: Este método aumenta los riesgos de seguridad, incurre en costos de transferencia de datos de internet y aumenta la latencia.
* **C. Desplegar todos los clusters en una sola VPC para reducir la complejidad de red**: Desplegar múltiples clusters en una sola VPC puede provocar limitaciones de espacio de direcciones IP, falta de límites de seguridad y problemas de escalabilidad.
* **D. Usar NAT gateways en cada cluster para la comunicación inter-cluster**: NAT gateways son para tráfico saliente a internet y no son adecuados para la comunicación inter-cluster.

</details>

### 5. What is the most effective method for optimizing pod networking performance in Amazon EKS?

A. Usar host network mode para todos los pods B. Habilitar la feature prefix delegation de Amazon VPC CNI C. Usar servicios NodePort para todos los pods D. Usar AWS Global Accelerator para toda la comunicación intra-cluster

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. Habilitar la feature prefix delegation de Amazon VPC CNI**

**Explicación:** El método más efectivo para optimizar el rendimiento de pod networking en Amazon EKS es habilitar la feature prefix delegation de Amazon VPC CNI. Esta feature aumenta significativamente el número de direcciones IP secundarias asignadas a cada node y reduce la frecuencia de creación de ENI (Elastic Network Interface), mejorando el rendimiento y la escalabilidad del networking.

**Cómo funciona Prefix Delegation:**

1. **Default VPC CNI vs Prefix Delegation**:
   * Default VPC CNI: Asigna direcciones IP secundarias individuales a cada ENI
   * Prefix Delegation: Asigna bloques CIDR /28 (16 IPs) a cada ENI
2.  **Método de habilitación**:

    ```bash
    # Enable prefix delegation
    kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

    # Verify prefix delegation
    kubectl describe daemonset aws-node -n kube-system | grep ENABLE_PREFIX_DELEGATION
    ```
3.  **Opciones de configuración adicionales**:

    ```bash
    # Set prefix allocation size (default: /28)
    kubectl set env daemonset aws-node -n kube-system WARM_PREFIX_TARGET=1

    # Threshold for requesting new prefix when available IPs are low
    kubectl set env daemonset aws-node -n kube-system WARM_IP_TARGET=5
    ```

**Beneficios de Prefix Delegation:**

1. **Escalabilidad mejorada**:
   * Mayor número máximo de pods por node (normalmente de 110 a 250+)
   * Menor API throttling debido a menos llamadas de creación de ENI
2. **Tiempo de inicio de Pod más rápido**:
   * Menos llamadas de API necesarias para asignar direcciones IP a nuevos pods
   * Mejor rendimiento para despliegues de pods a gran escala
3. **Eficiencia de direcciones IP**:
   * Soporta más pods con la misma cantidad de ENIs
   * Mitiga problemas de agotamiento de direcciones IP

**Comparación de Maximum Pods Per Instance Type:**

| Instance Type | Default VPC CNI | Prefix Delegation Enabled |
| ------------- | --------------- | ------------------------- |
| t3.medium     | 17              | 110                       |
| m5.large      | 29              | 110                       |
| c5.xlarge     | 58              | 250                       |
| r5.2xlarge    | 58              | 250                       |

**Ejemplo de configuración (ConfigMap):**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-prefix-delegation: "true"
  warm-prefix-target: "1"
  warm-ip-target: "5"
```

**Consideraciones y limitaciones:**

1. **Tamaño de subnet**:
   * Prefix delegation requiere subnets lo suficientemente grandes
   * Se recomienda un bloque CIDR mínimo /24
2. **Security Group Rules**:
   * Security group rules pueden simplificarse con prefix delegation
   * Puede referenciar bloques CIDR en lugar de IPs individuales
3. **Compatibilidad**:
   * Algunos tipos de instancias EC2 legacy no soportan prefix delegation
   * Se recomiendan instancias basadas en Nitro
4. **Administración de direcciones IP**:
   * Prefix delegation usa las direcciones IP de forma más eficiente, pero la planificación CIDR adecuada sigue siendo necesaria

**Monitoring y troubleshooting:**

```bash
# Check IP address allocation per node
kubectl exec -n kube-system aws-node-xxxxx -- curl -s http://localhost:61679/v1/enis | jq

# Check prefix delegation status
kubectl logs -n kube-system aws-node-xxxxx | grep -i prefix
```

Problemas con las otras opciones:

* **A. Usar host network mode para todos los pods**: Host network mode hace que los pods compartan el network namespace del node, lo que provoca conflictos de puertos y elimina el aislamiento de red.
* **C. Usar servicios NodePort para todos los pods**: NodePort es un mecanismo de exposición de Service y no está relacionado con la optimización del rendimiento de pod networking.
* **D. Usar AWS Global Accelerator para toda la comunicación intra-cluster**: AWS Global Accelerator es para administración de tráfico global y no es adecuado para la optimización de la comunicación intra-cluster.

</details>

## Short Answer Questions

### 7. What is the most commonly used open-source proxy for sidecar proxies when implementing a service mesh in Amazon EKS?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** Envoy

**Explicación detallada:**

El sidecar proxy más utilizado al implementar un service mesh en Amazon EKS es Envoy. Envoy es un proxy basado en C++ de alto rendimiento usado como data plane proxy en la mayoría de las implementaciones principales de service mesh (Istio, AWS App Mesh, Consul Connect, etc.).

**Características clave de Envoy:**

1. **Arquitectura de alto rendimiento**:
   * Escrito en C++ para baja latencia y alto throughput
   * Modelo de networking asíncrono y orientado a eventos
2. **Funciones completas de administración de tráfico**:
   * Load balancing (round robin, weighted, least request, etc.)
   * Circuit breaking y outlier detection
   * Políticas de retry y timeout
   * Traffic splitting y mirroring
3. **Observabilidad**:
   * Métricas y estadísticas detalladas
   * Integración con distributed tracing (Zipkin, Jaeger, etc.)
   * Access logging
4. **Funciones de seguridad**:
   * Terminación TLS/mTLS
   * Authentication y authorization
   * Rate limiting

**Despliegue de Envoy en Service Mesh:**

1.  **Patrón Sidecar**:

    ```yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: example-app
    spec:
      template:
        spec:
          containers:
          - name: app
            image: app:latest
          - name: envoy-proxy
            image: envoyproxy/envoy:v1.20.0
            ports:
            - containerPort: 15001
            volumeMounts:
            - name: envoy-config
              mountPath: /etc/envoy
          volumes:
          - name: envoy-config
            configMap:
              name: envoy-config
    ```
2. **Inyección automática**:
   * Istio: annotation `sidecar.istio.io/inject: "true"`
   * AWS App Mesh: label `appmesh.k8s.aws/sidecarInjectorWebhook: enabled`

**Ejemplo de configuración de Envoy:**

```yaml
static_resources:
  listeners:
  - address:
      socket_address:
        address: 0.0.0.0
        port_value: 15001
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          route_config:
            name: local_route
            virtual_hosts:
            - name: backend
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: service_backend
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  clusters:
  - name: service_backend
    connect_timeout: 0.25s
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: service_backend
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: backend-service
                port_value: 80
```

**Integración de Envoy por Service Mesh:**

1. **Istio**:
   * Usa Envoy como sidecar proxy
   * istiod administra dinámicamente la configuración de Envoy
   * Componentes como Pilot, Mixer, Citadel se integran con Envoy
2. **AWS App Mesh**:
   * El controller de AWS App Mesh inyecta el sidecar Envoy
   * Se integra con AWS Cloud Map para service discovery
   * Envoy Management Service (EMS) administra la configuración de Envoy
3. **Consul Connect**:
   * Usa Envoy como data plane proxy
   * Consul proporciona service discovery y configuration management

**Monitoring y debugging de Envoy:**

```bash
# Port forward Envoy admin interface
kubectl port-forward <pod-name> 19000:19000

# Check configuration and stats
curl localhost:19000/config_dump
curl localhost:19000/stats

# Check cluster status
curl localhost:19000/clusters
```

**Consideraciones de optimización de rendimiento:**

* Asignación de recursos: Asigna CPU y memoria suficientes a Envoy
* Connection pooling: Configura upstream connection pooling para mejorar el rendimiento
* Tamaño de buffer: Configura tamaños de buffer adecuados para la optimización del uso de memoria
* Filter chain: Habilita solo los filtros necesarios para minimizar el overhead

Envoy es un componente central de la arquitectura moderna de service mesh, y cumple un rol crítico para hacer que la comunicación de microservicios sea segura, confiable y observable.

</details>

### 8. What is the name of the Kubernetes add-on responsible for internal DNS resolution in Amazon EKS clusters?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** CoreDNS

**Explicación detallada:**

El Kubernetes add-on responsable de la resolución DNS interna en clusters de Amazon EKS es CoreDNS. CoreDNS actúa como el DNS server para service discovery dentro de los Kubernetes clusters, manejando la resolución de nombres para pods y services.

**Características clave de CoreDNS:**

1. **Service Discovery**:
   * Resuelve nombres DNS en el formato `<service-name>.<namespace>.svc.cluster.local`
   * Soporta reverse DNS lookups para direcciones IP de pod
2. **Arquitectura de plugins**:
   * Extiende la funcionalidad mediante varios plugins
   * Caching, metrics, logging, error handling, etc.
3. **Flexibilidad de configuración**:
   * Configuración declarativa mediante Corefile
   * Soporta recarga dinámica

**Despliegue de CoreDNS en EKS:**

1. **Configuración de despliegue predeterminada**:
   * Se despliega automáticamente cuando se crea el EKS cluster
   * Se ejecuta en el namespace kube-system
   * Normalmente se despliega con 2 o más replicas
2.  **Verificación**:

    ```bash
    # Check CoreDNS pods
    kubectl get pods -n kube-system -l k8s-app=kube-dns

    # Check CoreDNS version
    kubectl describe deployment coredns -n kube-system | grep Image
    ```

**Configuración de CoreDNS (Corefile):**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
            lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
            ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

**Descripciones de plugins clave:**

1. **errors**: Registra errores
2. **health**: Proporciona un endpoint de health check
3. **ready**: Proporciona un endpoint de readiness check
4. **kubernetes**: Maneja Kubernetes service discovery
5. **prometheus**: Expone métricas de Prometheus
6. **forward**: Reenvía consultas DNS externas a upstream DNS servers
7. **cache**: Almacena en caché respuestas DNS
8. **loop**: Detecta y evita DNS loops
9. **reload**: Recarga automáticamente ante cambios en Corefile
10. **loadbalance**: Balancea carga entre múltiples registros A/AAAA

**Ejemplos de configuración personalizada:**

1.  **Usar un DNS Server específico para External Domain**:

    ```
    example.com {
        forward . 10.0.0.1
    }
    ```
2.  **Configuración de Stub Domain**:

    ```
    internal.corp {
        file /etc/coredns/internal.db
    }
    ```
3.  **Conditional Forwarding**:

    ```
    . {
        forward . 8.8.8.8 8.8.4.4 {
            policy sequential
        }
    }
    ```

**Optimización de rendimiento y escalado:**

1.  **Auto Scaling**:

    ```yaml
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: coredns
      namespace: kube-system
    spec:
      scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: coredns
      minReplicas: 2
      maxReplicas: 10
      metrics:
      - type: Resource
        resource:
          name: cpu
          target:
            type: Utilization
            averageUtilization: 60
    ```
2.  **Optimización de asignación de recursos**:

    ```yaml
    resources:
      limits:
        memory: 170Mi
      requests:
        cpu: 100m
        memory: 70Mi
    ```
3.  **Ajuste de caché**:

    ```
    cache {
        success 10000
        denial 1000
        prefetch 10 10% 2m
    }
    ```

**Troubleshooting:**

1.  **Prueba de resolución DNS**:

    ```bash
    # Create test pod
    kubectl run dnsutils --image=gcr.io/kubernetes-e2e-test-images/dnsutils:1.3 -- sleep 3600

    # Test DNS lookup
    kubectl exec -it dnsutils -- nslookup kubernetes.default
    ```
2.  **Revisar logs de CoreDNS**:

    ```bash
    kubectl logs -n kube-system -l k8s-app=kube-dns
    ```
3.  **Revisar DNS Policy**:

    ```bash
    kubectl get pods <pod-name> -o jsonpath='{.spec.dnsPolicy}'
    ```

CoreDNS es un componente crítico de los EKS clusters, que proporciona funcionalidad central de service discovery para la arquitectura de microservicios. Garantizar un servicio DNS confiable mediante configuración y monitoring adecuados es esencial.

</details>

## Hands-on Questions

### 10. Explain how to implement a service mesh (e.g., AWS App Mesh) in an Amazon EKS cluster to secure and monitor microservice communication. Include implementation steps, key components, and monitoring methods.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

Así se implementa AWS App Mesh en un Amazon EKS cluster para asegurar y monitorear la comunicación de microservicios:

### 1. AWS App Mesh Implementation Steps

#### 1.1. Set Up Prerequisites

```bash
# Set up required IAM permissions
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=appmesh-system \
  --name=appmesh-controller \
  --attach-policy-arn=arn:aws:iam::aws:policy/AWSCloudMapFullAccess,arn:aws:iam::aws:policy/AWSAppMeshFullAccess \
  --override-existing-serviceaccounts \
  --approve

# Add Helm repository
helm repo add eks https://aws.github.io/eks-charts
helm repo update
```

#### 1.2. Install App Mesh Controller

```bash
# Create App Mesh controller namespace
kubectl create ns appmesh-system

# Install App Mesh controller
helm install appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system \
  --set region=${AWS_REGION} \
  --set serviceAccount.create=false \
  --set serviceAccount.name=appmesh-controller
```

#### 1.3. Create Mesh

```yaml
# mesh.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: Mesh
metadata:
  name: my-mesh
spec:
  namespaceSelector:
    matchLabels:
      mesh: my-mesh
```

```bash
kubectl apply -f mesh.yaml
```

#### 1.4. Set Up Application Namespace

```bash
# Create and label application namespace
kubectl create ns app-namespace
kubectl label namespace app-namespace mesh=my-mesh
kubectl label namespace app-namespace appmesh.k8s.aws/sidecarInjectorWebhook=enabled
```

#### 1.5. Define Virtual Nodes and Services

```yaml
# virtual-node.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualNode
metadata:
  name: service-a
  namespace: app-namespace
spec:
  podSelector:
    matchLabels:
      app: service-a
  listeners:
    - portMapping:
        port: 8080
        protocol: http
      healthCheck:
        protocol: http
        path: "/health"
        port: 8080
        healthyThreshold: 2
        unhealthyThreshold: 2
        timeoutMillis: 2000
        intervalMillis: 5000
  backends:
    - virtualService:
        virtualServiceRef:
          name: service-b
  serviceDiscovery:
    dns:
      hostname: service-a.app-namespace.svc.cluster.local
```

```yaml
# virtual-service.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualService
metadata:
  name: service-a
  namespace: app-namespace
spec:
  awsName: service-a.app-namespace.svc.cluster.local
  provider:
    virtualRouter:
      virtualRouterRef:
        name: service-a-router
```

```yaml
# virtual-router.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: service-a-router
  namespace: app-namespace
spec:
  listeners:
    - portMapping:
        port: 8080
        protocol: http
  routes:
    - name: service-a-route
      httpRoute:
        match:
          prefix: /
        action:
          weightedTargets:
            - virtualNodeRef:
                name: service-a
              weight: 1
```

#### 1.6. Deploy Application

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-a
  namespace: app-namespace
spec:
  replicas: 3
  selector:
    matchLabels:
      app: service-a
  template:
    metadata:
      labels:
        app: service-a
    spec:
      containers:
      - name: service-a
        image: service-a:latest
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
```

### 2. Secure Communication with mTLS Configuration

#### 2.1. Set Up AWS Certificate Manager Private CA

```bash
# Create private CA
aws acm-pca create-certificate-authority \
  --certificate-authority-configuration file://ca-config.json \
  --certificate-authority-type "ROOT" \
  --idempotency-token 1234567890 \
  --tags Key=Name,Value=AppMeshCA

# Save CA ARN
export CA_ARN=$(aws acm-pca list-certificate-authorities --query 'CertificateAuthorities[?Status==`ACTIVE`].Arn' --output text)
```

#### 2.2. Add TLS Configuration

```yaml
# virtual-node-with-tls.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualNode
metadata:
  name: service-a
  namespace: app-namespace
spec:
  podSelector:
    matchLabels:
      app: service-a
  listeners:
    - portMapping:
        port: 8080
        protocol: http
      tls:
        mode: STRICT  # Enable mTLS
        certificate:
          acm:
            certificateArn: arn:aws:acm:region:account-id:certificate/certificate-id
  backends:
    - virtualService:
        virtualServiceRef:
          name: service-b
        clientPolicy:
          tls:
            enforce: true
            ports:
              - 8080
            validation:
              trust:
                acm:
                  certificateAuthorityArns:
                    - ${CA_ARN}
  serviceDiscovery:
    dns:
      hostname: service-a.app-namespace.svc.cluster.local
```

### 3. Set Up Monitoring and Observability

#### 3.1. AWS X-Ray Integration

```yaml
# mesh-with-xray.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: Mesh
metadata:
  name: my-mesh
spec:
  namespaceSelector:
    matchLabels:
      mesh: my-mesh
  egressFilter:
    type: ALLOW_ALL
  tracing:
    awsXRay:
      logLevel: INFO
```

```bash
# Deploy X-Ray daemon
kubectl apply -f https://github.com/aws/aws-app-mesh-controller-for-k8s/raw/master/config/samples/xray-daemon.yaml
```

#### 3.2. Amazon CloudWatch Integration

```yaml
# envoy-config.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: Mesh
metadata:
  name: my-mesh
spec:
  namespaceSelector:
    matchLabels:
      mesh: my-mesh
  egressFilter:
    type: ALLOW_ALL
  serviceDiscovery:
    ipPreference: IPv4_PREFERRED
  logging:
    accessLog:
      file:
        path: /dev/stdout
        format:
          json:
            - key: "source"
              value: "%DOWNSTREAM_REMOTE_ADDRESS%"
            - key: "destination"
              value: "%UPSTREAM_REMOTE_ADDRESS%"
            - key: "protocol"
              value: "%PROTOCOL%"
```

```bash
# Deploy CloudWatch agent
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cloudwatch-namespace.yaml

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cwagent/cwagent-serviceaccount.yaml

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cwagent/cwagent-configmap.yaml

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cwagent/cwagent-daemonset.yaml
```

#### 3.3. Prometheus and Grafana Setup

```bash
# Create Prometheus namespace
kubectl create namespace prometheus

# Install Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/prometheus \
  --namespace prometheus \
  --set alertmanager.persistentVolume.storageClass="gp2" \
  --set server.persistentVolume.storageClass="gp2"

# Install Grafana
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install grafana grafana/grafana \
  --namespace prometheus \
  --set persistence.storageClassName="gp2" \
  --set persistence.enabled=true \
  --set adminPassword='EKS!sAWSome' \
  --values grafana.yaml \
  --set service.type=LoadBalancer
```

```yaml
# grafana.yaml
datasources:
  datasources.yaml:
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus-server.prometheus.svc.cluster.local
      access: proxy
      isDefault: true
```

### 4. Configure Traffic Management and Advanced Features

#### 4.1. Canary Deployment Configuration

```yaml
# virtual-router-canary.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: service-a-router
  namespace: app-namespace
spec:
  listeners:
    - portMapping:
        port: 8080
        protocol: http
  routes:
    - name: service-a-route
      httpRoute:
        match:
          prefix: /
        action:
          weightedTargets:
            - virtualNodeRef:
                name: service-a-v1
              weight: 90
            - virtualNodeRef:
                name: service-a-v2
              weight: 10
```

#### 4.2. Circuit Breaker Configuration

```yaml
# virtual-node-circuit-breaker.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualNode
metadata:
  name: service-a
  namespace: app-namespace
spec:
  # ... existing configuration ...
  listeners:
    - portMapping:
        port: 8080
        protocol: http
      outlierDetection:
        baseEjectionDuration:
          unit: s
          value: 30
        interval:
          unit: s
          value: 10
        maxEjectionPercent: 50
        maxServerErrors: 5
```

#### 4.3. Retry Policy Configuration

```yaml
# virtual-router-retry.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: service-a-router
  namespace: app-namespace
spec:
  # ... existing configuration ...
  routes:
    - name: service-a-route
      httpRoute:
        match:
          prefix: /
        action:
          weightedTargets:
            - virtualNodeRef:
                name: service-a
              weight: 1
        retryPolicy:
          maxRetries: 3
          perRetryTimeout:
            unit: ms
            value: 2000
          httpRetryEvents:
            - server-error
            - gateway-error
            - client-error
            - stream-error
```

### 5. Monitoring and Troubleshooting

#### 5.1. Check Envoy Proxy Logs

```bash
# Check Envoy sidecar logs for specific pod
kubectl logs <pod-name> -c envoy -n app-namespace

# Stream all Envoy logs
kubectl logs -f -l app=service-a -c envoy -n app-namespace
```

#### 5.2. Access Envoy Admin Interface

```bash
# Set up port forwarding
kubectl port-forward <pod-name> -n app-namespace 9901:9901

# Access in browser
# http://localhost:9901/
```

#### 5.3. Check X-Ray Traces

Navega al servicio X-Ray en la AWS Management Console para ver service maps y traces.

#### 5.4. Create CloudWatch Dashboard

```bash
# Prepare JSON file for CloudWatch dashboard creation
cat > appmesh-dashboard.json << EOF
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AWS/AppMesh", "RequestCount", "MeshName", "my-mesh", "VirtualNodeName", "service-a", { "stat": "Sum" } ]
        ],
        "period": 60,
        "region": "${AWS_REGION}",
        "title": "Request Count"
      }
    },
    {
      "type": "metric",
      "x": 12,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AWS/AppMesh", "Latency", "MeshName", "my-mesh", "VirtualNodeName", "service-a", { "stat": "Average" } ]
        ],
        "period": 60,
        "region": "${AWS_REGION}",
        "title": "Latency"
      }
    }
  ]
}
EOF

# Create dashboard using AWS CLI
aws cloudwatch put-dashboard --dashboard-name AppMeshDashboard --dashboard-body file://appmesh-dashboard.json
```

### 6. Best Practices and Considerations

#### 6.1. Resource Requirements

* Planifica los recursos de los nodes, ya que el sidecar Envoy se agrega a cada pod
* Normalmente asigna 100-200m CPU y 128-256Mi de memoria a cada Envoy proxy

#### 6.2. Gradual Implementation Strategy

1. **Enfoque por fases**:
   * Comienza con services no críticos para el negocio
   * Evalúa el impacto con traffic mirroring
   * Expande gradualmente después de una validación exitosa
2. **Implementación de mTLS**:
   * Comienza con modo PERMISSIVE
   * Verifica que todos los services sean compatibles
   * Cambia a modo STRICT

#### 6.3. Performance Optimization

* Ajusta los resource limits de Envoy
* Configura intervalos adecuados de health check
* Minimiza logging y tracing innecesarios

#### 6.4. Security Hardening

* Usa políticas IAM de least privilege
* Rotación regular de certificados
* Implementa defense in depth con network policies

AWS App Mesh proporciona una potente solución de service mesh para asegurar y monitorear la comunicación de microservicios en EKS clusters. Una configuración y monitoring adecuados pueden mejorar significativamente la confiabilidad, seguridad y observabilidad de las aplicaciones.

</details>
