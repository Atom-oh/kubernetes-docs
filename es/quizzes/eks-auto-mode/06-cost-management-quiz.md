# Cuestionario sobre gestión de costos de EKS Auto Mode

> **Documento relacionado**: [Gestión de costos](../../eks-auto-mode/06-cost-management.md)
> **Última actualización**: 12 de septiembre de 2026

## Preguntas de opción múltiple

### 1. ¿Cómo se debe interpretar el ejemplo anterior de un «ahorro del 20 % con Graviton» al permitir nodos ARM?

- A) Como una garantía universal de AWS
- B) Como un descuento en la factura completa
- C) Como un ejemplo no verificado; compara cargas de trabajo compatibles y tarifas reales
- D) Como prueba de que todas las imágenes funcionan en ARM

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Como un ejemplo no verificado; compara cargas de trabajo compatibles y tarifas reales**

**Explicación:**
Las cifras anteriores de aproximadamente un 20 % para ARM y un 70–90 % para Spot eran ejemplos de planificación, no una comparación verificada para esta carga de trabajo. Comprueba las imágenes multiarquitectura, las dependencias, el rendimiento por unidad de trabajo útil, las tarifas regionales actuales y los cargos de Auto Mode y otros servicios. Permitir `amd64` y `arm64` no valida la compatibilidad de la aplicación ni garantiza que se seleccione una arquitectura determinada.

</details>

### 2. ¿Qué limita `limits.cpu: 500` en un NodePool dinámico?

- A) Cada nodo a 500 núcleos
- B) Los recursos de CPU agregados que aprovisiona ese pool
- C) Cada Pod a 500m
- D) Todo el gasto de AWS de la cuenta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los recursos de CPU agregados que aprovisiona ese pool**

**Explicación:**
Es un límite de recursos a nivel del pool, que puede superarse temporalmente durante un aprovisionamiento rápido con consistencia eventual. `1Ti` equivale a 1 TiB (1024 GiB), no a un TB decimal. Los límites de recursos ayudan a restringir el crecimiento, pero no asignan precios a las instancias, no incluyen otros servicios ni imponen un presupuesto monetario estricto.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
        - i
        - d
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '500'
    memory: 1Ti
```


</details>

### 3. ¿Qué política permite consolidar nodos vacíos y subutilizados cuando lo permiten las condiciones de reprogramación y costo?

- A) `WhenEmpty`
- B) `WhenEmptyOrUnderutilized`
- C) `Always`
- D) `Aggressive`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `WhenEmptyOrUnderutilized`**

**Explicación:**
Evalúa la viabilidad de la programación basada en solicitudes de recursos y el costo; no elimina todos los nodos que estén por debajo de un umbral de CPU medido. `consolidateAfter` es un periodo de espera para evitar cambios repetidos, y los PDB, los presupuestos y las restricciones de ubicación pueden impedir la consolidación. `WhenEmpty` es más restrictiva; ninguna de las dos políticas garantiza ahorros ni desactiva todos los demás métodos de disrupción.

</details>

### 4. ¿Qué opción ofrece flexibilidad de facturación si el uso de EC2 que reúne los requisitos puede cambiar de familia o región?

- A) Compute Savings Plans
- B) Un EC2 Instance Savings Plan limitado a una familia y región
- C) Solo una Standard RI de tamaño exacto
- D) Excluir todos los descuentos por compromiso

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Compute Savings Plans**

**Explicación:**
Compute Savings Plans ofrece flexibilidad de familia, tamaño, región, sistema operativo y tenencia; EC2 Instance Savings Plans fija la familia y la región, pero permite flexibilidad de tamaño, sistema operativo y tenencia. Los máximos anunciados siguen siendo de hasta el 66 % y el 72 %, no son tarifas esperadas. Ajusta el compromiso en USD por hora al uso elegible, sostenido y no cubierto, a los compromisos existentes y a los cambios previstos. La antigua estrategia de tres meses y cobertura del 70 % es un ejemplo de planificación no verificado. Spot y el cargo separado de Auto Mode no reciben descuentos de EC2 Savings Plans; no existe un plan especial para ARM ni una exclusión universal para GPU.

</details>

### 5. ¿Qué hace falta para obtener una asignación útil de costos por Pod en Kubecost?

- A) Ninguna configuración ni fuente de datos
- B) Solo una etiqueta de centro de costos en el Pod
- C) Una integración configurada con agente/clúster y datos de costos adecuados
- D) Solo Cost Explorer, sin datos de asignación de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Una integración configurada con agente/clúster y datos de costos adecuados**

**Explicación:**
El chart de Kubecost 3.2.4 revisado es `kubecost/kubecost`, del nuevo repositorio. La arquitectura de agente FinOps/ClickHouse de la versión 3 es distinta del antiguo despliegue cost-analyzer. Configura la licencia, el acceso privado, el almacenamiento y su retención, IAM de las cargas de trabajo y la conciliación de facturación. Renderiza los valores revisados antes de la instalación; las etiquetas por sí solas no generan datos de costos reales.
```bash
: "${KUBECOST_VALUES:?Set the reviewed Kubecost 3.2.4 values file}"
test -f "$KUBECOST_VALUES"
helm repo add kubecost https://kubecost.github.io/kubecost/
helm repo update kubecost
helm show chart kubecost/kubecost --version 3.2.4
helm template cost-review kubecost/kubecost --version 3.2.4 \
  --namespace kubecost --values "$KUBECOST_VALUES" \
  > "$WORK_DIR/kubecost-rendered.yaml"
