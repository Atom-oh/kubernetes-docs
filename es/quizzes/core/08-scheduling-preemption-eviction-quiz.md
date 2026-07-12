## Preguntas de respuesta corta

1. Explica el procedimiento para hacer una copia de seguridad y restaurar la base de datos etcd en un cluster de Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Procedimiento de copia de seguridad de etcd:**

1. **Verificar la instalación de la herramienta etcdctl:**
   ```bash
   etcdctl version
   ```

2. **Ejecutar el comando de copia de seguridad:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
     --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key
   ```

3. **Verificar el archivo de copia de seguridad:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot status snapshot.db --write-out=table
   ```

4. **Almacenar el archivo de copia de seguridad en una ubicación segura:**
   - Almacenamiento externo al cluster
   - Almacenamiento en la nube (S3, GCS, etc.)
   - Ubicación física diferente

**Procedimiento de restauración de etcd:**

1. **Detener todos los API servers para la restauración:**
   ```bash
   sudo systemctl stop kube-apiserver
   ```

2. **Detener el servicio etcd:**
   ```bash
   sudo systemctl stop etcd
   ```

3. **Hacer una copia de seguridad del directorio de datos (opcional):**
   ```bash
   sudo mv /var/lib/etcd /var/lib/etcd.bak
   ```

4. **Crear un nuevo directorio de datos desde el snapshot:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \
     --data-dir=/var/lib/etcd-restore \
     --name=master \
     --initial-cluster=master=https://127.0.0.1:2380 \
     --initial-cluster-token=etcd-cluster-1 \
     --initial-advertise-peer-urls=https://127.0.0.1:2380
   ```

5. **Configurar etcd para usar el directorio de datos restaurado:**
   ```bash
   sudo mv /var/lib/etcd-restore /var/lib/etcd
   sudo chown -R etcd:etcd /var/lib/etcd
   ```

6. **Reiniciar el servicio etcd:**
   ```bash
   sudo systemctl start etcd
   ```

7. **Verificar el estado de etcd:**
   ```bash
   ETCDCTL_API=3 etcdctl endpoint health \
     --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key
   ```

8. **Reiniciar el API server:**
   ```bash
   sudo systemctl start kube-apiserver
   ```

9. **Verificar el estado del cluster:**
   ```bash
   kubectl get nodes
   kubectl get pods --all-namespaces
   ```

**Mejores prácticas:**
- Configurar un calendario regular de copias de seguridad (por ejemplo, diario)
- Verificar el estado del cluster de etcd antes de la copia de seguridad
- Verificar la integridad del archivo de copia de seguridad
- Probar regularmente el procedimiento de restauración
- Incluir una marca de tiempo en los archivos de copia de seguridad
- Mantener varias versiones de copias de seguridad
- Documentar los procedimientos de copia de seguridad y restauración
</details>

2. Explica el procedimiento para el mantenimiento de nodos en un cluster de Kubernetes y las diferencias entre los comandos `cordon`, `drain` y `uncordon`.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Procedimiento de mantenimiento de nodos:**

1. **Comprobar el estado del nodo:**
   ```bash
   kubectl get nodes
   kubectl describe node <node_name>
   ```

2. **Aplicar cordon al nodo:**
   ```bash
   kubectl cordon <node_name>
   ```

3. **Aplicar drain al nodo:**
   ```bash
   kubectl drain <node_name> --ignore-daemonsets --delete-emptydir-data
   ```

4. **Realizar el mantenimiento:**
   - Actualizaciones de software
   - Actualizaciones del kernel
   - Reemplazo de hardware
   - Cambios de configuración

5. **Aplicar uncordon al nodo después de completar el trabajo:**
   ```bash
   kubectl uncordon <node_name>
   ```

6. **Verificar el estado del nodo:**
   ```bash
   kubectl get nodes
   ```

**Diferencias entre comandos:**

1. **`kubectl cordon <node_name>`:**
   - Marca el nodo como no programable.
   - Los nuevos pods no se programarán en el nodo.
   - Los pods que ya se están ejecutando continúan ejecutándose.
   - El indicador `SchedulingDisabled` aparece en el estado del nodo.

2. **`kubectl drain <node_name>`:**
   - Marca el nodo como no programable (incluye cordon).
   - Desaloja de forma segura los pods que se ejecutan en el nodo.
   - Los pods se reprograman en otros nodos.
   - Los pods de DaemonSet se ignoran de forma predeterminada (se requiere la bandera `--ignore-daemonsets`).
   - Los pods que usan volúmenes emptyDir pueden perder datos, por lo que requieren manejo especial (bandera `--delete-emptydir-data`).
   - Respeta los PodDisruptionBudgets.

3. **`kubectl uncordon <node_name>`:**
   - Vuelve a marcar el nodo como programable.
   - Los nuevos pods pueden programarse en el nodo.
   - Los pods desalojados previamente no regresan automáticamente.

**Consideraciones de mantenimiento:**
- Asegurar capacidad suficiente en el cluster
- Configurar PodDisruptionBudgets para workloads críticos
- Mantener solo un nodo a la vez
- Ajustar la configuración de autoscaling durante el período de mantenimiento
- Verificar el estado de los workloads antes y después del mantenimiento
- Usar una estrategia de rolling update
</details>

3. Explica cómo monitorear y gestionar el uso de recursos en un cluster de Kubernetes. Enumera las herramientas y técnicas que deberían incluirse.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Métodos de monitoreo y gestión de recursos de Kubernetes:**

**1. Herramientas básicas de monitoreo:**

- **Metrics Server:**
  - Proporciona métricas básicas de uso de CPU y memoria
  - Compatible con el comando `kubectl top`
  - Instalación:
    ```bash
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    ```
  - Uso:
    ```bash
    kubectl top nodes
    kubectl top pods --all-namespaces
    ```

- **Kubernetes Dashboard:**
  - Representación visual del estado del cluster y del uso de recursos
  - Proporciona una interfaz para gestionar pods, nodos, namespaces, etc.

**2. Stack de monitoreo avanzado:**

- **Prometheus + Grafana:**
  - Prometheus: recopilación y almacenamiento de métricas
  - Grafana: visualización de métricas y dashboards
  - Puede instalarse con kube-prometheus-stack o Prometheus Operator
  - Compatible con reglas de alerta y dashboards personalizados

- **Stack ELK/EFK:**
  - Elasticsearch: almacenamiento y búsqueda de logs
  - Logstash/Fluentd: recopilación y procesamiento de logs
  - Kibana: visualización y análisis de logs

**3. Técnicas de gestión de recursos:**

- **Configurar Resource Requests y Limits:**
  ```yaml
  resources:
    requests:
      memory: "64Mi"
      cpu: "250m"
    limits:
      memory: "128Mi"
      cpu: "500m"
  ```

- **Cuotas de recursos a nivel de namespace (ResourceQuota):**
  ```yaml
  apiVersion: v1
  kind: ResourceQuota
  metadata:
    name: compute-quota
    namespace: dev
  spec:
    hard:
      pods: "10"
      requests.cpu: "4"
      requests.memory: 8Gi
      limits.cpu: "8"
      limits.memory: 16Gi
  ```

- **Límites de recursos predeterminados (LimitRange):**
  ```yaml
  apiVersion: v1
  kind: LimitRange
  metadata:
    name: default-limits
    namespace: dev
  spec:
    limits:
    - default:
        cpu: 500m
        memory: 512Mi
      defaultRequest:
        cpu: 200m
        memory: 256Mi
      type: Container
  ```

- **Horizontal Pod Autoscaler (HPA):**
  ```yaml
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: web-app
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: web-app
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

