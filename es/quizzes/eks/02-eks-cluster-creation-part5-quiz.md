# Cuestionario sobre la creación de clústeres EKS - Parte 5

Este cuestionario evalúa tu comprensión de la configuración avanzada, la optimización y las mejores prácticas operativas para clústeres de Amazon EKS. Se centra en la optimización de costos, el diseño de alta disponibilidad, la mejora de la seguridad y la automatización operativa.

## Preguntas de opción múltiple

### 1. ¿Cuál es la forma más efectiva de optimizar costos en un clúster de Amazon EKS?

A. Ejecutar todos los worker nodes como instancias On-Demand B. Usar una combinación de instancias Spot e instancias On-Demand C. Ejecutar todos los worker nodes como instancias Reserved D. Ejecutar todos los worker nodes en Fargate

<details>

<summary>Respuesta y explicación</summary>

**Respuesta: B. Usar una combinación de instancias Spot e instancias On-Demand**

**Explicación:** La forma más efectiva de optimizar costos en un clúster EKS es usar una combinación de instancias Spot e instancias On-Demand:

* **Instancias Spot**: Hasta un 90% más baratas que los precios On-Demand, pero pueden interrumpirse cuando AWS reclama capacidad. Adecuadas para cargas de trabajo sin estado y tolerantes a fallos.
* **Instancias On-Demand**: Precio más alto pero estables, adecuadas para cargas de trabajo críticas con estado o aplicaciones sensibles a interrupciones.

Mediante este enfoque mixto:

1. Ejecuta cargas de trabajo críticas en instancias On-Demand
2. Ejecuta cargas de trabajo tolerantes a fallos en instancias Spot
3. Controla la ubicación de cargas de trabajo usando node affinity, tolerations y taints

Las estrategias adicionales de optimización de costos incluyen el auto-scaling usando Karpenter o Cluster Autoscaler, seleccionar tamaños de instancia adecuados, usar instancias Graviton (ARM) y utilizar Reserved Instances o Savings Plans.

</details>

### 2. ¿Cuál es la razón principal para desplegar nodes en múltiples Availability Zones (AZs) en un clúster EKS?

A. Reducir la latencia de red B. Aumentar el throughput de datos C. Mejorar la alta disponibilidad y la tolerancia a fallos D. Habilitar la replicación de datos entre regiones de AWS

<details>

<summary>Respuesta y explicación</summary>

**Respuesta: C. Mejorar la alta disponibilidad y la tolerancia a fallos**

**Explicación:** La razón principal para desplegar nodes en múltiples Availability Zones (AZs) en un clúster EKS es mejorar la alta disponibilidad y la tolerancia a fallos:

1. **Respuesta ante fallos de AZ**: Si una AZ falla, los nodes en otras AZs continúan operando, manteniendo la disponibilidad de la aplicación.
2. **Redundancia de infraestructura**: Distribuir cargas de trabajo entre múltiples AZs añade una capa de protección contra fallos de infraestructura física.
3. **Recuperación automática**: Kubernetes reprograma automáticamente pods desde nodes fallidos a nodes saludables, minimizando la interrupción del servicio.
4. **Estabilidad de rolling updates**: La disponibilidad se mantiene durante las actualizaciones porque las cargas de trabajo se distribuyen entre múltiples AZs.

EKS despliega el control plane en múltiples AZs de forma predeterminada, pero desplegar worker nodes en múltiples AZs también es una mejor práctica para garantizar la alta disponibilidad general del clúster. Puedes especificar múltiples subnets (cada una ubicada en diferentes AZs) al crear node groups.

</details>

### 3. ¿Cuál es el plugin CNI predeterminado para networking de pods en un clúster EKS?

A. Calico B. Flannel C. Amazon VPC CNI D. Weave Net

<details>

<summary>Respuesta y explicación</summary>

**Respuesta: C. Amazon VPC CNI**

**Explicación:** El plugin CNI (Container Network Interface) predeterminado para networking de pods en clústeres de Amazon EKS es Amazon VPC CNI. Las características principales de este plugin son:

