# Extending Kubernetes Quiz

This quiz tests your conceptual and practical knowledge about Kubernetes extension mechanisms. It covers topics such as Custom Resource Definitions (CRD), custom controllers, API extensions, webhooks, and the operator pattern.

## Multiple Choice Questions

1. What is the most common way to define custom resources in Kubernetes?
   - A) Define resource schema using ConfigMap
   - B) Create a CustomResourceDefinition (CRD)
   - C) Directly modify API server code
   - D) Use the Aggregation Layer

<details>
<summary>Show Answer</summary>

**Answer: B) Create a CustomResourceDefinition (CRD)**

**Explanation:**
The most common way to define custom resources in Kubernetes is to create a CustomResourceDefinition (CRD). CRD is a mechanism that allows you to extend the Kubernetes API by defining new resource types.

Using CRDs provides the following benefits:
- You can add new resource types without modifying the existing Kubernetes API server.
- You can manage custom resources using standard Kubernetes tools like `kubectl`.
- You can leverage features such as resource validation, versioning, and status subresources.

CRD example:
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

Issues with other options:
- ConfigMaps are used to store configuration data and are not suitable for API extensions.
- Directly modifying API server code is complex, difficult to maintain, and can cause issues during upgrades.
- The Aggregation Layer is another way to define custom resources, but it's more complex than CRDs since it requires implementing a separate API server.
</details>

2. What is the main purpose of a Kubernetes Operator?
   - A) Optimize resource usage of cluster nodes
   - B) Encode operational knowledge of complex applications into automated software
   - C) Improve Kubernetes API server performance
   - D) Extend cluster networking functionality

<details>
<summary>Show Answer</summary>

**Answer: B) Encode operational knowledge of complex applications into automated software**

**Explanation:**
The main purpose of a Kubernetes Operator is to encode operational knowledge of complex applications into automated software. The operator pattern is a software implementation of how a human operator manages complex applications.

Key characteristics of operators:
- Combines custom resources with custom controllers to implement application-specific logic.
- Automates operational tasks such as application deployment, upgrades, backup, recovery, and scaling.
- Continuously monitors application state and adjusts to the desired state.
- Codifies domain knowledge to enable declarative management of complex applications.

Common use cases for operators:
- Automated management of databases (e.g., PostgreSQL, MySQL, MongoDB)
- Deployment and configuration of messaging systems (e.g., Kafka, RabbitMQ)
- Setup and maintenance of monitoring systems (e.g., Prometheus)
- Management of service meshes (e.g., Istio)

Operator example - Prometheus Operator:
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

With this simple declarative configuration, the Prometheus Operator automatically handles complex tasks such as:
- Deploying Prometheus servers
- Creating and managing configuration files
- Automatic discovery of service monitoring targets
- High availability setup
- Storage management
- Upgrade coordination

Other options are not the main purpose of operators:
- Resource usage optimization is the role of HPA (Horizontal Pod Autoscaler), VPA (Vertical Pod Autoscaler), etc.
- Improving API server performance is not the main purpose of operators.
- Extending networking functionality is the role of CNI plugins or service meshes.
</details>

3. What is the main function of Admission Webhooks in Kubernetes?
   - A) Handle authentication for API server
   - B) Intercept resource creation or modification requests to validate or modify them
   - C) Monitor cluster events and send alerts
   - D) Provide APIs for integration with external systems

<details>
<summary>Show Answer</summary>

**Answer: B) Intercept resource creation or modification requests to validate or modify them**

**Explanation:**
The main function of Admission Webhooks in Kubernetes is to intercept resource creation or modification requests to validate or modify them. Admission webhooks provide a mechanism to intercept requests before the Kubernetes API server stores them in persistent storage (etcd).

Two types of admission webhooks:

1. **Validating Webhook**:
   - Validates resource create, update, and delete requests.
   - Can allow or deny requests but cannot modify them.
   - Used for policy enforcement, security checks, configuration validation, etc.

2. **Mutating Webhook**:
   - Can validate and modify resource create and update requests.
   - Used for setting defaults, injecting sidecar containers, adding labels, etc.
   - Runs before validating webhooks.

Admission webhook configuration example:
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

Common use cases for admission webhooks:
- Enforcing security policies (e.g., prohibiting privileged containers)
- Enforcing resource requests and limits
- Automatic injection of sidecar containers (e.g., Istio)
- Automatic addition of labels and annotations
- Restricting image registries
- Applying namespace-based policies

