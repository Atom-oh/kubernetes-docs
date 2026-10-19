# Cuestionario de administración de clústeres

Este cuestionario abarca operaciones autogestionadas y de EKS, copias de seguridad, mantenimiento, supervisión y recuperación. Se conservan los 15 ejercicios originales; los procedimientos de etcd a nivel de host no se aplican al plano de control administrado de EKS.

## Preguntas de respuesta corta

1. Explica los procedimientos para respaldar y restaurar la base de datos etcd de un clúster Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Procedimiento de copia de seguridad de etcd:**

1. **Verifica que la herramienta etcdctl esté instalada:**
   ```bash
   etcdctl version
   ```

2. **Ejecuta el comando de copia de seguridad:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
     --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key
   ```

3. **Verifica el archivo de copia de seguridad:**
   ```bash
   etcdutl snapshot status snapshot.db --write-out=table
   ```

4. **Guarda el archivo en una ubicación segura:**
   - Almacenamiento fuera del clúster
   - Almacenamiento en la nube (S3, GCS, etc.)
   - Otra ubicación física

**Procedimiento de restauración de etcd:**

1. Valida la instantánea y conserva los datos originales, PKI y claves/configuración del proveedor de cifrado. Una instantánea de etcd no incluye archivos de volúmenes persistentes ni toda la configuración del host.
2. Detén todos los API servers y los procesos etcd afectados siguiendo el procedimiento de la distribución. kubeadm suele usar Pods estáticos, no unidades systemd independientes; detener kubelet por sí solo no detiene esos contenedores.
3. Restaura sin conexión en un directorio nuevo con una versión compatible de etcdutl. Este ejemplo de un solo miembro no sirve como comando de recuperación de un clúster de alta disponibilidad:
```bash
etcdutl snapshot restore snapshot.db \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-1 \
  --initial-cluster=etcd-1=https://127.0.0.1:2380 \
  --initial-cluster-token=restored-cluster \
  --initial-advertise-peer-urls=https://127.0.0.1:2380 \
  --bump-revision=1000000000 --mark-compacted
