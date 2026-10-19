# Cuestionario de seguridad

Este cuestionario evalúa tu comprensión de los conceptos de seguridad de Kubernetes, como la autenticación, la autorización, las políticas de red, los contextos de seguridad y la gestión de secretos.

## Preguntas de opción múltiple

1. ¿Qué método no admite Kubernetes para autenticar usuarios?
   - A) Certificados X.509
   - B) Tokens de cuentas de servicio
   - C) Tokens de ID de OpenID Connect
   - D) Base de datos de usuarios integrada
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Base de datos de usuarios integrada**

**Explicación:**
Kubernetes no proporciona una base de datos de usuarios integrada. Admite métodos de autenticación como certificados X.509, tokens de cuentas de servicio, tokens de ID de OIDC y autenticación de tokens mediante webhook. Para aceptar tokens de acceso OAuth arbitrarios, se debe configurar un autenticador adecuado. La gestión de usuarios suele integrarse con sistemas externos, como LDAP o Active Directory.
</details>

2. ¿Cuál de los siguientes no es un componente principal de RBAC (control de acceso basado en roles) en Kubernetes?
   - A) Role
   - B) ClusterRole
   - C) RoleBinding
   - D) SecurityPolicy
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) SecurityPolicy**

**Explicación:**
Los componentes principales de RBAC en Kubernetes son Role, ClusterRole, RoleBinding y ClusterRoleBinding. Role y ClusterRole definen conjuntos de permisos; RoleBinding y ClusterRoleBinding los conceden a usuarios, grupos o cuentas de servicio. SecurityPolicy no forma parte de RBAC. PodSecurityPolicy se eliminó en la versión 1.25. Pod Security Standards son definiciones de políticas que aplica Pod Security Admission; no existe un recurso de API llamado PodSecurityStandard.
</details>

3. ¿Qué no se puede configurar mediante el SecurityContext de un pod en Kubernetes?
   - A) ID de usuario del contenedor (UID)
   - B) ID de grupo del contenedor (GID)
   - C) Política de red del contenedor
   - D) Posibilidad de escalar privilegios del contenedor
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Política de red del contenedor**

**Explicación:**
El SecurityContext define opciones de privilegios y control de acceso para el pod o el contenedor. Incluye el ID de usuario (runAsUser), el ID de grupo (runAsGroup), la posibilidad de escalar privilegios (allowPrivilegeEscalation), el modo privilegiado (privileged) y las capabilities. Las políticas de red se definen mediante recursos NetworkPolicy independientes, no en SecurityContext.
</details>

4. ¿Cuál es la función principal de una cuenta de servicio (ServiceAccount) en Kubernetes?
   - A) Autenticar a usuarios externos al clúster
   - B) Proporcionar identidad a los pods para comunicarse con el servidor de API
   - C) Cifrar la comunicación entre nodos
   - D) Conceder privilegios de administrador del clúster
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporcionar identidad a los pods para comunicarse con el servidor de API**

**Explicación:**
Las cuentas de servicio proporcionan identidad a los procesos que se ejecutan dentro de los pods para comunicarse con el servidor de API de Kubernetes. Cada namespace tiene una cuenta de servicio predeterminada, que usan los pods salvo que se especifique otra. RBAC permite limitar las operaciones que pueden realizar los pods con esas identidades.
</details>

5. ¿Cuál es la función principal de NetworkPolicy en Kubernetes?
   - A) Enrutar tráfico desde fuera del clúster hacia su interior
   - B) Controlar y restringir la comunicación entre pods
   - C) Cifrar la comunicación entre nodos
   - D) Proporcionar descubrimiento de servicios
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Controlar y restringir la comunicación entre pods**

**Explicación:**
NetworkPolicy permite controlar la comunicación entre grupos de pods. Se puede especificar qué pods se comunican entre sí y qué puertos y protocolos pueden usar. Las políticas de red permiten controlar con precisión la comunicación entre servicios y mejorar la seguridad de las arquitecturas de microservicios.
</details>

6. ¿Cuál es el nivel más restrictivo de los tres niveles de políticas de Pod Security Standards?
   - A) Privileged
   - B) Baseline
   - C) Restricted
   - D) Enforced
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Restricted**

**Explicación:**
Pod Security Standards establecen tres niveles de políticas:
  - Privileged: sin restricciones; permite todos los privilegios
  - Baseline: bloquea vías conocidas de escalada de privilegios
  - Restricted: el nivel más estricto, con opciones de seguridad reforzadas

