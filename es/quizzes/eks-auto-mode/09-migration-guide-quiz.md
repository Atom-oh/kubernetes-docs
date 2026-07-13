# Cuestionario de la guía de migración de EKS Auto Mode

> **Documento relacionado**: [Guía de migración](../../eks-auto-mode/09-migration-guide.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es el primer paso al migrar de managed node groups a Auto Mode?

- A) Eliminar inmediatamente los node groups existentes
- B) Analizar el estado actual (comprobar el uso de recursos de los nodes, distribución de workloads)
- C) Crear Auto Mode NodePool
- D) Drenar todos los Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Analizar el estado actual (comprobar el uso de recursos de los nodes, distribución de workloads)**

**Explicación:**
El primer paso de la migración es analizar a fondo tu entorno actual.

**Pasos de migración:**
1. **Analizar el estado actual** - Comprobar node groups, uso de recursos, distribución de workloads
2. Habilitar Auto Mode
3. Configurar NodePool
4. Migrar workloads
5. Reducir la escala de los node groups existentes
6. Eliminar los node groups existentes
7. Validar y optimizar

```bash
# Check current node groups
eksctl get nodegroup --cluster my-cluster

# Analyze node resource usage
kubectl top nodes

# Check workload distribution
kubectl get pods -A -o wide | awk '{print $8}' | sort | uniq -c
```

</details>

### 2. ¿Cómo permites la coexistencia de los node groups existentes y Auto Mode durante la migración?

- A) No es posible; debe ser solo secuencial
- B) Separar workloads usando nodeSelector
- C) Requiere un cluster separado
- D) Requiere un ticket de AWS Support

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Separar workloads usando nodeSelector**

**Explicación:**
Durante el periodo de coexistencia, usa nodeSelector y affinity para separar workloads.

```yaml
# Workloads pinned to existing node groups
apiVersion: apps/v1
kind: Deployment
metadata:
  name: legacy-critical-app
spec:
  template:
    spec:
      nodeSelector:
        eks.amazonaws.com/nodegroup: old-nodegroup

---
# Workloads that can be migrated to Auto Mode
apiVersion: apps/v1
kind: Deployment
metadata:
  name: migrated-app
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: karpenter.sh/nodepool
                    operator: Exists
```

</details>

### 3. ¿Cuál es el orden recomendado para la migración gradual de workloads?

- A) Producción -> Staging -> Desarrollo
- B) Desarrollo -> Staging -> Producción (workloads no críticos primero)
- C) Todos los workloads simultáneamente
- D) Orden aleatorio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Desarrollo -> Staging -> Producción (workloads no críticos primero)**

**Explicación:**
La migración gradual minimiza el riesgo.

```yaml
# Step 1: Migrate non-critical workloads
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dev-app
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: node-type
                    operator: In
                    values: ["auto-mode"]
```

**Orden de migración:**
1. Workloads del entorno de desarrollo
2. Workloads de Staging
3. Workloads no críticos de producción
4. Workloads críticos de producción

</details>

### 4. ¿Cuál es la secuencia de pasos cuando se necesita rollback?

- A) Eliminar y recrear el cluster
- B) Eliminar NodePool -> Aumentar la escala de los node groups existentes -> Migrar workloads
- C) Contactar con AWS Support
- D) Solo deshabilitar Auto Mode

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Eliminar NodePool -> Aumentar la escala de los node groups existentes -> Migrar workloads**

**Explicación:**
El rollback procede en orden inverso.

```bash
#!/bin/bash
# rollback.sh

# 1. Disable Auto Mode NodePool
kubectl delete nodepool migration-pool

# 2. Scale up existing node groups
eksctl scale nodegroup \
    --cluster my-cluster \
    --name old-nodegroup \
    --nodes 10 \
    --nodes-min 3

# 3. Migrate workloads back to existing nodes
kubectl patch deployment migrated-app -p '
{
  "spec": {
    "template": {
      "spec": {
        "nodeSelector": {
          "eks.amazonaws.com/nodegroup": "old-nodegroup"
        },
        "affinity": null
      }
    }
  }
}'

# 4. Drain Auto Mode Pods
for node in $(kubectl get nodes -l karpenter.sh/nodepool=migration-pool -o name); do
    kubectl drain $node --ignore-daemonsets --delete-emptydir-data
done
```

</details>

### 5. ¿Cuál es el método recomendado para reducir gradualmente la escala de los node groups existentes?