```

4. En una configuración de alta disponibilidad, restaura la misma instantánea en cada miembro, con su propio nombre/URL de pares y la misma lista completa de miembros. Aumenta la revisión lo suficiente para superar las escrituras hechas desde la instantánea e invalidar las cachés de watch.
5. Configura el manifiesto/servicio de etcd para usar los datos restaurados, con la propiedad y los certificados correctos. Comprueba el cuórum y la salud de etcd antes de reiniciar los API servers/controladores; después verifica los nodos y las cargas de trabajo.
6. Sigue el [procedimiento oficial de recuperación](https://etcd.io/docs/v3.6/op-guide/recovery/). En EKS, restaura los recursos y datos de las aplicaciones con herramientas de copia de seguridad admitidas, en lugar de acceder al etcd administrado.

**Prácticas recomendadas:**
- Programa copias de seguridad periódicas (por ejemplo, a diario).
- Comprueba el estado del clúster etcd antes de hacer la copia.
- Valida la integridad del archivo de copia de seguridad.
- Prueba periódicamente los procedimientos de restauración.
- Incluye marcas de tiempo en los nombres de archivo.
- Conserva varias versiones de las copias.
- Documenta los procedimientos de copia y restauración.
</details>

2. Explica el procedimiento de mantenimiento de nodos de un clúster Kubernetes y las diferencias entre los comandos `cordon`, `drain` y `uncordon`.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Procedimiento de mantenimiento de nodos:**

1. **Comprueba el estado del nodo:**
   ```bash
   kubectl get nodes
   kubectl describe node <node_name>
   ```

2. **Marca el nodo como no programable (cordon):**
   ```bash
   kubectl cordon <node_name>
   ```

3. **Desaloja sus Pods (drain):**
   ```bash
   kubectl drain <node_name> --ignore-daemonsets
   ```

4. **Realiza las tareas de mantenimiento:**
   - Actualizaciones de software
   - Actualizaciones del kernel
   - Sustitución de hardware
   - Cambios de configuración

5. **Vuelve a permitir la programación en el nodo al terminar (uncordon):**
   ```bash
   kubectl uncordon <node_name>
   ```

6. **Verifica el estado del nodo:**
   ```bash
   kubectl get nodes
   ```

**Diferencias entre los comandos:**

1. **`kubectl cordon <node_name>`:**
   - Marca el nodo como no programable.
   - No se programarán Pods nuevos en ese nodo.
   - Los Pods que ya se ejecutan allí siguen funcionando.
   - El estado del nodo muestra el indicador `SchedulingDisabled`.

2. **`kubectl drain <node_name>`:**
   - Marca el nodo como no programable (incluye cordon).
   - Evacúa de forma segura los Pods en ejecución.
   - Los controladores de cargas de trabajo pueden crear Pods de reemplazo; su programación depende de la capacidad y las restricciones.
   - drain rechaza los Pods de DaemonSet salvo que se indique `--ignore-daemonsets`; esa opción los deja en ejecución.
   - Los Pods que usan volúmenes emptyDir pueden perder datos y requerir el tratamiento especial de la opción `--delete-emptydir-data`.
   - Respeta los PodDisruptionBudgets.

3. **`kubectl uncordon <node_name>`:**
   - Vuelve a marcar el nodo como programable.
   - Se pueden programar Pods nuevos en él.
   - Los Pods desalojados no regresan automáticamente.

**Consideraciones de mantenimiento:**
- Asegura que el clúster tenga capacidad libre suficiente.
- Configura PodDisruptionBudgets para las cargas de trabajo críticas.
- Mantén un nodo a la vez.
- Ajusta la configuración de autoescalado durante el mantenimiento.
- Verifica el estado de las cargas de trabajo antes y después.
- Usa estrategias de actualización gradual.
</details>

3. Explica cómo supervisar y administrar el uso de recursos en un clúster Kubernetes. Enumera las herramientas y técnicas que conviene incluir.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Métodos para supervisar y administrar los recursos de Kubernetes:**

**1. Herramientas básicas de supervisión:**

- **Metrics Server:**
  - Proporciona métricas básicas de uso de CPU y memoria.
  - Permite usar los comandos `kubectl top`.
  - Ejemplo de instalación para Kubernetes 1.34 o posterior (verifica primero los requisitos y si ya está instalado):
    ```bash
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.9.0/components.yaml
    ```
  - Ejemplos de uso:
    ```bash
    kubectl top nodes
    kubectl top pods --all-namespaces
    ```

- **Headlamp (Kubernetes Dashboard está archivado):**
  - Presenta visualmente el estado del clúster y el uso de recursos.
  - Ofrece una interfaz para administrar Pods, nodos, namespaces y otros recursos.

**2. Pila avanzada de supervisión:**

- **Prometheus + Grafana:**
  - Prometheus recopila y almacena métricas.
  - Grafana visualiza las métricas y los dashboards.
  - Se pueden instalar con kube-prometheus-stack o Prometheus Operator.
  - Admiten reglas de alerta y dashboards personalizados.

- **Pila ELK/EFK:**
  - Elasticsearch almacena y permite buscar logs.
  - Logstash/Fluentd recopila y procesa logs.
  - Kibana visualiza y analiza logs.

**3. Técnicas de administración de recursos:**

- **Configurar solicitudes y límites de recursos:**
  ```yaml
  resources:
    requests:
      memory: "64Mi"
      cpu: "250m"
    limits:
      memory: "128Mi"
      cpu: "500m"
  ```

- **Cuotas de recursos por namespace (ResourceQuota):**
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
  - Ajusta automáticamente las solicitudes de CPU y memoria de los Pods.
  - Ofrece recomendaciones basadas en los patrones de uso de recursos.

- **Cluster Autoscaler:**
  - Ajusta automáticamente el número de nodos del clúster según las necesidades de las cargas de trabajo.
  - Añade nodos cuando faltan recursos y los elimina cuando la utilización es baja.

**4. Prácticas recomendadas de supervisión:**

- Configura solicitudes y límites de recursos para todos los Pods.
- Configura alertas para las métricas críticas.
- Planifica los recursos a partir del análisis del uso histórico.
- Realiza auditorías periódicas de recursos.
- Analiza las tendencias de uso para optimizar los costos.
- Define cuotas de recursos adecuadas para desarrollo, pruebas y producción.
- Supervisa las métricas tanto de los nodos como de los Pods.
</details>

4. Explica los principales riesgos de una actualización de un clúster Kubernetes y las estrategias para mitigarlos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Riesgos de actualizar un clúster Kubernetes y estrategias de mitigación:**

**1. Riesgos principales:**

- **Problemas de compatibilidad de API:**
  - Las API pueden cambiar o eliminarse en versiones nuevas.
  - Algunas Custom Resource Definitions (CRD) o versiones de API pueden dejar de admitirse.

- **Interrupción de cargas de trabajo:**
  - El API server puede dejar de estar disponible temporalmente al reiniciar componentes del plano de control.
  - La reprogramación de Pods durante las actualizaciones de nodos puede interrumpir servicios.

- **Cambios de funcionalidades:**
  - Los comportamientos predeterminados pueden cambiar y afectar a las cargas de trabajo existentes.
  - Los cambios en las políticas de seguridad pueden causar problemas de permisos.

- **Problemas de rendimiento:**
  - Las versiones nuevas pueden requerir más recursos.
  - Puede haber una degradación del rendimiento durante la estabilización inicial.

- **Complejidad de la reversión:**
  - Algunas actualizaciones no se pueden revertir fácilmente.
  - Los cambios de formato de datos pueden limitar la reversión.

**2. Estrategias de mitigación:**

- **Planificación y preparación exhaustivas:**
  - **Revisa el registro de cambios:** identifica cambios, funcionalidades eliminadas y problemas conocidos de la nueva versión.
  - **Verifica la ruta de actualización:** confirma que se admite la actualización directa desde la versión actual hasta la de destino.
  - **Revisa los requisitos de recursos:** comprueba los requisitos mínimos de la nueva versión.

- **Prueba primero en un entorno de pruebas:**
  - Actualiza un clúster de pruebas parecido al de producción.
  - Prueba todas las cargas críticas y los recursos personalizados.
  - Ejecuta las suites de pruebas automatizadas.

- **Verifica la compatibilidad de API:**
  - Enumera las versiones de API que se ofrecen actualmente (esto no indica qué versiones usan los clientes):
    ```bash
    kubectl api-resources -o wide
    ```
  - Si tienes acceso a `/metrics`, inspecciona las solicitudes observadas a API obsoletas; audita también los manifiestos y logs de solicitudes:
    ```bash
    kubectl get --raw /metrics | grep '^apiserver_requested_deprecated_apis'
    ```
  - Actualiza los manifiestos cuando sea necesario.

- **Plan de copia de seguridad y recuperación:**
  - Haz una copia de seguridad de la base de datos etcd:
    ```bash
    ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
      --endpoints=https://127.0.0.1:2379 \
      --cacert=/etc/kubernetes/pki/etcd/ca.crt \
      --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
      --key=/etc/kubernetes/pki/etcd/healthcheck-client.key
    ```
  - Exporta un subconjunto de objetos de carga de trabajo (no es una copia completa; protege el archivo generado):
    ```bash
    umask 077
    kubectl get all --all-namespaces -o yaml > workload-subset.yaml
    ```
  - Documenta y prueba los procedimientos de recuperación.

- **Actualización gradual:**
  - **Actualiza primero los componentes del plano de control:**
    - En configuraciones de alta disponibilidad, actualiza un nodo del plano de control a la vez.
  - **Actualiza gradualmente los nodos de trabajo:**
    - Divide los grupos de nodos en lotes pequeños.
    - Comprueba la estabilidad después de cada lote.

- **Protección de las cargas de trabajo:**
  - **Configura PodDisruptionBudget:**
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
  - **Ten cuidado al desalojar nodos:**
    ```bash
    kubectl drain <node_name> --ignore-daemonsets
    ```

- **Supervisión mejorada:**
  - Supervisa el estado del clúster antes, durante y después de la actualización.
  - Presta atención a las métricas y los logs clave.
  - Ajusta temporalmente los umbrales de alerta.

- **Plan de reversión:**
  - Define las condiciones que activan la reversión.
  - Documenta el procedimiento de reversión.
  - Conserva todos los componentes e imágenes que se necesiten para revertir.

- **Plan de comunicación:**
  - Notifica a las partes interesadas el calendario y el impacto previsto.
  - Comunica el estado durante la actualización.
  - Define las vías de escalamiento de problemas.

**3. Consideraciones según la versión:**

- **Actualizaciones de versión menor (por ejemplo, 1.24 → 1.25):**
  - Presta especial atención a las API eliminadas y a los cambios de funcionalidades.
  - Actualiza una versión menor cada vez.

- **Actualizaciones de versión de parche (por ejemplo, 1.24.0 → 1.24.1):**
  - Suelen ser más seguras, pero también requieren pruebas.
  - Considera desplegar más rápidamente los parches de seguridad.
</details>

5. Explica qué problemas de red pueden presentarse en un clúster Kubernetes y cómo diagnosticarlos y resolverlos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Diagnóstico y resolución de problemas de red de Kubernetes:**

**1. Problemas de comunicación entre Pods:**

- **Síntomas:**
  - Los Pods no pueden comunicarse entre sí.
  - No es posible conectarse por el nombre del Service.
  - Se producen errores de tiempo de espera de red.

- **Métodos de diagnóstico:**
  - Comprueba las políticas de red:
    ```bash
    kubectl get networkpolicy --all-namespaces
    ```
  - Crea un Pod de prueba para probar la conectividad:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    ping <target_pod_IP>
    wget -O- <service_name>:<port>
    ```
  - Comprueba el estado de los Pods del complemento CNI:
    ```bash
    kubectl get pods -n kube-system | grep -E 'calico|flannel|weave|cilium'
    ```

