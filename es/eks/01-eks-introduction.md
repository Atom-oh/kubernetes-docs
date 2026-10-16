# Introducción a EKS

> **Versiones compatibles**: soporte estándar de Amazon EKS 1.34–1.37; soporte extendido 1.31–1.33 (verificado el 12 de octubre de 2026)
> **Última actualización**: October 12, 2026

Amazon Elastic Kubernetes Service (EKS) es un servicio administrado para ejecutar Kubernetes en AWS. En este capítulo, exploraremos los conceptos básicos de EKS, su arquitectura y las diferencias con Kubernetes estándar.

## EKS y Kubernetes

EKS es un servicio administrado que proporciona API estándar de Kubernetes. Para obtener información detallada sobre los conceptos básicos y el funcionamiento de Kubernetes, consulte el documento [Introducción a Kubernetes](../basics/04-kubernetes-introduction.md).

### Beneficios clave de EKS

1. **Control Plane administrado**: AWS administra la disponibilidad y la escalabilidad del Control Plane de Kubernetes
2. **Seguridad mejorada**: Autenticación y autorización mediante la integración con AWS IAM
3. **Integración con servicios de AWS**: Integración fluida con otros servicios de AWS (ELB, ECR, IAM, etc.)
4. **Diversas opciones de cómputo**: Nodos basados en EC2, EKS Auto Mode, Fargate y Hybrid Nodes. Bottlerocket es un sistema operativo de nodo, no un servicio de cómputo independiente
5. **Auto Scaling**: Compatibilidad con escalado automático mediante Cluster Autoscaler, Karpenter, etc.
6. **Managed Node Groups**: Administración automatizada del ciclo de vida de los nodos

## Arquitectura y componentes de EKS

La arquitectura general de Amazon EKS es la siguiente:

### Control Plane

EKS proporciona un Control Plane de alta disponibilidad. El Control Plane se ejecuta en varias zonas de disponibilidad y consta de los siguientes componentes:

* **API Server**: Expone la API de Kubernetes y gestiona la interacción con el clúster.
* **etcd**: Un almacén distribuido de clave-valor que guarda el estado del clúster.
* **Controller Manager**: Ejecuta controladores que administran el estado del clúster.
* **Scheduler**: Asigna Pods a nodos.

En EKS, estos componentes del Control Plane son administrados por AWS, por lo que los usuarios no necesitan administrarlos directamente.

### Data Plane

El Data Plane de EKS se puede configurar con las siguientes opciones:

1. **Managed Node Groups**: Grupos de nodos EC2 cuyo flujo de trabajo de aprovisionamiento y reemplazo administra AWS. Los operadores seleccionan e inician las actualizaciones de versión/AMI de los nodos; una actualización del Control Plane no actualiza automáticamente estos nodos.
2. **Self-Managed Nodes**: Instancias EC2 administradas directamente por el usuario.
3. **AWS Fargate**: Cómputo por Pod seleccionado mediante perfiles de Fargate. Los operadores aún administran la configuración de las cargas de trabajo y las solicitudes de recursos.
4. **EKS Auto Mode**: AWS administra el aprovisionamiento, el escalado y las actualizaciones de nodos EC2, además de las funcionalidades compatibles de redes, balanceo de carga y almacenamiento en bloques.
5. **Hybrid Nodes**: Máquinas on-premises/perimetrales administradas por el cliente se conectan a un Control Plane de EKS alojado en AWS; se requiere conectividad confiable.

### Redes

En los nodos EKS convencionales basados en EC2, Amazon VPC CNI es el predeterminado y asigna direcciones de VPC a los Pods comunes. Los Pods con `hostNetwork` comparten las redes del nodo. Auto Mode administra su propia funcionalidad de redes, mientras que Hybrid Nodes usan un CNI on-premises compatible en lugar de Amazon VPC CNI.

## Diferencias entre Kubernetes estándar y EKS

### Responsabilidad de administración

* **Kubernetes autoadministrado**: Los operadores administran el Control Plane y el Data Plane; otras distribuciones administradas pueden dividir la responsabilidad de manera diferente.
* **EKS**: AWS administra el Control Plane. La responsabilidad del Data Plane depende de la opción de cómputo. La seguridad, la identidad, la configuración, la disponibilidad y la protección de datos de las cargas de trabajo siguen siendo responsabilidades del cliente.

### Redes

* **Kubernetes estándar**: Puede elegir entre varios plugins de CNI.
* **EKS**: Los clústeres convencionales basados en EC2 usan Amazon VPC CNI de forma predeterminada. Los CNI alternativos y Auto Mode/Hybrid Nodes tienen distintas restricciones de funcionalidades y soporte.

### Balanceo de carga

* **Kubernetes estándar**: Se debe instalar un controlador independiente para usar servicios de tipo `LoadBalancer`.
* **EKS**: En un clúster convencional, instale y autorice AWS Load Balancer Controller para Services NLB e Ingresses ALB; el controlador heredado puede crear Classic Load Balancers. Auto Mode proporciona integración administrada con NLB/ALB con sus propias clases y configuración compatible. Un tipo de Service por sí solo no identifica el controlador. Fargate admite objetivos IP de ALB/NLB.

### Almacenamiento

* **Kubernetes estándar**: Se deben instalar y configurar manualmente varios controladores de almacenamiento.
* **EKS**: En un clúster convencional, instale el controlador/add-on de EBS CSI y conceda sus permisos de IAM. Auto Mode tiene compatibilidad administrada con EBS con el provisionador `ebs.csi.eks.amazonaws.com`, distinto de `ebs.csi.aws.com`. Las integraciones de EFS y FSx tienen requisitos previos independientes; los volúmenes EBS no se pueden montar mediante Fargate o Hybrid Nodes.

