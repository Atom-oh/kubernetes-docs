# Tekton Pipelines: CI nativa de Kubernetes

> **Última actualización**: 16 de octubre de 2026. Pipelines 1.17.0, Triggers 0.37.1, Chains 0.29.0, Dashboard 0.73.0, tkn 0.46.1.
> **Validación**: esquemas de CRD de la versión, dependencias de Tasks, scripts locales y programas simulados. No se ejecutaron instalaciones activas en EKS, compilaciones ni publicaciones de imágenes, firmas con KMS, webhooks externos ni notificaciones.

< [Anterior: FinOps](./13-finops-cost-platform.md) | [Contenido](./README.md) | [Siguiente: Operaciones zonales](./15-zonal-operations-guide.md) >

## Descripción general

Tekton define Tasks, Pipelines y sus ejecuciones mediante la API de Kubernetes. Los operadores siguen gestionando los controladores, la capacidad de los workers, el almacenamiento, las actualizaciones y el acceso. Otros sistemas de CI también pueden admitir ejecutores de Kubernetes, escalado automático y atestaciones; evita afirmar que Tekton es el único que los admite o que no tiene costos operativos.

Este ejemplo ejecuta CI para una aplicación Go desde **la rama main protegida de un repositorio aprobado**: clonar → vet/test en paralelo → publicar una imagen candidata → escanearla por digest. El procesamiento de Chains y la verificación criptográfica preceden a un cambio de GitOps que se revisa por separado. Los PR de forks externos no deben compartir los roles de IRSA, los PVC ni los privilegios de firma de este Pipeline.

## 1. Modelo de ejecución

| Componente | Función |
| --- | --- |
| Task / Pipeline | Definiciones reutilizables de trabajo y dependencias |
| TaskRun / PipelineRun | Ejecuciones con parámetros y estado |
| Step / Sidecar | Trabajo secuencial / servicio auxiliar, normalmente dentro de un Pod de TaskRun |
| Workspace / Result | Asociación de un volumen / valor de salida pequeño; no son CRD independientes |

Una definición de Task no es por sí misma un Pod: la ejecución de un TaskRun crea uno. Los Results admiten tipos string, array y object; usa almacenamiento de artefactos para informes grandes. Los Steps de un mismo Pod comparten la red y los volúmenes, por lo que no constituyen una barrera sólida entre código que no es de confianza mutua.

![Definiciones, ejecuciones, campos Workspace/Result y procesamiento independiente de Chains](../.gitbook/assets/en-ops-14-tekton-pipelines-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-0.html)

![Servidor de API, controladores, webhook y Pods de TaskRun con Workspaces por ejecución](../.gitbook/assets/en-ops-14-tekton-pipelines-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-1.html)

## 2. Instalación y permisos de ejecución

### 2.1 Versiones y vías de instalación

El mínimo oficial para la instalación es Kubernetes 1.28, mientras que los campos de seguridad y la validación de esquemas de este capítulo se dirigen a Kubernetes 1.36. El mínimo de upstream no es una recomendación para las versiones de EKS con soporte vigente. Dashboard 0.73.0 declara explícitamente compatibilidad con Pipelines 1.15 LTS/1.17 y Triggers 0.37 LTS.

Este es un ejemplo de instalación manual con versiones fijadas. La guía oficial también señala Tekton Operator para la gestión del ciclo de vida en producción. Decide quién será responsable antes de combinar una aplicación manual con recursos gestionados por Operator. Estos comandos modifican un clúster real; revisa la titularidad en vez de forzar conflictos a ciegas.

```bash
kubectl version -o yaml
kubectl get storageclass

curl --fail --location \
  https://infra.tekton.dev/tekton-releases/pipeline/previous/v1.17.0/release.yaml \
  -o pipelines-release.yaml
kubectl apply --server-side --field-manager=tekton-install -f pipelines-release.yaml
kubectl wait --for=condition=Established --timeout=120s \
  crd/tasks.tekton.dev crd/taskruns.tekton.dev \
  crd/pipelines.tekton.dev crd/pipelineruns.tekton.dev
kubectl -n tekton-pipelines wait deployment --all \
  --for=condition=Available --timeout=300s

kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/triggers/previous/v0.37.1/release.yaml
kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/triggers/previous/v0.37.1/interceptors.yaml
kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/chains/previous/v0.29.0/release.yaml
kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/dashboard/previous/v0.73.0/release.yaml
kubectl -n tekton-pipelines port-forward service/tekton-dashboard 9097:9097
```

