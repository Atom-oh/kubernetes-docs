# Administración de clústeres de Kubernetes

> **Versiones compatibles**: Kubernetes 1.34 (Publicado el 2025-11-24)
> **Última actualización**: 23 de febrero de 2026

La administración de clústeres de Kubernetes es una tarea importante que incluye la configuración, el mantenimiento, la supervisión, la resolución de problemas y las actualizaciones del clúster. En este capítulo, exploraremos diversos aspectos de la administración de clústeres de Kubernetes y las prácticas recomendadas para la gestión de clústeres en Amazon EKS.

## Conceptos básicos

- **Gestión del ciclo de vida del clúster**: Todo el proceso, desde la creación del clúster hasta su retirada
- **Gestión del plano de control**: Gestión de componentes principales como el servidor de API, el scheduler y el controller manager
- **Gestión de nodos**: Incorporación, eliminación y mantenimiento de nodos de trabajo
- **Asignación de recursos**: Configuración de la asignación y los límites de recursos para CPU, memoria, almacenamiento, etc.
- **Estrategia de actualización**: Estrategias de actualización del clúster y de las aplicaciones para minimizar el tiempo de inactividad

## Tabla de contenido
1. [Descripción general de la administración de clústeres](#cluster-administration-overview)
2. [Gestión de componentes del clúster](#cluster-component-management)
3. [Gestión de recursos](#resource-management)
4. [Redes del clúster](#cluster-networking)
5. [Gestión de autenticación y autorización](#authentication-and-authorization-management)
6. [Actualizaciones del clúster](#cluster-upgrades)
7. [Copia de seguridad y recuperación](#backup-and-recovery)
8. [Supervisión y registro](#monitoring-and-logging)
9. [Resolución de problemas](#troubleshooting)
10. [Administración de clústeres de Amazon EKS](#amazon-eks-cluster-administration)
11. [Prácticas recomendadas para la administración de clústeres](#cluster-administration-best-practices)
12. [Conclusión](#conclusion)

## Configuración del entorno

Las siguientes herramientas son necesarias para la administración del clúster:

```bash
# Install kubectl (Linux)
curl -LO "https://dl.k8s.io/release/v1.33.3/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Install kubeadm (for cluster creation and management)
sudo apt-get update && sudo apt-get install -y kubeadm=1.33.3-00

# Install Helm (for package management)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install k9s (cluster management UI)
curl -sS https://webinstall.dev/k9s | bash
```

## Descripción general de la administración de clústeres

La administración de clústeres de Kubernetes es el proceso de gestionar todo el ciclo de vida de un clúster. Incluye las siguientes áreas principales:

1. **Configuración y ajuste del clúster**: Creación del clúster, incorporación de nodos, configuración de redes, configuración de almacenamiento, etc.
2. **Gestión de operaciones**: Supervisión de recursos, optimización del rendimiento, planificación de capacidad, resolución de problemas
3. **Gestión de seguridad**: Autenticación, autorización, políticas de red, contextos de seguridad, etc.
4. **Actualizaciones y parches**: Actualizaciones de versión del clúster, aplicación de parches de seguridad
5. **Copia de seguridad y recuperación**: Copia de seguridad de datos del clúster, planificación de recuperación ante desastres

El siguiente diagrama muestra las áreas principales de la administración de clústeres de Kubernetes y las herramientas relacionadas:

## Gestión de componentes del clúster

Un clúster de Kubernetes consta de componentes del plano de control y componentes de nodo. Gestionar cada componente es fundamental para la estabilidad y el rendimiento del clúster.

### Gestión de componentes del plano de control

![Diagrama de árbol que muestra el plano de control de Kubernetes ramificándose en sus cinco componentes (servidor de API, etcd, scheduler, controller manager y cloud controller manager), cada uno junto con la responsabilidad operativa que asume: autenticación y autorización, copia de seguridad de datos, políticas de planificación, supervisión del estado de los controladores y gestión de recursos de la nube.](../.gitbook/assets/en-core-09-cluster-administration-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-0.html)

#### Gestión del servidor de API

El servidor de API es un componente central del plano de control que expone la API de Kubernetes.

```bash
# Check API server logs
kubectl logs -n kube-system kube-apiserver-<master-node-name>

# Check API server configuration (kubeadm cluster)
sudo cat /etc/kubernetes/manifests/kube-apiserver.yaml

# Check API server status
kubectl get --raw='/healthz'
```

#### Gestión de etcd

etcd es un almacén distribuido de clave-valor que guarda todos los datos del clúster de Kubernetes.

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
kubectl get componentstatuses

# Check system pod status
kubectl get pods -n kube-system

# Check node resource usage
kubectl top nodes
```

![Diagrama que muestra las cinco áreas de responsabilidad de un administrador de clústeres, cada una asociada con las herramientas utilizadas para llevarla a cabo.](../.gitbook/assets/en-core-09-cluster-administration-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-1.html)

### Herramientas de administración de clústeres

Hay diversas herramientas disponibles para la administración de clústeres de Kubernetes:

1. **kubectl**: Herramienta de línea de comandos para interactuar con clústeres de Kubernetes
2. **kubeadm**: Herramienta para crear y gestionar clústeres de Kubernetes
3. **kops**: Herramienta para crear, actualizar y gestionar clústeres de Kubernetes
4. **eksctl**: Herramienta para crear y gestionar clústeres de Amazon EKS
5. **Helm**: Gestor de paquetes de aplicaciones de Kubernetes
6. **Kubernetes Dashboard**: Interfaz de usuario web de Kubernetes
7. **Prometheus & Grafana**: Herramientas de supervisión y alertas
8. **Fluentd & Elasticsearch**: Herramientas de registro

## Gestión de componentes del clúster

Un clúster de Kubernetes consta de varios componentes, y gestionarlos de forma eficaz es importante.

### Componentes del plano de control

Los componentes del plano de control gestionan el estado general del clúster:

1. **kube-apiserver**: Componente que expone la API de Kubernetes
2. **etcd**: Almacén de clave-valor que guarda los datos del clúster
3. **kube-scheduler**: Componente que programa pods en nodos
4. **kube-controller-manager**: Componente que ejecuta controladores
5. **cloud-controller-manager**: Componente que interactúa con proveedores de nube

El siguiente diagrama muestra los componentes del plano de control de Kubernetes y sus interacciones:

![Diagrama de arquitectura que muestra etcd, kube-scheduler, kube-controller-manager y cloud-controller-manager comunicándose bidireccionalmente con kube-apiserver en el centro, y el kubelet de un nodo de trabajo comunicándose bidireccionalmente con el servidor de API mientras gestiona kube-proxy y el runtime de contenedores.](../.gitbook/assets/en-core-09-cluster-administration-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-2.html)

#### Supervisión de componentes del plano de control

Es importante supervisar el estado de los componentes del plano de control:

```bash
# Check control plane component status
kubectl get componentstatuses

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check etcd status
kubectl exec -it -n kube-system etcd-<node-name> -- etcdctl endpoint health
```

#### Configuración de componentes del plano de control

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
    - --etcd-certfile=/etc/kubernetes/pki/etcd/apiserver-etcd-client.crt
    - --etcd-keyfile=/etc/kubernetes/pki/etcd/apiserver-etcd-client.key
    - --etcd-servers=https://127.0.0.1:2379
    - --kubelet-client-certificate=/etc/kubernetes/pki/apiserver-kubelet-client.crt
    - --kubelet-client-key=/etc/kubernetes/pki/apiserver-kubelet-client.key
    - --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname
    - --secure-port=6443
    - --service-account-key-file=/etc/kubernetes/pki/sa.pub
    - --service-cluster-ip-range=10.96.0.0/12
    - --tls-cert-file=/etc/kubernetes/pki/apiserver.crt
    - --tls-private-key-file=/etc/kubernetes/pki/apiserver.key
    image: k8s.gcr.io/kube-apiserver:v1.21.0
    name: kube-apiserver
```

### Componentes de nodo

Los componentes de nodo se ejecutan en cada nodo y gestionan pods:

1. **kubelet**: Agente que se ejecuta en cada nodo y garantiza que los pods y contenedores estén en ejecución
2. **kube-proxy**: Mantiene reglas de red y gestiona el reenvío de conexiones
3. **Container Runtime**: Software que ejecuta contenedores (Docker, containerd, CRI-O, etc.)

#### Gestión de nodos

Comandos principales para la gestión de nodos:

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
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

#### Resolución de problemas de nodos

Comandos para resolver problemas de nodos:

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

## Gestión de recursos

Gestionar eficazmente los recursos en un clúster de Kubernetes es importante para mantener la estabilidad y el rendimiento del clúster.

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

En el ejemplo anterior, el namespace `dev` puede tener un máximo de 10 pods, solicitudes de 1 CPU y 1Gi de memoria, y límites de 2 CPU y 2Gi de memoria.

### Rangos de límites

Los rangos de límites establecen valores predeterminados y límites para los recursos individuales dentro de un namespace:

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

En el ejemplo anterior, todos los contenedores del namespace `dev` tienen límites predeterminados de 500m de CPU y 512Mi de memoria, solicitudes predeterminadas de 200m de CPU y 256Mi de memoria, un máximo de 1 CPU y 1Gi de memoria, y un mínimo de 100m de CPU y 128Mi de memoria.

### Horizontal Pod Autoscaler (HPA)

HPA ajusta automáticamente el número de pods según el uso de CPU o métricas personalizadas:

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

En el ejemplo anterior, el Deployment `frontend` escala horizontalmente de forma automática cuando la utilización de CPU supera el 80 % y se reduce cuando está por debajo del 80 %. Mantiene un mínimo de 2 y un máximo de 10 réplicas.

### Vertical Pod Autoscaler (VPA)

VPA ajusta automáticamente las solicitudes de CPU y memoria de los pods:

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
    updateMode: "Auto"
```

En el ejemplo anterior, las solicitudes de CPU y memoria de los pods del Deployment `frontend` se ajustan automáticamente según el uso real de recursos.
## Redes del clúster

Las redes del clúster de Kubernetes gestionan la comunicación entre pods, servicios y nodos.

### Modelo de red del clúster

Requisitos básicos del modelo de red de Kubernetes:

1. Todos los pods pueden comunicarse con todos los demás pods sin NAT
2. Los agentes de nodo (kubelet) pueden comunicarse con todos los pods de ese nodo
3. Los pods que se ejecutan en modo NAT pueden comunicarse con el exterior

El siguiente diagrama muestra los componentes de red de Kubernetes y los flujos de comunicación:

![Diagrama de arquitectura que muestra el tráfico de cliente entrando a través de Ingress a un Service que equilibra la carga entre dos pods en nodos independientes, los cuales se comunican entre sí y acceden a un servicio externo.](../.gitbook/assets/en-core-09-cluster-administration-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-3.html)

### Plugins de CNI (Container Network Interface)

Kubernetes implementa las redes mediante plugins de CNI. Plugins de CNI comunes:

1. **Calico**: CNI con funciones mejoradas de políticas de red y seguridad
2. **Flannel**: Proporciona redes superpuestas sencillas
3. **Cilium**: Solución de redes y seguridad basada en eBPF
4. **AWS VPC CNI**: CNI integrado con AWS VPC
5. **Weave Net**: Solución de redes de contenedores multi-host

#### Instalación y configuración de plugins de CNI

Ejemplo de instalación de un plugin de CNI (Calico):

```bash
# Install Calico
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Check Calico status
kubectl get pods -n kube-system -l k8s-app=calico-node
```

### Redes de Service

Los servicios de Kubernetes proporcionan endpoints estables para conjuntos de pods:

1. **ClusterIP**: Service accesible solo dentro del clúster
2. **NodePort**: Service accesible mediante un puerto específico en todos los nodos
3. **LoadBalancer**: Service accesible mediante un balanceador de carga externo
4. **ExternalName**: Proporciona un registro CNAME para servicios externos

#### Configuración de CIDR de Service

El CIDR de Service define el rango de direcciones IP del servicio:

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

Las políticas de red controlan la comunicación entre pods:

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

En el ejemplo anterior, los pods con la etiqueta `role=db` solo permiten tráfico entrante TCP por el puerto 3306 desde pods con la etiqueta `role=frontend` y tráfico saliente TCP por el puerto 9090 hacia pods con la etiqueta `role=monitoring`.

## Gestión de autenticación y autorización

La gestión de autenticación y autorización de Kubernetes es un elemento central de la seguridad del clúster.

El siguiente diagrama muestra el flujo de autenticación y autorización de Kubernetes:

![Diagrama de arquitectura que muestra una solicitud pasando por autenticación, autorización y control de admisión antes de llegar al servidor de API, junto con los métodos concretos de autenticación y los modos de autorización que admite cada etapa.](../.gitbook/assets/en-core-09-cluster-administration-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-4.html)

### Autenticación

Kubernetes admite diversos métodos de autenticación:

1. **Certificados X.509**: Autenticación mediante certificados de cliente
2. **Tokens de Service Account**: Tokens JWT asociados con cuentas de servicio
3. **OpenID Connect (OIDC)**: Autenticación mediante proveedores de identidad externos
4. **Autenticación de tokens mediante Webhook**: Verificación de tokens mediante servicios externos
5. **Proxy de autenticación**: Procesamiento de solicitudes mediante proxy de autenticación

#### Gestión de certificados X.509

Creación y gestión de certificados X.509:

```bash
# Create Certificate Signing Request (CSR)
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

# Get certificate
kubectl get csr user-csr -o jsonpath='{.status.certificate}' | base64 --decode > user.crt
```

#### Configuración de autenticación OIDC

Ejemplo de configuración de autenticación OIDC:

```bash
# Add OIDC flags to kube-apiserver configuration
--oidc-issuer-url=https://accounts.google.com
--oidc-client-id=kubernetes
--oidc-username-claim=email
--oidc-groups-claim=groups
```

### Autorización

Kubernetes admite diversos modos de autorización:

1. **RBAC (Role-Based Access Control)**: Control de acceso basado en roles
2. **ABAC (Attribute-Based Access Control)**: Control de acceso basado en atributos
3. **Node**: Autorización de nodo
4. **Webhook**: Autorización mediante servicios externos

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

En el ejemplo anterior, `user` tiene permiso para ver pods en el namespace `default`.

#### ClusterRole y ClusterRoleBinding

Gestiona permisos para recursos de todo el clúster:

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

### Gestión de Service Account

Las cuentas de servicio son utilizadas por los pods para comunicarse con el servidor de API:

```yaml
# Create service account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default

# Grant permissions to service account
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

El contexto de seguridad define permisos y control de acceso para pods y contenedores:

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
  containers:
  - name: security-context-container
    image: nginx
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      readOnlyRootFilesystem: true
```

En el ejemplo anterior, el pod se ejecuta con UID 1000 y GID 3000, y el contenedor no puede escalar privilegios, tiene eliminadas todas las capacidades de Linux y tiene el sistema de archivos raíz montado como de solo lectura.

## Actualizaciones del clúster

Las actualizaciones del clúster de Kubernetes son necesarias para aplicar nuevas funciones, mejoras de rendimiento y parches de seguridad.

El siguiente diagrama muestra el proceso de actualización de un clúster de Kubernetes:

![Diagrama de flujo de una actualización de clúster de Kubernetes: planificación y comprobación de compatibilidad de versiones, copia de seguridad de etcd, actualización y prueba funcional del primer nodo del plano de control, actualización de los nodos restantes del plano de control y de trabajo, y validación del clúster que termina con la actualización completa, con una ruta de reversión que restaura desde la copia de seguridad cuando la validación detecta un problema.](../.gitbook/assets/en-core-09-cluster-administration-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-5.html)

### Planificación de actualizaciones

Consideraciones al planificar actualizaciones del clúster:

1. **Compatibilidad de versiones**: Compruebe la compatibilidad entre versiones de Kubernetes
2. **Ruta de actualización**: Compruebe las rutas de actualización admitidas
3. **Tiempo de inactividad**: Planifique el tiempo de inactividad esperado durante la actualización
4. **Plan de reversión**: Desarrolle un plan de reversión en caso de problemas
5. **Impacto en las aplicaciones**: Evalúe el impacto de las actualizaciones en las aplicaciones

### Actualización del plano de control

Actualización del plano de control mediante kubeadm:

```bash
# Check upgrade plan
kubeadm upgrade plan

# Upgrade first control plane node
ssh control-plane-1
sudo apt-get update
sudo apt-get install -y kubeadm=1.22.0-00
sudo kubeadm upgrade apply v1.22.0

# Upgrade additional control plane nodes
ssh control-plane-2
sudo apt-get update
sudo apt-get install -y kubeadm=1.22.0-00
sudo kubeadm upgrade node

# Upgrade kubelet and kubectl
sudo apt-get install -y kubelet=1.22.0-00 kubectl=1.22.0-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

### Actualización de nodos de trabajo

Proceso de actualización de nodos de trabajo:

```bash
# Drain node
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# SSH to node
ssh <node-name>

# Upgrade kubeadm
sudo apt-get update
sudo apt-get install -y kubeadm=1.22.0-00
sudo kubeadm upgrade node

# Upgrade kubelet and kubectl
sudo apt-get install -y kubelet=1.22.0-00 kubectl=1.22.0-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# Uncordon node
kubectl uncordon <node-name>
```

### Verificación de actualización

Verifique el estado del clúster después de la actualización:

```bash
# Check node versions
kubectl get nodes

# Check component status
kubectl get componentstatuses

# Check pod status
kubectl get pods --all-namespaces

# Test cluster functionality
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80
kubectl get svc nginx
```
## Copia de seguridad y recuperación

La copia de seguridad y recuperación de clústeres de Kubernetes es una parte importante de la planificación de recuperación ante desastres.

El siguiente diagrama muestra el proceso de copia de seguridad y recuperación de un clúster de Kubernetes:

![Diagrama de arquitectura que muestra snapshots programados de etcd y copias de seguridad de YAML de recursos llegando al almacenamiento de copias de seguridad, que posteriormente alimenta una restauración de etcd y una restauración de recursos durante la recuperación ante desastres.](../.gitbook/assets/en-core-09-cluster-administration-6.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-6.html)

### Copia de seguridad de etcd

etcd almacena toda la información de estado del clúster de Kubernetes, por lo que las copias de seguridad periódicas son importantes:

```bash
# Create etcd snapshot
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d-%H-%M-%S).db

# Check snapshot status
ETCDCTL_API=3 etcdctl --write-out=table snapshot status /backup/etcd-snapshot-2023-01-01-12-00-00.db
```

### Recuperación de etcd

Restauración desde un snapshot de etcd:

```bash
# Stop all Kubernetes services
sudo systemctl stop kubelet kube-apiserver kube-controller-manager kube-scheduler

# Backup etcd data directory
sudo mv /var/lib/etcd /var/lib/etcd.bak

# Restore from snapshot
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  --data-dir=/var/lib/etcd \
  --initial-cluster=master-1=https://192.168.1.10:2380 \
  --initial-cluster-token=etcd-cluster-1 \
  --initial-advertise-peer-urls=https://192.168.1.10:2380 \
  snapshot restore /backup/etcd-snapshot-2023-01-01-12-00-00.db

# Set permissions
sudo chown -R etcd:etcd /var/lib/etcd

# Restart Kubernetes services
sudo systemctl start etcd
sudo systemctl start kubelet kube-apiserver kube-controller-manager kube-scheduler
```

### Copia de seguridad de recursos

Realice copias de seguridad de recursos de Kubernetes como archivos YAML:

```bash
# Backup all resources in all namespaces
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  mkdir -p /backup/resources/$ns
  for resource in $(kubectl api-resources --namespaced=true -o name); do
    kubectl get -n $ns $resource -o yaml > /backup/resources/$ns/$resource.yaml
  done
done

# Backup cluster-scoped resources
mkdir -p /backup/resources/cluster-scoped
for resource in $(kubectl api-resources --namespaced=false -o name); do
  kubectl get $resource -o yaml > /backup/resources/cluster-scoped/$resource.yaml
done
```

### Automatización de copias de seguridad

Automatice las tareas de copia de seguridad con CronJob:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: etcd-backup
  namespace: kube-system
spec:
  schedule: "0 0 * * *"  # Run daily at midnight
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: etcd-backup
            image: bitnami/etcd:latest
            command:
            - /bin/sh
            - -c
            - |
              ETCDCTL_API=3 etcdctl --endpoints=https://etcd-client:2379 \
                --cacert=/etc/kubernetes/pki/etcd/ca.crt \
                --cert=/etc/kubernetes/pki/etcd/server.crt \
                --key=/etc/kubernetes/pki/etcd/server.key \
                snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d-%H-%M-%S).db
            volumeMounts:
            - name: etcd-certs
              mountPath: /etc/kubernetes/pki/etcd
              readOnly: true
            - name: backup
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: etcd-certs
            hostPath:
              path: /etc/kubernetes/pki/etcd
              type: Directory
          - name: backup
            persistentVolumeClaim:
              claimName: etcd-backup-pvc
```

## Supervisión y registro

La supervisión y el registro eficaces son elementos centrales de la administración de clústeres.

El siguiente diagrama muestra la arquitectura de supervisión y registro de clústeres de Kubernetes:

![Diagrama de arquitectura que muestra métricas del servidor de API y de nodos que fluyen mediante kube-state-metrics y Node Exporter hacia Prometheus, luego a Alertmanager y Grafana, mientras que los logs de los pods fluyen mediante Fluentd/Fluent Bit hacia Elasticsearch con Kibana y hacia Loki, que también alimenta a Grafana.](../.gitbook/assets/en-core-09-cluster-administration-7.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-7.html)

### Herramientas de supervisión

Herramientas para la supervisión de clústeres de Kubernetes:

1. **Prometheus**: Recopilación y almacenamiento de métricas
2. **Grafana**: Visualización de métricas
3. **Alertmanager**: Gestión de alertas
4. **kube-state-metrics**: Generación de métricas de objetos de Kubernetes
5. **metrics-server**: Proporciona métricas de uso de recursos

#### Instalación de Prometheus y Grafana

Instale Prometheus y Grafana mediante Helm:

```bash
# Add Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

#### Métricas de supervisión clave

Métricas clave que se deben supervisar:

1. **Métricas de nodo**: Uso de CPU, memoria, disco y red
2. **Métricas de Pod**: Uso de CPU y memoria, número de reinicios
3. **Métricas de contenedor**: Uso de CPU, memoria y sistema de archivos
4. **Métricas del servidor de API**: Latencia de solicitudes, número de solicitudes, tasa de errores
5. **Métricas de etcd**: E/S de disco, cambios de líder, latencia de confirmación

### Herramientas de registro

Herramientas para el registro de clústeres de Kubernetes:

1. **Elasticsearch**: Almacenamiento y búsqueda de logs
2. **Fluentd/Fluent Bit**: Recopilación y reenvío de logs
3. **Kibana**: Visualización de logs
4. **Loki**: Sistema de agregación de logs
5. **Grafana**: Visualización de logs

#### Instalación de la pila EFK (Elasticsearch, Fluentd, Kibana)

Instale la pila EFK mediante Helm:

```bash
# Install Elasticsearch
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace

# Install Fluentd
helm install fluentd fluent/fluentd \
  --namespace logging

# Install Kibana
helm install kibana elastic/kibana \
  --namespace logging \
  --set service.type=LoadBalancer
```

#### Configuración de recopilación de logs

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
        @type json
        time_format %Y-%m-%dT%H:%M:%S.%NZ
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

## Resolución de problemas

La resolución de problemas de clústeres de Kubernetes es una parte importante de la administración de clústeres.

### Resolución de problemas de Pods

Comandos para resolver problemas de pods:

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

### Resolución de problemas de nodos

Comandos para resolver problemas de nodos:

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

### Resolución de problemas de redes

Comandos para resolver problemas de redes:

```bash
# Check service status
kubectl get svc <service-name>

# Check service detailed information
kubectl describe svc <service-name>

# Check endpoints
kubectl get endpoints <service-name>

# Check DNS
kubectl run -it --rm --restart=Never busybox --image=busybox -- nslookup <service-name>

# Test network connectivity
kubectl run -it --rm --restart=Never busybox --image=busybox -- wget -O- <service-name>:<port>

# Check network policies
kubectl get networkpolicy
kubectl describe networkpolicy <policy-name>
```

### Resolución de problemas del plano de control

Comandos para resolver problemas del plano de control:

```bash
# Check component status
kubectl get componentstatuses

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check controller manager logs
kubectl logs -n kube-system kube-controller-manager-<node-name>

# Check scheduler logs
kubectl logs -n kube-system kube-scheduler-<node-name>

# Check etcd logs
kubectl logs -n kube-system etcd-<node-name>
```

## Administración de clústeres de Amazon EKS

Amazon EKS es un servicio administrado de Kubernetes que automatiza muchos aspectos de la administración de clústeres.

El siguiente diagrama muestra la arquitectura del clúster de Amazon EKS y los componentes de gestión:

![Diagrama de arquitectura que muestra a un usuario gestionando Amazon EKS mediante la consola, la CLI o la API de AWS, con EKS ejecutando un plano de control más grupos de nodos administrados y Fargate, el plano de control utilizando AWS IAM, VPC y CloudWatch, y los complementos VPC CNI, CoreDNS y kube-proxy.](../.gitbook/assets/en-core-09-cluster-administration-8.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-8.html)

### Configuración del clúster de EKS

Gestión de la configuración del clúster de EKS:

```bash
# Check EKS cluster information
aws eks describe-cluster --name my-cluster

# Update EKS cluster
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true

# Update EKS cluster version
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version 1.22
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

Gestión de complementos de EKS:

```bash
# Check available add-ons
aws eks describe-addon-versions \
  --kubernetes-version 1.22

# Install add-on
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.10.1-eksbuild.1

# Update add-on
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.10.2-eksbuild.1

# Delete add-on
aws eks delete-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni
```

### Actualización del clúster de EKS

Proceso de actualización del clúster de EKS:

1. **Actualización del plano de control**:
   ```bash
   aws eks update-cluster-version \
     --name my-cluster \
     --kubernetes-version 1.22
   ```

2. **Actualización de complementos**:
   ```bash
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni \
     --addon-version v1.10.2-eksbuild.1
   ```

3. **Actualización del grupo de nodos**:
   ```bash
   aws eks update-nodegroup-version \
     --cluster-name my-cluster \
     --nodegroup-name my-nodegroup
   ```

### Supervisión del clúster de EKS

Herramientas de supervisión del clúster de EKS:

1. **Amazon CloudWatch**: Métricas, logs, alertas
2. **AWS CloudTrail**: Registro de llamadas a la API
3. **Amazon Managed Grafana**: Visualización de métricas
4. **Amazon Managed Service for Prometheus**: Recopilación y almacenamiento de métricas

Habilite CloudWatch Container Insights:

```bash
# Enable Container Insights
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --approve
```

## Prácticas recomendadas para la administración de clústeres

Prácticas recomendadas para la administración de clústeres de Kubernetes y EKS:

### Prácticas recomendadas para la configuración del clúster

1. **Infrastructure as Code (IaC)**: Gestione la configuración del clúster mediante Terraform, AWS CDK, eksctl, etc.
2. **Control de versiones**: Almacene la configuración del clúster en sistemas de control de versiones
3. **Varios entornos**: Separe los entornos de desarrollo, staging y producción
4. **Separación de red**: Configure una separación de red y grupos de seguridad adecuados
5. **Principio de mínimo privilegio**: Conceda solo los permisos mínimos necesarios

### Prácticas recomendadas de operaciones

1. **Copias de seguridad periódicas**: Realice copias de seguridad periódicas de etcd y de recursos importantes
2. **Supervisión y alertas**: Cree sistemas integrales de supervisión y alertas
3. **Registro centralizado**: Centralice y analice los logs
4. **Automatización**: Automatice tareas repetitivas
5. **Planificación de recuperación ante desastres**: Establezca y pruebe planes claros de recuperación ante desastres

### Prácticas recomendadas de seguridad

1. **Actualizaciones periódicas**: Actualice periódicamente el clúster y los nodos
2. **Políticas de red**: Configure políticas de red adecuadas
3. **Cifrado**: Cifre los datos en reposo y en tránsito
4. **Contexto de seguridad**: Configure contextos de seguridad adecuados
5. **Escaneo de imágenes**: Analice imágenes de contenedor en busca de vulnerabilidades

### Prácticas recomendadas para la gestión de recursos

1. **Solicitudes y límites de recursos**: Configure solicitudes y límites de recursos adecuados para todos los pods
2. **Separación por namespace**: Separe las cargas de trabajo por namespace
3. **Cuotas de recursos**: Configure cuotas de recursos por namespace
4. **HPA y VPA**: Configure el autoescalado
5. **Afinidad de nodos y taints**: Optimice la ubicación de cargas de trabajo

### Prácticas recomendadas específicas de EKS

1. **Grupos de nodos administrados**: Use grupos de nodos administrados cuando sea posible
2. **Fargate**: Use Fargate para cargas de trabajo sin servidor
3. **Complementos de EKS**: Use complementos oficiales de EKS
4. **IAM Roles for Service Accounts (IRSA)**: Gestione permisos de IAM por pod
5. **Personalización de VPC CNI**: Configure VPC CNI conforme a los requisitos de red

## Conclusión

La administración de clústeres de Kubernetes desempeña un papel importante en el mantenimiento de la estabilidad, la seguridad y el rendimiento del clúster. Este capítulo abarcó diversos aspectos de la administración de clústeres, incluida la gestión de componentes del clúster, la gestión de recursos, las redes, la gestión de autenticación y autorización, las actualizaciones, la copia de seguridad y recuperación, la supervisión y el registro, y la resolución de problemas.

El uso de Amazon EKS reduce la complejidad de la gestión del plano de control de Kubernetes y simplifica la administración de clústeres mediante la integración con servicios de AWS. Sin embargo, comprender los conceptos fundamentales y las prácticas recomendadas de Kubernetes sigue siendo importante para una gestión eficaz del clúster.

La administración de clústeres es un proceso continuo que debe ajustarse constantemente según los requisitos del clúster y las características de las cargas de trabajo. Es importante utilizar herramientas de supervisión para rastrear el estado del clúster, minimizar las tareas repetitivas mediante automatización y seguir las prácticas recomendadas para mantener la estabilidad y seguridad del clúster.

## Redes del clúster

Las redes del clúster de Kubernetes gestionan la comunicación entre pods, el descubrimiento de servicios y el acceso externo.

### Arquitectura de red

![Diagrama de arquitectura que muestra las redes del clúster divididas en red de pods, red de servicios, ingress y políticas de red, implementadas respectivamente por un plugin de CNI, tipos de Service (ClusterIP, NodePort, LoadBalancer), un controlador de ingress y seguridad de red.](../.gitbook/assets/en-core-09-cluster-administration-9.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-9.html)

### Gestión de plugins de CNI

Los plugins de CNI (Container Network Interface) gestionan las redes de los clústeres de Kubernetes.

```bash
# Install Calico CNI
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Install Flannel CNI
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml

# Install Cilium CNI (using Helm)
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium --version 1.14.0 --namespace kube-system
```

### Comparación de plugins de CNI

| Plugin de CNI | Modelo de red | Compatibilidad con políticas de red | Rendimiento | Funciones |
|-----------|---------------|----------------------|-------------|----------|
| **Calico** | BGP | Sí | Alto | Potente en políticas de red, basado en enrutamiento |
| **Flannel** | VXLAN/host-gateway | No | Medio | Configuración sencilla, funciones limitadas |
| **Cilium** | eBPF | Sí | Muy alto | Políticas L3-L7, alto rendimiento |
| **Weave Net** | VXLAN | Sí | Medio | Compatibilidad con cifrado, multiclúster |
| **AWS VPC CNI** | AWS VPC | No | Alto | Optimizado para AWS EKS |

### Resolución de problemas de red

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
kubectl get endpoints <service-name>

# Check network policies
kubectl describe networkpolicy -n <namespace>
```
## Gestión de autenticación y autorización

La gestión de autenticación y autorización de Kubernetes es un elemento central de la seguridad del clúster. RBAC (Role-Based Access Control) se utiliza para gestionar permisos de usuarios y cuentas de servicio.

### Métodos de autenticación

Kubernetes admite diversos métodos de autenticación:

1. **Certificados X.509**: Autenticación mediante certificados de cliente
2. **Tokens de Service Account**: Se utilizan para acceder al servidor de API desde los pods
3. **OpenID Connect (OIDC)**: Integración con proveedores de identidad externos
4. **Autenticación de tokens mediante Webhook**: Integración con servicios de autenticación externos
5. **Proxy de autenticación**: Autenticación mediante proxy

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
  name: secret-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "watch", "list"]
```

```yaml
# clusterrolebinding.yaml - binding cluster role to user
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-secrets-global
subjects:
- kind: Group
  name: manager
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: secret-reader
  apiGroup: rbac.authorization.k8s.io
```

### Creación de certificados de usuario

```bash
# Generate private key
openssl genrsa -out jane.key 2048

# Create Certificate Signing Request (CSR)
openssl req -new -key jane.key -out jane.csr -subj "/CN=jane/O=dev"

# Sign certificate with Kubernetes CA
sudo openssl x509 -req -in jane.csr \
  -CA /etc/kubernetes/pki/ca.crt \
  -CAkey /etc/kubernetes/pki/ca.key \
  -CAcreateserial \
  -out jane.crt -days 365

# Add user to kubeconfig
kubectl config set-credentials jane --client-certificate=jane.crt --client-key=jane.key
kubectl config set-context jane-context --cluster=kubernetes --user=jane
```

### Gestión de Service Account

```bash
# Create service account
kubectl create serviceaccount app-service-account

# Bind role to service account
kubectl create rolebinding app-service-account-binding \
  --role=pod-reader \
  --serviceaccount=default:app-service-account

# Check service account token
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

Las actualizaciones del clúster de Kubernetes son necesarias para aplicar nuevas funciones, parches de seguridad y correcciones de errores. Las actualizaciones deben planificarse y ejecutarse cuidadosamente.

### Planificación de actualizaciones

![Diagrama de árbol que muestra la planificación de actualizaciones dividida en cuatro tareas: comprobar la compatibilidad de versiones, crear una copia de seguridad, elegir una estrategia de actualización y planificar el tiempo de inactividad; cada una conduce a una acción concreta: revisar los cambios de API, una copia de seguridad de etcd, in-place frente a blue/green y comunicación con los usuarios.](../.gitbook/assets/en-core-09-cluster-administration-10.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-10.html)

### Comparación de estrategias de actualización

| Estrategia | Descripción | Ventajas | Desventajas | Entorno adecuado |
|----------|-------------|------------|---------------|---------------------|
| **Actualización in-place** | Actualiza directamente el clúster existente | Uso eficiente de recursos, procedimiento simple | Reversión compleja, posible tiempo de inactividad | Entornos de desarrollo y prueba |
| **Despliegue blue/green** | Crea un clúster con la nueva versión y cambia a él | Reversión segura, verificable | Duplicación de recursos, mayor costo | Entornos de producción |
| **Despliegue canary** | Traslada solo algunas cargas de trabajo al nuevo clúster | Verificación gradual, menor riesgo | Gestión compleja, operación dual | Entornos de producción críticos |

### Actualización mediante kubeadm

```bash
# Check current version
kubeadm version

# Check upgrade plan
sudo kubeadm upgrade plan

# Control plane upgrade
sudo apt-get update
sudo apt-get install -y kubeadm=1.33.3-00
sudo kubeadm upgrade apply v1.33.3

# kubelet upgrade
sudo apt-get install -y kubelet=1.33.3-00 kubectl=1.33.3-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# Worker node upgrade (on each node)
# 1. Drain node
kubectl drain <node-name> --ignore-daemonsets

# 2. kubeadm upgrade
sudo apt-get update
sudo apt-get install -y kubeadm=1.33.3-00
sudo kubeadm upgrade node

# 3. kubelet upgrade
sudo apt-get install -y kubelet=1.33.3-00 kubectl=1.33.3-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# 4. Uncordon node
kubectl uncordon <node-name>
```

### Verificación posterior a la actualización

```bash
# Check cluster version
kubectl version

# Check node versions
kubectl get nodes

# Check component status
kubectl get componentstatuses

# Check workload status
kubectl get pods -A
```
## Copia de seguridad y recuperación

La copia de seguridad y recuperación de clústeres de Kubernetes es una parte importante de la planificación de recuperación ante desastres. Los principales objetivos de la copia de seguridad son la base de datos etcd, los datos de volúmenes persistentes y las definiciones de recursos de Kubernetes.

### Copia de seguridad y recuperación de etcd

etcd es un componente central que almacena toda la información de estado del clúster.

```bash
# etcd backup
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d).db

# etcd recovery
# 1. Stop cluster
sudo systemctl stop kubelet
sudo docker stop $(docker ps -q)

# 2. Restore etcd data
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  snapshot restore /backup/etcd-snapshot-2025-11-24.db \
  --data-dir=/var/lib/etcd-restore \
  --name=master \
  --initial-cluster=master=https://127.0.0.1:2380 \
  --initial-cluster-token=etcd-cluster-1 \
  --initial-advertise-peer-urls=https://127.0.0.1:2380

# 3. Configure to use restored data directory
sudo mv /var/lib/etcd /var/lib/etcd.bak
sudo mv /var/lib/etcd-restore /var/lib/etcd

# 4. Restart cluster
sudo systemctl start kubelet
```

### Copia de seguridad de recursos de Kubernetes

```bash
# Backup all resources in all namespaces
mkdir -p /backup/resources/$(date +%Y-%m-%d)
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  kubectl -n $ns get all -o yaml > /backup/resources/$(date +%Y-%m-%d)/$ns-all.yaml
done

# Backup specific resource types
for resource in deployments services configmaps secrets; do
  kubectl get $resource -A -o yaml > /backup/resources/$(date +%Y-%m-%d)/$resource.yaml
done
```

### Copia de seguridad y recuperación mediante Velero

Velero es una herramienta para realizar copias de seguridad y recuperar recursos de clústeres de Kubernetes y volúmenes persistentes.

```bash
# Install Velero (using AWS S3 backup storage)
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.7.0 \
  --bucket velero-backup \
  --backup-location-config region=us-west-2 \
  --snapshot-location-config region=us-west-2 \
  --secret-file ./credentials-velero

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

| Método de copia de seguridad | Objetivo de la copia | Ventajas | Desventajas | Tiempo de recuperación |
|--------------|---------------|------------|---------------|---------------|
| **Snapshot de etcd** | Estado del clúster | Función integrada, preservación completa del estado | No incluye datos de volúmenes, proceso manual | Medio |
| **Copia de seguridad de YAML de recursos** | Objetos de Kubernetes | Implementación sencilla, restauración selectiva | No incluye datos de volúmenes, complejidad de relaciones | Lento |
| **Velero** | Recursos y volúmenes | Automatización, programación, snapshots de volúmenes | Requiere instalación de herramienta adicional | Rápido |
| **Snapshots del proveedor de nube** | Clúster completo | Recuperación completa, integración con la nube | Dependencia de la nube, costo | Muy rápido |
## Supervisión y registro

La gestión eficaz de clústeres requiere un sistema integral de supervisión y registro. Esto permite detectar y resolver problemas con antelación.

### Arquitectura de supervisión

![Diagrama de arquitectura que muestra la supervisión de Kubernetes dividida en recopilación de métricas, recopilación de logs, alertas y visualización, gestionadas respectivamente por Prometheus con kube-state-metrics y node-exporter, Fluentd/Fluent Bit enviando logs a Elasticsearch y Kibana, Alertmanager y Grafana.](../.gitbook/assets/en-core-09-cluster-administration-11.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-11.html)

### Instalación de Prometheus y Grafana

```bash
# Install Prometheus and Grafana using Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.enabled=true \
  --set prometheus.service.type=NodePort

# Check services
kubectl get svc -n monitoring

# Access Grafana (using port forwarding)
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring
# Default username: admin, default password: prom-operator
```

### Instalación de la pila EFK (Elasticsearch, Fluentd, Kibana)

```bash
# Install Elasticsearch and Kibana
helm repo add elastic https://helm.elastic.co
helm repo update

helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace \
  --set replicas=1 \
  --set minimumMasterNodes=1

helm install kibana elastic/kibana \
  --namespace logging \
  --set service.type=NodePort

# Install Fluentd
kubectl apply -f https://raw.githubusercontent.com/fluent/fluentd-kubernetes-daemonset/master/fluentd-daemonset-elasticsearch.yaml
```

### Métricas de supervisión clave

| Tipo de métrica | Descripción | Métricas clave | Herramientas de supervisión |
|-------------|-------------|-------------|-----------------|
| **Métricas de nodo** | Uso de recursos a nivel de nodo | CPU, memoria, disco, red | node-exporter, Prometheus |
| **Métricas de Pod** | Uso de recursos de contenedor | Uso y límites de CPU y memoria | cAdvisor, Prometheus |
| **Métricas de clúster** | Estado y recursos del clúster | Número de pods, estado de nodos, eventos | kube-state-metrics |
| **Métricas de aplicación** | Métricas personalizadas de aplicaciones | Número de solicitudes, latencia, tasa de errores | Bibliotecas de cliente de Prometheus |

### Recopilación y análisis de logs

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

Puede configurar alertas mediante Prometheus Alertmanager:

```yaml
# alertmanager-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
      slack_api_url: 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'

    route:
      receiver: 'slack-notifications'
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      group_by: ['alertname', 'cluster', 'service']

    receivers:
    - name: 'slack-notifications'
      slack_configs:
      - channel: '#alerts'
        send_resolved: true
        title: "{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}"
        text: "{{ range .Alerts }}{{ .Annotations.description }}\n{{ end }}"
```
## Resolución de problemas

La resolución de problemas de clústeres de Kubernetes es una habilidad importante para administradores y operadores de sistemas. Para resolver problemas de forma eficaz se requiere un enfoque sistemático.

### Metodología de resolución de problemas

![Diagrama de flujo que muestra la secuencia de seis pasos para la resolución de problemas, desde la identificación del problema hasta la documentación, donde el paso de recopilación de información se ramifica en comprobaciones de logs, eventos y estado de recursos.](../.gitbook/assets/en-core-09-cluster-administration-12.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-12.html)

### Problemas y soluciones comunes

| Tipo de problema | Síntomas | Comandos de diagnóstico | Soluciones comunes |
|-------------|----------|---------------------|-----------------|
| **Pod no se inicia** | Pod en estado Pending o ContainerCreating | `kubectl describe pod <pod-name>` | Compruebe restricciones de recursos, disponibilidad de imagen y montajes de volúmenes |
| **Problemas de conexión de Service** | No se puede acceder a los pods mediante el servicio | `kubectl describe svc <service-name>`, `kubectl get endpoints <service-name>` | Compruebe selectores de etiquetas, estado de pods y políticas de red |
| **Problemas de nodo** | Nodo en estado NotReady | `kubectl describe node <node-name>`, `kubectl get events` | Compruebe el estado de kubelet, los recursos del sistema y la conectividad de red |
| **Problemas de DNS** | No se puede conectar por el nombre de servicio | `kubectl exec -it <pod-name> -- nslookup kubernetes.default` | Compruebe los pods de CoreDNS, el servicio kube-dns y las políticas de red |
| **Problemas de autenticación** | Acceso al servidor de API denegado | `kubectl auth can-i <verb> <resource>` | Compruebe la configuración de RBAC, la validez del certificado y la cuenta de servicio |

### Resolución de problemas de Pods

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

### Resolución de problemas de nodos

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

### Resolución de problemas de redes

```bash
# Check service and endpoints
kubectl get svc <service-name>
kubectl get endpoints <service-name>

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

Amazon EKS (Elastic Kubernetes Service) es un servicio administrado de Kubernetes en AWS donde AWS gestiona el plano de control. Sin embargo, la gestión de nodos, redes, seguridad, etc. es responsabilidad del usuario.

### Arquitectura del clúster de EKS

![Diagrama de arquitectura que muestra un clúster de Amazon EKS dividido en un plano de control administrado por AWS (servidor de API, etcd, scheduler) y un área de responsabilidad del cliente que cubre el plano de datos (grupos de nodos administrados con grupos de EC2 Auto Scaling, nodos autogestionados y Fargate), las redes (VPC CNI y AWS VPC) y la seguridad (autenticación de IAM con roles y políticas de IAM).](../.gitbook/assets/en-core-09-cluster-administration-13.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-13.html)

### Creación de clústeres de EKS

```bash
# Create cluster using eksctl
eksctl create cluster \
  --name my-cluster \
  --version 1.33 \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --managed

# Create cluster using AWS CLI
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/eks-cluster-role \
  --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345
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
eksctl update nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --region us-west-2 \
  --max-pods-per-node 110
```

### Actualización del clúster de EKS

```bash
# Check cluster version
aws eks describe-cluster --name my-cluster --query "cluster.version"

# Upgrade cluster control plane
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version 1.33

# Upgrade managed node group
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

### Autenticación y autorización del clúster de EKS

```bash
# Map IAM user/role to cluster RBAC
eksctl create iamidentitymapping \
  --cluster my-cluster \
  --arn arn:aws:iam::123456789012:role/admin-role \
  --group system:masters \
  --username admin

# Check aws-auth ConfigMap
kubectl describe configmap aws-auth -n kube-system
```

### Supervisión del clúster de EKS

```bash
# Enable CloudWatch Container Insights
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --region us-west-2

# Install Prometheus and Grafana (using Amazon EKS add-on)
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name amazon-cloudwatch-observability \
  --addon-version v1.1.1-eksbuild.1
```
## Prácticas recomendadas para la administración de clústeres

Las prácticas recomendadas para una gestión eficaz de clústeres de Kubernetes son importantes para garantizar la estabilidad, la seguridad y el rendimiento.

### Prácticas recomendadas para la configuración del clúster

1. **Configuración de múltiples zonas de disponibilidad**: Distribuya nodos entre varias zonas de disponibilidad para obtener alta disponibilidad
2. **Dimensionamiento adecuado**: Seleccione tipos y cantidades de nodos adecuados para las cargas de trabajo
3. **Configuración de autoescalado**: Habilite el autoscaler de clúster y el Horizontal Pod Autoscaler
4. **Aplicar políticas de red**: Comience con una política predeterminada de denegación y permita solo la comunicación necesaria
5. **Configurar cuotas de recursos**: Configure límites de recursos por namespace

### Prácticas recomendadas de operaciones

1. **Usar configuración declarativa**: Defina todos los recursos como archivos YAML y contrólelos por versiones
2. **Adoptar GitOps**: Use Git como única fuente de verdad y cree pipelines de despliegue automatizados
3. **Copias de seguridad periódicas**: Realice copias de seguridad periódicas de datos de etcd y de volúmenes persistentes
4. **Supervisión y alertas**: Cree sistemas integrales de supervisión y establezca alertas para métricas clave
5. **Registro centralizado**: Recopile todos los logs en un sistema de registro central para facilitar el análisis

### Prácticas recomendadas de seguridad

1. **Principio de mínimo privilegio**: Conceda solo los permisos mínimos necesarios mediante RBAC
2. **Segmentación de red**: Limite la comunicación entre pods mediante políticas de red
3. **Escaneo de imágenes**: Implemente el escaneo de imágenes de contenedor para detectar vulnerabilidades
4. **Gestión de secretos**: Use herramientas externas de gestión de secretos (por ejemplo, AWS Secrets Manager, HashiCorp Vault)
5. **Auditorías de seguridad periódicas**: Realice auditorías periódicas de la configuración y los permisos del clúster

### Prácticas recomendadas para actualizaciones

1. **Actualizaciones graduales**: Actualice gradualmente en lugar de hacerlo todo de una vez
2. **Primero el entorno de prueba**: Verifique las actualizaciones en entornos de prueba antes de producción
3. **Crear copias de seguridad**: Realice copias de seguridad completas antes de las actualizaciones
4. **Plan de reversión**: Desarrolle un plan para volver a versiones anteriores en caso de problemas
5. **Establecer ventanas de actualización**: Realice actualizaciones durante períodos de poco uso

### Prácticas recomendadas de optimización de costos

1. **Seleccionar tamaños de nodo adecuados**: Seleccione tipos de nodo óptimos para las cargas de trabajo
2. **Utilizar instancias Spot**: Use instancias Spot para cargas de trabajo no críticas
3. **Configurar autoescalado**: Configure el escalado automático ascendente y descendente según la demanda
4. **Optimizar solicitudes y límites de recursos**: Configure solicitudes y límites de recursos según el uso real
5. **Identificar recursos inactivos**: Identifique y elimine periódicamente recursos inactivos

### Prácticas recomendadas de documentación

1. **Documentar la arquitectura**: Documente la arquitectura del clúster y la configuración de redes y seguridad
2. **Documentar procedimientos operativos**: Documente tareas operativas comunes, procedimientos de resolución de problemas y planes de respuesta ante emergencias
3. **Gestión de cambios**: Registre y haga seguimiento de todos los cambios del clúster
4. **Crear runbooks**: Proporcione guías paso a paso para escenarios comunes
5. **Intercambio de conocimientos**: Realice sesiones periódicas de intercambio de conocimientos y capacitación dentro del equipo
## Conclusión

La administración de clústeres de Kubernetes es una tarea compleja que incluye diversos aspectos. Se requiere un enfoque sistemático desde la configuración del clúster hasta la operación, supervisión, resolución de problemas y actualizaciones.

Para una administración eficaz de clústeres, concéntrese en las siguientes áreas clave:

1. **Gestión de componentes del clúster**: Operación estable de los componentes del plano de control y de nodo
2. **Gestión de recursos**: Asignación y uso eficientes de los recursos
3. **Redes**: Configuración de red segura y eficiente
4. **Seguridad**: Gestión adecuada de autenticación y autorización
5. **Copia de seguridad y recuperación**: Prevención de pérdida de datos y planificación de recuperación ante desastres
6. **Supervisión y registro**: Supervisión del estado y rendimiento del clúster
7. **Resolución de problemas**: Enfoque sistemático para la resolución de problemas

Al utilizar servicios administrados de Kubernetes como Amazon EKS, es importante comprender el modelo de responsabilidad compartida entre el proveedor de servicios y el usuario. Aunque AWS gestiona el plano de control, la gestión de nodos, redes, seguridad, etc. sigue siendo responsabilidad del usuario.

Al seguir las prácticas recomendadas y utilizar las herramientas adecuadas, puede operar un clúster de Kubernetes estable, seguro y eficiente. El aprendizaje y la mejora continuos para mejorar las capacidades de gestión de clústeres son importantes.

---

> **Referencias**:
> - [Documentación oficial de Kubernetes: Administración de clústeres](https://kubernetes.io/docs/tasks/administer-cluster/)
> - [Guía del usuario de Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
> - [Prácticas recomendadas de Kubernetes: Administración de clústeres](https://kubernetes.io/docs/setup/best-practices/)
> - [Documentación de etcd: Copia de seguridad y recuperación](https://etcd.io/docs/v3.5/op-guide/recovery/)
> - [Documentación de Prometheus](https://prometheus.io/docs/introduction/overview/)

## Cuestionario

Para comprobar lo aprendido en este capítulo, pruebe el [Cuestionario de administración de clústeres](../quizzes/core/09-cluster-administration-quiz.md).
