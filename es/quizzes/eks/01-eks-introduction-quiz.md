# Cuestionario de introducción a EKS

> **Última actualización**: 12 de octubre de 2026

Este cuestionario evalúa tu comprensión de los conceptos básicos y las características de Amazon Elastic Kubernetes Service (EKS). Abarca temas como la arquitectura de EKS, sus componentes, métodos de administración y modelos de precios.

Para los ejemplos independientes de API, establece `EXAMPLE_CLUSTER`, `EXAMPLE_REGION`, `EXAMPLE_CONTEXT` y las demás variables marcadas con el destino revisado. El ejemplo de IRSA requiere un `EXAMPLE_NAMESPACE` existente, un `APP_POLICY_ARN` limitado al bucket/prefijo necesario y una aplicación que use un SDK de AWS compatible con IRSA. Los dos ejercicios utilizan variables `EKS_INTRO_*` distintas para su clúster específico.

## Preguntas de opción múltiple

1. ¿Cuál es la principal ventaja de Amazon EKS (Elastic Kubernetes Service)?
   * A) No es necesario administrar la infraestructura del plano de control de Kubernetes
   * B) Tiene un costo menor que otros servicios de Kubernetes administrados
   * C) Solo se pueden usar servicios de AWS
   * D) Solo se puede ejecutar en una única zona de disponibilidad

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) No es necesario administrar la infraestructura del plano de control de Kubernetes**

**Explicación:** La principal ventaja de Amazon EKS (Elastic Kubernetes Service) es que no necesitas administrar la infraestructura del plano de control de Kubernetes. Como AWS administra la disponibilidad y la escalabilidad del plano de control de Kubernetes, los usuarios pueden centrarse en ejecutar sus cargas de trabajo.

Ventajas principales de EKS:

* **Plano de control administrado**: AWS administra los nodos del plano de control, el clúster de etcd, el servidor de API, etc.
* **Alta disponibilidad**: El plano de control regional se extiende por varias zonas de disponibilidad. La disponibilidad de las cargas de trabajo sigue dependiendo de las réplicas, la ubicación, la capacidad y las dependencias.
* **Mantenimiento administrado**: AWS aplica parches al plano de control. Los operadores planifican las actualizaciones de versiones menores; también se realizan actualizaciones automáticas conforme a la política de soporte de versiones.
* **Integración con los servicios de AWS**: Se integra sin problemas con varios servicios de AWS, como IAM, VPC, ELB, ECR, etc.
* **Kubernetes estándar**: Las API de Kubernetes conformes mejoran la portabilidad; las identidades, el almacenamiento y las integraciones específicos de AWS siguen requiriendo trabajo de migración.

Problemas con las demás opciones:

* EKS no es necesariamente más barato que otros servicios de Kubernetes administrados. De hecho, el plano de control tiene una tarifa por hora.
* EKS puede ejecutar cualquier aplicación o servicio compatible con Kubernetes, no solo servicios de AWS.
* El plano de control regional de EKS se extiende por varias zonas de disponibilidad; los usuarios deben distribuir por separado los nodos de trabajo y las réplicas de las aplicaciones.

</details>

2. ¿Dónde se implementa el plano de control del clúster de Amazon EKS?
   * A) Dentro de la VPC del usuario
   * B) En varias zonas de disponibilidad dentro de una cuenta administrada por AWS
   * C) En una única zona de disponibilidad elegida por el usuario
   * D) En las instancias EC2 del usuario

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) En varias zonas de disponibilidad dentro de una cuenta administrada por AWS**

**Explicación:** El plano de control del clúster de Amazon EKS se implementa en varias zonas de disponibilidad dentro de una cuenta administrada por AWS. Este es uno de los aspectos fundamentales de EKS como servicio administrado.

Características principales de la implementación del plano de control de EKS:

* **Infraestructura administrada por AWS**: El plano de control se ejecuta en una cuenta propiedad de AWS y administrada por AWS.
* **Implementación en varias AZ**: Los componentes regionales del plano de control de EKS se distribuyen entre varias zonas de disponibilidad.
* **Recuperación automática**: AWS supervisa el estado de los componentes del plano de control y reemplaza automáticamente los que fallan.
* **Accesibilidad del endpoint**: Configura el acceso público, el privado o ambos. El acceso privado también requiere DNS y enrutamiento desde la VPC o las redes conectadas.
* **Escalado automático**: La capacidad estándar del plano de control se ajusta automáticamente; los niveles opcionales de Provisioned Control Plane se seleccionan explícitamente.

Problemas con las demás opciones:

* El plano de control no se implementa dentro de la VPC del usuario. En su lugar, se establece una conexión entre la VPC del usuario y la VPC administrada por AWS mediante una ENI (interfaz de red elástica).
* El plano de control se implementa en varias zonas de disponibilidad, no en una sola, para garantizar una alta disponibilidad.
* El plano de control se ejecuta en infraestructura administrada por AWS, no en las instancias EC2 del usuario.

</details>

3. ¿Qué descripción de la administración de recursos de cómputo de EKS es incorrecta?
   * A) Nodos EC2 autoadministrados
   * B) Grupos de nodos administrados
   * C) Perfiles de Fargate
   * D) Bottlerocket como servicio de cómputo sin servidor independiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Bottlerocket como servicio de cómputo sin servidor independiente**

Bottlerocket es un sistema operativo para nodos de contenedores, no una opción de ejecución sin servidor independiente.

1. **Nodos autoadministrados**: Los clientes administran los grupos EC2/Auto Scaling, las AMI, las actualizaciones y la configuración de los nodos.
2. **Grupos de nodos administrados**: AWS administra los flujos de trabajo de aprovisionamiento y reemplazo, mientras que los operadores inician las actualizaciones de AMI/versión. Definir únicamente los tamaños mínimo y máximo no activa el escalado en función de la demanda.
3. **Fargate**: Los perfiles seleccionan Pods para su ejecución en recursos de cómputo aislados. Comprueba las limitaciones, como las de DaemonSets, GPU y EBS.
4. **EKS Auto Mode**: Una capacidad real de EKS que automatiza el aprovisionamiento, el escalado y el reemplazo de nodos.
5. **Nodos híbridos**: Conectan máquinas locales/de borde al plano de control administrado por AWS.

