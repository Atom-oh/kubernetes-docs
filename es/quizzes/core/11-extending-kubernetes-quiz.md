# Cuestionario sobre la extensión de Kubernetes

Este cuestionario evalúa tus conocimientos conceptuales y prácticos sobre los mecanismos de extensión de Kubernetes. Cubre temas como Custom Resource Definitions (CRD), custom controllers, extensiones de API, webhooks y el operator pattern.

## Preguntas de opción múltiple

1. ¿Cuál es la forma más común de definir custom resources en Kubernetes?
   - A) Definir el esquema del recurso usando ConfigMap
   - B) Crear una CustomResourceDefinition (CRD)
   - C) Modificar directamente el código del API server
   - D) Usar la Aggregation Layer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear una CustomResourceDefinition (CRD)**

**Explicación:**
La forma más común de definir custom resources en Kubernetes es crear una CustomResourceDefinition (CRD). CRD es un mecanismo que permite extender la Kubernetes API definiendo nuevos tipos de recursos.

Usar CRDs proporciona los siguientes beneficios:
- Puedes agregar nuevos tipos de recursos sin modificar el Kubernetes API server existente.
- Puedes administrar custom resources usando herramientas estándar de Kubernetes como `kubectl`.
- Puedes aprovechar características como validación de recursos, versionado y subresources de estado.

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
- ConfigMaps se usan para almacenar datos de configuración y no son adecuados para extensiones de API.
- Modificar directamente el código del API server es complejo, difícil de mantener y puede causar problemas durante las actualizaciones.
- La Aggregation Layer es otra forma de definir custom resources, pero es más compleja que las CRDs porque requiere implementar un API server separado.
</details>

2. ¿Cuál es el propósito principal de un Kubernetes Operator?
   - A) Optimizar el uso de recursos de los nodos del cluster
   - B) Codificar el conocimiento operativo de aplicaciones complejas en software automatizado
   - C) Mejorar el rendimiento del Kubernetes API server
   - D) Extender la funcionalidad de red del cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Codificar el conocimiento operativo de aplicaciones complejas en software automatizado**

**Explicación:**
El propósito principal de un Kubernetes Operator es codificar el conocimiento operativo de aplicaciones complejas en software automatizado. El operator pattern es una implementación de software de la forma en que un operador humano administra aplicaciones complejas.

Características clave de los operators:
- Combina custom resources con custom controllers para implementar lógica específica de la aplicación.
- Automatiza tareas operativas como despliegue de aplicaciones, actualizaciones, backup, recuperación y escalado.
- Monitorea continuamente el estado de la aplicación y lo ajusta al estado deseado.
- Codifica conocimiento del dominio para habilitar la administración declarativa de aplicaciones complejas.

Casos de uso comunes para operators:
- Administración automatizada de bases de datos (por ejemplo, PostgreSQL, MySQL, MongoDB)
- Despliegue y configuración de sistemas de mensajería (por ejemplo, Kafka, RabbitMQ)
- Configuración y mantenimiento de sistemas de monitoreo (por ejemplo, Prometheus)
- Administración de service meshes (por ejemplo, Istio)

Ejemplo de Operator - Prometheus Operator:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
spec:
  serviceAccountName: prometheus
  replicas: 2
  version: v2.35.0
  serviceMonitorSelector:
    matchLabels:
      team: frontend
  resources:
    requests:
      memory: 400Mi
```

Con esta configuración declarativa simple, el Prometheus Operator gestiona automáticamente tareas complejas como:
- Desplegar servidores Prometheus
- Crear y administrar archivos de configuración
- Descubrimiento automático de objetivos de monitoreo de servicios
- Configuración de alta disponibilidad
- Administración de almacenamiento
- Coordinación de actualizaciones

Las otras opciones no son el propósito principal de los operators:
- La optimización del uso de recursos es el rol de HPA (Horizontal Pod Autoscaler), VPA (Vertical Pod Autoscaler), etc.
- Mejorar el rendimiento del API server no es el propósito principal de los operators.
- Extender la funcionalidad de red es el rol de los plugins CNI o de los service meshes.
</details>

3. ¿Cuál es la función principal de los Admission Webhooks en Kubernetes?
   - A) Gestionar la autenticación para el API server
   - B) Interceptar solicitudes de creación o modificación de recursos para validarlas o modificarlas
   - C) Monitorear eventos del cluster y enviar alertas
   - D) Proporcionar APIs para la integración con sistemas externos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Interceptar solicitudes de creación o modificación de recursos para validarlas o modificarlas**

**Explicación:**
La función principal de los Admission Webhooks en Kubernetes es interceptar solicitudes de creación o modificación de recursos para validarlas o modificarlas. Los admission webhooks proporcionan un mecanismo para interceptar solicitudes antes de que el Kubernetes API server las almacene en almacenamiento persistente (etcd).

Dos tipos de admission webhooks:

1. **Validating Webhook**:
   - Valida solicitudes de creación, actualización y eliminación de recursos.
   - Puede permitir o denegar solicitudes, pero no puede modificarlas.
   - Se usa para aplicación de políticas, comprobaciones de seguridad, validación de configuración, etc.

2. **Mutating Webhook**:
   - Puede validar y modificar solicitudes de creación y actualización de recursos.
   - Se usa para establecer valores predeterminados, inyectar sidecar containers, agregar etiquetas, etc.
   - Se ejecuta antes de los validating webhooks.

Ejemplo de configuración de admission webhook:
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
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
```

Casos de uso comunes para admission webhooks:
- Aplicar políticas de seguridad (por ejemplo, prohibir containers privilegiados)
- Exigir resource requests y limits
- Inyección automática de sidecar containers (por ejemplo, Istio)
- Adición automática de etiquetas y anotaciones
- Restringir image registries
- Aplicar políticas basadas en namespace

Problemas con las otras opciones:
- Gestionar la autenticación para el API server es el rol de los Authentication Plugins.
- Monitorear eventos del cluster y enviar alertas es el rol de event listeners o herramientas de monitoreo.
- Proporcionar APIs para la integración con sistemas externos es un propósito general de las extensiones de API, pero no la función principal de los admission webhooks.
</details>

