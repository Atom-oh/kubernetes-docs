# Cuestionario de redes y balanceo de carga L2-L7 de Cilium

Este cuestionario evalúa tu comprensión de las funciones de redes L2-L7 de Cilium, la arquitectura de balanceo de carga, el masquerading, la integración con service mesh y más.

## Preguntas de opción múltiple

1. En el modelo OSI, ¿en qué capa operan protocolos como HTTP, gRPC y DNS?
   - A) L3 (capa de red)
   - B) L4 (capa de transporte)
   - C) L5 (capa de sesión)
   - D) L7 (capa de aplicación)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) L7 (capa de aplicación)**

**Explicación:**
En el modelo OSI, L7 (capa de aplicación) es la capa más cercana al usuario, donde operan protocolos de aplicación como HTTP, HTTPS, gRPC, DNS, FTP y Kafka. Cilium proporciona filtrado compatible con API en la capa L7, lo que permite políticas de red detalladas basadas en métodos/rutas/encabezados HTTP, métodos gRPC, topics de Kafka y más. Esto es esencial para el control detallado de la comunicación entre servicios en arquitecturas de microservicios.
</details>

2. ¿Cuál es la principal ventaja del modo DSR (Direct Server Return) de Cilium?
   - A) Puede ocultar las IP de los clientes
   - B) El tráfico de respuesta omite el balanceador de carga, lo que mejora el rendimiento
   - C) Cifra todo el tráfico
   - D) Aplica automáticamente políticas L7

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El tráfico de respuesta omite el balanceador de carga, lo que mejora el rendimiento**

**Explicación:**
En el modo DSR (Direct Server Return), solo las solicitudes del cliente pasan por el balanceador de carga, mientras que las respuestas del servidor omiten el balanceador de carga y se envían directamente al cliente. Esto elimina los cuellos de botella del balanceador de carga, ahorra ancho de banda de red y reduce la latencia de respuesta. Es particularmente eficaz al manejar respuestas grandes (descargas de archivos, streaming, etc.). El modo DSR también conserva las IP de los clientes incluso detrás de balanceadores de carga externos.
</details>

3. ¿Qué componente proporciona la funcionalidad de proxy L7 en Cilium?
   - A) kube-proxy
   - B) Hubble
   - C) Envoy
   - D) CoreDNS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Envoy**

**Explicación:**
Cilium integra el proxy Envoy para la funcionalidad de proxy L7. Cuando defines reglas L7 (HTTP, gRPC, Kafka, DNS, etc.) en una CiliumNetworkPolicy, Cilium implementa automáticamente el proxy Envoy de forma transparente sin sidecars. Envoy proporciona manejo de tráfico HTTP/gRPC, balanceo de carga avanzado, división de tráfico y recopilación de métricas. Este enfoque reduce la sobrecarga de recursos, ya que no es necesario implementar proxies sidecar separados.
</details>

4. ¿Cuál de los siguientes NO es un algoritmo de balanceo de carga compatible con Cilium?
   - A) Round Robin
   - B) Maglev Consistent Hashing
   - C) Source IP Hash
   - D) Weighted Response Time

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Weighted Response Time**

**Explicación:**
Cilium admite algoritmos de balanceo de carga como Round Robin, Least Connection, Source IP Hash, Random y Maglev Consistent Hashing. Maglev es un algoritmo de hashing consistente desarrollado por Google que mantiene la consistencia de las conexiones incluso cuando se agregan o eliminan servidores backend. Weighted Response Time no es un algoritmo compatible directamente con Cilium. Sin embargo, se pueden implementar estrategias de balanceo de carga más avanzadas mediante el proxy Envoy.
</details>

5. ¿Cuál NO es una ventaja de la implementación basada en eBPF para el masquerading de Cilium?
   - A) Procesamiento más rápido que iptables
   - B) Mejor escalabilidad
   - C) Compatible con todas las versiones del kernel de Linux
   - D) Procesamiento directo en el espacio del kernel

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Compatible con todas las versiones del kernel de Linux**

