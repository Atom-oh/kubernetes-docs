# Parte 1: Introducción

> **Versiones compatibles**: Cilium 1.18 **Última actualización**: February 23, 2026

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitará las siguientes herramientas y el siguiente entorno:

### Herramientas necesarias

* kubectl v1.33 o posterior
* Helm v3.12 o posterior
* Un clúster de Kubernetes funcional (EKS, minikube, kind, etc.)
* Kernel de Linux 4.19 o posterior (para la compatibilidad con las características de eBPF)

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

Cilium es un software de código abierto que proporciona redes, seguridad y observabilidad para aplicaciones en contenedores mediante el aprovechamiento de la potente tecnología eBPF del kernel de Linux. Está diseñado para proporcionar redes, seguridad y observabilidad para plataformas de orquestación de contenedores como Kubernetes, Docker y Mesos.

### Características principales:

* **Basado en eBPF**: Proporciona capacidades de redes y seguridad de alto rendimiento mediante un datapath programable dentro del kernel
* **Redes con reconocimiento de API**: Admite políticas de seguridad de red con reconocimiento de API en las capas L3-L7
* **Integración con Kubernetes**: Proporciona implementación de Kubernetes CNI (Container Network Interface)
* **Balanceo de carga distribuido**: Balanceo de carga distribuido eficiente para la comunicación de servicio a servicio
* **Visibilidad de red**: Supervisión y solución de problemas de flujos de red mediante Hubble
* **Compatibilidad con múltiples clústeres**: Compatibilidad con redes entre clústeres y políticas de seguridad
* **Compatibilidad con Kubernetes**: Totalmente compatible con Kubernetes 1.32 y versiones posteriores
* **Compatibilidad mejorada con BGP**: Configuración de enrutamiento más flexible con el plano de control BGP mejorado de Cilium 1.18
* **Observabilidad mejorada**: Información más profunda con métricas y capacidades de rastreo mejoradas

### Arquitectura de Cilium

![Diagrama de las capas desde Kubernetes hasta el CNI, Cilium, eBPF y el kernel de Linux, con Cilium enviando eventos de flujo a Hubble.](../../.gitbook/assets/en-networking-cilium-01-introduction-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-01-introduction-0.html)

## Fundamentos de las redes de contenedores

Las redes de contenedores proporcionan los mecanismos que permiten que las aplicaciones en contenedores se comuniquen entre sí y con el mundo exterior.

### Modelos de redes de contenedores:

1. **Red de host**: Los contenedores comparten el espacio de nombres de red del host
2. **Red de puente**: Los contenedores se conectan a un puente virtual dentro del host
3. **Red superpuesta**: Se crean redes virtuales en varios hosts
4. **Red subyacente**: Utilización directa de la infraestructura de red física

### Desafíos de las redes de contenedores:

* **Escalabilidad**: Compatibilidad con miles de contenedores y servicios
* **Rendimiento**: Minimización de la latencia y maximización del rendimiento
* **Seguridad**: Protección de la comunicación entre microservicios
* **Observabilidad**: Supervisión de flujos de red y solución de problemas
* **Portabilidad**: Proporcionar una experiencia de red coherente en diversos entornos

## Comprensión de CNI (Container Network Interface)

> **Concepto clave**: CNI (Container Network Interface) es un proyecto de CNCF que define una interfaz estándar entre los entornos de ejecución de contenedores y los plugins de red.

### Componentes principales de CNI:

* **Arquitectura de plugins**: Diseño modular que permite la integración de diversas soluciones de red
* **Configuración de red**: Ajustes de red definidos en formato JSON
* **IPAM (IP Address Management)**: Asignación y gestión de direcciones IP
* **API estándar**: API estándar para la configuración de red al añadir o eliminar contenedores

### Comparación de los principales plugins de CNI:

| Característica               | Cilium                    | Calico         | Flannel        | AWS VPC CNI            |
| ---------------------------- | ------------------------- | -------------- | -------------- | ---------------------- |
| **Tecnología base**          | eBPF                      | iptables/IPVS  | VXLAN/host-gw  | AWS ENI                |
| **Política de red**          | L3-L7                     | L3-L4          | Limitada       | AWS Security Groups    |
| **Cifrado**                  | IPsec/WireGuard           | IPsec          | Ninguno        | Ninguno                |
| **Observabilidad**           | Hubble                    | Flow Logs      | Limitada       | VPC Flow Logs          |
| **Service Mesh**             | Integrado                 | Requiere Istio | Requiere Istio | Requiere Istio/AppMesh |
| **Rendimiento**              | Muy alto                  | Alto           | Medio          | Alto                   |
| **IPAM**                     | Cluster Pool, CRD         | Plugin de IPAM | Subred de host | AWS IPAM               |
| **Compatibilidad con Kubernetes** | 1.32+                     | 1.29+          | 1.28+          | 1.29+                  |
| **Compatibilidad con BGP**   | Control mejorado (v1.18+) | Limitada       | Ninguna        | Enrutamiento de VPC    |

* **Weave Net**: Redes de contenedores para múltiples hosts
* **AWS VPC CNI**: Integración directa con AWS VPC

## Características diferenciadoras de Cilium

Cilium proporciona varias ventajas únicas en comparación con otras soluciones de CNI.

### Diferenciación técnica:

* **Utilización de eBPF**: Alto rendimiento y flexibilidad mediante un datapath programable dentro del kernel
* **Redes con reconocimiento de API**: Compatibilidad con políticas de red hasta la capa L7
* **XDP (eXpress Data Path)**: Optimización del rendimiento del procesamiento de paquetes
* **Reemplazo de Kube-proxy**: Balanceo de carga de servicios más eficiente
* **Integración con Hubble**: Potente herramienta de observabilidad de red
* **Compatibilidad con las versiones más recientes de Kubernetes**: Totalmente compatible con Kubernetes 1.32 y versiones posteriores

### Beneficios por caso de uso:

* **Arquitectura de microservicios**: Políticas de red y observabilidad detalladas
* **Implementación en múltiples clústeres**: Redes fluidas entre clústeres
* **Entornos centrados en la seguridad**: Políticas de seguridad de red sólidas
* **Requisitos de alto rendimiento**: Datapath optimizado
* **Integración con Service Mesh**: Integración con Service Mesh como Istio

## Laboratorio: Instalación de Cilium y configuración básica

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

### Aplicación de la política de red básica:

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

[Volver a la página principal](./README.md)

## Cuestionario

Para poner a prueba lo que ha aprendido en este capítulo, pruebe el [cuestionario del tema](../../quizzes/networking/cilium/01-introduction-quiz.md).
