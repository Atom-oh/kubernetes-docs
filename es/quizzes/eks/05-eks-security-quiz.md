# Cuestionario de seguridad de Amazon EKS

> **Última actualización**: 11 de septiembre de 2026

Este cuestionario evalúa tu comprensión de las funciones de seguridad, las prácticas recomendadas y las configuraciones de Amazon EKS.

## Descripción general del cuestionario
- Autenticación y autorización de EKS
- Seguridad de red
- Seguridad de contenedores
- Seguridad de los datos
- Cumplimiento y auditoría
- Prácticas recomendadas de seguridad

## Preguntas de opción múltiple

### 1. Para un usuario o rol de IAM, ¿qué configuración de EKS combina correctamente la autenticación de identidad y la autorización de Kubernetes?

- A) Usar únicamente permisos de administración de IAM
- B) Crear reglas de RBAC sin configurar la vía de autenticación de la identidad
- C) Configurar el acceso al clúster mediante IAM junto con el RBAC correspondiente o las políticas de acceso de EKS
- D) Usar únicamente restricciones de red para el punto de conexión de la API

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Configurar el acceso al clúster mediante IAM junto con el RBAC correspondiente o las políticas de acceso de EKS**

**Explicación:**

IAM autentica la identidad humana o de automatización prevista a través de la vía de acceso a EKS configurada. El RBAC de Kubernetes y las políticas de acceso de EKS autorizan las operaciones de Kubernetes; sus concesiones son aditivas. Las restricciones de red constituyen otra capa y no sustituyen la autorización. La autenticación de un Pod en Kubernetes normalmente usa el token de su ServiceAccount; IRSA/Pod Identity proporciona, en cambio, credenciales de AWS para la carga de trabajo.

El rol de servicio de un clúster de EKS y el rol de un desarrollador humano tienen propósitos distintos. Asociar AmazonEKSClusterPolicy al desarrollador no concede acceso a Kubernetes, y los permisos DescribeCluster/ListClusters o un archivo kubeconfig no conceden permisos sobre las cargas de trabajo.

**Implementación con alcance limitado:** un operador de plataforma autorizado prepara el espacio de nombres y el RBAC que aparecen a continuación para un rol de IAM de desarrollador existente y aprobado. El clúster ya debe admitir entradas de acceso. Conserva las asignaciones existentes de administradores y nodos, y revisa la migración del modo de autenticación; no sobrescribas aws-auth con un ConfigMap de ejemplo.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
```



```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set its Region}"
: "${DEVELOPER_ROLE_ARN:?Set a prepared IAM role ARN, not an STS session ARN}"
MODE=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.accessConfig.authenticationMode --output text)
case "$MODE" in
  API|API_AND_CONFIG_MAP) ;;
  *) echo "Access entries are not enabled; review the migration first"; exit 1 ;;
esac
aws eks list-access-entries --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --output json > security-access-entries.json
python3 - "$DEVELOPER_ROLE_ARN" <<'PY'
import json, sys
with open("security-access-entries.json") as stream:
    existing = json.load(stream)["accessEntries"]
if sys.argv[1] in existing:
    raise SystemExit("Entry already exists; inspect its groups/policies instead of overwriting")
PY
aws eks create-access-entry --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --principal-arn "$DEVELOPER_ROLE_ARN" --type STANDARD \
  --kubernetes-groups security-demo-developers
```



```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer
  namespace: security-demo
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - apps
  resources:
  - deployments
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
- apiGroups:
  - batch
  resources:
  - jobs
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer
  namespace: security-demo
subjects:
- kind: Group
  name: security-demo-developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

El nombre del grupo en la entrada de acceso debe coincidir con el sujeto del RoleBinding. Este rol permite únicamente las operaciones indicadas en security-demo; otras concesiones existentes pueden ampliar el acceso. Crear Deployments/Jobs puede usar indirectamente Secrets, PVC y ServiceAccounts de ese espacio de nombres, por lo que la ausencia de una regla directa para leer Secrets no constituye una frontera de seguridad entre inquilinos. Separa los inquilinos y limita el uso de identidades y recursos de las cargas de trabajo mediante controles de admisión y propiedad.

Un visor, revisado por separado, también puede usar una asociación AmazonEKSViewPolicy limitada a un espacio de nombres. Inspecciona las políticas de acceso existentes antes de añadirla; no revoca concesiones más amplias de RBAC ni otras políticas de acceso. `eks:namespaces` filtra las solicitudes de asociación de políticas de acceso, no las solicitudes generales de kubectl.

