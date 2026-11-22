# Cuestionario de seguridad de Amazon EKS

> **Última actualización**: 21 de noviembre de 2026

Este cuestionario evalúa tu comprensión de las funciones, las prácticas recomendadas y las configuraciones de seguridad de Amazon EKS.

## Resumen del cuestionario
- Seguridad de red
- Seguridad de contenedores
- Seguridad de datos
- Cumplimiento y auditoría
- Prácticas recomendadas de seguridad

Las preguntas sobre la autenticación de acceso al clúster, IRSA/OIDC y Pod Identity se encuentran en el cuestionario de cada página de detalles: [Cuestionario sobre la autenticación de acceso al clúster de EKS](./05-eks-security-cluster-access-quiz.md), [Cuestionario sobre IRSA y el proveedor OIDC](./05-eks-security-irsa-oidc-quiz.md), [Cuestionario sobre EKS Pod Identity](./05-eks-security-pod-identity-quiz.md).

## Preguntas de opción múltiple

### 1. ¿Qué mecanismo de Kubernetes expresa reglas de tráfico de Pod basadas en etiquetas en una red de EKS que admite la aplicación de políticas?

- A) Solo grupos de seguridad de instancias
- B) Recursos NetworkPolicy con una implementación de red que aplique las políticas
- C) Solo políticas de puntos de conexión de VPC
- D) Solo comandos de firewall del host

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Recursos NetworkPolicy con una implementación de red que aplique las políticas**

**Explicación:**

NetworkPolicy selecciona Pods y el tráfico permitido mediante etiquetas y espacios de nombres de Kubernetes. Requiere una implementación de red que aplique las políticas. Los grupos de seguridad, incluidos los grupos de seguridad compatibles con Pods, siguen siendo controles útiles de AWS; no se limitan a las instancias completas. Las políticas de puntos de conexión de VPC rigen el acceso a los servicios de AWS compatibles, no el tráfico arbitrario de Pods basado en etiquetas.

**Ejemplo de política completa:** estos manifiestos describen un espacio de nombres de demostración aislado; no instalan aplicaciones ni sustituyen un CNI. Suponen nodos EC2 Linux estándar con un CNI compatible que aplique las políticas, y las etiquetas habituales de Deployment/Pod de CoreDNS. Auto Mode o el DNS local del nodo requieren reglas para la ruta del resolver que se utilice realmente. Si se restringe el tráfico de entrada a CoreDNS, su propietario también debe permitir estas consultas.

