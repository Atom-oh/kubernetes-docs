# Cuestionario sobre la creación de clústeres EKS - Parte 4

Este cuestionario evalúa tu comprensión de temas avanzados de configuración, escalabilidad y operación relacionados con la creación de clústeres de Amazon EKS. Cubre temas como el escalado de clústeres, la automatización, la optimización de costos y las mejores prácticas operativas.

## Preguntas de conceptos básicos

1. ¿Cuál es la principal diferencia entre Cluster Autoscaler y Karpenter en un clúster de Amazon EKS?
   * A) Cluster Autoscaler es un servicio de AWS, mientras que Karpenter es una herramienta de código abierto
   * B) Cluster Autoscaler escala a nivel de node group, mientras que Karpenter aprovisiona nodes individuales que coinciden con los requisitos de la carga de trabajo
   * C) Cluster Autoscaler escala según el uso de CPU/memoria, mientras que Karpenter escala según la cantidad de pods
   * D) Cluster Autoscaler solo admite escalado horizontal, mientras que Karpenter también admite escalado vertical

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Cluster Autoscaler escala a nivel de node group, mientras que Karpenter aprovisiona nodes individuales que coinciden con los requisitos de la carga de trabajo**

**Explicación:** La principal diferencia entre Cluster Autoscaler y Karpenter en un clúster de Amazon EKS radica en su enfoque de escalado. Cluster Autoscaler escala a nivel de node group basándose en Auto Scaling Groups (ASG) existentes, mientras que Karpenter aprovisiona directamente nodes individuales que coinciden con los requisitos de la carga de trabajo.

**Características de Cluster Autoscaler:**

1. **Escalado basado en Node Group**:
   * Escala usando Auto Scaling Groups predefinidos
   * Usa el mismo tipo de instancia o tipos de instancia mixtos dentro de un node group
   *   Ejemplo:

       ```yaml
       # Cluster Autoscaler Deployment
       apiVersion: apps/v1
       kind: Deployment
       metadata:
         name: cluster-autoscaler
         namespace: kube-system
       spec:
         replicas: 1
         selector:
           matchLabels:
             app: cluster-autoscaler
         template:
           metadata:
             labels:
               app: cluster-autoscaler
           spec:
             containers:
             - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
               name: cluster-autoscaler
               command:
               - ./cluster-autoscaler
               - --v=4
               - --stderrthreshold=info
               - --cloud-provider=aws
               - --skip-nodes-with-local-storage=false
               - --expander=least-waste
               - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
       ```
2. **Cómo funciona**:
   * Escala hacia arriba los node groups cuando hay pods que no se pueden programar
   * Escala hacia abajo los node groups cuando la utilización de los nodes es baja
   * Opera dentro de los límites mínimo/máximo de tamaño del ASG
3. **Limitaciones**:
   * Velocidad de escalado relativamente lenta (2-10 minutos)
   * Limitado a tipos de instancia predefinidos
   * Solo puede escalar a nivel de node group

**Características de Karpenter:**

1. **Aprovisionamiento basado en la carga de trabajo**:
   * Selecciona tipos de instancia óptimos que coinciden con los requisitos de la carga de trabajo
   * Aprovisiona directamente instancias EC2 sin ASG
   *   Ejemplo:

       ```yaml
       # Karpenter Provisioner
       apiVersion: karpenter.sh/v1alpha5
       kind: NodePool
       metadata:
         name: default
       spec:
         template:
           spec:
             requirements:
               - key: karpenter.sh/capacity-type
                 operator: In
                 values: ["spot", "on-demand"]
               - key: kubernetes.io/arch
                 operator: In
                 values: ["amd64", "arm64"]
           - key: node.kubernetes.io/instance-type
             operator: In
             values: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m6g.large"]
         limits:
           resources:
             cpu: 1000
             memory: 1000Gi
         provider:
           subnetSelector:
             karpenter.sh/discovery: "true"
           securityGroupSelector:
             karpenter.sh/discovery: "true"
         ttlSecondsAfterEmpty: 30
       ```
2. **Cómo funciona**:
   * Analiza los requisitos de los pods que no se pueden programar
   * Selecciona tipos de instancia óptimos que coinciden con los requisitos
   * Aprovisiona directamente instancias y programa pods
   * Termina automáticamente los nodes cuando están vacíos
