# Harbor

> **Última actualización**: October 16, 2026

## Descripción general

Harbor es un registro de contenedores de código abierto y nativo de la nube que ofrece funciones de nivel empresarial para almacenar, firmar y analizar imágenes de contenedores. Como proyecto Graduado de CNCF, Harbor ha demostrado su madurez, seguridad y adopción en todo el sector.

### Funciones principales

| Función | Descripción |
|---------|-------------|
| **Multitenencia** | Aislamiento basado en proyectos con RBAC |
| **Análisis de vulnerabilidades** | Analizador Trivy integrado |
| **Firma de imágenes** | Compatibilidad con Cosign y Notation |
| **Replicación** | Replicación de envío/recepción entre registros |
| **Recolección de basura** | Limpieza automatizada de capas no utilizadas |
| **Caché de proxy** | Almacenamiento en caché de registros remotos (Docker Hub, etc.) |
| **Registro de auditoría** | Historial completo de operaciones |
| **OIDC/LDAP** | Integración de identidad empresarial |
| **Gestión de cuotas** | Límites de almacenamiento por proyecto |
| **Cuentas de robot** | Cuentas de servicio para automatización |

### Arquitectura

![Estructura interna de Harbor: el Portal proporciona acceso a la API Core, que distribuye las solicitudes al Registry, Job Service, PostgreSQL y Redis, mientras que Job Service ejecuta el analizador Trivy.](../.gitbook/assets/en-container-registry-03-harbor-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-03-harbor-0.html)

### Responsabilidades de los componentes

| Componente | Función |
|-----------|---------|
| **Core** | Servidor de API, autenticación, autorización y gestión de proyectos |
| **Registry** | Implementación de la API Docker Distribution v2 y almacenamiento de imágenes |
| **Job Service** | Ejecución de tareas asíncronas (replicación, análisis, GC) |
| **Trivy** | Motor de análisis de vulnerabilidades |
| **Portal** | Interfaz web para administración |
| **PostgreSQL** | Metadatos, datos de usuario y registros de auditoría |
| **Redis** | Cola de trabajos, caché de sesiones y caché del registro |

## Instalación con Helm

La versión de referencia revisada el 2026-10-16 es **Harbor 2.15.4 / Helm chart 1.19.2**. Las versiones de la aplicación y del chart son diferentes: el chart más reciente, 1.19.2, sigue usando appVersion 2.15.2 de forma predeterminada, por lo que una instalación predeterminada de Helm no incluye las correcciones de seguridad de 2.15.3 (por ejemplo, GHSA-2phj-cp9f-qq6w). Este ejemplo presupone que ya existen PostgreSQL externo de alta disponibilidad, Redis y almacenamiento compartido; el archivo de valores no los aprovisiona.

### Requisitos previos

- Prepare versiones compatibles de Kubernetes/Helm, DNS, un controlador Ingress con mantenimiento y su `IngressClass`. Configure límites de carga, tiempos de espera y TLS para ese controlador.
- Cree el Secret de certificado/clave `harbor-tls` en el namespace `harbor`. El certificado debe coincidir con el nombre de host; los clientes y nodos deben confiar en su CA.
- Dos réplicas de Registry en nodos distintos requieren un **PVC RWX compartido o almacenamiento de objetos**. Compartir un único PVC EBS `gp3` RWO entre nodos no es una configuración de alta disponibilidad.
- Prepare la base de datos PostgreSQL `registry`, su usuario y la clave `password` en el Secret `harbor-database`. `sslmode: require` solo exige cifrado; valide la confianza en la CA y `verify-full` cuando se requiera validar el certificado y el nombre de host.
- Redis debe admitir las múltiples bases de datos lógicas que utiliza Harbor. No use un modo Redis Cluster restringido a DB 0. Prepare `REDIS_PASSWORD` en el Secret `harbor-redis` y valide la conectividad TLS. Use `caBundleSecretName` del chart para una CA privada.

```bash
helm repo add harbor https://helm.goharbor.io
helm repo update
helm show chart harbor/harbor --version 1.19.2
kubectl create namespace harbor
kubectl get ingressclass
kubectl get storageclass
```

### Credenciales iniciales

```bash
# Initial installation only: preserve this encryption key during upgrades.
umask 077
HARBOR_SETUP_DIR=$(mktemp -d)
python3 - "$HARBOR_SETUP_DIR" <<'PYTHON'
import getpass
import pathlib
import secrets
import sys
root = pathlib.Path(sys.argv[1])
(root / "admin-password").write_text(getpass.getpass("Initial Harbor admin password: "))
(root / "secretKey").write_text(secrets.token_hex(8))  # exactly 16 characters
PYTHON
kubectl create secret generic harbor-admin -n harbor \
  --from-file=HARBOR_ADMIN_PASSWORD="$HARBOR_SETUP_DIR/admin-password"
kubectl create secret generic harbor-encryption-key -n harbor \
  --from-file=secretKey="$HARBOR_SETUP_DIR/secretKey"
rm -rf -- "$HARBOR_SETUP_DIR"
```