**Explicación:**
El masquerading basado en eBPF es más rápido que iptables, más escalable y más eficiente, ya que procesa directamente en el espacio del kernel. Sin embargo, el masquerading basado en eBPF solo es totalmente compatible con kernels de Linux recientes (4.19 y posteriores). En kernels antiguos, debes recurrir al masquerading basado en iptables. Puedes habilitar el masquerading basado en eBPF con la opción `enable-bpf-masquerade: true` en la configuración de Cilium.
</details>

6. ¿Qué modo de Cilium reemplaza completamente kube-proxy para los servicios de Kubernetes?
   - A) kube-proxy-replacement: partial
   - B) kube-proxy-replacement: strict
   - C) kube-proxy-replacement: hybrid
   - D) kube-proxy-replacement: disabled

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) kube-proxy-replacement: strict**

**Explicación:**
La configuración `kube-proxy-replacement: strict` hace que Cilium reemplace por completo toda la funcionalidad de kube-proxy. En este modo, Cilium maneja todos los servicios ClusterIP, NodePort, LoadBalancer y ExternalIP. En el modo strict, kube-proxy debe eliminarse o deshabilitarse. El modo `partial` reemplaza solo algunas funciones y `disabled` deshabilita el reemplazo de kube-proxy. El modo strict es obligatorio al usar funciones avanzadas como DSR, hashing Maglev y balanceo de carga a nivel de socket.
</details>

7. ¿Cuál NO es una condición que se puede usar para filtrar solicitudes HTTP en las políticas L7 de Cilium?
   - A) Método HTTP (GET, POST, etc.)
   - B) Ruta URL
   - C) Encabezados HTTP
   - D) Cuerpo de la solicitud

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Cuerpo de la solicitud**

**Explicación:**
Las políticas HTTP L7 de Cilium pueden filtrar según métodos HTTP (GET, POST, PUT, DELETE, etc.), rutas URL (con compatibilidad con regex) y encabezados HTTP (con compatibilidad con regex). Sin embargo, Cilium no admite directamente la inspección del cuerpo de la solicitud debido a la importante sobrecarga de rendimiento y complejidad. Si se requiere inspeccionar el cuerpo de la solicitud, debes usar un WAF (Web Application Firewall) o soluciones de seguridad de la capa de aplicación independientes.
</details>

8. ¿Cuál es el principal beneficio de integrar Cilium con Istio?
   - A) Reemplaza completamente toda la funcionalidad de Istio
   - B) Reduce la sobrecarga de sidecars mediante un plano de datos basado en eBPF
   - C) Deshabilita automáticamente mTLS
   - D) Implementa un service mesh sin Istio

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Reduce la sobrecarga de sidecars mediante un plano de datos basado en eBPF**

**Explicación:**
La integración de Cilium con Istio permite reemplazar parte de la funcionalidad de los sidecars de Envoy por el plano de datos basado en eBPF, lo que reduce la sobrecarga de recursos. Cilium maneja el procesamiento de tráfico L3/L4 y las políticas de red con eBPF, y reenvía solo el tráfico L7 necesario a Envoy. Esto mejora el rendimiento y reduce la latencia. Sin embargo, Cilium no reemplaza toda la funcionalidad de Istio, y las funciones avanzadas de Istio, como mTLS, siguen siendo manejadas por Istio.
</details>

9. ¿Cuál es el beneficio del balanceo de carga a nivel de socket en Cilium?
   - A) Traduce la IP del servicio a la IP del backend en el kernel antes de procesar los paquetes
   - B) Aplica automáticamente políticas L7
   - C) Solo maneja tráfico cifrado
   - D) Requiere un balanceador de carga externo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Traduce la IP del servicio a la IP del backend en el kernel antes de procesar los paquetes**

**Explicación:**
El balanceo de carga a nivel de socket traduce las IP de servicio a IP de Pod del backend en la llamada al sistema connect() antes de enviar los paquetes. Esto es mucho más eficiente que el NAT (Network Address Translation) tradicional basado en paquetes. Entre los beneficios se incluyen una menor sobrecarga de conntrack (connection tracking), la conservación de la IP de origen, menor latencia y mejor escalabilidad. El LB a nivel de socket opera de forma transparente desde la perspectiva de la aplicación, haciendo que las aplicaciones parezcan comunicarse directamente con los Pods backend.
</details>

