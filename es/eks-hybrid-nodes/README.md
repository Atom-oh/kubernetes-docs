# EKS Hybrid Nodes

> **Versiones compatibles**: EKS 1.31+, nodeadm 0.1+ **Última actualización**: February 23, 2026

Amazon EKS Hybrid Nodes es una característica que permite administrar servidores on-premises desde el plano de control de AWS EKS. Esta guía cubre los conceptos, los métodos de configuración y el uso práctico de EKS Hybrid Nodes en entornos de producción.

## Tabla de contenidos

1. [Requisitos previos y requisitos del sistema](01-prerequisites.md)
2. [Configuración de red](02-network-configuration.md)
3. [Configuración de entorno air-gap (S3 + VPC Endpoints)](03-airgap-setup.md)
4. [Bootstrap de Node](04-node-bootstrap.md)
5. [Integración de servidores GPU](05-gpu-integration.md)
6. [Estrategias de colocación de Workloads](06-workload-placement.md)
7. [Gestión del ciclo de vida de Node](07-node-lifecycle.md)
8. [Operaciones y mantenimiento](08-operations.md)
9. [Guía de instalación y migración de OS en servidores bare metal](09-bare-metal-os-setup.md)
10. [Hybrid Nodes Gateway](10-hybrid-nodes-gateway.md)

## ¿Qué son los Hybrid Nodes?

EKS Hybrid Nodes es una característica que permite registrar servidores de tu centro de datos on-premises o entorno edge como Kubernetes nodes (nodos) administrados por el plano de control de AWS EKS. Esto te permite administrar infraestructura cloud y on-premises como un único Kubernetes cluster.

![Arquitectura de red de alto nivel de EKS Hybrid Nodes](../.gitbook/assets/hybrid-nodes-highlevel-network.png)

El siguiente diagrama muestra los requisitos previos de red, incluida la conectividad de VPC, subnets, Transit Gateway/Virtual Private Gateway y Remote Node/Pod CIDR.

![Requisitos previos de red de EKS Hybrid Nodes](../.gitbook/assets/hybrid-prereq-diagram.png)

## ¿Por qué usar Hybrid Nodes?

### 1. Cumplimiento normativo y soberanía de datos

Ciertas industrias (finanzas, salud, gobierno) tienen regulaciones que exigen que los datos permanezcan dentro de regiones o instalaciones específicas. Con Hybrid Nodes, puedes mantener los datos sensibles on-premises mientras aprovechas las capacidades de administración de EKS.

```yaml
# Example of regulatory compliance workload placement
apiVersion: v1
kind: Pod
metadata:
  name: financial-data-processor
spec:
  nodeSelector:
    topology.kubernetes.io/zone: "on-premises"
    compliance.company.io/data-sovereignty: "required"
  containers:
  - name: processor
    image: harbor.internal.company.io/finance/data-processor:v1.2.0
```

### 2. Gravedad de los datos

Cuando existen grandes conjuntos de datos on-premises, es más eficiente acercar el cómputo a los datos que mover los datos al cloud.

### 3. Aprovechamiento del hardware existente

Puedes seguir utilizando servidores de alto rendimiento en los que ya se ha invertido (especialmente servidores GPU) mientras aplicas una gestión moderna de Workloads basada en Kubernetes.

### 4. Gestión unificada

Administrar Kubernetes Workloads tanto en entornos cloud como on-premises desde un único plano de control reduce la complejidad operativa.

## Componentes de la arquitectura

La arquitectura de EKS Hybrid Nodes consta de los siguientes componentes:

| Componente                      | Ubicación    | Rol                                               |
| ------------------------------- | ----------- | ------------------------------------------------- |
| EKS Control Plane               | AWS         | API server, etcd, controller manager, scheduler   |
| nodeadm                         | On-Premises | Agente de bootstrap y gestión de Node             |
| kubelet                         | On-Premises | Ejecución de Pod e informes de estado de Node     |
| containerd                      | On-Premises | Container runtime                                 |
| VPN/Direct Connect              | Red         | Conexión segura entre AWS y on-premises           |
| SSM Agent or IAM Roles Anywhere | On-Premises | Gestión de credenciales                           |

### Restricciones y limitaciones clave

