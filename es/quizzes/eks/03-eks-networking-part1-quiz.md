# Cuestionario de networking de EKS - Parte 1

Este cuestionario evalúa tu comprensión de los conceptos básicos de networking en Amazon EKS, VPC CNI, network policies y service discovery. Se centra en la arquitectura y los componentes de networking de los clusters de EKS.

## Preguntas de opción múltiple

### 1. ¿Cuál es el plugin CNI (Container Network Interface) predeterminado que se usa en Amazon EKS?

A. Calico B. Flannel C. Amazon VPC CNI D. Weave Net

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C. Amazon VPC CNI**

**Explicación:** Amazon EKS usa el plugin Amazon VPC CNI de forma predeterminada. Este plugin asigna direcciones IP de VPC a los pods de Kubernetes y permite la comunicación entre pods usando las características nativas del networking de AWS VPC.

**Características clave:**

1. **Networking nativo de VPC**: Cada pod recibe una dirección IP única dentro de la VPC. Esto permite que los pods se comuniquen directamente con otros servicios dentro de la VPC.
2. **Asignación de direcciones IP secundarias**: Las direcciones IP secundarias se asignan a la Elastic Network Interface (ENI) de cada node y se proporcionan a los pods.
3. **Integración con Security Groups**: Los AWS security groups pueden aplicarse a nivel de pod, lo que permite un control de seguridad de red granular.
4. **Rendimiento**: El rendimiento de red mejora al no usar overlay networks.
5. **Integración con servicios de AWS**: Se integra sin problemas con otros servicios de AWS como AWS Load Balancer Controller y AWS App Mesh.

**Ejemplo de configuración:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-network-policy: "true"
  enable-pod-eni: "true"
  warm-ip-target: "5"
  minimum-ip-target: "10"
```

Amazon VPC CNI es open source y se administra en GitHub. Puede reemplazarse por otros plugins CNI como Calico o Cilium según sea necesario, pero Amazon VPC CNI es la opción predeterminada para EKS y cuenta con soporte oficial de AWS.

</details>

### 2. ¿Cómo asigna VPC CNI direcciones IP a los pods en Amazon EKS?

A. Asigna una Elastic Network Interface (ENI) separada a cada pod B. Asigna direcciones IP secundarias a la Elastic Network Interface (ENI) del node y las proporciona a los pods C. Usa overlay networks para asignar direcciones IP virtuales D. Asigna una subnet de VPC separada a cada pod

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. Asigna direcciones IP secundarias a la Elastic Network Interface (ENI) del node y las proporciona a los pods**

**Explicación:** Amazon VPC CNI funciona asignando direcciones IP secundarias a la Elastic Network Interface (ENI) del node y proporcionando estas direcciones IP a los pods. Este método también se llama modelo "IP-per-Pod".

**Cómo funciona:**

1. **Asignación de ENI**: Cada instancia EC2 (node) puede tener una o más ENIs. La cantidad de direcciones IP que pueden asignarse por ENI está determinada por el tipo de instancia.
2. **Administración del pool de direcciones IP**: El DaemonSet `aws-node` de VPC CNI se ejecuta en cada node y administra el pool de direcciones IP disponibles.
3. **Asignación de direcciones IP**: Cuando se crea un pod, el CNI asigna una dirección IP del pool y la conecta al namespace de red del pod.
4. **Recuperación de direcciones IP**: Cuando un pod termina, el CNI recupera la dirección IP y la devuelve al pool.

**Configuración de ejemplo:**

```bash
# Maximum pods per node calculation
Maximum pods = (Number of ENIs × (IP addresses per ENI - 1)) + 2

