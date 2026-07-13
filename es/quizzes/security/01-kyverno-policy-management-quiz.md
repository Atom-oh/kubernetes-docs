# Cuestionario sobre gestión de políticas de Kyverno

Este cuestionario evalúa tu comprensión de la gestión de políticas usando Kyverno en Kubernetes.

## Preguntas del cuestionario

### 1. ¿Qué es Kyverno?

A. Un motor de políticas nativo de Kubernetes
B. Un escáner de imágenes de contenedor
C. Una herramienta de monitoreo de clusters
D. Una implementación de service mesh

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Un motor de políticas nativo de Kubernetes**

**Explicación:**
Kyverno es un motor de políticas nativo de Kubernetes que puede validar, mutar y generar recursos de Kubernetes usando políticas escritas en YAML o JSON. Como Kyverno usa la API de Kubernetes y la sintaxis YAML, puedes definir y gestionar políticas sin aprender un nuevo lenguaje ni nuevas herramientas.

**Características clave:**
1. **Integración nativa con Kubernetes**: Funciona directamente con la API de Kubernetes.
2. **Definición declarativa de políticas**: Usa políticas declarativas basadas en YAML.
3. **Compatibilidad con varios tipos de políticas**: Admite políticas Validate, Mutate, Generate y Cleanup.
4. **Verificación de imágenes**: Proporciona capacidades de verificación de seguridad para imágenes de contenedor.
5. **Auditoría e informes**: Proporciona capacidades de auditoría e informes para el cumplimiento de políticas.

**Política de ejemplo:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
spec:
  validationFailureAction: enforce
  rules:
  - name: check-team-label
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "label 'team' is required"
      pattern:
        metadata:
          labels:
            team: "?*"
```

Esta política requiere que todos los Pods tengan una etiqueta 'team'.

**Problemas con las otras opciones:**
- B. Escáner de imágenes de contenedor: Aunque Kyverno proporciona capacidades de verificación de imágenes, su propósito principal es la gestión de políticas. Entre los escáneres de imágenes dedicados se incluyen Trivy, Clair, etc.
- C. Herramienta de monitoreo de clusters: Kyverno no es una herramienta de monitoreo. Prometheus, Grafana, etc. son herramientas de monitoreo.
- D. Implementación de service mesh: Kyverno no es un service mesh. Istio, Linkerd, etc. son implementaciones de service mesh.
</details>

### 2. ¿Cuál de los siguientes NO es un tipo de política admitido por Kyverno?

A. Validate
B. Mutate
C. Generate
D. Authenticate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Authenticate**

**Explicación:**
Kyverno admite los siguientes tipos de políticas:

1. **Validate**: Valida que los recursos cumplan determinadas condiciones.
2. **Mutate**: Modifica automáticamente los recursos.
3. **Generate**: Crea automáticamente recursos adicionales cuando se crean otros recursos.
4. **Verify Images**: Verifica las firmas de imágenes de contenedor.
5. **Cleanup**: Elimina automáticamente recursos según determinadas condiciones.

Kyverno no admite directamente un tipo de política Authentication. La autenticación en Kubernetes suele gestionarse a nivel del servidor de API y administrarse mediante mecanismos como RBAC (Role-Based Access Control), OIDC (OpenID Connect) y service accounts.

**Ejemplos de cada tipo de política:**

1. **Ejemplo de política Validate**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: enforce
  rules:
  - name: check-resource-limits
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Resource limits are required"
      pattern:
        spec:
          containers:
          - resources:
              limits:
                memory: "?*"
                cpu: "?*"
```

2. **Ejemplo de política Mutate**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-default-labels
spec:
  rules:
  - name: add-environment-label
    match:
      resources:
        kinds:
        - Pod
    mutate:
      patchStrategicMerge:
        metadata:
          labels:
            environment: "{{request.object.metadata.namespace}}"
```

3. **Ejemplo de política Generate**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-networkpolicy
spec:
  rules:
  - name: generate-default-networkpolicy
    match:
      resources:
        kinds:
        - Namespace
    generate:
      kind: NetworkPolicy
      name: default-deny-all
      namespace: "{{request.object.metadata.name}}"
      data:
        spec:
          podSelector: {}
          policyTypes:
          - Ingress
          - Egress
```

