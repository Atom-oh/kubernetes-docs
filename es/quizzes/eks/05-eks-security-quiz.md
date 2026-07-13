# Cuestionario sobre seguridad de Amazon EKS

Este cuestionario evalúa tu comprensión de las características de seguridad, mejores prácticas y configuraciones de Amazon EKS.

## Descripción general del cuestionario
- Autenticación y autorización de EKS
- Seguridad de red
- Seguridad de contenedores
- Seguridad de datos
- Cumplimiento y auditoría
- Mejores prácticas de seguridad

## Preguntas de opción múltiple

### 1. ¿Cuál es la forma más efectiva de controlar el acceso al Kubernetes API server en Amazon EKS?

A. Usar solo usuarios y roles de IAM
B. Usar solo Kubernetes RBAC
C. Usar IAM y Kubernetes RBAC integrados
D. Usar solo restricciones de acceso de red al API server

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Usar IAM y Kubernetes RBAC integrados**

**Explicación:**
La forma más efectiva de controlar el acceso al Kubernetes API server en Amazon EKS es usar una integración de AWS IAM y Kubernetes RBAC (Role-Based Access Control). Este enfoque combina las potentes capacidades de gestión de identidad de AWS con el control de permisos detallado de Kubernetes para proporcionar un modelo de seguridad integral.

**Beneficios clave de la integración de IAM y RBAC:**

1. **Autenticación y autorización multicapa**:
   - IAM controla "quién" puede conectarse al API server (autenticación)
   - RBAC controla "qué" pueden hacer los usuarios autenticados (autorización)

2. **Integración fluida con servicios de AWS**:
   - Aprovechar las políticas y roles de AWS IAM existentes
   - Utilizar cuentas de servicio de AWS e identidades de workloads

3. **Control de permisos detallado**:
   - Definir permisos detallados para namespaces, tipos de recursos y recursos específicos
   - Implementar el principio de privilegio mínimo

**Métodos de implementación:**

1. **Configurar aws-auth ConfigMap**:
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: aws-auth
     namespace: kube-system
   data:
     mapRoles: |
       - rolearn: arn:aws:iam::123456789012:role/EKSAdminRole
         username: admin
         groups:
         - system:masters
       - rolearn: arn:aws:iam::123456789012:role/EKSDeveloperRole
         username: developer
         groups:
         - developers
     mapUsers: |
       - userarn: arn:aws:iam::123456789012:user/security-auditor
         username: security-auditor
         groups:
         - security-auditors
   ```

2. **Definir Kubernetes RBAC Roles y Bindings**:
   ```yaml
   # Developer role definition
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     namespace: dev
     name: developer
   rules:
   - apiGroups: ["", "apps", "batch"]
     resources: ["pods", "deployments", "jobs"]
     verbs: ["get", "list", "watch", "create", "update", "patch"]
   ---
   # Developer role binding
   apiVersion: rbac.authorization.k8s.io/v1
   kind: RoleBinding
   metadata:
     name: developer-binding
     namespace: dev
   subjects:
   - kind: Group
     name: developers
     apiGroup: rbac.authorization.k8s.io
   roleRef:
     kind: Role
     name: developer
     apiGroup: rbac.authorization.k8s.io
   ```

3. **Ejemplo de política de IAM**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "eks:DescribeCluster",
           "eks:ListClusters"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

**Mejores prácticas:**

1. **Aplicar el principio de privilegio mínimo**:
   - Conceder solo los permisos mínimos necesarios
   - Revisar y auditar los permisos con regularidad

2. **Implementar acceso basado en roles**:
   - Definir roles según las funciones laborales
   - Asignar permisos a roles, no a individuos

3. **Usar credenciales temporales**:
   - Usar credenciales temporales en lugar de credenciales de largo plazo
   - Aprovechar AWS STS (Security Token Service)

4. **Auditoría y monitoreo regulares**:
   - Registrar llamadas a la API mediante CloudTrail
   - Habilitar y analizar los logs de auditoría de Kubernetes

**Ejemplos prácticos de implementación:**

1. **Crear un IAM Role para acceso al EKS Cluster**:
   ```bash
   aws iam create-role \
     --role-name EKSDevRole \
     --assume-role-policy-document file://trust-policy.json

   aws iam attach-role-policy \
     --role-name EKSDevRole \
     --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
   ```

2. **Actualizar kubeconfig**:
   ```bash
   aws eks update-kubeconfig \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/EKSDevRole \
     --region us-west-2
   ```

3. **Aplicar la configuración de RBAC**:
   ```bash
   kubectl apply -f rbac-config.yaml
   ```

Problemas con otras opciones:
- **A. Usar solo usuarios y roles de IAM**: IAM puede controlar el acceso al cluster, pero no proporciona permisos detallados para recursos de Kubernetes.
- **B. Usar solo Kubernetes RBAC**: RBAC controla los permisos dentro del cluster, pero carece de integración con servicios de AWS y no proporciona seguridad a nivel de infraestructura de AWS.
- **D. Usar solo restricciones de acceso de red al API server**: El control a nivel de red es importante, pero no restringe los permisos de los usuarios autenticados ni proporciona control de acceso detallado.
</details>
### 2. ¿Cuál es la forma más efectiva de restringir el tráfico de red entre Pods en Amazon EKS?

A. Usar solo security groups
B. Usar Kubernetes Network Policies
C. Usar políticas de VPC endpoint
D. Usar firewalls basados en host

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar Kubernetes Network Policies**

**Explicación:**
La forma más efectiva de restringir el tráfico de red entre Pods en Amazon EKS es usar Kubernetes Network Policies. Las Network Policies proporcionan microsegmentación a nivel de Pod, lo que permite un control detallado sobre la comunicación entre Pods.

**Beneficios clave de Kubernetes Network Policies:**

1. **Control detallado a nivel de Pod**:
   - Filtrado basado en direcciones IP, puertos y protocolos
   - Aplicación dinámica de políticas mediante selectores basados en labels
   - Control tanto del tráfico ingress como egress

2. **Configuración declarativa**:
   - Gestionadas como recursos de Kubernetes
   - Integración con flujos de trabajo GitOps e IaC
   - Control de versiones y auditabilidad

3. **Integración con CNI Plugins**:
   - Integración con Amazon VPC CNI, Calico, Cilium, etc.
   - Varias opciones para aplicar políticas de red

**Métodos de implementación:**

1. **Implementar una política Default Deny**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny
     namespace: prod
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
   ```

