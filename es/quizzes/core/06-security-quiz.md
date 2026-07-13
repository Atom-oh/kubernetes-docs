# Cuestionario de seguridad

Este cuestionario evalúa tu comprensión de los conceptos de seguridad de Kubernetes, incluidos autenticación, autorización, network policies, security contexts y gestión de Secret.

## Preguntas de opción múltiple

1. ¿Qué método de autenticación NO es compatible con Kubernetes para la autenticación de usuarios?
   - A) Certificados X.509
   - B) Tokens de service account
   - C) Tokens OAuth
   - D) Base de datos de usuarios integrada
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Base de datos de usuarios integrada**

**Explicación:**
Kubernetes no proporciona una base de datos de usuarios integrada. En su lugar, admite métodos de autenticación como certificados X.509, tokens de service account, tokens OAuth, tokens OpenID Connect y autenticación mediante webhook token. La gestión de usuarios normalmente se realiza mediante integración con sistemas externos (por ejemplo, LDAP, Active Directory).
</details>

2. ¿Cuál NO es un componente principal de RBAC (Role-Based Access Control) en Kubernetes?
   - A) Role
   - B) ClusterRole
   - C) RoleBinding
   - D) SecurityPolicy
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) SecurityPolicy**

**Explicación:**
Los componentes principales de Kubernetes RBAC son Role, ClusterRole, RoleBinding y ClusterRoleBinding. Role y ClusterRole definen conjuntos de permisos, mientras que RoleBinding y ClusterRoleBinding asocian estos permisos con usuarios, grupos o service accounts. SecurityPolicy no es un componente de RBAC; recursos similares incluyen PodSecurityPolicy (ahora obsoleto) o PodSecurityStandard.
</details>

3. ¿Qué NO se puede configurar mediante el Security Context de un pod en Kubernetes?
   - A) ID de usuario del container (UID)
   - B) ID de grupo del container (GID)
   - C) Network policy del container
   - D) Capacidad de escalada de privilegios del container
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Network policy del container**

**Explicación:**
Security Context define configuraciones de privilegios y control de acceso a nivel de pod o container. Esto incluye ID de usuario (runAsUser), ID de grupo (runAsGroup), capacidad de escalada de privilegios (allowPrivilegeEscalation), containers privilegiados (privileged) y capabilities. Sin embargo, las network policies se definen mediante recursos NetworkPolicy separados, no mediante Security Context.
</details>

4. ¿Cuál es el propósito principal de un ServiceAccount en Kubernetes?
   - A) Autenticación para usuarios fuera del cluster
   - B) Proporcionar identidad a los pods para comunicarse con el API server
   - C) Cifrar la comunicación entre nodes
   - D) Conceder privilegios de administrador del cluster
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporcionar identidad a los pods para comunicarse con el API server**

**Explicación:**
Las service accounts proporcionan identidad a los procesos que se ejecutan dentro de pods para comunicarse con el Kubernetes API server. Cada namespace tiene una service account predeterminada, y los pods usan esta service account predeterminada a menos que se especifique explícitamente otra. Las service accounts se pueden usar con RBAC para limitar qué operaciones pueden realizar los pods.
</details>

5. ¿Cuál es el propósito principal de NetworkPolicy en Kubernetes?
   - A) Enrutar tráfico desde fuera del cluster hacia dentro
   - B) Controlar y restringir la comunicación entre pods
   - C) Cifrar la comunicación entre nodes
   - D) Proporcionar service discovery
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Controlar y restringir la comunicación entre pods**

**Explicación:**
NetworkPolicy proporciona una forma de controlar la comunicación entre grupos de pods. Mediante esto, puedes especificar qué pods pueden comunicarse con qué otros pods, y qué ports y protocols se pueden usar. Las network policies son importantes para el control detallado de la comunicación service-to-service y para mejorar la seguridad en arquitecturas de microservices.
</details>

6. ¿Cuál es el más restrictivo de los tres niveles de política en Pod Security Standards?
   - A) Privileged
   - B) Baseline
   - C) Restricted
   - D) Enforced
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Restricted**

**Explicación:**
Pod Security Standards define tres niveles de política:
  - Privileged: Sin restricciones, todos los privilegios permitidos
  - Baseline: Evita rutas conocidas de escalada de privilegios
  - Restricted: La política más restrictiva, con configuraciones de seguridad mejoradas aplicadas

