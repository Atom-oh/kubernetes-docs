# Cuestionario sobre políticas

Este cuestionario evalúa tu comprensión de los conceptos de políticas de Kubernetes, incluidos ResourceQuota, LimitRange, Pod Security Policies y NetworkPolicy.

## Preguntas de opción múltiple

1. ¿Cuál es el propósito principal de ResourceQuota en Kubernetes?
   - A) Limitar el uso de CPU y memoria de los Pods
   - B) Limitar la creación de recursos dentro de un namespace
   - C) Monitorear el uso de recursos en todo el cluster
   - D) Gestionar la asignación de recursos de los nodes
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Limitar la creación de recursos dentro de un namespace**

**Explicación:**
ResourceQuota limita la cantidad total de recursos que se pueden crear dentro de un namespace. Esto incluye no solo recursos de cómputo como CPU y memoria, sino también la cantidad de objetos como pods, services y configmaps. Usar ResourceQuota evita que un equipo monopolice todos los recursos del cluster.
</details>

2. ¿Cuál es la función principal de LimitRange?
   - A) Limitar el uso total de recursos del namespace
   - B) Establecer resource requests y limits predeterminados para containers individuales
   - C) Distribuir recursos entre los nodes del cluster
   - D) Restringir la comunicación de red entre pods
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Establecer resource requests y limits predeterminados para containers individuales**

**Explicación:**
LimitRange define restricciones de recursos para pods o containers dentro de un namespace. Esto permite establecer resource requests y limits predeterminados, o imponer un uso mínimo/máximo de recursos. LimitRange se aplica a recursos individuales, mientras que ResourceQuota se aplica a todo el namespace.
</details>

3. Después de que PodSecurityPolicy (PSP) se eliminó en Kubernetes v1.25, ¿qué mecanismo lo reemplazó?
   - A) PodSecurityStandards
   - B) PodSecurityContext
   - C) PodSecurityAdmission
   - D) SecurityContextConstraints
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) PodSecurityAdmission**

**Explicación:**
PodSecurityPolicy (PSP) se eliminó en Kubernetes v1.25, y PodSecurityAdmission lo reemplazó. Este es un admission controller integrado basado en Pod Security Standards, que proporciona tres niveles de política: Privileged, Baseline y Restricted. PodSecurityContext se usa para configurar opciones de seguridad a nivel de pod, y SecurityContextConstraints es un mecanismo similar usado en OpenShift.
</details>

4. ¿Qué NO se puede hacer usando NetworkPolicy?
   - A) Restringir el tráfico hacia pods solo desde un namespace específico
   - B) Restringir el tráfico solo a un rango CIDR de IP específico
   - C) Restringir el tráfico solo a un puerto específico
   - D) Inspeccionar el contenido de payload de protocolos específicos
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Inspeccionar el contenido de payload de protocolos específicos**

**Explicación:**
NetworkPolicy proporciona políticas de firewall de nivel L3/L4 que controlan la comunicación entre pods. Esto permite restringir el tráfico según namespaces específicos, labels, rangos CIDR de IP, puertos, etc. Sin embargo, NetworkPolicy no puede realizar inspección de nivel L7 (por ejemplo, headers HTTP, contenido de payload). Para esa funcionalidad, necesitas usar un service mesh (por ejemplo, Istio) o un API gateway.
</details>

5. ¿Cuál es el propósito principal de RBAC (Role-Based Access Control) en Kubernetes?
   - A) Controlar la comunicación de red entre pods
   - B) Gestionar permisos para usuarios y service accounts
   - C) Limitar el uso de recursos
   - D) Establecer políticas de scheduling de pods
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Gestionar permisos para usuarios y service accounts**

**Explicación:**
RBAC (Role-Based Access Control) es un mecanismo para controlar el acceso a la Kubernetes API. Mediante esto, puedes definir qué operaciones pueden realizar los usuarios, grupos o service accounts dentro del cluster. RBAC gestiona permisos usando recursos como Role, ClusterRole, RoleBinding y ClusterRoleBinding.
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
- Baseline: Evita rutas conocidas de escalación de privilegios
- Restricted: La política más restrictiva con configuraciones de seguridad mejoradas aplicadas

La política Restricted es la más restrictiva, sigue el principio de privilegio mínimo y aplica las mejores prácticas de seguridad. Esta política prohíbe containers privilegiados, compartir host namespaces, mounts de host path y más.
</details>

