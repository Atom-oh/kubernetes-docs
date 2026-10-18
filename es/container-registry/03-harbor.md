# Harbor

> **Última actualización**: 16 de octubre de 2026

## Descripción general

Harbor es un registro de contenedores de código abierto, diseñado para la nube, que ofrece funciones empresariales para almacenar, firmar y analizar imágenes de contenedores. Su condición de proyecto Graduated de CNCF refleja su madurez, seguridad y adopción en el sector.

### Funciones principales

| Función | Descripción |
|---------|-------------|
| **Varios inquilinos** | Aislamiento por proyectos con RBAC |
| **Análisis de vulnerabilidades** | Analizador Trivy integrado |
| **Firma de imágenes** | Compatible con Cosign y Notation |
| **Replicación** | Envío y descarga entre registros |
| **Recolección de basura** | Limpieza automática de capas que ya no se utilizan |
| **Caché de proxy** | Almacena contenido de registros remotos, como Docker Hub |
| **Registro de auditoría** | Historial completo de operaciones |
| **OIDC/LDAP** | Integración con la identidad empresarial |
| **Gestión de cuotas** | Límites de almacenamiento por proyecto |
| **Cuentas de robot** | Cuentas de servicio para automatización |

### Arquitectura

![Estructura interna de Harbor: el Portal proporciona acceso a la API Core, que distribuye las solicitudes al Registry, Job Service, PostgreSQL y Redis, mientras que Job Service ejecuta el analizador Trivy.](../.gitbook/assets/en-container-registry-03-harbor-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-03-harbor-0.html)

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

La revisión del 16 de octubre de 2026 utiliza como referencia **Harbor 2.15.4 / Helm chart 1.19.2**. Las versiones de la aplicación y del chart son distintas. En esa revisión, el chart más reciente, 1.19.2, seguía utilizando appVersion 2.15.2 de forma predeterminada; por tanto, instalarlo sin cambiar los valores no incluye las correcciones de seguridad de 2.15.3, como GHSA-2phj-cp9f-qq6w. El ejemplo presupone que ya dispone de PostgreSQL externo de alta disponibilidad, Redis y almacenamiento compartido. El archivo de valores no crea esos recursos.

### Requisitos previos

- Prepare versiones compatibles de Kubernetes y Helm, DNS, un controlador Ingress que siga recibiendo mantenimiento y su `IngressClass`. Configure en ese controlador los límites de carga, los tiempos de espera y TLS.
- Cree el Secret `harbor-tls`, con el certificado y la clave, en el namespace `harbor`. El certificado debe corresponder al nombre de host, y los clientes y los nodos deben confiar en su CA.
- Dos réplicas de Registry en nodos distintos necesitan un **PVC RWX compartido o almacenamiento de objetos**. Compartir un único PVC EBS `gp3` RWO entre nodos no proporciona alta disponibilidad.
- Prepare la base de datos PostgreSQL `registry`, su usuario y la clave `password` del Secret `harbor-database`. `sslmode: require` exige cifrado, pero no basta para validar el certificado y el nombre de host. Cuando necesite esa validación, compruebe la confianza en la CA y `verify-full`.
- Redis debe admitir las distintas bases de datos lógicas que utiliza Harbor. No utilice un modo Redis Cluster limitado a DB 0. Prepare `REDIS_PASSWORD` en el Secret `harbor-redis` y valide la conexión TLS. Para una CA privada, utilice `caBundleSecretName` del chart.

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

### Archivo values.yaml para producción

Guarde el archivo como `harbor-values.yaml` y sustituya todos los nombres de host y StorageClass de ejemplo. Añada solicitudes y límites de recursos y distribuya los Pods según la carga medida y los nodos disponibles. Active `serviceMonitor.enabled` después de instalar los CRD de Prometheus Operator.

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

Antes de actualizar, consulte en las notas de la versión qué ruta de actualización está admitida. Haga una copia de seguridad de los metadatos, los datos del registro, la configuración y las claves de cifrado en un punto de recuperación coherente, y pruebe la restauración. Compare los valores del chart anterior y del nuevo, y pruebe la generación de manifiestos y las migraciones en un entorno previo a producción. Fije la versión del chart de destino en `helm upgrade`. Una reversión de Helm por sí sola puede no revertir una migración de base de datos.