4. ¿Cuál es el propósito principal de la Aggregation Layer en el Kubernetes API server?
   - A) Optimizar el rendimiento del API server
   - B) Consolidar múltiples API servers en un único API server
   - C) Integrar custom API servers en el API server principal para extender la API
   - D) Proporcionar service discovery dentro del cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Integrar custom API servers en el API server principal para extender la API**

**Explicación:**
El propósito principal de la Aggregation Layer en el Kubernetes API server es integrar custom API servers en el API server principal para extender la API. Esto proporciona otra forma de extender la Kubernetes API, ofreciendo características más potentes que las CRDs, aunque con mayor complejidad.

Características clave de la Aggregation Layer:
- Integra custom API servers en el espacio de URL del Kubernetes API server.
- Los custom API servers pueden tener su propio almacenamiento, lógica de negocio, versiones de API, etc.
- El API server principal actúa como proxy de las solicitudes hacia el custom API server adecuado.
- La autenticación y la autorización son gestionadas por el API server principal.

Casos en los que se usa la Aggregation Layer:
- Cuando se necesita lógica de validación compleja
- Cuando se requiere un backend de almacenamiento personalizado
- Cuando se necesita un comportamiento diferente al de las APIs existentes
- Cuando se requiere transformación de recursos o cálculo de estado especial

Ejemplo de recurso APIService:
```yaml
apiVersion: apiregistration.k8s.io/v1
kind: APIService
metadata:
  name: v1alpha1.metrics.k8s.io
spec:
  service:
    name: metrics-server
    namespace: kube-system
  group: metrics.k8s.io
  version: v1alpha1
  insecureSkipTLSVerify: true
  groupPriorityMinimum: 100
  versionPriority: 100
```

Esta configuración enruta las solicitudes para el grupo de API `metrics.k8s.io/v1alpha1` al service `metrics-server` en el namespace `kube-system`.

Ejemplos reales que usan la Aggregation Layer:
- metrics-server: Proporciona métricas de uso de recursos de node y pod
- service-catalog: Integración con brokers de servicios externos
- custom-metrics-apiserver: Proporciona métricas personalizadas para HPA

Problemas con las otras opciones:
- La Aggregation Layer no está destinada a optimizar el rendimiento del API server.
- Consolidar múltiples API servers en uno no es una descripción precisa. La Aggregation Layer integra múltiples API servers en un único espacio de URL, pero los servers se ejecutan por separado.
- La Aggregation Layer no proporciona service discovery. Ese es el rol de Kubernetes Services.
</details>

5. ¿Cuál es el rol principal de un Custom Controller en Kubernetes?
   - A) Monitorear el uso de recursos de los nodos del cluster
   - B) Observar el estado de los custom resources y reconciliarlo con el estado deseado
   - C) Gestionar la autenticación y autorización para solicitudes del API server
   - D) Administrar la red del cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Observar el estado de los custom resources y reconciliarlo con el estado deseado**

**Explicación:**
El rol principal de un Custom Controller en Kubernetes es observar el estado de los custom resources y reconciliarlo con el estado deseado. Los controllers implementan el "reconciliation loop", un patrón operativo central en Kubernetes, para ajustar continuamente el estado real del sistema al estado deseado.

Características clave de los custom controllers:
- Observan tipos de recursos específicos (normalmente custom resources definidos mediante CRDs).
- Reaccionan a eventos de cambio de recursos y ejecutan lógica de negocio.
- Realizan tareas para ajustar el estado real de los recursos al estado deseado.
- Actualizan el campo de estado de los recursos para reflejar el estado actual.

Componentes comunes de los custom controllers:
1. **Informer**: Observa el Kubernetes API server y recibe eventos de cambio de recursos.
2. **Work Queue**: Almacena y administra eventos que deben procesarse.
3. **Reconciler**: Compara el estado deseado y el estado real de los recursos y realiza las tareas necesarias.
4. **Client**: Interactúa con la Kubernetes API para crear, actualizar y eliminar recursos.

Ejemplo de custom controller - función reconcile simple:
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
        // Resource deleted - perform cleanup
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
    _, err = c.customResourceClient.CustomResources(namespace).UpdateStatus(instanceCopy)
    return err
}
```

Casos de uso comunes para custom controllers:
- Automatizar el despliegue y la administración de aplicaciones complejas
- Integración con sistemas externos (por ejemplo, aprovisionamiento de recursos cloud)
- Automatizar procesos de backup y recuperación
- Implementar estrategias de despliegue avanzadas (por ejemplo, canary deployments, blue-green deployments)

Problemas con las otras opciones:
- Monitorear el uso de recursos de los nodos del cluster es el rol de metrics-server o herramientas de monitoreo como Prometheus.
- Gestionar la autenticación y autorización para solicitudes del API server es el rol de los plugins de autenticación y autorización.
- Administrar la red del cluster es el rol de los plugins CNI o network controllers.
</details>

6. ¿Qué formato se usa para definir esquemas de validación para CRDs (CustomResourceDefinitions) en Kubernetes?
   - A) JSON Schema
   - B) XML Schema
   - C) OpenAPI v3 Schema
   - D) GraphQL Schema

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) OpenAPI v3 Schema**

**Explicación:**
El formato usado para definir esquemas de validación para CRDs (CustomResourceDefinitions) en Kubernetes es OpenAPI v3 Schema. Este esquema define la estructura y los tipos de campos de los custom resources y lo usa el API server para validar solicitudes de creación y actualización de recursos.

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

OpenAPI v3 Schema proporciona varias características de validación:
- Especificar campos obligatorios
- Validación de tipos de datos (string, number, boolean, object, array, etc.)
- Validación de patrones de cadenas (expresiones regulares)
- Validación de rangos numéricos (minimum, maximum)
- Validación de longitud de arrays
- Validación de valores enum
- Definición de estructura de objetos anidados

Problemas con las otras opciones:
- JSON Schema es la base de OpenAPI, pero Kubernetes usa específicamente OpenAPI v3 Schema.
- XML Schema no se usa en la Kubernetes API.
- GraphQL Schema se usa para APIs GraphQL, pero no para la Kubernetes API.
</details>

7. ¿Cuál es el principal beneficio de habilitar el subresource de estado para custom resources en Kubernetes?
   - A) Creación de recursos más rápida
   - B) Separación de actualizaciones de spec y estado, y control RBAC
   - C) Características automáticas de backup y recuperación
   - D) Administración simplificada de versiones de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Separación de actualizaciones de spec y estado, y control RBAC**

**Explicación:**
El principal beneficio de habilitar el subresource de estado para custom resources en Kubernetes es la separación de las actualizaciones de spec y estado, y la capacidad de controlar el acceso mediante RBAC (Role-Based Access Control).

Beneficios de habilitar el subresource de estado:

1. **Separación de responsabilidades**:
   - El campo `spec` define el estado deseado especificado por los usuarios.
   - El campo `status` informa el estado real observado por los controllers.
   - Esta separación aclara las responsabilidades de usuarios y controllers.

2. **Control RBAC**:
   - Los permisos de actualización de estado pueden concederse solo a los controllers mientras se otorgan permisos de solo lectura a los usuarios normales.
   - Esto evita modificaciones no autorizadas de la información de estado.

3. **Prevención de conflictos**:
   - Aunque un usuario actualice `spec` mientras un controller actualiza `status`, no se produce ningún conflicto.
   - Esto se debe a que los dos campos se actualizan mediante solicitudes de API separadas.

4. **Soporte de subresource de escala**:
   - Habilitar el subresource de estado también permite habilitar el subresource de escala.
   - Esto permite usar herramientas estándar de escalado de Kubernetes como HPA (Horizontal Pod Autoscaler).

Ejemplo de habilitación del subresource de estado en CRD:
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
        status: {}  # Enable status subresource
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                # Spec field definitions...
            status:
              type: object
              properties:
                # Status field definitions...
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
```

