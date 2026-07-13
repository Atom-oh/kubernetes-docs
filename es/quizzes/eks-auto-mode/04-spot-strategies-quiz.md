# Cuestionario sobre estrategias Spot de EKS Auto Mode

> **Documento relacionado**: [Estrategias de Spot Instance](../../eks-auto-mode/04-spot-strategies.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es la estrategia óptima para distribuir el riesgo de interrupción de Spot instance?

- A) Usar solo un único tipo de instancia
- B) Usar diversas familias, generaciones y tamaños de instancia
- C) Usar solo On-Demand
- D) Seleccionar solo las instancias más baratas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar diversas familias, generaciones y tamaños de instancia**

**Explicación:**
Las Spot instances experimentan interrupciones por pool de capacidad. Permitir tipos de instancia diversos permite adquirir instancias de múltiples pools de capacidad, distribuyendo el riesgo de interrupción.

```yaml
spec:
  template:
    spec:
      requirements:
        # Diverse instance families
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r", "i", "d"]
        # Diverse generations
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
        # Diverse sizes
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]
        # Diverse architectures
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
```

</details>

### 2. ¿Cuál es la clave de etiqueta de Karpenter que distingue entre instancias Spot y On-Demand?

- A) `node.kubernetes.io/capacity-type`
- B) `karpenter.sh/capacity-type`
- C) `eks.amazonaws.com/instance-type`
- D) `karpenter.k8s.aws/spot-or-ondemand`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `karpenter.sh/capacity-type`**

**Explicación:**
Esta etiqueta permite especificar instancias Spot/On-Demand en nodeAffinity de Pod o en los requisitos de NodePool.

```yaml
# Setting Spot instance preference in Pod
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
            - key: karpenter.sh/capacity-type
              operator: In
              values: ["spot"]
```

</details>

### 3. ¿Cuál es el tiempo de advertencia predeterminado antes de que se interrumpa una Spot instance?

- A) 30 segundos
- B) 2 minutos
- C) 5 minutos
- D) 10 minutos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 2 minutos**

**Explicación:**
AWS Spot instances reciben una advertencia de 2 minutos antes de ser reclamadas. Las cargas de trabajo deben finalizar correctamente durante este tiempo.

**Prácticas recomendadas para gestionar interrupciones de Spot:**
- Configurar terminationGracePeriodSeconds del Pod en 2 minutos o menos
- Implementar un controlador SIGTERM en las aplicaciones
- Preferir cargas de trabajo sin estado
- Implementar un mecanismo de checkpointing (para trabajos batch)

</details>

### 4. ¿Qué tipo de carga de trabajo NO se recomienda para Spot instances?

- A) Trabajos de procesamiento batch
- B) Servidores web sin estado
- C) Bases de datos de una sola instancia
- D) Entornos de desarrollo/prueba

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Bases de datos de una sola instancia**

**Explicación:**
Las bases de datos de una sola instancia pueden experimentar problemas de disponibilidad durante las interrupciones, lo que las hace inadecuadas para Spot.

**Cargas de trabajo adecuadas para Spot:**
- Procesamiento batch / análisis de Big data
- Pipelines de CI/CD
- Servidores web sin estado (Auto Scaling)
- Entornos de desarrollo/prueba
- Microservicios basados en contenedores

**Cargas de trabajo que requieren On-Demand:**
- Bases de datos
- Colas de mensajes
- Componentes de administración del clúster
- Trabajos con estado de larga duración

</details>

### 5. ¿Cómo se configura la selección Spot-first al mezclar Spot y On-Demand en NodePool?

- A) `spotPriority: high`
- B) Configuración de prioridad de NodePool mediante el valor de weight
- C) `capacityPriority: spot`
- D) `preferSpot: true`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configuración de prioridad de NodePool mediante el valor de weight**

**Explicación:**
Crea varios NodePools y especifica la prioridad con valores de weight. El weight más alto se usa primero.

```yaml
# Spot-first NodePool (weight: 100)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-first
spec:
  weight: 100  # High priority
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
---
# On-Demand fallback NodePool (weight: 10)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ondemand-fallback
spec:
  weight: 10  # Low priority
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
```

</details>

### 6. ¿Cuál es la tasa máxima de ahorro para Spot instances en comparación con On-Demand?

- A) 30-40%
- B) 50-60%
- C) 70-90%
- D) 95% o más

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 70-90%**

**Explicación:**
Las Spot instances pueden lograr hasta un 70-90% de ahorro de costos en comparación con On-Demand.

**Combinaciones de estrategias de optimización de costos:**
| Estrategia | Ahorro esperado |
|----------|-----------------|
| Spot instances | 70-90% |
| Graviton (ARM) | ~20% |
| Spot + Graviton | Hasta 90% |

Sin embargo, las tasas de ahorro de Spot varían según el tipo de instancia y la zona de disponibilidad.

</details>