Los nodos EC2 convencionales pueden usar Cluster Autoscaler configurado por separado o Karpenter autoadministrado para escalar según la demanda.

</details>

4. ¿Cuál es la CNI predeterminada en los nodos de EKS convencionales basados en EC2?
   * A) Flannel
   * B) Calico
   * C) AWS VPC CNI
   * D) Weave Net

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) AWS VPC CNI**

**Explicación:** El complemento CNI (Container Network Interface) utilizado de forma predeterminada para la red de Pods en los clústeres de Amazon EKS es AWS VPC CNI. Este complemento integra directamente la red de Amazon VPC con los Pods de Kubernetes.

Características principales de AWS VPC CNI:

* **Asignación de direcciones IP nativas de la VPC**: Los Pods reciben direcciones IP directamente de la VPC y ocupan el mismo espacio de red que los demás recursos de la VPC.
* **Uso de direcciones IP secundarias**: Asigna a los Pods direcciones IP secundarias asociadas a la interfaz de red elástica (ENI) de cada nodo.
* **Integración con grupos de seguridad**: Los grupos de seguridad para Pods requieren instancias compatibles, permisos del controlador de recursos de VPC, configuración de CNI y una SecurityGroupPolicy.
* **Visibilidad en los registros de flujo de VPC**: El tráfico de los Pods es visible en los registros de flujo de VPC.
* **Uso de las características de red de AWS**: Los Pods pueden utilizar directamente características como el emparejamiento de VPC, Transit Gateway y PrivateLink.

AWS VPC CNI es un proyecto de código abierto; puedes consultar el código en GitHub: https://github.com/aws/amazon-vpc-cni-k8s

Las CNI alternativas en nodos EC2 requieren una revisión propia de compatibilidad y soporte. Fargate y Auto Mode no admiten el reemplazo arbitrario de CNI; Hybrid Nodes requiere una CNI local compatible. Los Pods `hostNetwork` comparten la red del nodo.

</details>

5. ¿Cómo se concede a una identidad de IAM acceso a la API de Kubernetes de EKS?
   * A) Autenticando cada usuario de IAM únicamente mediante un ServiceAccount
   * B) Mediante autenticación de IAM con entradas de acceso, usando políticas de acceso o RBAC de Kubernetes, o ambos
   * C) Las políticas de IAM de EKS conceden automáticamente permisos para todos los recursos de Kubernetes
   * D) Conectando automáticamente Cognito a todos los clústeres

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mediante autenticación de IAM con entradas de acceso, usando políticas de acceso o RBAC de Kubernetes, o ambos**

El acceso de IAM a la API de Kubernetes y el acceso de un Pod a las API de AWS son vías independientes.

1. `aws eks get-token` crea un token de autenticación firmado con credenciales de IAM.
2. EKS autentica la identidad de IAM. Para las nuevas configuraciones de acceso, usa una **entrada de acceso**.
3. Asocia una política de acceso de EKS o especifica grupos de Kubernetes y crea RoleBindings/ClusterRoleBindings. RBAC y el autorizador de EKS conceden permisos de forma aditiva; si ninguno permite la solicitud, esta se deniega.
4. El ConfigMap heredado `aws-auth` está obsoleto. No todas las asignaciones existentes se migran automáticamente, así que verifica cada identidad y permiso al pasar a las entradas de acceso.

Las políticas de IAM controlan las llamadas a la API del servicio EKS. Las políticas de acceso de EKS son plantillas de permisos de Kubernetes, no políticas de IAM. IRSA/Pod Identity conceden por separado permisos de AWS a las cargas de trabajo. Los tokens de Kubernetes ServiceAccount y un proveedor OIDC configurado también pueden autenticar en Kubernetes; IAM no es el único mecanismo de autenticación.

</details>

6. ¿Qué opción usa una relación de federación OIDC para conceder credenciales temporales de AWS a un ServiceAccount de Kubernetes?
   * A) Conceder roles de IAM a los nodos mediante perfiles de instancia EC2
   * B) Incrustar claves de acceso de AWS de larga duración en las variables de entorno de los Pods
   * C) Vincular roles de IAM a cuentas de servicio de Kubernetes (IRSA)
   * D) Almacenar credenciales de AWS como Secrets de Kubernetes y montarlas

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Vincular roles de IAM a cuentas de servicio de Kubernetes (IRSA)**

IRSA intercambia un token de ServiceAccount a través del proveedor OIDC del clúster para obtener credenciales temporales de AWS. Limita la política de confianza al espacio de nombres/ServiceAccount y a `aud=sts.amazonaws.com`. EKS Pod Identity también proporciona credenciales temporales, sin un proveedor OIDC independiente; comprueba los requisitos de cómputo, agente y SDK. Este ejemplo muestra el enfoque de IRSA.

Ventajas principales de IRSA:

* **Principio de privilegio mínimo**: Puedes conceder únicamente los permisos mínimos necesarios para cada aplicación.
* **Aislamiento de permisos**: Distintos Pods que se ejecutan en el mismo nodo pueden tener permisos de IAM diferentes.
* **Administración simplificada de credenciales**: No es necesario administrar directamente las credenciales de AWS.
* **Seguridad mejorada**: Las credenciales no se codifican directamente en el código ni en la configuración.

Cómo configurar IRSA:

1.  Asocia un proveedor OpenID Connect (OIDC) al clúster de EKS:

    ```bash
    eksctl utils associate-iam-oidc-provider --cluster="${EXAMPLE_CLUSTER:?}" --region="${EXAMPLE_REGION:?}" --approve
    ```
2.  Crea un rol de IAM para la cuenta de servicio:

    ```bash
    eksctl create iamserviceaccount \
      --name=app-sa \
      --namespace="${EXAMPLE_NAMESPACE:?}" \
      --cluster="${EXAMPLE_CLUSTER:?}" --region="${EXAMPLE_REGION:?}" \
      --attach-policy-arn="${APP_POLICY_ARN:?Use a reviewed policy scoped to the required bucket/prefix}" \
      --approve
    ```
