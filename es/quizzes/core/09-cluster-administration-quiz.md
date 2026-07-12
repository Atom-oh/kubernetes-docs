## Preguntas de respuesta corta

1. Explica los procedimientos de backup y restore para la base de datos etcd en un cluster Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Procedimiento de backup de etcd:**

1. **Verificar la instalación de la herramienta etcdctl:**
   ```bash
   etcdctl version
   ```

2. **Ejecutar el comando de backup:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
     --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key
   ```

3. **Verificar el archivo de backup:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot status snapshot.db --write-out=table
   ```

4. **Almacenar el archivo de backup en una ubicación segura:**
   - Almacenamiento fuera del cluster
   - Cloud storage (S3, GCS, etc.)
   - Ubicación física diferente

**Procedimiento de restore de etcd:**

1. **Detener todos los API servers para la restauración:**
   ```bash
   sudo systemctl stop kube-apiserver
   ```

2. **Detener el Service etcd:**
   ```bash
   sudo systemctl stop etcd
   ```

3. **Hacer backup del directorio de datos (opcional):**
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

6. **Reiniciar el Service etcd:**
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

**Buenas prácticas:**
- Configurar programaciones regulares de backup (por ejemplo, diariamente)
- Verificar el estado del cluster etcd antes del backup
- Validar la integridad del archivo de backup
- Probar regularmente los procedimientos de restore
- Incluir marcas de tiempo en los nombres de archivos de backup
- Mantener varias versiones de backup
- Documentar los procedimientos de backup y restore
</details>

2. Explica el procedimiento para el mantenimiento de Node en un cluster Kubernetes y describe las diferencias entre los comandos `cordon`, `drain` y `uncordon`.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Procedimiento de mantenimiento de Node:**

1. **Comprobar el estado del Node:**
   ```bash
   kubectl get nodes
   kubectl describe node <node_name>
   ```

2. **Aplicar cordon al Node:**
   ```bash
   kubectl cordon <node_name>
   ```

3. **Aplicar drain al Node:**
   ```bash
   kubectl drain <node_name> --ignore-daemonsets --delete-emptydir-data
   ```

4. **Realizar tareas de mantenimiento:**
   - Actualizaciones de software
   - Actualizaciones de Kernel
   - Reemplazo de hardware
   - Cambios de configuración

5. **Aplicar uncordon al Node después de completar las tareas:**
   ```bash
   kubectl uncordon <node_name>
   ```

6. **Verificar el estado del Node:**
   ```bash
   kubectl get nodes
   ```

**Diferencias entre comandos:**

1. **`kubectl cordon <node_name>`:**
   - Marca el Node como no programable.
   - No se programarán nuevos pods en el Node.
   - Los pods que ya se están ejecutando continúan ejecutándose.
   - El indicador `SchedulingDisabled` aparece en el estado del Node.

2. **`kubectl drain <node_name>`:**
   - Marca el Node como no programable (incluye cordon).
   - Desaloja de forma segura los pods en ejecución del Node.
   - Los Pods se reprograman en otros Nodes.
   - Los Pods de DaemonSet se ignoran de forma predeterminada (se requiere la flag `--ignore-daemonsets`).
   - Los Pods que usan volúmenes emptyDir pueden perder datos, lo que requiere manejo especial (flag `--delete-emptydir-data`).
   - Respeta los PodDisruptionBudgets.

3. **`kubectl uncordon <node_name>`:**
   - Marca el Node como programable de nuevo.
   - Se pueden programar nuevos pods en el Node.
   - Los Pods desalojados previamente no vuelven automáticamente.

**Consideraciones de mantenimiento:**
- Asegurar que el cluster tenga suficiente capacidad de reserva
- Configurar PodDisruptionBudgets para workloads críticos
- Realizar mantenimiento en un Node a la vez
- Ajustar la configuración de auto-scaling durante los períodos de mantenimiento
- Verificar el estado de los workloads antes y después del mantenimiento
- Usar estrategias de rolling update
</details>

3. Explica cómo monitorear y administrar el uso de recursos en un cluster Kubernetes. Enumera las herramientas y técnicas que deberían incluirse.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Métodos de monitoreo y administración de recursos de Kubernetes:**

**1. Herramientas básicas de monitoreo:**

- **Metrics Server:**
  - Proporciona métricas básicas de uso de CPU y memoria
  - Admite comandos `kubectl top`
  - Método de instalación:
    ```bash
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    ```
  - Ejemplos de uso:
    ```bash
    kubectl top nodes
    kubectl top pods --all-namespaces
    ```

- **Kubernetes Dashboard:**
  - Representación visual del estado del cluster y del uso de recursos
  - Proporciona una interfaz de administración de recursos para pods, nodes, namespaces, etc.

**2. Stack de monitoreo avanzado:**

- **Prometheus + Grafana:**
  - Prometheus: recopilación y almacenamiento de métricas
  - Grafana: visualización de métricas y dashboards
  - Puede instalarse mediante kube-prometheus-stack o Prometheus Operator
  - Admite reglas de alerting y dashboards personalizados

- **Stack ELK/EFK:**
  - Elasticsearch: almacenamiento y búsqueda de logs
  - Logstash/Fluentd: recopilación y procesamiento de logs
  - Kibana: visualización y análisis de logs

**3. Técnicas de administración de recursos:**