Notary v1 se eliminó en Harbor 2.9. Cosign y Notation son herramientas externas de firma; sus firmas se almacenan como artefactos OCI en el registro.

## Proyectos y RBAC

Los ejemplos de API presuponen una instancia de prueba de Harbor accesible mediante HTTPS y la disponibilidad de `curl` y `jq`. Asigne a `HARBOR_USER` un usuario con los permisos necesarios. `curl --user "$HARBOR_USER"` solicita la contraseña. Para automatizar, obtenga las credenciales de robot con permisos limitados de su gestor de secretos y evite escribirlas en los registros.

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
| **Administrador de proyecto** | Control total sobre miembros, políticas e imágenes |
| **Mantenedor** | Enviar y descargar imágenes, analizarlas y eliminar etiquetas |
| **Desarrollador** | Enviar y descargar imágenes; no incluye administrar miembros |
| **Invitado** | Solo descargar imágenes |
| **Invitado limitado** | Descargar y leer artefactos; no puede listar miembros ni registros del proyecto |

### Añadir miembros

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

![Harbor permite replicar en dos direcciones: descargar imágenes de un registro externo para mantener una copia local, o enviarlas desde un Harbor de origen a un registro remoto para distribuirlas.](../.gitbook/assets/en-container-registry-03-harbor-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-03-harbor-1.html)

Harbor admite la replicación bidireccional entre registros.

Los ID de endpoint `1` y `3` del ejemplo son ilustrativos. Obtenga los ID reales de la cabecera `Location` de la respuesta de creación o de la lista de endpoints. Las expresiones cron tienen seis campos, incluidos los segundos (`0 0 0 * * *`); compruebe la zona horaria de Job Service. La replicación de descarga necesita acceso al registro de origen y no puede importar contenido a una red completamente desconectada. La replicación por eventos sigue las operaciones locales de envío, cambio de etiqueta y eliminación en Harbor; no sigue cualquier cambio de un registro remoto.

### Modos de replicación

| Modo | Descripción | Caso de uso |
|------|-------------|----------|
| **Envío** | Harbor envía contenido a un registro remoto | Distribuirlo a ubicaciones periféricas |
| **Descarga** | Harbor descarga contenido de un registro remoto | Mantener una copia de Docker Hub o sincronizar desde ECR |

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

- Vulnerabilidades en paquetes del sistema operativo, como Alpine, Debian, Ubuntu o RHEL.
- Dependencias de aplicaciones: npm, pip, gem, Maven y módulos de Go.


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

El análisis es asíncrono. Compruebe que haya terminado y que su base de datos esté actualizada. Un informe vacío o incompleto no demuestra que la imagen esté libre de vulnerabilidades. A diferencia del nombre de un solo componente `app`, los nombres de repositorio anidados, como `team/app`, requieren doble codificación de URL en la API de Harbor.

### Listas de excepciones de CVE

Limite las excepciones a CVE aprobados, cada uno con un responsable, una justificación y una fecha de vencimiento. La solicitud PUT siguiente sustituye la lista de excepciones del proyecto; combine primero las entradas existentes. Además, desactiva la reutilización de la lista del sistema y requiere un identificador aprobado y un vencimiento futuro.

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

Esta política restringe las descargas desde el registro. No inspecciona ni detiene contenedores que ya estén en funcionamiento o utilicen imágenes en caché. Activar el análisis automático no activa por sí solo el bloqueo de descargas.

## Firma de imágenes

Las firmas verifican la integridad de los artefactos y que proceden de un firmante de confianza. No corrigen vulnerabilidades ni inspeccionan Pods en funcionamiento. Instale Cosign o Notation según sus guías oficiales y compruebe que el formato de firma sea compatible con Harbor y con su motor de políticas.

### Integración con Cosign