`release.yaml` instala el Dashboard de solo lectura; `release-full.yaml` incluye funciones de escritura. El modo de solo lectura no autentica a los usuarios ni aplica automáticamente permisos de usuario por namespace. Valida un modelo de acceso y un proxy de autenticación/OIDC antes de exponerlo operativamente. Un ALB interno no es un mecanismo de autenticación. La integración con Cognito requiere el listener HTTPS real, los endpoints de Cognito/OIDC y el Secret.

`https://tekton.dev/helm-charts` no es un repositorio oficial funcional de charts para este ejemplo. No instales el antiguo chart inexistente ni sus valores.

### 2.2 Significado de la configuración actual

| Configuración | Significado actual |
| --- | --- |
| `feature-flags.coschedule: workspaces` | Programa conjuntamente TaskRuns que comparten un Workspace de PVC; mantenla para este ejemplo RWO |
| `disable-affinity-assistant` | Indicador heredado eliminado después de la versión 0.68 |
| `set-security-context: true` | Valor predeterminado en 1.17 para los contenedores inyectados por Tekton; los Steps de usuario necesitan contextos compatibles propios |
| `results-from: termination-message` | Ruta predeterminada, sujeta a los límites de mensajes de terminación de Kubernetes |
| `max-result-size` | Se aplica a `sidecar-logs`; cambiarlo por sí solo no aumenta el mensaje de terminación predeterminado |
| Tiempo de espera predeterminado | Se gestiona en `config-defaults`; este ejemplo establece explícitamente los tiempos de espera del PipelineRun |

`running-in-environment-with-injected-sidecars` no aísla los Workspaces, y `keep-pod-on-cancel` no es un TTL de retención de PipelineRun. No sustituyas un ConfigMap completo por un fragmento pequeño.

### 2.3 ServiceAccounts y roles de IAM separados

Los controladores usan `tekton-pipelines` / `tekton-chains`; las compilaciones usan `tekton-builds`. Las referencias simples a nombres de Task/Pipeline se resuelven en el mismo namespace. No se puede hacer referencia a una Task de un namespace compartido usando solo su nombre.

Crea primero los roles de IAM. Cada política de confianza de IRSA debe restringir el proveedor OIDC existente del clúster, `aud=sts.amazonaws.com` y el `sub=system:serviceaccount:tekton-builds:<SA name>` exacto. Crea previamente los repositorios de ECR; las compilaciones no necesitan `CreateRepository`. A pesar de su nombre, en este ejemplo `ci-readonly` no tiene un Role de la API de Kubernetes: es la cuenta de ejecución predeterminada sin privilegios.

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

Asocia la política de publicación a `tekton-candidate-push` y la política de lectura a `tekton-candidate-read`. Sustituye en todas partes la cuenta, la región y el repositorio. `GetAuthorizationToken` no admite limitar el recurso al nivel del repositorio, por lo que se separa y se restringe por región solicitada.

IRSA autentica las llamadas del SDK/CLI de AWS dentro del Pod. Las solicitudes de extracción de imágenes de ECR que realiza kubelet usan los roles de los nodos, los roles de ejecución de Fargate o los imagePullSecrets, por vías independientes. La anotación IRSA de una Task por sí sola no resuelve ImagePullBackOff.

## 3. Definiciones completas de Tasks

Estas seis Tasks conforman un ejemplo coherente. El repositorio de origen debe contener un módulo Go, pruebas y un Dockerfile. Sustituye la URL fija `myorg/myapp` de checkout por el repositorio aprobado y haz que coincida con la lista permitida de Trigger. No aceptes URLs de Git ni comandos de shell arbitrarios como entrada del webhook.

Las sustituciones de Tekton son textuales. Pasa los parámetros mediante variables de entorno o argumentos en lugar de interpolarlos en los cuerpos de los scripts. Valida que los commits tengan los 40 caracteres completos. Los archivos de autenticación de ECR usan `emptyDir` local a la Task; no los escribas en volúmenes Secret de solo lectura ni des por sentado que la imagen de otro Step contiene las herramientas necesarias.

