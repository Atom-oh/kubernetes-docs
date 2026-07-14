# Cuestionario de introducción y conceptos básicos de Cilium

Este cuestionario evalúa tu comprensión de los conceptos básicos de Cilium, la tecnología eBPF, la arquitectura, los componentes clave y las comparaciones de CNI.

## Preguntas de opción múltiple

1. ¿Cuál es la tecnología principal de Cilium que proporciona una ruta de datos programable dentro del kernel?
   - A) iptables
   - B) eBPF
   - C) VXLAN
   - D) IPsec

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) eBPF**

**Explicación:**
eBPF (extended Berkeley Packet Filter) es una tecnología que permite que los programas se ejecuten de forma segura dentro del kernel de Linux. Cilium aprovecha eBPF para implementar funcionalidades de red, seguridad y observabilidad a nivel del kernel. Esto proporciona un rendimiento y una flexibilidad mucho mayores que las soluciones basadas en iptables, y permite aplicar políticas de red dinámicamente sin recompilar el kernel.
</details>

2. ¿Qué capa admite la política de red de Cilium?
   - A) Solo L3 (capa de red)
   - B) L3-L4 (capas de red y transporte)
   - C) L3-L7 (de la capa de red a la capa de aplicación)
   - D) L2-L3 (capas de enlace de datos y red)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) L3-L7 (de la capa de red a la capa de aplicación)**

**Explicación:**
Cilium admite políticas de red desde L3 (IP), L4 (puertos TCP/UDP) y hasta L7 (capa de aplicación). Esto significa que puede filtrar tráfico a nivel de aplicación, como métodos HTTP, rutas, encabezados, métodos gRPC, temas de Kafka y más. Esta red con reconocimiento de API es muy útil para implementar políticas de seguridad granulares en arquitecturas de microservicios.
</details>

3. ¿Qué herramienta proporciona visibilidad y monitoreo de red en Cilium?
   - A) Prometheus
   - B) Hubble
   - C) Grafana
   - D) Jaeger

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Hubble**

**Explicación:**
Hubble es la capa de observabilidad de red de Cilium que usa eBPF para monitorear y analizar flujos de red en tiempo real. Hubble proporciona funcionalidades como generación de mapas de dependencias de servicios, detección de infracciones de políticas de red, rastreo de solicitudes HTTP/gRPC/DNS y medición de latencia de red. Prometheus y Grafana son herramientas de recopilación y visualización de métricas, mientras que Jaeger es una herramienta de rastreo distribuido.
</details>

4. ¿Qué componente de Kubernetes puede reemplazar la funcionalidad de balanceo de carga distribuido de Cilium?
   - A) CoreDNS
   - B) kube-proxy
   - C) etcd
   - D) kubelet

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) kube-proxy**

**Explicación:**
Cilium proporciona balanceo de carga de Service basado en eBPF que puede reemplazar por completo a kube-proxy. Mientras kube-proxy usa iptables o IPVS para enrutar el tráfico de Service a los Pods de backend, Cilium usa eBPF para proporcionar mayor rendimiento y escalabilidad. Cuando está habilitado el modo de reemplazo de kube-proxy de Cilium, también están disponibles funcionalidades avanzadas como DSR (Direct Server Return), hash Maglev y balanceo de carga a nivel de socket.
</details>

5. ¿Cuál NO es un método de cifrado de tráfico entre nodos compatible con Cilium?
   - A) IPsec
   - B) WireGuard
   - C) TLS
   - D) Ambos son compatibles (A y B)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) TLS**

**Explicación:**
Cilium admite dos métodos para el cifrado de tráfico entre nodos: IPsec y WireGuard. IPsec es un conjunto tradicional de protocolos VPN ampliamente utilizado, mientras que WireGuard es un protocolo VPN más moderno, sencillo y rápido. TLS es un protocolo de cifrado de capa de aplicación que se utiliza con fines distintos al cifrado de capa de red de Cilium. En Cilium, puedes elegir IPsec o WireGuard mediante opciones de configuración para implementar cifrado de red transparente.
</details>

6. ¿Cómo se llama la funcionalidad de red multi-clúster de Cilium?
   - A) Cluster Federation
   - B) Cluster Mesh
   - C) Multi-Cluster Network
   - D) Global Cluster

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Cluster Mesh**