3. **Ventajas**:
   * Velocidad de escalado rápida (menos de 1 minuto)
   * Selecciona tipos de instancia optimizados para las cargas de trabajo
   * Optimización de costos (uso de instancias Spot, dimensionamiento correcto)
   * Configuración simplificada (no se necesita gestión de ASG)

**Comparación de ambas herramientas:**

| Característica           | Cluster Autoscaler                  | Karpenter                                    |
| ------------------------ | ----------------------------------- | -------------------------------------------- |
| Unidad de escalado       | Node Group (ASG)                    | Node individual                              |
| Selección de instancia   | Tipos de instancia predefinidos     | Instancias óptimas para los requisitos de la carga de trabajo |
| Velocidad de escalado    | Lenta (2-10 minutos)                | Rápida (menos de 1 minuto)                   |
| Complejidad de configuración | Media (se requiere configuración de ASG) | Baja (solo se necesita la definición de Provisioner) |
| Optimización de costos   | Limitada                            | Alta (selección de instancias optimizada para la carga de trabajo) |
| Madurez                  | Alta (proyecto más antiguo)         | Media (proyecto relativamente nuevo)         |

**Problemas con las otras opciones:**

* **Cluster Autoscaler es un servicio de AWS, mientras que Karpenter es una herramienta de código abierto**: Ambas son herramientas de código abierto. Cluster Autoscaler es gestionado por Kubernetes SIG Autoscaling y, aunque Karpenter fue iniciado por AWS, es un proyecto de código abierto.
* **Cluster Autoscaler escala según el uso de CPU/memoria, mientras que Karpenter escala según la cantidad de pods**: Ambos escalan fundamentalmente en función de pods que no se pueden programar (estado Pending). El escalado basado en uso de CPU/memoria es la función de Horizontal Pod Autoscaler (HPA).
* **Cluster Autoscaler solo admite escalado horizontal, mientras que Karpenter también admite escalado vertical**: Ambos solo admiten escalado horizontal (aumento de la cantidad de nodes). El escalado vertical (aumento de recursos de nodes) no es compatible. El escalado vertical a nivel de pod es la función de Vertical Pod Autoscaler (VPA).

Tanto Cluster Autoscaler como Karpenter son herramientas para el escalado automático de clústeres EKS, pero Karpenter proporciona un escalado más rápido y flexible, y puede seleccionar instancias óptimas que coinciden con los requisitos de la carga de trabajo.

</details>

2. ¿Cuáles son los tipos de capacidad válidos que se pueden usar al crear un node group en un clúster de Amazon EKS?
   * A) Reserved, On-Demand, Spot
   * B) On-Demand, Spot, Dedicated
   * C) On-Demand, Spot
   * D) Standard, Burstable, Compute-Optimized

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) On-Demand, Spot**

**Explicación:** Al crear un node group de Amazon EKS, los tipos de capacidad disponibles son On-Demand y Spot.

**Tipo de capacidad On-Demand:**

* **Características**: Instancias disponibles de forma confiable y sin interrupción
* **Precios**: Pagas una tarifa fija por hora
* **Cargas de trabajo adecuadas**:
  * Aplicaciones de producción sensibles a interrupciones
  * Cargas de trabajo con estado
  * Bases de datos
  * Aplicaciones empresariales críticas

**Tipo de capacidad Spot:**

* **Características**: Utiliza capacidad sobrante de AWS; puede interrumpirse cuando AWS reclama la capacidad
* **Precios**: Hasta un 90% de descuento en comparación con On-Demand
* **Cargas de trabajo adecuadas**:
  * Aplicaciones tolerantes a fallos
  * Cargas de trabajo sin estado
  * Trabajos de procesamiento por lotes
  * Entornos de desarrollo/prueba

**Ejemplo de especificación del tipo de capacidad al crear un EKS Node Group:**

Ejemplo de AWS CLI:

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-spot-nodegroup \
  --scaling-config minSize=3,maxSize=10,desiredSize=5 \
  --subnets subnet-0a1b2c3d4e5f6g7h8 subnet-0a1b2c3d4e5f6g7h9 \
  --instance-types t3.medium t3a.medium \
  --capacity-type SPOT \
  --node-role arn:aws:iam::123456789012:role/EKS-NodeInstanceRole
