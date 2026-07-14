# Cuestionario sobre el gestor de paquetes Helm

> **Documento relacionado**: [Gestor de paquetes Helm](../../platform-engineering/01-helm.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es la razón principal por la que se eliminó Tiller en Helm v3?

- A) Para mejorar el rendimiento
- B) Para mejorar la seguridad y simplificar la arquitectura
- C) Para reducir el tamaño del chart
- D) Por compatibilidad con versiones de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para mejorar la seguridad y simplificar la arquitectura**

**Explicación:**
Tiller de Helm v2 se ejecutaba con privilegios elevados dentro del cluster, lo que planteaba riesgos de seguridad. En Helm v3, Tiller se eliminó y el cliente se comunica directamente con la API de Kubernetes, mejorando la seguridad y simplificando la arquitectura.

</details>

### 2. ¿Cuál es el propósito principal del archivo values.yaml en un Helm Chart?

- A) Almacenar metadatos del chart
- B) Definir valores de configuración predeterminados usados en templates
- C) Almacenar manifiestos de Kubernetes directamente
- D) Definir dependencias del chart

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Definir valores de configuración predeterminados usados en templates**

**Explicación:**
El archivo values.yaml define valores de configuración predeterminados que usan los templates del chart. Los usuarios pueden sobrescribir estos valores usando el flag --set o el flag -f para personalizar deployments para diferentes entornos.

</details>

### 3. ¿Cuál es el comportamiento del comando `helm upgrade --install`?

- A) Siempre instala un nuevo release
- B) Siempre actualiza un release existente
- C) Instala si el release no existe, actualiza si existe
- D) Elimina y reinstala el release

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Instala si el release no existe, actualiza si existe**

**Explicación:**
`helm upgrade --install` proporciona un comportamiento idempotente. Si el release especificado no existe, instala uno nuevo; si existe, lo actualiza. Esto es especialmente útil en pipelines de CI/CD.

</details>

### 4. ¿A qué hace referencia <code v-pre>{{ .Release.Name }}</code> en un template de Helm?

- A) Nombre del chart
- B) Nombre del cluster de Kubernetes
- C) Nombre del release instalado
- D) Nombre del namespace

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Nombre del release instalado**

**Explicación:**
`.Release.Name` es un objeto integrado de Helm que hace referencia al nombre del release especificado en el comando `helm install`. Por ejemplo, en `helm install my-app chart/`, `.Release.Name` sería "my-app".

</details>

### 5. ¿Cuál es el propósito del atributo `condition` en el campo `dependencies` de Chart.yaml?

- A) Especificar la versión del chart de dependencia
- B) Especificar la ruta de values que habilita/deshabilita el chart de dependencia
- C) Especificar la URL del repositorio del chart de dependencia
- D) Especificar la prioridad del chart de dependencia

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Especificar la ruta de values que habilita/deshabilita el chart de dependencia**

**Explicación:**
El atributo `condition` especifica una ruta en values.yaml que determina si se habilita el chart de dependencia. Por ejemplo, `condition: postgresql.enabled` significa que el subchart de PostgreSQL solo se incluye cuando el valor `postgresql.enabled` es true.

</details>

### 6. ¿Cuándo se ejecuta el Helm Hook `pre-upgrade`?

- A) Antes de eliminar el release
- B) Después de la solicitud de actualización, antes de que se actualicen los recursos
- C) Después de que se hayan creado todos los recursos
- D) Después de completar el rollback

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Después de la solicitud de actualización, antes de que se actualicen los recursos**

**Explicación:**
El Hook `pre-upgrade` se ejecuta después de recibir una solicitud de actualización, pero antes de que comiencen las actualizaciones reales de recursos. Se usa comúnmente para migraciones de bases de datos u operaciones de respaldo.

</details>

### 7. ¿Cuál es el uso principal del comando `helm template`?

- A) Desplegar un chart en el cluster
- B) Renderizar templates del chart localmente para verificación
- C) Actualizar dependencias del chart
- D) Hacer rollback de un release

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Renderizar templates del chart localmente para verificación**

**Explicación:**
`helm template` renderiza templates del chart localmente, lo que permite previsualizar los manifiestos de Kubernetes que se generarán. Esto permite verificar templates sin conectarse a un cluster.

