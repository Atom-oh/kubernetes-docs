# Programa de formación de operadores de EKS Auto Mode (2 horas)

> **Audiencia**: ingenieros de infraestructura/plataforma que operan EKS
> **Requisitos previos**: conocimientos fundamentales de Kubernetes y experiencia operando EKS
> **Última actualización**: 12 de septiembre de 2026

## Objetivos de aprendizaje

Distinguir las responsabilidades administradas por AWS de las que corresponden a los operadores, diseñar recursos NodePool/NodeClass de Auto Mode, evaluar mejoras mediante evidencia de cargas de trabajo/costos/disponibilidad e investigar interrupciones de nodos. No se prometen porcentajes de ahorro ni tiempos de aprovisionamiento fijos.

## Programa y preparación

| Parte | Duración | Desglose |
| --- | --- | --- |
|1: Arquitectura y ubicación |40 min | Arquitectura 10 + NodePool/NodeClass 15 + escalado 15 |
|2: Optimización y ciclo de vida |35 min | Spot 10 + costos 10 + cargas de trabajo 10 + ciclo de vida 5 |
|Pausa |10 min | |
|3: Observabilidad y diagnóstico |25 min | Nodos 8 + correlación de señales 8 + escenarios 9 |
|4: IaC/GitOps |10 min | IaC 5 + ArgoCD 5 |

Total: 120 minutos. Verifique las API actuales, el entorno de laboratorio preparado, la cuenta/región/kubeconfig, los permisos y los límites de costos con la [guía de Auto Mode](../eks-auto-mode/README.md). Una sesión solo teórica puede usar eventos, NodeClaims y métricas capturados. Este programa no ejecuta automáticamente inyecciones de fallos de FIS ni elimina nodos.

El número de líneas y de apariciones de palabras clave no demuestra la calidad de la documentación ni una cobertura adecuada, por eso se eliminó la antigua tabla de evaluación. Use las referencias siguientes y complemente el programa con los procedimientos operativos y de Terragrunt específicos de la organización y de las versiones en uso.

## Parte 1: Arquitectura y ubicación (40 min)

### 1-1. Límites de administración (10 min)

Use la [guía de primeros pasos](../eks-auto-mode/01-getting-started.md) para comparar Auto Mode, los grupos de nodos administrados y Karpenter autoadministrado. Auto Mode proporciona capacidad de cómputo administrada basada en Karpenter; los operadores siguen siendo responsables de las solicitudes de las cargas de trabajo, los PDB y la configuración admitida de red/almacenamiento/identidad de NodeClass.

Auto Mode usa variantes administradas de Bottlerocket, no AMI AL2023/Bottlerocket seleccionables por el usuario, userData arbitrario ni acceso por SSH o SSM. Compruebe que los grupos generales/de sistema estén realmente habilitados y existan. No dé por sentado que el controlador administrado aparece como un Pod normal dentro del clúster.

### 1-2. NodePool y NodeClass (15 min)

Use la [guía de configuración](../eks-auto-mode/02-nodepool-configuration.md) para las etiquetas `eks.amazonaws.com` y las API de NodeClass. No las mezcle con las etiquetas de instancia `karpenter.k8s.aws` ni EC2NodeClass de Karpenter autoadministrado. Se admiten NodeClasses personalizadas; AWS no elige cada ajuste por usted.

Este **ejemplo de esquema** presupone que ya existe un NodeClass predeterminado y que las imágenes son compatibles con Arm. Los límites de CPU/memoria no son topes absolutos de facturación y el aprovisionamiento simultáneo puede superarlos temporalmente. No es un pool universal para todas las cargas de trabajo GPU/Spot.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier-training
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '5'
      - key: kubernetes.io/arch
        operator: In
        values:
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '16'
    memory: 64Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
