# Cuestionario de optimización de costos de Amazon EKS

Este cuestionario evalúa tu comprensión de las estrategias, herramientas y buenas prácticas para optimizar costos en clústeres de Amazon EKS.

## Descripción general del cuestionario
- Optimización de recursos de cómputo
- Optimización de costos de almacenamiento
- Optimización de costos de red
- Optimización de costos de administración del clúster
- Monitoreo y análisis de costos
- Herramientas y buenas prácticas de optimización de costos

## Preguntas de opción múltiple

### 1. ¿Cuál es la estrategia más efectiva para optimizar los costos de cómputo en Amazon EKS?

A. Usar siempre los tipos de instancia más grandes
B. Usar solo instancias bajo demanda para todas las cargas de trabajo
C. Combinar Spot Instances, dimensionamiento adecuado y auto-scaling
D. Consolidar todas las cargas de trabajo en un único node group

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Combinar Spot Instances, dimensionamiento adecuado y auto-scaling**

**Explicación:**
La estrategia más efectiva para optimizar los costos de cómputo en Amazon EKS es combinar Spot Instances, dimensionamiento adecuado y auto-scaling. Este enfoque integrado proporciona recursos de cómputo rentables que se ajustan a las características de la carga de trabajo y, al mismo tiempo, cumplen con los requisitos de rendimiento.

**Estrategias clave de optimización de cómputo:**

1. **Uso de Spot Instances**:
   - Ahorros de costos de hasta el 90% en comparación con on-demand
   - Adecuadas para cargas de trabajo tolerantes a fallos
   - Implementar mecanismos de manejo de interrupciones

2. **Dimensionamiento adecuado**:
   - Seleccionar instancias según el uso real de recursos
   - Eliminar recursos sobreaprovisionados
   - Optimizar resource requests y limits

3. **Implementación de auto-scaling**:
   - Escalado a nivel de node mediante Cluster Autoscaler o Karpenter
   - Escalado a nivel de Pod mediante Horizontal Pod Autoscaler
   - Ajuste de recursos basado en la demanda

**Métodos de implementación:**

1. **Crear Node Group con Spot Instances**:
   ```bash
   # Create Spot Instance node group using eksctl
   eksctl create nodegroup \
     --cluster my-cluster \
     --name spot-ng \
     --node-type m5.large \
     --nodes-min 2 \
     --nodes-max 10 \
     --spot \
     --asg-access
   ```

2. **Desplegar y configurar Karpenter**:
   ```yaml
   # Karpenter NodePool
   apiVersion: karpenter.sh/v1
   kind: NodePool
   metadata:
     name: default
   spec:
     template:
       spec:
         requirements:
           - key: "karpenter.sh/capacity-type"
             operator: In
             values: ["spot"]
           - key: "kubernetes.io/arch"
             operator: In
             values: ["amd64"]
           - key: "kubernetes.io/os"
             operator: In
             values: ["linux"]
           - key: "node.kubernetes.io/instance-type"
             operator: In
             values: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m4.large"]
         nodeClassRef:
           name: default
     limits:
       resources:
         cpu: 1000
         memory: 1000Gi
     disruption:
       consolidationPolicy: WhenEmpty
       consolidateAfter: 30s
   ---
   # Karpenter NodeClass
   apiVersion: karpenter.k8s.aws/v1
   kind: EC2NodeClass
   metadata:
     name: default
   spec:
     amiFamily: AL2
     role: KarpenterNodeRole
     subnetSelector:
       karpenter.sh/discovery: my-cluster
     securityGroupSelector:
       karpenter.sh/discovery: my-cluster
     tags:
       karpenter.sh/discovery: my-cluster
   ```

