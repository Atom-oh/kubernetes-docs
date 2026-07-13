# Cuestionario sobre Services y redes

Este cuestionario evalúa tu comprensión de los conceptos de redes de Kubernetes, incluidos los tipos de Service, Ingress, las políticas de red y el descubrimiento de servicios.

## Preguntas de opción múltiple

1. ¿Cuál es el tipo de Service predeterminado en Kubernetes?
   - A) NodePort
   - B) LoadBalancer
   - C) ClusterIP
   - D) ExternalName
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) ClusterIP**

**Explicación:**
ClusterIP es el tipo de Service predeterminado en Kubernetes, y proporciona una dirección IP que solo es accesible dentro del cluster. Este Service permite que otras aplicaciones dentro del cluster accedan al Service, pero no se puede acceder a él desde fuera del cluster.
</details>

2. ¿Qué objeto de API expone rutas HTTP y HTTPS desde fuera del cluster hacia Services dentro del cluster?
   - A) Service
   - B) Ingress
   - C) Endpoint
   - D) NetworkPolicy
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Ingress**

**Explicación:**
Ingress es un objeto de API que expone rutas HTTP y HTTPS desde fuera del cluster hacia Services dentro del cluster. Ingress proporciona balanceo de carga, terminación SSL y hosting virtual basado en nombres.
</details>

3. ¿Cuál de los siguientes NO es un método proporcionado por Kubernetes para el descubrimiento de servicios?
   - A) Variables de entorno
   - B) DNS
   - C) Service Mesh
   - D) ConfigMap
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) ConfigMap**

**Explicación:**
Kubernetes proporciona dos métodos principales de descubrimiento de servicios: variables de entorno y DNS. ConfigMap se usa para almacenar datos de configuración y no es un mecanismo de descubrimiento de servicios.
</details>

4. ¿Qué tipo de Service en Kubernetes hace que los Services sean accesibles a través de un puerto específico en todos los nodos?
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalName
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) NodePort**

**Explicación:**
Los Services NodePort hacen que los Services sean accesibles a través de un puerto específico en todos los nodos. Este tipo de Service permite acceder al Service mediante la dirección IP de cada nodo y el valor NodePort (asignado de forma predeterminada en el rango 30000-32767).
</details>

5. ¿Qué tipo de Service no tiene IP de cluster y crea registros DNS para cada pod?
   - A) NodePort service
   - B) LoadBalancer service
   - C) Headless service
   - D) ExternalName service
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Headless service**

**Explicación:**
Un headless service es un Service configurado con `clusterIP: None`, que no asigna una IP de cluster y crea registros DNS para cada pod. Esto es útil cuando los clientes necesitan acceder directamente a pods específicos detrás del Service.
</details>

6. ¿Qué recurso proporciona una forma de controlar la comunicación entre pods en Kubernetes?
   - A) Service
   - B) Ingress
   - C) NetworkPolicy
   - D) EndpointSlice
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) NetworkPolicy**

**Explicación:**
NetworkPolicy proporciona una forma de controlar la comunicación entre pods. Usando políticas de red, puedes restringir el tráfico ingress y egress entre pods.
</details>

7. ¿Qué se usa como servidor DNS para los clusters de Kubernetes?
   - A) kube-dns
   - B) CoreDNS
   - C) NodeDNS
   - D) ClusterDNS
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) CoreDNS**

**Explicación:**
CoreDNS es un servidor DNS flexible y extensible que se usa como servidor DNS para los clusters de Kubernetes. Desde Kubernetes 1.11, CoreDNS se ha usado como servidor DNS predeterminado.
</details>

8. ¿Qué tecnología del kernel de Linux utiliza Cilium?
   - A) iptables
   - B) netfilter
   - C) eBPF
   - D) nftables
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) eBPF**

**Explicación:**
Cilium utiliza la tecnología eBPF (extended Berkeley Packet Filter) del kernel de Linux para proporcionar conectividad de red, seguridad y observabilidad para aplicaciones en contenedores.
</details>

9. ¿Cuál de las siguientes NO es una función principal de un service mesh?
   - A) Service discovery
   - B) Load balancing
   - C) Providing persistent storage
   - D) Encrypted communication
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Providing persistent storage**

