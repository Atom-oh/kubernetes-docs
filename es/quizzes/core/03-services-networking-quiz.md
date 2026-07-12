# Cuestionario sobre Services y Networking

Este cuestionario evalúa tu comprensión de los conceptos de networking de Kubernetes, incluidos los tipos de Service, Ingress, NetworkPolicy y service discovery.

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
ClusterIP es el tipo de Service predeterminado en Kubernetes, y proporciona una dirección IP a la que solo se puede acceder dentro del cluster. Este Service permite que otras aplicaciones dentro del cluster accedan al Service, pero no se puede acceder a él desde fuera del cluster.
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

3. ¿Cuál de los siguientes NO es un método proporcionado por Kubernetes para service discovery?
   - A) Variables de entorno
   - B) DNS
   - C) Service Mesh
   - D) ConfigMap
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) ConfigMap**

**Explicación:**
Kubernetes proporciona dos métodos principales de service discovery: variables de entorno y DNS. ConfigMap se utiliza para almacenar datos de configuración y no es un mecanismo de service discovery.
</details>

4. ¿Qué tipo de Service en Kubernetes hace que los Services sean accesibles a través de un puerto específico en todos los nodes?
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalName
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) NodePort**

**Explicación:**
Los Services NodePort hacen que los Services sean accesibles a través de un puerto específico en todos los nodes. Este tipo de Service permite acceder al Service mediante la dirección IP de cada node y el valor de NodePort (asignado de forma predeterminada en el rango 30000-32767).
</details>

5. ¿Qué tipo de Service no tiene IP de cluster y crea registros DNS para cada Pod?
   - A) Service NodePort
   - B) Service LoadBalancer
   - C) Headless Service
   - D) Service ExternalName
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Headless Service**

**Explicación:**
Un Headless Service es un Service configurado con `clusterIP: None`, que no asigna una IP de cluster y crea registros DNS para cada Pod. Esto es útil cuando los clientes necesitan acceder directamente a Pods específicos detrás del Service.
</details>

6. ¿Qué recurso proporciona una forma de controlar la comunicación entre Pods en Kubernetes?
   - A) Service
   - B) Ingress
   - C) NetworkPolicy
   - D) EndpointSlice
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) NetworkPolicy**

**Explicación:**
NetworkPolicy proporciona una forma de controlar la comunicación entre Pods. Con NetworkPolicy, puedes restringir el tráfico de ingress y egress entre Pods.
</details>

7. ¿Qué se utiliza como servidor DNS para los clusters de Kubernetes?
   - A) kube-dns
   - B) CoreDNS
   - C) NodeDNS
   - D) ClusterDNS
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) CoreDNS**

**Explicación:**
CoreDNS es un servidor DNS flexible y extensible que se utiliza como servidor DNS para los clusters de Kubernetes. Desde Kubernetes 1.11, CoreDNS se utiliza como servidor DNS predeterminado.
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
Cilium utiliza la tecnología eBPF (extended Berkeley Packet Filter) del kernel de Linux para proporcionar conectividad de red, seguridad y observabilidad para aplicaciones en containers.
</details>

9. ¿Cuál de las siguientes NO es una función principal de un service mesh?
   - A) Service discovery
   - B) Load balancing
   - C) Proporcionar almacenamiento persistente
   - D) Comunicación cifrada
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Proporcionar almacenamiento persistente**

**Explicación:**
Un service mesh es una capa de infraestructura que gestiona la comunicación entre microservices y proporciona funciones como service discovery, load balancing, cifrado, autenticación, autorización y observabilidad. Proporcionar almacenamiento persistente no es una función principal de un service mesh.
</details>

10. ¿Qué tipo de Service en Kubernetes proporciona un alias para un Service externo?
    - A) ClusterIP
    - B) NodePort
    - C) LoadBalancer
    - D) ExternalName
    
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) ExternalName**

**Explicación:**
Los Services ExternalName proporcionan un alias para un Service externo. Este tipo de Service asigna un nombre DNS al nombre DNS de un Service externo.
</details>

## Preguntas de respuesta corta

1. ¿Cuál es el nombre del recurso en Kubernetes que almacena las direcciones IP y los puertos de los Pods apuntados por un Service?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Endpoints**

**Explicación:**
Endpoints es un recurso que almacena las direcciones IP y los puertos de los Pods apuntados por un Service. Cuando hay Pods que coinciden con el selector del Service, Kubernetes crea y administra automáticamente objetos Endpoints.
</details>

2. ¿Cuál es el nombre del Ingress Controller utilizado para aprovisionar Application Load Balancers en AWS EKS?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: AWS ALB Ingress Controller**

**Explicación:**
AWS ALB Ingress Controller es un Ingress Controller utilizado para aprovisionar Application Load Balancers en AWS EKS. Este controller convierte recursos Ingress de Kubernetes en AWS ALB.
</details>

3. ¿Cuál es el nombre de la política DNS de Pod en Kubernetes que hereda la configuración DNS del node donde se ejecuta el Pod?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Default**

**Explicación:**
La política DNS `Default` hereda la configuración DNS del node donde se ejecuta el Pod. Esto significa usar el archivo `/etc/resolv.conf` del node tal cual para el Pod.
</details>