- **Vertical Pod Autoscaler (VPA):**
  - Ajusta automáticamente los requests de CPU y memoria de los pods
  - Proporciona recomendaciones basadas en patrones de uso de recursos

- **Cluster Autoscaler:**
  - Ajusta automáticamente el número de nodos del cluster según los requisitos de los workloads
  - Añade nodos durante la escasez de recursos y elimina nodos durante la baja utilización

**4. Mejores prácticas de monitoreo:**

- Configurar resource requests y limits para todos los pods
- Configurar alertas para métricas importantes
- Planificar recursos mediante el análisis del uso histórico
- Realizar auditorías regulares de recursos
- Analizar tendencias de uso de recursos para optimizar costos
- Configurar cuotas de recursos adecuadas para entornos de desarrollo, staging y producción
- Monitorear métricas tanto a nivel de nodo como a nivel de pod
</details>

4. Explica los principales riesgos que pueden ocurrir durante las actualizaciones de un cluster de Kubernetes y las estrategias para mitigarlos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Riesgos y estrategias de mitigación en la actualización de clusters de Kubernetes:**

**1. Riesgos principales:**

- **Problemas de compatibilidad de API:**
  - Las APIs pueden cambiar o eliminarse en versiones nuevas
  - Algunas Custom Resource Definitions (CRDs) o versiones de API pueden dejar de ser compatibles

- **Interrupción de workloads:**
  - Indisponibilidad temporal del API server debido a reinicios de componentes del control plane
  - Interrupción de Service debido a la reprogramación de pods durante las actualizaciones de nodos

- **Cambios de funcionalidad:**
  - Los cambios en el comportamiento predeterminado pueden afectar los workloads existentes
  - Los cambios de políticas de seguridad pueden causar problemas de permisos

- **Problemas de rendimiento:**
  - Los requisitos de recursos pueden aumentar en las versiones nuevas
  - Posible degradación del rendimiento durante el período inicial de estabilización

- **Complejidad del rollback:**
  - Algunas actualizaciones no se pueden revertir fácilmente
  - Limitaciones de rollback debido a cambios en el formato de datos

**2. Estrategias de mitigación:**

- **Planificación y preparación exhaustivas:**
  - **Revisar el changelog:** comprobar cambios, funcionalidades obsoletas y problemas conocidos en la nueva versión
  - **Verificar la ruta de actualización:** confirmar que se admite la actualización directa desde la versión actual a la versión objetivo
  - **Revisar los requisitos de recursos:** comprobar los requisitos mínimos para la nueva versión

- **Probar primero en un entorno de pruebas:**
  - Realizar la actualización en un cluster de pruebas similar a producción
  - Probar todos los workloads críticos y recursos personalizados
  - Ejecutar suites de pruebas automatizadas

- **Verificar compatibilidad de API:**
  - Comprobar las versiones de API en uso:
    ```bash
    kubectl api-resources -o wide
    ```
  - Comprobar el uso de APIs obsoletas:
    ```bash
    kubectl get -A | grep "deprecated"
    ```
  - Actualizar los manifiestos según sea necesario

- **Plan de copia de seguridad y recuperación:**
  - Hacer copia de seguridad de la base de datos etcd:
    ```bash
    ETCDCTL_API=3 etcdctl snapshot save snapshot.db
    ```
  - Hacer copia de seguridad de todos los manifiestos importantes:
    ```bash
    kubectl get all --all-namespaces -o yaml > all-resources.yaml
    ```
  - Documentar y probar los procedimientos de recuperación

- **Enfoque de actualización gradual:**
  - **Actualizar primero los componentes del control plane:**
    - En configuraciones de alta disponibilidad, actualizar un nodo del control plane a la vez
  - **Actualización rolling de los worker nodes:**
    - Dividir los grupos de nodos en lotes pequeños para la actualización
    - Verificar la estabilidad después de cada lote

- **Protección de workloads:**
  - **Configurar PodDisruptionBudget:**
    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: app-pdb
    spec:
      minAvailable: 2  # or maxUnavailable: 1
      selector:
        matchLabels:
          app: my-app
    ```
  - **Tener cuidado al drenar nodos:**
    ```bash
    kubectl drain <node_name> --ignore-daemonsets --delete-emptydir-data
    ```

- **Monitoreo reforzado:**
  - Monitorear el estado del cluster antes, durante y después de la actualización
  - Observar de cerca métricas y logs clave
  - Ajustar temporalmente los umbrales de alerta

- **Plan de rollback:**
  - Definir condiciones que activen el rollback
  - Documentar procedimientos de rollback
  - Conservar todos los componentes e imágenes necesarios para el rollback

- **Plan de comunicación:**
  - Notificar a todos los stakeholders el calendario de actualización y el impacto esperado
  - Proporcionar actualizaciones de estado durante la actualización
  - Definir rutas de escalamiento en caso de problemas

**3. Consideraciones específicas por versión:**

- **Actualizaciones de versión menor (por ejemplo, 1.24 → 1.25):**
  - Prestar especial atención a APIs eliminadas y cambios de funcionalidad
  - Actualizar una versión menor a la vez

- **Actualizaciones de versión patch (por ejemplo, 1.24.0 → 1.24.1):**
  - Generalmente más seguras, pero aun así requieren pruebas
  - Considerar un despliegue más rápido para parches de seguridad
</details>

5. Explica los problemas de red comunes que pueden ocurrir en un cluster de Kubernetes y cómo diagnosticarlos y resolverlos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Diagnóstico y resolución de problemas de red de Kubernetes:**

**1. Problemas de comunicación Pod a Pod:**

- **Síntomas:**
  - Los Pods no pueden comunicarse con otros pods
  - No se puede conectar por nombre de service
  - Errores de timeout de red

- **Métodos de diagnóstico:**
  - Comprobar network policies:
    ```bash
    kubectl get networkpolicy --all-namespaces
    ```
  - Crear un pod de prueba para comprobar la conectividad:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    ping <target_pod_IP>
    wget -O- <service_name>:<port>
    ```
  - Comprobar el estado de los pods del plugin CNI:
    ```bash
    kubectl get pods -n kube-system | grep -E 'calico|flannel|weave|cilium'
    ```

- **Resolución:**
  - Reinstalar o actualizar el plugin CNI
  - Modificar o eliminar network policies
  - Comprobar las interfaces de red del nodo
  - Comprobar reglas de firewall

**2. Problemas de descubrimiento de Service y DNS:**

- **Síntomas:**
  - No se puede conectar por nombre de service
  - Fallos de resolución DNS
  - Problemas de conexión intermitentes

