# Cuestionario de introducción a EKS

> **Última actualización**: October 12, 2026

Este cuestionario evalúa su comprensión de los conceptos y las características básicos de Amazon Elastic Kubernetes Service (EKS). Abarca temas como la arquitectura de EKS, los componentes, los métodos de administración y los modelos de precios.

Para los ejemplos de API independientes, establezca `EXAMPLE_CLUSTER`, `EXAMPLE_REGION`, `EXAMPLE_CONTEXT` y las demás variables marcadas en el destino revisado. El ejemplo de IRSA requiere un `EXAMPLE_NAMESPACE` existente, un `APP_POLICY_ARN` limitado al bucket/prefijo requerido y una aplicación que use un AWS SDK compatible con IRSA. Los dos ejercicios usan variables `EKS_INTRO_*` separadas para su clúster dedicado.

## Preguntas de opción múltiple

1. ¿Cuál es el principal beneficio de Amazon EKS (Elastic Kubernetes Service)?
   * A) No es necesario administrar su propia infraestructura de plano de control de Kubernetes
   * B) Tiene un menor costo que otros servicios administrados de Kubernetes
   * C) Solo puede usar servicios de AWS
   * D) Solo puede ejecutarse en una única zona de disponibilidad

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) No es necesario administrar su propia infraestructura de plano de control de Kubernetes**

**Explicación:** El principal beneficio de Amazon EKS (Elastic Kubernetes Service) es que no necesita administrar su propia infraestructura de plano de control de Kubernetes. Puesto que AWS administra la disponibilidad y la escalabilidad del plano de control de Kubernetes, los usuarios pueden centrarse en ejecutar sus cargas de trabajo.

Beneficios principales de EKS:

* **Plano de control administrado**: AWS administra los nodos del plano de control, el clúster etcd, el servidor de API, etc.
* **Alta disponibilidad**: El plano de control regional abarca varias zonas de disponibilidad. La disponibilidad de las cargas de trabajo aún depende de las réplicas, la ubicación, la capacidad y las dependencias.
* **Mantenimiento administrado**: AWS aplica parches al plano de control. Los operadores planifican las actualizaciones de versiones secundarias; también se producen actualizaciones automáticas conforme a la política de soporte de versiones.
* **Integración con servicios de AWS**: Se integra sin problemas con diversos servicios de AWS, incluidos IAM, VPC, ELB, ECR, etc.
* **Kubernetes estándar**: Las API de Kubernetes conformes mejoran la portabilidad; las identidades, el almacenamiento y las integraciones específicos de AWS todavía requieren trabajo de migración.

Problemas de las demás opciones:

* EKS no es necesariamente más económico que otros servicios administrados de Kubernetes. De hecho, hay una tarifa por hora para el plano de control.
* EKS puede ejecutar cualquier aplicación y servicio compatible con Kubernetes, no solo servicios de AWS.
* El plano de control regional de EKS abarca varias zonas de disponibilidad; los usuarios deben distribuir por separado los nodos de trabajo y las réplicas de aplicaciones.

</details>

2. ¿Dónde se implementa el plano de control del clúster de Amazon EKS?
   * A) Dentro de la VPC del usuario
   * B) Se implementa en varias zonas de disponibilidad en una cuenta administrada por AWS
   * C) En una única zona de disponibilidad elegida por el usuario
   * D) Se ejecuta en las instancias EC2 del usuario

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Se implementa en varias zonas de disponibilidad en una cuenta administrada por AWS**

**Explicación:** El plano de control del clúster de Amazon EKS se implementa en varias zonas de disponibilidad en una cuenta administrada por AWS. Este es uno de los aspectos centrales de EKS como servicio administrado.

Características principales de la implementación del plano de control de EKS:

* **Infraestructura administrada por AWS**: El plano de control se ejecuta en una cuenta propiedad de AWS y administrada por AWS.
* **Implementación Multi-AZ**: Los componentes regionales del plano de control de EKS se distribuyen en varias zonas de disponibilidad.
* **Recuperación automática**: AWS supervisa el estado de los componentes del plano de control y reemplaza automáticamente los componentes que fallan.
* **Accesibilidad del endpoint**: Configure acceso público, acceso privado o ambos. El acceso privado también requiere DNS y enrutamiento desde la VPC o las redes conectadas.
* **Escalado automático**: La capacidad estándar del plano de control se ajusta automáticamente; los niveles opcionales de Provisioned Control Plane se seleccionan explícitamente.

Problemas de las demás opciones:

* El plano de control no se implementa dentro de la VPC del usuario. En cambio, se establece una conexión entre la VPC del usuario y la VPC administrada por AWS a través de ENI (Elastic Network Interface).
* El plano de control se implementa en varias zonas de disponibilidad, no en una sola, para garantizar alta disponibilidad.
* El plano de control se ejecuta en infraestructura administrada por AWS, no en las instancias EC2 del usuario.

</details>

3. ¿Qué descripción de la administración de cómputo de EKS es incorrecta?
   * A) Nodos EC2 autoadministrados
   * B) Grupos de nodos administrados
   * C) Perfiles de Fargate
   * D) Bottlerocket como un servicio de cómputo sin servidor independiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Bottlerocket como un servicio de cómputo sin servidor independiente**

Bottlerocket es un sistema operativo para nodos de contenedores, no una opción de ejecución sin servidor independiente.

1. **Nodos autoadministrados**: Los clientes administran los grupos de EC2/Auto Scaling, las AMI, las actualizaciones y la configuración de nodos.
2. **Grupos de nodos administrados**: AWS administra los flujos de trabajo de aprovisionamiento y reemplazo, mientras que los operadores inician las actualizaciones de AMI/versiones. Los tamaños mínimo y máximo por sí solos no habilitan el escalado basado en demanda.
3. **Fargate**: Los perfiles seleccionan Pods para cómputo aislado. Revise las limitaciones, como DaemonSets, GPU y EBS.
4. **EKS Auto Mode**: Una capacidad real de EKS que automatiza el aprovisionamiento, el escalado y el reemplazo de nodos.
5. **Hybrid Nodes**: Conectan máquinas locales/de borde al plano de control administrado por AWS.

Los nodos EC2 convencionales pueden usar Cluster Autoscaler configurado por separado o Karpenter autoadministrado para el escalado basado en demanda.

</details>

4. ¿Cuál es el CNI predeterminado en nodos convencionales de EKS basados en EC2?
   * A) Flannel
   * B) Calico
   * C) AWS VPC CNI
   * D) Weave Net

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) AWS VPC CNI**

**Explicación:** El complemento CNI (Container Network Interface) usado de forma predeterminada para las redes de Pod en clústeres de Amazon EKS es AWS VPC CNI. Este complemento integra directamente las redes de Amazon VPC con los Pods de Kubernetes.

Características principales de AWS VPC CNI:

* **Asignación de direcciones IP nativa de VPC**: Los Pods reciben direcciones IP directamente de la VPC y existen en el mismo espacio de red que los demás recursos de la VPC.
* **Uso de direcciones IP secundarias**: Asigna a los Pods direcciones IP secundarias conectadas a la Elastic Network Interface (ENI) de cada nodo.
* **Integración de grupos de seguridad**: Los grupos de seguridad para Pods requieren instancias compatibles, permisos del controlador de recursos de VPC, configuración de CNI y una SecurityGroupPolicy.
* **Visibilidad de registros de flujo de VPC**: El tráfico de Pod es visible en los registros de flujo de VPC.
* **Aprovechamiento de funciones de red de AWS**: Los Pods pueden utilizar directamente funciones como VPC peering, Transit Gateway y PrivateLink.