**Valida el inicio de sesión real:** el usuario que realiza la llamada debe poder descubrir el clúster y asumir el rol aprobado. Esto crea un kubeconfig temporal en lugar de reemplazar el contexto predeterminado:

```bash
set -euo pipefail
umask 077
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${DEVELOPER_ROLE_ARN:?Set the intended IAM role ARN}"
review_dir=$(mktemp -d "${TMPDIR:-/tmp}/eks-login-check.XXXXXXXX")
trap 'rm -rf -- "$review_dir"' EXIT
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --role-arn "$DEVELOPER_ROLE_ARN" --kubeconfig "$review_dir/config"
kubectl --kubeconfig "$review_dir/config" auth can-i list pods -n security-demo
kubectl --kubeconfig "$review_dir/config" auth can-i create jobs -n security-demo
kubectl --kubeconfig "$review_dir/config" auth can-i list pods -n another-team
```

Compara los resultados con las concesiones previstas e investiga cualquier permiso inesperado entre espacios de nombres. `--as` prueba la suplantación de identidad/RBAC y no demuestra que funcione la vía de acceso de IAM mediante políticas de acceso. Para este cuestionario no se ejecutó ninguna prueba real de inicio de sesión de IAM ni de autorización de Kubernetes; las pruebas de esquema y shell, junto con flujos simulados de entradas de acceso, constituyen la evidencia local.

Referencias: [Entradas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html), [Políticas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html), [RBAC de Kubernetes](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).

</details>

### 2. ¿Qué mecanismo de Kubernetes expresa reglas de tráfico de Pods basadas en etiquetas en una red de EKS que admite la aplicación de políticas?

- A) Solo grupos de seguridad de instancias
- B) Recursos NetworkPolicy con una implementación de red que aplique las políticas
- C) Solo políticas de puntos de conexión de VPC
- D) Solo comandos de firewall del host

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Recursos NetworkPolicy con una implementación de red que aplique las políticas**

**Explicación:**

NetworkPolicy selecciona Pods y permite tráfico mediante etiquetas y espacios de nombres de Kubernetes. Requiere una implementación de red que aplique las políticas. Los grupos de seguridad, incluidos los grupos de seguridad para Pods compatibles, siguen siendo controles útiles de AWS; no se limitan a instancias completas. Las políticas de puntos de conexión de VPC regulan el acceso a los servicios de AWS compatibles, no el tráfico arbitrario de Pods basado en etiquetas.

**Ejemplo completo de políticas:** estos manifiestos describen un espacio de nombres de demostración aislado; no instalan aplicaciones ni sustituyen el CNI. Presuponen nodos EC2 Linux estándar con un CNI compatible que aplique las políticas y las etiquetas habituales de Deployment/Pod de CoreDNS. Auto Mode o el DNS local al nodo requieren reglas para la ruta real del resolvedor. Si se restringe el tráfico entrante a CoreDNS, su propietario también debe permitir estas consultas.

Guárdalos y aplícalos a través del propietario del espacio de nombres. La denegación predeterminada aísla ambas direcciones; se permite explícitamente la salida del cliente y la entrada al destino para frontend → API y API → base de datos. DNS requiere UDP y TCP:

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

El par de monitoreo usa namespaceSelector **y** podSelector en un mismo par, por lo que solo selecciona los Pods de Prometheus coincidentes en security-monitoring-demo. Si ese cliente está aislado respecto a la salida, su conexión saliente también necesita permiso:

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
| Otro Pod del espacio de nombres de monitoreo → api TCP 9090 | Denegar |
| Carga de trabajo → Pod CoreDNS coincidente UDP/TCP 53 | Permitir, sujeto a los controles del lado del resolvedor |
| Destino externo arbitrario | Denegar, salvo que se añada una regla explícita de salida |

Las políticas son aditivas y no tienen un orden fijo. Otra regla de permiso amplia puede ampliar el resultado; la denegación predeterminada no la anula. Prueba el conjunto completo de políticas instaladas, la resolución DNS y las conexiones nuevas permitidas o denegadas en el CNI de destino. Las conexiones establecidas y el tráfico hostNetwork/de nodo, así como el comportamiento de NAT, tienen limitaciones específicas de cada implementación; una NetworkPolicy sencilla no es una frontera universal para IMDS ni para el firewall del host.

Para los servicios externos, limita las direcciones y los puertos de destino reales o usa los controles compatibles con DNS de la implementación elegida. Permitir todos los destinos en el puerto 443 o todo el intervalo 10.0.0.0/8 no constituye una lista de servicios permitidos. Un manifiesto arbitrario para sustituir Calico/Cilium o una marca parcial de sustitución de kube-proxy no es una forma segura de habilitar políticas en una red de EKS existente.

