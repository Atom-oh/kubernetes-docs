> [Versión coreana](https://www.atomai.click/kubernetes-docs/ko/)

# Contenido de formación de Kubernetes y Amazon EKS
[![GitBook](https://img.shields.io/static/v1?message=Documented%20on%20GitBook&logo=gitbook&logoColor=ffffff&label=%20&labelColor=5c5c5c&color=3F89A1)](https://www.gitbook.com/preview?utm_source=gitbook_readme_badge&utm_medium=organic&utm_campaign=preview_documentation&utm_content=link)

Este repositorio es una guía integral de cloud que abarca los fundamentos de Linux y contenedores, Kubernetes y Amazon EKS, redes, service mesh, almacenamiento, bases de datos, pipelines de datos, AI/ML, y seguridad y operaciones. Además de los materiales de aprendizaje, proporciona datos de benchmark medidos en entornos AWS reales, así como cuestionarios temáticos y laboratorios prácticos seleccionados.

## Materiales de aprendizaje y cuestionarios

Este contenido de formación proporciona cuestionarios para cada tema junto con los materiales de aprendizaje. Puedes poner a prueba y reforzar lo aprendido mediante los cuestionarios. Cada cuestionario está diseñado con respuestas de estilo desplegable ocultas, lo que te permite intentar responder las preguntas antes de revelar las respuestas.

- [Índice de materiales de aprendizaje](#table-of-contents) - Materiales de aprendizaje por tema
- [Colección de cuestionarios](./quizzes/README.md) - Cuestionarios por tema
- [Hoja de ruta de la guía](./roadmap.md) - El mapa de aprendizaje completo y las rutas de aprendizaje recomendadas | [Cuestionario](./quizzes/roadmap-quiz.md)
- [Lectura con LLMs](./llm-guide.md) - Encuentra y lee material de origen mediante llms.txt, el manifiesto y MCP | [Cuestionario](./quizzes/llm-guide-quiz.md)

## Índice

### Noticias
- [Noticias semanales](./news/README.md) - Resúmenes de las noticias más recientes del ecosistema Kubernetes/EKS

### Linux y contenedores
1. [Fundamentos de Linux](./basics/01-linux-basics.md) | [Cuestionario](./quizzes/basics/01-linux-basics-quiz.md) | [Laboratorio](./labs/basics/01-linux-basics-lab.md)
2. [Habilidades operativas de Linux](./basics/02-linux-advanced.md) | [Cuestionario](./quizzes/basics/02-linux-advanced-quiz.md) | [Laboratorio](./labs/basics/02-linux-advanced-lab.md)
3. [Tecnología de contenedores](./basics/03-container-technology.md) | [Cuestionario](./quizzes/basics/03-container-technology-quiz.md) | [Laboratorio](./labs/basics/03-container-technology-lab.md)
4. [Fundamentos de eBPF y aplicaciones prácticas](./basics/05-ebpf-fundamentals.md) | [Cuestionario](./quizzes/basics/05-ebpf-fundamentals-quiz.md)

### Kernel de Linux
1. [Descripción general del kernel de Linux](./kernel/README.md)
2. [Características del kernel detrás de los contenedores](./kernel/01-container-primitives.md) | [Cuestionario](./quizzes/kernel/01-container-primitives-quiz.md)
3. [Stack de red del kernel](./kernel/02-network-stack.md) | [Cuestionario](./quizzes/kernel/02-network-stack-quiz.md)
4. [Ajuste del kernel de nodos EKS](./kernel/03-eks-node-tuning.md) | [Cuestionario](./quizzes/kernel/03-eks-node-tuning-quiz.md)

### Conceptos básicos de Kubernetes
1. [Introducción a Kubernetes](./basics/04-kubernetes-introduction.md) | [Cuestionario](./quizzes/basics/04-kubernetes-introduction-quiz.md)
2. [Arquitectura de clúster](./core/01-cluster-architecture.md) | [Cuestionario](./quizzes/core/01-cluster-architecture-quiz.md)
3. [Pods y workloads](./core/02-pods-and-workloads.md) | [Cuestionario](./quizzes/core/02-pods-and-workloads-quiz.md)
4. [Services y redes](./core/03-services-networking.md) | [Cuestionario](./quizzes/core/03-services-networking-quiz.md)
5. [Almacenamiento](./core/04-storage.md) | [Cuestionario](./quizzes/core/04-storage-quiz.md)
6. [Configuración](./core/05-configuration-secrets.md) | [Cuestionario](./quizzes/core/05-configuration-secrets-quiz.md)
7. [Seguridad](./core/06-security.md) | [Cuestionario](./quizzes/core/06-security-quiz.md)
8. [Políticas](./core/07-policies.md) | [Cuestionario](./quizzes/core/07-policies-quiz.md)
9. [Scheduling, preemption y eviction](./core/08-scheduling-preemption-eviction.md) | [Cuestionario](./quizzes/core/08-scheduling-preemption-eviction-quiz.md)
10. [Administración de clústeres](./core/09-cluster-administration.md) | [Cuestionario](./quizzes/core/09-cluster-administration-quiz.md)
11. [Windows en Kubernetes](./core/10-windows-in-kubernetes.md) | [Cuestionario](./quizzes/core/10-windows-in-kubernetes-quiz.md)
12. [Extensión de Kubernetes](./core/11-extending-kubernetes.md) | [Cuestionario](./quizzes/core/11-extending-kubernetes-quiz.md)
13. Scheduler personalizado
   - [Parte 1: Fundamentos del scheduler personalizado](./scheduling/01-custom-scheduler-part1.md) | [Cuestionario](./quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
   - [Parte 2: Extensiones y framework del scheduler](./scheduling/02-custom-scheduler-part2.md) | [Cuestionario](./quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
   - [Parte 3: Ejemplos de implementación y monitorización del scheduler personalizado](./scheduling/03-custom-scheduler-part3.md) | [Cuestionario](./quizzes/scheduling/02-custom-scheduler-part3-quiz.md)
14. Autoscaling
   - [KEDA](./autoscaling/01-keda.md) | [Cuestionario](./quizzes/autoscaling/05-keda-quiz.md)
   - [Karpenter](./autoscaling/02-karpenter.md) | [Cuestionario](./quizzes/autoscaling/06-karpenter-quiz.md)
   - [Knative](./autoscaling/03-knative.md) | [Cuestionario](./quizzes/autoscaling/03-knative-quiz.md)

### Amazon EKS
1. [Introducción a EKS](./eks/01-eks-introduction.md) | [Cuestionario](./quizzes/eks/01-eks-introduction-quiz.md)
2. Creación de clústeres EKS
   - [Parte 1: Requisitos previos](./eks/02-eks-cluster-creation-part1.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
   - [Parte 2: Creación de clústeres con eksctl](./eks/02-eks-cluster-creation-part2.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part2-quiz.md)
   - [Parte 3: Creación de clústeres con AWS Management Console y CLI](./eks/02-eks-cluster-creation-part3.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part3-quiz.md)
   - [Parte 4: Creación de clústeres con Terraform y CDK](./eks/02-eks-cluster-creation-part4.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part4-quiz.md)
   - [Parte 5: Acceso, validación, actualización y eliminación de clústeres](./eks/02-eks-cluster-creation-part5.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part5-quiz.md)
3. Redes de EKS
   - [Parte 1: Conceptos básicos y configuración de VPC](./eks/03-eks-networking-part1.md) | [Cuestionario](./quizzes/eks/03-eks-networking-part1-quiz.md)
   - [Parte 2: Services y balanceo de carga, políticas de red](./eks/03-eks-networking-part2.md) | [Cuestionario](./quizzes/eks/03-eks-networking-part2-quiz.md)
   - [Parte 3: Optimización del rendimiento, troubleshooting, casos de uso avanzados](./eks/03-eks-networking-part3.md) | [Cuestionario](./quizzes/eks/03-eks-networking-part3-quiz.md)
4. Almacenamiento de EKS
   - [Parte 1: Conceptos básicos, EBS, EFS](./eks/04-eks-storage-part1.md) | [Cuestionario](./quizzes/eks/04-eks-storage-part1-quiz.md)
   - [Parte 2: FSx for Lustre, S3, snapshots, expansión de volumen, optimización del rendimiento](./eks/04-eks-storage-part2.md) | [Cuestionario](./quizzes/eks/04-eks-storage-part2-quiz.md)
   - [Parte 3: Monitorización, troubleshooting, optimización de costes, seguridad](./eks/04-eks-storage-part3.md) | [Cuestionario](./quizzes/eks/04-eks-storage-part3-quiz.md)
5. [Seguridad de EKS](./eks/05-eks-security.md) | [Cuestionario](./quizzes/eks/05-eks-security-quiz.md)
6. [Monitorización y logging de EKS](./eks/06-eks-monitoring-logging.md) | [Cuestionario](./quizzes/eks/06-eks-monitoring-logging-quiz.md)
7. [Optimización de costes de EKS](./eks/07-eks-cost-optimization.md) | [Cuestionario](./quizzes/eks/07-eks-cost-optimization-quiz.md)
8. [Actualizaciones de EKS](./eks/08-eks-upgrades.md) | [Cuestionario](./quizzes/eks/08-eks-upgrades-quiz.md)
9. [Troubleshooting de EKS](./eks/09-eks-troubleshooting.md) | [Cuestionario](./quizzes/eks/09-eks-troubleshooting-quiz.md)
10. [Resiliencia y alta disponibilidad de EKS](./eks/10-eks-resiliency.md) | [Cuestionario](./quizzes/eks/10-eks-resiliency-quiz.md)
11. [Depuración avanzada de EKS](./eks/11-eks-advanced-debugging.md) | [Cuestionario](./quizzes/eks/11-eks-advanced-debugging-quiz.md)
12. [Características y hoja de ruta de las versiones de Kubernetes](./eks/12-kubernetes-version-roadmap.md) | [Cuestionario](./quizzes/eks/12-kubernetes-version-roadmap-quiz.md)

### Nodos híbridos de EKS
1. [Introducción a los nodos híbridos de EKS](./eks-hybrid-nodes/README.md)
2. [Requisitos previos](./eks-hybrid-nodes/01-prerequisites.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
3. [Configuración de red](./eks-hybrid-nodes/02-network-configuration.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
4. [Configuración de entornos air-gap](./eks-hybrid-nodes/03-airgap-setup.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
5. [Bootstrap de nodos](./eks-hybrid-nodes/04-node-bootstrap.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
6. [Integración de servidores GPU](./eks-hybrid-nodes/05-gpu-integration.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
7. [Estrategias de colocación de workloads](./eks-hybrid-nodes/06-workload-placement.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
8. [Gestión del ciclo de vida de nodos](./eks-hybrid-nodes/07-node-lifecycle.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
9. [Operaciones y mantenimiento](./eks-hybrid-nodes/08-operations.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/08-operations-quiz.md)
10. [Configuración de SO bare metal](./eks-hybrid-nodes/09-bare-metal-os-setup.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
11. [Gateway de nodos híbridos](./eks-hybrid-nodes/10-hybrid-nodes-gateway.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)

### Modo automático de EKS
1. [Introducción al modo automático de EKS](./eks-auto-mode/README.md)
2. [Primeros pasos](./eks-auto-mode/01-getting-started.md) | [Cuestionario](./quizzes/eks-auto-mode/01-getting-started-quiz.md)
3. [Configuración de NodePool](./eks-auto-mode/02-nodepool-configuration.md) | [Cuestionario](./quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
4. [Comportamiento de escalado](./eks-auto-mode/03-scaling-behavior.md) | [Cuestionario](./quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
5. [Estrategias de instancias Spot](./eks-auto-mode/04-spot-strategies.md) | [Cuestionario](./quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
6. [Operaciones y gestión](./eks-auto-mode/05-operations.md) | [Cuestionario](./quizzes/eks-auto-mode/05-operations-quiz.md)
7. [Gestión de costes](./eks-auto-mode/06-cost-management.md) | [Cuestionario](./quizzes/eks-auto-mode/06-cost-management-quiz.md)
8. [Ciclo de vida de nodos](./eks-auto-mode/07-node-lifecycle.md) | [Cuestionario](./quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
9. [Optimización de workloads](./eks-auto-mode/08-workload-optimization.md) | [Cuestionario](./quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
10. [Guía de migración](./eks-auto-mode/09-migration-guide.md) | [Cuestionario](./quizzes/eks-auto-mode/09-migration-guide-quiz.md)

### Redes
1. [Descripción general de redes](./networking/README.md) | [Cuestionario](./quizzes/networking/00-networking-overview-quiz.md)
2. [Fundamentos de red — 25 protocolos](./basics/06-network-fundamentals-part1.md)
   - [Parte 1: El modelo de capas, capas de enlace y routing](./basics/06-network-fundamentals-part1.md) | [Cuestionario](./quizzes/basics/06-network-fundamentals-part1-quiz.md)
   - [Parte 2: La capa de transporte y TLS](./basics/06-network-fundamentals-part2.md) | [Cuestionario](./quizzes/basics/06-network-fundamentals-part2-quiz.md)
   - [Parte 3: Protocolos de aplicación](./basics/06-network-fundamentals-part3.md) | [Cuestionario](./quizzes/basics/06-network-fundamentals-part3-quiz.md)
   - [Parte 4: El recorrido de una solicitud y la cloud](./basics/06-network-fundamentals-part4.md) | [Cuestionario](./quizzes/basics/06-network-fundamentals-part4-quiz.md)
3. [VPC CNI](./networking/01-vpc-cni.md) | [Cuestionario](./quizzes/networking/01-vpc-cni-quiz.md)
4. **Análisis en profundidad de Cilium**
   - [Introducción a Cilium](./networking/cilium/README.md)
   - [Parte 1: Introducción](./networking/cilium/01-introduction.md) | [Cuestionario](./quizzes/networking/cilium/01-introduction-quiz.md)
   - [Parte 2: eBPF](./networking/cilium/02-ebpf.md) | [Cuestionario](./quizzes/networking/cilium/02-ebpf-quiz.md)
   - [Parte 3: Redes](./networking/cilium/03-networking.md) | [Cuestionario](./quizzes/networking/cilium/03-networking-quiz.md)
   - [Parte 4: IPAM y políticas](./networking/cilium/04-ipam-policy.md) | [Cuestionario](./quizzes/networking/cilium/04-ipam-policy-quiz.md)
   - [Parte 5: Redes L2-L7](./networking/cilium/05-l2-l7-networking.md) | [Cuestionario](./quizzes/networking/cilium/05-l2-l7-networking-quiz.md)
   - [Parte 6: Seguridad y visibilidad](./networking/cilium/06-security-visibility.md) | [Cuestionario](./quizzes/networking/cilium/06-security-visibility-quiz.md)
   - [Parte 7: Temas avanzados](./networking/cilium/07-advanced-topics.md) | [Cuestionario](./quizzes/networking/cilium/07-advanced-topics-quiz.md)
   - [Conceptos de red](./networking/cilium/networking-concepts.md) | [Cuestionario](./quizzes/networking/cilium/networking-concepts-quiz.md)
   - [Glosario](./networking/cilium/glossary.md) | [Cuestionario](./quizzes/networking/cilium/glossary-quiz.md)
5. **Análisis en profundidad de Calico**
   - [Introducción a Calico](./networking/calico/README.md)
   - [Parte 1: Introducción](./networking/calico/01-introduction.md) | [Cuestionario](./quizzes/networking/calico/01-introduction-quiz.md)
   - [Parte 2: Arquitectura](./networking/calico/02-architecture.md) | [Cuestionario](./quizzes/networking/calico/02-architecture-quiz.md)
   - [Parte 3: Modos de red](./networking/calico/03-networking-modes.md) | [Cuestionario](./quizzes/networking/calico/03-networking-modes-quiz.md)
   - [Parte 4: Análisis en profundidad de BGP](./networking/calico/04-bgp-deep-dive.md) | [Cuestionario](./quizzes/networking/calico/04-bgp-deep-dive-quiz.md)
   - [Parte 5: Política de red](./networking/calico/05-network-policy.md) | [Cuestionario](./quizzes/networking/calico/05-network-policy-quiz.md)
   - [Parte 6: Dataplane eBPF](./networking/calico/06-ebpf-dataplane.md) | [Cuestionario](./quizzes/networking/calico/06-ebpf-dataplane-quiz.md)
   - [Parte 7: Temas avanzados](./networking/calico/07-advanced-topics.md) | [Cuestionario](./quizzes/networking/calico/07-advanced-topics-quiz.md)
   - [Parte 8: Integración de EKS](./networking/calico/08-eks-integration.md) | [Cuestionario](./quizzes/networking/calico/08-eks-integration-quiz.md)
   - [Parte 9: Operaciones](./networking/calico/09-operations.md) | [Cuestionario](./quizzes/networking/calico/09-operations-quiz.md)
   - [Glosario](./networking/calico/glossary.md) | [Cuestionario](./quizzes/networking/calico/glossary-quiz.md)
6. [VPC Lattice](./networking/02-vpc-lattice.md) | [Cuestionario](./quizzes/networking/02-vpc-lattice-quiz.md)
7. [AWS Load Balancer Controller](./networking/03-aws-lb-controller.md) | [Cuestionario](./quizzes/networking/03-aws-lb-controller-quiz.md)
8. [Gateway API](./networking/04-gateway-api.md) | [Cuestionario](./quizzes/networking/04-gateway-api-quiz.md)
9. [Conectividad VPC entre organizaciones](./networking/05-cross-org-vpc-connectivity.md) | [Cuestionario](./quizzes/networking/05-cross-org-vpc-connectivity-quiz.md)
10. [Benchmark de red de Pods](./networking/06-pod-network-benchmark.md) | [Cuestionario](./quizzes/networking/06-pod-network-benchmark-quiz.md)

### Service Mesh
1. [Istio](./service-mesh/istio/README.md) | [Cuestionario](./quizzes/service-mesh/02-istio-quiz.md)
2. **Linkerd**
   - [Introducción a Linkerd](./service-mesh/linkerd/README.md)
   - [Instalación](./service-mesh/linkerd/01-installation.md) | [Cuestionario](./quizzes/service-mesh/linkerd/installation.md)
   - [Arquitectura](./service-mesh/linkerd/02-architecture.md) | [Cuestionario](./quizzes/service-mesh/linkerd/architecture.md)
   - [Gestión de tráfico](./service-mesh/linkerd/03-traffic-management.md) | [Cuestionario](./quizzes/service-mesh/linkerd/traffic-management.md)
   - [Seguridad](./service-mesh/linkerd/04-security.md) | [Cuestionario](./quizzes/service-mesh/linkerd/security.md)
   - [Observabilidad](./service-mesh/linkerd/05-observability.md) | [Cuestionario](./quizzes/service-mesh/linkerd/observability.md)
   - [Multiclúster](./service-mesh/linkerd/06-multi-cluster.md) | [Cuestionario](./quizzes/service-mesh/linkerd/multi-cluster.md)
   - [Mejores prácticas](./service-mesh/linkerd/07-best-practices.md)
3. **Cilium Service Mesh**
   - [Introducción a Cilium Service Mesh](./service-mesh/cilium-service-mesh/README.md)
   - [Arquitectura](./service-mesh/cilium-service-mesh/01-architecture.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/architecture.md)
   - [Gestión de tráfico](./service-mesh/cilium-service-mesh/02-traffic-management.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/traffic-management.md)
   - [Seguridad](./service-mesh/cilium-service-mesh/03-security.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/security.md)
   - [Observabilidad](./service-mesh/cilium-service-mesh/04-observability.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/observability.md)
   - [Ingress Gateway](./service-mesh/cilium-service-mesh/05-ingress-gateway.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/ingress-gateway.md)
   - [Mejores prácticas](./service-mesh/cilium-service-mesh/06-best-practices.md)

4. **Análisis en profundidad de VPC Lattice**
   - [Descripción general del análisis en profundidad de VPC Lattice](./service-mesh/vpc-lattice/README.md)
   - [Arquitectura de App Mesh frente a VPC Lattice](./service-mesh/vpc-lattice/01-appmesh-vs-lattice.md) | [Cuestionario](./quizzes/service-mesh/vpc-lattice/01-appmesh-vs-lattice-quiz.md)
   - [Análisis del impacto de la latencia](./service-mesh/vpc-lattice/02-latency.md) | [Cuestionario](./quizzes/service-mesh/vpc-lattice/02-latency-quiz.md)
   - [Flujo de autenticación IAM](./service-mesh/vpc-lattice/03-auth-flow.md) | [Cuestionario](./quizzes/service-mesh/vpc-lattice/03-auth-flow-quiz.md)
   - [Fundamentos — link-local y SNI](./service-mesh/vpc-lattice/04-networking-basics.md) | [Cuestionario](./quizzes/service-mesh/vpc-lattice/04-networking-basics-quiz.md)
   - [Migración de identidad de workload](./service-mesh/vpc-lattice/05-spiffe-to-iam.md) | [Cuestionario](./quizzes/service-mesh/vpc-lattice/05-spiffe-to-iam-quiz.md)
   - [Restricciones y puntos de decisión](./service-mesh/vpc-lattice/06-constraints.md) | [Cuestionario](./quizzes/service-mesh/vpc-lattice/06-constraints-quiz.md)
   - [Datapath del kernel](./service-mesh/vpc-lattice/07-kernel-datapath.md) | [Cuestionario](./quizzes/service-mesh/vpc-lattice/07-kernel-datapath-quiz.md)

### Almacenamiento
1. [Descripción general del almacenamiento](./storage/README.md)
2. [Benchmark medido de EBS gp2 frente a gp3](./storage/01-ebs-gp2-gp3-benchmark.md) | [Cuestionario](./quizzes/storage/01-ebs-gp2-gp3-benchmark-quiz.md)

### Base de datos
1. [Descripción general de las bases de datos en Kubernetes](./database/README.md)
2. [Benchmark medido de ClickHouse en EKS](./database/01-clickhouse-on-eks.md) | [Cuestionario](./quizzes/database/01-clickhouse-on-eks-quiz.md)

### Blockchain
1. [Descripción general de blockchain](./blockchain/README.md)
2. [Fundamentos de blockchain](./blockchain/01-fundamentals.md) | [Cuestionario](./quizzes/blockchain/01-fundamentals-quiz.md)
3. [Ejecución de nodos blockchain en EKS](./blockchain/02-nodes-on-eks.md) | [Cuestionario](./quizzes/blockchain/02-nodes-on-eks-quiz.md)
4. [Amazon Managed Blockchain](./blockchain/03-managed-blockchain.md) | [Cuestionario](./quizzes/blockchain/03-managed-blockchain-quiz.md)
5. [Perspectiva de servicios financieros](./blockchain/04-financial-services.md) | [Cuestionario](./quizzes/blockchain/04-financial-services-quiz.md)

### Pipeline de datos
1. [Descripción general de datos en EKS](./data-on-eks/README.md)
   - [Anatomía de un pipeline de datos moderno](./data-on-eks/01-data-pipeline-anatomy.md) | [Cuestionario](./quizzes/data-on-eks/01-data-pipeline-anatomy-quiz.md)
   - [Gobernanza de SageMaker Unified Studio](./data-on-eks/sagemaker-unified-studio/README.md)
   - [Parte 4: Gobernanza de dominios, proyectos y membresías](./data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | [Cuestionario](./quizzes/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance-quiz.md)
2. **Análisis en profundidad de Kafka en EKS**
   - [Introducción a Kafka en EKS](./data-on-eks/kafka/README.md)
   - [Parte 1: Fundamentos de Kafka](./data-on-eks/kafka/01-kafka-fundamentals.md) | [Cuestionario](./quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)
   - [Parte 2: Operador Strimzi](./data-on-eks/kafka/02-strimzi-operator.md) | [Cuestionario](./quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
   - [Parte 3: Operaciones de Kafka](./data-on-eks/kafka/03-kafka-operations.md) | [Cuestionario](./quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
   - [Parte 4: Schema Registry](./data-on-eks/kafka/04-schema-registry.md) | [Cuestionario](./quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
   - [Parte 5: Kafka Connect y MirrorMaker](./data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [Cuestionario](./quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
   - [Parte 6: Integración de MSK](./data-on-eks/kafka/06-msk-integration.md) | [Cuestionario](./quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
   - [Parte 7: Monitorización](./data-on-eks/kafka/07-monitoring.md) | [Cuestionario](./quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
   - [Parte 8: Mejores prácticas](./data-on-eks/kafka/08-best-practices.md) | [Cuestionario](./quizzes/data-on-eks/kafka/08-best-practices-quiz.md)
   - [Parte 9: Benchmark medido de Kafka](./data-on-eks/kafka/09-kafka-benchmark.md) | [Cuestionario](./quizzes/data-on-eks/kafka/09-kafka-benchmark-quiz.md)
3. **Análisis en profundidad de Spark en EKS**
   - [Introducción a Spark en EKS](./data-on-eks/spark/README.md)
   - [Parte 1: Fundamentos de Spark en Kubernetes](./data-on-eks/spark/01-spark-fundamentals.md) | [Cuestionario](./quizzes/data-on-eks/spark/01-spark-fundamentals-quiz.md)
   - [Parte 2: Operador Spark](./data-on-eks/spark/02-spark-operator.md) | [Cuestionario](./quizzes/data-on-eks/spark/02-spark-operator-quiz.md)
   - [Parte 3: Amazon EMR en EKS](./data-on-eks/spark/03-emr-on-eks.md) | [Cuestionario](./quizzes/data-on-eks/spark/03-emr-on-eks-quiz.md)
   - [Parte 4: Ajuste de rendimiento y costes](./data-on-eks/spark/04-performance-tuning.md) | [Cuestionario](./quizzes/data-on-eks/spark/04-performance-tuning-quiz.md)
   - [Parte 5: Mejores prácticas y seguridad](./data-on-eks/spark/05-best-practices.md) | [Cuestionario](./quizzes/data-on-eks/spark/05-best-practices-quiz.md)
4. **Análisis en profundidad de Airflow en EKS**
   - [Introducción a Airflow en EKS](./data-on-eks/airflow/README.md)
   - [Parte 1: Arquitectura de Airflow en Kubernetes](./data-on-eks/airflow/01-architecture.md) | [Cuestionario](./quizzes/data-on-eks/airflow/01-architecture-quiz.md)
   - [Parte 2: Despliegue de Helm y elección de executor](./data-on-eks/airflow/02-helm-deployment.md) | [Cuestionario](./quizzes/data-on-eks/airflow/02-helm-deployment-quiz.md)
   - [Parte 3: Patrones de DAG y KubernetesPodOperator](./data-on-eks/airflow/03-dag-patterns.md) | [Cuestionario](./quizzes/data-on-eks/airflow/03-dag-patterns-quiz.md)
   - [Parte 4: Integración de Amazon MWAA](./data-on-eks/airflow/04-mwaa-integration.md) | [Cuestionario](./quizzes/data-on-eks/airflow/04-mwaa-integration-quiz.md)
   - [Parte 5: Operaciones y seguridad](./data-on-eks/airflow/05-operations.md) | [Cuestionario](./quizzes/data-on-eks/airflow/05-operations-quiz.md)
5. **Análisis en profundidad de Flink en EKS**
   - [Introducción a Flink en EKS](./data-on-eks/flink/README.md)
   - [Parte 1: Arquitectura de Flink en Kubernetes](./data-on-eks/flink/01-architecture.md) | [Cuestionario](./quizzes/data-on-eks/flink/01-architecture-quiz.md)
   - [Parte 2: Operador de Kubernetes para Flink](./data-on-eks/flink/02-flink-kubernetes-operator.md) | [Cuestionario](./quizzes/data-on-eks/flink/02-flink-kubernetes-operator-quiz.md)
   - [Parte 3: Estado, checkpointing y patrones de streaming](./data-on-eks/flink/03-state-checkpointing-streaming.md) | [Cuestionario](./quizzes/data-on-eks/flink/03-state-checkpointing-streaming-quiz.md)
   - [Parte 4: Operaciones, alta disponibilidad y Flink administrado](./data-on-eks/flink/04-operations-ha.md) | [Cuestionario](./quizzes/data-on-eks/flink/04-operations-ha-quiz.md)

### AI/ML
1. [Workloads de AI/ML](./ai-ml/01-ai-ml-workloads.md) | [Cuestionario](./quizzes/ai-ml/03-ai-ml-workloads-quiz.md)
2. [Infraestructura de AI](./ai-ml/06-ai-infrastructure.md) | [Cuestionario](./quizzes/ai-ml/06-ai-infrastructure-quiz.md)
3. [Entrenamiento de modelos en EKS](./ai-ml/05-model-training.md) | [Cuestionario](./quizzes/ai-ml/05-model-training-quiz.md)
4. [Frameworks de inferencia](./ai-ml/04-inference-frameworks.md) | [Cuestionario](./quizzes/ai-ml/04-inference-frameworks-quiz.md)
5. [Despliegue y optimización de vLLM](./ai-ml/02-vllm-deployment.md) | [Cuestionario](./quizzes/ai-ml/04-vllm-deployment-quiz.md)
6. [Plataforma de AI agéntica en EKS](./ai-ml/03-agentic-ai-platform.md) | [Cuestionario](./quizzes/ai-ml/08-agentic-ai-platform-quiz.md)
7. [Mejores prácticas de AI/ML](./ai-ml/07-ai-ml-best-practices.md) | [Cuestionario](./quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)
8. **Análisis en profundidad de Ray en EKS**
   - [Introducción a Ray en EKS](./ai-ml/ray/README.md)
   - [Parte 1: Arquitectura de Ray](./ai-ml/ray/01-architecture.md) | [Cuestionario](./quizzes/ai-ml/ray/01-architecture-quiz.md)
   - [Parte 2: El operador KubeRay](./ai-ml/ray/02-kuberay-operator.md) | [Cuestionario](./quizzes/ai-ml/ray/02-kuberay-operator-quiz.md)
   - [Parte 3: Ray Train y Ray Tune](./ai-ml/ray/03-ray-train-tune.md) | [Cuestionario](./quizzes/ai-ml/ray/03-ray-train-tune-quiz.md)
   - [Parte 4: Ray Serve](./ai-ml/ray/04-ray-serve.md) | [Cuestionario](./quizzes/ai-ml/ray/04-ray-serve-quiz.md)
9. **Análisis en profundidad de Kubeflow en EKS**
   - [Introducción a Kubeflow en EKS](./ai-ml/kubeflow/README.md)
   - [Parte 1: Arquitectura e instalación de Kubeflow en EKS](./ai-ml/kubeflow/01-architecture-installation.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/01-architecture-installation-quiz.md)
   - [Parte 2: Kubeflow Pipelines](./ai-ml/kubeflow/02-pipelines.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/02-pipelines-quiz.md)
   - [Parte 3: Notebooks de Kubeflow](./ai-ml/kubeflow/03-notebooks.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/03-notebooks-quiz.md)
   - [Parte 4: Katib — ajuste de hiperparámetros y AutoML](./ai-ml/kubeflow/04-katib.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/04-katib-quiz.md)
   - [Parte 5: Kubeflow Trainer y entrenamiento distribuido](./ai-ml/kubeflow/05-training-operator.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/05-training-operator-quiz.md)
   - [Parte 6: KServe — serving de modelos en Kubernetes](./ai-ml/kubeflow/06-kserve.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/06-kserve-quiz.md)
10. **Análisis en profundidad de MLflow en EKS**
   - [Introducción a MLflow en EKS](./ai-ml/mlflow/README.md)
   - [Parte 1: Tracking de MLflow](./ai-ml/mlflow/01-tracking.md) | [Cuestionario](./quizzes/ai-ml/mlflow/01-tracking-quiz.md)
   - [Parte 2: Model Registry de MLflow](./ai-ml/mlflow/02-model-registry.md) | [Cuestionario](./quizzes/ai-ml/mlflow/02-model-registry-quiz.md)
   - [Parte 3: Despliegue de MLflow en EKS](./ai-ml/mlflow/03-eks-deployment.md) | [Cuestionario](./quizzes/ai-ml/mlflow/03-eks-deployment-quiz.md)
11. **Guía de SageMaker AI Qwen PII**
   - [Introducción a la guía](./ai-ml/sagemaker-ai/README.md)
   - [Parte 1: Arquitectura de la plataforma](./ai-ml/sagemaker-ai/01-platform-architecture.md) | [Cuestionario](./quizzes/ai-ml/sagemaker-ai/01-platform-architecture-quiz.md)
   - [Parte 2: Datos PII sintéticos y tokenización](./ai-ml/sagemaker-ai/02-pii-data-tokenization.md) | [Cuestionario](./quizzes/ai-ml/sagemaker-ai/02-pii-data-tokenization-quiz.md)
   - [Parte 3: Ejecución de SageMaker AI y MLflow](./ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md) | [Cuestionario](./quizzes/ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution-quiz.md)
   - [Parte 4: Gobernanza de Unified Studio](./data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | [Cuestionario](./quizzes/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance-quiz.md)
   - [Parte 5: Resultados de validación factual](./ai-ml/sagemaker-ai/04-validation-results.md) | [Cuestionario](./quizzes/ai-ml/sagemaker-ai/04-validation-results-quiz.md)
12. [Análisis en profundidad de LLM Gateway (Inference Gateway)](./ai-ml/08-llm-gateway.md) | [Cuestionario](./quizzes/ai-ml/08-llm-gateway-quiz.md)

### Seguridad y políticas
1. [Gestión de políticas con Kyverno](./security/01-kyverno-policy-management.md) | [Cuestionario](./quizzes/security/01-kyverno-policy-management-quiz.md)
2. [Autenticación y autorización de Kubernetes](./security/02-kubernetes-auth-authz.md) | [Cuestionario](./quizzes/security/02-kubernetes-auth-authz-quiz.md)
3. [Estándares de seguridad de Pods](./security/03-pod-security-standards.md) | [Cuestionario](./quizzes/security/03-pod-security-standards-quiz.md)
4. [Políticas de red](./security/04-network-policies.md) | [Cuestionario](./quizzes/security/04-network-policies-quiz.md)
5. [Gestión de Secrets](./security/05-secrets-management.md) | [Cuestionario](./quizzes/security/05-secrets-management-quiz.md)
6. [Mejores prácticas de seguridad de EKS](./security/06-eks-security-best-practices.md) | [Cuestionario](./quizzes/security/06-eks-security-best-practices-quiz.md)
7. [Seguridad de imágenes](./security/07-image-security.md) | [Cuestionario](./quizzes/security/07-image-security-quiz.md)
8. [Seguridad en runtime](./security/08-runtime-security.md) | [Cuestionario](./quizzes/security/08-runtime-security-quiz.md)
9. [OPA Gatekeeper](./security/09-opa-gatekeeper.md) | [Cuestionario](./quizzes/security/09-opa-gatekeeper-quiz.md)
10. [cert-manager](./security/10-cert-manager.md) | [Cuestionario](./quizzes/security/10-cert-manager-quiz.md)
11. [Kubescape](./security/11-kubescape.md) | [Cuestionario](./quizzes/security/11-kubescape-quiz.md)
12. [SPIFFE/SPIRE](./security/12-spiffe-spire.md) | [Cuestionario](./quizzes/security/12-spiffe-spire-quiz.md)

### GitOps
1. [Descripción general de GitOps](./gitops/README.md)
2. **ArgoCD**
   - [Introducción a ArgoCD](./gitops/argocd/README.md) | [Cuestionario](./quizzes/gitops/01-argocd-quiz.md)
   - [Instalación](./gitops/argocd/01-installation.md) | [Cuestionario](./quizzes/gitops/argocd/01-installation-quiz.md)
   - [Aplicaciones](./gitops/argocd/02-applications.md) | [Cuestionario](./quizzes/gitops/argocd/02-applications-quiz.md)
   - [Estrategias de sincronización](./gitops/argocd/03-sync-strategies.md) | [Cuestionario](./quizzes/gitops/argocd/03-sync-strategies-quiz.md)
   - [ApplicationSets](./gitops/argocd/04-applicationsets.md) | [Cuestionario](./quizzes/gitops/argocd/04-applicationsets-quiz.md)
   - [Gestión de tráfico](./gitops/argocd/05-traffic-management.md) | [Cuestionario](./quizzes/gitops/argocd/05-traffic-management-quiz.md)
   - [Proyectos y RBAC](./gitops/argocd/06-projects-rbac.md) | [Cuestionario](./quizzes/gitops/argocd/06-projects-rbac-quiz.md)
   - [Seguridad](./gitops/argocd/07-security.md) | [Cuestionario](./quizzes/gitops/argocd/07-security-quiz.md)
   - [Notificaciones](./gitops/argocd/08-notifications.md) | [Cuestionario](./quizzes/gitops/argocd/08-notifications-quiz.md)
   - [Mejores prácticas](./gitops/argocd/09-best-practices.md) | [Cuestionario](./quizzes/gitops/argocd/09-best-practices-quiz.md)
   - [Análisis en profundidad de experimentos de Rollouts](./gitops/argocd/10-rollouts-experiment.md) | [Cuestionario](./quizzes/gitops/argocd/10-rollouts-experiment-quiz.md)
3. [FluxCD](./gitops/02-fluxcd.md) | [Cuestionario](./quizzes/gitops/02-fluxcd-quiz.md)
4. [Comparación de herramientas GitOps](./gitops/03-gitops-comparison.md) | [Cuestionario](./quizzes/gitops/03-gitops-comparison-quiz.md)
5. [Entrega progresiva con Flagger](./gitops/04-flagger.md) | [Cuestionario](./quizzes/gitops/04-flagger-quiz.md)
6. [Feature flags y OpenFeature](./gitops/05-feature-flags.md) | [Cuestionario](./quizzes/gitops/05-feature-flags-quiz.md)

### Gobernanza cloud empresarial
1. [Descripción general de gobernanza](./governance/00-governance-overview.md) | [Cuestionario](./quizzes/governance/00-governance-overview-quiz.md)
2. [Landing Zone, OU y control organizativo](./governance/01-landing-zone-and-ou.md) | [Cuestionario](./quizzes/governance/01-landing-zone-and-ou-quiz.md)
3. [Estructura de cuentas y límites de IAM](./governance/02-account-and-iam.md) | [Cuestionario](./quizzes/governance/02-account-and-iam-quiz.md)
4. [Arquitectura EKS multi-cuenta y multi-clúster](./governance/03-eks-multi-account-multi-cluster.md) | [Cuestionario](./quizzes/governance/03-eks-multi-account-multi-cluster-quiz.md)
5. [VPC compartida y conectividad](./governance/04-shared-vpc-and-connectivity.md) | [Cuestionario](./quizzes/governance/04-shared-vpc-and-connectivity-quiz.md)
6. [Límites de datos y seguridad](./governance/05-data-security-boundaries.md) | [Cuestionario](./quizzes/governance/05-data-security-boundaries-quiz.md)
7. [Framework de decisión y diseño de PoC](./governance/06-decision-framework-and-poc.md) | [Cuestionario](./quizzes/governance/06-decision-framework-and-poc-quiz.md)

### Platform Engineering
0. [Descripción general de Platform Engineering](./platform-engineering/00-platform-engineering-overview.md) | [Cuestionario](./quizzes/platform-engineering/00-platform-engineering-overview-quiz.md)
1. [Helm](./platform-engineering/01-helm.md) | [Cuestionario](./quizzes/platform-engineering/01-helm-quiz.md)
2. [AWS Controllers for Kubernetes (ACK)](./platform-engineering/02-ack.md) | [Cuestionario](./quizzes/platform-engineering/02-ack-quiz.md)
3. [Kubernetes Resource Operator (KRO)](./platform-engineering/03-kro.md) | [Cuestionario](./quizzes/platform-engineering/03-kro-quiz.md)
4. [Mecanismos de extensión de Kubernetes](./platform-engineering/04-kubernetes-extensions.md) | [Cuestionario](./quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
5. [ExampleCorp: ejemplo de integración de ACK + KRO](./platform-engineering/05-example-corp-app.md)
6. [Backstage IDP](./platform-engineering/06-backstage-idp.md) | [Cuestionario](./quizzes/platform-engineering/06-backstage-idp-quiz.md)
7. [Crossplane](./platform-engineering/07-crossplane.md) | [Cuestionario](./quizzes/platform-engineering/07-crossplane-quiz.md)
8. [vCluster](./platform-engineering/08-vcluster.md) | [Cuestionario](./quizzes/platform-engineering/08-vcluster-quiz.md)

### Registro de contenedores
1. [Descripción general del registro de contenedores](./container-registry/README.md)
2. [Docker Hub](./container-registry/01-docker-hub.md) | [Cuestionario](./quizzes/container-registry/01-docker-hub-quiz.md)
3. [Amazon ECR](./container-registry/02-amazon-ecr.md) | [Cuestionario](./quizzes/container-registry/02-amazon-ecr-quiz.md)
4. [Harbor](./container-registry/03-harbor.md) | [Cuestionario](./quizzes/container-registry/03-harbor-quiz.md)
5. [Mejores prácticas para el registro de contenedores](./container-registry/04-best-practices.md) | [Cuestionario](./quizzes/container-registry/04-best-practices-quiz.md)

### Observabilidad
1. [Descripción general de observabilidad](./observability/README.md)
2. **Métricas**
   - [Descripción general de métricas](./observability/metrics/README.md) | [Cuestionario](./quizzes/observability/metrics/00-metrics-overview-quiz.md)
   - [Prometheus](./observability/metrics/01-prometheus.md) | [Cuestionario](./quizzes/observability/metrics/01-prometheus-quiz.md)
   - [VictoriaMetrics](./observability/metrics/02-victoriametrics.md) | [Cuestionario](./quizzes/observability/metrics/02-victoriametrics-quiz.md)
   - [Grafana Mimir](./observability/metrics/03-mimir.md) | [Cuestionario](./quizzes/observability/metrics/03-mimir-quiz.md)
   - [CloudWatch Metrics](./observability/metrics/04-cloudwatch-metrics.md) | [Cuestionario](./quizzes/observability/metrics/04-cloudwatch-metrics-quiz.md)
   - [Datadog](./observability/metrics/05-datadog.md) | [Cuestionario](./quizzes/observability/metrics/05-datadog-quiz.md)
3. **Logging**
   - [Descripción general de logging](./observability/logging/README.md) | [Cuestionario](./quizzes/observability/logging/README-quiz.md)
   - [Grafana Loki](./observability/logging/01-loki.md) | [Cuestionario](./quizzes/observability/logging/01-loki-quiz.md)
   - [OpenSearch](./observability/logging/02-opensearch.md) | [Cuestionario](./quizzes/observability/logging/02-opensearch-quiz.md)
   - [CloudWatch Logs](./observability/logging/03-cloudwatch-logs.md) | [Cuestionario](./quizzes/observability/logging/03-cloudwatch-logs-quiz.md)
   - [ClickHouse](./observability/logging/04-clickhouse.md) | [Cuestionario](./quizzes/observability/logging/04-clickhouse-quiz.md)
   - [Recolectores de logs](./observability/logging/05-collectors.md) | [Cuestionario](./quizzes/observability/logging/05-collectors-quiz.md)
4. **Tracing**
   - [Descripción general de tracing](./observability/tracing/README.md)
   - [Grafana Tempo](./observability/tracing/01-tempo.md) | [Cuestionario](./quizzes/observability/tracing/01-tempo-quiz.md)
   - [AWS X-Ray](./observability/tracing/02-xray.md) | [Cuestionario](./quizzes/observability/tracing/02-xray-quiz.md)
   - [OpenTelemetry](./observability/tracing/03-opentelemetry.md) | [Cuestionario](./quizzes/observability/tracing/03-opentelemetry-quiz.md)
   - [Dynatrace](./observability/tracing/04-dynatrace.md) | [Cuestionario](./quizzes/observability/tracing/04-dynatrace-quiz.md)
5. **Alertas**
   - [Descripción general de alertas](./observability/alerting/README.md)
   - [Alertmanager](./observability/alerting/01-alertmanager.md) | [Cuestionario](./quizzes/observability/alerting/01-alertmanager-quiz.md)
   - [Alarmas de CloudWatch](./observability/alerting/02-cloudwatch-alarms.md) | [Cuestionario](./quizzes/observability/alerting/02-cloudwatch-alarms-quiz.md)
   - [Grafana OnCall](./observability/alerting/03-grafana-oncall.md) | [Cuestionario](./quizzes/observability/alerting/03-grafana-oncall-quiz.md)
6. [Grafana](./observability/grafana/README.md) | [Cuestionario](./quizzes/observability/grafana/grafana-quiz.md)
7. [Guía de optimización de observabilidad](./observability/09-observability-optimization.md) | [Cuestionario](./quizzes/observability/09-observability-optimization-quiz.md)

### Guía de operaciones
1. [Configuración de infraestructura](./ops/01-infrastructure-setup.md) | [Cuestionario](./quizzes/ops/01-infrastructure-setup-quiz.md)
2. [Infraestructura avanzada](./ops/02-infrastructure-advanced.md) | [Cuestionario](./quizzes/ops/02-infrastructure-advanced-quiz.md)
3. [Pipelines de CI](./ops/03-ci-pipelines.md) | [Cuestionario](./quizzes/ops/03-ci-pipelines-quiz.md)
4. [GitOps multiclúster](./ops/04-gitops-multi-cluster.md) | [Cuestionario](./quizzes/ops/04-gitops-multi-cluster-quiz.md)
5. [Automatización de GitOps](./ops/05-gitops-automation.md) | [Cuestionario](./quizzes/ops/05-gitops-automation-quiz.md)
6. [Estrategias de escalado](./ops/06-scaling-strategies.md) | [Cuestionario](./quizzes/ops/06-scaling-strategies-quiz.md)
7. [Alertas de observabilidad](./ops/07-observability-alerts.md) | [Cuestionario](./quizzes/ops/07-observability-alerts-quiz.md)
8. [Análisis de observabilidad](./ops/08-observability-analysis.md) | [Cuestionario](./quizzes/ops/08-observability-analysis-quiz.md)
9. [Stack de observabilidad](./ops/09-observability-stack.md) | [Cuestionario](./quizzes/ops/09-observability-stack-quiz.md)
10. [Optimización de recursos](./ops/10-resource-optimization.md) | [Cuestionario](./quizzes/ops/10-resource-optimization-quiz.md)
11. [Operaciones de actualización](./ops/11-upgrade-operations.md) | [Cuestionario](./quizzes/ops/11-upgrade-operations-quiz.md)
12. [Playbook de planificación de capacidad para eventos](./ops/12-event-capacity-planning.md) | [Cuestionario](./quizzes/ops/12-event-capacity-planning-quiz.md)
13. [Plataforma de visibilidad de costes FinOps](./ops/13-finops-cost-platform.md) | [Cuestionario](./quizzes/ops/13-finops-cost-platform-quiz.md)
14. [Pipelines de Tekton](./ops/14-tekton-pipelines.md) | [Cuestionario](./quizzes/ops/14-tekton-pipelines-quiz.md)
15. [Operaciones de clúster zonal](./ops/15-zonal-operations-guide.md) | [Cuestionario](./quizzes/ops/15-zonal-operations-guide-quiz.md)
16. [Playbook de troubleshooting](./ops/16-troubleshooting-playbook.md) | [Cuestionario](./quizzes/ops/16-troubleshooting-playbook-quiz.md)
17. [Experimentos de producción con EKS Spot y evaluación de resultados](./ops/17-spot-production-experiments.md) | [Cuestionario](./quizzes/ops/17-spot-production-experiments-quiz.md)

## Guías de laboratorio

Proporcionamos guías de laboratorios prácticos para practicar en entornos reales después de aprender la teoría.

- [Lista de guías de laboratorio](./labs/README.md)
- Fundamentos: laboratorios de fundamentos de Linux, operaciones de Linux y contenedores
- Conceptos básicos: laboratorios de Pod, Service, Storage y ConfigMap
- EKS: laboratorio de creación de clústeres

### Laboratorios end-to-end de observabilidad
1. [Introducción a la serie de laboratorios](./labs/observability/README.md)
2. [Parte 1: Configuración de infraestructura](./labs/observability/01-infrastructure-setup-lab.md) | [Cuestionario](./quizzes/observability/labs/01-infrastructure-setup-quiz.md)
3. [Parte 2: Stack de observabilidad](./labs/observability/02-observability-stack-lab.md) | [Cuestionario](./quizzes/observability/labs/02-observability-stack-quiz.md)
4. [Parte 3: Despliegue de MSA y Canary](./labs/observability/03-msa-deployment-lab.md) | [Cuestionario](./quizzes/observability/labs/03-msa-deployment-quiz.md)
5. [Parte 4: Pruebas de carga y autoscaling](./labs/observability/04-load-testing-scaling-lab.md) | [Cuestionario](./quizzes/observability/labs/04-load-testing-scaling-quiz.md)
6. [Parte 5: Alertas y AIOps](./labs/observability/05-alerting-aiops-lab.md) | [Cuestionario](./quizzes/observability/labs/05-alerting-aiops-quiz.md)
7. [Parte 6: Análisis de tracing distribuido](./labs/observability/06-distributed-tracing-lab.md) | [Cuestionario](./quizzes/observability/labs/06-distributed-tracing-quiz.md)

## Guía de aprendizaje

### Ruta de aprendizaje para principiantes
1. Estudia en este orden: **Linux y contenedores** -> **Conceptos básicos de Kubernetes** -> **Amazon EKS**
2. Después de leer cada capítulo, realiza el cuestionario correspondiente para comprobar tu comprensión
3. Ejecuta comandos y código de ejemplo de forma práctica en un entorno de práctica

### Ruta de aprendizaje para usuarios avanzados
1. Estudia en este orden: **Amazon EKS** -> **AI/ML** -> **Service Mesh** -> **Seguridad y políticas**
2. Profundiza en redes con la sección de **Cilium**
3. Céntrate en herramientas o tecnologías específicas para un aprendizaje en profundidad

### Cómo usar los cuestionarios
- Haz clic en el enlace del cuestionario al final de cada documento para comprobar tu aprendizaje
- Piensa primero en las respuestas de estilo desplegable antes de revelarlas
- Revisa el documento correspondiente para cualquier pregunta que hayas respondido incorrectamente

## Contribuir

Si quieres contribuir a este proyecto:
1. Envía un issue cuando encuentres erratas o errores de contenido
2. Sugiere temas nuevos o mejoras
3. Sugiere adiciones o mejoras para las preguntas de los cuestionarios

## Licencia

Este material de formación es de uso gratuito con fines de aprendizaje.