2. **Permitir comunicación entre aplicaciones específicas**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: api-allow
     namespace: prod
   spec:
     podSelector:
       matchLabels:
         app: api
     policyTypes:
     - Ingress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: frontend
       ports:
       - protocol: TCP
         port: 8080
   ```

3. **Controlar la comunicación entre namespaces**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-from-monitoring
     namespace: prod
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             purpose: monitoring
       ports:
       - protocol: TCP
         port: 9090
   ```

**Implementación de Network Policies en EKS:**

1. **Seleccionar un CNI Plugin compatible**:
   - Amazon VPC CNI + Calico
   - Cilium
   - Antrea

2. **Ejemplo de instalación de Calico**:
   ```bash
   kubectl apply -f https://docs.projectcalico.org/manifests/calico-vxlan.yaml
   ```

3. **Ejemplo de instalación de Cilium**:
   ```bash
   helm repo add cilium https://helm.cilium.io/
   helm install cilium cilium/cilium \
     --namespace kube-system \
     --set nodeinit.enabled=true \
     --set kubeProxyReplacement=partial \
     --set hostServices.enabled=false \
     --set externalIPs.enabled=true \
     --set nodePort.enabled=true \
     --set hostPort.enabled=true \
     --set bpf.masquerade=false \
     --set image.pullPolicy=IfNotPresent
   ```

**Mejores prácticas:**

1. **Comenzar con una política Default Deny**:
   - Bloquear todo el tráfico de forma predeterminada
   - Permitir explícitamente solo la comunicación necesaria

2. **Aplicar el principio de privilegio mínimo**:
   - Permitir solo la comunicación mínima necesaria
   - Restringir a puertos y protocolos específicos

3. **Usar políticas basadas en labels**:
   - Usar labels en lugar de direcciones IP
   - Proporcionar flexibilidad en entornos dinámicos

4. **Probar y validar políticas**:
   - Probar políticas en entornos que no sean de producción
   - Utilizar herramientas de simulación de políticas de red

**Ejemplos prácticos de implementación:**

1. **Network Policy para arquitectura de microservices**:
   ```yaml
   # Allow only frontend to API communication
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: api-backend
     namespace: prod
   spec:
     podSelector:
       matchLabels:
         app: api
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: frontend
       ports:
       - protocol: TCP
         port: 8080
     egress:
     - to:
       - podSelector:
           matchLabels:
             app: database
       ports:
       - protocol: TCP
         port: 5432
   ```