Guárdalo y aplícalo a través del propietario del espacio de nombres. La denegación predeterminada aísla ambas direcciones; el tráfico de salida del cliente y el tráfico de entrada al destino se permiten explícitamente para frontend → API y API → base de datos. DNS necesita UDP y TCP:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-network-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: Namespace
metadata:
  name: security-monitoring-demo
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: security-network-demo
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: security-network-demo
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-api
  namespace: security-network-demo
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
          app: api
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
  namespace: security-network-demo
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
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-to-database
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-ingress
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: monitor-api
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: security-monitoring-demo
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9090
```

El par de supervisión utiliza namespaceSelector **y** podSelector en un mismo par, por lo que solo se seleccionan los Pods de Prometheus que coinciden en security-monitoring-demo. La conexión saliente también necesita permiso cuando el cliente está aislado para el tráfico de salida:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: prometheus-to-demo-api
  namespace: security-monitoring-demo
spec:
  podSelector:
    matchLabels:
      app: prometheus
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: security-network-demo
      podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 9090
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

| Flujo | Resultado previsto con estas políticas |
|---|---|
| frontend → api TCP 8080 | Permitir |
| api → database TCP 5432 | Permitir |
| frontend → database TCP 5432 | Denegar |
| Pod no relacionado → api TCP 8080 | Denegar |
| Prometheus seleccionado → api TCP 9090 | Permitir |
| Otro Pod del espacio de nombres de supervisión → api TCP 9090 | Denegar |
| carga de trabajo → Pod de CoreDNS coincidente UDP/TCP 53 | Permitir, sujeto a los controles del lado del resolver |
| Destino externo arbitrario | Denegar, salvo que se añada una regla explícita de tráfico de salida |

Las políticas son aditivas y no tienen orden. Otra regla amplia de permiso puede ampliar el resultado; la denegación predeterminada no la anula. Prueba el conjunto completo de políticas instalado, la resolución DNS y las conexiones nuevas permitidas/denegadas en el CNI de destino. Las conexiones establecidas, el tráfico hostNetwork/de nodo y el comportamiento de NAT tienen limitaciones específicas de cada implementación; una NetworkPolicy sencilla no constituye un límite universal para IMDS ni para el firewall del host.

Para los servicios externos, limita el tráfico a las direcciones/puertos de destino reales o utiliza los controles compatibles con DNS de la implementación elegida. Permitir cualquier destino en el puerto 443 o todo el rango 10.0.0.0/8 no es una lista de servicios permitidos. Un manifiesto arbitrario de reemplazo de Calico/Cilium o una marca parcial de reemplazo de kube-proxy no es una forma segura de habilitar políticas en una red de EKS existente.

Los 18 casos sintéticos de selector/puerto del documento de origen emparejado se comprobaron localmente; no se ejecutó ninguna prueba de paquetes/CNI. Referencia: [Comportamiento de NetworkPolicy en Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

</details>

### 2. ¿Qué enfoque combina controles complementarios para la seguridad de imágenes de contenedor en EKS?

- A) Depender únicamente de la inspección manual de imágenes
- B) Suponer que todas las imágenes oficiales están libres de vulnerabilidades
- C) Combinar análisis, firma/verificación y controles de admisión
- D) Depender únicamente del antivirus dentro del contenedor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Combinar análisis, firma/verificación y controles de admisión**

**Explicación:**

Un escáner identifica los problemas que cubren sus reglas y su base de datos de vulnerabilidades; no demuestra que no haya puertas traseras ni que no vayan a aparecer vulnerabilidades futuras. Una firma demuestra la integridad y una relación de identidad conforme a la política de confianza configurada, no que el software firmado sea seguro. Los controles de admisión aplican la política de despliegue seleccionada. Utiliza imágenes base mínimas mantenidas, vuelve a compilarlas para aplicar parches, lleva un registro de las excepciones y elige el modo de análisis adecuado de ECR básico/mejorado u otro.

**AWS Signer y Notation:** la plataforma de firma de contenedores es `Notation-OCI-SHA384-ECDSA`. Usa el complemento AWS Signer de Notation para firmar una imagen ya enviada, por digest. Una plataforma `Aws::ECR::Image` o `start-signing-job --source-image` no forman parte del flujo de trabajo compatible. La AWS CLI revisada rechaza esa opción.

La firma administrada actual de ECR también es una alternativa compatible activada por el envío, con reglas de firma del registro. Si la eliges, configura el perfil/permisos correctos y espera a que aparezca el estado real de la firma antes de promover la imagen. No supongas que la existencia de una imagen enviada demuestra que la firma asíncrona se completó.

**Configuración de confianza:** prepara una instalación verificada de Notation/complemento Signer, el almacén de confianza raíz de AWS Signer correspondiente a la partición correcta y una política de confianza estricta revisada. Este ejemplo para una región comercial limita la confianza a un repositorio y un perfil aprobados. Sustituye de forma coherente cada cuenta/región/repositorio/perfil; no confíes en cualquier firmante solo porque su certificado encadene con la raíz de AWS.

```json
{
  "version": "1.0",
  "trustPolicies": [
    {
      "name": "reviewed-eks-repository",
      "registryScopes": [
        "123456789012.dkr.ecr.us-west-2.amazonaws.com/team/app"
      ],
      "signatureVerification": {
        "level": "strict"
      },
      "trustStores": [
        "signingAuthority:aws-signer-ts"
      ],
      "trustedIdentities": [
        "arn:aws:signer:us-west-2:123456789012:/signing-profiles/eks_images"
      ]
    }
  ]
}
```

Importa esa política en la configuración de Notation propiedad del entorno de compilación con `notation policy import notation-trust-policy.json`. Revisa cualquier política existente antes de reemplazarla; no sobrescribas la configuración de confianza compartida de un desarrollador con un script no revisado. El rol de compilación necesita operaciones de extracción/envío de ECR limitadas al repositorio, autenticación de ECR y los permisos SignPayload/GetRevocationStatus necesarios. La creación del perfil de firma es una responsabilidad de aprovisionamiento independiente; la compilación no necesita PutSigningProfile para utilizar un perfil aprobado existente.

**Ejemplo de CodeBuild:** esto es un buildspec, no una definición de CodePipeline. Requiere una imagen de compilación Linux propia con Bash, Python, Docker/acceso al daemon, AWS CLI, Trivy, Notation y el complemento AWS Signer ya instalados y con sus versiones fijadas. Configura por separado el privilegio de ejecución requerido del proyecto, el acceso a la red, las bases de datos del escáner, el rol de IAM, el almacén/política de confianza y el repositorio ECR existente. El Dockerfile y el código fuente son entradas de confianza para ese rol de compilación. Este ejemplo usa un commit Git resuelto y una cuenta/región comercial de AWS; no implementa un diseño de firma entre cuentas.

```yaml
version: 0.2
env:
  shell: bash
