# Tekton Pipelines: CI nativa de Kubernetes

> **Última actualización**: 12 de septiembre de 2026. Pipelines 1.16.0, Triggers 0.37.0, Chains 0.29.0, Dashboard 0.72.0, tkn 0.46.0.
> **Validación**: Esquemas CRD publicados, dependencias de Tasks, scripts locales y programas simulados. No se ejecutaron instalaciones EKS reales, compilaciones/push de imágenes, firmas KMS, webhooks externos ni notificaciones.

< [Anterior: FinOps](./13-finops-cost-platform.md) | [Índice](./README.md) | [Siguiente: Operaciones zonales](./15-zonal-operations-guide.md) >

## Descripción general

Tekton define Tasks, Pipelines y sus ejecuciones mediante la API Kubernetes. Los operadores siguen gestionando controladores, capacidad de workers, almacenamiento, actualizaciones y acceso. Otros sistemas CI también admiten ejecutores Kubernetes, autoscaling y attestations; evite afirmar soporte exclusivo o coste operativo cero.

El ejemplo ejecuta CI de Go para **la rama main protegida de un repositorio aprobado**: clonado → vet/test paralelos → publicación de imagen candidata → escaneo por digest. El procesamiento Chains y la verificación criptográfica preceden a un cambio GitOps revisado por separado. Los PR de forks externos no deben compartir roles IRSA, PVC ni privilegios de firma de esta Pipeline.

## 1. Modelo de ejecución

| Componente | Rol |
| --- | --- |
| Task / Pipeline | Definiciones reutilizables de trabajo y dependencias |
| TaskRun / PipelineRun | Ejecuciones con parámetros y estado |
| Step / Sidecar | Trabajo secuencial / servicio auxiliar, normalmente en un Pod TaskRun |
| Workspace / Result | Vinculación de volumen / salida pequeña; no son CRD independientes |

Una Task no es un Pod: ejecutar TaskRun lo crea. Results admite cadenas, arrays y objetos; use almacenamiento de artefactos para informes grandes. Los Steps del mismo Pod comparten red y volúmenes, por lo que no son una frontera fuerte entre código mutuamente no confiable.

![Definiciones, ejecuciones, campos Workspace/Result y procesamiento Chains separado](../.gitbook/assets/en-ops-14-tekton-pipelines-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-0.html)

![Servidor API, controladores, webhook y Pods TaskRun con Workspaces por ejecución](../.gitbook/assets/en-ops-14-tekton-pipelines-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-1.html)

## 2. Instalación y permisos de ejecución

### 2.1 Versiones y vías de instalación

El mínimo oficial es Kubernetes 1.28, mientras los campos de seguridad y validación de este capítulo apuntan a Kubernetes 1.36. El mínimo upstream no recomienda versiones EKS actualmente soportadas. Dashboard 0.72.0 admite explícitamente Pipelines 1.15 LTS/1.16 y Triggers 0.37 LTS.

Es una instalación manual fijada. La guía oficial también remite a Tekton Operator para ciclo de vida en producción. Elija propietario antes de mezclar apply manual con recursos del Operator. Estos comandos cambian un clúster real; revise propiedad en vez de forzar conflictos a ciegas.

```bash
kubectl version -o yaml
kubectl get storageclass

curl --fail --location \
  https://infra.tekton.dev/tekton-releases/pipeline/previous/v1.16.0/release.yaml \
  -o pipelines-release.yaml
kubectl apply --server-side --field-manager=tekton-install -f pipelines-release.yaml
kubectl wait --for=condition=Established --timeout=120s \
  crd/tasks.tekton.dev crd/taskruns.tekton.dev \
  crd/pipelines.tekton.dev crd/pipelineruns.tekton.dev
kubectl -n tekton-pipelines wait deployment --all \
  --for=condition=Available --timeout=300s

kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/triggers/previous/v0.37.0/release.yaml
kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/triggers/previous/v0.37.0/interceptors.yaml
kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/chains/previous/v0.29.0/release.yaml
kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/dashboard/previous/v0.72.0/release.yaml
kubectl -n tekton-pipelines port-forward service/tekton-dashboard 9097:9097
```

`release.yaml` instala Dashboard de solo lectura; `release-full.yaml` incluye escritura. Solo lectura no autentica usuarios ni aplica automáticamente permisos por namespace. Valide proxy de autenticación/OIDC y modelo de acceso antes de exponerlo. Un ALB interno no es autenticación. Cognito requiere listener HTTPS real, endpoints Cognito/OIDC y Secret.

`https://tekton.dev/helm-charts` no es un repositorio oficial funcional para este ejemplo. No instale el antiguo chart inexistente ni sus values.

### 2.2 Significado actual de la configuración

| Ajuste | Significado |
| --- | --- |
| `feature-flags.coschedule: workspaces` | Coloca conjuntamente TaskRuns que comparten Workspace PVC; consérvelo en este ejemplo RWO |
| `disable-affinity-assistant` | Flag heredado eliminado después de v0.68 |
| `set-security-context: true` | Predeterminado en 1.16 para contenedores inyectados; los Steps propios necesitan contextos compatibles |
| `results-from: termination-message` | Ruta predeterminada, sujeta a límites del mensaje de terminación Kubernetes |
| `max-result-size` | Aplica a `sidecar-logs`; cambiarlo solo no amplía el mensaje de terminación predeterminado |
| Timeout predeterminado | Gestionado en `config-defaults`; aquí PipelineRun lo establece explícitamente |

`running-in-environment-with-injected-sidecars` no aísla Workspaces y `keep-pod-on-cancel` no es un TTL de retención PipelineRun. No sustituya un ConfigMap completo por un fragmento pequeño.

### 2.3 ServiceAccounts y roles IAM separados

Los controladores usan `tekton-pipelines` / `tekton-chains`; las compilaciones, `tekton-builds`. Las referencias simples a Task/Pipeline resuelven en el mismo namespace. No se referencia una Task de otro namespace solo por nombre.