```

Ejemplo de eksctl:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
nodeGroups:
  - name: ng-on-demand
    instanceType: m5.large
    desiredCapacity: 3
    capacityType: ON_DEMAND
  - name: ng-spot
    instanceType: m5.large
    desiredCapacity: 2
    capacityType: SPOT
    spotInstancePools: 3
```

**Problemas con las otras opciones:**

* **Reserved, On-Demand, Spot**: "Reserved" se refiere a EC2 Reserved Instances, pero no puede especificarse directamente como tipo de capacidad al crear node groups de EKS. Reserved Instances es un modelo de descuento de facturación y no puede seleccionarse directamente como tipo de capacidad de un node group.
* **On-Demand, Spot, Dedicated**: "Dedicated" se refiere a EC2 Dedicated Instances, pero no puede especificarse directamente como tipo de capacidad de un node group de EKS. Dedicated Instances puede configurarse mediante ajustes de tenancy separados.
* **Standard, Burstable, Compute-Optimized**: Estos representan tipos de familias de instancias EC2, no tipos de capacidad. Son características que se consideran al seleccionar tipos de instancia (por ejemplo, t3.medium, m5.large, c5.xlarge).

**Mejores prácticas:**

1. **Usar una estrategia de capacidad mixta**:
   * Coloca las cargas de trabajo críticas en node groups On-Demand
   * Coloca las cargas de trabajo tolerantes a fallos en node groups Spot
   * Controla la ubicación de las cargas de trabajo usando node affinity y tolerations
2. **Consideraciones al usar instancias Spot**:
   * Especifica varios tipos de instancia (distribuye el riesgo de interrupción)
   * Implementa mecanismos adecuados de manejo de interrupciones (Pod Disruption Budgets, hooks de apagado ordenado)
   * Despliega AWS Node Termination Handler
3. **Optimización de costos**:
   * Aplica Savings Plans o Reserved Instances a nodes On-Demand
   * Considera instancias Graviton (ARM)
   * Selecciona tamaños de instancia adecuados

</details>

3. ¿Qué se debe especificar obligatoriamente al configurar un perfil de Fargate en un clúster de Amazon EKS?
   * A) Tipo de instancia y tipo de capacidad
   * B) Namespace y selector de labels
   * C) Subnet ID y security group
   * D) Configuración de autoscaling y número máximo de pods

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Namespace y selector de labels**

**Explicación:** Al configurar un perfil de Fargate de Amazon EKS, los elementos obligatorios que se deben especificar son el namespace y, opcionalmente, el selector de labels. EKS usa esta información para determinar qué pods deben ejecutarse en Fargate.

**Componentes del perfil de Fargate:**

1. **Componentes requeridos**:
   * **Nombre del perfil**: Identificador único para el perfil de Fargate
   * **Pod Execution Role**: Rol de IAM requerido para ejecutar pods en la infraestructura de Fargate
   * **Subnets**: Subnets privadas donde se ejecutarán los pods de Fargate (usa las subnets del clúster de forma predeterminada)
   * **Selectores**: Array compuesto por namespaces y labels opcionales
2. **Configuración del selector**:
   * **Namespace**: Namespace de Kubernetes al que pertenece el pod (requerido)
   * **Labels**: Labels de Kubernetes en pares clave-valor (opcionales)

**Ejemplos de creación de perfiles de Fargate:**

Ejemplo de AWS CLI:

```bash
aws eks create-fargate-profile \
  --cluster-name my-cluster \
  --fargate-profile-name my-fargate-profile \
  --pod-execution-role-arn arn:aws:iam::123456789012:role/AmazonEKSFargatePodExecutionRole \
  --subnets subnet-0a1b2c3d4e5f6g7h8 subnet-0a1b2c3d4e5f6g7h9 \
  --selectors namespace=default,labels={app=nginx} namespace=kube-system,labels={k8s-app=kube-dns}
```

Ejemplo de eksctl:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
  - name: fp-default
    selectors:
      - namespace: default
        labels:
          app: nginx
      - namespace: kube-system
        labels:
          k8s-app: kube-dns