BuildKit sin privilegios requiere un entorno de compilación dedicado y validado con espacios de nombres de usuario, montajes y configuración adecuada de seccomp/AppArmor. `Unconfined` y `--oci-worker-no-process-sandbox` son concesiones explícitas de seguridad que las políticas de namespaces restringidos rechazan. No son valores predeterminados seguros de forma universal. Usa un entorno separado para PR externos.

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
    image: golang:1.27.2
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
    image: golang:1.27.2
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
    image: golang:1.27.2
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
    image: aquasec/trivy:0.76.0
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

El repositorio original de Google Kaniko está archivado; este nuevo ejemplo usa BuildKit 0.33.0. Ejecutar sin privilegios no garantiza el aislamiento completo de procesos. Antes de usarlo en producción, verifica y fija los digests y las plataformas de las imágenes, y prueba las rutas de escritura y los contextos de seguridad en los nodos reales.

El código de salida 1 del escáner por hallazgos y los demás códigos de error hacen que la Task falle. La ausencia de un informe no debe interpretarse como «cero vulnerabilidades». `/tmp/trivy-report.json` es temporal; expórtalo a un almacén de artefactos aprobado antes de que se limpien los recursos de ejecución si necesitas conservarlo a largo plazo.

## 4. Pipeline y ejecución

![Clonación, pruebas/vet en paralelo, publicación/análisis de la imagen candidata e informe final de mejor esfuerzo](../.gitbook/assets/en-ops-14-tekton-pipelines-2.png)

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

Se crea un PVC nuevo por ejecución. ReadWriteOnce permite que varios Pods estén en el mismo nodo, pero no es RWX multinodo. Un emptyDir no es almacenamiento compartido entre Pods de distintos TaskRun. Separa las cachés según el nivel de confianza y coordina las escrituras simultáneas.

`finally` se ejecuta después de las Tasks normales, pero su ejecución no es incondicional. Las referencias a Results inexistentes pueden hacer que se omitan ejecuciones; el modo de cancelación, el tiempo de espera total, los fallos de recursos y las referencias sin resolver también pueden impedirla. Este ejemplo informa solo el nombre de la ejecución y `tasks.status`, evitando Results de imagen que quizá nunca se hayan generado. No des por sentado que varias Tasks de finally se ejecuten en un orden determinado.

## 5. Webhooks y Triggers

Este Trigger verifica primero el HMAC de GitHub y después comprueba el **repositorio, la rama, el estado de eliminación y el SHA completo**. La URL de Git, la ruta de ECR, los nombres de Task y los ServiceAccounts permanecen fijados en definiciones de confianza. No conectes eventos de PR externos a esta plantilla. El HMAC verifica el origen de la entrega; no autoriza que el código de un PR se despliegue.

![La entrega verificada y los filtros de repositorio/rama crean un PipelineRun fijo para un commit aprobado](../.gitbook/assets/en-ops-14-tekton-pipelines-3.png)

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

El `token` del Secret `github-webhook` debe coincidir con el secreto del webhook de GitHub. Proporciónalo desde un almacenamiento protegido; nunca lo guardes en Git. Configura por separado el endpoint HTTPS externo y la política de reintentos/desduplicación de entregas. EventListener tiene un Service interno de forma predeterminada; este YAML por sí solo no crea un endpoint de Internet.

Conserva el cuerpo original durante la terminación TLS y el procesamiento de gateway/Ingress para poder verificar el HMAC. Aplica autenticación, límites de velocidad, disponibilidad y enrutamiento fijo adecuados a la llamada de retorno. Un período sin actividad no implica automáticamente que haya una interrupción del webhook: inspecciona los resultados reales de entrega y los errores de procesamiento de EventListener.

No des por sentado que `head_commit` siempre existe ni que puedes truncar `refs/heads/feature/a` usando un solo elemento de división. Los filtros de cambios de archivos deben tener en cuenta las rutas añadidas, modificadas y eliminadas, así como los límites del payload. Este ejemplo no inventa un filtro de rutas específico del negocio.

## 6. Chains y verificación de firmas

### 6.1 El éxito de CI y la finalización de la firma son independientes

Chains es un controlador independiente que procesa TaskRuns/PipelineRuns completados. Una firma de imagen por sí sola no demuestra que las pruebas y el análisis hayan concluido correctamente. `chains.tekton.dev/signed=true` no equivale ni a la aprobación del despliegue ni a la verificación criptográfica.