### values.yaml para producción

Guarde el archivo como `harbor-values.yaml` y reemplace todos los nombres de host de ejemplo y StorageClass. Añada solicitudes/límites de recursos y distribución de Pod según la carga medida y los nodos disponibles. Habilite `serviceMonitor.enabled` solo después de instalar los CRD del Prometheus Operator.

```yaml
expose:
  type: ingress
  tls:
    enabled: true
    certSource: secret
    secret:
      secretName: harbor-tls
  ingress:
    hosts:
      core: harbor.example.com
    className: your-ingress-class
    annotations: {}
externalURL: https://harbor.example.com
existingSecretAdminPassword: harbor-admin
existingSecretSecretKey: harbor-encryption-key
internalTLS:
  enabled: true
  certSource: auto
persistence:
  enabled: true
  resourcePolicy: keep
  persistentVolumeClaim:
    registry:
      storageClass: your-rwx-storage-class
      accessMode: ReadWriteMany
      size: 100Gi
    trivy:
      storageClass: your-storage-class
      size: 10Gi
core:
  replicas: 2
portal:
  replicas: 2
registry:
  replicas: 2
jobservice:
  replicas: 2
  jobLoggers: [database]
database:
  type: external
  external:
    host: harbor-db.internal
    port: "5432"
    username: harbor
    coreDatabase: registry
    existingSecret: harbor-database
    sslmode: require
redis:
  type: external
  external:
    addr: harbor-redis.internal:6379
    existingSecret: harbor-redis
    tlsOptions:
      enable: true
trivy:
  enabled: true
  skipUpdate: false
  skipJavaDBUpdate: false
  offlineScan: false
metrics:
  enabled: true
  serviceMonitor:
    enabled: false
```

### Instalación con valores personalizados

```bash
helm template harbor harbor/harbor --version 1.19.2   --namespace harbor --values harbor-values.yaml > harbor-rendered.yaml
helm install harbor harbor/harbor --version 1.19.2   --namespace harbor --values harbor-values.yaml --wait --timeout 15m
kubectl get pods,svc,ingress,pvc -n harbor
docker login harbor.example.com --username admin
```

### Actualización de Harbor

Antes de actualizar, compruebe la ruta de actualización compatible en las notas de la versión. Haga copias de seguridad de los metadatos, los datos del registro, la configuración y las claves de cifrado en un punto de recuperación coherente, y pruebe la restauración. Compare los valores antiguos y nuevos del chart y pruebe la renderización y las migraciones en un entorno de pruebas. Fije el chart de destino en `helm upgrade`; una reversión de Helm por sí sola podría no revertir una migración de base de datos.

Notary v1 se eliminó en Harbor 2.9. Cosign y Notation son herramientas externas de firma; sus firmas se almacenan como artefactos OCI en el registro.

## Proyectos y RBAC

Los ejemplos de API presuponen que se puede acceder a una instancia de prueba de Harbor mediante HTTPS, y que están disponibles `curl` y `jq`. Asigne a `HARBOR_USER` un usuario con los permisos necesarios. `curl --user "$HARBOR_USER"` solicitará la contraseña. Para la automatización, proporcione credenciales de robot con permisos limitados mediante su administrador de secretos, sin registrarlas en los logs.

```bash
export HARBOR_USER=admin
```

### Tipos de proyectos

| Tipo | Descripción | Caso de uso |
|------|-------------|----------|
| **Público** | Cualquiera puede descargar imágenes | Código abierto e imágenes base compartidas |
| **Privado** | Solo los miembros pueden acceder | Imágenes de aplicaciones y herramientas internas |

### Creación de proyectos

```bash
# Create project via API
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/projects" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "project_name": "myapp",
    "metadata": {
      "public": "false",
      "prevent_vul": "true",
      "auto_scan": "true",
      "severity": "high"
    },
    "storage_limit": 107374182400
  }'
```

### Roles de RBAC

| Rol | Permisos |
|------|-------------|
| **Administrador de proyecto** | Control total: gestión de miembros, políticas e imágenes |
| **Mantenedor** | Enviar/descargar imágenes, analizarlas y eliminar etiquetas |
| **Desarrollador** | Enviar/descargar imágenes; no incluye la administración de miembros |
| **Invitado** | Solo descargar imágenes |
| **Invitado limitado** | Descargar/leer artefactos; no puede enumerar miembros del proyecto ni logs |

