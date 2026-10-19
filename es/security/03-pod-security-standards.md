# Estándares de seguridad de Pod (PSS)

> **Línea base de validación**: biblioteca PSA de Kubernetes `k8s.io/pod-security-admission` v0.36.2; ejemplo de política PSS v1.35
> **Última actualización**: 12 de octubre de 2026

Los Estándares de seguridad de Pod (PSS) son un marco de políticas estandarizado para la seguridad de los Pod en Kubernetes. Este documento cubre los conceptos de PSS, los métodos de configuración y su implementación en entornos EKS.

PSS define políticas; PSA es la implementación de admisión integrada que las aplica. Esta guía da por sentados **Pod Linux ordinarios sin espacios de nombres de usuario**, salvo que se indique lo contrario. La evaluación local de las políticas upstream y las comprobaciones de esquema y comandos son distintas del despliegue: no se probó ningún clúster activo, EKS ni ejecución de contenedores. El ejemplo `v1.35` es una definición de política fijada, no una afirmación sobre la versión más reciente de Kubernetes/EKS compatible. El significado de `latest` cambia cuando se actualiza el servidor de la API.

## Tabla de contenido

1. [Evolución de PSP a PSS](#evolution-from-psp-to-pss)
2. [Controlador Pod Security Admission (PSA)](#pod-security-admission-psa-controller)
3. [Niveles de seguridad](#security-levels)
4. [Modos de aplicación](#enforcement-modes)
5. [Configuración a nivel de espacio de nombres](#namespace-level-configuration)
6. [Migración de PSP a PSS](#migration-from-psp-to-pss)
7. [Valores predeterminados y configuración de EKS](#eks-defaults-and-configuration)
8. [Detalles de los perfiles de seguridad](#security-profile-details)
9. [Configuración de excepciones](#exemptions-configuration)
10. [Buenas prácticas para una adopción gradual](#best-practices-for-gradual-adoption)

---

## Evolución de PSP a PSS {#evolution-from-psp-to-pss}

### Historial de PodSecurityPolicy (PSP)

PodSecurityPolicy (PSP) se introdujo por primera vez en Kubernetes 1.3 como mecanismo de seguridad para los Pod. Sin embargo, se declaró obsoleto en Kubernetes 1.21 y se eliminó por completo en 1.25 debido a los siguientes problemas:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Key Issues with PSP                           │
├─────────────────────────────────────────────────────────────────┤
│ 1. Complex RBAC binding requirements                             │
│ 2. Implicit policy application (unclear which policy applies)    │
│ 3. User vs workload permission confusion                         │
│ 4. No warn/audit rollout modes                                               │
│ 5. Limited audit capabilities                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Introducción de PSS

Pod Security Standards (PSS) y Pod Security Admission (PSA) se introdujeron como funciones alfa en Kubernetes 1.22, pasaron a beta en 1.23 y alcanzaron el estado GA (disponibilidad general) en 1.25.

![Hoja de ruta que distingue la obsolescencia de PSP, su eliminación y la disponibilidad general de PSA en 1.25, así como la evolución posterior de las políticas versionadas.](../.gitbook/assets/en-security-03-pod-security-standards-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-03-pod-security-standards-0.html)

> Interpretación del diagrama: PSA alcanzó el estado GA en 1.25; 1.28 no es un hito de estabilización independiente.

### Comparación entre PSP y PSS

| Característica | PodSecurityPolicy (PSP) | Pod Security Standards (PSS) |
|---------|------------------------|------------------------------|
| **Activación** | Complemento de admisión anterior | Definiciones PSS aplicadas por el complemento PSA integrado |
| **Definición de políticas** | Recursos PSP personalizados | Tres perfiles predefinidos |
| **Asociación de políticas** | Asociación RBAC compleja | Etiquetas de espacio de nombres simples |
| **Alcance** | En todo el clúster o por espacio de nombres | Nivel de espacio de nombres |
| **Vista previa de políticas** | Sin modos warn/audit al estilo de PSA; la simulación de la API es independiente | Modos warn/audit y simulación de la API |
| **Auditoría** | Limitada | Compatibilidad integrada con auditoría |
| **Flexibilidad** | Alta (control detallado) | Media (perfiles estandarizados) |
| **Complejidad** | Alta | Baja |

---

## Controlador Pod Security Admission (PSA) {#pod-security-admission-psa-controller}

### Arquitectura de PSA

PSA se ejecuta **dentro del servidor de la API durante la admisión de validación**, después de la admisión de mutación. También se aplican la autenticación, la autorización, la validación del esquema y otras comprobaciones de admisión. No es un webhook externo, y el diagrama no debe sugerir un orden universal entre PSA y todos los demás validadores.

```text
Request → authentication / authorization → mutating admission
        → validating admission (PSA + other checks) → persistence if accepted
```

### Cómo funciona PSA

![Creación CREATE simplificada de un Pod autenticada y autorizada. PSA es interna al servidor de la API; 201 requiere además que las demás comprobaciones de admisión y el almacenamiento se completen correctamente.](../.gitbook/assets/en-security-03-pod-security-standards-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-03-pod-security-standards-1.html)

> Alcance del diagrama: PSA es interna al servidor de la API. Un Pod creado correctamente con CREATE solo se guarda después de superar todas las comprobaciones aplicables; la aprobación de PSA por sí sola no garantiza una respuesta 201 Created.

### Verificación del estado de PSA

PSA pasó a beta y se habilitó de forma predeterminada en Kubernetes 1.23; después alcanzó el estado GA en 1.25. La ausencia de la marca explícita `--enable-admission-plugins=PodSecurity` no significa que esté deshabilitada. En servidores de la API autogestionados, inspeccione la configuración para comprobar si se deshabilitó explícitamente; EKS no expone esa configuración. Las métricas muestran evaluaciones, no la configuración de una puerta de funciones. El acceso a `/metrics` requiere autorización, y es posible que no aparezca una serie que no se haya utilizado.

```bash
kubectl --context "$PSS_CONTEXT" get namespace "$PSS_NAMESPACE" -o yaml
kubectl --context "$PSS_CONTEXT" get --raw /metrics
```

Use los controles de simulación de Pod positiva/negativa indicados a continuación para probar la ruta real de admisión. Nunca deduzca el cumplimiento únicamente a partir de una simulación de Deployment satisfactoria.

---

## Niveles de seguridad {#security-levels}

PSS define tres niveles de seguridad (perfiles). Cada nivel aplica restricciones de seguridad progresivamente más estrictas.

### 1. Privileged

Este perfil no añade restricciones de PSS. No habilita automáticamente los privilegios de los contenedores ni omite RBAC, la validación de la API u otras políticas de admisión.

```yaml
# Privileged profile: PSS imposes no controls; API/RBAC/other policies still apply
# Use cases: System daemons, CNI plugins, monitoring agents

apiVersion: v1
kind: Pod
metadata:
  name: privileged-pod
  namespace: pss-privileged-lab
spec:
  hostNetwork: true      # Allowed
  hostPID: true          # Allowed
  hostIPC: true          # Allowed
  containers:
  - name: privileged-container
    image: nginx
    securityContext:
      privileged: true   # Allowed
      runAsUser: 0    # Allowed
```

**El nivel Privileged permite:**
- Espacios de nombres de red, PID e IPC del host
- Contenedores privilegiados
- Todas las capacidades
- Montajes HostPath
- Cualquier ID de usuario/grupo

### 2. Baseline

Aplica restricciones mínimas para evitar escaladas de privilegios conocidas. Adecuado para la mayoría de las cargas de trabajo generales.

```yaml
# Baseline level: Prevents known privilege escalations
# Use cases: General applications, web servers, API servers

apiVersion: v1
kind: Pod
metadata:
  name: baseline-pod
spec:
  containers:
  - name: app
    image: nginx
    securityContext:
      # The following are prohibited in Baseline:
      # privileged: true        ❌
      # allowPrivilegeEscalation is not constrained by Baseline

      # The following are allowed in Baseline:
      runAsNonRoot: false      # ✓ (allowed but not recommended)
      readOnlyRootFilesystem: false  # ✓ (allowed)
    ports:
    - containerPort: 80
```

**Restricciones del nivel Baseline:**

| Campo | Restricción |
|-------|------------|
| HostProcess | Se prohíben los contenedores Windows HostProcess |
| Espacios de nombres del host | Se prohíben hostNetwork, hostPID y hostIPC |
| Contenedores privilegiados | Se prohíbe privileged: true |
| Capacidades | Las adiciones explícitas se limitan a la lista de permitidos de Baseline; `NET_RAW` no está incluida |
| Volúmenes HostPath | Se prohíben los volúmenes hostPath |
| Puertos del host | El PSA integrado permite que el valor no se establezca o sea 0; no tiene una lista de puertos permitidos personalizada |
| AppArmor | Sin establecer o RuntimeDefault/Localhost; las anotaciones heredadas usan runtime/default o localhost/* |
| SELinux | Solo se permiten valores de tipo restringidos; se prohíbe establecer usuario/rol |
| Tipo de montaje de /proc | Solo se permite el valor predeterminado |
| Seccomp | Se permite que no esté establecido; si se especifica, debe ser RuntimeDefault o Localhost (no Unconfined) |
| Sysctls | Solo la lista explícita de sysctls permitidos de la versión de PSS; no todos los sysctls seguros para kubelet |

### 3. Restricted

La política más restrictiva, que aplica las prácticas recomendadas de refuerzo de seguridad de Pod. Adecuada para cargas de trabajo con requisitos de seguridad sensibles.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: restricted-pod
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 101
    runAsGroup: 101
    fsGroup: 101
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir: {}
```

**Restricciones adicionales del nivel Restricted:**

| Campo | Restricción |
|-------|------------|
| Tipos de volumen | Solo se permiten configMap, csi, downwardAPI, emptyDir, ephemeral, persistentVolumeClaim, projected y secret |
| Escalada de privilegios | Se requiere allowPrivilegeEscalation: false |
| Ejecución como usuario no root | Se requiere runAsNonRoot: true |
| Ejecución como usuario no root | Se prohíbe el valor explícito runAsUser: 0 (v1.23+); el campo puede omitirse |
| Seccomp | Se requiere RuntimeDefault o Localhost |
| Capacidades | Se deben descartar todas las capacidades; solo se puede añadir NET_BIND_SERVICE |



Los controles se aplican a los contenedores normales, init y efímeros pertinentes. Se puede heredar un valor de nivel Pod para no root/seccomp; una anulación de contenedor en conflicto no cumple la política. La política v1.34+ también prohíbe un valor `host` no vacío en las sondas HTTP/TCP y los hooks del ciclo de vida. En v1.35, `hostUsers: false` flexibiliza las comprobaciones de no root; Baseline también flexibiliza `procMount`, pero Restricted sigue prohibiendo `Unmasked`. Esto requiere compatibilidad real con espacios de nombres de usuario, no solo una etiqueta. Las flexibilizaciones específicas de Windows para la escalada de privilegios, seccomp y las capacidades de Linux son independientes de este ejemplo para Linux.

### Gráfico comparativo de niveles de seguridad

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     Security Level Comparison                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Restriction  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶       │
│               Low                                           High          │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │  Privileged  │    │   Baseline   │    │  Restricted  │               │
│  │              │    │              │    │              │               │
│  │ No           │    │ Prevent      │    │ Security     │               │
│  │ restrictions │    │ known        │    │ best         │               │
│  │              │    │ escalations  │    │ practices    │               │
│  │              │    │              │    │              │               │
│  │ Use cases:   │    │ Use cases:   │    │ Use cases:   │               │
│  │ - CNI        │    │ - General    │    │ - Financial  │               │
│  │ - CSI        │    │   apps       │    │   apps       │               │
│  │ - Monitoring │    │ - Web        │    │ - Healthcare │               │
│  │              │    │   servers    │    │ - Multi-     │               │
│  │              │    │ - API        │    │   tenant     │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Modos de aplicación {#enforcement-modes}

PSA ofrece tres modos de aplicación. Se pueden utilizar de forma independiente o combinada.

### 1. enforce

Rechaza la creación de Pod que infrinja la política y las actualizaciones pertinentes de Pod. Las plantillas de cargas de trabajo se someten a comprobaciones warn/audit; la aplicación se realiza en los Pod resultantes. Cambiar las etiquetas de un espacio de nombres no expulsa los Pod que ya están en ejecución.

```yaml
# enforce mode: Block Pod creation on violation
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
```

**Fragmento ilustrativo de respuesta (no corresponde a una ejecución registrada en un clúster):**
```text
# Attempting to create a policy-violating Pod
$ kubectl apply --dry-run=server -f privileged-pod.yaml -n production
Error from server (Forbidden): error when creating "privileged-pod.yaml":
pods "privileged-pod" is forbidden: violates PodSecurity "restricted:v1.35":
privileged (container "app" must not set securityContext.privileged=true),
allowPrivilegeEscalation != false (container "app" must set
securityContext.allowPrivilegeEscalation=false)
```

### 2. audit

Añade anotaciones de infracción a los eventos de auditoría; este modo no rechaza por sí mismo la solicitud. La configuración de la política de auditoría y de entrega de registros determina si esos eventos se conservan. Otros modos y comprobaciones de admisión todavía pueden rechazarla.

```yaml
# audit mode: Record violations in audit logs
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
```

**Fragmento sintético de evento de auditoría (no es un evento capturado completo):**
```json
{
  "kind": "Event",
  "apiVersion": "audit.k8s.io/v1",
  "level": "Metadata",
  "auditID": "00000000-0000-4000-8000-000000000001",
  "stage": "ResponseComplete",
  "requestURI": "/api/v1/namespaces/staging/pods",
  "verb": "create",
  "user": {
    "username": "developer@example.com"
  },
  "objectRef": {
    "resource": "pods",
    "namespace": "staging",
    "name": "my-pod"
  },
  "annotations": {
    "pod-security.kubernetes.io/audit-violations": "privileged (container \"app\" must not set securityContext.privileged=true)"
  }
}
```

### 3. warn

Devuelve advertencias visibles para el cliente sin rechazar por sí mismo la solicitud; enforce u otras comprobaciones de admisión todavía pueden rechazarla.

```yaml
# warn mode: Display warning messages on violation
apiVersion: v1
kind: Namespace
metadata:
  name: development
  labels:
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

**Fragmento ilustrativo de advertencia (no corresponde a una ejecución registrada):**
```text
$ kubectl apply --dry-run=server -f non-compliant-pod.yaml -n development
Warning: would violate PodSecurity "restricted:v1.35":
allowPrivilegeEscalation != false (container "app" must set
securityContext.allowPrivilegeEscalation=false),
unrestricted capabilities (container "app" must set
securityContext.capabilities.drop=["ALL"])
pod/my-pod created (server dry run)
```

### Estrategia de combinación de modos

La etapa inicial Privileged solo debe usarse en un espacio de nombres que no tenga una política existente más estricta. Nunca reduzca la aplicación de Baseline/Restricted para seguir este diagrama.

En entornos de producción, se recomienda combinar varios modos:

```yaml
# Recommended configuration: Use mode combinations
apiVersion: v1
kind: Namespace
metadata:
  name: app-namespace
  labels:
    # Current enforcement level
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.35
    # Audit next level
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    # Warn next level
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

```
┌─────────────────────────────────────────────────────────────────┐
│                    Mode Combination Strategy                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: Assess Current State                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ enforce: privileged                                      │   │
│  │ audit: baseline                                          │   │
│  │ warn: baseline                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  Phase 2: Gradual Hardening                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ enforce: baseline                                        │   │
│  │ audit: restricted                                        │   │
│  │ warn: restricted                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  Phase 3: Final Goal                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ enforce: restricted                                      │   │
│  │ audit: restricted                                        │   │
│  │ warn: restricted                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuración a nivel de espacio de nombres {#namespace-level-configuration}

### Configuración básica de etiquetas

PSS se configura mediante etiquetas de espacio de nombres:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: secure-namespace
  labels:
    # Format: pod-security.kubernetes.io/<MODE>: <LEVEL>
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

### Especificación de versión

Puede utilizar definiciones PSS de una versión específica de Kubernetes:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: versioned-namespace
  labels:
    # Use PSS definitions from a specific version
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35  # Specific version

    # Using 'latest' applies PSS from current cluster version
    # pod-security.kubernetes.io/enforce-version: latest
```

### Ejemplos de configuración por entorno

```yaml
---
# Development environment: Relaxed policy
apiVersion: v1
kind: Namespace
metadata:
  name: development
  labels:
    environment: development
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/warn: restricted
---
# Staging environment: Intermediate policy
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    environment: staging
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
---
# Production environment: Strict policy
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    environment: production
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### Añadir etiquetas a espacios de nombres existentes

```bash
# Add labels using kubectl
kubectl label namespace my-namespace \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=v1.35 \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted

# Verify labels
kubectl get namespace my-namespace -o yaml | grep pod-security
```

---

## Migración de PSP a PSS {#migration-from-psp-to-pss}

### Descripción general de la migración

La migración de PSP a PSS debe planificarse y realizarse por etapas con cuidado.

![La migración conserva la aplicación existente mientras evalúa las brechas, observa warn/audit, corrige los problemas y valida una política objetivo. La limpieza de la API de PSP solo corresponde a entornos históricos con Kubernetes 1.24 o anterior.](../.gitbook/assets/en-security-03-pod-security-standards-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-03-pod-security-standards-2.html)

> Alcance del diagrama: el análisis y la eliminación de PSP son históricos. Nunca reduzca una política enforce existente más estricta para observar; readOnlyRootFilesystem es una recomendación, no un requisito de Restricted.

### Paso 1: Analizar la PSP actual

**Solo procedimiento histórico:** los comandos/recursos PSP de abajo se aplican a clústeres antiguos que aún ofrecían `policy/v1beta1` (hasta Kubernetes 1.24) o a manifiestos guardados. No aplique esta PSP a un clúster actual. Haga también un inventario de los campos que PSP establecía o modificaba anteriormente; PSA no los completa.

```bash
# List current PSPs
kubectl get psp

# Get PSP details
kubectl get psp <psp-name> -o yaml

# Check Pods with PSP applied
kubectl get pods --all-namespaces -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}: {.metadata.annotations.kubernetes\.io/psp}{"\n"}{end}'
```

### Paso 2: Asignar PSP a perfiles PSS

```yaml
# Example: Existing PSP
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: MustRunAsNonRoot
  seLinux:
    rule: RunAsAny
  fsGroup:
    rule: RunAsAny
  supplementalGroups:
    rule: RunAsAny
```

**Resultado de la asignación:** Restricted es un posible perfil objetivo, no una política equivalente. A esta PSP le falta el control seccomp requerido y permite configuraciones SELinux que PSS podría rechazar. Compare todos los controles y cada Pod resultante; tres campos seleccionados no bastan para establecer equivalencia.

### Tabla de asignación de PSP a PSS

| Requisito de la carga de trabajo | Perfil PSS candidato | Revisión necesaria |
|---|---|---|
| Espacios de nombres del host, contenedor privilegiado o hostPath | Privileged | Aísle la excepción y aplique controles adicionales |
| Sin acceso al host, pero se necesita un proceso root | Baseline | Compruebe todos los controles Baseline, incluidas las capacidades y seccomp |
| No root, sin escalada de privilegios, descartar ALL | Restricted | Compruebe también los volúmenes, seccomp, las anulaciones y los controles específicos de la versión |

### Paso 3: Validar en un entorno de prueba

```bash
# Create test namespace
kubectl create namespace pss-test

# Apply restricted in warn mode
kubectl label namespace pss-test \
  pod-security.kubernetes.io/warn=restricted \
  pod-security.kubernetes.io/warn-version=v1.35

# Test existing workload deployment
kubectl apply -f my-deployment.yaml -n pss-test

# Check warnings and modify workloads
```

### Paso 4: Aplicación gradual

```yaml
# Staged migration namespace configuration
apiVersion: v1
kind: Namespace
metadata:
  name: migrating-namespace
  labels:
    # Phase 1: New namespace without a previous stronger enforce policy
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: baseline
    pod-security.kubernetes.io/warn: baseline

    # Phase 2: Apply baseline, monitor restricted
    # pod-security.kubernetes.io/enforce: baseline
    # pod-security.kubernetes.io/audit: restricted
    # pod-security.kubernetes.io/warn: restricted

    # Phase 3: Final restricted enforcement
    # pod-security.kubernetes.io/enforce: restricted
```

### Paso 5: Modificar las cargas de trabajo

Antes: un Pod `nginx` sencillo sin contexto de seguridad no supera las comprobaciones Restricted. Añadir solo `runAsNonRoot` no basta: el usuario de la imagen, el puerto de escucha y las rutas con permisos de escritura también deben ser compatibles. El Pod corregido utiliza la imagen no privilegiada upstream (UID/GID 101), el puerto 8080 y `/tmp` con permisos de escritura, junto con un sistema de archivos raíz de solo lectura.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: new-pod
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 101
    runAsGroup: 101
    fsGroup: 101
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir: {}
```

### Script de automatización de la migración

Este script se dirige deliberadamente a **un espacio de nombres revisado**, añade solo las etiquetas warn/audit que aún no existan, conserva enforce y utiliza la versión del recurso observada para rechazar una edición simultánea. Al ejecutarse, modifica realmente el espacio de nombres; inspeccione el destino primero. Si ya existen etiquetas, falla para que se comparen manualmente, en vez de aplicar una reducción automática. Las advertencias aparecerán en solicitudes posteriores; no constituyen un análisis retrospectivo de todos los Pod en ejecución.

```python
#!/usr/bin/env python3
# add-pss-observation.py CONTEXT NAMESPACE
import json, subprocess, sys

if len(sys.argv) != 3:
    raise SystemExit("Usage: add-pss-observation.py CONTEXT NAMESPACE")
context, namespace = sys.argv[1:]
if namespace in {"kube-system", "kube-public", "kube-node-lease"}:
    raise SystemExit("Refusing system namespace; review its workload requirements separately")
base = ["kubectl", "--context", context, "--request-timeout=30s"]
obj = json.loads(subprocess.run(
    base + ["get", "namespace", namespace, "-o", "json"],
    check=True, text=True, capture_output=True).stdout)
labels = obj["metadata"].get("labels", {})
new = {
    "pod-security.kubernetes.io/warn": "restricted",
    "pod-security.kubernetes.io/warn-version": "v1.35",
    "pod-security.kubernetes.io/audit": "restricted",
    "pod-security.kubernetes.io/audit-version": "v1.35",
}
if any(key in labels for key in new):
    raise SystemExit("Existing observation policy: review it; do not overwrite automatically")
subprocess.run(base + [
    "label", "namespace", namespace,
    "--resource-version=" + obj["metadata"]["resourceVersion"],
] + [key + "=" + value for key, value in new.items()], check=True)
```

---

## Valores predeterminados y configuración de EKS {#eks-defaults-and-configuration}

### Configuración predeterminada de PSA en EKS

AWS documenta que PSA está habilitada de forma predeterminada desde EKS 1.23, con valores predeterminados del clúster `privileged/latest` para todos los modos y sin excepciones estáticas. Esos valores permisivos no son una política de refuerzo de cargas de trabajo. Las etiquetas de espacio de nombres creadas por herramientas de la plataforma o administradores pueden anular los valores predeterminados; inspeccione el espacio de nombres real en lugar de dar por sentado que no tiene etiquetas.

```bash
kubectl --context "$PSS_CONTEXT" get namespace "$PSS_NAMESPACE" -o yaml
```

### Configuración de PSS en EKS

```yaml
# Apply PSS to EKS namespace
apiVersion: v1
kind: Namespace
metadata:
  name: eks-app-namespace
  labels:
    # Example rollout choice, not a universal AWS requirement
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.35
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted

    # EKS-related labels
    app.kubernetes.io/managed-by: eks
```

### Consideraciones sobre los espacios de nombres del sistema de EKS

Un agente con acceso al host no puede cumplir Baseline, pero eso no significa que todos los Pod de `kube-system` necesiten privilegios completos. Revise la versión exacta del complemento y la especificación Pod representada. Evite sobrescribir en bloque la configuración para deshabilitar warn/audit en todo un espacio de nombres del sistema. Siempre que sea posible, aísle los agentes del host aprobados de las aplicaciones ordinarias y restrinja quién puede desplegar allí. El siguiente ejemplo corresponde a un espacio de nombres dedicado; no es una instrucción para volver a etiquetar espacios de nombres del sistema existentes.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: host-agents
  labels:
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

### Complementos de EKS y compatibilidad con PSS

| Componente / despliegue típico | Punto de revisión de PSS |
|---|---|
| VPC CNI `aws-node`, kube-proxy | La red del host o las operaciones privilegiadas en los nodos pueden superar Baseline |
| DaemonSet de nodo de EBS/EFS CSI | Los montajes del host pueden superar Baseline; los Pod del controlador tienen necesidades distintas |
| CloudWatch Agent / Fluent Bit a nivel de nodo | El acceso a los registros/sistema de archivos del host depende de la configuración real |
| CoreDNS, AWS Load Balancer Controller, Cluster Autoscaler | Evalúe la especificación representada frente a Baseline/Restricted; el nombre de un componente por sí solo no demuestra que cumpla |

Los componentes de nodo integrados de EKS Auto Mode son distintos de los complementos autogestionados. Esta tabla sirve de ayuda para la revisión; no es una matriz de compatibilidad probada ni un requisito para instalar todos los complementos enumerados.

### Ejemplo de Terraform para EKS

Este fragmento administra un espacio de nombres de aplicación. Configure y revise por separado el proveedor de Kubernetes y su contexto de destino; no se ejecutaron la inicialización, el plan ni el apply del proveedor. Adopte o importe un espacio de nombres existente a través de su responsable, en lugar de crear una propiedad de Terraform/GitOps en conflicto. La política está fijada deliberadamente y no se modifican etiquetas de espacios de nombres del sistema.

```hcl
# Provider authentication/context and ownership must be configured separately.
resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = "my-app"
    labels = {
      "pod-security.kubernetes.io/enforce"         = "restricted"
      "pod-security.kubernetes.io/enforce-version" = "v1.35"
      "pod-security.kubernetes.io/audit"           = "restricted"
      "pod-security.kubernetes.io/audit-version"   = "v1.35"
      "pod-security.kubernetes.io/warn"            = "restricted"
      "pod-security.kubernetes.io/warn-version"    = "v1.35"
      "environment"                              = "production"
    }
  }
}
```

---

## Detalles de los perfiles de seguridad {#security-profile-details}

### Detalles del perfil Privileged

El perfil Privileged no impone restricciones PSS; la validación de la API, RBAC y otras comprobaciones de admisión siguen vigentes. El siguiente ejemplo con root y acceso al host es solo para analizar políticas; no se recomienda desplegar esta carga de trabajo.

```yaml
# All options allowed in Privileged profile
apiVersion: v1
kind: Pod
metadata:
  name: privileged-example
spec:
  hostNetwork: true
  hostPID: true
  hostIPC: true
  containers:
  - name: privileged-container
    image: nginx
    securityContext:
      privileged: true
      allowPrivilegeEscalation: true
      runAsUser: 0
      capabilities:
        add:
          - ALL
    volumeMounts:
    - name: host-root
      mountPath: /host
  volumes:
  - name: host-root
    hostPath:
      path: /
      type: Directory
```

### Detalles del perfil Baseline

```yaml
# Baseline profile restrictions (v1.35)
#
# Prohibited fields and values:
#
# spec.hostNetwork: true prohibited
# spec.hostPID: true prohibited
# spec.hostIPC: true prohibited
#
# spec.containers[*].securityContext.privileged: true prohibited
# spec.initContainers[*].securityContext.privileged: true prohibited
# spec.ephemeralContainers[*].securityContext.privileged: true prohibited
#
# spec.containers[*].securityContext.capabilities.add restricted
#   - Allowed: NET_BIND_SERVICE (only this in Restricted)
#   - Additionally allowed in Baseline: AUDIT_WRITE, CHOWN, DAC_OVERRIDE,
#     FOWNER, FSETID, KILL, MKNOD, NET_BIND_SERVICE,
#     SETFCAP, SETGID, SETPCAP, SETUID, SYS_CHROOT
#
# spec.volumes[*].hostPath prohibited
#
# spec.containers[*].ports[*].hostPort prohibited (except 0)
#
# spec.securityContext.appArmorProfile.type restricted
#   - Allowed: profile omitted, or type RuntimeDefault/Localhost
#   - Prohibited: Unconfined
#
# spec.securityContext.seLinuxOptions.type restricted
#   - Prohibited: Custom types (container_t etc. allowed)
#
# spec.securityContext.seccompProfile.type restricted
#   - Prohibited: Unconfined
#
# spec.securityContext.sysctls restricted
#   - Only the explicit versioned PSS sysctl allowlist

apiVersion: v1
kind: Pod
metadata:
  name: baseline-compliant
spec:
  automountServiceAccountToken: false
  containers:
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    ports:
    - containerPort: 8080
    securityContext:
      capabilities:
        drop: [ALL]
```

### Detalles del perfil Restricted

Restricted añade a Baseline su lista de volúmenes permitidos, la ejecución como usuario no root, seccomp explícito, la prohibición de escalada de privilegios y el descarte de todas las capacidades. `NET_BIND_SERVICE` es la única capacidad que se permite añadir, pero este listener en el puerto 8080 no la necesita. `readOnlyRootFilesystem` es una medida de refuerzo recomendada, no un requisito de PSS. Establecer `containerPort` es metadato; no reconfigura Nginx.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: restricted-compliant
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 101
    runAsGroup: 101
    fsGroup: 101
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir: {}
```

### Ejemplo completo de Nginx compatible con Restricted

Se comprobó el digest con los metadatos OCI upstream para Linux amd64/arm64 (Nginx 1.30.4, usuario 101); no se descargaron capas de la imagen ni se ejecutó ningún contenedor. La documentación upstream indica el puerto 8080, `/tmp/nginx.pid` y las rutas temporales bajo `/tmp`. El ConfigMap siguiente proporciona el listener y el endpoint de estado correspondientes. Créelo en el mismo espacio de nombres antes del Deployment. Valide el inicio y la disponibilidad en el entorno aprobado antes del despliegue.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-restricted
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 101  # nginx user
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: nginx
        image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 101
          capabilities:
            drop:
              - ALL
        ports:
        - containerPort: 8080
        resources:
          limits:
            cpu: 100m
            memory: 128Mi
          requests:
            cpu: 50m
            memory: 64Mi
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: tmp
        emptyDir: {}
      - name: config
        configMap:
          name: nginx-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-config
  namespace: production
data:
  default.conf: |
    server {
        listen 8080;
        server_name localhost;

        location / {
            root /usr/share/nginx/html;
            index index.html;
        }

        location /healthz {
            return 200 'OK';
            add_header Content-Type text/plain;
        }
    }
```

---

## Configuración de excepciones {#exemptions-configuration}

### Configuración de excepciones a nivel de clúster

Los servidores de la API autogestionados pueden cargar esta configuración mediante `--admission-control-config-file`. El ejemplo deja vacías todas las listas de excepciones. Las excepciones omiten **todos los modos PSA**. `usernames` coincide exactamente con el nombre de usuario autenticado de la solicitud, no con un grupo, un comodín o la ServiceAccount del futuro Pod. Eximir la cuenta de un controlador omitiría las comprobaciones de los Pod que crea en nombre de muchos usuarios. Los nombres de espacios de nombres y RuntimeClass también deben coincidir exactamente. Configure una excepción solo después de restringir por separado quién puede utilizarla.

```yaml
# Self-managed API server configuration; not an EKS control-plane setting
apiVersion: apiserver.config.k8s.io/v1
kind: AdmissionConfiguration
plugins:
- name: PodSecurity
  configuration:
    apiVersion: pod-security.admission.config.k8s.io/v1
    kind: PodSecurityConfiguration
    defaults:
      enforce: baseline
      enforce-version: v1.35
      audit: restricted
      audit-version: v1.35
      warn: restricted
      warn-version: v1.35
    exemptions:
      usernames: []
      runtimeClasses: []
      namespaces: []
```

### Excepciones en EKS

EKS no permite editar la AdmissionConfiguration del servidor de la API administrado. El valor de espacio de nombres `enforce: privileged` es un perfil permisivo, **no una excepción estática**: warn/audit todavía pueden evaluar las solicitudes. Restrinja los permisos para escribir en el espacio de nombres y desplegar en él, y separe los agentes del host de las aplicaciones ordinarias. Por ejemplo, node-exporter configurado con hostNetwork/hostPID/hostPath no puede superar Baseline; establecer Baseline no hace que esos accesos al host sean seguros ni estén permitidos.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: host-agents
  labels:
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

### Excepciones basadas en RuntimeClass

Una RuntimeClass selecciona un controlador de runtime CRI configurado. Crear el recurso no instala gVisor/Kata ni concede una excepción PSA. Todos los nodos seleccionados deben ser compatibles con el controlador (o se deben utilizar restricciones de programación adecuadas). Esta definición, por sí sola, deja PSA plenamente aplicable:

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc
```

Solo una excepción `runtimeClasses: ["gvisor"]` configurada por separado en un servidor de la API autogestionado omite PSA. Cualquier solicitud que pueda seleccionar esa clase podría eludir PSA; el aislamiento del runtime no reemplaza la autorización de admisión. Esta configuración no está disponible en el plano de control administrado de EKS.

### Excepciones detalladas con Kyverno

Kyverno no puede convertir una denegación de PSA en una autorización. Si un agente del host necesita una excepción, primero diseñe el perfil PSA y los permisos de despliegue del espacio de nombres; después añada una política que aplique controles de forma independiente y con una excepción de alcance reducido. Una exclusión que solo abarque HostPath no excluye las comprobaciones de hostNetwork/hostPID; usar únicamente una etiqueta de Pod mutable o una etiqueta de imagen no constituye autorización.

Consulte [Gestión de políticas de Kyverno](./01-kyverno-policy-management.md) para conocer las API de políticas revisadas y los límites de versión/obsolescencia. No copie una `ClusterPolicy` heredada con `validationFailureAction: enforce` en minúsculas; no es un valor válido y ClusterPolicy está obsoleta en Kyverno 1.19. Se debe probar cualquier sustitución con las cargas de trabajo normales y las de excepción.

---

## Buenas prácticas para una adopción gradual {#best-practices-for-gradual-adoption}

### Paso 1: Analizar el estado actual

Obtenga una vista previa de un cambio a **enforce**, no a warn: solo un cambio de nivel/versión de enforce activa la comprobación de los Pod existentes. Esta simulación del servidor no guarda etiquetas ni expulsa Pod. Si la política enforce efectiva no cambia, no se activa un nuevo análisis. El análisis es de mejor esfuerzo y puede limitar o deduplicar las advertencias; que no aparezcan advertencias no constituye una auditoría completa de las cargas de trabajo. Los errores de comandos/autenticación siguen siendo errores.

```bash
#!/usr/bin/env bash
# preview-pss.sh: no namespace mutation
set -euo pipefail
: "${PSS_CONTEXT:?Set the approved test context}"
: "${PSS_NAMESPACE:?Set one namespace to inspect}"
kubectl --context "$PSS_CONTEXT" --request-timeout=30s \
  get namespace "$PSS_NAMESPACE" -o yaml
kubectl --context "$PSS_CONTEXT" --request-timeout=30s \
  label namespace "$PSS_NAMESPACE" \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=v1.35 \
  --overwrite --dry-run=server
```

### Paso 2: Estrategia de despliegue gradual

Los intervalos de días son un calendario de planificación ilustrativo, no duraciones de migración medidas. Utilice un inventario explícito de espacios de nombres, nunca reduzca una política existente más estricta y avance solo después de probar los Pod de sustitución y la capacidad de reversión.

```yaml
# Gradual rollout using GitOps

# Phase 1: Monitoring (Day 1-7)
# - Apply warn: baseline to all namespaces
# - Collect and analyze violations

# Phase 2: Development Environment (Day 8-14)
# - Apply enforce: baseline to development namespaces
# - Apply warn: baseline to staging namespaces

# Phase 3: Staging Environment (Day 15-21)
# - Apply enforce: baseline to staging namespaces
# - Apply warn: baseline to production namespaces

# Phase 4: Production Environment (Day 22-28)
# - Apply enforce: baseline to production namespaces
# - Apply warn: restricted to all environments

# Phase 5: Restricted Hardening (Day 29+)
# - Apply enforce: restricted as default for new namespaces
# - Gradually migrate existing namespaces
```

### Paso 3: Configurar la supervisión y las alertas

Estas reglas requieren las CRD de Prometheus Operator, un selector que incluya este PrometheusRule y una extracción autorizada del servidor de la API que exponga `pod_security_evaluations_total`. PSA integrado no es un webhook llamado `pod-security-webhook`. Las etiquetas de evaluación incluyen decision, policy_level, policy_version, mode, request_operation, resource y subresource; **no hay ninguna etiqueta de espacio de nombres**. Correlacione los eventos de auditoría conservados para obtener detalles del espacio de nombres y la solicitud. La ausencia de métricas no demuestra que haya cero infracciones; una denegación en modo audit indica una evaluación que infringe la política, no necesariamente una solicitud a la API rechazada.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: pss-violations
  namespace: monitoring
spec:
  groups:
  - name: pod-security-standards
    rules:
    - alert: PSSViolationDetected
      expr: |
        sum by (policy_level, policy_version, mode) (
          increase(pod_security_evaluations_total{mode="enforce",decision="deny"}[5m])
        ) > 0
      labels:
        severity: warning
      annotations:
        summary: "PSA denied a Pod request"
        description: "Policy {{ $labels.policy_level }}:{{ $labels.policy_version }}. Correlate audit logs for namespace and request identity."
    - alert: PSSAuditViolation
      expr: |
        sum by (policy_level, policy_version, mode) (
          increase(pod_security_evaluations_total{mode="audit",decision="deny"}[5m])
        ) > 10
      for: 5m
      labels:
        severity: info
      annotations:
        summary: "PSA audit violations increasing"
        description: "{{ $value }} violating evaluations over five minutes; not a count of unique Pods."
```

### Paso 4: Comprobaciones de cumplimiento automatizadas

Guarde este archivo como `check-pss.py` en el proyecto responsable de las cargas de trabajo. Requisitos previos: Python 3 con PyYAML, un kubectl compatible, credenciales de clúster aprobadas, un servidor de la API de Kubernetes compatible con la política v1.35 y un espacio de nombres de prueba existente que aplique explícitamente `restricted:v1.35`. Quien invoque el script necesita autorización para leer el espacio de nombres y crear Pod, incluso para la simulación del servidor. No exponga credenciales del clúster a código de solicitudes de cambios no confiable.

```python
#!/usr/bin/env python3
# check-pss.py CONTEXT NAMESPACE pod.yaml [pod2.yaml ...]
# Requires Python 3 + PyYAML and a preconfigured, authorized kubectl.
import copy, json, subprocess, sys
from pathlib import Path
import yaml

if len(sys.argv) < 4:
    raise SystemExit("Usage: check-pss.py CONTEXT NAMESPACE pod.yaml [...]")
context, namespace, *files = sys.argv[1:]
pods = []
for filename in files:
    docs = list(yaml.safe_load_all(Path(filename).read_text()))
    if not docs or any(not isinstance(p, dict) for p in docs):
        raise SystemExit(f"{filename}: empty/non-object YAML")
    for pod in docs:
        if (pod.get("apiVersion"), pod.get("kind")) != ("v1", "Pod"):
            raise SystemExit(f"{filename}: only explicit v1 Pod test inputs are supported")
        meta = pod.setdefault("metadata", {})
        if meta.get("namespace", namespace) != namespace:
            raise SystemExit(f"{filename}: namespace mismatch")
        meta["namespace"] = namespace
        pods.append(pod)
base = ["kubectl", "--context", context, "--request-timeout=30s"]
ns = json.loads(subprocess.run(
    base + ["get", "namespace", namespace, "-o", "json"],
    check=True, text=True, capture_output=True).stdout)
labels = ns["metadata"].get("labels", {})
if (labels.get("pod-security.kubernetes.io/enforce"),
    labels.get("pod-security.kubernetes.io/enforce-version")) != ("restricted", "v1.35"):
    raise SystemExit("Test namespace must explicitly enforce restricted:v1.35")

def dry_run(pod):
    return subprocess.run(
        base + ["create", "--dry-run=server", "--validate=strict",
                "--namespace", namespace, "-f", "-"],
        input=json.dumps(pod), text=True, capture_output=True)

control = {
    "apiVersion": "v1", "kind": "Pod",
    "metadata": {"generateName": "pss-control-", "namespace": namespace},
    "spec": {
        "automountServiceAccountToken": False,
        "securityContext": {"runAsNonRoot": True, "runAsUser": 65532,
                            "seccompProfile": {"type": "RuntimeDefault"}},
        "containers": [{"name": "probe", "image": "registry.k8s.io/pause:3.10",
                        "securityContext": {"allowPrivilegeEscalation": False,
                                            "capabilities": {"drop": ["ALL"]}}}],
    },
}
good = dry_run(control)
if good.returncode:
    raise SystemExit("Positive control failed; no compliance result:\n" + good.stderr)
bad = copy.deepcopy(control)
bad["spec"]["hostPID"] = True
denied = dry_run(bad)
if denied.returncode == 0 or 'violates PodSecurity "restricted:v1.35"' not in denied.stderr:
    raise SystemExit("Negative control did not confirm PSA rejection:\n" + denied.stderr)
for pod in pods:
    result = dry_run(pod)
    if result.returncode:
        raise SystemExit("Pod dry-run failed:\n" + result.stderr)
print(f"{len(pods)} explicit Pod inputs passed server dry-run in {namespace}")
```

```bash
python3 check-pss.py "$PSS_CONTEXT" "$PSS_NAMESPACE" ./pss-inputs/web-pod.yaml
```

La lista explícita de entradas debe cubrir la plantilla Pod de cada carga de trabajo, incluidos los contenedores init. Este ejemplo rechaza Deployments, archivos vacíos, espacios de nombres incorrectos, errores en las consultas, ausencia de aplicación de la política y una ruta de control negativo exenta/inactiva. La extracción de plantillas, los webhooks de mutación, la programación, el inicio de imágenes y el comportamiento futuro del runtime requieren comprobaciones independientes. PSA debe rechazar el control negativo; cualquier otro error no es concluyente y hace que la comprobación falle. El responsable del clúster de pruebas también debe prohibir o probar por separado cualquier otra excepción que pudiera seleccionar un Pod candidato (por ejemplo, una RuntimeClass exenta).

### Paso 5: Documentación y formación

```markdown
# Pod Security Standards Guidelines

## Checklist for Developers

### When Writing Restricted-Level Pods:

- [ ] Set `spec.securityContext.runAsNonRoot: true`
- [ ] Set `spec.securityContext.seccompProfile.type: RuntimeDefault`
- [ ] Set `allowPrivilegeEscalation: false` on all containers
- [ ] Set `capabilities.drop: ["ALL"]` on all containers
- [ ] Set `readOnlyRootFilesystem: true` (recommended)
- [ ] Use unprivileged images (e.g., nginxinc/nginx-unprivileged)
- [ ] Mount emptyDir for writable paths

### Common Problem Solutions:

1. **nginx fails to bind port 80**
   → Add `NET_BIND_SERVICE` capability or use port 8080

2. **File write failures**
   → Mount emptyDir volumes to required paths

3. **Process runs as root**
   → Use unprivileged base image or add USER directive in Dockerfile
```

---

## Solución de problemas

### Errores comunes y soluciones

#### 1. Error «allowPrivilegeEscalation != false»

Fragmento ilustrativo del error; el YAML es una **corrección parcial de la especificación Pod**, no un manifiesto independiente. Conserve la imagen y la configuración actuales del contenedor. Aplique también los controles pertinentes por contenedor a los contenedores init y efímeros.

```text
allowPrivilegeEscalation != false
```

```yaml
spec:
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
```

#### 2. Error «unrestricted capabilities»

Fragmento ilustrativo del error; el YAML es una **corrección parcial de la especificación Pod**, no un manifiesto independiente. Conserve la imagen y la configuración actuales del contenedor. Aplique también los controles pertinentes por contenedor a los contenedores init y efímeros.

```text
unrestricted capabilities
```

```yaml
spec:
  containers:
  - name: app
    securityContext:
      capabilities:
        drop: [ALL]
```

#### 3. Error «runAsNonRoot != true»

Fragmento ilustrativo del error; el YAML es una **corrección parcial de la especificación Pod**, no un manifiesto independiente. Conserve la imagen y la configuración actuales del contenedor. Aplique también los controles pertinentes por contenedor a los contenedores init y efímeros.

```text
runAsNonRoot != true
```

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 101
```

#### 4. Error «seccompProfile»

Fragmento ilustrativo del error; el YAML es una **corrección parcial de la especificación Pod**, no un manifiesto independiente. Conserve la imagen y la configuración actuales del contenedor. Aplique también los controles pertinentes por contenedor a los contenedores init y efímeros.

```text
seccompProfile must be RuntimeDefault or Localhost
```

```yaml
spec:
  securityContext:
    seccompProfile:
      type: RuntimeDefault
```

### Herramientas para comprobar infracciones de PSS

Polaris, kube-score y Trivy proporcionan comprobaciones estáticas adicionales; no son sustitutos exactos de la política PSA versionada, las excepciones y las mutaciones del clúster. Instale una versión revisada y consulte la ayuda de la CLI. Una simulación del servidor satisfactoria se limita a esa solicitud, identidad, espacio de nombres y momento; utilice los controles explícitos de Pod indicados arriba.

```bash
# Dry-run check with kubectl
kubectl apply -f my-pod.yaml --dry-run=server

# Check with Polaris
polaris audit --audit-path ./k8s/ --format pretty

# Check with kube-score
kube-score score my-deployment.yaml

# Configuration check with Trivy
trivy config ./k8s/
```

---

## Resumen

Pod Security Standards (PSS) ofrece un enfoque estandarizado para gestionar la seguridad de los Pod en Kubernetes:

1. **Tres niveles de seguridad**: Privileged (todos los privilegios), Baseline (evitar escaladas conocidas), Restricted (privilegios mínimos)
2. **Tres modos de aplicación**: enforce (bloquear), audit (registrar), warn (advertir)
3. **Etiquetas de espacio de nombres**: no hay asociación de uso al estilo PSP; RBAC aún debe restringir las etiquetas de espacio de nombres y la creación de cargas de trabajo
4. **Compatibilidad con la adopción gradual**: migración segura mediante los modos warn/audit

### Recomendaciones

- Habilite PSS desde el principio en los clústeres nuevos
- En clústeres existentes, empiece con el modo warn y refuerce la política gradualmente
- Aplique como mínimo el nivel Baseline en entornos de producción
- Aplique el nivel Restricted a las cargas de trabajo sensibles

---

## Referencias

- [Documentación oficial de Kubernetes sobre Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Documentación oficial de Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- [Guía de buenas prácticas de EKS: seguridad de Pod](https://docs.aws.amazon.com/eks/latest/best-practices/pod-security.html)
- [Guía de migración de PSP a PSS](https://kubernetes.io/docs/tasks/configure-pod-container/migrate-from-psp/)

- [Vista previa de las etiquetas de espacio de nombres de PSA y comprobaciones de Pod existentes](https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-namespace-labels/)
- [Configuración y excepciones de PSA](https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-admission-controller/)
- [Imagen Nginx no privilegiada y rutas con permisos de escritura](https://github.com/nginx/docker-nginx-unprivileged)