7. ¿Cuál es el rol de AdmissionController en Kubernetes?
   - A) Autenticación de usuarios
   - B) Monitorear el uso de recursos
   - C) Validar y modificar solicitudes de API
   - D) Scheduling de pods
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Validar y modificar solicitudes de API**

**Explicación:**
AdmissionController es un plugin que intercepta y valida o modifica solicitudes al Kubernetes API server después de que pasan autenticación y autorización, pero antes de que los objetos se almacenen en persistent storage. Esto permite a los administradores del cluster aplicar políticas para la creación y modificación de recursos. Por ejemplo, PodSecurityAdmission, ResourceQuota y LimitRanger se implementan como AdmissionControllers.
</details>

8. ¿Cuál es la función principal de OPA (Open Policy Agent) Gatekeeper en Kubernetes?
   - A) Monitoreo y logging del cluster
   - B) Gestión y validación de recursos basada en políticas
   - C) Auto scaling
   - D) Gestión de service mesh
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Gestión y validación de recursos basada en políticas**

**Explicación:**
OPA Gatekeeper es una solución extensible para aplicar políticas a clusters de Kubernetes. Está basada en OPA (Open Policy Agent) y usa CustomResourceDefinitions (CRDs) para definir y aplicar políticas. Gatekeeper opera como un AdmissionWebhook para verificar que los recursos creados o modificados en el cluster cumplan con las políticas definidas. Esto permite aplicar diversas políticas, como políticas de seguridad, límites de recursos y convenciones de nombres.
</details>

9. Al crear un pod sin especificar resource requests y limits en un namespace con ResourceQuota aplicado, ¿qué sucede?
   - A) El pod se crea con resource requests y limits predeterminados
   - B) Se rechaza la creación del pod
   - C) El pod se crea pero no se programa
   - D) El pod se crea y puede usar recursos ilimitados
   
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se rechaza la creación del pod**

**Explicación:**
Cuando ResourceQuota se aplica a un namespace y se establecen cuotas para recursos de cómputo como CPU y memoria, todos los containers de ese namespace deben especificar explícitamente resource requests y limits. De lo contrario, el API server rechaza la solicitud de creación del pod. Esto sirve para rastrear y limitar con precisión el uso de recursos en namespaces con cuotas aplicadas.
</details>

10. ¿Cuál es el propósito principal de PriorityClass en Kubernetes?
    - A) Definir la prioridad de scheduling de pods
    - B) Establecer la prioridad de asignación de recursos del namespace
    - C) Determinar la prioridad de procesamiento de solicitudes de API
    - D) Establecer niveles de importancia de los nodes
    
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Definir la prioridad de scheduling de pods**

**Explicación:**
PriorityClass define la prioridad de scheduling de los pods. Cuando los recursos son escasos, los pods de mayor prioridad se programan antes que los de menor prioridad y pueden hacer preempt (expulsar) a pods de menor prioridad si es necesario.
</details>

## Preguntas de respuesta corta

1. Explica las principales diferencias entre ResourceQuota y LimitRange.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
ResourceQuota limita el uso de recursos para todo el namespace, mientras que LimitRange establece restricciones de recursos para containers o pods individuales dentro de un namespace.

Diferencias clave:
1. **Ámbito**: ResourceQuota se aplica a todo el namespace; LimitRange se aplica a recursos individuales (pods, containers, etc.).
2. **Propósito**: ResourceQuota limita el uso total de recursos del namespace, mientras que LimitRange controla el uso de recursos individuales mediante configuraciones predeterminadas, límites mínimos/máximos, etc.
3. **Aplicación**: Cuando ResourceQuota está configurado, se rechaza la creación de recursos que excedan la cuota. LimitRange aplica valores predeterminados cuando se crean recursos o rechaza si se superan los límites.
4. **Tipos de recursos**: ResourceQuota puede limitar no solo CPU y memoria, sino también conteos de objetos como pods, services y PVCs. LimitRange se centra principalmente en recursos de cómputo como CPU, memoria y storage.
</details>

2. Explica los tres niveles de política (Privileged, Baseline, Restricted) de Pod Security Standards y sus características.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
Pod Security Standards define tres niveles de política para configuraciones de seguridad de pods:

1. **Privileged**:
   - Política más abierta con casi ninguna restricción.
   - Permite todas las operaciones privilegiadas.
   - Puede usar host namespaces, host ports, containers privilegiados, etc.
   - Adecuada para desarrollo y trabajo administrativo, pero plantea riesgos de seguridad significativos en producción.