# For m5.large instance
# Number of ENIs: 3, IP addresses per ENI: 10
Maximum pods = (3 × (10 - 1)) + 2 = 29
```

**Consideraciones clave:**

1. **Límite de direcciones IP**: La cantidad máxima de pods que pueden ejecutarse por node está limitada según el tipo de instancia.
2. **Warm IPs**: VPC CNI puede preasignar una cierta cantidad de direcciones IP mediante la configuración `WARM_IP_TARGET` para reducir el tiempo de inicio de los pods.
3. **Prefix Delegation**: Las versiones más recientes de VPC CNI admiten la característica de prefix delegation, que asigna bloques CIDR /28 (16 IPs) a cada ENI, aumentando la densidad de direcciones IP.
4. **Security Groups**: Habilitar la configuración `ENABLE_POD_ENI` permite configurar security groups separados para pods específicos (característica Security Groups for Pods).

Problemas con las otras opciones:

* **A**: Por lo general, no se asigna una ENI separada a cada pod. Esto es ineficiente debido a los límites de ENI por instancia EC2.
* **C**: VPC CNI no usa overlay networks. Esta es una característica de otros plugins CNI como Flannel o Weave Net.
* **D**: No es posible asignar una subnet de VPC separada a cada pod en la arquitectura de AWS VPC.

</details>

### 3. ¿Por qué la comunicación pod a pod en Amazon EKS ocurre directamente dentro de la VPC sin salir al exterior?

A. Porque todos los pods se encuentran en la misma subnet B. Porque los pods comparten el namespace de red del node C. Porque a los pods se les asignan directamente direcciones IP de VPC D. Porque la comunicación pod a pod siempre pasa por un service mesh

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C. Porque a los pods se les asignan directamente direcciones IP de VPC**

**Explicación:** La razón principal por la que la comunicación pod a pod en Amazon EKS ocurre directamente dentro de la VPC sin salir al exterior es que el plugin Amazon VPC CNI asigna directamente direcciones IP de VPC a cada pod.

**Mecanismos clave:**

1. **Asignación de direcciones IP de VPC**: Cada pod recibe una dirección IP única de la subnet de VPC. Esta dirección IP es una dirección IP secundaria conectada a la ENI del node.
2. **Enrutamiento directo**: Como los pods tienen direcciones IP de VPC, pueden comunicarse directamente con otros recursos en la VPC (otros pods, instancias EC2, bases de datos RDS, etc.).
3. **Tablas de enrutamiento de VPC**: La comunicación pod a pod sigue las tablas de enrutamiento de VPC y se enruta directamente dentro de la misma VPC sin salir al exterior.

**Ventajas:**

1. **Rendimiento de red**: Latencia reducida y throughput mejorado al no usar overlay networks ni NAT.
2. **Seguridad**: Puede aprovechar mecanismos de seguridad de red existentes de AWS, como VPC security groups y network ACLs.
3. **Visibilidad**: Puede monitorear y analizar el tráfico pod a pod mediante VPC Flow Logs.
4. **Integración con servicios de AWS**: Como los pods tienen direcciones IP de VPC, se integran sin problemas con servicios de AWS como VPC endpoints y PrivateLink.

**Escenario de ejemplo:**

Cuando Pod A (IP: 10.0.1.23) se comunica con Pod B (IP: 10.0.2.45):

1. Pod A envía paquetes directamente a la dirección IP de Pod B (10.0.2.45).
2. Los paquetes se enrutan según la tabla de enrutamiento de VPC.
3. Los paquetes llegan directamente a Pod B dentro de la VPC.
4. Durante todo este proceso, los paquetes no salen de la VPC.

Problemas con las otras opciones:

* **A**: Los pods pueden distribuirse entre varias subnets, y los pods en subnets diferentes aún pueden comunicarse directamente dentro de la VPC.
* **B**: Los pods no comparten el namespace de red del node. Cada pod tiene su propio namespace de red.
* **D**: La comunicación pod a pod no siempre pasa por un service mesh. Service mesh es una capa adicional opcional.

</details>

### 4. ¿Cuál es el recurso de Kubernetes más apropiado para controlar el tráfico entrante y saliente hacia los pods en Amazon EKS?

A. Service B. Ingress C. NetworkPolicy D. SecurityContext

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C. NetworkPolicy**

**Explicación:** El recurso de Kubernetes más apropiado para controlar el tráfico entrante y saliente hacia los pods en Amazon EKS es NetworkPolicy. NetworkPolicy es el mecanismo de seguridad de red de Kubernetes que permite un control granular de la comunicación entre pods.

**Características clave de NetworkPolicy:**

1. **Aplicación selectiva**: Puede aplicar policies a pods específicos usando label selectors.
2. **Reglas de entrada y salida**: Puede controlar tanto el tráfico ingress (entrante) como egress (saliente).
3. **Selectores variados**: Puede filtrar tráfico según namespaces, labels, bloques CIDR de IP, puertos, etc.
4. **Default Deny Policy**: El tráfico que no está permitido explícitamente se deniega de forma predeterminada.

**Ejemplo de NetworkPolicy:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          purpose: frontend
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          purpose: database
    ports:
    - protocol: TCP
      port: 5432
```

**Implementación de NetworkPolicy en EKS:**

Para usar NetworkPolicy en Amazon EKS, se requiere un plugin CNI que admita network policies. El Amazon VPC CNI predeterminado no admite directamente network policies, por lo que se necesita configuración adicional:

1.  **Instalar Calico**: Calico es la forma más común de implementar NetworkPolicy en EKS.

    ```bash
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
    ```
