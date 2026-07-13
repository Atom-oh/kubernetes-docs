# Cuestionario sobre el ciclo de vida de Node de EKS Auto Mode

> **Documento relacionado**: [Ciclo de vida de Node](../../eks-auto-mode/07-node-lifecycle.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es el nombre del campo de configuración para reemplazar periódicamente nodos en NodePool?

- A) `nodeLifetime`
- B) `maxAge`
- C) `expireAfter`
- D) `rotationPeriod`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `expireAfter`**

**Explicación:**
El campo `expireAfter` permite establecer la vida útil máxima del Node para el reemplazo periódico de nodos, con el fin de aplicar parches de seguridad o actualizaciones de AMI.

```yaml
spec:
  template:
    spec:
      # Set maximum node lifetime
      expireAfter: 168h  # Auto-replace after 7 days
```

**Configuraciones comunes:**
- Entorno de desarrollo: 336h (14 días)
- Staging: 168h (7 días)
- Producción: 72h ~ 168h (3-7 días)
- Entorno crítico para la seguridad: 24h ~ 48h (1-2 días)

</details>

### 2. ¿Qué ocurre cuando vence un Node que tiene expireAfter configurado?

- A) El Node se elimina inmediatamente
- B) El Node se marca como no programable, se drena y luego se elimina
- C) Solo se envía una notificación al administrador
- D) El Node se reinicia automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El Node se marca como no programable, se drena y luego se elimina**

**Explicación:**
Cuando un Node vence, Karpenter ejecuta un proceso ordenado:

1. **Cordon**: Bloquea la programación de nuevos Pods
2. **Drain**: Mueve los Pods existentes a otros nodos
3. **Delete**: Termina la instancia EC2

PodDisruptionBudgets y Disruption Budgets se respetan durante este proceso.

```yaml
disruption:
  budgets:
    # Expiration-based replacement also follows this budget
    - nodes: "10%"
```

</details>

### 3. ¿Qué AMI proporciona un tiempo de arranque más rápido entre AL2023 y Bottlerocket?

- A) AL2023
- B) Bottlerocket
- C) Son iguales
- D) Depende del tipo de instancia

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Bottlerocket**

**Explicación:**
Bottlerocket es un OS optimizado para workloads de contenedores, que proporciona tiempos de arranque más rápidos que AL2023.

**Comparación de tiempo de arranque:**
| AMI | Tiempo de arranque | Características |
|-----|-----------|-----------------|
| AL2023 | 20-40 sec | Paquetes generales, flexibilidad |
| Bottlerocket | 15-25 sec | Solo contenedores, OS mínimo |

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: fast-boot
spec:
  amiFamily: Bottlerocket  # Fast boot
```

Beneficios adicionales de Bottlerocket:
- Sistema de archivos raíz inmutable
- Actualizaciones de seguridad automáticas
- Superficie de ataque menor

</details>

### 4. ¿Qué ocurre cuando se detecta Drift en nodos existentes debido a actualizaciones de AMI?

- A) El Node se actualiza automáticamente in-place
- B) Los nodos se reemplazan secuencialmente con la nueva AMI
- C) Reemplazo después de la aprobación del administrador
- D) No ocurre nada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los nodos se reemplazan secuencialmente con la nueva AMI**

**Explicación:**
Cuando una nueva AMI está disponible, EKS Auto Mode detecta Drift y reemplaza los nodos secuencialmente.

**Condiciones de detección de Drift:**
- Nueva versión de AMI optimizada para EKS
- Cambio de amiFamily en NodeClass
- Cambios en security group
- Cambios en la configuración de subnet

```yaml
# Drift-based replacement also follows Disruption Budget
disruption:
  budgets:
    - nodes: "10%"  # Only 10% replaced at a time
