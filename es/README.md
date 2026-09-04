> [Versión coreana](https://atomoh.gitbook.io/kubernetes-docs/)

# Contenido de formación sobre Kubernetes y Amazon EKS
[![GitBook](https://img.shields.io/static/v1?message=Documented%20on%20GitBook&logo=gitbook&logoColor=ffffff&label=%20&labelColor=5c5c5c&color=3F89A1)](https://www.gitbook.com/preview?utm_source=gitbook_readme_badge&utm_medium=organic&utm_campaign=preview_documentation&utm_content=link)

Este repositorio proporciona materiales de formación completos sobre Kubernetes y Amazon EKS. Cubre todo, desde los fundamentos de Linux hasta la containerization (contenedorización), la orquestación con Kubernetes y las características avanzadas de Amazon EKS.

## Materiales de aprendizaje y cuestionarios

Este contenido de formación proporciona cuestionarios para cada tema junto con los materiales de aprendizaje. Puedes evaluar y reforzar lo que has aprendido mediante los cuestionarios. Cada cuestionario está diseñado con respuestas desplegables ocultas, lo que te permite intentar responder las preguntas antes de revelar las respuestas.

- [Tabla de contenido de los materiales de aprendizaje](#table-of-contents) - Materiales de aprendizaje por tema
- [Colección de cuestionarios](./quizzes/README.md) - Cuestionarios por tema

## Tabla de contenido

### Noticias
- [Noticias semanales](./news/README.md) - Resúmenes de las últimas noticias del ecosistema Kubernetes/EKS

### Conceptos básicos
1. [Fundamentos de Linux](./basics/01-linux-basics.md) | [Cuestionario](./quizzes/basics/01-linux-basics-quiz.md) | [Laboratorio](./labs/basics/01-linux-basics-lab.md)
2. [Habilidades operativas de Linux](./basics/02-linux-advanced.md) | [Cuestionario](./quizzes/basics/02-linux-advanced-quiz.md) | [Laboratorio](./labs/basics/02-linux-advanced-lab.md)
3. [Tecnología de containers](./basics/03-container-technology.md) | [Cuestionario](./quizzes/basics/03-container-technology-quiz.md) | [Laboratorio](./labs/basics/03-container-technology-lab.md)
4. [Introducción a Kubernetes](./basics/04-kubernetes-introduction.md) | [Cuestionario](./quizzes/basics/04-kubernetes-introduction-quiz.md)
5. [Fundamentos de eBPF y aplicaciones prácticas](./basics/05-ebpf-fundamentals.md) | [Cuestionario](./quizzes/basics/05-ebpf-fundamentals-quiz.md)

### Conceptos principales de Kubernetes
1. [Arquitectura de Cluster](./core/01-cluster-architecture.md) | [Cuestionario](./quizzes/core/01-cluster-architecture-quiz.md)
2. [Pods y Workloads](./core/02-pods-and-workloads.md) | [Cuestionario](./quizzes/core/02-pods-and-workloads-quiz.md)
3. [Services y Networking](./core/03-services-networking.md) | [Cuestionario](./quizzes/core/03-services-networking-quiz.md)
4. [Storage](./core/04-storage.md) | [Cuestionario](./quizzes/core/04-storage-quiz.md)
5. [Configuration](./core/05-configuration-secrets.md) | [Cuestionario](./quizzes/core/05-configuration-secrets-quiz.md)
6. [Security](./core/06-security.md) | [Cuestionario](./quizzes/core/06-security-quiz.md)
7. [Policies](./core/07-policies.md) | [Cuestionario](./quizzes/core/07-policies-quiz.md)
8. [Scheduling, Preemption y Eviction](./core/08-scheduling-preemption-eviction.md) | [Cuestionario](./quizzes/core/08-scheduling-preemption-eviction-quiz.md)
9. [Administración de Cluster](./core/09-cluster-administration.md) | [Cuestionario](./quizzes/core/09-cluster-administration-quiz.md)
10. [Windows en Kubernetes](./core/10-windows-in-kubernetes.md) | [Cuestionario](./quizzes/core/10-windows-in-kubernetes-quiz.md)
11. [Extensión de Kubernetes](./core/11-extending-kubernetes.md) | [Cuestionario](./quizzes/core/11-extending-kubernetes-quiz.md)

### Scheduling
1. Custom Scheduler
   - [Parte 1: Fundamentos de Custom Scheduler](./scheduling/01-custom-scheduler-part1.md) | [Cuestionario](./quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
   - [Parte 2: Extensiones de Scheduler y Framework](./scheduling/02-custom-scheduler-part2.md) | [Cuestionario](./quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
   - [Parte 3: Ejemplos de implementación y Monitoring de Custom Scheduler](./scheduling/03-custom-scheduler-part3.md) | [Cuestionario](./quizzes/scheduling/02-custom-scheduler-part3-quiz.md)

### Autoscaling
1. [KEDA](./autoscaling/01-keda.md) | [Cuestionario](./quizzes/autoscaling/05-keda-quiz.md)
2. [Karpenter](./autoscaling/02-karpenter.md) | [Cuestionario](./quizzes/autoscaling/06-karpenter-quiz.md)
3. [Knative](./autoscaling/03-knative.md) | [Cuestionario](./quizzes/autoscaling/03-knative-quiz.md)

### Amazon EKS
1. [Introducción a EKS](./eks/01-eks-introduction.md) | [Cuestionario](./quizzes/eks/01-eks-introduction-quiz.md)
2. Creación de EKS Cluster
   - [Parte 1: Requisitos previos](./eks/02-eks-cluster-creation-part1.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
   - [Parte 2: Creación de Clusters con eksctl](./eks/02-eks-cluster-creation-part2.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part2-quiz.md)
   - [Parte 3: Creación de Clusters con AWS Management Console y CLI](./eks/02-eks-cluster-creation-part3.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part3-quiz.md)
   - [Parte 4: Creación de Clusters con Terraform y CDK](./eks/02-eks-cluster-creation-part4.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part4-quiz.md)
   - [Parte 5: Acceso, validación, upgrade y eliminación de Cluster](./eks/02-eks-cluster-creation-part5.md) | [Cuestionario](./quizzes/eks/02-eks-cluster-creation-part5-quiz.md)
3. EKS Networking
   - [Parte 1: Conceptos básicos y configuración de VPC](./eks/03-eks-networking-part1.md) | [Cuestionario](./quizzes/eks/03-eks-networking-part1-quiz.md)
   - [Parte 2: Services y Load Balancing, Network Policies](./eks/03-eks-networking-part2.md) | [Cuestionario](./quizzes/eks/03-eks-networking-part2-quiz.md)
   - [Parte 3: Optimización del rendimiento, Troubleshooting y casos de uso avanzados](./eks/03-eks-networking-part3.md) | [Cuestionario](./quizzes/eks/03-eks-networking-part3-quiz.md)
4. EKS Storage
   - [Parte 1: Conceptos básicos, EBS, EFS](./eks/04-eks-storage-part1.md) | [Cuestionario](./quizzes/eks/04-eks-storage-part1-quiz.md)
   - [Parte 2: FSx for Lustre, S3, Snapshots, expansión de Volume, optimización del rendimiento](./eks/04-eks-storage-part2.md) | [Cuestionario](./quizzes/eks/04-eks-storage-part2-quiz.md)
   - [Parte 3: Monitoring, Troubleshooting, optimización de costos, Security](./eks/04-eks-storage-part3.md) | [Cuestionario](./quizzes/eks/04-eks-storage-part3-quiz.md)
5. [EKS Security](./eks/05-eks-security.md) | [Cuestionario](./quizzes/eks/05-eks-security-quiz.md)
6. [EKS Monitoring y Logging](./eks/06-eks-monitoring-logging.md) | [Cuestionario](./quizzes/eks/06-eks-monitoring-logging-quiz.md)
7. [Optimización de costos de EKS](./eks/07-eks-cost-optimization.md) | [Cuestionario](./quizzes/eks/07-eks-cost-optimization-quiz.md)
8. [EKS Upgrades](./eks/08-eks-upgrades.md) | [Cuestionario](./quizzes/eks/08-eks-upgrades-quiz.md)
9. [EKS Troubleshooting](./eks/09-eks-troubleshooting.md) | [Cuestionario](./quizzes/eks/09-eks-troubleshooting-quiz.md)
10. [Resiliency y High Availability de EKS](./eks/10-eks-resiliency.md) | [Cuestionario](./quizzes/eks/10-eks-resiliency-quiz.md)
11. [Debugging avanzado de EKS](./eks/11-eks-advanced-debugging.md) | [Cuestionario](./quizzes/eks/11-eks-advanced-debugging-quiz.md)
12. [Características y Roadmap de versiones de Kubernetes](./eks/12-kubernetes-version-roadmap.md) | [Cuestionario](./quizzes/eks/12-kubernetes-version-roadmap-quiz.md)

### EKS Hybrid Nodes
1. [Introducción a EKS Hybrid Nodes](./eks-hybrid-nodes/README.md)
2. [Requisitos previos](./eks-hybrid-nodes/01-prerequisites.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
3. [Configuración de Network](./eks-hybrid-nodes/02-network-configuration.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
4. [Configuración de entorno Air-Gap](./eks-hybrid-nodes/03-airgap-setup.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
5. [Node Bootstrap](./eks-hybrid-nodes/04-node-bootstrap.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
6. [Integración de GPU Server](./eks-hybrid-nodes/05-gpu-integration.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
7. [Estrategias de colocación de Workloads](./eks-hybrid-nodes/06-workload-placement.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
8. [Gestión del ciclo de vida de Node](./eks-hybrid-nodes/07-node-lifecycle.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
9. [Operaciones y mantenimiento](./eks-hybrid-nodes/08-operations.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/08-operations-quiz.md)
10. [Configuración de Bare Metal OS](./eks-hybrid-nodes/09-bare-metal-os-setup.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
11. [Hybrid Nodes Gateway](./eks-hybrid-nodes/10-hybrid-nodes-gateway.md) | [Cuestionario](./quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)

### EKS Auto Mode
1. [Introducción a EKS Auto Mode](./eks-auto-mode/README.md)
2. [Primeros pasos](./eks-auto-mode/01-getting-started.md) | [Cuestionario](./quizzes/eks-auto-mode/01-getting-started-quiz.md)
3. [Configuración de NodePool](./eks-auto-mode/02-nodepool-configuration.md) | [Cuestionario](./quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
4. [Comportamiento de Scaling](./eks-auto-mode/03-scaling-behavior.md) | [Cuestionario](./quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
5. [Estrategias de Spot Instance](./eks-auto-mode/04-spot-strategies.md) | [Cuestionario](./quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
6. [Operaciones y gestión](./eks-auto-mode/05-operations.md) | [Cuestionario](./quizzes/eks-auto-mode/05-operations-quiz.md)
7. [Gestión de costos](./eks-auto-mode/06-cost-management.md) | [Cuestionario](./quizzes/eks-auto-mode/06-cost-management-quiz.md)
8. [Ciclo de vida de Node](./eks-auto-mode/07-node-lifecycle.md) | [Cuestionario](./quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
9. [Optimización de Workload](./eks-auto-mode/08-workload-optimization.md) | [Cuestionario](./quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
10. [Guía de migración](./eks-auto-mode/09-migration-guide.md) | [Cuestionario](./quizzes/eks-auto-mode/09-migration-guide-quiz.md)

### AI/ML
1. [AI/ML Workloads](./ai-ml/01-ai-ml-workloads.md) | [Cuestionario](./quizzes/ai-ml/03-ai-ml-workloads-quiz.md)
2. [Infraestructura de AI](./ai-ml/06-ai-infrastructure.md) | [Cuestionario](./quizzes/ai-ml/06-ai-infrastructure-quiz.md)
3. [Entrenamiento de modelos en EKS](./ai-ml/05-model-training.md) | [Cuestionario](./quizzes/ai-ml/05-model-training-quiz.md)
4. [Inference Frameworks](./ai-ml/04-inference-frameworks.md) | [Cuestionario](./quizzes/ai-ml/04-inference-frameworks-quiz.md)
5. [Deployment y optimización de vLLM](./ai-ml/02-vllm-deployment.md) | [Cuestionario](./quizzes/ai-ml/04-vllm-deployment-quiz.md)
6. [Agentic AI Platform en EKS](./ai-ml/03-agentic-ai-platform.md) | [Cuestionario](./quizzes/ai-ml/08-agentic-ai-platform-quiz.md)
7. [Buenas prácticas de AI/ML](./ai-ml/07-ai-ml-best-practices.md) | [Cuestionario](./quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)
8. **Análisis profundo de Ray en EKS**
   - [Introducción a Ray en EKS](./ai-ml/ray/README.md)
   - [Parte 1: Arquitectura de Ray](./ai-ml/ray/01-architecture.md) | [Cuestionario](./quizzes/ai-ml/ray/01-architecture-quiz.md)
   - [Parte 2: El operador KubeRay](./ai-ml/ray/02-kuberay-operator.md) | [Cuestionario](./quizzes/ai-ml/ray/02-kuberay-operator-quiz.md)
   - [Parte 3: Ray Train y Ray Tune](./ai-ml/ray/03-ray-train-tune.md) | [Cuestionario](./quizzes/ai-ml/ray/03-ray-train-tune-quiz.md)
   - [Parte 4: Ray Serve](./ai-ml/ray/04-ray-serve.md) | [Cuestionario](./quizzes/ai-ml/ray/04-ray-serve-quiz.md)
9. **Análisis profundo de Kubeflow en EKS**
   - [Introducción a Kubeflow en EKS](./ai-ml/kubeflow/README.md)
   - [Parte 1: Arquitectura e instalación de Kubeflow en EKS](./ai-ml/kubeflow/01-architecture-installation.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/01-architecture-installation-quiz.md)
   - [Parte 2: Pipelines de Kubeflow](./ai-ml/kubeflow/02-pipelines.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/02-pipelines-quiz.md)
   - [Parte 3: Cuadernos de Kubeflow](./ai-ml/kubeflow/03-notebooks.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/03-notebooks-quiz.md)
   - [Parte 4: Katib — Ajuste de hiperparámetros y AutoML](./ai-ml/kubeflow/04-katib.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/04-katib-quiz.md)
   - [Parte 5: Kubeflow Trainer y entrenamiento distribuido](./ai-ml/kubeflow/05-training-operator.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/05-training-operator-quiz.md)
   - [Parte 6: KServe — Servicio de modelos en Kubernetes](./ai-ml/kubeflow/06-kserve.md) | [Cuestionario](./quizzes/ai-ml/kubeflow/06-kserve-quiz.md)
10. **Análisis profundo de MLflow en EKS**
    - [Introducción a MLflow en EKS](./ai-ml/mlflow/README.md)
    - [Parte 1: Seguimiento de MLflow](./ai-ml/mlflow/01-tracking.md) | [Cuestionario](./quizzes/ai-ml/mlflow/01-tracking-quiz.md)
    - [Parte 2: Registro de modelos de MLflow](./ai-ml/mlflow/02-model-registry.md) | [Cuestionario](./quizzes/ai-ml/mlflow/02-model-registry-quiz.md)
    - [Parte 3: Implementación de MLflow en EKS](./ai-ml/mlflow/03-eks-deployment.md) | [Cuestionario](./quizzes/ai-ml/mlflow/03-eks-deployment-quiz.md)

### Data on EKS
1. [Descripción general de Data on EKS](./data-on-eks/README.md)
2. **Análisis profundo de Kafka on EKS**
   - [Introducción a Kafka on EKS](./data-on-eks/kafka/README.md)
   - [Parte 1: Fundamentos de Kafka](./data-on-eks/kafka/01-kafka-fundamentals.md) | [Cuestionario](./quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)
   - [Parte 2: Strimzi Operator](./data-on-eks/kafka/02-strimzi-operator.md) | [Cuestionario](./quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
   - [Parte 3: Operaciones de Kafka](./data-on-eks/kafka/03-kafka-operations.md) | [Cuestionario](./quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
   - [Parte 4: Schema Registry](./data-on-eks/kafka/04-schema-registry.md) | [Cuestionario](./quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
   - [Parte 5: Kafka Connect y MirrorMaker](./data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [Cuestionario](./quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
   - [Parte 6: Integración con MSK](./data-on-eks/kafka/06-msk-integration.md) | [Cuestionario](./quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
   - [Parte 7: Monitoring](./data-on-eks/kafka/07-monitoring.md) | [Cuestionario](./quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
   - [Parte 8: Buenas prácticas](./data-on-eks/kafka/08-best-practices.md) | [Cuestionario](./quizzes/data-on-eks/kafka/08-best-practices-quiz.md)

### Networking
1. [Descripción general de Networking](./networking/README.md) | [Cuestionario](./quizzes/networking/00-networking-overview-quiz.md)
2. [VPC CNI](./networking/01-vpc-cni.md) | [Cuestionario](./quizzes/networking/01-vpc-cni-quiz.md)
3. **Análisis profundo de Cilium**
   - [Introducción a Cilium](./networking/cilium/README.md)
   - [Parte 1: Introducción](./networking/cilium/01-introduction.md) | [Cuestionario](./quizzes/networking/cilium/01-introduction-quiz.md)
   - [Parte 2: eBPF](./networking/cilium/02-ebpf.md) | [Cuestionario](./quizzes/networking/cilium/02-ebpf-quiz.md)
   - [Parte 3: Networking](./networking/cilium/03-networking.md) | [Cuestionario](./quizzes/networking/cilium/03-networking-quiz.md)
   - [Parte 4: IPAM y Policies](./networking/cilium/04-ipam-policy.md) | [Cuestionario](./quizzes/networking/cilium/04-ipam-policy-quiz.md)
   - [Parte 5: Networking L2-L7](./networking/cilium/05-l2-l7-networking.md) | [Cuestionario](./quizzes/networking/cilium/05-l2-l7-networking-quiz.md)
   - [Parte 6: Security y Visibility](./networking/cilium/06-security-visibility.md) | [Cuestionario](./quizzes/networking/cilium/06-security-visibility-quiz.md)
   - [Parte 7: Temas avanzados](./networking/cilium/07-advanced-topics.md) | [Cuestionario](./quizzes/networking/cilium/07-advanced-topics-quiz.md)
   - [Conceptos de Networking](./networking/cilium/networking-concepts.md) | [Cuestionario](./quizzes/networking/cilium/networking-concepts-quiz.md)
   - [Glosario](./networking/cilium/glossary.md) | [Cuestionario](./quizzes/networking/cilium/glossary-quiz.md)
4. **Análisis profundo de Calico**
   - [Introducción a Calico](./networking/calico/README.md)
   - [Parte 1: Introducción](./networking/calico/01-introduction.md) | [Cuestionario](./quizzes/networking/calico/01-introduction-quiz.md)
   - [Parte 2: Arquitectura](./networking/calico/02-architecture.md) | [Cuestionario](./quizzes/networking/calico/02-architecture-quiz.md)
   - [Parte 3: Modos de Networking](./networking/calico/03-networking-modes.md) | [Cuestionario](./quizzes/networking/calico/03-networking-modes-quiz.md)
   - [Parte 4: Análisis profundo de BGP](./networking/calico/04-bgp-deep-dive.md) | [Cuestionario](./quizzes/networking/calico/04-bgp-deep-dive-quiz.md)
   - [Parte 5: Network Policy](./networking/calico/05-network-policy.md) | [Cuestionario](./quizzes/networking/calico/05-network-policy-quiz.md)
   - [Parte 6: eBPF Dataplane](./networking/calico/06-ebpf-dataplane.md) | [Cuestionario](./quizzes/networking/calico/06-ebpf-dataplane-quiz.md)
   - [Parte 7: Temas avanzados](./networking/calico/07-advanced-topics.md) | [Cuestionario](./quizzes/networking/calico/07-advanced-topics-quiz.md)
   - [Parte 8: Integración con EKS](./networking/calico/08-eks-integration.md) | [Cuestionario](./quizzes/networking/calico/08-eks-integration-quiz.md)
   - [Parte 9: Operaciones](./networking/calico/09-operations.md) | [Cuestionario](./quizzes/networking/calico/09-operations-quiz.md)
   - [Glosario](./networking/calico/glossary.md) | [Cuestionario](./quizzes/networking/calico/glossary-quiz.md)
5. [VPC Lattice](./networking/02-vpc-lattice.md) | [Cuestionario](./quizzes/networking/02-vpc-lattice-quiz.md)
6. [AWS Load Balancer Controller](./networking/03-aws-lb-controller.md) | [Cuestionario](./quizzes/networking/03-aws-lb-controller-quiz.md)
7. [Gateway API](./networking/04-gateway-api.md) | [Cuestionario](./quizzes/networking/04-gateway-api-quiz.md)
8. [Conectividad de VPC entre organizaciones](./networking/05-cross-org-vpc-connectivity.md) | [Cuestionario](./quizzes/networking/05-cross-org-vpc-connectivity-quiz.md)
9. [Prueba de rendimiento de red de Pods](./networking/06-pod-network-benchmark.md) | [Cuestionario](./quizzes/networking/06-pod-network-benchmark-quiz.md)

### Service Mesh
1. [Istio](./service-mesh/istio/README.md) | [Cuestionario](./quizzes/service-mesh/02-istio-quiz.md)
2. **Linkerd**
   - [Introducción a Linkerd](./service-mesh/linkerd/README.md)
   - [Instalación](./service-mesh/linkerd/01-installation.md) | [Cuestionario](./quizzes/service-mesh/linkerd/installation.md)
   - [Arquitectura](./service-mesh/linkerd/02-architecture.md) | [Cuestionario](./quizzes/service-mesh/linkerd/architecture.md)
   - [Traffic Management](./service-mesh/linkerd/03-traffic-management.md) | [Cuestionario](./quizzes/service-mesh/linkerd/traffic-management.md)
   - [Security](./service-mesh/linkerd/04-security.md) | [Cuestionario](./quizzes/service-mesh/linkerd/security.md)
   - [Observability](./service-mesh/linkerd/05-observability.md) | [Cuestionario](./quizzes/service-mesh/linkerd/observability.md)
   - [Multi-cluster](./service-mesh/linkerd/06-multi-cluster.md) | [Cuestionario](./quizzes/service-mesh/linkerd/multi-cluster.md)
   - [Buenas prácticas](./service-mesh/linkerd/07-best-practices.md)
3. **Cilium Service Mesh**
   - [Introducción a Cilium Service Mesh](./service-mesh/cilium-service-mesh/README.md)
   - [Arquitectura](./service-mesh/cilium-service-mesh/01-architecture.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/architecture.md)
   - [Traffic Management](./service-mesh/cilium-service-mesh/02-traffic-management.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/traffic-management.md)
   - [Security](./service-mesh/cilium-service-mesh/03-security.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/security.md)
   - [Observability](./service-mesh/cilium-service-mesh/04-observability.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/observability.md)
   - [Ingress Gateway](./service-mesh/cilium-service-mesh/05-ingress-gateway.md) | [Cuestionario](./quizzes/service-mesh/cilium-service-mesh/ingress-gateway.md)
   - [Buenas prácticas](./service-mesh/cilium-service-mesh/06-best-practices.md)

### Security & Policy
1. [Gestión de Policy con Kyverno](./security/01-kyverno-policy-management.md) | [Cuestionario](./quizzes/security/01-kyverno-policy-management-quiz.md)
2. [Authentication y Authorization de Kubernetes](./security/02-kubernetes-auth-authz.md) | [Cuestionario](./quizzes/security/02-kubernetes-auth-authz-quiz.md)
3. [Pod Security Standards](./security/03-pod-security-standards.md) | [Cuestionario](./quizzes/security/03-pod-security-standards-quiz.md)
4. [Network Policies](./security/04-network-policies.md) | [Cuestionario](./quizzes/security/04-network-policies-quiz.md)
5. [Secrets Management](./security/05-secrets-management.md) | [Cuestionario](./quizzes/security/05-secrets-management-quiz.md)
6. [Buenas prácticas de EKS Security](./security/06-eks-security-best-practices.md) | [Cuestionario](./quizzes/security/06-eks-security-best-practices-quiz.md)
7. [Image Security](./security/07-image-security.md) | [Cuestionario](./quizzes/security/07-image-security-quiz.md)
8. [Runtime Security](./security/08-runtime-security.md) | [Cuestionario](./quizzes/security/08-runtime-security-quiz.md)
9. [OPA Gatekeeper](./security/09-opa-gatekeeper.md) | [Cuestionario](./quizzes/security/09-opa-gatekeeper-quiz.md)
10. [cert-manager](./security/10-cert-manager.md) | [Cuestionario](./quizzes/security/10-cert-manager-quiz.md)
11. [Kubescape](./security/11-kubescape.md) | [Cuestionario](./quizzes/security/11-kubescape-quiz.md)
12. [SPIFFE/SPIRE](./security/12-spiffe-spire.md) | [Cuestionario](./quizzes/security/12-spiffe-spire-quiz.md)

### Container Registry
1. [Descripción general de Container Registry](./container-registry/README.md)
2. [Docker Hub](./container-registry/01-docker-hub.md) | [Cuestionario](./quizzes/container-registry/01-docker-hub-quiz.md)
3. [Amazon ECR](./container-registry/02-amazon-ecr.md) | [Cuestionario](./quizzes/container-registry/02-amazon-ecr-quiz.md)
4. [Harbor](./container-registry/03-harbor.md) | [Cuestionario](./quizzes/container-registry/03-harbor-quiz.md)
5. [Buenas prácticas de Container Registry](./container-registry/04-best-practices.md) | [Cuestionario](./quizzes/container-registry/04-best-practices-quiz.md)

### Platform Engineering
0. [Descripción general de Platform Engineering](./platform-engineering/00-platform-engineering-overview.md) | [Cuestionario](./quizzes/platform-engineering/00-platform-engineering-overview-quiz.md)
1. [Helm](./platform-engineering/01-helm.md) | [Cuestionario](./quizzes/platform-engineering/01-helm-quiz.md)
2. [AWS Controllers for Kubernetes (ACK)](./platform-engineering/02-ack.md) | [Cuestionario](./quizzes/platform-engineering/02-ack-quiz.md)
3. [Kubernetes Resource Operator (KRO)](./platform-engineering/03-kro.md) | [Cuestionario](./quizzes/platform-engineering/03-kro-quiz.md)
4. [Mecanismos de extensión de Kubernetes](./platform-engineering/04-kubernetes-extensions.md) | [Cuestionario](./quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
5. [ExampleCorp: ejemplo de integración ACK + KRO](./platform-engineering/05-example-corp-app.md)
6. [Backstage IDP](./platform-engineering/06-backstage-idp.md) | [Cuestionario](./quizzes/platform-engineering/06-backstage-idp-quiz.md)
7. [Crossplane](./platform-engineering/07-crossplane.md) | [Cuestionario](./quizzes/platform-engineering/07-crossplane-quiz.md)
8. [vCluster](./platform-engineering/08-vcluster.md) | [Cuestionario](./quizzes/platform-engineering/08-vcluster-quiz.md)

### GitOps
1. [Descripción general de GitOps](./gitops/README.md)
2. **ArgoCD**
   - [Introducción a ArgoCD](./gitops/argocd/README.md) | [Cuestionario](./quizzes/gitops/01-argocd-quiz.md)
   - [Instalación](./gitops/argocd/01-installation.md) | [Cuestionario](./quizzes/gitops/argocd/01-installation-quiz.md)
   - [Applications](./gitops/argocd/02-applications.md) | [Cuestionario](./quizzes/gitops/argocd/02-applications-quiz.md)
   - [Estrategias de Sync](./gitops/argocd/03-sync-strategies.md) | [Cuestionario](./quizzes/gitops/argocd/03-sync-strategies-quiz.md)
   - [ApplicationSets](./gitops/argocd/04-applicationsets.md) | [Cuestionario](./quizzes/gitops/argocd/04-applicationsets-quiz.md)
   - [Traffic Management](./gitops/argocd/05-traffic-management.md) | [Cuestionario](./quizzes/gitops/argocd/05-traffic-management-quiz.md)
   - [Projects y RBAC](./gitops/argocd/06-projects-rbac.md) | [Cuestionario](./quizzes/gitops/argocd/06-projects-rbac-quiz.md)
   - [Security](./gitops/argocd/07-security.md) | [Cuestionario](./quizzes/gitops/argocd/07-security-quiz.md)
   - [Notifications](./gitops/argocd/08-notifications.md) | [Cuestionario](./quizzes/gitops/argocd/08-notifications-quiz.md)
   - [Buenas prácticas](./gitops/argocd/09-best-practices.md) | [Cuestionario](./quizzes/gitops/argocd/09-best-practices-quiz.md)
3. [FluxCD](./gitops/02-fluxcd.md) | [Cuestionario](./quizzes/gitops/02-fluxcd-quiz.md)
4. [Comparación de herramientas GitOps](./gitops/03-gitops-comparison.md) | [Cuestionario](./quizzes/gitops/03-gitops-comparison-quiz.md)
5. [Progressive Delivery con Flagger](./gitops/04-flagger.md) | [Cuestionario](./quizzes/gitops/04-flagger-quiz.md)
6. [Feature Flags y OpenFeature](./gitops/05-feature-flags.md) | [Cuestionario](./quizzes/gitops/05-feature-flags-quiz.md)

### Guía de operaciones
1. [Configuración de infraestructura](./ops/01-infrastructure-setup.md) | [Cuestionario](./quizzes/ops/01-infrastructure-setup-quiz.md)
2. [Infraestructura avanzada](./ops/02-infrastructure-advanced.md) | [Cuestionario](./quizzes/ops/02-infrastructure-advanced-quiz.md)
3. [CI Pipelines](./ops/03-ci-pipelines.md) | [Cuestionario](./quizzes/ops/03-ci-pipelines-quiz.md)
4. [GitOps Multi-Cluster](./ops/04-gitops-multi-cluster.md) | [Cuestionario](./quizzes/ops/04-gitops-multi-cluster-quiz.md)
5. [GitOps Automation](./ops/05-gitops-automation.md) | [Cuestionario](./quizzes/ops/05-gitops-automation-quiz.md)
6. [Estrategias de Scaling](./ops/06-scaling-strategies.md) | [Cuestionario](./quizzes/ops/06-scaling-strategies-quiz.md)
7. [Alertas de Observability](./ops/07-observability-alerts.md) | [Cuestionario](./quizzes/ops/07-observability-alerts-quiz.md)
8. [Análisis de Observability](./ops/08-observability-analysis.md) | [Cuestionario](./quizzes/ops/08-observability-analysis-quiz.md)
9. [Stack de Observability](./ops/09-observability-stack.md) | [Cuestionario](./quizzes/ops/09-observability-stack-quiz.md)
10. [Optimización de recursos](./ops/10-resource-optimization.md) | [Cuestionario](./quizzes/ops/10-resource-optimization-quiz.md)
11. [Operaciones de Upgrade](./ops/11-upgrade-operations.md) | [Cuestionario](./quizzes/ops/11-upgrade-operations-quiz.md)
12. [Playbook de planificación de capacidad para eventos](./ops/12-event-capacity-planning.md) | [Cuestionario](./quizzes/ops/12-event-capacity-planning-quiz.md)
13. [Plataforma de visibilidad de costos FinOps](./ops/13-finops-cost-platform.md) | [Cuestionario](./quizzes/ops/13-finops-cost-platform-quiz.md)
14. [Tekton Pipelines](./ops/14-tekton-pipelines.md) | [Cuestionario](./quizzes/ops/14-tekton-pipelines-quiz.md)

### Observability
1. [Descripción general de Observability](./observability/README.md)
2. **Metrics**
   - [Descripción general de Metrics](./observability/metrics/README.md) | [Cuestionario](./quizzes/observability/metrics/00-metrics-overview-quiz.md)
   - [Prometheus](./observability/metrics/01-prometheus.md) | [Cuestionario](./quizzes/observability/metrics/01-prometheus-quiz.md)
   - [VictoriaMetrics](./observability/metrics/02-victoriametrics.md) | [Cuestionario](./quizzes/observability/metrics/02-victoriametrics-quiz.md)
   - [Grafana Mimir](./observability/metrics/03-mimir.md) | [Cuestionario](./quizzes/observability/metrics/03-mimir-quiz.md)
   - [CloudWatch Metrics](./observability/metrics/04-cloudwatch-metrics.md) | [Cuestionario](./quizzes/observability/metrics/04-cloudwatch-metrics-quiz.md)
   - [Datadog](./observability/metrics/05-datadog.md) | [Cuestionario](./quizzes/observability/metrics/05-datadog-quiz.md)
3. **Logging**
   - [Descripción general de Logging](./observability/logging/README.md)
   - [Grafana Loki](./observability/logging/01-loki.md) | [Cuestionario](./quizzes/observability/logging/01-loki-quiz.md)
   - [OpenSearch](./observability/logging/02-opensearch.md) | [Cuestionario](./quizzes/observability/logging/02-opensearch-quiz.md)
   - [CloudWatch Logs](./observability/logging/03-cloudwatch-logs.md) | [Cuestionario](./quizzes/observability/logging/03-cloudwatch-logs-quiz.md)
   - [ClickHouse](./observability/logging/04-clickhouse.md) | [Cuestionario](./quizzes/observability/logging/04-clickhouse-quiz.md)
   - [Log Collectors](./observability/logging/05-collectors.md) | [Cuestionario](./quizzes/observability/logging/05-collectors-quiz.md)
4. **Tracing**
   - [Descripción general de Tracing](./observability/tracing/README.md)
   - [Grafana Tempo](./observability/tracing/01-tempo.md) | [Cuestionario](./quizzes/observability/tracing/01-tempo-quiz.md)
   - [AWS X-Ray](./observability/tracing/02-xray.md) | [Cuestionario](./quizzes/observability/tracing/02-xray-quiz.md)
   - [OpenTelemetry](./observability/tracing/03-opentelemetry.md) | [Cuestionario](./quizzes/observability/tracing/03-opentelemetry-quiz.md)
   - [Dynatrace](./observability/tracing/04-dynatrace.md) | [Cuestionario](./quizzes/observability/tracing/04-dynatrace-quiz.md)
5. **Alerting**
   - [Descripción general de Alerting](./observability/alerting/README.md)
   - [Alertmanager](./observability/alerting/01-alertmanager.md) | [Cuestionario](./quizzes/observability/alerting/01-alertmanager-quiz.md)
   - [CloudWatch Alarms](./observability/alerting/02-cloudwatch-alarms.md) | [Cuestionario](./quizzes/observability/alerting/02-cloudwatch-alarms-quiz.md)
   - [Grafana OnCall](./observability/alerting/03-grafana-oncall.md) | [Cuestionario](./quizzes/observability/alerting/03-grafana-oncall-quiz.md)
6. [Grafana](./observability/grafana/README.md) | [Cuestionario](./quizzes/observability/grafana/grafana-quiz.md)
7. [Guía de optimización de Observability](./observability/09-observability-optimization.md) | [Cuestionario](./quizzes/observability/09-observability-optimization-quiz.md)

## Guías de laboratorio

Proporcionamos guías de laboratorio prácticas para ejercitarse en entornos reales después de aprender la teoría.

- [Lista de guías de laboratorio](./labs/README.md)
- Básicos: fundamentos de Linux, operaciones de Linux, laboratorios de containers
- Core: laboratorios de Pod, Service, Storage y ConfigMap
- EKS: laboratorio de creación de Cluster

### Laboratorios de Observability de extremo a extremo
1. [Introducción a la serie de laboratorios](./labs/observability/README.md)
2. [Parte 1: Configuración de infraestructura](./labs/observability/01-infrastructure-setup-lab.md) | [Cuestionario](./quizzes/observability/labs/01-infrastructure-setup-quiz.md)
3. [Parte 2: Stack de Observability](./labs/observability/02-observability-stack-lab.md) | [Cuestionario](./quizzes/observability/labs/02-observability-stack-quiz.md)
4. [Parte 3: Deployment de MSA y Canary](./labs/observability/03-msa-deployment-lab.md) | [Cuestionario](./quizzes/observability/labs/03-msa-deployment-quiz.md)
5. [Parte 4: Load Testing y Autoscaling](./labs/observability/04-load-testing-scaling-lab.md) | [Cuestionario](./quizzes/observability/labs/04-load-testing-scaling-quiz.md)
6. [Parte 5: Alerting y AIOps](./labs/observability/05-alerting-aiops-lab.md) | [Cuestionario](./quizzes/observability/labs/05-alerting-aiops-quiz.md)
7. [Parte 6: Análisis de Distributed Tracing](./labs/observability/06-distributed-tracing-lab.md) | [Cuestionario](./quizzes/observability/labs/06-distributed-tracing-quiz.md)

## Guía de aprendizaje

### Ruta de aprendizaje para principiantes
1. Estudia en este orden: **Conceptos básicos** -> **Conceptos principales de Kubernetes** -> **Amazon EKS**
2. Después de leer cada capítulo, realiza el cuestionario correspondiente para comprobar tu comprensión
3. Ejecuta comandos y código de ejemplo de forma práctica en un entorno de práctica

### Ruta de aprendizaje para usuarios avanzados
1. Estudia en este orden: **Amazon EKS** -> **AI/ML** -> **Service Mesh** -> **Security & Policy**
2. Profundiza en Networking con la sección **Cilium**
3. Enfócate en herramientas o tecnologías específicas para un aprendizaje en profundidad

### Cómo usar los cuestionarios
- Haz clic en el enlace del cuestionario al final de cada documento para comprobar tu aprendizaje
- Piensa primero en las respuestas desplegables antes de revelarlas
- Revisa el documento correspondiente para cualquier pregunta que hayas respondido incorrectamente

## Contribuir

Si quieres contribuir a este proyecto:
1. Envía un issue cuando encuentres errores tipográficos o errores de contenido
2. Sugiere nuevos temas o mejoras
3. Sugiere adiciones o mejoras a las preguntas de los cuestionarios

## Licencia

Este material de formación es gratuito para uso con fines de aprendizaje.