### Cómo añadir miembros

```bash
# Add user to project
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/projects/myapp/members" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "role_id": 2,
    "member_user": {
      "username": "developer1"
    }
  }'

# Role IDs: 1=Admin, 2=Developer, 3=Guest, 4=Maintainer, 5=Limited Guest
```

### Cuentas de robot

Las cuentas de robot son cuentas de servicio para la automatización de CI/CD:

```bash
# Create robot account
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/robots" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "ci-robot",
    "description": "Robot account for CI/CD pipelines",
    "duration": 90,
    "level": "project",
    "permissions": [
      {
        "kind": "project",
        "namespace": "myapp",
        "access": [
          {"resource": "repository", "action": "push"},
          {"resource": "repository", "action": "pull"}
        ]
      }
    ]
  }'

# Response includes robot name and secret
# {
#   "name": "robot$myapp+ci-robot",
#   "secret": "xxxxxxxxxxxxxxxxxxxx",
#   ...
# }
```

Uso de una cuenta de robot en CI/CD:

```bash
# Docker login with robot account
read -r -p 'Robot name returned by Harbor: ' ROBOT_NAME
read -r -s -p 'Robot secret: ' ROBOT_SECRET
printf '\n'
printf '%s' "$ROBOT_SECRET" | docker login harbor.example.com \
  --username "$ROBOT_NAME" --password-stdin
unset ROBOT_SECRET

# Push image
docker push harbor.example.com/myapp/app:v1.0.0
```

## Replicación de imágenes

![Harbor admite dos direcciones de replicación: descargar imágenes desde un registro externo para reflejarlas localmente y enviar imágenes desde un Harbor de origen a un registro remoto para distribuirlas.](../.gitbook/assets/en-container-registry-03-harbor-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-03-harbor-1.html)

Harbor admite la replicación bidireccional entre registros.

Los ID de endpoint `1` y `3` que aparecen a continuación son ejemplos: obtenga los ID reales de la respuesta `Location` de creación o de la lista de endpoints. Las expresiones cron programadas tienen seis campos, incluidos los segundos (`0 0 0 * * *`); compruebe la zona horaria de Job Service. La replicación de extracción necesita conectividad con el registro ascendente y no puede importar contenido a una red completamente desconectada. La replicación basada en eventos sigue los eventos locales de envío, cambio de etiqueta y eliminación de Harbor, no los cambios arbitrarios en un registro remoto.

### Modos de replicación

| Modo | Descripción | Caso de uso |
|------|-------------|----------|
| **Envío** | Harbor envía contenido a un registro remoto | Distribución a ubicaciones periféricas |
| **Extracción** | Harbor extrae contenido de un registro remoto | Crear una réplica de Docker Hub, sincronizar desde ECR |

### Configuración de endpoints de replicación

```bash
# Create registry endpoint (e.g., Docker Hub)
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/registries" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "docker-hub",
    "type": "docker-hub",
    "url": "https://hub.docker.com",
    "credential": {
      "type": "basic",
      "access_key": "dockerhub-username",
      "access_secret": "<dockerhub-PAT>"
    }
  }'

# Create registry endpoint (ECR)
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/registries" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "aws-ecr",
    "type": "aws-ecr",
    "url": "https://123456789012.dkr.ecr.us-east-1.amazonaws.com",
    "credential": {
      "type": "basic",
      "access_key": "AKIAIOSFODNN7EXAMPLE",
      "access_secret": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    }
  }'

# Create registry endpoint (another Harbor)
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/registries" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "harbor-dr",
    "type": "harbor",
    "url": "https://harbor-dr.example.com",
    "credential": {
      "type": "basic",
      "access_key": "<replication-user>",
      "access_secret": "<replication-secret>"
    }
  }'
```

### Creación de reglas de replicación

```bash
# Pull replication from Docker Hub (mirror official images)
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/replication/policies" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "mirror-dockerhub-nginx",
    "src_registry": {"id": 1},
    "dest_namespace": "dockerhub-mirror",
    "filters": [
      {"type": "name", "value": "library/nginx"},
      {"type": "tag", "value": "1.*"}
    ],
    "trigger": {
      "type": "scheduled",
      "trigger_settings": {
        "cron": "0 0 0 * * *"
      }
    },
    "enabled": true,
    "replicate_deletion": false,
    "override": true,
    "speed": -1
  }'

# Push replication to DR site
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/replication/policies" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "replicate-to-dr",
    "dest_registry": {"id": 3},
    "filters": [
      {"type": "name", "value": "production/**"},
      {"type": "tag", "value": "v*"}
    ],
    "trigger": {
      "type": "event_based"
    },
    "enabled": true,
    "replicate_deletion": false,
    "override": true,
    "speed": 102400
  }'
```

