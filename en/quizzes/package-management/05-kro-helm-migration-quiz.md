# KRO Helm Migration Quiz

> **Related Document**: [KRO-based Helm Chart Migration](../../package-management/02-kro-helm-migration.md)

## Multiple Choice Questions

### 1. Which of the following is NOT a core concept of Kubernetes Resource Operator (KRO)?

- A) Declarative resource relationships
- B) State-based reconciliation
- C) Imperative script execution
- D) Resource graph

<details>
<summary>Show Answer</summary>

**Answer: C) Imperative script execution**

**Explanation:**
KRO manages resources declaratively. Declarative resource relationships, state-based reconciliation, resource graph, and automated lifecycle management are core concepts, while imperative script execution is not part of KRO's core concepts.

</details>

### 2. What is the role of `childResources` in a ResourceGraphDefinition (RGD)?

- A) To define parent resource metadata
- B) To define the list of child resources to be created from the parent resource
- C) To define cluster-wide settings
- D) To define namespace policies

<details>
<summary>Show Answer</summary>

**Answer: B) To define the list of child resources to be created from the parent resource**

**Explanation:**
`childResources` defines the list and templates of child Kubernetes resources (Deployment, Service, Ingress, etc.) that will be created from the parent custom resource.

</details>

### 3. What is KRO's main differentiator compared to Helm?

- A) Go template usage
- B) Chart archive packaging
- C) Explicit resource relationship modeling and automatic state propagation
- D) Release history management

<details>
<summary>Show Answer</summary>

**Answer: C) Explicit resource relationship modeling and automatic state propagation**

**Explanation:**
KRO models relationships between resources as an explicit graph and automatically propagates child resource states to the parent resource.

</details>

### 4. What does `.parent` reference in RGD templates?

- A) Kubernetes cluster
- B) Parent custom resource
- C) Namespace
- D) Controller pod

<details>
<summary>Show Answer</summary>

**Answer: B) Parent custom resource**

**Explanation:**
In RGD templates, `.parent` references the parent custom resource to which the ResourceGraphDefinition is applied.

</details>

### 5. Which field is used for conditional child resource creation in KRO?

- A) `when`
- B) `if`
- C) `condition`
- D) `enabled`

<details>
<summary>Show Answer</summary>

**Answer: C) `condition`**

**Explanation:**
The `condition` field in RGD's childResources can be used to conditionally create child resources.

</details>

### 6. What is the purpose of `statusMappings` in an RGD?

- A) To define error handling behavior
- B) To map child resource status to parent resource status
- C) To configure logging levels
- D) To set resource quotas

<details>
<summary>Show Answer</summary>

**Answer: B) To map child resource status to parent resource status**

**Explanation:**
`statusMappings` defines how to extract status information from child resources and propagate it to the parent custom resource's status field.

</details>

### 7. How does KRO handle resource dependencies?

- A) Through manual ordering in YAML files
- B) Through the resource graph that automatically determines creation order
- C) Through numeric priority fields
- D) Through alphabetical ordering

<details>
<summary>Show Answer</summary>

**Answer: B) Through the resource graph that automatically determines creation order**

**Explanation:**
KRO uses the resource graph to understand dependencies between resources and automatically determines the correct order for resource creation and deletion.

</details>

### 8. What happens when a parent custom resource is deleted in KRO?

- A) Child resources remain orphaned
- B) Child resources are automatically garbage collected
- C) Manual cleanup is required
- D) An error is thrown

<details>
<summary>Show Answer</summary>

**Answer: B) Child resources are automatically garbage collected**

**Explanation:**
KRO sets owner references on child resources, so when the parent is deleted, Kubernetes' garbage collector automatically removes all child resources.

</details>

### 9. Which component watches for custom resource changes in KRO?

- A) API Server
- B) Scheduler
- C) KRO Controller
- D) Kubelet

<details>
<summary>Show Answer</summary>

**Answer: C) KRO Controller**

**Explanation:**
The KRO Controller watches for changes to custom resources defined by ResourceGraphDefinitions and reconciles the desired state.

</details>

### 10. What is the equivalent of Helm's `helm upgrade --install` behavior in KRO?

- A) `kubectl apply` on the custom resource
- B) `kubectl replace` on the custom resource
- C) `kubectl patch` on the custom resource
- D) `kubectl create --save-config`

<details>
<summary>Show Answer</summary>

**Answer: A) `kubectl apply` on the custom resource**

**Explanation:**
`kubectl apply` provides idempotent behavior similar to `helm upgrade --install`. It creates the resource if it doesn't exist and updates it if it does.

</details>

## Short Answer Questions

### 1. What is the core resource in KRO that defines the relationship between custom resources and Kubernetes native resources?

<details>
<summary>Show Answer</summary>

**Answer: ResourceGraphDefinition (RGD)**

**Explanation:**
ResourceGraphDefinition (RGD) is the core component of KRO that declaratively defines the relationship between custom resources (parent) and Kubernetes native resources (children).

</details>

### 2. What is the KRO equivalent of Helm's values.yaml?

<details>
<summary>Show Answer</summary>

