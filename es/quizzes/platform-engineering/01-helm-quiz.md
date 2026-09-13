# Cuestionario sobre el gestor de paquetes Helm

> **Guía relacionada**: [Helm](../../platform-engineering/01-helm.md)

Estos 20 temas de preguntas siguen la revisión de Helm 3.21.3 / 4.3.0.

## Opción múltiple

### 1. ¿Qué cambió al eliminar Tiller?

- A) Solo cambia el tamaño del chart.
- B) El cliente utiliza sus credenciales de Kubernetes y RBAC.
- C) Todos los charts se vuelven seguros.
- D) La API de Kubernetes ya no es necesaria.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Helm 3 eliminó Tiller y simplificó la ruta de permisos. Los manifests no seguros y los permisos amplios del cliente aún requieren revisión.

</details>

### 2. ¿Para qué sirve values.yaml?

- A) Metadatos del chart
- B) Datos de configuración predeterminados consumidos por los templates
- C) Historial de releases
- D) Un template ejecutado automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Solo los values consumidos por los templates tienen efecto. Los archivos y las variantes de --set pueden sobrescribirlos; las cadenas de template incorporadas no se evalúan automáticamente.

</details>

### 3. ¿Qué hace helm upgrade --install?

- A) Siempre crea un release nuevo
- B) Siempre elimina y vuelve a crear
- C) Instala un release ausente o actualiza uno existente
- D) Garantiza la idempotencia de las operaciones externas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Selecciona la instalación o la actualización. Los hooks, los values aleatorios y los cambios en bases de datos externas no tienen por qué ser idempotentes.

</details>

### 4. ¿Qué es Release.Name?

- A) Nombre del chart
- B) Nombre del clúster
- C) El nombre de release elegido
- D) Tag de imagen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

En `helm install demo ./chart`, el nombre es demo. Es diferente del nombre del chart, appVersion y la revisión del release.

</details>

### 5. ¿Qué especifica una condición de dependencia?

- A) Tag de imagen
- B) Una ruta de values que controla si la dependencia está habilitada
- C) Contraseña del registry
- D) Prioridad de Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Para el alias cache, use una ruta Booleana real como cache.enabled. Pruebe el comportamiento de las rutas ausentes y distíngalo de los values pasados al subchart.

</details>

### 6. ¿Cuándo se ejecuta un hook pre-upgrade?

- A) Después de la eliminación
- B) Después del renderizado y antes de actualizar los recursos ordinarios
- C) Siempre después de que los Pods nuevos estén Ready
- D) Solo después del rollback

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Una migración de base de datos debe tener en cuenta la disponibilidad de la base de datos, los reintentos, los fallos y la compatibilidad con la app anterior. El rollback no deshace automáticamente los cambios en la base de datos.

</details>

### 7. ¿Cuál es el propósito de helm template ordinario?

- A) Instalar en un clúster
- B) Renderizar manifests localmente
- C) Validar webhooks reales
- D) Realizar rollback automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El renderizado local predeterminado no prueba la admisión, RBAC, la ejecución de imágenes ni la conectividad. Distíngalo de las opciones que contactan con un servidor.

</details>

### 8. ¿Para qué sirve _helpers.tpl?

- A) Almacenar metadatos
- B) Definir templates nombrados reutilizables
- C) Almacenar values predeterminados
- D) Almacenar el historial de releases

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Use define para los templates nombrados e include para consumirlos. Añada prefijos a los nombres para evitar colisiones y pase el contexto previsto.

</details>

### 9. ¿Qué genera helm get values demo --all?

- A) Solo las anulaciones del usuario
- B) Values calculados, incluidos los valores predeterminados del chart
- C) Solo manifests
- D) Solo historial

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Seleccione el namespace y el release correctos. Los values pueden contener información confidencial, por lo que debe proteger la salida.

</details>

### 10. ¿Por qué combinar toYaml con nindent?

- A) Cifrado automático
- B) Serializar values estructurados a YAML y añadir una nueva línea/sangría
- C) Generar solo JSON
- D) Convertir siempre los números en cadenas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

A diferencia de indent, nindent también antepone una nueva línea. Haga coincidir la sangría requerida en el punto de inserción.

</details>

## Respuesta corta

### 1. ¿Cuál es el recurso de almacenamiento predeterminado de los releases?

<details>
<summary>Mostrar respuesta</summary>