1. **Networking nativo de VPC**: Cada pod recibe una dirección IP única dentro de la VPC, utilizando directamente el networking de AWS VPC.
2. **Integración con Security Groups**: Los security groups de AWS se pueden aplicar a nivel de pod, lo que permite un control de seguridad de red detallado.
3. **Gestión de direcciones IP**: A cada node se le asignan direcciones IP secundarias de las subnets de VPC para proporcionarlas a los pods.
4. **Rendimiento**: El rendimiento de red mejora al no usar overlay networks.
5. **Integración con servicios de AWS**: Se integra sin problemas con otros servicios de AWS como AWS Load Balancer Controller y AWS App Mesh.

Amazon VPC CNI es de código abierto y se gestiona en GitHub. Se puede reemplazar por otros plugins CNI como Calico o Cilium según sea necesario, pero Amazon VPC CNI es la opción predeterminada para EKS y está oficialmente soportada por AWS.

</details>

### 4. ¿Cuál es el nombre de la característica que vincula roles de IAM con service accounts de Kubernetes en un clúster EKS?

A. IAM for Service Accounts (IRSA) B. Pod Identity Webhook C. Kubernetes IAM Authenticator D. EKS Identity Manager

<details>

<summary>Respuesta y explicación</summary>

**Respuesta: A. IAM for Service Accounts (IRSA)**

**Explicación:** La característica que vincula roles de IAM con service accounts de Kubernetes en un clúster EKS es IAM for Service Accounts (IRSA). Las características principales de esta característica son:

1. **Control de permisos detallado**: Controla el acceso a recursos de AWS a nivel de pod, evitando concesiones de permisos amplias a nivel de node.
2. **Autenticación basada en OIDC**: EKS usa un proveedor OpenID Connect (OIDC) para establecer relaciones de confianza entre service accounts de Kubernetes y roles de IAM.
3. **Seguridad mejorada**: Permite implementar el principio de privilegio mínimo al conceder solo los permisos mínimos requeridos por aplicación.
4. **Método de implementación**:
   * Crear un proveedor OIDC para el clúster EKS
   * Crear un rol de IAM que confíe en la service account
   * Crear una service account de Kubernetes con una annotation específica
   * Desplegar el pod usando esa service account

Con IRSA, las aplicaciones que usan el AWS SDK pueden acceder de forma segura a servicios de AWS usando su propio rol de IAM en lugar de depender del rol de IAM del node.

</details>

### 5. ¿Cuál es la herramienta nativa de Kubernetes que gestiona Auto Scaling de node groups en un clúster EKS?

A. Horizontal Pod Autoscaler B. Vertical Pod Autoscaler C. Cluster Autoscaler D. Node Autoscaler

<details>

<summary>Respuesta y explicación</summary>

**Respuesta: C. Cluster Autoscaler**

**Explicación:** La herramienta nativa de Kubernetes que gestiona Auto Scaling de node groups en un clúster EKS es Cluster Autoscaler. Las características principales de esta herramienta son:

1. **Escalado automático**: Añade nodes automáticamente cuando los pods no pueden programarse por falta de recursos, y elimina nodes cuando están infrautilizados.
2. **Integración con AWS Auto Scaling Groups**: Funciona integrado con AWS Auto Scaling Groups en EKS.
3. **Cómo funciona**:
   * Scale Out: Añade nodes cuando los pods están en estado Pending debido a restricciones de recursos
   * Scale In: Elimina nodes cuando la utilización es baja y los pods pueden moverse a otros nodes
4. **Opciones de configuración**:
   * Establecer umbrales de scale up/down
   * Especificar el método de descubrimiento de node groups
   * Establecer el retraso de scale down
   * Respetar Pod Disruption Budgets (PDB)

Horizontal Pod Autoscaler (HPA) ajusta automáticamente la cantidad de pods, y Vertical Pod Autoscaler (VPA) ajusta automáticamente las solicitudes de recursos de los pods, pero ajustar la cantidad de nodes es la función de Cluster Autoscaler.

Ten en cuenta que AWS también ofrece Karpenter como una nueva herramienta de aprovisionamiento de nodes, que proporciona capacidades de aprovisionamiento de nodes más rápidas y flexibles.

</details>

## Preguntas de respuesta corta

### 6. ¿Qué configuración se necesita para habilitar logs del control plane de Kubernetes y enviarlos a CloudWatch Logs en un clúster EKS?

<details>

<summary>Respuesta y explicación</summary>

