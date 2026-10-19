# Cuestionario sobre extensiones de Kubernetes

Este cuestionario evalúa tus conocimientos conceptuales y prácticos sobre los mecanismos de extensión de Kubernetes. Abarca temas como las definiciones de recursos personalizados (CRD), los controladores personalizados, las extensiones de API, los webhooks y el patrón Operator.

## Preguntas de opción múltiple

1. ¿Cuál es la forma más común de definir recursos personalizados en Kubernetes?
   - A) Definir el esquema del recurso mediante ConfigMap
   - B) Crear una definición de recurso personalizado (CRD)
   - C) Modificar directamente el código del servidor de API
   - D) Usar la capa de agregación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear una definición de recurso personalizado (CRD)**

**Explicación:**
La forma más común de definir recursos personalizados en Kubernetes es crear una definición de recurso personalizado (CRD). Una CRD es un mecanismo que permite extender la API de Kubernetes mediante la definición de nuevos tipos de recursos.

El uso de CRD ofrece las siguientes ventajas:
- Puedes agregar nuevos tipos de recursos sin modificar el servidor de API de Kubernetes existente.
- Puedes administrar recursos personalizados con herramientas estándar de Kubernetes como `kubectl`.
- Puedes aprovechar funciones como la validación de recursos, el versionado y los subrecursos de estado.

Ejemplo de CRD:
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                cronSpec:
                  type: string
                image:
                  type: string
                replicas:
                  type: integer
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
    shortNames:
    - ct
```

Problemas con las otras opciones:
- Los ConfigMap se usan para almacenar datos de configuración y no son adecuados para extender la API.
- Modificar directamente el código del servidor de API es complejo, difícil de mantener y puede causar problemas durante las actualizaciones.
- La capa de agregación es otra forma de definir recursos personalizados, pero es más compleja que las CRD porque requiere implementar un servidor de API independiente.
</details>

2. ¿Cuál es el propósito principal de un Kubernetes Operator?
   - A) Optimizar el uso de recursos de los nodos del clúster
   - B) Codificar en software automatizado los conocimientos operativos de aplicaciones complejas
   - C) Mejorar el rendimiento del servidor de API de Kubernetes
   - D) Ampliar las funciones de red del clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Codificar en software automatizado los conocimientos operativos de aplicaciones complejas**

**Explicación:**
El propósito principal de un Kubernetes Operator es codificar en software automatizado los conocimientos operativos de aplicaciones complejas. El patrón Operator es una implementación de software de la manera en que una persona encargada de las operaciones administra aplicaciones complejas.

Características principales de los Operator:
- Combinan recursos personalizados con controladores personalizados para implementar lógica específica de la aplicación.
- Automatizan tareas operativas como el despliegue, las actualizaciones, las copias de seguridad, la recuperación y el escalado de aplicaciones.
- Supervisan continuamente el estado de la aplicación y lo ajustan al estado deseado.
- Codifican conocimientos del dominio para permitir la administración declarativa de aplicaciones complejas.

Casos de uso comunes de los Operator:
- Administración automatizada de bases de datos (p. ej., PostgreSQL, MySQL, MongoDB)
- Despliegue y configuración de sistemas de mensajería (p. ej., Kafka, RabbitMQ)
- Instalación y mantenimiento de sistemas de supervisión (p. ej., Prometheus)
- Administración de mallas de servicios (p. ej., Istio)

Ejemplo de Operator: Prometheus Operator
```yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
spec:
  serviceAccountName: prometheus
  replicas: 2
  serviceMonitorSelector:
    matchLabels:
      team: frontend
  resources:
    requests:
      memory: 400Mi
```

Con esta sencilla configuración declarativa, Prometheus Operator se encarga automáticamente de tareas complejas como:
- Desplegar servidores Prometheus
- Crear y administrar archivos de configuración
- Detectar automáticamente los destinos de supervisión de servicios
- Configurar alta disponibilidad
- Administrar el almacenamiento cuando se configura un storage/volumeClaimTemplate
- Coordinar las actualizaciones

Las otras opciones no son el propósito principal de los Operator:
- La optimización del uso de recursos corresponde a HPA (Horizontal Pod Autoscaler), VPA (Vertical Pod Autoscaler), etc.
- Mejorar el rendimiento del servidor de API no es el propósito principal de los Operator.
- Ampliar las funciones de red corresponde a los complementos CNI o a las mallas de servicios.
</details>

3. ¿Cuál es la función principal de los webhooks de admisión en Kubernetes?
   - A) Gestionar la autenticación del servidor de API
   - B) Interceptar las solicitudes de creación o modificación de recursos para validarlas o modificarlas
   - C) Supervisar eventos del clúster y enviar alertas
   - D) Proporcionar API para integrarse con sistemas externos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Interceptar las solicitudes de creación o modificación de recursos para validarlas o modificarlas**

**Explicación:**
La función principal de los webhooks de admisión en Kubernetes es interceptar las solicitudes de creación o modificación de recursos para validarlas o modificarlas. Los webhooks de admisión proporcionan un mecanismo para interceptar solicitudes antes de que el servidor de API de Kubernetes las almacene en el almacenamiento persistente (etcd).

Hay dos tipos de webhooks de admisión:

1. **Webhook de validación**:
   - Valida las solicitudes de creación, actualización y eliminación de recursos.
   - Puede permitir o denegar solicitudes, pero no puede modificarlas.
   - Se usa para aplicar políticas, realizar comprobaciones de seguridad, validar configuraciones, etc.

2. **Webhook de mutación**:
   - Puede validar y modificar las solicitudes de creación y actualización de recursos.
   - Se usa para establecer valores predeterminados, inyectar contenedores sidecar, agregar etiquetas, etc.
   - Se ejecuta antes que los webhooks de validación.

Ejemplo de configuración de un webhook de admisión:
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: pod-policy-validator
webhooks:
- name: pod-policy.example.com
  clientConfig:
    service:
      namespace: webhook-namespace
      name: webhook-service
      path: "/validate-pods"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE", "UPDATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

Casos de uso comunes de los webhooks de admisión:
- Aplicar políticas de seguridad (p. ej., prohibir contenedores con privilegios)
- Aplicar solicitudes y límites de recursos
- Inyectar automáticamente contenedores sidecar (p. ej., Istio)
- Agregar automáticamente etiquetas y anotaciones
- Restringir los registros de imágenes permitidos
- Aplicar políticas basadas en espacios de nombres

Problemas con las otras opciones:
- La gestión de la autenticación del servidor de API corresponde a los complementos de autenticación.
- La supervisión de eventos del clúster y el envío de alertas corresponden a los detectores de eventos o a las herramientas de supervisión.
- Proporcionar API para integrarse con sistemas externos es un propósito general de las extensiones de API, pero no la función principal de los webhooks de admisión.
</details>

4. ¿Cuál es el propósito principal de la capa de agregación en el servidor de API de Kubernetes?
   - A) Optimizar el rendimiento del servidor de API
   - B) Consolidar varios servidores de API en un único servidor de API
   - C) Integrar servidores de API personalizados en el servidor de API principal para ampliar la API
   - D) Proporcionar detección de servicios dentro del clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Integrar servidores de API personalizados en el servidor de API principal para ampliar la API**

**Explicación:**
El propósito principal de la capa de agregación en el servidor de API de Kubernetes es integrar servidores de API personalizados en el servidor de API principal para ampliar la API. Esto proporciona otra forma de extender la API de Kubernetes y ofrece funciones más potentes que las CRD, aunque es más compleja.

Características principales de la capa de agregación:
- Integra servidores de API personalizados en el espacio de URL del servidor de API de Kubernetes.
- Los servidores de API personalizados pueden tener su propio almacenamiento, lógica de negocio, versiones de API, etc.
- El servidor de API principal envía las solicitudes mediante proxy al servidor de API personalizado correspondiente.
- El servidor de API principal autentica al usuario; la extensión debe verificar el proxy autenticador y realizar la autorización delegada (SubjectAccessReview).

Casos en los que se usa la capa de agregación:
- Cuando se necesita una lógica de validación compleja
- Cuando se requiere un backend de almacenamiento personalizado
- Cuando se necesita un comportamiento distinto al de las API existentes
- Cuando se requiere transformar recursos o calcular estados especiales

Ejemplo de recurso APIService:
```yaml
apiVersion: apiregistration.k8s.io/v1
kind: APIService
metadata:
  name: v1beta1.metrics.k8s.io
