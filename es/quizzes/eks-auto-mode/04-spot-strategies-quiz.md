# Cuestionario sobre estrategias de Spot en EKS Auto Mode

> **Documento relacionado**: [Estrategias para instancias Spot](../../eks-auto-mode/04-spot-strategies.md)

## Preguntas de opción múltiple

### 1. ¿Qué estrategia amplía las opciones compatibles de capacidad Spot?

- A) Usar un solo tipo de instancia en una zona de disponibilidad
- B) Permitir diversos tipos, tamaños, arquitecturas y zonas de disponibilidad compatibles
- C) Exigir imágenes incompatibles en arquitecturas adicionales
- D) Seleccionar siempre solo el tipo más barato

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Permitir diversos tipos, tamaños, arquitecturas y zonas de disponibilidad compatibles**

**Explicación:** Los grupos de capacidad Spot corresponden a combinaciones de tipo de instancia y zona de disponibilidad. Diversificar ofrece más opciones, pero no hace que las interrupciones sean independientes ni duplica la capacidad real solo por enumerar dos arquitecturas. Valida primero la imagen, las dependencias y el perfil de rendimiento.

```yaml
requirements:
- key: eks.amazonaws.com/instance-category
  operator: In
  values:
  - m
  - c
  - r
  - i
  - d
- key: eks.amazonaws.com/instance-generation
  operator: Gt
  values:
  - '4'
- key: eks.amazonaws.com/instance-size
  operator: In
  values:
  - large
  - xlarge
  - 2xlarge
- key: kubernetes.io/arch
  operator: In
  values:
  - amd64
  - arm64
- key: karpenter.sh/capacity-type
  operator: In
  values:
  - spot
```

Este es un fragmento de requisitos, no un NodePool completo.

</details>

### 2. ¿Qué etiqueta distingue la capacidad Spot de la On-Demand en estos ejemplos?

- A) node.kubernetes.io/capacity-type
- B) karpenter.sh/capacity-type
- C) eks.amazonaws.com/instance-type
- D) karpenter.k8s.aws/spot-or-ondemand

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) karpenter.sh/capacity-type**

**Explicación:** Usa `karpenter.sh/capacity-type` en los requisitos de NodePool o en la selección de Pods. La afinidad preferida no exige Spot, no reserva nodos de sobra ni establece una proporción fija entre opciones de compra.

```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values:
          - spot
```

Para una base obligatoria, usa un selector estricto compatible o una afinidad requerida en una carga de trabajo separada. `spec.nodeName` obtenido mediante Downward API es el nombre de un nodo, no un indicador booleano de Spot.

</details>

### 3. ¿Cómo se debe interpretar el aviso de detención o terminación de una instancia EC2 Spot?

- A) Se garantizan treinta segundos para cada Pod
- B) Normalmente son dos minutos, con entrega según el mejor esfuerzo
- C) Se garantizan cinco minutos para cada Pod
- D) Se puede solicitar una extensión de diez minutos con preStop

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Normalmente son dos minutos, con entrega según el mejor esfuerzo**

**Explicación:** EC2 normalmente avisa con dos minutos de antelación antes de detener o terminar una instancia, pero la entrega del aviso es según el mejor esfuerzo y la hibernación puede comenzar de inmediato. La detección de Kubernetes, la expulsión del Pod y el trabajo de la aplicación consumen parte del tiempo. El periodo de gracia del Pod y los hooks preStop no amplían el plazo de EC2; una pausa de 90 segundos no implementa un punto de control ni un apagado ordenado. Usa puntos de control duraderos y periódicos, recuperación idempotente y gestión probada de las señales de la aplicación.

</details>

### 4. ¿Qué patrón requiere más rediseño antes de depender de capacidad interrumpible?

- A) Procesamiento por lotes idempotente con reintentos validados
- B) Servicio sin estado replicado, con conmutación por error probada
- C) Base de datos crítica de una sola instancia, sin recuperación y cuyo único estado está en almacenamiento local
- D) Trabajos de desarrollo que toleran demoras y reintentos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Base de datos crítica de una sola instancia, sin recuperación y cuyo único estado está en almacenamiento local**

**Explicación:** El patrón de una sola instancia puede perder disponibilidad y todo su estado. Usar On-Demand tampoco vuelve duradero el almacenamiento local del nodo ni elimina el riesgo de mantenimiento o fallo. Las bases de datos, las colas y los trabajos de larga duración requieren una evaluación específica de su arquitectura, no una regla general basada solo en el nombre de la carga.

</details>

### 5. ¿Cómo se habilita la selección Spot primero en un mismo NodePool con capacidad mixta?

- A) Establecer `spotPriority: high`
- B) Permitir Spot y On-Demand; Auto Mode aplica la prioridad entre capacidades aptas
- C) Establecer `capacityPriority: spot`
- D) Usar el peso para reservar exactamente un 80 % de nodos Spot

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Permitir Spot y On-Demand; Auto Mode aplica la prioridad entre capacidades aptas**

**Explicación:** Permite ambos tipos de capacidad. El orden de la lista y el peso no eligen un porcentaje dentro de ese NodePool. Si también se permite capacidad reservada y esta es adecuada, tiene prioridad sobre Spot; Spot tiene prioridad sobre On-Demand. Siguen aplicándose la disponibilidad y las restricciones.

Una estrategia separada con dos pools puede usar pesos para influir en la preferencia de aprovisionamiento:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-first
spec:
  weight: 100
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
        - r
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
        capacity-strategy: spot-preferred
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ondemand-fallback
spec:
  weight: 10
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
        - r
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
        capacity-strategy: spot-preferred
  limits:
    cpu: '100'
    memory: 400Gi
```

Ambos pools tienen una etiqueta y un taint de laboratorio comunes. Las cargas de trabajo que necesitan capacidad alternativa deben tolerar el taint y coincidir con ambos pools; fijar un Pod al nombre del pool exclusivo de Spot impide esa alternativa. El peso no mueve los Pods ya programados ni garantiza que la capacidad alternativa aparezca de inmediato.

</details>

### 6. ¿Qué descuento potencial anuncia AWS para EC2 Spot?

- A) Un ahorro garantizado del 30–40 %
- B) Un ahorro garantizado del 50–60 %
- C) Hasta un 90 % frente a On-Demand; no garantiza ese ahorro en toda la carga de trabajo
- D) Un ahorro garantizado del 95 % o más

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Hasta un 90 % frente a On-Demand; no garantiza ese ahorro en toda la carga de trabajo**

**Explicación:** Las tarifas reales y el coste del trabajo útil dependen del tipo, la zona de disponibilidad, el periodo, la recuperación y otros cargos. Las tarifas de administración de Auto Mode se suman al precio de EC2. A continuación se conserva la tabla didáctica anterior, sin afirmar que sus resultados se hayan verificado:

| Ilustración anterior | Cifra no verificada |
|---|---|
| Spot | 70–90 % |
| Graviton/ARM | Alrededor del 20 % |
| Spot + Graviton | Hasta un 90 % |

No se establecieron las bases de comparación ni las mediciones. No sumes estos porcentajes ni los trates como ahorros garantizados. Los datos de Advisor resumen el mes anterior y pueden llegar con retraso; usa el historial de precios por zona de disponibilidad o las facturas reales, y evita contar dos veces las horas de recuperación.

</details>