La política Restricted es la más restrictiva, sigue el principio de privilegio mínimo y aplica buenas prácticas de seguridad. Esta política prohíbe containers privilegiados, el uso compartido de host namespace, montajes de host path y más.
</details>

7. ¿Cuál es el método más efectivo para proteger los datos de Secret en Kubernetes?
   - A) Codificación Base64
   - B) Configuración de cifrado de etcd
   - C) Aislamiento por namespace
   - D) Agregar labels
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configuración de cifrado de etcd**

**Explicación:**
Los datos de Secret en Kubernetes se almacenan codificados en Base64 de forma predeterminada, pero esto es una codificación simple, no cifrado. Usar la configuración de cifrado de etcd cifra los datos de Secret antes de almacenarlos en etcd, lo que protege la información confidencial frente al acceso no autorizado a la base de datos etcd. El aislamiento por namespace y los labels pueden ayudar con el control de acceso, pero no protegen los datos en sí.
</details>

8. ¿Cuál NO es un método para mejorar la seguridad de las container images en Kubernetes?
   - A) Escaneo de vulnerabilidades de images
   - B) Uso de registries de confianza
   - C) Firma y verificación de images
   - D) Conceder privilegios root a los containers
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Conceder privilegios root a los containers**

**Explicación:**
Conceder privilegios root a los containers debilita la seguridad. Los métodos para mejorar la seguridad de las container images incluyen el escaneo de vulnerabilidades de images, el uso de registries de confianza, la firma y verificación de images, la aplicación del principio de privilegio mínimo, la eliminación de paquetes innecesarios y la ejecución de containers como usuarios no root.
</details>

9. ¿Cuál es el propósito principal de Audit Logging en Kubernetes?
   - A) Recopilar logs de pod
   - B) Registrar solicitudes al API server
   - C) Monitorear el estado de node
   - D) Analizar tráfico de red
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Registrar solicitudes al API server**

**Explicación:**
Audit logging es un mecanismo que registra solicitudes al Kubernetes API server. Esto permite rastrear quién hizo qué en el cluster, lo cual es útil para la investigación de incidentes de seguridad, requisitos de cumplimiento y troubleshooting. Los audit logs pueden incluir información como la hora de la solicitud, el usuario, el contenido de la solicitud y la respuesta.
</details>

10. ¿Cuál NO es una característica de los containers privilegiados en Kubernetes?
    - A) Acceso a todos los dispositivos del host
    - B) Uso del network stack del host
    - C) Capacidad de cargar módulos del kernel del host
    - D) Acceso automático a recursos en otros namespaces
    
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Acceso automático a recursos en otros namespaces**

**Explicación:**
Los containers privilegiados pueden acceder a casi todas las capacidades del host, pero no tienen automáticamente acceso a recursos de Kubernetes en otros namespaces. El acceso entre namespaces está controlado por permisos RBAC. Los containers privilegiados pueden acceder a dispositivos del host, network stack, módulos del kernel, etc., lo que representa riesgos de seguridad significativos, por lo que deben usarse solo cuando sea absolutamente necesario.
</details>

## Preguntas de respuesta corta

1. ¿Cuál es la diferencia principal entre 'Role' y 'ClusterRole' en Kubernetes RBAC?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
Role define y aplica permisos solo dentro de un namespace específico, mientras que ClusterRole se aplica a nivel de cluster y define permisos en todos los namespaces. ClusterRole también se usa para definir permisos para recursos que no pertenecen a un namespace (nodes, PVs, etc.).
</details>

2. Explica tres métodos para aplicar el 'principio de privilegio mínimo' en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
1. Usar RBAC para conceder solo los permisos mínimos necesarios
2. Ejecutar containers como usuarios no root en el pod security context
3. Usar network policies para permitir solo la comunicación necesaria
4. Restringir el uso de containers privilegiados
5. Restringir las capabilities del container
6. Aplicar el perfil Restricted de Pod Security Standards

(Solo es necesario explicar tres de los anteriores)
</details>