- **Métodos de resolución:**
  - Reinstala o actualiza el complemento CNI.
  - Modifica o elimina las políticas de red.
  - Comprueba las interfaces de red de los nodos.
  - Comprueba las reglas del firewall.

**2. Problemas de descubrimiento de servicios y DNS:**

- **Síntomas:**
  - No es posible conectarse por el nombre del Service.
  - Fallan las consultas DNS.
  - Hay problemas de conexión intermitentes.

- **Métodos de diagnóstico:**
  - Comprueba el estado de los Pods de CoreDNS:
    ```bash
    kubectl get pods -n kube-system -l k8s-app=kube-dns
    kubectl logs -n kube-system -l k8s-app=kube-dns
    ```
  - Prueba la resolución DNS:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    nslookup kubernetes.default.svc.cluster.local
    nslookup <service_name>.<namespace>.svc.cluster.local
    cat /etc/resolv.conf
    ```
  - Comprueba los endpoints del Service:
    ```bash
    kubectl get endpoints <service_name>
    ```

- **Métodos de resolución:**
  - Reinicia los Pods de CoreDNS:
    ```bash
    kubectl rollout restart deployment coredns -n kube-system
    ```
  - Comprueba y modifica la configuración DNS:
    ```bash
    kubectl edit configmap coredns -n kube-system
    ```
  - Comprueba la configuración DNS de kubelet.

**3. Problemas de Service e Ingress:**

- **Síntomas:**
  - No se puede acceder al Service desde fuera.
  - Las reglas de Ingress no funcionan.
  - No se crea el balanceador de carga.

- **Métodos de diagnóstico:**
  - Describe el estado del Service:
    ```bash
    kubectl describe service <service_name>
    ```
  - Describe el estado del Ingress:
    ```bash
    kubectl describe ingress <ingress_name>
    ```
  - Comprueba los logs del Pod del controlador de Ingress:
    ```bash
    kubectl logs -n <ingress_namespace> <ingress_controller_pod>
    ```
  - Comprueba los endpoints:
    ```bash
    kubectl get endpoints <service_name>
    ```

- **Métodos de resolución:**
  - Verifica que el selector del Service coincida con las etiquetas de los Pods.
  - Reinstala o actualiza el controlador de Ingress.
  - Comprueba el tipo de Service y la configuración de puertos.
  - Comprueba la configuración del balanceador de carga del proveedor de nube.

**4. Problemas de red de los nodos:**

- **Síntomas:**
  - Un nodo se desconecta del clúster.
  - Falla la comunicación entre nodos.
  - Hay errores de conexión de kubelet.

- **Métodos de diagnóstico:**
  - Describe el estado del nodo:
    ```bash
    kubectl describe node <node_name>
    ```
  - Comprueba las interfaces de red del nodo:
    ```bash
    # Directly on the node
    ip addr
    ip route
    ```
  - Comprueba las reglas del firewall:
    ```bash
    # Directly on the node
    iptables -L
    ```
  - Comprueba los logs de kubelet:
    ```bash
    journalctl -u kubelet
    ```

- **Métodos de resolución:**
  - Reconfigura las interfaces de red del nodo.
  - Modifica las reglas del firewall.
  - Reinicia kubelet.
  - Reinicia el nodo si es necesario.

**5. Problemas con las políticas de red:**

- **Síntomas:**
  - Se bloquean conexiones inesperadamente.
  - No hay comunicación entre determinados namespaces.
  - Solo algunos Pods son accesibles.

- **Métodos de diagnóstico:**
  - Comprueba las políticas de red:
    ```bash
    kubectl get networkpolicy -A
    kubectl describe networkpolicy <policy_name> -n <namespace>
    ```
  - Comprueba las etiquetas de los Pods:
    ```bash
    kubectl get pods --show-labels
    ```
  - Verifica que el complemento de red admita políticas de red.

- **Métodos de resolución:**
  - Modifica o elimina las políticas de red.
  - Modifica las etiquetas de los Pods.
  - Usa herramientas para diagnosticar políticas de red.

**6. Herramientas habituales para diagnosticar problemas de red:**

- **Pod de diagnóstico de red:**
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

- **Herramientas específicas de complementos CNI:**
  - Calico: `calicoctl`
  - Cilium: `cilium`
  - Weave: `weave`

**7. Prácticas recomendadas:**

- Documenta la topología de red.
- Realiza pruebas de conectividad periódicas.
- Analiza el impacto antes de cambiar las políticas de red.
- Planifica los rangos CIDR de red del clúster.
- Implementa herramientas de supervisión de red.
</details>

## Preguntas prácticas

1. Escribe un manifiesto ResourceQuota que cumpla estos requisitos:
   - Namespace: development
   - Máximo de Pods: 20
   - Solicitudes máximas de CPU: 4 núcleos
   - Solicitudes máximas de memoria: 8Gi
   - Máximo de PVC: 10
   - Solicitudes máximas de almacenamiento: 100Gi

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

Este ResourceQuota establece los siguientes límites en el namespace `development`:
- Máximo de 20 Pods.
- Solicitudes totales de CPU: 4 núcleos.
- Solicitudes totales de memoria: 8Gi.
- Máximo de 10 PersistentVolumeClaims.
- Solicitudes totales de almacenamiento: 100Gi.

Para aplicar el ResourceQuota:
```bash
kubectl apply -f resource-quota.yaml
```

Para comprobar el uso actual de la cuota:
```bash
kubectl describe quota dev-quota -n development
```

Nota: el namespace debe existir antes de aplicar el ResourceQuota. Si no existe, créalo primero:
```bash
kubectl create namespace development
```
</details>

2. Escribe una comprobación de kubelet para un clúster Linux autogestionado con alias SSH para cada nodo y con un modo de reparación explícito.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
#!/usr/bin/env bash
# check_kubelet.sh: self-managed Linux nodes with configured SSH aliases only.
set -euo pipefail
repair=${REPAIR_KUBELET:-0}
status=0
nodes=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')
for node in $nodes; do
  printf '%s: ' "$node"
  if state=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
      'sudo -n systemctl is-active kubelet'); then
    printf 'kubelet %s\n' "$state"
    continue
  else
    rc=$?
  fi
  if [ "$rc" -ne 3 ]; then
    printf 'SSH/sudo/service query failed (exit %s); no repair attempted\n' "$rc" >&2
    status=1
    continue
  fi
  printf 'kubelet %s\n' "$state"
  if [ "$repair" != 1 ]; then
    printf 'Inspect logs and approve a repair before rerunning with REPAIR_KUBELET=1\n'
    status=1
    continue
  fi
  if ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
      'sudo -n systemctl start kubelet && sudo -n systemctl is-active --quiet kubelet' \
      && kubectl wait --for=condition=Ready "node/$node" --timeout=120s; then
    printf '%s: kubelet active and node Ready\n' "$node"
  else
    status=1
    ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
      'sudo -n journalctl -u kubelet --no-pager -n 50' || true
  fi
done
exit "$status"
```