Un Secret en el namespace del release, llamado `sh.helm.release.v1.<release>.v<revision>`. Se pueden configurar otros backends, como ConfigMap o SQL. Base64 no es cifrado.

</details>

### 2. ¿Qué archivo de bloqueo crea dependency update y cuáles son sus límites?

<details>
<summary>Mostrar respuesta</summary>

Chart.lock. dependency build utiliza sus versiones bloqueadas, pero el bloqueo por sí solo no garantiza la integridad de los artefactos, imágenes fijadas ni reproducibilidad completa.

</details>

### 3. ¿Qué values vacíos importan al usar default?

<details>
<summary>Mostrar respuesta</summary>

False, cero, las cadenas vacías y las colecciones cuentan como vacíos. Compruebe la presencia y el tipo cuando sea necesario conservar false/cero explícitos. default no protege todas las búsquedas anidadas.

</details>

### 4. ¿Qué annotation controla el orden de los hooks?

<details>
<summary>Mostrar respuesta</summary>

`helm.sh/hook-weight`. Los pesos inferiores se ejecutan primero dentro de la fase, incluidos los pesos negativos. Considere también el orden de desempate por kind/name, la finalización de Job y los timeouts.

</details>

### 5. ¿Cuándo y por qué se utiliza NOTES.txt?

<details>
<summary>Mostrar respuesta</summary>

Genera instrucciones mostradas después de una instalación/actualización correcta y disponibles mediante `helm get notes`. Mantenga las instrucciones precisas y evite los secretos. Las notas no demuestran la preparación de la aplicación.

</details>

## Práctico

### 1. Instale el ejemplo como web-server en frontend con tres réplicas.

<details>
<summary>Mostrar respuesta</summary>

```bash
helm install web-server examples/platform/helm/reviewed-app \
  --namespace frontend --create-namespace \
  --set replicaCount=3
```

Ejecute desde la raíz del repositorio con un contexto de clúster y permisos aprobados. Esta auditoría ejecutó lint/template/package, no la instalación.

</details>

### 2. ¿Cómo deberían renderizarse LOG_LEVEL=debug y MAX_CONNECTIONS="100" como env?

<details>
<summary>Mostrar respuesta</summary>

```yaml
env:
  - name: LOG_LEVEL
    value: "debug"
  - name: MAX_CONNECTIONS
    value: "100"
```

Itere sobre el map y entrecomille cada valor para que ambos sigan siendo cadenas. Los templates de Go recorren los maps con claves ordenadas básicas en orden de clave; esto es distinto del orden de las listas.

</details>

### 3. Escriba un helper para las etiquetas de chart, release y appVersion.

<details>
<summary>Mostrar respuesta</summary>

```text
{{- define "mychart.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
```

Pase el contexto raíz previsto y aplique sangría en el sitio de llamada. appVersion es metadato y no selecciona automáticamente un tag de imagen.

</details>

## Avanzado

### 1. ¿Qué se necesita para la entrega Blue/Green y canary con Helm?

<details>
<summary>Mostrar respuesta</summary>

Blue/Green requiere dos Deployments con etiquetas y un template de Service real que seleccione el color activo después de la validación. Las cadenas de template dentro de values.yaml no se evalúan automáticamente. Canary requiere rutas/subconjuntos reales o un controlador de rollout, pesos, métricas de observación y condiciones de cancelación. Los values por sí solos no crean análisis ni rollback automatizados. Tenga en cuenta la compatibilidad de la base de datos y las solicitudes en curso.

</details>

### 2. Diseñe la seguridad del chart y la gestión de secretos.

<details>
<summary>Mostrar respuesta</summary>

Valide los values y tipos requeridos con un values.schema.json compatible, y fije las revisiones de chart/imagen revisadas. Conecte los ServiceAccounts y RoleBindings requeridos con permisos mínimos de API. Un volumen Secret no justifica conceder a la app acceso a todos los Secrets. Mantenga los valores secretos fuera de los valores predeterminados, los argumentos de CLI y los logs de depuración; planifique los montajes de archivos aprobados, la rotación y la relectura. ESO v1, Sealed Secrets y helm-secrets requieren sus controladores/plugins y permisos de proveedor/clave. Compruebe si los valores descifrados entran en los registros de releases. Combine un UID no root, capacidades eliminadas, una raíz de solo lectura y los volúmenes de escritura requeridos, y luego verifique la compatibilidad real de la imagen.

</details>