2.  **Habilitar Network Policy en Amazon VPC CNI**: Las versiones más recientes de Amazon VPC CNI proporcionan soporte para network policy.

    ```bash
    kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
    ```

Problemas con las otras opciones:

* **A. Service**: Service proporciona acceso de red a los pods, pero no tiene capacidades de control o filtrado de tráfico.
* **B. Ingress**: Ingress se usa para enrutar tráfico HTTP/HTTPS a services dentro del cluster, pero no define network policies generales.
* **D. SecurityContext**: SecurityContext define configuraciones de seguridad a nivel de pod o container, pero no está relacionado con el control de tráfico de red.

</details>

### 5. ¿Qué servicio DNS se usa para service discovery dentro de un cluster de EKS?

A. Amazon Route 53 B. CoreDNS C. kube-dns D. AWS Cloud Map

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. CoreDNS**

**Explicación:** El servicio DNS que se usa de forma predeterminada para service discovery dentro de los clusters de Amazon EKS es CoreDNS. CoreDNS es un servidor DNS flexible y extensible que proporciona service discovery basado en DNS dentro de clusters de Kubernetes.

**Características clave de CoreDNS:**

1. **Integración con Kubernetes**: CoreDNS se integra con la Kubernetes API para crear automáticamente registros DNS para services y pods.
2. **Arquitectura de plugins**: CoreDNS puede extender su funcionalidad mediante varios plugins.
3. **Alta disponibilidad**: En EKS, CoreDNS normalmente se implementa con varias replicas para garantizar alta disponibilidad.
4. **Configurabilidad**: Se pueden configurar varios ajustes de DNS mediante el Corefile.

**Deployment de CoreDNS en EKS:**

Cuando creas un cluster de EKS, CoreDNS se implementa automáticamente. CoreDNS se ejecuta como un Deployment en el namespace `kube-system`:

```bash
kubectl get deployment coredns -n kube-system
```

**Ejemplo de configuración de CoreDNS:**

La configuración de CoreDNS se almacena en un ConfigMap:

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

**Cómo funciona Service Discovery:**

1. **Creación de Service**: Cuando se crea un Kubernetes Service, CoreDNS crea automáticamente un registro DNS.
2. **Formato de nombre DNS**:
   * Service: `<service-name>.<namespace>.svc.cluster.local`
   * Pod: `<pod-ip>.<namespace>.pod.cluster.local`
3. **Consulta DNS**: Cuando un pod dentro del cluster realiza una consulta DNS con un nombre de service, CoreDNS responde con el ClusterIP de ese service.

**Ejemplo:**

```bash
# If my-service service exists in the default namespace
nslookup my-service.default.svc.cluster.local

# Result
Name:   my-service.default.svc.cluster.local
Address: 10.100.43.150  # Service's ClusterIP
```

**Escalado y optimización de CoreDNS:**

En EKS, CoreDNS no escala automáticamente con el tamaño del cluster, por lo que en clusters grandes puede ser necesario escalar manualmente:

```bash
kubectl scale deployment coredns --replicas=4 -n kube-system
```

Además, puedes optimizar el rendimiento ajustando la configuración de caché:

```yaml
cache {
    success 10000
    denial 1000
    prefetch 10 10m 20%
}
```

Problemas con las otras opciones:

* **A. Amazon Route 53**: Route 53 es el servicio DNS de AWS, pero no se usa de forma predeterminada para service discovery dentro de clusters de EKS.
* **C. kube-dns**: kube-dns se usaba en versiones anteriores de Kubernetes, pero fue reemplazado por CoreDNS en EKS.
* **D. AWS Cloud Map**: Cloud Map es el servicio de service discovery de AWS, pero no se usa como el servicio DNS predeterminado dentro de clusters de EKS.

</details>

## Preguntas de respuesta corta

### 6. ¿Cuál es el factor principal que limita la cantidad máxima de pods por node en un cluster de Amazon EKS y qué métodos se pueden usar para aumentarla?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** El factor principal que limita la cantidad máxima de pods por node en un cluster de Amazon EKS es **la cantidad de ENIs (Elastic Network Interfaces) por tipo de instancia EC2 y la cantidad de direcciones IP asignables por ENI**. El método principal para aumentarla es **habilitar la característica Prefix Delegation**.

**Explicación detallada:**

1.  **Fórmula de cálculo de pods máximos por node**:

    ```
    Maximum pods = (Number of ENIs × (IP addresses per ENI - 1)) + 2
    ```

    * La primera dirección IP de cada ENI está reservada para el propio node.
    * Los 2 adicionales son para los pods kube-proxy y aws-node.