Issues with other options:
- Handling authentication for API server is the role of Authentication Plugins.
- Monitoring cluster events and sending alerts is the role of event listeners or monitoring tools.
- Providing APIs for integration with external systems is a general purpose of API extensions, but not the main function of admission webhooks.
</details>

4. What is the main purpose of the Aggregation Layer in the Kubernetes API server?
   - A) Optimize API server performance
   - B) Consolidate multiple API servers into a single API server
   - C) Integrate custom API servers into the main API server to extend the API
   - D) Provide service discovery within the cluster

<details>
<summary>Show Answer</summary>

**Answer: C) Integrate custom API servers into the main API server to extend the API**

**Explanation:**
The main purpose of the Aggregation Layer in the Kubernetes API server is to integrate custom API servers into the main API server to extend the API. This provides another way to extend the Kubernetes API, offering more powerful features than CRDs, though more complex.

Key characteristics of the Aggregation Layer:
- Integrates custom API servers into the URL space of the Kubernetes API server.
- Custom API servers can have their own storage, business logic, API versions, etc.
- The main API server proxies requests to the appropriate custom API server.
- Authentication and authorization are handled by the main API server.

Cases where the Aggregation Layer is used:
- When complex validation logic is needed
- When a custom storage backend is required
- When different behavior from existing APIs is needed
- When resource transformation or special state calculation is required

APIService resource example:
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

This configuration routes requests for the `metrics.k8s.io/v1alpha1` API group to the `metrics-server` service in the `kube-system` namespace.

Real examples using the Aggregation Layer:
- metrics-server: Provides node and pod resource usage metrics
- service-catalog: Integration with external service brokers
- custom-metrics-apiserver: Provides custom metrics for HPA

Issues with other options:
- The Aggregation Layer is not for optimizing API server performance.
- Consolidating multiple API servers into one is not an accurate description. The Aggregation Layer integrates multiple API servers into a single URL space, but the servers run separately.
- The Aggregation Layer does not provide service discovery. That is the role of Kubernetes Services.
</details>

5. What is the main role of a Custom Controller in Kubernetes?
   - A) Monitor resource usage of cluster nodes
   - B) Observe the state of custom resources and reconcile to the desired state
   - C) Handle authentication and authorization for API server requests
   - D) Manage cluster networking

<details>
<summary>Show Answer</summary>

**Answer: B) Observe the state of custom resources and reconcile to the desired state**

**Explanation:**
The main role of a Custom Controller in Kubernetes is to observe the state of custom resources and reconcile to the desired state. Controllers implement the "reconciliation loop," a core operational pattern in Kubernetes, to continuously adjust the system's actual state to the desired state.

Key characteristics of custom controllers:
- Watch specific resource types (typically custom resources defined via CRDs).
- React to resource change events and execute business logic.
- Perform tasks to adjust the actual state of resources to the desired state.
- Update the status field of resources to reflect the current state.

Common components of custom controllers:
1. **Informer**: Watches the Kubernetes API server and receives resource change events.
2. **Work Queue**: Stores and manages events to be processed.
3. **Reconciler**: Compares the desired state and actual state of resources and performs necessary tasks.
4. **Client**: Interacts with the Kubernetes API to create, update, and delete resources.

Custom controller example - simple reconcile function:
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

Common use cases for custom controllers:
- Automating complex application deployment and management
- Integration with external systems (e.g., cloud resource provisioning)
- Automating backup and recovery processes
- Implementing advanced deployment strategies (e.g., canary deployments, blue-green deployments)

Issues with other options:
- Monitoring resource usage of cluster nodes is the role of metrics-server or monitoring tools like Prometheus.
- Handling authentication and authorization for API server requests is the role of authentication and authorization plugins.
- Managing cluster networking is the role of CNI plugins or network controllers.
</details>

6. What format is used to define validation schemas for CRDs (CustomResourceDefinitions) in Kubernetes?
   - A) JSON Schema
   - B) XML Schema
   - C) OpenAPI v3 Schema
   - D) GraphQL Schema

<details>
<summary>Show Answer</summary>

**Answer: C) OpenAPI v3 Schema**