4. **Ejemplo de política Verify Images**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
spec:
  validationFailureAction: enforce
  rules:
  - name: check-image-signatures
    match:
      resources:
        kinds:
        - Pod
    verifyImages:
    - image: "docker.io/library/*"
      repository: "docker.io/library/*"
      key: |-
        -----BEGIN PUBLIC KEY-----
        MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE8xOUetsCa8AKa9F1hx3gUw1RcyZg
        rjMqwNZcDzDv3PpFtpSdwGzA1GRk7XBqDJJQa9Jekky0yvEUDjtwLFp7aw==
        -----END PUBLIC KEY-----
```

5. **Ejemplo de política Cleanup**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: cleanup-old-pods
spec:
  rules:
  - name: cleanup-completed-pods
    match:
      resources:
        kinds:
        - Pod
    preconditions:
      all:
      - key: "{{request.object.status.phase}}"
        operator: In
        value: ["Succeeded", "Failed"]
    cleanup:
      ttl: "24h"
```

**Explicación de las otras opciones:**
- A. Validate: Un tipo de política admitido por Kyverno que valida si los recursos cumplen determinadas condiciones.
- B. Mutate: Un tipo de política admitido por Kyverno que modifica automáticamente los recursos.
- C. Generate: Un tipo de política admitido por Kyverno que crea automáticamente recursos adicionales cuando se crean otros recursos.
</details>
### 3. ¿Qué significa `validationFailureAction: enforce` en una política de Kyverno?

A. Generar solo una advertencia ante una infracción de política
B. Bloquear la creación o actualización de recursos ante una infracción de política
C. Modificar automáticamente el recurso ante una infracción de política
D. Eliminar el recurso ante una infracción de política

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Bloquear la creación o actualización de recursos ante una infracción de política**

**Explicación:**
En una política de Kyverno, `validationFailureAction: enforce` es una configuración que bloquea la creación o actualización de recursos cuando se infringe una política. Cuando se aplica esta configuración, la política rechaza la creación o modificación de recursos que no cumplen las condiciones de la política y devuelve un mensaje de infracción de política al usuario.

Hay dos valores posibles para `validationFailureAction`:
1. **enforce**: Bloquea la creación o actualización de recursos ante una infracción de política.
2. **audit**: Permite la creación o actualización de recursos ante una infracción de política, pero registra la infracción. Esto es útil para probar políticas o auditar el estado actual.

**Política de ejemplo:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-probes
spec:
  validationFailureAction: enforce  # Block resource creation/update on policy violation
  rules:
  - name: check-readiness-probe
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Readiness probe is required"
      pattern:
        spec:
          containers:
          - readinessProbe:
              {}
```

Esta política comprueba que todos los contenedores de Pod tengan configurado un readinessProbe y, si no es así, bloquea la creación del Pod.

**Cómo aplicar la política:**
```bash
# Apply the policy
kubectl apply -f require-probes.yaml

# Attempt to create a Pod without a readinessProbe
kubectl apply -f pod-without-probe.yaml
# Result: Error from server: error when creating "pod-without-probe.yaml": admission webhook "validate.kyverno.svc" denied the request:
# resource Pod/default/nginx was blocked due to the following policies: require-probes: check-readiness-probe: Readiness probe is required
```

**Problemas con las otras opciones:**
- A. Generar solo una advertencia ante una infracción de política: Este es el comportamiento de `validationFailureAction: audit`.
- C. Modificar automáticamente el recurso ante una infracción de política: Este es el comportamiento de las políticas mutate y no está relacionado con validationFailureAction.
- D. Eliminar el recurso ante una infracción de política: Kyverno no elimina automáticamente los recursos existentes ante una infracción de política. Las políticas Cleanup pueden eliminar recursos según determinadas condiciones, pero este es un mecanismo diferente de validationFailureAction.
</details>

### 4. ¿Qué campo se usa en Kyverno para seleccionar a qué recursos se aplica una política?

A. selector
B. match
C. target
D. apply

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. match**

**Explicación:**
El campo usado en Kyverno para seleccionar a qué recursos se aplica una política es `match`. Este campo se usa para especificar el kind, nombre, namespace, etiquetas, etc. de los recursos a los que se aplican las reglas de la política.

El campo `match` puede incluir los siguientes subcampos:
1. **resources**: Especifica el kind del recurso, nombre, namespace, etc.
2. **subjects**: Especifica usuarios, grupos y service accounts a los que se aplica la política.
3. **roles**: Especifica roles a los que se aplica la política.
4. **clusterRoles**: Especifica cluster roles a los que se aplica la política.

Además, el campo `exclude` puede usarse para excluir recursos específicos de la aplicación de la política.

**Política de ejemplo:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels-for-deployments
spec:
  validationFailureAction: enforce
  rules:
  - name: check-required-labels
    match:
      resources:
        kinds:
        - Deployment
        namespaces:
        - "production"
        - "staging"
        selector:
          matchLabels:
            app.kubernetes.io/managed-by: kustomize
    validate:
      message: "Required labels are missing"
      pattern:
        metadata:
          labels:
            app.kubernetes.io/name: "?*"
            app.kubernetes.io/version: "?*"
            app.kubernetes.io/component: "?*"
```