2. **Ejemplos de límites por tipo de instancia**:
   * **t3.small**: (3 ENIs × (4 IPs - 1)) + 2 = 11 pods
   * **m5.large**: (3 ENIs × (10 IPs - 1)) + 2 = 29 pods
   * **c5.4xlarge**: (8 ENIs × (30 IPs - 1)) + 2 = 234 pods
3.  **Expansión mediante Prefix Delegation**: Prefix delegation es una característica que asigna bloques CIDR /28 (16 IPs) en lugar de direcciones IP individuales a cada ENI.

    **Cómo habilitarlo**:

    ```bash
    # Modify ConfigMap
    kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

    # Optionally set prefix allocation mode
    kubectl set env daemonset aws-node -n kube-system WARM_PREFIX_TARGET=1
    ```

    **Fórmula de cálculo después de habilitar Prefix Delegation**:

    ```
    Maximum pods = (Number of ENIs × (Prefixes per ENI × IPs per prefix - 1)) + 2
    ```

    Ejemplo: m5.large con prefix delegation habilitado

    * Sin prefix delegation: 29 pods
    * Con prefix delegation habilitado: (3 ENIs × (1 prefix × 16 IPs - 1)) + 2 = 47 pods
4. **Otros métodos para aumentar el conteo máximo de pods**:
   * **Usar tipos de instancia más grandes**: Cambiar a tipos de instancia que admitan más ENIs y direcciones IP
   * **Configuración CNI personalizada**: Ajustar la configuración de kubelet usando el flag `--max-pods` (no recomendado)
   * **Usar plugins CNI alternativos**: Cambiar a plugins CNI que usan overlay networks como Calico, Cilium
5. **Consideraciones**:
   * Prefix delegation solo se admite en instancias EC2 basadas en Nitro.
   * Cuando prefix delegation está habilitado, no se puede usar la característica SecurityGroupsForPods.
   * A medida que aumenta la cantidad de pods por node, puede producirse contención de recursos del node (CPU, memoria), por lo que es importante seleccionar un tamaño de instancia adecuado.
6.  **Monitoreo y optimización**:

    ```bash
    # Check current IP address usage
    kubectl exec -n kube-system ds/aws-node -- curl -s http://localhost:61679/v1/enis | jq

    # Check prefix delegation status
    kubectl describe daemonset aws-node -n kube-system | grep PREFIX
    ```

Aunque habilitar prefix delegation puede aumentar significativamente el conteo máximo de pods por node, es importante elegir la configuración adecuada según los requisitos del cluster y las características de las cargas de trabajo.

</details>

### 7. ¿Cómo se llama la característica que permite asignar AWS security groups específicos a pods en Amazon EKS y cómo se configura?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** La característica que permite asignar AWS security groups específicos a pods en Amazon EKS se llama **Security Groups for Pods** o **Pod ENI (Elastic Network Interface)**. Esta característica se puede configurar habilitando la opción **ENABLE\_POD\_ENI** en VPC CNI.

**Explicación detallada:**

1. **Descripción general de Security Groups for Pods**: Esta característica crea una ENI separada (también llamada trunk ENI) para pods específicos y adjunta security groups a esta ENI, lo que permite un control de seguridad de red granular a nivel de pod.
2. **Prerrequisitos**:
   * Versión 1.7.7 o superior del plugin Amazon VPC CNI
   * Versión 1.17 o superior de Kubernetes
   * Instancias EC2 basadas en Nitro
   * La característica de prefix delegation debe estar deshabilitada
3.  **Pasos de configuración**:

    a. **Habilitar la característica Pod ENI en VPC CNI**:

    ```bash
    kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true
    ```

    b. **Crear el recurso SecurityGroupPolicy**:

    ```yaml
    apiVersion: vpcresources.k8s.aws/v1beta1
    kind: SecurityGroupPolicy
    metadata:
      name: allow-db-access
      namespace: app
    spec:
      podSelector:
        matchLabels:
          role: db-client
      securityGroups:
        groupIds:
          - sg-0123456789abcdef0
    ```

    c. **Otorgar permisos IAM al Service Account**: El service account de VPC CNI necesita los siguientes permisos:

    * ec2:CreateNetworkInterface
    * ec2:DeleteNetworkInterface
    * ec2:DescribeNetworkInterfaces
    * ec2:DescribeSecurityGroups
    * ec2:ModifyNetworkInterfaceAttribute
    * ec2:CreateTags
