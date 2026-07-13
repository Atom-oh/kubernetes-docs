# Quiz de introducción a EKS

Este quiz evalúa tu comprensión de los conceptos básicos y las características de Amazon Elastic Kubernetes Service (EKS). Cubre temas como la arquitectura de EKS, sus componentes, métodos de administración y modelos de precios.

## Preguntas de opción múltiple

1. ¿Cuál es el beneficio principal de Amazon EKS (Elastic Kubernetes Service)?
   * A) No necesitas administrar tu propia infraestructura del control plane de Kubernetes
   * B) Menor costo que otros servicios Kubernetes administrados
   * C) Solo puede usar servicios de AWS
   * D) Solo puede ejecutarse en una única availability zone

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) No necesitas administrar tu propia infraestructura del control plane de Kubernetes**

**Explicación:** El beneficio principal de Amazon EKS (Elastic Kubernetes Service) es que no necesitas administrar tu propia infraestructura del control plane de Kubernetes. Como AWS administra la disponibilidad y la escalabilidad del control plane de Kubernetes, los usuarios pueden centrarse en ejecutar sus workloads.

Beneficios clave de EKS:

* **Control Plane administrado**: AWS administra los nodos del control plane, el clúster etcd, el API server, etc.
* **Alta disponibilidad**: El control plane se despliega en varias availability zones, lo que elimina puntos únicos de falla.
* **Actualizaciones y parches automáticos**: AWS administra las actualizaciones de versión de Kubernetes y los parches de seguridad.
* **Integración con servicios de AWS**: Se integra sin problemas con diversos servicios de AWS, incluidos IAM, VPC, ELB, ECR, etc.
* **Kubernetes estándar**: Proporciona Kubernetes totalmente compatible para evitar el vendor lock-in.

Problemas con las otras opciones:

* EKS no es necesariamente más barato que otros servicios Kubernetes administrados. De hecho, existe una tarifa por hora para el control plane.
* EKS puede ejecutar cualquier aplicación y servicio compatible con Kubernetes, no solo servicios de AWS.
* Los clústeres de EKS se despliegan de forma predeterminada en varias availability zones para alta disponibilidad.

</details>

2. ¿Dónde se despliega el control plane del clúster de Amazon EKS?
   * A) Dentro de la VPC del usuario
   * B) Desplegado en varias availability zones en una cuenta administrada por AWS
   * C) En una única availability zone elegida por el usuario
   * D) Ejecutándose en instancias EC2 del usuario

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Desplegado en varias availability zones en una cuenta administrada por AWS**

**Explicación:** El control plane del clúster de Amazon EKS se despliega en varias availability zones en una cuenta administrada por AWS. Este es uno de los aspectos centrales de EKS como servicio administrado.

Características clave del despliegue del control plane de EKS:

* **Infraestructura administrada por AWS**: El control plane se ejecuta en una cuenta propiedad de AWS y administrada por AWS.
* **Despliegue Multi-AZ**: Se despliega en al menos 3 availability zones para alta disponibilidad.
* **Recuperación automática**: AWS monitorea el estado de los componentes del control plane y reemplaza automáticamente los componentes con fallas.
* **Accesibilidad del endpoint**: Los endpoints del control plane se pueden configurar como accesibles públicamente o accesibles solo dentro de la VPC.
* **Auto Scaling**: La capacidad del control plane se ajusta automáticamente según la carga del clúster.

Problemas con las otras opciones:

* El control plane no se despliega dentro de la VPC del usuario. En su lugar, se establece una conexión entre la VPC del usuario y la VPC administrada por AWS mediante ENI (Elastic Network Interface).
* El control plane se despliega en varias availability zones, no en una sola, para garantizar alta disponibilidad.
* El control plane se ejecuta en infraestructura administrada por AWS, no en instancias EC2 del usuario.

</details>

3. ¿Cuál NO es un método válido para administrar worker nodes en Amazon EKS?
   * A) Self-managed node groups
   * B) Managed node groups
   * C) Fargate profiles
   * D) Aprovisionamiento automático de nodos de EKS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Aprovisionamiento automático de nodos de EKS**

**Explicación:** "EKS automatic node provisioning" no es un método de administración de worker nodes proporcionado oficialmente en Amazon EKS. Esta característica no existe.

Los métodos reales para administrar worker nodes en Amazon EKS son:

1. **Self-managed node groups**:
   * Los usuarios crean y administran directamente instancias EC2.
   * Se pueden administrar mediante Auto Scaling groups.
   * Proporcionan control completo sobre la configuración de los nodos.
   * Tienen la mayor carga operativa.
2. **Managed node groups**:
   * AWS administra el aprovisionamiento y el ciclo de vida de los nodos.
   * Las actualizaciones, parches y ajustes de nodos están automatizados.
   * Se basan en EC2 Auto Scaling groups.
   * Usan AMI estándar de Amazon Linux o Bottlerocket.
3. **Fargate profiles**:
   * Una opción de computación serverless que elimina la necesidad de administrar instancias EC2 individuales.
   * Aprovisiona recursos de cómputo por pod.
   * Tiene la menor carga de administración de infraestructura.
   * Tiene ciertas limitaciones (por ejemplo, no admite DaemonSet y tiene ciertas restricciones de recursos).