3. ¿Cuál es la diferencia principal entre Secret y ConfigMap desde una perspectiva de seguridad en Kubernetes?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
Secret es para almacenar información confidencial (contraseñas, tokens, claves, etc.), mientras que ConfigMap es para almacenar datos de configuración generales. Los Secrets se almacenan codificados en Base64 (no cifrados de forma predeterminada), se pueden configurar para montarse solo en memoria y solo se referencian cuando se crean pods. Sin embargo, sin configuración adicional, ambos se almacenan en texto plano en etcd, por lo que se requieren configuraciones de cifrado de etcd para una seguridad completa.
</details>

4. ¿Cuál es el propósito y beneficio de 'service account token volume projection' en Kubernetes?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
Service account token volume projection proporciona características de seguridad adicionales para los service account tokens montados en pods, como límites de tiempo y restricciones de audience. Esto permite limitar la vida útil del token y garantizar que solo API servers específicos acepten el token, reduciendo el riesgo en caso de filtración del token. Además, los tokens se renuevan automáticamente, lo que evita problemas de autenticación en aplicaciones de larga duración.
</details>

5. ¿Qué es 'container sandboxing' en Kubernetes y qué tecnologías se pueden usar para implementarlo?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
Container sandboxing es una técnica que mejora la seguridad al aislar los containers del sistema host y de otros containers. Las tecnologías para implementarlo incluyen:
1. Linux namespaces y cgroups: Proporcionan aislamiento básico de containers
2. seccomp: Restringe llamadas al sistema
3. AppArmor/SELinux: Control de acceso obligatorio
4. gVisor: Aislamiento adicional mediante implementación de kernel en user-space
5. Kata Containers: Aislamiento a nivel de hardware usando VMs ligeras
6. Firecracker: Aislamiento basado en MicroVM

Estas tecnologías limitan el impacto que los containers pueden tener en el sistema host y reducen el riesgo de ataques de escape de container.
</details>

## Preguntas prácticas

1. Crea recursos RBAC que cumplan los siguientes requisitos:
   - Un Role que pueda leer pods en el namespace 'monitoring'
   - Un RoleBinding que vincule este Role a la service account 'monitoring-team'

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
# monitoring-role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: monitoring
  name: pod-reader
rules:
  - apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
---
# monitoring-rolebinding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: monitoring
subjects:
- kind: ServiceAccount
  name: monitoring-team
  namespace: monitoring
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

Cómo aplicar:
```bash
kubectl apply -f monitoring-role.yaml
kubectl apply -f monitoring-rolebinding.yaml
```
</details>

2. Crea una NetworkPolicy que cumpla los siguientes requisitos:
   - Se aplica a todos los pods en el namespace 'backend'
   - Permite tráfico entrante solo desde pods en el namespace 'frontend' en el port 8080
   - Permite todo el tráfico saliente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
# backend-network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-allow-frontend
  namespace: backend
spec:
  podSelector: {}  # Apply to all pods
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - {}  # Allow all outgoing traffic
```

Cómo aplicar:
```bash
kubectl apply -f backend-network-policy.yaml
```

Nota: Para que esta NetworkPolicy funcione, el namespace 'frontend' debe tener el label 'name: frontend'. Si no lo tiene, agrégalo con:
```bash
kubectl label namespace frontend name=frontend
```
</details>

3. Crea un pod con los siguientes requisitos de security context:
   - El container se ejecuta como UID 1000
   - No se permite la escalada de privilegios
   - Root filesystem de solo lectura

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
# secure-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  containers:
  - name: secure-container
    image: nginx
    securityContext:
      runAsUser: 1000
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
```

Cómo aplicar:
```bash
kubectl apply -f secure-pod.yaml
```
</details>

4. Crea un Secret y móntalo como volumen en un pod con los siguientes requisitos:
   - Secret llamado 'db-credentials'
   - Contiene 'username=admin' y 'password=s3cr3t'
   - Montado en la ruta '/etc/db-credentials' en el pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

Crear Secret:
```bash
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password=s3cr3t
```

O como YAML:
```yaml
# db-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWRtaW4=  # base64 encoding of 'admin'
  password: czNjcjN0  # base64 encoding of 's3cr3t'
```