4.  **Ejemplo de configuración de Pod**:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: db-client
      namespace: app
      labels:
        role: db-client
    spec:
      containers:
      - name: app
        image: amazonlinux:2
        command: ['sleep', '3600']
    ```
5. **Cómo funciona**:
   * Cuando se crea un pod con labels que coinciden con una SecurityGroupPolicy, VPC CNI crea una branch ENI para ese pod.
   * Los security groups especificados se adjuntan a esta branch ENI.
   * El tráfico del pod se enruta a través de esta branch ENI, y se aplican las reglas de security group adjuntas.
6.  **Métodos de verificación**:

    ```bash
    # Check pod's ENI information
    kubectl describe pod db-client -n app

    # Check SecurityGroupPolicy
    kubectl get securitygrouppolicy -n app

    # Check VPC CNI logs
    kubectl logs -n kube-system -l k8s-app=aws-node
    ```
7. **Limitaciones**:
   * Hay límites en la cantidad de branch ENIs por node (varía según el tipo de instancia).
   * No se puede usar junto con la característica de prefix delegation.
   * Los security groups no pueden cambiarse después de que se crea el pod.
   * El tiempo de inicio del pod puede aumentar ligeramente.
8. **Casos de uso**:
   * Pods que acceden a servicios de AWS que controlan el acceso con security groups como RDS, ElastiCache
   * Cuando se necesita control granular del tráfico entrante/saliente para pods específicos
   * Workloads que requieren aislamiento de red según requisitos regulatorios

La característica Security Groups for Pods es una herramienta potente para mejorar la seguridad de networking de EKS, pero debe usarse de forma adecuada considerando el overhead de recursos por el uso de ENIs adicionales y sus limitaciones.

</details>

### 8. Al usar Service de tipo LoadBalancer en Amazon EKS, ¿qué tipo de load balancer crea AWS Load Balancer Controller de forma predeterminada y cómo se cambia?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** Al usar Service de tipo LoadBalancer en Amazon EKS, AWS Load Balancer Controller crea un **Classic Load Balancer (CLB)** de forma predeterminada. Para cambiarlo a un **Network Load Balancer (NLB)**, debes agregar una **annotation** específica al service.

**Explicación detallada:**

1. **Comportamiento predeterminado**: Cuando creas un Kubernetes Service de tipo `LoadBalancer`, el AWS cloud controller manager aprovisiona un Classic Load Balancer de forma predeterminada.
2.  **Cómo cambiar a Network Load Balancer**: Agrega la siguiente annotation al Service:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
    ```
3.  **Ejemplo completo de Service (usando NLB)**:

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-type: nlb
    spec:
      type: LoadBalancer
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: my-app
    ```
4.  **Configuración de Load Balancer interno**: De forma predeterminada, los load balancers creados son internet-facing. Para configurarlo como load balancer interno:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    ```
5.  **Opciones de configuración adicionales**:

    a. **Configuración de Target Type (IP Mode)**:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    ```

    b. **Especificar Security Groups**:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-security-groups: sg-0123456789abcdef0
    ```

    c. **Especificar Subnets**:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-subnets: subnet-0123456789abcdef0,subnet-0123456789abcdef1
    ```

    d. **Deshabilitar Cross-Zone Load Balancing**:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "false"
    ```

    e. **Habilitar Access Logs**:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-access-log-enabled: "true"
    service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-name: "my-elb-logs"
    service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-prefix: "my-app"
    ```

    f. **Configuración de certificado SSL (HTTPS)**:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: arn:aws:acm:region:account-id:certificate/certificate-id
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
    ```