La política Restricted es la más estricta: sigue el principio de privilegio mínimo y aplica prácticas recomendadas de seguridad. Prohíbe, entre otras cosas, los contenedores privilegiados, compartir namespaces del host y montar rutas del host.
</details>

7. ¿Qué opción cifra en reposo los datos de Secret almacenados en etcd?
   - A) Codificación Base64
   - B) Configuración de cifrado de etcd
   - C) Aislamiento por namespace
   - D) Añadir etiquetas
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configuración de cifrado de etcd**

**Explicación:**
De forma predeterminada, los datos de Secret se codifican en Base64, pero eso es codificación, no cifrado. La configuración de cifrado de etcd cifra los datos antes de guardarlos en etcd y los protege frente al acceso no autorizado a esa base de datos. El aislamiento por namespace y las etiquetas pueden ayudar a controlar el acceso, pero no protegen los datos en sí.
</details>

8. ¿Cuál de estas opciones no mejora la seguridad de las imágenes de contenedor en Kubernetes?
   - A) Analizar las imágenes en busca de vulnerabilidades
   - B) Usar registros de confianza
   - C) Firmar y verificar imágenes
   - D) Conceder privilegios de root a los contenedores
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Conceder privilegios de root a los contenedores**

**Explicación:**
Conceder privilegios de root a los contenedores debilita la seguridad. Para proteger las imágenes, se pueden analizar vulnerabilidades, usar registros de confianza, firmar y verificar imágenes, aplicar el principio de privilegio mínimo, eliminar paquetes innecesarios y ejecutar los contenedores sin privilegios de root.
</details>

9. ¿Cuál es la función principal del registro de auditoría en Kubernetes?
   - A) Recopilar los registros de los pods
   - B) Registrar las solicitudes al servidor de API
   - C) Supervisar el estado de los nodos
   - D) Analizar el tráfico de red
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Registrar las solicitudes al servidor de API**

**Explicación:**
El registro de auditoría guarda las solicitudes dirigidas al servidor de API de Kubernetes. Permite rastrear quién hizo qué en el clúster y resulta útil para investigar incidentes de seguridad, cumplir requisitos y solucionar problemas. Los registros pueden incluir la hora, el usuario, el contenido de la solicitud y la respuesta.
</details>

10. ¿Cuál de estas opciones no es una característica de los contenedores privilegiados en Kubernetes?
    - A) Acceder a todos los dispositivos del host
    - B) Recibir todas las capacidades de Linux
    - C) Poder cargar módulos del kernel del host
    - D) Acceder automáticamente a recursos de otros namespaces
    
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Acceder automáticamente a recursos de otros namespaces**

**Explicación:**
Los contenedores privilegiados pueden acceder a casi todas las capacidades del host, pero no obtienen automáticamente acceso a recursos de Kubernetes de otros namespaces. RBAC controla el acceso entre namespaces. `privileged: true` no establece por sí solo `hostNetwork: true`. Este modo elimina barreras importantes de aislamiento del host; si se compromete el host, pueden quedar expuestas credenciales y sortearse el aislamiento previsto. Por eso, RBAC no protege frente a una carga de trabajo privilegiada comprometida.
</details>

## Preguntas de respuesta breve

1. ¿Cuál es la diferencia principal entre 'Role' y 'ClusterRole' en RBAC de Kubernetes?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
Un Role define permisos dentro de un namespace. Un ClusterRole es una definición con alcance de clúster que puede abarcar recursos con alcance de namespace o de clúster. RoleBinding puede conceder, dentro de un namespace, los permisos de un ClusterRole para recursos con alcance de namespace; ClusterRoleBinding concede permisos en todo el clúster. Definir cualquiera de los dos roles por sí solo no concede acceso a nadie.
</details>

2. Explica tres formas de aplicar el principio de privilegio mínimo en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
1. Usa RBAC para conceder solo los permisos imprescindibles
2. Ejecuta los contenedores sin privilegios de root mediante el contexto de seguridad del pod
3. Usa políticas de red para permitir únicamente la comunicación necesaria
4. Limita el uso de contenedores privilegiados
5. Limita las capacidades de los contenedores
6. Aplica el perfil Restricted de Pod Security Standards

(Solo es necesario explicar tres de las opciones anteriores)
</details>