Cree primero los roles IAM. Cada confianza IRSA debe restringir proveedor OIDC existente, `aud=sts.amazonaws.com` y el `sub=system:serviceaccount:tekton-builds:<SA name>` exacto. Cree repositorios ECR previamente; la compilación no necesita `CreateRepository`. Pese al nombre, `ci-readonly` no tiene un Role API Kubernetes aquí: es la cuenta de ejecución sin privilegios predeterminada.

**`service-accounts.yaml`**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tekton-builds
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ci-readonly
  namespace: tekton-builds
automountServiceAccountToken: false
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ci-image-push
  namespace: tekton-builds
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/tekton-candidate-push
automountServiceAccountToken: false
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ci-image-read
  namespace: tekton-builds
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/tekton-candidate-read
automountServiceAccountToken: false
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ci-triggers
  namespace: tekton-builds
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: ci-triggers
  namespace: tekton-builds
rules:
  - apiGroups: [triggers.tekton.dev]
    resources: [eventlisteners, triggers, triggerbindings, triggertemplates, interceptors]
    verbs: [get, list, watch]
  - apiGroups: [tekton.dev]
    resources: [pipelineruns]
    verbs: [create]
  - apiGroups: [""]
    resources: [configmaps]
    verbs: [get, list, watch]
  - apiGroups: [""]
    resources: [secrets]
    resourceNames: [github-webhook]
    verbs: [get]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ci-triggers
  namespace: tekton-builds
subjects:
  - kind: ServiceAccount
    name: ci-triggers
    namespace: tekton-builds
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: ci-triggers
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: ci-triggers-interceptors
rules:
  - apiGroups: [triggers.tekton.dev]
    resources: [clusterinterceptors, clustertriggerbindings]
    verbs: [get, list, watch]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: ci-triggers-interceptors
subjects:
  - kind: ServiceAccount
    name: ci-triggers
    namespace: tekton-builds
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: ci-triggers-interceptors
```

**`ecr-push-policy.json`**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*",
      "Condition": {
        "StringEquals": {"aws:RequestedRegion": "ap-northeast-2"}
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutImage"
      ],
      "Resource": "arn:aws:ecr:ap-northeast-2:123456789012:repository/myapp-candidates"
    }
  ]
}
```

