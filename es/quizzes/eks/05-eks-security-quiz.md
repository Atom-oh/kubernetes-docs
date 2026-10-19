# Cuestionario sobre seguridad de Amazon EKS

> **Última actualización**: 11 de septiembre de 2026

Este cuestionario evalúa tu comprensión de las funciones de seguridad, las prácticas recomendadas y las configuraciones de Amazon EKS.

## Resumen del cuestionario
- Autenticación y autorización de EKS
- Seguridad de red
- Seguridad de contenedores
- Seguridad de datos
- Cumplimiento y auditoría
- Prácticas recomendadas de seguridad

## Preguntas de opción múltiple

### 1. Para un usuario o rol de IAM, ¿qué configuración de EKS combina correctamente la autenticación de identidad y la autorización de Kubernetes?

- A) Usar únicamente permisos de administración de IAM
- B) Crear reglas RBAC sin configurar la ruta de autenticación de la identidad
- C) Configurar el acceso de IAM al clúster junto con RBAC y/o políticas de acceso de EKS adecuadas
- D) Usar únicamente restricciones de red del endpoint de la API

<details>
<summary>Mostrar la respuesta</summary>

**Respuesta: C) Configurar el acceso de IAM al clúster junto con RBAC y/o políticas de acceso de EKS adecuadas**

**Explicación:**

IAM autentica la identidad humana o de automatización prevista a través de la ruta de acceso de EKS configurada. RBAC de Kubernetes y las políticas de acceso de EKS autorizan las operaciones de Kubernetes; sus concesiones se acumulan. Las restricciones de red son otra capa y no sustituyen la autorización. La autenticación de un Pod ante Kubernetes normalmente usa su token de ServiceAccount; IRSA/Pod Identity, en cambio, proporciona credenciales de AWS a la carga de trabajo.

El rol de servicio del clúster de EKS y el de un desarrollador humano tienen propósitos distintos. Asociar AmazonEKSClusterPolicy al desarrollador no concede acceso a Kubernetes, y los permisos DescribeCluster/ListClusters o un archivo kubeconfig tampoco conceden permisos sobre las cargas de trabajo.

**Implementación acotada:** un operador de plataforma autorizado prepara el namespace y el RBAC siguientes para un rol de IAM de desarrollador aprobado que ya existe. El clúster debe admitir entradas de acceso. Conserva las asignaciones existentes de administradores y nodos, y revisa la migración del modo de autenticación; no sobrescribas aws-auth con un ConfigMap de ejemplo.

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

El nombre del grupo de la entrada de acceso debe coincidir con el sujeto del RoleBinding. Este rol permite las operaciones enumeradas únicamente en security-demo; otras concesiones existentes pueden ampliar el acceso. Crear Deployments/Jobs puede permitir el uso indirecto de Secrets, PVC y ServiceAccounts de ese namespace, por lo que no tener una regla directa de lectura de Secret no constituye un límite de seguridad entre tenants. Separa los tenants y restringe la identidad de las cargas de trabajo y el uso de recursos mediante controles de admisión y propiedad.

Un usuario de solo lectura revisado por separado también puede usar una asociación de AmazonEKSViewPolicy limitada a un namespace. Inspecciona las políticas de acceso existentes antes de añadirla; no revoca concesiones más amplias de RBAC ni de otras políticas de acceso. `eks:namespaces` filtra las solicitudes de asociación de políticas de acceso, no las solicitudes generales de kubectl.

**Valida el inicio de sesión real:** el usuario o proceso que realiza la solicitud debe poder descubrir el clúster y asumir el rol aprobado. Esto crea un kubeconfig temporal en vez de reemplazar el contexto predeterminado:

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

Compara los resultados con las concesiones previstas e investiga cualquier permiso inesperado entre namespaces. `--as` prueba la suplantación de identidad y RBAC; no demuestra que funcione la ruta de políticas de acceso de IAM. Para este cuestionario no se ejecutó ningún inicio de sesión real de IAM ni prueba de autorización de Kubernetes; las pruebas locales consistieron en comprobaciones de esquema y shell y flujos simulados de entradas de acceso.

Referencias: [Entradas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html), [Políticas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html), [RBAC de Kubernetes](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).

</details>

### 2. ¿Qué mecanismo de Kubernetes define reglas de tráfico de Pods basadas en etiquetas en una red de EKS que admita la aplicación de políticas?