### Filtros de replicación

| Tipo de filtro | Descripción | Ejemplo |
|-------------|-------------|---------|
| `name` | Patrón de nombre del repositorio | `library/**`, `myapp/*` |
| `tag` | Patrón de etiqueta | `v*`, `latest` |
| `label` | Etiqueta de Harbor | `production`, `approved` |
| `resource` | Tipo de recurso | `image`, `chart` |

## Análisis de vulnerabilidades

### Integración con Trivy

Harbor usa Trivy como analizador de vulnerabilidades predeterminado. Trivy analiza:

- Vulnerabilidades de paquetes del sistema operativo (Alpine, Debian, Ubuntu, RHEL, etc.)
- Dependencias de aplicaciones (npm, pip, gem, maven, módulos go)


### Configuración del análisis al enviar imágenes

```bash
# Enable automatic scanning for a project
curl --fail-with-body -X PUT "https://harbor.example.com/api/v2.0/projects/myapp" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "metadata": {
      "auto_scan": "true"
    }
  }'
```

### Análisis manual

```bash
# Use the digest of an existing artifact from the Harbor UI/API.
: "${HARBOR_DIGEST:?Set the complete sha256 digest}"
curl --fail-with-body --user "$HARBOR_USER" -X POST \
  "https://harbor.example.com/api/v2.0/projects/myapp/repositories/app/artifacts/${HARBOR_DIGEST}/scan"
curl --fail-with-body --user "$HARBOR_USER" \
  "https://harbor.example.com/api/v2.0/projects/myapp/repositories/app/artifacts/${HARBOR_DIGEST}?with_scan_overview=true"
```

El análisis es asíncrono. Compruebe que se haya completado y que la base de datos esté actualizada; un informe vacío o incompleto no significa que el análisis no haya encontrado problemas. A diferencia del ejemplo `app` de un solo componente, los nombres de repositorio anidados, como `team/app`, requieren una doble codificación de URL en la API de Harbor.

### Listas de permitidos de CVE

Limite las excepciones a CVE aprobados, con un responsable, una justificación y una fecha de vencimiento. La solicitud PUT siguiente reemplaza la lista de permitidos del proyecto, así que primero combine las entradas existentes. Desactiva la reutilización de la lista del sistema y requiere un identificador aprobado y una fecha de vencimiento futura.

```bash
# Review the existing project allowlist before replacing it.
: "${APPROVED_CVE:?Set an approved CVE identifier}"
: "${ALLOWLIST_EXPIRES_AT:?Set a future Unix timestamp in seconds}"
jq -n --arg cve "$APPROVED_CVE" --argjson expires "$ALLOWLIST_EXPIRES_AT" \
  '{metadata:{reuse_sys_cve_allowlist:"false"},
    cve_allowlist:{items:[{cve_id:$cve}],expires_at:$expires}}' > cve-allowlist.json
curl --fail-with-body --user "$HARBOR_USER" -X PUT \
  -H 'Content-Type: application/json' \
  --data-binary @cve-allowlist.json \
  'https://harbor.example.com/api/v2.0/projects/myapp'
```

### Cómo impedir el despliegue de imágenes vulnerables

Configure Harbor para bloquear la descarga de imágenes vulnerables:

```bash
# Set vulnerability prevention policy
curl --fail-with-body -X PUT "https://harbor.example.com/api/v2.0/projects/myapp" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "metadata": {
      "prevent_vul": "true",
      "severity": "high"
    }
  }'

# Severity options: none, low, medium, high, critical
```

Esta política controla las descargas del registro; no inspecciona ni detiene los contenedores que ya están en ejecución o que usan imágenes almacenadas en caché. El análisis automático por sí solo no habilita el bloqueo de descargas.

## Firma de imágenes

Las firmas verifican la integridad del artefacto y la identidad de un firmante de confianza. No corrigen vulnerabilidades ni inspeccionan Pods en ejecución. Instale Cosign/Notation siguiendo sus guías oficiales y valide la compatibilidad del formato de firma con Harbor y su motor de políticas.

### Integración con Cosign

```bash
# HARBOR_IMAGE must include an existing image digest, not a mutable tag.
: "${HARBOR_IMAGE:?Set harbor.example.com/myapp/app@sha256:<actual-digest>}"
cosign version
cosign generate-key-pair
cosign sign --key cosign.key "$HARBOR_IMAGE"
cosign verify --key cosign.pub "$HARBOR_IMAGE"
```