spec:
  service:
    name: metrics-server
    namespace: kube-system
  group: metrics.k8s.io
  version: v1beta1
  caBundle: <base64-encoded-serving-ca>
  groupPriorityMinimum: 100
  versionPriority: 100
```

Esta configuración dirige las solicitudes del grupo de API `metrics.k8s.io/v1beta1` al servicio `metrics-server` en el espacio de nombres `kube-system`.

Ejemplos reales que usan la capa de agregación:
- metrics-server: proporciona métricas de uso de recursos de nodos y Pod
- service-catalog (archivado): integración histórica con intermediarios de servicios
- custom-metrics-apiserver: proporciona métricas personalizadas para HPA

Problemas con las otras opciones:
- La capa de agregación no sirve para optimizar el rendimiento del servidor de API.
- Consolidar varios servidores de API en uno no es una descripción precisa. La capa de agregación integra varios servidores de API en un único espacio de URL, pero los servidores se ejecutan por separado.
- La capa de agregación no proporciona detección de servicios. Esa es la función de los Service de Kubernetes.
</details>

5. ¿Cuál es la función principal de un controlador personalizado en Kubernetes?
   - A) Supervisar el uso de recursos de los nodos del clúster
   - B) Observar el estado de los recursos personalizados y reconciliarlo con el estado deseado
   - C) Gestionar la autenticación y autorización de las solicitudes al servidor de API
   - D) Administrar la red del clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Observar el estado de los recursos personalizados y reconciliarlo con el estado deseado**

**Explicación:**
La función principal de un controlador personalizado en Kubernetes es observar el estado de los recursos personalizados y reconciliarlo con el estado deseado. Los controladores implementan el «bucle de reconciliación», un patrón operativo fundamental de Kubernetes, para ajustar continuamente el estado real del sistema al estado deseado.

Características principales de los controladores personalizados:
- Observan tipos de recursos específicos (normalmente, recursos personalizados definidos mediante CRD).
- Responden a eventos de cambio de recursos y ejecutan lógica de negocio.
- Realizan tareas para ajustar el estado real de los recursos al estado deseado.
- Actualizan el campo de estado de los recursos para reflejar su estado actual.

Componentes comunes de los controladores personalizados:
1. **Informer**: observa el servidor de API de Kubernetes y recibe eventos de cambio de recursos.
2. **Cola de trabajo**: almacena y administra los eventos que se deben procesar.
3. **Reconciliador**: compara el estado deseado con el estado real de los recursos y realiza las tareas necesarias.
4. **Cliente**: interactúa con la API de Kubernetes para crear, actualizar y eliminar recursos.

Ejemplo de controlador personalizado: función de reconciliación sencilla
```go
func (c *Controller) reconcile(key string) error {
    // Split key into namespace and name
    namespace, name, err := cache.SplitMetaNamespaceKey(key)
    if err != nil {
        return err
    }

    // Get custom resource
    instance, err := c.customResourceLister.CustomResources(namespace).Get(name)
    if errors.IsNotFound(err) {
        // Already deleted. External cleanup must run earlier using a finalizer.
        return nil
    }
    if err != nil {
        return err
    }

    // Check resource state and perform necessary tasks
    // e.g., create sub-resources, integrate with external systems, update status, etc.

    // Update status
    instanceCopy := instance.DeepCopy()
    instanceCopy.Status.Phase = "Reconciled"
    _, err = c.customResourceClient.CustomResources(namespace).UpdateStatus(context.TODO(), instanceCopy, metav1.UpdateOptions{})
    return err
}
```

Casos de uso comunes de los controladores personalizados:
- Automatizar el despliegue y la administración de aplicaciones complejas
- Integrarse con sistemas externos (p. ej., aprovisionamiento de recursos en la nube)
- Automatizar procesos de copia de seguridad y recuperación
- Implementar estrategias avanzadas de despliegue (p. ej., despliegues canary y blue-green)

Problemas con las otras opciones:
- La supervisión del uso de recursos de los nodos del clúster corresponde a metrics-server o a herramientas de supervisión como Prometheus.
- La gestión de la autenticación y autorización de las solicitudes al servidor de API corresponde a los complementos de autenticación y autorización.
- La administración de la red del clúster corresponde a los complementos CNI o a los controladores de red.
</details>

6. ¿Qué formato se usa para definir los esquemas de validación de CRD (CustomResourceDefinitions) en Kubernetes?
   - A) JSON Schema
   - B) XML Schema
   - C) OpenAPI v3 Schema
   - D) GraphQL Schema

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) OpenAPI v3 Schema**

**Explicación:**
El formato que se usa para definir los esquemas de validación de CRD (CustomResourceDefinitions) en Kubernetes es OpenAPI v3 Schema. Este esquema define la estructura y los tipos de campos de los recursos personalizados, y el servidor de API lo usa para validar las solicitudes de creación y actualización de recursos.

Ejemplo de esquema de validación de CRD:
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: ["spec"]
          properties:
            spec:
              type: object
              required: ["cronSpec", "image"]
              properties:
                cronSpec:
                  type: string
                  pattern: '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
                image:
                  type: string
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
    shortNames:
    - ct
```

En este ejemplo, el campo `openAPIV3Schema` define las siguientes reglas de validación:
- El campo `spec` es obligatorio.
- Dentro de `spec`, los campos `cronSpec` e `image` son obligatorios.
- `cronSpec` es una cadena y debe seguir el patrón de expresión cron.
- `image` es una cadena.
- `replicas` es un entero y debe estar entre 1 y 10.

OpenAPI v3 Schema ofrece diversas funciones de validación:
- Especificar campos obligatorios
- Validar tipos de datos (cadena, número, booleano, objeto, matriz, etc.)
- Validar patrones de cadenas (expresiones regulares)
- Validar rangos numéricos (mínimo, máximo)
- Validar la longitud de matrices
- Validar valores de enumeración
- Definir estructuras de objetos anidados

Problemas con las otras opciones:
- JSON Schema es la base de OpenAPI, pero Kubernetes usa específicamente OpenAPI v3 Schema.
- XML Schema no se usa en la API de Kubernetes.
- GraphQL Schema se usa para las API GraphQL, pero no para la API de Kubernetes.
</details>

7. ¿Cuál es la principal ventaja de habilitar el subrecurso de estado para recursos personalizados en Kubernetes?
   - A) Creación de recursos más rápida
   - B) Separación de las actualizaciones de spec y status, y control RBAC
   - C) Funciones automáticas de copia de seguridad y recuperación
   - D) Administración simplificada de versiones de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Separación de las actualizaciones de spec y status, y control RBAC**

**Explicación:**
La principal ventaja de habilitar el subrecurso de estado para recursos personalizados en Kubernetes es separar las actualizaciones de spec y status, así como poder controlar el acceso mediante RBAC (control de acceso basado en roles).

Ventajas de habilitar el subrecurso de estado:

1. **Separación de responsabilidades**:
   - El campo `spec` define el estado deseado especificado por los usuarios.
   - El campo `status` informa del estado real observado por los controladores.
   - Esta separación aclara las responsabilidades de los usuarios y los controladores.

2. **Control RBAC**:
   - Los permisos para actualizar el estado se pueden conceder solo a los controladores, mientras que los usuarios habituales reciben permisos de solo lectura.
   - Esto impide la modificación no autorizada de la información de estado.

3. **Prevención de conflictos**:
   - Spec y status están separados, pero ambos comparten resourceVersion, por lo que las escrituras simultáneas aún pueden devolver 409 Conflict.
   - Lee el objeto más reciente y vuelve a intentarlo o reconcilia ante conflictos.

4. **Compatibilidad con el subrecurso scale**:
   - El subrecurso scale se configura de forma independiente, con specReplicasPath, statusReplicasPath y un labelSelectorPath opcional.
   - Esto permite usar herramientas estándar de escalado de Kubernetes como HPA (Horizontal Pod Autoscaler).