- A) Solo grupos de seguridad de instancias
- B) Recursos NetworkPolicy con una implementación de red que aplique las políticas
- C) Solo políticas de endpoints de VPC
- D) Solo comandos de firewall del host

<details>
<summary>Mostrar la respuesta</summary>

**Respuesta: B) Recursos NetworkPolicy con una implementación de red que aplique las políticas**

**Explicación:**

NetworkPolicy selecciona Pods y el tráfico permitido mediante etiquetas de Kubernetes y namespaces. Requiere una implementación de red que aplique las políticas. Los grupos de seguridad, incluidos los grupos de seguridad para Pods admitidos, siguen siendo controles útiles de AWS; no se limitan a instancias completas. Las políticas de endpoints de VPC rigen el acceso a los servicios de AWS compatibles, no el tráfico arbitrario de Pods según etiquetas.

**Ejemplo completo de políticas:** estos manifiestos describen un namespace aislado para demostración; no instalan aplicaciones ni reemplazan el CNI. Suponen nodos EC2 Linux estándar con un CNI compatible que aplique políticas y las etiquetas habituales de Deployment/Pod de CoreDNS. Auto Mode o DNS local del nodo requieren reglas para la ruta real que usa el resolver. Si se restringe el ingreso a CoreDNS, quien lo administre también debe permitir estas consultas.

Guarda y aplica los manifiestos a través de quien administre el namespace. La denegación predeterminada aísla ambas direcciones; se permiten explícitamente el egreso del cliente y el ingreso del destino para frontend → API y API → base de datos. DNS requiere tanto UDP como TCP:

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

El par de monitorización usa namespaceSelector **y** podSelector en un mismo par, por lo que solo selecciona los Pods de Prometheus coincidentes en security-monitoring-demo. La conexión saliente también necesita permiso cuando ese cliente está aislado por egreso:

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
| Otro Pod del namespace de monitorización → api TCP 9090 | Denegar |
| Carga de trabajo → Pod de CoreDNS coincidente, UDP/TCP 53 | Permitir, sujeto a controles del lado del resolver |
| Destino externo arbitrario | Denegar, salvo que se añada una regla de egreso explícita |

Las políticas se acumulan y no tienen orden. Otra regla amplia de permiso puede ampliar el resultado; la denegación predeterminada no la anula. Prueba el conjunto completo de políticas instaladas, la resolución DNS y conexiones nuevas permitidas y denegadas en el CNI de destino. Las conexiones establecidas, el tráfico de hostNetwork/nodo y el comportamiento de NAT tienen límites específicos de cada implementación; NetworkPolicy por sí sola no es un límite universal para IMDS ni un firewall del host.

Para servicios externos, limita las direcciones y puertos de destino reales o usa los controles con reconocimiento de DNS que admita la implementación elegida. Permitir cualquier destino por el puerto 443 o todo el rango 10.0.0.0/8 no crea una lista de servicios permitidos. Un manifiesto arbitrario de reemplazo para Calico/Cilium o una opción parcial de reemplazo de kube-proxy no es una forma segura de habilitar políticas en una red EKS existente.

Los 18 casos sintéticos de selectores y puertos de la fuente relacionada se comprobaron localmente; no se ejecutó ninguna prueba de paquetes/CNI. Referencia: [Comportamiento de NetworkPolicy en Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

</details>

### 3. ¿Qué enfoque combina controles complementarios para proteger las imágenes de contenedor en EKS?

- A) Confiar únicamente en la inspección manual de imágenes
- B) Suponer que todas las imágenes oficiales están libres de vulnerabilidades
- C) Combinar análisis, firma/verificación y controles de admisión
- D) Confiar únicamente en antivirus dentro del contenedor

<details>
<summary>Mostrar la respuesta</summary>

**Respuesta: C) Combinar análisis, firma/verificación y controles de admisión**

**Explicación:**

Un escáner identifica los problemas cubiertos por sus reglas y su base de datos de vulnerabilidades; no demuestra que no haya puertas traseras ni vulnerabilidades futuras. Una firma demuestra integridad y una relación con una identidad según la política de confianza configurada, pero no que el software firmado sea seguro. Los controles de admisión aplican la política de implementación seleccionada. Usa imágenes base mínimas mantenidas, vuelve a compilarlas para incorporar parches, registra las excepciones y elige el modo de análisis básico/mejorado de ECR u otro adecuado.