Para el auto-scaling de nodos, EKS admite herramientas como Kubernetes Cluster Autoscaler o Karpenter, pero no existe una característica oficial llamada "EKS automatic node provisioning".

</details>

4. ¿Qué plugin CNI se usa de forma predeterminada para la red de pods en los clústeres de Amazon EKS?
   * A) Flannel
   * B) Calico
   * C) AWS VPC CNI
   * D) Weave Net

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) AWS VPC CNI**

**Explicación:** El plugin CNI (Container Network Interface) usado de forma predeterminada para la red de pods en los clústeres de Amazon EKS es AWS VPC CNI. Este plugin integra directamente la red de Amazon VPC con los pods de Kubernetes.

Características clave de AWS VPC CNI:

* **Asignación de direcciones IP nativa de VPC**: Los pods reciben direcciones IP directamente de la VPC y existen en el mismo espacio de red que otros recursos de la VPC.
* **Uso de direcciones IP secundarias**: Asigna a los pods direcciones IP secundarias conectadas a la Elastic Network Interface (ENI) de cada nodo.
* **Integración con security groups**: Los security groups se pueden aplicar a nivel de pod (característica SecurityGroupsForPods).
* **Visibilidad en VPC flow logs**: El tráfico de los pods es visible en VPC flow logs.
* **Aprovechamiento de características de red de AWS**: Características como VPC peering, Transit Gateway y PrivateLink pueden ser utilizadas directamente por los pods.

AWS VPC CNI es un proyecto open-source, y puedes consultar el código en GitHub: https://github.com/aws/amazon-vpc-cni-k8s

Se pueden instalar otros plugins CNI (Flannel, Calico, Weave Net, etc.) en EKS, pero AWS VPC CNI se proporciona de forma predeterminada.

</details>

5. ¿Cuál es el método para administrar la autenticación y autorización de recursos de Kubernetes en Amazon EKS?
   * A) Usar solo Kubernetes service accounts
   * B) Integración de AWS IAM y Kubernetes RBAC
   * C) Sistema de administración de permisos específico de EKS
   * D) Autenticación de usuarios mediante AWS Cognito

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Integración de AWS IAM y Kubernetes RBAC**

**Explicación:** Amazon EKS administra la autenticación y autorización de recursos de Kubernetes mediante la integración de AWS IAM (Identity and Access Management) y Kubernetes RBAC (Role-Based Access Control). Este enfoque integrado combina las potentes capacidades de administración de identidades de AWS con el control granular de permisos de Kubernetes.

Características clave:

* **Autenticación IAM**: Autentica contra el Kubernetes API server usando credenciales de AWS IAM.
* **aws-auth ConfigMap**: Mapea roles o usuarios IAM a usuarios y grupos de Kubernetes.
* **Autorización RBAC**: Usa el sistema Kubernetes RBAC para controlar permisos dentro del clúster.
* **IRSA (IAM Roles for Service Accounts)**: Vincula roles IAM a Kubernetes service accounts, lo que permite que los pods accedan de forma segura a servicios de AWS.

Cómo funciona:

1. Los usuarios obtienen un token de autenticación para el Kubernetes API server usando el comando `aws eks get-token` (mediante AWS CLI o AWS SDK).
2. Este token se firma usando credenciales IAM.
3. El Kubernetes API server valida el token usando el AWS IAM authenticator.
4. Según los mapeos en el aws-auth ConfigMap, a los usuarios se les asignan usuarios y grupos de Kubernetes.
5. El sistema Kubernetes RBAC permite o deniega solicitudes según los permisos otorgados a esos usuarios o grupos.

Problemas con las otras opciones:

* Usar solo Kubernetes service accounts limita la integración con servicios de AWS.
* EKS no tiene un sistema de administración de permisos dedicado independiente; integra Kubernetes RBAC estándar con AWS IAM.
* AWS Cognito no se usa directamente para la autenticación de EKS, aunque puede configurarse como proveedor OIDC.

</details>

6. ¿Cuál es el método recomendado para que los pods accedan a servicios de AWS (por ejemplo, S3, DynamoDB) en un clúster de Amazon EKS?
   * A) Otorgar roles IAM a los nodos usando perfiles de instancia EC2
   * B) Inyectar credenciales de AWS directamente en los pods como variables de entorno
   * C) Vincular roles IAM a Kubernetes service accounts (IRSA)
   * D) Almacenar credenciales de AWS como Kubernetes Secrets y montarlas

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Vincular roles IAM a Kubernetes service accounts (IRSA)**

**Explicación:** El método recomendado para que los pods accedan a servicios de AWS en un clúster de Amazon EKS es vincular roles IAM a Kubernetes service accounts. Esta característica se llama IRSA (IAM Roles for Service Accounts) y proporciona permisos granulares a nivel de pod.

Beneficios clave de IRSA:

* **Principio de privilegio mínimo**: Puedes otorgar solo los permisos mínimos necesarios para cada aplicación.
* **Aislamiento de permisos**: Diferentes pods que se ejecutan en el mismo nodo pueden tener diferentes permisos IAM.
* **Administración simplificada de credenciales**: No es necesario administrar directamente credenciales de AWS.
* **Seguridad mejorada**: Las credenciales no se codifican directamente en el código ni en la configuración.