phases:
  build:
    commands:
      - |
        set -euo pipefail
        umask 077
        # Reserve this generated artifact name; remove stale output before any build step.
        rm -f -- verified-image.json
        : "${AWS_REGION:?Set the commercial AWS Region}"
        : "${AWS_ACCOUNT_ID:?Set the expected ECR/signing account ID}"
        : "${ECR_REPOSITORY:?Set the complete repository name, including any path}"
        : "${SIGNING_PROFILE_ARN:?Set the approved AWS Signer profile ARN}"
        : "${CODEBUILD_RESOLVED_SOURCE_VERSION:?This example requires a resolved Git commit}"
        python3 - <<'PY'
        import os, re
        checks = {
            "AWS_ACCOUNT_ID": r"[0-9]{12}",
            "AWS_REGION": r"[a-z0-9-]+",
            "ECR_REPOSITORY": r"[a-z0-9]+(?:[._/-][a-z0-9]+)*",
            "CODEBUILD_RESOLVED_SOURCE_VERSION": r"(?:[0-9a-f]{40}|[0-9a-f]{64})",
        }
        for name, pattern in checks.items():
            if not re.fullmatch(pattern, os.environ[name]):
                raise SystemExit("Invalid example input: " + name)
        prefix = f"arn:aws:signer:{os.environ['AWS_REGION']}:{os.environ['AWS_ACCOUNT_ID']}:/signing-profiles/"
        profile = os.environ["SIGNING_PROFILE_ARN"]
        if not profile.startswith(prefix) or not re.fullmatch(r"[A-Za-z0-9_/]+", profile[len(prefix):]):
            raise SystemExit("Use an approved signing profile in this example's account/Region")
        PY
        REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        IMAGE_URI="${REGISTRY}/${ECR_REPOSITORY}:${CODEBUILD_RESOLVED_SOURCE_VERSION}"
        ACTUAL_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
        if [[ "$ACTUAL_ACCOUNT" != "$AWS_ACCOUNT_ID" ]]; then
          printf '%s\n' 'Unexpected build-role account' >&2
          exit 1
        fi
        aws ecr get-login-password --region "$AWS_REGION" |
          docker login --username AWS --password-stdin "$REGISTRY"
        docker build --tag "$IMAGE_URI" .
        trivy image --image-src docker --scanners vuln --severity HIGH,CRITICAL \
          --exit-code 1 --no-progress "$IMAGE_URI"
        docker push "$IMAGE_URI"
        DIGESTS_JSON=$(docker image inspect --format '{{json .RepoDigests}}' "$IMAGE_URI")
        IMAGE_REFERENCE=$(python3 - "$REGISTRY/$ECR_REPOSITORY" "$DIGESTS_JSON" <<'PY'
        import json, re, sys
        digests = json.loads(sys.argv[2])
        if not isinstance(digests, list):
            raise SystemExit("Expected Docker RepoDigests array")
        pattern = re.escape(sys.argv[1]) + r"@sha256:[0-9a-f]{64}"
        matching = {d for d in digests if isinstance(d, str) and re.fullmatch(pattern, d)}
        if len(matching) != 1:
            raise SystemExit("Expected exactly one pushed digest for this repository")
        print(matching.pop())
        PY
        )
        notation sign --plugin com.amazonaws.signer.notation.plugin \
          --id "$SIGNING_PROFILE_ARN" "$IMAGE_REFERENCE"
        notation verify "$IMAGE_REFERENCE"
        python3 - "$IMAGE_REFERENCE" "$CODEBUILD_RESOLVED_SOURCE_VERSION" <<'PY'
        import json, sys
        with open("verified-image.json", "x") as stream:
            json.dump({"image": sys.argv[1], "sourceCommit": sys.argv[2]}, stream)
            stream.write("\n")
        PY
artifacts:
  files:
    - verified-image.json
```

Configura `AWS_ACCOUNT_ID`, `AWS_REGION`, `ECR_REPOSITORY` (por ejemplo, `team/app`) y `SIGNING_PROFILE_ARN` mediante la configuración revisada del proyecto. El comando se autentica en el nombre de host del registro, conserva las rutas de repositorio anidadas, analiza la imagen compilada localmente antes del envío y selecciona el RepoDigest enviado que coincide, en vez de una entrada arbitraria de la lista o una etiqueta mutable. En este caso, Trivy bloquea la compilación ante hallazgos de vulnerabilidades HIGH/CRITICAL; añade otras comprobaciones diseñadas explícitamente para secretos, configuración y procedencia.

Todos los pasos de promoción están en un único bloque de compilación de Bash con `set -euo pipefail`. Si falla el inicio de sesión, la compilación, el análisis, el envío, la firma o la verificación, el proceso se detiene antes de escribir un nuevo artefacto. CodeBuild puede ejecutar post_build después de una compilación fallida, por lo que un paso de envío/firma no protegido en post_build no es seguro. La ruta reservada para el artefacto se limpia primero para evitar reutilizar una salida anterior. El despliegue posterior también debe exigir una compilación correcta y validar el artefacto; el archivo JSON por sí solo no constituye una autorización ni una atestación firmada.

`verified-image.json` contiene la referencia exacta al digest para un consumidor de despliegues/GitOps de EKS. No es `imagedefinitions.json` de ECS y no despliega nada por sí solo. El éxito de la firma/verificación sigue dependiendo del acceso real al registro, la confianza, las comprobaciones de revocación y la disponibilidad de AWS Signer.

**Admisión:** un verificador de firmas de producción debe comprender la firma Notation/Signer elegida y la política de confianza. AWS documenta Gatekeeper con Ratify y Kyverno con una integración de AWS Signer/Notation. Instalar un motor de políticas genérico, una restricción de Gatekeeper sin su ConstraintTemplate o un campo de clave pública para un esquema de firma diferente no establece esa integración. Valida perfiles de confianza/no confianza, imágenes sin firmar, discrepancias de digest, firmas revocadas/caducadas, interrupciones del verificador y la política de fallo de admisión antes de aplicar la política.

La siguiente regla independiente de Kyverno 1.19.1 solo restringe la **sintaxis de referencia de imagen y el repositorio** en security-demo. Comprueba contenedores normales, de inicialización y efímeros. **No** afirma verificar una firma:

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: demo-approved-image-reference
spec:
  validationActions:
  - Deny
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      resources:
      - pods
      - pods/ephemeralcontainers
      operations:
      - CREATE
      - UPDATE
      scope: Namespaced
  matchConditions:
  - name: demo-namespace
    expression: has(object.metadata.namespace) && object.metadata.namespace == 'security-demo'
  validations:
  - expression: object.spec.containers.all(c, c.image.matches('^123456789012[.]dkr[.]ecr[.]us-west-2[.]amazonaws[.]com/team/app@sha256:[0-9a-f]{64}$'))
      && (!has(object.spec.initContainers) || object.spec.initContainers.all(c, c.image.matches('^123456789012[.]dkr[.]ecr[.]us-west-2[.]amazonaws[.]com/team/app@sha256:[0-9a-f]{64}$')))
      && (!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c, c.image.matches('^123456789012[.]dkr[.]ecr[.]us-west-2[.]amazonaws[.]com/team/app@sha256:[0-9a-f]{64}$')))
    message: Use a sha256 digest from the approved team/app repository in security-demo.
```

