# Optimización de costos de Amazon EKS

> **Alcance de la verificación**: documentación actual de precios y soporte de AWS; manifiestos de Kubernetes comprobados con la versión 1.36. Seleccione la versión real de EKS y los complementos en el catálogo de soporte de AWS.
> **Última actualización**: 16 de octubre de 2026

Amazon EKS (Elastic Kubernetes Service) facilita la implementación, administración y escalado de aplicaciones en contenedores, pero es importante gestionar los costos de manera eficaz. Este documento abarca diversas estrategias y prácticas recomendadas para optimizar los costos de su clúster de EKS.

Los comandos son ejemplos de configuración, no implementaciones registradas ni ahorros medidos. Antes de aplicarlos, verifique la cuenta, la región, el propietario de los recursos existentes, los requisitos de las cargas de trabajo y las versiones de las herramientas compatibles. Las suposiciones históricas sobre precios que aparecen a continuación se distinguen explícitamente del comportamiento actual del servicio.

## Tabla de contenido

1. [Componentes de los costos de EKS](#eks-cost-components)
2. [Principios de FinOps y EKS](#finops-principles-and-eks)
3. [Optimización de costos de cómputo](#compute-cost-optimization)
4. [Optimización de costos de almacenamiento](#storage-cost-optimization)
5. [Optimización de costos de redes](#networking-cost-optimization)
6. [Administración y gobernanza de recursos](#resource-management-and-governance)
7. [Supervisión y análisis de costos](#cost-monitoring-and-analysis)
8. [Prácticas recomendadas para optimizar costos](#cost-optimization-best-practices)

## Componentes de los costos de EKS

Los costos de usar Amazon EKS constan de los siguientes componentes:

![Diagrama que desglosa el costo total de EKS en cinco componentes: plano de control ($0.10/hora), cómputo (instancias EC2, Fargate), almacenamiento (EBS, EFS, S3), redes (transferencia de datos, balanceador de carga, NAT gateway) y otros costos (CloudWatch, ECR, otros servicios de AWS).](../.gitbook/assets/en-eks-07-eks-cost-optimization-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-0.html)

## Principios de FinOps y EKS

FinOps es un marco operativo y una práctica cultural para maximizar el valor empresarial de la tecnología. Los equipos de ingeniería, finanzas y negocios colaboran tomando decisiones oportunas basadas en datos y asumiendo responsabilidad financiera; este capítulo aplica ese enfoque a EKS.

### Principios fundamentales del marco de FinOps

La FinOps Foundation hace hincapié en la colaboración entre equipos, el valor empresarial en la toma de decisiones, la responsabilidad por el uso, los datos oportunos, precisos y accesibles, la habilitación centralizada y el uso deliberado del modelo de costos variables de la nube. Las prácticas de EKS que se describen a continuación aplican esos principios; no constituyen un marco oficial aparte de seis principios.

<!-- Pending parent diagram repair: see /tmp/eks-cost-optimization-audit/diagram-review.json
![Diagram mapping six FinOps core principles on the left to five EKS implementation methods on the right, showing which implementation method operationalizes each principle, with cost monitoring tools serving both forecasting and real-time decision making.](../.gitbook/assets/en-eks-07-eks-cost-optimization-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-1.html)
-->

### Aplicación de FinOps a EKS

1. **Lograr visibilidad de los costos**
   - Asignar costos mediante namespaces, etiquetas y anotaciones de Kubernetes
   - Realizar análisis detallados de costos mediante la integración de herramientas como AWS Cost Explorer y Kubecost
   - Analizar los costos por equipo, aplicación y entorno

2. **Implementar un modelo de responsabilidad compartida**
   - Asignar costos y elaborar informes por equipo
   - Establecer y hacer seguimiento de los objetivos de optimización de costos
   - Ofrecer incentivos por reducir costos

3. **Automatizar la optimización continua**
   - Implementar políticas de escalado automático
   - Automatizar el uso de instancias Spot
   - Detectar candidatos al desperdicio y eliminar recursos solo después de revisar con el propietario su retención

4. **Previsión y planificación de costos**
   - Prever los costos mediante el análisis de los patrones de las cargas de trabajo
   - Utilizar Reserved Instances y Savings Plans
   - Detectar anomalías en los costos y generar alertas

### Herramientas y tecnologías FinOps más recientes

1. **Kubecost**: herramienta de supervisión y optimización de costos de Kubernetes
2. **AWS Cost Anomaly Detection**: detección de aumentos anómalos en los costos
3. **Karpenter**: aprovisionamiento eficiente de nodos y optimización de costos
4. **Goldilocks**: optimización de solicitudes y límites de recursos
5. **Vertical Pod Autoscaler**: ajuste automático de las solicitudes de recursos de los Pod

### Costo del clúster de EKS

El cargo publicado por soporte de versiones es:

- **Soporte estándar**: $0.10 por hora de clúster.
- **Soporte extendido**: **$0.60 en total por hora de clúster** (tarifa base de $0.10 + cargo de $0.50 por soporte extendido); no se trata de un «clúster extendido» aparte a $0.10.

El soporte estándar dura 14 meses a partir del lanzamiento de la versión de EKS, seguido de 12 meses de soporte extendido. Consulte el [calendario de lanzamientos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) para conocer las fechas exactas de cada versión y la política de soporte. Los niveles Provisioned Control Plane, Auto Mode, Hybrid Nodes y EKS Capabilities pueden generar cargos aparte; EC2/Fargate, almacenamiento, redes y observabilidad también se cobran por separado. La etiqueta de $0.10 del diagrama general representa únicamente el soporte estándar de versiones. Consulte los [precios actuales de EKS](https://aws.amazon.com/eks/pricing/).

### Costo de cómputo

Costo de los nodos de trabajo que se ejecutan en el clúster de EKS:

- **Instancias EC2**: costo de las instancias EC2 utilizadas en los grupos de nodos
- **Fargate**: cargos por las configuraciones de vCPU/memoria aprovisionadas para los Pod y su duración, no por la utilización medida en muestras; incluya los cargos de almacenamiento correspondientes

### Costo de almacenamiento

Costo del almacenamiento utilizado en el clúster de EKS:

- **Volúmenes EBS**: costo de los volúmenes EBS utilizados para los volúmenes persistentes
- **EFS**: costo de EFS utilizado para sistemas de archivos compartidos
- **S3**: costo de S3 utilizado para almacenamiento de objetos

### Costo de redes

Costos relacionados con las redes del clúster de EKS:

- **Transferencia de datos**: cargos aplicables por transferencia entre zonas de disponibilidad, regiones e Internet; la dirección y la ruta exactas del servicio son importantes
- **Balanceador de carga**: costo de los balanceadores de carga utilizados para los servicios
- **NAT gateway**: costo del NAT gateway para el tráfico saliente de las subredes privadas

### Otros costos

- **CloudWatch**: costo de CloudWatch utilizado para supervisión y registro
- **ECR**: costo de ECR utilizado para almacenar imágenes de contenedor
- **Otros servicios de AWS**: costo de otros servicios de AWS utilizados con el clúster de EKS

## Optimización de costos de cómputo

El cómputo suele ser el componente de mayor costo de un clúster de EKS. Puede optimizar los costos de cómputo mediante las siguientes estrategias.

![Diagrama en el que la optimización de costos de cómputo para EKS se divide en cinco estrategias: optimización del tipo de instancia, uso de instancias Spot, Savings Plans y Reserved Instances, optimización del escalado automático y comparación de costos entre Fargate y EC2; cada estrategia incluye subelementos como familia, tamaño y generación, MNG, Karpenter y gestión de interrupciones, Compute SP, EC2 Instance SP y RI, y CA, Karpenter, HPA y VPA.](../.gitbook/assets/en-eks-07-eks-cost-optimization-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-2.html)

### Selección del tipo de instancia adecuado

Es importante seleccionar el tipo de instancia adecuado para la carga de trabajo:

#### Selección de la familia de instancias

Seleccione la familia según las características de la carga de trabajo. Las familias que se indican a continuación son ejemplos de generaciones anteriores, no recomendaciones para la generación actual; compruebe la disponibilidad en la región, la arquitectura del procesador, las AMI y los precios.

- **Propósito general (T3, M5, M6)**: cargas de trabajo que requieren un equilibrio entre recursos de cómputo, memoria y redes
- **Optimizada para cómputo (C5, C6)**: cargas de trabajo con gran uso de cómputo que requieren procesadores de alto rendimiento
- **Optimizada para memoria (R5, R6, X1)**: cargas de trabajo con gran uso de memoria, como bases de datos grandes en memoria y cachés
- **Optimizada para almacenamiento (I3, D2)**: cargas de trabajo que requieren un alto nivel de E/S de disco
- **Cómputo acelerado (P3, G4, Inf1)**: cargas de trabajo que requieren GPU o aceleradores de aprendizaje automático

#### Optimización del tamaño de las instancias

Seleccione el tamaño de instancia adecuado según las necesidades de la carga de trabajo:

- Las instancias demasiado grandes pueden desperdiciar recursos.
- Las instancias demasiado pequeñas pueden provocar problemas de rendimiento.
- Use CloudWatch Container Insights o las métricas de Kubernetes para supervisar el uso real de los recursos y seleccionar el tamaño adecuado.

#### Consideración de la generación de instancia

Compare las generaciones más recientes con las mediciones de sus propias cargas de trabajo y los precios regionales. Estos son ejemplos de rutas de migración anteriores; migrar de x86 (`i`) a Graviton (`g`) también requiere imágenes arm64 y dependencias compatibles:

- Use M6i o M6g en lugar de M5
- Use C6i o C6g en lugar de C5
- Use R6i o R6g en lugar de R5

### Uso de instancias Spot

AWS anuncia descuentos de Spot de hasta el 90 % en comparación con On-Demand; los precios reales, la capacidad disponible y la exposición a interrupciones varían. El hecho de que una aplicación no tenga estado no demuestra por sí solo que tolere interrupciones:

#### Cargas de trabajo adecuadas para instancias Spot

- **Aplicaciones sin estado**: aplicaciones que no almacenan estado
- **Aplicaciones tolerantes a fallos**: aplicaciones que pueden soportar interrupciones de instancias
- **Trabajos de procesamiento por lotes**: trabajos que pueden reiniciarse si se interrumpen
- **Procesos de CI/CD**: trabajos de compilación y pruebas

#### Uso de instancias Spot en grupos de nodos administrados

Esto crea un grupo de nodos administrado en un clúster existente; no instala Cluster Autoscaler. Revise las subredes privadas, el rol de IAM, la AMI y la diversidad de instancias en la configuración responsable. Agregue configuración explícita de escalado/IAM mediante el propietario del controlador, no mediante permisos amplios de complementos en el rol del nodo.

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

Requisitos previos: Karpenter/CRD instalados, IAM del controlador con alcance limitado, un rol de nodo autorizado, subredes/grupos de seguridad con etiquetas de detección y su cola de interrupciones. Para EKS 1.36, la matriz de compatibilidad actual requiere Karpenter >=1.13. Estos recursos no instalan el controlador. Las listas de instancias y los límites son ejemplos, no un tope de costos. Revise las AMI resueltas: `al2023@latest` es un selector dinámico que puede causar desviaciones o reemplazos; los cambios en producción deben fijar una versión de alias o un ID de AMI probados.

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

#### Gestión de interrupciones de instancias Spot

Prácticas recomendadas para gestionar las interrupciones de instancias Spot:

1. **Use varios tipos de instancia**: distribuya el riesgo de interrupción utilizando distintos tipos de instancia
2. **Use varias zonas de disponibilidad**: implemente instancias en varias zonas de disponibilidad
3. **Elija un responsable de las interrupciones para cada conjunto de nodos**: los grupos de nodos administrados ya gestionan las interrupciones y el reequilibrio de Spot. Configure la cola de interrupciones nativa de Karpenter para los nodos de Karpenter; no instale Node Termination Handler en los mismos nodos. Los ASG autoadministrados pueden usar [AWS Node Termination Handler](https://github.com/aws/aws-node-termination-handler) con un modo IMDS o de cola elegido explícitamente y los permisos/conexiones de eventos correspondientes.
4. **Diseñe la recuperación de la aplicación**: la capacidad de reemplazo no está garantizada. La terminación ordenada, los reintentos y los puntos de control, así como las réplicas distribuidas entre dominios de fallo, deben ajustarse a la ventana de interrupción disponible. Un PDB no puede impedir que EC2 recupere una instancia Spot.

### Savings Plans y Reserved Instances

Para cargas de trabajo previsibles, puede reducir los costos usando Savings Plans o Reserved Instances:

#### Compute Savings Plans

Compute Savings Plans ofrecen descuentos de hasta el 66 % sobre las tarifas On-Demand con un compromiso de 1 o 3 años:

- **Flexibilidad**: se aplican independientemente de la familia y el tamaño de la instancia, el sistema operativo, la tenencia y la región
- **Incluyen EC2, Fargate y Lambda**: se aplican a varios servicios de cómputo

#### EC2 Instance Savings Plans

EC2 Instance Savings Plans ofrecen descuentos de hasta el 72 % para familias de instancias en una región específica:

- **Flexibilidad moderada**: se aplican a todos los tamaños y sistemas operativos de una familia de instancias en una región específica
- **Mayor descuento**: ofrecen un descuento mayor que Compute Savings Plans

#### Reserved Instances

AWS anuncia actualmente ahorros de RI de hasta el **72 %**. Las RI Standard y Convertible tienen distintas reglas de modificación/intercambio; el alcance Regional y Zonal también varía. Una RI Zonal incluye una reserva de capacidad en su zona de disponibilidad, mientras que una RI Regional no. Las RI son beneficios de facturación que se aplican al uso coincidente, no un planificador de Kubernetes ni una garantía del mayor descuento.

Savings Plans comprometen un gasto elegible por hora durante uno o tres años; las RI comprometen el uso de instancias elegibles. Dimensione los compromisos a partir de la base estable una vez ajustado el tamaño y revise el riesgo de compromisos sin utilizar. Ninguno aplica un descuento adicional al uso de Spot, y los máximos anunciados no son ahorros medidos para este clúster.

### Comparación de costos entre Fargate y EC2

Al elegir entre Fargate y EC2, tenga en cuenta los costos:

#### Ventajas de Fargate

- **Menos carga operativa**: no es necesario administrar nodos
- **Aprovisionamiento preciso de recursos**: asignación de recursos a nivel de Pod
- **No requiere administrar por separado nodos de trabajo inactivos**: los cargos siguen dependiendo de la capacidad aprovisionada para los Pod y de su duración, incluidos el redondeo y el mínimo de facturación

#### Ventajas de EC2

- **Más económico para cargas de trabajo grandes**: en casos de alta utilización de recursos
- **Más opciones de tipos de instancia**: se pueden seleccionar tipos de instancia para distintas cargas de trabajo
- **Compatibilidad con instancias Spot**: es posible obtener ahorros adicionales utilizando instancias Spot

#### Ejemplo de comparación de costos

**Supuestos ilustrativos heredados (no se registraron la fuente del precio ni la región; no es una cotización ni una prueba comparativa actual)**: aplicación que solicita 2 vCPU y 4 GB de memoria. A continuación se conservan los precios unitarios y los cálculos originales; no incluyen reservas específicas de EKS ni la sobrecarga de los nodos.

**Costo de Fargate**:
- vCPU: $0.04048 por vCPU-hora × 2 = $0.08096 por hora
- Memoria: $0.004445 por GB-hora × 4 = $0.01778 por hora
- Costo total: $0.09874 por hora

**Costo de EC2 (t3.medium)**:
- On-Demand: $0.0416 por hora
- Spot: ~$0.0125 por hora (suponiendo un descuento del 70 %)

**Corrección de la asignación:** EKS Fargate agrega 256 MB para los componentes de Kubernetes y redondea a una configuración compatible. Con estos supuestos, las solicitudes de 2 vCPU/4 GB requieren **2 vCPU/5 GB** de capacidad aprovisionada: `2 × 0.04048 + 5 × 0.004445 = 0.103185 USD/hour`, utilizando las mismas tarifas históricas. Esto es un cálculo, no una nueva cotización. La facturación de Fargate para Linux comienza con la descarga de la imagen y tiene un mínimo de un minuto. Una instancia EC2 `t3.medium` tiene una capacidad nominal de 2 vCPU/4 GiB, pero los recursos asignables son menores después de las reservas del sistema operativo, Kubernetes y los DaemonSet; no se puede suponer que admita este Pod, y un uso sostenido de CPU puede generar cargos por créditos T3. Compare un plan de capacidad que realmente pueda programar la carga de trabajo e incluya EBS, redes, cargos del clúster, utilización y operaciones. Esta tabla no demuestra que una opción ofrezca un servicio equivalente mejor que la otra.

### Optimización del escalado automático

Puede optimizar los costos implementando estrategias eficaces de escalado automático:

#### Cluster Autoscaler

Cluster Autoscaler escala los ASG para los Pod que no se pueden programar y elimina nodos aptos según los recursos solicitados y las comprobaciones de reprogramación/interrupción; no se basa simplemente en una CPU medida baja. Haga coincidir su versión secundaria de Kubernetes con la del clúster; configure etiquetas de detección en los ASG reales y un rol de IAM dedicado a la carga de trabajo. Las etiquetas de EKS o de los grupos de nodos no se propagan automáticamente a todos los recursos subyacentes. Consulte la [configuración de AWS del proyecto ascendente](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/cloudprovider/aws) y las [recomendaciones de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html) para preparar la versión que administra.

Estos valores del chart se convierten en argumentos de CLI. Definir variables de entorno inventadas como `CLUSTER_AUTOSCALER_*` no las configura, y aplicar sin editar un ejemplo de `master` no proporciona la configuración específica de IAM/detección del clúster. Las duraciones siguientes son parámetros ilustrativos de ajuste; los retrasos más cortos pueden aumentar la rotación de nodos.

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

Karpenter aprovisiona nodos a partir de las restricciones de NodePool/EC2NodeClass, en lugar de redimensionar un ASG fijo. La latencia de aprovisionamiento y el costo dependen de la carga de trabajo y de la capacidad disponible; también se aplican aquí los requisitos previos mencionados para el controlador/IAM/AMI. Mantenga separados sus nodos de los ASG administrados por Cluster Autoscaler:

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

- **disruption.consolidateAfter**: retraso después de agregar/eliminar Pod antes de considerar la consolidación, sujeto a la política y a las comprobaciones de interrupción (por ejemplo, `30s`; reemplaza a `ttlSecondsAfterEmpty`, obsoleto)
- **disruption.consolidationPolicy**: política de consolidación de nodos: `WhenEmpty` (eliminar únicamente los nodos vacíos) o `WhenEmptyOrUnderutilized` (consolidar también los nodos infrautilizados; equivalente a `consolidation.enabled: true`, obsoleto)
- **template.spec.requirements** (`node.kubernetes.io/instance-type`): especifica tipos de instancia económicos

#### Horizontal Pod Autoscaler (HPA)

HPA ajusta automáticamente el número de Pod según la utilización de CPU o métricas personalizadas:

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

Los objetivos de utilización de CPU/memoria son porcentajes de las solicitudes y requieren la API de métricas de recursos y solicitudes en los contenedores correspondientes. Si se especifican varias métricas, HPA selecciona el mayor número deseado de réplicas; las métricas no disponibles pueden impedir la reducción de escala. Es posible que la memoria no disminuya al agregar réplicas, por lo que debe validar el comportamiento de la aplicación. EKS administra las marcas del controller-manager: configure `spec.behavior.scaleDown.stabilizationWindowSeconds` para cada HPA en lugar de asumir que puede modificar las marcas globales. No cambie automáticamente las mismas solicitudes de CPU/memoria con VPA mientras HPA utilice su denominador de utilización.

#### Vertical Pod Autoscaler (VPA)

VPA ajusta automáticamente las solicitudes de CPU y memoria de los Pod para optimizar el uso de recursos:

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

Este ejemplo usa **Off** para recopilar recomendaciones sin entrar en conflicto con el HPA anterior. Primero, instale los componentes/CRD de VPA y las dependencias de métricas.

- **Off**: solo recomendaciones.
- **Initial**: la admisión establece solicitudes en los Pod recién creados.
- **Recreate**: el updater puede desalojar Pod para que los controladores los vuelvan a crear con los recursos recomendados, sujeto a la política de desalojo/PDB.
- **Auto**: alias obsoleto de Recreate; para las nuevas configuraciones, elija el modo explícito.
- Los modos in situ requieren una versión compatible de VPA/Kubernetes y las puertas de funcionalidades documentadas. Lea el contrato del modo elegido: `InPlaceOrRecreate` puede recurrir al desalojo, mientras que `InPlace` no usa esa alternativa de recreación. Revise los límites, las interrupciones y la demanda máxima antes de habilitar actualizaciones automáticas.

## Optimización de costos de almacenamiento

El almacenamiento es un componente importante de los costos de los clústeres de EKS. Puede optimizar los costos de almacenamiento mediante las siguientes estrategias.

![Diagrama de arquitectura que muestra la optimización de costos de almacenamiento para EKS, dividida en optimización de volúmenes EBS (selección del tipo de volumen con migración a gp3, optimización del tamaño del volumen y administración del ciclo de vida del volumen), optimización de costos de EFS (selección del modo de rendimiento, administración del ciclo de vida y optimización de los patrones de acceso) y optimización de costos de S3 (optimización de la clase de almacenamiento mediante políticas de ciclo de vida y optimización de solicitudes).](../.gitbook/assets/en-eks-07-eks-cost-optimization-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-3.html)

### Optimización de volúmenes EBS

Los volúmenes EBS se utilizan principalmente para el almacenamiento persistente en los clústeres de EKS:

#### Seleccionar el tipo de volumen adecuado

Seleccione el tipo de volumen EBS adecuado para la carga de trabajo:

- **gp3**: SSD de propósito general recomendado para la mayoría de las cargas de trabajo
- **gp2**: SSD de propósito general de una generación anterior; se recomienda migrar a gp3
- **io1/io2**: SSD de IOPS aprovisionadas para cargas de trabajo de alto rendimiento
- **st1**: HDD optimizado para rendimiento para cargas de trabajo que requieren un alto rendimiento
- **sc1**: HDD frío para datos a los que se accede con poca frecuencia

gp3 separa los precios del tamaño, las IOPS y el rendimiento; su base de 3,000 IOPS no supera la de todos los volúmenes gp2. Los límites siguientes son los actuales para volúmenes generales de las regiones de AWS, sujetos a las relaciones entre tamaño/IOPS y a los límites de las instancias. Outposts tiene límites diferentes. Las tarifas de almacenamiento de $0.08/$0.10 se conservan como supuestos ilustrativos sin región ni fecha registradas; obtenga una cotización actual que incluya las IOPS/el rendimiento aprovisionados.

| Tipo de volumen | IOPS de referencia | IOPS máximas | Rendimiento de referencia | Rendimiento máximo | Precio por GB |
|------------|--------------|----------|---------------------|----------------|--------------|
| gp3 | 3,000 | 80,000 | 125 MiB/s | 2,000 MiB/s | $0.08/GB-mes (ilustrativo) |
| gp2 | 3 IOPS/GiB, mínimo de 100; los volúmenes pequeños aptos pueden usar ráfagas | 16,000 | Depende del tamaño y de las E/S | 250 MiB/s | $0.10/GB-mes (ilustrativo) |

#### Migración a gp3

Esta clase crea nuevos volúmenes gp3 mediante el controlador EBS CSI estándar (`ebs.csi.aws.com`); no migra los volúmenes existentes ni cambia la clase predeterminada del clúster. Auto Mode usa otro aprovisionador (`ebs.csi.eks.amazonaws.com`) y requiere una ruta de migración de nodos/almacenamiento adecuada. Verifique el controlador instalado, los permisos de IAM/KMS, quién administra la clase existente y la topología. `Retain` conserva el almacenamiento liberado para que lo revise el propietario, y puede seguir generando cargos:

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

1. Obtenga una copia de seguridad o instantánea coherente con la aplicación mediante los componentes CSI de instantáneas instalados y verifique que esté lista y que se pueda acceder a ella para restaurarla.
2. Restaure un **PVC nuevo** mediante la clase gp3; un PVC vinculado no puede cambiar de StorageClass in situ.
3. Pruebe la restauración y cambie la carga de trabajo durante una transición revisada; conserve el original hasta verificar la recuperación.

Un cambio in situ del tipo de volumen mediante EBS Elastic Volumes puede ser una alternativa para configuraciones compatibles. Coordínelo con el propietario de CSI/IaC en lugar de generar desviaciones de configuración. Consulte la [guía de almacenamiento](04-eks-storage-part1.md).

#### Optimización del tamaño de los volúmenes

Aprovisione únicamente el tamaño de volumen que necesite:

- Los volúmenes sobredimensionados generan costos innecesarios.
- Supervise el uso del sistema de archivos y amplíe los volúmenes compatibles cuando sea necesario. Los volúmenes EBS y los PVC de Kubernetes no se pueden reducir in situ; para reducir la capacidad se necesita un nuevo volumen más pequeño y una migración de datos adaptada a la aplicación.
- `allowVolumeExpansion` permite solicitudes de expansión compatibles; no supervisa el uso ni cambia automáticamente el tamaño. Cualquier expansor automático requiere un controlador configurado por separado, límites y gestión de errores.

#### Administración del ciclo de vida de los volúmenes

Identifique y elimine los volúmenes innecesarios:

- Revise periódicamente los PVC y PV sin uso.
- La terminación de un Pod no significa que su PVC/PV se pueda desechar. Compruebe la retención del StatefulSet, los consumidores pendientes, las copias de seguridad y la propiedad antes de eliminar una solicitud o un volumen.
- Establezca políticas de recuperación de PV adecuadas (Delete o Retain).

### Optimización de costos de EFS

EFS es útil para las cargas de trabajo que requieren acceso compartido desde varios nodos:

#### Seleccionar el modo de rendimiento adecuado

Seleccione el modo de rendimiento de EFS adecuado para la carga de trabajo:

- **Rendimiento Bursting**: adecuado para patrones de acceso intermitente
- **Rendimiento Provisioned**: adecuado para cargas de trabajo que requieren un rendimiento predecible
- **Rendimiento Elastic**: adecuado para cargas de trabajo muy variables

#### Administración del ciclo de vida

Las políticas de ciclo de vida de EFS pueden trasladar los archivos aptos a los que se accede con poca frecuencia a IA/Archive y, opcionalmente, devolverlos al almacenamiento principal cuando se accede a ellos. Los cargos de acceso, los tamaños y duraciones mínimos facturables, el modo de rendimiento y los patrones de acceso afectan los ahorros. El ejemplo exporta la matriz de políticas existente para revisarla. Edite la regla IA dentro de esa matriz y conserve las entradas requeridas de Archive/devolución al almacenamiento principal antes de enviar la configuración deseada completa:

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

Optimice los patrones de acceso a EFS para reducir costos:

- Use archivos más grandes en lugar de archivos pequeños.
- Reduzca al mínimo las operaciones de metadatos.
- Use patrones de acceso secuencial.

### Optimización de costos de S3

S3 es una opción económica para almacenar registros, copias de seguridad, contenido estático, etc.:

#### Optimización de la clase de almacenamiento

Seleccione la clase de almacenamiento de S3 adecuada para la carga de trabajo:

- **S3 Standard**: datos a los que se accede con frecuencia
- **S3 Intelligent-Tiering**: datos con patrones de acceso cambiantes
- **S3 Standard-IA**: datos a los que se accede con poca frecuencia
- **S3 One Zone-IA**: datos no críticos a los que se accede con poca frecuencia
- **S3 Glacier**: datos de archivo

#### Política de ciclo de vida

Esta regla ilustrativa hace la transición de los objetos actuales a los 30/90 días y los vence a los 365 días. Valide la latencia de recuperación, los requisitos de retención/Object Lock, los cargos de transición/solicitud, las duraciones mínimas de almacenamiento y la exclusión predeterminada de los objetos de menos de 128 KB de las transiciones en las configuraciones nuevas o modificadas. Los buckets con versionado necesitan una administración aparte de las versiones no actuales; el vencimiento de la versión actual puede crear un marcador de eliminación mientras los datos antiguos siguen siendo facturables. Una llamada a put-bucket-lifecycle-configuration reemplaza la configuración del ciclo de vida del bucket, por lo que debe combinarse con las reglas no relacionadas y conservarlas:

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

#### Optimización de las solicitudes a S3

Optimice los costos de las solicitudes a S3:

- Combine los objetos pequeños en objetos más grandes.
- Reduzca al mínimo las operaciones LIST innecesarias.
- La carga multiparte puede mejorar la transferencia y el comportamiento ante reintentos, pero añade cargos por solicitudes y almacenamiento de partes incompletas; configure la cancelación/limpieza de las cargas abandonadas. Transfer Acceleration puede generar cargos y es una opción de latencia/rendimiento, no un ahorro automático en los costos de solicitudes.

## Optimización de costos de redes

Los costos de redes pueden ser significativos, especialmente cuando se transfieren grandes volúmenes de datos. Puede optimizarlos mediante las siguientes estrategias.

<!-- Pending parent diagram repair: see /tmp/eks-cost-optimization-audit/diagram-review.json
![Tree diagram of EKS networking cost optimization branching into data transfer, load balancer, and NAT gateway optimization, each with three tactics such as intra-region communication, AZ-aware routing, compression, load balancer type selection and sharing, idle load balancer removal, NAT gateway sharing, VPC endpoints, and outbound traffic optimization, with the VPC endpoint path emphasized.](../.gitbook/assets/en-eks-07-eks-cost-optimization-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-4.html)
-->

### Optimización de la transferencia de datos

#### Usar la comunicación dentro de la región

Reduzca los costos de transferencia de datos entre regiones comunicándose dentro de la misma región siempre que sea posible:

- Ubique el clúster de EKS y los servicios de AWS relacionados en la misma región.
- Reduzca al mínimo la transferencia de datos entre regiones cuando abarque varias regiones.

#### Enrutamiento adaptado a la zona de disponibilidad

Implemente un enrutamiento adaptado a las zonas de disponibilidad para reducir los costos de transferencia entre zonas:

- Use el enrutamiento de servicios que tenga en cuenta la topología.
- Prefiera los endpoints locales cuando sean compatibles y conserve la disponibilidad en varias zonas. `trafficDistribution: PreferSameZone` es estable en Kubernetes 1.35 y versiones posteriores; valide la implementación del clúster/proxy. Es una preferencia, con alternativa cuando no hay endpoints locales disponibles, no una garantía de que no habrá tráfico entre zonas. La afinidad de ubicación por sí sola no enruta el tráfico de Service.

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

#### Usar compresión

Reduzca la cantidad de datos transferidos comprimiéndolos antes de la transferencia:

- Compresión de respuestas de API
- Compresión de registros y métricas
- Optimización de imágenes y recursos estáticos

### Optimización de balanceadores de carga

#### Seleccionar el tipo de balanceador de carga adecuado

Seleccione el tipo de balanceador de carga adecuado para la carga de trabajo:

- **Network Load Balancer (NLB)**: tráfico TCP/UDP cuando se necesita baja latencia
- **Application Load Balancer (ALB)**: tráfico HTTP/HTTPS cuando se necesita enrutamiento basado en rutas
- **Classic Load Balancer (CLB)**: cargas de trabajo heredadas

#### Uso compartido de balanceadores de carga

Reduzca los costos compartiendo balanceadores de carga entre varios servicios:

- Use AWS Load Balancer Controller.
- Exponga varios servicios mediante recursos Ingress.

Use la [guía de redes](03-eks-networking-part1.md) para instalar el AWS Load Balancer Controller estándar con el chart, la cuenta de servicio/IAM, las subredes y los grupos de seguridad correctos. Reutilice el propietario actual del controlador. Auto Mode tiene otra integración integrada; no suponga que se le aplican estos ajustes de instalación/clase. Ambos Service de backend que aparecen a continuación deben existir en el namespace de Ingress y exponer el puerto 80; el modo de destino IP requiere que se pueda acceder a las IP de los Pod. Este es un ejemplo de enrutamiento HTTP; el uso público en producción también requiere TLS, DNS y controles de acceso revisados.

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

#### Eliminar balanceadores de carga inactivos

Identifique y elimine los balanceadores de carga que no se utilizan:

- Supervise los balanceadores de carga que no reciben tráfico.
- Elimine los balanceadores de carga innecesarios de los entornos de prueba o desarrollo.

### Optimización de NAT gateway

Los NAT gateway generan cargos por hora y cargos de procesamiento de datos:

#### Uso compartido de NAT gateway

Reduzca los costos compartiendo NAT gateway entre varias subredes:

- Con los NAT gateway zonales, las subredes privadas de la misma zona de disponibilidad pueden compartir su gateway local. Evalúe la disponibilidad por zona y el costo fijo por hora.
- Un solo gateway zonal compartido entre zonas agrega una dependencia entre zonas y posibles cargos de transferencia; es una compensación deliberada, no un diseño de alta disponibilidad universalmente más económico. Evalúe por separado la opción actual de NAT regional conforme a su modelo de disponibilidad/precios documentado.

#### Usar VPC endpoints

Compare los cargos de los endpoints con la ruta NAT para el tráfico real. Los gateway endpoints de S3/DynamoDB no tienen cargos adicionales por hora ni por procesamiento de datos; los interface endpoints (como ECR/Logs/STS) tienen sus propios cargos y requieren configuración de DNS/grupos de seguridad. El siguiente ejemplo crea gateway endpoints en las tablas de rutas existentes ya revisadas; aplique una política de endpoint adecuada. Una ruta de extracción de imágenes de ECR suele necesitar tanto los interface endpoints `ecr.api`/`ecr.dkr` como acceso a S3, no solo el endpoint de la API de ECR:

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

- Reduzca al mínimo las llamadas innecesarias a API externas.
- La programación puede reducir la contención, pero los precios normales de NAT/transferencia de datos no tienen un descuento general fuera de las horas pico; reduzca los bytes facturables o la duración del aprovisionamiento.
- Use compresión de datos.

## Administración y gobernanza de recursos

La administración y gobernanza eficaces de los recursos son importantes para controlar los costos de los clústeres de EKS. Puede administrar los recursos eficazmente mediante las siguientes estrategias.

![Diagrama de árbol de la administración y gobernanza de recursos de EKS, dividida en optimización de solicitudes y límites de recursos, namespaces y cuotas de recursos, y asignación de costos y etiquetado; cada rama enumera prácticas como configurar solicitudes/límites, separar namespaces con ResourceQuota y LimitRange, y usar etiquetas de recursos, etiquetas de Kubernetes y Kubecost.](../.gitbook/assets/en-eks-07-eks-cost-optimization-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-5.html)

### Optimización de solicitudes y límites de recursos

#### Establecer solicitudes de recursos adecuadas

Establezca solicitudes de recursos que correspondan a las necesidades reales de la aplicación:

- Las solicitudes demasiado altas desperdician recursos.
- Las solicitudes demasiado bajas pueden provocar problemas de rendimiento.
- Use VPA (Vertical Pod Autoscaler) para optimizar las solicitudes de recursos.

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

#### Establecer límites de recursos

Establezca límites de recursos para impedir que los contenedores consuman recursos excesivos:

- Los límites de CPU normalmente imponen throttling; los límites excesivamente bajos pueden perjudicar la latencia incluso cuando al nodo le sobra CPU.
- Los límites de memoria se aplican de forma reactiva y pueden provocar la terminación por OOM; no garantizan que el uso nunca supere brevemente un valor. Dimensione las solicitudes/límites según el comportamiento medido de la carga de trabajo, no con una proporción universal.

#### Comprender las clases QoS

Comprenda y utilice las clases QoS (calidad de servicio) de Kubernetes:

Para la configuración de recursos a nivel de contenedor que se muestra aquí:

- **Guaranteed**: todos los contenedores tienen solicitudes distintas de cero de CPU y memoria, iguales a sus límites correspondientes.
- **Burstable**: se configura alguna solicitud o límite de CPU/memoria, pero no se cumplen los criterios de Guaranteed.
- **BestEffort**: ningún contenedor tiene solicitudes ni límites de CPU/memoria.

QoS no es lo mismo que la prioridad de los Pod y no establece un orden absoluto de desalojo. Cuando el nodo está bajo presión, kubelet considera si el uso supera las solicitudes, la prioridad del Pod y el exceso de uso relativo. El desalojo por presión del disco también es distinto porque QoS de CPU/memoria no clasifica las solicitudes de almacenamiento efímero. Consulte las [reglas QoS actuales](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/) cuando use recursos a nivel de Pod.

### Namespaces y cuotas de recursos

#### Separación basada en namespaces

Use namespaces para separar lógicamente los recursos:

- Cree namespaces por equipo, entorno o aplicación.
- Supervise el uso de recursos por namespace.

#### Establecer cuotas de recursos

ResourceQuota limita las solicitudes/límites de recursos admitidos y la cantidad de objetos dentro de un namespace existente; no es un límite de gasto ni un medidor de CPU en tiempo de ejecución. Cree primero el namespace `team-a`. La cuota de CPU/memoria puede requerir solicitudes/límites en los contenedores entrantes, así que coordine los valores predeterminados de LimitRange con las cargas de trabajo:

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

#### Establecer LimitRange

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

Aplique etiquetas a los recursos de AWS y active las claves de facturación aptas mediante el responsable de facturación. La etiqueta de un clúster de EKS no se propaga automáticamente a sus instancias EC2, ASG, volúmenes EBS ni balanceadores de carga. Verifique la cobertura real de las etiquetas y los retrasos del procesamiento de facturación; estos ejemplos de etiquetado explícito no garantizan una atribución completa de los costos del clúster:

- Etiquete por equipo, proyecto, entorno, centro de costos, etc.
- Implemente una estrategia de etiquetado coherente.

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

Las etiquetas/anotaciones de Kubernetes constituyen un sistema de metadatos independiente. Las herramientas de costos pueden agrupar por etiquetas seleccionadas de las cargas de trabajo; si se desea agrupar a nivel de Pod, las etiquetas del Deployment también deben aparecer en su plantilla de Pod. Las etiquetas del namespace no se heredan automáticamente en los Pod ni en los recursos de AWS. La asignación de costos divididos de AWS y los atributos de costos de Pod de EKS generados requieren una configuración de facturación aparte:

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

Use Kubecost para realizar un seguimiento de los costos de los recursos de Kubernetes y optimizarlos:

Siga la sección de instalación que aparece a continuación; elija una implementación administrada de Kubecost/OpenCost en lugar de instalar recopiladores duplicados. La asignación basada en recursos sigue siendo una estimación hasta que se reconcilia con el conjunto de datos de facturación y la política acordada de costos compartidos.

Kubecost ofrece las siguientes funciones:

- Análisis de costos por namespace, Deployment, Service y etiqueta
- Recomendaciones para optimizar costos
- Informes de asignación de costos y devolución de cargos

## Supervisión y análisis de costos

Para optimizar los costos de forma eficaz, debe supervisarlos y analizarlos continuamente. Puede hacerlo mediante las siguientes herramientas y estrategias.

![Diagrama de supervisión y análisis de costos para EKS dividido en cuatro herramientas: AWS Cost Explorer, Kubecost, CloudWatch Container Insights y un panel de costos personalizado; cada una está vinculada a capacidades clave como análisis de costos, detección de anomalías, presupuestos, panel y alertas de Kubecost, supervisión del uso de recursos, información para optimizar, panel de Grafana y puntuación de optimización de costos.](../.gitbook/assets/en-eks-07-eks-cost-optimization-6.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-6.html)

### AWS Cost Explorer

AWS Cost Explorer es una herramienta que ayuda a visualizar, comprender y administrar los costos y el uso de AWS:

#### Análisis de costos

Analice los costos del clúster de EKS mediante AWS Cost Explorer:

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

Las fechas de 2025 son ejemplos históricos de sintaxis, no un informe de costos actual; elija un período de facturación UTC disponible con una fecha de finalización exclusiva. Respete cualquier `NextPageToken` en lugar de considerar completa la primera respuesta. Compare por separado las bases de costos; no sume bases distintas ni agregue `UsageQuantity` entre unidades incompatibles. La agrupación por servicio/etiqueta incluye los valores sin etiqueta y no es específica del clúster automáticamente.

#### Detección de anomalías en los costos

Use AWS Cost Anomaly Detection para detectar aumentos anómalos en los costos:

1. Inicie sesión en AWS Management Console.
2. Vaya al servicio AWS Cost Management.
3. Seleccione «Cost Anomaly Detection».
4. Haga clic en «Create anomaly monitor».
5. Configure el tipo de monitor y las preferencias de notificación.

#### Configuración de un presupuesto de costos

Este ejemplo de 1,000 USD/80 % crea una notificación de presupuesto mensual real; sustituya la cuenta y el correo electrónico por valores aprobados. Verifique el filtro canónico de etiquetas de Budgets (por ejemplo, `user:Environment$Production`) con la configuración de facturación. El filtro selecciona los costos etiquetados de todos los servicios; limitar Service a EKS excluiría EC2, almacenamiento y otros costos del clúster. Los costos sin etiqueta o compartidos siguen necesitando una asignación aparte. Budgets procesa datos de facturación con retraso y no es un límite de gasto estricto. Los presupuestos existentes deben reconciliarse con su propietario; aquí no se establece una fecha de vencimiento fija pasada:

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

El chart/la aplicación comprobados corresponden a la versión **3.3.1** del repositorio actual que aparece a continuación. Kubecost 3.x usa ClickHouse y recopilación directa mediante finops-agent; no reutilice una instalación 2.x de `cost-analyzer` ni sus valores incluidos para Prometheus/node-exporter. Antes de aplicarlo, revise la licencia, la compatibilidad con Kubernetes, las clases de almacenamiento/el tamaño de PVC, el ID del clúster, la recopilación de redes y el control de acceso en la [documentación del chart](https://github.com/kubecost/cost-analyzer-helm-chart). Siga el procedimiento de migración documentado para una versión 2.x existente; esto no es un procedimiento de actualización in situ. No se afirma que haya una instalación activa ni que esté listo para producción. La [guía de la plataforma FinOps](../ops/13-finops-cost-platform.md) también abarca OpenCost y la conciliación de facturación.

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

- Costos por namespace, Deployment, Service y nodo
- Eficiencia y utilización de recursos
- Recomendaciones para optimizar costos
- Informes de asignación de costos y devolución de cargos

#### Alertas de Kubecost

Use el mecanismo de alertas documentado para la edición/versión instalada de Kubecost y configure explícitamente los destinatarios, las credenciales, el período presupuestario, la agregación y la entrega. Un ConfigMap arbitrario como `cost-analyzer-alerts` con `alerts.json` no se consume automáticamente, y el ejemplo anterior no establecía un esquema válido ni un montaje. El ejemplo de AWS Budgets anterior es una alerta de facturación independiente y concreta; la [guía de FinOps](../ops/13-finops-cost-platform.md) ofrece un flujo de trabajo explícito para elaborar informes de asignación. Valide la entrega con una prueba sintética antes de depender de las alertas y supervise también los datos faltantes/obsoletos, además de los umbrales excedidos.

### CloudWatch Container Insights

Use CloudWatch Container Insights para supervisar el uso de recursos del clúster de EKS:

#### Habilitar Container Insights

Container Insights es telemetría de nodos/cargas de trabajo recopilada por el agente de CloudWatch o el complemento de observabilidad; `containerinsights` no es un tipo de registro del plano de control de EKS para `eksctl utils update-cluster-logging`. Siga la [guía de supervisión](06-eks-monitoring-logging.md) para elegir el complemento compatible, la asociación de IAM, la configuración y la ruta de recopilación específica de la plataforma. Mantenga un único responsable del recopilador y verifique la entrega real de métricas/registros. La telemetría del complemento/agente puede generar cargos.

#### Supervisión del uso de recursos

El panel de CloudWatch permite supervisar las siguientes métricas:

- Uso de CPU y memoria
- E/S de disco y red
- Cantidad de reinicios de contenedores
- Estado de los nodos

#### Información para optimizar costos

Analice los datos de CloudWatch Container Insights para identificar oportunidades de optimización de costos:

- Identifique los recursos sobredimensionados.
- Identifique los nodos con baja utilización de recursos.
- Analice las diferencias entre las solicitudes de recursos y el uso real.

### Panel de costos personalizado

Puede crear paneles de costos personalizados para supervisar de forma integral los costos del clúster de EKS:

#### Panel de Grafana

Cree paneles de costos personalizados con Prometheus y Grafana:

1. Recopile métricas de uso de recursos en Prometheus.
2. Cree un panel de costos en Grafana.
3. Use una canalización de datos de facturación autenticada e implementada por separado, o una fuente de datos compatible para los resultados de Cost Explorer/CUR; añadir un panel no convierte las métricas de uso de Prometheus en datos reales de facturación. No exponga credenciales de facturación en el JSON del panel del navegador.

#### Puntuación de optimización de costos

Realice un seguimiento de estos indicadores por separado, con fórmulas, cobertura y períodos claramente documentados. No existe una puntuación universal de optimización de costos, y ninguno de estos cocientes por sí solo demuestra desperdicio ni ahorro monetario:

- Cociente entre solicitudes de recursos y uso
- Utilización de nodos
- Cociente de uso de instancias Spot
- Cociente de recursos inactivos

## Prácticas recomendadas para optimizar costos

Veamos las prácticas recomendadas para optimizar los costos de un clúster de EKS.

![Diagrama de prácticas recomendadas para la optimización de costos de EKS, dividido en prácticas generales, optimización específica de las cargas de trabajo y optimización de costos para servicios financieros; bajo las prácticas generales aparece un ciclo continuo de optimización de costos: medir, analizar, optimizar, supervisar e iterar.](../.gitbook/assets/en-eks-07-eks-cost-optimization-7.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-07-eks-cost-optimization-7.html)

### Prácticas recomendadas generales

#### Optimización continua de costos

La optimización de costos es un proceso continuo, no una tarea que se realiza una sola vez:

1. **Medir**: mida los costos y el uso de recursos actuales.
2. **Analizar**: analice los factores que impulsan los costos y las oportunidades de optimización.
3. **Optimizar**: implemente estrategias de optimización de costos.
4. **Supervisar**: supervise los resultados y haga ajustes según sea necesario.
5. **Iterar**: repita el proceso.

#### Fomentar una cultura consciente de los costos

Fomente una cultura consciente de los costos en la organización:

- Ofrezca visibilidad de los costos a los equipos.
- Establezca objetivos de optimización de costos.
- Reconozca y premie los logros en la optimización de costos.
- Comparta prácticas recomendadas para optimizar costos.

#### Uso de la automatización

Use la automatización para optimizar los costos:

- Implemente el escalado automático.
- Aprovisione recursos según el uso.
- Automatice la detección de anomalías en los costos y las alertas.
- Identifique automáticamente posibles candidatos; elimínelos solo después de comprobar la propiedad, la retención, las dependencias y la recuperación.

### Optimización específica de las cargas de trabajo

#### Entornos de desarrollo y pruebas

Optimice los costos de los entornos de desarrollo y pruebas:

- Apague automáticamente los entornos cuando no se utilicen.
- Use instancias Spot.
- Establezca límites de recursos.
- Considere usar entornos compartidos.

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

El CronJob está **suspendido de forma predeterminada**, se dirige únicamente al Deployment `dev/dev-app` existente y espera que haya tres réplicas. Use una versión de kubectl que se encuentre dentro de la asimetría de versiones compatible con el servidor. Acuerde el horario UTC y un procedimiento de restauración antes de habilitarlo; ajuste deliberadamente el nombre y la precondición. Si HPA o GitOps administra las réplicas, coordine el horario con ese responsable en lugar de competir con él. Reducir directamente la escala de un Deployment no usa la admisión de desalojos de PDB; reserve este método para el apagado de desarrollo aprobado. Detener los Pod no detiene el cargo del plano de control de EKS, el almacenamiento retenido ni los nodos que no puedan reducir su escala.

#### Cargas de trabajo por lotes

Optimice los costos de las cargas de trabajo por lotes:

- Use instancias Spot.
- Programe la ejecución dentro de los plazos de los trabajos y según la capacidad disponible; no hay un descuento general por hora del día para el cómputo On-Demand.
- Optimice las solicitudes de recursos.
- Libere los recursos al finalizar los trabajos.

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

Este Job selecciona **nodos Spot de grupos de nodos administrados**. Karpenter usa `karpenter.sh/capacity-type: spot`; seleccione la etiqueta que realmente tengan los nodos previstos. La imagen de la aplicación es un marcador de posición. Implemente reintentos idempotentes/puntos de control y asegúrese de tolerar cualquier taint de los nodos. La finalización del Job o el TTL limpia los objetos de Kubernetes, pero no necesariamente los PVC, los volúmenes ni los nodos facturables.

#### Aplicaciones web

Optimice los costos de las aplicaciones web:

- Implemente el escalado automático.
- Use una CDN para reducir el tráfico.
- Implemente una estrategia de almacenamiento en caché.
- Considere una arquitectura sin servidor.

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

- Seleccione un tipo de instancia adecuado.
- Configure el escalado automático del almacenamiento.
- Considere usar réplicas de lectura.
- Considere agregar una capa de caché.

### Optimización de costos para servicios financieros

Estrategias adicionales de optimización de costos que se deben tener en cuenta al usar EKS en el sector de los servicios financieros:

#### Administración de costos del cumplimiento normativo

Optimice los costos sin dejar de cumplir los requisitos normativos:

- Aprovisione los recursos mínimos necesarios para cumplir los requisitos normativos.
- Reduzca los costos operativos mediante la automatización del cumplimiento.
- Separe los entornos regulados de los no regulados.

#### Equilibrio entre alta disponibilidad y costo

Mantenga un equilibrio entre los requisitos de alta disponibilidad y los costos:

- Implemente en varias zonas de disponibilidad las cargas de trabajo críticas.
- Considere una implementación en una sola zona de disponibilidad para las cargas de trabajo no críticas.
- Implemente un enfoque económico para los entornos de recuperación ante desastres.

#### Equilibrio entre los requisitos de seguridad y el costo

Mantenga un equilibrio entre los requisitos de seguridad y los costos:

- Implemente controles de seguridad con un enfoque basado en el riesgo.
- Reduzca los costos operativos mediante la automatización de la seguridad.
- Seleccione herramientas y servicios de seguridad económicos.

## Conclusión

La optimización eficaz de los costos de un clúster de Amazon EKS requiere un enfoque integral que abarque el cómputo, el almacenamiento, las redes y los costos operativos. Evalúe cada cambio comparándolo con la facturación medida y los SLO de las cargas de trabajo; no se garantizan ahorros ni un rendimiento/estabilidad sin cambios.

Puntos clave:

1. **Componentes de los costos de EKS**: costo del clúster de EKS, costo de cómputo, costo de almacenamiento, costo de redes y otros costos
2. **Optimización de costos de cómputo**: selección de tipos de instancia adecuados, uso de instancias Spot, uso de Savings Plans y Reserved Instances y optimización del escalado automático
3. **Optimización de costos de almacenamiento**: optimización de volúmenes EBS, optimización de costos de EFS y optimización de costos de S3
4. **Optimización de costos de redes**: optimización de la transferencia de datos, optimización de balanceadores de carga y optimización de NAT gateway
5. **Administración y gobernanza de recursos**: optimización de solicitudes y límites de recursos, namespaces y cuotas de recursos, y asignación de costos y etiquetado
6. **Supervisión y análisis de costos**: AWS Cost Explorer, Kubecost, CloudWatch Container Insights y paneles de costos personalizados
7. **Prácticas recomendadas para optimizar costos**: prácticas recomendadas generales, optimización específica de las cargas de trabajo y optimización de costos para servicios financieros

La optimización de costos es un proceso continuo. Debe revisar y ajustar periódicamente las estrategias de optimización a medida que evolucionen el clúster y las cargas de trabajo.

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

Para poner a prueba lo que ha aprendido en este capítulo, pruebe el [cuestionario del tema](../quizzes/eks/07-eks-cost-optimization-quiz.md).