Esta política se aplica solo a Deployments en los namespaces 'production' y 'staging' que tienen la etiqueta 'app.kubernetes.io/managed-by: kustomize'.

**Ejemplo de coincidencia compleja:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: complex-matching-policy
spec:
  validationFailureAction: enforce
  rules:
  - name: complex-match-rule
    match:
      resources:
        kinds:
        - Deployment
        - StatefulSet
        namespaces:
        - "production"
        - "staging"
        selector:
          matchLabels:
            tier: "frontend"
      subjects:
      - kind: User
        name: "admin@example.com"
      - kind: Group
        name: "system:masters"
    exclude:
      resources:
        namespaces:
        - "kube-system"
        names:
        - "critical-deployment"
    validate:
      message: "Policy validation failed"
      pattern:
        spec:
          template:
            spec:
              containers:
              - securityContext:
                  runAsNonRoot: true
```

Esta política se aplica a Deployments y StatefulSets en los namespaces 'production' y 'staging' con la etiqueta 'tier: frontend', y solo cuando los crea o modifica el usuario 'admin@example.com' o el grupo 'system:masters'. Se excluyen los recursos en el namespace 'kube-system' y los recursos llamados 'critical-deployment'.

**Problemas con las otras opciones:**
- A. selector: En Kyverno, se usa como subcampo, por ejemplo `match.resources.selector`, pero no es un campo de nivel superior.
- C. target: Un campo que no se usa en las políticas de Kyverno.
- D. apply: Un campo que no se usa en las políticas de Kyverno.
</details>

### 5. ¿Qué tipo de política en Kyverno modifica automáticamente los recursos ante una infracción de política?

A. Validate
B. Mutate
C. Generate
D. Verify

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Mutate**

**Explicación:**
El tipo de política en Kyverno que modifica automáticamente los recursos ante una infracción de política es `Mutate`. Las políticas Mutate modifican automáticamente los recursos cuando se crean o actualizan para que cumplan los requisitos de la política.

Las políticas Mutate pueden modificar recursos usando los siguientes métodos:
1. **patchStrategicMerge**: Usa strategic merge patch para modificar recursos.
2. **patchesJson6902**: Usa JSON patch (RFC 6902) para modificar recursos.
3. **overlay**: (Legacy) Un campo heredado que proporciona la misma funcionalidad que patchStrategicMerge.

**Política de ejemplo:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-default-resources
spec:
  rules:
  - name: add-default-cpu-memory
    match:
      resources:
        kinds:
        - Deployment
    mutate:
      patchStrategicMerge:
        spec:
          template:
            spec:
              containers:
              - (name): "*"
                resources:
                  limits:
                    memory: "{{ if hasKey .object.spec.template.spec.containers[0].resources.limits \"memory\" }}{{ .object.spec.template.spec.containers[0].resources.limits.memory }}{{ else }}512Mi{{ end }}"
                    cpu: "{{ if hasKey .object.spec.template.spec.containers[0].resources.limits \"cpu\" }}{{ .object.spec.template.spec.containers[0].resources.limits.cpu }}{{ else }}500m{{ end }}"
                  requests:
                    memory: "{{ if hasKey .object.spec.template.spec.containers[0].resources.requests \"memory\" }}{{ .object.spec.template.spec.containers[0].resources.requests.memory }}{{ else }}256Mi{{ end }}"
                    cpu: "{{ if hasKey .object.spec.template.spec.containers[0].resources.requests \"cpu\" }}{{ .object.spec.template.spec.containers[0].resources.requests.cpu }}{{ else }}250m{{ end }}"
```