```

</details>

### 5. ¿Cuál es un trade-off potencial al configurar expireAfter con un valor corto para mantener los nodos actualizados?

- A) Reducción de costos
- B) Posible degradación temporal del rendimiento debido al aumento de la frecuencia de reemplazo de nodos
- C) Aumento de vulnerabilidades de seguridad
- D) Mejora de la estabilidad del cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Posible degradación temporal del rendimiento debido al aumento de la frecuencia de reemplazo de nodos**

**Explicación:**
Un expireAfter corto mejora la seguridad, pero tiene los siguientes trade-offs:

**Ventajas:**
- Se aplican los parches de seguridad más recientes
- Aplicación rápida de actualizaciones de AMI
- Prevención de drift de nodos

**Desventajas:**
- Reducción temporal de capacidad durante el reemplazo de nodos
- Más reprogramación de Pods
- Posibilidad adicional de interrupciones para instancias Spot

**Recomendaciones:**
```yaml
# Balanced setting
spec:
  template:
    spec:
      expireAfter: 168h  # 7 days
  disruption:
    budgets:
      - nodes: "10%"  # Limit concurrent replacement
```

</details>

### 6. ¿Qué tiene precedencia cuando Consolidation y Expiration se activan simultáneamente?

- A) Consolidation siempre tiene precedencia
- B) Expiration siempre tiene precedencia
- C) Se ejecuta lo que alcance primero la condición de reemplazo de Node
- D) El administrador debe elegir

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Se ejecuta lo que alcance primero la condición de reemplazo de Node**

**Explicación:**
Karpenter evalúa múltiples razones de disruption de forma independiente y ejecuta la acción cuando se cumplen las condiciones.

**Prioridad de disruption (orden típico de evaluación):**
1. **Drift**: Se detecta un cambio de configuración o una actualización de AMI
2. **Expiration**: Se excedió el tiempo de expireAfter
3. **Consolidation**: Node subutilizado o vacío

```yaml
# Example: 5-day-old underutilized node
# - expireAfter: 7 days -> Not expired yet
# - Consolidation condition met -> Replaced by Consolidation

# Example: 8-day-old normal utilization node
# - expireAfter: 7 days -> Expired
# - Replaced by Expiration
```

</details>

### 7. ¿Qué método se usa cuando los nodos deben reemplazarse inmediatamente para aplicar parches de seguridad?

- A) Configurar expireAfter en 0
- B) Agregar la anotación Drift al Node
- C) Actualizar NodeClass para activar Drift o drenar el Node
- D) Reiniciar el cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Actualizar NodeClass para activar Drift o drenar el Node**

**Explicación:**
Métodos de aplicación de parches de seguridad de emergencia:

**Método 1: Actualización de NodeClass (recomendado)**
```yaml
# Trigger drift by changing tags or settings
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: default
spec:
  tags:
    SecurityPatch: "2025-02-19"  # Drift triggered by tag change
```

**Método 2: Drain manual**
```bash
# Drain specific node
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Delete node (Auto Mode provisions new node)
kubectl delete node <node-name>
```

**Método 3: Reemplazo continuo**
```bash
# Sequentially replace all nodes
kubectl delete nodes -l karpenter.sh/nodepool=general-purpose
```

</details>

### 8. ¿Qué comportamiento resulta de configurar expireAfter en Never?

- A) El Node vence inmediatamente
- B) El reemplazo automático basado en tiempo queda deshabilitado
- C) La configuración se invalida y se aplica el valor predeterminado
- D) Se produce un error

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El reemplazo automático basado en tiempo queda deshabilitado**

**Explicación:**
Configurar `expireAfter: Never` deshabilita la expiración de nodos basada en tiempo.

```yaml
spec:
  template:
    spec:
      expireAfter: Never  # Disable time-based expiration
```

**Precauciones:**
- Drift y Consolidation siguen funcionando
- La aplicación de parches de seguridad puede demorarse
- Recomendado solo para workloads de larga duración

**Casos de uso recomendados:**
- Workloads con estado (bases de datos)
- Jobs de muy larga duración
- Entornos con cronogramas de mantenimiento manual

</details>