**Explanation:**
The format used to define validation schemas for CRDs (CustomResourceDefinitions) in Kubernetes is OpenAPI v3 Schema. This schema defines the structure and field types of custom resources and is used by the API server to validate resource creation and update requests.

Example of CRD validation schema:
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

In this example, the `openAPIV3Schema` field defines the following validation rules:
- The `spec` field is required.
- Within `spec`, the `cronSpec` and `image` fields are required.
- `cronSpec` is a string and must follow the cron expression pattern.
- `image` is a string.
- `replicas` is an integer and must be between 1 and 10.

OpenAPI v3 Schema provides various validation features:
- Specifying required fields
- Data type validation (string, number, boolean, object, array, etc.)
- String pattern validation (regular expressions)
- Number range validation (minimum, maximum)
- Array length validation
- Enum value validation
- Nested object structure definition

Issues with other options:
- JSON Schema is the basis for OpenAPI, but Kubernetes specifically uses OpenAPI v3 Schema.
- XML Schema is not used in the Kubernetes API.
- GraphQL Schema is used for GraphQL APIs but not for the Kubernetes API.
</details>

7. What is the main benefit of enabling the status subresource for custom resources in Kubernetes?
   - A) Faster resource creation
   - B) Separation of spec and status updates and RBAC control
   - C) Automatic backup and recovery features
   - D) Simplified resource version management

<details>
<summary>Show Answer</summary>

**Answer: B) Separation of spec and status updates and RBAC control**

**Explanation:**
The main benefit of enabling the status subresource for custom resources in Kubernetes is the separation of spec and status updates and the ability to control access through RBAC (Role-Based Access Control).

Benefits of enabling the status subresource:

1. **Separation of Concerns**:
   - The `spec` field defines the desired state specified by users.
   - The `status` field reports the actual state observed by controllers.
   - This separation clarifies the responsibilities of users and controllers.

2. **RBAC Control**:
   - Status update permissions can be granted only to controllers while giving regular users read-only permissions.
   - This prevents unauthorized modification of status information.

3. **Conflict Prevention**:
   - Even if a user updates `spec` while a controller updates `status`, no conflict occurs.
   - This is because the two fields are updated via separate API requests.

4. **Scale Subresource Support**:
   - Enabling the status subresource also allows enabling the scale subresource.
   - This enables the use of standard Kubernetes scaling tools like HPA (Horizontal Pod Autoscaler).

Example of enabling status subresource in CRD:
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

Example of status update from controller:
```go
// Update status only
statusUpdate := &v1alpha1.MyResource{}
statusUpdate.Name = instance.Name
statusUpdate.Namespace = instance.Namespace
statusUpdate.Status.Phase = "Running"
statusUpdate.Status.Message = "Resource is running"

_, err = c.clientset.MyGroup().MyResources(namespace).UpdateStatus(statusUpdate)
```

Issues with other options:
- The status subresource does not improve resource creation speed.
- It does not provide automatic backup and recovery features.
- Resource version management is handled through the CRD's `versions` field and is not directly related to the status subresource.
</details>

8. What is the main purpose of Webhook Conversion in Kubernetes?
   - A) Route API requests to external services
   - B) Handle conversion between different versions of custom resources
   - C) Convert authentication tokens to different formats
   - D) Convert log data to structured formats

<details>
<summary>Show Answer</summary>

**Answer: B) Handle conversion between different versions of custom resources**

**Explanation:**
The main purpose of Webhook Conversion in Kubernetes is to handle conversion between different versions of custom resources. This feature supports multiple versions of CRDs and enables smooth migration between versions.

Key characteristics of webhook conversion:

1. **Multi-Version Support**:
   - CRDs can support multiple API versions simultaneously (e.g., v1alpha1, v1beta1, v1).
   - Each version can have different schemas and fields.

2. **Automatic Conversion**:
   - The API server automatically handles conversion between the version requested by the client and the storage version.
   - The conversion webhook provides custom conversion logic in this process.

3. **Storage Version Independence**:
   - Even if the storage version changes, clients using previous versions can continue to work.
   - The webhook handles bidirectional conversion between old and new versions.

Example of conversion webhook configuration in CRD:
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

Example of conversion webhook server implementation:
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

Issues with other options:
- Routing API requests to external services is the role of API aggregation.
- Converting authentication tokens is the role of authentication plugins.
- Converting log data is the role of logging systems.
</details>