- A) Reducir la escala a 0 inmediatamente
- B) Reducir la escala en un 50% de forma incremental con comprobación de estabilización
- C) Reducir la escala solo en 1
- D) Drenar todos los nodes simultáneamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Reducir la escala en un 50% de forma incremental con comprobación de estabilización**

**Explicación:**
La reducción gradual de escala minimiza el impacto en el servicio.

```bash
#!/bin/bash
CLUSTER="my-cluster"
NODEGROUP="old-nodegroup"
CURRENT_SIZE=$(eksctl get nodegroup --cluster $CLUSTER --name $NODEGROUP -o json | jq -r '.[0].DesiredCapacity')

# Scale down by 50%
while [ $CURRENT_SIZE -gt 0 ]; do
    NEW_SIZE=$((CURRENT_SIZE / 2))
    if [ $NEW_SIZE -lt 1 ]; then
        NEW_SIZE=0
    fi

    echo "Scaling from $CURRENT_SIZE to $NEW_SIZE"
    eksctl scale nodegroup --cluster $CLUSTER --name $NODEGROUP \
        --nodes $NEW_SIZE --nodes-min 0

    # Wait for stabilization
    sleep 300

    # Check workload status
    kubectl get pods -A --field-selector=status.phase=Pending

    CURRENT_SIZE=$NEW_SIZE
done
```

</details>

### 6. ¿Cuál NO es una métrica clave para monitorizar durante la migración?

- A) Recuento de Pods en Pending
- B) Tiempo de aprovisionamiento de nodes
- C) Costo de instancias EC2
- D) Disponibilidad de workloads

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Costo de instancias EC2**

**Explicación:**
Durante la migración, la estabilidad del servicio es la máxima prioridad, por lo que debes monitorizar las siguientes métricas.

| Métrica | Rango normal | Condición de alarma |
|--------|--------------|-----------------|
| Recuento de Pods en Pending | 0-5 | > 10 durante 5 min |
| Tiempo de aprovisionamiento de nodes | < 90 sec | > 120 sec |
| Disponibilidad de workloads | > 99.9% | < 99.5% |
| Tiempo de respuesta de API | < 200ms | > 500ms |

El costo se revisa durante la fase de optimización después de completar la migración.

```bash
# Real-time monitoring
watch -n 5 'echo "=== Pending Pods ===" && \
kubectl get pods -A --field-selector=status.phase=Pending && \
echo "=== Node Status ===" && kubectl get nodes -o wide'
```

</details>

### 7. ¿Cuál NO es un elemento que se deba verificar después de completar la migración?

- A) Verificar que todos los workloads se ejecuten normalmente
- B) Verificar la distribución de Pods en nodes de Auto Mode
- C) Eliminación completa de los node groups existentes
- D) Verificar el estado de NodePool

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Eliminación completa de los node groups existentes**

**Explicación:**
En el punto de verificación, conserva los node groups existentes para mantener las opciones de rollback. La eliminación procede después de confirmar la estabilidad.

**Checklist de verificación:**
1. Verificar que todos los Pods estén en estado Running
2. Verificar la distribución de workloads en nodes de Auto Mode
3. Estado normal de NodePool y NodeClaim
4. Pruebas de rendimiento de la aplicación
5. Recopilación normal de logs y métricas
6. **Eliminar los node groups existentes después de confirmar la estabilidad durante un periodo (1-2 semanas)**

</details>

### 8. ¿Cuál es la precaución al pasar de un cluster que usa Karpenter directamente a Auto Mode?

- A) Es posible la transición directa
- B) Posible conflicto con recursos de Karpenter existentes; transición después de eliminar Karpenter
- C) Se recomienda la operación simultánea
- D) Se incurre en costo adicional

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Posible conflicto con recursos de Karpenter existentes; transición después de eliminar Karpenter**

**Explicación:**
Auto Mode usa Karpenter internamente, por lo que puede entrar en conflicto con Karpenter autoadministrado existente.

**Procedimiento de transición:**
1. Hacer backup de la configuración de NodePool de Karpenter existente
2. Migrar temporalmente los workloads gestionados por Karpenter a managed node groups
3. Eliminar Karpenter autoadministrado
4. Habilitar Auto Mode
5. Configurar Auto Mode NodePool (referencia del backup)
6. Migrar workloads

```bash
# Verify before removing Karpenter
kubectl get nodepools
kubectl get nodeclaims
kubectl get nodes -l karpenter.sh/nodepool

# Remove Karpenter
helm uninstall karpenter -n karpenter
kubectl delete namespace karpenter
```

</details>