3.  Haz referencia a la cuenta de servicio en un Pod del mismo espacio de nombres. Esta es una plantilla: sustituye la imagen por la de tu aplicación, que debe usar un SDK compatible con IRSA, y luego aplícala con `-n "$EXAMPLE_NAMESPACE"`:

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

Problemas con las demás opciones:

* Los Pods que pueden acceder a IMDS podrían obtener las credenciales del rol del nodo. Restringe el acceso a IMDS y usa roles específicos para las cargas de trabajo; IRSA, por sí sola, no bloquea ese acceso.
* Incrustar claves de acceso de larga duración en las variables de entorno de los Pods aumenta la exposición y el riesgo asociado a la rotación. Las variables de entorno del proveedor de credenciales de IRSA/Pod Identity son un mecanismo distinto.
* Almacenar credenciales de AWS como Secrets de Kubernetes aumenta la carga de administración de credenciales y complica su rotación.

</details>

7. ¿Qué afirmación sobre la función de registro de los clústeres de Amazon EKS es correcta?
   * A) Todos los registros se envían a CloudWatch Logs de forma predeterminada
   * B) Los registros del plano de control se pueden enviar opcionalmente a CloudWatch Logs
   * C) Solo se pueden enviar a CloudWatch Logs los registros de los nodos de trabajo
   * D) EKS no proporciona funciones de registro

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los registros del plano de control se pueden enviar opcionalmente a CloudWatch Logs**

**Explicación:** En los clústeres de Amazon EKS, los registros del plano de control se pueden enviar opcionalmente a CloudWatch Logs. Esta función está deshabilitada de forma predeterminada y los usuarios pueden elegir los tipos de registro que necesitan habilitar.

Características principales del registro del plano de control de EKS:

* **Activación opcional**: Se puede habilitar al crear el clúster o en clústeres existentes.
* **Selección de tipos de registro**: Puedes seleccionar únicamente los tipos de registro que necesitas:
  * Servidor de API (api)
  * Auditoría (audit)
  * Autenticador (authenticator)
  * Administrador de controladores (controllerManager)
  * Programador (scheduler)
* **Integración con CloudWatch Logs**: Los registros seleccionados se envían a AWS CloudWatch Logs para su almacenamiento, análisis y supervisión.
* **Consideración de costos**: Pueden aplicarse cargos por ingesta, retención y consulta en CloudWatch Logs.

Cómo habilitar el registro:

```bash
# Enable logging using AWS CLI
aws eks update-cluster-config \
    --region "${EXAMPLE_REGION:?}" \
    --name "${EXAMPLE_CLUSTER:?}" \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Enable logging using eksctl
eksctl utils update-cluster-logging --enable-types api,audit,authenticator,controllerManager,scheduler --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" --approve
```

Registro de los nodos de trabajo:

* Los registros de los nodos de trabajo no están incluidos en la función de registro del plano de control de EKS.
* Para enviar los registros de los nodos de trabajo a CloudWatch Logs, debes instalar el agente de CloudWatch o configurar una solución de registro como Fluentd/Fluent Bit.

Problemas con las demás opciones:

* No todos los registros se envían a CloudWatch Logs de forma predeterminada. Los usuarios deben habilitarlos explícitamente.
* No es cierto que solo puedan enviarse a CloudWatch Logs los registros de los nodos de trabajo; también pueden enviarse los del plano de control.
* EKS sí proporciona funciones de registro del plano de control.

</details>

8. ¿Cuál NO es un componente de costo de un clúster de Amazon EKS?
   * A) Tarifa por hora del plano de control de EKS
   * B) Costos de las instancias EC2 de los nodos de trabajo
   * C) Costos de ejecución de Pods de Fargate
   * D) Tarifas de licencia de Kubernetes

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Tarifas de licencia de Kubernetes**

**Explicación:** Las tarifas de licencia de Kubernetes no son un componente de costo de los clústeres de Amazon EKS. Kubernetes es software de código abierto administrado por la Cloud Native Computing Foundation (CNCF) y se puede usar de forma gratuita conforme a la licencia Apache 2.0. Por lo tanto, el uso de EKS no conlleva tarifas de licencia de Kubernetes independientes.

Los componentes de costo reales de los clústeres de Amazon EKS incluyen:

1. **Tarifa por hora del plano de control de EKS**:
   * El soporte estándar y el extendido tienen diferentes tarifas de clúster, y los niveles opcionales de Provisioned Control Plane conllevan cargos adicionales.
   * Un clúster de EKS es un recurso regional; una implementación en varias regiones requiere clústeres y cargos independientes.
   * Ten en cuenta por separado los cargos de Auto Mode, EKS Capabilities, Hybrid Nodes y la infraestructura de AWS.
2. **Costos de las instancias EC2 de los nodos de trabajo**:
   * Se incurre en costos por las instancias EC2 utilizadas en grupos de nodos autoadministrados o administrados.
   * Los costos varían según el tipo, el tamaño y la cantidad de instancias, así como el tiempo de ejecución.
   * Se pueden optimizar mediante instancias reservadas, Savings Plans e instancias Spot.
3. **Costos de ejecución de Pods de Fargate**:
   * Con Fargate, los costos se cobran según los recursos de vCPU y memoria asignados a los Pods.
   * La facturación de Fargate para Linux comienza al descargar la imagen, se redondea a segundos y tiene un mínimo de un minuto; los recursos solicitados se redondean a configuraciones compatibles.
   * Compara la capacidad total aprovisionada, la utilización y el esfuerzo operativo; Fargate y EC2 no son, de forma universal, más baratos uno que otro.
4. **Costos adicionales de recursos de AWS**:
   * Volúmenes EBS
   * Balanceadores de carga (NLB, ALB)
   * Registros y métricas de CloudWatch
   * NAT Gateway
   * Transferencia de datos