Cómo configurar IRSA:

1.  Asocia un proveedor OpenID Connect (OIDC) con el clúster de EKS:

    ```bash
    eksctl utils associate-iam-oidc-provider --cluster=<cluster-name> --approve
    ```
2.  Crea un rol IAM para el service account:

    ```bash
    eksctl create iamserviceaccount \
      --name=<service-account-name> \
      --namespace=<namespace> \
      --cluster=<cluster-name> \
      --attach-policy-arn=arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
      --approve
    ```
3.  Referencia el service account en el manifiesto del pod:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: <service-account-name>
      containers:
      - name: my-container
        image: my-image
    ```

Problemas con las otras opciones:

* Usar perfiles de instancia EC2 da los mismos permisos a todos los pods en el mismo nodo, lo que viola el principio de privilegio mínimo.
* Inyectar credenciales de AWS como variables de entorno implica riesgo de exposición de credenciales y dificulta la rotación de credenciales.
* Almacenar credenciales de AWS como Kubernetes Secrets agrega carga de administración de credenciales y complica la rotación de credenciales.

</details>

7. ¿Qué afirmación sobre la característica de logging de los clústeres de Amazon EKS es correcta?
   * A) Todos los logs se envían a CloudWatch Logs de forma predeterminada
   * B) Los logs del control plane se pueden enviar opcionalmente a CloudWatch Logs
   * C) Solo los logs de worker nodes se pueden enviar a CloudWatch Logs
   * D) EKS no proporciona funcionalidad de logging

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los logs del control plane se pueden enviar opcionalmente a CloudWatch Logs**

**Explicación:** En los clústeres de Amazon EKS, los logs del control plane se pueden enviar opcionalmente a CloudWatch Logs. Esta característica está deshabilitada de forma predeterminada, y los usuarios pueden elegir habilitar los tipos de logs que necesitan.

Características clave del logging del control plane de EKS:

* **Activación opcional**: Se puede habilitar durante la creación del clúster o en clústeres existentes.
* **Selección de tipos de log**: Puedes seleccionar solo los tipos de log que necesitas entre:
  * API server (api)
  * Audit (audit)
  * Authenticator (authenticator)
  * Controller manager (controllerManager)
  * Scheduler (scheduler)
* **Integración con CloudWatch Logs**: Los logs seleccionados se envían a AWS CloudWatch Logs para almacenamiento, análisis y monitoreo.
* **Consideración de costos**: Los precios de CloudWatch Logs se aplican al almacenamiento de logs.

Cómo habilitar logging:

```bash
# Enable logging using AWS CLI
aws eks update-cluster-config \
    --region <region> \
    --name <cluster-name> \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Enable logging using eksctl
eksctl utils update-cluster-logging --enable-types api,audit,authenticator,controllerManager,scheduler --cluster <cluster-name> --region <region>
```

Logging de worker nodes:

* Los logs de worker nodes no están incluidos en la característica de logging del control plane de EKS.
* Para enviar logs de worker nodes a CloudWatch Logs, necesitas instalar el CloudWatch agent o configurar una solución de logging como Fluentd/Fluent Bit.

Problemas con las otras opciones:

* No todos los logs se envían a CloudWatch Logs de forma predeterminada. Los usuarios deben habilitarlos explícitamente.
* No es que solo los logs de worker nodes puedan enviarse a CloudWatch Logs; los logs del control plane también pueden enviarse.
* EKS sí proporciona funcionalidad de logging del control plane.

</details>

8. ¿Cuál NO es un componente de costo de un clúster de Amazon EKS?
   * A) Tarifa por hora del control plane de EKS
   * B) Costos de instancias EC2 para worker nodes
   * C) Costos de ejecución de pods en Fargate
   * D) Tarifas de licencia de Kubernetes

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Tarifas de licencia de Kubernetes**

**Explicación:** Las tarifas de licencia de Kubernetes no son un componente de costo de los clústeres de Amazon EKS. Kubernetes es software open-source administrado por la Cloud Native Computing Foundation (CNCF) y se puede usar gratuitamente bajo la licencia Apache 2.0. Por lo tanto, no hay tarifas de licencia de Kubernetes independientes al usar EKS.

Los componentes reales de costo de los clústeres de Amazon EKS incluyen:

1. **Tarifa por hora del control plane de EKS**:
   * Se cobra una tarifa fija por hora por cada clúster de EKS (por ejemplo, $0.10 por hora).
   * Este costo es constante independientemente del tamaño del clúster o del workload.
   * Las tarifas se cobran por región si se extiende a varias regiones.
2. **Costos de instancias EC2 para worker nodes**:
   * Se incurren costos por las instancias EC2 usadas en self-managed o managed node groups.
   * Los costos varían según el tipo de instancia, tamaño, cantidad y tiempo de ejecución.
   * Los costos pueden optimizarse mediante Reserved Instances, Savings Plans y Spot Instances.
3. **Costos de ejecución de pods en Fargate**:
   * Al usar Fargate, los costos se cobran según los recursos de vCPU y memoria asignados a los pods.
   * Los costos se calculan por segundo según el tiempo de ejecución del pod.
   * No hay carga de administración de nodos, pero generalmente es más caro que los nodos basados en EC2.
4. **Costos adicionales de recursos de AWS**:
   * Volúmenes EBS
   * Load balancers (NLB, ALB)
   * Logs y métricas de CloudWatch
   * NAT Gateway
   * Transferencia de datos

Estrategias de optimización de costos:

* Seleccionar tipos de instancia adecuados
* Configurar auto-scaling
* Usar Spot Instances
* Automatización del clúster y escalado programado
* Optimizar requests y limits de recursos
* Monitoreo y análisis de costos

</details>

9. ¿Cuál es el método correcto para implementar load balancing en un clúster de Amazon EKS?
   * A) Usar el load balancer integrado de EKS
   * B) Integrar recursos Kubernetes Service con AWS Load Balancer Controller
   * C) Crear y configurar manualmente load balancers EC2
   * D) EKS no admite load balancing

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Integrar recursos Kubernetes Service con AWS Load Balancer Controller**

**Explicación:** El método correcto para implementar load balancing en un clúster de Amazon EKS es integrar recursos Kubernetes Service con AWS Load Balancer Controller. Este enfoque combina la administración declarativa de recursos de Kubernetes con las capacidades de load balancing de AWS.

Métodos para implementar load balancing en EKS:

1.  **Service de tipo LoadBalancer predeterminado**:

    * Crear un Service de tipo `LoadBalancer` en Kubernetes aprovisiona de forma predeterminada un Classic Load Balancer (CLB) o Network Load Balancer (NLB).

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
    spec:
      type: LoadBalancer
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: my-app
    ```