2. **Restringir acceso a servicios externos**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: limit-external
     namespace: prod
   spec:
     podSelector:
       matchLabels:
         app: backend
     policyTypes:
     - Egress
     egress:
     - to:
       - ipBlock:
           cidr: 10.0.0.0/8
     - to:
       - ipBlock:
           cidr: 0.0.0.0/0
           except:
           - 169.254.0.0/16
           - 10.0.0.0/8
       ports:
       - protocol: TCP
         port: 443
   ```

Problemas con otras opciones:
- **A. Usar solo security groups**: Los security groups operan a nivel de instancia y no proporcionan control detallado del tráfico entre Pods.
- **C. Usar políticas de VPC endpoint**: Las políticas de VPC endpoint controlan el acceso a servicios de AWS, pero no controlan la comunicación de Pod a Pod.
- **D. Usar firewalls basados en host**: Los firewalls basados en host operan a nivel de node y no pueden controlar de manera efectiva la comunicación entre Pods que se ejecutan en el mismo node.
</details>
### 3. ¿Cuál es el enfoque más efectivo para mejorar la seguridad de imágenes de contenedor en Amazon EKS?

A. Realizar verificaciones manuales de seguridad en todas las imágenes
B. Usar solo imágenes oficiales de confianza
C. Implementar un pipeline integrado que incluya escaneo de imágenes, verificación de firmas y políticas de admisión
D. Ejecutar software antivirus dentro de contenedores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Implementar un pipeline integrado que incluya escaneo de imágenes, verificación de firmas y políticas de admisión**

**Explicación:**
El enfoque más efectivo para mejorar la seguridad de imágenes de contenedor en Amazon EKS es implementar un pipeline integrado que incluya escaneo de imágenes, verificación de firmas y políticas de admisión. Este enfoque integral garantiza la seguridad durante todo el ciclo de vida de la imagen, desde la compilación hasta el Deployment.

**Componentes clave de un pipeline integrado de seguridad de imágenes:**

1. **Escaneo de imágenes**:
   - Comprobar vulnerabilidades conocidas (CVEs)
   - Detectar malware y backdoors
   - Identificar configuraciones incorrectas y violaciones de mejores prácticas de seguridad

2. **Firma y verificación de imágenes**:
   - Garantizar la integridad de la imagen
   - Verificar fuentes de confianza
   - Prevenir manipulaciones

3. **Políticas de admisión**:
   - Permitir el Deployment solo de imágenes aprobadas
   - Aplicar requisitos mínimos de imagen base
   - Establecer umbrales de severidad de vulnerabilidades

**Métodos de implementación:**

1. **Configurar el escaneo de imágenes de Amazon ECR**:
   ```bash
   # Enable scanning when creating repository
   aws ecr create-repository \
     --repository-name my-app \
     --image-scanning-configuration scanOnPush=true

   # Enable scanning for existing repository
   aws ecr put-image-scanning-configuration \
     --repository-name my-app \
     --image-scanning-configuration scanOnPush=true
   ```

2. **Firmar imágenes usando AWS Signer**:
   ```bash
   # Create signing profile
   aws signer put-signing-profile \
     --profile-name MyAppSigningProfile \
     --platform-id Aws::ECR::Image

   # Sign image
   aws signer start-signing-job \
     --source "s3={bucketName=my-bucket,key=my-image.tar}" \
     --destination "s3={bucketName=my-bucket,prefix=signed/}" \
     --profile-name MyAppSigningProfile
   ```

3. **Aplicar políticas de imágenes usando Kyverno**:
   ```yaml
   apiVersion: kyverno.io/v1
   kind: ClusterPolicy
   metadata:
     name: require-signed-images
   spec:
     validationFailureAction: enforce
     rules:
     - name: verify-image-signature
       match:
         resources:
           kinds:
           - Pod
       verifyImages:
       - image: "*.dkr.ecr.*.amazonaws.com/*"
         key: "https://my-keystore.com/keys/my-key.pub"
   ```

4. **Aplicar políticas de imágenes usando OPA Gatekeeper**:
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sTrustedImages
   metadata:
     name: trusted-repos
   spec:
     match:
       kinds:
       - apiGroups: [""]
         kinds: ["Pod"]
     parameters:
       repos:
       - "123456789012.dkr.ecr.us-west-2.amazonaws.com/*"
       - "docker.io/library/*"
   ```

**Creación de un pipeline integrado:**

1. **Integración con pipeline de CI/CD**:
   ```yaml
   # AWS CodePipeline example
   version: 0.2
   phases:
     pre_build:
       commands:
         - echo Logging in to Amazon ECR...
         - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI
     build:
       commands:
         - echo Building the Docker image...
         - docker build -t $ECR_REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION .
     post_build:
       commands:
         - echo Running security scan...
         - trivy image --exit-code 1 --severity HIGH,CRITICAL $ECR_REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION
         - echo Signing the image...
         - aws signer start-signing-job --profile-name MyAppSigningProfile --source-image $ECR_REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION
         - echo Pushing the Docker image...
         - docker push $ECR_REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION
   ```

2. **Implementar Image Admission Controller**:
   ```bash
   # Install Kyverno
   kubectl create -f https://github.com/kyverno/kyverno/releases/download/v1.8.0/install.yaml

   # Apply policy
   kubectl apply -f image-policy.yaml
   ```

**Mejores prácticas:**

1. **Usar imágenes base mínimas**:
   - Minimizar la superficie de ataque
   - Incluir solo los componentes necesarios
   - Usar imágenes distroless o ligeras

2. **Implementar defensa en profundidad**:
   - Escaneo en tiempo de compilación
   - Validación previa al Deployment
   - Monitoreo en runtime

3. **Actualizar imágenes con regularidad**:
   - Aplicar los parches de seguridad más recientes
   - Actualizar imágenes base con regularidad
   - Monitorear vulnerabilidades de forma continua