6.  **Uso de AWS Load Balancer Controller**: En clusters de EKS más recientes, puedes usar AWS Load Balancer Controller para aprovechar más características:

    a. **Instalación**:

    ```bash
    helm repo add eks https://aws.github.io/eks-charts
    helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
      -n kube-system \
      --set clusterName=my-cluster \
      --set serviceAccount.create=false \
      --set serviceAccount.name=aws-load-balancer-controller
    ```

    b. **Uso de Application Load Balancer (ALB) con Ingress**:

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: my-ingress
      annotations:
        kubernetes.io/ingress.class: alb
        alb.ingress.kubernetes.io/scheme: internet-facing
    spec:
      rules:
      - http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-service
                port:
                  number: 80
    ```
7.  **Comparación de tipos de Load Balancer**:

    | Característica          | Classic Load Balancer | Network Load Balancer | Application Load Balancer |
    | ----------------------- | --------------------- | --------------------- | ------------------------- |
    | Protocolo               | TCP, SSL, HTTP, HTTPS | TCP, UDP, TLS         | HTTP, HTTPS               |
    | Capa                    | 4 & 7                 | 4                     | 7                         |
    | Rendimiento             | Bueno                 | Muy bueno             | Bueno                     |
    | Latencia                | Media                 | Muy baja              | Baja                      |
    | IP estática             | No                    | Sí                    | No                        |
    | Enrutamiento por path   | No                    | No                    | Sí                        |
    | WebSockets              | Limitado              | Sí                    | Sí                        |
    | Targets basados en containers | No             | Sí (IP mode)          | Sí (IP mode)              |
8. **Prácticas recomendadas**:
   * Usa Ingress con ALB para la mayoría del tráfico HTTP/HTTPS
   * Usa NLB para tráfico TCP/UDP o cuando se necesita throughput muy alto
   * A menos que existan aplicaciones legacy o requisitos especiales, usa NLB o ALB en lugar de CLB
   * Habilita siempre cross-zone load balancing en entornos de producción

Usar AWS Load Balancer Controller permite una administración más eficaz de los load balancers de AWS mediante Kubernetes Services y recursos Ingress, con configuración granular posible mediante varias annotations.

</details>

## Preguntas prácticas

### 9. Escribe una NetworkPolicy que permita la comunicación solo entre pods dentro de un namespace específico y bloquee la comunicación con pods de otros namespaces en un cluster de Amazon EKS.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** La siguiente es una NetworkPolicy que permite la comunicación solo entre pods dentro de un namespace específico y bloquea la comunicación con pods de otros namespaces:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: restrict-to-same-namespace
  namespace: app-namespace  # Namespace name to apply
spec:
  podSelector: {}  # Apply to all pods in the namespace
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: app-namespace  # Same namespace
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: app-namespace  # Same namespace
  # Allow DNS lookups (to CoreDNS in kube-system)
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

**Explicación detallada:**

1. **Explicación de componentes de NetworkPolicy**:
   * **metadata.namespace**: Especifica el namespace donde se aplicará esta policy.
   * **spec.podSelector: {}**: Un selector de pod vacío aplica la policy a todos los pods del namespace.
   * **policyTypes**: Controla tanto el tráfico Ingress (entrante) como Egress (saliente).
   * **ingress.from.namespaceSelector**: Permite tráfico solo desde el mismo namespace.
   * **egress.to.namespaceSelector**: Permite tráfico solo hacia el mismo namespace.
   * **Allow DNS Lookups**: Permite tráfico DNS hacia CoreDNS en el namespace kube-system.
2.  **Pasos de implementación**:

    a. **Crear Namespace**:

    ```bash
    kubectl create namespace app-namespace
    ```

    b. **Agregar Label al Namespace** (se agrega automáticamente en Kubernetes 1.21+):

    ```bash
    kubectl label namespace app-namespace kubernetes.io/metadata.name=app-namespace
    ```

    c. **Aplicar NetworkPolicy**:

    ```bash
    kubectl apply -f network-policy.yaml
    ```

    d. **Verificar Policy**:

    ```bash
    kubectl describe networkpolicy restrict-to-same-namespace -n app-namespace
    ```
3.  **Método de prueba**:

    a. **Implementar Pod de prueba en el mismo Namespace**:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: test-pod-1
      namespace: app-namespace
    spec:
      containers:
      - name: busybox
        image: busybox
        command: ['sleep', '3600']
    ```

    b. **Implementar Pod de prueba en un Namespace diferente**:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: test-pod-2
      namespace: default
    spec:
      containers:
      - name: busybox
        image: busybox
        command: ['sleep', '3600']
    ```

    c. **Prueba de conexión**:

    ```bash
    # Test communication within same namespace (should succeed)
    kubectl exec -n app-namespace test-pod-1 -- ping -c 2 $(kubectl get pod test-pod-3 -n app-namespace -o jsonpath='{.status.podIP}')

    # Test communication to other namespace (should fail)
    kubectl exec -n app-namespace test-pod-1 -- ping -c 2 $(kubectl get pod test-pod-2 -n default -o jsonpath='{.status.podIP}')
    ```
4.  **Notas y consideraciones**:

    a. **Verificar soporte de NetworkPolicy**: Para usar NetworkPolicy en Amazon EKS, se requiere un plugin CNI que admita network policies:

    ```bash
    # Install Calico
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml

    # Or enable network policy in Amazon VPC CNI
    kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
    ```

    b. **Default Deny Policy**: Cuando se aplica NetworkPolicy, todo el tráfico que no está explícitamente permitido se deniega de forma predeterminada.

    c. **Permitir acceso DNS**: Debes permitir tráfico hacia CoreDNS en el namespace kube-system para que los pods puedan realizar consultas DNS.

    d. **Acceso a servicios del sistema**: Puede que necesites permitir acceso a servicios del sistema como el Kubernetes API server y servicios de monitoreo según sea necesario.
5.  **Extensiones y mejoras**:

    a. **Permitir comunicación solo entre pods específicos**:

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-specific-pods
      namespace: app-namespace
    spec:
      podSelector:
        matchLabels:
          app: web
      policyTypes:
      - Ingress
      ingress:
      - from:
        - podSelector:
            matchLabels:
              app: api
    ```

    b. **Permitir solo puertos específicos**:

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-specific-ports
      namespace: app-namespace
    spec:
      podSelector: {}
      policyTypes:
      - Ingress
      ingress:
      - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: app-namespace
        ports:
        - protocol: TCP
          port: 8080
    ```

    c. **Permitir acceso a servicios externos**:

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-external-service
      namespace: app-namespace
    spec:
      podSelector:
        matchLabels:
          app: web
      policyTypes:
      - Egress
      egress:
      - to:
        - ipBlock:
            cidr: 10.0.0.0/16  # VPC CIDR
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
            - 10.0.0.0/8
            - 172.16.0.0/12
            - 192.168.0.0/16
    ```