2.  **AWS Load Balancer Controller**:

    * Instala AWS Load Balancer Controller para obtener características más avanzadas para administrar Application Load Balancer (ALB) y Network Load Balancer (NLB).
    * ALB puede aprovisionarse y configurarse mediante recursos Ingress.
    * Se pueden configurar diversos atributos del load balancer mediante annotations.

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: my-ingress
      annotations:
        kubernetes.io/ingress.class: alb
        alb.ingress.kubernetes.io/scheme: internet-facing
        alb.ingress.kubernetes.io/target-type: ip
    spec:
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
3.  **Annotations de Service**:

    * Se pueden agregar annotations a los services para especificar el tipo y la configuración del load balancer.

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-type: nlb
        service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    spec:
      type: LoadBalancer
      # ...
    ```

Problemas con las otras opciones:

* No existe un componente independiente de "load balancer integrado de EKS" en EKS. El load balancing se proporciona mediante la integración de recursos Kubernetes Service y load balancers de AWS.
* Aunque es posible crear y configurar manualmente load balancers EC2, esto no se alinea con el enfoque declarativo de Kubernetes y complica la administración.
* EKS admite completamente load balancing.

</details>

10. ¿Cuál NO es un método válido para administrar storage en un clúster de Amazon EKS?
    * A) Aprovisionar volúmenes EBS usando el EBS CSI driver
    * B) Montar sistemas de archivos EFS usando el EFS CSI driver
    * C) Aprovisionamiento automático de volúmenes mediante el storage manager integrado de EKS
    * D) Conectar sistemas de archivos de alto rendimiento usando el FSx for Lustre CSI driver

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Aprovisionamiento automático de volúmenes mediante el storage manager integrado de EKS**

**Explicación:** "EKS built-in storage manager" es una característica que no existe. Amazon EKS no tiene un storage manager integrado para aprovisionamiento automático de volúmenes; el storage se administra mediante drivers CSI (Container Storage Interface).

Los métodos reales para administrar storage en clústeres de Amazon EKS incluyen:

1.  **EBS CSI driver**:

    * Permite conectar volúmenes de Amazon EBS (Elastic Block Store) a pods de Kubernetes.
    * Adecuado para aplicaciones que requieren block storage (bases de datos, etc.).
    * Admite aprovisionamiento dinámico, snapshots y redimensionamiento de volúmenes.
    * Accesible solo dentro de una única availability zone (modo de acceso ReadWriteOnce).

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
2.  **EFS CSI driver**:

    * Permite montar Amazon EFS (Elastic File System) en pods de Kubernetes.
    * Adecuado para sistemas de archivos compartidos que necesitan ser accedidos por varios pods simultáneamente.
    * Accesible en varias availability zones (modo de acceso ReadWriteMany).
    * Adecuado para servidores web, CMS, pipelines CI/CD, etc.

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
3.  **FSx for Lustre CSI driver**:

    * Permite conectar Amazon FSx for Lustre a pods de Kubernetes.
    * Adecuado para workloads de alto rendimiento como high-performance computing, machine learning y análisis de big data.
    * Proporciona alto throughput y baja latencia.

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
      storageCapacity: "1200"
    ```
4. **Otras opciones de storage**:
   * Amazon S3 (Simple Storage Service) mediante drivers CSI o S3 mounters
   * Amazon FSx for Windows File Server
   * Amazon FSx for NetApp ONTAP
   * Soluciones de storage de terceros (Portworx, Rook, etc.)