4. **Usar imágenes inmutables**:
   - No modificar imágenes después del Deployment
   - Crear e implementar nuevas imágenes cuando se necesiten cambios
   - Soportar gestión de versiones y rollback

**Ejemplos prácticos de implementación:**

1. **Integración de Amazon ECR, AWS CodePipeline y Kyverno**:
   ```yaml
   # buildspec.yml
   version: 0.2
   phases:
     pre_build:
       commands:
         - echo Logging in to Amazon ECR...
         - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI
         - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
         - IMAGE_TAG=${COMMIT_HASH:=latest}
     build:
       commands:
         - echo Building the Docker image...
         - docker build -t $ECR_REPOSITORY_URI:$IMAGE_TAG .
     post_build:
       commands:
         - echo Running Trivy security scan...
         - trivy image --exit-code 1 --severity HIGH,CRITICAL $ECR_REPOSITORY_URI:$IMAGE_TAG
         - echo Pushing the Docker image...
         - docker push $ECR_REPOSITORY_URI:$IMAGE_TAG
         - echo Creating image definition file...
         - aws ecr describe-images --repository-name $(echo $ECR_REPOSITORY_URI | cut -d'/' -f2) --image-ids imageTag=$IMAGE_TAG --query 'imageDetails[].imageTags[0]' --output text
   artifacts:
     files:
       - imagedefinitions.json
   ```

2. **Política de imágenes de Kyverno**:
   ```yaml
   apiVersion: kyverno.io/v1
   kind: ClusterPolicy
   metadata:
     name: restrict-image-registries
   spec:
     validationFailureAction: enforce
     background: true
     rules:
     - name: allowed-registries
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Only images from approved registries are allowed"
         pattern:
           spec:
             containers:
             - image: "{{ regex_match('123456789012.dkr.ecr.*.amazonaws.com/*|docker.io/library/*', '@@') }}"
   ```

Problemas con otras opciones:
- **A. Realizar verificaciones manuales de seguridad en todas las imágenes**: Las verificaciones manuales no escalan, carecen de consistencia y no son prácticas en entornos de Deployment continuo.
- **B. Usar solo imágenes oficiales de confianza**: Incluso las imágenes oficiales pueden tener vulnerabilidades, y a menudo se necesitan imágenes personalizadas.
- **D. Ejecutar software antivirus dentro de contenedores**: Ejecutar antivirus dentro de contenedores consume muchos recursos, viola los principios de diseño de contenedores y no aborda los problemas de seguridad en la etapa de creación de la imagen.
</details>
### 4. ¿Cuál es la forma más efectiva de mejorar la seguridad de Pods en Amazon EKS?

A. Deshabilitar el modo privilegiado para todos los Pods
B. Implementar Pod Security Standards (PSS) y Pod Security Policies (PSP)
C. Ejecutar todos los Pods como usuarios no root
D. Usar sistemas de archivos de solo lectura para todos los Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Implementar Pod Security Standards (PSS) y Pod Security Policies (PSP)**

**Explicación:**
La forma más efectiva de mejorar la seguridad de Pods en Amazon EKS es implementar Pod Security Standards (PSS) y Pod Security Policies (PSP) o sus mecanismos de reemplazo. Estos mecanismos controlan el security context de los Pods y aplican estándares de seguridad coherentes en todo el cluster.

**Nota**: Desde Kubernetes 1.25, PSP (Pod Security Policy) está obsoleto, y en su lugar se recomiendan PSS (Pod Security Standards) con PSA (Pod Security Admission). En EKS, puedes implementar funcionalidad similar usando motores de políticas como Kyverno u OPA Gatekeeper.

**Beneficios clave de Pod Security Standards y Policies:**

1. **Aplicar estándares de seguridad coherentes**:
   - Aplicar controles de seguridad coherentes en todo el cluster
   - Prevenir la escalada de privilegios
   - Reducir el riesgo de escape de contenedores

2. **Soportar varios niveles de seguridad**:
   - Privileged: Sin restricciones
   - Baseline: Aplicar restricciones básicas
   - Restricted: Aplicar controles de seguridad estrictos

3. **Controles de seguridad detallados**:
   - Limitar la escalada de privilegios
   - Restringir el acceso a namespaces del host
   - Restringir tipos de volumen
   - Restringir IDs de usuario y grupo

**Métodos de implementación:**

1. **Aplicar Pod Security Standards (PSS)**:
   ```yaml
   # Apply PSS labels to namespace
   apiVersion: v1
   kind: Namespace
   metadata:
     name: secure-ns
     labels:
       pod-security.kubernetes.io/enforce: restricted
       pod-security.kubernetes.io/audit: restricted
       pod-security.kubernetes.io/warn: restricted
   ```