Ejemplo de actualización de estado desde el controller:
```go
// Update status only
statusUpdate := &v1alpha1.MyResource{}
statusUpdate.Name = instance.Name
statusUpdate.Namespace = instance.Namespace
statusUpdate.Status.Phase = "Running"
statusUpdate.Status.Message = "Resource is running"

_, err = c.clientset.MyGroup().MyResources(namespace).UpdateStatus(statusUpdate)
```

Problemas con las otras opciones:
- El subresource de estado no mejora la velocidad de creación de recursos.
- No proporciona características automáticas de backup y recuperación.
- La administración de versiones de recursos se gestiona mediante el campo `versions` de la CRD y no está directamente relacionada con el subresource de estado.
</details>

8. ¿Cuál es el propósito principal de Webhook Conversion en Kubernetes?
   - A) Enrutar solicitudes de API a servicios externos
   - B) Gestionar la conversión entre diferentes versiones de custom resources
   - C) Convertir tokens de autenticación a diferentes formatos
   - D) Convertir datos de logs a formatos estructurados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Gestionar la conversión entre diferentes versiones de custom resources**

**Explicación:**
El propósito principal de Webhook Conversion en Kubernetes es gestionar la conversión entre diferentes versiones de custom resources. Esta característica admite múltiples versiones de CRDs y habilita una migración fluida entre versiones.

Características clave de webhook conversion:

1. **Soporte multiversión**:
   - Las CRDs pueden admitir múltiples versiones de API simultáneamente (por ejemplo, v1alpha1, v1beta1, v1).
   - Cada versión puede tener esquemas y campos diferentes.

2. **Conversión automática**:
   - El API server gestiona automáticamente la conversión entre la versión solicitada por el cliente y la versión de almacenamiento.
   - El conversion webhook proporciona lógica de conversión personalizada en este proceso.

3. **Independencia de la versión de almacenamiento**:
   - Incluso si cambia la versión de almacenamiento, los clientes que usan versiones anteriores pueden seguir funcionando.
   - El webhook gestiona la conversión bidireccional entre versiones antiguas y nuevas.

