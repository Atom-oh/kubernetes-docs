> [Versión en coreano](https://www.atomai.click/kubernetes-docs/ko/)

# Contenido de Formación sobre Kubernetes y Amazon EKS
[![GitBook](https://img.shields.io/static/v1?message=Documented%20on%20GitBook&logo=gitbook&logoColor=ffffff&label=%20&labelColor=5c5c5c&color=3F89A1)](https://www.gitbook.com/preview?utm_source=gitbook_readme_badge&utm_medium=organic&utm_campaign=preview_documentation&utm_content=link)

Este repositorio es una guía completa de la nube que abarca los fundamentos de Linux y contenedores, Kubernetes y Amazon EKS, redes, service mesh (malla de servicios), almacenamiento, bases de datos, canalizaciones de datos, IA/ML y seguridad y operaciones. Junto con los materiales de aprendizaje, proporciona datos de benchmark medidos en entornos reales de AWS, además de cuestionarios por tema y laboratorios prácticos seleccionados.

## Materiales de Aprendizaje y Cuestionarios

Este contenido de formación ofrece cuestionarios para cada tema junto con los materiales de aprendizaje. Puedes poner a prueba y reforzar lo aprendido mediante los cuestionarios. Cada cuestionario está diseñado con respuestas ocultas de tipo desplegable, lo que te permite intentar responder las preguntas antes de revelar las soluciones.

- [Índice de Materiales de Aprendizaje](#table-of-contents) - Materiales de aprendizaje por tema
- [Colección de Cuestionarios](./quizzes/README.md) - Cuestionarios por tema
- [Hoja de Ruta de la Guía](./roadmap.md) - El mapa de aprendizaje completo y las rutas de aprendizaje recomendadas | [Cuestionario](./quizzes/roadmap-quiz.md)
- [Lectura con LLMs](./llm-guide.md) - Encuentra y lee el material fuente a través de llms.txt, el manifiesto y MCP | [Cuestionario](./quizzes/llm-guide-quiz.md)

## Índice

### Noticias
- [Noticias Semanales](./news/README.md) - Los últimos resúmenes de noticias del ecosistema de Kubernetes/EKS

### Linux y Contenedores
1. [Fundamentos de Linux](./basics/01-linux-basics.md) | [Cuestionario](./quizzes/basics/01-linux-basics-quiz.md) | [Laboratorio](./labs/basics/01-linux-basics-lab.md)
2. [Habilidades de Operación de Linux](./basics/02-linux-advanced.md) | [Cuestionario](./quizzes/basics/02-linux-advanced-quiz.md) | [Laboratorio](./labs/basics/02-linux-advanced-lab.md)
3. [Tecnología de Contenedores](./basics/03-container-technology.md) | [Cuestionario](./quizzes/basics/03-container-technology-quiz.md) | [Laboratorio](./labs/basics/03-container-technology-lab.md)
4. [Fundamentos de eBPF y Aplicaciones Prácticas](./basics/05-ebpf-fundamentals.md) | [Cuestionario](./quizzes/basics/05-ebpf-fundamentals-quiz.md)

### Conceptos Fundamentales de Kubernetes
1. [Introducción a Kubernetes](./basics/04-kubernetes-introduction.md) | [Cuestionario](./quizzes/basics/04-kubernetes-introduction-quiz.md)
2. [Arquitectura del Cluster](./core/01-cluster-architecture.md) | [Cuestionario](./quizzes/core/01-cluster-architecture-quiz.md)
3. [Pods y Cargas de Trabajo](./core/02-pods-and-workloads.md) | [Cuestionario](./quizzes/core/02-pods-and-workloads-quiz.md)
4. [Services y Redes](./core/03-services-networking.md) | [Cuestionario](./quizzes/core/03-services-networking-quiz.md)
5. [Almacenamiento](./core/04-storage.md) | [Cuestionario](./quizzes/core/04-storage-quiz.md)
6. [Configuración](./core/05-configuration-secrets.md) | [Cuestionario](./quizzes/core/05-configuration-secrets-quiz.md)
7. [Seguridad](./core/06-security.md) | [Cuestionario](./quizzes/core/06-security-quiz.md)
8. [Políticas](./core/07-policies.md) | [Cuestionario](./quizzes/core/07-policies-quiz.md)
9. [Scheduling, Preemption y Eviction](./core/08-scheduling-preemption-eviction.md) | [Cuestionario](./quizzes/core/08-scheduling-preemption-eviction-quiz.md)
10. [Administración del Cluster](./core/09-cluster-administration.md) | [Cuestionario](./quizzes/core/09-cluster-administration-quiz.md)
11. [Windows en Kubernetes](./core/10-windows-in-kubernetes.md) | [Cuestionario](./quizzes/core/10-windows-in-kubernetes-quiz.md)
12. [Extender Kubernetes](./core/11-extending-kubernetes.md) | [Cuestionario](./quizzes/core/11-extending-kubernetes-quiz.md)
13. Scheduler Personalizado
   - [Parte 1: Fundamentos del Scheduler Personalizado](./scheduling/01-custom-scheduler-part1.md) | [Cuestionario](./quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
   - [Parte 2: Extensiones del Scheduler y Framework](./scheduling/02-custom-scheduler-part2.md) | [Cuestionario](./quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
   - [Parte 3: Ejemplos de Implementación y Monitorización de un Scheduler Personalizado](./scheduling/03-custom-scheduler-part3.md) | [Cuestionario](./quizzes/scheduling/02-custom-scheduler-part3-quiz.md)
14. Autoescalado
   - [KEDA](./autoscaling/01-keda.md) | [Cuestionario](./quizzes/autoscaling/05-keda-quiz.md)
   - [Karpenter](./autoscaling/02-karpenter.md) | [Cuestionario](./quizzes/autoscaling/06-karpenter-quiz.md)
   - [Knative](./autoscaling/03-knative.md) | [Cuestionario](./quizzes/autoscaling/03-knative-quiz.md)

### Amazon EKS
1. [Introducción a EKS](./eks/01-eks-introduction.md) | [Cuestionario](./quizzes/eks/01-eks-introduction-quiz.md)
2. Creación de un Cluster de EKS
   - [Parte 1: Requisitos Previos](./eks/02-eks-cluster-creation-part1.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
   - [Parte 2: Crear Clusters con eksctl](./eks/02-eks-cluster-creation-part2.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part2-quiz.md)
   - [Parte 3: Crear Clusters con la Consola de Administración de AWS y la CLI](./eks/02-eks-cluster-creation-part3.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part3-quiz.md)
   - [Parte 4: Crear Clusters con Terraform y CDK](./eks/02-eks-cluster-creation-part4.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part4-quiz.md)
   - [Parte 5: Acceso, Validación, Actualización y Eliminación del Cluster](./eks/02-eks-cluster-creation-part5.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part5-quiz.md)
3. Redes en EKS
   - [Parte 1: Conceptos Básicos y Configuración de la VPC](./eks/03-eks-networking-part1.md) | [Cuestionario](./quizzes/eks/03-eks-networking-part1-quiz.md)
   - [Parte 2: Services y Balanceo de Carga, Network Policies](./eks/03-eks-networking-part2.md) | [Cuestionario](./quizzes/eks/03-eks-networking-part2-quiz.md)
   - [Parte 3: Optimización del Rendimiento, Resolución de Problemas, Casos de Uso Avanzados](./eks/03-eks-networking-part3.md) | [Cuestionario](./quizzes/eks/03-eks-networking-part3-quiz.md)
4. Almacenamiento en EKS
   - [Parte 1: Conceptos Básicos, EBS, EFS](./eks/04-eks-storage-part1.md) | [Cuestionario](./quizzes/eks/04-eks-storage-part1-quiz.md)
   - [Parte 2: FSx for Lustre, S3, Snapshots, Expansión de Volúmenes, Optimización del Rendimiento](./eks/04-eks-storage-part2.md) | [Cuestionario](./quizzes/eks/04-eks-storage-part2-quiz.md)
   - [Parte 3: Monitorización, Resolución de Problemas, Optimización de Costes, Seguridad](./eks/04-eks-storage-part3.md) | [Cuestionario](./quizzes/eks/04-eks-storage-part3-quiz.md)
5. [Seguridad en EKS](./eks/05-eks-security.md) | [Cuestionario](./quizzes/eks/05-eks-security-quiz.md)
6. [Monitorización y Logging en EKS](./eks/06-eks-monitoring-logging.md) | [Cuestionario](./quizzes/eks/06-eks-monitoring-logging-quiz.md)
7. [Optimización de Costes en EKS](./eks/07-eks-cost-optimization.md) | [Cuestionario](./quizzes/eks/07-eks-cost-optimization-quiz.md)
8. [Actualizaciones de EKS](./eks/08-eks-upgrades.md) | [Cuestionario](./quizzes/eks/08-eks-upgrades-quiz.md)
9. [Resolución de Problemas en EKS](./eks/09-eks-troubleshooting.md) | [Cuestionario](./quizzes/eks/09-eks-troubleshooting-quiz.md)
10. [Resiliencia y Alta Disponibilidad en EKS](./eks/10-eks-resiliency.md) | [Cuestionario](./quizzes/eks/10-eks-resiliency-quiz.md)
11. [Depuración Avanzada en EKS](./eks/11-eks-advanced-debugging.md) | [Cuestionario](./quizzes/eks/11-eks-advanced-debugging-quiz.md)
12. [Características y Hoja de Ruta de las Versiones de Kubernetes](./eks/12-kubernetes-version-roadmap.md) | [Cuestionario](./quizzes/eks/12-kubernetes-version-roadmap-quiz.md)

### EKS Hybrid Nodes
1. [Introducción a EKS Hybrid Nodes](./eks-hybrid-nodes/README.md)
2. [Requisitos Previos](./eks-hybrid-nodes/01-prerequisites.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
3. [Configuración de Red](./eks-hybrid-nodes/02-network-configuration.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
4. [Configuración de Entornos Air-Gap](./eks-hybrid-nodes/03-airgap-setup.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
5. [Bootstrap de Nodos](./eks-hybrid-nodes/04-node-bootstrap.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
6. [Integración de Servidores GPU](./eks-hybrid-nodes/05-gpu-integration.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
7. [Estrategias de Ubicación de Cargas de Trabajo](./eks-hybrid-nodes/06-workload-placement.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
8. [Gestión del Ciclo de Vida de los Nodos](./eks-hybrid-nodes/07-node-lifecycle.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
9. [Operaciones y Mantenimiento](./eks-hybrid-nodes/08-operations.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/08-operations-quiz.md)
10. [Configuración del SO en Bare Metal](./eks-hybrid-nodes/09-bare-metal-os-setup.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
11. [Hybrid Nodes Gateway](./eks-hybrid-nodes/10-hybrid-nodes-gateway.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)

### EKS Auto Mode
1. [Introducción a EKS Auto Mode](./eks-auto-mode/README.md)
2. [Primeros Pasos](./eks-auto-mode/01-getting-started.md) | [Cuestionario](./quizzes/eks-auto-mode/01-getting-started-quiz.md)
3. [Configuración de NodePool](./eks-auto-mode/02-nodepool-configuration.md) | [Cuestionario](./quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
4. [Comportamiento del Escalado](./eks-auto-mode/03-scaling-behavior.md) | [Cuestionario](./quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
5. [Estrategias con Instancias Spot](./eks-auto-mode/04-spot-strategies.md) | [Cuestionario](./quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
6. [Operaciones y Gestión](./eks-auto-mode/05-operations.md) | [Cuestionario](./quizzes/eks-auto-mode/05-operations-quiz.md)
7. [Gestión de Costes](./eks-auto-mode/06-cost-management.md) | [Cuestionario](./quizzes/eks-auto-mode/06-cost-management-quiz.md)
8. [Ciclo de Vida de los Nodos](./eks-auto-mode/07-node-lifecycle.md) | [Cuestionario](./quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
9. [Optimización de Cargas de Trabajo](./eks-auto-mode/08-workload-optimization.md) | [Cuestionario](./quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
10. [Guía de Migración](./eks-auto-mode/09-migration-guide.md) | [Cuestionario](./quizzes/eks-auto-mode/09-migration-guide-quiz.md)

### Redes
1. [Visión General de Redes](./networking/README.md) | [Cuestionario](./quizzes/networking/00-networking-overview-quiz.md)
2. [Fundamentos de Redes — 25 Protocolos](./basics/06-network-fundamentals-part1.md)
   - [Parte 1: El Modelo de Capas, Capas de Enlace y Enrutamiento](./basics/06-network-fundamentals-part1.md) | [Cuestionario](./quizzes/basics/06-network-fundamentals-part1-quiz.md)
   - [Parte 2: La Capa de Transporte y TLS](./basics/06-network-fundamentals-part2.md) | [Cuestionario](./quizzes/basics/06-network-fundamentals-part2-quiz.md)
   - [Parte 3: Protocolos de Aplicación](./basics/06-network-fundamentals-part3.md) | [Cuestionario](./quizzes/basics/06-network-fundamentals-part3-quiz.md)
   - [Parte 4: El Recorrido de una Petición y la Nube](./basics/06-network-fundamentals-part4.md) | [Cuestionario](./quizzes/basics/06-network-fundamentals-part4-quiz.md)
3. [VPC CNI](./networking/01-vpc-cni.md) | [Cuestionario](./quizzes/networking/01-vpc-cni-quiz.md)
4. **Cilium en Profundidad**
   - [Introducción a Cilium](./networking/cilium/README.md)
   - [Parte 1: Introducción](./networking/cilium/01-introduction.md) | [Cuestionario](./quizzes/networking/cilium/01-introduction-quiz.md)
   - [Parte 2: eBPF](./networking/cilium/02-ebpf.md) | [Cuestionario](./quizzes/networking/cilium/02-ebpf-quiz.md)
   - [Parte 3: Redes](./networking/cilium/03-networking.md) | [Cuestionario](./quizzes/networking/cilium/03-networking-quiz.md)
   - [Parte 4: IPAM y Políticas](./networking/cilium/04-ipam-policy.md) | [Cuestionario](./quizzes/networking/cilium/04-ipam-policy-quiz.md)
   - [Parte 5: Redes L2-L7](./networking/cilium/05-l2-l7-networking.md) | [Cuestionario](./quizzes/networking/cilium/05-l2-l7-networking-quiz.md)
   - [Parte 6: Seguridad y Visibilidad](./networking/cilium/06-security-visibility.md) | [Cuestionario](./quizzes/networking/cilium/06-security-visibility-quiz.md)
   - [Parte 7: Temas Avanzados](./networking/cilium/07-advanced-topics.md) | [Cuestionario](./quizzes/networking/cilium/07-advanced-topics-quiz.md)
   - [Conceptos de Redes](./networking/cilium/networking-concepts.md) | [Cuestionario](./quizzes/networking/cilium/networking-concepts-quiz.md)
   - [Glosario](./networking/cilium/glossary.md) | [Cuestionario](./quizzes/networking/cilium/glossary-quiz.md)
5. **Calico en Profundidad**
   - [Introducción a Calico](./networking/calico/README.md)
   - [Parte 1: Introducción](./networking/calico/01-introduction.md) | [Cuestionario](./quizzes/networking/calico/01-introduction-quiz.md)
   - [Parte 2: Arquitectura](./networking/calico/02-architecture.md) | [Cuestionario](./quizzes/networking/calico/02-architecture-quiz.md)
   - [Parte 3: Modos de Red](./networking/calico/03-networking-modes.md) | [Cuestionario](./quizzes/networking/calico/03-networking-modes-quiz.md)
   - [Parte 4: BGP en Profundidad](./networking/calico/04-bgp-deep-dive.md) | [Cuestionario](./quizzes/networking/calico/04-bgp-deep-dive-quiz.md)
   - [Parte 5: Network Policy](./networking/calico/05-network-policy.md) | [Cuestionario](./quizzes/networking/calico/05-network-policy-quiz.md)
   - [Parte 6: Dataplane de eBPF](./networking/calico/06-ebpf-dataplane.md) | [Cuestionario](./quizzes/networking/calico/06-ebpf-dataplane-quiz.md)
   - [Parte 7: Temas Avanzados](./networking/calico/07-advanced-topics.md) | [Cuestionario](./quizzes/networking/calico/07-advanced-topics-quiz.md)
   - [Parte 8: Integración con EKS](./networking/calico/08-eks-integration.md) | [Cuestionario](./quizzes/networking/calico/08-eks-integration-quiz.md)
   - [Parte 9: Operaciones](./networking/calico/09-operations.md) | [Cuestionario](./quizzes/networking/calico/09-operations-quiz.md)
   - [Glosario](./networking/calico/glossary.md) | [Cuestionario](./quizzes/networking/calico/glossary-quiz.md)
6. [VPC Lattice](./networking/02-vpc-lattice.md) | [Cuestionario](./quizzes/networking/02-vpc-lattice-quiz.md)
7. [AWS Load Balancer Controller](./networking/03-aws-lb-controller.md) | [Cuestionario](./quizzes/networking/03-aws-lb-controller-quiz.md)
8. [Gateway API](./networking/04-gateway-api.md) | [Cuestionario](./quizzes/networking/04-gateway-api-quiz.md)
9. [Conectividad de VPC entre Organizaciones](./networking/05-cross-org-vpc-connectivity.md) | [Cuestionario](./quizzes/networking/05-cross-org-vpc-connectivity-quiz.md)
10. [Benchmark de Red de Pods](./networking/06-pod-network-benchmark.md) | [Cuestionario](./quizzes/networking/06-pod-network-benchmark-quiz.md)

### Service Mesh
1. [Istio](./service-mesh/istio/README.md) | [Cuestionario](./quizzes/service-mesh/02-istio-quiz.md)
2. **Linkerd**
   - [Introducción a Linkerd](./service-mesh/linkerd/README.md)
   - [Instalación](./service-mesh/linkerd/01-installation.md) | [Cuestionario](./quizzes/service-mesh/linkerd/installation.md)
   - [Arquitectura](./service-mesh/linkerd/02-architecture.md) | [Cuestionario](./quizzes/service-mesh/linkerd/architecture.md)
   - [Gestión del Tráfico](./service-mesh/linkerd/03-traffic-management.md) | [Cuestionario](./quizzes/service-mesh/linkerd/traffic-management.md)
   - [Seguridad](./service-mesh/linkerd/04-security.md) | [Cuestionario](./quizzes/service-mesh/linkerd/security.md)
   - [Observabilidad](./service-mesh/linkerd/05-observability.md) | [Cuestionario](./quizzes/service-mesh/linkerd/observability.md)
   - [Multi-cluster](./service-mesh/linkerd/06-multi-cluster.md) | [Cuestionario](./quizzes/service-mesh/linkerd/multi-cluster.md)
   - [Buenas Prácticas](./service-mesh/linkerd/07-best-practices.md)
3. **Cilium Service Mesh**
   - [Introducción a Cilium Service Mesh](./service-mesh/cilium-service-mesh/README.md)
   - [Arquitectura](./service-mesh/cilium-service-mesh/01-architecture.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/architecture.md)
   - [Gestión del Tráfico](./service-mesh/cilium-service-mesh/02-traffic-management.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/traffic-management.md)
   - [Seguridad](./service-mesh/cilium-service-mesh/03-security.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/security.md)
   - [Observabilidad](./service-mesh/cilium-service-mesh/04-observability.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/observability.md)
   - [Ingress Gateway](./service-mesh/cilium-service-mesh/05-ingress-gateway.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/ingress-gateway.md)
   - [Buenas Prácticas](./service-mesh/cilium-service-mesh/06-best-practices.md)

### Almacenamiento
1. [Visión General del Almacenamiento](./storage/README.md)
2. [Benchmark Medido de EBS gp2 vs gp3](./storage/01-ebs-gp2-gp3-benchmark.md) | [Cuestionario](./quizzes/storage/01-ebs-gp2-gp3-benchmark-quiz.md)

### Bases de Datos
1. [Visión General de Bases de Datos en Kubernetes](./database/README.md)
2. [Benchmark Medido de ClickHouse en EKS](./database/01-clickhouse-on-eks.md) | [Cuestionario](./quizzes/database/01-clickhouse-on-eks-quiz.md)

### Canalización de Datos
1. [Visión General de Data on EKS](./data-on-eks/README.md)
   - [Anatomía de una Canalización de Datos Moderna](./data-on-eks/01-data-pipeline-anatomy.md) | [Cuestionario](./quizzes/data-on-eks/01-data-pipeline-anatomy-quiz.md)
   - [Gobernanza de SageMaker Unified Studio](./data-on-eks/sagemaker-unified-studio/README.md)
   - [Parte 4: Gobernanza de Dominios, Proyectos y Membresías](./data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | [Cuestionario](./quizzes/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance-quiz.md)
2. **Kafka en EKS en Profundidad**
   - [Introducción a Kafka en EKS](./data-on-eks/kafka/README.md)
   - [Parte 1: Fundamentos de Kafka](./data-on-eks/kafka/01-kafka-fundamentals.md) | [Cuestionario](./quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)
   - [Parte 2: Strimzi Operator](./data-on-eks/kafka/02-strimzi-operator.md) | [Cuestionario](./quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
   - [Parte 3: Operación de Kafka](./data-on-eks/kafka/03-kafka-operations.md) | [Cuestionario](./quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
   - [Parte 4: Schema Registry](./data-on-eks/kafka/04-schema-registry.md) | [Cuestionario](./quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
   - [Parte 5: Kafka Connect y MirrorMaker](./data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [Cuestionario](./quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
   - [Parte 6: Integración con MSK](./data-on-eks/kafka/06-msk-integration.md) | [Cuestionario](./quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
   - [Parte 7: Monitorización](./data-on-eks/kafka/07-monitoring.md) | [Cuestionario](./quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
   - [Parte 8: Buenas Prácticas](./data-on-eks/kafka/08-best-practices.md) | [Cuestionario](./quizzes/data-on-eks/kafka/08-best-practices-quiz.md)
   - [Parte 9: Benchmark Medido de Kafka](./data-on-eks/kafka/09-kafka-benchmark.md) | [Cuestionario](./quizzes/data-on-eks/kafka/09-kafka-benchmark-quiz.md)
3. **Spark en EKS en Profundidad**
   - [Introducción a Spark en EKS](./data-on-eks/spark/README.md)
   - [Parte 1: Fundamentos de Spark en Kubernetes](./data-on-eks/spark/01-spark-fundamentals.md) | [Cuestionario](./quizzes/data-on-eks/spark/01-spark-fundamentals-quiz.md)
   - [Parte 2: Spark Operator](./data-on-eks/spark/02-spark-operator.md) | [Cuestionario](./quizzes/data-on-eks/spark/02-spark-operator-quiz.md)
   - [Parte 3: Amazon EMR en EKS](./data-on-eks/spark/03-emr-on-eks.md) | [Cuestionario](./quizzes/data-on-eks/spark/03-emr-on-eks-quiz.md)
   - [Parte 4: Ajuste de Rendimiento y Costes](./data-on-eks/spark/04-performance-tuning.md) | [Cuestionario](./quizzes/data-on-eks/spark/04-performance-tuning-quiz.md)
   - [Parte 5: Buenas Prácticas y Seguridad](./data-on-eks/spark/05-best-practices.md) | [Cuestionario](./quizzes/data-on-eks/spark/05-best-practices-quiz.md)
4. **Airflow en EKS en Profundidad**
   - [Introducción a Airflow en EKS](./data-on-eks/airflow/README.md)
   - [Parte 1: Arquitectura de Airflow en Kubernetes](./data-on-eks/airflow/01-architecture.md) | [Cuestionario](./quizzes/data-on-eks/airflow/01-architecture-quiz.md)
   - [Parte 2: Despliegue con Helm y Elección del Executor](./data-on-eks/airflow/02-helm-deployment.md) | [Cuestionario](./quizzes/data-on-eks/airflow/02-helm-deployment-quiz.md)
   - [Parte 3: Patrones de DAG y KubernetesPodOperator](./data-on-eks/airflow/03-dag-patterns.md) | [Cuestionario](./quizzes/data-on-eks/airflow/03-dag-patterns-quiz.md)
   - [Parte 4: Integración con Amazon MWAA](./data-on-eks/airflow/04-mwaa-integration.md) | [Cuestionario](./quizzes/data-on-eks/airflow/04-mwaa-integration-quiz.md)
   - [Parte 5: Operaciones y Seguridad](./data-on-eks/airflow/05-operations.md) | [Cuestionario](./quizzes/data-on-eks/airflow/05-operations-quiz.md)
5. **Flink en EKS en Profundidad**
   - [Introducción a Flink en EKS](./data-on-eks/flink/README.md)
   - [Parte 1: Arquitectura de Flink en Kubernetes](./data-on-eks/flink/01-architecture.md) | [Cuestionario](./quizzes/data-on-eks/flink/01-architecture-quiz.md)
   - [Parte 2: Flink Kubernetes Operator](./data-on-eks/flink/02-flink-kubernetes-operator.md) | [Cuestionario](./quizzes/data-on-eks/flink/02-flink-kubernetes-operator-quiz.md)
   - [Parte 3: Estado, Checkpointing y Patrones de Streaming](./data-on-eks/flink/03-state-checkpointing-streaming.md) | [Cuestionario](./quizzes/data-on-eks/flink/03-state-checkpointing-streaming-quiz.md)
   - [Parte 4: Operaciones, Alta Disponibilidad y Managed Flink](./data-on-eks/flink/04-operations-ha.md) | [Cuestionario](./quizzes/data-on-eks/flink/04-operations-ha-quiz.md)

### IA/ML
1. [Cargas de Trabajo de IA/ML](./ai-ml/01-ai-ml-workloads.md) | [Cuestionario](./quizzes/ai-ml/03-ai-ml-workloads-quiz.md)
2. [Infraestructura de IA](./ai-ml/06-ai-infrastructure.md) | [Cuestionario](./quizzes/ai-ml/06-ai-infrastructure-quiz.md)
3. [Entrenamiento de Modelos en EKS](./ai-ml/05-model-training.md) | [Cuestionario](./quizzes/ai-ml/05-model-training-quiz.md)
4. [Frameworks de Inferencia](./ai-ml/04-inference-frameworks.md) | [Cuestionario](./quizzes/ai-ml/04-inference-frameworks-quiz.md)
5. [Despliegue y Optimización de vLLM](./ai-ml/02-vllm-deployment.md) | [Cuestionario](./quizzes/ai-ml/04-vllm-deployment-quiz.md)
6. [Plataforma de IA Agéntica en EKS](./ai-ml/03-agentic-ai-platform.md) | [Cuestionario](./quizzes/ai-ml/08-agentic-ai-platform-quiz.md)
7. [Buenas Prácticas de IA/ML](./ai-ml/07-ai-ml-best-practices.md) | [Cuestionario](./quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)
8. **Ray en EKS en Profundidad**
   - [Introducción a Ray en EKS](./ai-ml/ray/README.md)
   - [Parte 1: Arquitectura de Ray](./ai-ml/ray/01-architecture.md) | [Cuestionario](./quizzes/ai-ml/ray/01-architecture-quiz.md)
   - [Parte 2: El KubeRay Operator](./ai-ml/ray/02-kuberay-operator.md) | [Cuestionario](./quizzes/ai-ml/ray/02-kuberay-operator-quiz.md)
   - [Parte 3: Ray Train y Ray Tune](./ai-ml/ray/03-ray-train-tune.md) | [Cuestionario](./quizzes/ai-ml/ray/03-ray-train-tune-quiz.md)
   - [Parte 4: Ray Serve](./ai-ml/ray/04-ray-serve.md) | [Cuestionario](./quizzes/ai-ml/ray/04-ray-serve-quiz.md)
9. **Kubeflow en EKS en Profundidad**
   - [Introducción a Kubeflow en EKS](./ai-ml/kubeflow/README.md)
   - [Parte 1: Arquitectura de Kubeflow e Instalación en EKS](./ai-ml/kubeflow/01-architecture-installation.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/01-architecture-installation-quiz.md)
   - [Parte 2: Kubeflow Pipelines](./ai-ml/kubeflow/02-pipelines.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/02-pipelines-quiz.md)
   - [Parte 3: Kubeflow Notebooks](./ai-ml/kubeflow/03-notebooks.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/03-notebooks-quiz.md)
   - [Parte 4: Katib — Ajuste de Hiperparámetros y AutoML](./ai-ml/kubeflow/04-katib.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/04-katib-quiz.md)
   - [Parte 5: Kubeflow Trainer y Entrenamiento Distribuido](./ai-ml/kubeflow/05-training-operator.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/05-training-operator-quiz.md)
   - [Parte 6: KServe — Servicio de Modelos en Kubernetes](./ai-ml/kubeflow/06-kserve.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/06-kserve-quiz.md)
10. **MLflow en EKS en Profundidad**
   - [Introducción a MLflow en EKS](./ai-ml/mlflow/README.md)
   - [Parte 1: MLflow Tracking](./ai-ml/mlflow/01-tracking.md) | [Cuestionario](./quizzes/ai-ml/mlflow/01-tracking-quiz.md)
   - [Parte 2: MLflow Model Registry](./ai-ml/mlflow/02-model-registry.md) | [Cuestionario](./quizzes/ai-ml/mlflow/02-model-registry-quiz.md)
   - [Parte 3: Despliegue de MLflow en EKS](./ai-ml/mlflow/03-eks-deployment.md) | [Cuestionario](./quizzes/ai-ml/mlflow/03-eks-deployment-quiz.md)
11. **Guía de SageMaker AI Qwen PII**
   - [Introducción a la Guía](./ai-ml/sagemaker-ai/README.md)
   - [Parte 1: Arquitectura de la Plataforma](./ai-ml/sagemaker-ai/01-platform-architecture.md) | [Cuestionario](./quizzes/ai-ml/sagemaker-ai/01-platform-architecture-quiz.md)
   - [Parte 2: Datos PII Sintéticos y Tokenización](./ai-ml/sagemaker-ai/02-pii-data-tokenization.md) | [Cuestionario](./quizzes/ai-ml/sagemaker-ai/02-pii-data-tokenization-quiz.md)
   - [Parte 3: Ejecución con SageMaker AI y MLflow](./ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md) | [Cuestionario](./quizzes/ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution-quiz.md)
   - [Parte 4: Gobernanza de Unified Studio](./data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | [Cuestionario](./quizzes/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance-quiz.md)
   - [Parte 5: Resultados de la Validación Factual](./ai-ml/sagemaker-ai/04-validation-results.md) | [Cuestionario](./quizzes/ai-ml/sagemaker-ai/04-validation-results-quiz.md)
12. [LLM Gateway (Inference Gateway) en Profundidad](./ai-ml/08-llm-gateway.md) | [Cuestionario](./quizzes/ai-ml/08-llm-gateway-quiz.md)

### Seguridad y Políticas
1. [Gestión de Políticas con Kyverno](./security/01-kyverno-policy-management.md) | [Cuestionario](./quizzes/security/01-kyverno-policy-management-quiz.md)
2. [Autenticación y Autorización en Kubernetes](./security/02-kubernetes-auth-authz.md) | [Cuestionario](./quizzes/security/02-kubernetes-auth-authz-quiz.md)
3. [Pod Security Standards](./security/03-pod-security-standards.md) | [Cuestionario](./quizzes/security/03-pod-security-standards-quiz.md)
4. [Network Policies](./security/04-network-policies.md) | [Cuestionario](./quizzes/security/04-network-policies-quiz.md)
5. [Gestión de Secrets](./security/05-secrets-management.md) | [Cuestionario](./quizzes/security/05-secrets-management-quiz.md)
6. [Buenas Prácticas de Seguridad en EKS](./security/06-eks-security-best-practices.md) | [Cuestionario](./quizzes/security/06-eks-security-best-practices-quiz.md)
7. [Seguridad de Imágenes](./security/07-image-security.md) | [Cuestionario](./quizzes/security/07-image-security-quiz.md)
8. [Seguridad en Runtime](./security/08-runtime-security.md) | [Cuestionario](./quizzes/security/08-runtime-security-quiz.md)
9. [OPA Gatekeeper](./security/09-opa-gatekeeper.md) | [Cuestionario](./quizzes/security/09-opa-gatekeeper-quiz.md)
10. [cert-manager](./security/10-cert-manager.md) | [Cuestionario](./quizzes/security/10-cert-manager-quiz.md)
11. [Kubescape](./security/11-kubescape.md) | [Cuestionario](./quizzes/security/11-kubescape-quiz.md)
12. [SPIFFE/SPIRE](./security/12-spiffe-spire.md) | [Cuestionario](./quizzes/security/12-spiffe-spire-quiz.md)

### GitOps
1. [Visión General de GitOps](./gitops/README.md)
2. **ArgoCD**
   - [Introducción a ArgoCD](./gitops/argocd/README.md) | [Cuestionario](./quizzes/gitops/01-argocd-quiz.md)
   - [Instalación](./gitops/argocd/01-installation.md) | [Cuestionario](./quizzes/gitops/argocd/01-installation-quiz.md)
   - [Applications](./gitops/argocd/02-applications.md) | [Cuestionario](./quizzes/gitops/argocd/02-applications-quiz.md)
   - [Estrategias de Sincronización](./gitops/argocd/03-sync-strategies.md) | [Cuestionario](./quizzes/gitops/argocd/03-sync-strategies-quiz.md)
   - [ApplicationSets](./gitops/argocd/04-applicationsets.md) | [Cuestionario](./quizzes/gitops/argocd/04-applicationsets-quiz.md)
   - [Gestión del Tráfico](./gitops/argocd/05-traffic-management.md) | [Cuestionario](./quizzes/gitops/argocd/05-traffic-management-quiz.md)
   - [Projects y RBAC](./gitops/argocd/06-projects-rbac.md) | [Cuestionario](./quizzes/gitops/argocd/06-projects-rbac-quiz.md)
   - [Seguridad](./gitops/argocd/07-security.md) | [Cuestionario](./quizzes/gitops/argocd/07-security-quiz.md)
   - [Notificaciones](./gitops/argocd/08-notifications.md) | [Cuestionario](./quizzes/gitops/argocd/08-notifications-quiz.md)
   - [Buenas Prácticas](./gitops/argocd/09-best-practices.md) | [Cuestionario](./quizzes/gitops/argocd/09-best-practices-quiz.md)
   - [Experimentos con Rollouts en Profundidad](./gitops/argocd/10-rollouts-experiment.md) | [Cuestionario](./quizzes/gitops/argocd/10-rollouts-experiment-quiz.md)
3. [FluxCD](./gitops/02-fluxcd.md) | [Cuestionario](./quizzes/gitops/02-fluxcd-quiz.md)
4. [Comparación de Herramientas de GitOps](./gitops/03-gitops-comparison.md) | [Cuestionario](./quizzes/gitops/03-gitops-comparison-quiz.md)
5. [Entrega Progresiva con Flagger](./gitops/04-flagger.md) | [Cuestionario](./quizzes/gitops/04-flagger-quiz.md)
6. [Feature Flags y OpenFeature](./gitops/05-feature-flags.md) | [Cuestionario](./quizzes/gitops/05-feature-flags-quiz.md)

### Gobernanza Empresarial de la Nube
1. [Visión General de la Gobernanza](./governance/00-governance-overview.md) | [Cuestionario](./quizzes/governance/00-governance-overview-quiz.md)
2. [Landing Zone, OUs y Control Organizativo](./governance/01-landing-zone-and-ou.md) | [Cuestionario](./quizzes/governance/01-landing-zone-and-ou-quiz.md)
3. [Estructura de Cuentas y Límites de IAM](./governance/02-account-and-iam.md) | [Cuestionario](./quizzes/governance/02-account-and-iam-quiz.md)
4. [Arquitectura EKS Multi-Cuenta y Multi-Cluster](./governance/03-eks-multi-account-multi-cluster.md) | [Cuestionario](./quizzes/governance/03-eks-multi-account-multi-cluster-quiz.md)
5. [VPC Compartida y Conectividad](./governance/04-shared-vpc-and-connectivity.md) | [Cuestionario](./quizzes/governance/04-shared-vpc-and-connectivity-quiz.md)
6. [Límites de Datos y Seguridad](./governance/05-data-security-boundaries.md) | [Cuestionario](./quizzes/governance/05-data-security-boundaries-quiz.md)
7. [Marco de Decisión y Diseño de PoC](./governance/06-decision-framework-and-poc.md) | [Cuestionario](./quizzes/governance/06-decision-framework-and-poc-quiz.md)

### Platform Engineering
0. [Visión General de Platform Engineering](./platform-engineering/00-platform-engineering-overview.md) | [Cuestionario](./quizzes/platform-engineering/00-platform-engineering-overview-quiz.md)
1. [Helm](./platform-engineering/01-helm.md) | [Cuestionario](./quizzes/platform-engineering/01-helm-quiz.md)
2. [AWS Controllers for Kubernetes (ACK)](./platform-engineering/02-ack.md) | [Cuestionario](./quizzes/platform-engineering/02-ack-quiz.md)
3. [Kubernetes Resource Operator (KRO)](./platform-engineering/03-kro.md) | [Cuestionario](./quizzes/platform-engineering/03-kro-quiz.md)
4. [Mecanismos de Extensión de Kubernetes](./platform-engineering/04-kubernetes-extensions.md) | [Cuestionario](./quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
5. [ExampleCorp: Ejemplo de Integración de ACK + KRO](./platform-engineering/05-example-corp-app.md)
6. [Backstage IDP](./platform-engineering/06-backstage-idp.md) | [Cuestionario](./quizzes/platform-engineering/06-backstage-idp-quiz.md)
7. [Crossplane](./platform-engineering/07-crossplane.md) | [Cuestionario](./quizzes/platform-engineering/07-crossplane-quiz.md)
8. [vCluster](./platform-engineering/08-vcluster.md) | [Cuestionario](./quizzes/platform-engineering/08-vcluster-quiz.md)

### Registro de Contenedores
1. [Visión General del Registro de Contenedores](./container-registry/README.md)
2. [Docker Hub](./container-registry/01-docker-hub.md) | [Cuestionario](./quizzes/container-registry/01-docker-hub-quiz.md)
3. [Amazon ECR](./container-registry/02-amazon-ecr.md) | [Cuestionario](./quizzes/container-registry/02-amazon-ecr-quiz.md)
4. [Harbor](./container-registry/03-harbor.md) | [Cuestionario](./quizzes/container-registry/03-harbor-quiz.md)
5. [Buenas Prácticas para Registros de Contenedores](./container-registry/04-best-practices.md) | [Cuestionario](./quizzes/container-registry/04-best-practices-quiz.md)

### Observabilidad
1. [Visión General de la Observabilidad](./observability/README.md)
2. **Métricas**
   - [Visión General de Métricas](./observability/metrics/README.md) | [Cuestionario](./quizzes/observability/metrics/00-metrics-overview-quiz.md)
   - [Prometheus](./observability/metrics/01-prometheus.md) | [Cuestionario](./quizzes/observability/metrics/01-prometheus-quiz.md)
   - [VictoriaMetrics](./observability/metrics/02-victoriametrics.md) | [Cuestionario](./quizzes/observability/metrics/02-victoriametrics-quiz.md)
   - [Grafana Mimir](./observability/metrics/03-mimir.md) | [Cuestionario](./quizzes/observability/metrics/03-mimir-quiz.md)
   - [CloudWatch Metrics](./observability/metrics/04-cloudwatch-metrics.md) | [Cuestionario](./quizzes/observability/metrics/04-cloudwatch-metrics-quiz.md)
   - [Datadog](./observability/metrics/05-datadog.md) | [Cuestionario](./quizzes/observability/metrics/05-datadog-quiz.md)
3. **Logging**
   - [Visión General del Logging](./observability/logging/README.md) | [Cuestionario](./quizzes/observability/logging/README-quiz.md)
   - [Grafana Loki](./observability/logging/01-loki.md) | [Cuestionario](./quizzes/observability/logging/01-loki-quiz.md)
   - [OpenSearch](./observability/logging/02-opensearch.md) | [Cuestionario](./quizzes/observability/logging/02-opensearch-quiz.md)
   - [CloudWatch Logs](./observability/logging/03-cloudwatch-logs.md) | [Cuestionario](./quizzes/observability/logging/03-cloudwatch-logs-quiz.md)
   - [ClickHouse](./observability/logging/04-clickhouse.md) | [Cuestionario](./quizzes/observability/logging/04-clickhouse-quiz.md)
   - [Colectores de Logs](./observability/logging/05-collectors.md) | [Cuestionario](./quizzes/observability/logging/05-collectors-quiz.md)
4. **Tracing**
   - [Visión General del Tracing](./observability/tracing/README.md)
   - [Grafana Tempo](./observability/tracing/01-tempo.md) | [Cuestionario](./quizzes/observability/tracing/01-tempo-quiz.md)
   - [AWS X-Ray](./observability/tracing/02-xray.md) | [Cuestionario](./quizzes/observability/tracing/02-xray-quiz.md)
   - [OpenTelemetry](./observability/tracing/03-opentelemetry.md) | [Cuestionario](./quizzes/observability/tracing/03-opentelemetry-quiz.md)
   - [Dynatrace](./observability/tracing/04-dynatrace.md) | [Cuestionario](./quizzes/observability/tracing/04-dynatrace-quiz.md)
5. **Alertas**
   - [Visión General de las Alertas](./observability/alerting/README.md)
   - [Alertmanager](./observability/alerting/01-alertmanager.md) | [Cuestionario](./quizzes/observability/alerting/01-alertmanager-quiz.md)
   - [CloudWatch Alarms](./observability/alerting/02-cloudwatch-alarms.md) | [Cuestionario](./quizzes/observability/alerting/02-cloudwatch-alarms-quiz.md)
   - [Grafana OnCall](./observability/alerting/03-grafana-oncall.md) | [Cuestionario](./quizzes/observability/alerting/03-grafana-oncall-quiz.md)
6. [Grafana](./observability/grafana/README.md) | [Cuestionario](./quizzes/observability/grafana/grafana-quiz.md)
7. [Guía de Optimización de la Observabilidad](./observability/09-observability-optimization.md) | [Cuestionario](./quizzes/observability/09-observability-optimization-quiz.md)

### Guía de Operaciones
1. [Configuración de la Infraestructura](./ops/01-infrastructure-setup.md) | [Cuestionario](./quizzes/ops/01-infrastructure-setup-quiz.md)
2. [Infraestructura Avanzada](./ops/02-infrastructure-advanced.md) | [Cuestionario](./quizzes/ops/02-infrastructure-advanced-quiz.md)
3. [Pipelines de CI](./ops/03-ci-pipelines.md) | [Cuestionario](./quizzes/ops/03-ci-pipelines-quiz.md)
4. [GitOps Multi-Cluster](./ops/04-gitops-multi-cluster.md) | [Cuestionario](./quizzes/ops/04-gitops-multi-cluster-quiz.md)
5. [Automatización de GitOps](./ops/05-gitops-automation.md) | [Cuestionario](./quizzes/ops/05-gitops-automation-quiz.md)
6. [Estrategias de Escalado](./ops/06-scaling-strategies.md) | [Cuestionario](./quizzes/ops/06-scaling-strategies-quiz.md)
7. [Alertas de Observabilidad](./ops/07-observability-alerts.md) | [Cuestionario](./quizzes/ops/07-observability-alerts-quiz.md)
8. [Análisis de Observabilidad](./ops/08-observability-analysis.md) | [Cuestionario](./quizzes/ops/08-observability-analysis-quiz.md)
9. [Stack de Observabilidad](./ops/09-observability-stack.md) | [Cuestionario](./quizzes/ops/09-observability-stack-quiz.md)
10. [Optimización de Recursos](./ops/10-resource-optimization.md) | [Cuestionario](./quizzes/ops/10-resource-optimization-quiz.md)
11. [Operaciones de Actualización](./ops/11-upgrade-operations.md) | [Cuestionario](./quizzes/ops/11-upgrade-operations-quiz.md)
12. [Playbook de Planificación de Capacidad para Eventos](./ops/12-event-capacity-planning.md) | [Cuestionario](./quizzes/ops/12-event-capacity-planning-quiz.md)
13. [Plataforma FinOps de Visibilidad de Costes](./ops/13-finops-cost-platform.md) | [Cuestionario](./quizzes/ops/13-finops-cost-platform-quiz.md)
14. [Tekton Pipelines](./ops/14-tekton-pipelines.md) | [Cuestionario](./quizzes/ops/14-tekton-pipelines-quiz.md)
15. [Operación de Clusters Zonales](./ops/15-zonal-operations-guide.md) | [Cuestionario](./quizzes/ops/15-zonal-operations-guide-quiz.md)
16. [Playbook de Resolución de Problemas](./ops/16-troubleshooting-playbook.md) | [Cuestionario](./quizzes/ops/16-troubleshooting-playbook-quiz.md)
17. [Experimentos de EKS Spot en Producción y Evaluación de Resultados](./ops/17-spot-production-experiments.md) | [Cuestionario](./quizzes/ops/17-spot-production-experiments-quiz.md)

## Guías de Laboratorio

Proporcionamos guías de laboratorio prácticas para practicar en entornos reales después de aprender la teoría.

- [Lista de Guías de Laboratorio](./labs/README.md)
- Fundamentos: Laboratorios de Fundamentos de Linux, Operación de Linux y Contenedores
- Core: Laboratorios de Pod, Service, Almacenamiento y ConfigMap
- EKS: Laboratorio de Creación de un Cluster

### Laboratorios de Observabilidad de Extremo a Extremo
1. [Introducción a la Serie de Laboratorios](./labs/observability/README.md)
2. [Parte 1: Configuración de la Infraestructura](./labs/observability/01-infrastructure-setup-lab.md) | [Cuestionario](./quizzes/observability/labs/01-infrastructure-setup-quiz.md)
3. [Parte 2: Stack de Observabilidad](./labs/observability/02-observability-stack-lab.md) | [Cuestionario](./quizzes/observability/labs/02-observability-stack-quiz.md)
4. [Parte 3: Despliegue de MSA y Canary](./labs/observability/03-msa-deployment-lab.md) | [Cuestionario](./quizzes/observability/labs/03-msa-deployment-quiz.md)
5. [Parte 4: Pruebas de Carga y Autoescalado](./labs/observability/04-load-testing-scaling-lab.md) | [Cuestionario](./quizzes/observability/labs/04-load-testing-scaling-quiz.md)
6. [Parte 5: Alertas y AIOps](./labs/observability/05-alerting-aiops-lab.md) | [Cuestionario](./quizzes/observability/labs/05-alerting-aiops-quiz.md)
7. [Parte 6: Análisis de Trazas Distribuidas](./labs/observability/06-distributed-tracing-lab.md) | [Cuestionario](./quizzes/observability/labs/06-distributed-tracing-quiz.md)

## Guía de Aprendizaje

### Ruta de Aprendizaje para Principiantes
1. Estudia en este orden: **Linux y Contenedores** -> **Conceptos Fundamentales de Kubernetes** -> **Amazon EKS**
2. Después de leer cada capítulo, realiza el cuestionario correspondiente para comprobar tu comprensión
3. Ejecuta los comandos y el código de ejemplo de forma práctica en un entorno de pruebas

### Ruta de Aprendizaje para Usuarios Avanzados
1. Estudia en este orden: **Amazon EKS** -> **IA/ML** -> **Service Mesh** -> **Seguridad y Políticas**
2. Profundiza en redes con la sección de **Cilium**
3. Céntrate en herramientas o tecnologías concretas para un aprendizaje en profundidad

### Cómo Usar los Cuestionarios
- Haz clic en el enlace del cuestionario al final de cada documento para comprobar tu aprendizaje
- Piensa primero en las respuestas desplegables antes de revelarlas
- Repasa el documento correspondiente para las preguntas que hayas fallado

## Contribuir

Si quieres contribuir a este proyecto:
1. Abre un issue cuando encuentres errores tipográficos o errores de contenido
2. Sugiere nuevos temas o mejoras
3. Sugiere adiciones o mejoras a las preguntas de los cuestionarios

## Licencia

Este material de formación es de uso libre con fines de aprendizaje.