Ejemplo de habilitación del subrecurso de estado en una CRD:
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
  - name: v1
    served: true
    storage: true
    subresources:
      status: {}
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              cronSpec:
                type: string
              image:
                type: string
          status:
            type: object
            properties:
              phase:
                type: string
              message:
                type: string
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
```

Ejemplo de actualización del estado desde un controlador:
```go
// Update status only
statusUpdate := instance.DeepCopy() // Preserve resourceVersion from a current read.
statusUpdate.Status.Phase = "Running"
statusUpdate.Status.Message = "Resource is running"

_, err = c.clientset.MyGroup().MyResources(namespace).UpdateStatus(ctx, statusUpdate, metav1.UpdateOptions{})
```

Problemas con las otras opciones:
- El subrecurso de estado no aumenta la velocidad de creación de recursos.
- No proporciona funciones automáticas de copia de seguridad y recuperación.
- La administración de versiones de recursos se realiza mediante el campo `versions` de la CRD y no está directamente relacionada con el subrecurso de estado.
</details>

8. ¿Cuál es el propósito principal de la conversión mediante webhook en Kubernetes?
   - A) Enrutar solicitudes de API a servicios externos
   - B) Gestionar la conversión entre distintas versiones de recursos personalizados
   - C) Convertir tokens de autenticación a distintos formatos
   - D) Convertir datos de registro a formatos estructurados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Gestionar la conversión entre distintas versiones de recursos personalizados**

**Explicación:**
El propósito principal de la conversión mediante webhook en Kubernetes es gestionar la conversión entre distintas versiones de recursos personalizados. Esta función admite varias versiones de CRD y permite migrar de una versión a otra sin inconvenientes.

Características principales de la conversión mediante webhook:

1. **Compatibilidad con varias versiones**:
   - Las CRD pueden admitir simultáneamente varias versiones de API (p. ej., v1alpha1, v1beta1, v1).
   - Cada versión puede tener distintos esquemas y campos.

2. **Conversión automática**:
   - El servidor de API gestiona automáticamente la conversión entre la versión solicitada por el cliente y la versión de almacenamiento.
   - El webhook de conversión proporciona lógica de conversión personalizada durante este proceso.

3. **Independencia de la versión de almacenamiento**:
   - Aunque cambie la versión de almacenamiento, los clientes que usan versiones anteriores pueden seguir funcionando.
   - El webhook gestiona la conversión bidireccional entre las versiones disponibles; cambiar storage:true no reescribe los datos existentes. Migra los objetos almacenados antes de eliminar las entradas antiguas de status.storedVersions.

Ejemplo de configuración de un webhook de conversión en una CRD:
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        required:
        - spec
        properties:
          spec:
            type: object
            required:
            - cronSpec
            - image
            properties:
              cronSpec:
                type: string
              image:
                type: string
              replicas:
                type: integer
          status:
            type: object
            properties:
              phase:
                type: string
  - name: v1beta1
    served: true
    storage: false
    schema:
      openAPIV3Schema:
        type: object
        required:
        - spec
        properties:
          spec:
            type: object
            required:
            - cron
            - image
            properties:
              cron:
                type: string
              image:
                type: string
              replicas:
                type: integer
          status:
            type: object
            properties:
              phase:
                type: string
  conversion:
    strategy: Webhook
    webhook:
      clientConfig:
        service:
          namespace: webhook-system
          name: crd-conversion-webhook
          path: /convert
        caBundle: <base64-encoded-ca-cert>
      conversionReviewVersions:
      - v1
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
```

Ejemplo de implementación de un servidor de webhook de conversión:
```go
// Include encoding/json, net/http, fmt and the Kubernetes types below in the server.
// apiextensionsv1 "k8s.io/apiextensions-apiserver/pkg/apis/apiextensions/v1"
// metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
// "k8s.io/apimachinery/pkg/runtime"
func convertCron(raw []byte, desired string) ([]byte, error) {
    var obj map[string]interface{}
    if err := json.Unmarshal(raw, &obj); err != nil { return nil, err }
    source, _ := obj["apiVersion"].(string)
    valid := func(v string) bool { return v == "stable.example.com/v1" || v == "stable.example.com/v1beta1" }
    if !valid(source) || !valid(desired) || obj["kind"] != "CronTab" {
        return nil, fmt.Errorf("unsupported CronTab conversion %q -> %q", source, desired)
    }
    spec, ok := obj["spec"].(map[string]interface{})
    if !ok { return nil, fmt.Errorf("spec object required") }
    if source != desired {
        oldField, newField := "cron", "cronSpec"
        if desired == "stable.example.com/v1beta1" { oldField, newField = newField, oldField }
        value, ok := spec[oldField]
        if !ok { return nil, fmt.Errorf("missing %s", oldField) }
        if _, collision := spec[newField]; collision { return nil, fmt.Errorf("ambiguous cron fields") }
        spec[newField] = value
        delete(spec, oldField)
    }
    obj["apiVersion"] = desired
    // Preserve metadata (including UID/resourceVersion), status and all other fields.
    return json.Marshal(obj)
}

func serveConvert(w http.ResponseWriter, r *http.Request) {
    var review apiextensionsv1.ConversionReview
    if r.Method != http.MethodPost || r.Body == nil {
        http.Error(w, "POST body required", http.StatusBadRequest); return
    }
    if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 8<<20)).Decode(&review); err != nil ||
        review.APIVersion != "apiextensions.k8s.io/v1" || review.Kind != "ConversionReview" ||
        review.Request == nil || review.Request.UID == "" {
        http.Error(w, "Invalid ConversionReview v1", http.StatusBadRequest); return
    }
    response := &apiextensionsv1.ConversionResponse{
        UID: review.Request.UID, Result: metav1.Status{Status: "Success"},
    }
    for _, obj := range review.Request.Objects {
        raw, err := convertCron(obj.Raw, review.Request.DesiredAPIVersion)
        if err != nil {
            response.Result = metav1.Status{Status: "Failure", Message: err.Error()}
            response.ConvertedObjects = nil
            break
        }
        response.ConvertedObjects = append(response.ConvertedObjects, runtime.RawExtension{Raw: raw})
    }
    out := apiextensionsv1.ConversionReview{
        TypeMeta: metav1.TypeMeta{APIVersion: "apiextensions.k8s.io/v1", Kind: "ConversionReview"},
        Response: response,
    }
    w.Header().Set("Content-Type", "application/json")
    _ = json.NewEncoder(w).Encode(out)
}
```

Problemas con las otras opciones:
- El enrutamiento de solicitudes de API a servicios externos corresponde a la agregación de API.
- La conversión de tokens de autenticación corresponde a los complementos de autenticación.
- La conversión de datos de registro corresponde a los sistemas de registro.
</details>

9. ¿Cuál de las siguientes opciones NO es un framework que ayude a desarrollar Operator de Kubernetes?
   - A) Operator Framework
   - B) Kubebuilder
   - C) Metacontroller
   - D) Kubespray

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Kubespray**

**Explicación:**
Kubespray no es un framework que ayude a desarrollar Operator de Kubernetes. Kubespray es una herramienta para desplegar y administrar clústeres de Kubernetes mediante playbooks de Ansible. Se centra en la instalación y configuración del clúster y no está relacionada con el desarrollo de Operator.

Los frameworks reales para desarrollar Operator de Kubernetes son:

1. **Operator Framework**:
   - Kit de herramientas para desarrollar Operator, creado por Red Hat
   - Componentes principales:
     - Operator SDK: herramientas de desarrollo y generación de estructura inicial de Operator
     - Operator Lifecycle Manager (OLM): administración de la instalación y actualización de Operator
     - Operator Metering: generación de informes sobre el uso de Operator
   - Admite el desarrollo de Operator con Go, Ansible y Helm

2. **Kubebuilder**:
   - Framework desarrollado por un SIG (grupo de interés especial) de Kubernetes
   - SDK para desarrollar controladores en Go
   - Proporciona herramientas para generar código, administrar CRD y realizar pruebas
   - Se basa en la biblioteca controller-runtime

3. **Metacontroller**:
   - Framework ligero de Operator basado en webhooks
   - Permite implementar la lógica de los controladores en varios lenguajes
   - Definición declarativa de controladores
   - Adecuado para desarrollar rápidamente controladores sencillos

Comparación de funciones de cada framework:

| Framework | Lenguaje principal | Complejidad | Funciones |
|-----------|------------------|------------|----------|
| Operator Framework | Go, Ansible, Helm | Media-alta | Kit de herramientas integral, diversas opciones de desarrollo |
| Kubebuilder | Go | Media | Patrones estandarizados, herramientas de generación de código |
| Metacontroller | Independiente del lenguaje | Baja | Basado en webhooks, implementación sencilla |

Ejemplo de desarrollo de Operator (con Kubebuilder):
```bash
# Initialize project
kubebuilder init --domain example.com --repo github.com/example/my-operator

# Create API
kubebuilder create api --group apps --version v1alpha1 --kind MyApp

# Implement controller (edit controller.go file)

# Create CRD and deploy controller
make install
make deploy
```

Explicaciones de las otras opciones:
- Operator Framework es el kit integral de Red Hat para desarrollar Operator.
- Kubebuilder es un framework de desarrollo de controladores basado en Go, creado por un SIG de Kubernetes.
- Metacontroller es un framework ligero de Operator basado en webhooks.
</details>

10. ¿Cuál es la principal diferencia entre las definiciones de recursos personalizados (CRD) y las API agregadas en Kubernetes?
    - A) Las CRD no admiten el versionado, pero las API agregadas sí
    - B) Las CRD no admiten esquemas de validación, pero las API agregadas sí
    - C) Las CRD son sencillas de implementar, pero tienen flexibilidad limitada; las API agregadas son complejas de implementar, pero ofrecen más flexibilidad
    - D) Las CRD solo admiten recursos de ámbito de clúster, y las API agregadas solo admiten recursos de ámbito de espacio de nombres

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Las CRD son sencillas de implementar, pero tienen flexibilidad limitada; las API agregadas son complejas de implementar, pero ofrecen más flexibilidad**

**Explicación:**
La principal diferencia entre las definiciones de recursos personalizados (CRD) y las API agregadas en Kubernetes radica en el equilibrio entre la complejidad de implementación y la flexibilidad. Las CRD son sencillas de implementar, pero tienen flexibilidad limitada; las API agregadas son complejas de implementar, pero ofrecen más flexibilidad.

**Características de las CRD (CustomResourceDefinitions):**
- **Implementación sencilla**: puedes definir nuevos recursos de API con un solo archivo YAML.
- **Usan el servidor de API existente**: no es necesario implementar un servidor de API independiente.
- **Flexibilidad limitada**:
  - El almacenamiento se limita a etcd.
  - Heredan el comportamiento del servidor de API predeterminado.
  - Admiten la validación CEL y los webhooks de admisión y conversión; el almacenamiento personalizado y el comportamiento de API no estándar siguen siendo factores diferenciadores.
- **Extensión mediante webhooks**: algunas funciones se pueden ampliar mediante webhooks de validación, webhooks de conversión, etc.

**Características de las API agregadas:**
- **Implementación compleja**: hay que desarrollar y desplegar un servidor de API independiente.
- **Alta flexibilidad**:
  - Pueden usar backends de almacenamiento personalizados.
  - Pueden implementar lógica de negocio compleja.
  - Pueden implementar lógica personalizada de autenticación y autorización.
  - Pueden implementar lógica especial para calcular y convertir estados.
- **Funcionalidad completa de servidor de API**: pueden aprovechar todas las funciones de un servidor de API estándar de Kubernetes.

**Criterios de selección:**

| Criterio | Elegir CRD | Elegir API agregada |
|----------|------------|----------------------|
| Complejidad de implementación | Baja: definición YAML sencilla | Alta: requiere desarrollar un servidor de API independiente |
| Tiempo de desarrollo | Corto: se puede implementar en minutos | Largo: requiere desarrollar un servidor de API completo |
| Mantenimiento | Fácil: lo administra el servidor de API existente | Difícil: requiere mantener un servicio independiente |
| Opciones de almacenamiento | Solo etcd | Se pueden usar backends de almacenamiento personalizados |
| Lógica de negocio | Limitada: se implementa mediante controladores | Flexible: se puede implementar directamente en el servidor de API |
| Rendimiento | Por lo general, bueno | Se puede optimizar de forma personalizada |
| Casos de uso | Operaciones CRUD sencillas, patrones estándar | Comportamiento complejo de API, validación y conversión especiales |

**Ejemplos de situaciones:**

Casos adecuados para CRD:
- Administración sencilla de la configuración de aplicaciones
- Los requisitos principales son operaciones CRUD básicas
- Creación rápida de prototipos y desarrollo

Casos adecuados para API agregadas:
- Integración con bases de datos externas
- Transformación y validación de datos complejas
- Se necesitan mecanismos de autenticación especiales
- API de alto rendimiento o de propósito especial

Problemas con las otras opciones:
- Las CRD sí admiten el versionado (A es incorrecta).
- Las CRD sí admiten esquemas de validación mediante OpenAPI v3 Schema (B es incorrecta).
- Tanto las CRD como las API agregadas admiten recursos de ámbito de clúster y de ámbito de espacio de nombres (D es incorrecta).
</details>

> La expresión regular cronSpec solo comprueba una estructura restringida de cinco campos que usa números, asteriscos y pasos. No valida rangos, listas, nombres ni todos los valores de tiempo válidos. Agrega un analizador cron real en el controlador o webhook. Una CRD por sí sola no ejecuta tareas programadas.

## Preguntas de respuesta corta

1. Explica cómo definir recursos personalizados mediante una definición de recurso personalizado (CRD) y cómo establecer reglas de validación para esos recursos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Cómo definir una definición de recurso personalizado (CRD):**

Una CRD es un mecanismo que amplía la API de Kubernetes para definir nuevos tipos de recursos. Al crear una CRD, se crea un nuevo endpoint de API RESTful y puedes administrar ese recurso con herramientas estándar como `kubectl`.

**1. Estructura básica de una CRD:**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: <plural>.<group>
spec:
  group: <api-group>
  names:
    kind: <kind-name>
    plural: <plural-name>
    singular: <singular-name>
    shortNames:
    - <short-name>
  scope: Namespaced
  versions:
  - name: <version>
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        required:
        - spec
        properties:
          spec:
            type: object
            required:
            - cronSpec
            - image
            properties:
              cronSpec:
                type: string
              image:
                type: string
              replicas:
                type: integer
          status:
            type: object
            properties:
              phase:
                type: string
```

**2. Establecimiento de reglas de validación:**

Las reglas de validación de las CRD se establecen mediante el campo `openAPIV3Schema`. Este esquema sigue el formato OpenAPI v3 y define la estructura y los tipos de campos de los recursos.

**Ejemplo de reglas básicas de validación:**

```yaml
schema:
  openAPIV3Schema:
    type: object
    required: ["spec"]
    properties:
      spec:
        type: object
        required: ["cronSpec", "image"]
        properties:
          cronSpec:
            type: string
            pattern: '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
          image:
            type: string
          replicas:
            type: integer
            minimum: 1
            maximum: 10
            default: 1
```

**3. Funciones avanzadas de validación:**

OpenAPI v3 Schema ofrece diversas funciones de validación:

- **Campos obligatorios**: agrega los nombres de los campos a la matriz `required`.
  ```yaml
  required: ["fieldName1", "fieldName2"]
  ```

- **Tipos de datos**: especifica los tipos de datos mediante el campo `type`.
  ```yaml
  type: string  # Choose one supported type, not a pipe-separated union.
  ```

- **Restricciones de cadenas**: valida la longitud y los patrones de las cadenas.
  ```yaml
  minLength: 3
  maxLength: 64
  pattern: '^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
  ```

- **Restricciones numéricas**: valida rangos numéricos.
  ```yaml
  minimum: 0
  maximum: 100
  multipleOf: 5
  ```

- **Restricciones de matrices**: valida la longitud de las matrices y sus elementos.
  ```yaml
  minItems: 1
  maxItems: 10
  x-kubernetes-list-type: set
  items:
    type: string
  ```

- **Valores de enumeración**: especifica la lista de valores permitidos.
  ```yaml
  enum: ["value1", "value2", "value3"]
  ```

- **Valores predeterminados**: especifica los valores predeterminados de los campos.
  ```yaml
  default: "default-value"
  ```

- **Valores de mapas**: define entradas de mapa tipadas; additionalProperties: false está prohibido en las CRD. Normalmente, los campos desconocidos se eliminan.
  ```yaml
  additionalProperties:
    type: string
  ```

**4. Ejemplo completo de CRD:**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: ["spec"]
          properties:
            spec:
              type: object
              required: ["cronSpec", "image"]
              properties:
                cronSpec:
                  type: string
                  pattern: '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
                image:
                  type: string
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
                  default: 1
            status:
              type: object
              properties:
                active:
                  type: boolean
                lastScheduleTime:
                  type: string
                  format: date-time
      subresources:
        status: {}  # Enable status subresource
      additionalPrinterColumns:
        - name: Schedule
          type: string
          description: The cron schedule
          jsonPath: .spec.cronSpec
        - name: Image
          type: string
          description: The image to use
          jsonPath: .spec.image
        - name: Age
          type: date
          jsonPath: .metadata.creationTimestamp
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
    shortNames:
    - ct
```