**AWS Signer y Notation:** la plataforma de firma de contenedores es `Notation-OCI-SHA384-ECDSA`. Usa el complemento Notation de AWS Signer para firmar por digest una imagen que ya se haya subido. Una plataforma `Aws::ECR::Image` o `start-signing-job --source-image` no es un flujo compatible. La CLI de AWS revisada rechaza esa opción.

La firma administrada de ECR también admite un flujo alternativo activado al subir la imagen, con reglas de firma del registro. Si eliges esa opción, configura el perfil y los permisos correctos, y espera el estado real de firma antes de promover la imagen. No supongas que una imagen subida ya terminó de firmarse de forma asíncrona.

**Configuración de confianza:** prepara una instalación verificada del complemento Notation/Signer, el almacén raíz de confianza de AWS Signer de la partición correcta y una política estricta de confianza revisada. Este ejemplo de una región comercial limita la confianza a un repositorio y un perfil aprobado. Sustituye de forma coherente cada cuenta, región, repositorio y perfil; no confíes en cualquier firmante solo porque su certificado encadene con la raíz de AWS.

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

Importa esa política a la configuración Notation propia del entorno de compilación con `notation policy import notation-trust-policy.json`. Revisa cualquier política existente antes de reemplazarla; no sobrescribas la configuración compartida de confianza de una persona desarrolladora mediante un script no revisado. El rol de compilación necesita operaciones de extracción y envío de ECR limitadas al repositorio, autenticación de ECR y los permisos SignPayload/GetRevocationStatus requeridos. Crear el perfil de firma es una responsabilidad de aprovisionamiento separada; la compilación no necesita PutSigningProfile para usar un perfil aprobado existente.

**Ejemplo de CodeBuild:** esto es un buildspec, no una definición de CodePipeline. Requiere una imagen Linux propia de compilación, con Bash, Python, acceso a Docker/daemon, AWS CLI, Trivy, Notation y el complemento AWS Signer ya instalados y con versiones fijadas. Configura por separado el privilegio de ejecución requerido por el proyecto, la red, las bases de datos del escáner, el rol de IAM, el almacén/política de confianza y el repositorio ECR existente. El Dockerfile y el código fuente son entradas de confianza para ese rol. Este ejemplo usa un commit de Git resuelto y una cuenta/región comercial de AWS; no implementa un diseño de firma entre cuentas.

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

Configura `AWS_ACCOUNT_ID`, `AWS_REGION`, `ECR_REPOSITORY` (por ejemplo, `team/app`) y `SIGNING_PROFILE_ARN` mediante la configuración revisada del proyecto. El comando se autentica en el nombre de host del registro, conserva las rutas de repositorios anidados, analiza la imagen compilada localmente antes de subirla y selecciona el RepoDigest subido que coincide, en lugar de elegir una entrada arbitraria o una etiqueta mutable. Aquí Trivy bloquea hallazgos de vulnerabilidad HIGH/CRITICAL; añade otras comprobaciones diseñadas explícitamente para secretos, configuración y procedencia.

Todos los pasos de promoción están en un único bloque Bash de compilación con `set -euo pipefail`. Si falla el inicio de sesión, compilación, análisis, subida, firma o verificación, se detiene antes de escribir un artefacto nuevo. CodeBuild puede ejecutar post_build después de fallar build, por lo que un paso de subida/firma independiente y sin protección en post_build no es seguro. Primero se elimina la ruta reservada del artefacto para evitar reutilizar una salida anterior. La implementación posterior también debe exigir que la compilación haya tenido éxito y validar el artefacto; el archivo JSON por sí solo no es una autorización ni una atestación firmada.

`verified-image.json` contiene la referencia exacta por digest para un consumidor de implementación/GitOps de EKS. No es `imagedefinitions.json` de ECS y no implementa nada por sí mismo. La firma/verificación correcta sigue dependiendo del acceso real al registro, la confianza, las comprobaciones de revocación y la disponibilidad de AWS Signer.

**Admisión:** un verificador de firmas de producción debe comprender la firma Notation/Signer y la política de confianza elegidas. AWS documenta Gatekeeper con Ratify y Kyverno con una integración de AWS Signer/Notation. Instalar un motor genérico de políticas, una restricción Gatekeeper sin su ConstraintTemplate o un campo de clave pública para otro esquema de firma no demuestra que exista esa integración. Antes de aplicarla, valida perfiles confiables/no confiables, imágenes sin firma, diferencias de digest, firmas revocadas/expiradas, interrupciones del verificador y la política de fallo de admisión.