## Estructura de costos de EKS

Los costos generados al operar un clúster EKS son los siguientes:

1. **Costo del Control Plane de EKS**: Se cobra una tarifa por hora por clúster, con precios diferentes para soporte estándar/extendido y cargos adicionales por niveles opcionales de Control Plane aprovisionado.
2. **Costos de cómputo**:
   * Instancias EC2 (nodos administrados o autoadministrados)
   * Fargate (se cobra según el tiempo de ejecución del Pod y el uso de recursos)
3. **Costos de almacenamiento**: Costos de servicios de almacenamiento como EBS, EFS y FSx
4. **Costos de red**: Costos de transferencia de datos, gateways NAT, direcciones IPv4 públicas y uso de balanceadores de carga
5. **Costos de funcionalidades administradas**: Auto Mode, EKS Capabilities y Hybrid Nodes tienen sus propios cargos además de los costos pertinentes de clúster/infraestructura.

### Estrategias de optimización de costos

1. **Use instancias Spot**: Compare los precios actuales de Spot y la tolerancia a interrupciones; los ahorros anunciados no son una garantía para una carga de trabajo.
2. **Evalúe Fargate**: Compare los tamaños de Pod aprovisionados, el tiempo de ejecución, los límites de funcionalidades y el esfuerzo operativo con EC2. La baja utilización de la aplicación por sí sola no garantiza ahorros.
3. **Configure Auto Scaling**: Escale los nodos automáticamente hacia arriba y abajo según sea necesario.
4. **Enrutamiento de localidad**: Cuando sea compatible, prefiera el tráfico dentro de la misma zona mientras mantiene una capacidad y conmutación por error adecuadas. La configuración de enrutamiento y del balanceador de carga determina cualquier ahorro de transferencia.
5. **EKS Auto Mode**: Evalúe los ahorros del escalado y la consolidación automáticos junto con el cargo de administración de Auto Mode.
6. **Hybrid Nodes**: Evalúe la capacidad on-premises existente junto con los cargos por vCPU de Hybrid Nodes y los costos de conectividad/operaciones. Esta funcionalidad no es sinónimo de mezclar tipos de instancias EC2.

## Integración con servicios de AWS

EKS se integra con los siguientes servicios de AWS:

![Diagrama de la integración de servicios de AWS alrededor de Amazon EKS: IAM, VPC, almacenamiento, CloudWatch, ECR y SageMaker/Bedrock.](../.gitbook/assets/en-eks-01-eks-introduction-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-01-eks-introduction-0.html)

1. **IAM**: Las identidades de IAM se autentican en el clúster; las entradas de acceso de EKS autorizan mediante políticas de acceso y/o grupos RBAC de Kubernetes. Pod Identity e IRSA conceden por separado permisos de AWS a las cargas de trabajo.
2. **VPC**: Proporciona infraestructura de redes.
3. **CloudWatch**: Proporciona monitoreo y registro.
4. **ALB/NLB**: Proporciona balanceo de carga.
5. **ECR**: Proporciona un registro de imágenes de contenedor.
6. **EBS/EFS/FSx**: Proporciona almacenamiento persistente.
7. **AWS App Mesh**: AWS finalizó el soporte el 30 de septiembre de 2026, y la consola y los recursos de App Mesh ya no son accesibles. Las integraciones existentes deben migrar; no lo seleccione para una implementación nueva.
8. **AWS Certificate Manager**: Administra certificados SSL/TLS.
9. **AWS Secrets Manager**: Almacena y administra de forma segura información confidencial.
10. **AWS SageMaker**: Ejecuta cargas de trabajo de machine learning.
11. **AWS Bedrock**: Aprovecha modelos de IA generativa.

## Prácticas recomendadas de EKS

1. **Diseño del clúster**:
   * Implemente nodos en varias zonas de disponibilidad
   * Seleccione tipos de instancias adecuados
   * Establezca una estrategia de grupos de nodos
2. **Seguridad**:
   * Aplique el principio de privilegio mínimo
   * Implemente políticas de red
   * Aplique Pod Security Standards mediante Pod Security Admission y/o políticas de admisión; la API PodSecurityPolicy se eliminó en Kubernetes 1.25
   * Escaneo de imágenes y administración de vulnerabilidades
3. **Redes**:
   * Diseño de subred adecuado
   * Configuración de grupos de seguridad
   * Aproveche Locality Routing
4. **Monitoreo y registro**:
   * Habilite CloudWatch Container Insights
   * Configure el registro del Control Plane
   * Aproveche Prometheus y Grafana
5. **Estrategia de actualización**:
   * Planifique actualizaciones periódicas
   * Considere la estrategia de implementación azul/verde
   * Realice pruebas antes de las actualizaciones

## Referencias oficiales

- [Ciclo de vida de versiones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Cómputo y responsabilidades compartidas](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [AWS Load Balancer Controller](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [EBS CSI y Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-overview.html)
- [Consideraciones de Fargate](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [Aviso de soporte de App Mesh](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html)
- [Precios de EKS](https://aws.amazon.com/eks/pricing/)
- [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)

## Cuestionario

Para comprobar lo que aprendió en este capítulo, pruebe el [Cuestionario de introducción a Amazon EKS](../quizzes/eks/01-eks-introduction-quiz.md).