Estrategias de optimización de costos:

* Seleccionar tipos de instancia adecuados
* Configurar el escalado automático
* Usar instancias Spot
* Automatizar el clúster y programar el escalado
* Optimizar las solicitudes y los límites de recursos
* Supervisar y analizar los costos

</details>

9. ¿Qué opción proporciona integración declarativa con ALB/NLB en un clúster de EKS convencional sin Auto Mode?
   * A) Usar el balanceador de carga integrado de EKS
   * B) Integrar recursos Service de Kubernetes con AWS Load Balancer Controller
   * C) Crear y configurar manualmente balanceadores de carga EC2
   * D) EKS no admite el balanceo de carga

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Integrar recursos Service de Kubernetes con AWS Load Balancer Controller**

**Explicación:** El método correcto para implementar el balanceo de carga en un clúster de Amazon EKS es integrar recursos Service de Kubernetes con AWS Load Balancer Controller. Este enfoque combina la administración declarativa de recursos de Kubernetes con las capacidades de balanceo de carga de AWS.

Métodos para implementar el balanceo de carga en EKS:

1.  **Service de tipo LoadBalancer predeterminado**:

    * El controlador seleccionado determina el balanceador de carga. En este ejemplo se selecciona explícitamente un AWS LBC instalado y autorizado con `service.k8s.aws/nlb`; la integración heredada puede crear un CLB.

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

    * Instala AWS Load Balancer Controller para administrar Application Load Balancer (ALB) y Network Load Balancer (NLB) con funciones más avanzadas.
    * Se puede aprovisionar y configurar un ALB mediante recursos Ingress.
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

    * Se pueden añadir anotaciones a los servicios para especificar el tipo y la configuración del balanceador de carga.

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

Problemas con las demás opciones:

* Auto Mode proporciona balanceo de carga administrado con distintas clases, incluida `eks.amazonaws.com/nlb`. No requiere instalar AWS LBC dentro del clúster; no mezcles sus clases ni uses anotaciones no compatibles.
* Aunque es posible crear y configurar balanceadores de carga EC2 manualmente, este método no se ajusta al enfoque declarativo de Kubernetes y complica la administración.
* EKS admite completamente el balanceo de carga.

</details>

10. ¿Cuál NO es un método válido para administrar el almacenamiento en un clúster de Amazon EKS?
    * A) Aprovisionar volúmenes EBS mediante el controlador CSI de EBS
    * B) Montar sistemas de archivos EFS mediante el controlador CSI de EFS
    * C) Montar un volumen EBS en un Pod de Fargate
    * D) Conectar sistemas de archivos de alto rendimiento mediante el controlador CSI de FSx for Lustre

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Montar un volumen EBS en un Pod de Fargate**

Fargate no puede montar volúmenes EBS. Los nodos EC2 convencionales utilizan un controlador CSI de EBS instalado con permisos de IAM. Auto Mode proporciona aprovisionamiento administrado de EBS mediante `ebs.csi.eks.amazonaws.com`, distinto del controlador convencional `ebs.csi.aws.com`.

Los métodos reales para administrar el almacenamiento en clústeres de Amazon EKS incluyen:

1.  **Controlador CSI de EBS**:

    * Permite conectar volúmenes Amazon EBS (Elastic Block Store) a Pods de Kubernetes.
    * Es adecuado para aplicaciones que requieren almacenamiento en bloques, como bases de datos.
    * Admite el aprovisionamiento dinámico, las instantáneas mediante un controlador de instantáneas y la expansión cuando StorageClass lo permite.
    * EBS tiene alcance de AZ. ReadWriteOnce significa montaje de lectura y escritura desde un nodo, no desde un único Pod; varios Pods de ese nodo pueden usar el volumen. El modo de acceso no define su AZ.

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
2.  **Controlador CSI de EFS**:

    * Permite montar Amazon EFS (Elastic File System) en Pods de Kubernetes.
    * Es adecuado para sistemas de archivos compartidos a los que deben acceder varios Pods al mismo tiempo.
    * Se puede acceder a él desde varias zonas de disponibilidad (modo de acceso ReadWriteMany).
    * Es adecuado para servidores web, CMS, procesos de CI/CD, etc.

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
3.  **Controlador CSI de FSx for Lustre**:

    * Permite conectar Amazon FSx for Lustre a Pods de Kubernetes.
    * Es adecuado para cargas de trabajo de alto rendimiento, como la computación de alto rendimiento, el aprendizaje automático y el análisis de macrodatos.
    * Proporciona un alto rendimiento y una baja latencia.

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
   Especifica la capacidad en el PVC en `spec.resources.requests.storage` (por ejemplo, `1200Gi`), no mediante un parámetro `storageCapacity` de StorageClass. Comprueba los incrementos de capacidad específicos de la implementación, las subredes y los grupos de seguridad, la compatibilidad del cliente de Lustre y los permisos de IAM del controlador.

4.  **Otras opciones de almacenamiento**:
   * Amazon S3 (Simple Storage Service) mediante controladores CSI o montadores de S3
   * Amazon FSx for Windows File Server
   * Amazon FSx for NetApp ONTAP
   * Soluciones de almacenamiento de terceros (Portworx, Rook, etc.)

Prácticas recomendadas para la administración del almacenamiento:

* Seleccionar tipos de almacenamiento adecuados a los requisitos de las cargas de trabajo
* Configurar StorageClass para el aprovisionamiento dinámico
* Establecer estrategias de copia de seguridad y recuperación
* Supervisar el rendimiento del almacenamiento
* Seleccionar clases y tamaños de almacenamiento adecuados para optimizar costos

</details>

## Ejercicios prácticos

### Ejercicio 1: Crear y configurar un clúster de EKS

**Escenario:** Eres ingeniero de DevOps en tu empresa y necesitas configurar un clúster de Amazon EKS para tu equipo de desarrollo. El clúster es para el entorno de desarrollo y debe ser rentable, a la vez que proporciona todas las funciones necesarias.

**Requisitos:**