**5. Aplicación y uso de la CRD:**

```bash
# Apply CRD
kubectl apply -f crontab-crd.yaml

# Create custom resource
cat <<EOF | kubectl apply -f -
apiVersion: stable.example.com/v1
kind: CronTab
metadata:
  name: my-crontab
spec:
  cronSpec: "* * * * */5"
  image: my-cron-image
  replicas: 3
EOF

# View custom resources
kubectl get crontabs
kubectl get ct  # Using short name
```

**6. Prueba de las reglas de validación:**

Si creas un recurso con valores no válidos, se producirán errores de validación:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: stable.example.com/v1
kind: CronTab
metadata:
  name: invalid-crontab
spec:
  cronSpec: "invalid-cron-spec"  # Pattern mismatch
  image: my-cron-image
  replicas: 20  # Exceeds maximum
EOF
```

Este comando devolverá errores como los siguientes:
El servidor de API rechaza cronSpec/replicas no válidos mediante la validación del esquema de la CRD. En este ejemplo no se instala ningún webhook de admisión independiente; el texto exacto del error varía según la versión.

**7. Prácticas recomendadas:**

- Definir esquemas claros y detallados
- Especificar explícitamente los campos obligatorios
- Proporcionar valores predeterminados adecuados
- Limitar los patrones de cadenas y los rangos numéricos
- Habilitar el subrecurso de estado
- Configurar columnas adicionales de impresión
- Establecer una estrategia de versionado
</details>

2. Explica los conceptos centrales del patrón Operator de Kubernetes y los métodos comunes para implementar Operator.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Conceptos centrales del patrón Operator de Kubernetes:**

El patrón Operator es un mecanismo de extensión de Kubernetes que codifica en software conocimientos operativos específicos de una aplicación para administrar automáticamente aplicaciones complejas. Este patrón imita la manera en que una persona encargada de las operaciones administra sistemas complejos.

**1. Conceptos centrales:**

- **Administración declarativa**: los usuarios declaran el estado deseado y el Operator ajusta el estado actual para que coincida con él.
- **Codificación de conocimientos del dominio**: codifica los conocimientos operativos y las prácticas recomendadas de aplicaciones específicas.
- **Bucle de reconciliación**: observa continuamente el estado real y lo ajusta al estado deseado.
- **Recursos personalizados**: se usan para almacenar la configuración y el estado específicos de la aplicación.
- **Controladores**: observan los cambios en los recursos personalizados y realizan las tareas necesarias.

**2. Funciones comunes de los Operator:**

- **Instalación y actualizaciones**: despliegan componentes de la aplicación y actualizan versiones.
- **Recuperación automática**: detectan fallos y realizan tareas de recuperación.
- **Copia de seguridad y restauración**: automatizan los procesos de copia de seguridad y restauración de datos.
- **Escalado**: expansión y reducción automáticas según los requisitos de carga de trabajo.
- **Administración de la configuración**: gestionan cambios de configuración específicos de la aplicación.
- **Automatización de operaciones**: automatizan tareas operativas rutinarias (p. ej., compactación de bases de datos y reconstrucción de índices).

**Métodos para implementar Operator:**

**1. Uso de Operator SDK:**

[Operator SDK](https://sdk.operatorframework.io/) forma parte de Operator Framework de Red Hat y es una herramienta que simplifica el desarrollo de Operator.

```bash
: "${OPERATOR_IMAGE:?Set a registry image tag or digest you control}"
# Install a supported released SDK/CLI and verify its checksum before scaffolding.

# Create Go-based operator project
operator-sdk init --domain example.com --repo github.com/example/my-operator

# Create API
operator-sdk create api --group apps --version v1alpha1 --kind MyApp --resource --controller

# Create CRD
make manifests

# Build and deploy operator
make docker-build docker-push IMG="$OPERATOR_IMAGE"
make deploy IMG="$OPERATOR_IMAGE"
```

**2. Uso de Kubebuilder:**

[Kubebuilder](https://book.kubebuilder.io/) es un framework desarrollado por un SIG de Kubernetes que proporciona herramientas para desarrollar controladores.

```bash
: "${OPERATOR_IMAGE:?Set a registry image tag or digest you control}"
# Install a supported released SDK/CLI and verify its checksum before scaffolding.

# Initialize project
kubebuilder init --domain example.com --repo github.com/example/my-operator

# Create API
kubebuilder create api --group apps --version v1alpha1 --kind MyApp

# Create CRD and deploy controller
make install
make deploy IMG="$OPERATOR_IMAGE"
```

**3. Implementación de controladores:**

El núcleo de un Operator es la función de reconciliación. Esta función observa el estado actual de los recursos personalizados y realiza las tareas necesarias.

```go
// Uses the scaffold's client.Client and Scheme. Import controllerutil and sort.
func (r *MyAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    var myApp appsv1alpha1.MyApp
    if err := r.Get(ctx, req.NamespacedName, &myApp); err != nil {
        return ctrl.Result{}, client.IgnoreNotFound(err)
    }
    if !myApp.DeletionTimestamp.IsZero() { return ctrl.Result{}, nil }
    deployment := &appsv1.Deployment{ObjectMeta: metav1.ObjectMeta{Name: myApp.Name, Namespace: myApp.Namespace}}
    _, err := controllerutil.CreateOrUpdate(ctx, r.Client, deployment, func() error {
        if deployment.UID != "" && !metav1.IsControlledBy(deployment, &myApp) {
            return fmt.Errorf("refusing to modify Deployment owned by another actor")
        }
        labels := map[string]string{"myapp.example.com/owner-uid": string(myApp.UID)}
        if deployment.Spec.Selector == nil {
            deployment.Spec.Selector = &metav1.LabelSelector{MatchLabels: labels}
        }
        if deployment.Spec.Template.Labels == nil { deployment.Spec.Template.Labels = map[string]string{} }
        deployment.Spec.Template.Labels["myapp.example.com/owner-uid"] = string(myApp.UID)
        size := myApp.Spec.Size
        deployment.Spec.Replicas = &size
        keys := []string{}
        for key := range myApp.Spec.Config { keys = append(keys, key) }
        sort.Strings(keys) // Stable output avoids unnecessary updates.
        env := []corev1.EnvVar{}
        for _, key := range keys { env = append(env, corev1.EnvVar{Name: key, Value: myApp.Spec.Config[key]}) }
        // This operator owns its application container; update image as well as replicas.
        deployment.Spec.Template.Spec.Containers = []corev1.Container{{
            Name: "myapp", Image: myApp.Spec.Image, Env: env,
            Ports: []corev1.ContainerPort{{ContainerPort: 8080, Name: "http"}},
        }}
        return ctrl.SetControllerReference(&myApp, deployment, r.Scheme)
    })
    if err != nil { return ctrl.Result{}, err }
    if myApp.Status.AvailableReplicas != deployment.Status.AvailableReplicas {
        myApp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
        if err := r.Status().Update(ctx, &myApp); err != nil { return ctrl.Result{}, err }
    }
    return ctrl.Result{}, nil
}

func (r *MyAppReconciler) SetupWithManager(mgr ctrl.Manager) error {
    return ctrl.NewControllerManagedBy(mgr).
        For(&appsv1alpha1.MyApp{}).
        Owns(&appsv1.Deployment{}).
        Complete(r)
}
```

**4. Definición de recurso personalizado:**

Define la API para los recursos personalizados que administra el Operator.

```go
// MyApp API
type MyAppSpec struct {
    // Application image
    Image string `json:"image"`

    // Number of replicas
    Size int32 `json:"size"`

    // Configuration options
    Config map[string]string `json:"config,omitempty"`
}