10. ¿Cuál es la práctica recomendada respecto al manejo de fragmentos IPv4 en Cilium?
    - A) Deshabilitar siempre el seguimiento de fragmentos
    - B) Configurar el MTU de forma coherente para evitar la fragmentación
    - C) Bloquear todos los fragmentos
    - D) Establecer el tamaño de fragmento al máximo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar el MTU de forma coherente para evitar la fragmentación**

**Explicación:**
La fragmentación IPv4 puede causar degradación del rendimiento y problemas de seguridad, por lo que debe evitarse cuando sea posible. Para lograrlo, configura el MTU (Maximum Transmission Unit) de forma coherente en toda la red y, al usar redes overlay (VXLAN, etc.), ajusta el MTU para considerar la sobrecarga de encapsulación (aproximadamente 50 bytes). Habilitar Path MTU Discovery (PMTUD) puede detectar automáticamente el MTU óptimo. Habilitar el seguimiento de fragmentos (`enable-ipv4-fragment-tracking`) puede evitar ataques basados en fragmentos.
</details>

## Preguntas de respuesta corta

11. Enumera 4 protocolos compatibles con Cilium para políticas de red L7.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** HTTP, gRPC, Kafka, DNS

**Explicación:**
Los principales protocolos compatibles con las políticas L7 de Cilium son:
- **HTTP/HTTPS**: API REST y tráfico web, con compatibilidad para filtrado basado en método/ruta/encabezado
- **gRPC**: Comunicación RPC entre microservicios, con compatibilidad para filtrado basado en servicio/método
- **Kafka**: Protocolo de cola de mensajes, con compatibilidad para filtrado basado en topic/clientID/API key
- **DNS**: Filtrado de consultas y respuestas DNS, con compatibilidad para políticas basadas en FQDN
Además, se pueden admitir protocolos personalizados mediante filtros de Envoy.
</details>

12. ¿Cuál es el nombre del mecanismo de los balanceadores de carga de Cilium que comprueba el estado de los servidores backend?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** Health Check

**Explicación:**
Los balanceadores de carga de Cilium admiten varios mecanismos de comprobación de estado:
- **Comprobaciones de estado TCP**: Verifican la conectividad del puerto
- **Comprobaciones de estado HTTP**: Verifican los códigos de respuesta HTTP (200 OK, etc.)
- **Integración con Kubernetes Readiness/Liveness Probe**: Utiliza los resultados de las sondas de estado de los Pods
Los backends no saludables se eliminan automáticamente del pool de balanceo de carga y se vuelven a agregar cuando se recuperan. Esto garantiza la alta disponibilidad de los servicios.
</details>

13. ¿Cuál es el nombre de la función de Cilium que traduce la IP de origen del tráfico externo a una IP interna?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** Masquerading o SNAT (Source NAT)

**Explicación:**
Masquerading es la función que traduce la IP de origen del tráfico saliente de los Pods dentro del clúster a la IP del nodo. Esta es una forma de SNAT (Source Network Address Translation). El propósito del masquerading es ocultar las IP internas del clúster a las redes externas y permitir el acceso a servicios fuera del clúster. Cilium admite tanto el masquerading basado en iptables como el basado en eBPF, y el basado en eBPF ofrece mayor rendimiento.
</details>

14. ¿Cuál es el nombre del algoritmo de hashing utilizado para la persistencia de sesión cuando Cilium reemplaza kube-proxy?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** Maglev (Consistent Hashing)

**Explicación:**
Maglev es un algoritmo de hashing consistente desarrollado por Google. Al usar Maglev en Cilium, la mayoría de las conexiones existentes se mantienen en el mismo backend incluso cuando se agregan o eliminan servidores backend. Esto es importante para las aplicaciones que requieren afinidad de sesión. Maglev proporciona una alta uniformidad en la distribución de carga y bajas tasas de redistribución de conexiones, por lo que es eficaz en entornos de balanceo de carga a gran escala.
</details>

15. ¿Cuál es el nombre y el número de la capa del modelo OSI en la que operan los protocolos TCP y UDP?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** L4 (capa de transporte)