Este script realiza lo siguiente:
1. Usa `kubectl get nodes` para obtener los nombres de todos los nodos del clúster.
2. Para cada nodo:
   - Comprueba el estado del servicio y, tras una reparación solicitada, verifica que el nodo esté Ready.
   - Se conecta al nodo por SSH para consultar el estado del servicio kubelet.
   - Informa si el servicio está inactivo; solo lo inicia cuando `REPAIR_KUBELET=1` y la consulta del servicio se completó correctamente.
   - Vuelve a comprobar el estado después de iniciar el servicio.
   - Consulta los logs si el inicio falla.
   - Distingue los errores de SSH/sudo/consulta de un servicio inactivo y comprueba que el nodo esté Ready después de repararlo.

**Uso:**
```bash
chmod +x check_kubelet.sh
./check_kubelet.sh
# After diagnosing the inactive service and approving repair:
REPAIR_KUBELET=1 ./check_kubelet.sh
```

**Notas:**
- Se necesita acceso SSH a todos los nodos para ejecutar este script.
- Se recomienda la autenticación mediante claves SSH en producción.
- En entornos de nube, el acceso SSH directo puede estar restringido; quizá debas usar las herramientas de administración de nodos del proveedor.
</details>

3. Configura un cron job que respalde la base de datos etcd del clúster y almacene el archivo en una ubicación segura.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**1. Crea el script de copia de seguridad:**

```bash
#!/usr/bin/env bash
# backup_etcd.sh: self-managed etcd; external storage must already be mounted.
set -euo pipefail
umask 077
BACKUP_DIR=${BACKUP_DIR:-/opt/etcd-backup}
REMOTE_ROOT=${REMOTE_ROOT:-/mnt/remote-storage}
REMOTE_DIR="$REMOTE_ROOT/etcd-backups"
METRICS_DIR=${METRICS_DIR:-/var/lib/node_exporter/textfile_collector}
RETENTION_DAYS=${RETENTION_DAYS:-7}
ETCD_ENDPOINT=${ETCD_ENDPOINT:-https://127.0.0.1:2379}
ETCD_CACERT=${ETCD_CACERT:-/etc/kubernetes/pki/etcd/ca.crt}
ETCD_CERT=${ETCD_CERT:-/etc/kubernetes/pki/etcd/healthcheck-client.crt}
ETCD_KEY=${ETCD_KEY:-/etc/kubernetes/pki/etcd/healthcheck-client.key}

publish_status() {
  rc=$?
  trap - EXIT
  if [ -d "$METRICS_DIR" ]; then
    tmp=$(mktemp "$METRICS_DIR/.etcd-backup.XXXXXX")
    success=0
    [ "$rc" -eq 0 ] && success=1
    printf 'etcd_backup_success %s\netcd_backup_last_attempt_timestamp_seconds %s\n' \
      "$success" "$(date +%s)" > "$tmp"
    chmod 0644 "$tmp"
    mv "$tmp" "$METRICS_DIR/etcd_backup_status.prom"
  fi
  exit "$rc"
}
trap publish_status EXIT
case "$RETENTION_DAYS" in ''|*[!0-9]*) echo 'Invalid retention' >&2; exit 1;; esac
mountpoint -q "$REMOTE_ROOT" || { echo 'Remote storage is not mounted' >&2; exit 1; }
mkdir -p "$BACKUP_DIR" "$REMOTE_DIR"
exec 9>"$BACKUP_DIR/.backup.lock"
flock -n 9 || { echo 'Another backup is running' >&2; exit 1; }
name="etcd-snapshot-$(date -u +%Y%m%d-%H%M%S).db"
ETCDCTL_API=3 etcdctl snapshot save "$BACKUP_DIR/$name" \
  --endpoints="$ETCD_ENDPOINT" --cacert="$ETCD_CACERT" \
  --cert="$ETCD_CERT" --key="$ETCD_KEY"
etcdutl snapshot status "$BACKUP_DIR/$name" --write-out=table
gzip "$BACKUP_DIR/$name"
cp "$BACKUP_DIR/$name.gz" "$REMOTE_DIR/.$name.gz.partial"
cmp "$BACKUP_DIR/$name.gz" "$REMOTE_DIR/.$name.gz.partial"
mv "$REMOTE_DIR/.$name.gz.partial" "$REMOTE_DIR/$name.gz"
# Retention runs only after snapshot validation and verified external copy.
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'etcd-snapshot-*.db.gz' \
  -mtime "+$RETENTION_DAYS" -delete
find "$REMOTE_DIR" -maxdepth 1 -type f -name 'etcd-snapshot-*.db.gz' \
  -mtime "+$RETENTION_DAYS" -delete
printf 'Verified backup copied to %s\n' "$REMOTE_DIR/$name.gz"
```

**2. Concede permiso de ejecución al script:**

```bash
chmod +x /opt/etcd-backup/backup_etcd.sh
```

**3. Configura el cron job:**

```bash
# Edit root user's crontab
sudo crontab -e
```

Añade lo siguiente:

```
# Run etcd backup daily at 2 AM
0 2 * * * /opt/etcd-backup/backup_etcd.sh >> /var/log/etcd-backup.log 2>&1
```

**4. Configura la rotación del log de copia de seguridad:**

Crea el archivo `/etc/logrotate.d/etcd-backup`:

```
/var/log/etcd-backup.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0600 root root
}
```