AWS VPC CNI es un proyecto de código abierto y puede consultar el código en GitHub: https://github.com/aws/amazon-vpc-cni-k8s

Los CNI alternativos en nodos EC2 requieren su propia revisión de compatibilidad y soporte. Fargate y Auto Mode no admiten el reemplazo arbitrario de CNI; Hybrid Nodes requiere un CNI local compatible. Los Pods `hostNetwork` comparten las redes del nodo.

</details>

5. ¿Cómo concede acceso a la API de Kubernetes de EKS a una identidad de IAM?
   * A) Autenticando cada usuario de IAM solo mediante una ServiceAccount
   * B) Autenticación de IAM con entradas de acceso mediante políticas de acceso y/o Kubernetes RBAC
   * C) Las políticas de IAM de EKS conceden automáticamente permiso para todos los recursos de Kubernetes
   * D) Conectando automáticamente Cognito a cada clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Autenticación de IAM con entradas de acceso mediante políticas de acceso y/o Kubernetes RBAC**

El acceso de IAM a la API de Kubernetes y el acceso de un Pod a las API de AWS son rutas independientes.

1. `aws eks get-token` crea un token de autenticación firmado con credenciales de IAM.
2. EKS autentica la identidad de IAM. Use una **entrada de acceso** para una nueva configuración de acceso.
3. Asocie una política de acceso de EKS o especifique grupos de Kubernetes y cree RoleBindings/ClusterRoleBindings. RBAC y el autorizador de EKS conceden permisos aditivos; si ninguno permite la solicitud, se deniega.
4. El ConfigMap `aws-auth` heredado está obsoleto. No todas las asignaciones existentes se migran automáticamente, así que verifique cada identidad y permiso al pasar a entradas de acceso.

Las políticas de IAM controlan las llamadas a la API de servicio de EKS. Las políticas de acceso de EKS son plantillas de permisos de Kubernetes, no políticas de IAM. IRSA/Pod Identity conceden por separado permisos de AWS a las cargas de trabajo. Los tokens de Kubernetes ServiceAccount y un proveedor de OIDC configurado también pueden autenticar en Kubernetes; IAM no es el único mecanismo de autenticación.

</details>

6. ¿Qué opción utiliza una relación de federación OIDC para conceder credenciales temporales de AWS a una Kubernetes ServiceAccount?
   * A) Conceder roles de IAM a nodos mediante perfiles de instancia EC2
   * B) Incrustar claves de acceso de AWS de larga duración en variables de entorno de Pod
   * C) Vincular roles de IAM a cuentas de servicio de Kubernetes (IRSA)
   * D) Almacenar credenciales de AWS como Kubernetes Secrets y montarlas

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Vincular roles de IAM a cuentas de servicio de Kubernetes (IRSA)**

IRSA intercambia un token de ServiceAccount mediante el proveedor OIDC del clúster por credenciales temporales de AWS. Restrinja la política de confianza al espacio de nombres/ServiceAccount y a `aud=sts.amazonaws.com`. EKS Pod Identity también proporciona credenciales temporales, sin un proveedor OIDC independiente; revise sus requisitos de cómputo, agente y SDK. Este ejemplo muestra el enfoque de IRSA.

Beneficios principales de IRSA:

* **Principio de mínimo privilegio**: Puede conceder únicamente los permisos mínimos necesarios para cada aplicación.
* **Aislamiento de permisos**: Distintos Pods que se ejecutan en el mismo nodo pueden tener distintos permisos de IAM.
* **Administración simplificada de credenciales**: No es necesario administrar directamente las credenciales de AWS.
* **Seguridad mejorada**: Las credenciales no se codifican de forma fija en código o configuración.

Cómo configurar IRSA:

1.  Asocie un proveedor de OpenID Connect (OIDC) con el clúster de EKS:

    ```bash
    eksctl utils associate-iam-oidc-provider --cluster="${EXAMPLE_CLUSTER:?}" --region="${EXAMPLE_REGION:?}" --approve
    ```
2.  Cree un rol de IAM para la cuenta de servicio:

    ```bash
    eksctl create iamserviceaccount \
      --name=app-sa \
      --namespace="${EXAMPLE_NAMESPACE:?}" \
      --cluster="${EXAMPLE_CLUSTER:?}" --region="${EXAMPLE_REGION:?}" \
      --attach-policy-arn="${APP_POLICY_ARN:?Use a reviewed policy scoped to the required bucket/prefix}" \
      --approve
    ```
3.  Haga referencia a la cuenta de servicio en un Pod del mismo espacio de nombres. Esta es una plantilla: sustituya la imagen por su aplicación que usa un SDK compatible con IRSA y aplíquela con `-n "$EXAMPLE_NAMESPACE"`:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: app-sa
      containers:
      - name: my-container
        image: registry.example.com/team/app:reviewed
    ```

Problemas de las demás opciones:

* Los Pods que pueden alcanzar IMDS pueden obtener credenciales de rol de nodo. Restrinja el acceso a IMDS y use roles específicos de carga de trabajo; IRSA por sí solo no bloquea ese acceso.
* Incrustar claves de acceso de larga duración en variables de entorno de Pod aumenta el riesgo de exposición y rotación. Las variables de entorno de proveedores de credenciales de IRSA/Pod Identity son un mecanismo diferente.
* Almacenar credenciales de AWS como Kubernetes Secrets añade carga de administración de credenciales y complica la rotación de credenciales.

</details>

7. ¿Qué afirmación sobre la función de registros de los clústeres de Amazon EKS es correcta?
   * A) Todos los registros se envían a CloudWatch Logs de forma predeterminada
   * B) Los registros del plano de control se pueden enviar opcionalmente a CloudWatch Logs
   * C) Solo los registros de nodos de trabajo se pueden enviar a CloudWatch Logs
   * D) EKS no proporciona funcionalidad de registros

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los registros del plano de control se pueden enviar opcionalmente a CloudWatch Logs**

**Explicación:** En los clústeres de Amazon EKS, los registros del plano de control se pueden enviar opcionalmente a CloudWatch Logs. Esta función está deshabilitada de forma predeterminada y los usuarios pueden elegir habilitar los tipos de registro que necesiten.

Características principales del registro del plano de control de EKS:

* **Activación opcional**: Puede habilitarse durante la creación del clúster o en clústeres existentes.
* **Selección de tipo de registro**: Puede seleccionar únicamente los tipos de registro que necesite de:
  * Servidor de API (api)
  * Auditoría (audit)
  * Autenticador (authenticator)
  * Administrador de controladores (controllerManager)
  * Programador (scheduler)
* **Integración con CloudWatch Logs**: Los registros seleccionados se envían a AWS CloudWatch Logs para almacenamiento, análisis y supervisión.
* **Consideración de costos**: Pueden aplicarse cargos por ingesta, retención y consultas de CloudWatch Logs.

Cómo habilitar los registros:

```bash
# Enable logging using AWS CLI
aws eks update-cluster-config \
    --region "${EXAMPLE_REGION:?}" \
    --name "${EXAMPLE_CLUSTER:?}" \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Enable logging using eksctl