La siguiente regla independiente de Kyverno 1.19.1 solo restringe la **sintaxis y el repositorio de la referencia de imagen** en security-demo. Comprueba los contenedores normales, de inicialización y efímeros. Deliberadamente **no** afirma verificar una firma:

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

Validación: 20 casos simulados de fallo/orden/artefacto de la canalización y nueve casos reales de políticas de cadenas mediante Kyverno CLI. Se comprobaron buildspec/Bash/Python/JSON y el CRD publicado de la política. No se compiló, analizó ni subió ninguna imagen; no se produjo ni verificó ninguna firma real de AWS; tampoco se desplegó un webhook de admisión. Este flujo didáctico revisado declara sus supuestos de entorno, pero no se probó para estar listo para producción.

Referencias: [Firma de Signer](https://docs.aws.amazon.com/signer/latest/developerguide/image-signing-steps.html), [Verificación de Signer](https://docs.aws.amazon.com/signer/latest/developerguide/image-verification.html), [Firma administrada de ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/managed-signing.html), [Verificación de admisión en EKS](https://docs.aws.amazon.com/eks/latest/userguide/image-verification.html), [Buildspec de CodeBuild](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html), [Opciones de imagen de Trivy](https://trivy.dev/docs/latest/references/configuration/cli/trivy_image/).

</details>

### 4. ¿Qué enfoque aplica una línea base de seguridad de Pods coherente y actual en EKS?

- A) Deshabilitar únicamente el modo privilegiado
- B) Usar perfiles PSS versionados mediante PSA, con políticas de admisión revisadas cuando hagan falta
- C) Configurar únicamente un UID no root
- D) Hacer de solo lectura únicamente el sistema de archivos raíz

<details>
<summary>Mostrar la respuesta</summary>

**Respuesta: B) Usar perfiles PSS versionados mediante PSA, con políticas de admisión revisadas cuando hagan falta**

**Explicación:**

Pod Security Standards define los perfiles Privileged, Baseline y Restricted. Pod Security Admission aplica los perfiles seleccionados por namespace. PSA es estable desde Kubernetes 1.25; PodSecurityPolicy quedó obsoleto en 1.21 y se **eliminó en 1.25**. Un clúster actual no puede desplegar esa API eliminada. Las políticas de Kyverno/Gatekeeper son recursos separados, aunque un ejemplo antiguo use “PSP” en el nombre de una restricción.

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

La etiqueta enforce del namespace se aplica a la admisión de Pods. Audit/warn puede informar infracciones en plantillas de controladores, pero que se aplique correctamente un Deployment/Job no demuestra que sus Pods pasen la aplicación de la política. Cambiar etiquetas no expulsa de forma retroactiva a los Pods existentes. Elige una versión de política adecuada al clúster real y revisa las cargas de trabajo existentes antes de aplicar la política.

runAsNonRoot/runAsUser y seccomp son distintos de allowPrivilegeEscalation y capabilities. fsGroup es una configuración de propiedad de volumen a nivel de Pod, no una capacidad de contenedor. Un sistema de archivos raíz de solo lectura es una medida útil si la aplicación es compatible, pero no es un requisito universal de PSS Restricted y no vuelve de solo lectura los PVC montados. Las aplicaciones reales necesitan UID/GID compatibles y rutas temporales, de caché y de sockets donde se pueda escribir; una imagen genérica de nginx que espera ejecutarse como root no funciona automáticamente por añadir estos campos.

**Regla de admisión adicional y acotada:** esta ValidatingPolicy de Kyverno 1.19.1 comprueba todos los contenedores normales, de inicialización y efímeros en security-demo. Si privileged no está presente, se acepta como false; si es true, se deniega. Usa la API de política v1 actual, no un manifiesto de instalación obsoleto:

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

Esta regla no reemplaza todo el perfil PSS ni la verificación de imágenes. Mantén los agentes CSI/de monitorización privilegiados y las excepciones deliberadas bajo la responsabilidad de su plataforma; no apliques indiscriminadamente una política de demostración a kube-system. Una alternativa con Gatekeeper necesita su ConstraintTemplate real, una restricción coincidente y comportamiento validado.