```

**Cómo funcionan los perfiles de Fargate:**

1. Cuando se crea un pod, EKS comprueba el namespace y las labels del pod.
2. Si el namespace y las labels del pod coinciden con los selectores de un perfil de Fargate, ese pod se ejecuta en la infraestructura de Fargate.
3. Si no existe un perfil de Fargate coincidente, el pod se programa en nodes EC2 (si están disponibles) o permanece en estado Pending.

**Problemas con las otras opciones:**

* **Tipo de instancia y tipo de capacidad**: Fargate es un servicio de cómputo serverless, por lo que no es necesario especificar tipos de instancia ni tipos de capacidad. AWS aprovisiona automáticamente los recursos de cómputo necesarios.
* **Subnet ID y security group**: Aunque se necesita el Subnet ID, se pueden usar las subnets del clúster como valores predeterminados. Los security groups son opcionales; si no se especifican, se usan los security groups del clúster.
* **Configuración de autoscaling y número máximo de pods**: Fargate escala automáticamente por pod, por lo que no se necesita configuración de autoscaling separada. La cantidad de pods se gestiona mediante Kubernetes Deployments o HPA (Horizontal Pod Autoscaler).

**Consideraciones al usar Fargate:**

1. **Costo**: Con Fargate, solo pagas por los recursos de vCPU y memoria que realmente se usan. No hay costo por nodes inactivos.
2. **Limitaciones**:
   * Los pods de DaemonSet no son compatibles con Fargate.
   * Los contenedores privilegiados no son compatibles.
   * Los modos de red del host como HostNetwork y HostPort no son compatibles.
   * Para volúmenes persistentes, solo se admite Amazon EFS.
3. **Casos de uso**:
   * Trabajos de procesamiento por lotes
   * Aplicaciones web
   * Servidores API
   * Microservices
   * Entornos de desarrollo/prueba

</details>

4. ¿Cuál de los siguientes NO es un elemento configurable en la "configuración de actualización" al actualizar un node group en un clúster de Amazon EKS?
   * A) Cantidad máxima de nodes no disponibles
   * B) Porcentaje máximo de nodes no disponibles
   * C) Estrategia de reemplazo de nodes
   * D) Tiempo de espera de actualización del node group

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Estrategia de reemplazo de nodes**

**Explicación:** "Estrategia de reemplazo de nodes" no es un elemento de configuración oficial en la configuración de actualización de node groups de Amazon EKS. Los node groups gestionados de EKS usan un enfoque de rolling update de forma predeterminada, y no existe una opción para cambiar directamente esta estrategia.

**Elementos configurables en la configuración de actualización de EKS Node Group:**

1. **maxUnavailable**:
   * Número máximo de nodes que pueden no estar disponibles simultáneamente durante la actualización
   * Puede especificarse como un número absoluto (por ejemplo, 1, 2, 3) o como porcentaje (por ejemplo, 20%)
   * Predeterminado: 1
2. **maxUnavailablePercentage**:
   * Porcentaje máximo de nodes que pueden no estar disponibles simultáneamente durante la actualización
   * Se especifica como un valor entre 1 y 100
   * No puede usarse junto con `maxUnavailable`
3. **force**:
   * Si se debe forzar la actualización del node group
   * Predeterminado: false
4. **Timeout**:
   * Tiempo máximo de espera para la operación de actualización del node group
   * Predeterminado: 60 minutos

**Ejemplos de configuración de actualización de Node Group:**

Ejemplo de AWS CLI:

```bash
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config maxUnavailable=2
```

O especificando un porcentaje:

```bash
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config maxUnavailablePercentage=20
```

Ejemplo de eksctl:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: my-nodegroup
    updateConfig:
      maxUnavailable: 2
```

**Proceso de actualización de Node Group:**

1. **Inicio de la actualización**: AWS inicia la actualización del node group.
2. **Node Draining**: Según la configuración de `maxUnavailable`, se aplican cordon y drain al número especificado de nodes.
3. **Terminación de nodes**: Termina los nodes drenados.
4. **Creación de nuevos nodes**: Crea nodes con la nueva configuración.
5. **Repetición**: Repite los pasos 2-4 hasta que todos los nodes estén actualizados.

**Explicación de las otras opciones:**

* **Cantidad máxima de nodes no disponibles (maxUnavailable)**: Configuración válida para especificar el número máximo de nodes que pueden no estar disponibles simultáneamente durante la actualización.
* **Porcentaje máximo de nodes no disponibles (maxUnavailable)**: Configuración válida para especificar el porcentaje máximo de nodes que pueden no estar disponibles simultáneamente durante la actualización.
* **Tiempo de espera de actualización del node group**: Configuración válida para especificar el tiempo máximo de espera para la operación de actualización del node group.

