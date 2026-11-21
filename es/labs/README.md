# Guía de laboratorio


> **Última actualización**: 21 de noviembre de 2026

Esta sección ofrece guías prácticas de laboratorio para aprender Kubernetes y tecnologías relacionadas. Cada laboratorio incluye instrucciones paso a paso y métodos de verificación que te permiten comprobar en un entorno real lo que aprendiste en teoría.

## Lista de laboratorios

| # | Laboratorio | Dificultad | Requisitos previos |
|---|-----|------------|---------------|
| 1 | [Laboratorio de conceptos básicos de Linux](basics/01-linux-basics-lab.md) | Principiante | Acceso a una terminal de Linux |
| 2 | [Laboratorio de habilidades avanzadas de Linux](basics/02-linux-advanced-lab.md) | Principiante | Haber completado los conceptos básicos de Linux |
| 3 | [Laboratorio de tecnologías de contenedores](basics/03-container-technology-lab.md) | Principiante | Docker instalado |
| 4 | [Laboratorio de Pods y cargas de trabajo](core/02-pods-and-workloads-lab.md) | Principiante | kubectl, clúster de K8s |
| 5 | [Laboratorio de Services y redes](core/03-services-networking-lab.md) | Intermedio | kubectl, clúster de K8s |
| 6 | [Laboratorio de almacenamiento](core/04-storage-lab.md) | Intermedio | kubectl, clúster de K8s |
| 7 | [Laboratorio de ConfigMap y Secret](core/05-configuration-secrets-lab.md) | Principiante | kubectl, clúster de K8s |
| 8 | [Laboratorio de creación de clústeres de EKS](eks/01-eks-cluster-creation-lab.md) | Intermedio | AWS CLI, eksctl |
| 9 | [Observabilidad E2E: introducción a la serie](observability/README.md) | Avanzado | Entorno de AWS aprobado, Helm, Python |
| 10 | [Observabilidad E2E: configuración de la infraestructura](observability/01-infrastructure-setup-lab.md) | Intermedio | Introducción a la serie y redes listas |
| 11 | [Observabilidad E2E: pila de observabilidad](observability/02-observability-stack-lab.md) | Avanzado | Parte 1 completada |
| 12 | [Observabilidad E2E: despliegue de MSA y canarios](observability/03-msa-deployment-lab.md) | Avanzado | Parte 2 completada |
| 13 | [Observabilidad E2E: pruebas de carga y escalado automático](observability/04-load-testing-scaling-lab.md) | Intermedio | Parte 3 completada |
| 14 | [Observabilidad E2E: alertas y AIOps](observability/05-alerting-aiops-lab.md) | Avanzado | Parte 4 completada |
| 15 | [Observabilidad E2E: análisis de trazas distribuidas](observability/06-distributed-tracing-lab.md) | Avanzado | Parte 5 completada |
| 16 | [Laboratorio de migración de IAM de cargas de trabajo de EKS](security/17-eks-workload-identity-migration-lab.md) | Avanzado | Clúster de EKS existente, AWS CLI, kubectl, jq |

## Ruta de aprendizaje recomendada

1. **Laboratorios básicos** (1→2→3): Aprende Linux y tecnologías de contenedores
2. **Laboratorios básicos de Kubernetes** (4→7→5→6): Trabaja con los recursos principales de Kubernetes
3. **Laboratorios de EKS** (8): Opera clústeres en un entorno de nube real
4. **Laboratorios de observabilidad** (9→10→11→12→13→14→15): Crea y opera una pila de observabilidad integral
5. **Laboratorios de seguridad** (16): Migra el IAM de las cargas de trabajo de EKS del rol del nodo a IRSA y Pod Identity

## Configuración del entorno de laboratorio

### Entorno local (para laboratorios básicos y de contenedores)
- Terminal de Linux (WSL2, Terminal de macOS o Linux)
- Docker Desktop o Docker Engine

### Entorno de Kubernetes (para laboratorios básicos de Kubernetes)
Instala las herramientas correspondientes a tu sistema operativo y arquitectura de CPU, y sigue los requisitos de clúster y versión de cada laboratorio. No instales sin modificar en macOS o ARM un binario de Linux AMD64.

```bash
kubectl version --client
kubectl config current-context
```

### Entorno de AWS (para laboratorios de EKS)
- Cuenta de AWS y AWS CLI configurada
- eksctl instalado

## Consejos para los laboratorios

- Consulta primero los **Requisitos previos** de cada laboratorio
- Después de ejecutar los comandos, compáralos con la **Salida esperada** para verificar que todo funcione correctamente
- Usa las **pistas** si te atascas
- Cuando completes el laboratorio, ejecuta siempre los comandos de la sección **Limpieza** para eliminar los recursos
