# Guía de laboratorios


> **Última actualización**: September 13, 2026

Esta sección ofrece guías prácticas de laboratorio para practicar Kubernetes y tecnologías relacionadas. Cada laboratorio incluye instrucciones paso a paso y métodos de verificación, lo que le permite confirmar en un entorno real lo que aprendió en la teoría.

## Lista de laboratorios

| # | Laboratorio | Dificultad | Prerrequisitos |
|---|-----|------------|---------------|
| 1 | [Laboratorio de fundamentos de Linux](basics/01-linux-basics-lab.md) | Principiante | Acceso a una terminal de Linux |
| 2 | [Laboratorio de habilidades avanzadas de Linux](basics/02-linux-advanced-lab.md) | Principiante | Fundamentos de Linux completados |
| 3 | [Laboratorio de tecnología de contenedores](basics/03-container-technology-lab.md) | Principiante | Docker instalado |
| 4 | [Laboratorio de Pods y cargas de trabajo](core/02-pods-and-workloads-lab.md) | Principiante | kubectl, clúster de K8s |
| 5 | [Laboratorio de Services y redes](core/03-services-networking-lab.md) | Intermedio | kubectl, clúster de K8s |
| 6 | [Laboratorio de almacenamiento](core/04-storage-lab.md) | Intermedio | kubectl, clúster de K8s |
| 7 | [Laboratorio de ConfigMap y Secret](core/05-configuration-secrets-lab.md) | Principiante | kubectl, clúster de K8s |
| 8 | [Laboratorio de creación de clústeres de EKS](eks/01-eks-cluster-creation-lab.md) | Intermedio | AWS CLI, eksctl |
| 9 | [Observabilidad E2E: introducción a la serie](observability/README.md) | Avanzado | Entorno de AWS aprobado, Helm, Python |
| 10 | [Observabilidad E2E: configuración de la infraestructura](observability/01-infrastructure-setup-lab.md) | Intermedio | Introducción a la serie y redes listas |
| 11 | [Observabilidad E2E: stack de observabilidad](observability/02-observability-stack-lab.md) | Avanzado | Parte 1 completada |
| 12 | [Observabilidad E2E: despliegue de MSA y canary](observability/03-msa-deployment-lab.md) | Avanzado | Parte 2 completada |
| 13 | [Observabilidad E2E: pruebas de carga y autoescalado](observability/04-load-testing-scaling-lab.md) | Intermedio | Parte 3 completada |
| 14 | [Observabilidad E2E: alertas y AIOps](observability/05-alerting-aiops-lab.md) | Avanzado | Parte 4 completada |
| 15 | [Observabilidad E2E: análisis de trazado distribuido](observability/06-distributed-tracing-lab.md) | Avanzado | Parte 5 completada |

## Ruta de aprendizaje recomendada

1. **Laboratorios básicos** (1→2→3): aprenda Linux y tecnología de contenedores
2. **Laboratorios principales** (4→7→5→6): trabaje con los recursos principales de Kubernetes
3. **Laboratorios de EKS** (8): opere clústeres en un entorno de nube real
4. **Laboratorios de observabilidad** (9→10→11→12→13→14→15): construya y opere un stack de observabilidad de extremo a extremo

## Preparación del entorno de laboratorio

### Entorno local (para los laboratorios básicos y de contenedores)
- Terminal de Linux (WSL2, Terminal de macOS o Linux)
- Docker Desktop o Docker Engine

### Entorno de Kubernetes (para los laboratorios principales)
Instale las herramientas correspondientes a su sistema operativo y arquitectura de CPU, y siga los requisitos de clúster y versión de cada laboratorio. No instale un binario de Linux AMD64 sin modificar en macOS o ARM.

```bash
kubectl version --client
kubectl config current-context
```

### Entorno de AWS (para los laboratorios de EKS)
- Cuenta de AWS y AWS CLI configurada
- eksctl instalado

## Consejos para los laboratorios

- Revise primero los **Prerrequisitos** de cada laboratorio
- Después de ejecutar los comandos, compare con la **Salida esperada** para verificar que el funcionamiento sea correcto
- Use las **pistas** cuando se quede atascado
- Al terminar el laboratorio, ejecute siempre los comandos de la sección **Limpieza** para eliminar los recursos