**Mejores prácticas de actualización de Node Group:**

1. **Establecer un valor maxUnavailable adecuado**:
   * Un valor demasiado pequeño prolonga el tiempo de actualización.
   * Un valor demasiado grande puede afectar la disponibilidad de la aplicación.
   * Establécelo considerando las características de la carga de trabajo y el tamaño del node group.
2. **Configurar Pod Disruption Budgets (PDB)**:
   * Configura PDB para cargas de trabajo críticas a fin de garantizar una disponibilidad mínima.
   *   Ejemplo:

       ```yaml
       apiVersion: policy/v1
       kind: PodDisruptionBudget
       metadata:
         name: app-pdb
       spec:
         minAvailable: 2  # or maxUnavailable: 1
         selector:
           matchLabels:
             app: my-app
       ```
3. **Probar antes de actualizar**:
   * Valida en un entorno de prueba antes de actualizaciones críticas.
   * Prepara un plan de rollback.
4. **Monitoreo**:
   * Monitorea el estado de la aplicación durante la actualización.
   * Pausa o revierte la actualización si ocurren problemas.

</details>

5. ¿Qué afirmación es correcta sobre "omitir" versiones al actualizar versiones de Kubernetes en un clúster EKS?
   * A) Se pueden omitir versiones menores, pero no versiones mayores
   * B) Se pueden omitir versiones mayores, pero no versiones menores
   * C) No se pueden omitir versiones mayores ni menores
   * D) Se pueden omitir tanto versiones mayores como menores

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) No se pueden omitir versiones mayores ni menores**

**Explicación:** Al actualizar un clúster de Amazon EKS, tanto las versiones mayores como las menores deben actualizarse secuencialmente. No se admite omitir versiones.

**Reglas de actualización de versiones de EKS:**

1. **Se requiere actualización secuencial**:
   * Cada versión de Kubernetes debe actualizarse secuencialmente desde la versión anterior.
   * Ejemplo: 1.22 -> 1.23 -> 1.24 (no se puede actualizar directamente de 1.22 a 1.24)
2. **Rutas de actualización compatibles**:
   * Solo se puede actualizar desde la versión actual a la siguiente versión menor
   * Las versiones mayores también deben actualizarse secuencialmente
3. **Diferencia de versión entre Control Plane y Node**:
   * El control plane puede estar hasta 2 versiones menores por delante de los nodes
   * Los nodes pueden estar hasta 1 versión menor por delante del control plane

**Proceso de actualización de versiones de EKS:**

1. **Establecer un plan de actualización**:
   * Revisa los cambios entre las versiones actual y objetivo
   * Verifica la compatibilidad de las aplicaciones
   * Establece el cronograma de actualización y el plan de rollback
2. **Orden de actualización recomendado**:
   * Actualización del control plane
   * Actualizaciones de add-ons (CoreDNS, kube-proxy, VPC CNI, etc.)
   * Actualizaciones de node groups
3.  **Ejemplos de comandos de actualización**:

    Actualización del control plane usando AWS CLI:

    ```bash
    aws eks update-cluster-version \
      --name my-cluster \
      --kubernetes-version 1.24
    ```

    Actualización del control plane usando eksctl:

    ```bash
    eksctl upgrade cluster \
      --name=my-cluster \
      --version=1.24 \
      --approve
    ```

    Actualización de node group:

    ```bash
    aws eks update-nodegroup-version \
      --cluster-name my-cluster \
      --nodegroup-name my-nodegroup
    ```

**Política de soporte de versiones de EKS:**

1. **Período de soporte**:
   * Cada versión de Kubernetes cuenta con soporte durante aproximadamente 14 meses después de su lanzamiento en EKS.
   * AWS siempre mantiene soporte para al menos 4 versiones de Kubernetes en producción.
2. **Aviso de fin de soporte**:
   * AWS lo anuncia aproximadamente 60 días antes de que finalice el soporte de una versión.
   * Después de que finaliza el soporte, los clústeres siguen operando, pero no recibirán parches de seguridad ni correcciones de errores.
3. **Ciclo de lanzamiento de versiones**:
   * AWS normalmente admite nuevas versiones en EKS dentro de 2-3 meses después del lanzamiento upstream de Kubernetes.

**Mejores prácticas de actualización:**

1. **Actualizar primero en un entorno de prueba**:
   * Valida en un clúster de prueba antes de actualizar el entorno de producción