El manifiesto/esquema y seis casos reales de Kyverno CLI cubren el valor omitido/false, contenedores privilegiados normales/de inicialización/efímeros y otro namespace. La prueba de contenedor efímero usa un objeto UPDATE sintético, no la creación de un Pod. No se ejecutó un webhook de admisión real ni se desplegó ningún Pod.

Referencias: [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/), [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/).

</details>

### 5. ¿Qué enfoque reúne evidencias de seguridad complementarias para una carga de trabajo de EKS?

- A) Realizar solo revisiones manuales ocasionales
- B) Usar solo comprobaciones de AWS Config
- C) Usar solo GuardDuty
- D) Combinar hallazgos de postura, registros de auditoría, cobertura de runtime y una ruta de respuesta verificada

<details>
<summary>Mostrar la respuesta</summary>

**Respuesta: D) Combinar hallazgos de postura, registros de auditoría, cobertura de runtime y una ruta de respuesta verificada**

**Explicación:**

| Evidencia/control | Qué aporta y qué no demuestra |
|---|---|
| Security Hub CSPM / AWS Config | Controles de configuración compatibles y hallazgos; no equivale a una certificación completa de Kubernetes ni normativa |
| GuardDuty EKS Protection | Análisis de amenazas basado en auditoría de Kubernetes a través de un flujo independiente |
| GuardDuty Runtime Monitoring | Eventos de runtime basados en agente en nodos compatibles; que esté habilitado no demuestra cobertura |
| CloudTrail | Actividad de la API de AWS; no reemplaza los registros de auditoría de Kubernetes ni los de acceso a datos de la aplicación |
| Registros de auditoría de Kubernetes | Solicitudes seleccionadas por la política/nivel de auditoría; no todas las acciones ni cuerpos de cargas de trabajo |
| CloudWatch / enrutamiento de incidentes | Análisis de registros y entrega a operadores; hay que verificar la entrega, retención y respuesta |

El estándar FSBP de Security Hub CSPM no es el Kubernetes Benchmark de CIS. Los controles CIS AWS Foundations compatibles tampoco constituyen una auditoría completa de CIS Kubernetes. Registra el benchmark/versión aplicable, las comprobaciones manuales, las excepciones de servicios administrados y la evidencia requerida por las obligaciones reales de la carga de trabajo.

Usa la propiedad organizativa/regional existente para detectores, estándares de CSPM, registradores de Config y CloudTrail. No crees otro detector regional, no sobrescribas configuración centralizada ni inicies un trail sin su política de bucket preparada, cifrado, selectores de eventos y retención. Los eventos de datos de CloudTrail son independientes de la cobertura predeterminada de eventos de administración. En esta revisión no se aprovisionaron recursos de monitorización a nivel de cuenta.

**Comprobaciones específicas de EKS:** habilita y confirma los tipos de registros del plano de control previstos, la finalización de la actualización y la llegada de registros tal como se muestra en el capítulo fuente. Tanto `eks-cluster-logging-enabled` (todos los tipos, periódico) como `eks-cluster-log-enabled` (tipos seleccionados opcionales, cambios de configuración) son reglas de Config válidas. Mantén el parámetro `oldestVersionSupported` en vez de suponer que existe un catálogo actual automático. Un hallazgo explícito del control encryptionConfig no significa que los datos de la API de EKS 1.28+ carezcan del cifrado de sobre predeterminado.

El análisis de auditoría de GuardDuty no requiere tu exportación de auditoría separada a CloudWatch. Runtime Monitoring necesita el agente de seguridad/endpoint de datos compatible y cobertura real; la compatibilidad actual de EKS incluye EC2 y Auto Mode, no Fargate ni Hybrid Nodes. Usa la función actual RUNTIME_MONITORING y revisa la migración de EKS_RUNTIME_MONITORING heredada. No confundas EKS_AUDIT_LOGS con la monitorización de runtime.

**Ejemplo de enrutamiento de eventos de CSPM:** guárdalo como `security-event-pattern.json`. Selecciona hallazgos ASFF activos HIGH/CRITICAL con estado de flujo NEW/NOTIFIED. Intencionalmente no coincide con el esquema diferente de eventos OCSF `Findings Imported V2`:

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

Este evento sintético sirve solo para comprobar el patrón; no es un hallazgo real ni una carga completa de importación ASFF. Guárdalo como `synthetic-security-event.json`:

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

