# Cuestionario de Services y redes

Este cuestionario evalúa tus conocimientos sobre los conceptos de redes de Kubernetes, incluidos los tipos de Service, Ingress, las políticas de red y el descubrimiento de servicios.

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
ClusterIP es el tipo de Service predeterminado en Kubernetes y proporciona una dirección IP accesible solo dentro del clúster. Así, otras aplicaciones del clúster pueden acceder al Service, pero no se puede acceder a él desde fuera del clúster.
</details>

2. ¿Qué objeto de la API expone rutas HTTP y HTTPS desde fuera del clúster hacia Services dentro del clúster?
   - A) Service
   - B) Ingress
   - C) Endpoint
   - D) NetworkPolicy
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Ingress**

**Explicación:**
Ingress es un objeto de la API que expone rutas HTTP y HTTPS desde fuera del clúster hacia Services dentro del clúster. Ingress proporciona balanceo de carga, terminación SSL y alojamiento virtual basado en nombres.
</details>

3. ¿Cuáles son los dos mecanismos de descubrimiento de Services integrados en Kubernetes? (Selecciona dos.)
   - A) Variables de entorno
   - B) DNS
   - C) Service Mesh
   - D) ConfigMap
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Variables de entorno y B) DNS**

**Explicación:**
Kubernetes proporciona dos métodos principales para descubrir Services: las variables de entorno y DNS. ConfigMap almacena datos de configuración y no es un mecanismo de descubrimiento de servicios.
</details>

4. ¿Qué tipo de Service de Kubernetes permite acceder a un Service mediante un puerto específico en todos los nodos?
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalName
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) NodePort**

**Explicación:**
Los Services de tipo NodePort permiten acceder al Service mediante un puerto específico de todos los nodos. Se puede acceder a él usando la dirección IP de cada nodo y el valor de NodePort, que se asigna de forma predeterminada dentro del intervalo 30000–32767.
</details>

5. ¿Qué tipo de Service no tiene una IP de clúster y crea registros DNS para cada Pod?
   - A) Service de tipo NodePort
   - B) Service de tipo LoadBalancer
   - C) Service headless
   - D) Service de tipo ExternalName
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Service headless**

**Explicación:**
Un Service headless se configura con `clusterIP: None`, por lo que no se le asigna una IP de clúster y se crean registros DNS para cada Pod. Esto resulta útil cuando los clientes necesitan acceder directamente a Pods concretos detrás del Service.
</details>

6. ¿Qué recurso permite controlar la comunicación entre Pods en Kubernetes?
   - A) Service
   - B) Ingress
   - C) NetworkPolicy
   - D) EndpointSlice
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) NetworkPolicy**

**Explicación:**
NetworkPolicy permite controlar la comunicación entre Pods. Las políticas de red pueden restringir el tráfico de entrada y salida entre Pods.
</details>

7. ¿Qué servidor DNS se utiliza en los clústeres de Kubernetes?
   - A) kube-dns
   - B) CoreDNS
   - C) NodeDNS
   - D) ClusterDNS
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) CoreDNS**

**Explicación:**
CoreDNS es un servidor DNS flexible y extensible que se utiliza en los clústeres de Kubernetes. Alcanzó el estado GA en Kubernetes 1.11 y es el servidor DNS predeterminado desde Kubernetes 1.13.
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
Cilium utiliza eBPF (extended Berkeley Packet Filter), una tecnología del kernel de Linux, para proporcionar conectividad de red, seguridad y observabilidad a las aplicaciones en contenedores.
</details>

9. ¿Cuál de las siguientes NO es una función principal de un service mesh?
   - A) Descubrimiento de servicios
   - B) Balanceo de carga
   - C) Proporcionar almacenamiento persistente
   - D) Comunicación cifrada
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Proporcionar almacenamiento persistente**