3. ¿Cuál es la diferencia principal entre Secret y ConfigMap desde el punto de vista de la seguridad en Kubernetes?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
Secret almacena información confidencial, como contraseñas, tokens y claves; ConfigMap almacena datos de configuración generales. El campo `data` de Secret aparece codificado en Base64 en las representaciones de la API, pero eso no es cifrado. En Linux, los volúmenes completos de Secret usan almacenamiento respaldado por memoria y pueden recibir actualizaciones después de crear el pod; la aplicación debe volver a leerlos. El cifrado en reposo depende del clúster (EKS cifra los datos de la API de forma predeterminada desde la versión 1.28). Siguen siendo necesarios RBAC y limitar el acceso de los pods.
</details>

4. ¿Para qué sirve la proyección de volúmenes de tokens de cuentas de servicio y qué ventajas ofrece en Kubernetes?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
La proyección de volúmenes de tokens de cuentas de servicio añade medidas de seguridad, como limitar la duración del token y restringir su audiencia. Así, solo los servidores de API previstos aceptan el token y se reduce el riesgo si se filtra. Kubelet rota el token proyectado; la aplicación debe volver a leerlo y el servicio receptor debe comprobar su audiencia y vencimiento. La rotación por sí sola no actualiza un token que la aplicación haya almacenado en caché indefinidamente.
</details>

5. ¿Qué es el aislamiento en sandbox de contenedores en Kubernetes y qué tecnologías permiten implementarlo?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
El aislamiento mediante sandbox aumenta la seguridad al separar los contenedores del sistema host y de otros contenedores. Entre las tecnologías que pueden implementarlo se incluyen:
1. Namespaces y cgroups de Linux: proporcionan el aislamiento básico de contenedores
2. seccomp: restringe las llamadas al sistema
3. AppArmor/SELinux: control de acceso obligatorio
4. gVisor: añade aislamiento mediante un kernel implementado en espacio de usuario
5. Kata Containers: proporciona aislamiento a nivel de hardware mediante máquinas virtuales ligeras
6. Firecracker: proporciona aislamiento mediante microVM

Estas tecnologías limitan el impacto de los contenedores sobre el host y reducen el riesgo de que escapen de su aislamiento.
</details>

## Preguntas prácticas

1. Crea recursos RBAC que cumplan estos requisitos:
   - Un Role que pueda leer pods en el namespace 'monitoring'
   - Un RoleBinding que asocie este Role con la cuenta de servicio 'monitoring-team'

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

Cómo aplicarlos:
```bash
kubectl apply -f monitoring-role.yaml
kubectl apply -f monitoring-rolebinding.yaml
```
</details>

2. Crea una NetworkPolicy que cumpla estos requisitos:
   - Se aplica a todos los pods del namespace 'backend'
   - Permite tráfico entrante en el puerto 8080 solo desde pods del namespace 'frontend'
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
          kubernetes.io/metadata.name: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - {}  # Allow all outgoing traffic
```

Cómo aplicarlo:
```bash
kubectl apply -f backend-network-policy.yaml
```

La etiqueta integrada del namespace `kubernetes.io/metadata.name: frontend` selecciona el namespace `frontend` sin necesidad de una etiqueta personalizada. Otras políticas aditivas y la política de egreso del pod de origen también afectan la conectividad.
</details>

3. Crea un pod que cumpla estos requisitos de contexto de seguridad:
   - El contenedor se ejecuta con UID 1000
   - No se permite escalar privilegios
   - El sistema de archivos raíz es de solo lectura

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
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
    securityContext:
      runAsUser: 1000
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
```

Cómo aplicarlo:
```bash
kubectl apply -f secure-pod.yaml
```
</details>

4. Crea un Secret y móntalo como volumen en un pod con estos requisitos:
   - El Secret se llama 'db-credentials'
   - Contiene 'username=admin' y 'password=s3cr3t'
   - Se monta en la ruta '/etc/db-credentials' del pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

Crear el Secret:
```bash
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password=s3cr3t
```

O bien, como YAML:
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

Montarlo en el pod:
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

Cómo aplicarlos:
```bash
kubectl apply -f db-secret.yaml
kubectl apply -f pod-with-secret.yaml
```
</details>

## Temas avanzados

1. Proporciona tres ejemplos de políticas que se pueden implementar con OPA (Open Policy Agent) Gatekeeper en Kubernetes y explícalos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

OPA Gatekeeper permite aplicar políticas a clústeres de Kubernetes. Antes de crear estas restricciones, instala Gatekeeper y los ConstraintTemplates correspondientes de la biblioteca oficial. Los tipos de restricciones no son API integradas de Kubernetes, y permitir imágenes de ciertos registros no verifica por sí solo sus firmas. Estos son algunos ejemplos:

1. **Restringir los registros de imágenes**: obliga a descargar imágenes únicamente de registros aprobados para impedir el uso de imágenes de fuentes no confiables.
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

2. **Impedir contenedores privilegiados**: prohíbe su uso para reducir los riesgos de seguridad.
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

3. **Exigir límites de recursos**: exige límites de CPU y memoria en todos los contenedores para prevenir ataques de agotamiento de recursos.
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

OPA Gatekeeper también puede exigir etiquetas específicas en los namespaces, restringir nombres de host de Ingress, limitar tipos de volúmenes y evitar montajes de rutas del host, entre otras políticas.
</details>

2. Explica cómo implementar mTLS (TLS mutuo) en Kubernetes y cuáles son sus ventajas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

mTLS (TLS mutuo) permite que el cliente y el servidor se autentiquen entre sí mediante certificados. A continuación se describen formas de implementarlo en Kubernetes y sus ventajas:

**Métodos de implementación:**

1. **Usar una malla de servicios**: herramientas como Istio y Linkerd pueden aplicar mTLS mediante proxies sidecar.
   ```yaml
   # Istio example
   apiVersion: security.istio.io/v1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: istio-system
   spec:
     mtls:
       mode: STRICT
   ```

2. **Combinarlo con políticas de red**: NetworkPolicy limita la conectividad de las capas L3/L4; la malla autentica los certificados. Incorpora las cargas de trabajo, exige mTLS y aplica autorización de la malla para restringir las identidades autenticadas.

3. **Gestionar certificados**: usa herramientas como cert-manager para administrar su ciclo de vida.
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

**Ventajas:**

1. **Autenticación mutua**: el cliente y el servidor se autentican entre sí, lo que ayuda a prevenir ataques de intermediario.
2. **Comunicación cifrada**: cifra el tráfico entre servicios y evita que terceros lo intercepten.
3. **Control de acceso granular**: la identidad basada en certificados permite aplicar controles precisos.
4. **Arquitectura de confianza cero**: exige autenticación para todas las comunicaciones, sin importar su ubicación en la red.
5. **Apoyo al cumplimiento**: ayuda a satisfacer requisitos como PCI DSS e HIPAA.

mTLS es una forma importante de proteger la comunicación entre servicios en arquitecturas de microservicios.
</details>

3. Explica cómo mejorar la seguridad de la cadena de suministro de software en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

Entre las medidas para proteger la cadena de suministro de software en Kubernetes se incluyen:

1. **Firma y verificación de imágenes**:
   - Firma imágenes de contenedor con herramientas como Cosign o Notary.
   - Aplica políticas para desplegar solo imágenes firmadas (por ejemplo, con OPA Gatekeeper o Kyverno).
   ```bash
   cosign sign --key cosign.key "${IMAGE_REF:?Set repository@sha256:digest}"
   ```

2. **Generación y verificación de la lista de materiales de software (SBOM)**:
   - Genera SBOM con herramientas como Syft o Anchore.
   - Registra todos los componentes de software incluidos en las imágenes.
   ```bash
   syft "${IMAGE_REF:?Set repository@sha256:digest}" -o spdx-json > sbom.json
   ```

3. **Análisis de vulnerabilidades**:
   - Analiza las imágenes con herramientas como Trivy o Clair.
   - Integra el análisis en los pipelines de CI/CD.
   ```bash
   trivy image "${IMAGE_REF:?Set repository@sha256:digest}"
   ```

4. **Usar imágenes base mínimas**:
   - Usa imágenes como distroless o scratch para reducir la superficie de ataque.
   ```dockerfile
   FROM gcr.io/distroless/java21-debian13:nonroot
   COPY app.jar /app.jar
   CMD ["app.jar"]
   ```