- **Configurar resource requests y limits:**
  ```yaml
  resources:
    requests:
      memory: "64Mi"
      cpu: "250m"
    limits:
      memory: "128Mi"
      cpu: "500m"
  ```

- **Resource quotas a nivel de Namespace (ResourceQuota):**
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

- **Resource limits predeterminados (LimitRange):**
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
  - Ajusta automáticamente los CPU y memory requests para pods
  - Proporciona recomendaciones basadas en patrones de uso de recursos

- **Cluster Autoscaler:**
  - Ajusta automáticamente el número de Nodes del cluster según los requisitos de workload
  - Añade Nodes cuando los recursos son insuficientes y elimina Nodes cuando la utilización es baja

**4. Buenas prácticas de monitoreo:**

- Configurar resource requests y limits para todos los pods
- Configurar alertas para métricas críticas
- Planificar recursos basándose en el análisis de uso histórico
- Realizar auditorías regulares de recursos
- Analizar tendencias de uso de recursos para la optimización de costos
- Configurar resource quotas apropiadas para entornos de desarrollo, staging y producción
- Monitorear métricas tanto a nivel de Node como a nivel de Pod
</details>

4. Explica los principales riesgos que pueden ocurrir durante una actualización de un cluster Kubernetes y las estrategias para mitigarlos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Riesgos de actualización de cluster Kubernetes y estrategias de mitigación:**

**1. Principales riesgos:**

- **Problemas de compatibilidad de API:**
  - Las API pueden cambiar o eliminarse en versiones nuevas
  - Algunas Custom Resource Definitions (CRDs) o versiones de API pueden dejar de estar soportadas

- **Interrupción de workload:**
  - Indisponibilidad temporal del API server debido a reinicios de componentes del control plane
  - Interrupción del Service debido a la reprogramación de pods durante las actualizaciones de Nodes

- **Cambios de funcionalidades:**
  - Los comportamientos predeterminados pueden cambiar, afectando workloads existentes
  - Problemas de permisos debido a cambios en políticas de seguridad

- **Problemas de rendimiento:**
  - Los requisitos de recursos pueden aumentar en versiones nuevas
  - Posible degradación del rendimiento durante el período inicial de estabilización

- **Complejidad de rollback:**
  - Algunas actualizaciones no pueden revertirse fácilmente
  - Limitaciones de rollback debido a cambios de formato de datos

**2. Estrategias de mitigación:**

- **Planificación y preparación exhaustivas:**
  - **Revisar el changelog:** Comprobar cambios, funcionalidades eliminadas y problemas conocidos en la nueva versión
  - **Verificar la ruta de actualización:** Confirmar que se admite la actualización directa desde la versión actual a la versión objetivo
  - **Revisar los requisitos de recursos:** Comprobar los requisitos mínimos para la nueva versión

- **Probar primero en un entorno de pruebas:**
  - Realizar la actualización en un cluster de pruebas similar a producción
  - Probar todos los workloads críticos y recursos personalizados
  - Ejecutar suites de pruebas automatizadas

- **Verificar la compatibilidad de API:**
  - Comprobar las versiones de API en uso:
    ```bash
    kubectl api-resources -o wide
    ```
  - Comprobar el uso de API obsoletas:
    ```bash
    kubectl get -A | grep "deprecated"
    ```
  - Actualizar manifests según sea necesario

- **Plan de backup y recovery:**
  - Hacer backup de la base de datos etcd:
    ```bash
    ETCDCTL_API=3 etcdctl snapshot save snapshot.db
    ```
  - Hacer backup de todos los manifests críticos:
    ```bash
    kubectl get all --all-namespaces -o yaml > all-resources.yaml
    ```
  - Documentar y probar los procedimientos de recovery

- **Enfoque de actualización gradual:**
  - **Actualizar primero los componentes del control plane:**
    - En configuraciones HA, actualizar un Node del control plane a la vez
  - **Rolling upgrade de worker nodes:**
    - Dividir los grupos de Nodes en lotes pequeños para la actualización
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
  - **Tener cuidado al aplicar drain a Nodes:**
    ```bash
    kubectl drain <node_name> --ignore-daemonsets --delete-emptydir-data
    ```

- **Monitoreo mejorado:**
  - Monitorear el estado del cluster antes, durante y después de la actualización
  - Centrarse en métricas y logs clave
  - Ajustar temporalmente los umbrales de alertas

- **Plan de rollback:**
  - Definir condiciones que disparen el rollback
  - Documentar los procedimientos de rollback
  - Conservar todos los componentes e imágenes necesarios para el rollback

- **Plan de comunicación:**
  - Notificar a todos los stakeholders el calendario de actualización y el impacto esperado
  - Proporcionar actualizaciones de estado durante la actualización
  - Definir rutas de escalación para problemas

**3. Consideraciones específicas de versión:**

- **Actualizaciones de versión menor (por ejemplo, 1.24 → 1.25):**
  - Prestar especial atención a API eliminadas y cambios de funcionalidades
  - Actualizar una versión menor a la vez

- **Actualizaciones de versión de patch (por ejemplo, 1.24.0 → 1.24.1):**
  - Generalmente son más seguras, pero aun así requieren pruebas
  - Considerar un despliegue más rápido para security patches
</details>

5. Explica los problemas comunes de networking que pueden ocurrir en un cluster Kubernetes y cómo diagnosticarlos y resolverlos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Diagnóstico y resolución de problemas de networking de Kubernetes:**