La firma sin clave usa una identidad OIDC y un registro de transparencia; la verificación debe limitarse al emisor y la identidad de confianza. Proteja la clave privada y su contraseña en el ejemplo basado en claves. Un entorno completamente desconectado no puede usar directamente un flujo de trabajo que dependa de servicios públicos de Sigstore.

### Integración con Notation (Notary v2)

Este ejemplo usa un certificado autofirmado destinado únicamente a pruebas. Importe la política de confianza para el almacén de confianza creado por `generate-test` antes de verificar. Las políticas de producción deben usar la gestión de claves/CA de la organización y restricciones explícitas sobre la identidad del firmante.

```bash
notation version
notation login harbor.example.com
notation cert generate-test --default harbor-demo
notation sign "$HARBOR_IMAGE"
cat > trustpolicy.json <<'JSON'
{
  "version": "1.0",
  "trustPolicies": [{
    "name": "harbor-demo",
    "registryScopes": ["harbor.example.com/myapp/app"],
    "signatureVerification": {"level": "strict"},
    "trustStores": ["ca:harbor-demo"],
    "trustedIdentities": ["*"]
  }]
}
JSON
notation policy import trustpolicy.json
notation verify "$HARBOR_IMAGE"
```

### Configuración de Cosign en Harbor

Seleccione la política de Cosign o Notation en la sección Configuration del proyecto. Si habilita ambas, se requieren los dos tipos de firma. El chart no tiene una opción `core.cosignKeyFile` para la verificación con clave pública. Distinga las comprobaciones de acceso a firmas del registro de la verificación basada en las claves e identidades de confianza de su organización.

### Aplicación de políticas de Kubernetes

Para aplicar políticas durante el despliegue, configure una política de admisión como Kyverno, tal como se describe en [Seguridad de imágenes](../security/07-image-security.md). Proporcione claves válidas o un emisor/identidad OIDC de confianza, un alcance de imagen exacto y credenciales del registro privado; incluya los contenedores init/efímeros. Valide en modo Audit antes de Enforce, incluidos los casos de clave incorrecta, imagen sin firma y reasignación de etiquetas.

## Escenarios de redes aisladas

El instalador sin conexión de Docker Compose y una implementación de Kubernetes con Helm son rutas de instalación distintas. El instalador sin conexión incluye imágenes de Harbor, pero no todos los paquetes de Docker/Compose, charts de Kubernetes, CNI, imágenes de aplicaciones ni bases de datos de Trivy.

### Instalador sin conexión

```bash
HARBOR_VERSION=2.15.4
curl --fail --location --remote-name \
  "https://github.com/goharbor/harbor/releases/download/v${HARBOR_VERSION}/harbor-offline-installer-v${HARBOR_VERSION}.tgz"
# Verify the release checksum/signature before transporting the bundle.
sha256sum "harbor-offline-installer-v${HARBOR_VERSION}.tgz" > harbor-bundle.sha256
# Transfer both files through the approved offline transport.
```

En el host desconectado, ejecute lo siguiente. Una suma SHA-256 generada localmente verifica la integridad de la transferencia; no reemplaza la verificación de la firma de publicación del editor.

```bash
sha256sum -c harbor-bundle.sha256
tar xzf harbor-offline-installer-v2.15.4.tgz
cd harbor
cp harbor.yml.tmpl harbor.yml
# Set hostname, HTTPS certificate/key, strong admin/DB passwords and data_volume.
# For Trivy: preload DBs, set skip_update, skip_java_db_update and offline_scan.
# Install Docker Engine/Compose and other prerequisites from offline packages first.
./install.sh --with-trivy
```

### Precarga de imágenes para Kubernetes en redes aisladas

Use un binario de kubeadm compatible para enumerar las imágenes del plano de control para la versión exacta de Kubernetes admitida. Añada por separado las imágenes de CNI, CSI, Ingress y monitorización, además de los charts/CRD. Para clústeres que no administra kubeadm, use el inventario de imágenes propio de la distribución.

```bash
: "${K8S_VERSION:?Set the exact supported Kubernetes patch version}"
kubeadm config images list --kubernetes-version "$K8S_VERSION" > kubeadm-images.txt
```

### Script automatizado de sincronización de imágenes

Asigne explícitamente referencias de origen y destino en un archivo TSV. Volver a etiquetar solo con el nombre base puede provocar colisiones entre registros/espacios de nombres. Estos ejemplos con Bash/Skopeo transfieren todas las plataformas mediante archivos OCI. Las firmas y los referenciadores SBOM requieren una transferencia y verificación aparte según la compatibilidad de las herramientas.