2. **Baseline**:
   - Política de nivel intermedio que evita rutas conocidas de escalación de privilegios.
   - Proporciona un nivel base de seguridad adecuado para la mayoría de las workloads.
   - Restringe containers privilegiados y el uso de host namespaces.
   - Sin embargo, algunas operaciones privilegiadas (por ejemplo, mounts de host path) todavía están permitidas.

3. **Restricted**:
   - Política más restrictiva con configuraciones de seguridad mejoradas.
   - Sigue el principio de privilegio mínimo e impone las mejores prácticas de seguridad.
   - Prohíbe containers privilegiados, host namespaces, mounts de host path y la escalación de privilegios.
   - Obliga a los containers a ejecutarse como usuarios no root.
   - Adecuada para workloads de producción críticas para la seguridad.
</details>

3. Explica cómo restringir pods en un namespace específico para que se comuniquen solo con pods específicos en otro namespace usando NetworkPolicy.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
Para restringir pods en un namespace específico para que se comuniquen solo con pods específicos en otro namespace usando NetworkPolicy:

1. **Aplicar NetworkPolicy al namespace de origen**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-specific-communication
  namespace: source-namespace  # Source namespace
spec:
  podSelector: {}  # Apply to all pods
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: destination-namespace  # Destination namespace label
      podSelector:
        matchLabels:
          app: specific-app  # Destination pod label
```

2. **Aplicar NetworkPolicy al namespace de destino**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-specific-namespace
  namespace: destination-namespace  # Destination namespace
spec:
  podSelector:
    matchLabels:
      app: specific-app  # Destination pod label
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: source-namespace  # Source namespace label
```

Para que este método funcione, los namespaces deben tener labels apropiadas:
```bash
kubectl label namespace source-namespace name=source-namespace
kubectl label namespace destination-namespace name=destination-namespace
```

NetworkPolicy opera en modo de lista de permitidos de forma predeterminada, por lo que una vez que se aplican estas políticas, solo es posible la comunicación permitida explícitamente y todo lo demás queda bloqueado.
</details>

4. Explica tres ejemplos de políticas que se pueden implementar usando OPA Gatekeeper en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
Ejemplos de políticas que se pueden implementar usando OPA Gatekeeper:

1. **Restricción de Image Registry**:
   - Política que obliga a que las imágenes se descarguen solo desde registries aprobados
   - Ejemplo: Permitir solo registries internos de la empresa o registries públicos específicos de confianza
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
         - "gcr.io/trusted-project/"
   ```

2. **Imponer Resource Requests y Limits**:
   - Política que obliga a todos los containers a tener resource requests y limits configurados
   - Evita el agotamiento de recursos y garantiza una asignación adecuada de recursos
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sRequiredResources
   metadata:
     name: container-must-have-limits-and-requests
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       limits:
         - cpu
         - memory
       requests:
         - cpu
         - memory
   ```

3. **Prevenir Containers Privilegiados**:
   - Política que prohíbe ejecutar containers privilegiados
   - Reduce los riesgos de seguridad y garantiza el aislamiento de containers
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

(Solo es necesario explicar tres de los anteriores)
</details>

5. Explica cómo asegurar la disponibilidad de workloads importantes usando PriorityClass en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
Cómo asegurar la disponibilidad de workloads importantes usando PriorityClass:

1. **Definir PriorityClass**:
   - Crear PriorityClasses con varios niveles de prioridad según la importancia
   ```yaml
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: high-priority
   value: 1000000  # Higher value means higher priority
   globalDefault: false
   description: "This priority class should be used for critical production workloads."
   ```

2. **Asignar PriorityClass a workloads importantes**:
   - Agregar la referencia de PriorityClass a pods importantes
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: critical-service
   spec:
     priorityClassName: high-priority
     containers:
     - name: app
       image: critical-service:latest
   ```

3. **Aprovechar Preemption**:
   - Cuando los recursos son escasos, los pods de mayor prioridad pueden hacer preempt (evict) a pods de menor prioridad y ser programados
   - Esto garantiza que las workloads importantes siempre puedan ejecutarse

4. **Considerar System Priority Classes**:
   - Kubernetes proporciona system priority classes como system-cluster-critical (2000000000) y system-node-critical (2000001000)
   - Las priority classes definidas por el usuario generalmente deberían usar valores menores que estos

5. **Diseñar una jerarquía de prioridades**:
   - Definir varios niveles de prioridad según la importancia de la workload
   - Ejemplo: Servicios de producción (900000), herramientas internas (500000), desarrollo/pruebas (100000)
</details>

## Preguntas prácticas

1. Crea un ResourceQuota que cumpla los siguientes requisitos:
   - Namespace: team-a
   - Máximo 10 pods
   - Máximo 5 services
   - Total CPU requests: 4 cores
   - Total memory requests: 8Gi

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-a-quota
  namespace: team-a
spec:
  hard:
    pods: "10"
    services: "5"
    requests.cpu: "4"
    requests.memory: 8Gi
```

