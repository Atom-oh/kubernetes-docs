# Cuestionario de optimización de cargas de trabajo de EKS Auto Mode

> **Documento relacionado**: [Optimización de cargas de trabajo](../../eks-auto-mode/08-workload-optimization.md)
> **Última actualización**: 12 de septiembre de 2026

## Preguntas de opción múltiple

### 1. ¿Cuál es un punto de partida razonable para un frontend sensible a la disponibilidad?

- A) Suponer que usar solo Spot siempre es adecuado
- B) Instancias On-Demand con controles de disponibilidad de la aplicación y de interrupciones
- C) Exigir siempre GPU
- D) Usar solo nodos optimizados para memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Instancias On-Demand con controles de disponibilidad de la aplicación y de interrupciones**

**Explicación:**
On-Demand evita los eventos de reclamación de Spot, pero no garantiza la disponibilidad. Deben probarse las réplicas, la distribución topológica, la preparación, los PDB y la recuperación. El presupuesto alternativo que se muestra a continuación inicia una ventana diaria a las 00:00 UTC durante 14 horas: de 09:00 a 23:00 en Seúl. No usa el antiguo patrón por hora `9-23`, que extendía la ventana repetidamente. Los presupuestos activos se combinan tomando el mínimo y no controlan todas las interrupciones forzosas.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: web-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: web-tier
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
    - nodes: '1'
      schedule: 0 0 * * *
      duration: 14h
  limits:
    cpu: '32'
    memory: 128Gi
```


</details>

### 2. ¿Qué pool puede ser adecuado para una carga de procesamiento por lotes que haya demostrado tolerancia a interrupciones y recuperación duradera?

- A) On-Demand es la única opción posible
- B) Spot con diversidad de instancias compatible y limpieza de nodos vacíos
- C) Solo GPU
- D) El pool del sistema de forma predeterminada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Spot con diversidad de instancias compatible y limpieza de nodos vacíos**

**Explicación:**
No todos los trabajos por lotes toleran interrupciones. Usar solo Spot no ofrece respaldo On-Demand. Reiniciar el contenedor o configurar `SPOT_AWARE=true` no implementa la lógica de puntos de control/reanudación; use resultados idempotentes y progreso duradero. `WhenEmpty` con una espera de 30s no termina un trabajo en ejecución al cabo de 30 segundos. La guía relacionada ofrece un Job Indexed de prueba acotada, no un procesador de datos de producción.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '4'
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: batch-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: batch-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
    - nodes: 10%
  limits:
    cpu: '16'
    memory: 64Gi
```


</details>

### 3. ¿Cómo debe interpretarse un `consolidateAfter` de 15 minutos en un pool de inferencia?

- A) Como un plazo garantizado para iniciar una GPU
- B) Como un ejemplo de equilibrio entre la espera de consolidación y la rotación de nodos
- C) Como una demora antes de que el planificador pueda colocar cualquier Pod
- D) Como una garantía de que el nodo nunca expirará

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Como un ejemplo de equilibrio entre la espera de consolidación y la rotación de nodos**

**Explicación:**
No hace que una GPU pase a Ready ni garantiza capacidad ya preparada. `WhenEmpty` limita la consolidación; la desviación de configuración, la expiración y las interrupciones son aspectos independientes. Ajuste el calentamiento del modelo, la capacidad deseada y el costo al comportamiento medido. La plantilla de inferencia de la guía permanece con cero réplicas hasta que se proporcionen una imagen, un entorno de ejecución y sondas revisados. Además, un Pod de 4 CPU/16Gi no cabe en una instancia g5.xlarge después de reservar recursos para el sistema.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - g
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g5.2xlarge
        - g5.4xlarge
      - key: eks.amazonaws.com/instance-gpu-manufacturer
        operator: In
        values:
        - nvidia
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: gpu-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: gpu-tier
        effect: NoSchedule
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: gpu-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 15m
    budgets:
    - nodes: 10%
  limits:
    cpu: '64'
    memory: 256Gi
    nvidia.com/gpu: '4'