9. Which of the following is NOT a framework that helps develop Kubernetes operators?
   - A) Operator Framework
   - B) Kubebuilder
   - C) Metacontroller
   - D) Kubespray

<details>
<summary>Show Answer</summary>

**Answer: D) Kubespray**

**Explanation:**
Kubespray is not a framework that helps develop Kubernetes operators. Kubespray is a tool for deploying and managing Kubernetes clusters using Ansible playbooks. It focuses on cluster installation and configuration and is not related to operator development.

Actual frameworks for Kubernetes operator development are:

1. **Operator Framework**:
   - Operator development toolkit developed by Red Hat
   - Key components:
     - Operator SDK: Operator scaffolding and development tools
     - Operator Lifecycle Manager (OLM): Operator installation and upgrade management
     - Operator Metering: Operator usage reporting
   - Supports Go, Ansible, and Helm-based operator development

2. **Kubebuilder**:
   - Framework developed by Kubernetes SIG (Special Interest Group)
   - SDK for developing controllers in Go
   - Provides code generation, CRD management, and testing tools
   - Based on controller-runtime library

3. **Metacontroller**:
   - Lightweight webhook-based operator framework
   - Can implement controller logic in various languages
   - Declarative controller definition
   - Suitable for quickly developing simple controllers

Feature comparison of each framework:

| Framework | Primary Language | Complexity | Features |
|-----------|------------------|------------|----------|
| Operator Framework | Go, Ansible, Helm | Medium-High | Comprehensive toolkit, various development options |
| Kubebuilder | Go | Medium | Standardized patterns, code generation tools |
| Metacontroller | Language-independent | Low | Webhook-based, simple implementation |

Operator development example (using Kubebuilder):
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

Explanations of other options:
- Operator Framework is Red Hat's comprehensive operator development toolkit.
- Kubebuilder is a Go-based controller development framework developed by Kubernetes SIG.
- Metacontroller is a lightweight webhook-based operator framework.
</details>

10. What is the main difference between Custom Resource Definitions (CRD) and Aggregated APIs in Kubernetes?
    - A) CRDs do not support versioning, but Aggregated APIs do
    - B) CRDs do not support validation schemas, but Aggregated APIs do
    - C) CRDs are simple to implement but have limited flexibility, while Aggregated APIs are complex to implement but provide more flexibility
    - D) CRDs only support cluster-scoped resources, and Aggregated APIs only support namespace-scoped resources

<details>
<summary>Show Answer</summary>

**Answer: C) CRDs are simple to implement but have limited flexibility, while Aggregated APIs are complex to implement but provide more flexibility**

**Explanation:**
The main difference between Custom Resource Definitions (CRD) and Aggregated APIs in Kubernetes is the balance between implementation complexity and flexibility. CRDs are simple to implement but have limited flexibility, while Aggregated APIs are complex to implement but provide more flexibility.

**Characteristics of CRDs (CustomResourceDefinitions):**
- **Simple implementation**: You can define new API resources with a single YAML file.
- **Uses existing API server**: No need to implement a separate API server.
- **Limited flexibility**:
  - Storage is limited to etcd.
  - Inherits the behavior of the default API server.
  - Difficult to implement complex validation or conversion logic.
- **Extension through webhooks**: Some functionality can be extended through validating webhooks, conversion webhooks, etc.

**Characteristics of Aggregated APIs:**
- **Complex implementation**: Must develop and deploy a separate API server.
- **High flexibility**:
  - Can use custom storage backends
  - Can implement complex business logic
  - Can implement custom authentication and authorization logic
  - Can implement special state calculation and conversion logic
- **Full API server functionality**: Can leverage all features of a standard Kubernetes API server.

**Selection Criteria:**

| Criteria | Choose CRD | Choose Aggregated API |
|----------|------------|----------------------|
| Implementation complexity | Low - Simple YAML definition | High - Requires separate API server development |
| Development time | Short - Can implement in minutes | Long - Requires complete API server development |
| Maintenance | Easy - Managed by existing API server | Difficult - Requires maintaining separate service |
| Storage options | etcd only | Custom storage backends possible |
| Business logic | Limited - Implement via controllers | Flexible - Can implement directly in API server |
| Performance | Generally good | Custom optimization possible |
| Use cases | Simple CRUD operations, standard patterns | Complex API behavior, special validation/conversion |