Mejores prácticas de administración de storage:

* Seleccionar tipos de storage adecuados para los requisitos del workload
* Configurar StorageClass para aprovisionamiento dinámico
* Establecer estrategias de backup y recuperación
* Monitorear el rendimiento del storage
* Seleccionar storage classes y tamaños adecuados para optimización de costos

</details>

## Ejercicios prácticos

### Ejercicio 1: Crear y configurar un clúster de EKS

**Escenario:** Eres un ingeniero DevOps en tu empresa y necesitas configurar un clúster de Amazon EKS para tu equipo de desarrollo. El clúster es para el entorno de desarrollo y debe ser rentable, a la vez que proporciona todas las características necesarias.

**Requisitos:**

1. Crear un clúster de EKS rentable
2. Configurar node groups adecuados
3. Configurar monitoreo básico
4. Configurar acceso de kubectl al clúster

**Solución:**

<details>

<summary>Mostrar solución</summary>

**1. Crear clúster de EKS usando eksctl**

```bash
# Install eksctl (if not already installed)
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
eksctl version

# Create cluster
cat << EOF > eks-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: dev-cluster
  region: us-west-2
  version: "1.28"

managedNodeGroups:
  - name: ng-1
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        appMesh: false
        ebs: true
        fsx: false
        efs: false
        albIngress: true
        xRay: false
        cloudWatch: true

cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
EOF

eksctl create cluster -f eks-cluster.yaml
```

**2. Configurar y verificar kubectl**

```bash
# Update kubectl configuration
aws eks update-kubeconfig --name dev-cluster --region us-west-2

# Verify cluster connection
kubectl get nodes
kubectl cluster-info
```

**3. Verificar componentes básicos de monitoreo**

```bash
# Check basic system pods
kubectl get pods -n kube-system

# Install metrics server (if not provided by default)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify metrics server operation
kubectl get deployment metrics-server -n kube-system
kubectl top nodes
```

**4. Instalar AWS Load Balancer Controller**

```bash
# Create IAM policy
curl -o iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json
aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam-policy.json

# Set up IRSA
eksctl create iamserviceaccount \
  --cluster=dev-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::<AWS_ACCOUNT_ID>:policy/AWSLoadBalancerControllerIAMPolicy \
  --override-existing-serviceaccounts \
  --approve

# Install controller with Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=dev-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

**5. Comprobar el estado del clúster**

```bash
# Check node status
kubectl get nodes -o wide

# Check system pod status
kubectl get pods -n kube-system

# Check cluster events
kubectl get events --sort-by='.lastTimestamp'

# Check cluster info
kubectl cluster-info
```

**6. Desplegar aplicación de prueba**

```bash
# Deploy simple nginx
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80 --type=LoadBalancer

# Verify deployment
kubectl get deployment nginx
kubectl get service nginx
```

A través de este ejercicio, aprendiste cómo crear un clúster de EKS rentable, configurar monitoreo básico y configurar el load balancer controller para exponer aplicaciones externamente. El tipo de instancia t3.medium es una opción rentable adecuada para entornos de desarrollo, y la configuración de auto-scaling permite que los nodos escalen según sea necesario.

</details>

### Ejercicio 2: Desplegar aplicaciones y exponer services en un clúster de EKS

**Escenario:** Tu equipo ha desarrollado una aplicación web basada en arquitectura de microservices. Necesitas desplegar esta aplicación en el clúster de EKS y configurarla para que sea accesible desde el exterior.

**Requisitos:**

1. Desplegar services frontend y backend
2. Configurar comunicación entre services
3. Configurar acceso externo mediante ingress controller
4. Configurar escalado básico

**Solución:**

<details>

<summary>Mostrar solución</summary>

**1. Crear Namespace**

```bash
kubectl create namespace web-app
kubectl config set-context --current --namespace=web-app
```

**2. Desplegar Backend Service**

```yaml
# backend-deployment.yaml
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
      containers:
      - name: backend
        image: nginx:alpine  # Replace with actual backend image
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
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
    targetPort: 8080
```

```bash
kubectl apply -f backend-deployment.yaml
```

**3. Desplegar Frontend Service**

```yaml
# frontend-deployment.yaml
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
      containers:
      - name: frontend
        image: nginx:alpine  # Replace with actual frontend image
        ports:
        - containerPort: 80
        env:
        - name: BACKEND_URL
          value: "http://backend-service"
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
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
    targetPort: 80
```

```bash
kubectl apply -f frontend-deployment.yaml
```

**4. Crear recurso Ingress (usando AWS ALB Ingress Controller)**

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-ingress
  namespace: web-app
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /
spec:
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
```

```bash
kubectl apply -f ingress.yaml
```

**5. Configurar Horizontal Pod Autoscaling (HPA)**

```yaml
# hpa.yaml
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
```

```bash
kubectl apply -f hpa.yaml
```

**6. Comprobar el estado del despliegue**