Ejemplo de configuración de conversion webhook en CRD:
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
          # v1 schema definition...
    - name: v1beta1
      served: true
      storage: false
      schema:
        openAPIV3Schema:
          # v1beta1 schema definition...
  conversion:
    strategy: Webhook
    webhook:
      clientConfig:
        service:
          namespace: webhook-system
          name: crd-conversion-webhook
          path: /convert
        caBundle: <base64-encoded-ca-cert>
      conversionReviewVersions: ["v1", "v1beta1"]
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
```

Ejemplo de implementación de un conversion webhook server:
```go
func (s *WebhookServer) ServeConvert(w http.ResponseWriter, r *http.Request) {
    var body []byte
    if r.Body != nil {
        if data, err := ioutil.ReadAll(r.Body); err == nil {
            body = data
        }
    }

    // Decode ConversionReview request
    convertReview := v1.ConversionReview{}
    if err := json.Unmarshal(body, &convertReview); err != nil {
        // Error handling
        return
    }

    // Perform conversion logic
    if convertReview.Request.DesiredAPIVersion == "stable.example.com/v1" {
        // v1beta1 -> v1 conversion
        for i, obj := range convertReview.Request.Objects {
            v1beta1Obj := &v1beta1.CronTab{}
            if err := json.Unmarshal(obj.Raw, v1beta1Obj); err != nil {
                // Error handling
                return
            }

            // Conversion logic
            v1Obj := &v1.CronTab{
                Spec: v1.CronTabSpec{
                    CronSpec: v1beta1Obj.Spec.Cron,  // Field name change
                    Image: v1beta1Obj.Spec.Image,
                    Replicas: v1beta1Obj.Spec.Replicas,
                },
            }

            // Encode converted object
            raw, err := json.Marshal(v1Obj)
            if err != nil {
                // Error handling
                return
            }

            convertReview.Response.ConvertedObjects = append(
                convertReview.Response.ConvertedObjects,
                runtime.RawExtension{Raw: raw},
            )
        }
    } else {
        // v1 -> v1beta1 conversion
        // Similar logic...
    }

    // Set response
    convertReview.Response.UID = convertReview.Request.UID
    convertReview.Response.Result.Status = "Success"

    // Send response
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(convertReview)
}
```

Problemas con las otras opciones:
- Enrutar solicitudes de API a servicios externos es el rol de API aggregation.
- Convertir tokens de autenticación es el rol de los plugins de autenticación.
- Convertir datos de logs es el rol de los sistemas de logging.
</details>

9. ¿Cuál de los siguientes NO es un framework que ayuda a desarrollar Kubernetes operators?
   - A) Operator Framework
   - B) Kubebuilder
   - C) Metacontroller
   - D) Kubespray

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Kubespray**

**Explicación:**
Kubespray no es un framework que ayude a desarrollar Kubernetes operators. Kubespray es una herramienta para desplegar y administrar clusters de Kubernetes usando playbooks de Ansible. Se centra en la instalación y configuración del cluster y no está relacionado con el desarrollo de operators.

Los frameworks reales para el desarrollo de Kubernetes operators son:

1. **Operator Framework**:
   - Toolkit de desarrollo de operators desarrollado por Red Hat
   - Componentes clave:
     - Operator SDK: Herramientas de scaffolding y desarrollo de Operator
     - Operator Lifecycle Manager (OLM): Administración de instalación y actualización de Operator
     - Operator Metering: Informes de uso de Operator
   - Admite desarrollo de operators basado en Go, Ansible y Helm

2. **Kubebuilder**:
   - Framework desarrollado por Kubernetes SIG (Special Interest Group)
   - SDK para desarrollar controllers en Go
   - Proporciona generación de código, administración de CRD y herramientas de prueba
   - Basado en la biblioteca controller-runtime

3. **Metacontroller**:
   - Framework de operators ligero basado en webhooks
   - Puede implementar lógica de controller en varios lenguajes
   - Definición declarativa de controller
   - Adecuado para desarrollar rápidamente controllers simples

Comparación de características de cada framework:

| Framework | Lenguaje principal | Complejidad | Características |
|-----------|------------------|------------|----------|
| Operator Framework | Go, Ansible, Helm | Media-alta | Toolkit integral, varias opciones de desarrollo |
| Kubebuilder | Go | Media | Patrones estandarizados, herramientas de generación de código |
| Metacontroller | Independiente del lenguaje | Baja | Basado en webhooks, implementación simple |

Ejemplo de desarrollo de Operator (usando Kubebuilder):
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
- Operator Framework es el toolkit integral de desarrollo de operators de Red Hat.
- Kubebuilder es un framework de desarrollo de controllers basado en Go desarrollado por Kubernetes SIG.
- Metacontroller es un framework de operators ligero basado en webhooks.
</details>

10. ¿Cuál es la principal diferencia entre Custom Resource Definitions (CRD) y Aggregated APIs en Kubernetes?
    - A) Las CRDs no admiten versionado, pero las Aggregated APIs sí
    - B) Las CRDs no admiten esquemas de validación, pero las Aggregated APIs sí
    - C) Las CRDs son simples de implementar, pero tienen flexibilidad limitada, mientras que las Aggregated APIs son complejas de implementar, pero proporcionan más flexibilidad
    - D) Las CRDs solo admiten recursos de alcance cluster, y las Aggregated APIs solo admiten recursos de alcance namespace

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Las CRDs son simples de implementar, pero tienen flexibilidad limitada, mientras que las Aggregated APIs son complejas de implementar, pero proporcionan más flexibilidad**

**Explicación:**
La principal diferencia entre Custom Resource Definitions (CRD) y Aggregated APIs en Kubernetes es el equilibrio entre complejidad de implementación y flexibilidad. Las CRDs son simples de implementar, pero tienen flexibilidad limitada, mientras que las Aggregated APIs son complejas de implementar, pero proporcionan más flexibilidad.

**Características de las CRDs (CustomResourceDefinitions):**
- **Implementación simple**: Puedes definir nuevos recursos de API con un único archivo YAML.
- **Usa el API server existente**: No es necesario implementar un API server separado.
- **Flexibilidad limitada**:
  - El almacenamiento está limitado a etcd.
  - Hereda el comportamiento del API server predeterminado.
  - Es difícil implementar lógica compleja de validación o conversión.
- **Extensión mediante webhooks**: Algunas funcionalidades pueden extenderse mediante validating webhooks, conversion webhooks, etc.

**Características de las Aggregated APIs:**
- **Implementación compleja**: Se debe desarrollar y desplegar un API server separado.
- **Alta flexibilidad**:
  - Puede usar backends de almacenamiento personalizados
  - Puede implementar lógica de negocio compleja
  - Puede implementar lógica personalizada de autenticación y autorización
  - Puede implementar cálculo de estado especial y lógica de conversión
- **Funcionalidad completa de API server**: Puede aprovechar todas las características de un Kubernetes API server estándar.

**Criterios de selección:**

| Criterio | Elegir CRD | Elegir Aggregated API |
|----------|------------|----------------------|
| Complejidad de implementación | Baja - Definición YAML simple | Alta - Requiere desarrollo de API server separado |
| Tiempo de desarrollo | Corto - Puede implementarse en minutos | Largo - Requiere desarrollo completo de API server |
| Mantenimiento | Fácil - Administrado por el API server existente | Difícil - Requiere mantener un service separado |
| Opciones de almacenamiento | Solo etcd | Posibles backends de almacenamiento personalizados |
| Lógica de negocio | Limitada - Implementar mediante controllers | Flexible - Puede implementarse directamente en el API server |
| Rendimiento | Generalmente bueno | Posible optimización personalizada |
| Casos de uso | Operaciones CRUD simples, patrones estándar | Comportamiento de API complejo, validación/conversión especial |

**Escenarios de ejemplo:**

Casos adecuados para CRDs:
- Administración simple de configuración de aplicaciones
- Operaciones CRUD básicas como requisitos principales
- Prototipado y desarrollo rápidos

Casos adecuados para Aggregated APIs:
- Integración con bases de datos externas
- Transformación y validación de datos complejas
- Necesidad de mecanismos especiales de autenticación
- APIs de alto rendimiento o de propósito especial

Problemas con las otras opciones:
- Las CRDs sí admiten versionado (A es incorrecta).
- Las CRDs sí admiten esquemas de validación mediante OpenAPI v3 Schema (B es incorrecta).
- Tanto las CRDs como las Aggregated APIs admiten recursos de alcance cluster y de alcance namespace (D es incorrecta).
</details>

## Preguntas de respuesta corta

1. Explica cómo definir custom resources usando CustomResourceDefinition (CRD) y cómo establecer reglas de validación para esos recursos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Cómo definir CustomResourceDefinition (CRD):**

CRD es un mecanismo que extiende la Kubernetes API para definir nuevos tipos de recursos. Cuando creas una CRD, se crea un nuevo endpoint de API RESTful, y puedes administrar ese recurso usando herramientas estándar como `kubectl`.

**1. Estructura básica de CRD:**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: <plural>.<group>  # e.g., crontabs.stable.example.com
spec:
  group: <api-group>      # e.g., stable.example.com
  names:
    kind: <kind-name>     # e.g., CronTab
    plural: <plural-name> # e.g., crontabs
    singular: <singular-name>  # e.g., crontab
    shortNames:           # optional
    - <short-name>        # e.g., ct
  scope: Namespaced       # or Cluster
  versions:
    - name: <version>     # e.g., v1
      served: true        # whether to serve via API server
      storage: true       # whether this is the storage version
      schema:
        openAPIV3Schema:
          # schema definition
```