**1. Problemas de comunicación Pod-to-Pod:**

- **Síntomas:**
  - Los Pods no pueden comunicarse con otros Pods
  - No se puede conectar por nombre de Service
  - Errores de timeout de red

- **Métodos de diagnóstico:**
  - Comprobar network policies:
    ```bash
    kubectl get networkpolicy --all-namespaces
    ```
  - Crear un Pod de prueba para pruebas de conectividad:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    ping <target_pod_IP>
    wget -O- <service_name>:<port>
    ```
  - Comprobar el estado del Pod del plugin CNI:
    ```bash
    kubectl get pods -n kube-system | grep -E 'calico|flannel|weave|cilium'
    ```

- **Métodos de resolución:**
  - Reinstalar o actualizar el plugin CNI
  - Modificar o eliminar network policies
  - Comprobar interfaces de red del Node
  - Comprobar reglas de firewall

**2. Problemas de Service Discovery y DNS:**

- **Síntomas:**
  - No se puede conectar por nombre de Service
  - Fallos de búsqueda DNS
  - Problemas de conexión intermitentes

- **Métodos de diagnóstico:**
  - Comprobar el estado de Pods CoreDNS:
    ```bash
    kubectl get pods -n kube-system -l k8s-app=kube-dns
    kubectl logs -n kube-system -l k8s-app=kube-dns
    ```
  - Probar la búsqueda DNS:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    nslookup kubernetes.default.svc.cluster.local
    nslookup <service_name>.<namespace>.svc.cluster.local
    cat /etc/resolv.conf
    ```
  - Comprobar endpoints del Service:
    ```bash
    kubectl get endpoints <service_name>
    ```

- **Métodos de resolución:**
  - Reiniciar Pods CoreDNS:
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
  - No se puede acceder al Service desde fuentes externas
  - Las reglas de Ingress no funcionan
  - No se crea el load balancer

- **Métodos de diagnóstico:**
  - Comprobar el estado del Service:
    ```bash
    kubectl describe service <service_name>
    ```
  - Comprobar el estado del ingress:
    ```bash
    kubectl describe ingress <ingress_name>
    ```
  - Comprobar los logs del Pod del ingress controller:
    ```bash
    kubectl logs -n <ingress_namespace> <ingress_controller_pod>
    ```
  - Comprobar endpoints:
    ```bash
    kubectl get endpoints <service_name>
    ```

- **Métodos de resolución:**
  - Verificar que el selector del Service coincida con las labels de los Pods
  - Reinstalar o actualizar el ingress controller
  - Comprobar el tipo de Service y la configuración de puertos
  - Comprobar la configuración del load balancer del cloud provider

**4. Problemas de networking de Nodes:**

- **Síntomas:**
  - Node desconectado del cluster
  - Fallo de comunicación Node-to-node
  - Errores de conexión de kubelet

- **Métodos de diagnóstico:**
  - Comprobar el estado del Node:
    ```bash
    kubectl describe node <node_name>
    ```
  - Comprobar interfaces de red del Node:
    ```bash
    # Directly on the node
    ip addr
    ip route
    ```
  - Comprobar reglas de firewall:
    ```bash
    # Directly on the node
    iptables -L
    ```
  - Comprobar logs de kubelet:
    ```bash
    journalctl -u kubelet
    ```

- **Métodos de resolución:**
  - Reconfigurar interfaces de red del Node
  - Modificar reglas de firewall
  - Reiniciar kubelet
  - Reiniciar el Node si es necesario

**5. Problemas de Network Policy:**

- **Síntomas:**
  - Bloqueo inesperado de conexiones
  - No se puede comunicar entre namespaces específicos
  - Solo algunos Pods son accesibles

- **Métodos de diagnóstico:**
  - Comprobar network policies:
    ```bash
    kubectl get networkpolicy -A
    kubectl describe networkpolicy <policy_name> -n <namespace>
    ```
  - Comprobar labels de Pods:
    ```bash
    kubectl get pods --show-labels
    ```
  - Verificar que el plugin de red soporte network policies

- **Métodos de resolución:**
  - Modificar o eliminar network policies
  - Modificar labels de Pods
  - Usar herramientas de debugging de network policy

**6. Herramientas comunes de debugging de networking:**

- **Pod de debugging de red:**
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

- **Herramientas de debugging específicas del plugin CNI:**
  - Calico: `calicoctl`
  - Cilium: `cilium`
  - Weave: `weave`

**7. Buenas prácticas:**

- Documentar la topología de red
- Realizar pruebas de conectividad regulares
- Analizar el impacto antes de cambios de network policy
- Planificar los rangos CIDR de red del cluster
- Implementar herramientas de monitoreo de red
</details>
## Preguntas prácticas

1. Escribe un manifest ResourceQuota que cumpla los siguientes requisitos:
   - Namespace: development
   - Pods máximos: 20
   - CPU requests máximos: 4 cores
   - Memory requests máximos: 8Gi
   - PVCs máximos: 10
   - Storage requests máximos: 100Gi

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

Este ResourceQuota establece los siguientes limits en el namespace 'development':
- Máximo de 20 pods
- CPU requests totales de 4 cores
- Memory requests totales de 8Gi
- Máximo de 10 PersistentVolumeClaims
- Storage requests totales de 100Gi