eksctl utils update-cluster-logging --enable-types api,audit,authenticator,controllerManager,scheduler --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" --approve
```

Registro de nodos de trabajo:

* Los registros de nodos de trabajo no se incluyen en la función de registro del plano de control de EKS.
* Para enviar registros de nodos de trabajo a CloudWatch Logs, debe instalar el agente de CloudWatch o configurar una solución de registro como Fluentd/Fluent Bit.

Problemas de las demás opciones:

* No todos los registros se envían a CloudWatch Logs de forma predeterminada. Los usuarios deben habilitarlos explícitamente.
* No es cierto que solo los registros de nodos de trabajo puedan enviarse a CloudWatch Logs; los registros del plano de control también pueden enviarse.
* EKS sí proporciona funcionalidad de registro del plano de control.

</details>

8. ¿Cuál NO es un componente de costo de un clúster de Amazon EKS?
   * A) Tarifa por hora del plano de control de EKS
   * B) Costos de instancias EC2 para nodos de trabajo
   * C) Costos de ejecución de Pods de Fargate
   * D) Tarifas de licencia de Kubernetes

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Tarifas de licencia de Kubernetes**

**Explicación:** Las tarifas de licencia de Kubernetes no son un componente de costo de los clústeres de Amazon EKS. Kubernetes es software de código abierto administrado por Cloud Native Computing Foundation (CNCF) y es gratuito de usar bajo la licencia Apache 2.0. Por lo tanto, no existen tarifas de licencia de Kubernetes separadas al usar EKS.

Los componentes de costo reales de los clústeres de Amazon EKS incluyen:

1. **Tarifa por hora del plano de control de EKS**:
   * El soporte estándar y extendido tienen diferentes tarifas de clúster, con cargos adicionales para niveles opcionales de Provisioned Control Plane.
   * Un clúster de EKS es un recurso regional; una implementación multirregional necesita clústeres y cargos independientes.
   * Contabilice por separado Auto Mode, EKS Capabilities, Hybrid Nodes y los cargos de infraestructura de AWS.
2. **Costos de instancias EC2 para nodos de trabajo**:
   * Se incurren costos por las instancias EC2 utilizadas en grupos de nodos autoadministrados o administrados.
   * Los costos varían según el tipo, tamaño, cantidad y tiempo de ejecución de la instancia.
   * Los costos pueden optimizarse mediante Reserved Instances, Savings Plans y Spot Instances.
3. **Costos de ejecución de Pods de Fargate**:
   * Al usar Fargate, los costos se cobran según los recursos de vCPU y memoria asignados a los Pods.
   * La facturación de Linux Fargate comienza con la descarga de la imagen, se redondea a segundos y tiene un mínimo de un minuto; los recursos solicitados se redondean a configuraciones compatibles.
   * Compare la capacidad total aprovisionada, la utilización y el esfuerzo operativo; ni Fargate ni EC2 son universalmente más económicos.
4. **Costos de recursos adicionales de AWS**:
   * Volúmenes EBS
   * Balanceadores de carga (NLB, ALB)
   * Registros y métricas de CloudWatch
   * NAT Gateway
   * Transferencia de datos

Estrategias de optimización de costos:

* Seleccionar tipos de instancia apropiados
* Configurar el escalado automático
* Usar Spot Instances
* Automatización de clúster y escalado programado
* Optimizar solicitudes y límites de recursos
* Supervisión y análisis de costos

</details>

9. ¿Qué opción proporciona integración declarativa de ALB/NLB en un clúster de EKS convencional sin Auto Mode?
   * A) Usar el balanceador de carga integrado de EKS
   * B) Integrar recursos Kubernetes Service con AWS Load Balancer Controller
   * C) Crear y configurar manualmente balanceadores de carga EC2
   * D) EKS no admite el equilibrio de carga

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Integrar recursos Kubernetes Service con AWS Load Balancer Controller**

**Explicación:** El método correcto para implementar el equilibrio de carga en un clúster de Amazon EKS es integrar recursos Kubernetes Service con AWS Load Balancer Controller. Este enfoque combina la administración declarativa de recursos de Kubernetes con las capacidades de equilibrio de carga de AWS.

Métodos para implementar el equilibrio de carga en EKS:

1.  **Service de tipo LoadBalancer predeterminado**:

    * El controlador seleccionado determina el balanceador de carga. Este ejemplo selecciona explícitamente un AWS LBC instalado y autorizado con `service.k8s.aws/nlb`; la integración heredada puede crear un CLB.

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
    spec:
      type: LoadBalancer
      loadBalancerClass: service.k8s.aws/nlb
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: my-app
    ```
2.  **AWS Load Balancer Controller**:

    * Instale AWS Load Balancer Controller para administrar Application Load Balancer (ALB) y Network Load Balancer (NLB) con funciones más avanzadas.
    * ALB se puede aprovisionar y configurar mediante recursos Ingress.
    * Se pueden configurar diversos atributos del balanceador de carga mediante anotaciones.

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: my-ingress
      annotations:
        alb.ingress.kubernetes.io/scheme: internet-facing
        alb.ingress.kubernetes.io/target-type: ip
    spec:
      ingressClassName: alb
      rules:
      - http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-service
                port:
                  number: 80
    ```
3.  **Anotaciones de Service**:

    * Se pueden agregar anotaciones a los servicios para especificar el tipo y la configuración del balanceador de carga.

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-scheme: internal
        service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    spec:
      type: LoadBalancer
      loadBalancerClass: service.k8s.aws/nlb
      selector:
        app: my-app
      ports:
      - port: 80
        targetPort: 8080
    ```

Problemas de las demás opciones:

* Auto Mode proporciona equilibrio de carga administrado con clases diferentes, incluida `eks.amazonaws.com/nlb`. No requiere instalar AWS LBC en el clúster; no mezcle sus clases ni anotaciones no compatibles.
* Aunque es posible crear y configurar manualmente balanceadores de carga EC2, no se ajusta al enfoque declarativo de Kubernetes y complica la administración.
* EKS admite completamente el equilibrio de carga.

</details>

10. ¿Cuál NO es un método válido para administrar almacenamiento en un clúster de Amazon EKS?
    * A) Aprovisionar volúmenes EBS mediante el controlador EBS CSI
    * B) Montar sistemas de archivos EFS mediante el controlador EFS CSI
    * C) Montar un volumen EBS en un Pod de Fargate
    * D) Conectar sistemas de archivos de alto rendimiento mediante el controlador FSx for Lustre CSI

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Montar un volumen EBS en un Pod de Fargate**

Fargate no puede montar volúmenes EBS. Los nodos EC2 convencionales usan un controlador EBS CSI instalado con permisos de IAM. Auto Mode proporciona aprovisionamiento EBS administrado mediante `ebs.csi.eks.amazonaws.com`, distinto del controlador convencional `ebs.csi.aws.com`.

Los métodos reales para administrar almacenamiento en clústeres de Amazon EKS incluyen:

1.  **Controlador EBS CSI**:

    * Permite conectar volúmenes Amazon EBS (Elastic Block Store) a Pods de Kubernetes.
    * Adecuado para aplicaciones que requieren almacenamiento en bloques (bases de datos, etc.).
    * Admite aprovisionamiento dinámico, instantáneas con un controlador de instantáneas y expansión cuando StorageClass lo permite.
    * EBS tiene alcance de AZ. ReadWriteOnce significa montaje de lectura y escritura desde un nodo, no desde un Pod; varios Pods de ese nodo pueden usar el volumen. El modo de acceso no define su AZ.

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    parameters:
      type: gp3
      encrypted: "true"
    ```
2.  **Controlador EFS CSI**:

    * Permite montar Amazon EFS (Elastic File System) en Pods de Kubernetes.
    * Adecuado para sistemas de archivos compartidos a los que varios Pods deben acceder simultáneamente.
    * Accesible en varias zonas de disponibilidad (modo de acceso ReadWriteMany).
    * Adecuado para servidores web, CMS, canalizaciones CI/CD, etc.

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: efs-sc
    provisioner: efs.csi.aws.com
    parameters:
      provisioningMode: efs-ap
      fileSystemId: fs-0123456789abcdef0
      directoryPerms: "700"
    ```
3.  **Controlador FSx for Lustre CSI**:

    * Permite conectar Amazon FSx for Lustre a Pods de Kubernetes.
    * Adecuado para cargas de trabajo de alto rendimiento, como computación de alto rendimiento, aprendizaje automático y análisis de macrodatos.
    * Proporciona alto rendimiento y baja latencia.

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: fsx-sc
    provisioner: fsx.csi.aws.com
    parameters:
      subnetId: subnet-0123456789abcdef0
      securityGroupIds: sg-0123456789abcdef0
      deploymentType: PERSISTENT_1
      automaticBackupRetentionDays: "1"
      dailyAutomaticBackupStartTime: "00:00"
      perUnitStorageThroughput: "200"
    ```
   Especifique la capacidad en PVC en `spec.resources.requests.storage` (por ejemplo, `1200Gi`), no en un parámetro `storageCapacity` de StorageClass. Revise los incrementos de capacidad específicos de la implementación, las subredes/grupos de seguridad, la compatibilidad de cliente Lustre y los permisos de IAM del controlador.

4. **Otras opciones de almacenamiento**:
   * Amazon S3 (Simple Storage Service) mediante controladores CSI o montadores S3
   * Amazon FSx for Windows File Server
   * Amazon FSx for NetApp ONTAP
   * Soluciones de almacenamiento de terceros (Portworx, Rook, etc.)

Prácticas recomendadas de administración de almacenamiento:

* Seleccionar tipos de almacenamiento apropiados para los requisitos de la carga de trabajo
* Configurar StorageClass para aprovisionamiento dinámico
* Establecer estrategias de copia de seguridad y recuperación
* Supervisar el rendimiento del almacenamiento
* Seleccionar clases y tamaños de almacenamiento apropiados para la optimización de costos

</details>

## Ejercicios prácticos

### Ejercicio 1: Creación y configuración de un clúster de EKS

**Escenario:** Es un ingeniero DevOps en su empresa y necesita configurar un clúster de Amazon EKS para su equipo de desarrollo. El clúster es para el entorno de desarrollo y debe ser rentable, a la vez que proporciona todas las características necesarias.

**Requisitos:**

1. Crear un clúster de EKS rentable
2. Configurar grupos de nodos apropiados
3. Configurar la supervisión básica
4. Configurar el acceso de kubectl al clúster

**Solución:**

<details>
<summary>Mostrar solución</summary>

La ejecución de estos comandos de implementación crea recursos facturables de AWS. No se ejecutaron durante la auditoría. Prepare Bash, una versión actual de AWS CLI v2, kubectl 1.36 y Helm, y use el [procedimiento oficial de instalación de eksctl](https://eksctl.io/installation/) para comprobar la arquitectura de SO/CPU y las sumas de comprobación. El ejemplo se revisó frente al esquema de eksctl 0.230.0 y EKS 1.36; no es una configuración de producción validada.

Ejecute los pasos en una sola shell y deténgase si falla un comando. Establezca `EKS_INTRO_ADMIN_CIDR` en el CIDR IPv4 externo real del cliente aprobado, normalmente `/32`. El nuevo clúster usa nodos privados/acceso de API privado más acceso de API público restringido. Una única NAT gateway es una elección de laboratorio de desarrollo, no un diseño de disponibilidad de producción. El acceso de administrador del creador del clúster es únicamente para inicializar este laboratorio dedicado.

**1. Crear un clúster dedicado**

```bash
# Use a dedicated nonproduction AWS account/role and an approved region.
eksctl version  # Example tool baseline: 0.230.0
aws --version
kubectl version --client
helm version

EKS_INTRO_DIR=$(mktemp -d /tmp/eks-intro.XXXXXX)
: "${EKS_INTRO_DIR:?}"
EKS_INTRO_CLUSTER=$(basename "$EKS_INTRO_DIR" | tr '[:upper:].' '[:lower:]-')
EKS_INTRO_REGION=us-west-2
: "${EKS_INTRO_ADMIN_CIDR:?Set your approved client egress IPv4 CIDR, normally /32}"
EKS_INTRO_KUBECONFIG="$EKS_INTRO_DIR/kubeconfig"
unset EKS_INTRO_CLUSTER_ARN EKS_INTRO_POLICY_ARN
aws sts get-caller-identity

cat > "$EKS_INTRO_DIR/eks-cluster.yaml" << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ${EKS_INTRO_CLUSTER}
  region: ${EKS_INTRO_REGION}
  version: "1.36"
  tags:
    docs-lab: ${EKS_INTRO_CLUSTER}
iam:
  withOIDC: true
accessConfig:
  authenticationMode: API
  bootstrapClusterCreatorAdminPermissions: true
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${EKS_INTRO_ADMIN_CIDR}"]
  nat:
    gateway: Single
managedNodeGroups:
- name: ng-1
  amiFamily: AmazonLinux2023
  instanceType: t3.medium
  privateNetworking: true
  disableIMDSv1: true
  disablePodIMDS: true
  desiredCapacity: 2
  minSize: 1
  maxSize: 3
cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
EOF

# Inspect the file, account, allowed CIDR and projected costs before provisioning.
cat "$EKS_INTRO_DIR/eks-cluster.yaml"
eksctl create cluster -f "$EKS_INTRO_DIR/eks-cluster.yaml" \
  --kubeconfig "$EKS_INTRO_KUBECONFIG" &&
  EKS_INTRO_CLUSTER_ARN=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
    --region "$EKS_INTRO_REGION" --query cluster.arn --output text)
: "${EKS_INTRO_CLUSTER_ARN:?Cluster creation/verification did not complete}"
```

Si la creación falla, inspeccione y elimine las pilas/recursos de CloudFormation con este nombre único antes de reutilizarlo. `minSize`/`maxSize` solo establecen límites; no instalan un escalador de nodos basado en demanda. t3.medium es un ejemplo y requiere revisión de capacidad, créditos de CPU y precio regional.

**2. Kubeconfig dedicado y comprobaciones de conexión**

```bash
aws eks update-kubeconfig --name "${EKS_INTRO_CLUSTER:?}" \
  --region "${EKS_INTRO_REGION:?}" --kubeconfig "${EKS_INTRO_KUBECONFIG:?}"
intro_kubectl() {
  kubectl --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" "$@"
}
intro_kubectl get nodes
intro_kubectl cluster-info
```

**3. Métricas básicas de recursos**

Metrics Server 0.9.x es compatible con Kubernetes 1.34+. Proporciona métricas de recursos, no registros ni supervisión a largo plazo. Verifique los certificados de kubelet y la conectividad de red sin deshabilitar la verificación TLS.

```bash
intro_kubectl get pods -n kube-system