- **Métodos de diagnóstico:**
  - Comprobar el estado de los pods de CoreDNS:
    ```bash
    kubectl get pods -n kube-system -l k8s-app=kube-dns
    kubectl logs -n kube-system -l k8s-app=kube-dns
    ```
  - Probar la resolución DNS:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    nslookup kubernetes.default.svc.cluster.local
    nslookup <service_name>.<namespace>.svc.cluster.local
    cat /etc/resolv.conf
    ```
  - Comprobar endpoints del service:
    ```bash
    kubectl get endpoints <service_name>
    ```

- **Resolución:**
  - Reiniciar los pods de CoreDNS:
    ```bash
    kubectl rollout restart deployment coredns -n kube-system
    ```
  - Comprobar y modificar la configuración DNS:
    ```bash
    kubectl edit configmap coredns -n kube-system
    ```
  - Comprobar la configuración DNS de kubelet

**3. Problemas de Service e Ingress:**

- **Síntomas:**
  - No se puede acceder al service externamente
  - Las reglas de Ingress no funcionan
  - No se creó el load balancer

- **Métodos de diagnóstico:**
  - Comprobar el estado del service:
    ```bash
    kubectl describe service <service_name>
    ```
  - Comprobar el estado del ingress:
    ```bash
    kubectl describe ingress <ingress_name>
    ```
  - Comprobar los logs del pod del ingress controller:
    ```bash
    kubectl logs -n <ingress_namespace> <ingress_controller_pod>
    ```
  - Comprobar endpoints:
    ```bash
    kubectl get endpoints <service_name>
    ```

- **Resolución:**
  - Verificar que el selector del service coincida con las etiquetas de los pods
  - Reinstalar o actualizar el ingress controller
  - Verificar el tipo de service y la configuración de puertos
  - Comprobar la configuración del load balancer del proveedor cloud

**4. Problemas de red de nodos:**

- **Síntomas:**
  - Nodo desconectado del cluster
  - Falla la comunicación entre nodos
  - Errores de conexión de kubelet

- **Métodos de diagnóstico:**
  - Comprobar el estado del nodo:
    ```bash
    kubectl describe node <node_name>
    ```
  - Comprobar las interfaces de red del nodo:
    ```bash
    # Run directly on node
    ip addr
    ip route
    ```
  - Comprobar reglas de firewall:
    ```bash
    # Run directly on node
    iptables -L
    ```
  - Comprobar logs de kubelet:
    ```bash
    journalctl -u kubelet
    ```

- **Resolución:**
  - Reconfigurar las interfaces de red del nodo
  - Modificar reglas de firewall
  - Reiniciar kubelet
  - Reiniciar el nodo si es necesario

**5. Problemas de Network Policy:**

- **Síntomas:**
  - Bloqueo de conexión inesperado
  - No se puede comunicar entre namespaces específicos
  - Solo algunos pods son accesibles

- **Métodos de diagnóstico:**
  - Comprobar network policies:
    ```bash
    kubectl get networkpolicy -A
    kubectl describe networkpolicy <policy_name> -n <namespace>
    ```
  - Comprobar etiquetas de pods:
    ```bash
    kubectl get pods --show-labels
    ```
  - Verificar que el plugin de red sea compatible con network policies

- **Resolución:**
  - Modificar o eliminar network policies
  - Modificar etiquetas de pods
  - Usar herramientas de depuración de network policy

**6. Herramientas generales de depuración de red:**

- **Pod de depuración de red:**
  ```yaml
  apiVersion: v1
  kind: Pod
  metadata:
    name: network-debug
  spec:
    containers:
    - name: debug
      image: nicolaka/netshoot
      command: ["sleep", "3600"]
  ```

- **Comandos útiles:**
  ```bash
  # Inside the pod
  ping <IP>
  traceroute <IP>
  dig <service_name>.<namespace>.svc.cluster.local
  curl -v <URL>
  tcpdump -i any
  netstat -tuln
  ```

- **Herramientas de depuración específicas del plugin CNI:**
  - Calico: `calicoctl`
  - Cilium: `cilium`
  - Weave: `weave`

**7. Mejores prácticas:**

- Documentar la topología de red
- Realizar pruebas regulares de conectividad
- Analizar el impacto antes de cambios en network policy
- Planificar rangos CIDR de red del cluster
- Implementar herramientas de monitoreo de red
</details>
## Preguntas prácticas

1. Escribe un manifiesto ResourceQuota que cumpla los siguientes requisitos:
   - Namespace: development
   - Pods máximos: 20
   - Requests máximos de CPU: 4 cores
   - Requests máximos de memoria: 8Gi
   - PVC máximos: 10
   - Requests máximos de almacenamiento: 100Gi

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: development
spec:
  hard:
    pods: "20"
    requests.cpu: "4"
    requests.memory: 8Gi
    persistentvolumeclaims: "10"
    requests.storage: 100Gi
```

Este ResourceQuota configura los siguientes límites en el namespace 'development':
- Máximo de 20 pods
- Requests totales de CPU de 4 cores
- Requests totales de memoria de 8Gi
- Máximo de 10 PersistentVolumeClaims
- Requests totales de almacenamiento de 100Gi

Para aplicar el ResourceQuota:
```bash
kubectl apply -f resource-quota.yaml
```

Para comprobar el uso actual de la cuota:
```bash
kubectl describe quota dev-quota -n development
```

Nota: El namespace debe existir antes de aplicar el ResourceQuota. Si el namespace no existe, créalo primero:
```bash
kubectl create namespace development
```
</details>

2. Escribe un script que compruebe el estado del servicio kubelet en todos los nodos del cluster y resuelva problemas si existen.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
#!/bin/bash
# Filename: check_kubelet.sh
# Description: Check kubelet service status on all nodes and troubleshoot

# Get node list
NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')