**Explicación:**
Cluster Mesh es la funcionalidad de red multi-clúster de Cilium que conecta varios clústeres de Kubernetes para que operen como una única red. Con Cluster Mesh, es posible realizar descubrimiento de Service entre clústeres, balanceo de carga y aplicación de políticas de red. Esta funcionalidad es útil para escenarios de nube híbrida, multi-cloud y recuperación ante desastres, ya que permite que los Pods de cada clúster accedan directamente a Services en otros clústeres.
</details>

7. ¿Qué tecnología usa Cilium para optimizar el rendimiento del procesamiento de paquetes?
   - A) DPDK
   - B) XDP (eXpress Data Path)
   - C) RDMA
   - D) SR-IOV

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) XDP (eXpress Data Path)**

**Explicación:**
XDP (eXpress Data Path) es una tecnología basada en eBPF que permite procesar paquetes a nivel del controlador de red. XDP omite la pila de red del kernel para habilitar un procesamiento de paquetes de muy alto rendimiento (millones de paquetes por segundo). Cilium usa XDP para implementar defensa contra DDoS, balanceo de carga de alto rendimiento y filtrado de paquetes. DPDK, RDMA y SR-IOV también son tecnologías de red de alto rendimiento, pero la tecnología principal de Cilium es eBPF/XDP.
</details>

8. ¿Cuál es la versión mínima del kernel de Linux compatible con Cilium 1.18?
   - A) 3.10
   - B) 4.9
   - C) 4.19
   - D) 5.10

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) 4.19**

**Explicación:**
Cilium 1.18 requiere kernel de Linux 4.19 o posterior. Esto se debe a que las funcionalidades de eBPF utilizadas por Cilium son totalmente compatibles en esta versión y posteriores. El uso de una versión más reciente del kernel (5.x y posteriores) proporciona funcionalidades adicionales de eBPF y mejor rendimiento. Por ejemplo, las funcionalidades avanzadas como el modo nativo de XDP, las llamadas de función BPF-a-BPF y BTF (BPF Type Format) tienen mejor compatibilidad en kernels más recientes.
</details>

9. ¿Cuál de los siguientes plugins de CNI NO está basado en eBPF?
   - A) Cilium
   - B) Calico (modo eBPF)
   - C) Flannel
   - D) Ambos no están basados en eBPF (solo C)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Flannel**

**Explicación:**
Flannel es una solución de red superpuesta simple que usa VXLAN o host-gw y no utiliza eBPF. En cambio, Cilium fue diseñado desde cero para basarse en eBPF, y Calico también admite el modo de plano de datos eBPF en versiones recientes. Flannel es sencillo de configurar y tiene bajo uso de recursos, pero no proporciona políticas de red L7 ni funcionalidades avanzadas de observabilidad.
</details>

10. ¿Cuál es la versión de la API de Cilium Network Policy?
    - A) networking.k8s.io/v1
    - B) cilium.io/v1
    - C) cilium.io/v2
    - D) policy.cilium.io/v1

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) cilium.io/v2**

**Explicación:**
CiliumNetworkPolicy usa la versión de API `cilium.io/v2`. Esta es una CRD (Custom Resource Definition) independiente de la NetworkPolicy estándar de Kubernetes (`networking.k8s.io/v1`) para admitir las funcionalidades avanzadas de Cilium (políticas L7, políticas basadas en DNS, selectores de endpoint, etc.). Cilium también admite la NetworkPolicy estándar de Kubernetes, pero usar CiliumNetworkPolicy permite un control más granular.
</details>

## Preguntas de respuesta corta

11. ¿Cuál es el nombre del componente principal que se ejecuta en cada nodo de Cilium, carga programas eBPF e implementa políticas de red?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Cilium Agent**

**Explicación:**
Cilium Agent es el componente principal de Cilium que se ejecuta como un DaemonSet en cada nodo de Kubernetes. Las responsabilidades principales del Agent incluyen cargar y administrar programas eBPF en el kernel, implementar y aplicar políticas de red, realizar balanceo de carga de Service, administración de direcciones IP (IPAM), administración de endpoints de red, recopilación de métricas y logs, y comunicación con el servidor de API. Cilium Agent gestiona todas las operaciones de red en el nodo local.
</details>

