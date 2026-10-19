# Administración de clústeres de Kubernetes

> **Versiones compatibles**: soporte estándar de EKS para Kubernetes 1.34–1.37 (verificado el 12 de octubre de 2026)
> **Última actualización**: 16 de octubre de 2026

La administración de clústeres de Kubernetes es una tarea importante que incluye la configuración, el mantenimiento, la supervisión, la solución de problemas y las actualizaciones del clúster. En este capítulo, exploraremos diversos aspectos de la administración de clústeres de Kubernetes y las prácticas recomendadas para la gestión de clústeres en Amazon EKS.

Las operaciones de kubeadm autogestionadas y las operaciones del servicio EKS son distintas. EKS no expone los hosts del plano de control, los manifiestos de Pod estáticos ni el acceso directo a etcd. Considera los bloques siguientes como ejemplos independientes, no como un único script que se debe ejecutar en secuencia. Comprueba el soporte del proyecto original de Kubernetes y la compatibilidad de los complementos con la versión real del clúster.

## Conceptos básicos

- **Gestión del ciclo de vida del clúster**: todo el proceso, desde la creación del clúster hasta su retirada
- **Gestión del plano de control**: gestión de componentes principales como el servidor de API, el planificador y el administrador de controladores
- **Gestión de nodos**: incorporación, eliminación y mantenimiento de nodos de trabajo
- **Asignación de recursos**: configuración de la asignación y los límites de recursos para CPU, memoria, almacenamiento, etc.
- **Estrategia de actualización**: estrategias de actualización del clúster y las aplicaciones para minimizar el tiempo de inactividad