type MyAppStatus struct {
    // Number of available replicas
    AvailableReplicas int32 `json:"availableReplicas"`

    // Last update time
    LastUpdateTime metav1.Time `json:"lastUpdateTime,omitempty"`

    // Status message
    Message string `json:"message,omitempty"`
}

// MyApp resource
// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:printcolumn:name="Replicas",type=integer,JSONPath=`.spec.size`
// +kubebuilder:printcolumn:name="Available",type=integer,JSONPath=`.status.availableReplicas`
// +kubebuilder:printcolumn:name="Age",type=date,JSONPath=`.metadata.creationTimestamp`
type MyApp struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`

    Spec   MyAppSpec   `json:"spec,omitempty"`
    Status MyAppStatus `json:"status,omitempty"`
}
```

**5. Operator basados en Ansible o Helm:**

Además de Go, Operator SDK también admite el desarrollo de Operator con Ansible o Helm.

**Operator basado en Ansible:**
```bash
# Create Ansible-based operator
operator-sdk init --plugins=ansible --domain example.com
operator-sdk create api --group apps --version v1alpha1 --kind MyApp --generate-role

# Edit roles/myapp/tasks/main.yml
```

**Operator basado en Helm:**
```bash
# Create Helm-based operator
operator-sdk init --plugins=helm --domain example.com --helm-chart=<chart-name>
```

**6. Despliegue y prueba de Operator:**

```bash
# Deploy operator
make deploy

# Create custom resource
kubectl apply -f config/samples/

# Check operator logs
kubectl logs -f deployment/my-operator-controller-manager -n my-operator-system

# Check resource status
kubectl get myapps
kubectl describe myapp my-app
```

**7. Niveles de madurez de Operator:**

El modelo de madurez de Operator define los niveles de capacidad de estos:

1. **Instalación básica**: instalación y configuración de aplicaciones
2. **Actualizaciones fluidas**: actualizaciones automáticas entre versiones
3. **Ciclo de vida completo**: copia de seguridad, restauración, recuperación ante fallos, etc.
4. **Información detallada**: escalado automático, ajustes, etc.
5. **Piloto automático**: optimización automática basada en la supervisión

**8. Prácticas recomendadas:**

- Implementar funciones de forma gradual (empezar por lo sencillo)
- Gestionar errores y registros de forma exhaustiva
- Garantizar la idempotencia (el mismo resultado para la misma entrada)
- Establecer referencias de propietario (jerarquía de recursos y recolección de elementos no utilizados)
- Informar del progreso mediante actualizaciones de estado
- Escribir pruebas unitarias y de integración
- Proporcionar documentación clara
</details>

3. Explica los tipos de webhooks de admisión en Kubernetes y los casos de uso de cada uno.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Tipos y casos de uso de los webhooks de admisión de Kubernetes:**

Los webhooks de admisión son mecanismos que pueden interceptar y modificar o validar solicitudes antes de que el servidor de API de Kubernetes las almacene en el almacenamiento persistente (etcd). En general, se dividen en dos tipos: webhooks de mutación y webhooks de validación.

**1. Webhook de mutación:**

Los webhooks de mutación pueden modificar los objetos de las solicitudes que llegan al servidor de API. Se ejecutan antes que los webhooks de validación.

**Características principales:**
- Pueden modificar los objetos de las solicitudes.
- Varios webhooks de mutación se ejecutan en cadena.
- Cada webhook recibe el objeto que modificó el webhook anterior.

**Ejemplo de configuración:**
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: sidecar-injector
webhooks:
- name: sidecar-injector.example.com
  clientConfig:
    service:
      namespace: webhook-system
      name: webhook-server
      path: "/mutate"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

**Casos de uso comunes:**

1. **Inyección de contenedores sidecar:**
   - Inyección automática de un proxy sidecar en mallas de servicios como Istio y Linkerd
   - Agregar sidecar de registro y supervisión
   - Ejemplo: el inyector sidecar de Istio agrega automáticamente contenedores proxy Envoy cuando se crean Pod.

2. **Establecimiento de valores predeterminados:**
   - Establecimiento automático de solicitudes y límites de recursos
   - Aplicación de valores predeterminados de contextos de seguridad
   - Adición automática de etiquetas y anotaciones
   - Ejemplo: establecer solicitudes predeterminadas de CPU y memoria para todos los Pod.

3. **Aplicación de políticas de imágenes:**
   - Modificar las URL de los registros de imágenes
   - Convertir etiquetas de imagen en digest
   - Ejemplo: cambiar `nginx:latest` a `internal-registry.example.com/nginx:1.30.6`.

4. **Modificaciones de volúmenes:**
   - Agregar montajes de volumen predeterminados
   - Montar ConfigMap o Secret automáticamente
   - Ejemplo: la admisión de ServiceAccount ya inyecta tokens proyectados, a menos que automountServiceAccountToken sea false; no anules esa exclusión voluntaria.

5. **Configuración de red de Pod:**
   - Agregar configuraciones de red predeterminadas
   - Modificar la configuración de DNS
   - Ejemplo: aplicar configuraciones específicas de DNS a todos los Pod de un espacio de nombres determinado.

**2. Webhook de validación:**

Los webhooks de validación pueden validar las solicitudes que llegan al servidor de API y permitirlas o denegarlas. Se ejecutan después que los webhooks de mutación.

**Características principales:**
- No pueden modificar los objetos de las solicitudes.
- Solo pueden permitir o denegar solicitudes.
- Varios webhooks de validación se ejecutan en paralelo.
- Todas las decisiones de los webhooks coincidentes deben permitir la solicitud; los errores de llamada y los tiempos de espera se rigen por failurePolicy, por lo que Ignore puede permitir una solicitud sin recibir respuesta.

**Ejemplo de configuración:**
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: pod-policy-validator
webhooks:
- name: pod-policy.example.com
  clientConfig:
    service:
      namespace: webhook-system
      name: webhook-server
      path: "/validate"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE", "UPDATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

**Casos de uso comunes:**

1. **Aplicación de políticas de seguridad:**
   - Prohibir contenedores con privilegios
   - Prohibir la ejecución como usuario root
   - Restringir el uso de la red, el PID o el IPC del host
   - Ejemplo: denegar Pod que se ejecuten en modo privilegiado.

2. **Validación de restricciones de recursos:**
   - Hacer obligatorias las solicitudes y los límites de recursos
   - Aplicar límites máximos de recursos
   - Aplicar clases de QoS
   - Ejemplo: denegar Pod sin límites de memoria.

3. **Validación de políticas de imágenes:**
   - Permitir solo registros aprobados
   - Prohibir el uso de la etiqueta latest
   - Verificar los resultados del análisis de vulnerabilidades
   - Ejemplo: permitir solo imágenes de registros oficiales.

4. **Validación de etiquetas y anotaciones:**
   - Comprobar las etiquetas obligatorias
   - Validar los formatos de las etiquetas
   - Ejemplo: hacer obligatorias las etiquetas `app` y `environment` para todos los Pod.

5. **Políticas basadas en espacios de nombres:**
   - Límites de recursos por espacio de nombres
   - Restricciones de funciones por espacio de nombres
   - Ejemplo: aplicar políticas más estrictas en los espacios de nombres de producción.

**3. Métodos de implementación de webhooks:**

Los webhooks de admisión se implementan como servicios que proporcionan endpoints HTTPS. Estos servicios reciben solicitudes `AdmissionReview`, las procesan y devuelven un `AdmissionResponse`.

**Ejemplo básico de implementación de servidor de webhook (Go):**

