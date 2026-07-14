# Parte 1: Introducción

> **Versiones compatibles**: Cilium 1.18 **Última actualización**: February 23, 2026

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y entorno:

### Herramientas requeridas

* kubectl v1.33 o posterior
* Helm v3.12 o posterior
* Un clúster de Kubernetes funcional (EKS, minikube, kind, etc.)
* Kernel de Linux 4.19 o posterior (para compatibilidad con características de eBPF)

### Instalación de Cilium

```bash
# Install Cilium CLI
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Install Cilium
cilium install --version 1.18.0

# Check installation status
cilium status
```

## ¿Qué es Cilium?

Cilium es software de código abierto que proporciona redes, seguridad y observabilidad para aplicaciones en contenedores mediante el aprovechamiento de la potente tecnología eBPF del kernel de Linux. Está diseñado para proporcionar redes, seguridad y observabilidad para plataformas de orquestación de contenedores como Kubernetes, Docker y Mesos.

### Características principales:

* **Basado en eBPF**: Proporciona capacidades de redes y seguridad de alto rendimiento mediante un datapath programable dentro del kernel
* **Redes con reconocimiento de API**: Admite políticas de seguridad de red con reconocimiento de API en las capas L3-L7
* **Integración con Kubernetes**: Proporciona una implementación de Kubernetes CNI (Container Network Interface)
* **Balanceo de carga distribuido**: Balanceo de carga distribuido eficiente para la comunicación de servicio a servicio
* **Visibilidad de red**: Monitoreo y resolución de problemas de flujos de red mediante Hubble
* **Compatibilidad con múltiples clústeres**: Compatibilidad con redes y políticas de seguridad entre clústeres
* **Compatibilidad con Kubernetes**: Totalmente compatible con Kubernetes 1.32 y versiones posteriores
* **Compatibilidad BGP mejorada**: Configuración de enrutamiento más flexible con el plano de control BGP mejorado de Cilium 1.18
* **Observabilidad mejorada**: Información más detallada con capacidades de métricas y trazado mejoradas

### Arquitectura de Cilium

## Fundamentos de las redes de contenedores

Las redes de contenedores proporcionan los mecanismos que permiten a las aplicaciones en contenedores comunicarse entre sí y con el mundo exterior.

### Modelos de redes de contenedores:

1. **Red de host**: Los contenedores comparten el espacio de nombres de red del host
2. **Red de puente**: Los contenedores se conectan a un puente virtual dentro del host
3. **Red superpuesta**: Se crean redes virtuales entre varios hosts
4. **Red subyacente**: Utilización directa de la infraestructura de red física

### Desafíos de las redes de contenedores:

* **Escalabilidad**: Compatibilidad con miles de contenedores y servicios
* **Rendimiento**: Minimizar la latencia y maximizar el rendimiento
* **Seguridad**: Proteger la comunicación entre microservicios
* **Observabilidad**: Monitorear flujos de red y resolver problemas
* **Portabilidad**: Proporcionar una experiencia de red coherente en diversos entornos

## Comprensión de CNI (Container Network Interface)

> **Concepto clave**: CNI (Container Network Interface) es un proyecto de CNCF que define una interfaz estándar entre los entornos de ejecución de contenedores y los plugins de red.

### Componentes principales de CNI:

* **Arquitectura de plugins**: Diseño modular que permite la integración de diversas soluciones de red
* **Configuración de red**: Ajustes de red definidos en formato JSON
* **IPAM (IP Address Management)**: Asignación y administración de direcciones IP
* **API estándar**: API estándar para la configuración de red al añadir/eliminar contenedores

### Comparación de los principales plugins de CNI:

| Feature                      | Cilium                    | Calico         | Flannel        | AWS VPC CNI            |
| ---------------------------- | ------------------------- | -------------- | -------------- | ---------------------- |
| **Base Technology**          | eBPF                      | iptables/IPVS  | VXLAN/host-gw  | AWS ENI                |
| **Network Policy**           | L3-L7                     | L3-L4          | Limited        | AWS Security Groups    |
| **Encryption**               | IPsec/WireGuard           | IPsec          | None           | None                   |
| **Observability**            | Hubble                    | Flow Logs      | Limited        | VPC Flow Logs          |
| **Service Mesh**             | Built-in                  | Requires Istio | Requires Istio | Requires Istio/AppMesh |
| **Performance**              | Very High                 | High           | Medium         | High                   |
| **IPAM**                     | Cluster Pool, CRD         | IPAM Plugin    | Host Subnet    | AWS IPAM               |
| **Kubernetes Compatibility** | 1.32+                     | 1.29+          | 1.28+          | 1.29+                  |
| **BGP Support**              | Enhanced control (v1.18+) | Limited        | None           | VPC Routing            |

* **Weave Net**: Redes de contenedores multihost
* **AWS VPC CNI**: Integración directa con AWS VPC

## Características diferenciadoras de Cilium

Cilium proporciona varias ventajas únicas en comparación con otras soluciones CNI.

### Diferenciación técnica:

* **Utilización de eBPF**: Alto rendimiento y flexibilidad mediante un datapath programable dentro del kernel
* **Redes con reconocimiento de API**: Compatibilidad con políticas de red hasta la capa L7
* **XDP (eXpress Data Path)**: Optimización del rendimiento del procesamiento de paquetes
* **Reemplazo de Kube-proxy**: Balanceo de carga de servicios más eficiente
* **Integración con Hubble**: Potente herramienta de observabilidad de red
* **Compatibilidad con las versiones más recientes de Kubernetes**: Totalmente compatible con Kubernetes 1.32 y versiones posteriores

### Beneficios por caso de uso:

* **Arquitectura de microservicios**: Políticas de red detalladas y observabilidad
* **Despliegue multiclúster**: Redes fluidas entre clústeres
* **Entornos centrados en la seguridad**: Políticas de seguridad de red sólidas
* **Requisitos de alto rendimiento**: Datapath optimizado
* **Integración con Service Mesh**: Integración con Service Mesh como Istio

## Laboratorio: instalación de Cilium y configuración básica

```bash
# Install Cilium CLI on Kubernetes cluster
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Install Cilium
cilium install --version 1.18.0

# Check installation status
cilium status

# Connectivity test
cilium connectivity test
```

### Aplicación de una política de red básica:

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "allow-frontend-backend"
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
```

[Volver a la página principal](./)

## Cuestionario

Para comprobar lo que has aprendido en este capítulo, prueba el [Cuestionario del tema](../../quizzes/networking/cilium/01-introduction-quiz.md).