Para aplicar el ResourceQuota:
```bash
kubectl apply -f resource-quota.yaml
```

Para comprobar el uso actual de la quota:
```bash
kubectl describe quota dev-quota -n development
```

Nota: El namespace ya debe existir antes de aplicar el ResourceQuota. Si el namespace no existe, créalo primero:
```bash
kubectl create namespace development
```
</details>

2. Escribe un script que compruebe el estado del Service kubelet en todos los Nodes del cluster y resuelva problemas si se encuentran.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
#!/bin/bash
# Filename: check_kubelet.sh
# Description: Check kubelet service status on all nodes and troubleshoot

# Get node list
NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')

# Iterate over each node
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
      echo "kubelet service failed to start. Checking logs..."
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
1. Usa `kubectl get nodes` para obtener una lista de todos los Nodes del cluster.
2. Para cada Node:
   - Comprueba el estado Ready del Node.
   - Se conecta al Node mediante SSH para comprobar el estado del Service kubelet.
   - Inicia el Service si kubelet no está en ejecución.
   - Vuelve a comprobar el estado después de iniciar el Service.
   - Comprueba logs si el inicio falla.
   - Comprueba configuraciones clave en el archivo de configuración de kubelet.

**Uso:**
```bash
chmod +x check_kubelet.sh
./check_kubelet.sh
```

**Notas:**
- Se requiere acceso SSH a todos los Nodes para ejecutar este script.
- Se recomienda autenticación basada en claves SSH para entornos de producción.
- En entornos cloud, el acceso SSH directo a Nodes puede estar restringido, por lo que puede que necesites usar las herramientas de administración de Nodes del cloud provider.
</details>

3. Configura un cron job que haga backup de la base de datos etcd del cluster y almacene el archivo de backup en una ubicación segura.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**1. Crear script de backup:**

```bash
#!/bin/bash
# Filename: backup_etcd.sh
# Description: etcd database backup and remote storage

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

**2. Otorgar permiso de ejecución al script:**

```bash
chmod +x /opt/etcd-backup/backup_etcd.sh
```

**3. Configurar cron job:**

```bash
# Edit root user's crontab
sudo crontab -e
```

Añade el siguiente contenido:

```
# Run etcd backup daily at 2 AM
0 2 * * * /opt/etcd-backup/backup_etcd.sh >> /var/log/etcd-backup.log 2>&1
```

**4. Configurar rotación de logs de backup:**

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

**5. Probar backup:**

```bash
sudo /opt/etcd-backup/backup_etcd.sh
```

**6. Configurar monitoreo de backup (opcional):**

Para recibir alertas ante fallos de backup, puedes integrarlo con herramientas de monitoreo como Prometheus. Añade el siguiente código al script de backup:

```bash
# Create file indicating backup success/failure
if [ $? -eq 0 ]; then
  echo "success" > /var/lib/node_exporter/etcd_backup_status.prom
else
  echo "failure" > /var/lib/node_exporter/etcd_backup_status.prom
fi
```

**Notas:**
- Los archivos de backup deben almacenarse en una ubicación segura fuera del cluster.
- En entornos cloud, se recomienda usar object storage como S3 o GCS.
- Realiza regularmente pruebas de restauración de backup para verificar la validez del backup.
- Para clusters HA de etcd, el backup solo necesita realizarse en una instancia de etcd.
</details>
4. Escribe un procedimiento para realizar rolling updates en todos los Nodes del cluster. La disponibilidad del workload debe mantenerse durante las actualizaciones.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Procedimiento de rolling update de Nodes:**

```bash
#!/bin/bash
# Filename: node_rolling_update.sh
# Description: Perform cluster node rolling update

# Variable settings
UPGRADE_COMMAND="sudo apt update && sudo apt upgrade -y"
REBOOT_REQUIRED_CHECK="[ -f /var/run/reboot-required ]"
MAX_UNAVAILABLE=1  # Number of nodes to update at once

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

echo "Updating $NODE_COUNT nodes total."
echo "Node list: $NODES"
echo "Maximum $MAX_UNAVAILABLE node(s) will be updated at once."
echo "Press Enter to continue. Press Ctrl+C to cancel."
read