```go
package main

import (
    "encoding/json"
    "log"
    "net/http"
    "os"
    "time"
    admissionv1 "k8s.io/api/admission/v1"
    corev1 "k8s.io/api/core/v1"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/api/resource"
)

func readPodReview(w http.ResponseWriter, r *http.Request) (*admissionv1.AdmissionRequest, *corev1.Pod, bool) {
    if r.Method != http.MethodPost || r.Body == nil {
        http.Error(w, "POST body required", http.StatusBadRequest)
        return nil, nil, false
    }
    var review admissionv1.AdmissionReview
    if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 2<<20)).Decode(&review); err != nil {
        http.Error(w, "Invalid AdmissionReview JSON", http.StatusBadRequest)
        return nil, nil, false
    }
    req := review.Request
    if review.APIVersion != "admission.k8s.io/v1" || review.Kind != "AdmissionReview" || req == nil || req.UID == "" {
        http.Error(w, "AdmissionReview v1 request and UID required", http.StatusBadRequest)
        return nil, nil, false
    }
    if req.Kind.Group != "" || req.Kind.Version != "v1" || req.Kind.Kind != "Pod" ||
        (req.Operation != admissionv1.Create && req.Operation != admissionv1.Update) {
        http.Error(w, "Only Pod CREATE/UPDATE is supported", http.StatusBadRequest)
        return nil, nil, false
    }
    var pod corev1.Pod
    if err := json.Unmarshal(req.Object.Raw, &pod); err != nil {
        http.Error(w, "Invalid Pod JSON", http.StatusBadRequest)
        return nil, nil, false
    }
    return req, &pod, true
}

func writeReview(w http.ResponseWriter, response admissionv1.AdmissionResponse) {
    review := admissionv1.AdmissionReview{
        TypeMeta: metav1.TypeMeta{APIVersion: "admission.k8s.io/v1", Kind: "AdmissionReview"},
        Response: &response,
    }
    data, err := json.Marshal(review)
    if err != nil {
        http.Error(w, "Response encoding failed", http.StatusInternalServerError)
        return
    }
    w.Header().Set("Content-Type", "application/json")
    _, _ = w.Write(data)
}

func writePatch(w http.ResponseWriter, req *admissionv1.AdmissionRequest, patches []map[string]interface{}) {
    response := admissionv1.AdmissionResponse{UID: req.UID, Allowed: true}
    if len(patches) > 0 {
        data, err := json.Marshal(patches)
        if err != nil {
            http.Error(w, "Patch encoding failed", http.StatusInternalServerError)
            return
        }
        patchType := admissionv1.PatchTypeJSONPatch
        response.PatchType, response.Patch = &patchType, data
    }
    writeReview(w, response)
}

func deny(w http.ResponseWriter, req *admissionv1.AdmissionRequest, message string) {
    writeReview(w, admissionv1.AdmissionResponse{
        UID: req.UID, Allowed: false,
        Result: &metav1.Status{Status: "Failure", Reason: metav1.StatusReasonForbidden, Code: 403, Message: message},
    })
}
var sidecarImage string

func mutateHandler(w http.ResponseWriter, r *http.Request) {
    req, pod, ok := readPodReview(w, r)
    if !ok { return }
    // This example targets explicitly declared Linux Pods on CREATE only.
    if req.Operation != admissionv1.Create || pod.Spec.OS == nil || pod.Spec.OS.Name != corev1.Linux {
        writePatch(w, req, nil)
        return
    }
    if sidecarImage == "" {
        deny(w, req, "Configure a tested SIDE_CAR_IMAGE first")
        return
    }
    changed, foundVolume, foundSidecar := false, false, false
    for _, volume := range pod.Spec.Volumes {
        if volume.Name == "shared-data" {
            if volume.EmptyDir == nil {
                deny(w, req, "shared-data is reserved for an emptyDir volume")
                return
            }
            foundVolume = true
        }
    }
    if !foundVolume {
        pod.Spec.Volumes = append(pod.Spec.Volumes, corev1.Volume{
            Name: "shared-data", VolumeSource: corev1.VolumeSource{EmptyDir: &corev1.EmptyDirVolumeSource{}},
        })
        changed = true
    }
    for i := range pod.Spec.Containers {
        c := &pod.Spec.Containers[i]
        if c.Name == "monitoring-sidecar" {
            if c.Image != sidecarImage {
                deny(w, req, "monitoring-sidecar name is reserved")
                return
            }
            foundSidecar = true
        }
        mounted := false
        for _, mount := range c.VolumeMounts {
            if mount.MountPath == "/var/monitoring" {
                if mount.Name != "shared-data" || mount.SubPath != "" || mount.SubPathExpr != "" {
                    deny(w, req, "/var/monitoring is reserved for shared-data")
                    return
                }
                mounted = true
            }
        }
        if !mounted {
            c.VolumeMounts = append(c.VolumeMounts, corev1.VolumeMount{Name: "shared-data", MountPath: "/var/monitoring"})
            changed = true
        }
    }
    if !foundSidecar {
        pod.Spec.Containers = append(pod.Spec.Containers, corev1.Container{
            Name: "monitoring-sidecar", Image: sidecarImage,
            VolumeMounts: []corev1.VolumeMount{{Name: "shared-data", MountPath: "/var/monitoring", ReadOnly: true}},
            Resources: corev1.ResourceRequirements{
                Requests: corev1.ResourceList{corev1.ResourceCPU: resource.MustParse("50m"), corev1.ResourceMemory: resource.MustParse("50Mi")},
                Limits: corev1.ResourceList{corev1.ResourceCPU: resource.MustParse("100m"), corev1.ResourceMemory: resource.MustParse("100Mi")},
            },
        })
        changed = true
    }
    if !changed { writePatch(w, req, nil); return }
    // Whole-array add also works when volumes was absent; preserve all existing entries.
    writePatch(w, req, []map[string]interface{}{
        {"op": "add", "path": "/spec/volumes", "value": pod.Spec.Volumes},
        {"op": "add", "path": "/spec/containers", "value": pod.Spec.Containers},
    })
}

func validateHandler(w http.ResponseWriter, r *http.Request) {
    req, pod, ok := readPodReview(w, r)
    if !ok { return }
    contexts := []*corev1.SecurityContext{}
    for _, c := range pod.Spec.Containers { contexts = append(contexts, c.SecurityContext) }
    for _, c := range pod.Spec.InitContainers { contexts = append(contexts, c.SecurityContext) }
    for _, c := range pod.Spec.EphemeralContainers { contexts = append(contexts, c.SecurityContext) }
    for _, sc := range contexts {
        if sc != nil && sc.Privileged != nil && *sc.Privileged {
            deny(w, req, "Privileged containers are not allowed")
            return
        }
    }
    writeReview(w, admissionv1.AdmissionResponse{UID: req.UID, Allowed: true})
}

func main() {
    sidecarImage = os.Getenv("SIDE_CAR_IMAGE")
    if sidecarImage == "" { log.Fatal("Set SIDE_CAR_IMAGE to a tested Linux image tag/digest") }
    mux := http.NewServeMux()
    mux.HandleFunc("/mutate", mutateHandler)
    mux.HandleFunc("/validate", validateHandler)
    server := &http.Server{Addr: ":8443", Handler: mux, ReadHeaderTimeout: 5*time.Second}
    log.Fatal(server.ListenAndServeTLS("/etc/webhook/certs/tls.crt", "/etc/webhook/certs/tls.key"))
}
```

**4. Despliegue y configuración del webhook:**

Compila el servidor completo anterior, sustituye los marcadores de posición de la imagen del servidor y del sidecar, y crea webhook-system y webhook-server-tls. El certificado del servidor debe incluir webhook-server.webhook-system.svc (y cualquier nombre alternativo de Service que se use), y caBundle debe contener la CA que lo firma. La imagen del sidecar debe admitir los permisos del sistema de archivos de la aplicación. Este ejemplo muestra un sidecar normal; configura por separado el comportamiento de apagado o de native sidecar para los Job.

```yaml
# Webhook server deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webhook-server
  namespace: webhook-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: webhook-server
  template:
    metadata:
      labels:
        app: webhook-server
    spec:
      containers:
      - name: server
        image: example/webhook-server:REPLACE_WITH_TESTED_RELEASE
        env:
        - name: SIDE_CAR_IMAGE
          value: example/monitoring-agent:REPLACE_WITH_TESTED_RELEASE
        ports:
        - containerPort: 8443
        volumeMounts:
        - name: tls
          mountPath: "/etc/webhook/certs"
          readOnly: true
      volumes:
      - name: tls
        secret:
          secretName: webhook-server-tls

---
# Webhook server service
apiVersion: v1
kind: Service
metadata:
  name: webhook-server
  namespace: webhook-system
spec:
  selector:
    app: webhook-server
  ports:
  - port: 443
    targetPort: 8443
```