La procedencia a nivel de Pipeline se crea una vez que este finaliza. Esperar dentro del Pipeline a su propia atestación puede entrar en conflicto con ese orden. Este ejemplo utiliza un procedimiento independiente de verificación y promoción después de que termine CI.

![Comprobar que CI tuvo éxito, verificar las firmas y la procedencia de Chains, y promover solo el digest aprobado](../.gitbook/assets/en-ops-14-tekton-pipelines-4.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-4.html)

### 6.2 Configuración de KMS

Usa una clave KMS asimétrica `SIGN_VERIFY` existente. Sustituye el ARN de la clave y `builder.id`. Configura un rol IRSA independiente en el **ServiceAccount del controlador de Chains `tekton-chains/tekton-chains-controller`**, con permisos de escritura en ECR para el repositorio candidato y los permisos de KMS indicados a continuación. Dar un rol IRSA al Pod de compilación no proporciona esas credenciales al controlador.

El backend OCI actual utiliza la búsqueda de credenciales de Kubernetes junto con las cadenas predeterminadas/de ECR del ayudante de credenciales. Configura la identidad AWS disponible para el controlador y verifica la carga real de firmas. El `emptyDir` `/auth` de una Task de compilación no es un Secret compartido que Chains pueda leer.

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

El nombre del formateador `slsa/v1` no significa SLSA provenance v1.0. En Chains actual, `slsa/v1` / `in-toto` corresponden a v0.2, mientras que `slsa/v2alpha3` / `slsa/v2alpha4` corresponden a v1.0. Este ejemplo usa `slsa/v2alpha3` a nivel de Pipeline, deshabilita el almacenamiento duplicado de la procedencia a nivel de Task y habilita por separado las firmas de imágenes.

`storage.oci.encoding-format: dsse` conserva el almacenamiento heredado `.sig` / `.att`. La opción `sigstore-bundle` de la versión 0.29 usa referrers de OCI 1.1; cambia conjuntamente el almacenamiento y las herramientas de verificación. Las cargas a Rekor están deshabilitadas aquí, por lo que la verificación sigue explícitamente una política de claves públicas interna. Si se requiere transparencia, configúrala por separado e incluye una revisión de los metadatos de compilación expuestos.

La firma sin clave requiere un emisor de confianza para el servicio Fulcio real y un token de carga de trabajo válido. Establecer la cadena del emisor de GitHub Actions en un Pod de EKS no proporciona autenticación. Las firmas y las atestaciones por sí solas no establecen un nivel SLSA concreto.

### 6.3 Verificar las ejecuciones y los artefactos de forma independiente

Este script comprueba que un PipelineRun **leído desde una API de confianza** tenga CI satisfactorio, el procesamiento de Chains completado y los resultados aprobados de repositorio, commit e imagen. No verifica las firmas. También se requieren las comprobaciones posteriores de Cosign y la revisión de la política de procedencia.

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

`--insecure-ignore-tlog` es una decisión explícita de no exigir una entrada pública en Rekor. La verificación de firmas con la clave de confianza sigue activa. Si la política de la organización exige la verificación de transparencia, configura esa cadena en vez de usar esta excepción.

Aplica la política al digest del subject de la atestación verificada, `runDetails.builder.id`, `buildDefinition.buildType`, el URI/commit exactos del origen y las definiciones aprobadas de Task/Pipeline. No basta con una firma válida de un productor arbitrario ni con una atestación de otra compilación. Los comandos anteriores no implementan automáticamente estas comprobaciones específicas de la organización.

Configura por separado la verificación de admisión para las mismas condiciones de clave/identidad de confianza, digest y procedencia. No apliques marcadores incompletos como `BEGIN PUBLIC KEY ...` ni compares campos de predicado inexistentes. Comprueba la versión instalada de Kyverno ImageValidatingPolicy y la autenticación del registro, y luego prueba casos aceptados y rechazados con claves, orígenes e imágenes sin firmar correctos e incorrectos.

## 7. Traspaso a GitOps

Actualiza la configuración real de Kustomize/Helm con el `repository@sha256:...` verificado. Este capítulo no incluye una Task que publique, abra o combine PR automáticamente. Un responsable o un flujo de promoción aprobado por separado edita repositorios/archivos fijos y los combina tras CI y la revisión. Evita que Tekton con kubectl y ArgoCD gestionen los mismos manifiestos a la vez.

