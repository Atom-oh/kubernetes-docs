# Karpenter

> **Versiones compatibles**: Karpenter 1.14 LTS (ejemplos: 1.14.1). Selecciona las versiones de Kubernetes y EKS según las tablas de compatibilidad y de soporte del proveedor.
> **Última actualización**: 16 de octubre de 2026

## Tabla de contenidos
- [Introducción](#introduction)
- [Arquitectura](#architecture)
- [Instalación y configuración](#installation-and-configuration)
- [NodePool](#nodepool)
- [Clases de nodo](#node-classes)
- [Gestión de interrupciones](#interruption-handling)
- [Integración](#integration)
- [Integración con Amazon EKS](#integration-with-amazon-eks)
- [Prácticas recomendadas](#best-practices)
- [Solución de problemas](#troubleshooting)
- [Conclusión](#conclusion)

## Introducción {#introduction}

Karpenter es un autoescalador de nodos de código abierto. Este capítulo utiliza su proveedor de AWS, que aprovisiona capacidad de EC2 para cargas de trabajo compatibles con Kubernetes. La disponibilidad y la eficiencia dependen de las restricciones, la capacidad de la nube, la inicialización de los nodos y el diseño de las aplicaciones.

### Ventajas principales de Karpenter

1. **Escalado ante la demanda**: inicia el aprovisionamiento cuando hay cargas de trabajo cuyos Pods no pueden programarse. No garantiza un tiempo fijo hasta que los nodos y las aplicaciones estén listos.
2. **Optimización de costos**: selecciona los tipos de instancia más adecuados para las cargas de trabajo.
3. **Configuración sencilla**: utiliza API declarativas.
4. **Diseño centrado en las cargas de trabajo**: aprovisiona nodos según los requisitos de los Pods.
5. **Integración con la nube**: aprovecha las capacidades del proveedor.
6. **Uso eficiente de los recursos**: agrupa las cargas de trabajo para aprovechar mejor la capacidad disponible.
7. **Gestión flexible de nodos**: gestiona su ciclo de vida e integra el tratamiento de interrupciones.

### Comparación con los autoescaladores existentes

| Característica | Karpenter | Cluster Autoscaler | Grupos de nodos administrados por el proveedor de nube |
|---------|-----------|-------------------|---------------------------|
| Velocidad de escalado | Depende de la programación, la capacidad de EC2 y la inicialización | Depende del escalado y la inicialización del grupo de nodos | Depende de la política de escalado, la capacidad y la inicialización |
| Selección del tipo de instancia | Dinámica | Basada en grupos de nodos | Basada en grupos de nodos |
| Eficiencia del empaquetado | Depende de la carga de trabajo/las restricciones | Depende de la carga de trabajo/del grupo de nodos | Depende del scheduler y del controlador de escalado |
| Complejidad de configuración | Baja | Media | Baja |
| Integración con la nube | Implementación específica del proveedor | Integraciones con varios proveedores de nube | Nativa del proveedor |
| Gestión de grupos de nodos | No necesaria | Necesaria | Necesaria |
| Gestión de interrupciones | Gestión de eventos configurada y ciclo de vida de los nodos | Depende de la plataforma/la integración | Gestión específica de la plataforma |

> **Nota**: EKS incorporó el soporte de warm pools en los grupos de nodos administrados el 8 de abril de 2026. Las instancias preinicializadas pueden reducir el trabajo de inicialización que debe repetirse. Los modos Stopped y Running tienen tiempos de transición y costos distintos, y la reutilización de instancias al reducir la capacidad es opcional. Según AWS, la integración con Cluster Autoscaler no requiere configuración adicional. Reanudar las instancias, dejar los nodos listos e iniciar las aplicaciones sigue llevando tiempo. Esta función pertenece a los grupos de nodos administrados de EKS y a Auto Scaling; Karpenter no administra esos pools.

## Arquitectura {#architecture}

Karpenter funciona como un controlador de Kubernetes: detecta los Pods que no pueden programarse y aprovisiona nodos adecuados.

![Diagrama de arquitectura que muestra el controlador de Karpenter en un clúster de Kubernetes observando pods no programables, usando los CRD NodePool y EC2NodeClass validados por CEL, y llamando a la API de Kubernetes y a la API de instancias del proveedor de nube para aprovisionar instancias de cómputo.](../.gitbook/assets/en-autoscaling-02-karpenter-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-0.html)

### Flujo de trabajo de Karpenter

El siguiente diagrama muestra cómo funciona Karpenter en un clúster de EKS:

![Diagrama de secuencia que muestra un pod no programable llegando al controlador de Karpenter a través de la API de Kubernetes, Karpenter consultando la API de EC2 de AWS y solicitando un nodo, y el nuevo nodo registrándose para que finalmente se programe el pod.](../.gitbook/assets/en-autoscaling-02-karpenter-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-1.html)

### Componentes principales

1. **Controlador de Karpenter**: simula las necesidades de programación, crea NodeClaims y gestiona el ciclo de vida de los nodos. El scheduler de Kubernetes realiza la asignación efectiva de los Pods a los nodos.
2. **Validación CEL de los CRD**: las reglas CEL de los CRD validan NodePool y EC2NodeClass. Los webhooks de admisión y conversión se eliminaron en Karpenter 1.1.
3. **CRD NodePool y NodeClaim**: NodePool define la política; cada NodeClaim registra los requisitos y el ciclo de vida de un nodo aprovisionado.
4. **CRD EC2NodeClass**: define la configuración de los nodos que se aprovisionarán.
5. **Integración con el proveedor de nube**: utiliza sus API para gestionar los recursos de cómputo.

### Cómo funciona

1. El controlador de Karpenter detecta los Pods que no pueden programarse.
2. Analiza sus requisitos: recursos, selectores de nodo, tolerancias y otros ajustes.
3. Determina los tipos de nodo adecuados según la configuración de NodePool y EC2NodeClass.
4. Llama a la API del proveedor de nube para aprovisionar nodos.
5. El nodo se registra y queda listo; entonces, el scheduler de Kubernetes puede asignarle los Pods que cumplan los requisitos. Karpenter no sustituye a kube-scheduler.
6. La consolidación, la deriva de configuración, la expiración, la eliminación manual y las interrupciones de la nube tienen desencadenantes y medidas de protección distintos. No todos ellos son eventos de interrupción recibidos por SQS.

## Instalación y configuración {#installation-and-configuration}

Los bloques YAML que no incluyen apiVersion/kind son fragmentos de configuración para la especificación de NodePool o EC2NodeClass en cuestión; no son documentos independientes para aplicar con kubectl.

Estos son ejemplos de aprendizaje independientes para un clúster existente, no un paquete de implementación listo para producción. Los nombres de objeto repetidos representan alternativas. Prepara y verifica IAM/OIDC, el acceso a los nodos, las subredes/grupos de seguridad aprobados, la capacidad de arranque y la cola de interrupciones antes de la instalación. Todo el YAML utiliza nombres de ejemplo literales, como `my-cluster`; kubectl no expande `${CLUSTER_NAME}` dentro de un archivo YAML guardado. La auditoría no aprovisionó recursos de AWS, no instaló Karpenter ni midió el escalado. Los comandos de instalación nueva fallan si esa versión ya está instalada; las instalaciones existentes deben seguir la guía de actualización/migración de CRD correspondiente a la versión.

### Requisitos previos

- Usa una versión de Kubernetes compatible con tu plataforma y con la matriz de Karpenter. La matriz publicada indica Karpenter 1.6 como mínimo para Kubernetes 1.34, 1.9 para 1.35 y 1.13 para 1.36. Estos mínimos no implican que todas las versiones menores anteriores de Karpenter sigan recibiendo mantenimiento. La matriz de v1.14 no incluye Kubernetes 1.37, y la de v1.15 exige Karpenter 1.15.x para Kubernetes 1.37. Comprueba por separado la disponibilidad y el soporte de las versiones de EKS.
- kubectl configurado.
- Credenciales y permisos del proveedor de nube.
- Helm, si se utiliza el método de instalación correspondiente.

### Instalación en AWS EKS

#### 1. Configuración del rol y la política de IAM

Los comandos presuponen que ya existen un rol de controlador y un rol de nodo, y que EKS utiliza autenticación basada en API (API o API_AND_CONFIG_MAP). En un clúster que solo usa CONFIG_MAP, hay que comprobar la asignación existente de nodos en aws-auth en lugar de ejecutar list-access-entries; no cambies el modo de autenticación como paso incidental de la configuración. El rol de nodo confía en EC2 y necesita permisos de nodo de trabajo/descarga de ECR (por ejemplo, AmazonEKSWorkerNodePolicy y AmazonEC2ContainerRegistryPullOnly). Asigna al VPC CNI su propia identidad cuando sea compatible; los permisos de SSM son opcionales y requieren un agente configurado. AmazonEKSClusterPolicy no sustituye a la política del controlador de Karpenter.

```bash
# Set the existing cluster and Region; these commands only inspect AWS/Kubernetes.
export CLUSTER_NAME="my-cluster"
export AWS_REGION="us-west-2"
export KARPENTER_VERSION="1.14.1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CLUSTER_ENDPOINT=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --query cluster.endpoint --output text)
export ACCOUNT_ID CLUSTER_ENDPOINT
kubectl config current-context
aws iam get-role --role-name "KarpenterControllerRole-${CLUSTER_NAME}" --query Role.AssumeRolePolicyDocument
aws iam get-role --role-name "KarpenterNodeRole-${CLUSTER_NAME}" --query Role.AssumeRolePolicyDocument
aws eks list-access-entries --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME"
```

#### 2. Instalación mediante Helm

Usa el ejemplo de instalación nueva una sola vez, después de preparar la cola indicada y la capacidad de arranque. Para una actualización, revisa la guía de migración específica de la versión y actualiza los CRD correspondientes (por ejemplo, mediante el chart karpenter-crd administrado por separado); una actualización del chart del controlador por sí sola generalmente no actualiza los CRD. Verifica la propiedad antes de migrar una instalación existente de CRD.

```bash
# Run only after the prerequisites and the current kubectl context are verified.
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${ACCOUNT_ID:?Set the AWS account ID}"
: "${CLUSTER_ENDPOINT:?Set the matching EKS endpoint}"
KARPENTER_VERSION="1.14.1"
helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "$KARPENTER_VERSION" \
  --namespace karpenter --create-namespace \
  --set-string 'serviceAccount.annotations.eks\.amazonaws\.com/role-arn'="arn:aws:iam::${ACCOUNT_ID}:role/KarpenterControllerRole-${CLUSTER_NAME}" \
  --set-string settings.clusterName="$CLUSTER_NAME" \
  --set-string settings.clusterEndpoint="$CLUSTER_ENDPOINT" \
  --set-string settings.interruptionQueue="$CLUSTER_NAME" \
  --wait --timeout 5m
```

#### 3. Verificación de la instalación

```bash
kubectl get deployments,pods -n karpenter
kubectl rollout status deployment/karpenter -n karpenter --timeout=180s
kubectl get nodepools,ec2nodeclasses,nodeclaims
```

Salida ilustrativa para las dos réplicas predeterminadas del controlador (no es una ejecución capturada en esta auditoría):
```
NAME                         READY   STATUS    RESTARTS   AGE
karpenter-<hash>-<id-1>      1/1     Running   0          1m
karpenter-<hash>-<id-2>      1/1     Running   0          1m
```

### Configuración básica de NodePool y EC2NodeClass

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
  limits:
    cpu: '1000'
    memory: 1000Gi
  template:
    spec:
      requirements:
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
        - m5.large
        - m5.xlarge
        - m5.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
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
  tags:
    karpenter.sh/discovery: my-cluster
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      deleteOnTermination: true
      encrypted: true
```

## NodePool

NodePool es un recurso personalizado de Kubernetes que define cómo aprovisiona Karpenter los nodos. Reemplaza al Provisioner anterior.

### Configuración básica de NodePool

El taint especial del siguiente ejemplo exige una tolerancia correspondiente en la carga de trabajo. Mantén startupTaints vacío hasta disponer de un inicializador verificado que elimine el taint configurado. Añadir un taint de inicio sin un controlador responsable de retirarlo puede dejar los nodos inutilizables. Los ejemplos de límites, inicialización e interrupciones son alternativas; no deben acumularse como cambios sobre un NodePool de producción en ejecución.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    metadata:
      labels:
        environment: training
        app: web
    spec:
      requirements:
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
        - m5.large
        - m5.xlarge
        - m5.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 720h
      taints:
      - key: example.com/special-taint
        value: 'true'
        effect: NoSchedule
      startupTaints: []
  limits:
    cpu: '1000'
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### Configuración de requisitos

Los requisitos se combinan por intersección entre sí, con EC2NodeClass y con las restricciones de los Pods. Permitir amd64 y arm64 solo resulta útil si los tipos de instancia disponibles, las AMI y las imágenes de contenedor admiten ambas arquitecturas. Enumerar zonas o tipos de capacidad permitidos no garantiza una distribución uniforme; utiliza las restricciones de topología de las cargas de trabajo para conseguirla.

Los requisitos definen las características de los nodos que Karpenter aprovisionará:

```yaml
template:
  spec:
    requirements:
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
    - key: node.kubernetes.io/instance-type
      operator: In
      values:
      - m5.large
      - m5.xlarge
      - c5.large
      - m6g.large
      - c6g.large
    - key: topology.kubernetes.io/zone
      operator: In
      values:
      - us-west-2a
      - us-west-2b
      - us-west-2c
    - key: kubernetes.io/os
      operator: In
      values:
      - linux
```

### Configuración de límites

`spec.limits` limita el total de recursos aprovisionados, pero el aprovisionamiento paralelo utiliza comprobaciones con coherencia eventual y puede superar temporalmente ese límite. No constituye un tope estricto de facturación. Expresar las cantidades como cadenas evita diferencias de tipos entre la API y GitOps.

```yaml
limits:
  cpu: '1000'
  memory: 1000Gi
  nvidia.com/gpu: '10'
```

### Seguimiento experimental de asignaciones DRA (v1.13)

El núcleo de Karpenter v1.13 incorporó el seguimiento de asignaciones de dispositivos DRA. Esto no garantiza por sí solo que el aprovisionamiento mediante DRA sea apto para producción: el chart del proveedor AWS 1.14.1 establece `settings.ignoreDRARequests: true` de forma predeterminada, y el proyecto original todavía no considera que su soporte formal de DRA esté disponible de forma general. Que se indique Kubernetes 1.29 como mínimo no demuestra la compatibilidad. Valida la API de recursos exacta de Kubernetes, el driver DRA, ResourceClaims, ResourceSlices y la configuración de Karpenter. No utilices las solicitudes DRA como sustituto directo del ejemplo de recursos extendidos mediante device-plugin que aparece más adelante.

### Configuración de expiración de nodos

`expireAfter` define cuándo comienza el vaciado provocado por la expiración, no un plazo garantizado para completar el reemplazo. El `terminationGracePeriod` opcional que aparece más abajo limita el tiempo de vaciado, pero puede eliminar forzosamente los Pods restantes, incluidos los bloqueados por PDB. Establece ese plazo solo después de validar los requisitos de cierre y recuperación de la aplicación.

```yaml
spec:
  template:
    spec:
      expireAfter: 720h
      terminationGracePeriod: 30m
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### Reconocimiento de los taints de NodeReadinessController (v1.13)

Karpenter core v1.13 reconoce los taints `readiness.k8s.io/` del NodeReadinessController independiente como efímeros durante la simulación de programación de un nodo administrado que aún no se ha inicializado. Sigue esperando a que desaparezcan esos taints antes de marcar la inicialización como completada; no los elimina ni permite que el scheduler de Kubernetes los ignore. Los demás taints de inicializador siguen requiriendo una configuración precisa de `startupTaints` y un controlador que los elimine.

### Actualización de julio de 2026: lanzamiento de v1.14

Karpenter v1.14, publicado el 11 de julio de 2026, incluye:

- **Compatibilidad con la API CapacityBuffers**: integración alfa de búferes de capacidad. `CapacityBuffer` está deshabilitado de forma predeterminada y requiere los CRD y la configuración del controlador correspondientes. Reservar capacidad adicional tiene un costo y no garantiza una latencia determinada.
- **Compatibilidad con tipos de instancia preliminares**: reconoce las ofertas preliminares admitidas. Aprovisionarlas sigue dependiendo del acceso de la cuenta y la región, y de su disponibilidad.
- **Compatibilidad con Nitro Enclaves**: el proveedor activa `EnclaveOptions.Enabled` en la plantilla de lanzamiento generada cuando las solicitudes de recursos de NodeClaim incluyen `eks.amazonaws.com/nip-slots`. Siguen siendo necesarias instancias y AMI compatibles, junto con el device-plugin adecuado. En 1.14.1 no existe el campo `EC2NodeClass.spec.enclaveOptions`.
- Correcciones de errores: contabilización de la IP principal de las ENI secundarias, inicialización de la caché de Zonal Shift, incorporación del tiempo de espera del cliente del SDK de AWS a la configuración del operador y otras mejoras.

Consulta las [notas de la versión v1.14.0](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.14.0) para obtener más información.

El 17 de julio de 2026, varias ramas anteriores recibieron parches, entre ellos 1.3.8 y 1.11.3. La publicación de esas correcciones no demuestra que todas las versiones menores intermedias sigan recibiendo mantenimiento. La política actual ofrece soporte para LTS 1.9 hasta febrero de 2027 y para LTS 1.14 hasta julio de 2027; las versiones menores regulares solo reciben soporte hasta la siguiente versión menor. Elige una línea con soporte y sigue su guía de migración.

El anuncio de AWS del 22 de julio de 2026 incorporó la configuración de interfaces de red EFA y grupos de ubicación para Karpenter y EKS Auto Mode. En el proveedor AWS de Karpenter 1.14.1, los campos son `EC2NodeClass.spec.networkInterfaces` y `spec.placementGroupSelector`; no pertenecen a NodePool. Las interfaces de tipo solo EFA no consumen direcciones IP de VPC, pero sigue siendo necesaria una `interface` principal en el índice 0 de dispositivo y tarjeta. Selecciona un grupo de ubicación existente por nombre o ID. Su estrategia de clúster, distribución o partición, junto con los tipos de instancia compatibles, condiciona la ubicación. Este ejemplo no configura ni valida una carga de trabajo HPC.

### Actualización de agosto de 2026: lanzamiento de parche v1.14.1

[v1.14.1](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.14.1), el primer parche de la línea v1.14, se publicó el 21 de agosto de 2026. Es una versión de mantenimiento que actualiza `sigs.k8s.io/karpenter`, procedente del proyecto original, e incorpora las correcciones realizadas desde v1.14.0.

### Actualización de octubre de 2026: lanzamiento estándar v1.15.0

[v1.15.0](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.0), una versión menor estándar (no LTS), se publicó el 10 de octubre de 2026. Cambios principales:

- **La reparación de nodos pasa a ser una interrupción voluntaria**: se incorpora al mecanismo de interrupciones. Si un NodePool limitado por capacidad no puede preparar primero un nodo de reemplazo, la reparación termina el nodo afectado antes de sustituirlo. Se añade el reinicio mediante `ec2:RebootInstances` como acción de reparación, sujeto a la función experimental de AWS `RebootForRepair`. El controlador de reparación anterior sigue disponible mediante `--legacy-node-repair`.
- **Compatibilidad con CEL en KubeletConfiguration**: `maxPodsExpression`, `kubeReserved` y `systemReserved` admiten expresiones CEL, y se amplían los campos de KubeletConfiguration en EC2NodeClass.
- **Mayor compatibilidad con DRA**: soporte de alternativas priorizadas y de DRA para los drivers de NVIDIA y EFA.
- Otras novedades: la opción `--aws-feature-gates`, consideración de las restricciones predeterminadas de distribución topológica de Pods, contabilización de los límites de volúmenes de cada tipo de instancia durante el aprovisionamiento, nuevas métricas de interrupción como `karpenter_pods_disrupted_total` y un controlador de gestión del costo de eliminación de Pods que debe habilitarse mediante su opción de función.

Según la política de soporte, las versiones menores regulares solo reciben soporte hasta la siguiente versión menor. Por tanto, tras la publicación de v1.15.0, v1.14 continúa únicamente como línea LTS (hasta julio de 2027); por eso, los ejemplos de este capítulo siguen en 1.14 LTS (1.14.1). Kubernetes 1.37 requiere Karpenter 1.15.x; así que, si necesitas Kubernetes 1.37 o quieres pasar a 1.15, consulta primero la [matriz de compatibilidad de v1.15](https://karpenter.sh/v1.15/upgrading/compatibility/) y la guía de actualización. Consulta las [notas de la versión v1.15.0](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.0) para obtener más información.

## Clases de nodo {#node-classes}

Las clases de nodo definen la configuración de los nodos que aprovisiona Karpenter. En AWS, utiliza el CRD EC2NodeClass.

### Configuración de AWS EC2NodeClass

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  tags:
    karpenter.sh/discovery: my-cluster
    environment: training
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      deleteOnTermination: true
      encrypted: true
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  userData: '#!/bin/bash

    echo "Hello from Karpenter node!"

    '
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1
    httpTokens: required
```

### Selección de subredes y grupos de seguridad

Las subredes y los grupos de seguridad se seleccionan mediante términos de selección (varios términos se combinan con OR; las etiquetas dentro de un término se combinan con AND):

```yaml
subnetSelectorTerms:
- tags:
    karpenter.sh/discovery: my-cluster
    Name: private-*
securityGroupSelectorTerms:
- tags:
    karpenter.sh/discovery: my-cluster
```

### Configuración de AMI

Karpenter selecciona las AMI mediante `amiSelectorTerms`. Un alias identifica una familia y una versión; **`@latest` no fija una versión** y puede cambiar las AMI resueltas y provocar deriva de configuración. Los ejemplos con `@latest` se incluyen para aprendizaje. Antes de un despliegue en producción, resuelve y prueba una versión concreta de AMI con soporte (`al2023@vYYYYMMDD`, con una fecha real de publicación) o ID de AMI aprobados. No se publican AMI de EKS basadas en AL2 para Kubernetes 1.33 o posterior. Las variantes siguientes son alternativas. Una AMI personalizada necesita que funcionen el arranque inicial, el taint de registro, kubelet, el CNI, el runtime y la configuración de identidad.

```yaml
# Amazon Linux 2023
amiSelectorTerms:
  - alias: al2023@latest
---
# Bottlerocket
amiSelectorTerms:
  - alias: bottlerocket@latest
---
# Custom AMI (by ID): amiFamily is required when no alias term is used
amiFamily: Custom
amiSelectorTerms:
  - id: "ami-0123456789abcdef0"
# Ubuntu: no v1 alias; use amiFamily: Custom with an id/tags/name term
```

### Configuración de dispositivos de bloque

Las asignaciones de dispositivos dependen de la familia de AMI. Estos ejemplos de AL2023 usan /dev/xvda para el dispositivo raíz; inspecciona la distribución real para otras AMI. Los volúmenes adicionales requieren un plan explícito de sistema de archivos/montaje o almacenamiento de la aplicación. Una clave KMS administrada por el cliente también requiere los permisos adecuados para la clave/IAM.

Puedes definir la configuración de almacenamiento de los nodos:

```yaml
blockDeviceMappings:
- deviceName: /dev/xvda
  ebs:
    volumeSize: 100Gi
    volumeType: gp3
    iops: 3000
    throughput: 125
    deleteOnTermination: true
    encrypted: true
    kmsKeyID: arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab
- deviceName: /dev/xvdb
  ebs:
    volumeSize: 500Gi
    volumeType: gp3
    deleteOnTermination: true
    encrypted: true
```

### Configuración de datos de usuario

Estos fragmentos de datos de usuario ejecutados por shell presuponen AL2023. Karpenter combina su configuración generada de arranque y nodeadm con los datos personalizados. No son instrucciones genéricas de arranque válidas para Bottlerocket o Windows. Incorpora los paquetes a una AMI y pruébalos, en lugar de ejecutar una actualización sin restricciones en cada lanzamiento. Instalar e iniciar CloudWatch Agent no basta para recopilar telemetría: también necesita su configuración, permisos de IAM y conectividad.

```yaml
userData: |
  #!/bin/bash
  set -euo pipefail
  # Only for a workload that requires this setting; keep node packages in a tested AMI.
  cat > /etc/sysctl.d/99-workload-map-count.conf <<'EOF'
  vm.max_map_count=262144
  EOF
  sysctl -p /etc/sysctl.d/99-workload-map-count.conf
```

### Proceso de consolidación de nodos

El siguiente diagrama muestra el proceso de consolidación de nodos de Karpenter. Esta característica es importante para optimizar la eficiencia del clúster y reducir costos:

![Consolidación conceptual: simular si las cargas de trabajo caben en la capacidad existente o de reemplazo, dejar listo cualquier reemplazo necesario y, después, desalojar y recrear los Pods antes de terminar los nodos antiguos aptos. No es una migración de Pods en vivo ni garantiza un resultado de tres a uno.](../.gitbook/assets/en-autoscaling-02-karpenter-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-2.html)

## Gestión de interrupciones {#interruption-handling}

La gestión de interrupciones configurada intenta reaccionar antes de que se pierda capacidad. Las notificaciones, la capacidad de reemplazo, los plazos de apagado y la recuperación de las aplicaciones determinan el resultado; no se garantiza la disponibilidad ininterrumpida.

### Gestión integrada de interrupciones

La gestión de interrupciones de la nube es independiente de la consolidación/expiración. Incluye señales como:

1. **Avisos de interrupción de Spot**: iniciar el drenaje y solicitar capacidad de reemplazo cuando sea posible. El intervalo de aviso no garantiza un SLA de recuperación.
2. **Eventos programados de estado o mantenimiento**: reaccionar ante las instancias afectadas.
3. **Eventos de detención o terminación de instancias**: ajustar la capacidad que deja de estar disponible.
4. **Fallos de estado de instancias EC2**: comprobar su estado con los permisos necesarios para la API de EC2. Las recomendaciones de rebalanceo se publican como eventos; por sí solas no provocan automáticamente la aplicación de taints, el drenaje ni la terminación.

### Configuración de gestión de interrupciones

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default

      # Node expiration settings
      expireAfter: 720h  # 30 days
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### Configuración del vaciado

Karpenter normalmente utiliza la API de desalojo durante el drenaje gradual. Los ajustes de Helm configuran el controlador. Los presupuestos de interrupción de NodePool limitan el inicio de la consolidación y de los cambios por deriva voluntarios; no limitan todas las pérdidas simultáneas de nodos. Un presupuesto del 30 % se redondea hacia arriba y después descuenta los nodos que se están eliminando o que no están listos. No constituye un máximo estricto del 30 %. La expiración, las interrupciones y las reparaciones pueden aplicar otros mecanismos de terminación forzada. Antes de habilitar `interruptionQueue`, configura la cola SQS indicada, las reglas y destinos de EventBridge, la política de la cola y los permisos del controlador. El campo de Helm no crea esos recursos.

```yaml
settings:
  clusterName: my-cluster
  interruptionQueue: my-cluster
  batchMaxDuration: 10s
  batchIdleDuration: 1s
  featureGates:
    spotToSpotConsolidation: false
controller:
  resources:
    requests:
      cpu: 1
      memory: 1Gi
    limits:
      cpu: '1'
      memory: 1Gi
logLevel: info
```

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 720h
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
      - nodes: "30%"   # Voluntary budget: round up, then subtract deleting/not-ready nodes
```

### Integración con PDB (PodDisruptionBudget)

Los PDB limitan las expulsiones voluntarias según el número de réplicas en buen estado; no crean réplicas ni garantizan la disponibilidad de la aplicación. El `minAvailable: 2` de abajo requiere suficientes Pods coincidentes y en buen estado antes de permitir una expulsión. La pérdida de instancias y los plazos de terminación forzada aún pueden interrumpirlos.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: default
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```

## Integración {#integration}

Karpenter se integra con varios servicios de Kubernetes y de la nube.

### Integración con Kubernetes

#### 1. Restricciones de distribución de topología de Pods

Karpenter tiene en cuenta las restricciones de distribución de topología de Pods al aprovisionar nodos:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
  namespace: default
spec:
  replicas: 10
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-server
      containers:
      - name: web-server
        image: nginx:1.30.6
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 256Mi
    metadata:
      labels:
        app: web-server
  selector:
    matchLabels:
      app: web-server
```

#### 2. Afinidad/antiafinidad de Pods

Karpenter tiene en cuenta las reglas de afinidad y antiafinidad de Pods:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
  namespace: default
spec:
  replicas: 10
  template:
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - web-server
            topologyKey: kubernetes.io/hostname
      containers:
      - name: web-server
        image: nginx:1.30.6
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 256Mi
    metadata:
      labels:
        app: web-server
  selector:
    matchLabels:
      app: web-server
```

#### 3. Taints y tolerancias

El ejemplo de GPU requiere una AMI acelerada compatible, un controlador de NVIDIA y un DaemonSet de device-plugin que tolere el taint de GPU y anuncie nvidia.com/gpu. El Pod BusyBox solo demuestra la reserva de una GPU; no ejecuta ni evalúa el rendimiento de CUDA. Valida por separado la imagen real de tu aplicación de GPU.

Karpenter tiene en cuenta los taints y las tolerancias al aprovisionar nodos:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu
spec:
  template:
    spec:
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g4dn.xlarge
        - g4dn.2xlarge
      taints:
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gpu-app
  namespace: default
spec:
  replicas: 3
  template:
    spec:
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      nodeSelector:
        karpenter.sh/nodepool: gpu
      containers:
      - name: gpu-allocation-demo
        image: busybox:1.38.0
        command:
        - sh
        - -c
        - sleep 3600
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            memory: 128Mi
            nvidia.com/gpu: 1
    metadata:
      labels:
        app: gpu-app
  selector:
    matchLabels:
      app: gpu-app
```

### Integración con AWS

#### 1. Instancias EC2 Spot

Karpenter admite instancias EC2 Spot para optimizar costos:

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
        values:
        - spot
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: spot
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: spot
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

#### 2. Perfiles de instancia EC2

role e instanceProfile son mutuamente excluyentes. Con role, Karpenter administra un perfil de instancia y necesita los permisos y la conectividad correspondientes para la API de IAM. Si el clúster no puede acceder al endpoint de IAM, utiliza un instanceProfile aprovisionado previamente; IAM no dispone de un endpoint de PrivateLink. El controlador sigue necesitando PassRole para el rol de nodo. Disponer de credenciales de EC2 no concede por sí solo acceso de los nodos a EKS.

Karpenter utiliza perfiles de instancia EC2 para asignar permisos de IAM a los nodos:

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  instanceProfile: KarpenterNodeInstanceProfile-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
```

#### 3. Reemplazo de las plantillas de lanzamiento (EC2NodeClass)

Karpenter v1 no acepta plantillas de lanzamiento de EC2 proporcionadas por el usuario (se eliminó el campo heredado `launchTemplate`). Karpenter genera y administra sus propias plantillas de lanzamiento a partir de EC2NodeClass, por lo que la configuración que habrías incluido en una plantilla de lanzamiento se expresa directamente en EC2NodeClass:

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: node-config
spec:
  role: KarpenterNodeRole-my-cluster
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  userData: '#!/bin/bash

    echo "Hello from Karpenter node!"

    '
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      deleteOnTermination: true
      encrypted: true
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1
    httpTokens: required
```
## Integración con Amazon EKS {#integration-with-amazon-eks}

El proveedor de AWS de Karpenter puede aprovisionar capacidad de EC2 junto con los recursos de cómputo administrados por EKS cuando se configuran la identidad, la red, el acceso de los nodos y el bootstrap.

![Diagrama de arquitectura que muestra el controlador de Karpenter en un clúster de Amazon EKS asumiendo un rol de IAM para llamar directamente a la API de EC2, sin pasar por Auto Scaling Groups ni Managed Node Groups, para crear instancias EC2.](../.gitbook/assets/en-autoscaling-02-karpenter-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-3.html)

### Preparación del clúster de EKS

Sustituye todos los nombres de ejemplo de forma coherente. Selecciona solo subredes/grupos de seguridad adecuados para nodos de trabajo; etiquetar todas las subredes del plano de control no es una estrategia segura de descubrimiento. Verifica las rutas de subredes, las reglas de seguridad, la capacidad de direcciones IP del CNI y los endpoints privados necesarios antes de permitir el lanzamiento de nodos.

#### 1. Configuración de etiquetas del clúster

Configura tu infraestructura para etiquetar únicamente las subredes y los grupos de seguridad de nodos de trabajo aprobados. Las etiquetas de VPC no son las que seleccionan esos recursos. Los valores de descubrimiento deben coincidir con los ejemplos (aquí, `my-cluster`); las etiquetas por sí solas no demuestran que haya enrutamiento privado, reglas de seguridad adecuadas o suficientes direcciones libres. Inspecciona los recursos y las rutas reales antes de aplicar un NodePool.

```bash
# Inspect resources that your infrastructure configuration has tagged for this cluster.
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws ec2 describe-subnets --region "$AWS_REGION" \
  --filters "Name=tag:karpenter.sh/discovery,Values=${CLUSTER_NAME}" \
  --query 'Subnets[].{ID:SubnetId,AZ:AvailabilityZone,FreeIPs:AvailableIpAddressCount,PublicIPOnLaunch:MapPublicIpOnLaunch,VPC:VpcId}'
aws ec2 describe-security-groups --region "$AWS_REGION" \
  --filters "Name=tag:karpenter.sh/discovery,Values=${CLUSTER_NAME}" \
  --query 'SecurityGroups[].{ID:GroupId,VPC:VpcId,Name:GroupName}'
# Inspect explicit and main route-table associations for the intended subnets.
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --filters "Name=vpc-id,Values=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --query cluster.resourcesVpcConfig.vpcId --output text)"
```

#### 2. Configuración del rol de IAM

Utiliza la política del controlador y la referencia de infraestructura específicas de la versión que aparecen a continuación. La política manual anterior era incompleta y demasiado permisiva. Las credenciales del controlador, obtenidas mediante IRSA en este ejemplo, son independientes de las credenciales de los nodos y de las identidades del VPC CNI y de las cargas de trabajo. La relación de confianza debe coincidir con el proveedor OIDC del clúster, `system:serviceaccount:karpenter:karpenter` y `aud: sts.amazonaws.com`. Concede únicamente las acciones, los recursos y las condiciones necesarios para esta versión y las funciones elegidas. El rol de nodo debe estar autorizado a unirse a EKS, normalmente mediante una entrada de acceso `EC2_LINUX` cuando se utiliza autenticación basada en API. Los comandos de inspección no crean roles de IAM ni entradas de acceso.

```bash
# Download a versioned reference for review; this does not create a CloudFormation stack.
KARPENTER_VERSION="1.14.1"
curl --fail --show-error --location \
  "https://raw.githubusercontent.com/aws/karpenter-provider-aws/v${KARPENTER_VERSION}/website/content/en/preview/getting-started/getting-started-with-karpenter/cloudformation.yaml" \
  --output karpenter-cloudformation-reference.yaml
# Inspect the existing role's attached and inline policies.
: "${CLUSTER_NAME:?Set the existing cluster name}"
aws iam list-attached-role-policies --role-name "KarpenterControllerRole-${CLUSTER_NAME}"
aws iam list-role-policies --role-name "KarpenterControllerRole-${CLUSTER_NAME}"
```

### Instalación de Karpenter en un clúster de EKS

```bash
# Run only after the prerequisites and the current kubectl context are verified.
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${ACCOUNT_ID:?Set the AWS account ID}"
: "${CLUSTER_ENDPOINT:?Set the matching EKS endpoint}"
KARPENTER_VERSION="1.14.1"
helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "$KARPENTER_VERSION" \
  --namespace karpenter --create-namespace \
  --set-string 'serviceAccount.annotations.eks\.amazonaws\.com/role-arn'="arn:aws:iam::${ACCOUNT_ID}:role/KarpenterControllerRole-${CLUSTER_NAME}" \
  --set-string settings.clusterName="$CLUSTER_NAME" \
  --set-string settings.clusterEndpoint="$CLUSTER_ENDPOINT" \
  --set-string settings.interruptionQueue="$CLUSTER_NAME" \
  --wait --timeout 5m
```

### Uso con grupos de nodos administrados de EKS

Karpenter puede coexistir con grupos de nodos administrados de EKS. El siguiente NodePool aprovisiona nodos EC2 independientes; no administra el grupo de nodos administrado. Mantén el controlador en una capacidad de arranque fiable (el chart predeterminado excluye los nodos de Karpenter y solicita dos réplicas en hosts distintos).

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: managed-ng
spec:
  template:
    metadata:
      labels:
        managed-by: karpenter
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.large
        - m5.xlarge
      taints:
      - key: managed-by
        value: karpenter
        effect: NoSchedule
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: managed-ng
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: managed-ng
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
  tags:
    karpenter.sh/discovery: my-cluster
```

### Uso con EKS Fargate

Fargate no implementa topologySpreadConstraints de Kubernetes, y tampoco aplica sus reglas de afinidad y antiafinidad. Las restricciones de ubicación en EC2 del chart predeterminado no garantizan que los Pods de Fargate estén separados entre zonas de disponibilidad. Diseña y verifica por separado la selección de perfiles y subredes.

Un perfil de Fargate con una selección limitada puede alojar los Pods del controlador, mientras Karpenter aprovisiona nodos EC2. Karpenter no crea capacidad de Fargate ni administra sus perfiles. Prepara un perfil que seleccione el espacio de nombres `karpenter` y las etiquetas del controlador, en lugar de incluir todo `default`/`kube-system`; la estructura del selector JSON es `[{"namespace":"karpenter","labels":{"app.kubernetes.io/name":"karpenter"}}]`. El perfil necesita su propio rol de ejecución de Pod/subredes privadas, y los permisos de AWS del controlador siguen necesitando IRSA (EKS Pod Identity no es compatible con Fargate). El siguiente comando solo inspecciona un perfil existente.

```bash
# Inspect an existing, narrowly selected controller Fargate profile.
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-fargate-profile --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --fargate-profile-name karpenter-controller
```

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ec2
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: ec2
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: ec2
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

### Respuesta ante fallos de AZ: integración con Zonal Shift de Amazon ARC (mayo de 2026)

Karpenter puede integrarse con un recurso de cambio de zona de EKS ARC habilitado. Una vez activo un cambio de zona manual o un cambio automático configurado, Karpenter evita nueva capacidad en la AZ afectada. No detecta por sí solo todos los fallos de AZ ni anula los requisitos de un Pod/PV que fijen la carga de trabajo a esa AZ.

Mientras el cambio de zona esté activo, se detienen las interrupciones voluntarias en la AZ afectada. También se impiden las interrupciones en zonas sanas que requieran trasladar Pods a esa AZ. Esto no suspende de forma incondicional todas las interrupciones voluntarias en todas las zonas sanas. Configura los requisitos previos de EKS y ARC, los permisos `eks:DescribeCluster` y de ARC, y `settings.enableZonalShift: true` (opción de entorno `ENABLE_ZONAL_SHIFT`). El cambio automático exige además habilitarlo y configurar sus pruebas correspondientes. No se necesita ningún CRD personalizado de ARC. Las operaciones se reanudan cuando termina el cambio de zona.

### Optimización de costos de EKS

Puedes usar Karpenter para optimizar los costos de los clústeres de EKS:

![Comparación conceptual del escalado de grupos de nodos y la selección dinámica de capacidad, la consolidación y las opciones Spot de Karpenter. No se establece ninguna clasificación universal o basada en mediciones de la velocidad de escalado ni del ahorro de costos.](../.gitbook/assets/en-autoscaling-02-karpenter-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-4.html)

#### 1. Uso de instancias Spot

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
        values:
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: spot
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: spot
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

#### 2. Uso de diversos tipos de instancia

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: flexible
spec:
  template:
    spec:
      requirements:
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
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.large
        - m5.xlarge
        - m5.2xlarge
        - m6g.large
        - m6g.xlarge
        - m6g.2xlarge
        - c5.large
        - c5.xlarge
        - c5.2xlarge
        - c6g.large
        - c6g.xlarge
        - c6g.2xlarge
        - r5.large
        - r5.xlarge
        - r5.2xlarge
        - r6g.large
        - r6g.xlarge
        - r6g.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

#### 3. Habilitación de la consolidación de nodos

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
```

## Prácticas recomendadas {#best-practices}

![Cuatro listas paralelas de prácticas recomendadas de Karpenter, agrupadas por categoría: optimización del rendimiento, optimización de costos, mejora de la disponibilidad y refuerzo de la seguridad.](../.gitbook/assets/en-autoscaling-02-karpenter-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-5.html)

### Optimización del rendimiento

1. **Selecciona los tipos de instancia adecuados**: elige tipos de instancia apropiados para tus cargas de trabajo
2. **Permite diversos tipos de instancia**: permite varios tipos de instancia para optimizar la disponibilidad y los costos
3. **Establece un TTL adecuado**: establece un TTL que se ajuste a los patrones de tus cargas de trabajo
4. **Habilita la consolidación de nodos**: habilita la consolidación de nodos para optimizar la utilización de recursos

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: optimized
spec:
  template:
    spec:
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.large
        - m5.xlarge
        - m5.2xlarge
        - c5.large
        - c5.xlarge
        - c5.2xlarge
        - r5.large
        - r5.xlarge
        - r5.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 720h
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### Optimización de costos

1. **Aprovecha las instancias Spot**: usa instancias Spot para reducir costos
2. **Selecciona tamaños de instancia adecuados**: elige tamaños de instancia apropiados para tus cargas de trabajo
3. **Evalúa la eliminación de nodos vacíos**: los NodePools de nodos de trabajo aptos pueden reducirse a cero; los costos de cómputo del controlador/arranque y los demás costos del clúster permanecen.
4. **Planifica la renovación de nodos**: la expiración rota la capacidad apta según las restricciones actuales; no elige automáticamente tipos de instancia más nuevos ni actualiza una AMI fijada.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 168h
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### Mejora de la disponibilidad

1. **Usa varias zonas de disponibilidad**: despliega nodos en varias zonas de disponibilidad
2. **Combina instancias On-demand y Spot**: equilibra la disponibilidad y los costos
3. **Establece PDB adecuados**: protege frente a expulsiones voluntarias dentro de los límites reales de réplicas en buen estado, junto con un diseño de redundancia y recuperación.
4. **Configura y prueba la gestión de interrupciones**: valida las rutas de notificación, los plazos de apagado y la capacidad de reemplazo sin suponer que el servicio será ininterrumpido.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: high-availability
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - us-west-2a
        - us-west-2b
        - us-west-2c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 720h
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 60s
```

## Solución de problemas {#troubleshooting}

### Problemas comunes

#### 1. Error al aprovisionar nodos

**Síntoma**: los Pods permanecen en estado Pending y no se aprovisionan nodos

**Solución**:
- Comprueba los registros de Karpenter
- Verifica los permisos de IAM
- Comprueba la configuración de NodePool

```bash
# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller

# Check NodePool status
kubectl describe nodepool <name>

# Check pod events
kubectl describe pod <name>
```

#### 2. Problemas al eliminar nodos

**Síntoma**: los nodos no se eliminan como se esperaba

**Solución**:
- Comprueba la configuración de TTL
- Verifica la configuración de consolidación de nodos
- Comprueba el estado del vaciado de los pods

```bash
# Check node status
kubectl describe node <name>

# Check node labels
kubectl get node <name> --show-labels

# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller --since=30m
```

#### 3. Problemas de selección del tipo de instancia

**Síntoma**: se aprovisionan tipos de instancia inesperados

**Solución**:
- Comprueba los requisitos de NodePool
- Verifica las solicitudes de recursos del pod
- Comprueba las restricciones de zona de disponibilidad

```bash
# Check NodePool requirements
kubectl get nodepool <name> -o yaml

# Check pod resource requests
kubectl describe pod <name>

# Check node information
kubectl describe node <name>
```

### Herramientas de depuración

```bash
# Check Karpenter version
kubectl get deployment -n karpenter karpenter -o jsonpath="{.spec.template.spec.containers[0].image}"

# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller

# Check NodePool list
kubectl get nodepools

# Check EC2NodeClass list
kubectl get ec2nodeclasses

# Check events
kubectl get events --sort-by='.lastTimestamp'

# Inspect the installed chart version and values before any optional log-level change.
helm list --namespace karpenter --filter '^karpenter$'
helm get values karpenter --namespace karpenter
kubectl get nodeclaims -o wide
```

## Conclusión

Karpenter automatiza el aprovisionamiento de nodos y su ciclo de vida según las restricciones de las cargas de trabajo y la infraestructura. Puede mejorar la gestión de capacidad, pero los resultados de disponibilidad, rendimiento y costos requieren una verificación específica para cada carga de trabajo.

Este documento abordó los conceptos básicos de Karpenter, los métodos de instalación, la configuración de NodePool y EC2NodeClass, la gestión de interrupciones, diversas integraciones, la integración con Amazon EKS, las prácticas recomendadas y la solución de problemas.

Con Karpenter, puedes simplificar la gestión del clúster, optimizar la utilización de recursos y reducir costos. En especial, en entornos de Kubernetes administrados en la nube como Amazon EKS, puedes aprovechar al máximo las ventajas de Karpenter.

### Próximos pasos

- Implementa estrategias de optimización de costos con Karpenter
- Configura NodePools para distintos tipos de carga de trabajo
- Diseña arquitecturas de clúster híbridas
- Integra Karpenter con otras herramientas de Kubernetes
- Desarrolla estrategias avanzadas de gestión del ciclo de vida de nodos

## Referencias

- [Documentación oficial de Karpenter](https://karpenter.sh/)
- [Repositorio del proveedor AWS de Karpenter](https://github.com/aws/karpenter-provider-aws)
- [Taller de Amazon EKS - Karpenter](https://www.eksworkshop.com/docs/autoscaling/compute/karpenter/)
- [Blog de AWS - Karpenter](https://aws.amazon.com/blogs/aws/introducing-karpenter-an-open-source-high-performance-kubernetes-cluster-autoscaler/)
- [Prácticas recomendadas de Karpenter](https://aws.github.io/aws-eks-best-practices/karpenter/)
- [Versiones de Karpenter en GitHub](https://github.com/aws/karpenter-provider-aws/releases)
- [Novedades de AWS - Compatibilidad con Zonal Shift de ARC en Karpenter](https://aws.amazon.com/about-aws/whats-new/2026/05/karpenter-arc-zonal-shift/)
- [Novedades de AWS - Compatibilidad con warm pools de grupos de nodos administrados de Amazon EKS](https://aws.amazon.com/about-aws/whats-new/2026/04/amazon-eks-managed-node-groups-ec2-warm-pools/)

## Cuestionario

Para comprobar lo que has aprendido en este capítulo, intenta responder el [cuestionario del tema](../quizzes/autoscaling/06-karpenter-quiz.md).

Referencias principales verificadas para esta revisión: [Compatibilidad](https://karpenter.sh/v1.14/upgrading/compatibility/), [NodePool](https://karpenter.sh/v1.14/concepts/nodepools/), [EC2NodeClass](https://karpenter.sh/v1.14/concepts/nodeclasses/), [Interrupciones](https://karpenter.sh/v1.14/concepts/disruption/), [Política de soporte](https://github.com/aws/karpenter-provider-aws/blob/main/SUPPORT.md), [Valores de Helm fijados](https://github.com/aws/karpenter-provider-aws/blob/v1.14.1/charts/karpenter/values.yaml), [Taints de preparación](https://github.com/kubernetes-sigs/karpenter/commit/05431485c90c76a3a662b678a46c1a8da330038d), [Opción DRA fijada](https://github.com/kubernetes-sigs/karpenter/blob/6e7eab7a0f48/pkg/operator/options/options.go), [IAM de nodos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html), [Perfiles de Fargate](https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html).