2. **Implementar Pod Security Policy usando Kyverno**:
   ```yaml
   apiVersion: kyverno.io/v1
   kind: ClusterPolicy
   metadata:
     name: restrict-privileged
   spec:
     validationFailureAction: enforce
     rules:
     - name: no-privileged-pods
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Privileged mode is not allowed"
         pattern:
           spec:
             containers:
             - name: "*"
               securityContext:
                 privileged: false
   ```

3. **Implementar Pod Security Policy usando OPA Gatekeeper**:
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sPSPPrivilegedContainer
   metadata:
     name: no-privileged-containers
   spec:
     match:
       kinds:
       - apiGroups: [""]
         kinds: ["Pod"]
   ```

**Controles clave de seguridad de Pods:**

1. **Restringir el modo privilegiado**:
   ```yaml
   securityContext:
     privileged: false
   ```

2. **Ejecutar como usuario no root**:
   ```yaml
   securityContext:
     runAsUser: 1000
     runAsGroup: 3000
     fsGroup: 2000
   ```

3. **Restringir capacidades**:
   ```yaml
   securityContext:
     capabilities:
       drop:
       - ALL
       add:
       - NET_BIND_SERVICE
   ```

4. **Root Filesystem de solo lectura**:
   ```yaml
   securityContext:
     readOnlyRootFilesystem: true
   ```

5. **Aplicar seccomp Profile**:
   ```yaml
   securityContext:
     seccompProfile:
       type: RuntimeDefault
   ```

**Mejores prácticas:**

1. **Aplicar el principio de privilegio mínimo**:
   - Conceder solo los permisos mínimos necesarios
   - Limitar el uso del modo privilegiado
   - Permitir solo las capacidades necesarias

2. **Implementar defensa en profundidad**:
   - Políticas a nivel de namespace
   - Políticas a nivel de cluster
   - Monitoreo de seguridad en runtime

3. **Definir explícitamente el Security Context**:
   - No depender de los valores predeterminados
   - Especificar el security context para todos los contenedores
   - Revisar las configuraciones de seguridad con regularidad

4. **Gestionar excepciones de políticas**:
   - Definir procesos claros cuando se necesiten excepciones
   - Revisar y auditar excepciones con regularidad
   - Minimizar las excepciones

**Ejemplos prácticos de implementación:**

1. **Definición de Pod con seguridad mejorada**:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: secure-pod
   spec:
     securityContext:
       fsGroup: 2000
       runAsNonRoot: true
       runAsUser: 1000
       seccompProfile:
         type: RuntimeDefault
     containers:
     - name: app
       image: my-secure-app:1.0
       securityContext:
         allowPrivilegeEscalation: false
         capabilities:
           drop:
           - ALL
         readOnlyRootFilesystem: true
         runAsNonRoot: true
         runAsUser: 1000
         seccompProfile:
           type: RuntimeDefault
   ```

2. **Colección de políticas de Kyverno**:
   ```yaml
   apiVersion: kyverno.io/v1
   kind: ClusterPolicy
   metadata:
     name: pod-security
   spec:
     validationFailureAction: enforce
     rules:
     - name: no-privileged
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Privileged containers are not allowed"
         pattern:
           spec:
             containers:
             - name: "*"
               securityContext:
                 privileged: false
     - name: no-privilege-escalation
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Privilege escalation is not allowed"
         pattern:
           spec:
             containers:
             - name: "*"
               securityContext:
                 allowPrivilegeEscalation: false
     - name: require-non-root
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Running as root is not allowed"
         pattern:
           spec:
             containers:
             - name: "*"
               securityContext:
                 runAsNonRoot: true
   ```

Problemas con otras opciones:
- **A. Deshabilitar el modo privilegiado para todos los Pods**: Deshabilitar el modo privilegiado es importante, pero es solo un aspecto de la seguridad de Pods y no proporciona una estrategia de seguridad integral.
- **C. Ejecutar todos los Pods como usuarios no root**: Ejecutar como no root es una buena práctica, pero no aborda otros controles de seguridad importantes (por ejemplo, capabilities, montajes de volumen, acceso a namespaces del host).
- **D. Usar sistemas de archivos de solo lectura para todos los Pods**: Los sistemas de archivos de solo lectura son un control de seguridad útil, pero no son adecuados para todas las aplicaciones y no abordan otros aspectos importantes de seguridad.
</details>
### 5. ¿Cuál es el enfoque más efectivo para monitorear y auditar el cumplimiento de seguridad en Amazon EKS?

A. Realizar revisiones manuales de seguridad
B. Usar solo reglas de AWS Config
C. Usar solo AWS GuardDuty
D. Usar AWS Security Hub, GuardDuty, CloudTrail y logs de auditoría de Kubernetes integrados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Usar AWS Security Hub, GuardDuty, CloudTrail y logs de auditoría de Kubernetes integrados**

**Explicación:**
El enfoque más efectivo para monitorear y auditar el cumplimiento de seguridad en Amazon EKS es integrar AWS Security Hub, GuardDuty, CloudTrail y los logs de auditoría de Kubernetes. Este enfoque integrado proporciona visibilidad de seguridad integral a nivel de infraestructura, cluster y aplicación.