Los 18 casos sintéticos de selector/puerto de la fuente relacionada se comprobaron localmente; no se ejecutó ninguna prueba de paquetes/CNI. Referencia: [Comportamiento de NetworkPolicy en Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

</details>

### 3. ¿Qué enfoque combina controles complementarios para proteger las imágenes de contenedor en EKS?

- A) Confiar únicamente en la inspección manual de imágenes
- B) Suponer que todas las imágenes oficiales están libres de vulnerabilidades
- C) Combinar análisis, firma/verificación y controles de admisión
- D) Confiar únicamente en un antivirus dentro del contenedor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Combinar análisis, firma/verificación y controles de admisión**

**Explicación:**

Un analizador identifica los problemas cubiertos por sus reglas y su base de datos de vulnerabilidades; no demuestra que no existan puertas traseras ni vulnerabilidades futuras. Una firma demuestra la integridad y la relación con una identidad conforme a la política de confianza configurada, no que el software firmado sea seguro. Los controles de admisión aplican la política de implementación seleccionada. Usa imágenes base mínimas y mantenidas, vuelve a compilarlas para incorporar parches, registra las excepciones y selecciona el modo de análisis de ECR básico/mejorado u otro que corresponda.

**AWS Signer y Notation:** la plataforma de firma de contenedores es `Notation-OCI-SHA384-ECDSA`. Usa el complemento Notation AWS Signer para firmar por resumen una imagen que ya se haya subido. Una plataforma `Aws::ECR::Image` o `start-signing-job --source-image` no forman parte del flujo de trabajo compatible. La CLI de AWS revisada rechaza esa opción.

La firma administrada actual de ECR también es una alternativa compatible, activada al subir la imagen mediante reglas de firma del registro. Si la eliges, configura el perfil y los permisos correctos y espera al estado de firma real antes de promoverla. No des por hecho que la presencia de una imagen subida demuestra que la firma asíncrona se completó.

**Configuración de confianza:** prepara una instalación verificada de Notation y del complemento Signer, el almacén de confianza raíz de AWS Signer correspondiente a la partición correcta y una política de confianza estricta revisada. Este ejemplo para una Región comercial limita la confianza a un repositorio y un perfil aprobados. Sustituye de forma coherente cada cuenta/Región/repositorio/perfil; no confíes en cualquier firmante solo porque su certificado encadene con la raíz de AWS.

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

Importa esa política en la configuración de Notation propiedad del entorno de compilación con `notation policy import notation-trust-policy.json`. Revisa cualquier política existente antes de reemplazarla; no sobrescribas la configuración de confianza compartida de un desarrollador desde un script que no se haya revisado. El rol de compilación necesita operaciones de extracción/subida de ECR limitadas al repositorio, autenticación de ECR y los permisos SignPayload/GetRevocationStatus necesarios. Crear el perfil de firma es una responsabilidad de aprovisionamiento independiente; la compilación no necesita PutSigningProfile solo para usar un perfil existente y aprobado.

**Ejemplo de CodeBuild:** esto es un buildspec, no una definición de CodePipeline. Requiere una imagen de compilación Linux propia con Bash, Python, Docker/acceso al daemon, AWS CLI, Trivy, Notation y el complemento AWS Signer ya instalados y con sus versiones fijadas. Configura por separado el privilegio de ejecución requerido por el proyecto, el acceso a la red, las bases de datos del analizador, el rol de IAM, el almacén/política de confianza y el repositorio de ECR existente. El Dockerfile y el código fuente son entradas de confianza para ese rol de compilación. Este ejemplo usa una confirmación de Git resuelta y una cuenta/Región comercial de AWS; no implementa un diseño de firma entre cuentas.

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

Configura `AWS_ACCOUNT_ID`, `AWS_REGION`, `ECR_REPOSITORY` (por ejemplo, `team/app`) y `SIGNING_PROFILE_ARN` mediante la configuración revisada del proyecto. El comando se autentica con el nombre de host del registro, conserva las rutas de repositorio anidadas, analiza la imagen compilada localmente antes de subirla y selecciona el RepoDigest subido coincidente, en lugar de una primera entrada arbitraria o una etiqueta mutable. En este caso, Trivy bloquea la compilación ante hallazgos de vulnerabilidades HIGH/CRITICAL; añade otras comprobaciones diseñadas explícitamente para secretos, configuración y procedencia.