# Loop through each node
for NODE in $NODES; do
  echo "===== Checking node: $NODE ====="

  # Check node status
  NODE_STATUS=$(kubectl get node $NODE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
  echo "Node status: $NODE_STATUS"

  # Check kubelet status via SSH
  echo "Checking kubelet service status..."
  ssh $NODE "sudo systemctl status kubelet | grep Active"

  # Start kubelet if not running
  if ssh $NODE "sudo systemctl is-active kubelet" != "active"; then
    echo "kubelet is not running. Starting service..."
    ssh $NODE "sudo systemctl start kubelet"

    # Check status again after starting
    sleep 5
    if ssh $NODE "sudo systemctl is-active kubelet" == "active"; then
      echo "kubelet service started successfully."
    else
      echo "Failed to start kubelet service. Checking logs..."
      ssh $NODE "sudo journalctl -u kubelet --no-pager -n 50"
    fi
  else
    echo "kubelet service is running normally."
  fi

  # Check kubelet configuration
  echo "Checking kubelet configuration..."
  ssh $NODE "sudo cat /var/lib/kubelet/config.yaml | grep -E 'address|authentication|authorization'"

  echo "===== $NODE check complete ====="
  echo ""
done
```

Este script realiza las siguientes tareas:
1. Obtiene la lista de todos los nodos del cluster usando `kubectl get nodes`.
2. Para cada nodo:
   - Comprueba el estado Ready del nodo.
   - Se conecta al nodo mediante SSH para comprobar el estado del servicio kubelet.
   - Inicia el servicio si kubelet no se está ejecutando.
   - Comprueba el estado nuevamente después de iniciar el servicio.
   - Comprueba los logs si el inicio falla.
   - Comprueba configuraciones clave en el archivo de configuración de kubelet.

**Uso:**
```bash
chmod +x check_kubelet.sh
./check_kubelet.sh
```

**Notas:**
- Se requiere acceso SSH a todos los nodos para ejecutar este script.
- Se recomienda usar autenticación basada en claves SSH para entornos de producción.
- En entornos cloud, el acceso SSH directo a los nodos puede estar restringido, por lo que puede ser necesario usar herramientas de gestión de nodos del proveedor cloud.
</details>

3. Configura un cron job que haga una copia de seguridad de la base de datos etcd del cluster y almacene el archivo de copia de seguridad en una ubicación segura.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**1. Crear script de copia de seguridad:**

```bash
#!/bin/bash
# Filename: backup_etcd.sh
# Description: Backup etcd database and store remotely

# Variable settings
BACKUP_DIR="/opt/etcd-backup"
REMOTE_BACKUP_DIR="/mnt/remote-storage/etcd-backups"
DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="etcd-snapshot-$DATE.db"
ETCD_ENDPOINTS="https://127.0.0.1:2379"
ETCD_CACERT="/etc/kubernetes/pki/etcd/ca.crt"
ETCD_CERT="/etc/kubernetes/pki/etcd/server.crt"
ETCD_KEY="/etc/kubernetes/pki/etcd/server.key"
RETENTION_DAYS=7

# Create backup directory
mkdir -p $BACKUP_DIR

# Create etcd snapshot
ETCDCTL_API=3 etcdctl snapshot save $BACKUP_DIR/$BACKUP_FILE \
  --endpoints=$ETCD_ENDPOINTS \
  --cacert=$ETCD_CACERT \
  --cert=$ETCD_CERT \
  --key=$ETCD_KEY

# Verify backup success
if [ $? -eq 0 ]; then
  echo "etcd backup successful: $BACKUP_FILE"

  # Check backup file status
  ETCDCTL_API=3 etcdctl snapshot status $BACKUP_DIR/$BACKUP_FILE --write-out=table

  # Compress backup file
  gzip $BACKUP_DIR/$BACKUP_FILE

  # Copy to remote storage
  mkdir -p $REMOTE_BACKUP_DIR
  cp $BACKUP_DIR/$BACKUP_FILE.gz $REMOTE_BACKUP_DIR/

  # Clean up old backup files (local)
  find $BACKUP_DIR -name "etcd-snapshot-*.db.gz" -type f -mtime +$RETENTION_DAYS -delete

  # Clean up old backup files (remote)
  find $REMOTE_BACKUP_DIR -name "etcd-snapshot-*.db.gz" -type f -mtime +$RETENTION_DAYS -delete

  echo "Backup complete and copied to remote storage: $REMOTE_BACKUP_DIR/$BACKUP_FILE.gz"
else
  echo "etcd backup failed"
  exit 1
fi
```

**2. Conceder permiso de ejecución al script:**

```bash
chmod +x /opt/etcd-backup/backup_etcd.sh
```

**3. Configurar Cron Job:**

```bash
# Edit root user's crontab
sudo crontab -e
```

Añade el siguiente contenido:

```
# Run etcd backup at 2 AM daily
0 2 * * * /opt/etcd-backup/backup_etcd.sh >> /var/log/etcd-backup.log 2>&1
```

**4. Configurar rotación del log de copia de seguridad:**

Crea el archivo `/etc/logrotate.d/etcd-backup`:

```
/var/log/etcd-backup.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
```

**5. Probar la copia de seguridad:**

```bash
sudo /opt/etcd-backup/backup_etcd.sh
```

**6. Configurar monitoreo de la copia de seguridad (opcional):**

Para recibir alertas ante fallos de copia de seguridad, puedes integrarlo con herramientas de monitoreo (por ejemplo, Prometheus). Añade el siguiente código al script de copia de seguridad:

```bash
# Create file indicating backup success
if [ $? -eq 0 ]; then
  echo "success" > /var/lib/node_exporter/etcd_backup_status.prom
else
  echo "failure" > /var/lib/node_exporter/etcd_backup_status.prom
fi
```

**Notas:**
- Los archivos de copia de seguridad deben almacenarse en una ubicación segura fuera del cluster.
- En entornos cloud, se recomienda usar almacenamiento de objetos como S3 o GCS.
- Prueba regularmente la restauración de copias de seguridad para verificar su validez.
- Para clusters etcd de alta disponibilidad, la copia de seguridad solo necesita realizarse en una instancia de etcd.
</details>
4. Escribe un procedimiento para realizar rolling updates en todos los nodos del cluster. La disponibilidad de los workloads debe mantenerse durante las actualizaciones.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Procedimiento de rolling update de nodos:**

```bash
#!/bin/bash
# Filename: node_rolling_update.sh
# Description: Perform cluster node rolling update

# Variable settings
UPGRADE_COMMAND="sudo apt update && sudo apt upgrade -y"
REBOOT_REQUIRED_CHECK="[ -f /var/run/reboot-required ]"
MAX_UNAVAILABLE=1  # Number of nodes to update at a time

# Check cluster status
echo "Checking cluster status..."
kubectl get nodes
kubectl get pods --all-namespaces -o wide

# Check PodDisruptionBudgets
echo "Checking PodDisruptionBudgets..."
kubectl get poddisruptionbudget --all-namespaces

# Get node list
NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')
NODE_COUNT=$(echo $NODES | wc -w)

echo "Updating $NODE_COUNT nodes in total."
echo "Node list: $NODES"
echo "Maximum $MAX_UNAVAILABLE nodes will be updated at a time."
echo "Press Enter to continue. Press Ctrl+C to cancel."
read

# Loop through each node
for NODE in $NODES; do
  echo "===== Updating node: $NODE ====="

  # Cordon node
  echo "Cordoning node..."
  kubectl cordon $NODE

  # Drain node
  echo "Draining node..."
  kubectl drain $NODE --ignore-daemonsets --delete-emptydir-data --force

  # Update node
  echo "Updating node..."
  ssh $NODE "$UPGRADE_COMMAND"

  # Check if reboot required
  REBOOT_REQUIRED=$(ssh $NODE "$REBOOT_REQUIRED_CHECK && echo 'true' || echo 'false'")

  if [ "$REBOOT_REQUIRED" == "true" ]; then
    echo "Node reboot required. Rebooting..."
    ssh $NODE "sudo reboot"

    # Wait until node becomes Ready again
    echo "Node rebooting. Waiting until Ready..."
    while true; do
      STATUS=$(kubectl get node $NODE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
      if [ "$STATUS" == "True" ]; then
        echo "Node is Ready."
        break
      fi
      echo "Node not Ready yet. Checking again in 10 seconds."
      sleep 10
    done
  else
    echo "Node reboot not required."
  fi

  # Uncordon node
  echo "Uncordoning node..."
  kubectl uncordon $NODE

  # Check node status
  echo "Checking node status..."
  kubectl get node $NODE

  # Wait for pods to be rescheduled to node
  echo "Waiting for pods to be rescheduled to node..."
  sleep 30

  # Check cluster status
  echo "Checking cluster status..."
  kubectl get pods --all-namespaces -o wide | grep $NODE

  echo "===== $NODE update complete ====="
  echo ""

  # User confirmation before proceeding to next node (optional)
  echo "Press Enter to proceed to next node. Press Ctrl+C to cancel."
  read
done

echo "All node updates complete!"
kubectl get nodes
```

**Preparativos previos al rolling update:**

1. **Configurar PodDisruptionBudget:**
   Configura PDBs para workloads críticos para asegurar la disponibilidad.

   ```yaml
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata:
     name: app-pdb
     namespace: default
   spec:
     minAvailable: 2  # or maxUnavailable: 1
     selector:
       matchLabels:
         app: my-app
   ```

2. **Asegurar recursos suficientes:**
   Verifica que los nodos restantes puedan manejar todos los workloads cuando se retire un nodo.

3. **Realizar copia de seguridad:**
   Realiza una copia de seguridad de la base de datos etcd antes de la actualización.

**Mejores prácticas de rolling update:**

1. **Enfoque gradual:**
   - Actualizar solo un nodo a la vez
   - Verificar el estado del cluster después de actualizar cada nodo

2. **Automatización e idempotencia:**
   - Automatizar el proceso usando scripts
   - Diseñar para reintentos seguros en caso de fallo

3. **Monitoreo reforzado:**
   - Monitorear métricas del cluster durante la actualización
   - Monitorear el estado y rendimiento de la aplicación

4. **Plan de rollback:**
   - Preparar el procedimiento de rollback en caso de problemas
   - Asegurar métodos para restaurar el estado anterior

5. **Comunicación:**
   - Anunciar el calendario de actualización y el impacto esperado
   - Informar regularmente el progreso de la actualización

**Notas:**
- En entornos cloud, se pueden utilizar funciones de actualización de nodos de servicios administrados de Kubernetes (EKS, GKE, AKS, etc.).
- Si hay varios grupos de nodos, realiza las actualizaciones por grupo.
- Monitorea especialmente el estado de los pods importantes del sistema (CoreDNS, kube-proxy, etc.).
</details>

5. Escribe un script que identifique pods con alto uso de recursos en el cluster y genere un informe con esa información.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
#!/bin/bash
# Filename: resource_usage_report.sh
# Description: Identify pods with high resource usage and generate report

# Variable settings
REPORT_DIR="/tmp/k8s-reports"
DATE=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="$REPORT_DIR/resource-usage-report-$DATE.txt"
TOP_N=10  # Show top N pods

# Create report directory
mkdir -p $REPORT_DIR

# Write report header
echo "===== Kubernetes Cluster Resource Usage Report =====" > $REPORT_FILE
echo "Generated: $(date)" >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Add cluster information
echo "===== Cluster Information =====" >> $REPORT_FILE
kubectl cluster-info >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

# Node resource usage
echo "===== Node Resource Usage =====" >> $REPORT_FILE
kubectl top nodes | sort -k 3 -hr >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Top pods by CPU usage
echo "===== Top $TOP_N Pods by CPU Usage =====" >> $REPORT_FILE
kubectl top pods --all-namespaces | sort -k 3 -hr | head -n $((TOP_N + 1)) >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Top pods by memory usage
echo "===== Top $TOP_N Pods by Memory Usage =====" >> $REPORT_FILE
kubectl top pods --all-namespaces | sort -k 4 -hr | head -n $((TOP_N + 1)) >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Resource usage by namespace
echo "===== Resource Usage by Namespace =====" >> $REPORT_FILE
echo "CPU Usage (cores):" >> $REPORT_FILE
kubectl top pods --all-namespaces | tail -n +2 | awk '{print $2, $3}' | sed 's/m//' | awk '{ns[$1] += $2} END {for (namespace in ns) print namespace, ns[namespace]/1000}' | sort -k 2 -hr >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "Memory Usage (GiB):" >> $REPORT_FILE
kubectl top pods --all-namespaces | tail -n +2 | awk '{print $2, $4}' | sed 's/Mi//' | awk '{ns[$1] += $2} END {for (namespace in ns) print namespace, ns[namespace]/1024}' | sort -k 2 -hr >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Identify pods with high usage relative to requests
echo "===== Pods with High Resource Usage Relative to Requests =====" >> $REPORT_FILE
echo "Collecting pod information..." >> $REPORT_FILE

# Create temporary files
PODS_USAGE_FILE="$REPORT_DIR/pods-usage-$DATE.tmp"
PODS_REQUESTS_FILE="$REPORT_DIR/pods-requests-$DATE.tmp"

# Collect current usage
kubectl top pods --all-namespaces | tail -n +2 > $PODS_USAGE_FILE

# Collect resource requests for all namespaces
echo "Namespace,Pod,CPURequest(m),MemoryRequest(Mi)" > $PODS_REQUESTS_FILE
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get pods -n $ns -o jsonpath='{range .items[*]}{.metadata.namespace},{.metadata.name},{range .spec.containers[*]}{.resources.requests.cpu}{","}{.resources.requests.memory}{"\n"}{end}{end}' | sed 's/$/,/' | sed 's/,$//' >> $PODS_REQUESTS_FILE
done

# Calculate usage relative to requests and add to report
echo "Pods with high CPU utilization (usage/request > 80%):" >> $REPORT_FILE
while read line; do
  ns=$(echo $line | awk '{print $1}')
  pod=$(echo $line | awk '{print $2}')
  cpu_usage=$(echo $line | awk '{print $3}' | sed 's/m//')

  # Find CPU request for this pod
  cpu_request=$(grep "$ns,$pod," $PODS_REQUESTS_FILE | awk -F, '{print $3}' | sed 's/[^0-9m.]//g' | sed 's/m//')

  # Show "Not set" if no CPU request
  if [ -z "$cpu_request" ] || [ "$cpu_request" == "" ]; then
    echo "$ns/$pod: CPU usage ${cpu_usage}m, request not set" >> $REPORT_FILE
  else
    # Calculate CPU utilization
    cpu_percentage=$(echo "scale=2; $cpu_usage / $cpu_request * 100" | bc)

    # Show only if utilization is 80% or higher
    if (( $(echo "$cpu_percentage >= 80" | bc -l) )); then
      echo "$ns/$pod: CPU usage ${cpu_usage}m, request ${cpu_request}m, utilization ${cpu_percentage}%" >> $REPORT_FILE
    fi
  fi
done < $PODS_USAGE_FILE

echo "" >> $REPORT_FILE
echo "Pods with high memory utilization (usage/request > 80%):" >> $REPORT_FILE
while read line; do
  ns=$(echo $line | awk '{print $1}')
  pod=$(echo $line | awk '{print $2}')
  mem_usage=$(echo $line | awk '{print $4}' | sed 's/Mi//')

  # Find memory request for this pod
  mem_request=$(grep "$ns,$pod," $PODS_REQUESTS_FILE | awk -F, '{print $4}' | sed 's/[^0-9Mi.]//g' | sed 's/Mi//')

  # Show "Not set" if no memory request
  if [ -z "$mem_request" ] || [ "$mem_request" == "" ]; then
    echo "$ns/$pod: Memory usage ${mem_usage}Mi, request not set" >> $REPORT_FILE
  else
    # Calculate memory utilization
    mem_percentage=$(echo "scale=2; $mem_usage / $mem_request * 100" | bc)

    # Show only if utilization is 80% or higher
    if (( $(echo "$mem_percentage >= 80" | bc -l) )); then
      echo "$ns/$pod: Memory usage ${mem_usage}Mi, request ${mem_request}Mi, utilization ${mem_percentage}%" >> $REPORT_FILE
    fi
  fi
done < $PODS_USAGE_FILE

echo "" >> $REPORT_FILE

# Identify pods without resource requests
echo "===== Pods Without Resource Requests =====" >> $REPORT_FILE
kubectl get pods --all-namespaces -o json | jq -r '.items[] | select((.spec.containers[].resources.requests.cpu == null) or (.spec.containers[].resources.requests.memory == null)) | .metadata.namespace + "/" + .metadata.name' >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Clean up temporary files
rm -f $PODS_USAGE_FILE $PODS_REQUESTS_FILE

# Report summary
echo "===== Report Summary =====" >> $REPORT_FILE
echo "Total nodes: $(kubectl get nodes | tail -n +2 | wc -l)" >> $REPORT_FILE
echo "Total pods: $(kubectl get pods --all-namespaces | tail -n +2 | wc -l)" >> $REPORT_FILE
echo "Total namespaces: $(kubectl get ns | tail -n +2 | wc -l)" >> $REPORT_FILE
echo "Report generation complete: $REPORT_FILE" >> $REPORT_FILE

# Output report location
echo "Report generated: $REPORT_FILE"

# Generate HTML report (optional)
HTML_REPORT="${REPORT_FILE%.txt}.html"
echo "<html><head><title>Kubernetes Resource Usage Report</title>" > $HTML_REPORT
echo "<style>body{font-family:Arial;margin:20px}h1{color:#326ce5}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:8px}th{background-color:#f2f2f2}</style>" >> $HTML_REPORT
echo "</head><body>" >> $HTML_REPORT
echo "<h1>Kubernetes Cluster Resource Usage Report</h1>" >> $HTML_REPORT
echo "<p>Generated: $(date)</p>" >> $HTML_REPORT

# Convert report content to HTML
awk '/===== Cluster Information =====/{flag=1;print "<h2>Cluster Information</h2><pre>"}/===== Node Resource Usage =====/{flag=0;print "</pre><h2>Node Resource Usage</h2><table><tr><th>Node</th><th>CPU(%)</th><th>Memory(%)</th></tr>"}/===== Top.*CPU Usage/{flag=0;print "</table><h2>Top Pods by CPU Usage</h2><table><tr><th>Namespace</th><th>Pod</th><th>CPU(m)</th><th>Memory(Mi)</th></tr>"}/===== Top.*Memory Usage/{flag=0;print "</table><h2>Top Pods by Memory Usage</h2><table><tr><th>Namespace</th><th>Pod</th><th>CPU(m)</th><th>Memory(Mi)</th></tr>"}/===== Resource Usage by Namespace =====/{flag=0;print "</table><h2>Resource Usage by Namespace</h2>"}/CPU Usage \(cores\):/{flag=0;print "<h3>CPU Usage (cores)</h3><table><tr><th>Namespace</th><th>CPU(cores)</th></tr>"}/Memory Usage \(GiB\):/{flag=0;print "</table><h3>Memory Usage (GiB)</h3><table><tr><th>Namespace</th><th>Memory(GiB)</th></tr>"}/===== Pods with High Resource Usage Relative to Requests =====/{flag=0;print "</table><h2>Pods with High Resource Usage Relative to Requests</h2>"}/Pods with high CPU utilization/{flag=0;print "<h3>Pods with High CPU Utilization (usage/request > 80%)</h3><ul>"}/Pods with high memory utilization/{flag=0;print "</ul><h3>Pods with High Memory Utilization (usage/request > 80%)</h3><ul>"}/===== Pods Without Resource Requests =====/{flag=0;print "</ul><h2>Pods Without Resource Requests</h2><ul>"}/===== Report Summary =====/{flag=0;print "</ul><h2>Report Summary</h2><ul>"}{if(flag==1)print;else if($0 ~ /^NAME/){print "<tr>";for(i=1;i<=NF;i++)print "<th>"$i"</th>";print "</tr>"}else if($0 ~ /^[a-z].*[0-9]%/){print "<tr>";for(i=1;i<=NF;i++)print "<td>"$i"</td>";print "</tr>"}else if($0 ~ /^[a-z].*[0-9]m/){print "<tr>";for(i=1;i<=NF;i++)print "<td>"$i"</td>";print "</tr>"}else if($0 ~ /^[a-z].* [0-9]/){print "<tr><td>"$1"</td><td>"$2"</td></tr>"}else if($0 ~ /^[a-z].*\//){print "<li>"$0"</li>"}else if($0 ~ /^Total/){print "<li>"$0"</li>"}}' $REPORT_FILE >> $HTML_REPORT

echo "</ul></body></html>" >> $HTML_REPORT
echo "HTML report generated: $HTML_REPORT"
```

**Uso del script:**
```bash
chmod +x resource_usage_report.sh
./resource_usage_report.sh
```

**Características del script:**
1. Recopila información del cluster
2. Recopila uso de recursos de nodos
3. Identifica los pods principales por uso de CPU y memoria
4. Calcula el uso de recursos por namespace
5. Identifica pods con uso alto relativo a requests
6. Identifica pods sin resource requests
7. Genera informes en formatos de texto y HTML

**Notas:**
- Las herramientas `kubectl`, `jq` y `bc` son necesarias para ejecutar este script.
- Metrics Server debe estar instalado en el cluster.
- El tiempo de ejecución del script puede ser largo en clusters grandes.
- Puede configurarse como un cron job para generar informes regularmente.
- Los informes pueden enviarse por email o integrarse con sistemas de monitoreo.
</details>
## Temas avanzados

1. ¿Cuáles son los parámetros de configuración clave y las mejores prácticas para optimizar el rendimiento de etcd en un cluster de Kubernetes?
   - A) `--max-request-bytes`, `--quota-backend-bytes`, compactación regular
   - B) `--max-concurrent-requests`, `--max-connections`, configuración RAID de disco
   - C) `--auto-compaction-retention`, `--snapshot-count`, uso de almacenamiento SSD
   - D) `--max-txn-ops`, `--max-result-buffer`, ampliación de memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `--auto-compaction-retention`, `--snapshot-count`, uso de almacenamiento SSD**