```bash
# Check deployment status
kubectl get deployments -n web-app

# Check service status
kubectl get services -n web-app

# Check ingress status
kubectl get ingress -n web-app

# Check HPA status
kubectl get hpa -n web-app

# Get ALB address
kubectl get ingress web-app-ingress -n web-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

**7. Prueba de carga y verificación del escalado**

```bash
# Get ALB address
ALB_ADDRESS=$(kubectl get ingress web-app-ingress -n web-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Load test (requires separate tool)
# Example: Using Apache Bench
ab -n 10000 -c 100 http://$ALB_ADDRESS/

# Verify scaling
kubectl get hpa -n web-app -w
```

A través de este ejercicio, aprendiste cómo desplegar una aplicación con arquitectura de microservices en un clúster de EKS, exponerla externamente usando AWS ALB Ingress Controller y configurar auto-scaling mediante HPA. Los resource requests y limits se configuraron adecuadamente para garantizar un uso eficiente de recursos, y el enrutamiento basado en path se implementó mediante reglas de ingress.

</details>

## Temas avanzados

Las siguientes son preguntas sobre temas avanzados de Amazon EKS. Esta sección evalúa tu comprensión de características e integraciones avanzadas de EKS.

1. ¿Cuál es la descripción correcta al configurar un Fargate profile en Amazon EKS?
   * A) Los Fargate profiles especifican que los pods deben ejecutarse en Fargate según namespaces y labels específicos
   * B) Los Fargate profiles ejecutan automáticamente todos los pods en Fargate
   * C) Los Fargate profiles restringen la ejecución de pods a tipos específicos de instancias EC2
   * D) Los Fargate profiles establecen cuotas de recursos para todo el clúster

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Los Fargate profiles especifican que los pods deben ejecutarse en Fargate según namespaces y labels específicos**

**Explicación:** Un Amazon EKS Fargate profile es una configuración que especifica qué pods deben ejecutarse en Fargate según namespaces y labels específicos. Esto permite configurar una arquitectura híbrida usando tanto entornos de ejecución de contenedores serverless como nodos basados en EC2.

Características clave de Fargate profiles:

* **Ejecución selectiva**: Solo los pods que coinciden con las condiciones definidas en el profile se ejecutan en Fargate, no todos los pods.
* **Selectores de namespace y label**: Los pods se seleccionan según combinaciones específicas de namespace y label.
* **Especificación de subnet**: Puedes especificar private subnets donde se ejecutarán los pods.
* **Rol IAM**: Especifica el rol de ejecución IAM para pods de Fargate.

Ejemplo de creación de Fargate profile:

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --name my-fargate-profile \
  --namespace my-namespace \
  --labels app=my-app
```

Definición de Fargate profile basada en YAML:

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
* Los contenedores privileged no pueden ejecutarse.
* HostNetwork y HostPort no son compatibles.
* Los workloads de GPU no son compatibles.
* Se aplican costos por pod, por lo que es necesaria la planificación de costos.
* El storage se limita a storage efímero (volúmenes persistentes posibles mediante EFS).

Problemas con las otras opciones:

* Los Fargate profiles no ejecutan automáticamente todos los pods en Fargate; solo los pods que coinciden con los selectors se ejecutan en Fargate.
* Los Fargate profiles no están relacionados con tipos de instancias EC2; Fargate es un entorno de ejecución de contenedores serverless.
* Los Fargate profiles no establecen cuotas de recursos a nivel de clúster. Las cuotas de recursos se administran mediante Kubernetes ResourceQuota.

</details>

2. ¿Cuál es el orden correcto al realizar una actualización de clúster en Amazon EKS?
   * A) Actualización de worker nodes -> Actualización de control plane -> Actualización de add-ons
   * B) Actualización de control plane -> Actualización de worker nodes -> Actualización de add-ons
   * C) Actualización de add-ons -> Actualización de control plane -> Actualización de worker nodes
   * D) Actualizar todos los componentes simultáneamente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Actualización de control plane -> Actualización de worker nodes -> Actualización de add-ons**

**Explicación:** El orden correcto para una actualización de clúster de Amazon EKS es actualizar primero el control plane, luego los worker nodes y finalmente los add-ons. Este orden sigue el modelo de compatibilidad de versiones de Kubernetes y minimiza posibles problemas durante el proceso de actualización.

**1. Actualización del Control Plane**

* El control plane actúa como el cerebro del clúster y debe actualizarse primero.
* Kubernetes está diseñado para que el control plane pueda estar hasta 2 versiones menores por delante de los nodos.
* Las actualizaciones del control plane se pueden realizar mediante AWS Management Console, AWS CLI o eksctl.

```bash
# Control plane upgrade using AWS CLI
aws eks update-cluster-version --name my-cluster --kubernetes-version 1.28

# Control plane upgrade using eksctl
eksctl upgrade cluster --name=my-cluster --version=1.28 --approve
```

**2. Actualización de Worker Nodes**

* Después de completar la actualización del control plane, actualiza los worker nodes.
* Para managed node groups, las actualizaciones pueden realizarse mediante AWS Management Console, AWS CLI o eksctl.
* Para self-managed nodes, los nodos deben reemplazarse con nuevas AMI.

```bash
# Managed node group upgrade
aws eks update-nodegroup-version --cluster-name my-cluster --nodegroup-name my-nodegroup

# Managed node group upgrade using eksctl
eksctl upgrade nodegroup --cluster=my-cluster --name=my-nodegroup
```