**5. Prueba la copia de seguridad:**

```bash
sudo /opt/etcd-backup/backup_etcd.sh
```

**6. Supervisa la copia de seguridad:**

Si existe `METRICS_DIR`, la trampa EXIT del script publica las métricas numéricas `etcd_backup_success` y `etcd_backup_last_attempt_timestamp_seconds`. Configura el textfile collector de node-exporter para leer ese directorio, concede permisos de escritura y genera alertas ante un fallo o un intento demasiado antiguo. No añadas una comprobación posterior de `$?` después de comandos `echo` o de copia. El montaje externo debe existir de antemano; si falla la validación o la copia, se detiene la retención.

**Notas:**
- Guarda las copias en una ubicación segura fuera del clúster.
- En la nube, se recomienda almacenamiento de objetos como S3 o GCS.
- Prueba periódicamente la restauración para comprobar la validez de las copias.
- En clústeres etcd de alta disponibilidad, basta con hacer la copia en una instancia etcd.
</details>

4. Escribe un procedimiento de mantenimiento acotado para nodos de trabajo Linux autogestionados que se seleccionen explícitamente, respete los presupuestos de interrupción y se detenga si fallan las comprobaciones de salud.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Procedimiento de actualización gradual de nodos:**

```bash
#!/usr/bin/env bash
# node_rolling_update.sh: explicitly selected self-managed Linux workers only.
set -euo pipefail
: "${MAINTENANCE_COMMAND:?Set a reviewed node-maintenance command that does not reboot itself}"
: "${WORKLOAD_HEALTHCHECK:?Set a command that verifies critical workload health}"
[ "$#" -gt 0 ] || { echo 'Pass the worker node names as arguments' >&2; exit 1; }
trap 'echo "Stopped on error; inspect the node before manually uncordoning it" >&2' ERR
for node in "$@"; do
  kubectl get node "$node" -o json | jq -e '
    (.metadata.labels["kubernetes.io/os"] == "linux") and
    (.metadata.labels | has("node-role.kubernetes.io/control-plane") | not) and
    (.metadata.labels | has("node-role.kubernetes.io/master") | not)' >/dev/null
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" 'sudo -n true'
done
kubectl get poddisruptionbudgets -A
bash -c "$WORKLOAD_HEALTHCHECK"
for node in "$@"; do
  kubectl wait --for=condition=Ready "node/$node" --timeout=120s
  boot_before=$(kubectl get node "$node" -o jsonpath='{.status.nodeInfo.bootID}')
  kubectl cordon "$node"
  kubectl drain "$node" --ignore-daemonsets --timeout=10m
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" "$MAINTENANCE_COMMAND"
  reboot_required=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
    'if [ -f /var/run/reboot-required ]; then echo yes; else echo no; fi')
  if [ "$reboot_required" = yes ]; then
    ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" 'sudo -n reboot' || true
    deadline=$((SECONDS + 600))
    while :; do
      boot_after=$(kubectl get node "$node" -o jsonpath='{.status.nodeInfo.bootID}')
      [ -n "$boot_after" ] && [ "$boot_after" != "$boot_before" ] && break
      [ "$SECONDS" -lt "$deadline" ] || { echo 'New boot ID not reported' >&2; exit 1; }
      sleep 5
    done
  fi
  # Require a fresh kubelet lease renewal, not a stale pre-maintenance Ready flag.
  lease_before=$(kubectl -n kube-node-lease get lease "$node" -o jsonpath='{.spec.renewTime}')
  deadline=$((SECONDS + 120))
  while :; do
    lease_after=$(kubectl -n kube-node-lease get lease "$node" -o jsonpath='{.spec.renewTime}')
    [ -n "$lease_after" ] && [ "$lease_after" != "$lease_before" ] && break
    [ "$SECONDS" -lt "$deadline" ] || { echo 'No fresh kubelet lease' >&2; exit 1; }
    sleep 5
  done
  kubectl wait --for=condition=Ready "node/$node" --timeout=5m
  bash -c "$WORKLOAD_HEALTHCHECK"
  kubectl uncordon "$node"
  bash -c "$WORKLOAD_HEALTHCHECK"
done
```

Este ejemplo requiere kubectl, jq, alias SSH para los nodos seleccionados, sudo autorizado sin contraseña y un comando de mantenimiento revisado. Comprueba el marcador de Debian/Ubuntu que indica que hace falta reiniciar; adáptalo al sistema operativo. Define `WORKLOAD_HEALTHCHECK` como un comando que compruebe realmente las aplicaciones críticas y pasa únicamente la lista de nodos de trabajo revisada. Por ejemplo:

```bash
MAINTENANCE_COMMAND='sudo -n /usr/local/sbin/approved-node-maintenance' \
WORKLOAD_HEALTHCHECK='kubectl -n app rollout status deployment/frontend --timeout=5m' \
./node_rolling_update.sh worker-1 worker-2
```

Los nombres del comando/script y de las aplicaciones deben existir y coincidir con tu plan. No usa force ni autoriza la pérdida de datos de emptyDir. Se detiene si falla el desalojo o el mantenimiento, espera a que cambie el boot ID después de un reinicio y a que se renueve el lease de kubelet, y deja los nodos con cordon si hay un fallo. Los PDB y estas comprobaciones reducen las interrupciones planificadas, pero no garantizan la disponibilidad ante fallos ajenos. Usa las actualizaciones administradas por el proveedor para nodos administrados o Auto Mode de EKS, y el procedimiento separado de kubeadm para los nodos del plano de control.

**Preparación antes de la actualización gradual:**

1. **Configura PodDisruptionBudget:**
   Configura PDB para garantizar la disponibilidad de las cargas críticas.

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

2. **Asegura que haya recursos suficientes:**
   Comprueba que los nodos restantes puedan ejecutar todas las cargas de trabajo al retirar un nodo.

3. **Haz una copia de seguridad:**
   Haz una copia de la base de datos etcd antes de las actualizaciones.

**Prácticas recomendadas para las actualizaciones graduales:**

1. **Avanza gradualmente:**
   - Actualiza un nodo a la vez.
   - Comprueba el estado del clúster después de cada nodo.

2. **Automatiza y haz el proceso idempotente:**
   - Automatiza el proceso con scripts.
   - Diseña reintentos seguros ante fallos.

3. **Mejora la supervisión:**
   - Supervisa las métricas del clúster durante las actualizaciones.
   - Supervisa el estado y el rendimiento de las aplicaciones.

4. **Prepara un plan de reversión:**
   - Documenta cómo revertir si hay problemas.
   - Prepara métodos para volver al estado anterior.