1. Crear un clúster de EKS rentable
2. Configurar grupos de nodos adecuados
3. Configurar la supervisión básica
4. Configurar el acceso al clúster mediante kubectl

**Solución:**

<details>
<summary>Mostrar solución</summary>

La ejecución de estos comandos de implementación crea recursos de AWS facturables. No se ejecutaron durante la auditoría. Prepara Bash, una versión actual de AWS CLI v2, kubectl 1.36 y Helm, y usa el [procedimiento oficial de instalación de eksctl](https://eksctl.io/installation/) para comprobar el sistema operativo, la arquitectura de la CPU y las sumas de comprobación. El ejemplo se revisó con el esquema de eksctl 0.230.0 y EKS 1.36; no es una configuración de producción validada.

Ejecuta los pasos en un mismo shell y detente si falla algún comando. Establece `EKS_INTRO_ADMIN_CIDR` en el CIDR IPv4 externo real y autorizado del cliente; normalmente, `/32`. El nuevo clúster usa nodos privados/acceso privado a la API, además de acceso público restringido a la API. Una sola puerta de enlace NAT es una opción para un laboratorio de desarrollo, no un diseño de disponibilidad de producción. El acceso de administrador para quien crea el clúster es solo para iniciar este laboratorio específico.

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

Si la creación falla, revisa y limpia las pilas de CloudFormation y los recursos de este nombre único antes de volver a usarlo. `minSize`/`maxSize` solo establecen límites; no instalan un escalador de nodos basado en la demanda. t3.medium es un ejemplo que requiere revisar la capacidad, los créditos de CPU y los precios regionales.

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

Metrics Server 0.9.x admite Kubernetes 1.34 y versiones posteriores. Proporciona métricas de recursos, no registros ni supervisión a largo plazo. Verifica los certificados de kubelet y la conectividad de red sin desactivar la verificación TLS.

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

La política, el controlador y el chart están fijados a la versión 3.5.0. Usa su rol de IRSA en lugar de conceder permisos de complementos no relacionados a todos los nodos. La configuración explícita de región/VPC evita depender de la detección mediante IMDS. Comprueba por separado las etiquetas de subred, los grupos de seguridad y las cuotas de servicio.

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

**6. Comprobar una aplicación básica mediante el reenvío local de puertos**

```bash
intro_kubectl create namespace intro-smoke
intro_kubectl -n intro-smoke create deployment nginx --image=nginx:1.30.6-alpine
intro_kubectl -n intro-smoke rollout status deployment/nginx --timeout=180s
intro_kubectl -n intro-smoke expose deployment nginx --port=80 --type=ClusterIP
intro_kubectl -n intro-smoke get deployment,service
# Run in a separate terminal using the same dedicated kubeconfig.
kubectl --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" -n intro-smoke \
  port-forward --address 127.0.0.1 service/nginx 8080:80
```

Mientras se ejecuta el reenvío de puertos, abre `http://127.0.0.1:8080`; detenlo con Ctrl-C. El siguiente ejercicio configura el acceso externo mediante ALB. Usa el procedimiento de limpieza después de ambos ejercicios; el comportamiento esperado y los posibles ahorros no son resultados medidos de una auditoría.

</details>

### Ejercicio 2: Implementar aplicaciones y exponer servicios en un clúster de EKS

**Escenario:** Tu equipo ha desarrollado una aplicación web basada en una arquitectura de microservicios. Debes implementar esta aplicación en el clúster de EKS y configurarla para que se pueda acceder a ella desde el exterior.

**Requisitos:**

1. Implementar los servicios frontend y backend
2. Configurar la comunicación entre servicios
3. Configurar el acceso externo mediante un controlador de Ingress
4. Configurar el escalado básico

**Solución:**

<details>
<summary>Mostrar solución</summary>

Usa el clúster dedicado y las variables del shell del ejercicio 1, AWS LBC/IngressClass `alb` y un Metrics Server en buen estado. Esta demostración HTTP sirve únicamente respuestas públicas ficticias y restringe el acceso al ALB al CIDR de cliente seleccionado. No implementa autenticación de aplicaciones, TLS ni validación de carga de producción.

**1. Crear el espacio de nombres**

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Complete exercise1 first}"
unset EKS_INTRO_WEB_UID
EKS_INTRO_WEB_UID=$(intro_kubectl create namespace web-app -o jsonpath='{.metadata.uid}')
: "${EKS_INTRO_WEB_UID:?Stop if this namespace already exists}"
```

**2. Configurar el backend**

Configura NGINX para que escuche en el puerto 80 y devuelva JSON ficticio para rutas que incluyen `/api`.

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
        image: nginx:1.30.6-alpine
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

**3. Configurar el frontend y la comunicación entre servicios**

La imagen estándar de NGINX no utiliza `BACKEND_URL`. Esta configuración explícita de NGINX redirige mediante proxy `/proxy-api/` a `backend-service`, lo que proporciona una ruta real entre servicios.

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
        image: nginx:1.30.6-alpine
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

El ALB no elimina `/api` automáticamente; este backend procesa directamente la ruta. `/` y `/proxy-api/` se envían al frontend.

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

La utilización de CPU se mide con respecto a las solicitudes. HPA cambia la cantidad de réplicas de Pods, no la cantidad de nodos, y requiere Metrics Server además de capacidad libre en los nodos.

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

El nombre de host de un ALB no demuestra que sus destinos estén en buen estado. Si las solicitudes fallan, inspecciona los eventos, el estado de los destinos, los grupos de seguridad y el CIDR del cliente.

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

**7. Observar una carga limitada**

Esta carga de ejemplo no garantiza que se supere el objetivo de CPU ni que se active HPA. Las respuestas estáticas de NGINX pueden usar poca CPU, y las solicitudes a la raíz del frontend no generan carga en el backend. Observa las métricas, el estado de HPA y los Pods Pending para determinar el escalado real.

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

### Limpiar los recursos de los ejercicios

Confirma que la cuenta, el ARN y la etiqueta corresponden al clúster de laboratorio dedicado. Elimina los balanceadores de carga de la aplicación antes que el controlador y espera a que finalice la eliminación. Si se agota el tiempo de espera, investiga los errores del controlador en lugar de eliminar finalizadores.

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

Continúa únicamente después de verificar la propiedad y eliminar correctamente Ingress/el espacio de nombres. Confirma que se haya eliminado la pila del rol de IAM y que se haya desvinculado la política antes de eliminarla.

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

Verifica la eliminación de CloudFormation y comprueba si quedan balanceadores de carga, grupos de seguridad, NAT, EBS o costos de retención de registros. Decide por separado si se conservará o eliminará el grupo de registros de CloudWatch. No des por hecho que se hayan limpiado automáticamente los recursos creados parcialmente ni los que no forman parte de estos pasos. Elimina los manifiestos, la política y el kubeconfig del directorio dedicado después del laboratorio.

## Temas avanzados

A continuación se presentan preguntas sobre temas avanzados de Amazon EKS. Esta sección evalúa tu comprensión de las funciones avanzadas e integraciones de EKS.

1. ¿Cuál es la descripción correcta al configurar un perfil de Fargate en Amazon EKS?
   * A) Los perfiles de Fargate especifican qué Pods deben ejecutarse en Fargate según espacios de nombres y etiquetas concretos
   * B) Los perfiles de Fargate ejecutan automáticamente todos los Pods en Fargate
   * C) Los perfiles de Fargate restringen la ejecución de Pods a tipos de instancia EC2 concretos
   * D) Los perfiles de Fargate establecen cuotas de recursos para todo el clúster

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Los perfiles de Fargate especifican qué Pods deben ejecutarse en Fargate según espacios de nombres y etiquetas concretos**

**Explicación:** Un perfil de Fargate de Amazon EKS es una configuración que especifica qué Pods deben ejecutarse en Fargate según espacios de nombres y etiquetas concretos. Esto permite configurar una arquitectura híbrida que utiliza tanto entornos de ejecución de contenedores sin servidor como nodos basados en EC2.

Características principales de los perfiles de Fargate:

* **Ejecución selectiva**: Solo se ejecutan en Fargate los Pods que cumplen las condiciones definidas en el perfil, no todos los Pods.
* **Selectores de espacio de nombres y etiquetas**: Los Pods se seleccionan según combinaciones concretas de espacio de nombres y etiquetas.
* **Especificación de subredes**: Puedes especificar las subredes privadas en las que se ejecutarán los Pods.
* **Rol de IAM**: El rol de ejecución del Pod lo utiliza la infraestructura de Fargate, por ejemplo, para descargar imágenes. Los contenedores de la aplicación necesitan su propio rol de IRSA para acceder a las API de AWS.

Ejemplo de creación de un perfil de Fargate:

```bash
eksctl create fargateprofile \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --name my-fargate-profile \
  --namespace my-namespace \
  --labels app=my-app
