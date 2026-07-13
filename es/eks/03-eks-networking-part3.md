# Parte 3: Troubleshooting

## Descripción general

Este documento cubre la optimización del rendimiento, los métodos de troubleshooting y los casos de uso avanzados para Amazon EKS networking. Analizaremos cómo optimizar el rendimiento de red, resolver problemas comunes de networking y aprovechar funcionalidades avanzadas de networking.

![Optimización del rendimiento de red de EKS](../.gitbook/assets/network_performance_optimization.png)

## Optimización del rendimiento de red

Existen varias estrategias para optimizar el rendimiento de red en clusters de EKS.

![Optimización del rendimiento de red de EKS](../.gitbook/assets/network_performance_optimization.png)

### Selección del tipo de instance

El rendimiento de red varía significativamente según el tipo de instance. Para workloads intensivos en red, se recomienda elegir tipos de instance que soporten enhanced networking.

1. **Instances con soporte para Enhanced Networking**:
   * Los tipos de instance como C5, M5 y R5 soportan enhanced networking.
   * Estas instances proporcionan mayor bandwidth, menor latency y menor jitter.
2. **Network Bandwidth**:
   * Los tamaños de instance más grandes proporcionan mayor network bandwidth.
   * Por ejemplo, m5.large proporciona hasta 10Gbps, mientras que m5.24xlarge proporciona hasta 25Gbps de network bandwidth.
3. **Elastic Network Adapter (ENA)**:
   * ENA soporta network bandwidth de hasta 100Gbps.
   * La mayoría de los tipos de instance modernos soportan ENA.

### Modos de Cluster Networking

EKS soporta múltiples modos de networking, cada uno con diferentes características de rendimiento.

![Modos de EKS Networking](../.gitbook/assets/eks_networking_modes.png)

1. **AWS VPC CNI (Default)**:
   * Asigna direcciones IP de VPC directamente a los Pods.
   * Rendimiento excelente porque usa VPC networking nativo.
   * Cada node tiene un límite en la cantidad de direcciones IP que puede asignar.
2. **Custom Networking**:
   * Permite asignar direcciones IP desde subnets específicas a los Pods.
   * Puede ampliar el espacio de direcciones IP usando bloques CIDR secundarios.
   * Proporciona un control más preciso sobre la topología de red.
3. **Alternative CNI Plugins**:
   * Se pueden usar Alternative CNI plugins como Calico y Cilium.
   * Estos plugins proporcionan funcionalidades adicionales (por ejemplo, network policies, encryption), pero pueden tener overhead de rendimiento.

### Optimización de MTU

MTU (Maximum Transmission Unit) es un factor importante que afecta el rendimiento de red.

1. **Configuraciones de MTU por defecto**:
   * El MTU por defecto para AWS VPC CNI es 9001.
   * Algunas rutas de red pueden requerir un MTU más pequeño.
2. **Ajuste de MTU**:
   * La configuración de MTU de AWS VPC CNI se puede ajustar:

```bash
kubectl set env daemonset aws-node -n kube-system ENI_MTU=9001
```

3. **Jumbo Frames**:
   * Usar jumbo frames (MTU > 1500) puede mejorar el rendimiento de red.
   * Todos los componentes de red, incluidos VPC, subnets, security groups y load balancers, deben soportar jumbo frames.

### Optimización de TCP

La configuración de TCP se puede optimizar para mejorar el rendimiento de red.

1. **TCP Early Demux**:
   * TCP early demux puede mejorar el rendimiento, pero puede causar problemas en algunos modos de networking.
   * Se puede deshabilitar si es necesario:

```bash
kubectl set env daemonset aws-node -n kube-system DISABLE_TCP_EARLY_DEMUX=true
```

2. **Configuración de TCP Keepalive**:
   * La configuración de TCP keepalive se puede ajustar para optimizar el mantenimiento y la reutilización de conexiones.
   * Esto es particularmente útil para workloads que manejan muchas conexiones cortas.

```bash
# System-level TCP keepalive settings
sysctl -w net.ipv4.tcp_keepalive_time=60
sysctl -w net.ipv4.tcp_keepalive_intvl=15
sysctl -w net.ipv4.tcp_keepalive_probes=6
```

3. **Tamaño del TCP Buffer**:
   * El tamaño del TCP buffer se puede ajustar para optimizar el throughput.
   * Se recomienda configurar el tamaño del buffer de acuerdo con el Bandwidth Delay Product (BDP).

```bash
# System-level TCP buffer settings
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.wmem_max=16777216
sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216"
sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216"
```

### Ubicación y localidad de Nodes

El rendimiento de red se puede mejorar optimizando la ubicación y la localidad de los nodes.

![Optimización de ubicación y localidad de Nodes](../.gitbook/assets/node_placement_locality.png)

1. **Localidad de Availability Zone**:
   * Coloca Pods que se comunican con frecuencia en la misma Availability Zone para reducir la latency.
   * Usa pod affinity y anti-affinity para controlar la ubicación de los Pods.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      affinity:
        podAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - cache
              topologyKey: topology.kubernetes.io/zone
```

2. **Localidad de Node**:
   * Coloca Pods que se comunican con frecuencia en el mismo node para reducir los network hops.
   * Esto es particularmente útil para aplicaciones sensibles a la latency.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      affinity:
        podAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - cache
              topologyKey: kubernetes.io/hostname
```