Cómo aplicar:
```bash
# Create namespace
kubectl create namespace team-a

# Apply ResourceQuota
kubectl apply -f team-a-quota.yaml
```

Comprobar el estado de ResourceQuota:
```bash
kubectl describe resourcequota team-a-quota -n team-a
```
</details>

2. Crea un LimitRange que cumpla los siguientes requisitos:
   - Namespace: team-b
   - Container default request: CPU 100m, Memory 256Mi
   - Container default limit: CPU 200m, Memory 512Mi
   - Container maximum limit: CPU 1 core, Memory 2Gi

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: team-b-limits
  namespace: team-b
spec:
  limits:
  - default:
      cpu: 200m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    max:
      cpu: "1"
      memory: 2Gi
    type: Container
```

Cómo aplicar:
```bash
# Create namespace
kubectl create namespace team-b

# Apply LimitRange
kubectl apply -f team-b-limits.yaml
```

Comprobar el estado de LimitRange:
```bash
kubectl describe limitrange team-b-limits -n team-b
```
</details>

3. Crea una NetworkPolicy que cumpla los siguientes requisitos:
   - Namespace: web
   - Los Pods con la label app 'frontend' solo pueden comunicarse con Pods con la label app 'backend'
   - Los backend Pods permiten comunicación solo en el puerto 8080

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-backend-only
  namespace: web
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-allow-frontend-only
  namespace: web
spec:
  podSelector:
    matchLabels:
      app: backend
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

Cómo aplicar:
```bash
# Create namespace
kubectl create namespace web

# Apply NetworkPolicy
kubectl apply -f web-network-policies.yaml
```

Comprobar el estado de NetworkPolicy:
```bash
kubectl describe networkpolicy -n web
```
</details>

4. Crea un PriorityClass y un pod que lo use con los siguientes requisitos:
   - Nombre de PriorityClass: high-priority
   - Valor de prioridad: 100000
   - Descripción: "For critical production workloads"
   - Nombre del Pod: critical-app
   - Image: nginx

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 100000
globalDefault: false
description: "For critical production workloads"
---
apiVersion: v1
kind: Pod
metadata:
  name: critical-app
spec:
  priorityClassName: high-priority
  containers:
  - name: nginx
    image: nginx
```

Cómo aplicar:
```bash
kubectl apply -f high-priority-pod.yaml
```

Comprobar el estado de PriorityClass y del pod:
```bash
kubectl get priorityclass high-priority
kubectl get pod critical-app
```
</details>

5. Aplica las siguientes configuraciones de Pod Security:
   - Namespace: restricted-ns
   - Modo: enforce
   - Nivel: restricted

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

En Kubernetes 1.25 y versiones posteriores, puedes aplicar Pod Security Standards agregando labels al namespace:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: restricted-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

Cómo aplicar:
```bash
kubectl apply -f restricted-namespace.yaml
```

O agregar labels a un namespace existente:
```bash
kubectl create namespace restricted-ns
kubectl label namespace restricted-ns \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```
</details>

## Temas avanzados

1. Explica las diferencias entre OPA Gatekeeper y Kyverno en Kubernetes, y sus respectivos pros y contras.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Comparación entre OPA Gatekeeper y Kyverno:**

1. **Arquitectura y enfoque**:
   - **OPA Gatekeeper**: Basado en Open Policy Agent (OPA), usa el lenguaje de políticas Rego. Define políticas usando dos CRDs: ConstraintTemplate y Constraint.
   - **Kyverno**: Usa su propio motor de políticas y proporciona definiciones de políticas basadas en YAML/JSON. Define políticas usando un único CRD Policy.

2. **Lenguaje de políticas**:
   - **OPA Gatekeeper**: Usa el lenguaje Rego, potente pero con una curva de aprendizaje pronunciada.
   - **Kyverno**: Define políticas usando sintaxis YAML similar a los recursos de Kubernetes, más familiar para los usuarios de Kubernetes.