**2. Establecer reglas de validación:**

Las reglas de validación para CRDs se establecen mediante el campo `openAPIV3Schema`. Este esquema sigue el formato OpenAPI v3 y define la estructura y los tipos de campos de los recursos.

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

**3. Características avanzadas de validación:**

OpenAPI v3 Schema proporciona varias características de validación:

- **Campos obligatorios**: Agrega nombres de campos al array `required`
  ```yaml
  required: ["fieldName1", "fieldName2"]
  ```

- **Tipos de datos**: Especifica tipos de datos usando el campo `type`
  ```yaml
  type: string | number | integer | boolean | array | object
  ```

- **Restricciones de cadenas**: Valida longitud y patrones de cadenas
  ```yaml
  minLength: 3
  maxLength: 64
  pattern: '^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
  ```

- **Restricciones numéricas**: Valida rangos numéricos
  ```yaml
  minimum: 0
  maximum: 100
  multipleOf: 5
  ```

- **Restricciones de arrays**: Valida longitud e ítems de arrays
  ```yaml
  minItems: 1
  maxItems: 10
  uniqueItems: true
  items:
    type: string
  ```

- **Valores enum**: Especifica la lista de valores permitidos
  ```yaml
  enum: ["value1", "value2", "value3"]
  ```

- **Valores predeterminados**: Especifica valores predeterminados para campos
  ```yaml
  default: "default-value"
  ```

- **Propiedades adicionales**: Controla si se permiten propiedades adicionales
  ```yaml
  additionalProperties: false
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

**5. Aplicar y usar CRD:**

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

**6. Probar reglas de validación:**

Crear un recurso con valores no válidos producirá errores de validación:

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

Este comando devolverá errores como:
```
Error from server (Invalid): error when creating "STDIN": admission webhook "validate-crontab.example.com" denied the request:
- spec.cronSpec: Invalid value: "invalid-cron-spec": does not match pattern '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
- spec.replicas: Invalid value: 20: must be less than or equal to 10
```

**7. Buenas prácticas:**

- Definiciones de esquema claras y detalladas
- Especificar explícitamente los campos obligatorios
- Proporcionar valores predeterminados adecuados
- Limitar patrones de cadenas y rangos numéricos
- Habilitar el subresource de estado
- Configurar columnas de impresión adicionales
- Establecer una estrategia de versionado
</details>

2. Explica los conceptos centrales del Kubernetes Operator Pattern y los métodos comunes para implementar operators.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Conceptos centrales del Kubernetes Operator Pattern:**

El operator pattern es un mecanismo de extensión de Kubernetes que codifica conocimiento operativo específico de la aplicación en software para administrar automáticamente aplicaciones complejas. Este patrón imita cómo un operador humano administra sistemas complejos.

**1. Conceptos centrales:**

- **Administración declarativa**: Los usuarios declaran el estado deseado, y el operator ajusta el estado actual al estado deseado.
- **Codificación de conocimiento de dominio**: Codifica conocimiento operativo y mejores prácticas para aplicaciones específicas.
- **Reconciliation Loop**: Observa continuamente el estado real y lo ajusta al estado deseado.
- **Custom Resources**: Se usan para almacenar configuración y estado específicos de la aplicación.
- **Controllers**: Observan cambios en custom resources y realizan las tareas necesarias.

**2. Funciones comunes de los Operators:**

- **Instalación y actualizaciones**: Desplegar componentes de aplicación y actualizar versiones
- **Recuperación automática**: Detectar fallas y realizar tareas de recuperación
- **Backup y restauración**: Automatizar procesos de backup y restauración de datos
- **Escalado**: Expansión y contracción automáticas según los requisitos de carga de trabajo
- **Administración de configuración**: Gestionar cambios de configuración específicos de la aplicación
- **Automatización de operaciones**: Automatizar tareas operativas rutinarias (por ejemplo, compactación de bases de datos, reconstrucción de índices)

**Métodos para implementar Operators:**

**1. Usar Operator SDK:**

[Operator SDK](https://sdk.operatorframework.io/) es parte del Operator Framework de Red Hat y es una herramienta que simplifica el desarrollo de operators.

```bash
# Install Operator SDK
curl -LO https://github.com/operator-framework/operator-sdk/releases/download/v1.25.0/operator-sdk_linux_amd64
chmod +x operator-sdk_linux_amd64
sudo mv operator-sdk_linux_amd64 /usr/local/bin/operator-sdk

# Create Go-based operator project
operator-sdk init --domain example.com --repo github.com/example/my-operator

# Create API
operator-sdk create api --group apps --version v1alpha1 --kind MyApp --resource --controller

# Create CRD
make manifests

# Build and deploy operator
make docker-build docker-push
make deploy
```

**2. Usar Kubebuilder:**

[Kubebuilder](https://book.kubebuilder.io/) es un framework desarrollado por Kubernetes SIG que proporciona herramientas para el desarrollo de controllers.

```bash
# Install Kubebuilder
curl -L https://go.kubebuilder.io/dl/latest/$(go env GOOS)/$(go env GOARCH) | tar -xz -C /tmp/
sudo mv /tmp/kubebuilder_*/bin/kubebuilder /usr/local/bin/

# Initialize project
kubebuilder init --domain example.com --repo github.com/example/my-operator

# Create API
kubebuilder create api --group apps --version v1alpha1 --kind MyApp