**Answer: The spec field of the Custom Resource (CR)**

**Explanation:**
Just as Helm customizes configuration through values.yaml, KRO defines application configuration through the spec field of the custom resource.

</details>

### 3. How do you reference a sibling child resource's output in an RGD template?

<details>
<summary>Show Answer</summary>

**Answer: Using `.children.<resourceId>` syntax**

**Explanation:**
In RGD templates, you can reference other child resources using `.children.<resourceId>` to access their metadata, spec, or status fields for cross-resource references.

</details>

### 4. What annotation does KRO use to track managed resources?

<details>
<summary>Show Answer</summary>

**Answer: `kro.run/owner` annotation**

**Explanation:**
KRO uses the `kro.run/owner` annotation along with Kubernetes owner references to track which resources are managed by which parent custom resource.

</details>

### 5. How does KRO handle schema validation for custom resources?

<details>
<summary>Show Answer</summary>

**Answer: Through OpenAPI v3 Schema defined in the RGD's spec.schema field**

**Explanation:**
KRO generates a CRD from the RGD, and the schema validation is performed using OpenAPI v3 Schema defined in the ResourceGraphDefinition.

</details>

## Hands-on Questions

### 1. Convert the following Helm values.yaml to a KRO custom resource instance.

```yaml
# Helm values.yaml
replicaCount: 2
image:
  repository: myapp
  tag: "1.0.0"
service:
  type: ClusterIP
  port: 8080
```

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: kro.example.com/v1
kind: MyApp
metadata:
  name: my-application
spec:
  replicas: 2
  image:
    repository: myapp
    tag: "1.0.0"
  service:
    type: ClusterIP
    port: 8080
```

</details>

### 2. Write an RGD childResource definition that creates a Deployment based on the parent spec.

<details>
<summary>Show Answer</summary>

```yaml
childResources:
  - id: deployment
    resource:
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: "{{.parent.metadata.name}}"
      spec:
        replicas: "{{.parent.spec.replicas}}"
        selector:
          matchLabels:
            app: "{{.parent.metadata.name}}"
        template:
          metadata:
            labels:
              app: "{{.parent.metadata.name}}"
          spec:
            containers:
              - name: app
                image: "{{.parent.spec.image.repository}}:{{.parent.spec.image.tag}}"
                ports:
                  - containerPort: "{{.parent.spec.service.port}}"
```

</details>

### 3. Write a statusMappings configuration that exposes the Deployment's available replicas to the parent status.

<details>
<summary>Show Answer</summary>

```yaml
statusMappings:
  - childResourceId: deployment
    fieldPath: status.availableReplicas
    parentFieldPath: status.availableReplicas
  - childResourceId: deployment
    fieldPath: status.conditions
    parentFieldPath: status.deploymentConditions
```

**Explanation:**
statusMappings extracts specific fields from child resource status and maps them to the parent custom resource's status, enabling users to check application state through the parent resource.

</details>

## Advanced Questions

### 1. Design a multi-environment (dev/staging/production) deployment strategy using KRO.

<details>
<summary>Show Answer</summary>

**Environment-specific Custom Resource Instances:**

```yaml
# dev/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-dev
spec:
  replicas: 1
  image:
    tag: "dev-latest"
  resources:
    requests:
      cpu: "100m"
      memory: "128Mi"
---
# staging/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-staging
spec:
  replicas: 2
  image:
    tag: "rc-1.0.0"
  resources:
    requests:
      cpu: "250m"
      memory: "256Mi"
---
# production/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-prod
spec:
  replicas: 3
  image:
    tag: "v1.0.0"
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
  resources:
    requests:
      cpu: "500m"
      memory: "512Mi"
```

**GitOps Integration:**
Use ArgoCD ApplicationSet to automate environment-specific deployments with a single RGD across all environments.

</details>

### 2. Compare the operational differences between Helm and KRO for managing a stateful application like a database cluster.

<details>
<summary>Show Answer</summary>

**Helm Approach:**
- Templating-based: generates static manifests at install time
- Release management: tracks versions via Secrets/ConfigMaps
- Upgrade process: requires `helm upgrade` command
- State tracking: no built-in reconciliation after initial deployment
- Rollback: uses stored release history

**KRO Approach:**
- Reconciliation-based: continuously monitors and corrects drift
- Native Kubernetes: uses standard kubectl and CRDs
- Upgrade process: modify the CR spec, controller reconciles
- State tracking: controller watches and reconciles continuously
- Rollback: revert CR spec to previous state

**Key Differences for Stateful Applications:**

| Aspect | Helm | KRO |
|--------|------|-----|
| Drift Detection | Manual | Automatic |
| Self-healing | No | Yes |
| Status Visibility | External (helm status) | Native (kubectl get) |
| Dependency Management | Chart dependencies | Resource graph |
| Lifecycle Hooks | pre/post hooks | Controller logic |

**Recommendation:**
KRO is better suited for stateful applications that require continuous reconciliation, automatic drift correction, and complex lifecycle management. Helm is simpler for stateless applications with straightforward deployments.

</details>