**3. Actualización de Add-ons**

* Finalmente, actualiza los add-ons del clúster (kube-proxy, CoreDNS, Amazon VPC CNI, etc.).
* Los add-ons están diseñados para ser compatibles con versiones específicas de Kubernetes, por lo que deben actualizarse después de las actualizaciones del control plane y de los nodos.

```bash
# Add-on upgrade using AWS CLI
aws eks update-addon --cluster-name my-cluster --addon-name vpc-cni --addon-version v1.12.0-eksbuild.1

# Add-on upgrade using eksctl
eksctl update addon --name vpc-cni --version v1.12.0-eksbuild.1 --cluster my-cluster
```

**Mejores prácticas de actualización:**

* Verificar el estado del clúster y realizar backup antes de la actualización
* Probar primero la actualización en un entorno de prueba
* Considerar una estrategia de despliegue blue/green
* Configurar PodDisruptionBudget para minimizar la interrupción de workloads durante la actualización
* Actualizar una versión menor a la vez
* Validar workloads y componentes del sistema después de la actualización

Problemas con las otras opciones:

* Actualizar worker nodes antes del control plane puede causar problemas de compatibilidad de versiones.
* Actualizar add-ons primero puede hacer que las nuevas versiones de add-ons sean incompatibles con la versión antigua de Kubernetes.
* Actualizar todos los componentes simultáneamente es riesgoso, y es difícil identificar la causa si ocurren problemas.

</details>

3. ¿Cuál NO es una característica clave del plugin VPC CNI en Amazon EKS?
   * A) Asignar direcciones IP de VPC a pods
   * B) Aplicar security groups a nivel de pod
   * C) Cifrar el tráfico de red entre pods
   * D) Expandir direcciones IP mediante prefix delegation

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Cifrar el tráfico de red entre pods**

**Explicación:** El plugin Amazon VPC CNI (Container Network Interface) no cifra automáticamente el tráfico de red entre pods. El cifrado de tráfico pod-to-pod no es una característica básica de VPC CNI y requiere herramientas adicionales como service meshes (por ejemplo, AWS App Mesh, Istio) o soluciones de network policy (por ejemplo, Calico, Cilium).

Las características clave reales del plugin Amazon VPC CNI incluyen:

1. **Asignar direcciones IP de VPC a pods**:
   * Cada pod recibe una dirección IP única dentro de la VPC.
   * Esto permite que los pods se comuniquen directamente con otros recursos en la VPC.
   * Las IP de pod son enrutables dentro de la VPC, lo que elimina la necesidad de overlay networks complejas.
2. **Aplicar security groups a nivel de pod**:
   * Los security groups de AWS se pueden aplicar a pods individuales mediante la característica SecurityGroupsForPods.
   * Esto permite implementar políticas de seguridad de red granulares a nivel de pod.
   *   Configuración de ejemplo:

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
3. **Expandir direcciones IP mediante prefix delegation**:
   * De forma predeterminada, cada nodo puede asignar un número limitado de direcciones IP (varía según el tipo de instancia) a pods.
   * Usando la característica prefix delegation, puedes asignar bloques CIDR /28 (16 IP) a cada nodo, lo que aumenta las direcciones IP disponibles.
   * Esto resuelve problemas de escasez de direcciones IP en escenarios de despliegue de alta densidad.
4. **Redes personalizadas**:
   * Los pods pueden ubicarse en subnets específicas.
   * La red de pods puede configurarse usando varias network interfaces.
5. **Integración con host networking**:
   * Los pods pueden usar directamente el stack de red del host.
   * Útil para workloads donde el rendimiento de red es crítico.

Ejemplos de configuración de VPC CNI:

```bash
# Enable prefix delegation
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

# Enable security group pods feature
kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

# Enable custom networking
kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
```

Para implementar cifrado de tráfico de red entre pods, considera las siguientes alternativas:

* Usar AWS App Mesh con TLS
* Implementar Istio service mesh
* Usar la característica de cifrado transparente de Cilium
* Implementar TLS/mTLS a nivel de aplicación

</details>

4. ¿Cuál es el método correcto para configurar control de acceso basado en roles IAM (RBAC) para la autenticación de clúster en Amazon EKS?
   * A) Asignar directamente roles Kubernetes RBAC a usuarios IAM
   * B) Configurar mapeos de roles IAM y grupos Kubernetes en el aws-auth ConfigMap
   * C) Adjuntar directamente políticas IAM al clúster de EKS
   * D) Vincular roles IAM a Kubernetes service accounts

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar mapeos de roles IAM y grupos Kubernetes en el aws-auth ConfigMap**

**Explicación:** El método correcto para configurar control de acceso basado en roles IAM (RBAC) para la autenticación de clúster en Amazon EKS es configurar mapeos entre roles IAM y grupos Kubernetes usando el `aws-auth` ConfigMap. Este método permite integrar credenciales de AWS IAM con el sistema Kubernetes RBAC.

**Cómo funciona aws-auth ConfigMap:**

1. EKS usa AWS IAM Authenticator para autenticar solicitudes de API.
2. El `aws-auth` ConfigMap mapea entidades IAM (usuarios o roles) a usuarios y grupos de Kubernetes.
3. El sistema Kubernetes RBAC otorga permisos a estos usuarios y grupos.