3. **Características**:
   - **OPA Gatekeeper**: 
     - Lenguaje de políticas potente para expresar políticas complejas
     - Puede integrar fuentes de datos para decisiones basadas en datos externos
     - Soporta bibliotecas de políticas y templates reutilizables
   - **Kyverno**: 
     - Funciones integradas de creación, modificación y validación de recursos
     - Funciones de verificación y modificación de imágenes
     - Puede crear automáticamente otros recursos cuando se crean recursos
     - Funciones de gestión de excepciones de políticas

4. **Pros**:
   - **OPA Gatekeeper**:
     - Más maduro y ampliamente adoptado
     - Más adecuado para expresar políticas complejas
     - Documentación y ejemplos extensos para diversos casos de uso
     - El ecosistema OPA se puede usar fuera de Kubernetes
   - **Kyverno**:
     - Curva de aprendizaje más sencilla con sintaxis YAML familiar
     - No requiere aprender un lenguaje de políticas separado
     - Funciones integradas de creación y modificación de recursos
     - Configuración inicial y configuración más simples

5. **Contras**:
   - **OPA Gatekeeper**:
     - Requiere aprender el lenguaje Rego
     - Configuración inicial y configuración complejas
     - Se necesita configuración adicional para la modificación de recursos
   - **Kyverno**:
     - Relativamente menos maduro
     - Puede tener limitaciones para expresar políticas muy complejas
     - El rendimiento puede ser menor en comparación con OPA

6. **Criterios de selección**:
   - **Elige OPA Gatekeeper cuando**:
     - Se necesita lógica de políticas compleja
     - Ya se usa OPA o se conoce Rego
     - Se necesita una aplicación de políticas consistente en varios sistemas
   - **Elige Kyverno cuando**:
     - Son importantes un inicio rápido y una curva de aprendizaje sencilla
     - El equipo está familiarizado con la sintaxis de recursos de Kubernetes
     - Se necesitan funciones de creación y modificación de recursos
     - Solo se necesitan políticas simples
</details>

2. Explica las principales diferencias entre Pod Security Admission y el PodSecurityPolicy (PSP) anterior en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Comparación entre Pod Security Admission y PodSecurityPolicy (PSP):**

1. **Implementación**:
   - **PodSecurityPolicy**: Implementado como recurso de API (CRD), aplicado mediante admission controller.
   - **Pod Security Admission**: Implementado como admission controller integrado, configurado mediante labels de namespace.

2. **Método de configuración**:
   - **PodSecurityPolicy**: El administrador del cluster debe crear recursos PSP y vincularlos a usuarios/service accounts mediante RBAC.
   - **Pod Security Admission**: Se aplica agregando labels a namespaces que especifican el nivel de aplicación (enforce, audit, warn) y el nivel de política (privileged, baseline, restricted).

3. **Granularidad de la política**:
   - **PodSecurityPolicy**: Permite control muy detallado; se pueden configurar individualmente varias opciones de security context.
   - **Pod Security Admission**: Solo proporciona tres niveles de política predefinidos (privileged, baseline, restricted); no puede ajustar individualmente configuraciones detalladas.

4. **Facilidad de uso**:
   - **PodSecurityPolicy**: Configuración compleja que requiere RBAC bindings; los errores de configuración son comunes.
   - **Pod Security Admission**: Se aplica con un simple etiquetado de namespace, mucho más fácil de usar.

5. **Ámbito**:
   - **PodSecurityPolicy**: Se aplica a todo el cluster o a usuarios/service accounts específicos.
   - **Pod Security Admission**: Se aplica por namespace.

6. **Modos**:
   - **PodSecurityPolicy**: Enfoque binario de aplicar o no aplicar.
   - **Pod Security Admission**: Proporciona tres modos (enforce, audit, warn) para una aplicación gradual.
     - enforce: Rechaza la creación de pod ante una infracción
     - audit: Registra infracciones en el audit log
     - warn: Muestra un mensaje de advertencia ante una infracción

7. **Migración y soporte**:
   - **PodSecurityPolicy**: Eliminado en Kubernetes v1.25.
   - **Pod Security Admission**: Disponible como beta desde Kubernetes v1.23, reemplazó completamente a PSP en v1.25.

8. **Extensibilidad**:
   - **PodSecurityPolicy**: Alta extensibilidad mediante configuraciones personalizadas.
   - **Pod Security Admission**: Extensibilidad limitada; pueden ser necesarias herramientas adicionales como OPA Gatekeeper o Kyverno para un control más preciso.
</details>
