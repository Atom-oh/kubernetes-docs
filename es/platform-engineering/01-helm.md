# Gestor de paquetes Helm

> **Última actualización**: September 12, 2026
> **Validación local**: Helm 3.21.3 / Helm 4.3.0

Helm renderiza charts y gestiona recursos de Kubernetes y el historial de releases. La versión del chart, appVersion, el tag/digest de la imagen y la revisión del release son valores diferentes. Helm 4 acepta charts existentes de apiVersion:v2, pero el comportamiento de CLI/apply/wait debe verificarse para la versión exacta.

## Conceptos básicos y permisos

Helm 3 eliminó Tiller; los clientes utilizan sus propias credenciales de Kubernetes/RBAC. La comunicación con repositorios de charts/registros OCI es independiente del acceso a la API de Kubernetes. Eliminar Tiller no hace inofensivos a los charts no seguros ni a los permisos amplios.

El almacenamiento de releases usa Secrets en el namespace del release de forma predeterminada; se pueden configurar alternativas como backends ConfigMap/SQL. Los datos de releases almacenados incluyen manifests/values y pueden exponer información sensible. Base64 no es cifrado; restrinja el acceso a los Secrets de releases.

## Ejemplo completo de chart local

`examples/platform/helm/reviewed-app` contiene los ocho archivos siguientes. Se probaron las salidas de lint/render de Helm 3/4, el empaquetado, las sobrescrituras de values y el rechazo de replicaCount no válido. No se realizó ninguna instalación de Kubernetes ni ejecución de contenedores. Verifique los digests de imágenes, namespaces, hardware y políticas antes de las operaciones.

### Chart.yaml

```yaml
apiVersion: v2
name: reviewed-app
description: Offline Helm teaching chart
type: application
version: 0.1.0
appVersion: "1.30.4"
```

### values.yaml

```yaml
replicaCount: 1
image:
  repository: nginxinc/nginx-unprivileged
  tag: "1.30.4-alpine"
service:
  port: 8080
resources:
  requests:
    cpu: 100m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 128Mi
env:
  LOG_LEVEL: info
```