**Beneficios clave del monitoreo y la auditoría de seguridad integrados:**

1. **Visibilidad de seguridad multicapa**:
   - Monitoreo a nivel de infraestructura de AWS
   - Auditoría a nivel de cluster de Kubernetes
   - Eventos de seguridad a nivel de contenedor y aplicación

2. **Verificaciones de cumplimiento automatizadas**:
   - Verificar el cumplimiento con estándares del sector y mejores prácticas
   - Detectar desviaciones de configuración
   - Monitoreo continuo del cumplimiento

3. **Gestión centralizada de seguridad**:
   - Ver el estado de seguridad desde un único dashboard
   - Alertas y respuesta integradas
   - Informes de seguridad completos

**Métodos de implementación:**

1. **Habilitar AWS Security Hub**:
   ```bash
   # Enable Security Hub
   aws securityhub enable-security-hub \
     --enable-default-standards \
     --tags Environment=Production
   ```

2. **Habilitar Amazon GuardDuty EKS Protection**:
   ```bash
   # Enable GuardDuty
   aws guardduty create-detector \
     --enable \
     --finding-publishing-frequency FIFTEEN_MINUTES

   # Enable EKS Protection
   aws guardduty update-detector \
     --detector-id $(aws guardduty list-detectors --query 'DetectorIds[0]' --output text) \
     --features '[{"Name": "EKS_RUNTIME_MONITORING", "Status": "ENABLED"}]'
   ```

3. **Configurar CloudTrail Logging**:
   ```bash
   # Create CloudTrail trail
   aws cloudtrail create-trail \
     --name eks-audit-trail \
     --s3-bucket-name my-eks-audit-logs \
     --is-multi-region-trail \
     --enable-log-file-validation

   # Enable trail logging
   aws cloudtrail start-logging \
     --name eks-audit-trail
   ```

4. **Habilitar EKS Audit Logs**:
   ```bash
   # Enable audit logs when creating cluster
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/EKSClusterRole \
     --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345 \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

   # Enable audit logs for existing cluster
   aws eks update-cluster-config \
     --name my-cluster \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   ```

**Componentes clave de monitoreo y auditoría:**

1. **AWS Security Hub**:
   - Aplicar estándares de mejores prácticas de EKS
   - Verificaciones del benchmark CIS Kubernetes
   - Centralizar hallazgos de seguridad

2. **Amazon GuardDuty**:
   - Monitoreo de runtime de EKS
   - Detección de amenazas en contenedores
   - Detección de anomalías

3. **AWS CloudTrail**:
   - Registrar llamadas a la API del control plane de EKS
   - Rastrear eventos de gestión
   - Auditar actividad de usuarios

4. **Kubernetes Audit Logs**:
   - Registrar actividad dentro del cluster
   - Rastrear solicitudes al API server
   - Monitorear cambios de permisos

5. **Amazon CloudWatch**:
   - Centralizar logs
   - Monitorear métricas
   - Configurar alertas

**Mejores prácticas:**

1. **Implementar una estrategia integral de logging**:
   - Habilitar todas las fuentes de logs relevantes
   - Establecer políticas de retención de logs adecuadas
   - Garantizar la integridad de los logs

2. **Configurar verificaciones de cumplimiento automatizadas**:
   - Programar escaneos de cumplimiento regulares
   - Configurar alertas para violaciones críticas
   - Automatizar informes de cumplimiento

3. **Establecer planes de respuesta para eventos de seguridad**:
   - Definir rutas de escalamiento claras
   - Implementar respuestas automatizadas
   - Probar los planes de respuesta con regularidad

4. **Aplicar el principio de privilegio mínimo**:
   - Restringir el acceso a logs de auditoría
   - Control de acceso basado en roles para herramientas de seguridad
   - Revisar permisos con regularidad

**Ejemplos prácticos de implementación:**

1. **Integración de AWS Security Hub y GuardDuty**:
   ```bash
   # Send Security Hub findings to SNS topic
   aws events put-rule \
     --name SecurityHubFindings \
     --event-pattern '{"source":["aws.securityhub"],"detail-type":["Security Hub Findings - Imported"]}'

   aws events put-targets \
     --rule SecurityHubFindings \
     --targets 'Id"="1","Arn"="arn:aws:sns:us-west-2:123456789012:security-alerts"'
   ```

2. **Análisis de logs de auditoría con CloudWatch Logs Insights**:
   ```
   fields @timestamp, @message
   | filter @logStream like /kube-apiserver-audit/
   | filter @message like "system:serviceaccount"
   | filter @message like "create" or @message like "update" or @message like "delete"
   | sort @timestamp desc
   | limit 100
   ```

3. **Monitorear la configuración de EKS con AWS Config Rules**:
   ```bash
   # Create Config rule to check if EKS cluster endpoint is public
   aws configservice put-config-rule \
     --config-rule file://eks-endpoint-rule.json
   ```