**Example Scenarios:**

Suitable cases for CRDs:
- Simple application configuration management
- Basic CRUD operations as main requirements
- Rapid prototyping and development

Suitable cases for Aggregated APIs:
- Integration with external databases
- Complex data transformation and validation
- Special authentication mechanisms needed
- High-performance or special-purpose APIs

Issues with other options:
- CRDs do support versioning (A is incorrect).
- CRDs do support validation schemas through OpenAPI v3 Schema (B is incorrect).
- Both CRDs and Aggregated APIs support cluster-scoped and namespace-scoped resources (D is incorrect).
</details>

## Short Answer Questions

1. Explain how to define custom resources using CustomResourceDefinition (CRD) and how to set validation rules for those resources.

<details>
<summary>Show Answer</summary>

**Answer:**

**How to Define CustomResourceDefinition (CRD):**

CRD is a mechanism that extends the Kubernetes API to define new resource types. When you create a CRD, a new RESTful API endpoint is created, and you can manage that resource using standard tools like `kubectl`.

**1. Basic CRD Structure:**

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

**2. Setting Validation Rules:**

Validation rules for CRDs are set through the `openAPIV3Schema` field. This schema follows OpenAPI v3 format and defines the structure and field types of resources.

**Basic Validation Rules Example:**

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

**3. Advanced Validation Features:**

OpenAPI v3 Schema provides various validation features:

- **Required fields**: Add field names to the `required` array
  ```yaml
  required: ["fieldName1", "fieldName2"]
  ```

- **Data types**: Specify data types using the `type` field
  ```yaml
  type: string | number | integer | boolean | array | object
  ```

- **String constraints**: Validate string length and patterns
  ```yaml
  minLength: 3
  maxLength: 64
  pattern: '^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
  ```

- **Number constraints**: Validate number ranges
  ```yaml
  minimum: 0
  maximum: 100
  multipleOf: 5
  ```

- **Array constraints**: Validate array length and items
  ```yaml
  minItems: 1
  maxItems: 10
  uniqueItems: true
  items:
    type: string
  ```

- **Enum values**: Specify allowed value list
  ```yaml
  enum: ["value1", "value2", "value3"]
  ```

- **Default values**: Specify default values for fields
  ```yaml
  default: "default-value"
  ```

- **Additional properties**: Control whether additional properties are allowed
  ```yaml
  additionalProperties: false
  ```

**4. Complete CRD Example:**

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

**5. Applying and Using CRD:**

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

**6. Testing Validation Rules:**

Creating a resource with invalid values will result in validation errors:

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

This command will return errors like:
```
Error from server (Invalid): error when creating "STDIN": admission webhook "validate-crontab.example.com" denied the request:
- spec.cronSpec: Invalid value: "invalid-cron-spec": does not match pattern '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
- spec.replicas: Invalid value: 20: must be less than or equal to 10
```

**7. Best Practices:**

- Clear and detailed schema definitions
- Explicitly specify required fields
- Provide appropriate default values
- Limit string patterns and number ranges
- Enable status subresource
- Configure additional printer columns
- Establish versioning strategy
</details>

2. Explain the core concepts of the Kubernetes Operator Pattern and the common methods for implementing operators.

<details>
<summary>Show Answer</summary>

**Answer:**

**Core Concepts of the Kubernetes Operator Pattern:**

The operator pattern is a Kubernetes extension mechanism that encodes application-specific operational knowledge into software to automatically manage complex applications. This pattern mimics how a human operator manages complex systems.

**1. Core Concepts:**

- **Declarative Management**: Users declare the desired state, and the operator adjusts the current state to the desired state.
- **Encoding Domain Knowledge**: Codifies operational knowledge and best practices for specific applications.
- **Reconciliation Loop**: Continuously observes actual state and adjusts to desired state.
- **Custom Resources**: Used to store application-specific configuration and state.
- **Controllers**: Watch changes to custom resources and perform necessary tasks.

**2. Common Functions of Operators:**

- **Installation and Upgrades**: Deploy application components and upgrade versions
- **Automatic Recovery**: Detect failures and perform recovery tasks
- **Backup and Restore**: Automate data backup and restore processes
- **Scaling**: Automatic expansion and contraction based on workload requirements
- **Configuration Management**: Handle application-specific configuration changes
- **Operations Automation**: Automate routine operational tasks (e.g., database compaction, index rebuilding)