```


</details>

### 6. ¿Qué datos deben orientar los cambios en las solicitudes de recursos?

- A) Hacer siempre iguales las solicitudes y los límites
- B) Las recomendaciones de VPA junto con datos representativos de la carga de trabajo y los SLO
- C) Maximizar todas las solicitudes
- D) Eliminar las solicitudes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las recomendaciones de VPA junto con datos representativos de la carga de trabajo y los SLO**

**Explicación:**
El modo `Off` no aplica las recomendaciones y aun así requiere componentes de VPA y métricas funcionales. Comprueba cada contenedor, la confianza y el historial, los picos de inicio, los límites de memoria y la limitación de CPU. Una recomendación no garantiza el rendimiento, no evita todos los OOM ni demuestra un ahorro. No elimines los sufijos de unidades de Kubernetes al comparar cantidades.
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: cost-app-vpa
  namespace: cost-lab
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cost-efficient-app
  updatePolicy:
    updateMode: 'Off'
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: '4'
        memory: 8Gi
```


</details>

### 7. Si los niveles tienen requisitos realmente distintos de interrupción o arquitectura, ¿qué diseño permite expresarlos?

- A) Exigir la misma ubicación para todos los niveles
- B) Usar pools adecuados por nivel y las restricciones de carga de trabajo correspondientes
- C) Crear un pool distinto para cada tamaño de instancia
- D) Suponer que cada AZ ofrece un descuento de facturación independiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar pools adecuados por nivel y las restricciones de carga de trabajo correspondientes**

**Explicación:**
Los pools separados pueden expresar restricciones reales, pero la fragmentación puede aumentar el costo ocioso. Un pool de procesamiento por lotes exclusivo de Spot no tiene alternativa On-Demand; úsalo solo para trabajos compatibles y tolerantes a interrupciones que cuenten con recuperación. El nombre de un pool no dirige las cargas de trabajo: configura los selectores y las tolerancias indicados en la guía.

| Nivel | Estrategia anterior | Ahorro original no verificado |
|------|----------------|----------------------------|
| Frontend | On-Demand + Graviton | ~20% |
| API | Spot mixto + Graviton | ~40% |
| Procesamiento por lotes | Spot + diversidad | ~70% |
| ML | Dimensionamiento de instancias | ~30% |

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
        - m
        - c
        - r
        - i
        - d
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
```


</details>

### 8. ¿Qué se necesita para que las etiquetas personalizadas de NodeClass permitan asignar costos de AWS?

- A) Todas las etiquetas de Kubernetes se propagan automáticamente
- B) Permisos válidos de NodeClass/etiquetado, etiquetas reales en los recursos y activación en Billing
- C) Solo crear una organización de AWS
- D) No se pueden asignar costos a etiquetas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Permisos válidos de NodeClass/etiquetado, etiquetas reales en los recursos y activación en Billing**

**Explicación:**
La guía relacionada proporciona un NodeClass completo con selectores de identidad y red. Revisa las entradas de acceso de los nodos y los permisos de etiquetado, referencia esa clase desde el pool previsto, verifica las etiquetas reales y activa las claves en Billing. Las claves definidas por el usuario pueden tardar hasta 24 horas en aparecer y otras 24 horas en activarse; la latencia de los informes es independiente. La clave de clúster EC2 generada por AWS es `aws:eks:cluster-name`; no incluye los cargos del plano de control. Las etiquetas de espacios de nombres no se propagan por sí solas ni asignan todos los costos de AWS.

</details>

## Referencias

- [Precios de EKS](https://aws.amazon.com/eks/pricing/)
- [Tipos de Savings Plans](https://docs.aws.amazon.com/savingsplans/latest/userguide/plan-types.html)
- [Etiquetas de facturación de EKS](https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html)