```text
# images.tsv: two columns separated by a TAB; replace the internal hostname.
docker.io/library/nginx:1.30.6	harbor.airgap.local/k8s-system/dockerhub/library/nginx:1.30.6
```

En el lado conectado:

```bash
#!/usr/bin/env bash
set -euo pipefail
mkdir -p image-bundle
: > image-bundle/import.tsv
index=0
while IFS=$'\t' read -r source target || [[ -n "$source" ]]; do
  [[ -z "$source" || "$source" == \#* ]] && continue
  [[ -n "$target" ]] || { echo 'Missing target image' >&2; exit 1; }
  index=$((index + 1))
  file="image-${index}.tar"
  skopeo copy --all "docker://${source}" "oci-archive:image-bundle/${file}"
  printf '%s\t%s\n' "$file" "$target" >> image-bundle/import.tsv
done < images.tsv
(cd image-bundle && sha256sum image-*.tar import.tsv > SHA256SUMS)
```

Después de transferir `image-bundle`, en el lado desconectado:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd image-bundle
sha256sum -c SHA256SUMS
# Pre-create the target Harbor projects and trust its TLS CA.
skopeo login harbor.airgap.local
while IFS=$'\t' read -r file target; do
  skopeo copy --all "oci-archive:${file}" "docker://${target}"
done < import.tsv
```

Aplique las URI de imagen internas asignadas a la configuración de Pod/Helm/kubeadm y verifique los resúmenes, las plataformas y las descargas. `--all` solicita todos los manifiestos de plataforma; la conversión de formato puede cambiar un resumen, así que compare los resultados de origen y destino.

### Actualización de la base de datos de Trivy para redes aisladas

```bash
# Use a Trivy version compatible with the deployed Harbor scanner adapter.
trivy image --cache-dir ./trivy-cache --download-db-only
trivy image --cache-dir ./trivy-cache --download-java-db-only
tar -C trivy-cache -czf trivy-db-bundle.tgz db java-db
```

Extraiga el paquete en la raíz de la caché persistente `/home/scanner/.cache/trivy` de cada réplica de Trivy, con los permisos de propietario correctos para `db/trivy.db`, `db/metadata.json`, `java-db/trivy-java.db` y sus metadatos. Detenga el analizador o use un PVC de reemplazo/trabajo init en lugar de sobrescribir una base de datos abierta. El formato `tar -C` anterior evita anidar accidentalmente una ruta de directorio personal dentro de la caché.

```yaml
trivy:
  skipUpdate: true
  skipJavaDBUpdate: true
  offlineScan: true
```

`offlineScan` por sí solo no deshabilita todas las actualizaciones de bases de datos ni crea una base de datos que falte. Establezca un calendario de importación y actualización de las bases de datos y vuelva a analizar tras las actualizaciones. Las claves equivalentes de `harbor.yml` para Compose son `skip_update`, `skip_java_db_update` y `offline_scan`.

### Configuración de confianza de Containerd

Use referencias explícitas a imágenes de Harbor interno en los manifiestos sin conexión. Redirigir registros externos arbitrarios a `/v2/<project>` no reescribe automáticamente las rutas de los repositorios ni las credenciales. Instale la CA en cada nodo y use la configuración adecuada para la versión de su entorno de ejecución.

```toml
# containerd 2.x: /etc/containerd/config.toml
[plugins."io.containerd.cri.v1.images".registry]
  config_path = "/etc/containerd/certs.d"
# containerd 1.x uses plugins."io.containerd.grpc.v1.cri".registry instead.
```

```toml
# /etc/containerd/certs.d/harbor.airgap.local/hosts.toml
server = "https://harbor.airgap.local"
[host."https://harbor.airgap.local"]
  capabilities = ["pull", "resolve"]
  ca = "/etc/containerd/certs.d/harbor.airgap.local/ca.crt"
```

Reinicie containerd siguiendo el procedimiento de mantenimiento de nodos al cambiar `config_path` y, después, verifique una descarga real mediante CRI. Proporcione credenciales de solo lectura limitadas al namespace mediante `imagePullSecrets`.

## Integración de Harbor con Kubernetes

### Creación de imagePullSecrets

```bash
# Create pull credentials in the same namespace as the consuming Pod.
umask 077
HARBOR_AUTH_DIR=$(mktemp -d)
python3 - "$HARBOR_AUTH_DIR/config.json" <<'PYTHON'
import base64
import getpass
import json
import pathlib
import sys
name = input("Pull robot name returned by Harbor: ")
password = getpass.getpass("Pull robot secret: ")
auth = base64.b64encode(f"{name}:{password}".encode()).decode()
pathlib.Path(sys.argv[1]).write_text(json.dumps({
    "auths": {"harbor.example.com": {"auth": auth}}
}))
PYTHON
kubectl create secret generic harbor-secret -n default \
  --type=kubernetes.io/dockerconfigjson \
  --from-file=.dockerconfigjson="$HARBOR_AUTH_DIR/config.json" \
  --dry-run=client -o yaml \
  | kubectl apply --server-side --field-manager=harbor-pull-secret -f -