**Explicación:**
L4 (capa de transporte) es la cuarta capa del modelo OSI, responsable de la conexión de extremo a extremo y la fiabilidad. TCP (Transmission Control Protocol) y UDP (User Datagram Protocol) operan en esta capa. TCP está orientado a conexión y proporciona comunicación fiable, mientras que UDP no requiere conexión y es rápido, pero no garantiza la fiabilidad. Las políticas L4 de Cilium pueden filtrar el tráfico según los números de puerto y los protocolos (TCP/UDP).
</details>

## Preguntas prácticas

16. Escribe una CiliumNetworkPolicy que permita solo solicitudes HTTP GET a la ruta `/api/v1/users` y permita solicitudes POST a la ruta `/api/v1/data` solo cuando esté presente el encabezado `X-Auth-Token`.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "l7-http-policy"
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: backend-api
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "80"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/users"
        - method: "POST"
          path: "/api/v1/data"
          headers:
          - "X-Auth-Token: .*"
```

**Explicación:**
Esta CiliumNetworkPolicy implementa control de acceso detallado mediante reglas HTTP L7. La sección `rules.http` define dos reglas: la primera permite el método GET a la ruta `/api/v1/users` y la segunda permite el método POST a la ruta `/api/v1/data` solo cuando está presente el encabezado `X-Auth-Token`. Los valores de los encabezados se pueden especificar con regex, por lo que `.*` permite cualquier valor. Cuando se aplica esta política, Cilium implementa automáticamente el proxy Envoy de forma transparente para inspeccionar el tráfico L7.
</details>

17. Escribe un comando Helm para instalar Cilium en modo de reemplazo de kube-proxy con el modo DSR y el hashing Maglev habilitados.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# Add Helm repo
helm repo add cilium https://helm.cilium.io/
helm repo update

# Install Cilium with kube-proxy replacement + DSR + Maglev settings
helm install cilium cilium/cilium --version 1.18.0 \
  --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost=<API_SERVER_IP> \
  --set k8sServicePort=6443 \
  --set loadBalancer.mode=dsr \
  --set loadBalancer.algorithm=maglev \
  --set maglev.tableSize=65521 \
  --set bpf.masquerade=true

# Disable existing kube-proxy (delete or scale down DaemonSet)
kubectl -n kube-system delete ds kube-proxy
# Or modify kube-proxy ConfigMap to disable

# Verify installation
cilium status --verbose
kubectl -n kube-system exec ds/cilium -- cilium status | grep KubeProxyReplacement
```

**Explicación:**
`kubeProxyReplacement=true` configura Cilium para reemplazar la funcionalidad de kube-proxy. `k8sServiceHost` y `k8sServicePort` especifican la dirección del servidor API (necesaria para acceder al servidor API sin kube-proxy). `loadBalancer.mode=dsr` habilita el modo Direct Server Return y `loadBalancer.algorithm=maglev` utiliza hashing consistente Maglev. `maglev.tableSize` establece el tamaño de la tabla hash (se recomiendan números primos). `bpf.masquerade=true` habilita el masquerading basado en eBPF.
</details>

18. Escribe una CiliumNetworkPolicy que aplique políticas L7 al tráfico de Kafka y permita solo operaciones de producción en el topic `orders` y solo operaciones de consumo en el topic `payments`.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "kafka-l7-policy"
  namespace: messaging
spec:
  endpointSelector:
    matchLabels:
      app: kafka-broker
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: order-service
    toPorts:
    - ports:
      - port: "9092"
        protocol: TCP
      rules:
        kafka:
        - apiKey: "produce"
          topic: "orders"
  - fromEndpoints:
    - matchLabels:
        app: payment-processor
    toPorts:
    - ports:
      - port: "9092"
        protocol: TCP
      rules:
        kafka:
        - apiKey: "fetch"
          topic: "payments"