### values.schema.json

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "replicaCount",
    "image",
    "service"
  ],
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 0,
      "maximum": 5
    },
    "image": {
      "type": "object",
      "required": [
        "repository",
        "tag"
      ],
      "properties": {
        "repository": {
          "type": "string",
          "minLength": 1
        },
        "tag": {
          "type": "string",
          "minLength": 1
        }
      }
    },
    "service": {
      "type": "object",
      "required": [
        "port"
      ],
      "properties": {
        "port": {
          "type": "integer",
          "minimum": 1,
          "maximum": 65535
        }
      }
    },
    "env": {
      "type": "object",
      "additionalProperties": {
        "type": "string"
      }
    }
  }
}
```

### templates/_helpers.tpl

```text
{{- define "reviewed-app.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- define "reviewed-app.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
{{- end -}}
```

### templates/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "reviewed-app.fullname" . }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "reviewed-app.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "reviewed-app.selectorLabels" . | nindent 8 }}
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
      - name: web
        image: {{ printf "%s:%s" .Values.image.repository .Values.image.tag | quote }}
        ports:
        - name: http
          containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: [ALL]
        resources:
          {{- toYaml .Values.resources | nindent 10 }}
        env:
          {{- range $key, $value := .Values.env }}
        - name: {{ $key | quote }}
          value: {{ $value | quote }}
          {{- end }}
        readinessProbe:
          httpGet:
            path: /
            port: http
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 64Mi
```

### templates/service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "reviewed-app.fullname" . }}
spec:
  type: ClusterIP
  selector:
    {{- include "reviewed-app.selectorLabels" . | nindent 4 }}
  ports:
  - name: http
    port: {{ .Values.service.port }}
    targetPort: http
```

### templates/NOTES.txt

```text
Inspect the rendered resources and prepare namespace/image compatibility before installation.
Release: {{ .Release.Name }}
Namespace: {{ .Release.Namespace }}
```

### .helmignore

```text
*.private
```

Todos los helpers están definidos, el Service apunta a un puerto de contenedor con nombre, securityContext está en el manifest y resources/env se conectan desde values a las templates. Una entrada de values sin usar no tiene efecto. Este chart básico no crea una base de datos, Ingress ni autoscaler.

### Comprobaciones locales

Ejecute desde la raíz del repositorio y compruebe el binario seleccionado con `helm version --short`.

```bash
helm lint examples/platform/helm/reviewed-app
helm template demo examples/platform/helm/reviewed-app --namespace example
helm template demo examples/platform/helm/reviewed-app   --set replicaCount=3 --set-string env.MAX_CONNECTIONS=100
helm package examples/platform/helm/reviewed-app --destination ./chart-packages
```

El éxito de lint/template no valida admission, CEL, RBAC, la ejecución de imágenes, la conectividad de Service ni la disponibilidad. Los hooks de prueba deben ejecutarse realmente en un clúster. `helm template --api-versions` proporciona capacidades sin conexión; no instala CRDs.

## Comandos y diferencias entre Helm 3/4

| Propósito | Ejemplo y límites |
| --- | --- |
| Repositorios | `helm repo add/update/list/remove`, `helm search repo`; los registros OCI tienen flujos independientes de login/pull |
| Instalación | `helm install demo ./chart -n example --create-namespace`; verifique la existencia del namespace/release |
| Instalación o actualización | `helm upgrade --install`; los hooks, valores aleatorios y el estado externo no tienen por qué ser idempotentes |
| Inspección | `helm list -n example`, status/history/get values/get manifest; proteja la salida sensible |
| Valores calculados | `helm get values demo -n example --all` incluye los valores predeterminados del chart |
| Rollback | `helm rollback demo REVISION -n example`; la revisión no es un tag de imagen |
| Desinstalación | `helm uninstall demo -n example`; inspeccione el ciclo de vida de PVC/CRD/hook/recurso externo |

El antiguo repositorio stable es histórico, no un valor predeterminado actual. Verifique la disponibilidad, las licencias, el soporte y la seguridad de charts/imágenes externos, y fije las versiones de charts. Las antiguas dependencias Bitnami PostgreSQL12/Redis17 ya no son los valores predeterminados de este ejemplo.

### Ejecuciones en seco y espera

Helm 4.3 distingue `--dry-run=client` y `--dry-run=server`. En este entorno, el modo cliente de 4.3 funcionó sin un clúster; el dry-run de instalación en cliente de 3.21.3 intentó acceder al clúster y falló. Utilice la ruta verificada de `helm template` para el renderizado sin conexión. El modo servidor necesita acceso/permisos de clúster y no demuestra todos los efectos secundarios de webhooks/externos.

En Helm 4.3, omitir --wait usa hookOnly de forma predeterminada; especificar --wait usa watcher de forma predeterminada, y también está disponible legacy. `--rollback-on-failure` revierte las actualizaciones fallidas a un release exitoso anterior. Su nombre difiere de --atomic de Helm 3. `--force-replace` y `--force-conflicts` controlan por separado el reemplazo y los conflictos de server-side-apply; consulte la ayuda de la versión exacta.

Rollback no es una transacción que revierta migraciones de DB, efectos de API externas o datos eliminados. Distinga entre timeout, disponibilidad de Pod, finalización de Job y SLO de la aplicación.

## Templates y values

Chart, Release, Values y Capabilities son objetos de contexto. range/with cambian el contexto del punto; use `$` cuando se necesite la raíz. Capabilities refleja la información de descubrimiento proporcionada, no la compatibilidad universal.

include devuelve la salida de una template con nombre como una cadena y puede canalizarse a nindent, que también inserta una nueva línea. Use prefijos en los nombres de helpers para evitar colisiones de subcharts y evite cambios innecesarios de selector entre actualizaciones.

default/coalesce tratan false, cero, cadenas vacías y colecciones como vacíos. Compruebe la existencia/tipos por separado al preservar false/cero explícitos. Un valor predeterminado no protege todas las búsquedas anidadas cuyo mapa padre está ausente.

values.yaml es datos: <code v-pre>{{ .Values... }}</code> integrado no se evalúa automáticamente de nuevo. Los autores de charts pueden usar explícitamente tpl cuando sea necesario, pero deben revisar la confianza de entrada y los privilegios de templates. Los anteriores strings de selector de storageClass y Blue/Green de subcharts no se conectaron automáticamente.

Para archivos/sobrescrituras repetidos, prevalecen los values más a la derecha; comprenda la combinación de mapas y el reemplazo de listas. Guarde dev/staging/prod como archivos separados en lugar de claves duplicadas en un documento YAML. Use --set-string para cadenas que parecen números y --set-json compatible con la versión para estructuras.

--reuse-values, --reset-values y --reset-then-reuse-values combinan de forma distinta los values de releases anteriores y los nuevos valores predeterminados. Revise los valores calculados y las diferencias renderizadas en lugar de confiar en el comportamiento implícito.

## Gestión de dependencias

Chart.yaml declara los nombres, versiones, repositorios y alias/condiciones opcionales de las dependencias. Este fragmento asume un **subchart auxiliar local preparado**.

```yaml
dependencies:
- name: helper
  alias: cache
  version: 0.1.0
  repository: file://../dependency-child
  condition: cache.enabled
```

Con un alias, coloque los values bajo cache y use una condición coincidente. Pruebe el comportamiento cuando falta una ruta de condición. Los valores globales importan solo cuando el subchart los consume; import-values requiere una estructura de exportación hija/padre coincidente.

dependency update resuelve las restricciones de Chart.yaml y escribe Chart.lock. build usa versiones bloqueadas; sin un bloqueo puede resolver de forma similar a update. Un bloqueo por sí solo no establece resistencia a manipulaciones, imágenes de tiempo de ejecución fijadas ni reproducibilidad completa. Gestione los digests/firmas de charts, las rutas de suministro y las revisiones de imágenes. Se probaron update/build de dependencias de archivos locales y la activación/desactivación de alias con Helm 3/4.

## Hooks, CRDs y pruebas

Los hooks pre/post install, upgrade, rollback, delete y test se ejecutan en sus etapas de ciclo de vida. Los pesos más bajos se ejecutan primero; inspeccione la ordenación por kind/name en caso de empates. Una migración pre-install puede ejecutarse antes de que exista el recurso de base de datos ordinario del chart.

Los Job/Pod de hooks necesitan ejecutables, imágenes, Services/Secrets, permisos, timeouts y comportamiento seguro para repeticiones reales. Planifique la limpieza con before-hook-creation/hook-succeeded/hook-failed y TTL de Job; uninstall no tiene por qué eliminar todos los recursos de hooks. Interprete la disponibilidad post-install junto con --wait.

Los CRDs en crds/ difieren de las templates normales. No suponga la actualización/eliminación automática ni el rollback de esquemas de CRD. Use planes explícitos de migración y retención de recursos personalizados; eliminar un CRD puede borrar los datos de recursos personalizados.

helm test ejecuta los hooks declarados. Una conectividad HTTP simple no valida bases de datos, seguridad, carga ni recuperación. Blue/Green/canary necesita Deployments, Services/rutas de mesh, controladores y condiciones de métricas/rollback reales. Los values por sí solos no implementan la entrega progresiva.

## GitOps y seguridad

Argo CD generalmente usa Helm como renderizador de templates, distinto de ser propietario del ciclo de vida de releases de Helm. Flux helm-controller reconcilia HelmRelease. Verifique las revisiones de fuente/chart, el namespace/precedencia de valuesFrom, el mapeo de hooks, la poda y la propiedad; evite controladores en competencia.

No coloque secretos en valores predeterminados de charts, argumentos --set ni salida de depuración. --hide-secret cubre la salida de Kubernetes Secret durante dry-run, no el enmascaramiento general de todos los values/logs. Las referencias a Secret existentes entregadas mediante variables de entorno de la app siguen infringiendo las políticas de credenciales en archivos. Use volúmenes Secret aprobados y rutas de relectura/rotación de archivos.

Prepare por separado las API actuales como ESO v1 y sus controladores. Sealed Secrets/helm-secrets requieren su controlador/plugin, acceso a clave/KMS y flujo de trabajo de descifrado; no son características principales de Helm. Inspeccione si los values descifrados entran en registros de releases o logs.

Los ServiceAccounts/Roles por sí solos no otorgan permisos de carga de trabajo. Conecte RoleBindings y serviceAccountName cuando sea necesario, y no conceda get/list/watch de todos los Secrets simplemente para un volumen Secret. El chart web de demostración no necesita credenciales de la API de Kubernetes y deshabilita el automontaje de tokens.

## Orden de solución de problemas

| Síntoma | Investigación y corrección |
| --- | --- |
| Nombre de release reutilizado | Compruebe namespace/state/history; elija la actualización prevista o un nombre nuevo |
| Colisión de recurso existente | Inspeccione anotaciones/labels/controladores del propietario; use una adopción/migración revisada o cambie el nombre |
| Release fallido | Compruebe causas/events/history y vuelva a intentarlo con una revisión/configuración verificada |
| Helper faltante | Compruebe definiciones, nombres, ámbito y contexto raíz |
| Fallo de esquema | Inspeccione los values finales combinados, tipos, campos requeridos y rangos |

Las opciones de eliminación/force no son soluciones universales. Revise las diferencias, los campos inmutables, la retención de datos y otros controladores antes de elegir una mutación.

## Verificación y referencias

Se revisaron las 764 líneas de la guía, 462 líneas de cuestionario por configuración regional y 58 bloques únicos. Las comprobaciones cubrieron lint/template/package de Helm 3/4 para el chart completo, esquemas de sobrescrituras/negativos y dependencias/alias locales; el dry-run de cliente 4.3 funcionó. Se registró el fallo de acceso al clúster del dry-run de instalación de 3.21.3. No se validó ninguna instalación, actualización, rollback, hook ni comportamiento HTTP de app de Kubernetes real.

- [Helm install](https://helm.sh/docs/helm/helm_install/)
- [Helm upgrade](https://helm.sh/docs/helm/helm_upgrade/)
- [Charts and values](https://helm.sh/docs/topics/charts/)
- [Chart hooks](https://helm.sh/docs/topics/charts_hooks/)
- [Dependency build](https://helm.sh/docs/helm/helm_dependency_build/)
- [Helm 4.3.0 release](https://github.com/helm/helm/releases/tag/v4.3.0)

[Helm quiz](../quizzes/platform-engineering/01-helm-quiz.md)