Validación: 20 casos simulados de fallo/orden/artefactos de la canalización y nueve casos reales de políticas de cadenas con la CLI de Kyverno. Se comprobaron el buildspec/Bash/Python/JSON y la CRD publicada de la política. No se compiló, analizó ni envió ninguna imagen, no se produjo ni verificó ninguna firma real de AWS y no se desplegó ningún webhook de admisión. Este es un flujo de trabajo didáctico revisado con supuestos explícitos de entorno, no un flujo de trabajo cuya preparación para producción haya sido probada.

Referencias: [Firma de Signer](https://docs.aws.amazon.com/signer/latest/developerguide/image-signing-steps.html), [Verificación de Signer](https://docs.aws.amazon.com/signer/latest/developerguide/image-verification.html), [Firma administrada de ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/managed-signing.html), [Verificación de admisión de EKS](https://docs.aws.amazon.com/eks/latest/userguide/image-verification.html), [Buildspec de CodeBuild](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html), [Marcas de imagen de Trivy](https://trivy.dev/docs/latest/references/configuration/cli/trivy_image/).

</details>

### 3. ¿Qué enfoque aplica una línea base de seguridad de Pod coherente y actual en EKS?

- A) Deshabilitar únicamente el modo privilegiado
- B) Usar perfiles PSS versionados mediante PSA, con políticas de admisión revisadas cuando sea necesario
- C) Establecer únicamente un UID distinto de root
- D) Hacer que únicamente el sistema de archivos raíz sea de solo lectura

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar perfiles PSS versionados mediante PSA, con políticas de admisión revisadas cuando sea necesario**

**Explicación:**

Pod Security Standards define los perfiles Privileged, Baseline y Restricted. Pod Security Admission aplica los perfiles seleccionados para cada espacio de nombres. PSA es estable desde Kubernetes 1.25; PodSecurityPolicy quedó obsoleto en 1.21 y **se eliminó en 1.25**. Un clúster actual no puede desplegar esa API eliminada. Las políticas de Kyverno/Gatekeeper son recursos independientes, aunque un ejemplo antiguo use «PSP» en el nombre de una restricción.

Una demostración aislada de Linux con un perfil v1.36 revisado es:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
---
apiVersion: v1
kind: Pod
metadata:
  name: security-context-demo
  namespace: security-demo
spec:
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: busybox:1.38.0
    command:
    - sh
    - -c
    args:
    - id && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        cpu: 100m
        memory: 64Mi
```

enforce del espacio de nombres se aplica a la admisión de Pod. Audit/warn pueden informar de infracciones en las plantillas de los controladores, pero que la aplicación de un Deployment/Job se complete correctamente no demuestra que sus Pods superen la aplicación de políticas. Cambiar las etiquetas no expulsa de forma retroactiva los Pods existentes. Elige una versión de política adecuada para el clúster real y revisa las cargas de trabajo existentes antes de aplicarla.

runAsNonRoot/runAsUser y seccomp son distintos de allowPrivilegeEscalation y capabilities. fsGroup es un ajuste de propiedad de volúmenes a nivel de Pod, no una capacidad de contenedor. Un sistema de archivos raíz de solo lectura es una medida de refuerzo útil si la aplicación es compatible, pero no es un requisito universal de PSS Restricted y no hace que los PVC montados sean de solo lectura. Las aplicaciones reales necesitan UID/GID compatibles y rutas de escritura para archivos temporales/caché/sockets; añadir estos campos a una imagen genérica de nginx orientada a root no hace que funcione.

**Regla de admisión adicional y acotada:** esta ValidatingPolicy de Kyverno 1.19.1 comprueba todos los contenedores normales, de inicialización y efímeros en security-demo. Se acepta que privileged no esté presente, como si fuera false; true se deniega. Usa la API de política v1 actual, en lugar de un manifiesto de instalación obsoleto:

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: demo-disallow-privileged
spec:
  validationActions:
  - Deny
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      resources:
      - pods
      - pods/ephemeralcontainers
      operations:
      - CREATE
      - UPDATE
      scope: Namespaced
  matchConditions:
  - name: demo-namespace
    expression: has(object.metadata.namespace) && object.metadata.namespace == 'security-demo'
  validations:
  - expression: object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged)
      || c.securityContext.privileged == false) && (!has(object.spec.initContainers)
      || object.spec.initContainers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged)
      || c.securityContext.privileged == false)) && (!has(object.spec.ephemeralContainers)
      || object.spec.ephemeralContainers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged)
      || c.securityContext.privileged == false))
    message: Privileged containers, including init and ephemeral containers, are not
      allowed in security-demo.
```

Esta única regla no sustituye todo el perfil PSS ni la verificación de imágenes. Mantén los agentes CSI/de supervisión privilegiados y las excepciones deliberadas bajo el control del propietario de la plataforma; no apliques una política de demostración de forma general a kube-system. Una alternativa con Gatekeeper necesita su ConstraintTemplate real, la restricción correspondiente y un comportamiento validado.