Montar en el pod:
```yaml
# pod-with-secret.yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-secret
spec:
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - name: secret-volume
      mountPath: "/etc/db-credentials"
      readOnly: true
  volumes:
  - name: secret-volume
    secret:
      secretName: db-credentials
```

Cómo aplicar:
```bash
kubectl apply -f db-secret.yaml
kubectl apply -f pod-with-secret.yaml
```
</details>

## Temas avanzados

1. Proporciona tres ejemplos de políticas que se pueden implementar usando OPA (Open Policy Agent) Gatekeeper en Kubernetes y explícalas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

OPA Gatekeeper es una herramienta potente para aplicar políticas a clusters de Kubernetes. Estos son ejemplos de políticas que se pueden aplicar:

1. **Restricción de Image Registry**: Obliga a que las images se descarguen solo desde registries aprobados, evitando el uso de images de fuentes no confiables.
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sAllowedRepos
   metadata:
     name: allowed-repos
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       repos:
         - "docker.io/company/"
         - "gcr.io/company/"
   ```

2. **Prevenir containers privilegiados**: Prohíbe el uso de containers privilegiados para reducir riesgos de seguridad.
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sPSPPrivilegedContainer
   metadata:
     name: prevent-privileged-containers
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
   ```

3. **Aplicar Resource Limits**: Obliga a que todos los containers tengan limits de CPU y memoria configurados para prevenir ataques de agotamiento de recursos.
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sRequiredResources
   metadata:
     name: container-must-have-limits
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       limits:
         - cpu
         - memory
   ```

OPA Gatekeeper también puede aplicar varias otras políticas, como exigir labels específicos en namespaces, restringir ingress hostnames, limitar tipos de volume y prevenir montajes de host path.
</details>

2. Explica cómo implementar mTLS (mutual TLS) en Kubernetes y sus beneficios.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

mTLS (mutual TLS) es un método en el que tanto el client como el server se autentican mutuamente mediante certificados. Así se implementa mTLS en Kubernetes y estos son sus beneficios:

**Métodos de implementación:**

1. **Uso de Service Mesh**: Service meshes como Istio y Linkerd implementan automáticamente mTLS mediante sidecar proxies.
   ```yaml
   # Istio example
   apiVersion: security.istio.io/v1beta1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: istio-system
   spec:
     mtls:
       mode: STRICT
   ```

2. **Uso con Network Policies**: Combina mTLS con network policies para permitir solo tráfico autenticado.

3. **Gestión de certificados**: Usa herramientas como cert-manager para gestionar el ciclo de vida de los certificados.
   ```yaml
   apiVersion: cert-manager.io/v1
   kind: Certificate
   metadata:
     name: service-cert
     namespace: default
   spec:
     secretName: service-tls
     issuerRef:
       name: ca-issuer
       kind: ClusterIssuer
     commonName: service.default.svc.cluster.local
     dnsNames:
     - service.default.svc.cluster.local
   ```

**Beneficios:**

1. **Autenticación mutua**: El client y el server se autentican mutuamente, evitando ataques man-in-the-middle
2. **Comunicación cifrada**: Todo el tráfico service-to-service está cifrado, evitando eavesdropping
3. **Control de acceso detallado**: La identidad basada en certificados permite control de acceso detallado
4. **Arquitectura Zero Trust**: Requiere autenticación para toda comunicación, independientemente de la ubicación en la red
5. **Soporte de cumplimiento**: Ayuda a cumplir requisitos de cumplimiento como PCI DSS, HIPAA

mTLS es un método importante para mejorar la seguridad de la comunicación service-to-service en arquitecturas de microservices.
</details>

3. Explica métodos para mejorar la 'supply chain security' en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

Los métodos para mejorar la supply chain security en Kubernetes incluyen:

1. **Firma y verificación de images**:
   - Firmar container images usando herramientas como Cosign, Notary
   - Aplicar políticas para garantizar que solo se desplieguen images firmadas (por ejemplo, OPA Gatekeeper, Kyverno)
   ```bash
   cosign sign --key cosign.key docker.io/company/app:latest
   ```

2. **Generación y verificación de Software Bill of Materials (SBOM)**:
   - Generar SBOMs usando herramientas como Syft, Anchore
   - Rastrear todos los componentes de software incluidos en las images
   ```bash
   syft docker.io/company/app:latest -o spdx-json > sbom.json
   ```

3. **Escaneo de vulnerabilidades**:
   - Escanear images en busca de vulnerabilidades usando herramientas como Trivy, Clair
   - Integrar el escaneo en CI/CD pipelines
   ```bash
   trivy image docker.io/company/app:latest
   ```

4. **Usar Base Images mínimas**:
   - Usar images mínimas como distroless, scratch para reducir la superficie de ataque
   ```dockerfile
   FROM gcr.io/distroless/java:11
   COPY --from=build /app/target/app.jar /app.jar
   CMD ["app.jar"]
   ```

5. **Aplicar Image Policies**:
   - Aplicar políticas basadas en la antigüedad de la image, la gravedad de vulnerabilidades, el origen del registry, etc.
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sTrustedImages
   metadata:
     name: trusted-images
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       allowedRegistries:
         - "docker.io/company/"
         - "gcr.io/verified/"
   ```