# Iterate over each node
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

  # Check if reboot is required
  REBOOT_REQUIRED=$(ssh $NODE "$REBOOT_REQUIRED_CHECK && echo 'true' || echo 'false'")

  if [ "$REBOOT_REQUIRED" == "true" ]; then
    echo "Reboot required. Rebooting..."
    ssh $NODE "sudo reboot"

    # Wait until node is Ready again
    echo "Node rebooting. Waiting until Ready..."
    while true; do
      STATUS=$(kubectl get node $NODE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
      if [ "$STATUS" == "True" ]; then
        echo "Node is now Ready."
        break
      fi
      echo "Node is not Ready yet. Checking again in 10 seconds."
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

  # Wait for pods to be rescheduled on the node
  echo "Waiting for pods to be rescheduled on the node..."
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

**Preparación previa al rolling update:**

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
   Verifica que los Nodes restantes puedan manejar todos los workloads cuando se retire un Node.

3. **Realizar backup:**
   Realiza backup de la base de datos etcd antes de las actualizaciones.

**Buenas prácticas de rolling update:**

1. **Enfoque gradual:**
   - Actualizar solo un Node a la vez
   - Verificar el estado del cluster después de cada actualización de Node

2. **Automatización e idempotencia:**
   - Automatizar el proceso usando scripts
   - Diseñar para reintentos seguros ante fallos

3. **Monitoreo mejorado:**
   - Monitorear métricas del cluster durante las actualizaciones
   - Monitorear el estado y rendimiento de la aplicación

4. **Plan de rollback:**
   - Preparar procedimientos de rollback para problemas
   - Tener métodos para restaurar al estado anterior

5. **Comunicación:**
   - Anunciar el calendario de actualización y el impacto esperado
   - Informar regularmente del progreso de la actualización

**Notas:**
- En entornos cloud, puedes aprovechar las funcionalidades de actualización de Nodes de los managed Kubernetes services (EKS, GKE, AKS, etc.).
- Si hay varios grupos de Nodes, realiza las actualizaciones por grupo.
- Monitorea especialmente el estado de los system pods críticos (CoreDNS, kube-proxy, etc.).
</details>

5. Escribe un script que identifique pods con alto uso de recursos en el cluster y genere un reporte con esa información.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
#!/bin/bash
# Filename: resource_usage_report.sh
# Description: Identify pods with high resource usage in the cluster and generate report

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
echo "===== Pods with High Usage Relative to Requests =====" >> $REPORT_FILE
echo "Collecting pod information..." >> $REPORT_FILE

# Create temporary files
PODS_USAGE_FILE="$REPORT_DIR/pods-usage-$DATE.tmp"
PODS_REQUESTS_FILE="$REPORT_DIR/pods-requests-$DATE.tmp"

# Collect current usage
kubectl top pods --all-namespaces | tail -n +2 > $PODS_USAGE_FILE

# Collect resource requests for all pods in all namespaces
echo "Namespace,Pod,CPU Request(m),Memory Request(Mi)" > $PODS_REQUESTS_FILE
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get pods -n $ns -o jsonpath='{range .items[*]}{.metadata.namespace},{.metadata.name},{range .spec.containers[*]}{.resources.requests.cpu}{","}{.resources.requests.memory}{"\n"}{end}{end}' | sed 's/$/,/' | sed 's/,$//' >> $PODS_REQUESTS_FILE
done

# Calculate usage relative to requests and add to report
echo "Pods with high CPU usage (usage/request > 80%):" >> $REPORT_FILE
while read line; do
  ns=$(echo $line | awk '{print $1}')
  pod=$(echo $line | awk '{print $2}')
  cpu_usage=$(echo $line | awk '{print $3}' | sed 's/m//')

  # Find CPU request for the pod
  cpu_request=$(grep "$ns,$pod," $PODS_REQUESTS_FILE | awk -F, '{print $3}' | sed 's/[^0-9m.]//g' | sed 's/m//')

  # Show as "not set" if no CPU request
  if [ -z "$cpu_request" ] || [ "$cpu_request" == "" ]; then
    echo "$ns/$pod: CPU usage ${cpu_usage}m, request not set" >> $REPORT_FILE
  else
    # Calculate CPU usage percentage
    cpu_percentage=$(echo "scale=2; $cpu_usage / $cpu_request * 100" | bc)

    # Only show if usage is 80% or higher
    if (( $(echo "$cpu_percentage >= 80" | bc -l) )); then
      echo "$ns/$pod: CPU usage ${cpu_usage}m, request ${cpu_request}m, utilization ${cpu_percentage}%" >> $REPORT_FILE
    fi
  fi
done < $PODS_USAGE_FILE

echo "" >> $REPORT_FILE
echo "Pods with high memory usage (usage/request > 80%):" >> $REPORT_FILE
while read line; do
  ns=$(echo $line | awk '{print $1}')
  pod=$(echo $line | awk '{print $2}')
  mem_usage=$(echo $line | awk '{print $4}' | sed 's/Mi//')

  # Find memory request for the pod
  mem_request=$(grep "$ns,$pod," $PODS_REQUESTS_FILE | awk -F, '{print $4}' | sed 's/[^0-9Mi.]//g' | sed 's/Mi//')

  # Show as "not set" if no memory request
  if [ -z "$mem_request" ] || [ "$mem_request" == "" ]; then
    echo "$ns/$pod: Memory usage ${mem_usage}Mi, request not set" >> $REPORT_FILE
  else
    # Calculate memory usage percentage
    mem_percentage=$(echo "scale=2; $mem_usage / $mem_request * 100" | bc)

    # Only show if usage is 80% or higher
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

# HTML report generation (optional)
HTML_REPORT="${REPORT_FILE%.txt}.html"
echo "<html><head><title>Kubernetes Resource Usage Report</title>" > $HTML_REPORT
echo "<style>body{font-family:Arial;margin:20px}h1{color:#326ce5}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:8px}th{background-color:#f2f2f2}</style>" >> $HTML_REPORT
echo "</head><body>" >> $HTML_REPORT
echo "<h1>Kubernetes Cluster Resource Usage Report</h1>" >> $HTML_REPORT
echo "<p>Generated: $(date)</p>" >> $HTML_REPORT

# Convert report content to HTML
awk '/===== Cluster Information =====/{flag=1;print "<h2>Cluster Information</h2><pre>"}/===== Node Resource Usage =====/{flag=0;print "</pre><h2>Node Resource Usage</h2><table><tr><th>Node</th><th>CPU(%)</th><th>Memory(%)</th></tr>"}/===== Top.*CPU Usage/{flag=0;print "</table><h2>Top Pods by CPU Usage</h2><table><tr><th>Namespace</th><th>Pod</th><th>CPU(m)</th><th>Memory(Mi)</th></tr>"}/===== Top.*Memory Usage/{flag=0;print "</table><h2>Top Pods by Memory Usage</h2><table><tr><th>Namespace</th><th>Pod</th><th>CPU(m)</th><th>Memory(Mi)</th></tr>"}/===== Resource Usage by Namespace =====/{flag=0;print "</table><h2>Resource Usage by Namespace</h2>"}/CPU Usage \(cores\):/{flag=0;print "<h3>CPU Usage (cores)</h3><table><tr><th>Namespace</th><th>CPU(cores)</th></tr>"}/Memory Usage \(GiB\):/{flag=0;print "</table><h3>Memory Usage (GiB)</h3><table><tr><th>Namespace</th><th>Memory(GiB)</th></tr>"}/===== Pods with High Usage Relative to Requests =====/{flag=0;print "</table><h2>Pods with High Usage Relative to Requests</h2>"}/Pods with high CPU usage/{flag=0;print "<h3>Pods with High CPU Usage (usage/request > 80%)</h3><ul>"}/Pods with high memory usage/{flag=0;print "</ul><h3>Pods with High Memory Usage (usage/request > 80%)</h3><ul>"}/===== Pods Without Resource Requests =====/{flag=0;print "</ul><h2>Pods Without Resource Requests</h2><ul>"}/===== Report Summary =====/{flag=0;print "</ul><h2>Report Summary</h2><ul>"}{if(flag==1)print;else if($0 ~ /^NAME/){print "<tr>";for(i=1;i<=NF;i++)print "<th>"$i"</th>";print "</tr>"}else if($0 ~ /^[a-z].*[0-9]%/){print "<tr>";for(i=1;i<=NF;i++)print "<td>"$i"</td>";print "</tr>"}else if($0 ~ /^[a-z].*[0-9]m/){print "<tr>";for(i=1;i<=NF;i++)print "<td>"$i"</td>";print "</tr>"}else if($0 ~ /^[a-z].* [0-9]/){print "<tr><td>"$1"</td><td>"$2"</td></tr>"}else if($0 ~ /^[a-z].*\//){print "<li>"$0"</li>"}else if($0 ~ /^Total/){print "<li>"$0"</li>"}}' $REPORT_FILE >> $HTML_REPORT

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
2. Recopila uso de recursos de Nodes
3. Identifica los principales pods por uso de CPU y memoria
4. Calcula el uso de recursos por namespace
5. Identifica pods con alto uso relativo a requests
6. Identifica pods sin resource requests
7. Genera reportes en formatos de texto y HTML

**Notas:**
- Este script requiere las herramientas `kubectl`, `jq` y `bc`.
- Metrics Server debe estar instalado en el cluster.
- El tiempo de ejecución del script puede ser mayor en clusters grandes.
- Puede configurarse como cron job para la generación regular de reportes.
- Los reportes pueden enviarse por correo electrónico o integrarse con sistemas de monitoreo.
</details>
## Temas avanzados

1. ¿Cuáles son los parámetros de configuración clave y las buenas prácticas para optimizar el rendimiento de etcd en un cluster Kubernetes?
   - A) `--max-request-bytes`, `--quota-backend-bytes`, compactación regular
   - B) `--max-concurrent-requests`, `--max-connections`, configuración RAID de disco
   - C) `--auto-compaction-retention`, `--snapshot-count`, almacenamiento SSD
   - D) `--max-txn-ops`, `--max-result-buffer`, ampliación de memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `--auto-compaction-retention`, `--snapshot-count`, almacenamiento SSD**