12. ¿Qué componente de Cilium se ejecuta en todo el clúster y realiza tareas como la sincronización de CRD y la coordinación de asignación de IP?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Cilium Operator**

**Explicación:**
Cilium Operator es un Kubernetes Operator que se ejecuta como una única instancia en todo el clúster. Mientras el Agent gestiona operaciones locales en cada nodo, el Operator gestiona operaciones a nivel de todo el clúster. Las funciones clave incluyen la administración de CRD CiliumIdentity y CiliumEndpoint, administración de IPAM a nivel de clúster, coordinación de asignación de CIDR entre nodos, recolección de basura (limpieza de recursos no utilizados) y administración de conexiones de Cluster Mesh.
</details>

13. ¿Qué comando de CLI se usa para diagnosticar problemas de conectividad en Cilium?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: cilium connectivity test**

**Explicación:**
El comando `cilium connectivity test` prueba de forma integral la conectividad de red en un clúster de Cilium. Este comando prueba automáticamente diversos escenarios, incluidos la comunicación de Pod a Pod, la conectividad de Service, la conectividad externa y la aplicación de políticas de red. Los resultados de la prueba se muestran como éxito/error, y se proporciona información detallada para las pruebas fallidas. Además, puedes comprobar el estado de Cilium con `cilium status` y monitorear el tráfico en tiempo real con `cilium monitor`.
</details>

14. ¿Cuál es el identificador numérico que representa la identidad de seguridad de un Pod en Cilium?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Identity (o Security Identity, Cilium Identity)**

**Explicación:**
Cilium Identity es un identificador numérico generado según el conjunto de labels de un Pod. Todos los Pods con los mismos labels comparten la misma Identity. Este enfoque permite aplicar políticas de red mediante Identity en lugar de direcciones IP, de modo que las políticas permanecen coherentes incluso cuando cambian las IP de los Pods. Las políticas basadas en Identity son altamente escalables y funcionan de forma eficiente incluso en clústeres grandes.
</details>

15. ¿Cuál es la abreviatura del proyecto CNCF que define la interfaz estándar entre los runtimes de contenedores y los plugins de red?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: CNI (Container Network Interface)**

**Explicación:**
CNI (Container Network Interface) es un proyecto de CNCF que define la interfaz estándar entre los runtimes de contenedores y los plugins de red. En Kubernetes, kubelet se comunica con los plugins de red (Cilium, Calico, Flannel, etc.) mediante la interfaz de CNI. CNI define una API estándar para la configuración de red cuando se agregan o eliminan contenedores, y diversas soluciones de red pueden integrarse mediante una arquitectura de plugins.
</details>

## Preguntas prácticas

16. Escribe el comando para instalar Cilium 1.18.0 en un clúster de Kubernetes mediante la CLI de Cilium.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# Install Cilium CLI
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

**Explicación:**
Los comandos anteriores primero descargan e instalan el binario de la CLI de Cilium en `/usr/local/bin`. Luego, el comando `cilium install` instala la versión especificada de Cilium en el clúster de Kubernetes. Después de la instalación, verifica que todos los componentes se estén ejecutando correctamente con `cilium status` y valida la conectividad de red con `cilium connectivity test`. También es posible instalar mediante Helm, lo que permite opciones de configuración más granulares.
</details>

17. Escribe una CiliumNetworkPolicy que permita únicamente tráfico TCP desde el Pod frontend al puerto 8080 del Pod backend.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "allow-frontend-backend"
  namespace: default
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

**Explicación:**
Esta CiliumNetworkPolicy permite únicamente tráfico de entrada TCP por el puerto 8080 desde Pods con el label `app: frontend` hacia Pods con el label `app: backend`. El `endpointSelector` selecciona los Pods de destino a los que se aplica la política, y la sección `ingress` define el tráfico entrante permitido. `fromEndpoints` especifica los Pods de origen y `toPorts` especifica los puertos y protocolos permitidos. Cuando se aplica esta política, se bloqueará el tráfico de otros Pods hacia el backend.
</details>