6. **Supply Chain Levels for Software Artifacts (SLSA)**:
   - Rastrear la procedencia de la compilación
   - Garantizar builds reproducibles
   - Verificar la integridad del build

7. **Monitoreo y auditoría continuos**:
   - Usar herramientas de runtime security para detectar comportamiento anómalo
   - Realizar auditorías de seguridad periódicas

Combinar estos métodos ayuda a proteger entornos de Kubernetes contra ataques a la software supply chain.
</details>

4. Explica el enfoque para implementar un 'zero trust security model' en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

El zero trust security model se basa en el principio de "nunca confiar, siempre verificar". Este es el enfoque para implementar zero trust en Kubernetes:

1. **Gestión detallada de identidad y acceso**:
   - Implementar políticas RBAC sólidas
   - Conceder los permisos mínimos necesarios a service accounts
   - Integrar con proveedores de identidad externos (OIDC, LDAP, etc.)
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     namespace: default
     name: minimal-access
   rules:
   - apiGroups: [""]
     resources: ["pods"]
     verbs: ["get", "list"]
     resourceNames: ["app-pod"]
   ```

2. **Segmentación de red**:
   - Denegar todo el tráfico de forma predeterminada
   - Aplicar network policies que permitan solo la comunicación requerida explícitamente
   - Implementar microsegmentación
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
   ```

3. **Aplicar Mutual TLS (mTLS)**:
   - Usar service mesh (Istio, Linkerd, etc.) para aplicar mTLS a toda la comunicación service-to-service
   - Verificación de identidad de services basada en certificados
   ```yaml
   apiVersion: security.istio.io/v1beta1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: istio-system
   spec:
     mtls:
       mode: STRICT
   ```

4. **Verificación y autenticación continuas**:
   - Autenticación y autorización continuas para todas las solicitudes
   - Control de acceso basado en contexto (hora, ubicación, estado del dispositivo, etc.)
   - Aplicación dinámica de políticas usando OPA Gatekeeper o Kyverno

5. **Cifrado**:
   - Cifrado de datos en reposo (cifrado de etcd, PVs cifrados, etc.)
   - Cifrado de datos en tránsito (TLS, mTLS)
   - Integración con herramientas de gestión de Secret (Vault, Sealed Secrets, etc.)

6. **Detección y respuesta ante amenazas**:
   - Desplegar herramientas de monitoreo de runtime security
   - Detectar comportamiento anómalo y alertar
   - Implementar mecanismos de respuesta automatizados

7. **Configuración de workloads con privilegio mínimo**:
   - Ejecutar containers como usuarios no root
   - Usar filesystems de solo lectura
   - Aplicar restricciones de security context
   ```yaml
   securityContext:
     runAsUser: 1000
     runAsGroup: 3000
     fsGroup: 2000
     readOnlyRootFilesystem: true
     allowPrivilegeEscalation: false
   ```

8. **Evaluación continua de la postura de seguridad**:
   - Escaneo regular de vulnerabilidades
   - Pruebas de penetración y auditorías de seguridad
   - Monitoreo de cumplimiento

El zero trust model no es una solución única, sino un enfoque que combina múltiples capas de seguridad, basado en la verificación continua y el principio de privilegio mínimo.
</details>

5. Compara y explica herramientas y tecnologías para 'runtime security' en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