El manifiesto/esquema y los seis casos reales de la CLI de Kyverno cubren los casos de campo omitido/false, contenedores privilegiados normales/de inicialización/efímeros y otro espacio de nombres. La prueba de contenedores efímeros usa un objeto UPDATE sintético, no la creación de un Pod. No se ejecutó ningún webhook de admisión activo ni se desplegó ningún Pod.

Referencias: [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/), [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/).

</details>

### 4. ¿Qué enfoque proporciona pruebas de seguridad complementarias para una carga de trabajo de EKS?

- A) Usar únicamente revisiones manuales ocasionales
- B) Usar únicamente comprobaciones de AWS Config
- C) Usar únicamente GuardDuty
- D) Combinar hallazgos de postura, registros de auditoría, cobertura de ejecución y una ruta de respuesta verificada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Combinar hallazgos de postura, registros de auditoría, cobertura de ejecución y una ruta de respuesta verificada**

**Explicación:**

| Evidencia/control | Qué aporta y qué no demuestra |
|---|---|
| Security Hub CSPM / AWS Config | Controles de configuración compatibles y hallazgos; no constituyen una certificación completa de Kubernetes ni normativa |
| GuardDuty EKS Protection | Análisis de amenazas basado en auditoría de Kubernetes mediante un flujo independiente |
| GuardDuty Runtime Monitoring | Eventos de ejecución basados en agentes en nodos compatibles; el estado habilitado por sí solo no demuestra cobertura |
| CloudTrail | Actividad de la API de AWS; no sustituye la auditoría de Kubernetes ni los registros de acceso a datos de la aplicación |
| Registros de auditoría de Kubernetes | Solicitudes seleccionadas por la política/nivel de auditoría, no todas las acciones/cargas de trabajo |
| CloudWatch / encaminamiento de incidentes | Análisis de registros y entrega a los operadores; deben verificarse la entrega, la retención y la respuesta |

El estándar FSBP de Security Hub CSPM no es el CIS Kubernetes Benchmark. Los controles de CIS AWS Foundations compatibles tampoco constituyen una auditoría completa de CIS Kubernetes. Registra el benchmark/la versión aplicable, las comprobaciones manuales, las excepciones de servicios administrados y las pruebas requeridas para las obligaciones reales de la carga de trabajo.

Utiliza la responsabilidad existente de la organización/región para los detectores, los estándares CSPM, los grabadores de Config y CloudTrail. No crees otro detector regional, no sobrescribas la configuración centralizada ni inicies un trail sin tener preparado su bucket policy, cifrado, selectores de eventos y retención. Los eventos de datos de CloudTrail son independientes de la cobertura predeterminada de eventos de administración. En esta revisión no se aprovisionaron recursos de supervisión a nivel de cuenta.

**Comprobaciones específicas de EKS:** habilita y confirma los tipos de registros del plano de control previstos, la finalización de las actualizaciones y la llegada de registros, tal como se muestra en el capítulo de origen. Tanto `eks-cluster-logging-enabled` (todos los tipos, periódica) como `eks-cluster-log-enabled` (tipos seleccionados opcionales, cambios de configuración) son reglas de Config válidas. Mantén el parámetro `oldestVersionSupported` en lugar de dar por supuesto que hay un catálogo automático de versiones actuales. Un hallazgo explícito de control de encryptionConfig no significa que los datos de la API de EKS 1.28+ carezcan de cifrado de sobre predeterminado.

El análisis de auditoría de GuardDuty no requiere que exportes por separado los registros de auditoría de CloudWatch. Runtime Monitoring necesita el agente de seguridad/punto de conexión de datos compatible y cobertura real; la compatibilidad actual de EKS incluye EC2 y Auto Mode, pero no Fargate ni Hybrid Nodes. Usa la característica actual RUNTIME_MONITORING y revisa la migración de EKS_RUNTIME_MONITORING heredada. No confundas EKS_AUDIT_LOGS con la supervisión de ejecución.

**Ejemplo de enrutamiento de eventos de CSPM:** guarda esto como `security-event-pattern.json`. Selecciona hallazgos ASFF activos de gravedad HIGH/CRITICAL con estado de flujo de trabajo NEW/NOTIFIED. Intencionadamente, no coincide con el esquema de eventos OCSF distinto de `Findings Imported V2`:

```json
{
  "source": [
    "aws.securityhub"
  ],
  "detail-type": [
    "Security Hub Findings - Imported"
  ],
  "detail": {
    "findings": {
      "Severity": {
        "Label": [
          "HIGH",
          "CRITICAL"
        ]
      },
      "Workflow": {
        "Status": [
          "NEW",
          "NOTIFIED"
        ]
      },
      "RecordState": [
        "ACTIVE"
      ]
    }
  }
}
```

Este evento sintético solo sirve para comprobar el patrón; no es un hallazgo real ni una carga completa de importación ASFF. Guárdalo como `synthetic-security-event.json`:

```json
{
  "version": "0",
  "id": "00000000-0000-0000-0000-000000000001",
  "account": "123456789012",
  "region": "us-west-2",
  "time": "2026-09-11T00:00:00Z",
  "source": "aws.securityhub",
  "detail-type": "Security Hub Findings - Imported",
  "resources": [],
  "detail": {
    "findings": [
      {
        "Id": "synthetic-example-not-a-real-finding",
        "Severity": {
          "Label": "HIGH"
        },
        "Workflow": {
          "Status": "NEW"
        },
        "RecordState": "ACTIVE"
      }
    ]
  }
}
```

