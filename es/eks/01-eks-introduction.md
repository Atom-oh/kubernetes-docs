# Introducción a EKS

> **Versiones compatibles**: Amazon EKS 1.31, 1.32, 1.33 **Última actualización**: February 21, 2026

Amazon Elastic Kubernetes Service (EKS) es un servicio administrado para ejecutar Kubernetes en AWS. En este capítulo, exploraremos los conceptos básicos de EKS, su arquitectura y las diferencias con Kubernetes estándar.

## EKS y Kubernetes

EKS es un servicio administrado que proporciona APIs estándar de Kubernetes. Para obtener información detallada sobre los conceptos básicos y la operación de Kubernetes, consulta el documento [Introducción a Kubernetes](../basics/04-kubernetes-introduction.md).

### Beneficios principales de EKS

1. **Control Plane administrado**: AWS administra la disponibilidad y la escalabilidad del control plane de Kubernetes
2. **Seguridad mejorada**: Autenticación y autorización mediante la integración con AWS IAM
3. **Integración con servicios de AWS**: Integración fluida con otros servicios de AWS (ELB, ECR, IAM, etc.)
4. **Diversas opciones de cómputo**: Compatibilidad con múltiples opciones de cómputo, incluidas EC2, Fargate y Bottlerocket
5. **Auto Scaling**: Compatibilidad con auto scaling mediante Cluster Autoscaler, Karpenter, etc.
6. **Managed Node Groups**: Administración automatizada del ciclo de vida de los nodes

## Arquitectura y componentes de EKS

La arquitectura general de Amazon EKS es la siguiente:

### Control Plane

EKS proporciona un control plane de alta disponibilidad. El control plane se ejecuta en múltiples zonas de disponibilidad y consta de los siguientes componentes:

* **API Server**: Expone la API de Kubernetes y gestiona la interacción con el clúster.
* **etcd**: Un almacén distribuido de clave-valor que guarda el estado del clúster.
* **Controller Manager**: Ejecuta controllers que administran el estado del clúster.
* **Scheduler**: Asigna pods a los nodes.

En EKS, estos componentes del control plane son administrados por AWS, por lo que los usuarios no necesitan administrarlos directamente.

### Data Plane

El data plane de EKS se puede configurar con las siguientes opciones:

1. **Managed Node Groups**: Grupos de nodes compuestos por instancias EC2 en los que AWS administra el ciclo de vida de los nodes.
2. **Self-Managed Nodes**: Instancias EC2 administradas directamente por el usuario.
3. **AWS Fargate**: Un motor de cómputo sin servidor que elimina la necesidad de administrar infraestructura para ejecutar contenedores.

### Redes

EKS utiliza el plugin Amazon VPC CNI para proporcionar redes para pods. Este plugin asigna direcciones IP de VPC a cada pod, lo que permite usar las capacidades de red de AWS.

## Diferencias entre Kubernetes estándar y EKS

### Responsabilidad de administración

* **Kubernetes estándar**: Los usuarios deben administrar tanto el control plane como el data plane.
* **EKS**: AWS administra el control plane, y los usuarios solo deben administrar el data plane.

### Redes

* **Kubernetes estándar**: Puedes elegir entre varios plugins de CNI.
* **EKS**: De forma predeterminada, se utiliza Amazon VPC CNI y a cada pod se le asigna una dirección IP de VPC.

### Balanceo de carga

* **Kubernetes estándar**: Se debe instalar un controller independiente para usar servicios de tipo `LoadBalancer`.
* **EKS**: Los servicios de tipo `LoadBalancer` crean automáticamente un AWS Network Load Balancer (NLB). Para usar un Application Load Balancer (ALB), debes instalar AWS Load Balancer Controller.

### Almacenamiento

* **Kubernetes estándar**: Se deben instalar y configurar manualmente varios drivers de almacenamiento.
* **EKS**: El driver AWS EBS CSI se proporciona de forma predeterminada, y los drivers para otros servicios de almacenamiento de AWS, como EFS y FSx, se pueden instalar fácilmente.

## Estructura de costos de EKS

Los costos generados al operar un clúster de EKS son los siguientes:

1. **Costo del control plane de EKS**: Se cobra una tarifa por hora por cada clúster.
2. **Costos de cómputo**:
   * Instancias EC2 (managed o self-managed nodes)
   * Fargate (se cobra según el tiempo de ejecución del pod y el uso de recursos)
3. **Costos de almacenamiento**: Costos de servicios de almacenamiento como EBS, EFS y FSx
4. **Costos de red**: Costos de transferencia de datos y uso de balanceadores de carga

### Estrategias de optimización de costos

1. **Usar Spot Instances**: Puede reducir los costos hasta en un 90%.
2. **Aprovechar Fargate**: Adecuado para cargas de trabajo con baja utilización.
3. **Configurar Auto Scaling**: Escala automáticamente los nodes hacia arriba y hacia abajo según sea necesario.
4. **Locality Routing**: Mantén el tráfico dentro de la misma zona de disponibilidad para reducir los costos de red.
5. **EKS Auto Mode**: Optimiza los costos mediante el escalado automático del clúster.
6. **Hybrid Nodes**: Aumenta la eficiencia de costos al combinar varios tipos de instancias.

## Integración con servicios de AWS

EKS se integra con los siguientes servicios de AWS:

![Diagrama de integración de servicios de AWS alrededor de Amazon EKS: IAM, VPC, almacenamiento, CloudWatch, ECR y SageMaker/Bedrock.](../.gitbook/assets/en-eks-01-eks-introduction-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-01-eks-introduction-0.html)

1. **IAM**: Administra la autenticación y autorización mediante la integración con Kubernetes RBAC.
2. **VPC**: Proporciona infraestructura de red.
3. **CloudWatch**: Proporciona monitoreo y registros.
4. **ALB/NLB**: Proporciona balanceo de carga.
5. **ECR**: Proporciona un registro de imágenes de contenedor.
6. **EBS/EFS/FSx**: Proporciona almacenamiento persistente.
7. **AWS App Mesh**: Proporciona capacidades de service mesh.
8. **AWS Certificate Manager**: Administra certificados SSL/TLS.
9. **AWS Secrets Manager**: Almacena y administra de forma segura información confidencial.
10. **AWS SageMaker**: Ejecuta cargas de trabajo de machine learning.
11. **AWS Bedrock**: Aprovecha modelos de IA generativa.

## Mejores prácticas de EKS

1. **Diseño del clúster**:
   * Implementar nodes en múltiples zonas de disponibilidad
   * Seleccionar tipos de instancia adecuados
   * Establecer una estrategia de grupos de nodes
2. **Seguridad**:
   * Aplicar el principio de mínimo privilegio
   * Implementar políticas de red
   * Aplicar políticas de seguridad de pods
   * Escaneo de imágenes y gestión de vulnerabilidades
3. **Redes**:
   * Diseño adecuado de subredes
   * Configuración de security groups
   * Aprovechar Locality Routing
4. **Monitoreo y registros**:
   * Habilitar CloudWatch Container Insights
   * Configurar registros del control plane
   * Aprovechar Prometheus y Grafana
5. **Estrategia de actualización**:
   * Planificar actualizaciones regulares
   * Considerar la estrategia de implementación blue/green
   * Realizar pruebas antes de las actualizaciones

## Cuestionario

Para poner a prueba lo que aprendiste en este capítulo, intenta el [Cuestionario de introducción a Amazon EKS](../quizzes/eks/01-eks-introduction-quiz.md).