# Fresh lab cluster only: do not overwrite an existing managed installation.
curl -fL https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.9.0/components.yaml \
  -o "${EKS_INTRO_DIR:?}/metrics-server.yaml" &&
  intro_kubectl apply -f "$EKS_INTRO_DIR/metrics-server.yaml"
intro_kubectl rollout status deployment/metrics-server -n kube-system --timeout=180s
intro_kubectl top nodes
```

**4. Instalar AWS Load Balancer Controller**

La política, el controlador y el gráfico están fijados a 3.5.0. Use su rol de IRSA en lugar de conceder permisos de complementos no relacionados a cada nodo. La configuración explícita de región/VPC evita depender del descubrimiento de IMDS. Verifique por separado las etiquetas de subred, los grupos de seguridad y las cuotas de servicio.

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Use the new lab cluster}"
curl -fL https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v3.5.0/docs/install/iam_policy.json \
  -o "${EKS_INTRO_DIR:?}/lbc-policy.json" || exit 1
# Inspect the pinned policy before creating this lab-owned IAM policy.
EKS_INTRO_POLICY_ARN=$(aws iam create-policy \
  --policy-name "${EKS_INTRO_CLUSTER:?}-lbc" \
  --policy-document "file://$EKS_INTRO_DIR/lbc-policy.json" \
  --query Policy.Arn --output text)
: "${EKS_INTRO_POLICY_ARN:?Policy creation failed}"

# iam.withOIDC created the cluster OIDC provider in step1.
eksctl create iamserviceaccount \
  --cluster="$EKS_INTRO_CLUSTER" --region="${EKS_INTRO_REGION:?}" \
  --namespace=kube-system --name=aws-load-balancer-controller \
  --attach-policy-arn="$EKS_INTRO_POLICY_ARN" --approve

EKS_INTRO_VPC_ID=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
  --region "$EKS_INTRO_REGION" --query cluster.resourcesVpcConfig.vpcId --output text)
: "${EKS_INTRO_VPC_ID:?}"
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" install aws-load-balancer-controller \
  eks/aws-load-balancer-controller --version 3.5.0 -n kube-system \
  --set clusterName="$EKS_INTRO_CLUSTER" \
  --set region="$EKS_INTRO_REGION" --set vpcId="$EKS_INTRO_VPC_ID" \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller \
  --wait --timeout 5m
```

**5. Comprobar el estado del clúster**

```bash
intro_kubectl get nodes -o wide
intro_kubectl get pods -n kube-system
intro_kubectl get events --sort-by='.lastTimestamp'
intro_kubectl cluster-info
```

**6. Comprobar una aplicación básica mediante reenvío de puerto local**

```bash
intro_kubectl create namespace intro-smoke
intro_kubectl -n intro-smoke create deployment nginx --image=nginx:1.30.4-alpine
intro_kubectl -n intro-smoke rollout status deployment/nginx --timeout=180s
intro_kubectl -n intro-smoke expose deployment nginx --port=80 --type=ClusterIP
intro_kubectl -n intro-smoke get deployment,service
# Run in a separate terminal using the same dedicated kubeconfig.
kubectl --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" -n intro-smoke \
  port-forward --address 127.0.0.1 service/nginx 8080:80
```

Mientras se ejecuta el reenvío de puerto, abra `http://127.0.0.1:8080`; detenga el reenvío con Ctrl-C. El siguiente ejercicio configura el acceso ALB externo. Use el procedimiento de limpieza después de ambos ejercicios; el comportamiento esperado y los posibles ahorros no son resultados de auditoría medidos.

</details>

### Ejercicio 2: Implementación de aplicaciones y exposición de servicios en un clúster de EKS

**Escenario:** Su equipo ha desarrollado una aplicación web basada en una arquitectura de microservicios. Debe implementar esta aplicación en el clúster de EKS y configurarla para que sea accesible desde el exterior.

**Requisitos:**

1. Implementar servicios de frontend y backend
2. Configurar la comunicación entre servicios
3. Configurar acceso externo mediante el controlador de ingress
4. Configurar escalado básico

**Solución:**

<details>
<summary>Mostrar solución</summary>

Use el clúster dedicado y las variables de shell del ejercicio1, AWS LBC/IngressClass `alb` y un Metrics Server en buen estado. Esta demostración HTTP solo sirve respuestas ficticias públicas y restringe el acceso a ALB al CIDR de cliente seleccionado. No implementa autenticación de aplicación, TLS ni validación de carga de producción.