**Explicación:**
etcd es el almacén de datos central de un cluster de Kubernetes, y su rendimiento impacta directamente en el rendimiento general del cluster. Los parámetros de configuración clave y las mejores prácticas para optimizar el rendimiento de etcd son los siguientes:

1. **`--auto-compaction-retention`**: etcd es un almacén append-only que mantiene un historial de todos los cambios. Este parámetro establece el período para compactar automáticamente versiones anteriores de claves. El valor predeterminado es 0 (deshabilitado), pero en entornos de producción normalmente se establece en 1 hora (1h) o 24 horas (24h). Esto ahorra espacio en disco y mejora el rendimiento.

2. **`--snapshot-count`**: Especifica el número de transacciones que se confirman antes de que etcd cree un snapshot. El valor predeterminado es 100,000, pero para clusters grandes este valor puede ajustarse para optimizar la frecuencia de creación de snapshots. Valores más pequeños significan snapshots más frecuentes, reducen el tiempo de recuperación pero aumentan el I/O de disco.

3. **Uso de almacenamiento SSD**: etcd es sensible al I/O de disco, por lo que usar SSDs (Solid State Drives) mejora significativamente el rendimiento. El uso de SSD es esencial especialmente para clusters grandes.

Otras configuraciones de optimización y mejores prácticas importantes:

- **Usar disco dedicado**: Usa un disco dedicado para los datos de etcd para evitar contención de I/O con otras aplicaciones.
- **Asignación de memoria adecuada**: etcd almacena datos en caché en memoria para mejorar el rendimiento, por lo que se debe asignar memoria suficiente.
- **Optimización del tamaño del cluster**: Generalmente, 3-5 miembros de etcd proporcionan rendimiento y disponibilidad óptimos.
- **Minimizar la latencia de red**: Coloca los miembros de etcd en el mismo centro de datos o zona de disponibilidad para minimizar la latencia de red entre miembros.
- **Copia de seguridad y compactación regulares**: Realiza copias de seguridad y compactación regulares para asegurar la seguridad de los datos y un uso eficiente del espacio en disco.

`--max-request-bytes` y `--quota-backend-bytes` son parámetros reales de etcd, pero se relacionan principalmente con límites de recursos en lugar de rendimiento. `--max-concurrent-requests`, `--max-connections`, `--max-txn-ops`, `--max-result-buffer` no son parámetros reales de etcd o no son factores clave para la optimización del rendimiento.
</details>

2. ¿Cuál es la forma más efectiva de implementar alta disponibilidad (HA) del control plane en un cluster de Kubernetes?
   - A) Ejecutar múltiples instancias de API server en un solo nodo master
   - B) Configurar un cluster de etcd con múltiples nodos master y load balancer
   - C) Desplegar API server como StatefulSet y usar PersistentVolume
   - D) Implementar un proceso de watch con recuperación automática en el nodo master

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar un cluster de etcd con múltiples nodos master y load balancer**