Usar NetworkPolicy permite implementar un control de seguridad de red granular dentro de clusters de EKS, lo que resulta especialmente útil en entornos multi-tenant o workloads con requisitos regulatorios.

</details>

## Preguntas avanzadas

### 10. Explica varias estrategias para resolver el problema de agotamiento de direcciones IP con VPC CNI en un cluster de Amazon EKS y compara las ventajas y desventajas de cada enfoque.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** Las siguientes son varias estrategias para resolver el problema de agotamiento de direcciones IP con VPC CNI en un cluster de Amazon EKS y las ventajas y desventajas de cada enfoque:

### 1. Habilitar Prefix Delegation

**Descripción**: Una característica que asigna bloques CIDR /28 (16 IPs) en lugar de direcciones IP individuales a cada ENI.

**Método de implementación**:

```bash
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
```

**Ventajas**:

* Aumenta significativamente las direcciones IP disponibles por node (hasta 5x)
* Compatible con las características existentes de VPC CNI
* Velocidad de asignación de direcciones IP mejorada

**Desventajas**:

* Solo se admite en instancias EC2 basadas en Nitro
* No se puede usar junto con la característica Security Groups for Pods
* Posibles problemas de compatibilidad con algunos servicios de AWS

### 2. Habilitar Custom Networking Mode

**Descripción**: Una característica que asigna direcciones IP de pod desde subnets separadas en lugar de la subnet donde se encuentran los nodes.

**Método de implementación**:

```bash
kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
kubectl set env daemonset aws-node -n kube-system ENI_CONFIG_LABEL_DEF=failure-domain.beta.kubernetes.io/zone
```

Crear ENIConfig para cada availability zone:

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  securityGroups:
    - sg-0123456789abcdef0
  subnet: subnet-0123456789abcdef0
```

**Ventajas**:

* Evita el agotamiento de direcciones IP de las subnets de nodes
* Permite configuración de subnet dedicada para networking de pods
* Puede usar bloques CIDR más grandes

**Desventajas**:

* Configuración y administración complejas
* Se requieren subnets adicionales
* Se necesita reconfigurar ENIConfig cuando se reemplazan nodes

### 3. Agregar bloques CIDR secundarios

**Descripción**: Agregar bloques CIDR secundarios a la VPC y asignarlos a nuevas subnets para ampliar el espacio de direcciones IP.

**Método de implementación**:

1. Agregar un bloque CIDR secundario a la VPC mediante la consola de AWS o CLI
2. Crear nuevas subnets en el bloque CIDR secundario
3. Usarlo junto con custom networking mode

**Ventajas**:

* Amplía en gran medida el espacio de direcciones IP de la VPC existente
* Puede implementarse sin afectar la infraestructura existente
* Puede usar bloques CIDR más grandes

**Desventajas**:

* Mayor complejidad de configuración de networking con VPC peering, Transit Gateway, etc.
* Se requieren actualizaciones de tablas de enrutamiento
* Es posible que algunos servicios de AWS no admitan completamente CIDRs secundarios

### 4. Usar plugins CNI alternativos

**Descripción**: Usar plugins CNI alternativos como Calico o Cilium en lugar de Amazon VPC CNI.

**Método de implementación**:

```bash
# Calico installation example
kubectl apply -f https://docs.projectcalico.org/manifests/calico-vxlan.yaml