**1. Crear el espacio de nombres**

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Complete exercise1 first}"
unset EKS_INTRO_WEB_UID
EKS_INTRO_WEB_UID=$(intro_kubectl create namespace web-app -o jsonpath='{.metadata.uid}')
: "${EKS_INTRO_WEB_UID:?Stop if this namespace already exists}"
```

**2. Configurar el backend**

Configure NGINX para escuchar en el puerto80 y devolver JSON ficticio para rutas que incluyen `/api`.

```bash
cat > "${EKS_INTRO_DIR:?}/backend-deployment.yaml" << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: web-app
data:
  default.conf: |
    server {
        listen 80;
        location / {
            default_type application/json;
            return 200 '{"service":"backend","example":true}\n';
        }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: web-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      containers:
      - name: backend
        image: nginx:1.30.4-alpine
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
        volumeMounts:
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: backend-config
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: web-app
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: http
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/backend-deployment.yaml"
```

**3. Configurar el frontend y la comunicación de Service**

La imagen estándar de NGINX no consume `BACKEND_URL`. Esta configuración explícita de NGINX actúa como proxy de `/proxy-api/` a `backend-service`, proporcionando una ruta real de servicio a servicio.

```bash
cat > "${EKS_INTRO_DIR:?}/frontend-deployment.yaml" << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: frontend-config
  namespace: web-app
data:
  default.conf: |
    server {
        listen 80;
        location /proxy-api/ {
            proxy_pass http://backend-service/;
        }
        location / {
            default_type text/plain;
            return 200 'frontend demo\n';
        }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: web-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      automountServiceAccountToken: false
      containers:
      - name: frontend
        image: nginx:1.30.4-alpine
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
        volumeMounts:
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: frontend-config
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: web-app
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: http
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/frontend-deployment.yaml"
```

**4. Crear un Ingress de AWS LBC**

El ALB no elimina `/api` automáticamente; este backend administra la ruta directamente. `/` y `/proxy-api/` van al frontend.

```bash
cat > "${EKS_INTRO_DIR:?}/ingress.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-ingress
  namespace: web-app
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /
    alb.ingress.kubernetes.io/inbound-cidrs: ${EKS_INTRO_ADMIN_CIDR:?}
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/ingress.yaml"
```

**5. Configurar HPA**

La utilización de CPU se mide respecto a las solicitudes. HPA cambia las réplicas de Pod, no el número de nodos, y requiere Metrics Server además de capacidad libre en los nodos.

```bash
cat > "${EKS_INTRO_DIR:?}/hpa.yaml" << 'EOF'
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
  namespace: web-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: web-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/hpa.yaml"
```

**6. Comprobar el enrutamiento y el estado**

Un nombre de host de ALB no demuestra que sus destinos estén en buen estado. Si las solicitudes fallan, inspeccione los eventos, el estado de destino, los grupos de seguridad y el CIDR de cliente.

```bash
intro_kubectl -n web-app rollout status deployment/backend --timeout=180s
intro_kubectl -n web-app rollout status deployment/frontend --timeout=180s
intro_kubectl -n web-app get deployments,services,ingress,hpa
intro_kubectl -n web-app describe ingress web-app-ingress
ALB_ADDRESS=$(intro_kubectl -n web-app get ingress web-app-ingress \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
: "${ALB_ADDRESS:?Wait for ALB provisioning and inspect events}"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/api"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/proxy-api/"
```

**7. Observar carga limitada**

Esta carga de muestra no garantiza superar el objetivo de CPU ni activar HPA. Las respuestas estáticas de NGINX pueden usar poca CPU y las solicitudes a la raíz del frontend no cargan el backend. Observe las métricas, el estado de HPA y los Pods Pending para determinar el escalado real.

```bash
# Only target the lab ALB whose ownership and health you checked above.
: "${ALB_ADDRESS:?}"
ab -n 1000 -c 10 -s 10 "http://$ALB_ADDRESS/"
intro_kubectl -n web-app get hpa
intro_kubectl -n web-app top pods
intro_kubectl -n web-app get events --sort-by='.lastTimestamp'
# Optional observation; Ctrl-C stops watching, not the HPA.
intro_kubectl -n web-app get hpa -w
```

</details>

### Limpiar los recursos del ejercicio

Confirme que la cuenta, el ARN y la etiqueta identifican el clúster de laboratorio dedicado. Elimine los balanceadores de carga de la aplicación antes que el controlador y espere a la finalización. Investigue los errores del controlador si se agota el tiempo de espera en vez de eliminar finalizers.

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Use only the dedicated cluster created in exercise1}"
EKS_INTRO_CLEANUP_READY=false
current_arn=$(aws eks describe-cluster --name "${EKS_INTRO_CLUSTER:?}" \
  --region "${EKS_INTRO_REGION:?}" --query cluster.arn --output text)
current_tag=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
  --region "$EKS_INTRO_REGION" --query 'cluster.tags."docs-lab"' --output text)
if [[ "$current_arn" = "$EKS_INTRO_CLUSTER_ARN" && "$current_tag" = "$EKS_INTRO_CLUSTER" ]]; then
  # Keep the controller running until it removes ALB resources/finalizers.
  intro_kubectl -n web-app delete ingress web-app-ingress --ignore-not-found --wait=true --timeout=180s &&
    intro_kubectl delete namespace web-app intro-smoke --ignore-not-found --wait=true --timeout=180s &&
    EKS_INTRO_CLEANUP_READY=true
else
  printf 'Ownership check failed; stop cleanup and inspect the selected account/cluster\n' >&2
fi
```

Continúe solo después de verificar la propiedad y eliminar correctamente Ingress/el espacio de nombres. Confirme la eliminación de la pila de rol de IAM y la desvinculación de la política antes de eliminarla.

```bash
if [[ ${EKS_INTRO_CLEANUP_READY:-false} = true ]]; then
  helm --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" uninstall aws-load-balancer-controller -n kube-system
  eksctl delete iamserviceaccount --cluster="${EKS_INTRO_CLUSTER:?}" \
    --region="${EKS_INTRO_REGION:?}" --namespace=kube-system --name=aws-load-balancer-controller --approve --wait
  # Wait for the related IAM-role stack deletion to finish before deleting its policy.
  aws iam list-entities-for-policy --policy-arn "${EKS_INTRO_POLICY_ARN:?}"
  # Continue only when no attachment remains.
  aws iam delete-policy --policy-arn "$EKS_INTRO_POLICY_ARN" &&
    eksctl delete cluster --config-file="${EKS_INTRO_DIR:?}/eks-cluster.yaml" --wait
else
  printf 'Complete ownership and load balancer cleanup checks first\n' >&2
fi
```

Verifique la eliminación de CloudFormation y los balanceadores de carga, grupos de seguridad, NAT, EBS y costos de retención de registros restantes. Tome una decisión independiente de retención/eliminación para el grupo de registros de CloudWatch. No suponga que la creación parcial o los recursos fuera de estos pasos se limpiaron automáticamente. Elimine los manifiestos, la política y el kubeconfig del directorio dedicado después del laboratorio.

## Temas avanzados

Las siguientes son preguntas sobre temas avanzados de Amazon EKS. Esta sección evalúa su comprensión de características e integraciones avanzadas de EKS.

1. ¿Cuál es la descripción correcta al configurar un perfil de Fargate en Amazon EKS?
   * A) Los perfiles de Fargate especifican que los Pods deben ejecutarse en Fargate según espacios de nombres y etiquetas específicos
   * B) Los perfiles de Fargate ejecutan automáticamente todos los Pods en Fargate
   * C) Los perfiles de Fargate restringen la ejecución de Pod a tipos de instancia EC2 específicos
   * D) Los perfiles de Fargate establecen cuotas de recursos para todo el clúster

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Los perfiles de Fargate especifican que los Pods deben ejecutarse en Fargate según espacios de nombres y etiquetas específicos**

**Explicación:** Un perfil de Fargate de Amazon EKS es una configuración que especifica qué Pods deben ejecutarse en Fargate según espacios de nombres y etiquetas específicos. Esto permite configurar una arquitectura híbrida que usa tanto entornos de ejecución de contenedores sin servidor como nodos basados en EC2.

Características principales de los perfiles de Fargate:

* **Ejecución selectiva**: Solo los Pods que coinciden con las condiciones definidas en el perfil se ejecutan en Fargate, no todos los Pods.
* **Selectores de espacio de nombres y etiquetas**: Los Pods se seleccionan según combinaciones específicas de espacio de nombres y etiquetas.
* **Especificación de subred**: Puede especificar subredes privadas donde se ejecutarán los Pods.
* **Rol de IAM**: El rol de ejecución de Pod lo usa la infraestructura de Fargate, por ejemplo, para obtener imágenes. Los contenedores de aplicación necesitan su propio rol de IRSA para acceder a API de AWS.

Ejemplo de creación de perfil de Fargate:

```bash
eksctl create fargateprofile \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --name my-fargate-profile \
  --namespace my-namespace \
  --labels app=my-app
```

Definición de perfil de Fargate basada en YAML:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
  - name: my-fargate-profile
    selectors:
      - namespace: my-namespace
        labels:
          app: my-app
      - namespace: another-namespace
