# Optimización de costos de Amazon EKS

> **Alcance de la verificación**: Documentación actual de precios y soporte de AWS; manifiestos de Kubernetes comprobados con la versión 1.36. Seleccione la versión real de EKS y los complementos del catálogo de soporte de AWS.
> **Última actualización**: October 16, 2026

Amazon EKS (Elastic Kubernetes Service) facilita la implementación, administración y escalado de aplicaciones en contenedores, pero es importante administrar los costos de forma eficaz. Este documento cubre diversas estrategias y prácticas recomendadas para optimizar los costos de su clúster de EKS.

Los comandos son ejemplos de configuración, no implementaciones registradas ni ahorros medidos. Verifique la cuenta, la Región, el propietario de los recursos existentes, los requisitos de las cargas de trabajo y las versiones compatibles de las herramientas antes de aplicarlos. Las suposiciones históricas sobre precios que se indican a continuación se separan explícitamente del comportamiento actual del servicio.

## Tabla de contenido

1. [Componentes de costos de EKS](#eks-cost-components)
2. [Principios de FinOps y EKS](#finops-principles-and-eks)
3. [Optimización de costos de cómputo](#compute-cost-optimization)
4. [Optimización de costos de almacenamiento](#storage-cost-optimization)
5. [Optimización de costos de redes](#networking-cost-optimization)
6. [Administración y gobernanza de recursos](#resource-management-and-governance)
7. [Supervisión y análisis de costos](#cost-monitoring-and-analysis)
8. [Prácticas recomendadas para optimizar costos](#cost-optimization-best-practices)

## Componentes de costos de EKS

Los costos en los que se incurre al usar Amazon EKS constan de los siguientes componentes:

![Diagrama que desglosa el costo total de EKS en cinco componentes: plano de control ($0.10/hora), cómputo (instancias EC2, Fargate), almacenamiento (EBS, EFS, S3), redes (transferencia de datos, balanceador de carga, NAT gateway) y otros costos (CloudWatch, ECR y otros servicios de AWS).](../.gitbook/assets/en-eks-07-eks-cost-optimization-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-0.html)

## Principios de FinOps y EKS

FinOps es un marco operativo y una práctica cultural para maximizar el valor empresarial de la tecnología. Los equipos de ingeniería, finanzas y negocio colaboran tomando decisiones oportunas basadas en datos y asumiendo responsabilidad financiera; este capítulo aplica ese enfoque a EKS.

### Principios fundamentales del marco FinOps

La FinOps Foundation destaca la colaboración entre equipos, el valor empresarial en las decisiones, la responsabilidad por el uso, los datos oportunos, precisos y accesibles, la habilitación centralizada y el uso deliberado del modelo de costos variables de la nube. Las prácticas de EKS que se describen a continuación aplican esos principios; no constituyen un marco oficial independiente de seis principios.

<!-- Pending parent diagram repair: see /tmp/eks-cost-optimization-audit/diagram-review.json
![Diagram mapping six FinOps core principles on the left to five EKS implementation methods on the right, showing which implementation method operationalizes each principle, with cost monitoring tools serving both forecasting and real-time decision making.](../.gitbook/assets/en-eks-07-eks-cost-optimization-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-1.html)
-->

### Aplicación de FinOps a EKS

1. **Lograr visibilidad de los costos**
   - Asignación de costos mediante namespaces, etiquetas y anotaciones de Kubernetes
   - Análisis detallado de costos mediante la integración de herramientas como AWS Cost Explorer y Kubecost
   - Análisis de costos por equipo, aplicación y entorno

2. **Implementar un modelo de responsabilidad compartida**
   - Asignación de costos e informes por equipo
   - Establecimiento y seguimiento de objetivos de optimización de costos
   - Incentivos para el ahorro de costos

3. **Automatizar la optimización continua**
   - Implementación de políticas de autoescalado
   - Automatización del uso de instancias Spot
   - Detección de posibles desperdicios y eliminación de recursos solo después de revisar su propietario y retención

4. **Previsión y planificación de costos**
   - Previsión de costos mediante el análisis de patrones de carga de trabajo
   - Uso de Reserved Instances y Savings Plans
   - Detección de anomalías de costos y generación de alertas

### Herramientas y tecnologías FinOps más recientes

1. **Kubecost**: herramienta de supervisión y optimización de costos de Kubernetes
2. **AWS Cost Anomaly Detection**: detección de aumentos anómalos de costos
3. **Karpenter**: aprovisionamiento eficiente de nodos y optimización de costos
4. **Goldilocks**: optimización de solicitudes y límites de recursos
5. **Vertical Pod Autoscaler**: ajuste automático de las solicitudes de recursos de los Pod

### Costo del clúster de EKS

El cargo publicado por soporte de versión es:

- **Soporte estándar**: $0.10 por hora de clúster.
- **Soporte extendido**: **$0.60 en total por hora de clúster** (base de $0.10 + cargo de soporte extendido de $0.50), no un «clúster extendido» independiente a $0.10.

El soporte estándar dura 14 meses desde la publicación de la versión de EKS, seguido de 12 meses de soporte extendido. Consulte el [calendario de versiones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) para conocer las fechas exactas de cada versión y la política de soporte. Los niveles de plano de control aprovisionado, Auto Mode, Hybrid Nodes y EKS Capabilities pueden generar cargos independientes; EC2/Fargate, almacenamiento, redes y observabilidad se cobran por separado. La etiqueta de $0.10 del diagrama general describe únicamente el soporte estándar de versión. Consulte los [precios actuales de EKS](https://aws.amazon.com/eks/pricing/).

### Costo de cómputo

Costo de los nodos de trabajo que se ejecutan en el clúster de EKS:

- **Instancias EC2**: costo de las instancias EC2 que se usan para los grupos de nodos
- **Fargate**: cargos por la configuración y duración de la vCPU/memoria de los Pod aprovisionados, no por la utilización muestreada; incluya los cargos de almacenamiento aplicables

### Costo de almacenamiento

Costo del almacenamiento que se usa en el clúster de EKS:

- **Volúmenes EBS**: costo de los volúmenes EBS que se usan para los volúmenes persistentes
- **EFS**: costo de EFS para los sistemas de archivos compartidos
- **S3**: costo de S3 para el almacenamiento de objetos

### Costo de redes

Costos relacionados con las redes del clúster de EKS:

- **Transferencia de datos**: cargos aplicables por transferencia entre zonas de disponibilidad, entre Regiones y hacia Internet; la dirección y la ruta exactas del servicio son importantes
- **Load Balancer**: costo de los balanceadores de carga que se usan para los servicios
- **NAT Gateway**: costo de NAT gateway para el tráfico saliente de las subredes privadas

### Otros costos

- **CloudWatch**: costo de CloudWatch para la supervisión y el registro
- **ECR**: costo de ECR para el almacenamiento de imágenes de contenedores
- **Otros servicios de AWS**: costo de otros servicios de AWS que se usan con el clúster de EKS

## Optimización de costos de cómputo

El costo de cómputo suele ser el componente más importante del costo de un clúster de EKS. Puede optimizarlo mediante las siguientes estrategias.

![Diagrama que muestra cinco estrategias de optimización de costos de cómputo para EKS: optimización del tipo de instancia, uso de instancias Spot, Savings Plans y Reserved Instances, optimización del autoescalado y comparación de costos de Fargate frente a EC2; para cada estrategia se muestran elementos secundarios como familia, tamaño y generación, MNG, Karpenter y administración de interrupciones, Compute SP, EC2 Instance SP y RI, y CA, Karpenter, HPA y VPA.](../.gitbook/assets/en-eks-07-eks-cost-optimization-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-2.html)

### Selección del tipo de instancia adecuado

Es importante seleccionar el tipo de instancia adecuado para la carga de trabajo:

#### Selección de familia de instancias

Seleccione según las características de la carga de trabajo. Las familias que aparecen a continuación son ejemplos de generaciones anteriores, no recomendaciones de generaciones actuales; compruebe la disponibilidad en la Región, la arquitectura del procesador, las AMI y los precios.

- **Propósito general (T3, M5, M6)**: cargas de trabajo que requieren recursos equilibrados de cómputo, memoria y redes
- **Optimizadas para cómputo (C5, C6)**: cargas de trabajo de cómputo intensivo que requieren procesadores de alto rendimiento
- **Optimizadas para memoria (R5, R6, X1)**: cargas de trabajo con uso intensivo de memoria, como grandes bases de datos en memoria y cachés
- **Optimizadas para almacenamiento (I3, D2)**: cargas de trabajo que requieren un alto rendimiento de E/S de disco
- **Cómputo acelerado (P3, G4, Inf1)**: cargas de trabajo que requieren aceleradores de GPU o de aprendizaje automático

#### Optimización del tamaño de instancia

Seleccione el tamaño de instancia adecuado para los requisitos de la carga de trabajo:

- Las instancias demasiado grandes pueden desperdiciar recursos.
- Las instancias demasiado pequeñas pueden causar problemas de rendimiento.
- Use CloudWatch Container Insights o las métricas de Kubernetes para supervisar el uso real de recursos y seleccionar el tamaño adecuado.

#### Consideraciones sobre la generación de instancias

Compare las generaciones más recientes según sus propias mediciones de carga de trabajo y los precios de la Región. Estos son ejemplos de rutas de migración anteriores; pasar de x86 (`i`) a Graviton (`g`) también requiere imágenes arm64 y dependencias compatibles:

- Use M6i o M6g en lugar de M5
- Use C6i o C6g en lugar de C5
- Use R6i o R6g en lugar de R5

### Uso de instancias Spot

AWS anuncia descuentos Spot de hasta el 90 % frente a On-Demand; los precios reales, la capacidad disponible y la exposición a interrupciones varían. El hecho de que una aplicación no tenga estado no basta para demostrar que tolera interrupciones:

#### Cargas de trabajo adecuadas para instancias Spot

- **Aplicaciones sin estado**: aplicaciones que no almacenan estado
- **Aplicaciones tolerantes a fallos**: aplicaciones que pueden gestionar interrupciones de instancias
- **Trabajos de procesamiento por lotes**: trabajos que se pueden reiniciar si se interrumpen
- **Pipelines de CI/CD**: trabajos de compilación y prueba

#### Uso de instancias Spot en grupos de nodos administrados

Esto crea un grupo de nodos administrado en un clúster existente; no instala Cluster Autoscaler. Revise las subredes privadas, el rol de IAM, la AMI y la diversidad de instancias en la configuración propietaria. Agregue explícitamente la configuración de escalado/IAM a través del propietario del controlador, no mediante permisos amplios de complementos en el rol del nodo.

```bash
eksctl create nodegroup \
  --cluster my-cluster \
  --name my-spot-ng \
  --managed \
  --node-type m5.large \
  --nodes-min 2 \
  --nodes-max 5 \
  --spot
```

#### Aprovisionamiento de instancias Spot con Karpenter

Requisitos previos: Karpenter/CRD instalados, IAM del controlador con alcance limitado, un rol de nodo autorizado, subredes/grupos de seguridad con etiquetas de detección y su cola de interrupciones. Para EKS 1.36, la matriz de compatibilidad actual requiere Karpenter >=1.13. Estos recursos no instalan el controlador. Las listas y los límites de instancias son ejemplos, no un límite de costos. Revise las AMI resueltas: `al2023@latest` es un selector dinámico que puede causar desviaciones o reemplazos; en producción, los cambios deben fijar una versión de alias o un ID de AMI probado.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["spot"]
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64"]
      - key: node.kubernetes.io/instance-type
        operator: In
        values: ["m5.large", "m5.xlarge", "m5.2xlarge"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: spot-class
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: spot-class
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```

#### Administración de interrupciones de instancias Spot

Prácticas recomendadas para administrar interrupciones de instancias Spot:

1. **Use varios tipos de instancia**: distribuya el riesgo de interrupción usando distintos tipos de instancia
2. **Use varias zonas de disponibilidad**: implemente instancias en varias zonas de disponibilidad
3. **Elija un solo responsable de las interrupciones para cada conjunto de nodos**: los grupos de nodos administrados ya gestionan las interrupciones/rebalanceo de Spot. Configure la cola nativa de interrupciones de Karpenter para los nodos de Karpenter; no instale Node Termination Handler en los mismos nodos. Los ASG autoadministrados pueden usar [AWS Node Termination Handler](https://github.com/aws/aws-node-termination-handler) con un modo IMDS o de cola elegido explícitamente y los permisos/conexiones de eventos correspondientes.
4. **Diseñe la recuperación de la aplicación**: no se garantiza que haya capacidad de reemplazo. La terminación ordenada, los reintentos o puntos de control y las réplicas en distintos dominios de fallo deben ajustarse al tiempo disponible antes de la interrupción. Un PDB no puede impedir que EC2 recupere una instancia Spot.

### Savings Plans y Reserved Instances

Para cargas de trabajo predecibles, puede reducir los costos con Savings Plans o Reserved Instances:

#### Compute Savings Plans

Compute Savings Plans ofrecen descuentos de hasta el 66 % sobre las tarifas On-Demand con un compromiso de 1 o 3 años:

- **Flexibilidad**: se aplican independientemente de la familia, el tamaño, el sistema operativo, la tenencia y la Región de la instancia
- **Incluyen EC2, Fargate y Lambda**: se aplican a varios servicios de cómputo

#### EC2 Instance Savings Plans

EC2 Instance Savings Plans ofrecen descuentos de hasta el 72 % para familias de instancias en una Región específica:

- **Flexibilidad moderada**: se aplican a distintos tamaños y sistemas operativos dentro de una familia de instancias en una Región específica
- **Mayor tasa de descuento**: ofrecen una tasa de descuento más alta que Compute Savings Plans

#### Reserved Instances

Actualmente, AWS anuncia ahorros de RI de hasta el **72 %**. Las RI Standard y Convertible tienen reglas distintas de modificación/intercambio; también difiere el alcance Regional y Zonal. Una RI Zonal incluye una reserva de capacidad en su zona de disponibilidad, mientras que una RI Regional no. Las RI son beneficios de facturación aplicados al uso que coincide con sus criterios, no un programador de Kubernetes ni una garantía del mayor descuento.

Savings Plans compromete un gasto elegible por hora durante uno o tres años; las RI comprometen el uso de instancias elegibles. Dimensione los compromisos según la línea base estable después de ajustar correctamente los recursos y revise el riesgo de compromisos no utilizados. Ninguno aplica un descuento adicional al uso Spot, y los máximos anunciados no representan ahorros medidos para este clúster.

### Comparación de costos de Fargate frente a EC2

Al elegir entre Fargate y EC2, tenga en cuenta los costos:

#### Ventajas de Fargate

- **Menor carga operativa**: no es necesario administrar nodos
- **Aprovisionamiento preciso de recursos**: asignación de recursos a nivel de Pod
- **Sin nodos de trabajo inactivos administrados por separado**: los cargos siguen dependiendo de la capacidad y duración de los Pod aprovisionados, incluido el redondeo y el mínimo de facturación

#### Ventajas de EC2

- **Más rentable para cargas de trabajo grandes**: en casos de alta utilización de recursos
- **Más opciones de tipos de instancia**: permite seleccionar tipos de instancia para distintas cargas de trabajo
- **Compatibilidad con instancias Spot**: permite obtener ahorros adicionales usando instancias Spot

#### Ejemplo de comparación de costos

**Suposiciones ilustrativas heredadas (fuente de precios/Región no registrada; no es una cotización ni una prueba de rendimiento actuales)**: aplicación que solicita 2 vCPU y 4 GB de memoria. Los precios unitarios y las operaciones aritméticas originales se conservan a continuación; no incluyen las reservas específicas de EKS ni la sobrecarga de los nodos.

**Costo de Fargate**:
- vCPU: $0.04048 por vCPU-hora × 2 = $0.08096 por hora
- Memoria: $0.004445 por GB-hora × 4 = $0.01778 por hora
- Costo total: $0.09874 por hora

**Costo de EC2 (t3.medium)**:
- On-Demand: $0.0416 por hora
- Spot: ~$0.0125 por hora (suponiendo un descuento del 70 %)

**Corrección de la asignación:** EKS Fargate agrega 256 MB para los componentes de Kubernetes y redondea a una configuración admitida. Con estas suposiciones, las solicitudes de 2 vCPU/4 GB requieren una capacidad aprovisionada de **2 vCPU/5 GB**: `2 × 0.04048 + 5 × 0.004445 = 0.103185 USD/hour` con las mismas tarifas históricas. Es un cálculo aritmético, no una cotización de precios nueva. La facturación de Fargate para Linux comienza cuando se descarga la imagen y tiene un mínimo de un minuto. Una instancia EC2 `t3.medium` tiene una capacidad nominal de 2 vCPU/4 GiB, pero sus recursos asignables son menores después de las reservas del sistema operativo/Kubernetes/DaemonSet; no se puede suponer que sea suficiente para este Pod, y el uso sostenido de CPU puede generar cargos por créditos T3. Compare un plan de capacidad que realmente permita programar la carga de trabajo, incluidos EBS, redes, cargos del clúster, utilización y operaciones. Esta tabla no determina qué servicio equivalente es mejor.

### Optimización del autoescalado

Puede optimizar los costos implementando estrategias de autoescalado eficaces:

#### Cluster Autoscaler

Cluster Autoscaler escala los ASG para los Pod que no se pueden programar y elimina los nodos aptos según los recursos solicitados y las comprobaciones de reprogramación/interrupción, no simplemente porque la CPU medida sea baja. Alinee su versión secundaria de Kubernetes con la del clúster; configure etiquetas de detección en los ASG reales y un rol de IAM dedicado para las cargas de trabajo. Las etiquetas de EKS/grupos de nodos no se propagan automáticamente a todos los recursos subyacentes. Use la [configuración de AWS del proyecto upstream](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/cloudprovider/aws) y las [recomendaciones de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html) para preparar la versión administrada.

Estos valores de chart se convierten en argumentos de CLI. Definir variables de entorno inventadas `CLUSTER_AUTOSCALER_*` no configura esos argumentos, y aplicar sin modificar un ejemplo de `master` no proporciona la configuración de IAM/detección específica del clúster. Los tiempos que aparecen a continuación son parámetros ilustrativos de ajuste; los retrasos más cortos pueden aumentar la rotación.

```yaml
# Values fragment for the upstream cluster-autoscaler Helm chart.
# Merge into the existing release's reviewed values, including workload IAM.
autoDiscovery:
  clusterName: my-cluster
awsRegion: us-west-2
extraArgs:
  expander: least-waste
  scale-down-delay-after-add: 10m
  scale-down-unneeded-time: 10m
  max-node-provision-time: 15m
```

#### Karpenter

Karpenter aprovisiona nodos a partir de las restricciones de NodePool/EC2NodeClass, en lugar de cambiar el tamaño de un ASG fijo. La latencia de aprovisionamiento y el costo dependen de la carga de trabajo y de la capacidad disponible; aquí también se aplican los requisitos previos anteriores del controlador/IAM/AMI. Mantenga separados sus nodos de los ASG administrados por Cluster Autoscaler:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64"]
      - key: node.kubernetes.io/instance-type
        operator: In
        values: ["m5.large", "m5.xlarge", "m5.2xlarge"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default-class
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default-class
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```

Configuración de optimización de costos de Karpenter:

- **disruption.consolidateAfter**: retraso tras agregar o quitar Pod antes de considerar la consolidación, sujeto a la política y las comprobaciones de interrupción (p. ej., `30s`; reemplaza el `ttlSecondsAfterEmpty` heredado)
- **disruption.consolidationPolicy**: política de consolidación de nodos, ya sea `WhenEmpty` (elimina solo nodos vacíos) o `WhenEmptyOrUnderutilized` (también consolida nodos infrautilizados; equivalente al `consolidation.enabled: true` heredado)
- **template.spec.requirements** (`node.kubernetes.io/instance-type`): especifica tipos de instancia rentables

#### Horizontal Pod Autoscaler (HPA)

HPA ajusta automáticamente la cantidad de Pod según la utilización de CPU o métricas personalizadas:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

Los objetivos de utilización de CPU/memoria son porcentajes de las solicitudes y requieren la API de métricas de recursos y que los contenedores pertinentes tengan solicitudes configuradas. Cuando hay varias métricas, HPA elige la mayor cantidad de réplicas deseada; la falta de métricas puede impedir el escalado hacia abajo. La memoria puede no reducirse al agregar réplicas, así que valide el comportamiento de la aplicación. EKS administra los indicadores del controller-manager: configure `spec.behavior.scaleDown.stabilizationWindowSeconds` por HPA en lugar de suponer que puede modificar sus indicadores globales. No cambie automáticamente las mismas solicitudes de CPU/memoria con VPA mientras HPA las use como denominador de utilización.

#### Vertical Pod Autoscaler (VPA)

VPA ajusta automáticamente las solicitudes de CPU y memoria de los Pod para optimizar la utilización de recursos:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: app-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 50m
        memory: 100Mi
      maxAllowed:
        cpu: 1
        memory: 1Gi
```

Este ejemplo usa **Off** para recopilar recomendaciones sin competir con el HPA anterior. Instale primero los componentes/CRD de VPA y las dependencias de métricas.

- **Off**: solo recomendaciones.
- **Initial**: el mecanismo de admisión establece las solicitudes de los Pod recién creados.
- **Recreate**: el actualizador puede desalojar Pod para que los controladores los vuelvan a crear con los recursos recomendados, sujeto a la política de desalojo/PDB.
- **Auto**: alias obsoleto de Recreate; para nuevas configuraciones, elija el modo explícito.
- Los modos in-place requieren una versión compatible de VPA/Kubernetes y sus feature gates documentados. Lea el contrato del modo seleccionado: `InPlaceOrRecreate` puede recurrir al desalojo, mientras que `InPlace` no usa esa alternativa de recreación. Revise los límites, las interrupciones y la demanda máxima antes de habilitar las actualizaciones automáticas.

## Optimización de costos de almacenamiento

El almacenamiento es un componente importante del costo de los clústeres de EKS. Puede optimizar los costos de almacenamiento mediante las siguientes estrategias.

![Diagrama de arquitectura que muestra la optimización de costos de almacenamiento para EKS dividida en optimización de volúmenes EBS (selección del tipo de volumen con migración a gp3, optimización del tamaño del volumen y administración del ciclo de vida del volumen), optimización de costos de EFS (selección del modo de rendimiento, administración del ciclo de vida y optimización de patrones de acceso) y optimización de costos de S3 (optimización de la clase de almacenamiento mediante una política de ciclo de vida y optimización de solicitudes).](../.gitbook/assets/en-eks-07-eks-cost-optimization-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-3.html)

### Optimización de volúmenes EBS

Los volúmenes EBS se usan principalmente para almacenamiento persistente en los clústeres de EKS:

#### Selección del tipo de volumen adecuado

Seleccione el tipo de volumen EBS adecuado para la carga de trabajo:

- **gp3**: SSD de propósito general recomendado para la mayoría de las cargas de trabajo
- **gp2**: SSD de propósito general de generación anterior; se recomienda migrar a gp3
- **io1/io2**: SSD con IOPS aprovisionadas para cargas de trabajo de alto rendimiento
- **st1**: HDD optimizado para rendimiento para cargas de trabajo con uso intensivo de rendimiento
- **sc1**: HDD de bajo costo para datos a los que se accede con poca frecuencia

gp3 separa los precios de tamaño, IOPS y rendimiento; su base de 3,000 IOPS no supera la de todos los volúmenes gp2. Los límites que aparecen a continuación son los actuales para volúmenes generales de Regiones de AWS, sujetos a las proporciones de tamaño/IOPS y a los límites de las instancias. Outposts tiene límites diferentes. Las tarifas de almacenamiento de $0.08/$0.10 se conservan como supuestos ilustrativos sin Región/fecha registrada; obtenga una cotización actual que incluya las IOPS/el rendimiento aprovisionados.

| Tipo de volumen | IOPS de referencia | IOPS máximas | Rendimiento de referencia | Rendimiento máximo | Precio por GB |
|------------|--------------|----------|---------------------|----------------|--------------|
| gp3 | 3,000 | 80,000 | 125 MiB/s | 2,000 MiB/s | $0.08/GB-mes (ilustrativo) |
| gp2 | 3 IOPS/GiB, mínimo 100; los volúmenes pequeños que cumplan los requisitos pueden alcanzar picos | 16,000 | Depende del tamaño/E/S | 250 MiB/s | $0.10/GB-mes (ilustrativo) |

#### Migración a gp3

Esta clase crea volúmenes gp3 nuevos mediante el controlador EBS CSI estándar (`ebs.csi.aws.com`); no migra volúmenes existentes ni cambia el valor predeterminado del clúster. Auto Mode utiliza otro aprovisionador (`ebs.csi.eks.amazonaws.com`) y una ruta de migración de nodo/almacenamiento adecuada. Verifique el controlador instalado, los permisos de IAM/KMS, quién administra la clase existente y la topología. `Retain` conserva el almacenamiento liberado para que el propietario lo revise, pero puede seguir generando cargos:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
```

Migración de un PVC existente a gp3:

1. Obtenga una copia de seguridad o instantánea coherente con la aplicación usando los componentes de instantáneas CSI instalados y verifique que esté lista y que se pueda restaurar.
2. Restaure un PVC **nuevo** usando la clase gp3; un PVC enlazado no cambia de StorageClass en el mismo sitio.
3. Pruebe la restauración y cambie la carga de trabajo durante una transición revisada; conserve el original hasta verificar la recuperación.

Un cambio in-place del tipo de EBS Elastic Volumes puede ser una alternativa para las configuraciones compatibles. Coordínelo con el propietario de CSI/IaC en lugar de crear una desviación de configuración. Consulte la [guía de almacenamiento](04-eks-storage-part1.md).

#### Optimización del tamaño del volumen

Aprovisione solo el tamaño de volumen necesario:

- Los volúmenes sobredimensionados generan costos innecesarios.
- Supervise el uso del sistema de archivos y amplíe los volúmenes compatibles cuando sea necesario. Los volúmenes EBS y los PVC de Kubernetes no se pueden reducir in-place; para reducir la capacidad se necesita un volumen nuevo más pequeño y una migración de datos que tenga en cuenta la aplicación.
- `allowVolumeExpansion` permite solicitudes de expansión compatibles; no supervisa el uso ni cambia automáticamente el tamaño. Cualquier ampliador automático necesita un controlador configurado por separado, límites y manejo de fallos.

#### Administración del ciclo de vida de los volúmenes

Identifique y elimine los volúmenes innecesarios:

- Revise periódicamente los PVC y PV que no se usan.
- La terminación de un Pod no significa que su PVC/PV se pueda descartar. Compruebe la retención de StatefulSet, los consumidores pendientes, las copias de seguridad y la propiedad antes de eliminar una solicitud o un volumen.
- Establezca políticas de recuperación de PV adecuadas (Delete o Retain).

### Optimización de costos de EFS

EFS es útil para cargas de trabajo que requieren acceso compartido entre varios nodos:

#### Selección del modo de rendimiento adecuado

Seleccione el modo de rendimiento de EFS adecuado para la carga de trabajo:

- **Rendimiento Bursting**: adecuado para patrones de acceso intermitente
- **Rendimiento Provisioned**: adecuado para cargas de trabajo que requieren un rendimiento predecible
- **Rendimiento Elastic**: adecuado para cargas de trabajo muy variables

#### Administración del ciclo de vida

Las políticas de ciclo de vida de EFS pueden mover archivos aptos a los que se accede con poca frecuencia a IA/Archive y, de manera opcional, devolverlos al almacenamiento principal al acceder a ellos. Los cargos de acceso, los tamaños/duraciones mínimos facturables, el modo de rendimiento y los patrones de acceso afectan los ahorros. El ejemplo exporta la matriz de políticas existente para revisarla. Edite la regla IA dentro de esa matriz y conserve las entradas obligatorias de Archive/devolución al almacenamiento principal antes de enviar la configuración deseada completa:

```bash
aws efs describe-lifecycle-configuration \
  --file-system-id fs-1234567890abcdef0 \
  --query LifecyclePolicies --output json > efs-lifecycle-policies.json
# Edit the exported array; an IA rule is {"TransitionToIA":"AFTER_30_DAYS"}.
# Preserve required Archive/return-to-primary rules and review the complete array.
aws efs put-lifecycle-configuration \
  --file-system-id fs-1234567890abcdef0 \
  --lifecycle-policies file://efs-lifecycle-policies.json
```

#### Optimización de los patrones de acceso

Optimice los patrones de acceso a EFS para reducir los costos:

- Use archivos más grandes en lugar de archivos pequeños
- Reduzca las operaciones de metadatos
- Use patrones de acceso secuencial

### Optimización de costos de S3

S3 es una opción rentable para almacenar registros, copias de seguridad, contenido estático, etc.:

#### Optimización de la clase de almacenamiento

Seleccione la clase de almacenamiento de S3 adecuada para la carga de trabajo:

- **S3 Standard**: datos a los que se accede con frecuencia
- **S3 Intelligent-Tiering**: datos con patrones de acceso cambiantes
- **S3 Standard-IA**: datos a los que se accede con poca frecuencia
- **S3 One Zone-IA**: datos no críticos a los que se accede con poca frecuencia
- **S3 Glacier**: datos de archivo

#### Política de ciclo de vida

Esta regla ilustrativa transiciona los objetos actuales a los 30/90 días y los vence a los 365 días. Valide la latencia de recuperación, los requisitos de retención/Object Lock, los cargos por transición/solicitudes, las duraciones mínimas de almacenamiento y la exclusión predeterminada de las transiciones de objetos menores de 128 KB en configuraciones nuevas o modificadas. Los buckets con versionado necesitan administración independiente de las versiones no actuales; el vencimiento de la versión actual puede crear un marcador de eliminación mientras los datos antiguos siguen generando cargos. Una llamada a put-bucket-lifecycle-configuration reemplaza la configuración del ciclo de vida del bucket, así que combine/conserve las reglas no relacionadas:

```json
{
  "Rules": [
    {
      "ID": "Move to IA after 30 days, Glacier after 90 days",
      "Status": "Enabled",
      "Filter": {"Prefix": "logs/"},
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

#### Optimización de solicitudes de S3

Optimice los costos de solicitudes de S3:

- Combine objetos pequeños en objetos más grandes
- Reduzca las operaciones LIST innecesarias
- La carga multiparte puede mejorar la transferencia y los reintentos, pero agrega cargos por solicitudes y por almacenamiento de partes incompletas; configure la cancelación/limpieza de las cargas abandonadas. Transfer Acceleration puede generar cargos y es una opción de latencia/rendimiento, no un ahorro automático en el costo de las solicitudes

## Optimización de costos de redes

Los costos de redes pueden ser significativos, especialmente con grandes transferencias de datos. Puede optimizarlos mediante las siguientes estrategias.

<!-- Pending parent diagram repair: see /tmp/eks-cost-optimization-audit/diagram-review.json
![Tree diagram of EKS networking cost optimization branching into data transfer, load balancer, and NAT gateway optimization, each with three tactics such as intra-region communication, AZ-aware routing, compression, load balancer type selection and sharing, idle load balancer removal, NAT gateway sharing, VPC endpoints, and outbound traffic optimization, with the VPC endpoint path emphasized.](../.gitbook/assets/en-eks-07-eks-cost-optimization-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-4.html)
-->

### Optimización de la transferencia de datos

#### Uso de comunicaciones dentro de la Región

Reduzca los costos de transferencia de datos entre Regiones comunicándose dentro de la misma Región siempre que sea posible:

- Ubique el clúster de EKS y los servicios de AWS relacionados en la misma Región
- Reduzca al mínimo la transferencia de datos entre Regiones cuando abarque varias Regiones

#### Enrutamiento consciente de las zonas de disponibilidad

Implemente enrutamiento consciente de las zonas de disponibilidad para reducir los costos de transferencia de datos entre zonas:

- Use el enrutamiento de servicios consciente de la topología
- Prefiera los puntos de conexión locales cuando sea compatible, sin perder la disponibilidad en varias zonas. `trafficDistribution: PreferSameZone` es estable en Kubernetes 1.35+; valide la implementación del clúster/proxy. Es una preferencia, con alternativa cuando no hay puntos de conexión locales disponibles, no una garantía de que no haya tráfico entre zonas. La afinidad de ubicación por sí sola no enruta el tráfico del Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  trafficDistribution: PreferSameZone
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

#### Uso de compresión

Reduzca la cantidad de datos transferidos mediante compresión antes de transferirlos:

- Compresión de respuestas de API
- Compresión de registros y métricas
- Optimización de imágenes y recursos estáticos

### Optimización del Load Balancer

#### Selección del tipo de Load Balancer adecuado

Seleccione el tipo de Load Balancer adecuado para la carga de trabajo:

- **Network Load Balancer (NLB)**: tráfico TCP/UDP cuando se necesita baja latencia
- **Application Load Balancer (ALB)**: tráfico HTTP/HTTPS cuando se necesita enrutamiento basado en rutas
- **Classic Load Balancer (CLB)**: cargas de trabajo heredadas

#### Uso compartido de Load Balancer

Reduzca los costos compartiendo los Load Balancer entre varios servicios:

- Use AWS Load Balancer Controller
- Exponga varios servicios mediante recursos Ingress

Use la [guía de redes](03-eks-networking-part1.md) para instalar el AWS Load Balancer Controller estándar con el chart, la cuenta de servicio/IAM, las subredes y los grupos de seguridad correctos. Reutilice el propietario del controlador existente. Auto Mode tiene otra integración integrada; no suponga que la instalación ni la configuración de clases se aplican a ese modo. Ambos Services de backend deben existir en el namespace de Ingress y exponer el puerto 80; el modo de destino IP requiere que las IP de Pod sean accesibles. Este es un ejemplo de enrutamiento HTTP; el uso público en producción también requiere TLS, DNS y controles de acceso revisados.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shared-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - host: service1.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: service1
            port:
              number: 80
  - host: service2.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: service2
            port:
              number: 80
```

#### Eliminación de Load Balancer inactivos

Identifique y elimine los Load Balancer que no se usan:

- Supervise los Load Balancer sin tráfico
- Elimine los Load Balancer innecesarios de los entornos de prueba o desarrollo

### Optimización de NAT Gateway

NAT gateway genera cargos por hora y por procesamiento de datos:

#### Uso compartido de NAT Gateway

Reduzca los costos compartiendo NAT gateway entre varias subredes:

- Con NAT gateway zonales, las subredes privadas de la misma zona de disponibilidad pueden compartir su gateway local. Evalúe la disponibilidad por zona y el costo fijo por hora.
- Un solo gateway zonal compartido entre varias zonas agrega una dependencia entre zonas y posibles cargos por transferencia; es una compensación deliberada, no un diseño de alta disponibilidad universalmente más económico. Evalúe por separado la opción regional actual de NAT según su modelo documentado de disponibilidad/precios.

#### Uso de VPC endpoints

Compare los cargos de los endpoints con la ruta NAT según el tráfico real. Los gateway endpoints de S3/DynamoDB no tienen cargos adicionales por hora de endpoint ni por procesamiento de datos; los interface endpoints (como ECR/Logs/STS) tienen cargos propios y requieren configuración de DNS/grupos de seguridad. Lo siguiente crea gateway endpoints en tablas de enrutamiento existentes y revisadas; aplique una política de endpoint adecuada. Una ruta de descarga de imágenes de ECR generalmente necesita tanto los interface endpoints `ecr.api`/`ecr.dkr` como acceso a S3, no solo el endpoint de ECR API:

```bash
# Create S3 VPC Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-1234567890abcdef0 \
  --service-name com.amazonaws.us-west-2.s3 \
  --route-table-ids rtb-1234567890abcdef0

# Create DynamoDB VPC Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-1234567890abcdef0 \
  --service-name com.amazonaws.us-west-2.dynamodb \
  --route-table-ids rtb-1234567890abcdef0
```

VPC endpoints de uso común:

- S3
- DynamoDB
- ECR
- CloudWatch Logs
- STS

#### Optimización del tráfico saliente

Optimice el tráfico saliente que pasa por NAT gateway:

- Reduzca las llamadas innecesarias a API externas
- La programación puede reducir la contención, pero los precios normales de NAT/transferencia de datos no tienen un descuento general fuera de las horas pico; reduzca los bytes facturados o la duración aprovisionada
- Use compresión de datos

## Administración y gobernanza de recursos

La administración y gobernanza eficaces de recursos son importantes para controlar los costos del clúster de EKS. Puede administrar los recursos eficazmente con las siguientes estrategias.

![Diagrama de árbol de la administración y gobernanza de recursos de EKS, dividido en optimización de solicitudes y límites de recursos, namespaces y cuotas de recursos, y asignación de costos y etiquetado; cada rama enumera prácticas como establecer solicitudes/límites, separar namespaces con ResourceQuota y LimitRange, y usar etiquetas de recursos, etiquetas de Kubernetes y Kubecost.](../.gitbook/assets/en-eks-07-eks-cost-optimization-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-5.html)

### Optimización de solicitudes y límites de recursos

#### Establecimiento de solicitudes de recursos adecuadas

Establezca solicitudes de recursos que coincidan con los requisitos reales de recursos de la aplicación:

- Las solicitudes demasiado altas desperdician recursos.
- Las solicitudes demasiado bajas pueden causar problemas de rendimiento.
- Use VPA (Vertical Pod Autoscaler) para optimizar las solicitudes de recursos

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
  - name: app
    image: app:latest
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 512Mi
```

#### Establecimiento de límites de recursos

Establezca límites de recursos para evitar que los contenedores usen recursos en exceso:

- Los límites de CPU normalmente aplican estrangulamiento; los límites demasiado bajos pueden perjudicar la latencia incluso cuando el nodo tiene CPU disponible.
- Los límites de memoria se aplican de forma reactiva y pueden provocar la terminación por OOM; no garantizan que el uso nunca supere brevemente un valor. Dimensione las solicitudes/límites según el comportamiento medido de la carga de trabajo, no según una proporción universal.

#### Comprensión de las clases QoS

Comprenda y utilice las clases QoS (Quality of Service) de Kubernetes:

Para la configuración de recursos a nivel de contenedor que se muestra aquí:

- **Guaranteed**: todos los contenedores tienen solicitudes de CPU y memoria distintas de cero, iguales a sus límites correspondientes.
- **Burstable**: se configura alguna solicitud o algún límite de CPU/memoria, pero no se cumplen los criterios de Guaranteed.
- **BestEffort**: ningún contenedor tiene solicitudes ni límites de CPU/memoria.

QoS no es prioridad de Pod ni establece un orden absoluto de desalojo. Cuando hay presión en el nodo, kubelet tiene en cuenta si el uso supera las solicitudes, la prioridad del Pod y el exceso relativo de uso. El desalojo por presión de disco también difiere, ya que QoS de CPU/memoria no clasifica las solicitudes de almacenamiento efímero. Consulte las [reglas QoS actuales](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/) cuando use recursos a nivel de Pod.

### Namespaces y cuotas de recursos

#### Separación basada en namespaces

Use namespaces para separar recursos de forma lógica:

- Cree namespaces por equipo, entorno o aplicación
- Supervise el uso de recursos por namespace

#### Establecimiento de cuotas de recursos

ResourceQuota restringe las solicitudes/límites de recursos admitidos y la cantidad de objetos dentro de un namespace existente; no es un límite de gasto ni un medidor de CPU en tiempo de ejecución. Cree primero el namespace `team-a`. La cuota de CPU/memoria puede requerir solicitudes/límites en los contenedores entrantes, así que coordine los valores predeterminados de LimitRange con las cargas de trabajo:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-quota
  namespace: team-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "20"
    services: "10"
    persistentvolumeclaims: "5"
```

#### Establecimiento de LimitRange

Use LimitRange para establecer límites de recursos predeterminados para los contenedores de un namespace:

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: team-a
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
```

### Asignación de costos y etiquetado

#### Etiquetado de recursos

Aplique etiquetas a los recursos de AWS y active las claves de facturación aptas mediante el responsable de facturación. Una etiqueta del clúster de EKS no se propaga automáticamente a sus instancias EC2, ASG, volúmenes EBS ni Load Balancer. Verifique la cobertura real de las etiquetas y los retrasos del procesamiento de facturación; estos ejemplos explícitos de etiquetado no garantizan una atribución completa de los costos del clúster:

- Etiquete por equipo, proyecto, entorno, centro de costos, etc.
- Implemente una estrategia de etiquetado coherente

```bash
# Tag EKS cluster
aws eks tag-resource \
  --resource-arn arn:aws:eks:us-west-2:123456789012:cluster/my-cluster \
  --tags Team=DevOps,Environment=Production,CostCenter=123456

# Tag EC2 instance
aws ec2 create-tags \
  --resources i-1234567890abcdef0 \
  --tags Key=Team,Value=DevOps Key=Environment,Value=Production Key=CostCenter,Value=123456
```

#### Etiquetas y anotaciones de Kubernetes

Las etiquetas/anotaciones de Kubernetes son un sistema de metadatos independiente. Las herramientas de costos pueden agrupar por las etiquetas de carga de trabajo seleccionadas; las etiquetas de Deployment también deben aparecer en su plantilla de Pod cuando se quiera agrupar a nivel de Pod. Las etiquetas de namespace no se heredan automáticamente en los Pod ni en los recursos de AWS. La asignación de costos divididos de AWS y los atributos de costos de Pod de EKS generados requieren una configuración de facturación independiente:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  labels:
    app: app
    team: team-a
    environment: production
    cost-center: "123456"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
        team: team-a
        environment: production
        cost-center: "123456"
    spec:
      containers:
      - name: app
        image: app:latest
```

#### Uso de Kubecost

Use Kubecost para hacer seguimiento y optimizar los costos de recursos de Kubernetes:

Siga la sección de instalación que aparece a continuación; elija una sola implementación administrada de Kubecost/OpenCost en lugar de instalar recopiladores duplicados. La asignación basada en recursos sigue siendo una estimación hasta que se concilia con el conjunto de datos de facturación y la política acordada de costos compartidos.

Kubecost ofrece las siguientes funciones:

- Análisis de costos por namespace, Deployment, Service y etiqueta
- Recomendaciones para optimizar costos
- Informes de asignación de costos y devolución de cargos

## Supervisión y análisis de costos

Para optimizar los costos de forma eficaz, debe supervisarlos y analizarlos continuamente. Puede supervisar y analizar los costos del clúster de EKS con las siguientes herramientas y estrategias.

![Diagrama de supervisión y análisis de costos de EKS con cuatro ramas: AWS Cost Explorer, Kubecost, CloudWatch Container Insights y un panel de costos personalizado; cada rama se vincula con funciones clave como análisis de costos, detección de anomalías, presupuestos, panel y alertas de Kubecost, supervisión del uso de recursos, información para optimizar, panel de Grafana y puntuación de optimización de costos.](../.gitbook/assets/en-eks-07-eks-cost-optimization-6.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-6.html)

### AWS Cost Explorer

AWS Cost Explorer es una herramienta que ayuda a visualizar, comprender y administrar los costos y el uso de AWS:

#### Análisis de costos

Analice los costos del clúster de EKS con AWS Cost Explorer:

- Análisis de costos por servicio
- Análisis de costos por etiqueta
- Análisis de tendencias de costos a lo largo del tiempo

```bash
# Get cost data using AWS CLI
aws ce get-cost-and-usage \
  --time-period Start=2025-06-01,End=2025-07-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" "AmortizedCost" \
  --group-by Type=DIMENSION,Key=SERVICE Type=TAG,Key=Environment
```

Las fechas de 2025 son ejemplos de sintaxis histórica, no un informe de costos actual; elija un período de facturación UTC disponible con fecha de finalización exclusiva. Respete cualquier `NextPageToken` en lugar de tratar la primera respuesta como completa. Compare las bases de costos por separado; no sume bases distintas ni agregue `UsageQuantity` entre unidades incompatibles. La agrupación por servicio/etiqueta incluye valores sin etiqueta y no se limita automáticamente al clúster.

#### Detección de anomalías de costos

Use AWS Cost Anomaly Detection para detectar aumentos anómalos de costos:

1. Inicie sesión en AWS Management Console
2. Vaya al servicio AWS Cost Management
3. Seleccione «Cost Anomaly Detection»
4. Haga clic en «Create anomaly monitor»
5. Configure el tipo de monitor y las preferencias de notificación

#### Configuración de presupuestos de costos

Este ejemplo de 1,000 USD/80 % crea una notificación de presupuesto mensual real; reemplace la cuenta y el correo electrónico por valores aprobados. Verifique el filtro canónico de etiquetas de Budgets (por ejemplo, `user:Environment$Production`) con su configuración de facturación. El filtro selecciona costos etiquetados de todos los servicios; restringir Service a EKS excluiría EC2, almacenamiento y otros costos del clúster. Los costos compartidos/sin etiquetar también requieren una asignación independiente. Budgets procesa datos de facturación con retraso y no es un límite de gasto estricto. Los presupuestos existentes deben conciliarse con su propietario; aquí no se establece una fecha de vencimiento fija anterior:

```bash
# Create budget using AWS CLI
aws budgets create-budget \
  --account-id 123456789012 \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

budget.json:
```json
{
  "BudgetName": "Tagged Production Workloads",
  "BudgetLimit": {
    "Amount": "1000",
    "Unit": "USD"
  },
  "BudgetType": "COST",
  "CostFilters": {
    "TagKeyValue": [
      "user:Environment$Production"
    ]
  },
  "TimeUnit": "MONTHLY"
}
```

notifications.json:
```json
[
  {
    "Notification": {
      "ComparisonOperator": "GREATER_THAN",
      "NotificationType": "ACTUAL",
      "Threshold": 80,
      "ThresholdType": "PERCENTAGE"
    },
    "Subscribers": [
      {
        "Address": "email@example.com",
        "SubscriptionType": "EMAIL"
      }
    ]
  }
]
```

### Kubecost

Kubecost es una herramienta dedicada a supervisar y optimizar los costos de los clústeres de Kubernetes:

#### Instalación de Kubecost

El chart/la aplicación verificados corresponden a la versión **3.3.1** del repositorio actual que se indica a continuación. Kubecost 3.x usa ClickHouse y recopilación directa de finops-agent; no reutilice una instalación de `cost-analyzer` de 2.x ni sus valores de Prometheus/node-exporter incluidos. Antes de aplicarlos, revise las licencias, la compatibilidad con Kubernetes, las clases de almacenamiento/el tamaño de PVC, el ID del clúster, la recopilación de redes y el control de acceso en la [documentación del chart](https://github.com/kubecost/cost-analyzer-helm-chart). Para una versión 2.x existente, siga la migración documentada; esto no es un procedimiento de actualización in-place. No se afirma que haya una instalación activa ni que esté lista para producción. La [guía de la plataforma FinOps](../ops/13-finops-cost-platform.md) también cubre OpenCost y la conciliación de facturación.

```bash
helm repo add kubecost https://kubecost.github.io/kubecost/
helm repo update kubecost
helm show values kubecost/kubecost --version 3.3.1 > kubecost-values.yaml
# Edit this file for the reviewed cluster ID, storage, license, and collection settings.
helm template kubecost kubecost/kubecost --version 3.3.1 \
  --namespace kubecost -f kubecost-values.yaml > kubecost-rendered.yaml
# Install a NEW release only after reviewing the rendered resources and prerequisites.
helm install kubecost kubecost/kubecost --version 3.3.1 \
  --namespace kubecost --create-namespace -f kubecost-values.yaml
```

#### Panel de Kubecost

El panel de Kubecost proporciona la siguiente información:

- Costo por namespace, Deployment, Service y nodo
- Eficiencia y utilización de recursos
- Recomendaciones para optimizar costos
- Informes de asignación de costos y devolución de cargos

#### Alertas de Kubecost

Use el mecanismo de alertas documentado para la edición/versión instalada de Kubecost y configure explícitamente los destinatarios, las credenciales, el período del presupuesto, la agregación y la entrega. Un ConfigMap arbitrario `cost-analyzer-alerts` con `alerts.json` no se consume automáticamente, y el ejemplo anterior no establecía un esquema o montaje válido. El ejemplo de AWS Budgets anterior es una alerta de facturación independiente y concreta; la [guía de FinOps](../ops/13-finops-cost-platform.md) proporciona un flujo de trabajo explícito para informes de asignación. Valide la entrega con una prueba sintética antes de depender de las alertas y supervise tanto los datos ausentes/obsoletos como los incumplimientos de umbrales.

### CloudWatch Container Insights

Use CloudWatch Container Insights para supervisar el uso de recursos del clúster de EKS:

#### Habilitación de Container Insights

Container Insights es telemetría de nodos/cargas de trabajo recopilada por el agente de CloudWatch o el complemento de observabilidad; `containerinsights` no es un tipo de registro del plano de control de EKS para `eksctl utils update-cluster-logging`. Siga la [guía de supervisión](06-eks-monitoring-logging.md) para seleccionar el complemento compatible, la asociación de IAM, la configuración y la ruta de recopilación específica de la plataforma. Mantenga un solo responsable del recopilador y verifique la entrega real de métricas/registros. La telemetría del complemento/agente puede generar cargos.

#### Supervisión del uso de recursos

El panel de CloudWatch permite supervisar las siguientes métricas:

- Uso de CPU y memoria
- E/S de disco y red
- Cantidad de reinicios de contenedores
- Estado de los nodos

#### Información para optimizar costos

Analice los datos de CloudWatch Container Insights para identificar oportunidades de optimización de costos:

- Identifique los recursos sobredimensionados
- Identifique los nodos con baja utilización de recursos
- Analice las diferencias entre las solicitudes de recursos y el uso real

### Panel de costos personalizado

Puede crear paneles de costos personalizados para supervisar de forma integral los costos del clúster de EKS:

#### Panel de Grafana

Cree paneles de costos personalizados con Prometheus y Grafana:

1. Recopile métricas de uso de recursos en Prometheus
2. Cree un panel de costos en Grafana
3. Use un pipeline de datos de facturación autenticado e implementado por separado, o una fuente de datos compatible con los resultados de Cost Explorer/CUR; las métricas de uso de Prometheus no se convierten en datos reales de facturación por agregar un panel. No exponga credenciales de facturación en el JSON del panel del navegador

#### Puntuación de optimización de costos

Realice seguimiento de estos indicadores por separado, con fórmulas, cobertura y períodos de tiempo documentados. No existe una puntuación universal de optimización de costos y ninguno de estos índices, por sí solo, demuestra desperdicio ni ahorro monetario:

- Relación entre solicitud de recursos y uso
- Utilización de nodos
- Relación de uso de instancias Spot
- Relación de recursos inactivos

## Prácticas recomendadas para optimizar costos

Veamos las prácticas recomendadas para optimizar los costos del clúster de EKS.

![Diagrama de prácticas recomendadas para optimizar costos de EKS, dividido en prácticas generales, optimización específica de cargas de trabajo y optimización de costos para servicios financieros; bajo las prácticas generales se muestra un ciclo continuo de optimización de costos: medir, analizar, optimizar, supervisar e iterar.](../.gitbook/assets/en-eks-07-eks-cost-optimization-7.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-7.html)

### Prácticas recomendadas generales

#### Optimización continua de costos

La optimización de costos es un proceso continuo, no una tarea que se realiza una sola vez:

1. **Medir**: mida los costos actuales y el uso de recursos
2. **Analizar**: analice los factores que generan costos y las oportunidades de optimización
3. **Optimizar**: implemente estrategias de optimización de costos
4. **Supervisar**: supervise los resultados y ajuste según sea necesario
5. **Iterar**: repita el proceso

#### Desarrollo de una cultura consciente de los costos

Desarrolle una cultura consciente de los costos dentro de la organización:

- Proporcione a los equipos visibilidad de los costos
- Establezca objetivos de optimización de costos
- Reconozca y recompense los logros en la optimización de costos
- Comparta prácticas recomendadas para optimizar costos

#### Uso de automatización

Use la automatización para optimizar los costos:

- Implemente el autoescalado
- Aprovisione recursos según el uso
- Automatice la detección de anomalías de costos y las alertas
- Identifique automáticamente posibles candidatos; elimínelos solo después de comprobar la propiedad, la retención, las dependencias y la recuperación

### Optimización específica de cargas de trabajo

#### Entornos de desarrollo y prueba

Optimice los costos de los entornos de desarrollo y prueba:

- Apague automáticamente los entornos cuando no se usen
- Use instancias Spot
- Establezca límites de recursos
- Considere el uso de entornos compartidos

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dev-app-scaler
  namespace: dev
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: dev-app-scaler
  namespace: dev
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  resourceNames: ["dev-app"]
  verbs: ["get"]
- apiGroups: ["apps"]
  resources: ["deployments/scale"]
  resourceNames: ["dev-app"]
  verbs: ["get", "patch", "update"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-app-scaler
  namespace: dev
subjects:
- kind: ServiceAccount
  name: dev-app-scaler
  namespace: dev
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: dev-app-scaler
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: dev-app-shutdown
  namespace: dev
spec:
  suspend: true
  schedule: "0 20 * * 1-5"
  timeZone: Etc/UTC
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 1800
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 120
      template:
        spec:
          serviceAccountName: dev-app-scaler
          restartPolicy: Never
          securityContext:
            runAsNonRoot: true
            runAsUser: 65532
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: kubectl
            image: registry.k8s.io/kubectl:v1.36.2
            command: ["kubectl"]
            args: ["scale", "deployment/dev-app", "--namespace=dev", "--current-replicas=3", "--replicas=0"]
            env:
            - name: HOME
              value: /tmp
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop: ["ALL"]
            resources:
              requests:
                cpu: 10m
                memory: 32Mi
              limits:
                memory: 128Mi
            volumeMounts:
            - name: tmp
              mountPath: /tmp
          volumes:
          - name: tmp
            emptyDir: {}
```

El CronJob está **suspendido de forma predeterminada**, apunta solo al Deployment existente `dev/dev-app` y espera tres réplicas. Use una versión de kubectl dentro del desfase de versiones admitido por el servidor. Acuerde el horario UTC y un procedimiento de restauración antes de habilitarlo; ajuste deliberadamente el nombre y la condición previa. Si HPA o GitOps administra las réplicas, coordine el horario con ese propietario en lugar de competir con él. Reducir directamente el escalado de Deployment no usa la admisión de desalojo de PDB; reserve esta acción para el apagado de desarrollo aprobado. Detener los Pod no detiene el cargo del plano de control de EKS, el almacenamiento retenido ni los nodos que no pueden reducirse.

#### Cargas de trabajo por lotes

Optimice los costos de las cargas de trabajo por lotes:

- Use instancias Spot
- Programe dentro de los plazos del trabajo y según la disponibilidad de capacidad; no hay un descuento general por hora del día para el cómputo On-Demand
- Optimice las solicitudes de recursos
- Libere los recursos cuando finalicen los trabajos

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: batch-job
spec:
  template:
    spec:
      nodeSelector:
        eks.amazonaws.com/capacityType: SPOT
      containers:
      - name: batch-processor
        image: batch-processor:latest
        resources:
          requests:
            cpu: 2
            memory: 4Gi
          limits:
            cpu: 4
            memory: 8Gi
      restartPolicy: Never
  backoffLimit: 4
```

Este Job selecciona **nodos Spot de grupos de nodos administrados**. Karpenter usa `karpenter.sh/capacity-type: spot`; seleccione la etiqueta que realmente esté presente en los nodos previstos. La imagen de la aplicación es un marcador de posición. Implemente reintentos/puntos de control idempotentes y asegúrese de tolerar las taints de los nodos. La finalización del Job/TTL limpia los objetos de Kubernetes, pero no necesariamente los PVC, los volúmenes ni los nodos facturables.

#### Aplicaciones web

Optimice los costos de las aplicaciones web:

- Implemente el autoescalado
- Use una CDN para reducir el tráfico
- Implemente una estrategia de almacenamiento en caché
- Considere una arquitectura sin servidor

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### Cargas de trabajo de bases de datos

Optimice los costos de las cargas de trabajo de bases de datos:

- Seleccione el tipo de instancia adecuado
- Configure el escalado automático del almacenamiento
- Considere el uso de réplicas de lectura
- Considere agregar una capa de almacenamiento en caché

### Optimización de costos para servicios financieros

Estrategias adicionales de optimización de costos que debe tener en cuenta al usar EKS en el sector de servicios financieros:

#### Administración de costos de cumplimiento normativo

Optimice los costos mientras cumple los requisitos normativos:

- Aprovisione los recursos mínimos necesarios para cumplir los requisitos normativos
- Reduzca los costos operativos mediante la automatización del cumplimiento
- Separe los entornos regulados y no regulados

#### Equilibrio entre alta disponibilidad y costos

Mantenga el equilibrio entre los requisitos de alta disponibilidad y los costos:

- Implemente en varias zonas de disponibilidad las cargas de trabajo críticas
- Considere una implementación en una sola zona de disponibilidad para las cargas de trabajo no críticas
- Implemente un enfoque rentable para los entornos de recuperación ante desastres

#### Equilibrio entre los requisitos de seguridad y los costos

Mantenga el equilibrio entre los requisitos de seguridad y los costos:

- Implemente controles de seguridad basados en el riesgo
- Reduzca los costos operativos mediante la automatización de la seguridad
- Seleccione herramientas y servicios de seguridad rentables

## Conclusión

Optimizar eficazmente los costos de un clúster de Amazon EKS requiere un enfoque integral que abarque cómputo, almacenamiento, redes y costos operativos. Evalúe cada cambio con respecto a la facturación medida y los SLO de la carga de trabajo; no se garantizan los ahorros ni que se mantengan el rendimiento y la estabilidad.

Puntos clave:

1. **Componentes de costos de EKS**: costo del clúster de EKS, costo de cómputo, costo de almacenamiento, costo de redes y otros costos
2. **Optimización de costos de cómputo**: selección de tipos de instancia adecuados, uso de instancias Spot, uso de Savings Plans y Reserved Instances, optimización del autoescalado
3. **Optimización de costos de almacenamiento**: optimización de volúmenes EBS, optimización de costos de EFS y optimización de costos de S3
4. **Optimización de costos de redes**: optimización de la transferencia de datos, optimización del Load Balancer y optimización de NAT gateway
5. **Administración y gobernanza de recursos**: optimización de solicitudes y límites de recursos, namespaces y cuotas de recursos, asignación de costos y etiquetado
6. **Supervisión y análisis de costos**: AWS Cost Explorer, Kubecost, CloudWatch Container Insights y paneles de costos personalizados
7. **Prácticas recomendadas para optimizar costos**: prácticas recomendadas generales, optimización específica de cargas de trabajo y optimización de costos para servicios financieros

La optimización de costos es un proceso continuo; debe revisar y ajustar periódicamente las estrategias de optimización a medida que evolucionan el clúster y las cargas de trabajo.

## Referencias

- [Precios de Amazon EKS](https://aws.amazon.com/eks/pricing/)
- [Recursos de optimización de costos de AWS](https://aws.amazon.com/aws-cost-management/)
- [Administración de recursos de Kubernetes](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [AWS Well-Architected Framework: pilar de optimización de costos](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)
- [Documentación de Kubecost](https://www.kubecost.com/kubernetes-cost-optimization/kubernetes-cost-optimization-best-practices/)
- [Prácticas recomendadas de EKS: optimización de costos](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt.html)

- [Principios de FinOps](https://www.finops.org/framework/principles/)
- [Compatibilidad de Karpenter](https://karpenter.sh/docs/upgrading/compatibility/)
- [Asignación de Fargate en EKS](https://docs.aws.amazon.com/eks/latest/userguide/fargate-pod-configuration.html)
- [Límites de EBS gp3](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [NAT gateway regionales](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateways-regional.html)

## Cuestionario

Para comprobar lo que ha aprendido en este capítulo, intente el [cuestionario del tema](../quizzes/eks/07-eks-cost-optimization-quiz.md).