rm -rf -- "$HARBOR_AUTH_DIR"
kubectl get secret harbor-secret -n default -o jsonpath='{.type}'
```

### Configuración de ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: default
imagePullSecrets:
- name: harbor-secret
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      serviceAccountName: app-sa
      containers:
      - name: app
        image: harbor.example.com/myapp/app:v1.0.0
```

### Configuración de la caché de proxy

![Una solicitud de descarga de un cliente llega a la caché de proxy de Harbor; si hay una coincidencia en la caché, la imagen almacenada se devuelve directamente, mientras que, si no la hay, la imagen se obtiene del registro ascendente, se guarda en Harbor y después se devuelve al cliente.](../.gitbook/assets/en-container-registry-03-harbor-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-03-harbor-2.html)

Configure Harbor como caché de proxy para registros externos:

```bash
# Create proxy cache project via API
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/projects" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "project_name": "dockerhub-proxy",
    "registry_id": 1,
    "metadata": {
      "public": "true"
    }
  }'
```

Descargue desde la ruta explícita del proxy, por ejemplo, `harbor.example.com/dockerhub-proxy/library/nginx:1.30.6`. Si no hay una coincidencia en la caché, se requiere acceso ascendente. La vigencia del contenido almacenado en caché, el comportamiento ante eliminaciones en el registro ascendente y la autenticación dependen de la configuración del proyecto de proxy; esto no garantiza que todo el contenido esté disponible sin conexión.

### Recolección de basura

GC recupera los blobs sin referencias. `delete_untagged` también elimina artefactos sin etiquetas, que aún podrían estar implementados por resumen. Proteja primero las imágenes implementadas o necesarias para una reversión. El siguiente ejemplo realiza una ejecución de prueba sin eliminar nada.

```bash
curl --fail-with-body --user "$HARBOR_USER" -X POST \
  'https://harbor.example.com/api/v2.0/system/gc/schedule' \
  -H 'Content-Type: application/json' \
  -d '{"schedule":{"type":"Manual"},
       "parameters":{"delete_untagged":false,"dry_run":true}}'
curl --fail-with-body --user "$HARBOR_USER"   'https://harbor.example.com/api/v2.0/system/gc'
```

Revise los resultados antes de configurar una ejecución o programación real en la interfaz de usuario. Harbor permite operaciones de envío/descarga durante GC, pero la carga de E/S y el periodo de protección de las cargas recientes pueden retrasar la recuperación de espacio.

### Políticas de retención de etiquetas

En la vista Policy → Tag Retention del proyecto, defina qué se debe **conservar**. Si combina las 10 cargas más recientes con los últimos 30 días, se conservará la **unión/OR** de ambos conjuntos, posiblemente más de 10 artefactos. Use Dry Run para revisar las etiquetas/artefactos excluidos, las relaciones entre firmas y los resúmenes implementados o necesarios para una reversión.

El endpoint de creación de políticas es `/api/v2.0/retentions`, no un endpoint `/tag-retention` del proyecto. En lugar de crear una política con un ID de proyecto supuesto, inspeccione y ejecute una prueba de una política existente configurada en la interfaz de usuario.

```bash
curl --fail-with-body --user "$HARBOR_USER" \
  'https://harbor.example.com/api/v2.0/projects/myapp' \
  | jq '{project_id, retention_id: .metadata.retention_id}'
# Use the actual non-empty policy ID returned above.
: "${RETENTION_ID:?Set an existing retention policy ID}"
curl --fail-with-body --user "$HARBOR_USER"   "https://harbor.example.com/api/v2.0/retentions/${RETENTION_ID}"
curl --fail-with-body --user "$HARBOR_USER" -X POST \
  "https://harbor.example.com/api/v2.0/retentions/${RETENTION_ID}/executions" \
  -H 'Content-Type: application/json' -d '{"dry_run":true}'
```

## Prácticas recomendadas

### Alta disponibilidad