![Revisar un cambio de GitOps con digest verificado; ArgoCD sincroniza los manifiestos y kubelet descarga las imágenes](../.gitbook/assets/en-ops-14-tekton-pipelines-5.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-5.html)

```bash
# In a reviewed checkout with the Kustomize CLI installed:
cd overlays/production
kustomize edit set image "myapp=$DOCS_IMAGE_REF"
kustomize build . > /tmp/rendered-myapp.yaml
git diff -- kustomization.yaml
# Run repository checks and submit the focused change for review.
```

Dividir las referencias de imagen con `cut -d: -f1/2` rompe los puertos de registro y los digests. Pasa la referencia completa a la herramienta. Configura SSH known_hosts mediante una ruta de confianza; un resultado no verificado de ssh-keyscan no es una raíz de confianza. Las credenciales copiadas al directorio home de un Step no se comparten automáticamente con otro.

ArgoCD sincroniza los manifiestos de Git; kubelet/los runtimes de contenedores descargan las imágenes de la aplicación. Comprueba el estado de la aplicación por separado del de la sincronización. La reversión no restaura automáticamente los datos ni los cambios de esquema.

## 8. Operaciones y limpieza

### 8.1 Registros de ejecución y PVC

`keep` y `keep-since` son opciones de herramientas como los comandos de eliminación de tkn, no un campo TTL integrado de PipelineRun. tkn 0.46.1 `pipelinerun delete` no tiene `--dry-run`. Comprueba las políticas de retención para los registros, los informes de análisis, las firmas/procedencia y los datos de auditoría antes de eliminar nada. No elimines todos los Pods completados correctamente sin una política de antigüedad.

Esta herramienta imprime **solo candidatos para revisión** en un namespace: ejecuciones correctas completadas hace más de siete días y ejecuciones fallidas hace más de catorce días. Usa la hora de finalización, no la de creación, y requiere confirmaciones de Chains y del archivo. `ci.example.com/archive-complete` es una anotación gestionada por el operador y registrada tras confirmar que el archivado se realizó correctamente; no es un campo automático de Tekton. El script no llama a la API de Kubernetes ni elimina nada.

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

El ciclo de vida de los PVC depende de `coschedule`.

| Modo | PVC de volumeClaimTemplate tras la finalización |
| --- | --- |
| `workspaces` | Se conserva de forma predeterminada; la anotación Run `tekton.dev/auto-cleanup-pvc: "true"` habilita su limpieza al finalizar |
| `pipelineruns`, `isolate-pipelinerun` | Se limpian al finalizar |
| `disabled` | Recolección de basura mediante ownerReference; verifica el comportamiento de eliminación al borrar el Run |

Los PVC existentes asociados directamente a Workspaces no se eliminan mediante esa anotación. No habilites la limpieza automática de datos que aún deban archivarse. Inspecciona ownerReferences antes de clasificar TaskRuns como huérfanos.

### 8.2 Supervisión

Pipelines 1.17 exporta métricas mediante OpenTelemetry. Con `metrics-protocol: prometheus` en `config-observability`, el puerto del Service del controlador se llama **`http-metrics`**. Haz coincidir tanto la selección de ServiceMonitor como la de Prometheus.

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

El archivo usa el formato habitual de reglas de Prometheus; inclúyelo en `PrometheusRule.spec` si usas el Operator. Los recuentos actuales de ejecuciones completadas usan `pipelinerun_total`; los recuentos activos usan `running_pipelineruns`. Los estados del contador son `success`, `failed` y `cancelled`, y el contador no tiene una etiqueta de namespace. Este ejemplo compara los éxitos y fallos de todo el clúster, excluyendo las cancelaciones.

Calcula la duración promedio a partir de **la suma de los valores de duración acumulada de los histogramas dividida por la suma de sus recuentos**. Promediar los promedios por serie no da el promedio general. Una métrica de duración de ejecuciones completadas con `status=running` no proporciona la antigüedad transcurrida de las ejecuciones activas. Inspecciona el startTime real del Run, sus condiciones y el estado del Pod.

### 8.3 Solución de problemas y registros