```

Definición de un perfil de Fargate basado en YAML:

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
* No se pueden ejecutar contenedores privilegiados.
* HostNetwork y HostPort no son compatibles.
* Las cargas de trabajo con GPU no son compatibles.
* Se aplican costos por Pod, por lo que es necesario planificar los costos.
* El almacenamiento persistente está disponible mediante volúmenes EFS aprovisionados estáticamente. Los volúmenes EBS y el aprovisionamiento dinámico de EFS no son compatibles con Fargate.

Problemas con las demás opciones:

* Los perfiles de Fargate no ejecutan automáticamente todos los Pods en Fargate; solo se ejecutan allí los Pods que coinciden con los selectores.
* Los perfiles de Fargate no están relacionados con los tipos de instancia EC2; Fargate es un entorno de ejecución de contenedores sin servidor.
* Los perfiles de Fargate no establecen cuotas de recursos para todo el clúster. Las cuotas de recursos se administran mediante ResourceQuota de Kubernetes.

</details>

2. ¿Cómo se debe planificar una actualización de EKS?
   * A) Actualizar primero los nodos a la versión de destino y revisar la compatibilidad después
   * B) Preparar las versiones actuales y su compatibilidad; después, plano de control → nodos, coordinando cada actualización de complemento
   * C) Actualizar todos los complementos a la versión más reciente sin revisar nada como preparación completa
   * D) Cambiar todos los componentes simultáneamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Preparar las versiones actuales y su compatibilidad; después, plano de control → nodos, coordinando cada actualización de complemento**

Primero comprueba las versiones actuales del clúster y de los nodos, las perspectivas de actualización, las API eliminadas, la compatibilidad de webhooks/CRD/complementos, las IP libres de subredes y el plan de recuperación. Antes de pasar a la siguiente versión menor, actualiza los nodos que estén por detrás para que alcancen la versión actual del plano de control.

**1. Plano de control**

Avanza una versión menor a la vez. La versión de kubelet no puede ser posterior a la del servidor de API y puede estar hasta tres versiones menores por detrás, pero EKS recomienda que coincidan antes y después de las actualizaciones. La desviación máxima permitida no es un objetivo de estado estable.

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

Una vez que la actualización del plano de control se complete correctamente, inicia las actualizaciones de los grupos de nodos administrados y comprueba el estado de la actualización, la disponibilidad de los nodos y las versiones de kubelet. Los grupos de nodos convencionales no se actualizan automáticamente junto con el plano de control. Los operadores actualizan los nodos autoadministrados/Hybrid Nodes; vuelve a crear los Pods de Fargate para que usen la nueva versión. Auto Mode actualiza los nodos de forma incremental.

```bash
aws eks update-nodegroup-version --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
# Alternative:
# eksctl upgrade nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --name "$EXAMPLE_NODEGROUP" --kubernetes-version "$NEXT_MINOR_VERSION"
```

**3. Complementos y clientes**

Revisa con antelación la compatibilidad con las versiones actual y de destino. Algunos componentes de CNI, webhook o controlador pueden necesitar actualizaciones compatibles antes de actualizar el plano de control, por lo que los complementos no siempre se actualizan al final. Después de actualizar el plano de control, actualiza los demás complementos, Cluster Autoscaler y kubectl a versiones compatibles y valida cada uno.

```bash
aws eks describe-addon-versions --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}" \
  --query 'addons[].addonVersions[].addonVersion' --output table

