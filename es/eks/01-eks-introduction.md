# Introducción a EKS

> **Versiones compatibles**: Amazon EKS 1.31, 1.32, 1.33 **Última actualización**: February 21, 2026

Amazon Elastic Kubernetes Service (EKS) es un servicio administrado para ejecutar Kubernetes en AWS. En este capítulo, exploraremos los conceptos básicos de EKS, su arquitectura y las diferencias con Kubernetes estándar.

## EKS y Kubernetes

EKS es un servicio administrado que proporciona APIs estándar de Kubernetes. Para obtener información detallada sobre los conceptos básicos y el funcionamiento de Kubernetes, consulta el documento [Introduction to Kubernetes](../basics/04-kubernetes-introduction.md).

### Beneficios clave de EKS

1. **Managed Control Plane**: AWS administra la disponibilidad y escalabilidad del control plane de Kubernetes
2. **Seguridad mejorada**: Autenticación y autorización mediante la integración con AWS IAM
3. **Integración con servicios de AWS**: Integración fluida con otros servicios de AWS (ELB, ECR, IAM, etc.)
4. **Varias opciones de compute**: Compatibilidad con múltiples opciones de compute, incluidos EC2, Fargate y Bottlerocket
5. **Auto Scaling**: Compatibilidad con auto scaling mediante Cluster Autoscaler, Karpenter, etc.
6. **Managed Node Groups**: Administración automatizada del ciclo de vida de los nodes

## Arquitectura y componentes de EKS

La arquitectura general de Amazon EKS es la siguiente:

### Control Plane

EKS proporciona un control plane de alta disponibilidad. El control plane se ejecuta en varias Availability Zones y consta de los siguientes componentes:

* **API Server**: Expone la Kubernetes API y gestiona la interacción con el cluster.
* **etcd**: Un almacén distribuido de clave-valor que almacena el estado del cluster.
* **Controller Manager**: Ejecuta controllers que administran el estado del cluster.
* **Scheduler**: Asigna pods a nodes.

En EKS, estos componentes del control plane son administrados por AWS, por lo que los usuarios no necesitan administrarlos directamente.

### Data Plane

El data plane de EKS se puede configurar con las siguientes opciones:

1. **Managed Node Groups**: Node groups compuestos por instancias EC2 donde AWS administra el ciclo de vida de los nodes.
2. **Self-Managed Nodes**: Instancias EC2 administradas directamente por el usuario.
3. **AWS Fargate**: Un motor de compute serverless que elimina la necesidad de administrar infraestructura para ejecutar containers.

### Networking

EKS utiliza el plugin Amazon VPC CNI para proporcionar networking de pods. Este plugin asigna direcciones IP de VPC a cada pod, lo que permite usar las capacidades de networking de AWS.

## Diferencias entre Kubernetes estándar y EKS

### Responsabilidad de administración

* **Kubernetes estándar**: Los usuarios deben administrar tanto el control plane como el data plane.
* **EKS**: AWS administra el control plane, y los usuarios solo necesitan administrar el data plane.

### Networking

* **Kubernetes estándar**: Puedes elegir entre varios plugins CNI.
* **EKS**: De forma predeterminada, se utiliza Amazon VPC CNI, y a cada pod se le asigna una dirección IP de VPC.

### Load Balancing

* **Kubernetes estándar**: Se debe instalar un controller independiente para usar services de tipo `LoadBalancer`.
* **EKS**: Los services de tipo `LoadBalancer` crean automáticamente un AWS Network Load Balancer (NLB). Para usar un Application Load Balancer (ALB), necesitas instalar el AWS Load Balancer Controller.

### Storage

* **Kubernetes estándar**: Varios storage drivers deben instalarse y configurarse manualmente.
* **EKS**: El AWS EBS CSI driver se proporciona de forma predeterminada, y los drivers para otros servicios de storage de AWS como EFS y FSx se pueden instalar fácilmente.

## Estructura de costos de EKS

Los costos incurridos al operar un cluster de EKS son los siguientes:

1. **Costo del EKS Control Plane**: Se cobra una tarifa por hora por cada cluster.
2. **Costos de compute**:
   * Instancias EC2 (nodes administrados o self-managed)
   * Fargate (se cobra según el tiempo de ejecución del pod y el uso de recursos)
3. **Costos de storage**: Costos por servicios de storage como EBS, EFS, FSx
4. **Costos de red**: Costos de transferencia de datos y uso de load balancer

### Estrategias de optimización de costos

1. **Usar Spot Instances**: Pueden reducir los costos hasta en un 90%.
2. **Aprovechar Fargate**: Adecuado para workloads con baja utilización.
3. **Configurar Auto Scaling**: Escalar automáticamente los nodes hacia arriba y hacia abajo según sea necesario.
4. **Locality Routing**: Mantener el tráfico dentro de la misma Availability Zone para reducir los costos de red.
5. **EKS Auto Mode**: Optimizar costos mediante el escalado automático del cluster.
6. **Hybrid Nodes**: Aumentar la eficiencia de costos combinando varios tipos de instancia.

## Integración con servicios de AWS

EKS se integra con los siguientes servicios de AWS:

![EKS AWS Services Integration](../.gitbook/assets/eks_aws_services_integration.png)

1. **IAM**: Administra la autenticación y autorización mediante la integración con Kubernetes RBAC.
2. **VPC**: Proporciona infraestructura de networking.
3. **CloudWatch**: Proporciona monitoreo y logging.
4. **ALB/NLB**: Proporciona load balancing.
5. **ECR**: Proporciona un container image registry.
6. **EBS/EFS/FSx**: Proporciona persistent storage.
7. **AWS App Mesh**: Proporciona capacidades de service mesh.
8. **AWS Certificate Manager**: Administra certificados SSL/TLS.
9. **AWS Secrets Manager**: Almacena y administra información confidencial de forma segura.
10. **AWS SageMaker**: Ejecuta workloads de machine learning.
11. **AWS Bedrock**: Aprovecha modelos de generative AI.

## Mejores prácticas de EKS

1. **Diseño del cluster**:
   * Implementar nodes en varias Availability Zones
   * Seleccionar tipos de instancia adecuados
   * Establecer una estrategia de node groups
2. **Seguridad**:
   * Aplicar el principio de mínimo privilegio
   * Implementar network policies
   * Aplicar pod security policies
   * Escaneo de imágenes y administración de vulnerabilidades
3. **Networking**:
   * Diseño adecuado de subnets
   * Configuración de security groups
   * Aprovechar Locality Routing
4. **Monitoreo y logging**:
   * Habilitar CloudWatch Container Insights
   * Configurar logging del control plane
   * Aprovechar Prometheus y Grafana
5. **Estrategia de actualización**:
   * Planificar actualizaciones regulares
   * Considerar una estrategia de deployment blue/green
   * Realizar pruebas antes de las actualizaciones

## Cuestionario

Para comprobar lo que aprendiste en este capítulo, prueba el [Amazon EKS Introduction Quiz](../quizzes/eks/01-eks-introduction-quiz.md).