**`ecr-read-policy.json`**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*",
      "Condition": {
        "StringEquals": {"aws:RequestedRegion": "ap-northeast-2"}
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "arn:aws:ecr:ap-northeast-2:123456789012:repository/myapp-candidates"
    }
  ]
}
```

Adjunte la política de push a `tekton-candidate-push` y la de lectura a `tekton-candidate-read`. Sustituya cuenta, región y repositorio en todos los sitios. `GetAuthorizationToken` no admite alcance por repositorio, por lo que se separa y restringe por región solicitada.

IRSA autentica llamadas AWS SDK/CLI dentro del Pod. Las descargas ECR del kubelet usan roles de nodo, roles Fargate o imagePullSecrets por vías separadas. Una anotación IRSA Task no corrige por sí sola ImagePullBackOff.

## 3. Definiciones completas de Tasks

Estas seis Tasks forman un ejemplo coherente. El repositorio debe contener módulo Go, pruebas y Dockerfile. Sustituya la URL fija `myorg/myapp` del checkout por el repositorio aprobado y ajuste la allowlist Trigger. No acepte URL Git ni comandos shell arbitrarios de un webhook.

Las sustituciones Tekton son textuales. Pase params mediante variables de entorno o argumentos, no interpolados en scripts. Valide commits completos de 40 caracteres. Los archivos de autenticación ECR usan `emptyDir` local de Task; no escriba en volúmenes Secret de solo lectura ni asuma que existen herramientas de la imagen de otro Step.

BuildKit rootless requiere un entorno dedicado validado con namespaces de usuario, montajes y seccomp/AppArmor adecuados. `Unconfined` y `--oci-worker-no-process-sandbox` son compromisos explícitos de seguridad rechazados por políticas restricted. No son valores universalmente seguros. Use otro entorno para PR externos.

**`tasks.yaml`**

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: checkout
  namespace: tekton-builds
spec:
  params:
  - name: revision
    type: string
  workspaces:
  - name: source
  results:
  - name: CHAINS-GIT_URL
    type: string
  - name: CHAINS-GIT_COMMIT
    type: string
  steps:
  - name: checkout
    image: golang:1.27.1
    script: |
      #!/usr/bin/env bash
      set -euo pipefail
      if [[ ! "$REVISION" =~ ^[0-9a-f]{40}$ ]]; then
        echo "Expected a full commit SHA" >&2
        exit 1
      fi
      cd "$SOURCE"
      git init .
      git config credential.helper ''
      git remote add origin "$REPOSITORY"
      git -c protocol.file.allow=never fetch --depth=1 origin "$REVISION"
      git -c advice.detachedHead=false checkout --detach FETCH_HEAD
      test "$(git rev-parse HEAD)" = "$REVISION"
      printf '%s' "$REPOSITORY" > "$GIT_URL_RESULT"
      printf '%s' "$REVISION" > "$GIT_COMMIT_RESULT"
    env:
    - name: REVISION
      value: $(params.revision)
    - name: REPOSITORY
      value: https://github.com/myorg/myapp.git
    - name: SOURCE
      value: $(workspaces.source.path)
    - name: GIT_URL_RESULT
      value: $(results.CHAINS-GIT_URL.path)
    - name: GIT_COMMIT_RESULT
      value: $(results.CHAINS-GIT_COMMIT.path)
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
  stepTemplate:
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
---
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: go-vet
  namespace: tekton-builds
spec:
  params: []
  workspaces:
  - name: source
  results: []
  steps:
  - name: vet
    image: golang:1.27.1
    script: |
      #!/usr/bin/env bash
      set -euo pipefail
      cd "$SOURCE"
      go vet ./...
    env:
    - name: SOURCE
      value: $(workspaces.source.path)
    - name: GOCACHE
      value: /tmp/go-build
    - name: GOMODCACHE
      value: /tmp/go-mod
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
  stepTemplate:
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
---
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: go-test
  namespace: tekton-builds
spec:
  params: []
  workspaces:
  - name: source
  results: []
  steps:
  - name: test
    image: golang:1.27.1
    script: |
      #!/usr/bin/env bash
      set -euo pipefail
      cd "$SOURCE"
      go test -count=1 -race -coverprofile=/tmp/coverage.out ./...
      go tool cover -func=/tmp/coverage.out
    env:
    - name: SOURCE
      value: $(workspaces.source.path)
    - name: GOCACHE
      value: /tmp/go-build
    - name: GOMODCACHE
      value: /tmp/go-mod
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
  stepTemplate:
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
---
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: build-image
  namespace: tekton-builds
spec:
  params:
  - name: image
    type: string
  - name: revision
    type: string
  - name: region
    type: string
  workspaces:
  - name: source
  results:
  - name: IMAGE_URL
    type: string
  - name: IMAGE_DIGEST
    type: string
  steps:
  - name: ecr-token
    image: public.ecr.aws/aws-cli/aws-cli:2.36.44
    script: |
      #!/bin/bash
      set -euo pipefail
      umask 077
      aws ecr get-authorization-token --region "$AWS_REGION" \
        --query 'authorizationData[0].authorizationToken' --output text > /auth/token
    env:
    - name: AWS_REGION
      value: $(params.region)
    - name: AWS_DEFAULT_REGION
      value: $(params.region)
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
    volumeMounts:
    - name: auth
      mountPath: /auth
  - name: docker-config
    image: python:3.12.13-slim
    script: |
      #!/usr/bin/env python3
      import base64, json, os, re
      from pathlib import Path
      image, region = os.environ["IMAGE"], os.environ["REGION"]
      match = re.fullmatch(r"([0-9]{12})\.dkr\.ecr\.([a-z0-9-]+)\.amazonaws\.com/([a-z0-9][a-z0-9._/-]*)", image)
      if not match or match.group(2) != region or ".." in match.group(3):
          raise SystemExit("Use a private ECR repository in the configured region")
      token = Path("/auth/token").read_text().strip()
      decoded = base64.b64decode(token, validate=True)
      if not decoded.startswith(b"AWS:") or len(decoded) <= 4:
          raise SystemExit("Invalid ECR authorization token")
      Path("/auth/config.json").write_text(json.dumps({"auths": {image.split("/")[0]: {"auth": token}}}))
      Path("/auth/config.json").chmod(0o600)
      Path("/auth/token").unlink()
    env:
    - name: IMAGE
      value: $(params.image)
    - name: REGION
      value: $(params.region)
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
    volumeMounts:
    - name: auth
      mountPath: /auth
  - name: build-and-push
    image: moby/buildkit:v0.33.0-rootless
    script: |
      #!/bin/sh
      set -eu
      case "$REVISION" in *[!0-9a-f]*|"") echo "Invalid commit tag" >&2; exit 1;; esac
      test "${#REVISION}" -eq 40
      buildctl-daemonless.sh build \
        --frontend dockerfile.v0 \
        --local "context=$SOURCE" --local "dockerfile=$SOURCE" \
        --output "type=image,name=$IMAGE:$REVISION,push=true" \
        --metadata-file /build-result/metadata.json
    env:
    - name: SOURCE
      value: $(workspaces.source.path)
    - name: IMAGE
      value: $(params.image)
    - name: REVISION
      value: $(params.revision)
    - name: DOCKER_CONFIG
      value: /auth
    - name: BUILDKITD_FLAGS
      value: --oci-worker-no-process-sandbox
    computeResources:
      requests:
        cpu: '1'
        memory: 1Gi
      limits:
        memory: 4Gi
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
      seccompProfile:
        type: Unconfined
      appArmorProfile:
        type: Unconfined
    volumeMounts:
    - name: auth
      mountPath: /auth
      readOnly: true
    - name: buildkit-state
      mountPath: /home/user/.local/share/buildkit
    - name: build-result
      mountPath: /build-result
  - name: record-digest
    image: python:3.12.13-slim
    script: |
      #!/usr/bin/env python3
      import json, os, re
      from pathlib import Path
      data = json.loads(Path("/build-result/metadata.json").read_text())
      digest = data.get("containerimage.digest", "")
      if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
          raise SystemExit("BuildKit did not return an image digest")
      Path(os.environ["URL_RESULT"]).write_text(os.environ["IMAGE"])
      Path(os.environ["DIGEST_RESULT"]).write_text(digest)
    env:
    - name: IMAGE
      value: $(params.image)
    - name: URL_RESULT
      value: $(results.IMAGE_URL.path)
    - name: DIGEST_RESULT
      value: $(results.IMAGE_DIGEST.path)
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
    volumeMounts:
    - name: build-result
      mountPath: /build-result
      readOnly: true
  volumes:
  - name: auth
    emptyDir: {}
  - name: buildkit-state
    emptyDir: {}
  - name: build-result
    emptyDir: {}
  stepTemplate:
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
---
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: scan-image
  namespace: tekton-builds
spec:
  params:
  - name: image
    type: string
  - name: digest
    type: string
  - name: region
    type: string
  workspaces: []
  results: []
  steps:
  - name: ecr-token
    image: public.ecr.aws/aws-cli/aws-cli:2.36.44
    script: |
      #!/bin/bash
      set -euo pipefail
      umask 077
      aws ecr get-authorization-token --region "$AWS_REGION" \
        --query 'authorizationData[0].authorizationToken' --output text > /auth/token
    env:
    - name: AWS_REGION
      value: $(params.region)
    - name: AWS_DEFAULT_REGION
      value: $(params.region)
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
    volumeMounts:
    - name: auth
      mountPath: /auth
  - name: docker-config
    image: python:3.12.13-slim
    script: |
      #!/usr/bin/env python3
      import base64, json, os, re
      from pathlib import Path
      image, region = os.environ["IMAGE"], os.environ["REGION"]
      match = re.fullmatch(r"([0-9]{12})\.dkr\.ecr\.([a-z0-9-]+)\.amazonaws\.com/([a-z0-9][a-z0-9._/-]*)", image)
      if not match or match.group(2) != region or ".." in match.group(3):
          raise SystemExit("Use a private ECR repository in the configured region")
      token = Path("/auth/token").read_text().strip()
      decoded = base64.b64decode(token, validate=True)
      if not decoded.startswith(b"AWS:") or len(decoded) <= 4:
          raise SystemExit("Invalid ECR authorization token")
      Path("/auth/config.json").write_text(json.dumps({"auths": {image.split("/")[0]: {"auth": token}}}))
      Path("/auth/config.json").chmod(0o600)
      Path("/auth/token").unlink()
    env:
    - name: IMAGE
      value: $(params.image)
    - name: REGION
      value: $(params.region)
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
    volumeMounts:
    - name: auth
      mountPath: /auth
  - name: scan
    image: aquasec/trivy:0.74.0
    script: |
      #!/bin/sh
      set -eu
      trivy image --scanners vuln --severity HIGH,CRITICAL \
        --exit-code 1 --format json --output /tmp/trivy-report.json "$IMAGE@$DIGEST"
    env:
    - name: IMAGE
      value: $(params.image)
    - name: DIGEST
      value: $(params.digest)
    - name: DOCKER_CONFIG
      value: /auth
    - name: TRIVY_CACHE_DIR
      value: /tmp/trivy-cache
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
    volumeMounts:
    - name: auth
      mountPath: /auth
      readOnly: true
  volumes:
  - name: auth
    emptyDir: {}
  stepTemplate:
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
---
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: report-status
  namespace: tekton-builds
spec:
  params:
  - name: run
    type: string
  - name: status
    type: string
  workspaces: []
  results: []
  steps:
  - name: report
    image: python:3.12.13-slim
    script: |
      #!/usr/bin/env python3
      import json, os
      print(json.dumps({"pipelineRun": os.environ["RUN"], "status": os.environ["STATUS"]}))
    env:
    - name: RUN
      value: $(params.run)
    - name: STATUS
      value: $(params.status)
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
  stepTemplate:
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
```