En una prueba de AWS autorizada, `aws events test-event-pattern --event-pattern file://security-event-pattern.json --event file://synthetic-security-event.json --region us-west-2` debería coincidir. Prueba también gravedad LOW, flujos RESOLVED/SUPPRESSED, estado ARCHIVED, campos ausentes y el tipo de evento V2; no deberían coincidir con este patrón. Esta revisión comprobó el esquema JSON/fuente, no el evaluador del servicio EventBridge ni la entrega de eventos en vivo.

La configuración del destino puede usar un **rol de ejecución de EventBridge existente y revisado** con permiso de publicación en el tema SNS administrado, tal como admite la guía actual de EventBridge. Sustituye los ARN propios y guarda la configuración como `security-event-targets.json`:

```json
[
  {
    "Id": "SecurityAlerts",
    "Arn": "arn:aws:sns:us-west-2:123456789012:eks-security-alerts",
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSecurityAlerts"
  }
]
```

El rol necesita una relación de confianza de EventBridge correcta y permiso sns:Publish de privilegio mínimo; inspecciona las políticas aplicables del tema/clave y cualquier denegación explícita. Como alternativa, un destino sin rol de ejecución necesita la ruta de permisos basada en recursos que admita el servicio. El JSON del destino por sí solo no concede permisos ni crea la regla, el tema, el rol o la suscripción.

Antes de usar `aws events put-targets --rule eks-security-alerts --targets file://security-event-targets.json --region us-west-2`, inspecciona la propiedad de las reglas/destinos existentes. Comprueba FailedEntryCount y FailedEntries, no solo el código de salida del comando. Confirma las suscripciones de SNS, permisos de cifrado, comportamiento de reintentos y de la cola de mensajes no entregados y una prueba controlada de entrega de extremo a extremo. En esta auditoría no se envió ninguna notificación.

**Investigación de auditoría:** en el grupo de registros real de EKS, este ejemplo de Logs Insights supone que se detectan campos JSON en los registros de auditoría de Kubernetes. Se centra en solicitudes que modifican RBAC; inspecciona responseStatus.code para distinguir las aceptadas de las rechazadas:

```text
fields @timestamp, verb, user.username, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter verb in ["create", "update", "patch", "delete", "deletecollection"]
| filter objectRef.resource in ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
| sort @timestamp desc
| limit 100
```

Verifica los campos de un registro de muestra y el nombre del flujo antes de confiar en la consulta. Conserva la evidencia pertinente, define responsables/gravedad/escalamiento y prueba el proceso de respuesta. Los paneles de hallazgos y los servicios habilitados no demuestran que la corrección se haya completado ni que se haya cumplido una obligación normativa.

Referencias: [Estándares de CSPM](https://docs.aws.amazon.com/securityhub/latest/userguide/standards-view-manage.html), [Eventos ASFF](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-cwe-event-formats.html), [Eventos V2](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-v2-cwe-event-formats.html), [Permisos de destinos de EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html), [Registros de auditoría de EKS](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html).

</details>

### 6. Para credenciales de aplicaciones que requieren acceso a AWS gobernado de forma centralizada y gestión de ciclo de vida, ¿qué enfoque corresponde?

- A) Almacenar los valores sin un plan de acceso, rotación ni recarga
- B) Tratar las variables de entorno como mecanismo de cifrado
- C) Usar un backend adecuado de secretos/parámetros de AWS con identidad acotada y un diseño explícito de entrega/ciclo de vida
- D) Incluir credenciales de producción codificadas en la imagen

<details>
<summary>Mostrar la respuesta</summary>

**Respuesta: C) Usar un backend adecuado de secretos/parámetros de AWS con identidad acotada y un diseño explícito de entrega/ciclo de vida**

**Explicación:**

Secrets Manager y Parameter Store pueden centralizar los controles de acceso y la auditoría de AWS, pero un backend externo no es automáticamente seguro sin identidad de carga de trabajo, privilegio mínimo y controles de entrega/recarga. Secrets Manager admite rotación configurada para credenciales compatibles; Parameter Store no ofrece el mismo flujo integrado de rotación de credenciales. El cifrado KMS y el versionado de un parámetro SecureString no equivalen a cambiar las credenciales en la base de datos/servicio de destino.