En una prueba de AWS autorizada, `aws events test-event-pattern --event-pattern file://security-event-pattern.json --event file://synthetic-security-event.json --region us-west-2` debería coincidir. Prueba también gravedad LOW, flujos de trabajo RESOLVED/SUPPRESSED, estado ARCHIVED, campos ausentes y el tipo de evento V2; no deberían coincidir con este patrón. Esta revisión comprobó el esquema JSON/de origen, no el motor de coincidencias del servicio EventBridge ni la entrega de eventos en vivo.

Una configuración de destino puede usar un **rol de ejecución existente de EventBridge revisado**, con permiso para publicar en el tema SNS propio, como admite la guía actual de EventBridge. Después de sustituir los ARN propios, guárdalo como `security-event-targets.json`:

```json
[
  {
    "Id": "SecurityAlerts",
    "Arn": "arn:aws:sns:us-west-2:123456789012:eks-security-alerts",
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSecurityAlerts"
  }
]
```

El rol necesita la relación de confianza correcta de EventBridge y permiso sns:Publish con privilegios mínimos; inspecciona las políticas aplicables del tema/clave y cualquier denegación explícita. Como alternativa, un destino sin rol de ejecución necesita la ruta de permisos basada en recursos compatible. El JSON de destino por sí solo no concede permisos ni crea la regla, el tema, el rol o la suscripción.

Antes de usar `aws events put-targets --rule eks-security-alerts --targets file://security-event-targets.json --region us-west-2`, inspecciona la propiedad de las reglas/destinos existentes. Comprueba FailedEntryCount y FailedEntries, no solo el estado de salida del comando. Confirma las suscripciones SNS, los permisos de cifrado, el comportamiento de reintentos/carta muerta y una prueba controlada de entrega integral. Durante esta auditoría no se envió ninguna notificación.

**Investigación de auditoría:** en el grupo de registros real de EKS, este ejemplo de Logs Insights presupone la detección de campos JSON para los registros de auditoría de Kubernetes. Se centra en las solicitudes de modificación de RBAC; inspecciona responseStatus.code para distinguir las solicitudes correctas de las rechazadas:

```text
fields @timestamp, verb, user.username, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter verb in ["create", "update", "patch", "delete", "deletecollection"]
| filter objectRef.resource in ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
| sort @timestamp desc
| limit 100
```

Verifica los campos de un registro de muestra y el nombre del flujo antes de confiar en la consulta. Conserva las pruebas pertinentes, define la titularidad/gravedad/escalamiento y prueba el proceso de respuesta. Los paneles de hallazgos y los servicios habilitados no demuestran que se haya completado la corrección ni que se haya cumplido una obligación normativa.

Referencias: [Estándares de CSPM](https://docs.aws.amazon.com/securityhub/latest/userguide/standards-view-manage.html), [Eventos ASFF](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-cwe-event-formats.html), [Eventos V2](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-v2-cwe-event-formats.html), [Permisos de destino de EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html), [Registros de auditoría de EKS](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html).

</details>

### 5. Para credenciales de aplicaciones que requieren acceso a AWS gobernado centralmente y gestión del ciclo de vida, ¿qué enfoque es adecuado?

- A) Almacenar valores sin un plan de acceso, rotación o recarga
- B) Tratar las variables de entorno como un mecanismo de cifrado
- C) Usar un backend adecuado de secretos/parámetros de AWS con identidad acotada y un diseño explícito de entrega/ciclo de vida
- D) Codificar las credenciales de producción directamente en la imagen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar un backend adecuado de secretos/parámetros de AWS con identidad acotada y un diseño explícito de entrega/ciclo de vida**

**Explicación:**

Secrets Manager y Parameter Store pueden centralizar los controles de acceso y la auditoría de AWS, pero un backend externo no es automáticamente seguro sin identidad de carga de trabajo, privilegios mínimos y controles de entrega/recarga. Secrets Manager admite rotación configurada para las credenciales compatibles; Parameter Store no ofrece el mismo flujo de trabajo integrado de rotación de credenciales. El cifrado KMS y el versionado de un parámetro SecureString son distintos de cambiar la credencial en la base de datos/servicio de destino.

EKS 1.28+ ya cifra todos los datos de la API de Kubernetes con el cifrado de sobre KMS v2 predeterminado. La codificación Base64 en un manifiesto Secret sigue siendo solo codificación, y el acceso a la API/Pod puede exponer el valor. Las variables de entorno son un mecanismo de entrega, no de cifrado; los entornos de procesos existentes no se actualizan cuando cambia un Secret.

**Elige cuidadosamente la titularidad y la entrega:** ESO escribe un Secret de Kubernetes. ASCP con Secrets Store CSI Driver monta archivos y puede sincronizar opcionalmente un Secret de Kubernetes. No permitas que ambos controladores gestionen el mismo Secret de destino. Un diseño de CSI solo con archivos sigue necesitando controles de acceso a la carga de trabajo/nodo; la sincronización opcional también introduce una copia del valor en la API de Kubernetes.

**Ejemplo de ASCP:** esta es una instalación nueva, propiedad del equipo, para Linux EC2 en el ejemplo revisado de EKS 1.36; no es un despliegue en un clúster existente desconocido. Primero inspecciona la propiedad de los lanzamientos/CSIDriver existentes, la compatibilidad de los nodos, la admisión de agentes de plataforma privilegiados, el acceso a la red y la programación. Fargate no puede ejecutar el DaemonSet de nodo CSI. El uso de Hybrid/Auto Mode exige los requisitos previos actuales de proveedor/nodo; el renderizado local siguiente no lo verifica.