</details>

### 8. ¿Cuál es el propósito del archivo `_helpers.tpl` en Helm?

- A) Almacenar metadatos del chart
- B) Definir funciones auxiliares reutilizables de templates
- C) Almacenar valores predeterminados
- D) Mostrar mensajes posteriores a la instalación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Definir funciones auxiliares reutilizables de templates**

**Explicación:**
El archivo `_helpers.tpl` define funciones auxiliares (templates con nombre) que se usan comúnmente en múltiples templates. Encapsula lógica repetitiva como nombres de charts, labels y selectors.

</details>

### 9. ¿Qué muestra el comando `helm get values my-release --all`?

- A) Solo valores especificados por el usuario
- B) Todos los valores, incluidos los predeterminados
- C) El manifiesto del release
- D) El historial del release

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Todos los valores, incluidos los predeterminados**

**Explicación:**
Usar el flag `--all` muestra todos los valores calculados, incluidos tanto los valores sobrescritos por el usuario como los valores predeterminados del chart desde values.yaml.

</details>

### 10. ¿Por qué las funciones `toYaml` y `nindent` se usan comúnmente juntas en charts de Helm?

- A) Para convertir YAML a JSON
- B) Para insertar valores complejos en YAML con la indentación adecuada
- C) Para codificar valores en Base64
- D) Para envolver strings entre comillas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para insertar valores complejos en YAML con la indentación adecuada**

**Explicación:**
`toYaml` convierte objetos de Go en strings YAML, y `nindent` aplica el número especificado de espacios para la indentación. Esta combinación es esencial para insertar correctamente estructuras complejas como resources y annotations en templates.

</details>

## Preguntas de respuesta corta

### 1. ¿Qué tipo de recurso de Kubernetes se usa para almacenar información de release en Helm v3?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Secret**

**Explicación:**
Helm v3 almacena la información de release como Secrets dentro del namespace donde se despliega el release. El formato del nombre del Secret es `sh.helm.release.v1.<release-name>.v<version>`.

</details>

### 2. ¿Cuál es el nombre del archivo de bloqueo generado por el comando `helm dependency update`?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Chart.lock**

**Explicación:**
`helm dependency update` analiza las dependencias en Chart.yaml y genera un archivo Chart.lock que contiene versiones exactas. Este archivo garantiza builds reproducibles.

</details>

### 3. ¿Qué función proporciona un valor predeterminado cuando un valor está vacío en templates de Helm?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: default**

**Explicación:**
La función `default` proporciona un valor predeterminado cuando un valor está vacío o no está definido. Ejemplo de uso: <code v-pre>{{ .Values.image.tag | default .Chart.AppVersion }}</code>

</details>

### 4. ¿Qué annotation controla el orden de ejecución de Helm Hooks?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: helm.sh/hook-weight**

**Explicación:**
La annotation `helm.sh/hook-weight` determina el orden de ejecución dentro del mismo tipo de Hook. Los números más bajos se ejecutan primero, y se permiten valores negativos.

</details>

### 5. ¿Cuándo se muestra a los usuarios el archivo NOTES.txt en un chart de Helm?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Después de que helm install o helm upgrade se completen correctamente**

**Explicación:**
NOTES.txt se muestra a los usuarios después de una instalación o actualización correcta. Normalmente incluye instrucciones de acceso a la aplicación y guía de configuración inicial.

</details>

## Preguntas prácticas

### 1. Escribe un comando de Helm que cumpla con los siguientes requisitos:

- Instalar el chart bitnami/nginx como release "web-server"
- Desplegar en el namespace "frontend" (crearlo si no existe)
- Establecer replicaCount en 3

<details>
<summary>Mostrar respuesta</summary>

```bash
helm install web-server bitnami/nginx \
  -n frontend --create-namespace \
  --set replicaCount=3
```

**Explicación:**
- `helm install web-server bitnami/nginx`: Instalar el chart nginx como release "web-server"
- `-n frontend`: Especificar el namespace frontend
- `--create-namespace`: Crear el namespace si no existe
- `--set`: Sobrescribir values en línea