**Explicación:**
La forma más efectiva de implementar alta disponibilidad (HA) del control plane de Kubernetes es configurar un cluster de etcd con múltiples nodos master y un load balancer. Este enfoque consta de los siguientes componentes:

1. **Múltiples nodos master**: Normalmente se despliegan 3 o 5 nodos master en diferentes zonas de disponibilidad para eliminar puntos únicos de fallo. Cada nodo master ejecuta los siguientes componentes del control plane:
   - kube-apiserver: servidor que maneja solicitudes de API
   - kube-controller-manager: ejecuta procesos controller
   - kube-scheduler: toma decisiones de scheduling de pods

2. **Cluster etcd**: etcd es un almacén clave-valor distribuido que almacena todos los datos del cluster. Para alta disponibilidad, normalmente se ejecutan 3 o 5 instancias de etcd. etcd puede ejecutarse directamente en nodos master o en nodos dedicados separados.

3. **Load balancer**: Se necesita un load balancer para distribuir las solicitudes de clientes entre múltiples instancias de kube-apiserver. Normalmente se implementa usando servicios de load balancer del proveedor cloud o load balancers de software como HAProxy, Nginx.

Beneficios clave de esta configuración:
- **Tolerancia a fallos**: Si un nodo master falla, el cluster continúa operando.
- **Alta disponibilidad**: El despliegue en múltiples zonas de disponibilidad puede responder a fallos a nivel de centro de datos.
- **Escalabilidad**: Las solicitudes al API server pueden distribuirse y procesarse entre múltiples instancias.
- **Consistencia de datos**: La consistencia de datos se asegura mediante el algoritmo de consenso Raft de etcd.

Problemas con otras opciones:
- Ejecutar múltiples instancias de API server en un solo nodo master convierte al propio nodo en un punto único de fallo.
- Desplegar API server como StatefulSet no es un enfoque común; los componentes del control plane normalmente se gestionan fuera de Kubernetes.
- Un proceso de watch puede ayudar, pero no es una solución real de alta disponibilidad por sí solo.
</details>

3. ¿Cuál es la consideración más importante al configurar Audit Logging en un cluster de Kubernetes?
   - A) Registrar todas las solicitudes API para tener una pista de auditoría completa
   - B) Usar audit policy para registrar selectivamente solo eventos importantes
   - C) Enviar audit logs a un sistema SIEM externo en tiempo real
   - D) Restringir el acceso a audit logs solo a administradores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar audit policy para registrar selectivamente solo eventos importantes**

**Explicación:**
La consideración más importante al configurar Audit Logging de Kubernetes es usar audit policies para registrar selectivamente solo eventos importantes. Esto es importante por las siguientes razones:

1. **Minimizar el impacto en el rendimiento**: Registrar todas las solicitudes API puede causar una carga significativa en el API server y degradar el rendimiento. Especialmente en clusters grandes, pueden producirse miles de solicitudes API por segundo.

2. **Eficiencia de almacenamiento**: Registrar todos los eventos causa un rápido aumento en el volumen de datos de logs, aumenta los costos de almacenamiento y dificulta el análisis de logs.

3. **Enfoque en información relevante**: Registrar solo eventos importantes permite que los analistas de seguridad se enfoquen en información crítica.

4. **Compliance**: Muchos requisitos de compliance requieren registrar tipos específicos de eventos en lugar de todos los eventos.

Las audit policies de Kubernetes admiten los siguientes niveles de auditoría:

- **None**: No registrar el evento.
- **Metadata**: Registrar solo metadatos de la solicitud (usuario, timestamp, recurso, acción, etc.) y excluir los cuerpos de solicitud/respuesta.
- **Request**: Registrar metadatos y cuerpo de la solicitud, pero excluir el cuerpo de la respuesta.
- **RequestResponse**: Registrar metadatos, cuerpo de la solicitud y cuerpo de la respuesta.

Ejemplo de una audit policy efectiva:
```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
# Set logging level for authentication and authorization requests
- level: Metadata
  users: ["system:anonymous"]
  verbs: ["get", "list", "watch"]

# Log changes to sensitive resources like Secrets, ConfigMaps in detail
- level: Request
  resources:
  - group: ""
    resources: ["secrets", "configmaps"]
  verbs: ["create", "update", "patch", "delete"]

# Log important resource changes in detail
- level: RequestResponse
  resources:
  - group: ""
    resources: ["pods"]
  verbs: ["create", "update", "patch", "delete"]

# Log only metadata by default
- level: Metadata
```