Usa estos ajustes de `secrets-csi-values.yaml` para un controlador CSI 1.6.1 gestionado por separado. Configuran explícitamente las dos audiencias del token de AWS, la sincronización opcional de Secret y la rotación:

```yaml
tokenRequests:
- audience: sts.amazonaws.com
- audience: pods.eks.amazonaws.com
syncSecret:
  enabled: true
enableSecretRotation: true
rotationPollInterval: 2m
```

El chart ASCP 3.1.3 suele incluir el controlador como dependencia y configura sus audiencias de token. Como este ejemplo instala el controlador por separado, guarda lo siguiente como `ascp-values.yaml` para evitar instalar un segundo controlador:

```yaml
secrets-store-csi-driver:
  install: false
```



```bash
helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm repo add aws-secrets-manager https://aws.github.io/secrets-store-csi-driver-provider-aws
helm repo update secrets-store-csi-driver aws-secrets-manager
helm install csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver \
  --version 1.6.1 --namespace kube-system -f secrets-csi-values.yaml --wait --timeout 5m
helm install secrets-provider-aws aws-secrets-manager/secrets-store-csi-driver-provider-aws \
  --version 3.1.3 --namespace kube-system -f ascp-values.yaml --wait --timeout 5m
```

Las instalaciones existentes necesitan el procedimiento de actualización de versión/CRD de su propietario; no ejecutes estos comandos de instalación nueva ni un `helm upgrade` parcial sobre valores no relacionados. Fijar versiones del chart y renderizarlo correctamente no demuestra la compatibilidad del complemento de nodo, la conectividad ni el acceso a secretos.

Prepara un secreto JSON propio de Secrets Manager con campos username/password y un rol `ASCPSecretReader` limitado a ese secreto exacto, además del permiso de descifrado de la clave del cliente que corresponda, si hace falta. Esta relación de confianza de IRSA utiliza el sujeto preciso de ServiceAccount; sustituye de forma coherente el emisor/proveedor OIDC completo y la cuenta:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLEOIDCID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLEOIDCID:aud": "sts.amazonaws.com",
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLEOIDCID:sub": "system:serviceaccount:security-secrets-demo:ascp-reader"
        }
      }
    }
  ]
}
```

El Namespace, el ServiceAccount, el SecretProviderClass y el Pod siguientes conforman el ejemplo de entrega mediante archivos. Selecciona la versión de PSS adecuada para el clúster real. JMESPath extrae campos en alias; `secretObjects.data.objectName` especifica esos alias montados. No se admite un campo `property` dentro de secretObjects.data. Los permisos 0444 hacen que los archivos sean legibles para este proceso de demostración que no se ejecuta como root; limita quién puede montar/crear Pods y elige UID/GID y permisos de archivo compatibles con una aplicación real.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-secrets-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ascp-reader
  namespace: security-secrets-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ASCPSecretReader
automountServiceAccountToken: false
---
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: db-secrets-files
  namespace: security-secrets-demo
spec:
  provider: aws
  parameters:
    region: us-west-2
    usePodIdentity: 'false'
    objects: |
      - objectName: arn:aws:secretsmanager:us-west-2:123456789012:secret:training/db-credentials-ABC123
        objectType: secretsmanager
        objectAlias: credentials
        filePermission: '0444'
        jmesPath:
        - path: username
          objectAlias: db_username
        - path: password
          objectAlias: db_password
  secretObjects:
  - secretName: csi-db-credentials
    type: Opaque
    data:
    - objectName: db_username
      key: username
    - objectName: db_password
      key: password
---
apiVersion: v1
kind: Pod
metadata:
  name: secret-file-check
  namespace: security-secrets-demo
spec:
  serviceAccountName: ascp-reader
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: check
    image: busybox:1.37
    command:
    - sh
    - -c
    - test -s /mnt/secrets/db_username && test -s /mnt/secrets/db_password && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    volumeMounts:
    - name: secrets
      mountPath: /mnt/secrets
      readOnly: true
  volumes:
  - name: secrets
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: db-secrets-files
```

El Pod comprueba que los archivos existan sin imprimir su contenido. `automountServiceAccountToken: false` deshabilita el montaje automático del token de la API de Kubernetes, no las solicitudes de token explícitas del controlador CSI. Para usar Pod Identity en lugar de este ejemplo de IRSA, utiliza un agente/asociación compatible para el ServiceAccount de la carga de trabajo y `usePodIdentity: "true"`; no supongas que una anotación de IRSA proporciona esa asociación.

El Secret opcional csi-db-credentials solo se sincroniza después de que un Pod monte el volumen. Su ciclo de vida sigue el de los Pods consumidores y puede eliminarse cuando se borran todos los consumidores. Crear un SecretProviderClass por sí solo no genera un Secret de forma independiente. Inspecciona SecretProviderClassPodStatus y los eventos del controlador/nodo sin volcar los valores.

Para Parameter Store, el valor objects puede contener en su lugar la siguiente entrada, con el permiso de lectura SSM requerido por el proveedor para el parámetro propio y el acceso KMS adecuado para SecureString. Este es un fragmento de objects, no un SecretProviderClass completo:

```yaml
- objectName: /training/app/config
  objectType: ssmparameter
  objectAlias: app_config
  filePermission: "0444"
```