Para enviar logs del control plane de Kubernetes a CloudWatch Logs en un clúster EKS, debes habilitar tipos de log específicos durante la creación del clúster o en un clúster existente.

**Configuración requerida:**

1. **Habilitar tipos de log**: Habilita uno o más de los siguientes tipos de log:
   * `api`: logs del Kubernetes API server
   * `audit`: logs de auditoría de Kubernetes
   * `authenticator`: logs del autenticador de AWS IAM
   * `controllerManager`: logs del controller manager
   * `scheduler`: logs del scheduler
2. **Habilitar mediante AWS Management Console**:
   * Selecciona el clúster en la consola de EKS
   * Selecciona la pestaña "Logging"
   * Habilita los tipos de log deseados
3. **Habilitar mediante AWS CLI**:

```bash
aws eks update-cluster-config \
    --region region-code \
    --name cluster-name \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

4. **Habilitar mediante eksctl**:

```bash
eksctl utils update-cluster-logging \
    --region=region-code \
    --cluster=cluster-name \
    --enable-types=api,audit,authenticator,controllerManager,scheduler
```

Los logs habilitados se envían automáticamente al log group de CloudWatch Logs `/aws/eks/cluster-name/cluster`. Cada tipo de log se almacena como un log stream separado.

**Notas:**

* Habilitar logs genera costos adicionales (se aplica el precio de CloudWatch Logs).
* Los logs de auditoría en particular pueden generar grandes cantidades de datos, así que ten en cuenta la gestión de costos.
* Establece períodos de retención de logs para gestionar costos.

</details>

### 7. ¿Cómo envías logs de kubelet desde worker nodes a CloudWatch Logs en un clúster EKS?

<details>

<summary>Respuesta y explicación</summary>

Para enviar logs de kubelet desde worker nodes a CloudWatch Logs en un clúster EKS, debes instalar y configurar el agente de CloudWatch. A diferencia de los logs del control plane, los logs de worker nodes no se envían automáticamente a CloudWatch.

**Pasos de implementación:**

1. **Instalar CloudWatch Agent**: Despliega CloudWatch agent como DaemonSet en Kubernetes.
2. **Configurar Fluentd o Fluent Bit**: Configura el recolector de logs para enviar logs de kubelet a CloudWatch Logs.
3.  **Método recomendado: usar Amazon EKS Add-on**:

    ```bash
    # Create namespace for CloudWatch log collection
    kubectl create namespace amazon-cloudwatch

    # Create service account for AWS observability access
    eksctl create iamserviceaccount \
        --name cloudwatch-agent \
        --namespace amazon-cloudwatch \
        --cluster my-cluster \
        --attach-policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy \
        --approve \
        --override-existing-serviceaccounts

    # Create service account for Fluent Bit
    eksctl create iamserviceaccount \
        --name fluent-bit \
        --namespace amazon-cloudwatch \
        --cluster my-cluster \
        --attach-policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy \
        --approve \
        --override-existing-serviceaccounts

    # Install CloudWatch agent and Fluent Bit
    kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluent-bit-quickstart.yaml
    ```
4.  **Personalizar configuración**: Modifica ConfigMap para recopilar rutas y formatos de log específicos.

    ```yaml
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: fluent-bit-config
      namespace: amazon-cloudwatch
    data:
      fluent-bit.conf: |
        [INPUT]
            Name tail
            Path /var/log/kubelet.log
            Tag kubelet
        [OUTPUT]
            Name cloudwatch
            Match kubelet
            region region-name
            log_group_name /aws/eks/my-cluster/nodes
            log_stream_prefix kubelet-
            auto_create_group true
    ```
5. **Verificar logs**: Revisa el log group `/aws/eks/my-cluster/nodes` en la consola de CloudWatch Logs.

**Objetivos clave de recopilación de logs:**

* `/var/log/kubelet.log`: logs de kubelet
* `/var/log/kube-proxy.log`: logs de kube-proxy
* `/var/log/aws-routed-eni/ipamd.log`: logs de VPC CNI
* `/var/log/containers/*.log`: logs de containers

**Métodos alternativos:**

* Usar AWS Distro for OpenTelemetry (ADOT)
* Usar Amazon OpenSearch con una combinación de Fluent Bit
* Crear una solución de logging personalizada (por ejemplo, stack ELK)

**Mejores prácticas:**

* Gestionar costos con ajustes de período de retención de logs
* Recopilar selectivamente solo los logs necesarios
* Recopilar solo información importante mediante filtrado de logs
* Hacer seguimiento de costos etiquetando log groups

</details>

### 8. ¿Por qué Pod Security Policy (PSP) ya no se usa en clústeres EKS y cuáles son las alternativas?

<details>

<summary>Respuesta y explicación</summary>

Pod Security Policy (PSP) está obsoleto desde Kubernetes versión 1.21 y fue eliminado por completo en Kubernetes 1.25. En consecuencia, EKS ya no soporta PSP.

**Razones de la obsolescencia:**

1. **Complejidad**: PSP era difícil de configurar y comprender.
2. **Dificultad de debugging**: No proporcionaba mensajes de error claros cuando ocurrían infracciones de PSP, lo que dificultaba la solución de problemas.
3. **Flexibilidad limitada**: El control detallado era difícil en ciertos escenarios.
4. **Falta de consistencia**: La integración con otros mecanismos de seguridad de Kubernetes no era fluida.

**Alternativas:**

1. **Pod Security Standards (PSS) / Pod Security Admission (PSA)**:
   * Alternativa oficial introducida desde Kubernetes 1.22
   * Proporciona tres niveles de seguridad: Privileged, Baseline, Restricted
   * Se aplica mediante labels de namespace
   *   Ejemplo:

       ```yaml
       apiVersion: v1
       kind: Namespace
       metadata:
         name: my-namespace
         labels:
           pod-security.kubernetes.io/enforce: restricted
           pod-security.kubernetes.io/audit: restricted
           pod-security.kubernetes.io/warn: restricted
       ```
2. **Kyverno**:
   * Policy engine con definiciones de políticas basadas en YAML
   * Proporciona características más flexibles y potentes que PSP
   * Soporta políticas de validación, mutación, generación y limpieza
   *   Ejemplo:

       ```yaml
       apiVersion: kyverno.io/v1
       kind: ClusterPolicy
       metadata:
         name: restrict-privileged
       spec:
         validationFailureAction: enforce
         rules:
         - name: privileged-containers
           match:
             resources:
               kinds:
               - Pod
           validate:
             message: "Privileged containers are not allowed"
             pattern:
               spec:
                 containers:
                   - name: "*"
                     securityContext:
                       privileged: false
       ```
3. **OPA Gatekeeper**:
   * Policy controller basado en Open Policy Agent
   * Definiciones de políticas usando el lenguaje Rego
   * Usa conceptos de ConstraintTemplate y Constraint
   *   Ejemplo:

       ```yaml
       apiVersion: templates.gatekeeper.sh/v1beta1
       kind: ConstraintTemplate
       metadata:
         name: k8spsprivilegedcontainer
       spec:
         crd:
           spec:
             names:
               kind: K8sPSPPrivilegedContainer
         targets:
           - target: admission.k8s.gatekeeper.sh
             rego: |
               package k8spsprivilegedcontainer
               violation[{"msg": msg}] {
                 c := input.review.object.spec.containers[_]
                 c.securityContext.privileged
                 msg := "Privileged containers are not allowed"
               }
       ```
4. **Características de seguridad integradas de AWS**:
   * Amazon GuardDuty for EKS Protection
   * Estándares de seguridad de EKS de AWS Security Hub
   * Amazon Inspector for EKS

**Estrategia de migración:**

1. Analizar y documentar las políticas PSP actuales
2. Seleccionar una solución de reemplazo (PSA, Kyverno, OPA Gatekeeper, etc.)
3. Desplegar nuevas políticas en modo audit para evaluar el impacto
4. Aplicar políticas gradualmente (transición a modo enforce)
5. Hacer seguimiento de infracciones de políticas con ajustes de monitoreo y logging

Es importante migrar desde PSP a una solución alternativa antes de actualizar a EKS 1.25 o superior.

</details>

## Preguntas prácticas

### 9. Escribe una configuración de node group que use una combinación de instancias Spot e instancias On-Demand para optimización de costos en un clúster EKS. Debe cumplir los siguientes requisitos:

* Node group On-Demand para cargas de trabajo críticas (2-5 nodes)
* Node group Spot para cargas de trabajo generales (2-10 nodes)
* Node labels y taints adecuados
* Ejemplo de node affinity y tolerations para ubicación de cargas de trabajo

<details>

<summary>Respuesta y explicación</summary>

Una configuración de node group que usa una combinación de instancias Spot e instancias On-Demand para optimización de costos en un clúster EKS es la siguiente:

#### 1. Configuración de Node Group On-Demand (para cargas de trabajo críticas)

**Configuración usando eksctl:**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
nodeGroups:
  - name: critical-workloads
    instanceType: m5.xlarge
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    capacityType: ON_DEMAND
    labels:
      workload-type: critical
      node-lifecycle: on-demand
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/my-cluster: "owned"
    iam:
      withAddonPolicies:
        autoScaler: true
    ssh:
      allow: false
```

**Configuración usando AWS CLI:**

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name critical-workloads \
  --scaling-config minSize=2,maxSize=5,desiredSize=2 \
  --instance-types m5.xlarge \
  --capacity-type ON_DEMAND \
  --subnets subnet-0a1b2c3d4e5f6g7h8 subnet-0a1b2c3d4e5f6g7h9 \
  --node-role arn:aws:iam::123456789012:role/EKS-NodeInstanceRole \
  --labels workload-type=critical,node-lifecycle=on-demand \
  --tags "k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/my-cluster=owned"
```

#### 2. Configuración de Node Group Spot (para cargas de trabajo generales)

**Configuración usando eksctl:**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
nodeGroups:
  - name: general-workloads
    instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
    desiredCapacity: 3
    minSize: 2
    maxSize: 10
    capacityType: SPOT
    labels:
      workload-type: general
      node-lifecycle: spot
    taints:
      - key: spot
        value: "true"
        effect: PreferNoSchedule
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/my-cluster: "owned"
    iam:
      withAddonPolicies:
        autoScaler: true
    ssh:
      allow: false
```

**Configuración usando AWS CLI:**

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name general-workloads \
  --scaling-config minSize=2,maxSize=10,desiredSize=3 \
  --instance-types m5.large m5a.large m5d.large m5ad.large \
  --capacity-type SPOT \
  --subnets subnet-0a1b2c3d4e5f6g7h8 subnet-0a1b2c3d4e5f6g7h9 \
  --node-role arn:aws:iam::123456789012:role/EKS-NodeInstanceRole \
  --labels workload-type=general,node-lifecycle=spot \
  --taints "spot=true:PreferNoSchedule" \
  --tags "k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/my-cluster=owned"
```

#### 3. Ejemplo de Node Affinity y Tolerations para ubicación de cargas de trabajo

**Ejemplo de Deployment de carga de trabajo crítica (prefiere nodes On-Demand):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: critical-app
  template:
    metadata:
      labels:
        app: critical-app
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: workload-type
                operator: In
                values:
                - critical
              - key: node-lifecycle
                operator: In
                values:
                - on-demand
      containers:
      - name: critical-app
        image: my-critical-app:latest
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

**Ejemplo de Deployment de carga de trabajo general (permite nodes Spot):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: general-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: general-app
  template:
    metadata:
      labels:
        app: general-app
    spec:
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 1
            preference:
              matchExpressions:
              - key: node-lifecycle
                operator: In
                values:
                - spot
      tolerations:
      - key: "spot"
        operator: "Equal"
        value: "true"
        effect: "PreferNoSchedule"
      containers:
      - name: general-app
        image: my-general-app:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

#### 4. Ajustes adicionales de optimización

**Deployment de Cluster Autoscaler:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
  labels:
    app: cluster-autoscaler
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
        name: cluster-autoscaler
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
        - --balance-similar-node-groups
        - --skip-nodes-with-system-pods=false
```

**AWS Node Termination Handler (manejo de interrupciones de instancias Spot):**

```bash
helm repo add eks https://aws.github.io/eks-charts
helm install aws-node-termination-handler \
  --namespace kube-system \
  --set enableSpotInterruptionDraining=true \
  --set enableRebalanceMonitoring=true \
  --set enableRebalanceDraining=true \
  eks/aws-node-termination-handler
```

#### 5. Mejores prácticas y consideraciones

1. **Usar varios tipos de instancia**: Usar múltiples tipos de instancia en node groups Spot distribuye el riesgo de interrupción.
2.  **Configurar Pod Disruption Budgets (PDB)**: Configura PDBs para aplicaciones críticas a fin de limitar la cantidad de pods interrumpidos simultáneamente.

    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: critical-app-pdb
    spec:
      minAvailable: 2
      selector:
        matchLabels:
          app: critical-app
    ```
3. **Establecer requests y limits de recursos adecuados**: Establece requests y limits de recursos de containers adecuados para utilizar eficientemente los recursos de los nodes.
4.  **Utilizar Horizontal Pod Autoscaler**: Ajusta automáticamente la cantidad de pods según la demanda de la carga de trabajo.

    ```yaml
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: general-app-hpa
    spec:
      scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: general-app
      minReplicas: 3
      maxReplicas: 10
      metrics:
      - type: Resource
        resource:
          name: cpu
          target:
            type: Utilization
            averageUtilization: 70
    ```
5. **Monitoreo y optimización de costos**: Monitorea y optimiza los costos del clúster usando herramientas como AWS Cost Explorer y Kubecost.

</details>

## Preguntas avanzadas

### 10. Explica estrategias para implementar multi-tenancy en un clúster EKS y compara las ventajas y desventajas de cada enfoque.

<details>

<summary>Respuesta y explicación</summary>

Implementar multi-tenancy en un clúster EKS significa garantizar aislamiento y gestión de recursos adecuados mientras múltiples equipos, aplicaciones o clientes comparten la misma infraestructura de Kubernetes. Las siguientes son las principales estrategias para implementar multi-tenancy en EKS y las ventajas y desventajas de cada enfoque.

### 1. Separación a nivel de clúster (Hard Multi-tenancy)

**Descripción**: Aprovisionar clústeres EKS separados por tenant.

**Método de implementación**:

```bash
# Create cluster for Tenant A
eksctl create cluster --name tenant-a-cluster --region us-west-2

# Create cluster for Tenant B
eksctl create cluster --name tenant-b-cluster --region us-west-2
```

**Ventajas**:

* Garantiza aislamiento completo (seguridad, networking, recursos)
* Versiones y configuraciones de clúster personalizables por tenant
* Los problemas de un tenant no afectan a otros
* Adecuado para entornos con requisitos regulatorios estrictos

**Desventajas**:

* Alta sobrecarga operativa (gestionar múltiples clústeres)
* Menor utilización de recursos (control plane y componentes del sistema duplicados por clúster)
* Costos más altos (costo de control plane por clúster)
* Dificultad en la gestión centralizada y la aplicación de políticas

### 2. Separación a nivel de namespace (Soft Multi-tenancy)

**Descripción**: Separar tenants usando namespaces de Kubernetes dentro de un único clúster EKS.

**Método de implementación**:

```yaml
# Create namespace for Tenant A
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    tenant: a

# Create namespace for Tenant B
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-b
  labels:
    tenant: b
```

**Ventajas**:

* Gestión simplificada con un solo clúster
* Mejor utilización de recursos
* Eficiencia de costos (control plane compartido)
* Gestión centralizada y aplicación de políticas más sencillas

**Desventajas**:

* Difícil garantizar aislamiento completo
* Riesgos de seguridad debido al uso compartido de recursos a nivel de clúster
* El uso excesivo de recursos por un tenant puede afectar a otros
* Las actualizaciones del clúster afectan a todos los tenants

### 3. Separación a nivel de namespace + controles de seguridad adicionales

**Descripción**: Aplicar mecanismos adicionales de seguridad y control de recursos a la separación por namespace.

**Método de implementación**:

1. **Network Policies**:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-cross-tenant-traffic
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          tenant: a
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          tenant: a
```

2. **Resource Quotas**:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
```

3. **Control de permisos RBAC**:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-admin
  namespace: tenant-a
subjects:
- kind: Group
  name: tenant-a-admins
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-admin-role
  apiGroup: rbac.authorization.k8s.io
```

**Ventajas**:

* Mantiene las ventajas de la separación por namespace
* Seguridad y aislamiento de recursos mejorados
* Control de acceso y asignación de recursos por tenant
* Mantiene la eficiencia de costos

**Desventajas**:

* Mayor complejidad de configuración y gestión
* Aún carece de aislamiento completo de recursos a nivel de clúster
* Se requiere esfuerzo adicional para configurar y mantener políticas

### 4. Virtual Clusters

**Descripción**: Crear control planes virtuales de Kubernetes dentro de un único clúster EKS físico, proporcionando a cada tenant su propio "clúster".

**Método de implementación**:

```bash
# Install vcluster
helm repo add vcluster https://charts.loft.sh
helm repo update

# Create virtual cluster for Tenant A
helm install vcluster-tenant-a vcluster/vcluster \
  --namespace tenant-a \
  --create-namespace \
  --set sync.nodes.enabled=true

# Create virtual cluster for Tenant B
helm install vcluster-tenant-b vcluster/vcluster \
  --namespace tenant-b \
  --create-namespace \
  --set sync.nodes.enabled=true
```

**Ventajas**:

* Combina ventajas de la separación a nivel de clúster y a nivel de namespace
* Proporciona un Kubernetes API server y control plane dedicados por tenant
* Mejor utilización de recursos y eficiencia de costos
* Versiones y configuraciones de clúster personalizables por tenant

**Desventajas**:

* Sobrecarga y complejidad adicionales
* Madurez y soporte limitados para la tecnología de virtual cluster
* Soporte limitado para algunas características de Kubernetes
* Complejidad en debugging y troubleshooting

### 5. Multi-tenancy utilizando integración con servicios de AWS

**Descripción**: Mejorar la multi-tenancy de clústeres EKS usando servicios de AWS como AWS IAM, AWS Organizations y AWS Resource Access Manager.

**Método de implementación**:

1. **IAM Roles for Service Accounts (IRSA)**:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tenant-a-sa
  namespace: tenant-a
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/tenant-a-role
```

2. **AWS Organizations y SCP (Service Control Policies)**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyAccessToOtherTenantsResources",
      "Effect": "Deny",
      "Action": ["s3:*"],
      "Resource": ["arn:aws:s3:::tenant-b-*"]
    }
  ]
}
```

**Ventajas**:

* Control de acceso detallado para servicios de AWS
* Gobernanza mejorada utilizando estructura organizativa y políticas
* Capa adicional de aislamiento a nivel de servicio de AWS
* Integración con el modelo de seguridad existente de AWS

**Desventajas**:

* Mayor dependencia de servicios de AWS
* Mayor complejidad de configuración y gestión
* Portabilidad limitada al ser una solución específica de AWS
* Posibles costos adicionales de servicios de AWS

### Mejores prácticas para la implementación de multi-tenancy

1. **Analizar requisitos**:
   * Evaluar el nivel requerido de aislamiento entre tenants
   * Considerar requisitos regulatorios y de compliance
   * Considerar sobrecarga operativa y restricciones de costos
2. **Considerar un enfoque híbrido**:
   * Proporcionar clústeres dedicados para tenants críticos
   * Agrupar tenants menos críticos con separación a nivel de namespace
3. **Automatización e IaC (Infrastructure as Code)**:
   * Automatizar el aprovisionamiento de clústeres y namespaces usando Terraform, AWS CDK o eksctl
   * Gestionar configuraciones mediante flujos de trabajo GitOps
4. **Monitoreo y asignación de costos**:
   * Monitorear el uso de recursos por tenant
   * Hacer seguimiento de costos por tenant usando cost allocation tags
   * Analizar costos usando Kubecost o AWS Cost Explorer
5. **Mejora de seguridad**:
   * Auditorías de seguridad y escaneo de vulnerabilidades regulares
   * Aplicar el principio de privilegio mínimo
   * Utilizar network policies y service mesh

### Conclusión

La estrategia óptima para implementar multi-tenancy en EKS varía según los requisitos específicos de la organización, las necesidades de seguridad, las capacidades operativas y las restricciones de costos. Muchas organizaciones adoptan un enfoque híbrido que combina múltiples estrategias en lugar de un único enfoque. Por ejemplo, usar clústeres dedicados para cargas de trabajo críticas o reguladas mientras se aplica separación a nivel de namespace para entornos de desarrollo y prueba.

Al seleccionar una estrategia de multi-tenancy, debes equilibrar factores como seguridad, aislamiento, utilización de recursos, sobrecarga operativa y costo. También es importante evaluar si la estrategia elegida puede adaptarse a los requisitos cambiantes de la organización con el tiempo.

</details>