# Disable Amazon VPC CNI
kubectl patch daemonset aws-node -n kube-system -p '{"spec": {"template": {"spec": {"nodeSelector": {"non-existing": "true"}}}}}'
```

**Ventajas**:

* Resuelve las limitaciones de direcciones IP mediante overlay networks
* Características de network policy más completas
* Networking independiente del cloud provider

**Desventajas**:

* Falta de integración con características nativas de AWS (security groups, etc.)
* Posible overhead de rendimiento
* Complejidad adicional de administración
* Fuera del alcance del soporte de AWS

### 5. Usar CIDRs de subnet más grandes

**Descripción**: Usar subnets con bloques CIDR más grandes al crear clusters.

**Método de implementación**: Al crear nuevos clusters, usar subnets con bloques CIDR más grandes (por ejemplo, /16 o /17)

**Ventajas**:

* Implementación simple
* No se necesita configuración adicional
* Todas las características existentes de VPC CNI disponibles

**Desventajas**:

* Difícil de aplicar a clusters existentes
* Posible uso ineficiente del espacio de direcciones IP
* Se requieren cambios en el diseño de VPC

### 6. Optimizar la configuración de Warm IP y Minimum IP

**Descripción**: Mejorar la eficiencia del uso de direcciones IP optimizando el comportamiento de asignación de direcciones IP de VPC CNI.

**Método de implementación**:

```bash
# Set warm IP target
kubectl set env daemonset aws-node -n kube-system WARM_IP_TARGET=5

# Set minimum IP target
kubectl set env daemonset aws-node -n kube-system MINIMUM_IP_TARGET=10

# Set maximum ENI
kubectl set env daemonset aws-node -n kube-system MAX_ENI=5
```

**Ventajas**:

* Puede implementarse con un ajuste simple de la configuración existente
* No se necesitan cambios de infraestructura adicionales
* Eficiencia mejorada en la asignación de direcciones IP

**Desventajas**:

* Puede no resolver completamente el problema de escasez de direcciones IP
* Posibles retrasos en el inicio de pods
* Efectividad limitada según el tipo de node

### 7. Enfoque híbrido

**Descripción**: Usar una combinación de varias estrategias. Por ejemplo, usar prefix delegation junto con custom networking o mover algunas workloads a Fargate.

**Método de implementación**: Aplicar selectivamente varias estrategias según las características de las workloads

**Ventajas**:

* Solución optimizada para las características de las workloads
* Eficiencia de recursos mejorada
* Implementación gradual posible

**Desventajas**:

* Mayor complejidad de configuración y administración
* Necesidad de comprender varios modelos de networking
* Mayor dificultad de troubleshooting

### 8. Usar Fargate

**Descripción**: Usar Fargate en lugar de workloads basadas en nodes para delegar la administración de direcciones IP a AWS.

**Método de implementación**:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  labels:
    fargate: "true"

---
apiVersion: eks.amazonaws.com/v1alpha1
kind: FargateProfile
metadata:
  name: my-fargate-profile
  namespace: default
spec:
  selectors:
  - namespace: my-app
```

**Ventajas**:

* Elimina el overhead de administración de direcciones IP
* No se necesita administración de nodes
* Escalabilidad serverless

**Desventajas**:

* Posible aumento de costos
* Algunas limitaciones de características de Kubernetes (DaemonSets, containers privilegiados, etc.)
* No es adecuado para todas las workloads

### Enfoques recomendados y prácticas recomendadas

1. **Evaluar la situación actual**:
   * Analizar el uso actual de direcciones IP y la tasa de crecimiento esperada
   * Comprender las características y requisitos de las workloads
   * Revisar la configuración de red existente
2. **Soluciones a corto plazo**:
   * Habilitar prefix delegation (el método más simple y eficaz)
   * Optimizar la configuración de warm IP y minimum IP
   * Limpiar pods innecesarios
3. **Soluciones a mediano y largo plazo**:
   * Configurar custom networking
   * Agregar bloques CIDR secundarios
   * Implementar un enfoque híbrido
4. **Monitoreo y alertas**:
   * Monitorear el uso de direcciones IP
   * Configurar alertas basadas en umbrales
   * Revisiones periódicas de planificación de capacidad
5. **Automatización**:
   * Automatizar el monitoreo y reporting del uso de direcciones IP
   * Ajustar automáticamente la configuración de red cuando el cluster escala
   * Establecer documentación y procedimientos operativos

El agotamiento de direcciones IP es un problema común a medida que los clusters de EKS crecen, y se deben seleccionar o combinar estrategias adecuadas según la escala del cluster y las características de las workloads. Prefix delegation es la solución más simple y eficaz en la mayoría de los casos, pero puede que se necesite un diseño de red más completo a largo plazo.

</details>