2. **Hacer backup antes de actualizar**:
   * Backup de etcd y backup YAML de recursos importantes
3. **Actualización gradual**:
   * Avanza gradualmente en lugar de actualizar todos los node groups a la vez
4. **Verificar después de la actualización**:
   * Confirma que las cargas de trabajo funcionen normalmente
   * Revisa los sistemas de monitoreo
   * Revisa los logs
5. **Mantener la versión más reciente**:
   * Establece un cronograma regular de actualización
   * Haz seguimiento de las fechas de fin de soporte

**Problemas con las otras opciones:**

* **Se pueden omitir versiones menores, pero no versiones mayores**: Las versiones menores tampoco pueden omitirse. Debe actualizarse secuencialmente.
* **Se pueden omitir versiones mayores, pero no versiones menores**: Las versiones mayores tampoco pueden omitirse. Debe actualizarse secuencialmente.
* **Se pueden omitir tanto versiones mayores como menores**: En EKS no se admite omitir versiones.

</details>

## Preguntas de respuesta corta

6. ¿Qué se requiere para cambiar el tipo de instancia de un node group en un clúster EKS?

<details>

<summary>Respuesta y explicación</summary>

Para cambiar el tipo de instancia de un node group gestionado de EKS, debes crear un nuevo node group y migrar las cargas de trabajo, luego eliminar el node group existente. Los tipos de instancia de los node groups gestionados no se pueden cambiar directamente después de su creación.

El procedimiento general es el siguiente:

1. Crear un nuevo node group con el tipo de instancia deseado
2. Configurar Pod Disruption Budgets (PDB) si es necesario
3. Aplicar cordon y drain a los nodes existentes para migrar las cargas de trabajo a los nuevos nodes
4. Verificar que todas las cargas de trabajo se hayan movido al nuevo node group
5. Eliminar el node group existente

Si usas node groups autogestionados, puedes actualizar el launch template del Auto Scaling Group y realizar un instance refresh.

</details>

7. ¿Qué ajustes deben cambiarse para deshabilitar el acceso público al servidor de la API de Kubernetes y permitir solo acceso privado en un clúster EKS?

<details>

<summary>Respuesta y explicación</summary>

Para deshabilitar el acceso público al servidor de la API de un clúster EKS y permitir solo acceso privado, debes cambiar la configuración de acceso al endpoint del clúster:

1. Mediante AWS Management Console:
   * Navega a la consola de EKS
   * Selecciona el clúster
   * Selecciona la pestaña "Networking"
   * Haz clic en "Edit" en la sección "Cluster endpoint access"
   * Configura como "Private" (deshabilitar el acceso público, habilitar el acceso privado)
2. Usando AWS CLI:

```bash
aws eks update-cluster-config \
    --region region-code \
    --name cluster-name \
    --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
```

Después de cambiar esta configuración, solo se puede acceder al servidor de la API de Kubernetes desde dentro de la VPC. Por lo tanto, solo los sistemas dentro de la VPC o las redes conectadas a la VPC pueden gestionar el clúster.

</details>

8. ¿Cuál es el período de soporte típico para las versiones de Kubernetes disponibles en un clúster EKS?

<details>

<summary>Respuesta y explicación</summary>

Cada versión de Kubernetes en Amazon EKS normalmente cuenta con soporte durante aproximadamente 14 meses después de su lanzamiento. AWS se esfuerza por admitir siempre al menos 4 versiones de Kubernetes en producción.

El ciclo de soporte de versiones de EKS es el siguiente:

1. Lanzamiento inicial: AWS pone a disposición una nueva versión de Kubernetes en EKS
2. Soporte estándar: Se proporcionan parches de seguridad y correcciones de errores durante aproximadamente 14 meses
3. Anuncio de fin de soporte: AWS lo anuncia aproximadamente 60 días antes de que finalice el soporte de la versión
4. Fin de soporte: Los clústeres que ejecutan versiones obsoletas no se actualizan automáticamente, sino que deben actualizarse manualmente

AWS comienza a admitir nuevas versiones un poco después de los lanzamientos de la comunidad de Kubernetes, pero el período de soporte suele ser más largo. El proyecto upstream de Kubernetes admite cada versión durante aproximadamente 9 meses, mientras que EKS la admite durante aproximadamente 14 meses.

</details>

