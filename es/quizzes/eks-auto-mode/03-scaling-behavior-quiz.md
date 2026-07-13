# Cuestionario sobre el comportamiento de escalado de EKS Auto Mode

> **Documento relacionado**: [Comportamiento de escalado](../../eks-auto-mode/03-scaling-behavior.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es el comportamiento de `consolidationPolicy: WhenEmptyOrUnderutilized` de NodePool?

- A) Solo elimina nodes vacíos
- B) Consolida tanto nodes vacíos como infrautilizados
- C) Siempre mantiene todos los nodes
- D) Solo elimina nodes en momentos específicos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Consolida tanto nodes vacíos como infrautilizados**

**Explicación:**
La política `WhenEmptyOrUnderutilized` consolida no solo nodes vacíos, sino también nodes infrautilizados para optimizar costos. Esto permite consolidar workloads de varios nodes infrautilizados en menos nodes.

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 1m  # Consolidate 1 minute after condition is met
```

**Comparación:**
- `WhenEmpty`: Solo elimina nodes vacíos (conservador)
- `WhenEmptyOrUnderutilized`: Consolida nodes vacíos + infrautilizados (agresivo)

</details>

### 2. ¿Cuál es el comando kubectl para comprobar el estado de NodeClaim?

- A) `kubectl get nodes --show-claims`
- B) `kubectl get nodeclaims`
- C) `kubectl describe karpenter claims`
- D) `kubectl get ec2-nodes`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `kubectl get nodeclaims`**

**Explicación:**
NodeClaim es un recurso que representa el estado de un node que se está aprovisionando.

```bash
# List NodeClaims
kubectl get nodeclaims

# Detailed information for specific NodeClaim
kubectl describe nodeclaim <name>

# View NodeClaims with node information
kubectl get nodeclaims -o wide
```

</details>

### 3. ¿Bajo qué condición comienza el aprovisionamiento de nodes cuando ocurre un Pod en estado Pending en Auto Mode?

- A) Cuando el Pod ha estado en Pending durante más de 5 minutos
- B) Cuando ningún node satisface los requisitos del NodePool
- C) Cuando el recuento total de nodes cae por debajo del umbral
- D) Cuando se ejecuta el comando manual de scale-up

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuando ningún node satisface los requisitos del NodePool**

**Explicación:**
Auto Mode analiza los requisitos de los Pods en Pending y aprovisiona inmediatamente un nuevo node si no existe ningún node adecuado.

**Flujo de aprovisionamiento:**
1. El Pod entra en estado Pending
2. Karpenter analiza las solicitudes de recursos, nodeSelector y affinity del Pod
3. Comprueba los requisitos de los NodePools adecuados
4. Selecciona el tipo de instancia óptimo
5. Lanza una instancia EC2 (40-90 segundos)

</details>

### 4. ¿En qué casos NO ocurre la Consolidation?

- A) Cuando el node tiene la anotación do-not-disrupt
- B) Cuando el node solo tiene Pods de DaemonSet
- C) Cuando no ha transcurrido el tiempo consolidateAfter
- D) Todas las anteriores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Todas las anteriores**

**Explicación:**
La Consolidation no ocurre en las siguientes situaciones:

1. **Anotación do-not-disrupt**: Los nodes o Pods con esta anotación se excluyen de la consolidation
2. **Solo Pods de DaemonSet**: Los DaemonSets se ejecutan en todos los nodes, por lo que se tratan como un node vacío
3. **consolidateAfter no transcurrido**: Debe esperarse el tiempo especificado después de que se cumpla la condición

```yaml
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

</details>

### 5. ¿Qué situaciones activan la detección de Drift?

- A) Cuando cambia la especificación de NodeClass
- B) Cuando una nueva AMI está disponible
- C) Cuando cambian los security groups
- D) Todas las anteriores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Todas las anteriores**

**Explicación:**
La detección de Drift se activa cuando el estado actual de un node difiere del estado deseado:

- **Cambios en NodeClass**: Se cambiaron la familia de AMI, subnets, security groups, etc.
- **Nueva AMI**: AMI optimizada para EKS actualizada
- **Cambios en security groups**: Se modificaron los security groups referenciados

Cuando se detecta Drift, los nodes se reemplazan secuencialmente.

</details>

### 6. ¿Qué familia de AMI se recomienda para optimizar la velocidad de aprovisionamiento de nodes?

- A) AL2023
- B) Bottlerocket
- C) Ubuntu
- D) Amazon Linux 2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Bottlerocket**

**Explicación:**
Bottlerocket es un OS diseñado específicamente para containers, que proporciona tiempos de arranque más rápidos que AL2023.

**Comparación de tiempo de arranque:**
- **AL2023**: 20-40 segundos
- **Bottlerocket**: 15-25 segundos

Beneficios adicionales de Bottlerocket:
- Superficie de ataque más pequeña
- Sistema de archivos inmutable
- Actualizaciones de seguridad automáticas

</details>