**Methods for Implementing Operators:**

**1. Using Operator SDK:**

[Operator SDK](https://sdk.operatorframework.io/) is part of Red Hat's Operator Framework and is a tool that simplifies operator development.

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

**2. Using Kubebuilder:**

[Kubebuilder](https://book.kubebuilder.io/) is a framework developed by Kubernetes SIG that provides tools for controller development.

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

**3. Controller Implementation:**

The core of an operator is the reconciliation function. This function observes the current state of custom resources and performs necessary tasks.

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

Define the API for custom resources managed by the operator.

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

**5. Ansible or Helm-Based Operators:**

Operator SDK also supports operator development using Ansible or Helm in addition to Go.

**Ansible-based operator:**
```bash
# Create Ansible-based operator
operator-sdk init --plugins=ansible --domain example.com
operator-sdk create api --group apps --version v1alpha1 --kind MyApp --generate-role

# Edit roles/myapp/tasks/main.yml
```

**Helm-based operator:**
```bash
# Create Helm-based operator
operator-sdk init --plugins=helm --domain example.com --helm-chart=<chart-name>
```

**6. Deploying and Testing Operators:**

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

**7. Operator Maturity Levels:**

The operator maturity model defines the capability levels of operators:

1. **Basic Install**: Application installation and configuration
2. **Seamless Upgrades**: Automatic upgrades between versions
3. **Full Lifecycle**: Backup, restore, failure recovery, etc.
4. **Deep Insights**: Auto-scaling, tuning, etc.
5. **Auto Pilot**: Monitoring-based automatic optimization

**8. Best Practices:**

- Implement features incrementally (start with simple things)
- Thorough error handling and logging
- Ensure idempotency (same result for same input)
- Set owner references (resource hierarchy and garbage collection)
- Report progress through status updates
- Write unit tests and integration tests
- Clear documentation
</details>

3. Explain the types of Admission Webhooks in Kubernetes and the use cases for each.

<details>
<summary>Show Answer</summary>

**Answer:**

**Types and Use Cases of Kubernetes Admission Webhooks:**

Admission webhooks are mechanisms that can intercept and modify or validate requests before the Kubernetes API server stores them in persistent storage (etcd). Admission webhooks are broadly divided into two types: Mutating webhooks and Validating webhooks.

**1. Mutating Webhook:**

Mutating webhooks can modify request objects coming into the API server. These webhooks run before validating webhooks.

**Key Characteristics:**
- Can modify request objects
- Multiple mutating webhooks run in a chain
- Each webhook receives the object modified by the previous webhook

**Configuration Example:**
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

**Common Use Cases:**

1. **Sidecar Container Injection:**
   - Automatic proxy sidecar injection in service meshes like Istio and Linkerd
   - Adding logging and monitoring sidecars
   - Example: Istio's sidecar injector automatically adds Envoy proxy containers when pods are created

2. **Setting Defaults:**
   - Automatic resource requests and limits setting
   - Applying security context defaults
   - Automatic addition of labels and annotations
   - Example: Setting default CPU and memory requests for all pods

3. **Applying Image Policies:**
   - Modifying image registry URLs
   - Converting image tags to digests
   - Example: Changing `nginx:latest` to `internal-registry.example.com/nginx:v1.19.0`

4. **Volume Modifications:**
   - Adding default volume mounts
   - Automatic ConfigMap or Secret mounting
   - Example: Automatic service account token volume mounting for all pods

5. **Applying Network Policies:**
   - Adding default network settings
   - Modifying DNS configuration
   - Example: Applying specific DNS settings to all pods in a specific namespace

**2. Validating Webhook:**

Validating webhooks can validate requests coming into the API server and allow or deny them. These webhooks run after mutating webhooks.

**Key Characteristics:**
- Cannot modify request objects
- Can only allow or deny requests
- Multiple validating webhooks run in parallel
- All webhooks must allow the request for it to be processed

**Configuration Example:**
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

**Common Use Cases:**

1. **Enforcing Security Policies:**
   - Prohibiting privileged containers
   - Prohibiting root user execution
   - Restricting host network/PID/IPC usage
   - Example: Denying pods running in privileged mode

2. **Validating Resource Constraints:**
   - Making resource requests and limits mandatory
   - Applying resource caps
   - Enforcing QoS classes
   - Example: Denying pods without memory limits

3. **Validating Image Policies:**
   - Allowing only approved registries
   - Prohibiting latest tag usage
   - Verifying vulnerability scan results
   - Example: Allowing only images from official registries

4. **Validating Labels and Annotations:**
   - Checking required labels
   - Validating label formats
   - Example: Making `app` and `environment` labels mandatory for all pods

5. **Namespace-Based Policies:**
   - Per-namespace resource limits
   - Per-namespace feature restrictions
   - Example: Applying stricter policies in production namespaces

**3. Webhook Implementation Methods:**

Admission webhooks are implemented as services that provide HTTPS endpoints. These services receive `AdmissionReview` requests, process them, and return `AdmissionResponse`.

**Basic Webhook Server Implementation Example (Go):**

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

**4. Webhook Deployment and Configuration:**

Webhook servers are typically deployed within the Kubernetes cluster and require a service and TLS certificates.

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

**5. Best Practices:**

- **Performance Optimization**: Webhooks are in the API server request path, so they must respond quickly.
- **Error Handling**: Consider behavior when webhook server fails and set `failurePolicy` appropriately.
- **Scope Limitation**: Apply webhooks only to necessary resources and operations.
- **Testing**: Thoroughly test webhook behavior in various scenarios.
- **Monitoring**: Monitor webhook server performance and errors.
- **Version Management**: Support multiple versions of AdmissionReview in preparation for API version changes.
</details>

## Hands-on Questions

1. Write a CustomResourceDefinition (CRD) that meets the following requirements:
   - API Group: webapp.example.com
   - Version: v1
   - Kind: WebApp
   - Scope: Namespaced
   - Required fields: spec.image, spec.replicas
   - Validation rules: replicas must be an integer between 1 and 10
   - Enable status subresource

<details>
<summary>Show Answer</summary>

**Answer:**

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

This CRD has the following characteristics:

1. **Basic Information**:
   - API Group: `webapp.example.com`
   - Version: `v1`
   - Kind: `WebApp`
   - Scope: `Namespaced`

2. **Schema Validation**:
   - The `spec` field is required.
   - `spec.image` and `spec.replicas` are required fields.
   - `spec.replicas` must be an integer between 1 and 10.
   - `spec.port` is an optional field with a default value of 80.
   - `spec.env` is an optional field defining an array of environment variables.

3. **Status Subresource**:
   - The `status` subresource is enabled so controllers can update status.
   - `status.availableReplicas` and `status.phase` fields are defined.

4. **Additional Printer Columns**:
   - When running `kubectl get webapps`, Replicas, Image, and Age columns are displayed.

5. **Name Configuration**:
   - Plural: `webapps`
   - Singular: `webapp`
   - Kind: `WebApp`
   - Short name: `wa`

You can create custom resources like this using this CRD:

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

Controllers can watch this resource and update status:

```yaml
status:
  availableReplicas: 3
  phase: Running
```
</details>

2. Write a Mutating Admission Webhook configuration that meets the following requirements:
   - Add sidecar container to all pod creation requests
   - Apply only to a specific namespace (monitoring)
   - Webhook service: webhook-service.webhook-system.svc
   - Path: /mutate

<details>
<summary>Show Answer</summary>

**Answer:**

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

This configuration has the following characteristics:

1. **Webhook Configuration**:
   - Name: `sidecar-injector`
   - Webhook service: `webhook-service.webhook-system.svc`
   - Path: `/mutate`

2. **Scope**:
   - API Group: `""` (core API group)
   - API Version: `v1`
   - Operation: `CREATE` (apply only on pod creation)
   - Resource: `pods`
   - Scope: `Namespaced`

3. **Namespace Selector**:
   - Apply only to namespaces with `monitoring-injection: enabled` label
   - Add this label to the `monitoring` namespace

4. **Additional Settings**:
   - `admissionReviewVersions`: Supported AdmissionReview API versions
   - `sideEffects`: No side effects from webhook
   - `timeoutSeconds`: Webhook response wait time
   - `failurePolicy`: Deny requests on webhook failure

The webhook server should implement logic like this:

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

This webhook automatically adds a monitoring sidecar container to all pods created in the `monitoring` namespace. The sidecar container uses a monitoring agent image and mounts a shared volume to share data with the main container.
</details>