4. ¿Cuál es el nombre de la capa de observabilidad de Cilium que utiliza eBPF para monitorear flujos de red y solucionar problemas?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Hubble**

**Explicación:**
Hubble es la capa de observabilidad de Cilium que utiliza eBPF para monitorear flujos de red y solucionar problemas. Hubble proporciona funciones como monitoreo de flujos de red, mapeo de dependencias de Service, observación de seguridad, análisis de rendimiento y troubleshooting.
</details>

5. ¿Cuál es el nombre del recurso en Kubernetes que es una alternativa escalable a Endpoints y proporciona mejor rendimiento en clusters grandes?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: EndpointSlice**

**Explicación:**
EndpointSlice es una alternativa escalable a Endpoints y proporciona mejor rendimiento en clusters grandes. EndpointSlice mejora el rendimiento de Services grandes al dividir Endpoints en varios slices para su administración.
</details>

## Preguntas avanzadas

1. Explica cómo se utiliza un service mesh (p. ej., Istio) para gestionar la comunicación entre microservices en Kubernetes y sus beneficios.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

Un service mesh es una capa de infraestructura que gestiona la comunicación entre microservices, implementada de las siguientes maneras:

1. **Patrón sidecar**: Se inyectan containers proxy (p. ej., Envoy) en cada Pod para interceptar y controlar todo el tráfico de red.

2. **Control plane**: Un componente de administración centralizado (p. ej., istiod de Istio) configura y administra todos los proxies sidecar.

3. **Gestión del tráfico**:
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

1. **Gestión del tráfico**: Admite enrutamiento avanzado, load balancing, división de tráfico, deployments canary y más.

2. **Seguridad**: Proporciona cifrado TLS mutuo (mTLS), autenticación y autorización entre Services.

3. **Observabilidad**: Monitorea la comunicación entre Services mediante tracing distribuido, recopilación de métricas y logging.

4. **Resiliencia**: Mejora la resiliencia del sistema mediante circuit breakers, reintentos, timeouts e inyección de fallos.

5. **Aplicación de políticas**: Puede aplicar políticas como rate limiting, cuotas y control de acceso.

6. **Independencia de plataforma**: Estas funciones se pueden agregar sin cambiar el código de la aplicación.

Los service mesh abstraen la complejidad de la comunicación entre Services en arquitecturas complejas de microservices, lo que permite a los desarrolladores centrarse en la lógica de negocio.
</details>

2. Explica los beneficios que proporciona la tecnología eBPF de Cilium en comparación con enfoques de networking tradicionales (p. ej., iptables), y sugiere formas de optimizar Cilium en AWS EKS.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Beneficios de la tecnología eBPF de Cilium**:

1. **Rendimiento**: eBPF se ejecuta directamente dentro del kernel para optimizar las rutas de procesamiento de paquetes, lo que proporciona un rendimiento mucho mayor que iptables. En particular, mientras iptables realiza búsquedas lineales cuando hay muchas reglas, eBPF puede usar estructuras de datos eficientes como tablas hash.

2. **Escalabilidad**: eBPF mantiene un rendimiento constante incluso en clusters grandes. El rendimiento de iptables se degrada rápidamente a medida que aumenta el número de reglas.

3. **Programabilidad**: eBPF se puede programar en un lenguaje similar a C, lo que permite implementar lógica de networking compleja. iptables solo admite un conjunto limitado de reglas.

4. **Observabilidad**: eBPF puede recopilar métricas detalladas sobre flujos de red, útiles para troubleshooting y optimización del rendimiento.

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
Esta configuración aprovecha AWS Elastic Network Interfaces (ENI) para asignar direcciones IP nativas de VPC a Pods y proporciona networking nativo de VPC sin redes overlay.

2. **Optimización de node group**:
  - Elige tipos de instancia que proporcionen suficientes ENI y direcciones IP (p. ej., m5.large o superiores)
  - Configura un conteo máximo de Pods adecuado (varía según el tipo de instancia)

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
Esta configuración reemplaza kube-proxy y habilita el modo Direct Server Return (DSR) y la aceleración nativa del load balancing.

4. **Habilitar Hubble**:
```bash
helm upgrade cilium cilium/cilium \
   --namespace kube-system \
   --reuse-values \
   --set hubble.enabled=true \
   --set hubble.relay.enabled=true \
   --set hubble.ui.enabled=true
```
Habilita Hubble para proporcionar monitoreo de flujos de red y capacidades de troubleshooting.

5. **Conectividad entre clusters**:
Configura Cilium Cluster Mesh para proporcionar networking fluido entre varios clusters EKS.

6. **Integración de monitoreo**:
Configura Prometheus y Grafana para recopilar y visualizar métricas de Cilium.

Estas optimizaciones pueden maximizar el rendimiento, la seguridad y la observabilidad de Cilium en AWS EKS.
</details>

## Conclusión

A través de este cuestionario, comprobaste tu comprensión de los Services y el networking de Kubernetes. Los conceptos cubiertos incluyen tipos de Service, Ingress, NetworkPolicy, service discovery, CoreDNS y Cilium. Comprender y utilizar estos conceptos te permite crear aplicaciones Kubernetes seguras y escalables.
