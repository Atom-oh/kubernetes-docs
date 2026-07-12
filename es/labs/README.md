# Guía de laboratorios

> **Última actualización**: February 22, 2026

Esta sección proporciona guías de laboratorio prácticas para practicar Kubernetes y tecnologías relacionadas. Cada laboratorio incluye instrucciones paso a paso y métodos de verificación, lo que te permite confirmar en un entorno real lo que aprendiste en la teoría.

## Lista de laboratorios

| # | Laboratorio | Dificultad | Requisitos previos |
|---|-----|------------|---------------|
| 1 | [Laboratorio de conceptos básicos de Linux](basics/01-linux-basics-lab.md) | Principiante | Acceso a terminal Linux |
| 2 | [Laboratorio de habilidades avanzadas de Linux](basics/02-linux-advanced-lab.md) | Principiante | Conceptos básicos de Linux completados |
| 3 | [Laboratorio de tecnología de contenedores](basics/03-container-technology-lab.md) | Principiante | Docker instalado |
| 4 | [Laboratorio de Pods y Workloads](core/02-pods-and-workloads-lab.md) | Principiante | kubectl, cluster K8s |
| 5 | [Laboratorio de Services y Networking](core/03-services-networking-lab.md) | Intermedio | kubectl, cluster K8s |
| 6 | [Laboratorio de Storage](core/04-storage-lab.md) | Intermedio | kubectl, cluster K8s |
| 7 | [Laboratorio de ConfigMap y Secret](core/05-configuration-secrets-lab.md) | Principiante | kubectl, cluster K8s |
| 8 | [Laboratorio de creación de cluster EKS](eks/01-eks-cluster-creation-lab.md) | Intermedio | AWS CLI, eksctl |
| 9 | [Observability E2E: Introducción a la serie](observability/README.md) | Avanzado | Cuenta de AWS, Terraform, Helm |
| 10 | [Observability E2E: Configuración de infraestructura](observability/01-infrastructure-setup-lab.md) | Intermedio | Parte 0 completada |
| 11 | [Observability E2E: Stack de observability](observability/02-observability-stack-lab.md) | Avanzado | Parte 1 completada |
| 12 | [Observability E2E: Despliegue de MSA y Canary](observability/03-msa-deployment-lab.md) | Avanzado | Parte 2 completada |
| 13 | [Observability E2E: Pruebas de carga y autoscaling](observability/04-load-testing-scaling-lab.md) | Intermedio | Parte 3 completada |
| 14 | [Observability E2E: Alerting y AIOps](observability/05-alerting-aiops-lab.md) | Avanzado | Parte 4 completada |
| 15 | [Observability E2E: Análisis de Distributed Tracing](observability/06-distributed-tracing-lab.md) | Avanzado | Parte 5 completada |

## Ruta de aprendizaje recomendada

1. **Laboratorios básicos** (1→2→3): Aprende Linux y tecnología de contenedores
2. **Laboratorios core** (4→7→5→6): Trabaja con recursos core de Kubernetes
3. **Laboratorios de EKS** (8): Opera clusters en un entorno real de cloud
4. **Laboratorios de Observability** (9→10→11→12→13→14→15): Construye y opera un stack de observability de extremo a extremo

## Configuración del entorno de laboratorio

### Entorno local (para laboratorios básicos/de contenedores)
- Terminal Linux (WSL2, Terminal de macOS o Linux)
- Docker Desktop o Docker Engine

### Entorno Kubernetes (para laboratorios core)
```bash
# Install and start minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
minikube start

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl
```

### Entorno AWS (para laboratorios de EKS)
- Cuenta de AWS y AWS CLI configurada
- eksctl instalado

## Consejos para los laboratorios

- Revisa primero los **Requisitos previos** de cada laboratorio
- Después de ejecutar comandos, compara con la **salida esperada** para verificar el funcionamiento correcto
- Usa **pistas** cuando te quedes atascado
- Después de completar el laboratorio, ejecuta siempre los comandos de la sección **Cleanup** para eliminar recursos