Esta política agrega valores predeterminados si no se han definido límites y solicitudes de recursos para los contenedores cuando se crean o actualizan recursos Deployment.

**Ejemplo usando JSON Patch:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-labels-json-patch
spec:
  rules:
  - name: add-labels
    match:
      resources:
        kinds:
        - Pod
    mutate:
      patchesJson6902: |-
        - op: add
          path: /metadata/labels/app.kubernetes.io~1managed-by
          value: kyverno
        - op: add
          path: /metadata/labels/environment
          value: "{{ request.object.metadata.namespace }}"
```

Esta política usa JSON patch para agregar etiquetas a Pods.

**Cómo aplicar una política Mutate:**
```bash
# Apply the policy
kubectl apply -f add-default-resources.yaml

# Create a Deployment without resource limits
kubectl apply -f deployment-without-resources.yaml

# Check the created Deployment
kubectl get deployment my-deployment -o yaml
# Result: Resource limits and requests are automatically added
```

**Problemas con las otras opciones:**
- A. Validate: Solo valida si los recursos cumplen las condiciones de la política; no los modifica.
- C. Generate: Crea recursos adicionales cuando se crean otros recursos, pero no modifica recursos existentes.
- D. Verify: Un tipo de política que verifica firmas de imágenes de contenedor; no modifica recursos.
</details>
### 6. ¿Cuándo es útil la política Generate de Kyverno?

A. Crear automáticamente recursos relacionados cuando se crea un recurso
B. Generar automáticamente mensajes de error durante la validación de recursos
C. Crear automáticamente backups cuando se elimina un recurso
D. Crear automáticamente versiones anteriores cuando se actualiza un recurso

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Crear automáticamente recursos relacionados cuando se crea un recurso**

**Explicación:**
La política Generate de Kyverno es útil para crear automáticamente recursos relacionados cuando se crea un recurso específico. Este tipo de política ayuda a gestionar dependencias entre recursos, automatizar configuraciones estándar y mantener entornos consistentes.

Casos de uso principales de las políticas Generate:
1. **Crear recursos predeterminados cuando se crea un namespace**: Crear automáticamente recursos como NetworkPolicy, ResourceQuota y LimitRange cuando se crea un namespace.
2. **Crear recursos relacionados cuando se despliega una aplicación**: Crear automáticamente Service, ConfigMap y Secret relacionados cuando se crea un Deployment.
3. **Automatizar configuraciones estándar**: Crear recursos adicionales con configuraciones estándar cuando se crean tipos específicos de recursos.
4. **Gestión de entornos multi-tenant**: Crear automáticamente todos los recursos necesarios cuando se crea un namespace para un nuevo tenant.

**Política de ejemplo:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-default-networkpolicy
spec:
  rules:
  - name: generate-default-networkpolicy
    match:
      resources:
        kinds:
        - Namespace
    exclude:
      resources:
        namespaces:
        - "kube-system"
        - "kube-public"
        - "kube-node-lease"
    generate:
      kind: NetworkPolicy
      name: default-deny-all
      namespace: "{{request.object.metadata.name}}"
      synchronize: true
      data:
        spec:
          podSelector: {}
          policyTypes:
          - Ingress
          - Egress
```

Esta política crea automáticamente una NetworkPolicy predeterminada en el namespace cuando se crea un nuevo namespace (excluyendo kube-system, kube-public y kube-node-lease). Esta NetworkPolicy bloquea todo el tráfico de ingress y egress.

**Campo synchronize**:
- `synchronize: true`: Sincroniza el recurso generado con el recurso de origen. Cuando el recurso de origen se cambia o elimina, el recurso generado también se actualiza o elimina según corresponda.
- `synchronize: false`: El recurso generado existe independientemente del recurso de origen.