18. Escribe el comando para instalar Cilium con el modo de reemplazo de kube-proxy habilitado y la configuración para habilitar el modo DSR (Direct Server Return).

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# Install Cilium with kube-proxy replacement and DSR mode
cilium install --version 1.18.0 \
  --set kubeProxyReplacement=true \
  --set loadBalancer.mode=dsr

# Or installation using Helm
helm install cilium cilium/cilium --version 1.18.0 \
  --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set loadBalancer.mode=dsr \
  --set k8sServiceHost=<API_SERVER_IP> \
  --set k8sServicePort=<API_SERVER_PORT>

# Verify installation
cilium status --verbose
```

**Explicación:**
La opción `kubeProxyReplacement=true` configura Cilium para reemplazar toda la funcionalidad de kube-proxy. En este modo, el kube-proxy existente debe eliminarse o deshabilitarse. `loadBalancer.mode=dsr` habilita el modo Direct Server Return, por lo que el tráfico de respuesta se envía directamente al cliente sin pasar por el balanceador de carga. El modo DSR elimina los cuellos de botella del balanceador de carga y ahorra ancho de banda, lo que resulta particularmente eficaz al gestionar respuestas grandes.
</details>

19. Escribe los comandos para comprobar el estado de Cilium, consultar información de endpoint de un Pod específico y ver las políticas de red aplicadas.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# Check overall Cilium status
cilium status

# Check detailed status (all components)
cilium status --verbose

# List all endpoints
cilium endpoint list

# Get detailed information for a specific endpoint (using endpoint ID)
cilium endpoint get <endpoint_id>

# Query endpoint by pod name
kubectl exec -n kube-system <cilium-agent-pod> -- cilium endpoint list | grep <pod-name>

# Query applied network policies
cilium policy get

# Query policies applied to a specific endpoint
cilium endpoint get <endpoint_id> -o json | jq '.status.policy'

# Real-time traffic monitoring
cilium monitor
```

**Explicación:**
`cilium status` muestra el estado de todos los componentes, incluidos Cilium Agent, Operator y Hubble. `cilium endpoint list` enumera todos los endpoints (Pods) en el nodo actual, donde puedes comprobar el ID, estado, labels e Identity de cada endpoint. `cilium policy get` consulta todas las políticas de red aplicadas en el clúster. `cilium monitor` monitorea el tráfico de red en tiempo real para comprobar flujos de paquetes, aplicación de políticas y paquetes descartados.
</details>

20. Escribe los comandos para habilitar Hubble y observar flujos de red mediante la CLI de Hubble.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# Install Cilium with Hubble enabled
cilium install --version 1.18.0 \
  --set hubble.enabled=true \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true

# Enable Hubble on existing Cilium
cilium hubble enable

# Install Hubble CLI
export HUBBLE_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/hubble/master/stable.txt)
curl -L --remote-name-all https://github.com/cilium/hubble/releases/download/$HUBBLE_VERSION/hubble-linux-amd64.tar.gz
sudo tar xzvfC hubble-linux-amd64.tar.gz /usr/local/bin
rm hubble-linux-amd64.tar.gz

# Hubble port forwarding
cilium hubble port-forward &

# Observe network flows
hubble observe

# Observe flows in a specific namespace
hubble observe --namespace default

# Observe flows for a specific pod
hubble observe --pod default/frontend

# Filter HTTP traffic only
hubble observe --protocol http

# Observe only dropped packets
hubble observe --verdict DROPPED

# Access Hubble UI (separate terminal)
cilium hubble ui
```

**Explicación:**
Hubble es la capa de observabilidad de Cilium que usa eBPF para monitorear flujos de red en tiempo real. `hubble.enabled=true` habilita Hubble y `hubble.relay.enabled=true` habilita Hubble Relay para recopilar flujos de todo el clúster. `hubble.ui.enabled=true` habilita la UI basada en web. El comando `hubble observe` proporciona diversas opciones de filtro para filtrar tráfico por namespace, Pod, protocolo, veredicto específicos y más.
</details>

---

[Volver a los materiales de aprendizaje](../../../networking/cilium/01-introduction.md) | [Siguiente cuestionario: conceptos básicos de eBPF](./02-ebpf-quiz.md)