Todos los pasos de promoción están en un único bloque de compilación de Bash con `set -euo pipefail`. Si falla el inicio de sesión, la compilación, el análisis, la subida, la firma o la verificación, el proceso se detiene antes de escribir un artefacto nuevo. CodeBuild puede ejecutar post_build después de que falle la compilación, por lo que no es seguro usar un paso de subida/firma independiente y sin protección en post_build. La ruta reservada del artefacto se limpia primero para impedir que se reutilice una salida anterior. La implementación posterior también debe exigir una compilación correcta y validar el artefacto; el archivo JSON por sí solo no es una autorización ni una atestación firmada.

`verified-image.json` contiene la referencia exacta por resumen para un consumidor de EKS/GitOps. No es `imagedefinitions.json` de ECS y no implementa nada por sí solo. El éxito de la firma/verificación sigue dependiendo del acceso real al registro, la confianza, las comprobaciones de revocación y la disponibilidad de AWS Signer.

**Admisión:** un verificador de firmas de producción debe entender la firma de Notation/Signer elegida y la política de confianza. AWS documenta Gatekeeper con Ratify y Kyverno con una integración de AWS Signer/Notation. Instalar un motor de políticas genérico, una restricción de Gatekeeper sin su ConstraintTemplate o un campo de clave pública para un esquema de firma distinto no establece esa integración. Antes de aplicar la política, valida los perfiles de confianza y los no confiables, las imágenes sin firmar, las discrepancias de resumen, las firmas revocadas o vencidas, las interrupciones del verificador y la política de fallos de admisión.

La siguiente regla independiente de Kyverno 1.19.1 solo restringe la **sintaxis de las referencias de imagen y el repositorio** en security-demo. Comprueba los contenedores normales, los de inicialización y los efímeros. **No** afirma verificar una firma:

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

Validación: 20 casos simulados de fallo/orden/artefactos de la canalización y nueve casos reales de cadenas de políticas con la CLI de Kyverno. Se comprobaron el buildspec, Bash, Python, JSON y la CRD publicada de la política. No se compiló, analizó ni subió ninguna imagen; tampoco se generó ni verificó ninguna firma real de AWS, ni se implementó ningún webhook de admisión. Este es un flujo de trabajo didáctico revisado, con supuestos explícitos sobre el entorno; no es un flujo de trabajo cuya preparación para producción se haya probado.

Referencias: [Firma de Signer](https://docs.aws.amazon.com/signer/latest/developerguide/image-signing-steps.html), [Verificación de Signer](https://docs.aws.amazon.com/signer/latest/developerguide/image-verification.html), [Firma administrada de ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/managed-signing.html), [Verificación de admisión de EKS](https://docs.aws.amazon.com/eks/latest/userguide/image-verification.html), [Buildspec de CodeBuild](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html), [Opciones de imagen de Trivy](https://trivy.dev/docs/latest/references/configuration/cli/trivy_image/).

</details>

### 4. ¿Qué enfoque aplica una base de seguridad de Pods coherente y actualizada en EKS?

- A) Deshabilitar únicamente el modo privilegiado
- B) Usar perfiles PSS versionados mediante PSA, con políticas de admisión revisadas cuando sea necesario
- C) Establecer únicamente un UID distinto de root
- D) Hacer únicamente de solo lectura el sistema de archivos raíz

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

El parámetro enforce del espacio de nombres se aplica a la admisión de Pods. Audit/warn puede informar de infracciones en las plantillas de controladores, pero que se aplique correctamente un Deployment/Job no demuestra que sus Pods superen la aplicación de la política. Cambiar las etiquetas no expulsa retroactivamente los Pods existentes. Elige una versión de la política adecuada para el clúster real y revisa las cargas de trabajo existentes antes de aplicarla.

runAsNonRoot/runAsUser y seccomp son distintos de allowPrivilegeEscalation y capabilities. fsGroup es una configuración de propiedad de volúmenes a nivel de Pod, no una capacidad del contenedor. Un sistema de archivos raíz de solo lectura es una medida de refuerzo útil si la aplicación es compatible, pero no es un requisito universal de PSS Restricted ni hace de solo lectura los PVC montados. Las aplicaciones reales necesitan un UID/GID compatible y rutas escribibles para archivos temporales/caché/sockets; un imagen genérica de nginx diseñada para ejecutarse como root no se vuelve funcional con solo añadir estos campos.

**Una regla de admisión adicional y con alcance limitado:** esta ValidatingPolicy de Kyverno 1.19.1 comprueba todos los contenedores normales, de inicialización y efímeros en security-demo. Si privileged no está presente, se acepta como false; si es true, se deniega. Usa la API de políticas v1 actual, no un manifiesto de instalación obsoleto:

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