</details>

### 2. Predice la salida del siguiente fragmento de template de Helm:

```yaml
# values.yaml
env:
  LOG_LEVEL: debug
  MAX_CONNECTIONS: "100"

# template
env:
{{- range $key, $value := .Values.env }}
  - name: {{ $key }}
    value: {{ $value | quote }}
{{- end }}
```

<details>
<summary>Mostrar respuesta</summary>

```yaml
env:
  - name: LOG_LEVEL
    value: "debug"
  - name: MAX_CONNECTIONS
    value: "100"
```

**Explicación:**
- La función `range` itera sobre el mapa `.Values.env`
- `$key` es la clave del mapa, `$value` es el valor del mapa
- La función `quote` envuelve los valores entre comillas
- Los mapas se ordenan alfabéticamente

</details>

### 3. Escribe un template `_helpers.tpl` que cumpla con los siguientes requisitos:

- Nombre: mychart.labels
- app.kubernetes.io/name: nombre del chart
- app.kubernetes.io/instance: nombre del release
- app.kubernetes.io/version: versión de la aplicación

<details>
<summary>Mostrar respuesta</summary>

```yaml
{{- define "mychart.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
```

**Explicación:**
- `define` crea un template con nombre reutilizable
- `.Chart.Name` hace referencia al nombre del chart
- `.Release.Name` hace referencia al nombre del release
- `.Chart.AppVersion` hace referencia a la versión de la aplicación (quote garantiza el tipo string)

</details>

## Preguntas avanzadas

### 1. Explica cómo implementar deployments Blue-Green y Canary usando charts de Helm.

<details>
<summary>Mostrar respuesta</summary>

**Deployment Blue-Green:**
```yaml
# values.yaml
deployment:
  activeColor: blue

blue:
  enabled: true
  image:
    tag: "v1.0.0"

green:
  enabled: true
  image:
    tag: "v2.0.0"

service:
  selector:
    color: "{{ .Values.deployment.activeColor }}"
```

**Estrategia de implementación:**
1. Crear dos templates de Deployment para Blue y Green
2. Cambiar el selector del Service usando el valor activeColor
3. Establecer green.image.tag en la nueva versión durante el deployment
4. Después de la verificación, cambiar deployment.activeColor a green
5. Hacer rollback inmediatamente a blue si surgen problemas

**Canary Deployment (con Istio):**
```yaml
# VirtualService for traffic distribution
http:
  - route:
      - destination:
          host: myapp
          subset: stable
        weight: 90
      - destination:
          host: myapp
          subset: canary
        weight: 10
```

**Estrategia de implementación:**
1. Crear dos Deployments para Stable y Canary
2. Controlar la proporción de tráfico usando Istio VirtualService
3. Aumentar gradualmente la proporción de Canary (10% -> 25% -> 50% -> 100%)
4. Implementar rollback automático basado en monitoreo de métricas

</details>

### 2. Explica las mejores prácticas de seguridad para charts de Helm y diseña una estrategia de gestión de secretos.

<details>
<summary>Mostrar respuesta</summary>

**Mejores prácticas de seguridad:**

1. **Validación de valores (values.schema.json)**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["image"],
  "properties": {
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "repository": {
          "type": "string",
          "pattern": "^[a-z0-9.-/]+$"
        }
      }
    }
  }
}
```

2. **Principio de privilegio mínimo de RBAC**
```yaml
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]  # Grant only necessary permissions
```

3. **Aplicar Pod Security Standards**
```yaml
securityContext:
  runAsNonRoot: true
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
```

**Estrategia de gestión de secretos:**

1. **Integración con External Secrets Manager (AWS Secrets Manager)**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: {{ include "mychart.fullname" . }}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: {{ include "mychart.fullname" . }}-secrets
  data:
    - secretKey: database-password
      remoteRef:
        key: myapp/database
        property: password
```

2. **Uso de Sealed Secrets**
```bash
# Encrypt secret
kubeseal --format=yaml < secret.yaml > sealed-secret.yaml
```

3. **Plugin Helm Secrets**
```bash
# Use encrypted values file
helm secrets install myapp ./mychart -f secrets.yaml
```

</details>