Distribuya al menos dos réplicas de portal/core/jobservice/registry y valide la conmutación por error de PostgreSQL, Redis y el propio almacenamiento compartido. Para S3, configure `persistence.imageChartStorage.type: s3`, el bucket/la región y una identidad IAM explícita para el Pod de registry o `existingSecret`. No incluya claves de larga duración en los valores. IRSA/Pod Identity requiere compatibilidad con el SDK en la imagen de registry, el ServiceAccount correcto y permisos de S3 con alcance limitado; omitir las claves estáticas no configura por sí solo un rol de IAM.

### Endurecimiento de la seguridad

Use TLS externo/interno, OIDC/LDAP, robots con permisos limitados y caducidad, registros de auditoría y gestión de parches. Elabore las NetworkPolicies a partir de las etiquetas de Pod/puertos de contenedor renderizados y de los flujos necesarios de DNS, core/registry/jobservice, PostgreSQL/Redis, base de datos del analizador y replicación. Una política general limitada al puerto 443 puede interrumpir el tráfico interno y DNS. Gestione los requisitos de contraseña/MFA mediante el proveedor de identidad en lugar de suponer que Harbor dispone de controles no documentados en la interfaz de usuario.

### Estrategia de copias de seguridad

Coordine las escrituras, la replicación y GC para capturar un punto de recuperación coherente de PostgreSQL, los blobs del registro, la configuración, TLS y las claves de cifrado. Los valores de Helm no hacen copias de seguridad de bases de datos ni imágenes; el versionado de S3 o `aws s3 sync` por sí solos no garantizan una instantánea coherente. El YAML de Secret solo está codificado en base64, así que guárdelo en una copia de seguridad cifrada y con acceso controlado. Pruebe la restauración de proyectos/autenticación de robots, descargas por resumen, firmas, políticas y resultados de análisis.

### Supervisión

Use `metrics.enabled` del chart y, si existen los CRD del Operator, `metrics.serviceMonitor.enabled`. Inspeccione los ServiceMonitor/puertos de Service generados en lugar de suponer un puerto `http-metrics`. Haga coincidir los selectores de ServiceMonitor de Prometheus y de namespace. Supervise la capacidad de almacenamiento/base de datos, los errores de replicación/análisis/GC, los retrasos en las colas, la vigencia de la base de datos de Trivy y el vencimiento de certificados/robots.

## Resumen

Harbor ofrece una solución completa de registro de contenedores de nivel empresarial que destaca por:

- **Seguridad**: análisis de vulnerabilidades, firma de imágenes y RBAC integrados
- **Flexibilidad**: autohospedado, con control total sobre los datos y la infraestructura
- **Compatibilidad con redes aisladas**: diseñado para entornos desconectados
- **Multitenencia**: aislamiento basado en proyectos con control de acceso granular
- **Integración**: replicación mediante adaptadores de registro y formatos de artefactos compatibles

### Cuándo elegir Harbor

| Escenario | Recomendación |
|----------|----------------|
| Entorno aislado de la red | Harbor u otro registro autohospedado compatible |
| Soberanía estricta de los datos | Harbor |
| Implementación multinube | Harbor |
| Nativo de AWS con EKS | Considere primero ECR; Harbor para funciones avanzadas |
| Equipo pequeño con operaciones limitadas | Docker Hub o ECR |
| Empresa con requisitos de cumplimiento | Harbor o ECR |

### Puntos clave

1. **Planifique cuidadosamente el almacenamiento**: use almacenamiento compatible con S3 en producción
2. **Configure la replicación**: establezca la replicación de recuperación ante desastres desde el primer día
3. **Habilite el análisis**: análisis automático al enviar imágenes con umbrales de gravedad
4. **Use cuentas de robot**: nunca use credenciales personales en CI/CD
5. **Implemente la retención**: configure la recolección de basura y las políticas de retención
6. **Supervise y genere alertas**: use métricas y alertas de Prometheus
7. **Haga copias de seguridad con regularidad**: las copias de seguridad de bases de datos son esenciales para la recuperación ante desastres

## Referencias

- [Versión 2.15.4 de Harbor](https://github.com/goharbor/harbor/releases/tag/v2.15.4)
- [Valores del Helm chart 1.19.2](https://github.com/goharbor/harbor-helm/blob/v1.19.2/values.yaml)
- [Esquema de API de Harbor 2.15.4](https://github.com/goharbor/harbor/blob/v2.15.4/api/v2.0/swagger.yaml)
- [Permisos de los roles de proyecto](https://goharbor.io/docs/main/administration/managing-users/user-permissions-by-role/)
- [Cosign y Notation](https://goharbor.io/docs/main/working-with-projects/working-with-images/sign-images/)
- [Hosts de registro de Containerd](https://github.com/containerd/containerd/blob/main/docs/hosts.md)