Esta regla no sustituye todo el perfil PSS ni la verificación de imágenes. Mantén los agentes CSI/de monitoreo con privilegios y las excepciones deliberadas bajo la responsabilidad del propietario de la plataforma; no apliques indiscriminadamente una política de demostración a kube-system. Una alternativa con Gatekeeper necesita su ConstraintTemplate real, la restricción correspondiente y un comportamiento validado.

El manifiesto/esquema y seis casos reales de la CLI de Kyverno cubren la omisión/falsedad, los contenedores normales/de inicialización/efímeros con privilegios y otro espacio de nombres. La prueba de contenedores efímeros usa un objeto UPDATE sintético, no la creación de un Pod. No se ejecutó ningún webhook de admisión real ni se desplegó ningún Pod.

Referencias: [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/), [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/).

</details>

### 5. ¿Qué enfoque proporciona evidencia de seguridad complementaria para una carga de trabajo de EKS?

- A) Usar únicamente revisiones manuales ocasionales
- B) Usar únicamente comprobaciones de AWS Config
- C) Usar únicamente GuardDuty
- D) Combinar hallazgos de postura, registros de auditoría, cobertura de tiempo de ejecución y una vía de respuesta verificada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Combinar hallazgos de postura, registros de auditoría, cobertura de tiempo de ejecución y una vía de respuesta verificada**

**Explicación:**

| Evidencia/control | Qué aporta y qué no demuestra |
|---|---|
| Security Hub CSPM / AWS Config | Controles de configuración compatibles y hallazgos; no constituye una certificación regulatoria o de Kubernetes completa |
| GuardDuty EKS Protection | Análisis de amenazas basado en auditorías de Kubernetes a través de un flujo independiente |
| GuardDuty Runtime Monitoring | Eventos de tiempo de ejecución basados en agentes en nodos compatibles; que esté habilitado no demuestra cobertura |
| CloudTrail | Actividad de la API de AWS; no sustituye los registros de auditoría de Kubernetes ni los registros de acceso a datos de la aplicación |
| Registros de auditoría de Kubernetes | Solicitudes seleccionadas por la política/nivel de auditoría, no todas las acciones o cuerpos de las cargas de trabajo |
| CloudWatch / encaminamiento de incidentes | Análisis de registros y entrega a los operadores; hay que verificar la entrega, la retención y la respuesta |

El estándar FSBP de Security Hub CSPM no es el CIS Kubernetes Benchmark. Los controles CIS AWS Foundations compatibles tampoco constituyen una auditoría CIS Kubernetes completa. Registra el benchmark/versión aplicable, las comprobaciones manuales, las excepciones de servicios administrados y la evidencia que requieren las obligaciones reales de la carga de trabajo.

Usa la propiedad organizativa/regional existente para los detectores, los estándares de CSPM, los grabadores de Config y CloudTrail. No crees otro detector regional, no sobrescribas la configuración centralizada ni inicies un trail sin su política de bucket, cifrado, selectores de eventos y retención previamente preparados. Los eventos de datos de CloudTrail son distintos de la cobertura predeterminada de eventos de administración. En esta revisión no se aprovisionaron recursos de monitoreo a nivel de cuenta.

**Comprobaciones específicas de EKS:** habilita y confirma los tipos de registros del plano de control previstos, la finalización de la actualización y la llegada de los registros, como se muestra en el capítulo de origen. Tanto `eks-cluster-logging-enabled` (todos los tipos, periódico) como `eks-cluster-log-enabled` (tipos opcionales seleccionados, cambios de configuración) son reglas válidas de Config. Mantén el parámetro `oldestVersionSupported` en lugar de suponer que existe un catálogo automático de versiones actuales. Un hallazgo explícito del control encryptionConfig no significa que los datos de la API de EKS 1.28+ carezcan del cifrado de sobre predeterminado.

El análisis de auditoría de GuardDuty no requiere que exportes por separado la auditoría a CloudWatch. Runtime Monitoring necesita el agente de seguridad compatible, el punto de conexión de datos y cobertura real; la compatibilidad actual de EKS incluye EC2 y Auto Mode, pero no Fargate ni Hybrid Nodes. Usa la función actual RUNTIME_MONITORING y revisa la migración desde EKS_RUNTIME_MONITORING heredado. No confundas EKS_AUDIT_LOGS con el monitoreo de tiempo de ejecución.