**Alternativa ESO:** usa el rol/relación de confianza IRSA EKSSecretReader preparado en el capítulo de origen para el ServiceAccount eso-reader exacto. Con ESO 2.10.0 y sus CRD v1 instaladas bajo la responsabilidad de su propietario, lo siguiente escribe en un destino distinto, eso-db-credentials. El ARN del backend, el espacio de nombres, el rol y las propiedades JSON deben corresponder al secreto preparado real:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-secrets-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: eso-reader
  namespace: security-secrets-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/EKSSecretReader
automountServiceAccountToken: false
---
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: aws-secretsmanager
  namespace: security-secrets-demo
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: eso-reader
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: db-credentials
  namespace: security-secrets-demo
spec:
  refreshPolicy: Periodic
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: eso-db-credentials
    creationPolicy: Owner
    deletionPolicy: Retain
  data:
    - secretKey: username
      remoteRef:
        key: arn:aws:secretsmanager:us-west-2:123456789012:secret:training/db-credentials-ABC123
        property: username
    - secretKey: password
      remoteRef:
        key: arn:aws:secretsmanager:us-west-2:123456789012:secret:training/db-credentials-ABC123
        property: password
```

Aquí Owner vincula el Secret de destino al ExternalSecret; al eliminar el propietario puede activarse la recolección de basura. Retain se refiere a la desaparición del backend, no a la inmunidad frente a la eliminación del propietario. El método JWT de serviceAccountRef de ESO es IRSA. Pod Identity del Pod del controlador es un diseño distinto: asocia el ServiceAccount del controlador y omite el bloque auth del almacén; ESO no puede usar serviceAccountRef para suplantar otra cuenta asociada a Pod Identity.

**Rotación y recarga:** CSI 1.6+ utiliza llamadas RequiresRepublish de kubelet para la rotación. requiresRepublish por sí solo no habilita la rotación: también se necesita la marca enableSecretRotation del controlador. El rotationPollInterval de dos minutos en este caso es una duración mínima de caché, no una garantía de actualización integral en dos minutos; el tiempo real depende de la republicación de kubelet. El intervalo de actualización de ESO es otro calendario de reconciliación independiente. Las aplicaciones deben volver a abrir/vigilar los archivos actualizados o realizar un despliegue controlado; los montajes subPath y las variables de entorno existentes no se actualizan automáticamente.

rotate-secret de Secrets Manager tiene la rotación inmediata como opción predeterminada. Incluso `--no-rotate-immediately` puede probar una función Lambda de rotación y crear/eliminar AWSPENDING, mientras que puede seguir vigente un calendario anterior basado en intervalos/días. No es una comprobación inocua limitada al calendario ni de solo lectura. Revisa los cambios de credenciales de destino, la validez simultánea, la recarga de la aplicación y la reversión antes de invocar la rotación.

**Ejemplo de Terraform sin valores secretos:** Terraform sensitive solo suprime la salida seleccionada que se muestra; los valores normales de secret_string/random_password pueden seguir almacenándose en el estado. Lo siguiente solo administra metadatos del secreto, usando una clave KMS aprobada existente. Para un secreto que ya exista, reconcilia e impórtalo con su propietario antes de administrarlo en esta configuración:

```hcl
terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.1"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-west-2"
}

variable "kms_key_arn" {
  type        = string
  description = "Existing approved Secrets Manager encryption key ARN in this Region"
}

provider "aws" {
  region = var.aws_region
}

resource "aws_secretsmanager_secret" "credentials" {
  name                    = "training/db-credentials"
  kms_key_id              = var.kms_key_arn
  recovery_window_in_days = 30
  lifecycle {
    prevent_destroy = true
  }
}

output "secret_arn" {
  value = aws_secretsmanager_secret.credentials.arn
}
```

Esto no crea ninguna versión/valor del secreto ni habilita la rotación. Proporciona el valor inicial mediante el proceso aprobado de entrada de secretos, no con una cadena de Terraform codificada directamente ni como argumento de comando en texto sin cifrar. Protege el estado y los planes aunque solo se esperen metadatos. prevent_destroy es una protección de configuración de Terraform, no una protección irreversible del servicio; quitar el recurso de la configuración o actuar fuera de Terraform cambia el contexto de protección.

La validación cubrió Kubernetes nativo y las CRD publicadas de SecretProviderClass/ESO, las sumas de comprobación publicadas de los charts, 22 objetos CSI/ASCP renderizados y la proyección real de datos sintéticos con JMESPath. Los campos creationTimestamp nulos generados se omitieron únicamente para la comprobación del esquema Swagger. Terraform fmt se ejecutó correctamente; no se ejecutó init/plan/apply. No se obtuvo, montó, sincronizó ni rotó ningún secreto de AWS, y no se probó la recarga de ninguna aplicación.

Referencias: [Configuración de ASCP](https://github.com/aws/secrets-store-csi-driver-provider-aws), [CSI 1.6.1](https://github.com/kubernetes-sigs/secrets-store-csi-driver/releases/tag/v1.6.1), [Sincronización de Secret de CSI](https://secrets-store-csi-driver.sigs.k8s.io/topics/sync-as-kubernetes-secret), [Rotación de CSI](https://secrets-store-csi-driver.sigs.k8s.io/topics/secret-auto-rotation), [Autenticación de ESO con AWS](https://github.com/external-secrets/external-secrets/blob/v2.10.0/docs/provider/aws-access.md), [Cifrado de sobre de EKS](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html), [Rotación de Secrets Manager](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/rotate-secret.html).

</details>