```bash
# HARBOR_IMAGE must include an existing image digest, not a mutable tag.
: "${HARBOR_IMAGE:?Set harbor.example.com/myapp/app@sha256:<actual-digest>}"
cosign version
cosign generate-key-pair
cosign sign --key cosign.key "$HARBOR_IMAGE"
cosign verify --key cosign.pub "$HARBOR_IMAGE"
```

La firma sin clave utiliza una identidad OIDC y un registro de transparencia. Al verificarla, limite la comprobación a emisores e identidades de confianza. En el ejemplo de firma con clave, proteja tanto la clave privada como su contraseña. Un entorno completamente desconectado no puede utilizar directamente un flujo que dependa de los servicios públicos de Sigstore.

### Integración con Notation (Notary v2)

Este ejemplo utiliza un certificado autofirmado destinado exclusivamente a pruebas. Antes de verificar, importe la política de confianza para el almacén creado por `generate-test`. En producción, utilice la gestión de CA y claves de la organización y restricciones explícitas sobre la identidad del firmante.

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

Seleccione la política de Cosign o de Notation en Configuration del proyecto. Si activa ambas, se necesitan los dos tipos de firma. El chart no dispone de una opción `core.cosignKeyFile` para verificar claves públicas. Distinga las comprobaciones del registro sobre los artefactos de firma asociados de la verificación contra las claves e identidades de confianza de su organización.

### Aplicación de políticas de Kubernetes

Para aplicar la política al desplegar, configure una política de admisión, por ejemplo con Kyverno, como se describe en [Seguridad de imágenes](../security/07-image-security.md). Proporcione claves válidas o un emisor y una identidad OIDC de confianza, un alcance de imágenes preciso y credenciales del registro privado. Incluya los contenedores init y efímeros. Valide primero en Audit y después en Enforce, incluidos los casos de clave incorrecta, imagen sin firma y reasignación de una etiqueta.

## Escenarios de redes aisladas

El instalador sin conexión para Docker Compose y el despliegue en Kubernetes mediante Helm son métodos de instalación distintos. El instalador sin conexión incluye las imágenes de Harbor, pero no todos los paquetes de Docker y Compose, charts de Kubernetes, CNI, imágenes de aplicaciones o bases de datos de Trivy.

### Instalador sin conexión

```bash
HARBOR_VERSION=2.15.4
curl --fail --location --remote-name \
  "https://github.com/goharbor/harbor/releases/download/v${HARBOR_VERSION}/harbor-offline-installer-v${HARBOR_VERSION}.tgz"
# Verify the release checksum/signature before transporting the bundle.
sha256sum "harbor-offline-installer-v${HARBOR_VERSION}.tgz" > harbor-bundle.sha256
# Transfer both files through the approved offline transport.
```

En el host desconectado, ejecute lo siguiente. Una suma SHA-256 generada localmente permite comprobar la integridad de la transferencia; no sustituye la verificación de la firma de la versión publicada por el proyecto.

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

Utilice un binario kubeadm compatible para listar las imágenes del plano de control de la versión exacta de Kubernetes admitida. Añada por separado las imágenes de CNI, CSI, Ingress y supervisión, así como los charts y CRD. Para clústeres que no administra kubeadm, utilice el inventario de imágenes de la propia distribución.

```bash
: "${K8S_VERSION:?Set the exact supported Kubernetes patch version}"
kubeadm config images list --kubernetes-version "$K8S_VERSION" > kubeadm-images.txt
```

### Script automatizado de sincronización de imágenes

Asocie explícitamente las referencias de origen y destino en un archivo TSV. Reetiquetar usando solo el nombre base puede provocar colisiones entre registros o namespaces. Estos ejemplos con Bash y Skopeo transfieren todas las plataformas mediante archivos OCI. Los artefactos de firma y SBOM que referencian la imagen requieren transporte y verificación independientes, según lo que admitan las herramientas.

```text
# images.tsv: two columns separated by a TAB; replace the internal hostname.
docker.io/library/nginx:1.30.6	harbor.airgap.local/k8s-system/dockerhub/library/nginx:1.30.6
```

En el entorno conectado:

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