**Ejemplo de encaminamiento de eventos de CSPM:** guarda esto como `security-event-pattern.json`. Selecciona hallazgos ASFF activos de gravedad HIGH/CRITICAL con estado de flujo de trabajo NEW/NOTIFIED. Intencionadamente no coincide con el esquema de eventos OCSF distinto de `Findings Imported V2`:

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

Este evento sintético solo sirve para comprobar el patrón; no es un hallazgo real ni una carga útil completa de importación ASFF. Guárdalo como `synthetic-security-event.json`:

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

En una prueba de AWS autorizada, `aws events test-event-pattern --event-pattern file://security-event-pattern.json --event file://synthetic-security-event.json --region us-west-2` debería coincidir. Prueba también una gravedad LOW, los estados de flujo de trabajo RESOLVED/SUPPRESSED, el estado ARCHIVED, los campos que falten y el tipo de evento V2; no deberían coincidir con este patrón. Esta revisión comprobó el esquema JSON/de origen, no el comparador del servicio EventBridge ni la entrega de eventos en vivo.

La configuración de destino puede usar un **rol de ejecución de EventBridge existente y revisado**, con permiso para publicar en el tema SNS de propiedad propia, tal como admite la guía actual de EventBridge. Tras sustituir los ARN por los propios, guárdala como `security-event-targets.json`:

```json
[
  {
    "Id": "SecurityAlerts",
    "Arn": "arn:aws:sns:us-west-2:123456789012:eks-security-alerts",
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSecurityAlerts"
  }
]
```

El rol necesita la relación de confianza correcta para EventBridge y un permiso sns:Publish de privilegio mínimo; inspecciona las políticas aplicables del tema/clave y cualquier denegación explícita. Como alternativa, un destino sin rol de ejecución necesita la vía de permisos basada en recursos compatible. El JSON del destino por sí solo no concede ningún permiso ni crea la regla, el tema, el rol o la suscripción.

Antes de usar `aws events put-targets --rule eks-security-alerts --targets file://security-event-targets.json --region us-west-2`, inspecciona la propiedad de las reglas/destinos existentes. Comprueba FailedEntryCount y FailedEntries, no solo el código de salida del comando. Confirma las suscripciones SNS, los permisos de cifrado, el comportamiento de reintento/cola de mensajes fallidos y una prueba controlada de entrega de extremo a extremo. Durante esta auditoría no se envió ninguna notificación.

**Investigación de auditoría:** en el grupo de registros real de EKS, este ejemplo de Logs Insights presupone la detección de campos JSON para los registros de auditoría de Kubernetes. Se centra en las solicitudes de modificación de RBAC; inspecciona responseStatus.code para distinguir las solicitudes correctas de las rechazadas:

```text
fields @timestamp, verb, user.username, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter verb in ["create", "update", "patch", "delete", "deletecollection"]
| filter objectRef.resource in ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
| sort @timestamp desc
| limit 100
```

Verifica los campos de un registro de muestra y el nombre del flujo antes de confiar en la consulta. Conserva la evidencia pertinente, define responsables/gravedad/escalamiento y prueba el proceso de respuesta. Los paneles de hallazgos y los servicios habilitados no demuestran que se haya completado la corrección ni que se haya cumplido una obligación de conformidad.

Referencias: [Estándares de CSPM](https://docs.aws.amazon.com/securityhub/latest/userguide/standards-view-manage.html), [Eventos ASFF](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-cwe-event-formats.html), [Eventos V2](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-v2-cwe-event-formats.html), [Permisos para destinos de EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html), [Registros de auditoría de EKS](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html).

</details>

### 6. Para credenciales de aplicaciones que requieren acceso a AWS gobernado centralmente y gestión del ciclo de vida, ¿qué enfoque es adecuado?

- A) Almacenar valores sin un plan de acceso, rotación o recarga
- B) Tratar las variables de entorno como un mecanismo de cifrado
- C) Usar un backend adecuado de secretos/parámetros de AWS con identidad de alcance limitado y un diseño explícito de entrega/ciclo de vida
- D) Codificar las credenciales de producción en la imagen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar un backend adecuado de secretos/parámetros de AWS con identidad de alcance limitado y un diseño explícito de entrega/ciclo de vida**

**Explicación:**

Secrets Manager y Parameter Store pueden centralizar los controles de acceso y la auditoría de AWS, pero un backend externo no es seguro automáticamente si no se configuran la identidad de la carga de trabajo, los privilegios mínimos, la entrega y los controles de recarga. Secrets Manager admite la rotación configurada para las credenciales compatibles; Parameter Store no ofrece el mismo flujo de trabajo integrado de rotación de credenciales. El cifrado KMS y el versionado de un parámetro SecureString son distintos de cambiar las credenciales en la base de datos/servicio de destino.