Las principales herramientas y tecnologías para runtime security en Kubernetes incluyen:

1. **Falco**:
   - **Cómo funciona**: Monitorea llamadas al sistema para detectar comportamiento anómalo
   - **Características**: 
     - Opera a nivel de kernel para monitorear la actividad interna del container
     - Reglas personalizadas para detectar diversas amenazas de seguridad
     - Soporte de alertas y respuesta en tiempo real
   - **Regla de ejemplo**:
     ```yaml
     - rule: Terminal shell in container
       desc: A shell was spawned by a container
       condition: container and proc.name = bash
       output: Shell opened in container (user=%user.name container=%container.name)
       priority: WARNING
     ```

2. **Seccomp (Secure Computing Mode)**:
   - **Cómo funciona**: Restringe las llamadas al sistema que los containers pueden usar
   - **Características**:
     - Usa una característica integrada del kernel de Linux
     - Solo se pueden ejecutar llamadas al sistema permitidas
     - Reduce la superficie de ataque
   - **Ejemplo de implementación**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: seccomp-pod
     spec:
       securityContext:
         seccompProfile:
           type: Localhost
           localhostProfile: profiles/audit.json
     ```

3. **AppArmor**:
   - **Cómo funciona**: Aplica perfiles de control de acceso por programa
   - **Características**:
     - Control de acceso detallado para archivos, red, capabilities, etc.
     - Incluido de forma predeterminada en distribuciones Linux
     - Posible aplicación de perfiles por container
   - **Ejemplo de implementación**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: apparmor-pod
       annotations:
         container.apparmor.security.beta.kubernetes.io/container1: localhost/restricted
     ```

4. **SELinux**:
   - **Cómo funciona**: Aplica políticas Mandatory Access Control (MAC)
   - **Características**:
     - Políticas de seguridad detalladas basadas en labels
     - Soporte de estándar de seguridad de nivel militar
     - Requiere configuración compleja
   - **Ejemplo de implementación**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: selinux-pod
     spec:
       securityContext:
         seLinuxOptions:
           level: "s0:c123,c456"
     ```

5. **OPA Gatekeeper**:
   - **Cómo funciona**: Gobernanza en runtime basada en políticas
   - **Características**:
     - Definición declarativa de políticas
     - Amplio alcance de aplicación de políticas
     - Soporte de modo audit y enforcement

6. **Herramientas comerciales (Aqua, Sysdig, StackRox, etc.)**:
   - **Cómo funciona**: Proporcionan plataformas integrales de seguridad de containers
   - **Características**:
     - Escaneo de vulnerabilidades, protección en runtime y monitoreo de cumplimiento integrados
     - Detección de anomalías basada en machine learning
     - Funciones de dashboard y reportes

7. **gVisor**:
   - **Cómo funciona**: Proporciona un kernel en user-space entre la aplicación y el kernel del host
   - **Características**:
     - Capa de aislamiento adicional entre container y host
     - Intercepción y emulación de llamadas al sistema
     - Existe overhead de rendimiento
   - **Ejemplo de implementación**:
     ```yaml
     apiVersion: node.k8s.io/v1
     kind: RuntimeClass
     metadata:
       name: gvisor
     handler: runsc
     ```

8. **Kata Containers**:
   - **Cómo funciona**: Ejecuta containers usando VMs ligeras
   - **Características**:
     - Aislamiento a nivel de hardware
     - Se mantiene la compatibilidad OCI
     - Mayor overhead que los containers normales

**Comparación y criterios de selección**:
  - **Nivel de seguridad**: Kata Containers y gVisor proporcionan el aislamiento más fuerte
  - **Impacto en el rendimiento**: Seccomp tiene overhead mínimo; Kata Containers tiene el más alto
  - **Complejidad de implementación**: Seccomp y AppArmor son relativamente fáciles; SELinux es complejo
  - **Monitoreo vs prevención**: Falco es principalmente monitoreo; otros proporcionan protección preventiva
  - **Facilidad de integración**: OPA Gatekeeper se integra estrechamente con Kubernetes

Elige la combinación adecuada de herramientas según los requisitos de seguridad de tu organización, los objetivos de rendimiento y la tolerancia a la complejidad operativa.
</details>