```


</details>

### 4. ¿Qué puede equilibrar el costo y la disponibilidad para un backend de API de aplicación compatible y tolerante a interrupciones?

- A) On-Demand siempre es una mala opción
- B) Usar solo Spot siempre garantiza la disponibilidad
- C) Evaluar una combinación de Spot/On-Demand y la compatibilidad probada con ARM
- D) Suponer que Auto Mode aprovisiona nodos Fargate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Evaluar una combinación de Spot/On-Demand y la compatibilidad probada con ARM**

**Explicación:**
Esto se refiere al backend de una API de aplicación, no al servidor de API de Kubernetes administrado por AWS. La capacidad mixta no implica una proporción fija ni un respaldo inmediato; ARM requiere imágenes y dependencias compatibles, además de pruebas de la aplicación. `weight: 10` es una preferencia relativa de aprovisionamiento, no un porcentaje ni un límite de gasto. El ahorro original de ~40% no está verificado.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: api-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: api-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: api-tier
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
  weight: 10
```


</details>

### 5. ¿Qué debe verificarse antes de permitir amd64 y arm64?

- A) Nada
- B) Las plataformas de las imágenes fijadas, las dependencias nativas y el comportamiento de la aplicación
- C) Solo la versión de Kubernetes
- D) Solo la región

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las plataformas de las imágenes fijadas, las dependencias nativas y el comportamiento de la aplicación**

**Explicación:**
La comprobación del índice que aparece a continuación confirma las entradas de plataforma Linux, no que la imagen funcione correctamente en tiempo de ejecución. Omite las entradas de atestación no relacionadas y rechaza las plataformas faltantes. La guía relacionada muestra el resultado de una compilación OCI local; publicar una imagen `myapp:latest` sin especificar no es una prueba de arquitectura necesaria.

```bash
: "${IMAGE_REF:?Set a reviewed image reference pinned by digest}"
if ! [[ "$IMAGE_REF" =~ @sha256:[0-9a-f]{64}$ ]]; then
  printf 'Use an immutable sha256 digest reference.\n' >&2
  exit 1
fi
docker buildx imagetools inspect --raw "$IMAGE_REF" > "$WORK_DIR/image-index.json"
jq -e '[.manifests[]?.platform |
         select(.os=="linux" and (.architecture=="amd64" or .architecture=="arm64")) |
         .architecture] | unique | sort == ["amd64","arm64"]' \
  "$WORK_DIR/image-index.json"
```


</details>

### 6. ¿Cómo seleccionan las cargas de trabajo el pool previsto y, a la vez, toleran su restricción de ubicación?

- A) Coincidencia por nombre del Pod
- B) Una tolerancia coincidente junto con `nodeSelector` o afinidad de nodo obligatoria
- C) Coincidencia automática por namespace
- D) Solo etiquetas de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una tolerancia coincidente junto con `nodeSelector` o afinidad de nodo obligatoria**

**Explicación:**
Una tolerancia permite colocar un Pod en un nodo con taint, pero no exige que se coloque allí. El selector o la afinidad obligatoria reduce los nodos elegibles. El fragmento de abajo pertenece a `spec` de la plantilla del Pod; la fuente incluye un Job completo. Las etiquetas y los taints no constituyen un límite de autorización entre inquilinos, y una capacidad coincidente insuficiente puede dejar un Pod en estado Pending.
```yaml
nodeSelector:
  karpenter.sh/nodepool: batch-tier
tolerations:
- key: workload-lab
  operator: Equal
  value: batch-tier
  effect: NoSchedule
```


</details>

## Referencias

- [Cómputo de ML en Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [Interrupciones de Karpenter](https://karpenter.sh/v1.14/concepts/disruption/)
- [Compilaciones multiplataforma de Docker](https://docs.docker.com/build/building/multi-platform/)