## Tabla de contenido
1. [Descripción general de la administración de clústeres](#cluster-administration-overview)
2. [Gestión de los componentes del clúster](#cluster-component-management)
3. [Gestión de recursos](#resource-management)
4. [Redes del clúster](#cluster-networking)
5. [Gestión de la autenticación y la autorización](#authentication-and-authorization-management)
6. [Actualizaciones del clúster](#cluster-upgrades)
7. [Copia de seguridad y recuperación](#backup-and-recovery)
8. [Supervisión y registro](#monitoring-and-logging)
9. [Solución de problemas](#troubleshooting)
10. [Administración de clústeres de Amazon EKS](#amazon-eks-cluster-administration)
11. [Prácticas recomendadas para la administración de clústeres](#cluster-administration-best-practices)
12. [Conclusión](#conclusion)

## Configuración del entorno

Se necesitan las siguientes herramientas para administrar clústeres:

Usa la [guía oficial de instalación de kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/) y mantén una diferencia máxima de una versión menor entre kubectl y el servidor de API. Para clústeres autogestionados, instala kubeadm/kubelet desde el repositorio `pkgs.k8s.io` de la versión menor de destino; los ejemplos antiguos de paquetes `1.x.y-00` ya no son válidos. Antes de la instalación, selecciona una versión exacta del paquete del repositorio configurado.

Instala Helm y k9s siguiendo las [instrucciones oficiales de Helm](https://helm.sh/docs/intro/install/) y las [versiones de k9s](https://github.com/derailed/k9s/releases); comprueba la arquitectura de la plataforma y las sumas de comprobación. La administración de EKS también requiere una CLI de AWS autenticada y una versión compatible de eksctl.

```bash
kubectl version --client
helm version
k9s version
# Self-managed nodes only, after configuring the target minor repository:
apt-cache madison kubeadm
```


## Descripción general de la administración de clústeres {#cluster-administration-overview}

La administración de clústeres de Kubernetes es el proceso de gestionar todo el ciclo de vida de un clúster. Esto incluye las siguientes áreas principales:

1. **Configuración del clúster**: creación del clúster, incorporación de nodos, configuración de redes, configuración del almacenamiento, etc.
2. **Gestión de operaciones**: supervisión de recursos, optimización del rendimiento, planificación de capacidad y solución de problemas
3. **Gestión de la seguridad**: autenticación, autorización, políticas de red, contextos de seguridad, etc.
4. **Actualizaciones y parches**: actualizaciones de la versión del clúster y aplicación de parches de seguridad
5. **Copia de seguridad y recuperación**: copias de seguridad de los datos del clúster y planificación de la recuperación ante desastres

El diagrama siguiente muestra las principales áreas de la administración de clústeres de Kubernetes y las herramientas relacionadas:

## Gestión de los componentes del clúster {#cluster-component-management}

Un clúster de Kubernetes consta de componentes del plano de control y componentes de los nodos. La gestión de cada componente es fundamental para la estabilidad y el rendimiento del clúster.

### Gestión de los componentes del plano de control

![Diagrama de árbol que muestra el plano de control de Kubernetes ramificándose en sus cinco componentes (servidor de API, etcd, planificador, administrador de controladores y administrador de controladores de nube), cada uno asociado con el aspecto operativo de su responsabilidad: autenticación y autorización, copia de seguridad de datos, políticas de planificación, supervisión del estado de los controladores y gestión de recursos de la nube.](../.gitbook/assets/en-core-09-cluster-administration-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-0.html)

#### Gestión del servidor de API

El servidor de API es un componente básico del plano de control que expone la API de Kubernetes.

```bash
# Check API server logs
kubectl logs -n kube-system kube-apiserver-<master-node-name>

# Check API server configuration (kubeadm cluster)
sudo cat /etc/kubernetes/manifests/kube-apiserver.yaml

# Check API server status
kubectl get --raw='/readyz?verbose'
```

#### Gestión de etcd

etcd es un almacén distribuido de clave-valor que guarda el estado de la API de Kubernetes.

```bash
# etcd backup
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d).db

# Check etcd status
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint health
```

### Gestión de nodos

Los nodos son máquinas de trabajo que ejecutan aplicaciones en contenedores.

```bash
# List nodes
kubectl get nodes

# Check node detailed information
kubectl describe node <node-name>

# Add node label
kubectl label node <node-name> environment=production

# Set node to maintenance mode
kubectl drain <node-name> --ignore-daemonsets

# Return node after maintenance
kubectl uncordon <node-name>
```

### Supervisión del estado de los componentes

```bash
# Check control plane component status
kubectl get --raw='/readyz?verbose'

# Check system pod status
kubectl get pods -n kube-system

# Check node resource usage
kubectl top nodes
```

![Diagrama que muestra las cinco áreas de responsabilidad de un administrador de clústeres, cada una asociada con las herramientas utilizadas para llevarla a cabo.](../.gitbook/assets/en-core-09-cluster-administration-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-1.html)

### Herramientas para administrar clústeres

Hay varias herramientas disponibles para administrar clústeres de Kubernetes:

1. **kubectl**: herramienta de línea de comandos para interactuar con clústeres de Kubernetes
2. **kubeadm**: herramienta para crear y administrar clústeres de Kubernetes
3. **kops**: herramienta para crear, actualizar y administrar clústeres de Kubernetes
4. **eksctl**: herramienta para crear y administrar clústeres de Amazon EKS
5. **Helm**: gestor de paquetes para aplicaciones de Kubernetes
6. **Headlamp**: interfaz web de Kubernetes; el antiguo proyecto Kubernetes Dashboard está archivado
7. **Prometheus y Grafana**: herramientas de supervisión y alertas
8. **Fluentd y Elasticsearch**: herramientas de registro

## Gestión de los componentes del clúster

Un clúster de Kubernetes consta de varios componentes, y gestionarlos de manera eficaz es importante.

### Componentes del plano de control

Los componentes del plano de control administran el estado general del clúster:

1. **kube-apiserver**: componente que expone la API de Kubernetes
2. **etcd**: almacén de clave-valor que guarda los datos del clúster
3. **kube-scheduler**: componente que asigna Pods a los nodos
4. **kube-controller-manager**: componente que ejecuta controladores
5. **cloud-controller-manager**: componente que interactúa con los proveedores de nube

El diagrama siguiente muestra los componentes del plano de control de Kubernetes y sus interacciones:

![Diagrama de arquitectura que muestra etcd, kube-scheduler, kube-controller-manager y cloud-controller-manager comunicándose bidireccionalmente con kube-apiserver, situado en el centro, y kubelet de un nodo de trabajo comunicándose bidireccionalmente con el servidor de API mientras utiliza el entorno de ejecución de contenedores; kube-proxy observa de forma independiente el estado de Service/EndpointSlice.](../.gitbook/assets/en-core-09-cluster-administration-2.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-2.html)

#### Supervisión de los componentes del plano de control

Es importante supervisar el estado de los componentes del plano de control:

```bash
# Check control plane component status
kubectl get --raw='/readyz?verbose'

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check etcd status
kubectl exec -n kube-system etcd-<node-name> -- etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key endpoint health
```

#### Configuración de los componentes del plano de control

El manifiesto siguiente es solo un fragmento de opciones y configuración. Omite la red del host, los montajes de certificados y otros parámetros generados por kubeadm; no sustituyas el manifiesto del plano de control en ejecución por este fragmento. Asegúrate de que la imagen coincida con el plan de actualización del clúster.

Cómo gestionar la configuración de los componentes del plano de control:

```yaml
# kube-apiserver configuration example
apiVersion: v1
kind: Pod
metadata:
  name: kube-apiserver
  namespace: kube-system
spec:
  containers:
  - command:
    - kube-apiserver
    - --advertise-address=192.168.1.10
    - --allow-privileged=true
    - --authorization-mode=Node,RBAC
    - --client-ca-file=/etc/kubernetes/pki/ca.crt
    - --enable-admission-plugins=NodeRestriction
    - --enable-bootstrap-token-auth=true
    - --etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt
    - --etcd-certfile=/etc/kubernetes/pki/apiserver-etcd-client.crt
    - --etcd-keyfile=/etc/kubernetes/pki/apiserver-etcd-client.key
    - --etcd-servers=https://127.0.0.1:2379
    - --kubelet-client-certificate=/etc/kubernetes/pki/apiserver-kubelet-client.crt
    - --kubelet-client-key=/etc/kubernetes/pki/apiserver-kubelet-client.key
    - --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname
    - --secure-port=6443
    - --service-account-key-file=/etc/kubernetes/pki/sa.pub
    - --service-account-signing-key-file=/etc/kubernetes/pki/sa.key
    - --service-account-issuer=https://kubernetes.default.svc.cluster.local
    - --service-cluster-ip-range=10.96.0.0/12
    - --tls-cert-file=/etc/kubernetes/pki/apiserver.crt
    - --tls-private-key-file=/etc/kubernetes/pki/apiserver.key
    image: registry.k8s.io/kube-apiserver:v1.36.5
    name: kube-apiserver
```

### Componentes de los nodos

Los componentes de los nodos se ejecutan en cada nodo y administran los Pods:

1. **kubelet**: agente que se ejecuta en cada nodo y se asegura de que los Pods y los contenedores estén en ejecución
2. **kube-proxy**: mantiene las reglas de red y gestiona el reenvío de conexiones
3. **Entorno de ejecución de contenedores**: software que ejecuta contenedores (containerd, CRI-O o Docker Engine con un adaptador CRI externo)

#### Gestión de nodos

Comandos clave para administrar nodos:

```bash
# List nodes
kubectl get nodes

# Check node detailed information
kubectl describe node <node-name>

# Add node label
kubectl label node <node-name> key=value

# Add node taint
kubectl taint node <node-name> key=value:NoSchedule

# Set node to maintenance mode
kubectl cordon <node-name>

# Drain node
kubectl drain <node-name> --ignore-daemonsets
```

El vaciado del nodo (drain) puede detenerse ante Pods independientes, PDB o datos locales. Investiga la causa en lugar de añadir `--force` o `--delete-emptydir-data` de forma predeterminada; esta última opción autoriza explícitamente la pérdida de datos de emptyDir. Espera a que finalice el vaciado y comprueba el estado de las cargas de trabajo antes del mantenimiento.

#### Solución de problemas de nodos

Comandos para solucionar problemas de nodos:

```bash
# Check node status
kubectl describe node <node-name> | grep Conditions -A 10

# Check node resource usage
kubectl top node <node-name>

# Check kubelet logs
journalctl -u kubelet

# Check container runtime status
systemctl status docker  # When using Docker
systemctl status containerd  # When using containerd
```

## Gestión de recursos {#resource-management}

Gestionar eficazmente los recursos de un clúster de Kubernetes es importante para mantener su estabilidad y rendimiento.

### Gestión de namespaces

Usa un namespace desechable para practicar las operaciones del ciclo de vida. Al eliminar un namespace, se eliminan sus recursos con ámbito de namespace; primero inspecciona y haz una copia de seguridad de los datos necesarios. `get all` solo muestra un subconjunto de las cargas de trabajo.

```bash
kubectl create namespace admin-demo
kubectl get all -n admin-demo
# Cleanup only the disposable exercise namespace:
kubectl delete namespace admin-demo
```

### Cuotas de recursos

Las cuotas de recursos limitan el uso de recursos por namespace:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-resources
  namespace: dev
spec:
  hard:
    requests.cpu: "1"
    requests.memory: 1Gi
    limits.cpu: "2"
    limits.memory: 2Gi
    pods: "10"
```

En el ejemplo anterior, el namespace `dev` puede tener un máximo de 10 Pods, solicitudes de 1 CPU y 1Gi de memoria, y límites de 2 CPU y 2Gi de memoria.

### Rangos de límites

Los rangos de límites establecen valores predeterminados y límites para recursos individuales dentro de un namespace:

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: limit-range
  namespace: dev
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 200m
      memory: 256Mi
    max:
      cpu: 1
      memory: 1Gi
    min:
      cpu: 100m
      memory: 128Mi
    type: Container
```

En el ejemplo anterior, todos los contenedores del namespace `dev` tienen límites predeterminados de 500m de CPU y 512Mi de memoria, solicitudes predeterminadas de 200m de CPU y 256Mi de memoria, máximos de 1 CPU y 1Gi de memoria, y mínimos de 100m de CPU y 128Mi de memoria.

### Horizontal Pod Autoscaler (HPA)

HPA ajusta automáticamente el número de Pods según el uso de CPU o métricas personalizadas:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

En el ejemplo anterior, el Deployment `frontend` tiene como objetivo una utilización media de CPU del 80 % de la CPU solicitada, sujeta a tolerancias, métricas ausentes, ventanas de estabilización y políticas de escalado. Mantiene un mínimo de 2 réplicas y un máximo de 10.

### Vertical Pod Autoscaler (VPA)

VPA ajusta automáticamente las solicitudes de CPU y memoria de los Pods:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: frontend-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  updatePolicy:
    updateMode: "Recreate"
```

En el ejemplo anterior, las solicitudes de CPU y memoria de los Pods del Deployment `frontend` se ajustan automáticamente según el uso real de recursos.

## Redes del clúster {#cluster-networking}

Las redes del clúster de Kubernetes gestionan la comunicación entre Pods, Services y nodos.

### Modelo de red del clúster

Requisitos básicos del modelo de red de Kubernetes:

1. Todos los Pods pueden comunicarse con los demás sin NAT
2. Los agentes de nodo (kubelet) pueden comunicarse con todos los Pods de ese nodo
3. La conectividad externa depende del enrutamiento y de la política de salida; no existe un requisito universal de modo NAT para los Pod

El diagrama siguiente muestra los componentes de red de Kubernetes y los flujos de comunicación:

![Diagrama de arquitectura que muestra el tráfico de cliente entrando mediante Ingress a un Service que distribuye la carga entre dos Pods en nodos distintos; estos se comunican entre sí y acceden a un servicio externo.](../.gitbook/assets/en-core-09-cluster-administration-3.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-3.html)

### Complementos CNI (Container Network Interface)

Kubernetes implementa las redes mediante complementos CNI. Algunos complementos CNI comunes son:

1. **Calico**: CNI con funciones mejoradas de políticas de red y seguridad
2. **Flannel**: proporciona redes overlay sencillas
3. **Cilium**: solución de redes y seguridad basada en eBPF
4. **AWS VPC CNI**: CNI integrado con AWS VPC
5. **Weave Net (histórico)**: está archivado; para instalaciones nuevas, elige una alternativa mantenida

#### Instalación y configuración de complementos CNI

Ejemplo de instalación de un complemento CNI (Calico):

Elige un único CNI o una configuración documentada de encadenamiento/migración. Las alternativas Calico, Flannel y Cilium no deben instalarse secuencialmente en el mismo clúster en ejecución. Usa una versión compatible y fijada, y sigue las instrucciones específicas del proveedor; en EKS, sigue el procedimiento del VPC CNI o de la alternativa CNI planificada en el [capítulo de redes](./03-services-networking.md).

```bash
# Inspect the installed networking components before making changes
kubectl get daemonsets -A
kubectl get pods -A -l k8s-app=calico-node
```


### Redes de Service

Los Service de Kubernetes proporcionan puntos de conexión estables para conjuntos de Pods:

1. **ClusterIP**: Service accesible solo dentro del clúster
2. **NodePort**: Service accesible mediante un puerto específico en todos los nodos
3. **LoadBalancer**: Service accesible mediante un balanceador de carga externo
4. **ExternalName**: proporciona un registro CNAME para servicios externos

#### Configuración del CIDR de Service

El CIDR de Service define el rango de direcciones IP del Service:

```bash
# Set service CIDR in kube-apiserver configuration
--service-cluster-ip-range=10.96.0.0/12
```

### Gestión de CoreDNS

CoreDNS proporciona servicios DNS para Kubernetes:

```bash
# Check CoreDNS status
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Check CoreDNS configuration
kubectl get configmap -n kube-system coredns -o yaml
```

Ejemplo de configuración de CoreDNS:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
           lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
           pods insecure
           fallthrough in-addr.arpa ip6.arpa
           ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

### Políticas de red

Las políticas de red controlan la comunicación entre Pods:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      role: db
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 3306
  egress:
  - to:
    - podSelector:
        matchLabels:
          role: monitoring
    ports:
    - protocol: TCP
      port: 9090
```

En el ejemplo anterior, los Pods con la etiqueta `role=db` solo permiten el tráfico entrante TCP por el puerto 3306 desde Pods con la etiqueta `role=frontend`, y el tráfico saliente TCP por el puerto 9090 hacia Pods con la etiqueta `role=monitoring`.

## Gestión de la autenticación y la autorización {#authentication-and-authorization-management}

La gestión de la autenticación y la autorización de Kubernetes es un elemento fundamental de la seguridad del clúster.

El diagrama siguiente muestra el flujo de autenticación y autorización de Kubernetes:

![Diagrama de arquitectura que muestra una solicitud pasando por las fases de autenticación, autorización y control de admisión dentro del servidor de API, junto con los métodos de autenticación y los modos de autorización concretos que admite cada fase.](../.gitbook/assets/en-core-09-cluster-administration-4.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-4.html)

### Autenticación

Kubernetes admite varios métodos de autenticación:

1. **Certificados X.509**: autenticación mediante certificados de cliente
2. **Tokens de ServiceAccount**: tokens JWT asociados a cuentas de servicio
3. **OpenID Connect (OIDC)**: autenticación mediante proveedores de identidad externos
4. **Autenticación de tokens mediante webhook**: verificación de tokens mediante servicios externos
5. **Proxy de autenticación**: procesamiento de solicitudes mediante un proxy de autenticación

#### Gestión de certificados X.509

Creación y gestión de certificados X.509:

```bash
# Generate a protected private key and CSR
umask 077
openssl genrsa -out user.key 2048
openssl req -new -key user.key -out user.csr -subj "/CN=user/O=group"

# Submit CSR to Kubernetes
cat <<EOF | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: user-csr
spec:
  request: $(cat user.csr | base64 | tr -d '\n')
  signerName: kubernetes.io/kube-apiserver-client
  usages:
  - client auth
EOF

# Approve CSR
kubectl certificate approve user-csr
kubectl wait --for=jsonpath='{.status.certificate}' csr/user-csr --timeout=60s

# Get certificate
kubectl get csr user-csr -o jsonpath='{.status.certificate}' | base64 --decode > user.crt
```

#### Configuración de la autenticación OIDC

Ejemplo de configuración de la autenticación OIDC:

```bash
# Add OIDC flags to kube-apiserver configuration
--oidc-issuer-url=https://accounts.google.com
--oidc-client-id=kubernetes
--oidc-username-claim=email
--oidc-groups-claim=groups
```

### Autorización

Kubernetes admite varios modos de autorización:

1. **RBAC (Role-Based Access Control)**: control de acceso basado en roles
2. **ABAC (Attribute-Based Access Control)**: control de acceso basado en atributos
3. **Node**: autorización de nodos
4. **Webhook**: autorización mediante servicios externos

#### Configuración de RBAC

RBAC es el mecanismo de autorización más común:

```yaml
# Role example
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]

# RoleBinding example
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: user
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

En el ejemplo anterior, `user` tiene permiso para ver Pods en el namespace `default`.

#### ClusterRole y ClusterRoleBinding

Gestiona los permisos para los recursos de todo el clúster:

```yaml
# ClusterRole example
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: node-reader
rules:
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "watch", "list"]

# ClusterRoleBinding example
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-nodes
subjects:
- kind: User
  name: user
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: node-reader
  apiGroup: rbac.authorization.k8s.io
```

En el ejemplo anterior, `user` tiene permiso para ver todos los nodos del clúster.

### Gestión de ServiceAccount

Las cuentas de servicio (ServiceAccount) permiten que los Pods se comuniquen con el servidor de API:

```yaml
# Create service account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default

# Grant permissions to service account
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: my-service-account-binding
  namespace: default
subjects:
- kind: ServiceAccount
  name: my-service-account
  namespace: default
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io

# Use service account in pod
---
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  serviceAccountName: my-service-account
  containers:
  - name: my-container
    image: nginx
```

### Contexto de seguridad

El contexto de seguridad define los permisos y el control de acceso de Pods y contenedores:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: security-context-pod
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: security-context-container
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      readOnlyRootFilesystem: true
```

En el ejemplo anterior, el pod se ejecuta con UID 1000 y GID 3000, y el contenedor no puede escalar privilegios, tiene deshabilitadas todas las capacidades de Linux y tiene el sistema de archivos raíz montado en modo de solo lectura.

## Actualizaciones del clúster {#cluster-upgrades}

Las actualizaciones de clústeres de Kubernetes son necesarias para aplicar nuevas funciones, mejoras de rendimiento y parches de seguridad.

El diagrama siguiente muestra el proceso de actualización de un clúster de Kubernetes:

![Diagrama de flujo de una actualización de clúster de Kubernetes: planificación y comprobación de compatibilidad de versiones, copia de seguridad de etcd, actualización y prueba funcional del primer nodo del plano de control, actualización del resto de los nodos del plano de control y de trabajo, y validación final del clúster; si la validación detecta un problema, hay una ruta de reversión que restaura la copia de seguridad.](../.gitbook/assets/en-core-09-cluster-administration-5.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-5.html)

### Planificación de la actualización

Consideraciones para planificar las actualizaciones del clúster:

1. **Compatibilidad de versiones**: comprueba la compatibilidad entre las versiones de Kubernetes
2. **Ruta de actualización**: comprueba las rutas de actualización compatibles
3. **Tiempo de inactividad**: planifica el tiempo de inactividad previsto durante la actualización
4. **Plan de reversión**: prepara un plan de reversión por si surgen problemas
5. **Impacto en las aplicaciones**: evalúa el impacto de las actualizaciones en las aplicaciones

### Actualización del plano de control

Actualización del plano de control con kubeadm:

Sigue el [procedimiento de actualización de kubeadm específico para cada versión](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/). Habilita el repositorio pkgs.k8s.io de la versión menor de destino y selecciona una versión de paquete publicada concreta; actualiza una versión menor cada vez.

1. Haz una copia de seguridad de etcd y valida la compatibilidad de las cargas de trabajo y los complementos. En el primer nodo del plano de control, actualiza kubeadm, ejecuta `kubeadm upgrade plan` y, a continuación, `kubeadm upgrade apply <target-version>`.
2. En los demás nodos del plano de control, actualiza kubeadm y ejecuta `kubeadm upgrade node`.
3. Vacía cada nodo (drain) antes de actualizar kubelet. Si el vaciado falla, detén el procedimiento y resuelve la causa. Actualiza kubelet/kubectl a versiones compatibles, vuelve a cargar systemd, reinicia kubelet, comprueba que el nodo esté Ready y que las cargas de trabajo estén sanas y, después, habilita de nuevo la asignación de Pods al nodo (uncordon) desde un cliente administrativo.
4. En cada nodo de trabajo, actualiza kubeadm y ejecuta `kubeadm upgrade node`; después, realiza la secuencia de vaciado, actualización de kubelet, verificación y habilitación de nuevas asignaciones. No ejecutes una actualización genérica de todo el sistema como sustituto del procedimiento de Kubernetes específico para cada versión.

Ejecuta los comandos en el nodo o cliente administrativo identificado explícitamente; una secuencia de sesiones `ssh` anidadas no es un script de automatización multinodo.

### Actualización de nodos de trabajo

Proceso de actualización de nodos de trabajo:

Sigue el [procedimiento de actualización de kubeadm específico para cada versión](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/). Habilita el repositorio pkgs.k8s.io de la versión menor de destino y selecciona una versión de paquete publicada concreta; actualiza una versión menor cada vez.

1. Haz una copia de seguridad de etcd y valida la compatibilidad de las cargas de trabajo y los complementos. En el primer nodo del plano de control, actualiza kubeadm, ejecuta `kubeadm upgrade plan` y, a continuación, `kubeadm upgrade apply <target-version>`.
2. En los demás nodos del plano de control, actualiza kubeadm y ejecuta `kubeadm upgrade node`.
3. Vacía cada nodo (drain) antes de actualizar kubelet. Si el vaciado falla, detén el procedimiento y resuelve la causa. Actualiza kubelet/kubectl a versiones compatibles, vuelve a cargar systemd, reinicia kubelet, comprueba que el nodo esté Ready y que las cargas de trabajo estén sanas y, después, habilita de nuevo la asignación de Pods al nodo (uncordon) desde un cliente administrativo.
4. En cada nodo de trabajo, actualiza kubeadm y ejecuta `kubeadm upgrade node`; después, realiza la secuencia de vaciado, actualización de kubelet, verificación y habilitación de nuevas asignaciones. No ejecutes una actualización genérica de todo el sistema como sustituto del procedimiento de Kubernetes específico para cada versión.

Ejecuta los comandos en el nodo o cliente administrativo identificado explícitamente; una secuencia de sesiones `ssh` anidadas no es un script de automatización multinodo.

### Verificación de la actualización

Verifica el estado del clúster después de la actualización:

```bash
# Check node versions
kubectl get nodes

# Check component status
kubectl get --raw='/readyz?verbose'

# Check pod status
kubectl get pods --all-namespaces

# Test cluster functionality
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80
kubectl get svc nginx
```
## Copia de seguridad y recuperación {#backup-and-recovery}

La copia de seguridad y recuperación de un clúster de Kubernetes es una parte importante de la planificación de recuperación ante desastres.

El diagrama siguiente muestra el proceso de copia de seguridad y recuperación de un clúster de Kubernetes:

![Diagrama de arquitectura que muestra las instantáneas programadas de etcd y las copias de seguridad de recursos en YAML guardándose en el almacenamiento de copias de seguridad, que más adelante se utiliza para restaurar etcd y los recursos durante la recuperación ante desastres.](../.gitbook/assets/en-core-09-cluster-administration-6.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-6.html)

### Copia de seguridad de etcd

etcd almacena toda la información de estado del clúster de Kubernetes, por lo que es importante realizar copias de seguridad periódicas:

```bash
# Create etcd snapshot
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d-%H-%M-%S).db

# Check snapshot status
etcdutl snapshot status --write-out=table /backup/etcd-snapshot-2023-01-01-12-00-00.db
```

### Recuperación de etcd

Restauración desde una instantánea de etcd:

Para la recuperación ante desastres de un clúster autogestionado, detén todos los servidores de API y los procesos de etcd afectados mediante el procedimiento operativo específico de la distribución. Detener solo kubelet deja en ejecución los contenedores de los Pod estáticos existentes. Restaura en un directorio nuevo con una versión compatible de etcdutl; conserva los datos originales hasta verificar la recuperación. Este comando ilustra la restauración de un solo miembro; una restauración de alta disponibilidad con varios miembros requiere un procedimiento propio:

```bash
etcdutl snapshot status "$SNAPSHOT_FILE" --write-out=table
etcdutl snapshot restore "$SNAPSHOT_FILE" \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-1 \
  --initial-cluster=etcd-1=https://127.0.0.1:2380 \
  --initial-cluster-token=restored-cluster \
  --initial-advertise-peer-urls=https://127.0.0.1:2380 \
  --bump-revision=1000000000 --mark-compacted
```

Establece SNAPSHOT_FILE en la instantánea verificada. Para alta disponibilidad, restaura la misma instantánea en cada miembro con un nombre y una URL de comunicación únicos para ese miembro, y con la misma lista completa de miembros. Elige un incremento de revisión que supere los cambios realizados desde la instantánea. Actualiza el manifiesto/servicio de etcd para que apunte a la ruta restaurada, con el propietario y los certificados correctos; verifica el cuórum y el estado y, después, reinicia los servidores de API y los controladores. Consulta la [guía oficial de recuperación](https://etcd.io/docs/v3.6/op-guide/recovery/). Los usuarios de EKS no pueden restaurar directamente etcd del plano de control administrado.

### Copia de seguridad de recursos

Estas exportaciones son inventarios protegidos, no un plan completo para restaurar el clúster en otro entorno. Incluyen Secrets, requieren permisos restringidos y cifrado y no incluyen los datos de PV. Usa `umask 077` y comprueba si falla algún comando; restaura las CRD y sus dependencias en el orden adecuado y elimina los metadatos administrados por el servidor cuando corresponda. `kubectl get all` solo devuelve un subconjunto de tipos de recursos.

Haz copias de seguridad de los recursos de Kubernetes como archivos YAML:

```bash
# Export listable resources (includes sensitive Secrets)
set -eu
umask 077
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  mkdir -p /backup/resources/$ns
  for resource in $(kubectl api-resources --verbs=list --namespaced=true -o name); do
    kubectl get -n "$ns" "$resource" -o yaml > "/backup/resources/$ns/$resource.yaml"
  done
done

# Backup cluster-scoped resources
mkdir -p /backup/resources/cluster-scoped
for resource in $(kubectl api-resources --verbs=list --namespaced=false -o name); do
  kubectl get "$resource" -o yaml > "/backup/resources/cluster-scoped/$resource.yaml"
done
```

### Automatización de copias de seguridad

Solo para el ejemplo de kubeadm autogestionado: sustituye la imagen de herramientas por una imagen verificada que incluya una versión compatible de etcdctl, asegúrate de que la etiqueta y el taint del plano de control y las rutas de certificados coincidan, y crea el PVC de copia de seguridad. El host seleccionado debe exponer etcd en la dirección de bucle local indicada y permitir el montaje del PVC. Esto no se ejecuta en el plano de control administrado de EKS. Verifica la instantánea y cópiala en un almacenamiento externo protegido; un PVC dentro del clúster por sí solo no constituye una recuperación ante desastres.

Automatiza las tareas de copia de seguridad con CronJob:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: etcd-backup
  namespace: kube-system
spec:
  concurrencyPolicy: Forbid
  schedule: "0 0 * * *"  # Run daily at midnight
  jobTemplate:
    spec:
      template:
        spec:
          hostNetwork: true
          automountServiceAccountToken: false
          nodeSelector:
            node-role.kubernetes.io/control-plane: ""
          tolerations:
          - key: node-role.kubernetes.io/control-plane
            operator: Exists
            effect: NoSchedule
          containers:
          - name: etcd-backup
            image: example.invalid/etcd-backup-tools:replace-me
            command:
            - /bin/sh
            - -c
            - |
              set -eu
              umask 077
              ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
                --cacert=/etc/kubernetes/pki/etcd/ca.crt \
                --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
                --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
                snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d-%H-%M-%S).db
            volumeMounts:
            - name: etcd-ca
              mountPath: /etc/kubernetes/pki/etcd/ca.crt
              readOnly: true
            - name: etcd-client-cert
              mountPath: /etc/kubernetes/pki/etcd/healthcheck-client.crt
              readOnly: true
            - name: etcd-client-key
              mountPath: /etc/kubernetes/pki/etcd/healthcheck-client.key
              readOnly: true
            - name: backup
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: etcd-ca
            hostPath:
              path: /etc/kubernetes/pki/etcd/ca.crt
              type: File
          - name: etcd-client-cert
            hostPath:
              path: /etc/kubernetes/pki/etcd/healthcheck-client.crt
              type: File
          - name: etcd-client-key
            hostPath:
              path: /etc/kubernetes/pki/etcd/healthcheck-client.key
              type: File
          - name: backup
            persistentVolumeClaim:
              claimName: etcd-backup-pvc
```

## Supervisión y registro {#monitoring-and-logging}

La supervisión y el registro eficaces son elementos fundamentales de la administración de clústeres.

El diagrama siguiente muestra la arquitectura de supervisión y registro de un clúster de Kubernetes:

![Diagrama de arquitectura que muestra las métricas del servidor de API y de los nodos fluyendo a través de kube-state-metrics y Node Exporter hacia Prometheus, y después hacia Alertmanager y Grafana; los registros de los Pods pasan por Fluentd/Fluent Bit a Elasticsearch con Kibana y a Loki, que también envía datos a Grafana.](../.gitbook/assets/en-core-09-cluster-administration-7.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-7.html)

### Herramientas de supervisión

Herramientas para supervisar clústeres de Kubernetes:

1. **Prometheus**: recopilación y almacenamiento de métricas
2. **Grafana**: visualización de métricas
3. **Alertmanager**: gestión de alertas
4. **kube-state-metrics**: generación de métricas de objetos de Kubernetes
5. **metrics-server**: suministro de métricas de uso de recursos

#### Instalación de Prometheus y Grafana

Instala Prometheus y Grafana mediante Helm:

```bash
# Add Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

#### Métricas clave de supervisión

Métricas clave para supervisar:

1. **Métricas de nodos**: uso de CPU, memoria, disco y red
2. **Métricas de Pods**: uso de CPU y memoria, número de reinicios
3. **Métricas de contenedores**: uso de CPU, memoria y sistema de archivos
4. **Métricas del servidor de API**: latencia de solicitudes, número de solicitudes, tasa de errores
5. **Métricas de etcd**: E/S de disco, cambios de líder, latencia de confirmación

### Herramientas de registro

Herramientas para el registro de clústeres de Kubernetes:

1. **Elasticsearch**: almacenamiento y búsqueda de registros
2. **Fluentd/Fluent Bit**: recopilación y reenvío de registros
3. **Kibana**: visualización de registros
4. **Loki**: sistema de agregación de registros
5. **Grafana**: visualización de registros

#### Instalación de la pila EFK (Elasticsearch, Fluentd y Kibana)

Instala la pila EFK mediante Helm:

El repositorio independiente de charts de Helm de Elastic Stack está archivado. Para desplegar una solución mantenida, usa Elastic Cloud on Kubernetes (ECK) y, después, define los recursos de Elasticsearch/Kibana y un recopilador de registros compatible. La instalación del operador por sí sola no crea una pila EFK:

```bash
helm repo add elastic https://helm.elastic.co
helm upgrade --install elastic-operator elastic/eck-operator \
  --namespace elastic-system --create-namespace \
  --version "${ECK_CHART_VERSION:?Select a supported ECK chart version}"
```

Mantén los paneles accesibles mediante ClusterIP y un acceso autenticado; configura el almacenamiento, TLS, las credenciales, el análisis de registros del recopilador y RBAC siguiendo la [guía de ECK](https://www.elastic.co/docs/deploy-manage/deploy/cloud-on-k8s/install-using-helm-chart).

#### Configuración de la recopilación de registros

Este ejemplo analiza el formato de registro de CRI en lugar de presuponer que se trata de JSON de Docker. La imagen del recopilador debe incluir los complementos de metadatos y salida, montar los registros de los nodos y un almacenamiento con permisos de escritura para el archivo que guarda la posición de lectura, y disponer de RBAC de metadatos con ámbito restringido. Configura TLS/autenticación para el servicio real de Elasticsearch; el nombre de host de ejemplo por sí solo no constituye una integración completa con ECK. Gestiona los registros parciales y de varias líneas según el recopilador elegido.

Ejemplo de configuración de Fluentd:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: logging
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      read_from_head true
      <parse>
        @type regexp
        expression /^(?<time>[^ ]+) (?<stream>stdout|stderr) (?<logtag>[^ ]*) (?<log>.*)$/
        time_type string
        time_format %Y-%m-%dT%H:%M:%S.%N%:z
      </parse>
    </source>

    <filter kubernetes.**>
      @type kubernetes_metadata
      kubernetes_url https://kubernetes.default.svc
      bearer_token_file /var/run/secrets/kubernetes.io/serviceaccount/token
      ca_file /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    </filter>

    <match kubernetes.**>
      @type elasticsearch
      host elasticsearch-master
      port 9200
      logstash_format true
      logstash_prefix k8s
    </match>
```

## Solución de problemas {#troubleshooting}

La solución de problemas de clústeres de Kubernetes es una parte importante de la administración de clústeres.

### Solución de problemas de Pods

Comandos para solucionar problemas de Pods:

```bash
# Check pod status
kubectl get pod <pod-name> -o wide

# Check pod detailed information
kubectl describe pod <pod-name>

# Check pod logs
kubectl logs <pod-name>
kubectl logs <pod-name> -c <container-name>  # For multi-container pods
kubectl logs <pod-name> --previous  # Logs from previous container

# Execute command in pod
kubectl exec -it <pod-name> -- /bin/sh
```

### Solución de problemas de nodos

Comandos para solucionar problemas de nodos:

```bash
# Check node status
kubectl get node <node-name> -o wide

# Check node detailed information
kubectl describe node <node-name>

# Check node resource usage
kubectl top node <node-name>

# SSH to node
ssh <node-name>

# Check node system logs
journalctl -u kubelet

# Check node resource usage
top
df -h
free -m
```

### Solución de problemas de red

Comandos para solucionar problemas de red:

```bash
# Check service status
kubectl get svc <service-name>

# Check service detailed information
kubectl describe svc <service-name>

# Check endpoints
kubectl get endpointslices -l kubernetes.io/service-name=<service-name>

# Check DNS
kubectl run -it --rm --restart=Never busybox --image=busybox -- nslookup <service-name>

# Test network connectivity
kubectl run -it --rm --restart=Never busybox --image=busybox -- wget -O- <service-name>:<port>

# Check network policies
kubectl get networkpolicy
kubectl describe networkpolicy <policy-name>
```

### Solución de problemas del plano de control

Comandos para solucionar problemas del plano de control:

```bash
# Check component status
kubectl get --raw='/readyz?verbose'

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check controller manager logs
kubectl logs -n kube-system kube-controller-manager-<node-name>

# Check scheduler logs
kubectl logs -n kube-system kube-scheduler-<node-name>

# Check etcd logs
kubectl logs -n kube-system etcd-<node-name>
```

## Administración de clústeres de Amazon EKS {#amazon-eks-cluster-administration}

Amazon EKS es un servicio de Kubernetes administrado que automatiza muchos aspectos de la administración de clústeres.

El diagrama siguiente muestra la arquitectura del clúster de Amazon EKS y sus componentes de gestión:

![Diagrama de arquitectura que muestra a un usuario administrando Amazon EKS mediante la consola, la CLI o la API de AWS; EKS ejecuta un plano de control, grupos de nodos administrados y Fargate; el plano de control utiliza AWS IAM, VPC y CloudWatch; y los complementos son VPC CNI, CoreDNS y kube-proxy.](../.gitbook/assets/en-core-09-cluster-administration-8.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-8.html)

### Configuración del clúster de EKS

Establece el CIDR real del administrador antes de cambiar el acceso al endpoint y comprueba que el acceso privado siga siendo posible. Una actualización de versión debe pasar a la siguiente versión menor compatible, con complementos/nodos compatibles; no uses el ejemplo para volver a una versión anterior ni omitir versiones menores. Consulta periódicamente el estado del ID de actualización devuelto y detén los cambios dependientes si falla.

Gestión de la configuración del clúster de EKS:

```bash
# Check EKS cluster information
aws eks describe-cluster --name my-cluster

# Update EKS cluster
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config "endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=${ADMIN_CIDR:?Set an approved administrator public CIDR}"

# Update EKS cluster version
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version "${TARGET_VERSION:?Select the next EKS-supported minor version}"
```

### Gestión de grupos de nodos de EKS

Gestión de grupos de nodos de EKS:

```bash
# Check node group information
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup

# Scale node group
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --scaling-config minSize=2,maxSize=10,desiredSize=5

# Update node group
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

### Gestión de complementos de EKS

Lee la versión actual con `aws eks describe-cluster --name my-cluster --query cluster.version --output text`; úsala para buscar complementos y seleccionar una versión compatible concreta. Revisa la configuración/IAM existente antes de crear o actualizar, y no vuelvas a crear un complemento que ya esté administrado. El ejemplo de eliminación usa `--preserve` para que el CNI siga en ejecución mientras se elimina la gestión de EKS; desinstalar los componentes de red en uso es una operación disruptiva independiente.

Gestión de complementos de EKS:

```bash
# Check available add-ons
aws eks describe-addon-versions --addon-name vpc-cni \
  --kubernetes-version "${CLUSTER_VERSION:?Set the actual cluster version}"

# Install add-on
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version "${CNI_ADDON_VERSION:?Select a compatible pinned VPC CNI add-on version}"

# Update add-on
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version "${CNI_ADDON_VERSION:?Select a compatible pinned VPC CNI add-on version}"

# Delete add-on
aws eks delete-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni --preserve
```

### Actualización del clúster de EKS

Proceso de actualización del clúster de EKS:

1. **Actualización del plano de control**:
   ```bash
   aws eks update-cluster-version \
     --name my-cluster \
     --kubernetes-version "${TARGET_VERSION:?Select the next EKS-supported minor version}"
   ```

2. **Actualización de complementos**:
   ```bash
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni \
     --addon-version "${CNI_ADDON_VERSION:?Select a compatible pinned VPC CNI add-on version}"
   ```

3. **Actualización del grupo de nodos**:
   ```bash
   aws eks update-nodegroup-version \
     --cluster-name my-cluster \
     --nodegroup-name my-nodegroup
   ```

### Supervisión del clúster de EKS

El registro del plano de control exporta registros de api/audit/authenticator/controllerManager/scheduler. Container Insights requiere el agente/complemento de CloudWatch y permisos de IAM con ámbito restringido para la telemetría; no se habilita mediante update-cluster-logging. El complemento de observabilidad de CloudWatch instala componentes de CloudWatch/Fluent Bit, no Prometheus/Grafana. Consulta la [configuración oficial del complemento](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html).

Herramientas de supervisión del clúster de EKS:

1. **Amazon CloudWatch**: métricas, registros y alertas
2. **AWS CloudTrail**: registro de llamadas a la API
3. **Amazon Managed Grafana**: visualización de métricas
4. **Amazon Managed Service for Prometheus**: recopilación y almacenamiento de métricas

Habilita el registro del plano de control de EKS:

```bash
# Enable EKS control-plane logs
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --approve
```

## Prácticas recomendadas para la administración de clústeres {#cluster-administration-best-practices}

Prácticas recomendadas para administrar clústeres de Kubernetes y EKS:

### Prácticas recomendadas para la configuración del clúster

1. **Infraestructura como código (IaC)**: administra la configuración del clúster con Terraform, AWS CDK, eksctl, etc.
2. **Control de versiones**: almacena la configuración del clúster en sistemas de control de versiones
3. **Varios entornos**: separa los entornos de desarrollo, preproducción y producción
4. **Separación de redes**: configura una separación de redes y grupos de seguridad adecuados
5. **Principio de privilegio mínimo**: concede únicamente los permisos mínimos necesarios

### Prácticas recomendadas de operaciones

1. **Copias de seguridad periódicas**: realiza copias de seguridad periódicas de etcd y de los recursos importantes
2. **Supervisión y alertas**: crea sistemas completos de supervisión y alertas
3. **Registro centralizado**: centraliza y analiza los registros
4. **Automatización**: automatiza las tareas repetitivas
5. **Planificación de recuperación ante desastres**: establece y prueba planes claros de recuperación ante desastres

### Prácticas recomendadas de seguridad

1. **Actualizaciones periódicas**: actualiza periódicamente el clúster y los nodos
2. **Políticas de red**: configura políticas de red adecuadas
3. **Cifrado**: cifra los datos en reposo y en tránsito
4. **Contexto de seguridad**: configura contextos de seguridad adecuados
5. **Análisis de imágenes**: analiza las imágenes de contenedor para detectar vulnerabilidades

### Prácticas recomendadas para la gestión de recursos

1. **Solicitudes y límites de recursos**: establece solicitudes y límites de recursos adecuados para todos los Pods
2. **Separación de namespaces**: separa las cargas de trabajo por namespace
3. **Cuotas de recursos**: establece cuotas de recursos por namespace
4. **HPA y VPA**: configura el escalado automático
5. **Afinidad de nodos y taints**: optimiza la colocación de las cargas de trabajo

### Prácticas recomendadas específicas de EKS

1. **Grupos de nodos administrados**: usa grupos de nodos administrados siempre que sea posible
2. **Fargate**: usa Fargate para cargas de trabajo sin servidor
3. **Complementos de EKS**: usa los complementos oficiales de EKS
4. **Roles de IAM para ServiceAccount (IRSA)**: administra los permisos de IAM por Pod
5. **Personalización de VPC CNI**: configura VPC CNI según los requisitos de red

## Conclusión

La administración de clústeres de Kubernetes desempeña un papel importante en el mantenimiento de la estabilidad, la seguridad y el rendimiento del clúster. En este capítulo se trataron distintos aspectos de la administración de clústeres, incluida la gestión de los componentes del clúster, la gestión de recursos, las redes, la gestión de la autenticación y la autorización, las actualizaciones, la copia de seguridad y recuperación, la supervisión y el registro, y la solución de problemas.

Amazon EKS reduce la complejidad de la gestión del plano de control de Kubernetes y simplifica la administración de clústeres mediante la integración con los servicios de AWS. Sin embargo, sigue siendo importante comprender los conceptos fundamentales de Kubernetes y las prácticas recomendadas para gestionar clústeres de manera eficaz.

La administración de clústeres es un proceso continuo que debe ajustarse constantemente a los requisitos del clúster y a las características de las cargas de trabajo. Es importante usar herramientas de supervisión para seguir el estado del clúster, minimizar las tareas repetitivas mediante la automatización y seguir las prácticas recomendadas para mantener la estabilidad y la seguridad del clúster.

## Redes del clúster

Las redes del clúster de Kubernetes gestionan la comunicación entre Pods, el descubrimiento de servicios y el acceso externo.

### Arquitectura de red

![Diagrama de arquitectura que muestra las redes del clúster divididas en red de Pods, red de Service, ingress y políticas de red, cada una implementada por un complemento CNI, tipos de Service (ClusterIP, NodePort, LoadBalancer), un controlador de ingress y seguridad de red, respectivamente.](../.gitbook/assets/en-core-09-cluster-administration-9.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-9.html)

### Gestión de complementos CNI

Los complementos CNI (Container Network Interface) gestionan las redes de los clústeres de Kubernetes.

Elige un único CNI o una configuración documentada de encadenamiento/migración. Las alternativas Calico, Flannel y Cilium no deben instalarse secuencialmente en el mismo clúster en ejecución. Usa una versión compatible y fijada, y sigue las instrucciones específicas del proveedor; en EKS, sigue el procedimiento del VPC CNI o de la alternativa CNI planificada en el [capítulo de redes](./03-services-networking.md).

```bash
# Inspect the installed networking components before making changes
kubectl get daemonsets -A
kubectl get pods -A -l k8s-app=calico-node
```


### Comparación de complementos CNI

| Complemento CNI | Modelo de red | Compatibilidad con políticas de red | Rendimiento | Características |
|-----------|---------------|----------------------|-------------|----------|
| **Calico** | BGP | Sí | Alto | Destaca en políticas de red, basado en enrutamiento |
| **Flannel** | VXLAN/host-gateway | No | Medio | Configuración sencilla, funciones limitadas |
| **Cilium** | eBPF | Sí | Muy alto | Políticas L3-L7, alto rendimiento |
| **Weave Net** | VXLAN | Sí | Medio | Compatibilidad con cifrado, multiclúster |
| **AWS VPC CNI** | AWS VPC | Sí, con una versión/configuración compatible | Depende de la carga de trabajo | Integración nativa con EKS |

### Solución de problemas de red

```bash
# Test pod network connectivity
kubectl run -it --rm network-test --image=busybox -- sh
# Inside the container
ping <target-ip>
traceroute <target-ip>
wget -O- <service-name>

# DNS troubleshooting
kubectl run -it --rm dns-test --image=busybox -- sh
# Inside the container
nslookup kubernetes.default.svc.cluster.local
cat /etc/resolv.conf

# Check service endpoints
kubectl get endpointslices -l kubernetes.io/service-name=<service-name>

# Check network policies
kubectl describe networkpolicy -n <namespace>
```
## Gestión de la autenticación y la autorización

La gestión de la autenticación y la autorización de Kubernetes es un elemento fundamental de la seguridad del clúster. RBAC (Role-Based Access Control) se usa para gestionar los permisos de usuarios y cuentas de servicio.

### Métodos de autenticación

Kubernetes admite varios métodos de autenticación:

1. **Certificados X.509**: autenticación mediante certificados de cliente
2. **Tokens de ServiceAccount**: se usan para acceder al servidor de API desde los Pods
3. **OpenID Connect (OIDC)**: integración con proveedores de identidad externos
4. **Autenticación de tokens mediante webhook**: integración con servicios de autenticación externos
5. **Proxy de autenticación**: autenticación mediante un proxy

### Configuración de RBAC

```yaml
# role.yaml - namespace-scoped role
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

```yaml
# rolebinding.yaml - binding role to user
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: jane
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

```yaml
# clusterrole.yaml - cluster-scoped role
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: namespace-reader
rules:
- apiGroups: [""]
  resources: ["namespaces"]
  verbs: ["get", "watch", "list"]
```

```yaml
# clusterrolebinding.yaml - binding cluster role to user
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-namespaces-global
subjects:
- kind: Group
  name: namespace-viewers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: namespace-reader
  apiGroup: rbac.authorization.k8s.io
```

### Creación de certificados de usuario

Para la autenticación con certificados de cliente en un clúster autogestionado, envía una solicitud de firma de certificado (CSR) y haz que un aprobador autorizado verifique la identidad y los grupos solicitados. No distribuyas la clave privada de la CA del clúster. El acceso de los usuarios de EKS debe gestionarse con IAM y entradas de acceso.

```bash
umask 077
openssl genrsa -out jane.key 2048
openssl req -new -key jane.key -out jane.csr -subj "/CN=jane/O=dev"
cat <<EOF | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: jane-csr
spec:
  request: $(base64 < jane.csr | tr -d '\n')
  signerName: kubernetes.io/kube-apiserver-client
  expirationSeconds: 86400
  usages:
  - client auth
EOF
# Authorized approver only, after reviewing the CSR identity:
kubectl certificate approve jane-csr
kubectl wait --for=jsonpath='{.status.certificate}' csr/jane-csr --timeout=60s
kubectl get csr jane-csr -o jsonpath='{.status.certificate}' | base64 --decode > jane.crt
kubectl config set-credentials jane --client-certificate=jane.crt --client-key=jane.key
kubectl config set-context jane-context --cluster=kubernetes --user=jane
```

### Gestión de ServiceAccount

```bash
# Create service account
kubectl create serviceaccount app-service-account

# Bind role to service account
kubectl create rolebinding app-service-account-binding \
  --role=pod-reader \
  --serviceaccount=default:app-service-account

# Inspect ServiceAccount metadata (projected tokens are not listed here)
kubectl describe serviceaccount app-service-account
```

### Verificación de permisos

```bash
# Check user permissions
kubectl auth can-i get pods --as jane

# Check permissions in a specific namespace
kubectl auth can-i create deployments --as jane --namespace production
```
## Actualizaciones del clúster

Las actualizaciones de clústeres de Kubernetes son necesarias para aplicar nuevas funciones, parches de seguridad y correcciones de errores. Deben planificarse y ejecutarse cuidadosamente.

### Planificación de la actualización

![Diagrama de árbol que muestra la planificación de la actualización dividida en cuatro tareas: comprobar la compatibilidad de versiones, crear una copia de seguridad, elegir una estrategia de actualización y planificar el tiempo de inactividad; cada tarea conduce a una acción concreta: revisar los cambios de la API, hacer una copia de seguridad de etcd, elegir entre actualización in situ o blue/green y comunicar los cambios a los usuarios.](../.gitbook/assets/en-core-09-cluster-administration-10.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-10.html)

### Comparación de estrategias de actualización

| Estrategia | Descripción | Ventajas | Desventajas | Entorno adecuado |
|----------|-------------|------------|---------------|---------------------|
| **Actualización in situ** | Actualizar directamente el clúster existente | Uso eficiente de recursos, procedimiento sencillo | Reversión compleja, posible tiempo de inactividad | Entornos de desarrollo y pruebas |
| **Despliegue blue/green** | Crear un clúster con la nueva versión y cambiar a él | Reversión segura, permite verificar | Duplicación de recursos, coste elevado | Entornos de producción |
| **Despliegue canary** | Mover solo algunas cargas de trabajo al clúster nuevo | Verificación gradual, riesgo reducido | Gestión compleja, operación en paralelo | Entornos de producción críticos |

### Actualización mediante kubeadm

Sigue el [procedimiento de actualización de kubeadm específico para cada versión](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/). Habilita el repositorio pkgs.k8s.io de la versión menor de destino y selecciona una versión de paquete publicada concreta; actualiza una versión menor cada vez.

1. Haz una copia de seguridad de etcd y valida la compatibilidad de las cargas de trabajo y los complementos. En el primer nodo del plano de control, actualiza kubeadm, ejecuta `kubeadm upgrade plan` y, a continuación, `kubeadm upgrade apply <target-version>`.
2. En los demás nodos del plano de control, actualiza kubeadm y ejecuta `kubeadm upgrade node`.
3. Vacía cada nodo (drain) antes de actualizar kubelet. Si el vaciado falla, detén el procedimiento y resuelve la causa. Actualiza kubelet/kubectl a versiones compatibles, vuelve a cargar systemd, reinicia kubelet, comprueba que el nodo esté Ready y que las cargas de trabajo estén sanas y, después, habilita de nuevo la asignación de Pods al nodo (uncordon) desde un cliente administrativo.
4. En cada nodo de trabajo, actualiza kubeadm y ejecuta `kubeadm upgrade node`; después, realiza la secuencia de vaciado, actualización de kubelet, verificación y habilitación de nuevas asignaciones. No ejecutes una actualización genérica de todo el sistema como sustituto del procedimiento de Kubernetes específico para cada versión.

Ejecuta los comandos en el nodo o cliente administrativo identificado explícitamente; una secuencia de sesiones `ssh` anidadas no es un script de automatización multinodo.

### Verificación posterior a la actualización

```bash
# Check cluster version
kubectl version

# Check node versions
kubectl get nodes

# Check component status
kubectl get --raw='/readyz?verbose'

# Check workload status
kubectl get pods -A
```
## Copia de seguridad y recuperación

La copia de seguridad y recuperación de un clúster de Kubernetes es una parte importante de la planificación de recuperación ante desastres. Los principales objetivos de las copias de seguridad son la base de datos etcd, los datos de los volúmenes persistentes y las definiciones de recursos de Kubernetes.

### Copia de seguridad y recuperación de etcd

etcd es un componente fundamental que almacena toda la información de estado del clúster.

Para la recuperación ante desastres de un clúster autogestionado, detén todos los servidores de API y los procesos de etcd afectados mediante el procedimiento operativo específico de la distribución. Detener solo kubelet deja en ejecución los contenedores de los Pod estáticos existentes. Restaura en un directorio nuevo con una versión compatible de etcdutl; conserva los datos originales hasta verificar la recuperación. Este comando ilustra la restauración de un solo miembro; una restauración de alta disponibilidad con varios miembros requiere un procedimiento propio:

```bash
etcdutl snapshot status "$SNAPSHOT_FILE" --write-out=table
etcdutl snapshot restore "$SNAPSHOT_FILE" \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-1 \
  --initial-cluster=etcd-1=https://127.0.0.1:2380 \
  --initial-cluster-token=restored-cluster \
  --initial-advertise-peer-urls=https://127.0.0.1:2380 \
  --bump-revision=1000000000 --mark-compacted
```

Establece SNAPSHOT_FILE en la instantánea verificada. Para alta disponibilidad, restaura la misma instantánea en cada miembro con un nombre y una URL de comunicación únicos para ese miembro, y con la misma lista completa de miembros. Elige un incremento de revisión que supere los cambios realizados desde la instantánea. Actualiza el manifiesto/servicio de etcd para que apunte a la ruta restaurada, con el propietario y los certificados correctos; verifica el cuórum y el estado y, después, reinicia los servidores de API y los controladores. Consulta la [guía oficial de recuperación](https://etcd.io/docs/v3.6/op-guide/recovery/). Los usuarios de EKS no pueden restaurar directamente etcd del plano de control administrado.

### Copia de seguridad de recursos de Kubernetes

```bash
# Export selected resources, not a full cluster backup
set -eu
umask 077
mkdir -p /backup/resources/$(date +%Y-%m-%d)
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  kubectl -n $ns get all -o yaml > /backup/resources/$(date +%Y-%m-%d)/$ns-all.yaml
done

# Backup specific resource types
for resource in deployments services configmaps secrets; do
  kubectl get $resource -A -o yaml > /backup/resources/$(date +%Y-%m-%d)/$resource.yaml
done
```

### Copia de seguridad y recuperación con Velero

Selecciona versiones compatibles de Velero y del complemento de AWS según la matriz oficial. El ejemplo de IRSA presupone que hay un proveedor OIDC del clúster configurado y un rol con ámbito restringido que confía en el ServiceAccount de velero. Configura el bucket de copia de seguridad, la compatibilidad con instantáneas de volúmenes/copia de archivos, el cifrado y los permisos de restauración antes de la instalación; no todos los PVC se protegen automáticamente.

Velero es una herramienta para hacer copias de seguridad y recuperar recursos de clústeres de Kubernetes y volúmenes persistentes.

```bash
# Install Velero (using AWS S3 backup storage)
velero install \
  --provider aws \
  --plugins "${VELERO_AWS_PLUGIN_IMAGE:?Select a plugin compatible with your Velero release}" \
  --bucket velero-backup \
  --backup-location-config region=us-west-2 \
  --snapshot-location-config region=us-west-2 \
  --no-secret \
  --sa-annotations "eks.amazonaws.com/role-arn=${VELERO_ROLE_ARN:?Set the preconfigured IRSA role ARN}"

# Full cluster backup
velero backup create full-cluster-backup --include-namespaces '*'

# Backup specific namespace
velero backup create production-backup --include-namespaces production

# Check backup status
velero backup describe full-cluster-backup

# Restore from backup
velero restore create --from-backup full-cluster-backup
```

### Comparación de estrategias de copia de seguridad

| Método de copia de seguridad | Objetivo de la copia de seguridad | Ventajas | Desventajas | Tiempo de recuperación |
|--------------|---------------|------------|---------------|---------------|
| **Instantánea de etcd** | Estado del clúster | Función integrada, conserva el estado completo | No incluye los datos de volúmenes, proceso manual | Medio |
| **Copia de seguridad de recursos YAML** | Objetos de Kubernetes | Implementación sencilla, restauración selectiva | No incluye los datos de volúmenes, relaciones complejas | Lento |
| **Velero** | Recursos y volúmenes | Automatización, ejecución programada, instantáneas de volúmenes | Requiere instalar una herramienta adicional | Rápido |
| **Instantáneas del proveedor de nube** | Discos/sistemas de archivos compatibles | Puntos de recuperación nativos del backend | No captura todo el clúster de Kubernetes/EKS | Depende de los datos/backend |
## Supervisión y registro

La gestión eficaz de clústeres requiere un sistema completo de supervisión y registro. Esto permite detectar y resolver los problemas cuanto antes.

### Arquitectura de supervisión

![Diagrama de arquitectura que muestra la supervisión de Kubernetes dividida en recopilación de métricas, recopilación de registros, alertas y visualización; las gestionan Prometheus con kube-state-metrics y node-exporter, Fluentd/Fluent Bit enviando registros a Elasticsearch y Kibana, Alertmanager y Grafana, respectivamente.](../.gitbook/assets/en-core-09-cluster-administration-11.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-11.html)

### Instalación de Prometheus y Grafana

```bash
# Install Prometheus and Grafana using Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.enabled=true \
  --set prometheus.service.type=ClusterIP

# Check services
kubectl get svc -n monitoring

# Access Grafana (using port forwarding)
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring
# Obtain credentials from the configured Grafana Secret; do not assume a published default password
```

### Instalación de la pila EFK (Elasticsearch, Fluentd y Kibana)

El repositorio independiente de charts de Helm de Elastic Stack está archivado. Para desplegar una solución mantenida, usa Elastic Cloud on Kubernetes (ECK) y, después, define los recursos de Elasticsearch/Kibana y un recopilador de registros compatible. La instalación del operador por sí sola no crea una pila EFK:

```bash
helm repo add elastic https://helm.elastic.co
helm upgrade --install elastic-operator elastic/eck-operator \
  --namespace elastic-system --create-namespace \
  --version "${ECK_CHART_VERSION:?Select a supported ECK chart version}"
```

Mantén los paneles accesibles mediante ClusterIP y un acceso autenticado; configura el almacenamiento, TLS, las credenciales, el análisis de registros del recopilador y RBAC siguiendo la [guía de ECK](https://www.elastic.co/docs/deploy-manage/deploy/cloud-on-k8s/install-using-helm-chart).

### Métricas clave de supervisión

| Tipo de métrica | Descripción | Métricas clave | Herramientas de supervisión |
|-------------|-------------|-------------|-----------------|
| **Métricas de nodos** | Uso de recursos a nivel de nodo | CPU, memoria, disco, red | node-exporter, Prometheus |
| **Métricas de Pods** | Uso de recursos de contenedores | CPU, uso de memoria, límites | cAdvisor, Prometheus |
| **Métricas del clúster** | Estado y recursos del clúster | Número de Pods, estado de nodos/objetos, réplicas deseadas/actuales | kube-state-metrics |
| **Métricas de aplicaciones** | Métricas personalizadas de aplicaciones | Número de solicitudes, latencia, tasa de errores | Bibliotecas cliente de Prometheus |

### Recopilación y análisis de registros

```bash
# Check logs for a specific pod
kubectl logs <pod-name> -n <namespace>

# Check logs from previous instance
kubectl logs <pod-name> -n <namespace> --previous

# Check logs for a specific container (multi-container pod)
kubectl logs <pod-name> -c <container-name> -n <namespace>

# Stream logs
kubectl logs -f <pod-name> -n <namespace>

# Check logs for all pods (using label selector)
kubectl logs -l app=nginx -n <namespace>
```

### Configuración de alertas

Puedes configurar alertas con Prometheus Alertmanager:

Crea un Secret protegido `slack-webhook` con la clave `url` en monitoring y, después, combina estos valores de Helm con los de la instalación existente de kube-prometheus-stack. No incluyas la URL del webhook en el repositorio. El operador no consume automáticamente un ConfigMap independiente.

```yaml
# alertmanager-values.yaml
alertmanager:
  alertmanagerSpec:
    secrets:
    - slack-webhook
  config:
    global:
      resolve_timeout: 5m
      slack_api_url_file: /etc/alertmanager/secrets/slack-webhook/url
    route:
      receiver: slack-notifications
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      group_by: [alertname, cluster, service]
    receivers:
    - name: slack-notifications
      slack_configs:
      - channel: '#alerts'
        send_resolved: true
        title: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

Al actualizar, conserva la versión actual del chart y los demás valores; comprueba que Alertmanager se haya recargado y esté operativo antes de confiar en las notificaciones.
## Solución de problemas

La solución de problemas de clústeres de Kubernetes es una habilidad importante para administradores de sistemas y operadores. Para resolver los problemas de manera eficaz, se requiere un enfoque sistemático.

### Metodología para la solución de problemas

![Diagrama de flujo que muestra la secuencia de seis pasos para solucionar problemas, desde la identificación del problema hasta su documentación; el paso de recopilación de información se divide en comprobaciones de registros, eventos y estado de los recursos.](../.gitbook/assets/en-core-09-cluster-administration-12.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-12.html)

### Problemas habituales y soluciones

| Tipo de problema | Síntomas | Comandos de diagnóstico | Soluciones habituales |
|-------------|----------|---------------------|-----------------|
| **El Pod no se inicia** | El Pod está en estado Pending o ContainerCreating | `kubectl describe pod <pod-name>` | Comprueba las restricciones de recursos, la disponibilidad de la imagen y los montajes de volúmenes |
| **Problemas de conexión de Service** | No se puede acceder a los Pods mediante el Service | `kubectl describe svc <service-name>`, `kubectl get endpointslices -l kubernetes.io/service-name=<service-name>` | Comprueba los selectores de etiquetas, el estado de los Pods y las políticas de red |
| **Problemas de nodos** | El nodo está en estado NotReady | `kubectl describe node <node-name>`, `kubectl get events` | Comprueba el estado de kubelet, los recursos del sistema y la conectividad de red |
| **Problemas de DNS** | No se puede conectar por nombre de Service | `kubectl exec -it <pod-name> -- nslookup kubernetes.default` | Comprueba los Pods de CoreDNS, el Service kube-dns y las políticas de red |
| **Problemas de autenticación/autorización** | Se deniega el acceso al servidor de API | `kubectl auth can-i <verb> <resource>` | Comprueba la configuración de RBAC, la validez del certificado y la cuenta de servicio |

### Solución de problemas de Pods

```bash
# Check pod status
kubectl get pod <pod-name> -o wide

# Check pod details
kubectl describe pod <pod-name>

# Check pod logs
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # Logs from previous container

# Execute command in pod
kubectl exec -it <pod-name> -- /bin/sh

# Check pod events
kubectl get events --field-selector involvedObject.name=<pod-name>
```

### Solución de problemas de nodos

```bash
# Check node status
kubectl get nodes
kubectl describe node <node-name>

# Check node resource usage
kubectl top node <node-name>

# Check node system logs (SSH required)
ssh <node-ip> 'sudo journalctl -u kubelet'

# Check kubelet status (SSH required)
ssh <node-ip> 'sudo systemctl status kubelet'
```

### Solución de problemas de red

```bash
# Check service and endpoints
kubectl get svc <service-name>
kubectl get endpointslices -l kubernetes.io/service-name=<service-name>

# DNS troubleshooting
kubectl run -it --rm dns-test --image=busybox -- sh
# Inside the container
nslookup kubernetes.default.svc.cluster.local
cat /etc/resolv.conf

# Network connectivity test
kubectl run -it --rm network-test --image=nicolaka/netshoot -- sh
# Inside the container
ping <target-ip>
traceroute <target-ip>
curl <service-name>:<port>
```
## Administración de clústeres de Amazon EKS

Amazon EKS (Elastic Kubernetes Service) es un servicio de Kubernetes administrado en AWS en el que AWS administra el plano de control. Las responsabilidades del cliente respecto a los nodos dependen de si se usan grupos de nodos administrados, Auto Mode, Fargate o infraestructura de cómputo autogestionada; la seguridad y la configuración de las cargas de trabajo siguen siendo responsabilidad del cliente.

### Arquitectura del clúster de EKS

![Diagrama de arquitectura que muestra un clúster de Amazon EKS dividido en un plano de control administrado por AWS (servidor de API, etcd y scheduler) y un área de responsabilidad del cliente que abarca el plano de datos (grupos de nodos administrados con grupos de EC2 Auto Scaling, nodos autogestionados y Fargate), las redes (VPC CNI y AWS VPC) y la seguridad (autenticación de IAM con roles y políticas de IAM).](../.gitbook/assets/en-core-09-cluster-administration-13.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-13.html)

### Creación de un clúster de EKS

```bash
# Create cluster using eksctl
eksctl create cluster \
  --name my-cluster \
  --version 1.36 \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --managed

# Alternative: create control plane using AWS CLI (not after the eksctl example)
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/eks-cluster-role \
  --kubernetes-version 1.36 \
  --resources-vpc-config "subnetIds=${EKS_SUBNET_IDS:?Set two or more appropriate subnets},securityGroupIds=${EKS_SECURITY_GROUP_ID:?Set the intended security group},endpointPrivateAccess=true,endpointPublicAccess=true,publicAccessCidrs=${ADMIN_CIDR:?Set an approved administrator public CIDR}"
```

### Gestión de grupos de nodos

```bash
# Create managed node group
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-nodegroup \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5

# Scale node group
eksctl scale nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --nodes 5 \
  --region us-west-2

# Update node group
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --region us-west-2
```

### Actualización del clúster de EKS

```bash
# Check cluster version
aws eks describe-cluster --name my-cluster --query "cluster.version"

# Upgrade cluster control plane
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version "${TARGET_VERSION:?Select the next EKS-supported minor version}"

# Upgrade managed node group
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

### Autenticación y autorización del clúster de EKS

El clúster debe usar el modo de autenticación `API` o `API_AND_CONFIG_MAP`. Planifica la migración desde las asignaciones heredadas de aws-auth y conserva el acceso existente de administrador/nodo. Este ejemplo concede a un rol de solo lectura acceso únicamente al namespace predeterminado:

```bash
aws eks describe-cluster --name my-cluster --query cluster.accessConfig.authenticationMode
aws eks create-access-entry --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:role/cluster-viewer --type STANDARD
aws eks associate-access-policy --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:role/cluster-viewer \
  --policy-arn arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy \
  --access-scope type=namespace,namespaces=default
```

Consulta la [guía de entradas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html). Los permisos para administrar entradas de acceso de EKS y los permisos sobre las cargas de trabajo de Kubernetes son independientes.

### Supervisión del clúster de EKS

El registro del plano de control exporta registros de api/audit/authenticator/controllerManager/scheduler. Container Insights requiere el agente/complemento de CloudWatch y permisos de IAM con ámbito restringido para la telemetría; no se habilita mediante update-cluster-logging. El complemento de observabilidad de CloudWatch instala componentes de CloudWatch/Fluent Bit, no Prometheus/Grafana. Consulta la [configuración oficial del complemento](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html).

```bash
# Enable EKS control-plane logs
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --region us-west-2

# Install CloudWatch observability (not Prometheus/Grafana)
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name amazon-cloudwatch-observability \
  --addon-version "${CLOUDWATCH_ADDON_VERSION:?Select a compatible add-on version}"
```
## Prácticas recomendadas para la administración de clústeres

Es importante seguir las prácticas recomendadas para una gestión eficaz de clústeres de Kubernetes y así garantizar la estabilidad, la seguridad y el rendimiento.

### Prácticas recomendadas para la configuración del clúster

1. **Configuración en varias zonas de disponibilidad**: distribuye los nodos entre varias zonas de disponibilidad para lograr alta disponibilidad
2. **Dimensionamiento adecuado**: selecciona los tipos y la cantidad de nodos adecuados para las cargas de trabajo
3. **Configuración del escalado automático**: habilita Cluster Autoscaler y Horizontal Pod Autoscaler
4. **Aplicación de políticas de red**: empieza con una política de denegación predeterminada y permite solo la comunicación necesaria
5. **Establecimiento de cuotas de recursos**: establece límites de recursos por namespace

### Prácticas recomendadas de operaciones

1. **Uso de configuración declarativa**: define todos los recursos en archivos YAML y guárdalos en un sistema de control de versiones
2. **Adopción de GitOps**: usa Git como fuente única de verdad y crea pipelines de despliegue automatizados
3. **Copias de seguridad periódicas**: realiza copias de seguridad periódicas de los datos de etcd y de los volúmenes persistentes
4. **Supervisión y alertas**: crea sistemas completos de supervisión y configura alertas para las métricas clave
5. **Registro centralizado**: recopila todos los registros en un sistema centralizado para facilitar su análisis

### Prácticas recomendadas de seguridad

1. **Principio de privilegio mínimo**: concede solo los permisos mínimos necesarios mediante RBAC
2. **Segmentación de redes**: limita la comunicación entre Pods mediante políticas de red
3. **Análisis de imágenes**: implementa el análisis de imágenes de contenedor para detectar vulnerabilidades
4. **Gestión de Secrets**: usa herramientas externas de gestión de Secrets (por ejemplo, AWS Secrets Manager o HashiCorp Vault)
5. **Auditorías de seguridad periódicas**: audita periódicamente la configuración y los permisos del clúster

### Prácticas recomendadas para las actualizaciones

1. **Actualizaciones graduales**: actualiza gradualmente en lugar de hacerlo todo de una vez
2. **Primero, el entorno de pruebas**: verifica las actualizaciones en entornos de prueba antes de producción
3. **Creación de copias de seguridad**: realiza copias de seguridad completas antes de las actualizaciones
4. **Plan de reversión**: prepara un plan para volver a las versiones anteriores si surgen problemas
5. **Establecimiento de ventanas de actualización**: realiza las actualizaciones en periodos de bajo uso

### Prácticas recomendadas para la optimización de costes

1. **Selección de tamaños de nodo adecuados**: selecciona los tipos de nodo óptimos para las cargas de trabajo
2. **Uso de instancias Spot**: usa instancias Spot para cargas de trabajo no críticas
3. **Configuración del escalado automático**: configura el aumento y la reducción automáticos de capacidad según la demanda
4. **Optimización de solicitudes y límites de recursos**: establece solicitudes y límites de recursos según el uso real
5. **Identificación de recursos inactivos**: identifica y elimina periódicamente los recursos inactivos

### Prácticas recomendadas para la documentación

1. **Documentación de la arquitectura**: documenta la arquitectura del clúster, las redes y la configuración de seguridad
2. **Documentación de procedimientos operativos**: documenta las tareas operativas habituales, los procedimientos de solución de problemas y los planes de respuesta ante emergencias
3. **Gestión de cambios**: registra y supervisa todos los cambios en el clúster
4. **Creación de runbooks**: proporciona guías paso a paso para situaciones habituales
5. **Intercambio de conocimientos**: organiza periódicamente sesiones de intercambio de conocimientos y formación en el equipo
## Conclusión

La administración de clústeres de Kubernetes es una tarea compleja que abarca distintos aspectos. Se requiere un enfoque sistemático desde la configuración del clúster hasta su operación, supervisión, solución de problemas y actualización.

Para administrar clústeres de manera eficaz, céntrate en las siguientes áreas clave:

1. **Gestión de los componentes del clúster**: funcionamiento estable de los componentes del plano de control y de los nodos
2. **Gestión de recursos**: asignación y uso eficientes de recursos
3. **Redes**: configuración de red segura y eficiente
4. **Seguridad**: gestión adecuada de la autenticación y la autorización
5. **Copia de seguridad y recuperación**: prevención de la pérdida de datos y planificación de la recuperación ante desastres
6. **Supervisión y registro**: supervisión del estado y el rendimiento del clúster
7. **Solución de problemas**: enfoque sistemático para resolver problemas

Al utilizar servicios de Kubernetes administrados como Amazon EKS, es importante comprender el modelo de responsabilidad compartida entre el proveedor del servicio y el usuario. AWS administra el plano de control, mientras que la responsabilidad sobre la infraestructura de cómputo varía según el modo; los clientes siguen administrando la configuración y la seguridad de las aplicaciones.

Si sigues las prácticas recomendadas y utilizas las herramientas adecuadas, podrás operar un clúster de Kubernetes estable, seguro y eficiente. Es importante aprender y mejorar continuamente para reforzar las capacidades de gestión del clúster.

---

> **Referencias**:
> - [Documentación oficial de Kubernetes: administración de clústeres](https://kubernetes.io/docs/tasks/administer-cluster/)
> - [Guía del usuario de Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
> - [Prácticas recomendadas de Kubernetes: administración de clústeres](https://kubernetes.io/docs/setup/best-practices/)
> - [Documentación de etcd: copia de seguridad y recuperación](https://etcd.io/docs/v3.6/op-guide/recovery/)
> - [Documentación de Prometheus](https://prometheus.io/docs/introduction/overview/)

## Cuestionario

Para comprobar lo que has aprendido en este capítulo, prueba el [cuestionario sobre administración de clústeres](../quizzes/core/09-cluster-administration-quiz.md).