**Explicación:**
Un service mesh es una capa de infraestructura que gestiona la comunicación entre microservicios. Ofrece funciones como descubrimiento de servicios, balanceo de carga, cifrado, autenticación, autorización y observabilidad. Proporcionar almacenamiento persistente no es una de sus funciones principales.
</details>

10. ¿Qué tipo de Service de Kubernetes proporciona un alias para un servicio externo?
    - A) ClusterIP
    - B) NodePort
    - C) LoadBalancer
    - D) ExternalName
    
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) ExternalName**

**Explicación:**
Los Services de tipo ExternalName proporcionan un alias para un servicio externo. Este tipo de Service asigna un nombre DNS al nombre DNS del servicio externo.
</details>

## Preguntas de respuesta corta

1. ¿Cómo se llama el recurso de Kubernetes que almacena las direcciones IP y los puertos de los Pods que actúan como backends de un Service?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: EndpointSlice**

**Explicación:**
Los EndpointSlices almacenan las direcciones y los puertos de los backends de un Service. El controlador los gestiona en los Services que usan selectores. El recurso Endpoints heredado cumple una función similar, pero está obsoleto desde Kubernetes v1.33.
</details>

2. ¿Cómo se llama el controlador de Ingress que aprovisiona Application Load Balancers en AWS EKS?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: AWS Load Balancer Controller**

**Explicación:**
AWS Load Balancer Controller es un controlador de Ingress que aprovisiona Application Load Balancers en AWS EKS. Convierte los recursos Ingress de Kubernetes en ALB de AWS.
</details>

3. ¿Cómo se llama la política DNS de Pod de Kubernetes que hereda la configuración DNS del nodo donde se ejecuta el Pod?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Default**

**Explicación:**
La política DNS `Default` hereda la configuración DNS del nodo donde se ejecuta el Pod. Es decir, el Pod utiliza tal cual el archivo `/etc/resolv.conf` del nodo.
</details>

4. ¿Cómo se llama la capa de observabilidad de Cilium que utiliza eBPF para supervisar los flujos de red y diagnosticar problemas?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Hubble**

**Explicación:**
Hubble es la capa de observabilidad de Cilium que utiliza eBPF para supervisar los flujos de red y diagnosticar problemas. Ofrece supervisión de flujos de red, mapas de dependencias entre servicios, observación de seguridad, análisis del rendimiento y herramientas de diagnóstico.
</details>

5. ¿Qué recurso de Kubernetes es una alternativa escalable a Endpoints que ofrece un mejor rendimiento en clústeres grandes?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: EndpointSlice**

**Explicación:**
EndpointSlice es una alternativa escalable a Endpoints que ofrece un mejor rendimiento en clústeres grandes. Mejora el rendimiento de los Services grandes al dividir los endpoints en varios fragmentos para gestionarlos.
</details>

## Preguntas avanzadas

1. Explica cómo se utiliza un service mesh (por ejemplo, Istio) para gestionar la comunicación entre microservicios en Kubernetes y describe sus beneficios.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

Un service mesh es una capa de infraestructura que gestiona la comunicación entre microservicios. Puede implementarse de las siguientes formas:

1. **Patrón sidecar**: Se inyectan contenedores proxy (por ejemplo, Envoy) en cada Pod para interceptar y controlar todo el tráfico de red.

2. **Plano de control**: Un componente de gestión centralizado (por ejemplo, istiod de Istio) configura y gestiona todos los proxies sidecar.