Problemas con otras opciones:
- Registrar todas las solicitudes API puede causar problemas de rendimiento y almacenamiento.
- La transmisión en tiempo real a sistemas SIEM externos es importante, pero tiene menor prioridad que decidir qué registrar.
- Restringir el acceso a audit logs es importante, pero es una medida de seguridad más que la política de logging en sí.
</details>

4. ¿Cuál es la forma más efectiva de implementar Node Auto-Repair en un cluster de Kubernetes?
   - A) Desplegar DaemonSet que monitoree el estado del nodo y reinicie automáticamente nodos problemáticos
   - B) Utilizar grupos de nodos administrados del proveedor cloud y funciones de auto-repair
   - C) Usar Node Problem Detector y un custom controller para monitoreo y reparación del estado del nodo
   - D) Implementar un cron job que compruebe periódicamente el estado del nodo y recree nodos problemáticos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar Node Problem Detector y un custom controller para monitoreo y reparación del estado del nodo**

**Explicación:**
La forma más efectiva de implementar Node Auto-Repair en un cluster de Kubernetes es usar Node Problem Detector junto con un custom controller. Este enfoque proporciona los siguientes beneficios:

1. **Detección precisa de problemas**: Node Problem Detector (NPD) es una herramienta de propósito especial que puede detectar varios problemas de nodos. Puede detectar los siguientes problemas:
   - Errores y fallos del kernel
   - Problemas de hardware
   - Problemas del sistema de archivos
   - Problemas de red
   - Problemas de escasez de recursos

2. **Respuesta flexible**: Usar un custom controller permite implementar varias estrategias de recuperación para los problemas detectados:
   - Problemas menores: reinicio del nodo
   - Problemas graves: reemplazo del nodo
   - Tipos específicos de problemas: reinicio de un servicio específico

3. **Integración nativa con Kubernetes**: NPD informa el estado del nodo como NodeConditions, integrándose bien con los mecanismos existentes de Kubernetes.

4. **Independiente de cloud**: Este enfoque funciona en todos los entornos (on-premises, varios proveedores cloud).

Pasos de implementación:

1. **Desplegar Node Problem Detector**:
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/node-problem-detector/master/deployment/node-problem-detector.yaml
   ```

2. **Implementar custom controller**:
   - Observar eventos de Kubernetes y cambios de estado de nodos
   - Implementar lógica que responda a NodeConditions específicas
   - Realizar operaciones de recuperación (ejecución de comandos mediante SSH, recreación de nodos mediante API cloud, etc.)

3. **Configurar alertas y logging**:
   - Configurar alertas para operaciones de recuperación
   - Registrar problemas y operaciones de recuperación

Problemas con otras opciones:

- **Enfoque con DaemonSet**: Si un nodo tiene problemas graves, el propio DaemonSet puede verse afectado, y es difícil detectar todos los tipos de problemas.

- **Grupos de nodos administrados del proveedor cloud**: Depende de proveedores cloud específicos y no puede usarse en entornos on-premises. Además, los tipos de problemas que pueden detectarse pueden ser limitados.

- **Enfoque con cron job**: Tiempo de reacción lento, capacidad limitada de detección de problemas y debe ejecutarse fuera del cluster.

Combinar Node Problem Detector con un custom controller permite implementar una solución de auto-repair de nodos robusta y flexible que funciona en diversos entornos.
</details>

5. ¿Cuál es la mejor práctica para gestionar RBAC (Role-Based Access Control) de forma efectiva en un cluster de Kubernetes?
   - A) Conceder el rol cluster-admin a todos los usuarios para facilitar la gestión
   - B) Definir roles granulares por namespace y aplicar el principio de mínimo privilegio
   - C) Consolidar todos los permisos en un único ClusterRole para mantener la consistencia
   - D) Usar siempre certificados de usuario en lugar de service accounts para la autenticación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Definir roles granulares por namespace y aplicar el principio de mínimo privilegio**

**Explicación:**
La mejor práctica para gestionar RBAC (Role-Based Access Control) de forma efectiva en un cluster de Kubernetes es definir roles granulares por namespace y aplicar el principio de mínimo privilegio. Este enfoque proporciona los siguientes beneficios:

1. **Principio de mínimo privilegio**: Concede solo los permisos mínimos necesarios a usuarios y service accounts para minimizar riesgos de seguridad. Esto ayuda a proteger el cluster contra cambios no intencionados o comportamiento malicioso.

2. **Aislamiento por namespace**: Definir roles por namespace fortalece el aislamiento lógico entre equipos o aplicaciones. Esto evita que los errores de un equipo afecten los recursos de otro equipo.

3. **Control de acceso granular**: Los permisos pueden controlarse de forma precisa para tipos de recursos u operaciones específicas. Por ejemplo, se puede conceder a los desarrolladores permisos para gestionar pods y services, pero restringir permisos para modificar secrets o el propio namespace.

4. **Facilidad de auditoría**: Usar roles granulares documenta claramente quién puede realizar qué operaciones, lo que facilita la auditoría y el compliance.

Ejemplos de implementación de mejores prácticas de RBAC:

1. **Definir roles por namespace**:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: developer
     namespace: development
   rules:
   - apiGroups: [""]
     resources: ["pods", "services", "configmaps"]
     verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
   - apiGroups: ["apps"]
     resources: ["deployments", "replicasets"]
     verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
   - apiGroups: [""]
     resources: ["secrets"]
     verbs: ["get", "list", "watch"]  # Allow only reading secrets
   ```

2. **Crear role bindings**:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: RoleBinding
   metadata:
     name: developer-binding
     namespace: development
   subjects:
   - kind: Group
     name: developers
     apiGroup: rbac.authorization.k8s.io
   roleRef:
     kind: Role
     name: developer
     apiGroup: rbac.authorization.k8s.io
   ```

3. **Usar roles a nivel de cluster con moderación**:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: ClusterRole
   metadata:
     name: pod-reader
   rules:
   - apiGroups: [""]
     resources: ["pods"]
     verbs: ["get", "list", "watch"]
   ```

4. **Permisos granulares para service accounts**:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: app-role
     namespace: production
   rules:
   - apiGroups: [""]
     resources: ["configmaps"]
     resourceNames: ["app-config"]  # Only access to specific ConfigMap
     verbs: ["get"]
   ```

Problemas con otras opciones:

- **Conceder el rol cluster-admin a todos los usuarios**: Esto supone riesgos de seguridad graves. Que todos los usuarios tengan acceso completo a todos los recursos del cluster hace que el sistema sea vulnerable a cambios no intencionados o comportamiento malicioso.

- **Consolidar todos los permisos en un único ClusterRole**: Esto imposibilita el control de acceso granular y viola el principio de mínimo privilegio.

- **Usar siempre certificados de usuario**: Las service accounts son adecuadas para la autenticación de aplicaciones, y usar certificados de usuario en todas las situaciones aumenta la carga de gestión. Es importante elegir el mecanismo de autenticación adecuado para cada situación.
</details>