**5. Prácticas recomendadas:**

- **Optimización del rendimiento**: los webhooks forman parte de la ruta de solicitudes del servidor de API, por lo que deben responder rápidamente.
- **Gestión de errores**: considera qué debe ocurrir si falla el servidor del webhook y establece `failurePolicy` según corresponda.
- **Limitación del ámbito**: aplica los webhooks solo a los recursos y las operaciones necesarios.
- **Pruebas**: prueba exhaustivamente el comportamiento del webhook en distintas situaciones.
- **Supervisión**: supervisa el rendimiento y los errores del servidor del webhook.
- **Administración de versiones**: anuncia únicamente las versiones de AdmissionReview que realmente se implementen y devuelve la misma versión que la solicitud.
</details>

## Preguntas prácticas

1. Escribe una definición de recurso personalizado (CRD) que cumpla los siguientes requisitos:
   - Grupo de API: webapp.example.com
   - Versión: v1
   - Kind: WebApp
   - Ámbito: Namespaced
   - Campos obligatorios: spec.image, spec.replicas
   - Reglas de validación: replicas debe ser un entero entre 1 y 10
   - Habilitar el subrecurso de estado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.webapp.example.com
spec:
  group: webapp.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: ["spec"]
          properties:
            spec:
              type: object
              required: ["image", "replicas"]
              properties:
                image:
                  type: string
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
                port:
                  type: integer
                  default: 80
                env:
                  type: array
                  items:
                    type: object
                    required: ["name"]
                    properties:
                      name:
                        type: string
                      value:
                        type: string
            status:
              type: object
              properties:
                availableReplicas:
                  type: integer
                phase:
                  type: string
      subresources:
        status: {}
      additionalPrinterColumns:
      - name: Replicas
        type: integer
        jsonPath: .spec.replicas
      - name: Image
        type: string
        jsonPath: .spec.image
      - name: Age
        type: date
        jsonPath: .metadata.creationTimestamp
  scope: Namespaced
  names:
    plural: webapps
    singular: webapp
    kind: WebApp
    shortNames:
    - wa
```

Esta CRD tiene las siguientes características:

1. **Información básica**:
   - Grupo de API: `webapp.example.com`
   - Versión: `v1`
   - Kind: `WebApp`
   - Ámbito: `Namespaced`

2. **Validación del esquema**:
   - El campo `spec` es obligatorio.
   - `spec.image` y `spec.replicas` son campos obligatorios.
   - `spec.replicas` debe ser un entero entre 1 y 10.
   - `spec.port` es un campo opcional cuyo valor predeterminado es 80.
   - `spec.env` es un campo opcional que define una matriz de variables de entorno.

3. **Subrecurso de estado**:
   - El subrecurso `status` está habilitado para que los controladores puedan actualizar el estado.
   - Se definen los campos `status.availableReplicas` y `status.phase`.

4. **Columnas adicionales de impresión**:
   - Al ejecutar `kubectl get webapps`, se muestran las columnas Replicas, Image y Age.

5. **Configuración de nombres**:
   - Plural: `webapps`
   - Singular: `webapp`
   - Kind: `WebApp`
   - Nombre corto: `wa`

Con esta CRD puedes crear recursos personalizados como el siguiente:

```yaml
apiVersion: webapp.example.com/v1
kind: WebApp
metadata:
  name: my-webapp
  namespace: default
spec:
  image: nginx:1.30.6
  replicas: 3
  port: 80
  env:
    - name: ENV_VAR1
      value: "value1"
    - name: ENV_VAR2
      value: "value2"
```

Los controladores pueden observar este recurso y actualizar su estado:

```yaml
status:
  availableReplicas: 3
  phase: Running
```
</details>

2. Escribe una configuración de webhook de admisión de mutación que cumpla los siguientes requisitos:
   - Agregar un sidecar a las solicitudes CREATE de Pod que declaren explícitamente spec.os.name: linux
   - Aplicarse solo a un espacio de nombres específico (monitoring)
   - Servicio del webhook: webhook-service.webhook-system.svc
   - Ruta: /mutate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: sidecar-injector
webhooks:
- name: sidecar-injector.example.com
  clientConfig:
    service:
      namespace: webhook-system
      name: webhook-service
      path: "/mutate"
    caBundle: ${CA_BUNDLE}  # Replace with base64-encoded CA certificate in actual environment
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE"]
    resources: ["pods"]
    scope: "Namespaced"
  namespaceSelector:
    matchLabels:
      kubernetes.io/metadata.name: monitoring
  matchConditions:
  - name: explicit-linux-pod
    expression: "has(object.spec.os) && object.spec.os.name == 'linux'"
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
  failurePolicy: Fail
---
# Add label to namespace
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring
  labels:
    kubernetes.io/metadata.name: monitoring
```

Esta configuración tiene las siguientes características:

1. **Configuración del webhook**:
   - Nombre: `sidecar-injector`
   - Servicio del webhook: `webhook-service.webhook-system.svc`
   - Ruta: `/mutate`

2. **Ámbito**:
   - Grupo de API: `""` (grupo de API principal)
   - Versión de API: `v1`
   - Operación: `CREATE` (solo se aplica al crear Pod)
   - Recurso: `pods`
   - Ámbito: `Namespaced`

3. **Selector de espacio de nombres**:
   - Se aplica solo a espacios de nombres con la etiqueta `kubernetes.io/metadata.name: monitoring`.
   - El servidor de API proporciona esa etiqueta inmutable con el nombre del espacio de nombres monitoring.

4. **Configuración adicional**:
   - `admissionReviewVersions`: versiones de API de AdmissionReview admitidas
   - `sideEffects`: el webhook no tiene efectos secundarios
   - `timeoutSeconds`: tiempo de espera de la respuesta del webhook
   - `failurePolicy`: denegar las solicitudes si falla el webhook

El servidor del webhook debe implementar una lógica como esta:

Usa `mutateHandler` y los auxiliares comunes de solicitud y respuesta del servidor completo anterior. Crea la matriz volumes si falta, conserva las entradas existentes, evita la inyección duplicada y monta shared-data tanto en los contenedores de la aplicación como en los sidecar. Los conflictos de nombres o rutas reservados se deniegan.

Este webhook agrega automáticamente un contenedor sidecar de supervisión a los Pod que declaren `spec.os.name: linux` y se creen en el espacio de nombres `monitoring`. El contenedor sidecar usa una imagen de agente de supervisión y monta un volumen compartido para compartir datos con el contenedor principal.
</details>

> Los fragmentos de código de los controladores requieren los tipos, el cliente y RBAC del proyecto generado. Comprueban la propiedad del Deployment, reconcilian la configuración de imagen, réplicas y entorno, y usan una observación Owns para los cambios de estado. Limpia los recursos externos con finalizers antes de eliminarlos. Durante esta revisión no se ejecutó ningún despliegue en Kubernetes ni en AWS.

## Referencias de verificación

- https://kubernetes.io/releases/
- https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/
- https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/
- https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/
- https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/
- https://kubernetes.io/docs/tasks/extend-kubernetes/configure-aggregation-layer/
- https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/
- https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/scheduler/apis/config/types.go
- https://github.com/kubernetes/cloud-provider-aws/blob/master/docs/prerequisites.md
- https://github.com/kubernetes/cloud-provider-aws/blob/master/examples/existing-cluster/base/aws-cloud-controller-manager-daemonset.yaml
- https://github.com/kubernetes-sigs/kubebuilder/blob/master/README.md
- https://github.com/operator-framework/operator-sdk/blob/master/README.md
- https://github.com/NVIDIA/k8s-device-plugin/blob/main/README.md
- https://github.com/jaegertracing/jaeger-operator/blob/main/README.md
- https://istio.io/latest/blog/2024/in-cluster-operator-deprecation-announcement/
- https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html
- https://docs.aws.amazon.com/eks/latest/userguide/lbc-helm.html
- https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html
- https://github.com/aws-controllers-k8s/community/blob/main/docs/content/docs/user-docs/install.md
- https://github.com/aws-controllers-k8s/s3-controller/blob/main/helm/values.yaml