```

Consideraciones al usar Fargate:

* DaemonSets no son compatibles con Fargate.
* Los contenedores privilegiados no pueden ejecutarse.
* HostNetwork y HostPort no son compatibles.
* Las cargas de trabajo de GPU no son compatibles.
* Se aplican costos por Pod, por lo que es necesario planificar costos.
* El almacenamiento persistente está disponible mediante volúmenes EFS aprovisionados estáticamente. Los volúmenes EBS y el aprovisionamiento dinámico de EFS no son compatibles con Fargate.

Problemas de las demás opciones:

* Los perfiles de Fargate no ejecutan automáticamente todos los Pods en Fargate; solo se ejecutan los Pods que coinciden con los selectores.
* Los perfiles de Fargate no se relacionan con tipos de instancia EC2; Fargate es un entorno de ejecución de contenedores sin servidor.
* Los perfiles de Fargate no establecen cuotas de recursos para todo el clúster. Las cuotas de recursos se administran mediante Kubernetes ResourceQuota.

</details>

2. ¿Cómo debe planificar una actualización de EKS?
   * A) Actualizar primero los nodos a la versión de destino y revisar la compatibilidad después
   * B) Preparar la compatibilidad/versiones actuales, después plano de control → nodos, coordinando cada actualización de complemento
   * C) Actualizar a ciegas cada complemento a la última versión como preparación completa
   * D) Cambiar todos los componentes simultáneamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Preparar la compatibilidad/versiones actuales, después plano de control → nodos, coordinando cada actualización de complemento**

Primero compruebe las versiones actuales de clúster/nodo, los insights de actualización, las API eliminadas, la compatibilidad de webhook/CRD/complementos, las IP de subred disponibles y el plan de recuperación. Lleve los nodos atrasados a la versión actual del plano de control antes de pasar a la siguiente versión secundaria.

**1. Plano de control**

Avance una versión secundaria cada vez. Los kubelets actuales no pueden ser más nuevos que el servidor de API y pueden tener hasta tres versiones secundarias menos, pero EKS recomienda igualar las versiones antes y después de las actualizaciones. La desviación máxima permitida no es un objetivo de estado estable.

```bash
# Inspect the current version and node versions before choosing the next minor.
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.{version:version,status:status}' --output table
kubectl --context "${EXAMPLE_CONTEXT:?}" get nodes

# Choose one interface, after prerequisite checks and workload testing.
aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?Select the next supported minor}"
# Alternative:
# eksctl upgrade cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --version "$NEXT_MINOR_VERSION" --approve

# Use the update ID returned above. Proceed only after status is Successful.
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "${CONTROL_PLANE_UPDATE_ID:?}" --query update.status
```

**2. Nodos**

Después de que se complete la actualización del plano de control, inicie las actualizaciones de grupos de nodos administrados y compruebe su estado de actualización, la preparación de los nodos y las versiones de kubelet. Los grupos de nodos convencionales no se actualizan automáticamente con el plano de control. Los operadores actualizan nodos autoadministrados/Hybrid Nodes; vuelva a crear Pods de Fargate para usar la nueva versión. AWS actualiza incrementalmente los nodos de Auto Mode.

```bash
aws eks update-nodegroup-version --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
# Alternative:
# eksctl upgrade nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --name "$EXAMPLE_NODEGROUP" --kubernetes-version "$NEXT_MINOR_VERSION"
```

**3. Complementos y clientes**

Revise con antelación la compatibilidad con las versiones actual y de destino. Algunos componentes de CNI, webhook o controlador necesitan actualizaciones compatibles antes del plano de control, por lo que los complementos no son universalmente el último paso. Después de la actualización del plano de control, lleve los complementos restantes, Cluster Autoscaler y kubectl a versiones compatibles y valide cada uno.

```bash
aws eks describe-addon-versions --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}" \
  --query 'addons[].addonVersions[].addonVersion' --output table

# Select a compatible EKS add-on build after reviewing configuration changes.
aws eks update-addon --cluster-name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --addon-version "${REVIEWED_ADDON_VERSION:?}" \
  --resolve-conflicts PRESERVE
```

`PRESERVE` conserva la configuración del usuario; no garantiza compatibilidad. Compruebe PDB, capacidad disponible y terminación ordenada, y no oculte fallos con indicadores force. Valide cada etapa y prepare copias de seguridad restaurables de aplicación/datos. Las copias de seguridad del plano de control de AWS no reemplazan un plan de recuperación de datos del cliente.

EKS ahora admite reversión a la versión secundaria anterior dentro de los siete días posteriores a una actualización elegible completada. Se aplican restricciones de nodos, complementos, cambios de API y política de soporte, y los datos de aplicaciones no se restauran automáticamente. Siga el [procedimiento de actualización](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html) y las [condiciones de reversión](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html).

</details>

3. ¿Cuál NO es una característica clave del complemento VPC CNI en Amazon EKS?
   * A) Asignar direcciones IP de VPC a Pods
   * B) Aplicar grupos de seguridad a nivel de Pod
   * C) Cifrar el tráfico de red entre Pods
   * D) Ampliar direcciones IP mediante delegación de prefijo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Cifrar el tráfico de red entre Pods**

Amazon VPC CNI no proporciona cifrado general del tráfico de Pod a Pod. Configure TLS/mTLS de aplicación o una función de cifrado de mesh/CNI explícitamente compatible. NetworkPolicy solo filtra tráfico; no lo cifra.

Las características clave reales del complemento Amazon VPC CNI incluyen:

1. **Asignar direcciones IP de VPC a Pods**:
   * Los Pods normales reciben IP de VPC; los Pods `hostNetwork` comparten la red del nodo.
   * Esto permite que los Pods se comuniquen directamente con otros recursos de la VPC.
   * Las IP de Pod son enrutables dentro de la VPC, lo que elimina la necesidad de redes de superposición complejas.
2. **Aplicar grupos de seguridad a nivel de Pod**:
   * Los grupos de seguridad de AWS se pueden aplicar a Pods individuales mediante la función SecurityGroupsForPods.
   * Esto permite implementar políticas de seguridad de red detalladas a nivel de Pod.
   *   Ejemplo de configuración:

       ```yaml
       apiVersion: vpcresources.k8s.aws/v1beta1
       kind: SecurityGroupPolicy
       metadata:
         name: my-security-group-policy
         namespace: default
       spec:
         podSelector:
           matchLabels:
             app: my-app
         securityGroups:
           groupIds:
             - sg-0123456789abcdef0
       ```
3. **Ampliar direcciones IP mediante delegación de prefijo**:
   * De forma predeterminada, cada nodo puede asignar un número limitado de direcciones IP (varía según el tipo de instancia) a Pods.
   * Con la función de delegación de prefijo, puede asignar bloques CIDR /28 (16 IP) a cada nodo, aumentando las direcciones IP disponibles.
   * Esto aumenta la capacidad de direcciones por ENI, pero consume direcciones de subred existentes. Requiere prefijos libres contiguos y no crea nueva capacidad de subred.
4. **Redes personalizadas**:
   * Los Pods se pueden colocar en subredes específicas.
   * Las redes de Pod se pueden configurar mediante varias interfaces de red.
5. **Redes de host de Kubernetes**:
   * `hostNetwork` usa la red del nodo; es una configuración de Kubernetes Pod, no una función de cifrado o aislamiento de CNI.
   * Es útil para cargas de trabajo donde el rendimiento de red es crítico.

Aplique las capacidades de VPC CNI por separado después de comprobar sus requisitos previos.

| Configuración | Comprobaciones necesarias |
| --- | --- |
| `ENABLE_PREFIX_DELEGATION` | Instancia/versión de CNI compatible, bloques `/28` libres contiguos, max-pods de kubelet y un plan de transición a nodos nuevos |
| `ENABLE_POD_ENI` | Instancias ENI trunk/branch compatibles, permisos del controlador de recursos de VPC, SecurityGroupPolicy y reglas de DNS/grupo de seguridad |
| `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG` | IPv4, subredes/grupos de seguridad de Pod en la misma VPC/AZ, selección ENIConfig de nodo e IP libres |

Habilitar solo una marca puede hacer que los Pods antiguos/nuevos se comporten de forma diferente o que falle la asignación de IP. Siga el procedimiento oficial de transición sin entrar en conflicto con la configuración de complementos administrados por EKS. No aplique este enfoque convencional de DaemonSet EC2 directamente a Auto Mode, Fargate o Hybrid Nodes.

```bash
# Inspect current non-secret CNI flags; this does not enable any feature.
kubectl --context "${EXAMPLE_CONTEXT:?}" -n kube-system get daemonset aws-node \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="aws-node")].env}{"\n"}'
```


Para implementar el cifrado de tráfico de red entre Pods, considere las siguientes alternativas:

* El soporte de App Mesh finalizó el 30 de septiembre de 2026; los usuarios existentes deben migrar.
* Implementar mesh de servicio Istio
* Usar la función de cifrado transparente de Cilium
* Implementar TLS/mTLS a nivel de aplicación

</details>

4. ¿Cómo puede un rol de IAM de desarrollador recibir acceso de lectura de Kubernetes limitado a un espacio de nombres?
   * A) Adjuntar un Kubernetes Role directamente a un usuario de IAM
   * B) Usar una entrada de acceso de EKS para asignar el rol de IAM a un grupo de Kubernetes y configurar enlaces RBAC
   * C) Adjuntar solo una política S3 al rol de IAM del clúster
   * D) Conceder a un desarrollador acceso de kubectl únicamente mediante una configuración IRSA de ServiceAccount de aplicación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar una entrada de acceso de EKS para asignar el rol de IAM a un grupo de Kubernetes y configurar enlaces RBAC**

Use una **entrada de acceso de EKS** para un nuevo acceso de IAM. El modo de autenticación del clúster debe ser `API` o `API_AND_CONFIG_MAP`. Prepare la migración de asignaciones y una ruta de recuperación de administrador antes de cambiar el modo de un clúster existente. `aws-auth` está obsoleto y no es el único mecanismo de asignación.

Este ejemplo asocia un rol de IAM de desarrollador existente a `dev-readers`. Una identidad de IAM y una entrada de acceso no crean automáticamente objetos Kubernetes RBAC.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster.accessConfig.authenticationMode

aws eks create-access-entry --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --principal-arn "${DEV_ROLE_ARN:?Existing developer IAM role}" \
  --type STANDARD --kubernetes-groups dev-readers
```