```bash
tkn pipelinerun describe "$DOCS_RUN" -n tekton-builds
tkn pipelinerun logs "$DOCS_RUN" -n tekton-builds --log-failed
tkn pipelinerun logs "$DOCS_RUN" -n tekton-builds --task build
kubectl -n tekton-builds get pipelinerun "$DOCS_RUN" -o yaml
kubectl -n tekton-builds describe pod -l "tekton.dev/pipelineRun=$DOCS_RUN"
kubectl -n tekton-pipelines logs deployment/tekton-pipelines-controller --tail=100
kubectl -n tekton-chains logs deployment/tekton-chains-controller --tail=100
```

`--last` selecciona la ejecución más reciente, no la última que falló. Lee las condiciones desde JSON en vez de usar selectores de campos de condición de CRD no admitidos. Consulta el namespace y las etiquetas de PipelineRun que realmente recopila Loki/Alloy. Recopilar solo los archivos del namespace de los controladores omite las compilaciones que se ejecutan en `tekton-builds`.

Si los Pods están Pending, inspecciona las cuotas, los nodos, los PVC y los eventos de programación. Cambiar gp3 RWO por RWX en YAML no le da el comportamiento de EFS. Aumentar los tiempos de espera no resuelve Results demasiado grandes, permisos, Tasks inexistentes ni herramientas ausentes.

## 9. Reutilización y decisiones operativas

- **Sidecars**: Comprueba la preparación de la base de datos y las conexiones reales. Dormir no demuestra que esté lista. Revisa la configuración de funciones de native sidecar y el comportamiento de terminación de la versión instalada.
- **StepAction**: La función es estable en 1.17, pero la API de almacenamiento de la versión sigue siendo `tekton.dev/v1beta1`. Conecta las herramientas, credenciales y rutas de resultados reales con la Task consumidora.
- **Catálogos**: La obsolescencia del servicio Hub y la integración de la CLI son asuntos distintos. Los comandos de Hub en tkn 0.46 no garantizan la disponibilidad del servicio a largo plazo. Gestiona las definiciones aprobadas con commits fijos o digests verificados de bundles OCI y restringe el acceso al resolver.
- **Redes**: Una NetworkPolicy con `to: []` y TCP 443 permite ese puerto a todos los destinos; no es una lista de dominios permitidos de ECR/GitHub. Restringe DNS, STS/ECR/S3, el registro y las rutas de la API necesarias mediante el diseño real de CNI/proxy/VPC.
- **Spot y costos**: Karpenter usa `karpenter.sh/capacity-type: spot`; los EKS Managed Node Groups usan sus etiquetas reales `eks.amazonaws.com/capacityType`. Ten en cuenta las interrupciones, los reintentos, las cuotas y el almacenamiento. Que no haya Pods de compilación en ejecución no significa que el costo total sea cero.
- **Cachés**: Mide la reutilización específica de la carga de trabajo. No prometas una mejora universal del 40–60 %. Los distintos niveles de confianza no deben compartir cachés de escritura.

## 10. Referencias

- [Pipelines 1.17.0](https://github.com/tektoncd/pipeline/releases/tag/v1.17.0)
- [Triggers 0.37.1](https://github.com/tektoncd/triggers/releases/tag/v0.37.1)
- [Chains 0.29.0](https://github.com/tektoncd/chains/releases/tag/v0.29.0)
- [Dashboard 0.73.0](https://github.com/tektoncd/dashboard/releases/tag/v0.73.0)
- [Modelo de seguridad de Pipelines](https://github.com/tektoncd/pipeline/blob/v1.17.0/docs/security/README.md)
- [Afinidad y ciclo de vida de PVC](https://github.com/tektoncd/pipeline/blob/v1.17.0/docs/affinityassistants.md)
- [Métricas de Pipelines](https://github.com/tektoncd/pipeline/blob/v1.17.0/docs/metrics.md)
- [Configuración de Chains](https://github.com/tektoncd/chains/blob/v0.29.0/docs/config.md)
- [Formateador SLSA e indicaciones de tipo](https://github.com/tektoncd/chains/blob/v0.29.0/docs/slsa-provenance.md)
- [Requisitos de BuildKit sin privilegios](https://github.com/moby/buildkit/blob/v0.33.0/docs/rootless.md)
- [Cosign 3.1.3](https://github.com/sigstore/cosign/releases/tag/v3.1.3)
- [Infraestructura de CI](./03-ci-pipelines.md)
- [GitOps multiclúster](./04-gitops-multi-cluster.md)
- [Pila de observabilidad](./09-observability-stack.md)