```

Compare los selectores/afinidad de los Pods, las solicitudes, las taints/tolerations y las restricciones del pool. La migración a Arm requiere validar los manifiestos de imagen, las dependencias nativas y el rendimiento.

### 1-3. Escalado (15 min)

Siga la [guía de escalado](../eks-auto-mode/03-scaling-behavior.md): Pods no programables, restricciones del pool, aprovisionamiento de nodos y preparación de los Pods. No se garantiza un tiempo de 40–90 segundos; mida la descarga de imágenes, las dependencias de IP/cuota/capacidad y los volúmenes.

Compare WhenEmpty, WhenEmptyOrUnderutilized y consolidateAfter, incluidas las cargas cuyas solicitudes difieren de la utilización. La consolidación no reemplaza la optimización manual ni la validación de carga. Drift no garantiza un reemplazo inmediato de uno en uno para cada cambio.

## Parte 2: Optimización y ciclo de vida (35 min)

### 2-1. Spot (10 min)

Use la [guía de Spot](../eks-auto-mode/04-spot-strategies.md) para revisar la diversidad de instancias compatibles, la capacidad crítica y la interrupción/recuperación. Exigir solo Spot es una restricción estricta; no expresa una preferencia con alternativa automática de On-Demand. do-not-disrupt/PDB no impiden la reclamación de instancias Spot ni el fallo de un nodo.

### 2-2. Costos (10 min)

La [guía de costos](../eks-auto-mode/06-cost-management.md) separa EC2, las tarifas de Auto Mode, EBS, balanceadores de carga/NAT/transferencias y observabilidad. No presente como resultados medidos porcentajes hipotéticos multiplicados de Graviton/Spot/consolidación.

Los Savings Plans/RIs de instancias EC2 que cumplan los requisitos pueden aplicarse al uso de EC2 junto con Compute Savings Plans, sujetos a sus condiciones. No descuentan automáticamente las tarifas independientes de Auto Mode ni se acumulan sobre Spot. Savings Plans no son reservas de capacidad. Tome las decisiones de compra por separado, usando líneas base horarias que cumplan los requisitos y la cobertura existente.

### 2-3. Diseño de cargas de trabajo (10 min)

Use la [guía de cargas de trabajo](../eks-auto-mode/08-workload-optimization.md) para comparar las solicitudes, imágenes/arquitectura, almacenamiento y SLO de las cargas web, por lotes, GPU y del sistema. HPA controla las réplicas, VPA recomienda/actualiza CPU/memoria y Auto Mode proporciona los nodos. Las cargas GPU necesitan modelos/controladores compatibles; VPA no elige instancias GPU.

VPA Off solo genera recomendaciones. La separación de pools sigue las necesidades de equipo, disponibilidad, autorización y capacidad; las taints/etiquetas no constituyen límites de seguridad entre inquilinos.

### 2-4. Ciclo de vida de los nodos (5 min)

Diferencie los valores **predeterminados documentados por AWS: vencimiento predeterminado de 336 h (14 días), gracia predeterminada de terminación de NodeClaim de 24 h y vida útil máxima de instancia administrada de 21 días** con la [guía del ciclo de vida](../eks-auto-mode/07-node-lifecycle.md). El antiguo ejemplo de 720 h (30 días) no es la referencia básica de Auto Mode, ni ninguna vida útil garantiza el tiempo de actividad.

Los presupuestos limitan la tasa de disrupciones voluntarias por drift, nodos vacíos y consolidación; no permiten aplazar todas las expiraciones, interrupciones o reparaciones fuera del horario laboral. Inspeccione los valores almacenados de NodeClaim, los PDB, el tiempo de terminación y la recuperación de la aplicación.

## Pausa (10 min)

## Parte 3: Observabilidad y diagnóstico (25 min)

### 3-1. Observaciones de nodos (8 min)

Use las [pautas operativas](../eks-auto-mode/05-operations.md) para revisar condiciones de NodePool/NodeClass/NodeClaim, eventos y métricas de nodos/cargas de trabajo. No dé por sentado un endpoint de métricas de Karpenter normal ni registros de Deployment para el controlador administrado por AWS. Configure los registros admitidos de los componentes administrados y los publicadores reales de CloudWatch/Prometheus.

Estas alertas básicas usan kube-state-metrics y cubren todo el clúster. Las vistas solo de Auto Mode requieren etiquetas de tipo de cómputo permitidas y una unión correcta. Los nodos eliminados o las series que faltan requieren una investigación independiente de ausencia de datos/historial.

```yaml
groups:
- name: node-health
  rules:
  - alert: NodeNotReady
    expr: kube_node_status_condition{condition="Ready",status="true"} == 0
    for: 5m
  - alert: NodeMemoryPressure
    expr: kube_node_status_condition{condition="MemoryPressure",status="true"} ==
      1
    for: 2m