5. **Aplicar políticas de imágenes**:
   - Aplica políticas según la antigüedad de la imagen, la gravedad de sus vulnerabilidades, el registro de origen y otros criterios.
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sAllowedRepos
   metadata:
     name: trusted-images
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       repos:
         - "docker.io/company/"
         - "gcr.io/verified/"
   ```

6. **Niveles de garantía de la cadena de suministro de software (SLSA)**:
   - Registra la procedencia de las compilaciones.
   - Garantiza compilaciones reproducibles.
   - Verifica la integridad de las compilaciones.

7. **Supervisión y auditoría continuas**:
   - Usa herramientas de seguridad en tiempo de ejecución para detectar comportamientos anómalos.
   - Realiza auditorías de seguridad periódicas.

La combinación de estas medidas ayuda a proteger los entornos de Kubernetes frente a ataques a la cadena de suministro de software.
</details>

4. Explica cómo implementar un modelo de seguridad de confianza cero en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

El modelo de confianza cero se basa en el principio «nunca confíes, verifica siempre». Este es un enfoque para implementarlo en Kubernetes:

1. **Gestión granular de identidades y accesos**:
   - Implementa políticas RBAC sólidas.
   - Concede a las cuentas de servicio solo los permisos necesarios.
   - Integra proveedores de identidad externos, como OIDC o LDAP.
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     namespace: default
     name: minimal-access
   rules:
   - apiGroups: [""]
     resources: ["pods"]
     verbs: ["get"]
     resourceNames: ["app-pod"]
   ```

2. **Segmentación de red**:
   - Deniega todo el tráfico de forma predeterminada.
   - Aplica políticas de red que permitan únicamente las comunicaciones requeridas explícitamente.
   - Implementa microsegmentación.
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

3. **Aplicar TLS mutuo (mTLS)**:
   - Usa una malla de servicios, como Istio o Linkerd, para aplicar mTLS a toda la comunicación entre servicios.
   - Verifica la identidad de los servicios mediante certificados.
   ```yaml
   apiVersion: security.istio.io/v1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: istio-system
   spec:
     mtls:
       mode: STRICT
   ```

4. **Verificación y autenticación continuas**:
   - Autentica y autoriza continuamente todas las solicitudes.
   - Aplica control de acceso según el contexto (hora, ubicación, estado del dispositivo, etc.).
   - Aplica políticas dinámicamente con OPA Gatekeeper o Kyverno.

5. **Cifrado**:
   - Cifra los datos en reposo (cifrado de etcd, PV cifrados, etc.).
   - Cifra los datos en tránsito mediante TLS o mTLS.
   - Integra herramientas de gestión de secretos, como Vault o Sealed Secrets.

6. **Detección y respuesta ante amenazas**:
   - Implementa herramientas de supervisión de seguridad en tiempo de ejecución.
   - Detecta comportamientos anómalos y genera alertas.
   - Implementa mecanismos de respuesta automatizada.

7. **Configurar las cargas de trabajo con privilegio mínimo**:
   - Ejecuta los contenedores sin privilegios de root.
   - Usa sistemas de archivos de solo lectura.
   - Aplica restricciones mediante el contexto de seguridad.
   ```yaml
   spec:
     securityContext:
       runAsUser: 1000
       runAsGroup: 3000
       fsGroup: 2000
       runAsNonRoot: true
       seccompProfile:
         type: RuntimeDefault
     containers:
     - name: app
       image: busybox:1.36
       command: ["sh", "-c", "sleep 3600"]
       securityContext:
         readOnlyRootFilesystem: true
         allowPrivilegeEscalation: false
         capabilities:
           drop: ["ALL"]
   ```

8. **Evaluación continua de la postura de seguridad**:
   - Analiza vulnerabilidades periódicamente.
   - Realiza pruebas de penetración y auditorías de seguridad.
   - Supervisa el cumplimiento.

La confianza cero no es una solución única, sino un enfoque que combina varias capas de seguridad y se basa en la verificación continua y el principio de privilegio mínimo.
</details>

5. Compara y explica herramientas y tecnologías de seguridad en tiempo de ejecución para Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

Entre las principales herramientas y tecnologías de seguridad en tiempo de ejecución para Kubernetes se incluyen:

1. **Falco**:
   - **Funcionamiento**: supervisa las llamadas al sistema para detectar comportamientos anómalos.
   - **Características**: 
     - Opera a nivel del kernel para supervisar la actividad interna de los contenedores.
     - Permite crear reglas para detectar diversas amenazas de seguridad.
     - Admite alertas y respuestas en tiempo real.
   - **Regla de ejemplo**:
     ```yaml
     - rule: Terminal shell in container
       desc: A shell was spawned by a container
       condition: spawned_process and container and proc.name = bash and proc.tty != 0
       output: Shell opened in container (user=%user.name container=%container.name)
       priority: WARNING
     ```

