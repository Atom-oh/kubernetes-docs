# Cuestionario de operaciones de EKS Auto Mode

> **Documento relacionado**: [Operaciones](../../eks-auto-mode/05-operations.md)
> **Última actualización**: 12 de septiembre de 2026

## Preguntas de opción múltiple

### 1. ¿Qué configuración programada bloquea las interrupciones voluntarias aplicables de un NodePool durante el horario laboral de Seúl?

- A) `nodes: "100%"`
- B) `nodes: "0"` con un horario UTC con límites correctos
- C) `consolidateAfter: 0s`
- D) `consolidationPolicy: Never`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `nodes: "0"` con un horario UTC con límites correctos**

**Explicación:**
Un presupuesto de cero bloquea, mientras está activo, los métodos de disrupción ordenada aplicables, como la consolidación y el drift. No impide las interrupciones de EC2, la expiración, la reparación ni todas las eliminaciones manuales. El inicio diario a las 00:00 UTC y la duración de nueve horas que se muestran abajo corresponden al horario de 09:00–18:00 de Seúl, de lunes a viernes. Un horario por hora `9-18` con una duración de nueve horas inicia repetidamente ventanas que se superponen.
```yaml
# Fragment of NodePool spec.disruption
budgets:
  - nodes: "10%"
  - nodes: "0"
    schedule: "0 0 * * mon-fri"
    duration: 9h
```


</details>

### 2. ¿Qué significa `minAvailable: "80%"` para un PDB que selecciona seis réplicas de un controlador escalable?

- A) No puede haber más del 80 % en ejecución
- B) Las decisiones de desalojo requieren cinco réplicas sanas tras redondear hacia arriba
- C) Cada Pod tiene un 80 % de probabilidad de conservarse
- D) Los Pods están protegidos durante 80 segundos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las decisiones de desalojo requieren cinco réplicas sanas tras redondear hacia arriba**

**Explicación:**
El controlador redondea hacia arriba el 80 % de seis, por lo que exige cinco réplicas sanas/Ready. Esto limita las decisiones de la API Eviction, pero no todos los fallos, las eliminaciones directas ni la creación de réplicas. `minAvailable` y `maxUnavailable` son campos alternativos con significados distintos; no configure ambos. El ejemplo del documento base, con cinco réplicas y `minAvailable: 3`, permite hasta dos desalojos, mientras que `maxUnavailable: 1` permite solo uno.
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
  namespace: ops-lab
spec:
  minAvailable: "80%"
  selector:
    matchLabels:
      app: web-app
```

Un valor de cero para `disruptionsAllowed` puede ser un bloqueo intencional y saludable. Antes de considerarlo una infracción, inspeccione `observedGeneration`, `currentHealthy` y `desiredHealthy`.

</details>

### 3. ¿Qué recurso ayuda a diagnosticar el ciclo de aprovisionamiento de un nodo de Auto Mode?

- A) Solo los logs de la aplicación
- B) Las condiciones de NodeClaim, seguidas de la evidencia relacionada de NodePool/NodeClass
- C) Solo la consola de EC2
- D) Solo un widget de CloudWatch

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las condiciones de NodeClaim, seguidas de la evidencia relacionada de NodePool/NodeClass**

**Explicación:**
Lea las condiciones y los motivos; luego investigue las restricciones de planificación, la disponibilidad de NodeClass y la configuración de IAM y red según indique la evidencia. NodeClaim no tiene un campo general `.status.phase`. El siguiente comando usa el `KUBE_CONTEXT` revisado y definido en la guía relacionada, y selecciona campos de diagnóstico en lugar de volcar los objetos completos.
```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaims -o json |
  jq '[.items[] | {name: .metadata.name, uid: .metadata.uid, node: .status.nodeName,
      pool: .metadata.labels["karpenter.sh/nodepool"], createdAt: .metadata.creationTimestamp,
      expireAfter: .spec.expireAfter, terminationGracePeriod: .spec.terminationGracePeriod,
      imageID: .status.imageID,
      conditions: [.status.conditions[]? | {type,status,reason,lastTransitionTime,observedGeneration}]}]'
```


</details>

### 4. ¿Cuál es la anotación reconocida `do-not-disrupt`?

- A) `kubernetes.io/do-not-disrupt: "true"`
- B) `karpenter.sh/do-not-disrupt: "true"`
- C) `eks.amazonaws.com/no-disrupt: "true"`
- D) `node.kubernetes.io/exclude-disruption: "true"`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `karpenter.sh/do-not-disrupt: "true"`**

**Explicación:**
Las anotaciones de Pod y Node tienen alcances distintos. La anotación de un Pod bloquea su desalojo voluntario y la consolidación del nodo donde se ejecuta; el periodo de gracia de terminación de NodeClaim permite el drift de un nodo que contiene esos Pods y, en última instancia, limita el tiempo de drenaje. Una anotación de Node excluye ese nodo de las disrupciones voluntarias. Ninguna ofrece una garantía indefinida frente a expiraciones, interrupciones, reparaciones o eliminaciones manuales. Auto Mode tiene su propio periodo de gracia de terminación predeterminado; no suponga que está sin definir.
```yaml
# Metadata fragment for a deliberately selected Pod or Node.
# Review the different Pod/Node semantics before applying.
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