5. **Comunícate:**
   - Anuncia el calendario y el impacto previsto.
   - Informa periódicamente del progreso.

**Notas:**
- En la nube, puedes aprovechar las funciones de actualización de nodos de servicios Kubernetes administrados (EKS, GKE, AKS, etc.).
- Si hay varios grupos de nodos, actualízalos por grupo.
- Supervisa especialmente los Pods críticos del sistema (CoreDNS, kube-proxy, etc.).
</details>

5. Escribe un script que detecte Pods con un uso elevado de recursos en el clúster y genere un informe.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```python
#!/usr/bin/env python3
# resource_usage_report.py: read-only Kubernetes API/metrics reporting.
import datetime
from decimal import Decimal
import html
import json
import os
from pathlib import Path
import re
import subprocess

SCALE = {"": Decimal(1), "n": Decimal("1e-9"), "u": Decimal("1e-6"),
         "m": Decimal("1e-3"), "k": Decimal(1000), "K": Decimal(1000)}
SCALE.update({s: Decimal(1000) ** n for n, s in enumerate("MGTPE", 2)})
SCALE.update({s + "i": Decimal(1024) ** n for n, s in enumerate("KMGTPE", 1)})

def quantity(value):
    text = str(value)
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z]*)", text)
    if not match or match[2] not in SCALE:
        raise ValueError("Unsupported Kubernetes quantity: " + text)
    return Decimal(match[1]) * SCALE[match[2]]

def kubectl_json(*args):
    return json.loads(subprocess.check_output(["kubectl", *args], text=True))

def make_rows(pods, metrics):
    index = {(p["metadata"]["namespace"], p["metadata"]["name"]): p for p in pods}
    rows = []
    for metric in metrics:
        key = metric["metadata"]["namespace"], metric["metadata"]["name"]
        if key not in index:
            continue  # API snapshots are not atomic; the Pod may have disappeared.
        spec = index[key]["spec"]
        active = spec.get("containers", []) + [c for c in spec.get("initContainers", [])
                                               if c.get("restartPolicy") == "Always"]
        usage = {r: sum((quantity(c["usage"][r]) for c in metric["containers"]), Decimal(0))
                 for r in ("cpu", "memory")}
        requests = {}
        for resource in ("cpu", "memory"):
            pod_request = spec.get("resources", {}).get("requests", {}).get(resource)
            values = [c.get("resources", {}).get("requests", {}).get(resource) for c in active]
            requests[resource] = (quantity(pod_request) if pod_request is not None else
                                  sum((quantity(v) for v in values), Decimal(0))
                                  if all(v is not None for v in values) else None)
        rows.append((key, usage, requests))
    return rows

def render_report(rows):
    lines = ["Kubernetes resource usage report", "Generated: " + datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "Requests: active application/native-sidecar containers or Pod-level requests.",
             "This is not scheduler effective-request accounting for completed init stages/overhead."]
    totals = {}
    for key, usage, _ in rows:
        total = totals.setdefault(key[0], {"cpu": Decimal(0), "memory": Decimal(0)})
        for resource in total:
            total[resource] += usage[resource]
    for resource in ("cpu", "memory"):
        lines.append("\nTop 10 Pods by " + resource)
        for key, usage, requests in sorted(rows, key=lambda row: row[1][resource], reverse=True)[:10]:
            request = requests[resource]
            ratio = f"{usage[resource] / request * 100:.1f}%" if request else "request missing/zero"
            lines.append(f"{key[0]}/{key[1]}: usage={usage[resource]}, request={request}, ratio={ratio}")
    lines.append("\nNamespace totals (CPU cores, memory GiB)")
    for namespace, total in sorted(totals.items()):
        lines.append(f"{namespace}: {total['cpu']:.3f}, {total['memory'] / (1024 ** 3):.3f}")
    lines.append("\nPods above 80% of known requests or with missing requests")
    for key, usage, requests in rows:
        if any(not requests[r] or usage[r] / requests[r] >= Decimal('0.8') for r in requests):
            lines.append(f"{key[0]}/{key[1]}: usage={usage}; requests={requests}")
    return "\n".join(lines)

def main():
    os.umask(0o077)
    group = kubectl_json("get", "--raw", "/apis/metrics.k8s.io")
    version = group["preferredVersion"]["version"]
    pod_metrics = kubectl_json("get", "--raw", f"/apis/metrics.k8s.io/{version}/pods")["items"]
    pods = kubectl_json("get", "pods", "-A", "-o", "json")["items"]
    rows = make_rows(pods, pod_metrics)
    report = render_report(rows)
    nodes = subprocess.check_output(["kubectl", "top", "nodes"], text=True)
    report += "\n\nNode resource usage\n" + nodes
    node_count = len(kubectl_json("get", "nodes", "-o", "json")["items"])
    namespace_count = len(kubectl_json("get", "namespaces", "-o", "json")["items"])
    context = subprocess.check_output(["kubectl", "config", "current-context"], text=True).strip()
    report += f"\nContext: {context}; nodes: {node_count}; namespaces: {namespace_count}\n"
    report += f"Inventory Pods: {len(pods)}; Pods with matched metrics: {len(rows)}\n"
    directory = Path(os.environ.get("REPORT_DIR", "/tmp/k8s-reports"))
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    stem = "resource-usage-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    text_path = directory / (stem + ".txt")
    text_path.write_text(report, encoding="utf-8")
    (directory / (stem + ".html")).write_text(
        '<!doctype html><meta charset="utf-8"><title>Kubernetes resource report</title><pre>'
        + html.escape(report) + '</pre>', encoding="utf-8")
    print(text_path)

if __name__ == "__main__":
    main()
```

**Uso del script:**
```bash
python3 resource_usage_report.py
```

**Funciones del script:**
1. Recopila información del clúster.
2. Recopila el uso de recursos de los nodos.
3. Identifica los Pods con mayor uso de CPU y memoria.
4. Calcula el uso de recursos por namespace.
5. Detecta Pods con un uso elevado en relación con sus solicitudes.
6. Detecta Pods sin solicitudes de recursos.
7. Genera informes en texto y HTML.

**Notas:**
- Este script requiere Python 3 y kubectl con acceso de lectura a las API de Pods y métricas. Descubre la versión de métricas disponible, agrega el uso de varios contenedores por namespace, maneja las unidades de cantidades y escapa el HTML de salida.
- Metrics Server debe estar instalado en el clúster.
- En clústeres grandes, el script puede tardar más.
- Se puede ejecutar como cron job para generar informes periódicos.
- Los informes se pueden enviar por correo o integrar con sistemas de supervisión.
</details>

