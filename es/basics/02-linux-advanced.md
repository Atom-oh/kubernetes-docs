# Habilidades de operaciones de Linux

> **Versiones compatibles**: Bash en distribuciones de Linux con mantenimiento; los comandos presuponen que las herramientas indicadas están instaladas **Última actualización**: 16 de octubre de 2026

Este documento cubre habilidades esenciales de operaciones de Linux para trabajar eficazmente en entornos de Kubernetes.

***

## Tabla de contenido

1. [Variables de entorno y configuración del shell](02-linux-advanced.md#1-environment-variables-and-shell-configuration)
2. [Conceptos básicos de scripting de shell](02-linux-advanced.md#2-shell-scripting-basics)
3. [Herramientas de procesamiento de texto](02-linux-advanced.md#3-text-processing-tools)
4. [SSH y acceso remoto](02-linux-advanced.md#4-ssh-and-remote-access)
5. [Supervisión del rendimiento y solución de problemas](02-linux-advanced.md#5-performance-monitoring-and-troubleshooting)
6. [Conceptos básicos de administración del almacenamiento](02-linux-advanced.md#6-storage-management-basics)
7. [curl y llamadas a API](02-linux-advanced.md#7-curl-and-api-calls)
8. [Colección de one-liners prácticos](02-linux-advanced.md#8-practical-one-liners-collection)

***

<span id="1-environment-variables-and-shell-configuration"></span>

## 1. Variables de entorno y configuración del shell

Las variables de entorno son el mecanismo principal para administrar la configuración en Linux y Kubernetes.

### 1.1 Conceptos básicos de las variables de entorno

```bash
env
echo "$HOME"
echo "$PATH"
printenv HOME
```

### 1.2 El comando export

```bash
export MY_VAR="hello"
export DATABASE_URL="postgresql://localhost:5432/mydb"
export KUBECONFIG="/home/user/.kube/config"
```

### 1.3 El comando source

```bash
cat > ~/my-env.sh << 'SCRIPT'
export APP_ENV="production"
export APP_PORT="8080"
alias k='kubectl'
SCRIPT

source ~/my-env.sh
```

### 1.4 .bashrc y .bash\_profile

Bash interactivo que no es de inicio de sesión lee .bashrc; Bash de inicio de sesión lee el primer archivo disponible entre .bash_profile/.bash_login/.profile. Un perfil de inicio de sesión puede cargar explícitamente .bashrc. Añada el bloque siguiente una sola vez.

```bash
cat >> ~/.bashrc << 'SCRIPT'
export KUBECONFIG=~/.kube/config
command -v kubectl >/dev/null && source <(kubectl completion bash)
alias k='kubectl'
SCRIPT

source ~/.bashrc
```

### 1.5 Conexión con ConfigMap de Kubernetes

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  DATABASE_HOST: "mysql.default.svc.cluster.local"
  DATABASE_PORT: "3306"
---
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    envFrom:
    - configMapRef:
        name: app-config
```

***

<span id="2-shell-scripting-basics"></span>

## 2. Conceptos básicos de scripting de shell

### 2.1 Variables

```bash
#!/bin/bash
NAME="kubernetes"
NAMESPACE=${1:-default}
: "${REQUIRED_VAR:?REQUIRED_VAR must be set}"
```

### 2.2 Condicionales

```bash
if [ "$ENV" = "production" ]; then
    echo "Production mode"
fi

case "$1" in
    start) echo "Starting..." ;;
    stop) echo "Stopping..." ;;
esac
```

### 2.3 Bucles

```bash
for ns in default kube-system monitoring; do
    kubectl get pods -n "$ns"
done

# Running phase does not imply readiness. A bounded wait propagates API errors/timeouts.
kubectl wait --for=condition=Ready pod/mypod --timeout=120s
```

### 2.4 Funciones

```bash
check_pod_exists() {
    local pod_name=${1:?Pod name required}
    local namespace=${2:-default}
    # Nonzero also includes authorization/connection errors; inspect stderr.
    kubectl get pod "$pod_name" -n "$namespace" -o name >/dev/null
}
```

### 2.5 Patrones de contenedores de inicialización

Este ejemplo de bucle acotado espera a que se resuelva el DNS. Que el DNS funcione no implica que la base de datos esté lista; la aplicación necesita reintentos de conexión o una comprobación de disponibilidad específica de la base de datos. Prepare el Service mysql y la imagen personalizada myapp. Kubelet puede reiniciar un contenedor de inicialización que haya fallado, por lo que este mecanismo es distinto de un plazo límite total para iniciar el Pod.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-init
spec:
  initContainers:
  - name: wait-for-db-dns
    image: busybox:1.38.0
    command:
    - sh
    - -c
    - |
      for attempt in $(seq 1 60); do
        nslookup mysql.default.svc.cluster.local >/dev/null 2>&1 && exit 0
        sleep 2
      done
      echo "Database Service DNS did not become available" >&2
      exit 1
  containers:
  - name: app
    image: myapp:1.0
```

***

<span id="3-text-processing-tools"></span>

## 3. Herramientas de procesamiento de texto

### 3.1 grep con kubectl

```bash
kubectl get pods --field-selector=status.phase!=Running
kubectl logs nginx-pod | grep -i error
```

### 3.2 Extracción de campos con awk

```bash
kubectl get pods | awk 'NR>1 {print $1}'
kubectl get pods --no-headers | awk '$3 != "Running" {print $1, $3}'
```

### 3.3 Edición con sed

```bash
# Text-only preview; this can match more than the intended YAML field.
sed 's/replicas: [0-9]*/replicas: 5/' deployment.yaml
# For a structured edit, use the yq example below.
```

### 3.4 Análisis de JSON con jq

```bash
kubectl get pod nginx -o json | jq '.metadata.name'
kubectl get pods -o json | jq -r '.items[].metadata.name'
```

### 3.5 Análisis de YAML con yq

Estos ejemplos usan Mike Farah yq v4; Python yq tiene opciones distintas.

```bash
yq '.metadata.name' deployment.yaml
yq -i '.spec.replicas = 5' deployment.yaml
```

***

<span id="4-ssh-and-remote-access"></span>

## 4. SSH y acceso remoto

### 4.1 Generación de claves SSH

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 4.2 Túneles SSH

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8080:localhost:80 user@server
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:6443:kubernetes-api:6443 user@bastion
```

En los túneles de API, conserve la CA original y el nombre del servidor TLS en kubeconfig. Al conectarse a 127.0.0.1, establezca tls-server-name con el nombre real del servidor incluido en el certificado de la API; mantenga habilitada la verificación TLS.

### 4.3 Uso de un host bastión

```bash
ssh -J bastion user@internal-server
```

### 4.4 rsync

```bash
rsync -avzP ./local/ user@remote:/path/
```

***

<span id="5-performance-monitoring-and-troubleshooting"></span>

## 5. Supervisión del rendimiento y solución de problemas

### 5.1 top y htop

```bash
top -b -n 1 | head -20
```

### 5.2 vmstat e iostat

```bash
vmstat 1 5
iostat -dx 1 5
```

### 5.3 free y df

```bash
free -h
df -h
```

### 5.4 kubectl top

Requiere un proveedor de metrics.k8s.io, como Metrics Server; kubectl top no es un sistema de supervisión histórica.

```bash
kubectl top nodes
kubectl top pods --sort-by=memory
```

***

<span id="6-storage-management-basics"></span>

## 6. Conceptos básicos de administración del almacenamiento

### 6.1 lsblk

```bash
lsblk -f
```

### 6.2 LVM

```bash
# Use only an explicitly selected empty training disk. These commands write storage metadata.
: "${LAB_DISK:?Set an unused lab block device after checking lsblk and backups}"
lsblk -f "$LAB_DISK"
sudo wipefs --no-act "$LAB_DISK"
# Stop if the disk contains data, mounted filesystems, or existing volume metadata.
sudo pvcreate "$LAB_DISK"
sudo vgcreate data_vg "$LAB_DISK"
sudo lvcreate -l 100%FREE -n data_lv data_vg
```

### 6.3 PV/PVC de Kubernetes

La ruta y el nombre de host indicados a continuación deben coincidir con el nodo donde está montado el sistema de archivos existente.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-storage
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: local-pv
spec:
  capacity:
    storage: 100Gi
  accessModes: [ReadWriteOnce]
  storageClassName: local-storage
  persistentVolumeReclaimPolicy: Retain
  local:
    path: /mnt/disks/vol1
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values: [replace-with-actual-node-hostname]
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: local-pvc
spec:
  storageClassName: local-storage
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 10Gi
```

***

Si un nodo falla, el almacenamiento local no se puede mover a otro nodo. Esta StorageClass no aprovisiona discos; el PVC puede permanecer en estado Pending hasta que se programe un Pod consumidor. Ajuste la capacidad del PV al sistema de archivos real: el valor anunciado no constituye una cuota de directorio. La limpieza y reutilización de recursos retenidos son acciones independientes que debe realizar el operador.

<span id="7-curl-and-api-calls"></span>

## 7. curl y llamadas a API

### 7.1 Métodos HTTP

```bash
curl -X POST -H "Content-Type: application/json" -d '{"name":"John"}' https://api.example.com/users
```

### 7.2 Llamadas a la API de Kubernetes

```bash
# Run inside a Pod with projected ServiceAccount credentials and curl installed.
set -e
SERVICEACCOUNT=/var/run/secrets/kubernetes.io/serviceaccount
CACERT="$SERVICEACCOUNT/ca.crt"
NAMESPACE=$(cat "$SERVICEACCOUNT/namespace")
TOKEN=$(cat "$SERVICEACCOUNT/token")
curl --fail --silent --show-error --cacert "$CACERT" \
  -H "Authorization: Bearer $TOKEN" \
  "https://kubernetes.default.svc/api/v1/namespaces/$NAMESPACE/pods"
unset TOKEN
```

El ServiceAccount necesita permisos RBAC para listar Pods en ese espacio de nombres. Es posible que estos archivos no estén montados si automountServiceAccountToken: false. Los tokens proyectados se renuevan, por lo que los clientes de larga duración deben volver a leer el archivo; no registre tokens.

### 7.3 Opciones útiles de curl

```bash
curl --silent --show-error -o /dev/null -w "%{http_code}\n" https://api.example.com/health
```

***

<span id="8-practical-one-liners-collection"></span>

## 8. Colección de one-liners prácticos

### 8.1 Operaciones de Kubernetes

```bash
kubectl get pods -A | awk '$4 != "Running" && NR>1 {print $1, $2, $4}'
kubectl get pods -A -o json | jq -r '.items[] | select(any((.status.containerStatuses // [])[]; .restartCount > 5)) | [.metadata.namespace, .metadata.name] | @tsv'
```

### 8.2 Análisis de registros

```bash
kubectl logs deploy/app --since=1h | grep -i error
```

### 8.3 Depuración de redes

```bash
nslookup kubernetes.default.svc.cluster.local
nc -zv service-name 80
```

***

## Conclusión

1. **Variables de entorno**: Base para ConfigMap/Secret de K8s
2. **Scripting de shell**: Esencial para contenedores de inicialización y comprobaciones de estado
3. **Procesamiento de texto**: Fundamental para analizar la salida de kubectl
4. **SSH**: Importante para depurar nodos
5. **Supervisión del rendimiento**: Base para la solución de problemas

***

[Anterior: Conceptos básicos de Linux](01-linux-basics.md) | [Siguiente: Conceptos básicos de contenedores](03-container-technology.md)

## Referencias de verificación

- https://kubernetes.io/docs/concepts/storage/volumes/#local
- https://kubernetes.io/docs/concepts/storage/storage-classes/#local
- https://kubernetes.io/docs/tasks/run-application/access-api-from-pod/
- https://kubernetes.io/docs/concepts/configuration/configmap/
- https://kubernetes.io/docs/reference/kubectl/generated/kubectl_wait/
- https://www.gnu.org/software/bash/manual/html_node/Shell-Parameter-Expansion.html
- https://www.gnu.org/software/bash/manual/html_node/Bash-Startup-Files.html
- https://download.samba.org/pub/rsync/rsync.1
- https://github.com/mikefarah/yq
- https://busybox.net/downloads/BusyBox.html
- https://github.com/docker-library/official-images/blob/master/library/busybox