**Explicación:**
etcd es el almacén de datos central para clusters Kubernetes, y su rendimiento afecta directamente el rendimiento general del cluster. Los parámetros de configuración clave y las buenas prácticas para optimizar el rendimiento de etcd son los siguientes:

1. **`--auto-compaction-retention`**: etcd es un almacén append-only que conserva un historial de todos los cambios. Este parámetro establece el intervalo para compactar automáticamente versiones anteriores de keys. El valor predeterminado es 0 (deshabilitado), pero en entornos de producción suele configurarse en 1 hora (1h) o 24 horas (24h). Esto ayuda a ahorrar espacio en disco y mejorar el rendimiento.

2. **`--snapshot-count`**: Especifica el número de transacciones que se deben confirmar antes de que etcd cree un snapshot. El valor predeterminado es 100,000, pero en clusters grandes este valor puede ajustarse para optimizar la frecuencia de creación de snapshots. Los valores más pequeños crean snapshots con más frecuencia, reduciendo el tiempo de recovery pero aumentando el I/O de disco.

3. **Almacenamiento SSD**: etcd es sensible al I/O de disco, por lo que usar SSDs (Solid State Drives) mejora significativamente el rendimiento. El uso de SSD es esencial en clusters grandes.

Otros ajustes importantes de optimización y buenas prácticas:

- **Usar discos dedicados**: Usa discos dedicados para datos de etcd para evitar contención de I/O con otras aplicaciones.
- **Asignación de memoria adecuada**: etcd almacena datos en caché en memoria para mejorar el rendimiento, por lo que debe asignarse memoria suficiente.
- **Optimizar el tamaño del cluster**: Normalmente, 3-5 miembros de etcd proporcionan rendimiento y disponibilidad óptimos.
- **Minimizar la latencia de red**: Ubica los miembros de etcd en el mismo data center o availability zone para minimizar la latencia de red entre miembros.
- **Backup y compactación regulares**: Realiza backups y compactación regulares para garantizar la seguridad de los datos y el uso eficiente del espacio en disco.