**Explicación:**
Un service mesh es una capa de infraestructura que gestiona la comunicación entre microservices, y proporciona funciones como descubrimiento de servicios, balanceo de carga, cifrado, autenticación, autorización y observabilidad. Proporcionar almacenamiento persistente no es una función principal de un service mesh.
</details>

10. ¿Qué tipo de Service en Kubernetes proporciona un alias para un servicio externo?
    - A) ClusterIP
    - B) NodePort
    - C) LoadBalancer
    - D) ExternalName
    
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) ExternalName**

**Explicación:**
Los Services ExternalName proporcionan un alias para un servicio externo. Este tipo de Service asigna un nombre DNS al nombre DNS de un servicio externo.
</details>

## Preguntas de respuesta corta

1. ¿Cuál es el nombre del recurso en Kubernetes que almacena las direcciones IP y los puertos de los pods apuntados por un Service?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Endpoints**

**Explicación:**
Endpoints es un recurso que almacena las direcciones IP y los puertos de los pods apuntados por un Service. Cuando hay pods que coinciden con el selector del Service, Kubernetes crea y gestiona automáticamente objetos endpoint.
</details>

2. ¿Cuál es el nombre del ingress controller usado para aprovisionar Application Load Balancers en AWS EKS?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: AWS ALB Ingress Controller**

**Explicación:**
AWS ALB Ingress Controller es un ingress controller usado para aprovisionar Application Load Balancers en AWS EKS. Este controller convierte recursos Ingress de Kubernetes en ALB de AWS.
</details>

3. ¿Cuál es el nombre de la política DNS de pod en Kubernetes que hereda la configuración DNS del nodo donde se ejecuta el pod?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Default**

**Explicación:**
La política DNS `Default` hereda la configuración DNS del nodo donde se ejecuta el pod. Esto significa usar el archivo `/etc/resolv.conf` del nodo tal cual para el pod.
</details>

4. ¿Cuál es el nombre de la capa de observabilidad de Cilium que usa eBPF para monitorizar flujos de red y solucionar problemas?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Hubble**

**Explicación:**
Hubble es la capa de observabilidad de Cilium que usa eBPF para monitorizar flujos de red y solucionar problemas. Hubble proporciona funciones como monitorización de flujos de red, mapeo de dependencias de servicios, observación de seguridad, análisis de rendimiento y solución de problemas.
</details>

5. ¿Cuál es el nombre del recurso en Kubernetes que es una alternativa escalable a Endpoints y proporciona mejor rendimiento en clusters grandes?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: EndpointSlice**

**Explicación:**
EndpointSlice es una alternativa escalable a Endpoints y proporciona mejor rendimiento en clusters grandes. EndpointSlice mejora el rendimiento para Services grandes al dividir los endpoints en múltiples slices para su gestión.
</details>

## Preguntas avanzadas

1. Explica cómo se usa un service mesh (por ejemplo, Istio) para gestionar la comunicación entre microservices en Kubernetes y sus beneficios.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

Un service mesh es una capa de infraestructura que gestiona la comunicación entre microservices, implementada de las siguientes maneras:

1. **Patrón sidecar**: Los contenedores proxy (por ejemplo, Envoy) se inyectan en cada pod para interceptar y controlar todo el tráfico de red.

2. **Control plane**: Un componente de gestión centralizado (por ejemplo, istiod de Istio) configura y gestiona todos los proxies sidecar.

3. **Gestión de tráfico**:
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
    - reviews
  http:
    - match:
      - headers:
          end-user:
            exact: jason
      route:
        - destination:
            host: reviews
            subset: v2
    - route:
      - destination:
          host: reviews
          subset: v1
```

4. **Políticas de seguridad**:
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: httpbin
  namespace: foo
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
    - from:
      - source:
          principals: ["cluster.local/ns/default/sa/sleep"]
      to:
        - operation:
            methods: ["GET"]
            paths: ["/info*"]
```

**Beneficios**:

1. **Gestión de tráfico**: Soporta routing avanzado, balanceo de carga, división de tráfico, despliegues canary y más.

2. **Seguridad**: Proporciona cifrado mutual TLS (mTLS), autenticación y autorización entre servicios.

3. **Observabilidad**: Monitoriza la comunicación entre servicios mediante tracing distribuido, recopilación de métricas y logging.