# Create CRD and deploy controller
make install
make deploy
```

**3. Implementación de Controller:**

El núcleo de un operator es la función de reconciliación. Esta función observa el estado actual de los custom resources y realiza las tareas necesarias.

```go
// Reconcile function example
func (r *MyAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := r.Log.WithValues("myapp", req.NamespacedName)

    // Get custom resource
    var myApp appsv1alpha1.MyApp
    if err := r.Get(ctx, req.NamespacedName, &myApp); err != nil {
        if errors.IsNotFound(err) {
            // Resource deleted - perform cleanup
            return ctrl.Result{}, nil
        }
        // Error occurred
        return ctrl.Result{}, err
    }

    // 1. Check if required resources exist
    deployment := &appsv1.Deployment{}
    err := r.Get(ctx, types.NamespacedName{Name: myApp.Name, Namespace: myApp.Namespace}, deployment)
    if errors.IsNotFound(err) {
        // Create deployment if it doesn't exist
        deployment = r.deploymentForMyApp(&myApp)
        log.Info("Creating a new Deployment", "Deployment.Namespace", deployment.Namespace, "Deployment.Name", deployment.Name)
        if err := r.Create(ctx, deployment); err != nil {
            log.Error(err, "Failed to create new Deployment")
            return ctrl.Result{}, err
        }
        // Deployment creation successful
        return ctrl.Result{Requeue: true}, nil
    } else if err != nil {
        log.Error(err, "Failed to get Deployment")
        return ctrl.Result{}, err
    }

    // 2. Check if deployment is in desired state
    size := myApp.Spec.Size
    if *deployment.Spec.Replicas != size {
        deployment.Spec.Replicas = &size
        if err := r.Update(ctx, deployment); err != nil {
            log.Error(err, "Failed to update Deployment")
            return ctrl.Result{}, err
        }
        // Deployment update successful
        return ctrl.Result{Requeue: true}, nil
    }

    // 3. Update status
    if myApp.Status.AvailableReplicas != deployment.Status.AvailableReplicas {
        myApp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
        if err := r.Status().Update(ctx, &myApp); err != nil {
            log.Error(err, "Failed to update MyApp status")
            return ctrl.Result{}, err
        }
    }

    return ctrl.Result{}, nil
}

// Deployment creation function
func (r *MyAppReconciler) deploymentForMyApp(m *appsv1alpha1.MyApp) *appsv1.Deployment {
    ls := labelsForMyApp(m.Name)
    replicas := m.Spec.Size

    dep := &appsv1.Deployment{
        ObjectMeta: metav1.ObjectMeta{
            Name:      m.Name,
            Namespace: m.Namespace,
        },
        Spec: appsv1.DeploymentSpec{
            Replicas: &replicas,
            Selector: &metav1.LabelSelector{
                MatchLabels: ls,
            },
            Template: corev1.PodTemplateSpec{
                ObjectMeta: metav1.ObjectMeta{
                    Labels: ls,
                },
                Spec: corev1.PodSpec{
                    Containers: []corev1.Container{{
                        Image: m.Spec.Image,
                        Name:  "myapp",
                        Ports: []corev1.ContainerPort{{
                            ContainerPort: 8080,
                            Name:          "http",
                        }},
                    }},
                },
            },
        },
    }

    // Set owner reference
    ctrl.SetControllerReference(m, dep, r.Scheme)
    return dep
}
```

**4. Custom Resource Definition:**

Define la API para custom resources administrados por el operator.

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

**5. Operators basados en Ansible o Helm:**

Operator SDK también admite el desarrollo de operators usando Ansible o Helm además de Go.

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

**6. Desplegar y probar Operators:**

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

El modelo de madurez de operator define los niveles de capacidad de los operators:

1. **Instalación básica**: Instalación y configuración de aplicaciones
2. **Actualizaciones sin interrupciones**: Actualizaciones automáticas entre versiones
3. **Ciclo de vida completo**: Backup, restauración, recuperación ante fallas, etc.
4. **Información profunda**: Auto-scaling, tuning, etc.
5. **Auto Pilot**: Optimización automática basada en monitoreo

**8. Buenas prácticas:**

- Implementar características de forma incremental (empezar con cosas simples)
- Manejo de errores y logging exhaustivos
- Garantizar idempotencia (mismo resultado para la misma entrada)
- Establecer owner references (jerarquía de recursos y garbage collection)
- Informar el progreso mediante actualizaciones de estado
- Escribir unit tests e integration tests
- Documentación clara
</details>

3. Explica los tipos de Admission Webhooks en Kubernetes y los casos de uso de cada uno.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Tipos y casos de uso de Kubernetes Admission Webhooks:**

Los admission webhooks son mecanismos que pueden interceptar y modificar o validar solicitudes antes de que el Kubernetes API server las almacene en almacenamiento persistente (etcd). Los admission webhooks se dividen principalmente en dos tipos: Mutating webhooks y Validating webhooks.

**1. Mutating Webhook:**

Los mutating webhooks pueden modificar objetos de solicitud que entran al API server. Estos webhooks se ejecutan antes de los validating webhooks.

**Características clave:**
- Pueden modificar objetos de solicitud
- Múltiples mutating webhooks se ejecutan en cadena
- Cada webhook recibe el objeto modificado por el webhook anterior

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
      name: sidecar-injector
      path: "/inject"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
```

**Casos de uso comunes:**

1. **Inyección de Sidecar Container:**
   - Inyección automática de proxy sidecar en service meshes como Istio y Linkerd
   - Agregar sidecars de logging y monitoreo
   - Ejemplo: el sidecar injector de Istio agrega automáticamente Envoy proxy containers cuando se crean pods

2. **Establecimiento de valores predeterminados:**
   - Configuración automática de resource requests y limits
   - Aplicación de valores predeterminados de security context
   - Adición automática de etiquetas y anotaciones
   - Ejemplo: establecer requests predeterminados de CPU y memoria para todos los pods

3. **Aplicación de políticas de imágenes:**
   - Modificar URLs de image registry
   - Convertir image tags a digests
   - Ejemplo: cambiar `nginx:latest` a `internal-registry.example.com/nginx:v1.19.0`

4. **Modificaciones de volúmenes:**
   - Agregar volume mounts predeterminados
   - Montaje automático de ConfigMap o Secret
   - Ejemplo: montaje automático del volumen de service account token para todos los pods

5. **Aplicación de Network Policies:**
   - Agregar configuraciones de red predeterminadas
   - Modificar configuración de DNS
   - Ejemplo: aplicar configuraciones DNS específicas a todos los pods en un namespace específico

**2. Validating Webhook:**