3. **Topology Aware Hints**:
   * Usa topology aware hints para mantener el tráfico del Service dentro de la misma zone.
   * Esto reduce los costos de data transfer entre Availability Zones y mejora la latency.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    service.kubernetes.io/topology-aware-hints: "auto"
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

### Optimización de Network Policy

Las network policies mejoran la seguridad, pero pueden afectar el rendimiento.

1. **Minimizar el número de policies**:
   * Aplica solo las network policies mínimas necesarias.
   * Demasiadas policies pueden causar degradación del rendimiento.
2. **Optimizar el alcance de las policies**:
   * Usa policies específicas en lugar de policies amplias.
   * Usa label selectors para limitar el alcance de las policies.
3. **Considerar el orden de evaluación de policies**:
   * Las network policies se evalúan de forma acumulativa.
   * Define primero las reglas usadas con más frecuencia para optimizar el rendimiento de la evaluación.

## Troubleshooting de Networking

Exploremos los problemas comunes de networking que pueden ocurrir en clusters de EKS y cómo resolverlos.

![Troubleshooting de EKS Networking](../.gitbook/assets/networking_troubleshooting.png)

### Problemas de Pod Networking

![Problemas de Pod Networking](../.gitbook/assets/pod_networking_issues.png)

1. **Fallo en la asignación de IP de Pod**:
   * Síntoma: El Pod queda atascado en estado `ContainerCreating`
   * Causa: El node no tiene suficientes direcciones IP disponibles
   * Solución:
     * Verificar el estado del node: `kubectl describe node <node-name>`
     * Verificar los logs de AWS VPC CNI: `kubectl logs -n kube-system -l k8s-app=aws-node`
     * Aumentar WARM\_IP\_TARGET: `kubectl set env daemonset aws-node -n kube-system WARM_IP_TARGET=10`
     * Actualizar el tipo de instance del node: Cambiar a un tipo de instance que soporte más ENIs y direcciones IP
2. **Problemas de comunicación Pod-to-Pod**:
   * Síntoma: El Pod no puede comunicarse con otros Pods
   * Causa: Network policies, security groups, problemas de routing, etc.
   * Solución:
     * Verificar network policies: `kubectl get networkpolicy`
     * Verificar reglas de security group: Usar AWS console o AWS CLI
     * Probar la conectividad de red desde dentro del Pod:

```bash
kubectl exec -it <pod-name> -- ping <target-pod-ip>
kubectl exec -it <pod-name> -- curl <target-service-name>
kubectl exec -it <pod-name> -- traceroute <target-pod-ip>
```

3. **Problemas de resolución DNS**:
   * Síntoma: El Pod no puede resolver nombres de Service
   * Causa: Problemas de CoreDNS, network policies, security groups, etc.
   * Solución:
     * Verificar el estado del Pod de CoreDNS: `kubectl get pods -n kube-system -l k8s-app=kube-dns`
     * Verificar logs de CoreDNS: `kubectl logs -n kube-system -l k8s-app=kube-dns`
     * Verificar configuración de DNS: `kubectl exec -it <pod-name> -- cat /etc/resolv.conf`
     * Probar consultas DNS:

```bash
kubectl exec -it <pod-name> -- nslookup kubernetes.default.svc.cluster.local
kubectl exec -it <pod-name> -- dig kubernetes.default.svc.cluster.local
```

### Problemas de Service y Load Balancing

![Problemas de Service y Load Balancer](../.gitbook/assets/service_loadbalancer_issues.png)

1. **Problemas de conexión de Service**:
   * Síntoma: No se puede conectar a los Pods a través del Service
   * Causa: Selector del Service, estado del Pod, endpoints, etc.
   * Solución:
     * Verificar el estado del Service: `kubectl describe service <service-name>`
     * Verificar endpoints: `kubectl get endpoints <service-name>`
     * Verificar el estado del Pod: `kubectl get pods -l <selector-label>`
     * Verificar DNS del Service: `kubectl exec -it <pod-name> -- nslookup <service-name>`
2. **Problemas de Load Balancer**:
   * Síntoma: No se puede conectar al load balancer desde el exterior
   * Causa: Security groups, subnet tags, health checks, etc.
   * Solución:
     * Verificar el estado del load balancer: Usar AWS console o AWS CLI
     * Verificar reglas de security group: Confirmar que el inbound traffic esté permitido
     * Verificar subnet tags: Confirmar que existan los tags adecuados
     * Verificar la configuración de health check: Ruta de health check, port, etc.
3. **Problemas de Ingress**:
   * Síntoma: No se puede conectar al Service a través de Ingress
   * Causa: Ingress controller, annotations, certificates, etc.
   * Solución:
     * Verificar el estado de Ingress: `kubectl describe ingress <ingress-name>`
     * Verificar logs del Ingress controller: `kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller`
     * Verificar el estado de ALB: Usar AWS console o AWS CLI
     * Verificar el estado del target group: Confirmar que los targets estén healthy

## Quiz

Para comprobar lo que has aprendido en este capítulo, intenta el [quiz del tema](../quizzes/eks/03-eks-networking-part3-quiz.md).