## Preguntas prácticas

9. Explica cómo configurar los ajustes de Auto Scaling para un node group en un clúster EKS y escribe una configuración que cumpla con los siguientes requisitos:

* Cantidad mínima de nodes: 2
* Cantidad máxima de nodes: 10
* Cantidad deseada de nodes: 3
* Escalar hacia fuera según la utilización de CPU (cuando la utilización de CPU supere el 75%)
* Escalar hacia fuera según la utilización de memoria (cuando la utilización de memoria supere el 80%)

<details>

<summary>Respuesta y explicación</summary>

Para configurar los ajustes de Auto Scaling para un node group de EKS, sigue estos pasos:

1. Primero, configura el tamaño básico al crear el node group o en la configuración del Auto Scaling Group del node group existente:

```bash
aws eks create-nodegroup \
    --cluster-name my-cluster \
    --nodegroup-name my-nodegroup \
    --scaling-config minSize=2,maxSize=10,desiredSize=3 \
    # Other required parameters...
```

2. Para el escalado basado en la utilización de CPU y memoria, puedes configurar Cluster Autoscaler o Karpenter, o agregar políticas basadas en alarmas de CloudWatch directamente al Auto Scaling Group.

**Enfoque con Cluster Autoscaler:**

YAML de Deployment de Cluster Autoscaler:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
  labels:
    app: cluster-autoscaler
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
        name: cluster-autoscaler
        resources:
          limits:
            cpu: 100m
            memory: 300Mi
          requests:
            cpu: 100m
            memory: 300Mi
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
        - --balance-similar-node-groups
        - --skip-nodes-with-system-pods=false
```

**Políticas de Auto Scaling basadas en alarmas de CloudWatch:**

Política de scale out basada en la utilización de CPU:

```bash
aws autoscaling put-scaling-policy \
    --auto-scaling-group-name my-nodegroup-xxx \
    --policy-name cpu-scale-out \
    --policy-type TargetTrackingScaling \
    --target-tracking-configuration file://cpu-policy.json
```

cpu-policy.json:

```json
{
  "TargetValue": 75.0,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ASGAverageCPUUtilization"
  }
}
```

Política de scale out basada en la utilización de memoria (requiere una métrica personalizada de CloudWatch):

```bash
# First need to set up agent to publish memory utilization as CloudWatch custom metric
aws autoscaling put-scaling-policy \
    --auto-scaling-group-name my-nodegroup-xxx \
    --policy-name memory-scale-out \
    --policy-type TargetTrackingScaling \
    --target-tracking-configuration file://memory-policy.json