`--max-request-bytes` y `--quota-backend-bytes` son parámetros reales de etcd, pero están relacionados principalmente con límites de recursos más que con rendimiento. `--max-concurrent-requests`, `--max-connections`, `--max-txn-ops` y `--max-result-buffer` no son parámetros reales de etcd o no son factores principales en la optimización del rendimiento.
</details>

2. ¿Cuál es la forma más efectiva de implementar alta disponibilidad (HA) del control plane en un cluster Kubernetes?
   - A) Ejecutar varias instancias de API server en un único master node
   - B) Configurar un cluster etcd con varios master nodes y un load balancer
   - C) Desplegar el API server como StatefulSet con PersistentVolume
   - D) Implementar un proceso watchdog con auto-recovery en el master node

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar un cluster etcd con varios master nodes y un load balancer**

**Explicación:**
La forma más efectiva de implementar alta disponibilidad (HA) del control plane de Kubernetes es configurar un cluster etcd con varios master nodes y un load balancer. Este enfoque consta de los siguientes componentes:

1. **Varios master nodes**: Normalmente se despliegan 3 o 5 master nodes en distintas availability zones para eliminar puntos únicos de falla. Cada master node ejecuta los siguientes componentes del control plane:
   - kube-apiserver: Server que gestiona solicitudes API
   - kube-controller-manager: Ejecuta procesos de controller
   - kube-scheduler: Decisiones de scheduling de Pod

2. **Cluster etcd**: etcd es un key-value store distribuido que almacena todos los datos del cluster Kubernetes. Para alta disponibilidad, normalmente se ejecutan 3 o 5 instancias de etcd. etcd puede ejecutarse directamente en master nodes o en Nodes dedicados.

3. **Load balancer**: Se necesita un load balancer para distribuir solicitudes de clientes entre varias instancias de kube-apiserver. Esto normalmente se implementa usando servicios de load balancer del cloud provider o load balancers de software como HAProxy o Nginx.

Beneficios clave de esta configuración:
- **Tolerancia a fallos**: El cluster continúa operando incluso si falla un master node.
- **Alta disponibilidad**: Desplegar en varias availability zones puede manejar incluso fallos a nivel de data center.
- **Escalabilidad**: Las solicitudes al API server pueden distribuirse y procesarse entre varias instancias.
- **Consistencia de datos**: El algoritmo de consenso Raft de etcd garantiza la consistencia de los datos.

Problemas con otras opciones:
- Ejecutar varias instancias de API server en un solo master node convierte al propio Node en un punto único de falla.
- Desplegar el API server como StatefulSet no es un enfoque común, y los componentes del control plane normalmente se administran fuera de Kubernetes.
- Un proceso watchdog puede ser útil, pero por sí solo no es una solución real de alta disponibilidad.
</details>

3. ¿Cuál es la consideración más importante al configurar audit logging en un cluster Kubernetes?
   - A) Registrar todas las solicitudes API para garantizar una audit trail completa
   - B) Usar audit policies para registrar selectivamente solo eventos importantes
   - C) Streaming en tiempo real de audit logs a un sistema SIEM externo
   - D) Restringir el acceso a audit logs solo a administradores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar audit policies para registrar selectivamente solo eventos importantes**

**Explicación:**
La consideración más importante al configurar audit logging de Kubernetes es usar audit policies para registrar selectivamente solo eventos importantes. Esto es importante por las siguientes razones:

1. **Minimizar el impacto en el rendimiento**: Registrar todas las solicitudes API puede imponer una carga significativa en el API server y degradar el rendimiento. Los clusters grandes pueden tener miles de solicitudes API por segundo.

2. **Eficiencia de almacenamiento**: Registrar todos los eventos hace que los datos de logs crezcan rápidamente, aumentando costos de almacenamiento y dificultando el análisis de logs.

3. **Centrarse en información relevante**: Al registrar solo eventos importantes, los analistas de seguridad pueden centrarse en información crítica.

4. **Compliance**: Muchos requisitos de compliance requieren registrar tipos específicos de eventos, no todos los eventos.

Las audit policies de Kubernetes admiten los siguientes niveles de auditoría:

- **None**: No registra el evento.
- **Metadata**: Registra solo metadata de la solicitud (usuario, timestamp, recurso, acción, etc.) y excluye el cuerpo de la solicitud/respuesta.
- **Request**: Registra metadata y cuerpo de la solicitud, pero excluye el cuerpo de la respuesta.
- **RequestResponse**: Registra metadata, cuerpo de la solicitud y cuerpo de la respuesta.