3. **Gestión del tráfico**:
```yaml
apiVersion: networking.istio.io/v1
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
apiVersion: security.istio.io/v1
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

**Beneficios:**

1. **Gestión del tráfico**: Admite enrutamiento avanzado, balanceo de carga, división del tráfico, despliegues canary y otras funciones.

2. **Seguridad**: Proporciona cifrado TLS mutuo (mTLS), autenticación y autorización entre servicios.

3. **Observabilidad**: Supervisa la comunicación entre servicios mediante trazado distribuido, recopilación de métricas y registro de logs.

4. **Resiliencia**: Mejora la resiliencia del sistema mediante circuit breakers, reintentos, timeouts e inyección de fallos.

5. **Aplicación de políticas**: Permite aplicar políticas como límites de tasa, cuotas y control de acceso.

6. **Independencia de la plataforma**: Estas funciones pueden añadirse sin cambiar el código de la aplicación.

Los service meshes abstraen la complejidad de la comunicación entre servicios en arquitecturas de microservicios complejas y permiten que los desarrolladores se centren en la lógica de negocio.
</details>

2. Explica los beneficios de la tecnología eBPF de Cilium frente a los enfoques de red tradicionales (por ejemplo, iptables) y sugiere formas de optimizar Cilium en AWS EKS.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Beneficios de la tecnología eBPF de Cilium:**

1. **Rendimiento**: eBPF se ejecuta directamente en el kernel para optimizar las rutas de procesamiento de paquetes y ofrecer un rendimiento muy superior al de iptables. En particular, iptables realiza búsquedas lineales cuando hay muchas reglas, mientras que eBPF puede utilizar estructuras de datos eficientes, como tablas hash.

2. **Escalabilidad**: eBPF mantiene un rendimiento uniforme incluso en clústeres grandes. El rendimiento de iptables se degrada rápidamente al aumentar el número de reglas.

3. **Programabilidad**: eBPF se puede programar en un lenguaje similar a C, lo que permite implementar lógica de red compleja. iptables solo admite un conjunto limitado de reglas.

4. **Observabilidad**: eBPF puede recopilar métricas detalladas sobre los flujos de red, útiles para diagnosticar problemas y optimizar el rendimiento.

5. **Políticas de capa L7**: Cilium combina eBPF con Envoy en espacio de usuario para inspeccionar HTTP y otros protocolos de capa L7; este procesamiento no se realiza íntegramente en el kernel mediante eBPF.

**Formas de optimizar Cilium en AWS EKS:**

1. **Elegir deliberadamente IPAM y enrutamiento**: El encadenamiento con AWS VPC CNI mantiene `aws-node`; el modo ENI de Cilium requiere permisos de EC2 y una transición controlada de la propiedad de las ENI. Usa los valores de Helm revisados en el capítulo y el procedimiento oficial de instalación.

2. **Dimensionar la red de los nodos**: Comprueba los límites reales de ENI e IP de cada instancia, la capacidad de las subredes y la densidad de Pods; el nombre de una familia de instancias no basta para determinar la capacidad.

3. **Medir antes de ajustar**: Los valores actuales de Helm usan `routingMode: native` y, cuando corresponde, el valor booleano `kubeProxyReplacement: true`, en lugar de las opciones eliminadas `tunnel=disabled` o `kubeProxyReplacement=strict`. El reemplazo también requiere conectividad con el servidor de API y un plan de migración. DSR y XDP necesitan una red de AWS y compatibilidad de NIC/kernel adecuadas, además de pruebas con mediciones; activar todas las opciones no es una receta de optimización universal.

4. **Habilitar Hubble**:
```bash
cilium hubble enable --ui
```
Habilita Hubble para supervisar los flujos de red y diagnosticar problemas.

5. **Conectividad entre clústeres**:
Configura Cilium Cluster Mesh para habilitar la conectividad de red entre varios clústeres de EKS.

6. **Integración de monitorización**:
Configura Prometheus y Grafana para recopilar y visualizar métricas de Cilium.

Estas optimizaciones pueden maximizar el rendimiento, la seguridad y la observabilidad de Cilium en AWS EKS.
</details>

## Conclusión

Con este cuestionario, pusiste a prueba tus conocimientos sobre los Services y las redes de Kubernetes. Los temas incluyen los tipos de Service, Ingress, las políticas de red, el descubrimiento de servicios, CoreDNS y Cilium. Comprender y aplicar estos conceptos te permite crear aplicaciones de Kubernetes seguras y escalables.