Un administrador aplica este Role y RoleBinding en el espacio de nombres existente `dev`. Concede acceso de lectura a Pod/Deployment, sin permisos de Secret ni mutación. Los permisos de creación de carga de trabajo pueden permitir el uso de Secrets de espacio de nombres y requieren revisión independiente.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: dev-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-readers
  namespace: dev
subjects:
- kind: Group
  name: dev-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: dev-reader
  apiGroup: rbac.authorization.k8s.io
```

Con una identidad que pueda asumir el rol, cree un kubeconfig dedicado y verifique los permisos reales. La primera comprobación debe permitir y la segunda debe denegar, salvo que otra concesión RBAC o política de acceso de EKS agregue permiso.

```bash
aws eks update-kubeconfig --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --role-arn "${DEV_ROLE_ARN:?}" --kubeconfig "${DEV_KUBECONFIG:?Use a dedicated file}"
kubectl --kubeconfig "$DEV_KUBECONFIG" auth can-i get pods -n dev
kubectl --kubeconfig "$DEV_KUBECONFIG" auth can-i get secrets -n dev
```

Como alternativa, asocie una política de acceso de EKS limitada al espacio de nombres con la entrada. Las políticas de acceso y las concesiones RBAC son aditivas; adjuntar solo una política de IAM no concede permisos de Kubernetes. IRSA/Pod Identity proporcionan una ruta independiente para que los Pods llamen a las API de AWS. No conceda a desarrolladores comunes `system:masters` ni sobrescriba todo el ConfigMap `aws-auth`.

</details>

5. ¿Qué descripción del soporte de versiones de EKS es correcta?
   * A) Todas las versiones son compatibles indefinidamente
   * B) Todo el soporte termina después de 12 meses
   * C) Siempre exactamente la última versión más las tres versiones anteriores
   * D) 14 meses de soporte estándar más 12 meses de soporte extendido de pago después del lanzamiento de EKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) 14 meses de soporte estándar más 12 meses de soporte extendido de pago después del lanzamiento de EKS**

Una versión secundaria de EKS recibe **14 meses de soporte estándar desde la fecha de lanzamiento de EKS**, seguidos de **12 meses de soporte extendido de pago**. El plazo no comienza en la fecha de lanzamiento upstream.

* Lista oficial al 12 de octubre de 2026: soporte estándar **1.34–1.37**, soporte extendido **1.31–1.33**. EKS 1.37 estuvo disponible el 1 de octubre de 2026, después de su lanzamiento upstream el 26 de agosto.
* El soporte extendido está habilitado de forma predeterminada. Seleccionar la política de actualización `STANDARD` lo desactiva y hace que el clúster esté sujeto a actualización automática al finalizar el soporte estándar.
* Después de que termina el soporte extendido, AWS actualiza automáticamente el plano de control a una versión compatible. El momento exacto de ejecución no está garantizado, por lo que los operadores deben planificar las actualizaciones de forma proactiva.
* Los nodos administrados/autoadministrados/Hybrid Nodes no se actualizan únicamente porque el plano de control se haya actualizado automáticamente. Planifique por separado el reemplazo de Pods de Fargate y las actualizaciones de complementos; los nodos de Auto Mode siguen actualizaciones administradas.
* Las versiones compatibles reciben parches de seguridad; no se admite conservar indefinidamente todas las versiones. No se pueden crear clústeres nuevos en versiones posteriores al fin de soporte.

Compruebe el calendario de lanzamiento y la información de versiones en la región real. Buscar con grep los metadatos de complementos no sustituye a la lista de soporte de versiones de clúster.

```bash
aws eks describe-cluster-versions --region "${EXAMPLE_REGION:?}" --output table
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --query 'cluster.{version:version,upgradePolicy:upgradePolicy}' --output json
```

Mantenga un calendario de actualización, revise las API eliminadas/la compatibilidad, pruebe en un entorno ajeno a producción, prepare recuperación de aplicación/datos y avance una versión secundaria cada vez. EKS ofrece al menos tres versiones con soporte estándar, sin una regla fija de «solo la última más tres».

</details>


## Referencias oficiales y alcance de validación

- [Ciclo de vida de versiones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Entradas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Pod Identity e IRSA](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)
- [Load Balancer Controller](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [Equilibrio de carga de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-configure-nlb.html)
- [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [Configuración de FSx CSI y capacidad de PVC](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi-create.html)
- [Limitaciones de Fargate](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [Delegación de prefijo](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses.html)
- [Redes personalizadas](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network.html)
- [Precios de EKS](https://aws.amazon.com/eks/pricing/)
- [Precios de Fargate](https://aws.amazon.com/fargate/pricing/)
- [Esquema de eksctl 0.230.0](https://github.com/eksctl-io/eksctl/blob/v0.230.0/pkg/apis/eksctl.io/v1alpha5/assets/schema.json)
- [Instalación de LBC 3.5.0](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/installation.md)
- [Compatibilidad de Metrics Server 0.9.0](https://github.com/kubernetes-sigs/metrics-server/blob/v0.9.0/README.md)

Esta es una revisión estática frente a documentación oficial y esquemas de lanzamiento. No se realizó aprovisionamiento de clúster/IAM/balanceador de carga, implementación de aplicación, actualización/reversión, ejecución de NGINX, prueba de carga ni medición de costos. El comportamiento esperado del ejemplo no es un resultado medido.