## Temas avanzados

1. ¿Qué dos conjuntos contienen parámetros reales de etcd o prácticas operativas válidas? (Selecciona dos.)
   - A) `--max-request-bytes`, `--quota-backend-bytes`, compactación periódica
   - B) `--max-concurrent-requests`, `--max-connections`, configuración RAID de disco
   - C) `--auto-compaction-retention`, `--snapshot-count`, almacenamiento SSD
   - D) `--max-txn-ops`, `--max-result-buffer`, ampliación de memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A y C**

**Explicación:**
etcd es el almacén de datos central de los clústeres Kubernetes y su rendimiento influye directamente en el rendimiento general. Entre los parámetros y prácticas importantes para optimizarlo se incluyen:

1. **`--auto-compaction-retention`:** etcd es un almacén de solo anexado que conserva el historial de cambios. Este parámetro establece el intervalo de compactación automática de versiones anteriores de claves. El valor predeterminado es 0 (desactivado); en producción suele configurarse en 1 hora (`1h`) o 24 horas (`24h`). Esto ayuda a ahorrar espacio y mejorar el rendimiento.

2. **`--snapshot-count`:** Indica cuántas transacciones se confirman antes de que etcd cree una instantánea. Controla las instantáneas internas de Raft, no las instantáneas portátiles de copia de seguridad. Los valores predeterminados dependen de la versión (la referencia de v3.6 indica 10 000); comprueba la versión instalada y mide antes de ajustar este parámetro.

3. **Almacenamiento SSD:** etcd es sensible al rendimiento de disco; las unidades SSD mejoran considerablemente la E/S. Son esenciales en clústeres grandes.

Otras configuraciones y prácticas útiles:

- **Usa discos dedicados:** evita la contención de E/S con otras aplicaciones.
- **Asigna memoria suficiente:** etcd almacena datos en caché para mejorar el rendimiento.
- **Dimensiona correctamente el clúster:** normalmente, entre 3 y 5 miembros de etcd ofrecen un buen equilibrio entre rendimiento y disponibilidad.
- **Reduce la latencia de red:** equilibra la latencia entre miembros con el aislamiento ante fallos; si todos están en una sola zona, perder esa zona elimina el cuórum.
- **Haz copias de seguridad y compacta periódicamente:** protege los datos y administra el espacio de disco.

`--max-request-bytes`, `--quota-backend-bytes` y `--max-txn-ops` son parámetros reales. La opción D también incluye `--max-result-buffer`, que no es compatible; no confundas los límites de configuración, la retención ni las instantáneas internas con una estrategia de copia de seguridad.
</details>

2. ¿Cuál es la forma más eficaz de implementar alta disponibilidad (HA) para el plano de control de un clúster Kubernetes?
   - A) Ejecutar varias instancias del API server en un único nodo principal
   - B) Configurar un clúster etcd en varios nodos principales y usar un balanceador de carga
   - C) Desplegar el API server como StatefulSet con un PersistentVolume
   - D) Implementar un proceso watchdog con recuperación automática en el nodo principal

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar un clúster etcd en varios nodos principales y usar un balanceador de carga**

**Explicación:**
La forma más eficaz de implementar alta disponibilidad para el plano de control de Kubernetes es configurar un clúster etcd con varios nodos principales y un balanceador de carga. Esta configuración incluye:

1. **Varios nodos principales:** normalmente se despliegan 3 o 5 nodos principales en distintas zonas de disponibilidad para evitar puntos únicos de fallo. Cada nodo ejecuta estos componentes del plano de control:
   - kube-apiserver, que atiende las solicitudes de la API.
   - kube-controller-manager, que ejecuta los controladores.
   - kube-scheduler, que decide dónde programar los Pods.

2. **Clúster etcd:** etcd es un almacén distribuido de clave-valor que contiene los datos del clúster Kubernetes. Para lograr alta disponibilidad suelen ejecutarse 3 o 5 instancias etcd, en los nodos principales o en nodos dedicados.

3. **Balanceador de carga:** distribuye las solicitudes de los clientes entre varias instancias de kube-apiserver. Puede ser un servicio del proveedor de nube o un balanceador de software como HAProxy o Nginx.

Ventajas principales:
- **Tolerancia a fallos:** el clúster sigue funcionando si falla un nodo principal.
- **Alta disponibilidad:** el despliegue en varias zonas de disponibilidad puede tolerar fallos de un centro de datos.
- **Escalabilidad:** las solicitudes de la API se distribuyen entre varias instancias.
- **Coherencia de datos:** el consenso Raft de etcd mantiene la coherencia de los datos.

Problemas de las demás opciones:
- Varias instancias de API server en un solo nodo principal siguen dejando ese nodo como punto único de fallo.
- El API server no suele desplegarse como StatefulSet; los componentes del plano de control suelen administrarse fuera de Kubernetes.
- Un proceso watchdog puede ser útil, pero no constituye por sí solo una solución de alta disponibilidad.
</details>

3. ¿Qué mecanismo selecciona los eventos y el nivel de detalle que registra el sistema de auditoría de Kubernetes?
   - A) Registrar sin filtros todos los cuerpos de solicitud y respuesta
   - B) Usar una política de auditoría para seleccionar eventos y niveles
   - C) Transmitir en tiempo real los logs de auditoría a un SIEM externo
   - D) Limitar el acceso a los logs de auditoría a los administradores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar una política de auditoría para seleccionar eventos y niveles**

**Explicación:**
Las políticas de auditoría seleccionan los eventos y su nivel de detalle. Una regla general de nivel Metadata puede conservar una cobertura amplia sin incluir cargas útiles sensibles; también importan la retención, el control de acceso y la entrega de los logs. Esto es importante por varios motivos:

1. **Reduce el impacto en el rendimiento:** registrar todas las solicitudes de API puede cargar significativamente el API server y degradar su rendimiento. Elige los niveles según la cobertura de auditoría necesaria y el impacto medido; registrar los metadatos de todas las solicitudes es una opción de referencia admitida.

2. **Ahorra almacenamiento:** registrar todos los eventos hace crecer rápidamente los logs, aumenta los costos y dificulta el análisis.

3. **Se centra en la información relevante:** al registrar los eventos importantes, los analistas de seguridad pueden centrarse en la información crítica.

4. **Cumplimiento:** adapta la cobertura de eventos, la retención y los controles de acceso a los requisitos aplicables al sistema.

Las políticas de auditoría de Kubernetes admiten estos niveles:

- **None:** no registra el evento.
- **Metadata:** registra solo los metadatos de la solicitud (usuario, marca de tiempo, recurso, acción, etc.) y excluye el cuerpo de la solicitud y de la respuesta.
- **Request:** registra los metadatos y el cuerpo de la solicitud, pero excluye el cuerpo de la respuesta.
- **RequestResponse:** registra los metadatos y los cuerpos de la solicitud y la respuesta.

Ejemplo de política de auditoría:
```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: Metadata
  resources:
  - group: ""
    resources: ["secrets", "configmaps", "serviceaccounts/token"]
  - group: authentication.k8s.io
    resources: ["tokenreviews"]
- level: Metadata
```

Problemas de las demás opciones:
- Registrar todas las solicitudes de API puede causar problemas de rendimiento y almacenamiento.
- La transmisión en tiempo real a un SIEM externo es importante, pero primero hay que decidir qué registrar.
- Restringir el acceso a los logs de auditoría es importante, pero es una medida de seguridad y no la política que selecciona el registro.
</details>

4. ¿Qué patrón combina un detector dedicado de problemas de nodos con una lógica de reparación personalizada en un entorno autogestionado?
   - A) Desplegar un DaemonSet que supervise los nodos y reinicie automáticamente los problemáticos
   - B) Usar grupos de nodos administrados y funciones de reparación automática del proveedor de nube
   - C) Usar Node Problem Detector y controladores personalizados para supervisar y recuperar el estado de los nodos
   - D) Ejecutar un cron job que compruebe periódicamente los nodos y vuelva a crear los problemáticos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar Node Problem Detector y controladores personalizados para supervisar y recuperar el estado de los nodos**

**Explicación:**
Node Problem Detector junto con una reparación personalizada es un diseño extensible, aunque no siempre es la mejor opción: la reparación administrada por el proveedor, incluida la reparación de nodos de EKS, puede reducir el trabajo operativo. Este patrón ofrece las ventajas siguientes:

1. **Detección precisa de problemas:** Node Problem Detector (NPD) detecta varios problemas de nodos, por ejemplo:
   - Errores y fallos del kernel.
   - Problemas de hardware.
   - Problemas del sistema de archivos.
   - Problemas de red.
   - Falta de recursos.

2. **Respuesta flexible:** los controladores personalizados pueden aplicar distintas estrategias según el problema detectado:
   - Problemas menores: reiniciar el nodo.
   - Problemas graves: sustituir el nodo.
   - Problemas concretos: reiniciar un servicio específico.

3. **Integración con Kubernetes:** NPD informa el estado mediante NodeConditions y se integra con los mecanismos existentes de Kubernetes.

4. **Independencia de la nube:** la detección y reparación deben adaptarse al sistema operativo, el runtime y el proveedor; la pérdida de un nodo también requiere una señal/controlador externo si el agente del propio nodo no puede informar.

Pasos de implementación:

1. **Despliega Node Problem Detector:**
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/node-problem-detector/master/deployment/node-problem-detector.yaml
   ```

2. **Implementa un controlador personalizado:**
   - Observa eventos de Kubernetes y cambios de estado de los nodos.
   - Define la lógica para responder a NodeConditions específicas.
   - Ejecuta acciones de recuperación (comandos por SSH, recreación del nodo mediante la API de la nube, etc.).

3. **Configura alertas y logs:**
   - Configura alertas para las acciones de recuperación.
   - Registra los problemas y las acciones de recuperación.

Problemas de las demás opciones:

- **DaemonSet:** si el nodo tiene un problema grave, el propio DaemonSet puede verse afectado; además, es difícil detectar todos los tipos de problemas.
- **Grupos de nodos administrados por el proveedor:** dependen de proveedores concretos y no se pueden usar en instalaciones locales; los tipos de problemas detectables también pueden ser limitados.
- **Cron job:** reacciona lentamente, detecta una gama limitada de problemas y debe ejecutarse fuera del clúster.

Node Problem Detector con controladores personalizados permite una reparación potente y flexible en distintos entornos.
</details>

5. ¿Cuáles son las prácticas recomendadas para administrar RBAC (Role-Based Access Control) de forma eficaz en un clúster Kubernetes?
   - A) Conceder el rol cluster-admin a todos los usuarios para simplificar la administración
   - B) Definir roles granulares por namespace y aplicar el principio de privilegio mínimo
   - C) Consolidar todos los permisos en un único ClusterRole para mantener la coherencia
   - D) Usar siempre certificados de usuario en vez de service accounts para la autenticación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Definir roles granulares por namespace y aplicar el principio de privilegio mínimo**

**Explicación:**
La práctica recomendada para administrar RBAC eficazmente es definir roles granulares por namespace y aplicar el principio de privilegio mínimo. Este enfoque ofrece varias ventajas:

1. **Principio de privilegio mínimo:** concede a los usuarios y service accounts solo los permisos mínimos necesarios para reducir riesgos de seguridad y cambios involuntarios o maliciosos.

2. **Aislamiento por namespace:** los roles por namespace refuerzan el aislamiento lógico entre equipos o aplicaciones. Esto limita las acciones habituales de la API; también hacen falta controles de admisión de cargas de trabajo y de red.

3. **Control de acceso granular:** permite limitar permisos por tipo de recurso y acción. Por ejemplo, se puede permitir que los desarrolladores administren Pods y Services, pero restringirles la modificación de Secrets o del propio namespace.

4. **Facilidad de auditoría:** los roles granulares documentan con claridad quién puede hacer qué y facilitan las auditorías y el cumplimiento.

Ejemplos de prácticas recomendadas para RBAC:

1. **Define roles por namespace:**
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
   ```

La creación de Pods o Deployments puede exponer indirectamente Secrets y privilegios de ServiceAccount del namespace. Quitar el acceso de lectura directo a Secrets es útil, pero no basta para limitar las credenciales que pueden montar las cargas; usa controles de admisión apropiados.

2. **Crea un role binding:**
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

3. **Usa con moderación los roles de clúster:**
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

4. **Concede permisos granulares a service accounts:**
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

Problemas de las demás opciones:

- **Conceder cluster-admin a todos los usuarios:** crea riesgos de seguridad graves, porque todos tendrían acceso completo a los recursos del clúster.
- **Consolidar todos los permisos en un ClusterRole:** un rol compartido con demasiados permisos puede conceder acceso excesivo; sí puede ser apropiado reutilizar un ClusterRole de alcance limitado mediante RoleBindings con ámbito de namespace.
- **Usar siempre certificados de usuario:** las service accounts son adecuadas para la autenticación de aplicaciones, mientras que usar certificados de usuario en todos los casos aumenta la carga administrativa. El mecanismo debe elegirse según la situación.
</details>
