# Cuestionario de operaciones de EKS Auto Mode

> **Documento relacionado**: [Operaciones](../../eks-auto-mode/05-operations.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es la configuración de NodePool Disruption Budget para minimizar las interrupciones de nodos durante el horario laboral?

- A) `nodes: "100%"`
- B) `nodes: "0"` con programación
- C) `consolidateAfter: 0s`
- D) `consolidationPolicy: Never`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `nodes: "0"` con programación**

**Explicación:**
Configurar `nodes: "0"` junto con una programación evita por completo las interrupciones de nodos durante ventanas de tiempo específicas.

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
    # Default: Only 10% of total nodes can be disrupted simultaneously
    - nodes: "10%"

    # Business hours: No disruptions
    - nodes: "0"
      schedule: "0 9-18 * * mon-fri"  # Mon-Fri 9-18
      duration: 9h
```

</details>

### 2. ¿Qué significa `minAvailable: 80%` en un PodDisruptionBudget (PDB)?

- A) Puede ejecutarse como máximo el 80% de los Pods
- B) Siempre debe estar ejecutándose como mínimo el 80% de los Pods
- C) 80% de probabilidad de retención de Pods
- D) Proteger Pods durante 80 segundos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Siempre debe estar ejecutándose como mínimo el 80% de los Pods**

**Explicación:**
`minAvailable` de PDB especifica el número o porcentaje mínimo de Pods que siempre deben estar ejecutándose.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 80%
  selector:
    matchLabels:
      app: web
```

Como alternativa, puedes usar `maxUnavailable`:
```yaml
spec:
  maxUnavailable: 1  # Only 1 Pod can be disrupted simultaneously
```

</details>

### 3. ¿Cuál es el primer recurso que se debe comprobar al diagnosticar problemas de nodos de Auto Mode?

- A) Logs de Pod
- B) Estado de NodeClaim
- C) Consola de EC2
- D) Métricas de CloudWatch

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Estado de NodeClaim**

**Explicación:**
NodeClaim es el recurso clave que rastrea el proceso y el estado de aprovisionamiento de nodos.

```bash
# Check NodeClaim status
kubectl get nodeclaims

# Check details and events
kubectl describe nodeclaim <name>

# Check provisioning failure causes
kubectl get nodeclaims -o yaml | grep -A 10 status
```

Orden típico de solución de problemas:
1. Comprobar el estado de NodeClaim
2. Revisar la configuración de NodePool
3. Verificar los roles/policies de IAM
4. Validar subnets/security groups

</details>

### 4. ¿Cuál es el uso correcto de la anotación do-not-disrupt?

- A) `kubernetes.io/do-not-disrupt: "true"`
- B) `karpenter.sh/do-not-disrupt: "true"`
- C) `eks.amazonaws.com/no-disrupt: "true"`
- D) `node.kubernetes.io/exclude-disruption: "true"`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `karpenter.sh/do-not-disrupt: "true"`**

**Explicación:**
Agregar esta anotación a un Pod o Node lo excluye de la consolidación o del reemplazo por drift de Karpenter.

```yaml
# Apply to Pod
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
  annotations:
    karpenter.sh/do-not-disrupt: "true"
spec:
  containers:
    - name: app
      image: myapp:latest

# Apply to Node
kubectl annotate node <node-name> karpenter.sh/do-not-disrupt=true
```

</details>

### 5. ¿Cuál es la herramienta recomendada para monitorear el estado de nodos en un cluster de Auto Mode?

- A) Solo kubectl top nodes
- B) Combinación de Container Insights + kubectl
- C) Comprobar directamente en la consola de EC2
- D) Solo AWS CLI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Combinación de Container Insights + kubectl**

**Explicación:**
Usa una combinación de herramientas para un monitoreo eficaz.

```bash
# Real-time monitoring
watch -n 5 'echo "=== Pending Pods ===" && \
kubectl get pods -A --field-selector=status.phase=Pending && \
echo "=== Node Status ===" && kubectl get nodes -o wide'

# Check resource usage
kubectl top nodes
kubectl top pods -A

# Check NodePool status
kubectl get nodepools
kubectl describe nodepool <name>
```

Métricas de Container Insights:
- Utilización de CPU/memoria de Node
- Latencia de scheduling de Pod
- Conteo de reinicios de Container

</details>

### 6. ¿Qué campo de NodePool se debe configurar para automatizar las actualizaciones de nodos en operaciones Day-2?

- A) `autoUpdate: true`
- B) Configuración `expireAfter`
- C) `updatePolicy: Rolling`
- D) `refreshInterval: 24h`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configuración `expireAfter`**

**Explicación:**
Configurar `expireAfter` garantiza que los nodos se reemplacen automáticamente después del tiempo especificado, aplicando la AMI más reciente y los parches de seguridad.

```yaml
spec:
  template:
    spec:
      expireAfter: 168h  # Auto-replace after 7 days
```

Configuraciones de automatización de operaciones Day-2:
- `expireAfter`: Reemplazo regular de nodos
- `consolidationPolicy`: Optimización de costos
- Disruption Budget: Minimizar el impacto en el servicio

</details>

### 7. ¿Cuál es la configuración recomendada de Disruption Budget para rolling updates en entornos de producción?

- A) `nodes: "100%"` para actualizaciones rápidas
- B) `nodes: "10%"` o valor absoluto para actualizaciones graduales
- C) Deshabilitar Disruption Budget
- D) `nodes: "50%"` para velocidad media

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `nodes: "10%"` o valor absoluto para actualizaciones graduales**

**Explicación:**
En entornos de producción, actualiza gradualmente mientras minimizas el impacto en el servicio.

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
    # Default: Gradual replacement at 10%
    - nodes: "10%"

    # Peak hours: More conservative
    - nodes: "1"
      schedule: "0 9-18 * * mon-fri"
      duration: 9h

    # Maintenance window: More aggressive
    - nodes: "30%"
      schedule: "0 2-4 * * sun"
      duration: 2h
```

</details>

### 8. ¿Cuáles son las métricas clave para las alarmas de CloudWatch relacionadas con nodos de Auto Mode?

- A) Solo estado de instancia EC2
- B) Conteo de Pending Pod, tiempo de aprovisionamiento de nodos, disponibilidad de workloads
- C) Solo métricas de costos
- D) Solo tráfico de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Conteo de Pending Pod, tiempo de aprovisionamiento de nodos, disponibilidad de workloads**

**Explicación:**
Métricas clave que se deben monitorear en operaciones de Auto Mode:

| Metric | Normal Range | Alarm Condition |
|--------|--------------|-----------------|
| Pending Pod count | 0-5 | > 10 for 5 min |
| Node provisioning time | < 90 sec | > 120 sec |
| Workload availability | > 99.9% | < 99.5% |
| API response time | < 200ms | > 500ms |

Habilita CloudWatch Container Insights para recopilar automáticamente estas métricas.

</details>