2. **Seccomp (Secure Computing Mode)**:
   - **Funcionamiento**: restringe las llamadas al sistema que pueden realizar los contenedores.
   - **Características**:
     - Usa una función integrada en el kernel de Linux.
     - Solo permite ejecutar las llamadas al sistema autorizadas.
     - Reduce la superficie de ataque.
   - **Ejemplo de configuración**:
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
       containers:
       - name: app
         image: busybox:1.36
         command: ["sh", "-c", "sleep 3600"]
     ```

3. **AppArmor**:
   - **Funcionamiento**: aplica perfiles de control de acceso para cada programa.
   - **Características**:
     - Ofrece controles precisos para archivos, red, capacidades y otros recursos.
     - Requiere un nodo Linux con AppArmor habilitado y el perfil cargado previamente.
     - Permite aplicar perfiles por contenedor.
   - **Ejemplo de configuración**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: apparmor-pod
     spec:
       containers:
       - name: container1
         image: busybox:1.36
         command: ["sh", "-c", "sleep 3600"]
         securityContext:
           appArmorProfile:
             type: Localhost
             localhostProfile: restricted
     ```

4. **SELinux**:
   - **Funcionamiento**: aplica políticas de control de acceso obligatorio (MAC).
   - **Características**:
     - Usa políticas de seguridad granulares basadas en etiquetas.
     - Aplica la política SELinux configurada en el host.
     - Requiere una configuración compleja.
   - **Ejemplo de configuración**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: selinux-pod
     spec:
       securityContext:
         seLinuxOptions:
           level: "s0:c123,c456"
       containers:
       - name: app
         image: busybox:1.36
         command: ["sh", "-c", "sleep 3600"]
     ```

5. **OPA Gatekeeper**:
   - **Funcionamiento**: aplica políticas durante la admisión y audita periódicamente los objetos de API; no supervisa llamadas al sistema.
   - **Características**:
     - Permite definir políticas de forma declarativa.
     - Permite aplicar políticas a muchos tipos de objetos.
     - Admite modos de auditoría y aplicación.

6. **Herramientas comerciales (Aqua, Sysdig, StackRox, etc.)**:
   - **Funcionamiento**: ofrecen plataformas integrales de seguridad de contenedores.
   - **Características**:
     - Integran análisis de vulnerabilidades, protección en tiempo de ejecución y supervisión del cumplimiento.
     - Detectan anomalías mediante aprendizaje automático.
     - Incluyen paneles e informes.

7. **gVisor**:
   - **Funcionamiento**: interpone un kernel en espacio de usuario entre la aplicación y el kernel del host.
   - **Características**:
     - Añade una capa de aislamiento entre el contenedor y el host.
     - Intercepta y emula llamadas al sistema.
     - Introduce una sobrecarga de rendimiento.
   - **Ejemplo de configuración**:
     ```yaml
     apiVersion: node.k8s.io/v1
     kind: RuntimeClass
     metadata:
       name: gvisor
     handler: runsc
     ```

8. **Kata Containers**:
   - **Funcionamiento**: ejecuta contenedores dentro de máquinas virtuales ligeras.
   - **Características**:
     - Proporciona aislamiento a nivel de hardware.
     - Mantiene la compatibilidad con OCI.
     - Tiene más sobrecarga que los contenedores normales.

En los nodos compatibles, el perfil seccomp de tipo Localhost debe existir en el directorio de perfiles seccomp de kubelet; un perfil de solo auditoría registra las llamadas, pero no las bloquea. AppArmor y SELinux requieren compatibilidad del host y perfiles o etiquetas configurados. Los controladores de RuntimeClass (`runsc`, `kata`) deben estar instalados y configurados en el runtime CRI, y los pods deben indicar `runtimeClassName`; crear un RuntimeClass no instala el runtime. El Dockerfile de Java presupone que `app.jar`, ya compilado y compatible, está en el contexto de compilación.

**Criterios de comparación y selección**:
  - **Nivel de seguridad**: Kata Containers y gVisor añaden fronteras de aislamiento; elige según el modelo de amenazas.
  - **Impacto en el rendimiento**: mide el arranque, la E/S, la memoria y la sobrecarga de llamadas al sistema con la carga de trabajo real.
  - **Complejidad de implementación**: seccomp y AppArmor son relativamente sencillos; SELinux es complejo.
  - **Supervisión frente a prevención**: Falco se centra principalmente en la supervisión; otras herramientas ofrecen protección preventiva.
  - **Facilidad de integración**: OPA Gatekeeper se integra estrechamente con Kubernetes.

Elige la combinación de herramientas que mejor se ajuste a los requisitos de seguridad, los objetivos de rendimiento y la complejidad operativa que tu organización pueda asumir.
</details>