**Ejemplo de política Clone:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: clone-secrets-across-namespaces
spec:
  rules:
  - name: clone-docker-registry-secret
    match:
      resources:
        kinds:
        - Namespace
    generate:
      kind: Secret
      name: docker-registry
      namespace: "{{request.object.metadata.name}}"
      synchronize: true
      clone:
        namespace: default
        name: docker-registry
```

Esta política clona el Secret 'docker-registry' desde el namespace 'default' al nuevo namespace cuando se crea un nuevo namespace.

**Problemas con las otras opciones:**
- B. Generar automáticamente mensajes de error durante la validación de recursos: Esta es una característica de las políticas Validate.
- C. Crear automáticamente backups cuando se elimina un recurso: Kyverno no proporciona funcionalidad de backup automático cuando se eliminan recursos de forma predeterminada.
- D. Crear automáticamente versiones anteriores cuando se actualiza un recurso: Esto está relacionado con el mecanismo de gestión de versiones de recursos de Kubernetes y no está relacionado con la política Generate de Kyverno.
</details>

### 7. ¿Qué tipo de política se usa en Kyverno para verificar firmas de imágenes de contenedor?

A. ImagePolicy
B. VerifyImages
C. SignaturePolicy
D. ImageVerification

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. VerifyImages**

**Explicación:**
El tipo de política que se usa en Kyverno para verificar firmas de imágenes de contenedor es `VerifyImages`. Este tipo de política se usa para confirmar que las imágenes de contenedor provienen de fuentes confiables y para verificar que no hayan sido manipuladas.

Las políticas VerifyImages proporcionan las siguientes características:
1. **Verificación de firmas de imágenes**: Verifica la integridad y el origen de las imágenes mediante firmas digitales.
2. **Restricción de image registry**: Restringe la descarga de imágenes únicamente desde registries específicos.
3. **Restricción de image tag**: Restringe tags específicos (por ejemplo, prohibir el uso del tag latest).
4. **Verificación de image digest**: Verifica digests de imágenes para garantizar que se usen versiones exactas de las imágenes.

**Política de ejemplo:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
spec:
  validationFailureAction: enforce
  rules:
  - name: verify-signatures
    match:
      resources:
        kinds:
        - Pod
    verifyImages:
    - image: "docker.io/library/*"
      repository: "docker.io/library/*"
      key: |-
        -----BEGIN PUBLIC KEY-----
        MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE8xOUetsCa8AKa9F1hx3gUw1RcyZg
        rjMqwNZcDzDv3PpFtpSdwGzA1GRk7XBqDJJQa9Jekky0yvEUDjtwLFp7aw==
        -----END PUBLIC KEY-----
    - image: "ghcr.io/my-org/*"
      repository: "ghcr.io/my-org/*"
      roots: |-
        -----BEGIN CERTIFICATE-----
        MIICmTCCAj+gAwIBAgIUYzA4YTU5YjQ2OTk1MjNmMDI2OTVkMGYwDQYJKoZIhvcN
        AQELBQAwXDELMAkGA1UEBhMCVVMxCzAJBgNVBAgMAkNBMRYwFAYDVQQHDA1TYW4g
        RnJhbmNpc2NvMQ8wDQYDVQQKDAZNeU9yZzEXMBUGA1UEAwwOY2EubXlvcmcubG9j
        YWwwHhcNMjMwNzIwMDAwMDAwWhcNMjQwNzE5MDAwMDAwWjBcMQswCQYDVQQGEwJV
        UzELMAkGA1UECAwCQ0ExFjAUBgNVBAcMDVNhbiBGcmFuY2lzY28xDzANBgNVBAoM
        Bk15T3JnMRcwFQYDVQQDDA5jYS5teW9yZy5sb2NhbDCBnzANBgkqhkiG9w0BAQEF
        AAOBjQAwgYkCgYEA1Jcpv/Gj0M3vaJQY4dLQJA9ZEMVCfOUzAFAgxm0DKJQSiQ+6
        HuQFTJjHnOJwYwKSAEGYe4JUg/fMUJMKl9BM7A9gjXKe0v8JMSyYGHVqTiPZ2RuW
        x7tO5Nh5jLz3GQYmZl0m7CRReY2zt9OUdRz2LR5xMPHitpy7aLGvGSsIZVECAwEA
        AaN7MHkwHQYDVR0OBBYEFPgVXUQGbNrGkFmXQkCXYvs8HzIIMB8GA1UdIwQYMBaA
        FPgVXUQGbNrGkFmXQkCXYvs8HzIIMA8GA1UdEwEB/wQFMAMBAf8wCwYDVR0PBAQD
        AgEGMB0GA1UdJQQWMBQGCCsGAQUFBwMBBggrBgEFBQcDAjANBgkqhkiG9w0BAQsF
        AAOBgQBB3TVGvZXKpZSzqPOzQzUNnCMzMEf1I7Qx9mKIqTKSZLqHYBDxHpQRQQNy
        aBBtMBgUn3KkZY8QdRUKj8Sw0PN+GV4bCXGwCJeRNZWO1FdaIVoUYKKWMPLYUUrJ
        UpZXfNQO8XUjIEqBK8RGn3MwYYwRF+OjDHGvpOf6hk0XPHGjlQ==
        -----END CERTIFICATE-----
```