Los validating webhooks pueden validar solicitudes que entran al API server y permitirlas o denegarlas. Estos webhooks se ejecutan después de los mutating webhooks.

**Características clave:**
- No pueden modificar objetos de solicitud
- Solo pueden permitir o denegar solicitudes
- Múltiples validating webhooks se ejecutan en paralelo
- Todos los webhooks deben permitir la solicitud para que sea procesada

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
      name: pod-policy-validator
      path: "/validate"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE", "UPDATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
```

**Casos de uso comunes:**

1. **Aplicación de políticas de seguridad:**
   - Prohibir containers privilegiados
   - Prohibir la ejecución como usuario root
   - Restringir el uso de host network/PID/IPC
   - Ejemplo: denegar pods que se ejecutan en modo privilegiado

2. **Validación de restricciones de recursos:**
   - Hacer obligatorios resource requests y limits
   - Aplicar límites máximos de recursos
   - Exigir clases QoS
   - Ejemplo: denegar pods sin memory limits

3. **Validación de políticas de imágenes:**
   - Permitir solo registries aprobados
   - Prohibir el uso de la etiqueta latest
   - Verificar resultados de escaneo de vulnerabilidades
   - Ejemplo: permitir solo imágenes de registries oficiales

4. **Validación de etiquetas y anotaciones:**
   - Comprobar etiquetas obligatorias
   - Validar formatos de etiquetas
   - Ejemplo: hacer obligatorias las etiquetas `app` y `environment` para todos los pods

5. **Políticas basadas en namespace:**
   - Límites de recursos por namespace
   - Restricciones de características por namespace
   - Ejemplo: aplicar políticas más estrictas en namespaces de producción

**3. Métodos de implementación de Webhook:**

Los admission webhooks se implementan como services que proporcionan endpoints HTTPS. Estos services reciben solicitudes `AdmissionReview`, las procesan y devuelven `AdmissionResponse`.

**Ejemplo básico de implementación de Webhook Server (Go):**

```go
package main

import (
    "encoding/json"
    "io/ioutil"
    "net/http"

    admissionv1 "k8s.io/api/admission/v1"
    corev1 "k8s.io/api/core/v1"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/runtime"
    "k8s.io/apimachinery/pkg/runtime/serializer"
)

var (
    runtimeScheme = runtime.NewScheme()
    codecs        = serializer.NewCodecFactory(runtimeScheme)
    deserializer  = codecs.UniversalDeserializer()
)