# Select a compatible EKS add-on build after reviewing configuration changes.
aws eks update-addon --cluster-name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --addon-version "${REVIEWED_ADDON_VERSION:?}" \
  --resolve-conflicts PRESERVE
```

`PRESERVE` conserva la configuración del usuario; no garantiza la compatibilidad. Comprueba los PDB, la capacidad disponible y la terminación ordenada; no ocultes los fallos con indicadores de forzado. Valida cada etapa y prepara copias de seguridad recuperables de las aplicaciones y los datos. Las copias de seguridad del plano de control de AWS no sustituyen un plan de recuperación de datos del cliente.

EKS admite ahora la reversión a la versión menor anterior durante los siete días posteriores a una actualización completada que reúna los requisitos. Se aplican restricciones relacionadas con los nodos, los complementos, los cambios de API y la política de soporte; los datos de las aplicaciones no se restauran automáticamente. Sigue el [procedimiento de actualización](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html) y las [condiciones de reversión](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html).

</details>

3. ¿Cuál NO es una característica principal del complemento VPC CNI de Amazon EKS?
   * A) Asignar direcciones IP de la VPC a los Pods
   * B) Aplicar grupos de seguridad a nivel de Pod
   * C) Cifrar el tráfico de red entre Pods
   * D) Ampliar las direcciones IP mediante la delegación de prefijos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Cifrar el tráfico de red entre Pods**

Amazon VPC CNI no proporciona cifrado generalizado del tráfico entre Pods. Configura TLS/mTLS en la aplicación o una función de cifrado de malla/CNI compatible de forma explícita. NetworkPolicy filtra el tráfico, pero no lo cifra.

Las características principales reales del complemento Amazon VPC CNI incluyen:

1. **Asignación de direcciones IP de la VPC a los Pods**:
   * Los Pods normales reciben IP de la VPC; los Pods `hostNetwork` comparten la red del nodo.
   * Esto permite que los Pods se comuniquen directamente con otros recursos de la VPC.
   * Las IP de los Pods se pueden enrutar dentro de la VPC, lo que elimina la necesidad de redes de superposición complejas.
2. **Aplicación de grupos de seguridad a nivel de Pod**:
   * Se pueden aplicar grupos de seguridad de AWS a Pods individuales mediante la función SecurityGroupsForPods.
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
3. **Ampliación de las direcciones IP mediante la delegación de prefijos**:
   * De forma predeterminada, cada nodo puede asignar a los Pods una cantidad limitada de direcciones IP, que varía según el tipo de instancia.
   * Con la función de delegación de prefijos, puedes asignar bloques CIDR /28 (16 IP) a cada nodo y aumentar así la cantidad de direcciones IP disponibles.
   * Esto aumenta la capacidad de direcciones por ENI, pero consume direcciones existentes de la subred. Requiere prefijos libres contiguos y no crea capacidad adicional en la subred.
4. **Redes personalizadas**:
   * Se pueden ubicar los Pods en subredes específicas.
   * La red de los Pods se puede configurar mediante varias interfaces de red.
5. **Red de host de Kubernetes**:
   * `hostNetwork` usa la red del nodo; es una configuración de Pod de Kubernetes, no una función de cifrado ni aislamiento de CNI.
   * Es útil para las cargas de trabajo en las que el rendimiento de red es fundamental.

Aplica por separado las capacidades de VPC CNI después de comprobar sus requisitos previos.

| Configuración | Comprobaciones necesarias |
| --- | --- |
| `ENABLE_PREFIX_DELEGATION` | Instancia/versión de CNI compatible, bloques `/28` libres contiguos, max-pods de kubelet y un plan de transición para nodos nuevos |
| `ENABLE_POD_ENI` | Instancias compatibles con trunk/branch ENI, permisos del controlador de recursos de VPC, SecurityGroupPolicy y reglas de DNS/grupos de seguridad |
| `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG` | IPv4, subredes/grupos de seguridad de los Pods en la misma VPC/AZ, selección de ENIConfig del nodo e IP libres |

Activar solo una opción puede hacer que los Pods antiguos y nuevos se comporten de manera diferente o que falle la asignación de IP. Sigue el procedimiento oficial de transición sin entrar en conflicto con la configuración de complementos administrados por EKS. No apliques directamente este enfoque convencional de DaemonSet de EC2 a Auto Mode, Fargate ni Hybrid Nodes.

```bash
# Inspect current non-secret CNI flags; this does not enable any feature.
kubectl --context "${EXAMPLE_CONTEXT:?}" -n kube-system get daemonset aws-node \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="aws-node")].env}{"\n"}'
```


Para implementar el cifrado del tráfico de red entre Pods, considera las siguientes alternativas:

* El soporte de App Mesh finalizó el 30 de septiembre de 2026; los usuarios actuales deben migrar.
* Implementar una malla de servicios Istio
* Usar la función de cifrado transparente de Cilium
* Implementar TLS/mTLS a nivel de aplicación

</details>

4. ¿Cómo puede un rol de IAM de desarrollador obtener acceso de lectura de Kubernetes limitado a un espacio de nombres?
   * A) Asociar directamente un Role de Kubernetes a un usuario de IAM
   * B) Usar una entrada de acceso de EKS para asignar el rol de IAM a un grupo de Kubernetes y configurar vinculaciones RBAC
   * C) Asociar únicamente una política de S3 al rol de IAM del clúster
   * D) Conceder a un desarrollador acceso a kubectl exclusivamente mediante la configuración IRSA de un ServiceAccount de aplicación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar una entrada de acceso de EKS para asignar el rol de IAM a un grupo de Kubernetes y configurar vinculaciones RBAC**

Para el nuevo acceso de IAM, usa una **entrada de acceso de EKS**. El modo de autenticación del clúster debe ser `API` o `API_AND_CONFIG_MAP`. Antes de cambiar el modo de un clúster existente, prepara la migración de asignaciones y una vía de recuperación administrativa. `aws-auth` está obsoleto y no es el único mecanismo de asignación.

Este ejemplo asocia un rol de IAM de desarrollador existente con `dev-readers`. Una identidad de IAM y una entrada de acceso no crean automáticamente objetos RBAC de Kubernetes.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster.accessConfig.authenticationMode

aws eks create-access-entry --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --principal-arn "${DEV_ROLE_ARN:?Existing developer IAM role}" \
  --type STANDARD --kubernetes-groups dev-readers
```