4. **Configurar infraestructura de monitoreo de seguridad con Terraform**:
   ```hcl
   # Enable GuardDuty
   resource "aws_guardduty_detector" "main" {
     enable = true
     finding_publishing_frequency = "FIFTEEN_MINUTES"
   }

   # Enable EKS Protection
   resource "aws_guardduty_detector_feature" "eks_runtime" {
     detector_id = aws_guardduty_detector.main.id
     name        = "EKS_RUNTIME_MONITORING"
     status      = "ENABLED"
   }

   # Enable Security Hub
   resource "aws_securityhub_account" "main" {}

   # Enable EKS standards
   resource "aws_securityhub_standards_subscription" "cis_eks" {
     depends_on    = [aws_securityhub_account.main]
     standards_arn = "arn:aws:securityhub:${data.aws_region.current.name}::standards/aws-foundational-security-best-practices/v/1.0.0"
   }
   ```

Problemas con otras opciones:
- **A. Realizar revisiones manuales de seguridad**: Las revisiones manuales no escalan, no proporcionan detección de amenazas en tiempo real y son propensas a errores humanos.
- **B. Usar solo reglas de AWS Config**: AWS Config es útil para monitorear el cumplimiento de configuración, pero no proporciona detección de amenazas en runtime ni logging integral.
- **C. Usar solo AWS GuardDuty**: GuardDuty se centra en la detección de amenazas, pero no proporciona verificaciones de cumplimiento de configuración ni logging de auditoría integral.
</details>
### 6. ¿Cuál es el enfoque más seguro para la gestión de secrets en Amazon EKS?

A. Usar Kubernetes Secrets con la configuración predeterminada
B. Pasar secrets como variables de entorno
C. Integrar con AWS Secrets Manager o AWS Parameter Store
D. Codificar secrets directamente en imágenes de contenedor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Integrar con AWS Secrets Manager o AWS Parameter Store**

**Explicación:**
El enfoque más seguro para la gestión de secrets en Amazon EKS es integrarse con servicios dedicados de gestión de secrets como AWS Secrets Manager o AWS Parameter Store. Estos servicios proporcionan características de seguridad avanzadas como cifrado, control de acceso, rotación automática y auditoría.

**Beneficios clave de la integración con servicios de gestión de secrets de AWS:**

1. **Cifrado fuerte**:
   - Cifrado en reposo usando AWS KMS
   - Cifrado en tránsito
   - Gestión detallada de claves de cifrado

2. **Control de acceso detallado**:
   - Control de acceso mediante políticas de IAM
   - Aplicar el principio de privilegio mínimo
   - Soporte para credenciales temporales

3. **Rotación automática de secrets**:
   - Automatizar la rotación regular de secrets
   - Rotar sin interrupción de la aplicación
   - Gestionar calendarios y políticas de rotación

4. **Auditoría y logging integrales**:
   - Auditar el acceso a secrets
   - Integración con CloudTrail
   - Cumplir requisitos de cumplimiento

**Métodos de implementación:**