**Ejemplo de configuración de aws-auth ConfigMap:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/EksAdminRole
      username: eks-admin
      groups:
        - system:masters
    - rolearn: arn:aws:iam::123456789012:role/DevTeamRole
      username: dev-team
      groups:
        - dev-group
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/admin-user
      username: admin
      groups:
        - system:masters
    - userarn: arn:aws:iam::123456789012:user/read-only-user
      username: read-only
      groups:
        - read-only-group
```

**Configuración de roles y bindings de Kubernetes RBAC:**

```yaml
# Create developer role
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: developer
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["pods", "deployments", "jobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

---
# Bind role to developer group
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-binding
  namespace: dev
subjects:
- kind: Group
  name: dev-group
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

**Configuración de IAM y RBAC usando eksctl:**

```bash
# Add IAM role mapping
eksctl create iamidentitymapping \
  --cluster my-cluster \
  --arn arn:aws:iam::123456789012:role/EksAdminRole \
  --username eks-admin \
  --group system:masters

# Add IAM user mapping
eksctl create iamidentitymapping \
  --cluster my-cluster \
  --arn arn:aws:iam::123456789012:user/admin-user \
  --username admin \
  --group system:masters
```

**Mejores prácticas:**

* Aplicar el principio de privilegio mínimo
* Preferir roles IAM sobre usuarios IAM individuales
* Separar permisos por namespace
* Revisar regularmente los permisos de acceso
* Otorgar permisos de administrador de clúster (system:masters) con moderación

Problemas con las otras opciones:

* Los roles Kubernetes RBAC no se pueden asignar directamente a usuarios IAM. Como IAM y Kubernetes son sistemas separados, se requiere el mapeo mediante el aws-auth ConfigMap.
* Adjuntar directamente políticas IAM al clúster de EKS no está relacionado con permisos RBAC dentro del clúster. Las políticas IAM controlan permisos de llamadas API sobre el clúster en sí.
* Vincular roles IAM a Kubernetes service accounts (IRSA) es para que los pods accedan a servicios de AWS y cumple un propósito diferente al de la autenticación y autorización del clúster.

</details>

5. ¿Cuál es la descripción correcta de la política de soporte de versiones de Kubernetes de Amazon EKS?
   * A) Todas las versiones de Kubernetes se admiten indefinidamente
   * B) Cada versión de Kubernetes se admite durante 12 meses después de su lanzamiento
   * C) Solo se admite la versión más reciente y las 3 versiones anteriores
   * D) Cada versión de Kubernetes se admite durante 14 meses después de su lanzamiento

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Cada versión de Kubernetes se admite durante 14 meses después de su lanzamiento**

**Explicación:** Según la política de soporte de versiones de Kubernetes de Amazon EKS, cada versión de Kubernetes se admite durante 14 meses después de su lanzamiento en EKS. Después de este período, la versión deja de tener soporte y debes actualizar tu clúster a una versión compatible.

**Características clave de la política de soporte de versiones de EKS:**

1. **Período de soporte de 14 meses**:
   * Cada versión de Kubernetes se admite durante 14 meses desde la fecha en que se lanzó en EKS.
   * AWS anuncia con anticipación las fechas de fin de soporte.
2. **Calendario de soporte estándar**:
   * La comunidad de Kubernetes lanza una nueva versión aproximadamente cada 4 meses.
   * EKS normalmente admite nuevas versiones de Kubernetes dentro de 2-3 meses después del lanzamiento de la comunidad.
   * Esto resulta típicamente en 3-4 versiones de Kubernetes admitidas simultáneamente en EKS.
3. **Sin actualizaciones automáticas**:
   * AWS no actualiza automáticamente los clústeres incluso cuando finaliza el soporte.
   * Los administradores de clúster deben realizar actualizaciones explícitamente.
4. **Impacto después de que finaliza el soporte**:
   * Los clústeres que se ejecutan en versiones sin soporte continúan operando, pero AWS ya no proporciona parches de seguridad ni correcciones de errores.
   * No se pueden crear nuevos clústeres en versiones sin soporte.
   * El soporte de AWS no está disponible.

**Mejores prácticas de actualización de versiones:**

* Establecer calendarios de actualización regulares
* Monitorear fechas de fin de soporte
* Probar primero las actualizaciones en entornos de prueba
* Realizar backup del clúster antes de la actualización
* Actualizar una versión menor a la vez
* Considerar una estrategia de despliegue blue/green

**Comprobar el estado de soporte de versiones:**

```bash
# Check available EKS versions
aws eks describe-addon-versions | grep kubernetesVersion

# Check specific cluster version
aws eks describe-cluster --name my-cluster --query "cluster.version"
```

Problemas con las otras opciones:

* No todas las versiones de Kubernetes se admiten indefinidamente. Cada versión solo se admite durante un período definido.
* Cada versión se admite durante 14 meses, no 12 meses.
* No existe una regla fija de "solo se admite la versión más reciente y las 3 versiones anteriores"; el número de versiones admitidas varía según el calendario de lanzamientos de la comunidad de Kubernetes y la política de soporte de EKS.

</details>