3. **Configurar Horizontal Pod Autoscaler**:
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: web-app
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: web-app
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
     - type: Resource
       resource:
         name: memory
         target:
           type: Utilization
           averageUtilization: 80
   ```

4. **Configurar Vertical Pod Autoscaler**:
   ```yaml
   apiVersion: autoscaling.k8s.io/v1
   kind: VerticalPodAutoscaler
   metadata:
     name: web-app-vpa
   spec:
     targetRef:
       apiVersion: "apps/v1"
       kind: Deployment
       name: web-app
     updatePolicy:
       updateMode: "Auto"
     resourcePolicy:
       containerPolicies:
       - containerName: '*'
         minAllowed:
           cpu: 50m
           memory: 100Mi
         maxAllowed:
           cpu: 1
           memory: 1Gi
         controlledResources: ["cpu", "memory"]
   ```

**Estrategias de optimización por tipo de carga de trabajo:**

1. **Aplicaciones stateless**:
   - Priorizar Spot Instances
   - Implementar escalado horizontal
   - Desplegar en múltiples zonas de disponibilidad

2. **Aplicaciones stateful**:
   - Combinar instancias on-demand y Spot Instances
   - Seleccionar tipos de instancia adecuados
   - Equilibrar rendimiento y costo del almacenamiento

3. **Batch Jobs**:
   - Maximizar el uso de Spot Instances
   - Implementar mecanismos de reintento de jobs
   - Ejecutar durante ventanas de tiempo rentables

**Buenas prácticas:**

1. **Optimizar Resource Requests y Limits**:
   ```yaml
   # Resource requests and limits example
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         containers:
         - name: web-app
           image: web-app:1.0
           resources:
             requests:
               cpu: 100m
               memory: 256Mi
             limits:
               cpu: 500m
               memory: 512Mi
   ```

2. **Optimizar Node Affinity y distribución de Pod**:
   ```yaml
   # Node affinity and pod distribution example
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         affinity:
           nodeAffinity:
             preferredDuringSchedulingIgnoredDuringExecution:
             - weight: 1
               preference:
                 matchExpressions:
                 - key: node.kubernetes.io/instance-type
                   operator: In
                   values:
                   - m5.large
                   - m5a.large
           podAntiAffinity:
             preferredDuringSchedulingIgnoredDuringExecution:
             - weight: 100
               podAffinityTerm:
                 labelSelector:
                   matchExpressions:
                   - key: app
                     operator: In
                     values:
                     - web-app
                 topologyKey: "kubernetes.io/hostname"
   ```

3. **Manejar interrupciones de Spot Instances**:
   ```yaml
   # Spot Instance interruption handling example
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         terminationGracePeriodSeconds: 60
         containers:
         - name: web-app
           image: web-app:1.0
           lifecycle:
             preStop:
               exec:
                 command: ["/bin/sh", "-c", "sleep 10; /app/cleanup.sh"]
   ```

Problemas con las otras opciones:
- **A. Usar siempre los tipos de instancia más grandes**: Esto lleva al sobreaprovisionamiento con costos innecesarios y puede no coincidir con los requisitos de la carga de trabajo.
- **B. Usar solo instancias bajo demanda para todas las cargas de trabajo**: Las instancias bajo demanda cuestan más que Spot Instances, y muchas cargas de trabajo pueden ejecutarse eficazmente en Spot Instances.
- **D. Consolidar todas las cargas de trabajo en un único node group**: Esto dificulta cumplir con diversos requisitos de carga de trabajo, carece de aislamiento de recursos y complica la asignación y optimización de costos.
</details>

### 2. ¿Cuál es el enfoque más efectivo para optimizar los costos de almacenamiento en Amazon EKS?

A. Usar el tipo de almacenamiento más barato para todas las cargas de trabajo
B. Migrar todos los datos a S3
C. Seleccionar tipos de almacenamiento que coincidan con los requisitos de la carga de trabajo e implementar administración del ciclo de vida
D. Minimizar todos los tamaños de volumen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Seleccionar tipos de almacenamiento que coincidan con los requisitos de la carga de trabajo e implementar administración del ciclo de vida**

**Explicación:**
El enfoque más efectivo para optimizar los costos de almacenamiento en Amazon EKS es seleccionar tipos de almacenamiento que coincidan con los requisitos de la carga de trabajo e implementar administración del ciclo de vida. Este enfoque minimiza los costos y, al mismo tiempo, cumple con los requisitos de rendimiento y aprovecha niveles de almacenamiento adecuados según el valor de los datos y los patrones de acceso.

**Estrategias clave de optimización de almacenamiento:**

1. **Seleccionar tipos de almacenamiento adecuados para las cargas de trabajo**:
   - Necesidades de alto rendimiento: io2, gp3 (EBS)
   - Necesidades de acceso compartido: EFS
   - Procesamiento de datos a gran escala: FSx for Lustre
   - Datos de archivo: S3, S3 Glacier

2. **Administración del ciclo de vida del almacenamiento**:
   - Datos accedidos con frecuencia: almacenamiento de alto rendimiento
   - Datos accedidos ocasionalmente: almacenamiento estándar
   - Datos accedidos raramente: almacenamiento de archivo de bajo costo

3. **Administración eficiente de volúmenes**:
   - Establecer tamaños de volumen adecuados
   - Identificar y eliminar volúmenes no utilizados
   - Administrar ciclos de vida de snapshots

**Métodos de implementación:**

1. **Optimización de volúmenes EBS**:
   ```yaml
   # gp3 StorageClass configuration
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-gp3
   provisioner: ebs.csi.aws.com
   parameters:
     type: gp3
     iops: "3000"
     throughput: "125"
   allowVolumeExpansion: true
   ```

2. **Administración del ciclo de vida de EFS**:
   ```bash
   # Set lifecycle policy when creating EFS file system
   aws efs create-file-system \
     --creation-token eks-efs \
     --performance-mode generalPurpose \
     --throughput-mode bursting \
     --lifecycle-policies '[{"TransitionToIA":"AFTER_30_DAYS"}]'
   ```

3. **Política de ciclo de vida de S3**:
   ```json
   {
     "Rules": [
       {
         "ID": "Move to IA after 30 days, Glacier after 90 days",
         "Status": "Enabled",
         "Prefix": "eks-backups/",
         "Transitions": [
           {
             "Days": 30,
             "StorageClass": "STANDARD_IA"
           },
           {
             "Days": 90,
             "StorageClass": "GLACIER"
           }
         ],
         "Expiration": {
           "Days": 365
         }
       }
     ]
   }
   ```

4. **Administración del ciclo de vida de EBS Snapshots**:
   ```yaml
   # VolumeSnapshotClass configuration
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   metadata:
     name: ebs-snapshot
     annotations:
       snapshot.storage.kubernetes.io/is-default-class: "true"
   driver: ebs.csi.aws.com
   deletionPolicy: Delete
   ```

Problemas con las otras opciones:
- **A. Usar el tipo de almacenamiento más barato para todas las cargas de trabajo**: El almacenamiento más barato puede no cumplir con los requisitos de rendimiento, lo que podría causar degradación del rendimiento de la aplicación e impacto en el negocio.
- **B. Migrar todos los datos a S3**: S3 es adecuado para algunos tipos de datos, pero no es apropiado para cargas de trabajo sensibles a la latencia o aplicaciones que requieren block storage.
- **D. Minimizar todos los tamaños de volumen**: Minimizar excesivamente los tamaños de volumen puede causar problemas de falta de espacio, y algunos tipos de volumen (por ejemplo, gp2) tienen el rendimiento determinado por el tamaño.
</details>

### 3. ¿Cuál es la estrategia más efectiva para optimizar los costos de red en Amazon EKS?

A. Usar el ancho de banda de red más caro para todo el tráfico
B. Colocar todos los services en una única zona de disponibilidad
C. Optimizar patrones de tráfico, minimizar costos de transferencia de datos y utilizar VPC endpoints
D. Bloquear todo el tráfico de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Optimizar patrones de tráfico, minimizar costos de transferencia de datos y utilizar VPC endpoints**

**Explicación:**
La estrategia más efectiva para optimizar los costos de red en Amazon EKS es optimizar los patrones de tráfico, minimizar los costos de transferencia de datos y utilizar VPC endpoints. Este enfoque mejora la eficiencia del tráfico de red y reduce costos innecesarios al considerar los modelos de costos de red de AWS.

**Estrategias clave de optimización de costos de red:**

1. **Optimización de patrones de tráfico**:
   - Minimizar el tráfico entre zonas de disponibilidad
   - Minimizar el tráfico entre regiones
   - Implementar enrutamiento consciente de localidad

2. **Minimizar costos de transferencia de datos**:
   - Usar compresión y formatos de datos eficientes
   - Implementar estrategias de caching
   - Eliminar transferencias de datos innecesarias

3. **Uso de VPC Endpoint**:
   - Conexiones privadas a servicios de AWS
   - Evitar internet gateways
   - Reducir costos de transferencia de datos

**Métodos de implementación:**

1. **Ubicación de Pod consciente de la zona de disponibilidad**:
   ```yaml
   # Deployment with topology spread constraints
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 6
     template:
       spec:
         topologySpreadConstraints:
         - maxSkew: 1
           topologyKey: topology.kubernetes.io/zone
           whenUnsatisfiable: DoNotSchedule
           labelSelector:
             matchLabels:
               app: web-app
   ```

2. **Enrutamiento de topología de Service**:
   ```yaml
   # Topology-aware service configuration
   apiVersion: v1
   kind: Service
   metadata:
     name: web-app
   spec:
     selector:
       app: web-app
     ports:
     - port: 80
       targetPort: 8080
     topologyKeys:
     - "kubernetes.io/hostname"
     - "topology.kubernetes.io/zone"
     - "*"
   ```

3. **Configuración de VPC Endpoint**:
   ```bash
   # Create S3 VPC endpoint
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.s3 \
     --route-table-ids rtb-12345678

   # Create DynamoDB VPC endpoint
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.dynamodb \
     --route-table-ids rtb-12345678

   # Create ECR API VPC endpoint
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.ecr.api \
     --vpc-endpoint-type Interface \
     --subnet-ids subnet-12345678 subnet-87654321 \
     --security-group-ids sg-12345678
   ```

4. **Enrutamiento de localidad con Istio**:
   ```yaml
   # Istio locality routing configuration
   apiVersion: networking.istio.io/v1alpha3
   kind: DestinationRule
   metadata:
     name: web-app
   spec:
     host: web-app
     trafficPolicy:
       loadBalancer:
         localityLbSetting:
           enabled: true
           failover:
           - from: us-west-2a
             to: us-west-2b
           - from: us-west-2b
             to: us-west-2c
           - from: us-west-2c
             to: us-west-2a
   ```

Problemas con las otras opciones:
- **A. Usar el ancho de banda de red más caro para todo el tráfico**: Esto genera costos innecesarios, y no todas las cargas de trabajo requieren alto ancho de banda.
- **B. Colocar todos los services en una única zona de disponibilidad**: Esto degrada significativamente la disponibilidad y la tolerancia a fallos, lo que infringe los principios de diseño de alta disponibilidad de AWS.
- **D. Bloquear todo el tráfico de red**: Esto es impráctico y limita severamente la funcionalidad de la aplicación.
</details>

### 4. ¿Cuál es el enfoque más efectivo para optimizar los costos de administración de clústeres de Amazon EKS?

A. Crear tantos clústeres como sea posible
B. Consolidar todas las cargas de trabajo en un único clúster
C. Optimizar la cantidad de clústeres según los requisitos de la carga de trabajo y minimizar la sobrecarga de administración
D. Administrar los clústeres manualmente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Optimizar la cantidad de clústeres según los requisitos de la carga de trabajo y minimizar la sobrecarga de administración**

**Explicación:**
El enfoque más efectivo para optimizar los costos de administración de clústeres de Amazon EKS es optimizar la cantidad de clústeres según los requisitos de la carga de trabajo y minimizar la sobrecarga de administración. Este enfoque equilibra los costos de administración de clústeres y la complejidad operativa, a la vez que cumple con los requisitos de aislamiento y seguridad de la carga de trabajo.

**Estrategias clave de optimización de costos de administración del clúster:**

1. **Mantener una cantidad adecuada de clústeres**:
   - Separación de clústeres basada en requisitos de negocio
   - Separación de clústeres basada en entorno (desarrollo, staging, producción)
   - Considerar requisitos de seguridad y cumplimiento

2. **Minimizar la sobrecarga de administración**:
   - Utilizar herramientas automatizadas de administración de clústeres
   - Implementar Infrastructure as Code (IaC)
   - Monitoreo y logging centralizados

3. **Optimizar recursos del clúster**:
   - Configuración adecuada del control plane
   - Administración eficiente de node groups
   - Utilizar servicios compartidos

**Métodos de implementación:**

1. **Configuración optimizada de clúster EKS**:
   ```bash
   # Create optimized cluster using eksctl
   eksctl create cluster \
     --name optimized-cluster \
     --region us-west-2 \
     --version 1.28 \
     --nodegroup-name standard-workers \
     --node-type m5.large \
     --nodes-min 2 \
     --nodes-max 10 \
     --managed \
     --asg-access \
     --external-dns-access \
     --full-ecr-access \
     --appmesh-access \
     --alb-ingress-access
   ```

2. **Automatización de administración del clúster con Terraform**:
   ```hcl
   module "eks" {
     source  = "terraform-aws-modules/eks/aws"
     version = "~> 19.0"

     cluster_name    = "optimized-cluster"
     cluster_version = "1.28"

     cluster_endpoint_public_access  = true
     cluster_endpoint_private_access = true

     cluster_addons = {
       coredns = {
         most_recent = true
       }
       kube-proxy = {
         most_recent = true
       }
       vpc-cni = {
         most_recent = true
       }
     }

     vpc_id     = module.vpc.vpc_id
     subnet_ids = module.vpc.private_subnets

     eks_managed_node_groups = {
       general = {
         min_size     = 1
         max_size     = 10
         desired_size = 2

         instance_types = ["m5.large"]
         capacity_type  = "ON_DEMAND"
       }

       spot = {
         min_size     = 1
         max_size     = 10
         desired_size = 2

         instance_types = ["m5.large", "m5a.large", "m5d.large", "m4.large"]
         capacity_type  = "SPOT"
       }
     }

     tags = {
       Environment = "production"
       Terraform   = "true"
     }
   }
   ```

3. **Administración de configuración del clúster con GitOps**:
   ```yaml
   # ArgoCD Application example
   apiVersion: argoproj.io/v1alpha1
   kind: Application
   metadata:
     name: cluster-config
     namespace: argocd
   spec:
     project: default
     source:
       repoURL: https://github.com/myorg/cluster-config.git
       targetRevision: HEAD
       path: configs
     destination:
       server: https://kubernetes.default.svc
       namespace: default
     syncPolicy:
       automated:
         prune: true
         selfHeal: true
       syncOptions:
       - CreateNamespace=true
   ```

4. **Configuración de clúster multi-tenant**:
   ```yaml
   # Namespace resource quota
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: team-a-quota
     namespace: team-a
   spec:
     hard:
       requests.cpu: "10"
       requests.memory: 20Gi
       limits.cpu: "20"
       limits.memory: 40Gi
       pods: "50"
       services: "20"
       persistentvolumeclaims: "30"
   ```

Problemas con las otras opciones:
- **A. Crear tantos clústeres como sea posible**: Esto aumenta los costos del control plane y la sobrecarga de administración para cada clúster, reduciendo la utilización de recursos.
- **B. Consolidar todas las cargas de trabajo en un único clúster**: Esto puede ser adecuado en algunos entornos, pero no considera requisitos de seguridad, aislamiento de cargas de trabajo y radio de impacto de fallos.
- **D. Administrar los clústeres manualmente**: La administración manual aumenta la posibilidad de errores, degrada la consistencia e incrementa la sobrecarga operativa.
</details>

### 5. ¿Cuál es el enfoque más efectivo para el monitoreo y la asignación de costos en Amazon EKS?

A. Revisar solo las facturas de AWS
B. Implementar estrategia de tagging, herramientas de asignación de costos y monitoreo continuo
C. Asignar el mismo costo a todos los recursos
D. Usar recursos sin monitoreo de costos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Implementar estrategia de tagging, herramientas de asignación de costos y monitoreo continuo**

**Explicación:**
El enfoque más efectivo para el monitoreo y la asignación de costos en Amazon EKS es implementar una estrategia de tagging, herramientas de asignación de costos y monitoreo continuo. Este enfoque ayuda a rastrear los costos con precisión, asignarlos por equipo o proyecto e identificar oportunidades de optimización de costos.

**Estrategias clave de monitoreo y asignación de costos:**

1. **Estrategia integral de tagging**:
   - Tags por unidad de negocio, equipo, proyecto, entorno
   - Aplicar reglas de tagging consistentes
   - Implementar tagging automatizado

2. **Uso de herramientas de asignación de costos**:
   - AWS Cost Explorer y AWS Budgets
   - Herramientas especializadas como Kubecost o CloudHealth
   - Dashboards e informes personalizados

3. **Monitoreo y optimización continuos**:
   - Revisión y análisis periódicos de costos
   - Detección de anomalías y alertas
   - Implementar recomendaciones de optimización

**Métodos de implementación:**

1. **Implementar estrategia de tagging**:
   ```yaml
   # Namespace tagging
   apiVersion: v1
   kind: Namespace
   metadata:
     name: team-a
     labels:
       team: team-a
       cost-center: cc-123
       environment: production
       project: project-x

   # Deployment tagging
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
     namespace: team-a
     labels:
       app: web-app
       team: team-a
       cost-center: cc-123
       environment: production
       project: project-x
   ```

2. **Configuración de política de tags de AWS**:
   ```json
   {
     "tags": {
       "team": {
         "tag_key": {
           "@@assign": "team"
         },
         "tag_value": {
           "@@assign": [
             "team-a",
             "team-b",
             "platform"
           ]
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       },
       "cost-center": {
         "tag_key": {
           "@@assign": "cost-center"
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       },
       "environment": {
         "tag_key": {
           "@@assign": "environment"
         },
         "tag_value": {
           "@@assign": [
             "production",
             "staging",
             "development"
           ]
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       }
     }
   }
   ```

3. **Instalación y configuración de Kubecost**:
   ```bash
   # Install Kubecost using Helm
   helm repo add kubecost https://kubecost.github.io/cost-analyzer/
   helm install kubecost kubecost/cost-analyzer \
     --namespace kubecost \
     --create-namespace \
     --set kubecostToken="<YOUR_KUBECOST_TOKEN>" \
     --set prometheus.server.persistentVolume.size=100Gi \
     --set prometheus.nodeExporter.enabled=true \
     --set serviceMonitor.enabled=true
   ```

4. **Configuración de informe de AWS Cost Explorer**:
   ```bash
   # Create cost and usage report
   aws cur put-report-definition \
     --report-definition '{
       "ReportName": "eks-cost-report",
       "TimeUnit": "HOURLY",
       "Format": "Parquet",
       "Compression": "Parquet",
       "AdditionalSchemaElements": ["RESOURCES"],
       "S3Bucket": "my-cost-reports",
       "S3Prefix": "eks-costs",
       "S3Region": "us-east-1",
       "AdditionalArtifacts": ["ATHENA"],
       "RefreshClosedReports": true,
       "ReportVersioning": "OVERWRITE_REPORT"
     }'
   ```

Problemas con las otras opciones:
- **A. Revisar solo las facturas de AWS**: Las facturas de AWS solo proporcionan información de costos de alto nivel, lo que dificulta identificar asignaciones de costos detalladas u oportunidades de optimización.
- **C. Asignar el mismo costo a todos los recursos**: Esto no refleja con precisión el uso real de recursos ni la generación de costos, y no aclara la responsabilidad de costos por equipo o proyecto.
- **D. Usar recursos sin monitoreo de costos**: Sin monitoreo de costos, no puedes detectar aumentos de costos de forma temprana ni identificar oportunidades de optimización, lo que dificulta la administración del presupuesto.
</details>

### 6. ¿Cuál es la combinación más efectiva de herramientas para la optimización de costos en Amazon EKS?

A. Usar solo administración manual de recursos
B. Usar solo AWS Cost Explorer
C. Integrar Kubecost, Karpenter, AWS Cost Explorer y herramientas de auto-scaling de Kubernetes
D. Usar solo herramientas de administración de costos de terceros

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Integrar Kubecost, Karpenter, AWS Cost Explorer y herramientas de auto-scaling de Kubernetes**

**Explicación:**
La combinación más efectiva de herramientas para la optimización de costos en Amazon EKS es integrar Kubecost, Karpenter, AWS Cost Explorer y herramientas de auto-scaling de Kubernetes. Este enfoque integrado optimiza los costos a nivel de clúster, carga de trabajo e infraestructura, proporciona visibilidad y permite la optimización automatizada.

**Herramientas y características clave de optimización de costos:**

1. **Kubecost**:
   - Visibilidad de costos de recursos de Kubernetes
   - Asignación de costos por namespace, deployment, service
   - Recomendaciones de optimización de costos
   - Forecasting de costos y administración de presupuesto

2. **Karpenter**:
   - Aprovisionamiento y administración inteligente de nodes
   - Selección óptima de instancias que coincide con los requisitos de la carga de trabajo
   - Escalado rápido y uso eficiente de recursos
   - Optimización del uso de Spot Instances

3. **AWS Cost Explorer**:
   - Análisis de costos en todos los servicios de AWS
   - Asignación de costos basada en tags
   - Tendencias de costos y forecasting
   - Recomendaciones de Reserved Instances y Savings Plans

4. **Herramientas de auto-scaling de Kubernetes**:
   - Horizontal Pod Autoscaler (HPA)
   - Vertical Pod Autoscaler (VPA)
   - Cluster Autoscaler
   - Cluster Proportional Autoscaler

**Métodos de implementación:**

1. **Instalación y configuración de Kubecost**:
   ```bash
   # Install Kubecost using Helm
   helm repo add kubecost https://kubecost.github.io/cost-analyzer/
   helm install kubecost kubecost/cost-analyzer \
     --namespace kubecost \
     --create-namespace \
     --set kubecostToken="<YOUR_KUBECOST_TOKEN>" \
     --set prometheus.server.persistentVolume.size=100Gi \
     --set prometheus.nodeExporter.enabled=true \
     --set serviceMonitor.enabled=true
   ```

2. **Instalación y configuración de Karpenter**:
   ```bash
   # Install Karpenter
   helm repo add karpenter https://charts.karpenter.sh
   helm upgrade --install karpenter karpenter/karpenter \
     --namespace karpenter \
     --create-namespace \
     --set serviceAccount.create=true \
     --set serviceAccount.name=karpenter \
     --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="arn:aws:iam::123456789012:role/KarpenterControllerRole" \
     --set controller.clusterName=my-cluster \
     --set controller.clusterEndpoint=$(aws eks describe-cluster --name my-cluster --query "cluster.endpoint" --output text)
   ```

   ```yaml
   # Karpenter NodePool and NodeClass configuration
   apiVersion: karpenter.sh/v1
   kind: NodePool
   metadata:
     name: default
   spec:
     template:
       spec:
         requirements:
           - key: "karpenter.sh/capacity-type"
             operator: In
             values: ["spot", "on-demand"]
           - key: "kubernetes.io/arch"
             operator: In
             values: ["amd64"]
           - key: "kubernetes.io/os"
             operator: In
             values: ["linux"]
           - key: "node.kubernetes.io/instance-type"
             operator: In
             values: ["m5.large", "m5a.large", "m5d.large", "m4.large", "t3.large", "t3a.large"]
         nodeClassRef:
           name: default
     limits:
       resources:
         cpu: 1000
         memory: 1000Gi
     disruption:
       consolidationPolicy: WhenEmpty
       consolidateAfter: 30s
   ---
   apiVersion: karpenter.k8s.aws/v1
   kind: EC2NodeClass
   metadata:
     name: default
   spec:
     amiFamily: AL2
     role: KarpenterNodeRole
     subnetSelector:
       karpenter.sh/discovery: my-cluster
     securityGroupSelector:
       karpenter.sh/discovery: my-cluster
     tags:
       karpenter.sh/discovery: my-cluster
   ```

3. **Configurar Horizontal Pod Autoscaler**:
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: web-app
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: web-app
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
     - type: Resource
       resource:
         name: memory
         target:
           type: Utilization
           averageUtilization: 80
   ```

4. **Configurar Vertical Pod Autoscaler**:
   ```yaml
   apiVersion: autoscaling.k8s.io/v1
   kind: VerticalPodAutoscaler
   metadata:
     name: web-app-vpa
   spec:
     targetRef:
       apiVersion: "apps/v1"
       kind: Deployment
       name: web-app
     updatePolicy:
       updateMode: "Auto"
     resourcePolicy:
       containerPolicies:
       - containerName: '*'
         minAllowed:
           cpu: 50m
           memory: 100Mi
         maxAllowed:
           cpu: 1
           memory: 1Gi
         controlledResources: ["cpu", "memory"]
   ```

**Integración de herramientas y flujo de trabajo:**

1. **Visibilidad y análisis de costos**:
   - Kubecost: análisis de costos de recursos dentro del clúster
   - AWS Cost Explorer: análisis de costos en todos los servicios de AWS
   - Dashboards integrados: panorama general y tendencias de costos

2. **Optimización automatizada de recursos**:
   - Karpenter: aprovisionamiento y administración óptimos de nodes
   - HPA/VPA: optimización de recursos a nivel de carga de trabajo
   - Uso de Spot Instances: recursos de cómputo rentables

3. **Asignación de costos y responsabilidad**:
   - Asignación de costos basada en tags
   - Análisis de costos por namespace y label
   - Informes de costos por equipo y proyecto

4. **Optimización y mejora continuas**:
   - Implementar recomendaciones de optimización de costos
   - Revisión y análisis periódicos de costos
   - Establecer y rastrear objetivos de reducción de costos

Problemas con las otras opciones:
- **A. Usar solo administración manual de recursos**: La administración manual carece de escalabilidad, tiene alta posibilidad de errores y puede pasar por alto oportunidades de optimización.
- **B. Usar solo AWS Cost Explorer**: AWS Cost Explorer es útil para el análisis de costos a nivel de servicios de AWS, pero no proporciona análisis detallado de costos a nivel de recursos de Kubernetes ni características de optimización automatizada.
- **D. Usar solo herramientas de administración de costos de terceros**: Las herramientas de terceros pueden ser útiles, pero pueden tener integración limitada con servicios nativos de AWS y herramientas de auto-scaling de Kubernetes, y pueden generar costos adicionales.
</details>