Ejemplo de una audit policy efectiva:
```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
# Set logging level for authentication and authorization requests
- level: Metadata
  users: ["system:anonymous"]
  verbs: ["get", "list", "watch"]

# Log changes to sensitive resources like Secret, ConfigMap in detail
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
- El streaming en tiempo real a sistemas SIEM externos es importante, pero tiene menor prioridad que decidir qué registrar.
- Restringir el acceso a audit logs es importante, pero es una medida de seguridad más que la propia política de logging.
</details>

4. ¿Cuál es la forma más efectiva de implementar node auto-repair en un cluster Kubernetes?
   - A) Desplegar un DaemonSet que monitoree el estado de Nodes y reinicie automáticamente Nodes problemáticos
   - B) Utilizar managed node groups y funcionalidades de auto-repair del cloud provider
   - C) Usar Node Problem Detector y custom controllers para monitoreo y recovery del estado de Nodes
   - D) Implementar un cron job que compruebe periódicamente el estado de Nodes y recree Nodes problemáticos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar Node Problem Detector y custom controllers para monitoreo y recovery del estado de Nodes**

**Explicación:**
La forma más efectiva de implementar node auto-repair en un cluster Kubernetes es usar Node Problem Detector junto con custom controllers. Este enfoque proporciona los siguientes beneficios:

1. **Detección precisa de problemas**: Node Problem Detector (NPD) es una herramienta de propósito especial que puede detectar diversos problemas de Node, incluyendo:
   - Errores y crashes de Kernel
   - Problemas de hardware
   - Problemas del file system
   - Problemas de red
   - Problemas de escasez de recursos

2. **Respuesta flexible**: Los custom controllers permiten implementar diversas estrategias de recovery para los problemas detectados:
   - Problemas menores: reinicio de Node
   - Problemas graves: reemplazo de Node
   - Tipos específicos de problemas: reinicio de Service específico

3. **Integración nativa con Kubernetes**: NPD informa el estado de Nodes como NodeConditions, integrándose bien con los mecanismos existentes de Kubernetes.

4. **Independiente del cloud**: Este enfoque funciona en todos los entornos (on-premises, varios cloud providers).

Pasos de implementación:

1. **Desplegar Node Problem Detector**:
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/node-problem-detector/master/deployment/node-problem-detector.yaml
   ```

2. **Implementar custom controller**:
   - Observar eventos de Kubernetes y cambios de estado de Nodes
   - Implementar lógica para responder a NodeConditions específicas
   - Realizar acciones de recovery (ejecución de comandos mediante SSH, recreación de Node mediante cloud API, etc.)

3. **Configurar alertas y logging**:
   - Configurar alertas para acciones de recovery
   - Registrar problemas y acciones de recovery

Problemas con otras opciones:

- **Enfoque DaemonSet**: Si el Node tiene problemas graves, el propio DaemonSet puede verse afectado, y es difícil detectar todos los tipos de problemas.

- **Managed node groups del cloud provider**: Está ligado a cloud providers específicos y no puede usarse en entornos on-premises. Los tipos de problemas que pueden detectarse también pueden estar limitados.

- **Enfoque cron job**: Tiempo de reacción lento, capacidad limitada de detección de problemas, y debe ejecutarse fuera del cluster.

Combinar Node Problem Detector con custom controllers permite implementar una solución de node auto-repair potente y flexible que funciona en varios entornos.
</details>

5. ¿Cuáles son las mejores prácticas para administrar eficazmente RBAC (Role-Based Access Control) en un cluster Kubernetes?
   - A) Otorgar el rol cluster-admin a todos los usuarios para facilitar la administración
   - B) Definir roles granulares por namespace y aplicar el principio de least privilege
   - C) Consolidar todos los permisos en un único ClusterRole para mantener la consistencia
   - D) Usar siempre certificados de usuario en lugar de service accounts para autenticación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Definir roles granulares por namespace y aplicar el principio de least privilege**

**Explicación:**
La mejor práctica para administrar eficazmente RBAC (Role-Based Access Control) en un cluster Kubernetes es definir roles granulares por namespace y aplicar el principio de least privilege. Este enfoque proporciona los siguientes beneficios:

1. **Principio de least privilege**: Otorga solo los permisos mínimos necesarios a usuarios y service accounts para minimizar el riesgo de seguridad. Esto ayuda a proteger el cluster de cambios no intencionados o acciones maliciosas.

2. **Aislamiento por namespace**: Definir roles por namespace refuerza el aislamiento lógico entre equipos o aplicaciones. Esto evita que errores de un equipo afecten los recursos de otro equipo.

3. **Control de acceso granular**: Los permisos pueden controlarse de forma precisa para tipos de recursos o acciones específicos. Por ejemplo, a los desarrolladores se les puede otorgar permiso para administrar pods y services mientras se restringen permisos para modificar secrets o el propio namespace.

4. **Facilidad de auditoría**: Usar roles granulares documenta claramente quién puede realizar qué acciones, lo que facilita auditorías y compliance.

Ejemplos de implementación de buenas prácticas RBAC:

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
     verbs: ["get", "list", "watch"]  # Only allow reading secrets
   ```

2. **Crear role binding**:
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

- **Otorgar el rol cluster-admin a todos los usuarios**: Esto presenta riesgos graves de seguridad. Todos los usuarios tendrían acceso completo a todos los recursos del cluster, haciéndolo vulnerable a cambios no intencionados o acciones maliciosas.

- **Consolidar todos los permisos en un único ClusterRole**: Esto hace imposible el control de acceso granular y viola el principio de least privilege.

- **Usar siempre certificados de usuario**: Las service accounts son adecuadas para la autenticación de aplicaciones, y usar certificados de usuario en todas las situaciones aumenta la carga de administración. Es importante elegir el mecanismo de autenticación apropiado según la situación.
</details>