El repositorio original Google Kaniko está archivado; este ejemplo usa BuildKit 0.33.0. Rootless no garantiza aislamiento completo de procesos. Antes de producción, verifique/fije digests y plataformas y pruebe rutas escribibles y contextos de seguridad en nodos reales.

El código de salida 1 por hallazgos y otros códigos de error del escáner fallan la Task. Un informe ausente no debe convertirse en «cero vulnerabilidades». `/tmp/trivy-report.json` es temporal; expórtelo a almacenamiento aprobado antes de limpiar si requiere retención larga.

## 4. Pipeline y ejecución

![Clonado, test/vet paralelos, publicación/escaneo candidato e informe final de mejor esfuerzo](../.gitbook/assets/en-ops-14-tekton-pipelines-2.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-2.html)

**`pipeline.yaml`**

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: trusted-image-ci
  namespace: tekton-builds
spec:
  params:
    - name: revision
      type: string
    - name: image
      type: string
    - name: region
      type: string
      default: ap-northeast-2
  workspaces:
    - name: source
  results:
    - name: CHAINS-GIT_URL
      value: $(tasks.clone.results.CHAINS-GIT_URL)
    - name: CHAINS-GIT_COMMIT
      value: $(tasks.clone.results.CHAINS-GIT_COMMIT)
    - name: IMAGE_URL
      value: $(tasks.build.results.IMAGE_URL)
    - name: IMAGE_DIGEST
      value: $(tasks.build.results.IMAGE_DIGEST)
  tasks:
    - name: clone
      taskRef:
        name: checkout
      params:
        - name: revision
          value: $(params.revision)
      workspaces:
        - name: source
          workspace: source
    - name: lint
      runAfter: [clone]
      taskRef:
        name: go-vet
      workspaces:
        - name: source
          workspace: source
    - name: test
      runAfter: [clone]
      taskRef:
        name: go-test
      workspaces:
        - name: source
          workspace: source
    - name: build
      runAfter: [lint, test]
      taskRef:
        name: build-image
      params:
        - name: image
          value: $(params.image)
        - name: revision
          value: $(tasks.clone.results.CHAINS-GIT_COMMIT)
        - name: region
          value: $(params.region)
      workspaces:
        - name: source
          workspace: source
    - name: scan
      runAfter: [build]
      taskRef:
        name: scan-image
      params:
        - name: image
          value: $(tasks.build.results.IMAGE_URL)
        - name: digest
          value: $(tasks.build.results.IMAGE_DIGEST)
        - name: region
          value: $(params.region)
  finally:
    - name: report
      taskRef:
        name: report-status
      params:
        - name: run
          value: $(context.pipelineRun.name)
        - name: status
          value: $(tasks.status)
```

**`pipelinerun.yaml`**

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  generateName: trusted-image-ci-
  namespace: tekton-builds
spec:
  pipelineRef:
    name: trusted-image-ci
  params:
    - name: revision
      value: REPLACE_WITH_FULL_40_CHARACTER_COMMIT_SHA
    - name: image
      value: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp-candidates
  workspaces:
    - name: source
      volumeClaimTemplate:
        spec:
          accessModes: [ReadWriteOnce]
          storageClassName: gp3
          resources:
            requests:
              storage: 10Gi
  taskRunTemplate:
    serviceAccountName: ci-readonly
    podTemplate:
      automountServiceAccountToken: false
      securityContext:
        fsGroup: 1000
  taskRunSpecs:
    - pipelineTaskName: build
      serviceAccountName: ci-image-push
    - pipelineTaskName: scan
      serviceAccountName: ci-image-read
  timeouts:
    pipeline: 1h
    tasks: 50m
    finally: 5m
```