```

Compare status.resources de NodePool con spec.limits usando las mismas unidades. Se eliminó la relación inventada karpenter_nodeclaims_state/karpenter_nodepool_usage_limit. CloudWatch Events y EventBridge no son dos servicios secuenciales; verifique las fuentes de eventos, reglas, destinos y retrasos reales.

### 3-2. Correlación de señales (8 min)

Use la [guía de observabilidad](../observability/09-observability-optimization.md) y la [guía de Grafana](../observability/grafana/README.md) para distinguir la relación traza-registros, los campos derivados y los exemplars. TraceID no tiene que ser una etiqueta de Loki indexada; evite una cardinalidad alta con campos de registro/metadatos estructurados y consultas.

Verifique ajustes específicos de la versión como tracesToLogsV2, los UID/URL de fuentes de datos, la asignación de etiquetas, el muestreo y la retención. Los exemplars requieren publicadores, recopilación, almacenamiento e interfaz compatibles; una sola opción no crea enlaces a trazas para datos existentes. Prepare un ejemplo real de solicitud correlacionada para la clase.

### 3-3. Escenarios basados en evidencia (9 min)

| Síntoma | Evidencia | Evite conclusiones prematuras |
| --- | --- | --- |
| Pendiente sin un nodo nuevo | Eventos del Pod, PVC, afinidad, taints, condiciones de clase/pool, cuotas/IP/capacidad y errores de API | Suponer siempre falta de capacidad |
| Desapareció un nodo | Eventos de eliminación/interrupción, NodeClaims, registros administrados, EC2/CloudTrail y recuperación | Suponer siempre consolidación u OOM |
| Latencia de respuesta | Distribuciones de errores/latencia, colas, trazas/registros y CPU/RAM/red/almacenamiento | Concluir que una sola traza o una lectura de temperatura demuestra la causa |

CloudTrail muestra acciones de API registradas, no la causa definitiva de todos los fallos de programación. Las condiciones/eventos de Kubernetes son importantes cuando no se realizó ninguna llamada a EC2. No dé a entender que se recuperó telemetría histórica que faltaba.

## Parte 4: IaC/GitOps (10 min)

### 4-1. Límites de IaC (5 min)

Use la [guía de infraestructura](../ops/01-infrastructure-setup.md) para distinguir la configuración del backend compartido de las capas de implementación de red/clúster/plataforma. Separar archivos/estados no garantiza que los cambios de red no puedan afectar a los clústeres. Verifique la configuración de Auto Mode del proveedor/módulo, el bloqueo, las dependencias de salida y el orden de aplicación.

### 4-2. Operaciones de GitOps (5 min)

Compare los permisos, generadores y políticas de sincronización en [Aplicaciones de ArgoCD](../gitops/argocd/02-applications.md) y [ApplicationSets](../gitops/argocd/04-applicationsets.md). La autosincronización, la autorreparación y la poda no equivalen automáticamente a despliegues progresivos seguros. Revise el impacto de eliminar NodePool/NodeClass y quién administra las desviaciones, y compruebe que Progressive Sync esté habilitado y sea compatible con la versión.

## Evaluación y preparación del laboratorio

- [Primeros pasos y límites](../quizzes/eks-auto-mode/01-getting-started-quiz.md)
- [NodePool/NodeClass](../quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
- [Escalado](../quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
- [Spot](../quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
- [Costos](../quizzes/eks-auto-mode/06-cost-management-quiz.md)
- [Cargas de trabajo](../quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
- [Ciclo de vida de los nodos](../quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
- [Operaciones](../quizzes/eks-auto-mode/05-operations-quiz.md)

Prepare comprobaciones de cuenta/clúster, API/imágenes compatibles, telemetría y procedimientos de limpieza, e indique exactamente qué se ejecutó. Consulte la [migración](../eks-auto-mode/09-migration-guide.md) y [experimentos de producción con Spot](../ops/17-spot-production-experiments.md); la inyección de fallos es un laboratorio independiente y acotado que requiere un entorno dedicado, condiciones de detención y evidencia de recuperación.

## Evidencia de revisión

Las comprobaciones abarcan el programa de 120 minutos, los enlaces, el esquema estructural de NodePool y las reglas de alertas de nodos. No se creó ningún clúster, ni se reemplazaron nodos, ejecutaron experimentos de FIS, midieron ahorros ni implementaron backends de observabilidad.

- [Valores predeterminados de NodePool en Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Vida útil máxima de instancia administrada](https://docs.aws.amazon.com/eks/latest/userguide/auto-security.html)
- [Responsabilidades y sistema operativo de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [Registros de componentes administrados](https://docs.aws.amazon.com/eks/latest/userguide/auto-managed-component-logs.html)
- [Configuración de Grafana Tempo](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/)
- [Cardinalidad de etiquetas de Loki](https://grafana.com/docs/loki/latest/get-started/labels/)