Después de transferir `image-bundle`, en el entorno desconectado:

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

Aplique las URI internas de imagen correspondientes a la configuración de Pod, Helm o kubeadm y compruebe los digests, las plataformas y las descargas. `--all` solicita todos los manifiestos de plataforma. Convertir la representación puede cambiar un digest, por lo que debe comparar los resultados de origen y destino.

### Actualización de la base de datos de Trivy para redes aisladas

```bash
# Use a Trivy version compatible with the deployed Harbor scanner adapter.
trivy image --cache-dir ./trivy-cache --download-db-only
trivy image --cache-dir ./trivy-cache --download-java-db-only
tar -C trivy-cache -czf trivy-db-bundle.tgz db java-db
```

Extraiga el paquete en la raíz de la caché persistente `/home/scanner/.cache/trivy` de cada réplica de Trivy. Asigne el propietario correcto a `db/trivy.db`, `db/metadata.json`, `java-db/trivy-java.db` y sus metadatos. Detenga el analizador o utilice un PVC de sustitución o un trabajo de inicialización; evite sobrescribir una base de datos abierta. La forma `tar -C` anterior evita introducir accidentalmente una ruta de directorio personal dentro de la caché.

```yaml
trivy:
  skipUpdate: true
  skipJavaDBUpdate: true
  offlineScan: true
```

`offlineScan` por sí solo no desactiva todas las actualizaciones ni crea las bases de datos que falten. Establezca un calendario para importar las bases de datos y mantenerlas actualizadas, y vuelva a analizar las imágenes después de actualizarlas. En Compose, las claves equivalentes de `harbor.yml` son `skip_update`, `skip_java_db_update` y `offline_scan`.

### Configuración de confianza de Containerd

Utilice referencias explícitas a las imágenes del Harbor interno en los manifiestos sin conexión. Redirigir cualquier registro externo a `/v2/<project>` no modifica automáticamente las rutas de repositorio ni las credenciales. Instale la CA en cada nodo y utilice la configuración apropiada para su versión del entorno de ejecución.

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

Cuando cambie `config_path`, reinicie containerd según el procedimiento de mantenimiento de nodos y compruebe después una descarga real mediante CRI. Proporcione credenciales limitadas a la descarga de imágenes y al namespace mediante `imagePullSecrets`.

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

![Una solicitud de descarga llega a la caché de proxy de Harbor. Si la imagen está en caché, se devuelve directamente. Si no está, Harbor la obtiene del registro de origen, la almacena y después la devuelve al cliente.](../.gitbook/assets/en-container-registry-03-harbor-2.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-03-harbor-2.html)

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

Descargue mediante la ruta explícita del proxy, por ejemplo `harbor.example.com/dockerhub-proxy/library/nginx:1.30.6`. Si el contenido no está en caché, se necesita acceso al registro de origen. La actualización del contenido en caché, el comportamiento ante eliminaciones en origen y la autenticación dependen de la configuración del proyecto de proxy. La caché no garantiza disponer de todo el contenido sin conexión.

### Recolección de basura

GC recupera el espacio de los blobs que ya no tienen referencias. `delete_untagged` elimina además los artefactos sin etiquetas, aunque puedan seguir desplegados mediante su digest. Proteja primero las imágenes desplegadas y las necesarias para una reversión. El ejemplo siguiente ejecuta una simulación sin borrar contenido.

```bash
curl --fail-with-body --user "$HARBOR_USER" -X POST \
  'https://harbor.example.com/api/v2.0/system/gc/schedule' \
  -H 'Content-Type: application/json' \
  -d '{"schedule":{"type":"Manual"},
       "parameters":{"delete_untagged":false,"dry_run":true}}'
curl --fail-with-body --user "$HARBOR_USER"   'https://harbor.example.com/api/v2.0/system/gc'
```

Revise los resultados antes de configurar una ejecución real o una programación en la interfaz. Harbor permite envíos y descargas durante GC, pero la carga de E/S y el período de protección de cargas recientes pueden retrasar la recuperación de espacio.

### Políticas de retención de etiquetas