```bash
kubectl apply -f service-accounts.yaml
kubectl apply -f tasks.yaml -f pipeline.yaml
# Replace the commit placeholder and provision the referenced IAM roles first.
kubectl create -f pipelinerun.yaml
tkn pipelinerun logs --last -n tekton-builds --follow --exit-with-pipelinerun-error
```

Se crea un PVC nuevo por ejecución. ReadWriteOnce permite varios Pods en el mismo nodo, no RWX entre nodos. emptyDir no comparte almacenamiento entre distintos Pods TaskRun. Separe cachés por nivel de confianza y coordine escritores concurrentes.

`finally` se ejecuta después de las Tasks ordinarias, pero no incondicionalmente. Referencias a Results ausentes pueden omitirlo; cancelación, timeout total, fallos de recursos y referencias sin resolver también pueden impedirlo. El ejemplo solo informa nombre y `tasks.status`, evitando Results de imagen que quizá nunca se produjeron. No asuma orden entre varias Tasks finally.

## 5. Webhooks y Triggers

Este Trigger verifica primero GitHub HMAC y luego **repositorio, rama, estado de eliminación y SHA completo**. URL Git, ruta ECR, nombres Task y ServiceAccounts permanecen fijos en definiciones confiables. No conecte eventos de PR externos a esta plantilla. HMAC verifica origen de entrega; no autoriza código PR para desplegar.

![Entrega verificada y filtros de repositorio/rama crean una PipelineRun fija para un commit aprobado](../.gitbook/assets/en-ops-14-tekton-pipelines-3.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-3.html)

**`triggers.yaml`**

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: trusted-github
  namespace: tekton-builds
spec:
  serviceAccountName: ci-triggers
  triggers:
    - name: protected-main-push
      interceptors:
        - ref:
            name: github
          params:
            - name: secretRef
              value:
                secretName: github-webhook
                secretKey: token
            - name: eventTypes
              value: [push]
        - ref:
            name: cel
          params:
            - name: filter
              value: >-
                body.repository.full_name == 'myorg/myapp' &&
                body.ref == 'refs/heads/main' &&
                body.deleted == false &&
                body.after.matches('^[0-9a-f]{40}$')
      bindings:
        - ref: trusted-commit
      template:
        ref: trusted-image-ci
---
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerBinding
metadata:
  name: trusted-commit
  namespace: tekton-builds
spec:
  params:
    - name: revision
      value: $(body.after)
---
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerTemplate
metadata:
  name: trusted-image-ci
  namespace: tekton-builds
spec:
  params:
    - name: revision
  resourcetemplates:
    - apiVersion: tekton.dev/v1
      kind: PipelineRun
      metadata:
        generateName: trusted-image-ci-
        namespace: tekton-builds
      spec:
        pipelineRef:
          name: trusted-image-ci
        params:
          - name: revision
            value: $(tt.params.revision)
          - name: image
            value: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp-candidates
        workspaces:
          - name: source
            volumeClaimTemplate:
              spec:
                accessModes: [ReadWriteOnce]
                storageClassName: gp3
                resources:
                  requests:
                    storage: 10Gi
        taskRunTemplate:
          serviceAccountName: ci-readonly
          podTemplate:
            automountServiceAccountToken: false
            securityContext:
              fsGroup: 1000
        taskRunSpecs:
          - pipelineTaskName: build
            serviceAccountName: ci-image-push
          - pipelineTaskName: scan
            serviceAccountName: ci-image-read
        timeouts:
          pipeline: 1h
          tasks: 50m
          finally: 5m
```

El `token` del Secret `github-webhook` debe coincidir con el secreto GitHub. Proporciónelo desde almacenamiento protegido, nunca Git. Configure por separado HTTPS externo y reintentos/deduplicación de entregas. EventListener tiene un Service interno por defecto; este YAML no crea por sí solo un endpoint Internet.

Conserve el cuerpo original durante terminación TLS y procesamiento gateway/Ingress para verificar HMAC. Aplique autenticación, rate limits, disponibilidad y rutas fijas al callback. Un período silencioso no implica automáticamente una caída de webhook: inspeccione entregas reales y errores EventListener.

No asuma que `head_commit` siempre existe ni trunque `refs/heads/feature/a` usando un solo elemento split. Los filtros de archivos deben considerar rutas añadidas, modificadas y eliminadas y límites de payload. El ejemplo no inventa un filtro específico del negocio.

## 6. Chains y verificación de firmas

### 6.1 Éxito CI y finalización de firma son independientes

Chains es un controlador separado que procesa TaskRuns/PipelineRuns completadas. Una firma de imagen no demuestra que todas las pruebas y el escaneo pasaran. `chains.tekton.dev/signed=true` no es aprobación de despliegue ni verificación criptográfica.

La procedencia a nivel Pipeline se crea después de completarla. Esperar dentro de ella a su propia attestation puede entrar en conflicto con ese orden. El ejemplo verifica y promociona por separado tras finalizar CI.

![Comprobar CI, verificar firmas/procedencia Chains y promocionar solo el digest aprobado](../.gitbook/assets/en-ops-14-tekton-pipelines-4.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-4.html)

### 6.2 Configuración KMS

Use una clave KMS asimétrica `SIGN_VERIFY` existente. Sustituya ARN y `builder.id`. Configure un rol IRSA separado en la **ServiceAccount del controlador Chains `tekton-chains/tekton-chains-controller`**, con escritura ECR en el repositorio candidato y los permisos KMS siguientes. Dar IRSA al Pod de build no da esas credenciales al controlador.

El backend OCI actual usa búsqueda de credenciales Kubernetes y cadenas predeterminadas/asistentes ECR. Configure la identidad AWS disponible en el entorno del controlador y verifique la subida real de firmas. El emptyDir `/auth` de una Task no es un Secret compartido legible por Chains.

**`chains-kms-policy.json`**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["kms:Sign", "kms:GetPublicKey", "kms:DescribeKey"],
    "Resource": "arn:aws:kms:ap-northeast-2:123456789012:key/REPLACE_KEY_ID"
  }]
}
```