// Mutating webhook handler
func mutateHandler(w http.ResponseWriter, r *http.Request) {
    body, err := ioutil.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "Failed to read request body", http.StatusBadRequest)
        return
    }

    // Decode AdmissionReview request
    admissionReview := admissionv1.AdmissionReview{}
    if _, _, err := deserializer.Decode(body, nil, &admissionReview); err != nil {
        http.Error(w, "Failed to decode request", http.StatusBadRequest)
        return
    }

    // Decode pod object
    pod := corev1.Pod{}
    if err := json.Unmarshal(admissionReview.Request.Object.Raw, &pod); err != nil {
        http.Error(w, "Failed to decode pod", http.StatusBadRequest)
        return
    }

    // Create patch (add sidecar container)
    patch := []map[string]interface{}{
        {
            "op": "add",
            "path": "/spec/containers/-",
            "value": map[string]interface{}{
                "name": "sidecar",
                "image": "sidecar-image:latest",
                "resources": map[string]interface{}{
                    "limits": map[string]interface{}{
                        "cpu": "100m",
                        "memory": "100Mi",
                    },
                    "requests": map[string]interface{}{
                        "cpu": "50m",
                        "memory": "50Mi",
                    },
                },
            },
        },
    }

    // Convert patch to JSON
    patchBytes, err := json.Marshal(patch)
    if err != nil {
        http.Error(w, "Failed to marshal patch", http.StatusInternalServerError)
        return
    }

    // Create response
    admissionResponse := admissionv1.AdmissionResponse{
        UID:     admissionReview.Request.UID,
        Allowed: true,
        Patch:   patchBytes,
        PatchType: func() *admissionv1.PatchType {
            pt := admissionv1.PatchTypeJSONPatch
            return &pt
        }(),
    }

    // Send response
    admissionReview.Response = &admissionResponse
    resp, err := json.Marshal(admissionReview)
    if err != nil {
        http.Error(w, "Failed to marshal response", http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}

// Validating webhook handler
func validateHandler(w http.ResponseWriter, r *http.Request) {
    body, err := ioutil.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "Failed to read request body", http.StatusBadRequest)
        return
    }

    // Decode AdmissionReview request
    admissionReview := admissionv1.AdmissionReview{}
    if _, _, err := deserializer.Decode(body, nil, &admissionReview); err != nil {
        http.Error(w, "Failed to decode request", http.StatusBadRequest)
        return
    }

    // Decode pod object
    pod := corev1.Pod{}
    if err := json.Unmarshal(admissionReview.Request.Object.Raw, &pod); err != nil {
        http.Error(w, "Failed to decode pod", http.StatusBadRequest)
        return
    }

    // Validation logic
    allowed := true
    var message string

    // Check for privileged containers
    for _, container := range pod.Spec.Containers {
        if container.SecurityContext != nil && container.SecurityContext.Privileged != nil && *container.SecurityContext.Privileged {
            allowed = false
            message = "Privileged containers are not allowed"
            break
        }
    }

    // Create response
    admissionResponse := admissionv1.AdmissionResponse{
        UID:     admissionReview.Request.UID,
        Allowed: allowed,
    }

    if !allowed {
        admissionResponse.Result = &metav1.Status{
            Message: message,
            Status:  "Failure",
            Reason:  metav1.StatusReasonForbidden,
            Code:    403,
        }
    }

    // Send response
    admissionReview.Response = &admissionResponse
    resp, err := json.Marshal(admissionReview)
    if err != nil {
        http.Error(w, "Failed to marshal response", http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}

func main() {
    http.HandleFunc("/mutate", mutateHandler)
    http.HandleFunc("/validate", validateHandler)

    fmt.Println("Starting webhook server on :8443")
    http.ListenAndServeTLS(":8443", "tls.crt", "tls.key", nil)
}
```

**4. Despliegue y configuración de Webhook:**

Los webhook servers normalmente se despliegan dentro del Kubernetes cluster y requieren un service y certificados TLS.

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
        image: webhook-server:latest
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

**5. Buenas prácticas:**

- **Optimización de rendimiento**: Los webhooks están en la ruta de solicitudes del API server, por lo que deben responder rápidamente.
- **Manejo de errores**: Considera el comportamiento cuando falla el webhook server y configura `failurePolicy` adecuadamente.
- **Limitación de alcance**: Aplica webhooks solo a los recursos y operaciones necesarios.
- **Pruebas**: Prueba exhaustivamente el comportamiento del webhook en varios escenarios.
- **Monitoreo**: Monitorea el rendimiento y los errores del webhook server.
- **Administración de versiones**: Admite múltiples versiones de AdmissionReview en preparación para cambios de versión de API.
</details>

## Preguntas prácticas

1. Escribe una CustomResourceDefinition (CRD) que cumpla los siguientes requisitos:
   - API Group: webapp.example.com
   - Version: v1
   - Kind: WebApp
   - Scope: Namespaced
   - Campos obligatorios: spec.image, spec.replicas
   - Reglas de validación: replicas debe ser un entero entre 1 y 10
   - Habilitar el subresource de estado

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
   - API Group: `webapp.example.com`
   - Version: `v1`
   - Kind: `WebApp`
   - Scope: `Namespaced`

2. **Validación de esquema**:
   - El campo `spec` es obligatorio.
   - `spec.image` y `spec.replicas` son campos obligatorios.
   - `spec.replicas` debe ser un entero entre 1 y 10.
   - `spec.port` es un campo opcional con un valor predeterminado de 80.
   - `spec.env` es un campo opcional que define un array de variables de entorno.

3. **Status Subresource**:
   - El subresource `status` está habilitado para que los controllers puedan actualizar el estado.
   - Se definen los campos `status.availableReplicas` y `status.phase`.

4. **Additional Printer Columns**:
   - Al ejecutar `kubectl get webapps`, se muestran las columnas Replicas, Image y Age.

5. **Configuración de nombres**:
   - Plural: `webapps`
   - Singular: `webapp`
   - Kind: `WebApp`
   - Nombre corto: `wa`

Puedes crear custom resources como este usando esta CRD:

```yaml
apiVersion: webapp.example.com/v1
kind: WebApp
metadata:
  name: my-webapp
  namespace: default
spec:
  image: nginx:1.19
  replicas: 3
  port: 8080
  env:
    - name: ENV_VAR1
      value: "value1"
    - name: ENV_VAR2
      value: "value2"
```

Los controllers pueden observar este recurso y actualizar el estado:

```yaml
status:
  availableReplicas: 3
  phase: Running
```
</details>

2. Escribe una configuración de Mutating Admission Webhook que cumpla los siguientes requisitos:
   - Agregar sidecar container a todas las solicitudes de creación de pod
   - Aplicar solo a un namespace específico (monitoring)
   - Webhook service: webhook-service.webhook-system.svc
   - Path: /mutate

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
      monitoring-injection: enabled
  admissionReviewVersions: ["v1", "v1beta1"]
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
    monitoring-injection: enabled
```

Esta configuración tiene las siguientes características:

1. **Configuración de Webhook**:
   - Nombre: `sidecar-injector`
   - Webhook service: `webhook-service.webhook-system.svc`
   - Path: `/mutate`

2. **Alcance**:
   - API Group: `""` (core API group)
   - API Version: `v1`
   - Operación: `CREATE` (aplicar solo en la creación de pod)
   - Recurso: `pods`
   - Scope: `Namespaced`

3. **Namespace Selector**:
   - Aplicar solo a namespaces con la etiqueta `monitoring-injection: enabled`
   - Agregar esta etiqueta al namespace `monitoring`

4. **Configuraciones adicionales**:
   - `admissionReviewVersions`: Versiones de API AdmissionReview admitidas
   - `sideEffects`: Sin efectos secundarios del webhook
   - `timeoutSeconds`: Tiempo de espera para la respuesta del webhook
   - `failurePolicy`: Denegar solicitudes ante falla del webhook

El webhook server debe implementar una lógica como esta:

```go
func mutateHandler(w http.ResponseWriter, r *http.Request) {
    // Decode request
    body, _ := ioutil.ReadAll(r.Body)
    admissionReview := admissionv1.AdmissionReview{}
    deserializer.Decode(body, nil, &admissionReview)

    // Decode pod object
    pod := corev1.Pod{}
    json.Unmarshal(admissionReview.Request.Object.Raw, &pod)

    // Define sidecar container
    sidecarContainer := corev1.Container{
        Name:  "monitoring-sidecar",
        Image: "monitoring-agent:latest",
        Resources: corev1.ResourceRequirements{
            Limits: corev1.ResourceList{
                corev1.ResourceCPU:    resource.MustParse("100m"),
                corev1.ResourceMemory: resource.MustParse("100Mi"),
            },
            Requests: corev1.ResourceList{
                corev1.ResourceCPU:    resource.MustParse("50m"),
                corev1.ResourceMemory: resource.MustParse("50Mi"),
            },
        },
        VolumeMounts: []corev1.VolumeMount{
            {
                Name:      "shared-data",
                MountPath: "/var/monitoring",
            },
        },
    }

    // Create patch
    patch := []map[string]interface{}{
        {
            "op":    "add",
            "path":  "/spec/containers/-",
            "value": sidecarContainer,
        },
        {
            "op":   "add",
            "path": "/spec/volumes/-",
            "value": map[string]interface{}{
                "name": "shared-data",
                "emptyDir": map[string]interface{}{},
            },
        },
    }

    // Convert patch to JSON
    patchBytes, _ := json.Marshal(patch)

    // Create response
    admissionResponse := admissionv1.AdmissionResponse{
        UID:       admissionReview.Request.UID,
        Allowed:   true,
        Patch:     patchBytes,
        PatchType: func() *admissionv1.PatchType {
            pt := admissionv1.PatchTypeJSONPatch
            return &pt
        }(),
    }

    // Send response
    admissionReview.Response = &admissionResponse
    resp, _ := json.Marshal(admissionReview)
    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}
```

Este webhook agrega automáticamente un monitoring sidecar container a todos los pods creados en el namespace `monitoring`. El sidecar container usa una imagen de monitoring agent y monta un volumen compartido para compartir datos con el container principal.
</details>