4. **Resiliencia**: Mejora la resiliencia del sistema mediante circuit breakers, reintentos, timeouts e inyección de fallos.

5. **Aplicación de políticas**: Puede aplicar políticas como limitación de tasa, cuotas y control de acceso.

6. **Independencia de la plataforma**: Estas funciones pueden añadirse sin cambiar el código de la aplicación.

Los service meshes abstraen la complejidad de la comunicación entre servicios en arquitecturas complejas de microservices, permitiendo que los desarrolladores se centren en la lógica de negocio.
</details>

2. Explica los beneficios que proporciona la tecnología eBPF de Cilium en comparación con los enfoques de redes tradicionales (por ejemplo, iptables), y sugiere formas de optimizar Cilium en AWS EKS.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Beneficios de la tecnología eBPF de Cilium**:

1. **Rendimiento**: eBPF se ejecuta directamente dentro del kernel para optimizar las rutas de procesamiento de paquetes, proporcionando un rendimiento mucho mayor que iptables. En particular, mientras iptables realiza búsquedas lineales cuando hay muchas reglas, eBPF puede usar estructuras de datos eficientes como tablas hash.

2. **Escalabilidad**: eBPF mantiene un rendimiento consistente incluso en clusters grandes. El rendimiento de iptables se degrada rápidamente a medida que aumenta el número de reglas.

3. **Programabilidad**: eBPF se puede programar en un lenguaje similar a C, lo que permite implementar lógica de redes compleja. iptables solo soporta un conjunto limitado de reglas.

4. **Observabilidad**: eBPF puede recopilar métricas detalladas sobre flujos de red, útiles para la solución de problemas y la optimización del rendimiento.

5. **Conciencia de L7**: eBPF puede reconocer hasta la capa de aplicación (L7), lo que permite políticas detalladas para protocolos como HTTP, gRPC y Kafka.

**Formas de optimizar Cilium en AWS EKS**:

1. **Habilitar el modo AWS ENI**:
```bash
helm install cilium cilium/cilium \
   --namespace kube-system \
   --set eni.enabled=true \
   --set ipam.mode=eni \
   --set egressMasqueradeInterfaces=eth0 \
   --set tunnel=disabled
```
Esta configuración aprovecha AWS Elastic Network Interfaces (ENI) para asignar direcciones IP nativas de VPC a los pods y proporciona redes nativas de VPC sin redes overlay.

2. **Optimización del grupo de nodos**:
  - Elegir tipos de instancia que proporcionen suficientes ENI y direcciones IP (por ejemplo, m5.large o superior)
  - Configurar un recuento máximo de pods adecuado (varía según el tipo de instancia)

3. **Optimización del rendimiento**:
```bash
helm install cilium cilium/cilium \
   --namespace kube-system \
   --set eni.enabled=true \
   --set ipam.mode=eni \
   --set tunnel=disabled \
   --set bpf.masquerade=true \
   --set kubeProxyReplacement=strict \
   --set loadBalancer.mode=dsr \
   --set loadBalancer.acceleration=native
```
Esta configuración reemplaza kube-proxy y habilita el modo Direct Server Return (DSR) y la aceleración nativa de balanceo de carga.

4. **Habilitar Hubble**:
```bash
helm upgrade cilium cilium/cilium \
   --namespace kube-system \
   --reuse-values \
   --set hubble.enabled=true \
   --set hubble.relay.enabled=true \
   --set hubble.ui.enabled=true
```
Habilita Hubble para proporcionar monitorización de flujos de red y capacidades de solución de problemas.

5. **Conectividad entre clusters**:
Configurar Cilium Cluster Mesh para proporcionar redes fluidas entre múltiples clusters EKS.

6. **Integración de monitorización**:
Configurar Prometheus y Grafana para recopilar y visualizar métricas de Cilium.

Estas optimizaciones pueden maximizar el rendimiento, la seguridad y la observabilidad de Cilium en AWS EKS.
</details>

## Conclusión

A través de este cuestionario, evaluaste tu comprensión de los Services y las redes de Kubernetes. Los conceptos cubiertos incluyen tipos de Service, Ingress, políticas de red, descubrimiento de servicios, CoreDNS y Cilium. Comprender y utilizar estos conceptos te permite crear aplicaciones de Kubernetes seguras y escalables.