**`chains-config.yaml`**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: chains-config
  namespace: tekton-chains
data:
  artifacts.taskrun.storage: ""
  artifacts.pipelinerun.format: slsa/v2alpha3
  artifacts.pipelinerun.storage: oci
  artifacts.pipelinerun.signer: kms
  artifacts.oci.format: simplesigning
  artifacts.oci.storage: oci
  artifacts.oci.signer: kms
  signers.kms.kmsref: awskms:///arn:aws:kms:ap-northeast-2:123456789012:key/REPLACE_KEY_ID
  signers.x509.fulcio.enabled: "false"
  transparency.enabled: "false"
  storage.oci.encoding-format: dsse
  builder.id: https://ci.example.com/tekton/trusted-image-ci
  builddefinition.buildtype: https://tekton.dev/chains/v2/slsa
```

El formateador `slsa/v1` no significa SLSA provenance v1.0. En Chains actual, `slsa/v1` / `in-toto` corresponden a v0.2, y `slsa/v2alpha3` / `slsa/v2alpha4` a v1.0. El ejemplo usa `slsa/v2alpha3` a nivel Pipeline, desactiva almacenamiento de procedencia Task duplicado y habilita firmas de imagen por separado.

`storage.oci.encoding-format: dsse` conserva almacenamiento heredado `.sig` / `.att`. `sigstore-bundle` de 0.29 usa referrers OCI 1.1; cambie almacenamiento y verificación conjuntamente. Aquí no se sube a Rekor, por lo que se verifica explícitamente según una política interna de clave pública. Configure transparencia aparte si se exige, revisando metadatos de build expuestos.

La firma keyless requiere un issuer confiable para el Fulcio real y un token válido. Poner una cadena issuer GitHub Actions en un Pod EKS no autentica. Firmas y attestations por sí solas no establecen un nivel SLSA concreto.

### 6.3 Verificar ejecución y artefactos independientemente

El script comprueba una PipelineRun **leída de una API confiable** para confirmar CI correcto, Chains completado y repositorio, commit e imágenes aprobados. No verifica firmas. También se requieren las comprobaciones Cosign posteriores y revisión de política de procedencia.

**`check_run.py`**

```python
"""Check trusted API output before separate cryptographic artifact verification."""
import argparse
import json
import re
from pathlib import Path