EKS 1.28+ ya cifra todos los datos de la API de Kubernetes mediante el cifrado de sobre KMS v2 predeterminado. Base64 en un manifiesto Secret sigue siendo solo codificación, y el acceso a la API/Pod puede exponer el valor. Las variables de entorno son un mecanismo de entrega, no cifrado; los entornos de procesos existentes no se actualizan cuando cambia un Secret.

**Elige deliberadamente la propiedad y la entrega:** ESO escribe un Secret de Kubernetes. ASCP con Secrets Store CSI Driver monta archivos y, opcionalmente, puede sincronizar un Secret de Kubernetes. No permitas que ambos controladores administren el mismo Secret de destino. Un diseño CSI solo de archivos también necesita controles de acceso de la carga de trabajo y el nodo; la sincronización opcional añade además una copia del valor en la API de Kubernetes.

**Ejemplo de ASCP:** es una instalación nueva en Linux/EC2 administrada por el equipo para el ejemplo revisado de EKS 1.36, no un despliegue en un clúster existente desconocido. Primero inspecciona las versiones instaladas y quién es propietario de CSIDriver, compatibilidad de nodos, admisión de agentes de plataforma privilegiados, red y planificación. Fargate no puede ejecutar el DaemonSet de nodos CSI. El uso con Hybrid/Auto Mode requiere sus requisitos actuales de proveedor/nodo; el renderizado local siguiente no lo verifica.

Usa estos ajustes en `secrets-csi-values.yaml` para un driver CSI administrado por separado, versión 1.6.1. Configuran explícitamente ambas audiencias de tokens de AWS, la sincronización opcional de Secret y la rotación:

```yaml
tokenRequests:
- audience: sts.amazonaws.com
- audience: pods.eks.amazonaws.com
syncSecret:
  enabled: true
enableSecretRotation: true
rotationPollInterval: 2m
```

El chart 3.1.3 de ASCP normalmente incluye el driver como dependencia y configura sus audiencias de tokens. Como este ejemplo instala el driver por separado, guarda lo siguiente como `ascp-values.yaml` para evitar instalar un segundo driver:

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

Las instalaciones existentes requieren el procedimiento de actualización de versión/CRD de su propietario; no ejecutes estos comandos de instalación nueva ni un `helm upgrade` parcial que sobrescriba valores no relacionados. Fijar el chart y renderizar correctamente no demuestra la compatibilidad del complemento de nodo, la conectividad ni el acceso al secreto.

Prepara un secreto JSON propio de Secrets Manager con campos username/password y un rol `ASCPSecretReader` limitado a ese secreto exacto, junto con el permiso de descifrado de la clave administrada por el cliente que corresponda. Esta relación de confianza de IRSA usa el sujeto exacto de ServiceAccount; sustituye de forma coherente el emisor/proveedor OIDC completo y la cuenta:

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

El Namespace, ServiceAccount, SecretProviderClass y Pod siguientes forman el ejemplo de entrega en archivos. Elige la versión de PSS adecuada para el clúster real. JMESPath extrae campos en alias; `secretObjects.data.objectName` nombra esos alias montados. No se admite un campo `property` dentro de secretObjects.data. Los permisos 0444 permiten que este proceso de demostración no root lea los archivos; limita quién puede montar/crear Pods y elige UID/GID y permisos de archivo compatibles con la aplicación real.

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

El Pod comprueba que existan los archivos sin imprimir su contenido. `automountServiceAccountToken: false` deshabilita el montaje automático del token de la API de Kubernetes, no las solicitudes explícitas de tokens del driver CSI. Para usar Pod Identity en lugar de este ejemplo IRSA, utiliza un agente/asociación compatible con el ServiceAccount de la carga de trabajo y `usePodIdentity: "true"`; no supongas que una anotación IRSA crea esa asociación.

El Secret opcional csi-db-credentials solo se sincroniza después de que un Pod monte el volumen. Su ciclo de vida sigue al de los Pods consumidores y puede eliminarse cuando se borren todos ellos. Crear solo un SecretProviderClass no genera un Secret por sí mismo. Inspecciona SecretProviderClassPodStatus y los eventos de controladores/nodos sin volcar los valores.

Para Parameter Store, el valor objects puede contener en su lugar la entrada siguiente, con el permiso de lectura SSM requerido por el proveedor sobre el parámetro propio y el acceso KMS correspondiente para SecureString. Es un fragmento objects, no un SecretProviderClass completo:

```yaml
- objectName: /training/app/config
  objectType: ssmparameter
  objectAlias: app_config
  filePermission: "0444"
```

**Alternativa con ESO:** usa el rol/relación de confianza IRSA EKSSecretReader preparado en el capítulo fuente para el ServiceAccount exacto eso-reader. Con ESO 2.10.0 y sus CRD v1 instalados bajo responsabilidad de su propietario, lo siguiente escribe un destino diferente: eso-db-credentials. El ARN de backend, namespace, rol y propiedades JSON deben corresponder al secreto realmente preparado:

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

Aquí Owner vincula el Secret de destino al ExternalSecret; al borrar al propietario puede activarse la recolección de basura. Retain se refiere a la desaparición del backend, no protege frente al borrado del propietario. El método JWT serviceAccountRef de ESO es IRSA. Pod Identity del controlador es otro diseño: asocia el ServiceAccount del controlador y omite el bloque de autenticación del store; ESO no puede usar serviceAccountRef para suplantar a otra cuenta asociada con Pod Identity.

**Rotación y recarga:** CSI 1.6+ usa llamadas RequiresRepublish de kubelet para la rotación. requiresRepublish por sí solo no habilita la rotación: también se necesita la opción enableSecretRotation del driver. El rotationPollInterval de dos minutos es aquí una duración mínima de caché, no un intervalo garantizado de actualización de extremo a extremo; el tiempo real depende de la republicación de kubelet. El intervalo de actualización de ESO es otro ciclo de reconciliación independiente. Las aplicaciones deben volver a abrir/vigilar los archivos actualizados o realizar un despliegue controlado; los montajes subPath y las variables de entorno existentes no se actualizan automáticamente.

Secrets Manager rotate-secret inicia la rotación inmediatamente de forma predeterminada. Incluso --no-rotate-immediately puede probar una función Lambda de rotación y crear/eliminar AWSPENDING, mientras que aún puede ejecutarse un calendario antiguo basado en frecuencia/días. No es una comprobación inocua, solo de calendario ni de lectura. Revisa los cambios en las credenciales de destino, la validez solapada, la recarga de la aplicación y el rollback antes de invocar la rotación.

**Ejemplo de Terraform sin valores secretos:** sensitive de Terraform solo oculta ciertos resultados mostrados; los valores normales de secret_string/random_password todavía pueden almacenarse en el estado. Lo siguiente administra únicamente metadatos del secreto y usa una clave KMS aprobada existente. Si el secreto ya existe, concilia/importa su propiedad antes de administrarlo desde esta configuración:

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

Esto no crea una versión/valor del secreto ni habilita la rotación. Proporciona el valor inicial mediante el proceso aprobado de entrada de secretos, no mediante una cadena Terraform codificada ni un argumento de comando en texto claro. Protege el estado y los planes incluso cuando solo se esperan metadatos. prevent_destroy es una protección de configuración de Terraform, no una protección irreversible del servicio; quitar el recurso de la configuración u operar fuera de Terraform cambia el contexto de protección.

La validación cubrió Kubernetes nativo y los CRD publicados de SecretProviderClass/ESO, checksums de charts publicados, 22 objetos CSI/ASCP renderizados y una proyección JMESPath real de datos sintéticos. Los campos creationTimestamp generados con valor null se omitieron solo para la comprobación del esquema Swagger. Terraform fmt pasó; no se ejecutaron init/plan/apply. No se obtuvo, montó, sincronizó ni rotó ningún secreto de AWS, y no se probó la recarga de ninguna aplicación.

Referencias: [Configuración de ASCP](https://github.com/aws/secrets-store-csi-driver-provider-aws), [CSI 1.6.1](https://github.com/kubernetes-sigs/secrets-store-csi-driver/releases/tag/v1.6.1), [Sincronización de Secret de CSI](https://secrets-store-csi-driver.sigs.k8s.io/topics/sync-as-kubernetes-secret), [Rotación de CSI](https://secrets-store-csi-driver.sigs.k8s.io/topics/secret-auto-rotation), [Autenticación de ESO con AWS](https://github.com/external-secrets/external-secrets/blob/v2.10.0/docs/provider/aws-access.md), [Cifrado de sobre de EKS](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html), [Rotación de Secrets Manager](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/rotate-secret.html).

</details>