Un administrador aplica este Role y RoleBinding en el espacio de nombres `dev` existente. Conceden acceso de lectura a Pods/Deployments, sin permisos para Secrets ni para realizar modificaciones. Los permisos para crear cargas de trabajo pueden permitir el uso de Secrets del espacio de nombres y requieren una revisión independiente.

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

Con una identidad autorizada para asumir el rol, crea un kubeconfig dedicado y verifica los permisos reales. La primera comprobación debería permitirse y la segunda debería denegarse, salvo que otra concesión de RBAC o una política de acceso de EKS añada permisos.

```bash
aws eks update-kubeconfig --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --role-arn "${DEV_ROLE_ARN:?}" --kubeconfig "${DEV_KUBECONFIG:?Use a dedicated file}"
kubectl --kubeconfig "$DEV_KUBECONFIG" auth can-i get pods -n dev
kubectl --kubeconfig "$DEV_KUBECONFIG" auth can-i get secrets -n dev
```

Como alternativa, asocia a la entrada una política de acceso de EKS limitada a un espacio de nombres. Las políticas de acceso y las concesiones de RBAC son aditivas; asociar únicamente una política de IAM no concede permisos de Kubernetes. IRSA/Pod Identity proporcionan una vía independiente para que los Pods llamen a las API de AWS. No concedas `system:masters` a desarrolladores comunes ni sobrescribas todo el ConfigMap `aws-auth`.

</details>

5. ¿Qué descripción del soporte de versiones de EKS es correcta?
   * A) Todas las versiones reciben soporte indefinidamente
   * B) El soporte de todas las versiones termina después de 12 meses
   * C) Siempre se admiten exactamente la última versión y las tres versiones anteriores
   * D) 14 meses de soporte estándar y 12 meses de soporte extendido de pago a partir del lanzamiento de EKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) 14 meses de soporte estándar y 12 meses de soporte extendido de pago a partir del lanzamiento de EKS**

Una versión menor de EKS recibe **14 meses de soporte estándar a partir de su fecha de lanzamiento en EKS**, seguidos de **12 meses de soporte extendido de pago**. El cómputo no comienza en la fecha de lanzamiento de la versión upstream.

* Lista oficial al 12 de octubre de 2026: soporte estándar para **1.34–1.37** y soporte extendido para **1.31–1.33**. EKS 1.37 estuvo disponible el 1 de octubre de 2026, después de su lanzamiento upstream el 26 de agosto.
* El soporte extendido está habilitado de forma predeterminada. Al seleccionar la política de actualización `STANDARD`, se excluye ese soporte y el clúster queda sujeto a una actualización automática cuando finalice el soporte estándar.
* Cuando termina el soporte extendido, AWS actualiza automáticamente el plano de control a una versión compatible. No se garantiza el momento exacto de ejecución, por lo que los operadores deben planificar las actualizaciones de forma proactiva.
* Los nodos administrados/autoadministrados/Hybrid Nodes no se actualizan solo porque el plano de control se haya actualizado automáticamente. Planifica por separado el reemplazo de los Pods de Fargate y las actualizaciones de complementos; los nodos de Auto Mode siguen las actualizaciones administradas.
* Las versiones compatibles reciben parches de seguridad; no se admite conservar todas las versiones indefinidamente. No se pueden crear clústeres nuevos con versiones cuyo soporte haya finalizado.

Comprueba el calendario de lanzamientos y la información de versiones en la región correspondiente. Buscar en los metadatos de complementos no sustituye la lista de versiones compatibles del clúster.

```bash
aws eks describe-cluster-versions --region "${EXAMPLE_REGION:?}" --output table
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --query 'cluster.{version:version,upgradePolicy:upgradePolicy}' --output json
```

Mantén un calendario de actualizaciones, revisa las API eliminadas y la compatibilidad, realiza pruebas en un entorno que no sea de producción, prepara la recuperación de las aplicaciones y los datos y avanza una versión menor a la vez. EKS ofrece al menos tres versiones con soporte estándar, sin una regla fija de “solo la última y las tres anteriores”.

</details>


## Referencias oficiales y alcance de la validación

- [Ciclo de vida de las versiones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Entradas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Pod Identity e IRSA](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)
- [Load Balancer Controller](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [Balanceo de carga de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-configure-nlb.html)
- [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [Configuración de FSx CSI y capacidad de PVC](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi-create.html)
- [Limitaciones de Fargate](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [Delegación de prefijos](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses.html)
- [Redes personalizadas](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network.html)
- [Precios de EKS](https://aws.amazon.com/eks/pricing/)
- [Precios de Fargate](https://aws.amazon.com/fargate/pricing/)
- [Esquema de eksctl 0.230.0](https://github.com/eksctl-io/eksctl/blob/v0.230.0/pkg/apis/eksctl.io/v1alpha5/assets/schema.json)
- [Instalación de LBC 3.5.0](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/installation.md)
- [Compatibilidad de Metrics Server 0.9.0](https://github.com/kubernetes-sigs/metrics-server/blob/v0.9.0/README.md)

Esta es una revisión estática basada en la documentación oficial y los esquemas de lanzamiento. No se aprovisionaron clústeres, IAM ni balanceadores de carga; tampoco se implementaron aplicaciones, se realizaron actualizaciones o reversiones, se ejecutó NGINX o una prueba de carga, ni se midieron costos. El comportamiento esperado del ejemplo no es un resultado medido.