def check(run, repository, revision, image):
    if run.get("kind") != "PipelineRun" or run.get("apiVersion") != "tekton.dev/v1":
        raise ValueError("Expected a tekton.dev/v1 PipelineRun")
    metadata = run.get("metadata", {})
    if metadata.get("namespace") != "tekton-builds" or not metadata.get("uid"):
        raise ValueError("Unexpected namespace or missing run UID")
    if run.get("spec", {}).get("pipelineRef", {}).get("name") != "trusted-image-ci":
        raise ValueError("Unexpected pipeline")
    succeeded = [c for c in run.get("status", {}).get("conditions", []) if c.get("type") == "Succeeded"]
    if len(succeeded) != 1 or succeeded[0].get("status") != "True":
        raise ValueError("CI has not succeeded")
    if not run.get("status", {}).get("completionTime"):
        raise ValueError("CI completion time is missing")
    if metadata.get("annotations", {}).get("chains.tekton.dev/signed") != "true":
        raise ValueError("Chains has not completed; retry later with a fresh API read")
    results = {}
    for result in run.get("status", {}).get("results", []):
        if result["name"] in results:
            raise ValueError("Duplicate result")
        results[result["name"]] = result["value"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Expected full source revision")
    expected = {"CHAINS-GIT_URL": repository, "CHAINS-GIT_COMMIT": revision, "IMAGE_URL": image}
    if any(results.get(k) != v for k, v in expected.items()):
        raise ValueError("Run outputs do not match the approved source and repository")
    digest = results.get("IMAGE_DIGEST", "")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("Missing or invalid image digest")
    return image + "@" + digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    try:
        print(check(json.loads(args.run.read_text()), args.repository, args.revision, args.image))
    except (ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Run gate failed: {error}\n")
```

```bash
set -euo pipefail
DOCS_RUN="REPLACE_PIPELINERUN_NAME"
DOCS_REVISION="REPLACE_WITH_FULL_40_CHARACTER_COMMIT_SHA"
DOCS_IMAGE="123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp-candidates"
kubectl -n tekton-builds get pipelinerun "$DOCS_RUN" -o json > run.json
DOCS_IMAGE_REF="$(python3 check_run.py --run run.json \
  --repository https://github.com/myorg/myapp.git \
  --revision "$DOCS_REVISION" --image "$DOCS_IMAGE")"

# chains.pub must be the independently trusted public key for the configured KMS key.
# Registry read authentication must already be configured.
# Explicit private-key policy: verify signatures, without requiring a Rekor entry.
cosign verify --key chains.pub --insecure-ignore-tlog=true "$DOCS_IMAGE_REF" \
  > verified-signature.json
cosign verify-attestation --key chains.pub --insecure-ignore-tlog=true \
  --type https://slsa.dev/provenance/v1 "$DOCS_IMAGE_REF" \
  > verified-attestations.json
```

`--insecure-ignore-tlog` elige explícitamente no exigir una entrada Rekor pública. La verificación contra la clave confiable sigue activa. Si la organización exige transparencia, configure esa cadena en vez de esta excepción.

Aplique política al digest subject de la attestation verificada, `runDetails.builder.id`, `buildDefinition.buildType`, URI/commit de origen exactos y definiciones Task/Pipeline aprobadas. Una firma válida de cualquier productor o una attestation de otro build no basta. Los comandos no implementan automáticamente esas comprobaciones organizativas.

Configure admisión por separado para la misma clave/identidad, digest y condiciones de procedencia. No aplique marcadores incompletos `BEGIN PUBLIC KEY ...` ni compare campos predicate inexistentes. Revise ImageValidatingPolicy de Kyverno y autenticación de registro para la versión instalada; pruebe aceptaciones/rechazos con claves correctas/erróneas, orígenes e imágenes sin firmar.

## 7. Relevo a GitOps

Actualice Kustomize/Helm real con `repository@sha256:...` verificado. Este capítulo no incluye una Task que haga push, abra o fusione PR automáticamente. Un propietario o flujo de promoción aprobado aparte edita repositorios/archivos fijos y fusiona tras CI y revisión. Evite que despliegues kubectl de Tekton y ArgoCD gestionen los mismos manifiestos.

![Revisar cambio GitOps con digest verificado; ArgoCD sincroniza manifiestos y kubelets descargan imágenes](../.gitbook/assets/en-ops-14-tekton-pipelines-5.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-5.html)

```bash
# In a reviewed checkout with the Kustomize CLI installed:
cd overlays/production
kustomize edit set image "myapp=$DOCS_IMAGE_REF"
kustomize build . > /tmp/rendered-myapp.yaml
git diff -- kustomization.yaml
# Run repository checks and submit the focused change for review.
```

Separar referencias con `cut -d: -f1/2` rompe puertos de registro y digests. Pase la referencia completa. Proporcione known_hosts SSH por una vía confiable; ssh-keyscan sin verificar no es un ancla de confianza. Las credenciales copiadas al home de un Step no se comparten automáticamente con otro.

ArgoCD sincroniza manifiestos Git; kubelets/runtimes descargan imágenes. Compruebe salud de aplicación aparte de la sincronización. La reversión no restaura automáticamente datos o cambios de esquema.

## 8. Operaciones y limpieza

### 8.1 Registros de ejecución y PVC

`keep` y `keep-since` son opciones de herramientas como comandos de eliminación tkn, no un TTL PipelineRun integrado. tkn 0.46.0 `pipelinerun delete` no tiene `--dry-run`. Revise retención de logs, informes de escaneo, firmas/procedencia y auditoría antes de borrar. No elimine todos los Pods exitosos sin política de antigüedad.

La herramienta muestra **solo candidatos para revisión** en un namespace: ejecuciones exitosas terminadas hace más de siete días y fallidas hace más de catorce. Usa finalización, no creación, y exige confirmaciones Chains y de archivo. `ci.example.com/archive-complete` es una anotación del operador registrada tras archivar realmente, no un campo automático Tekton. El script no llama a Kubernetes API ni elimina recursos.

**`cleanup_candidates.py`**

```python
"""Print names for review; this script never deletes Kubernetes objects."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timezone required")
    return parsed.astimezone(timezone.utc)


def candidates(document, now, namespace):
    if now.tzinfo is None:
        raise ValueError("Timezone required")
    result, skipped = [], []
    for obj in document.get("items", []):
        meta, status = obj.get("metadata", {}), obj.get("status", {})
        name = meta.get("name", "<unnamed>")
        conditions = [c for c in status.get("conditions", []) if c.get("type") == "Succeeded"]
        annotations = meta.get("annotations", {})
        if (obj.get("kind") != "PipelineRun" or meta.get("namespace") != namespace
                or not meta.get("uid") or len(conditions) != 1
                or conditions[0].get("status") not in ("True", "False")):
            skipped.append({"name": name, "reason": "not a terminal run in the selected namespace"})
            continue
        if annotations.get("ci.example.com/retain") == "true":
            skipped.append({"name": name, "reason": "retention hold"})
            continue
        if (annotations.get("chains.tekton.dev/signed") != "true"
                or annotations.get("ci.example.com/archive-complete") != "true"):
            skipped.append({"name": name, "reason": "Chains processing or archive acknowledgement incomplete"})
            continue
        try:
            completed = timestamp(status["completionTime"])
        except (ValueError, KeyError, TypeError, AttributeError):
            skipped.append({"name": name, "reason": "invalid completion time"})
            continue
        retention_days = 7 if conditions[0]["status"] == "True" else 14
        if completed < now - timedelta(days=retention_days):
            result.append({"namespace": namespace, "name": name, "uid": meta["uid"],
                           "completed": completed.isoformat(), "retentionDays": retention_days})
    return {"mode": "review-only", "candidates": result, "skipped": skipped}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--namespace", default="tekton-builds")
    parser.add_argument("--now", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    print(json.dumps(candidates(json.loads(args.input.read_text()), timestamp(args.now), args.namespace), indent=2))
```

```bash
kubectl -n tekton-builds get pipelineruns -o json > runs.json
python3 cleanup_candidates.py --input runs.json --namespace tekton-builds
```

El ciclo de vida PVC depende de `coschedule`.

| Modo | PVC volumeClaimTemplate tras finalizar |
| --- | --- |
| `workspaces` | Se conserva por defecto; la anotación Run `tekton.dev/auto-cleanup-pvc: "true"` habilita limpieza al terminar |
| `pipelineruns`, `isolate-pipelinerun` | Se limpia al finalizar |
| `disabled` | GC por referencia de propietario; verifique el comportamiento al eliminar Run |

La anotación no borra PVC existentes vinculados directamente a Workspaces. No active limpieza automática de datos que aún deban archivarse. Inspeccione ownerReferences antes de declarar TaskRuns huérfanas.

### 8.2 Monitorización

Pipelines 1.16 exporta métricas con OpenTelemetry. Con `metrics-protocol: prometheus` en `config-observability`, el puerto Service del controlador se llama **`http-metrics`**. Haga coincidir selección ServiceMonitor y Prometheus.

**`servicemonitor.yaml`**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: tekton-pipelines
  namespace: observability
  labels:
    release: prometheus
spec:
  namespaceSelector:
    matchNames: [tekton-pipelines]
  selector:
    matchLabels:
      app.kubernetes.io/component: controller
      app.kubernetes.io/part-of: tekton-pipelines
  endpoints:
    - port: http-metrics
      path: /metrics
      interval: 30s
      honorLabels: true
```

**`monitoring-rules.yaml`**

```yaml
groups:
  - name: tekton-ci
    rules:
      - record: tekton:completed_duration_seconds:mean1h
        expr: |
          sum(rate(tekton_pipelines_controller_pipelinerun_duration_seconds_sum[1h]))
          /
          sum(rate(tekton_pipelines_controller_pipelinerun_duration_seconds_count[1h]))
      - alert: TektonCompletedRunFailureRatio
        expr: |
          (
            sum(increase(tekton_pipelines_controller_pipelinerun_total{status="failed"}[1h]))
            /
            sum(increase(tekton_pipelines_controller_pipelinerun_total{status=~"success|failed"}[1h]))
            > 0.30
          )
          and
          (
            sum(increase(tekton_pipelines_controller_pipelinerun_total{status=~"success|failed"}[1h])) >= 10
          )
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "More than 30% failed among at least 10 completed non-cancelled CI runs"
      - alert: TektonControllerMetricsUnavailable
        expr: |
          absent(up{namespace="tekton-pipelines",service="tekton-pipelines-controller",endpoint="http-metrics"} == 1)
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "No healthy scrape target for the Tekton controller"
```

El archivo usa formato ordinario de reglas Prometheus; colóquelo bajo `PrometheusRule.spec` con el Operator. Los conteos completados usan `pipelinerun_total`; los activos, `running_pipelineruns`. Los estados del contador son `success`, `failed` y `cancelled`, sin etiqueta namespace. Aquí se comparan éxitos/fallos de todo el clúster excluyendo cancelaciones.

Calcule duración media mediante **la suma de los sum de histogramas dividida por la suma de counts**. Promediar medias por serie no da la media global. Una métrica de duración completada con `status=running` no da antigüedad transcurrida de ejecuciones activas. Inspeccione startTime, condiciones y estado Pod reales.

### 8.3 Diagnóstico y logs

```bash
tkn pipelinerun describe "$DOCS_RUN" -n tekton-builds
tkn pipelinerun logs "$DOCS_RUN" -n tekton-builds --log-failed
tkn pipelinerun logs "$DOCS_RUN" -n tekton-builds --task build
kubectl -n tekton-builds get pipelinerun "$DOCS_RUN" -o yaml
kubectl -n tekton-builds describe pod -l "tekton.dev/pipelineRun=$DOCS_RUN"
kubectl -n tekton-pipelines logs deployment/tekton-pipelines-controller --tail=100
kubectl -n tekton-chains logs deployment/tekton-chains-controller --tail=100
```

`--last` selecciona la última ejecución, no la última fallida. Lea condiciones JSON, no selectores de campo de condiciones CRD no admitidos. Consulte las etiquetas namespace/PipelineRun realmente recogidas por Loki/Alloy. Recoger solo archivos del namespace de controladores omite builds de `tekton-builds`.

Para Pods Pending, revise cuota, nodo, PVC y eventos de planificación. Cambiar gp3 RWO por RWX en YAML no lo convierte en EFS. Más timeout no arregla Results excesivos, permisos, Tasks ausentes ni herramientas faltantes.

## 9. Reutilización y decisiones operativas

- **Sidecars**: Use readiness de DB y conexiones reales. Dormir no prueba disponibilidad. Revise funciones de sidecar nativo y terminación de la versión instalada.
- **StepAction**: Es estable en 1.16, pero la API de almacenamiento sigue siendo `tekton.dev/v1beta1`. Conecte herramientas, credenciales y rutas de resultados reales a la Task consumidora.
- **Catálogos**: La retirada del servicio Hub y su integración interna en CLI son diferentes. Los comandos Hub de tkn 0.46 no garantizan disponibilidad futura. Gestione definiciones aprobadas con commits fijos o digests OCI verificados y restrinja resolvers.
- **Redes**: NetworkPolicy `to: []` con TCP 443 permite ese puerto a todos los destinos; no es una allowlist ECR/GitHub. Restrinja DNS, STS/ECR/S3, registros y API necesarios mediante el diseño real CNI/proxy/VPC.
- **Spot y coste**: Karpenter usa `karpenter.sh/capacity-type: spot`; EKS Managed Node Groups usan sus etiquetas reales `eks.amazonaws.com/capacityType`. Considere interrupciones, reintentos, cuota y almacenamiento. Sin Pods de build activos no significa coste total cero.
- **Cachés**: Mida reutilización por carga. No prometa una mejora universal de 40–60%. Niveles de confianza distintos no deben compartir cachés escribibles.

## 10. Referencias

- [Pipelines 1.16.0](https://github.com/tektoncd/pipeline/releases/tag/v1.16.0)
- [Triggers 0.37.0](https://github.com/tektoncd/triggers/releases/tag/v0.37.0)
- [Chains 0.29.0](https://github.com/tektoncd/chains/releases/tag/v0.29.0)
- [Dashboard 0.72.0](https://github.com/tektoncd/dashboard/releases/tag/v0.72.0)
- [Modelo de seguridad de Pipelines](https://github.com/tektoncd/pipeline/blob/v1.16.0/docs/security/README.md)
- [Afinidad y ciclo de vida PVC](https://github.com/tektoncd/pipeline/blob/v1.16.0/docs/affinityassistants.md)
- [Métricas de Pipelines](https://github.com/tektoncd/pipeline/blob/v1.16.0/docs/metrics.md)
- [Configuración Chains](https://github.com/tektoncd/chains/blob/v0.29.0/docs/config.md)
- [Formateador SLSA e indicaciones de tipos](https://github.com/tektoncd/chains/blob/v0.29.0/docs/slsa-provenance.md)
- [Requisitos rootless de BuildKit](https://github.com/moby/buildkit/blob/v0.33.0/docs/rootless.md)
- [Cosign 3.1.3](https://github.com/sigstore/cosign/releases/tag/v3.1.3)
- [Infraestructura CI](./03-ci-pipelines.md)
- [GitOps multiclúster](./04-gitops-multi-cluster.md)
- [Stack de observabilidad](./09-observability-stack.md)