```

memory-policy.json:

```json
{
  "TargetValue": 80.0,
  "CustomizedMetricSpecification": {
    "MetricName": "MemoryUtilization",
    "Namespace": "AWS/EC2",
    "Dimensions": [
      {
        "Name": "AutoScalingGroupName",
        "Value": "my-nodegroup-xxx"
      }
    ],
    "Statistic": "Average",
    "Unit": "Percent"
  }
}
```

En entornos reales, usar Cluster Autoscaler es más adecuado para cargas de trabajo de Kubernetes. Cluster Autoscaler escala los nodes basándose en las solicitudes de recursos de los pods, lo que permite un escalado más eficiente.

</details>

## Preguntas avanzadas

10. Explica la estrategia para actualizar node groups usando un enfoque blue/green en un clúster EKS, y presenta los posibles problemas y soluciones que pueden ocurrir durante este proceso.

<details>

<summary>Respuesta y explicación</summary>

#### Estrategia de actualización Blue/Green de EKS Node Group

El despliegue blue/green es un enfoque en el que construyes un nuevo entorno (green) junto al entorno existente (blue) y luego cambias el tráfico al nuevo entorno. Cuando se aplica a node groups de EKS, el proceso avanza de la siguiente manera:

**Pasos de actualización Blue/Green:**

1. **Fase de preparación**:
   * Documentar la configuración actual del node group (labels, taints, tags, etc.)
   * Identificar el estado actual de las cargas de trabajo y los requisitos de recursos
2. **Crear el entorno Green**:
   * Crear un nuevo node group (AMI actualizada, versión de Kubernetes, tipo de instancia, etc.)
   * Aplicar las mismas labels y taints que el node group existente
   * Aplicar la configuración adicional necesaria (tags, roles de IAM, etc.)
3. **Pruebas**:
   * Desplegar cargas de trabajo de prueba en el nuevo node group
   * Validar la funcionalidad y el rendimiento
4. **Transición de tráfico**:
   * Verificar la configuración de Pod Disruption Budget (PDB)
   * Aplicar cordon a los nodes existentes (evitar la programación de nuevos pods)
   * Aplicar drain gradualmente a los nodes existentes (migrar cargas de trabajo a los nuevos nodes)
   * Monitorear el estado de las cargas de trabajo
5. **Finalización y limpieza**:
   * Verificar que todas las cargas de trabajo se hayan movido a los nuevos nodes
   * Eliminar el node group existente
   * Actualizar el monitoreo y las alertas si es necesario

**Posibles problemas y soluciones:**

1. **Problema de escasez de recursos**:
   * **Problema**: Se necesitan el doble de recursos mientras se crea el nuevo node group, lo que podría superar las service quotas
   * **Solución**: Revisar las service quotas con anticipación y solicitar un aumento si es necesario, o actualizar gradualmente en lotes pequeños
2. **Migración de cargas de trabajo con estado**:
   * **Problema**: Las cargas de trabajo con estado que usan volúmenes persistentes pueden tener problemas al moverse entre nodes
   * **Solución**: Verificar la configuración de PVC/PV, usar StatefulSets, usar storage classes adecuadas, realizar backups
3. **Node Affinity y Pod Disruption**:
   * **Problema**: Algunas cargas de trabajo pueden no moverse a los nuevos nodes debido a node affinity o pod anti-affinity
   * **Solución**: Revisar las reglas de node affinity y anti-affinity en las especificaciones de los pods y ajustarlas si es necesario
4. **Network Policies y Security Groups**:
   * **Problema**: Es posible que las network policies o los security groups requeridos no se apliquen al nuevo node group
   * **Solución**: Revisar y replicar la configuración de red, incluidos security groups, network policies y rangos CIDR
5. **Retrasos de DNS y Service Discovery**:
   * **Problema**: Retrasos temporales en la resolución DNS o problemas de service discovery durante la transición de nodes
   * **Solución**: Optimizar la configuración de CoreDNS, ajustar valores TTL, considerar service mesh
6. **Brechas de monitoreo y alertas**:
   * **Problema**: Es posible que los agentes de monitoreo o recolectores de logs no se instalen automáticamente en el nuevo node group
   * **Solución**: Usar herramientas de monitoreo basadas en DaemonSet, incluir scripts de instalación de agentes en el launch template del node group
7. **Falta de plan de rollback**:
   * **Problema**: No hay método de rollback si la actualización falla
   * **Solución**: No eliminar el node group existente de inmediato, mantenerlo durante un período, crear snapshots de estado, documentar procedimientos de rollback

**Ejemplo de implementación (AWS CLI):**

```bash
# 1. Check current node group information
aws eks describe-nodegroup --cluster-name my-cluster --nodegroup-name blue-nodegroup

# 2. Create new node group (green)
aws eks create-nodegroup \
    --cluster-name my-cluster \
    --nodegroup-name green-nodegroup \
    --scaling-config minSize=3,maxSize=10,desiredSize=5 \
    --subnets subnet-xxxx subnet-yyyy \
    --instance-types t3.large \
    --ami-type AL2_x86_64 \
    --node-role arn:aws:iam::123456789012:role/EKS-NodeInstanceRole \
    --labels environment=prod,app=myapp \
    --tags "k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/my-cluster=owned"

# 3. Check node group status
aws eks describe-nodegroup --cluster-name my-cluster --nodegroup-name green-nodegroup

# 4. Cordon existing nodes (using kubectl)
# Get node list
kubectl get nodes -l eks.amazonaws.com/nodegroup=blue-nodegroup

# Cordon each node
kubectl cordon <node-name>

# 5. Drain existing nodes
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# 6. Verify all pods have moved to new nodes
kubectl get pods -o wide

# 7. Delete existing node group
aws eks delete-nodegroup --cluster-name my-cluster --nodegroup-name blue-nodegroup
```

Las actualizaciones blue/green minimizan el downtime y proporcionan capacidad de rollback, pero requieren recursos adicionales y aumentan la complejidad. Se necesita una planificación y pruebas exhaustivas, y se recomienda un enfoque gradual, especialmente para entornos de producción a gran escala.

</details>