* **Conectividad de red**: Requiere conectividad confiable entre on-premises y AWS mediante VPN o Direct Connect (no es adecuado para entornos desconectados, intermitentes, limitados o denegados)
* **Límites de CIDR**: Hasta 15 CIDR para Remote Node Networks y Remote Pod Networks por cluster
* **Solo IPv4**: Debe usar la familia de direcciones IPv4 (IPv6 no es compatible con hybrid nodes)
* **Modo de autenticación**: El cluster debe usar el modo de autenticación `API` o `API_AND_CONFIG_MAP`
* **Acceso a endpoints**: Debe usar solo Public O Private ("Public and Private" **no es compatible** — causa fallos de incorporación de hybrid nodes)
* **Precios por vCPU**: Los hybrid nodes se cobran por vCPU por hora (sin compromisos mínimos)
* **Infraestructura cloud**: No es compatible con infraestructura cloud (ejecutarlo en EC2 generará cargos de hybrid node)
* **VPC CNI**: Amazon VPC CNI no es compatible con hybrid nodes; usa Cilium o Calico

### Opciones de proveedores de credenciales

EKS Hybrid Nodes admite dos proveedores de credenciales para autenticar nodes on-premises con AWS:

| Característica           | SSM Hybrid Activations                                                                 | IAM Roles Anywhere                                           |
| ------------------------ | -------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **Complejidad de configuración** | Simple — par de código/ID de activación                                         | Moderada — requiere infraestructura PKI                      |
| **Certificado requerido** | No                                                                                    | Sí (certificado X.509 por node)                              |
| **Compatible con air-gap** | No (requiere acceso al endpoint de SSM)                                               | Sí (funciona con CA local)                                   |
| **Rotación de credenciales** | Automática (administrada por AWS, TTL fijo de 1 hora)                              | Automática (basada en certificados, configurable de 1 a 12 horas) |
| **Nombres de Node**      | Generados automáticamente (`mi-xxxx`, no personalizables)                              | Personalizados (deben coincidir con el CN del certificado)   |
| **Límites de escalado**  | 1,000 gratuitos por cuenta por región; nivel advanced-instances para más (costo extra) | Sin límites                                                  |
| **Dependencia de AWS**   | Servicio SSM                                                                           | Servicio IAM Roles Anywhere                                  |
| **Ideal para**           | Entornos estándar con internet/VPN                                                     | Air-gap, cumplimiento estricto, PKI existente                |

> **Recomendación**: Usa SSM Hybrid Activations por su simplicidad en la mayoría de los entornos. Elige IAM Roles Anywhere cuando necesites compatibilidad con air-gap o ya tengas infraestructura PKI.

## Casos de uso principales

1. **AI/ML Workloads**: Entrenamiento de modelos en servidores GPU on-premises, servicios de inferencia en el cloud
2. **Servicios financieros**: Procesamiento de datos de transacciones on-premises, analítica en el cloud
3. **Manufactura**: Edge computing en fábricas integrado con el cloud central
4. **Procesamiento multimedia**: Procesamiento de archivos multimedia grandes donde residen los datos

## Próximos pasos

Comienza con los [Requisitos previos y requisitos del sistema](01-prerequisites.md) para asegurarte de que tu entorno esté listo para EKS Hybrid Nodes.

## Quiz

Para poner a prueba tu comprensión de EKS Hybrid Nodes, intenta el siguiente quiz:

* [Quiz de EKS Hybrid Nodes](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/eks-hybrid-nodes/README.md)

## Documentos relacionados

* [Guía de resiliencia de EKS](../eks/10-eks-resiliency.md) - Configuración de alta disponibilidad en entornos híbridos
* [Optimización de costos de EKS](../eks/07-eks-cost-optimization.md) - Estrategias de gestión de costos
* [Monitoreo y logging de EKS](../eks/06-eks-monitoring-logging.md) - Configuración de monitoreo integrado

## Documentación oficial

* [Documentación oficial de AWS EKS Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-overview.html)
* [Guía de usuario de nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
* [Documentación oficial de Harbor](https://goharbor.io/docs/)
* [Documentación de NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
* [Guía de networking de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [Configuración de CNI de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
* [Solución de problemas de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-troubleshooting.html)