Esta política verifica firmas para dos fuentes de imágenes:
1. Las imágenes docker.io/library/* se verifican usando la clave pública especificada.
2. Las imágenes ghcr.io/my-org/* se verifican usando el certificado especificado.

**Herramientas de firma de imágenes:**
Kyverno se integra con varias herramientas de firma de imágenes:
1. **Cosign**: Parte del proyecto Sigstore, una herramienta para firmar y verificar imágenes de contenedor.
2. **Notary**: El framework de confianza de contenido de Docker.
3. **GnuPG (GPG)**: Herramienta de cifrado open-source.

**Ejemplo de firma y verificación de imágenes usando Cosign:**
```bash
# Generate key pair
cosign generate-key-pair

# Sign the image
cosign sign --key cosign.key my-registry.io/my-image:tag

# Extract public key to use in Kyverno policy
cat cosign.pub
```

**Problemas con las otras opciones:**
- A. ImagePolicy: Un tipo de política que no se usa en Kyverno.
- C. SignaturePolicy: Un tipo de política que no se usa en Kyverno.
- D. ImageVerification: Un tipo de política que no se usa en Kyverno.
</details>

### 8. ¿Qué significa la configuración `background: false` en una política de Kyverno?

A. La política no se ejecuta en segundo plano
B. La política no se aplica a recursos existentes
C. La política no afecta a jobs en segundo plano del cluster
D. La política no se aplica a recursos creados por procesos en segundo plano

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. La política no se aplica a recursos existentes**

**Explicación:**
La configuración `background: false` en una política de Kyverno significa que la política no se aplica a recursos existentes y solo se aplica a recursos recién creados o actualizados. El valor predeterminado es `background: true`, en cuyo caso la política se aplica a todos los recursos, incluidos los existentes.

Características clave de la configuración `background`:
1. **Escaneo de recursos existentes**: Cuando `background: true`, Kyverno escanea periódicamente los recursos existentes en el cluster para comprobar el cumplimiento de políticas.
2. **Carga de recursos**: Escanear muchos recursos en clusters grandes puede causar una carga significativa, por lo que es mejor usar `background: true` solo cuando sea necesario.
3. **Informes de auditoría**: Los resultados del escaneo en segundo plano se registran en los CRDs PolicyReport y ClusterPolicyReport.
4. **Alcance**: Incluso cuando `background: false`, la política sigue actuando como Admission Controller y se aplica a recursos recién creados o actualizados.

**Política de ejemplo:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
spec:
  validationFailureAction: enforce
  background: false  # Does not apply to existing resources
  rules:
  - name: check-team-label
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "label 'team' is required"
      pattern:
        metadata:
          labels:
            team: "?*"
```

Esta política se aplica solo a Pods recién creados o actualizados y no escanea Pods existentes.

**Cuándo se necesita el escaneo en segundo plano:**
1. **Auditoría de cumplimiento**: Cuando necesitas comprobar regularmente que todos los recursos del cluster cumplen las políticas
2. **Aplicación de políticas de seguridad**: Cuando necesitas monitorear e informar continuamente vulnerabilidades de seguridad
3. **Detección de drift de configuración**: Cuando necesitas detectar si las configuraciones de recursos se desvían de las políticas con el tiempo

**Cuándo no se necesita el escaneo en segundo plano:**
1. **Optimización del rendimiento**: Cuando necesitas minimizar el uso de recursos en clusters grandes
2. **Gestionar solo recursos nuevos**: Cuando quieres dejar los recursos existentes tal como están y hacer que solo los recursos nuevos cumplan las políticas
3. **Introducción gradual de políticas**: Cuando quieres aplicar políticas solo a nuevos workloads sin afectar workloads existentes

**Problemas con las otras opciones:**
- A. La política no se ejecuta en segundo plano: Esta es una interpretación incorrecta de la configuración `background`. Todas las políticas de Kyverno actúan como Admission Controllers.
- C. La política no afecta a jobs en segundo plano del cluster: Esto no está relacionado con la configuración `background`.
- D. La política no se aplica a recursos creados por procesos en segundo plano: Esto no está relacionado con la configuración `background`. Las políticas se aplican independientemente de qué proceso haya creado el recurso.
</details>
### 9. ¿Qué recurso se usa en Kyverno para generar informes de infracciones de políticas?

A. PolicyViolation
B. PolicyReport
C. ComplianceReport
D. AuditReport

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. PolicyReport**

**Explicación:**
Los recursos usados en Kyverno para generar informes de infracciones de políticas son `PolicyReport` y `ClusterPolicyReport`. Estos recursos se usan para almacenar e informar los resultados de comprobación de políticas.

Características clave de PolicyReport y ClusterPolicyReport:
1. **Alcance**:
   - `PolicyReport`: Informa resultados de comprobación de políticas para recursos dentro de un namespace específico.
   - `ClusterPolicyReport`: Informa resultados de comprobación de políticas para recursos a nivel de cluster.

2. **Método de generación**:
   - Escaneo en segundo plano: Las políticas con `background: true` escanean periódicamente recursos y registran resultados en informes.
   - Comprobaciones de admisión: Los resultados de comprobación de políticas realizados durante la creación o actualización de recursos también se registran en informes.

3. **Contenido del informe**:
   - Nombre de la política
   - Recurso escaneado
   - Resultado (pass, fail, warn, error, skip)
   - Mensaje
   - Severidad
   - Categoría
   - Marca de tiempo

**Ejemplo de PolicyReport:**
```yaml
apiVersion: wgpolicyk8s.io/v1alpha2
kind: PolicyReport
metadata:
  name: polr-ns-default
  namespace: default
summary:
  pass: 7
  fail: 3
  warn: 0
  error: 0
  skip: 0
results:
- policy: require-labels
  rule: check-team-label
  resource:
    kind: Pod
    name: nginx
    namespace: default
  status: fail
  message: "label 'team' is required"
  severity: medium
  category: Best Practices
  timestamp:
    created: "2023-07-20T10:15:30Z"
- policy: require-probes
  rule: check-readiness-probe
  resource:
    kind: Pod
    name: nginx
    namespace: default
  status: pass
  timestamp:
    created: "2023-07-20T10:15:30Z"
```

**Cómo consultar informes:**
```bash
# Query namespace policy reports
kubectl get policyreport -n default

# Query cluster policy reports
kubectl get clusterpolicyreport

# Query specific report details
kubectl describe policyreport polr-ns-default -n default
```

**Integración de PolicyReport:**
Los informes de políticas de Kyverno siguen la especificación del CRD PolicyReport definida por el Kubernetes Policy Working Group. Esto permite que los resultados de varios motores de políticas (Kyverno, OPA Gatekeeper, etc.) se informen en un formato consistente.

**Cómo usar informes:**
1. **Monitoreo de cumplimiento**: Monitorear continuamente el estado de cumplimiento de políticas del cluster.
2. **Evidencia de auditoría**: Proporcionar la evidencia necesaria para auditorías de cumplimiento.
3. **Solución de problemas**: Ayudar a identificar y resolver infracciones de políticas.
4. **Análisis de tendencias**: Analizar tendencias de cumplimiento de políticas a lo largo del tiempo.

**Problemas con las otras opciones:**
- A. PolicyViolation: Un tipo de recurso que no se usa en Kyverno.
- C. ComplianceReport: Un tipo de recurso que no se usa en Kyverno.
- D. AuditReport: Un tipo de recurso que no se usa en Kyverno.
</details>

### 10. ¿Qué herramienta de línea de comandos se puede usar para probar políticas en Kyverno?

A. kyverno-cli
B. kubectl-kyverno
C. kyverno-test
D. policy-test

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. kubectl-kyverno**

**Explicación:**
La herramienta de línea de comandos que se puede usar para probar políticas en Kyverno es `kubectl-kyverno`. Esta herramienta funciona como un plugin de kubectl y ayuda a probar, validar y gestionar políticas de Kyverno.

Características clave de `kubectl-kyverno`:
1. **Pruebas de políticas**: Simula resultados de aplicación de políticas contra recursos.
2. **Validación de políticas**: Valida la sintaxis y estructura de las políticas.
3. **Generación de políticas**: Genera plantillas de políticas para casos de uso comunes.
4. **Aplicación de políticas**: Aplica políticas al cluster.

**Método de instalación:**
```bash
# Installation using krew
kubectl krew install kyverno

# Direct download and installation
curl -L https://github.com/kyverno/kyverno/releases/download/v1.10.0/kubectl-kyverno_v1.10.0_linux_x86_64.tar.gz | tar -xvz
sudo mv kubectl-kyverno /usr/local/bin/
```

**Comandos clave:**

1. **Pruebas de políticas**:
```bash
# Test policy application against a resource
kubectl kyverno apply /path/to/policy.yaml --resource /path/to/resource.yaml

# Test multiple policies
kubectl kyverno apply /path/to/policies/ --resource /path/to/resources/

# Check mutation results
kubectl kyverno apply /path/to/policy.yaml --resource /path/to/resource.yaml -o yaml
```

2. **Validación de políticas**:
```bash
# Validate policy syntax and structure
kubectl kyverno validate /path/to/policy.yaml
```

3. **Generación de políticas**:
```bash
# Generate a common policy template
kubectl kyverno create disallow-latest-tag

# Check available template list
kubectl kyverno create --help
```

4. **Aplicación de políticas**:
```bash
# Apply policy to the cluster
kubectl kyverno apply /path/to/policy.yaml --cluster
```

**Ejemplo de prueba:**
```bash
# Create policy file
cat > require-labels.yaml << EOF
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
spec:
  validationFailureAction: enforce
  rules:
  - name: check-team-label
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "label 'team' is required"
      pattern:
        metadata:
          labels:
            team: "?*"
EOF

# Create resource file
cat > pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  containers:
  - name: nginx
    image: nginx:1.19.0
EOF

# Test the policy
kubectl kyverno apply require-labels.yaml --resource pod.yaml

# Result:
# applying 1 policy to 1 resource...
# resource Pod/default/nginx failed validation
# policy require-labels: rule check-team-label failed: label 'team' is required
```

**Uso en pipeline de CI/CD:**
```yaml
# GitHub Actions example
name: Kyverno Policy Test

on:
  pull_request:
    paths:
      - 'policies/**'
      - 'resources/**'

jobs:
  test-policies:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v2

      - name: Install kubectl-kyverno
        run: |
          curl -L https://github.com/kyverno/kyverno/releases/download/v1.10.0/kubectl-kyverno_v1.10.0_linux_x86_64.tar.gz | tar -xvz
          sudo mv kubectl-kyverno /usr/local/bin/

      - name: Validate policies
        run: |
          kubectl kyverno validate policies/

      - name: Test policies against resources
        run: |
          kubectl kyverno apply policies/ --resource resources/
```

**Problemas con las otras opciones:**
- A. kyverno-cli: Un nombre de herramienta que no se usa en Kyverno.
- C. kyverno-test: Un nombre de herramienta que no se usa en Kyverno.
- D. policy-test: Un nombre de herramienta que no se usa en Kyverno.
</details>
