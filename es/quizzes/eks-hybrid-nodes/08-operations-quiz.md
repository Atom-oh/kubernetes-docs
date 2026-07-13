# Cuestionario de operaciones de EKS Hybrid Nodes

> **Documento relacionado**: [Operaciones](../../eks-hybrid-nodes/08-operations.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es la combinación de herramientas recomendada para la monitorización de Node en entornos Hybrid Nodes?

A. Bloc de notas y registro manual
B. Prometheus + Grafana + Node Exporter
C. Solo notificaciones por correo electrónico
D. Revisión manual de archivos de log

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Prometheus + Grafana + Node Exporter**

**Explicación:**
El stack estándar de monitorización en entornos Kubernetes es la combinación de Prometheus, Grafana y Node Exporter.

```yaml
# Node Exporter DaemonSet
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    spec:
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.6.1
        ports:
        - containerPort: 9100
```

**Componentes del stack de monitorización:**
- **Prometheus**: Recopilación y almacenamiento de métricas
- **Grafana**: Dashboards de visualización
- **Node Exporter**: Métricas del sistema de Node
- **DCGM Exporter**: Métricas de GPU (para Nodes con GPU)
- **Alertmanager**: Gestión de alertas

```bash
# Install Prometheus stack (Helm)
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

</details>

### 2. ¿Cómo verificas cuándo es necesario renovar el certificado de kubelet?

A. Los certificados son permanentes, no se necesita verificación
B. Verificar la fecha de expiración del certificado con el comando openssl
C. Esperar hasta que el Node pase a NotReady
D. Renovar manualmente todos los días

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Verificar la fecha de expiración del certificado con el comando openssl**

**Explicación:**
Los certificados de kubelet expiran después de cierto período y deben revisarse y renovarse periódicamente.

```bash
# Check kubelet certificate expiration
sudo openssl x509 -in /var/lib/kubelet/pki/kubelet-client-current.pem \
  -text -noout | grep -A 2 "Validity"

# Or use kubeadm
kubeadm certs check-expiration

# Renew certificates (kubeadm cluster)
kubeadm certs renew all
```

**Configuración de renovación automática (EKS):**
```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      rotateCertificates: true  # Auto certificate renewal
      serverTLSBootstrap: true
```

**Alerta de monitorización:**
```yaml
- alert: KubeletCertExpiringSoon
  expr: |
    kubelet_certificate_manager_client_expiration_seconds < 604800
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "kubelet certificate expiring within 7 days"
```

</details>

### 3. ¿Cuál es el primer paso de solución de problemas cuando kubelet no responde en un Hybrid Node?

A. Reiniciar todo el cluster
B. Verificar el estado y los logs del servicio kubelet
C. Crear un Node nuevo
D. Eliminar todos los Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Verificar el estado y los logs del servicio kubelet**

**Explicación:**
Procedimiento sistemático de solución de problemas para incidencias de kubelet:

```bash
# 1. Check kubelet service status
sudo systemctl status kubelet

# 2. Check kubelet logs
sudo journalctl -u kubelet -f --no-pager | tail -100

# 3. Check for common error patterns
sudo journalctl -u kubelet | grep -E "error|failed|unable"

# 4. Check resource status (memory, disk)
free -h
df -h

# 5. Test network connectivity
curl -vk https://<eks-api-endpoint>:443

# 6. Check containerd status
sudo systemctl status containerd

# 7. Restart kubelet (if needed)
sudo systemctl restart kubelet
```

**Causas comunes de fallo de kubelet:**
- Memoria agotada (OOM)
- Espacio en disco insuficiente
- Expiración de certificados
- Desconexión de red
- Fallo de containerd

</details>

### 4. ¿Qué comando se usa para mover workloads de forma segura durante el mantenimiento de un Node?

A. kubectl delete node
B. kubectl drain
C. solo kubectl cordon
D. kubectl delete pods --all

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. kubectl drain**

**Explicación:**
`kubectl drain` hace que el Node no sea programable y expulsa de forma segura los Pods existentes.

```bash
# 1. Drain node (move workloads)
kubectl drain hybrid-node-1 \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --grace-period=300

# 2. Perform maintenance
# (OS patches, driver updates, etc.)

# 3. Make node schedulable again
kubectl uncordon hybrid-node-1
```

**Comparación entre drain y cordon:**

| Command | Action |
|---------|--------|
| `kubectl cordon` | Only prevent new Pod scheduling |
| `kubectl drain` | cordon + evict existing Pods |
| `kubectl uncordon` | Allow scheduling again |

```yaml
# PodDisruptionBudget for safe draining
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: myapp-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: myapp
```

</details>

### 5. ¿Cuál es la solución recomendada para centralizar logs de Hybrid Nodes?

A. Copiar manualmente los archivos de log desde cada Node
B. Recopilación y reenvío de logs usando Fluent Bit/Fluentd
C. Sin recopilación de logs
D. Solo salida de consola

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Recopilación y reenvío de logs usando Fluent Bit/Fluentd**

**Explicación:**
Fluent Bit o Fluentd recopila los logs de containers y los reenvía al almacenamiento central de logs.

```yaml
# Fluent Bit DaemonSet
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
spec:
  template:
    spec:
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit:2.1
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
```

**Arquitectura de logging:**
```
[Hybrid Nodes]          [Central Log System]
+-- Node 1              +------------------+
|   +-- Fluent Bit ---> | Elasticsearch    |
+-- Node 2              | or               |
|   +-- Fluent Bit ---> | CloudWatch Logs  |
+-- Node 3              | or               |
    +-- Fluent Bit ---> | Loki             |
                        +------------------+
```

</details>

### 6. ¿Cuál es el tiempo de espera predeterminado antes de reprogramar automáticamente Pods en otros Nodes cuando falla un Node?

A. Inmediatamente (0 segundos)
B. 30 segundos
C. 5 minutos (300 segundos)
D. 1 hora

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. 5 minutos (300 segundos)**

**Explicación:**
El `pod-eviction-timeout` predeterminado en Kubernetes es de 5 minutos. Los Pods se expulsan 5 minutos después de que un Node pasa a NotReady.

```yaml
# Node Lifecycle Controller settings (kube-controller-manager)
# --pod-eviction-timeout=5m0s  (default)
# --node-monitor-grace-period=40s  (NotReady detection)
```

**Configuración para un failover más rápido:**
```yaml
# Add tolerations to Pod
apiVersion: v1
kind: Pod
spec:
  tolerations:
  - key: "node.kubernetes.io/not-ready"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 60  # Evict after 60 seconds (default 300)
  - key: "node.kubernetes.io/unreachable"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 60
```

**Transiciones de estado de Node:**
```
Ready --(40s)--> NotReady --(5min)--> Pod Eviction
         |                    |
    node-monitor-        pod-eviction-
    grace-period         timeout
```

</details>

### 7. ¿Cuál es la estrategia recomendada para upgrades de EKS Hybrid Nodes?

A. Actualizar todos los Nodes simultáneamente
B. Rolling upgrade (uno a la vez)
C. Eliminar y recrear el cluster
D. Sin upgrades

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Rolling upgrade (uno a la vez)**

**Explicación:**
Los rolling upgrades actualizan los Nodes secuencialmente sin interrupción del servicio.

```bash
# Rolling upgrade procedure

# 1. Drain first node
kubectl drain hybrid-node-1 --ignore-daemonsets --delete-emptydir-data

# 2. Upgrade nodeadm
sudo nodeadm upgrade --config-source file://nodeadm-config.yaml

# 3. Check node status
kubectl get node hybrid-node-1

# 4. Uncordon node
kubectl uncordon hybrid-node-1

# 5. Wait for workload stabilization
sleep 60

# 6. Repeat for next node
kubectl drain hybrid-node-2 ...
```

**Checklist de upgrade:**
- [ ] Verificar la configuración de PodDisruptionBudget
- [ ] Upgrades secuenciales de Nodes
- [ ] Verificar el estado después de cada paso
- [ ] Preparar plan de rollback
- [ ] Realizar backups

</details>