1. **Integración con AWS Secrets Manager**:

   a. **Instalar ASCP (AWS Secrets and Configuration Provider)**:
   ```bash
   helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
   helm install -n kube-system csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver

   kubectl apply -f https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml
   ```

   b. **Crear SecretProviderClass**:
   ```yaml
   apiVersion: secrets-store.csi.x-k8s.io/v1
   kind: SecretProviderClass
   metadata:
     name: aws-secrets
   spec:
     provider: aws
     parameters:
       objects: |
         - objectName: "prod/myapp/db-creds"
           objectType: "secretsmanager"
           objectAlias: "db-creds.json"
     secretObjects:
     - secretName: db-credentials
       type: Opaque
       data:
       - objectName: db-creds.json
         key: username
         property: username
       - objectName: db-creds.json
         key: password
         property: password
   ```

   c. **Montar Secrets en Pod**:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: app
   spec:
     containers:
     - name: app
       image: myapp:1.0
       volumeMounts:
       - name: secrets-store
         mountPath: "/mnt/secrets"
         readOnly: true
       env:
       - name: DB_USERNAME
         valueFrom:
           secretKeyRef:
             name: db-credentials
             key: username
       - name: DB_PASSWORD
         valueFrom:
           secretKeyRef:
             name: db-credentials
             key: password
     volumes:
     - name: secrets-store
       csi:
         driver: secrets-store.csi.k8s.io
         readOnly: true
         volumeAttributes:
           secretProviderClass: aws-secrets
   ```

2. **Integración con AWS Parameter Store**:

   a. **Instalar External Secrets Operator**:
   ```bash
   helm repo add external-secrets https://charts.external-secrets.io
   helm install external-secrets external-secrets/external-secrets \
     -n external-secrets \
     --create-namespace
   ```

   b. **Crear SecretStore**:
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: SecretStore
   metadata:
     name: aws-parameter-store
   spec:
     provider:
       aws:
         service: ParameterStore
         region: us-west-2
         auth:
           jwt:
             serviceAccountRef:
               name: external-secrets-sa
   ```

   c. **Crear ExternalSecret**:
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: ExternalSecret
   metadata:
     name: db-credentials
   spec:
     refreshInterval: 1h
     secretStoreRef:
       name: aws-parameter-store
       kind: SecretStore
     target:
       name: db-credentials
     data:
     - secretKey: username
       remoteRef:
         key: /prod/myapp/db/username
     - secretKey: password
       remoteRef:
         key: /prod/myapp/db/password
   ```

**Mejores prácticas de gestión de secrets:**

1. **Aplicar el principio de privilegio mínimo**:
   - Conceder acceso solo a los secrets necesarios
   - Usar IAM roles por service account
   - Revisiones regulares de permisos

2. **Implementar rotación automática de secrets**:
   ```bash
   # Configure AWS Secrets Manager automatic rotation
   aws secretsmanager rotate-secret \
     --secret-id prod/myapp/db-creds \
     --rotation-lambda-arn arn:aws:lambda:us-west-2:123456789012:function:RotateDBCreds \
     --rotation-rules '{"AutomaticallyAfterDays": 30}'
   ```

3. **Mejorar el cifrado de secrets**:
   ```bash
   # Encrypt secrets with customer-managed KMS key
   aws secretsmanager create-secret \
     --name prod/myapp/api-key \
     --secret-string '{"api-key": "abcdef12345"}' \
     --kms-key-id arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab
   ```

4. **Auditar acceso a secrets**:
   ```bash
   # Filter CloudTrail events
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=EventName,AttributeValue=GetSecretValue
   ```

**Ejemplos prácticos de implementación:**

1. **Integración de AWS Secrets Manager e IRSA (IAM Roles for Service Accounts)**:
   ```yaml
   # Create service account
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: app-sa
     namespace: default
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/app-role
   ---
   # Deployment configuration
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: app
   spec:
     selector:
       matchLabels:
         app: myapp
     template:
       metadata:
         labels:
           app: myapp
       spec:
         serviceAccountName: app-sa
         containers:
         - name: app
           image: myapp:1.0
           volumeMounts:
           - name: secrets-store
             mountPath: "/mnt/secrets"
             readOnly: true
         volumes:
         - name: secrets-store
           csi:
             driver: secrets-store.csi.k8s.io
             readOnly: true
             volumeAttributes:
               secretProviderClass: aws-secrets
   ```

2. **Configurar infraestructura de gestión de secrets con Terraform**:
   ```hcl
   # Create AWS Secrets Manager secret
   resource "aws_secretsmanager_secret" "db_credentials" {
     name                    = "prod/myapp/db-creds"
     recovery_window_in_days = 7
     kms_key_id              = aws_kms_key.secrets_key.arn
   }

   resource "aws_secretsmanager_secret_version" "db_credentials" {
     secret_id     = aws_secretsmanager_secret.db_credentials.id
     secret_string = jsonencode({
       username = "dbuser",
       password = random_password.db_password.result
     })
   }

   # IAM role and policy
   resource "aws_iam_role" "app_role" {
     name = "app-role"
     assume_role_policy = jsonencode({
       Version = "2012-10-17",
       Statement = [{
         Effect = "Allow",
         Principal = {
           Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${module.eks.oidc_provider}"
         },
         Action = "sts:AssumeRoleWithWebIdentity",
         Condition = {
           StringEquals = {
             "${module.eks.oidc_provider}:sub" = "system:serviceaccount:default:app-sa"
           }
         }
       }]
     })
   }

   resource "aws_iam_policy" "secrets_access" {
     name = "secrets-access"
     policy = jsonencode({
       Version = "2012-10-17",
       Statement = [{
         Effect = "Allow",
         Action = [
           "secretsmanager:GetSecretValue",
           "secretsmanager:DescribeSecret"
         ],
         Resource = aws_secretsmanager_secret.db_credentials.arn
       }]
     })
   }

   resource "aws_iam_role_policy_attachment" "secrets_access" {
     role       = aws_iam_role.app_role.name
     policy_arn = aws_iam_policy.secrets_access.arn
   }
   ```

Problemas con otras opciones:
- **A. Usar Kubernetes Secrets con la configuración predeterminada**: Los Kubernetes Secrets predeterminados solo están codificados en base64 (no cifrados) y carecen de rotación automática o características de control de acceso detallado.
- **B. Pasar secrets como variables de entorno**: Las variables de entorno pueden exponerse en logs o accederse mediante información de procesos, y carecen de rotación automática o características de auditoría.
- **D. Codificar secrets directamente en imágenes de contenedor**: Codificar secrets directamente en imágenes plantea riesgos de seguridad graves y requiere reconstruir y volver a implementar imágenes cuando los secrets deben rotarse.
</details>