EKS 1.28+ ya cifra todos los datos de la API de Kubernetes con el cifrado de sobre predeterminado KMS v2. La codificación Base64 de un manifiesto Secret sigue siendo solo codificación, y el acceso a la API/al Pod puede exponer el valor. Las variables de entorno son un mecanismo de entrega, no de cifrado; los entornos de procesos existentes no se actualizan cuando cambia un Secret.

**Elige deliberadamente la propiedad y el método de entrega:** ESO escribe un Secret de Kubernetes. ASCP con Secrets Store CSI Driver monta archivos y, opcionalmente, puede sincronizar un Secret de Kubernetes. No permitas que ambos controladores administren el mismo Secret de destino. Un diseño CSI solo con archivos sigue necesitando controles de acceso a la carga de trabajo/nodo; la sincronización opcional también introduce una copia del valor en la API de Kubernetes.

**Ejemplo de ASCP:** se trata de una instalación nueva de propiedad propia en EC2 Linux para el ejemplo revisado de EKS 1.36, no de un despliegue en un clúster existente desconocido. Primero inspecciona la propiedad de las versiones/CSIDriver existentes, la compatibilidad de los nodos, la admisión de agentes de plataforma con privilegios, el acceso a la red y la programación. Fargate no puede ejecutar el DaemonSet de nodos CSI. El uso con Hybrid/Auto Mode requiere los requisitos previos actuales del proveedor/nodo; el renderizado local siguiente no lo verifica.

Usa esta configuración de `secrets-csi-values.yaml` para un controlador CSI 1.6.1 administrado por separado. Configura explícitamente ambas audiencias de token de AWS, la sincronización opcional de Secrets y la rotación:

```yaml
tokenRequests:
- audience: sts.amazonaws.com
- audience: pods.eks.amazonaws.com
syncSecret:
  enabled: true
enableSecretRotation: true
rotationPollInterval: 2m
```

ASCP chart 3.1.3 normalmente incluye el controlador como dependencia y configura sus audiencias de token. Como este ejemplo instala el controlador por separado, guarda lo siguiente como `ascp-values.yaml` para evitar instalar un segundo controlador:

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

Las instalaciones existentes necesitan el procedimiento de actualización de versión/CRD de su propietario; no ejecutes estos comandos de instalación nueva ni un `helm upgrade` parcial sobre valores no relacionados. Fijar versiones del chart y renderizar correctamente no demuestra la compatibilidad del complemento de nodo, la conectividad ni el acceso a los secretos.

Prepara un secreto JSON de Secrets Manager de propiedad propia con los campos username/password y un rol `ASCPSecretReader` limitado a ese secreto exacto, además del permiso adecuado para descifrar con una clave del cliente, si fuera necesario. Esta relación de confianza IRSA usa el sujeto exacto de ServiceAccount; sustituye de manera coherente el proveedor/emisor OIDC completo y la cuenta:

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

El Namespace, el ServiceAccount, el SecretProviderClass y el Pod siguientes forman el ejemplo de entrega mediante archivos. Selecciona la versión PSS adecuada para el clúster real. JMESPath extrae campos en alias; `secretObjects.data.objectName` indica el nombre de esos alias montados. No se admite un campo `property` dentro de secretObjects.data. Los permisos 0444 permiten que estos archivos sean leídos por el proceso de demostración sin privilegios; limita quién puede montar/crear Pods y elige UID/GID y permisos de archivo compatibles para una aplicación real.

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

El Pod comprueba que los archivos existan sin imprimir su contenido. `automountServiceAccountToken: false` deshabilita el montaje automático del token de la API de Kubernetes, no las solicitudes explícitas de tokens del controlador CSI. En lugar de este ejemplo con IRSA, para Pod Identity usa un agente/asociación compatible para el ServiceAccount de la carga de trabajo y `usePodIdentity: "true"`; no des por hecho que una anotación IRSA proporciona esa asociación.

El Secret opcional csi-db-credentials solo se sincroniza después de que un Pod monte el volumen. Su ciclo de vida sigue el de los Pods consumidores y puede eliminarse cuando se borran todos los consumidores. Crear un SecretProviderClass no genera un Secret por sí solo. Inspecciona SecretProviderClassPodStatus y los eventos del controlador/nodo sin volcar los valores.

Para Parameter Store, el valor objects puede contener, en cambio, la siguiente entrada, con el permiso de lectura SSM requerido por el proveedor sobre el parámetro de propiedad propia y el acceso KMS adecuado para SecureString. Es un fragmento de objects, no un SecretProviderClass completo:

```yaml
- objectName: /training/app/config
  objectType: ssmparameter
  objectAlias: app_config
  filePermission: "0444"
```

**Alternativa con ESO:** usa el rol/relación de confianza IRSA EKSSecretReader preparado en el capítulo de origen para el ServiceAccount eso-reader exacto. Con ESO 2.10.0 y sus CRD v1 instaladas bajo la responsabilidad de su propietario, lo siguiente escribe un destino diferente, eso-db-credentials. El ARN del backend, el espacio de nombres, el rol y las propiedades JSON deben corresponder al secreto preparado real:

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

Aquí Owner vincula el Secret de destino al ExternalSecret; al eliminar el propietario, puede activarse la recolección de basura. Retain se refiere a la desaparición del backend, no protege contra la eliminación del propietario. El método JWT serviceAccountRef de ESO es IRSA. Pod Identity del Pod del controlador es un diseño distinto: asocia el ServiceAccount del controlador y omite el bloque auth del store; ESO no puede usar serviceAccountRef para suplantar otra cuenta asociada con Pod Identity.

**Rotación y recarga:** CSI 1.6+ usa llamadas RequiresRepublish de kubelet para la rotación. requiresRepublish por sí solo no habilita la rotación: también se necesita la marca enableSecretRotation del controlador. El rotationPollInterval de dos minutos que aparece aquí es una duración mínima de caché, no un intervalo garantizado de actualización de extremo a extremo de dos minutos; el tiempo real depende de la republicación de kubelet. El intervalo de actualización de ESO es otro ciclo de conciliación independiente. Las aplicaciones deben volver a abrir/vigilar los archivos actualizados o realizar un despliegue controlado; los montajes subPath y las variables de entorno existentes no se actualizan automáticamente.

rotate-secret de Secrets Manager establece la rotación inmediata como valor predeterminado. Incluso `--no-rotate-immediately` puede probar una función Lambda de rotación y crear/eliminar AWSPENDING, mientras que puede seguir ejecutándose una programación anterior basada en intervalos/días. No es una comprobación inocua que solo configure una programación ni una comprobación de solo lectura. Revisa los cambios en las credenciales de destino, los períodos de validez solapados, la recarga de la aplicación y la reversión antes de invocar la rotación.

**Ejemplo de Terraform sin valores secretos:** sensitive en Terraform solo suprime determinadas salidas visibles; los valores normales de secret_string/random_password pueden seguir almacenándose en el estado. Lo siguiente administra únicamente los metadatos del secreto y usa una clave KMS aprobada existente. Si el secreto ya existe, concílialo/importalo a través de su propietario antes de administrarlo con esta configuración:

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

Esto no crea ninguna versión/valor del secreto ni habilita la rotación. Proporciona el valor inicial mediante el proceso aprobado de entrada de secretos, no mediante una cadena Terraform codificada o un argumento de comando en texto sin cifrar. Protege el estado y los planes aunque solo se esperen metadatos. prevent_destroy es una salvaguarda de configuración de Terraform, no una protección irreversible del servicio; eliminar la configuración del recurso o actuar fuera de Terraform cambia el contexto de protección.

La validación abarcó Kubernetes nativo y las CRD publicadas de SecretProviderClass/ESO, las sumas de comprobación publicadas de los charts, 22 objetos CSI/ASCP renderizados y la proyección JMESPath real de datos sintéticos. Los campos creationTimestamp nulos generados se omitieron únicamente para la comprobación del esquema Swagger. Terraform fmt se ejecutó correctamente; no se ejecutaron init/plan/apply. No se obtuvo, montó, sincronizó ni rotó ningún secreto de AWS, y no se probó la recarga de ninguna aplicación.

Referencias: [Configuración de ASCP](https://github.com/aws/secrets-store-csi-driver-provider-aws), [CSI 1.6.1](https://github.com/kubernetes-sigs/secrets-store-csi-driver/releases/tag/v1.6.1), [Sincronización de Secrets CSI](https://secrets-store-csi-driver.sigs.k8s.io/topics/sync-as-kubernetes-secret), [Rotación CSI](https://secrets-store-csi-driver.sigs.k8s.io/topics/secret-auto-rotation), [Autenticación de ESO con AWS](https://github.com/external-secrets/external-secrets/blob/v2.10.0/docs/provider/aws-access.md), [Cifrado de sobre de EKS](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html), [Rotación de Secrets Manager](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/rotate-secret.html).

</details>