En Policy → Tag Retention del proyecto, defina qué debe **conservarse**. Combinar los 10 envíos más recientes con los de los últimos 30 días conserva la **unión de ambos conjuntos, mediante OR**, por lo que pueden quedar más de 10 artefactos. Utilice Dry Run para revisar las etiquetas y los artefactos excluidos, sus relaciones con las firmas y los digests desplegados o necesarios para una reversión.

El endpoint para crear políticas es `/api/v2.0/retentions`, no `/tag-retention` dentro del proyecto. En lugar de crear una política con un ID de proyecto supuesto, inspeccione una política existente configurada en la interfaz y ejecute su simulación.

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

Distribuya al menos dos réplicas de portal, core, jobservice y registry y valide la conmutación ante fallos de PostgreSQL, Redis y del propio almacenamiento compartido. Para S3, configure `persistence.imageChartStorage.type: s3`, el bucket y la región, además de una identidad IAM explícita para el Pod del registro o `existingSecret`. Evite incluir claves de larga duración en los valores. IRSA o Pod Identity requieren un SDK compatible en la imagen del registro, el ServiceAccount correcto y permisos limitados de S3. Omitir las claves estáticas no configura automáticamente un rol de IAM.

### Endurecimiento de la seguridad

Utilice TLS externo e interno, OIDC o LDAP, cuentas de robot con permisos limitados y vencimiento, registros de auditoría y gestión de parches. Diseñe las NetworkPolicies a partir de las etiquetas de Pods y los puertos de contenedor de los manifiestos generados. Incluya los flujos necesarios de DNS, core, registry, jobservice, PostgreSQL, Redis, la base de datos del analizador y la replicación. Permitir únicamente el puerto 443 puede impedir el tráfico interno y DNS. Gestione las contraseñas y MFA mediante el proveedor de identidad; no presuponga controles de Harbor que no estén documentados.

### Estrategia de copias de seguridad

Coordine las escrituras, la replicación y GC para obtener un punto de recuperación coherente de PostgreSQL, los blobs del registro, la configuración, TLS y las claves de cifrado. Los valores de Helm no hacen copias de seguridad de las bases de datos o las imágenes. Tampoco el versionado de S3 ni `aws s3 sync` garantizan por sí solos una instantánea coherente. El YAML de un Secret solo codifica sus datos en base64; guárdelo en una copia cifrada con acceso controlado. Pruebe la restauración de proyectos, la autenticación de robots, las descargas por digest, las firmas, las políticas y los resultados de análisis.

### Supervisión

Utilice `metrics.enabled` del chart y, cuando estén instalados los CRD de Operator, `metrics.serviceMonitor.enabled`. Inspeccione los puertos de ServiceMonitor y Service generados en lugar de suponer un puerto `http-metrics`. Ajuste los selectores de ServiceMonitor y namespace de Prometheus. Supervise la capacidad de almacenamiento y base de datos, los fallos de replicación, análisis y GC, los retrasos en las colas, la actualización de la base de datos de Trivy y el vencimiento de certificados y cuentas de robot.

## Resumen

Harbor ofrece una solución completa de registro de contenedores de nivel empresarial que destaca por:

- **Seguridad**: análisis de vulnerabilidades, firma de imágenes y RBAC integrados.
- **Flexibilidad**: alojamiento propio, con control total de los datos y la infraestructura.
- **Entornos sin conexión**: diseñado para redes desconectadas.
- **Varios inquilinos**: aislamiento por proyectos con control de acceso detallado.
- **Integración**: replicación mediante adaptadores de registro y formatos de artefactos compatibles.

### Cuándo elegir Harbor

| Escenario | Recomendación |
|----------|----------------|
| Entorno desconectado | Harbor u otro registro compatible con alojamiento propio |
| Requisitos estrictos de soberanía de datos | Harbor |
| Despliegue en varias nubes | Harbor |
| Entorno nativo de AWS con EKS | Considere primero ECR; Harbor para funciones avanzadas |
| Equipo pequeño con poca capacidad operativa | Docker Hub o ECR |
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
