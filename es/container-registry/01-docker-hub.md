# Docker Hub

> **Última actualización**: September 11, 2026

## Descripción general

Docker Hub es el registro predeterminado de Docker CLI cuando no se especifica ningún registro. Aloja imágenes de contenedor públicas y privadas, incluidas las imágenes oficiales de Docker, las imágenes de editores verificados y el contenido aportado por la comunidad.

### Planes y funciones

| Función | Personal | Pro | Team | Business |
|---------|------|-----|------|----------|
| **Precio** | Cuota gratuita básica | $11 al mes / $9 al mes con facturación anual | $16 al mes / $15 por usuario al mes con facturación anual | Consulta el precio y el contrato vigentes |
| **Repositorios privados** | 1 | Ilimitados | Ilimitados | Ilimitados |
| **Funciones para equipos** | Uso individual | Uso individual | Colaboración de la organización | Gobernanza de la organización |
| **Concurrencia de compilaciones automatizadas heredadas** | No disponible | 5 | 15 | 15 |
| **Seguridad y administración** | Consulta el alcance del plan | Consulta el alcance del plan | Consulta las funciones de la organización | Consulta el alcance de SSO, auditoría y contrato |

Los precios reflejan los importes en USD que aparecían en la [página oficial de precios](https://www.docker.com/pricing/) consultada el 11 de septiembre de 2026; verifica las condiciones de facturación y los impuestos. Automated Builds está obsoleto y su retirada está prevista para el 1 de abril de 2027.

### Límites de frecuencia

La [documentación de uso](https://docs.docker.com/docker-hub/usage/) describe los siguientes límites de seis horas. Comprueba las condiciones reales de la cuenta y los encabezados de respuesta; los límites de uso razonable y contra el abuso son independientes:

| Tipo de usuario | Límite de frecuencia | Período de restablecimiento |
|-----------|------------|--------------|
| Anónimo | 100 descargas | 6 horas |
| Autenticado (Free) | 200 descargas | 6 horas |
| Autenticado (Pro) | Ilimitadas dentro del uso razonable | - |
| Autenticado (Team) | Ilimitadas dentro del uso razonable | - |
| Autenticado (Business) | Ilimitadas | - |

Los límites para usuarios anónimos se aplican por dirección IPv4 o subred IPv6 /64. Las descargas autenticadas se atribuyen de acuerdo con las reglas de la cuenta/organización. Los nodos que comparten una dirección NAT comparten la cuota **anónima**, pero no necesariamente las cuotas de las cuentas autenticadas.

## Uso de Docker Hub con Kubernetes

### Creación de secretos para extraer imágenes

Para extraer imágenes privadas de Docker Hub, crea un Secret de Kubernetes:

El Secret, el Pod y el ServiceAccount deben usar el mismo espacio de nombres. Usa un PAT de solo lectura para las descargas y evita incluir credenciales reales directamente en el historial del shell o en los registros de CI.

```bash
# Create docker-registry secret
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=<your-username> \
  --docker-password=<your-password-or-token> \
  --docker-email=<your-email> \
  -n <namespace>
```

Uso de un token de acceso personal (recomendado en lugar de una contraseña):

```bash
# Generate a Personal Access Token at https://hub.docker.com/settings/security
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=myuser \
  --docker-password=dckr_pat_xxxxxxxxxxxx \
  -n default
```

### Uso de Secrets en Pods

Haz referencia al secreto en la especificación del Pod:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: private-app
  namespace: default
spec:
  containers:
  - name: app
    image: myusername/private-app:v1.0.0
  imagePullSecrets:
  - name: dockerhub-secret
```

### Integración con ServiceAccount

Asocia secretos para extraer imágenes a un ServiceAccount para que se inyecten automáticamente:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-service-account
  namespace: default
imagePullSecrets:
- name: dockerhub-secret
```

Ahora, cualquier Pod que use este ServiceAccount utilizará automáticamente las credenciales de Docker Hub:

Esto se aplica a los Pods recién admitidos que no especifiquen ya sus propios `imagePullSecrets`; los Pods existentes y otros ServiceAccounts no se modifican retroactivamente.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: app-service-account
      containers:
      - name: app
        image: myusername/private-app:v1.0.0
```

### Distribución de Secrets en todo el espacio de nombres

Para clústeres con varios espacios de nombres, automatiza la distribución de secretos:

```yaml
# Using Kubernetes Replicator or similar controller
apiVersion: v1
kind: Secret
metadata:
  name: dockerhub-secret
  namespace: default
  annotations:
    replicator.v1.mittwald.de/replicate-to: "staging,production,dev-*"
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: <base64-encoded-config>
```

## Estrategias para mitigar los límites de frecuencia

![Diagrama de flujo para un límite de frecuencia de Docker Hub: si se alcanza, elige según el entorno ECR Pull-through Cache (AWS/EKS), Harbor Proxy Cache (autohospedado) o un mirror de containerd/registro Distribution; si aún no se alcanza, usa descargas autenticadas; todas las opciones resuelven el límite.](../.gitbook/assets/en-container-registry-01-docker-hub-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-01-docker-hub-0.html)

### Estrategia 1: caché de paso a través con Harbor

Implementa Harbor como caché proxy para reducir las descargas de Docker Hub:

```yaml
# Harbor values.yaml excerpt
proxy:
  httpProxy: ""
  httpsProxy: ""
  noProxy: 127.0.0.1,localhost,.local,.internal

# After Harbor deployment, configure a Docker Hub registry endpoint
# and select that endpoint when creating a proxy cache project.
```

Usa un nombre de imagen de proyecto proxy explícito, como `harbor.internal.example.com/dockerhub-cache/library/nginx:TAG`. No trates la configuración del proxy HTTP saliente de Harbor anterior como configuración de caché del registro. Un mirror de containerd también necesita un formato de URL de registro compatible y una configuración TLS de confianza.

```toml
# containerd 2.x: /etc/containerd/config.toml
[plugins."io.containerd.cri.v1.images".registry]
  config_path = "/etc/containerd/certs.d"
```

```toml
# containerd 1.x uses this plugin name instead
[plugins."io.containerd.grpc.v1.cri".registry]
  config_path = "/etc/containerd/certs.d"
```

```toml
# /etc/containerd/certs.d/docker.io/hosts.toml
server = "https://registry-1.docker.io"
[host."https://mirror.gcr.io"]
  capabilities = ["pull"]
```

La configuración antigua `registry.mirrors` está obsoleta. Sigue la [documentación de hosts de containerd](https://github.com/containerd/containerd/blob/main/docs/hosts.md) y concede `resolve` únicamente a mirrors de confianza. Un mirror público no garantiza la disponibilidad de todas las imágenes públicas o privadas.

### Estrategia 2: mirror del registro con Distribution

Implementa el registro de CNCF Distribution como caché de paso a través:

Crea primero el PVC y el Secret `dockerhub-creds` a los que se hace referencia. Este fragmento expone un registro HTTP para un laboratorio controlado; en producción se requieren TLS, autenticación y controles de acceso. Un proxy que use credenciales privilegiadas del upstream no debe exponer imágenes privadas almacenadas en caché a usuarios no autorizados.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: registry-mirror
spec:
  replicas: 1
  selector:
    matchLabels:
      app: registry-mirror
  template:
    metadata:
      labels:
        app: registry-mirror
    spec:
      containers:
      - name: registry
        image: registry:2
        ports:
        - containerPort: 5000
        env:
        - name: REGISTRY_PROXY_REMOTEURL
          value: "https://registry-1.docker.io"
        - name: REGISTRY_PROXY_USERNAME
          valueFrom:
            secretKeyRef:
              name: dockerhub-creds
              key: username
        - name: REGISTRY_PROXY_PASSWORD
          valueFrom:
            secretKeyRef:
              name: dockerhub-creds
              key: password
        volumeMounts:
        - name: cache-storage
          mountPath: /var/lib/registry
      volumes:
      - name: cache-storage
        persistentVolumeClaim:
          claimName: registry-cache-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: registry-mirror
spec:
  selector:
    app: registry-mirror
  ports:
  - port: 5000
    targetPort: 5000
```

### Estrategia 3: caché de paso a través de Amazon ECR

Si trabajas en AWS, usa la función de caché de paso a través de ECR. Primero crea el secreto de credenciales del upstream en la misma cuenta y región, con el prefijo de nombre `ecr-pullthroughcache/`; usa su ARN completo real:

```bash
# Example after creating a secret named ecr-pullthroughcache/dockerhub
PTC_SECRET_ARN=$(aws secretsmanager describe-secret \
  --secret-id ecr-pullthroughcache/dockerhub --region us-east-1 \
  --query ARN --output text)
# Create pull-through cache rule for Docker Hub
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix docker-hub \
  --upstream-registry-url registry-1.docker.io \
  --credential-arn "$PTC_SECRET_ARN" \
  --region us-east-1

# Pull images through ECR
# Original: docker.io/library/nginx:latest
# Via ECR: 123456789012.dkr.ecr.us-east-1.amazonaws.com/docker-hub/library/nginx:latest
```

### Estrategia 4: descarga previa de imágenes en los nodos

Para cargas de trabajo previsibles, descarga previamente las imágenes con un DaemonSet:

La descarga previa cambia el momento de la descarga; no elimina las descargas del upstream ni garantiza que la recolección de basura de imágenes de kubelet conserve la caché. Mantén las credenciales en el espacio de nombres del DaemonSet y usa etiquetas mantenidas o resúmenes verificados.

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: image-prepuller
spec:
  selector:
    matchLabels:
      app: image-prepuller
  template:
    metadata:
      labels:
        app: image-prepuller
    spec:
      initContainers:
      - name: prepull-nginx
        image: nginx:1.30.6
        command: ['sh', '-c', 'echo Image pulled']
      - name: prepull-redis
        image: redis:7
        command: ['sh', '-c', 'echo Image pulled']
      containers:
      - name: pause
        image: registry.k8s.io/pause:3.10
      imagePullSecrets:
      - name: dockerhub-secret
```

## Compilaciones automatizadas

Docker Hub Automated Builds está **obsoleto** y su retirada está prevista para el 1 de abril de 2027. A continuación se describe la integración heredada con GitHub/Bitbucket. Las compilaciones de GitLab deben ejecutarse en GitLab CI y publicar el resultado; los pipelines nuevos deben seguir la [guía de migración](https://docs.docker.com/docker-hub/repos/manage/builds/).

### Configuración de compilaciones automatizadas

1. Si ya tienes una configuración de autobuild, revisa la cuenta de GitHub/Bitbucket vinculada
2. Crea un repositorio y conéctalo a un repositorio de código fuente
3. Configura las reglas de compilación:

```yaml
# Example build rules configuration
Source Type: Branch
Source: main
Docker Tag: latest
Dockerfile location: /Dockerfile
Build Context: /

Source Type: Tag
Source: /^v[0-9.]+$/
Docker Tag: {sourceref}
Dockerfile location: /Dockerfile
Build Context: /
```

### Hooks de compilación

Personaliza las compilaciones con scripts de hooks en tu repositorio:

```bash
# hooks/build - Custom build script
#!/bin/bash
docker build \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  -t $IMAGE_NAME .
```

```bash
# hooks/post_push - Run after successful push
#!/bin/bash
# Tag with additional tags
docker tag $IMAGE_NAME $DOCKER_REPO:$SOURCE_COMMIT
docker push $DOCKER_REPO:$SOURCE_COMMIT
```

### Limitaciones de Docker Hub Automated Builds

- El servicio está obsoleto; planifica la migración antes del 1 de abril de 2027.
- La concurrencia de compilaciones documentada es de 5 para Pro y 15 para Team/Business.
- No supongas que el comportamiento de plataformas múltiples, caché, credenciales y retención coincide con el de un ejecutor externo de CI; revisa la configuración heredada real.

**Recomendación**: usa GitHub Actions con `docker/build-push-action` o GitLab CI con comandos de Docker/BuildKit. Las acciones de GitHub Actions no se pueden ejecutar directamente como trabajos de GitLab CI.

## Consideraciones de seguridad para imágenes públicas

### Vectores de ataque a la cadena de suministro

Las imágenes públicas de Docker Hub pueden presentar riesgos de seguridad:

1. **Suplantación tipográfica**: imágenes maliciosas con nombres parecidos a los de imágenes populares
2. **Cuentas de mantenedores comprometidas**: imágenes legítimas tomadas por atacantes
3. **Malware incorporado**: mineros de criptomonedas, puertas traseras o código para la exfiltración de datos
4. **Imágenes base vulnerables**: imágenes obsoletas con CVE conocidos
5. **Imágenes infladas**: paquetes innecesarios que aumentan la superficie de ataque

### Identificación de imágenes de confianza

| Tipo de imagen | Indicador | Nivel de confianza |
|------------|-----------|-------------|
| Imágenes oficiales de Docker | Programa de imágenes upstream seleccionadas | Verifica la etiqueta, el resumen y las vulnerabilidades concretos |
| Editor verificado | Identidad del editor verificada | Verifica el artefacto concreto y la política de mantenimiento |
| OSS patrocinado | Programa de proyectos patrocinados | El patrocinio no garantiza que no haya vulnerabilidades |
| Imágenes de la comunidad | Sin distintivo | Verifica manualmente |

### Imágenes oficiales de Docker

Las imágenes oficiales se seleccionan junto con Docker y los mantenedores upstream/de la comunidad; no todas las imágenes son mantenidas directamente por Docker Inc.:

```bash
# Official images use the library/ namespace (often omitted)
docker pull nginx          # Same as docker.io/library/nginx
docker pull postgres:15    # Same as docker.io/library/postgres:15
```

Características de las imágenes oficiales:
- Documentación clara y transparencia del Dockerfile
- Actualizaciones de seguridad periódicas
- Patrones de Dockerfile recomendados
- La compatibilidad con arquitecturas varía según la imagen/etiqueta
- El tamaño base y los paquetes incluidos varían según la variante

### Editores verificados

Los editores verificados son organizaciones validadas por Docker:

```bash
# Select an actual maintained tag/digest from the publisher's current catalog
docker buildx imagetools inspect "$VERIFIED_VENDOR_IMAGE"
docker pull "$VERIFIED_VENDOR_IMAGE"
```

No deduzcas la disponibilidad actual de etiquetas ni el estado de vulnerabilidades a partir del distintivo de un editor. Los catálogos de los proveedores y las políticas de acceso cambian; los ejemplos antiguos de etiquetas de Bitnami o Grafana no son una recomendación vigente.

### Prácticas recomendadas para el análisis de seguridad

Analiza siempre las imágenes públicas antes de implementarlas:

```bash
# Using Trivy (recommended)
trivy image nginx:latest

# Using Docker Scout (Docker Desktop)
docker scout cves nginx:latest

# Using Grype
grype nginx:latest
```

Una lista de permitidos de fuentes es útil, pero **no aplica la firma ni el análisis de vulnerabilidades**. El siguiente ejemplo usa el modo Audit de Kyverno en un espacio de nombres dedicado `registry-demo`; revisa los resultados antes de elegir una política de aplicación.

```yaml
# Source allowlist only; Kyverno must already be installed
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: allowed-image-sources
spec:
  validationFailureAction: Audit
  rules:
  - name: check-image-source
    match:
      any:
      - resources:
          kinds:
          - Pod
          namespaces:
          - registry-demo
    validate:
      message: "Use an approved, fully qualified image reference."
      pattern:
        spec:
          =(initContainers):
          - image: "docker.io/library/* | docker.io/my-approved-org/*"
          =(ephemeralContainers):
          - image: "docker.io/library/* | docker.io/my-approved-org/*"
          containers:
          - image: "docker.io/library/* | docker.io/my-approved-org/*"
```

Las políticas de firma necesitan claves/identidades de confianza y verificación de resúmenes. Las políticas de atestación de vulnerabilidades también necesitan un firmante de confianza y criterios de aceptación explícitos; comprobar una cadena `scanner` sin firmar no es suficiente. Consulta [seguridad de imágenes](../security/07-image-security.md) y el [ejemplo upstream de lista de permitidos de fuentes](https://github.com/kyverno/policies/tree/main/best-practices/restrict-image-registries). La configuración de Content Trust de Docker CLI no aplica automáticamente la admisión de Kubernetes/containerd.

### Recomendaciones para imágenes públicas

1. **Fija imágenes a resúmenes específicos** (no solo a etiquetas):
   ```yaml
   # Avoid
   image: nginx:latest

   # Better
   image: nginx:1.30.6

   ```

   Obtén el valor completo con `docker image inspect nginx:1.30.6 --format='{{index .RepoDigests 0}}'` después de descargar la imagen y, luego, usa el valor `repository@sha256:...` que se muestra en la carga de trabajo. Un hash de ejemplo abreviado no es una referencia de imagen válida para su uso.

2. **Replica las imágenes en un registro privado**:
   ```bash
   # Pull, scan, and push to your private registry
   docker pull nginx:1.30.6
   trivy image nginx:1.30.6 --exit-code 1
   docker tag nginx:1.30.6 myregistry.com/library/nginx:1.30.6
   docker push myregistry.com/library/nginx:1.30.6
   ```

3. **Usa imágenes base Distroless o mínimas**:
   ```dockerfile
   # Instead of full OS base images
   FROM gcr.io/distroless/static-debian12
   # or
   FROM cgr.dev/chainguard/static:latest
   ```

## Uso de la API de Docker Hub

### Autenticación

La ruta heredada `/v2/users/login` está obsoleta. La [API oficial de Hub](https://docs.docker.com/reference/api/hub/latest/) acepta `identifier` y `secret` en `/v2/auth/token` y devuelve `access_token`. Este token vence en 10 minutos y es distinto del token `auth.docker.io` que se usa para las descargas del registro. Es preferible usar un PAT con el alcance requerido en lugar de una contraseña.

```bash
set -euo pipefail
# Load these from secure shell input or CI secrets; do not commit their values.
: "${DOCKER_USER:?Set Docker Hub username}"
: "${DOCKER_PAT:?Load a Docker Hub personal access token}"
export DOCKER_USER DOCKER_PAT
HUB_TOKEN=$(jq -n '{identifier: env.DOCKER_USER, secret: env.DOCKER_PAT}' | \
  curl -fsS -X POST https://hub.docker.com/v2/auth/token \
    -H 'Content-Type: application/json' --data-binary @- | jq -er '.access_token')
HUB_NAMESPACE=${HUB_NAMESPACE:-$DOCKER_USER}
export HUB_TOKEN HUB_NAMESPACE
```

### Lista de repositorios y etiquetas

`HUB_NAMESPACE` usa como valor predeterminado el usuario de inicio de sesión; si hace falta, establece el espacio de nombres de una organización autorizada. Estos ejemplos solicitan únicamente la primera página visible. El valor máximo de `page_size` es 100; sigue la URL `next` de la respuesta para obtener un inventario completo.

```bash
: "${DOCKER_REPO:?Set repository name}"
curl -fsS -H "Authorization: Bearer $HUB_TOKEN" \
  "https://hub.docker.com/v2/namespaces/$HUB_NAMESPACE/repositories?page_size=100" | \
  jq '.results[] | {name, is_private}'

curl -fsS -H "Authorization: Bearer $HUB_TOKEN" \
  "https://hub.docker.com/v2/namespaces/$HUB_NAMESPACE/repositories/$DOCKER_REPO/tags?page_size=100" | \
  jq '.results[] | {name, last_updated}'
```

### Revisión de etiquetas antes de la limpieza

No elimines etiquetas basándote en los primeros 100 registros ni supongas un orden del servidor que no esté documentado. Este script Bash independiente recopila todas las páginas y ordena el inventario localmente; no elimina nada. Antes de borrar cualquier elemento, comprueba los resúmenes de las cargas de trabajo en ejecución, la retención para reversiones y las etiquetas protegidas; luego usa la interfaz de administración de Hub o las funciones de la API documentadas actualmente.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${HUB_TOKEN:?Create a current Hub API access token}"
: "${HUB_NAMESPACE:?Set namespace}"
: "${DOCKER_REPO:?Set repository}"
registry_tag_index=$(mktemp)
trap 'rm -f "$registry_tag_index"' EXIT
registry_next="https://hub.docker.com/v2/namespaces/$HUB_NAMESPACE/repositories/$DOCKER_REPO/tags?page_size=100"
while [ -n "$registry_next" ]; do
  case "$registry_next" in
    https://hub.docker.com/*) ;;
    *) printf '%s\n' 'Unexpected pagination host' >&2; exit 1 ;;
  esac
  registry_page=$(curl -fsS -H "Authorization: Bearer $HUB_TOKEN" "$registry_next")
  printf '%s' "$registry_page" | jq -c '.results[]' >> "$registry_tag_index"
  registry_next=$(printf '%s' "$registry_page" | jq -r '.next // empty')
done
# Read-only inventory. No DELETE request is made.
jq -s 'sort_by(.last_updated // "") | reverse | .[] | {name, last_updated}' "$registry_tag_index"
```

### Análisis de vulnerabilidades

```bash
# Check Scout access against the account, plan and repository configuration.
# Use the documented CLI instead of assuming a /tags/TAG/vulnerabilities endpoint.
docker scout cves nginx:1.30.6
```

### Creación de un repositorio privado

Confirma primero los permisos del espacio de nombres y las cuotas del plan.

```bash
jq -n --arg ns "$HUB_NAMESPACE" \
  '{namespace:$ns, name:"myapp", description:"My application", is_private:true}' | \
  curl -fsS -X POST "https://hub.docker.com/v2/namespaces/$HUB_NAMESPACE/repositories" \
    -H "Authorization: Bearer $HUB_TOKEN" \
    -H 'Content-Type: application/json' --data-binary @-
```

## Prácticas recomendadas

### 1. Autenticación y acceso

- Usa tokens de acceso personal en lugar de contraseñas
- Rota los tokens periódicamente (se recomienda cada 90 días)
- Usa tokens de solo lectura para las operaciones de descarga de CI/CD
- Habilita la autenticación de dos factores en las cuentas de Docker Hub
- Para equipos, usa la administración de acceso a nivel de organización

### 2. Administración de imágenes

- Usa etiquetas específicas; nunca uses `latest` en producción
- Implementa una estrategia de etiquetado coherente (se recomienda SemVer)
- Limpia periódicamente las etiquetas antiguas o sin uso
- Documenta las dependencias de las imágenes y los procedimientos de actualización

### 3. Seguridad

- Analiza todas las imágenes antes de implementarlas
- Prefiere las imágenes oficiales y los editores verificados
- Replica las imágenes críticas en tu registro privado
- Implementa controladores de admisión para aplicar políticas
- Revisa los Dockerfiles en busca de problemas de seguridad

### 4. Rendimiento y fiabilidad

- Implementa el mirroring/la caché del registro en los clústeres de producción
- Supervisa el uso de los límites de frecuencia
- Usa descargas autenticadas incluso para imágenes públicas (límites más altos)
- Descarga previamente las imágenes para implementaciones previsibles

### 5. Integración de CI/CD

- Usa GitHub Actions o GitLab CI para las compilaciones (ofrecen más funciones que Docker Hub Automated Builds)
- Implementa compilaciones en varias etapas para reducir el tamaño de las imágenes
- Almacena eficazmente las capas en caché para acelerar las compilaciones
- Firma las imágenes para proteger la cadena de suministro

## Resumen

Docker Hub ofrece el ecosistema predeterminado de imágenes públicas de Docker CLI y repositorios privados. Para usarlo de forma fiable en la infraestructura de Kubernetes, se necesitan autenticación, caché, verificación de artefactos y políticas de mantenimiento explícitas.

Para cargas de trabajo de producción que requieren mayor fiabilidad o controles de seguridad más estrictos, considera:
- **Amazon ECR** para entornos nativos de AWS
- **Harbor** para escenarios autohospedados, aislados de redes externas o multinube
- **Docker Hub Business** para funciones empresariales con la comodidad del SaaS

Conclusiones clave:
- Usa una autenticación adecuada y verifica los límites reales de frecuencia/uso razonable de la cuenta
- Implementa caché de paso a través en los clústeres de producción
- Confía, pero verifica: analiza todas las imágenes públicas
- Usa imágenes oficiales y editores verificados cuando sea posible
- Considera enfoques híbridos: Docker Hub para las imágenes base y un registro privado para tus aplicaciones

## Referencias

- [Uso de Docker Hub y límites de descarga](https://docs.docker.com/docker-hub/usage/pulls/)
- [API de Docker Hub](https://docs.docker.com/reference/api/hub/latest/)
- [Obsolescencia de Automated Builds](https://docs.docker.com/docker-hub/repos/manage/builds/)
- [Configuración del host del registro de containerd](https://github.com/containerd/containerd/blob/main/docs/hosts.md)
- [Reglas de caché de paso a través de ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/pull-through-cache-creating-rule.html)