```

**Explicación:**
Esta CiliumNetworkPolicy implementa control de acceso detallado mediante reglas Kafka L7. La primera regla de ingress permite que los Pods `order-service` realicen solo operaciones de producción (`apiKey: produce`) en el topic `orders`. La segunda regla permite que los Pods `payment-processor` realicen solo operaciones de consumo (`apiKey: fetch`) en el topic `payments`. Las API keys de Kafka incluyen `produce`, `fetch`, `metadata`, `offsets`, etc., y también puedes agregar `clientID` para permitir solo clientes específicos.
</details>

19. Escribe una configuración para habilitar el masquerading basado en eBPF en Cilium y excluir el masquerading para un rango CIDR específico (10.0.0.0/8).

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
# ConfigMap settings
apiVersion: v1
kind: ConfigMap
metadata:
  name: cilium-config
  namespace: kube-system
data:
  enable-ipv4-masquerade: "true"
  enable-bpf-masquerade: "true"
  ipv4-native-routing-cidr: "10.0.0.0/8"
  enable-ipv6-masquerade: "false"
```

```bash
# Install/upgrade using Helm
helm upgrade cilium cilium/cilium --version 1.18.0 \
  --namespace kube-system \
  --set ipv4NativeRoutingCIDR=10.0.0.0/8 \
  --set bpf.masquerade=true \
  --set enableIPv4Masquerade=true

# Verify settings
kubectl -n kube-system exec ds/cilium -- cilium status --verbose | grep -i masquerade

# Check masquerading rules
kubectl -n kube-system exec ds/cilium -- cilium bpf nat list
```

**Explicación:**
`enable-bpf-masquerade: true` habilita el masquerading basado en eBPF. `ipv4-native-routing-cidr: 10.0.0.0/8` configura el tráfico hacia este rango CIDR para usar enrutamiento nativo sin masquerading. Esto es útil cuando es necesario conservar la IP de origen para la comunicación dentro del clúster o dentro de la VPC. Si el CIDR de Pods y el CIDR de servicios del clúster se incluyen en este rango, el masquerading no se aplicará al tráfico interno.
</details>

20. Escribe los comandos para diagnosticar problemas cuando las políticas L7 no funcionan como se espera en Cilium. Incluye el estado del proxy Envoy, el estado de aplicación de políticas y la monitorización de tráfico en tiempo real.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# 1. Check overall Cilium status
cilium status --verbose

# 2. Check Envoy proxy status
kubectl -n kube-system exec ds/cilium -- cilium status | grep -i proxy
kubectl -n kube-system exec ds/cilium -- cilium bpf proxy list

# 3. Check policy application status
cilium policy get
kubectl get cnp -A -o wide
kubectl get ccnp -A -o wide

# 4. Check policy status for a specific endpoint
cilium endpoint list
cilium endpoint get <endpoint_id> -o json | jq '.status.policy'

# 5. Real-time traffic monitoring (including L7)
cilium monitor --type l7
cilium monitor --type policy-verdict
cilium monitor --type drop

# 6. Observe L7 flows through Hubble
hubble observe --protocol http
hubble observe --verdict DROPPED
hubble observe --pod <namespace>/<pod-name>

# 7. Check Envoy logs
kubectl -n kube-system logs ds/cilium | grep -i envoy
kubectl -n kube-system logs ds/cilium | grep -i proxy

# 8. Regenerate endpoint (reapply policy)
kubectl -n kube-system exec ds/cilium -- cilium endpoint regenerate <endpoint_id>

# 9. Network policy troubleshooting
cilium policy trace --src-identity <src_id> --dst-identity <dst_id> --dport <port>
```

**Explicación:**
Se necesita un enfoque sistemático para solucionar problemas de políticas L7. Primero, verifica el estado general del sistema con `cilium status` y confirma que el proxy Envoy esté funcionando normalmente. Comprueba las políticas aplicadas con `cilium policy get` y verifica que las políticas se apliquen correctamente a Pods específicos con `cilium endpoint get`. Monitoriza el tráfico en tiempo real y los veredictos de políticas con `cilium monitor` y `hubble observe`. El comando `policy trace` simula el proceso de decisión de políticas para flujos de tráfico específicos.
</details>

---

[Volver a los materiales de aprendizaje](../../../networking/cilium/05-l2-l7-networking.md) | [Siguiente cuestionario: Seguridad y visibilidad](./06-security-visibility-quiz.md)