Un fragmento de metadatos no constituye un Pod completo que pueda ejecutarse. Defina un plan de recuperación y retirada antes de aplicar este control a una carga de trabajo real.

</details>

### 5. ¿Qué enfoque de monitoreo aporta evidencia útil para las operaciones de Auto Mode?

- A) Usar solo `kubectl top`
- B) Combinar los collectors y la entrega de logs configurados con las condiciones de Kubernetes y las señales de las cargas de trabajo
- C) Usar solo la consola de EC2
- D) Suponer que todas las métricas existen en CloudWatch sin configurar su recopilación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Combinar los collectors y la entrega de logs configurados con las condiciones de Kubernetes y las señales de las cargas de trabajo**

**Explicación:**
Container Insights, las métricas del plano de control de EKS, kube-state-metrics/node-exporter y los logs de los componentes administrados de Auto Mode tienen requisitos previos distintos. Verifique cada publicador y sus dimensiones. `kubectl top` requiere que la API de métricas funcione; un error no demuestra que metrics-server esté ausente. Los logs de los componentes administrados requieren su propia configuración de entrega de Vended Logs. La latencia de planificación y la disponibilidad de la aplicación necesitan instrumentación adecuada; habilitar Container Insights no genera automáticamente todas las señales propuestas.

</details>

### 6. ¿Qué campo de NodePool determina cuándo un nodo pasa a ser elegible para expirar por antigüedad?

- A) `autoUpdate: true`
- B) `expireAfter`
- C) `updatePolicy: Rolling`
- D) `refreshInterval: 24h`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `expireAfter`**

**Explicación:**
El ejemplo hace que NodeClaim sea elegible para expirar después de 168 horas y establece por separado un límite para su fase de terminación. No promete siete días de disponibilidad ininterrumpida, un reemplazo en un momento exacto ni la instalación del parche de seguridad más reciente para esa fecha límite. Antes pueden producirse drift, consolidación o interrupciones, y cambiar la plantilla no modifica los NodeClaims existentes. Compruebe los valores predeterminados y la vida útil máxima de Auto Mode, así como los requisitos de recuperación de la aplicación.
```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```


</details>

### 7. ¿Cómo se combinan varios presupuestos de disrupción aplicables de NodePool?

- A) La última entrada programada reemplaza las anteriores
- B) Prevalece el límite más estricto
- C) Sus porcentajes se suman
- D) Establecen un número garantizado de nodos de reemplazo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Prevalece el límite más estricto**

**Explicación:**
Un límite permanente del 10 % no puede flexibilizarse con un presupuesto programado del 30 %. La guía relacionada parte de un 30 %, añade un límite del 10 % para los días laborables de Seúl y otro de un nodo para el horario laboral, además de una congelación mensual explícita en UTC. Para 20 nodos que por lo demás están en buen estado, los límites son seis, dos, uno y cero, respectivamente. Los nodos que se eliminan o no están listos reducen el límite; estos presupuestos no restringen todas las disrupciones forzosas.
```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
  - nodes: 30%
  - nodes: 10%
    schedule: 0 15 * * sun-thu
    duration: 24h
  - nodes: '1'
    schedule: 0 0 * * mon-fri
    duration: 9h
  - nodes: '0'
    schedule: 0 0 1 * *
    duration: 24h
```


</details>

### 8. ¿Qué señales ayudan a definir alertas operativas relacionadas con nodos cuando sus publicadores están configurados?

- A) Solo el estado de EC2
- B) Acumulación de Pods pendientes de planificación, latencia de aprovisionamiento medida y disponibilidad de las cargas de trabajo
- C) Solo el costo
- D) Solo el tráfico de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Acumulación de Pods pendientes de planificación, latencia de aprovisionamiento medida y disponibilidad de las cargas de trabajo**

**Explicación:**
Para cada alerta, elija un publicador, sus dimensiones, una estadística, una ventana temporal y un objetivo de la aplicación. Que un Pod esté Pending no significa que no se pueda planificar. Los ejemplos numéricos originales que aparecen abajo se conservan como umbrales de planificación no verificados, no como rangos normales medidos, valores predeterminados de Auto Mode ni métricas garantizadas de Container Insights.

| Señal | Ejemplo previo de planificación | Ejemplo previo de alerta |
|--------|---------------------------|------------------------|
| Pods en estado Pending | 0–5 | >10 durante 5 min |
| Tiempo de aprovisionamiento del nodo | <90 s | >120 s |
| Disponibilidad de la carga de trabajo | >99.9% | <99.5% |
| Tiempo de respuesta de la API | <200 ms | >500 ms |

La ausencia de métricas o el retraso de los collectors deben poder distinguirse de cero errores. La guía genera una definición local de panel de CloudWatch a partir de un catálogo real de métricas, en lugar de inventar nombres de métricas.

</details>

## Referencias

- [Controles de disrupción de Karpenter](https://karpenter.sh/v1.14/concepts/disruption/)
- [Semántica de PDB de Kubernetes](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [NodePools de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
