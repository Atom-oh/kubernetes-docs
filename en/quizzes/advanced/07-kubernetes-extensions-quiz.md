# Kubernetes Extension Mechanisms Quiz

> **Related Document**: [Kubernetes Extension Mechanisms](../../advanced/07-kubernetes-extensions.md)

## Multiple Choice Questions

### 1. What is the primary purpose of CRD (Custom Resource Definition)?

- A) To modify existing Kubernetes resources
- B) To extend the Kubernetes API with custom resource types
- C) To configure pod networking
- D) To provision storage volumes

<details>
<summary>Show Answer</summary>

**Answer: B) To extend the Kubernetes API with custom resource types**

**Explanation:**
CRDs allow you to extend the Kubernetes API by defining custom resource types that behave like native Kubernetes resources.

</details>

### 2. What is the main task performed by a custom controller's reconciliation loop?

- A) Immediately delete resources
- B) Reconcile differences between current state and desired state
- C) Register new APIs with the API server
- D) Apply network policies

<details>
<summary>Show Answer</summary>

**Answer: B) Reconcile differences between current state and desired state**

**Explanation:**
The custom controller's reconciliation loop observes the current state of resources, compares it with the desired state (spec), and takes actions to achieve the desired state when differences exist.

</details>

### 3. What are the core components of the Operator pattern?

- A) Deployment and Service
- B) CRD and Custom Controller
- C) ConfigMap and Secret
- D) Ingress and NetworkPolicy

<details>
<summary>Show Answer</summary>

**Answer: B) CRD and Custom Controller**

**Explanation:**
The Operator pattern uses CRDs to define application configuration and custom controllers to automate operational knowledge such as deployment, upgrades, and recovery.

</details>

### 4. What is the primary use of MutatingAdmissionWebhook?

- A) Reject API requests
- B) Modify API requests
- C) Log API responses
- D) Upgrade API versions

<details>
<summary>Show Answer</summary>

**Answer: B) Modify API requests**

**Explanation:**
MutatingAdmissionWebhook can modify API requests before they are persisted. Common uses include: sidecar container injection, setting defaults, etc.

</details>

### 5. What is the role of the Filter plugin in the scheduler framework?

- A) Assign scores to nodes
- B) Exclude nodes that cannot run the pod
- C) Bind the pod to a node
- D) Reserve node resources

<details>
<summary>Show Answer</summary>

**Answer: B) Exclude nodes that cannot run the pod**

**Explanation:**
Filter plugins filter out nodes that don't meet the pod's requirements, excluding them from consideration.

</details>

### 6. What is the difference between Aggregated API Server and CRD?

- A) No difference, they are the same
- B) Aggregated API provides more control but requires running a separate server
- C) CRD provides more features than Aggregated API
- D) Aggregated API is deprecated

<details>
<summary>Show Answer</summary>

**Answer: B) Aggregated API provides more control but requires running a separate server**

**Explanation:**
Aggregated API Server provides full control over API behavior, custom storage backends, and advanced features but requires deploying and maintaining a separate API server. CRDs are simpler but have limitations.

</details>

### 7. What is the purpose of a Finalizer in Kubernetes?

- A) To speed up resource deletion
- B) To prevent resource deletion until cleanup is complete
- C) To automatically restart failed pods
- D) To validate resource creation

<details>
<summary>Show Answer</summary>

**Answer: B) To prevent resource deletion until cleanup is complete**

**Explanation:**
Finalizers block resource deletion until the controller performs necessary cleanup operations (like deleting external resources) and removes the finalizer.

</details>

### 8. Which scheduler extension point runs after a pod has been bound to a node?

- A) PreFilter
- B) PostBind
- C) Reserve
- D) Score

<details>
<summary>Show Answer</summary>

**Answer: B) PostBind**

**Explanation:**
PostBind plugins are called after the pod has been successfully bound to a node. They are informational and used for cleanup or notifications.

</details>

### 9. What annotation is used to inject sidecars via admission webhook in Istio?

- A) istio.io/inject
- B) sidecar.istio.io/inject
- C) istio-injection
- D) auto-inject.istio.io

<details>
<summary>Show Answer</summary>

**Answer: B) sidecar.istio.io/inject**

**Explanation:**
The `sidecar.istio.io/inject` annotation controls whether Istio's mutating webhook injects the Envoy sidecar into a pod. Namespace-level control uses the `istio-injection` label.

</details>

### 10. What is the purpose of the Score plugin in the scheduler framework?

- A) To filter out unsuitable nodes
- B) To rank nodes and select the best one
- C) To bind the pod to the selected node
- D) To validate pod specifications

<details>
<summary>Show Answer</summary>

**Answer: B) To rank nodes and select the best one**

**Explanation:**
Score plugins assign scores to nodes that passed filtering. The scheduler selects the node with the highest combined score from all Score plugins.

</details>

## Short Answer Questions

### 1. What standard is used for schema validation in CRDs?

<details>
<summary>Show Answer</summary>

**Answer: OpenAPI v3 Schema (openAPIV3Schema)**

**Explanation:**
CRDs use OpenAPI v3 schema in `spec.versions[].schema.openAPIV3Schema` to define the structure and validation rules for custom resources.

</details>

### 2. What is the role of Owner Reference in Kubernetes controllers?

<details>
<summary>Show Answer</summary>

**Answer: To define ownership relationships between resources and manage garbage collection and event propagation**

**Explanation:**
Owner Reference defines parent-child relationships and automatically deletes children when the parent is deleted through Kubernetes garbage collection.

</details>

### 3. What is the difference between ValidatingAdmissionPolicy and ValidatingAdmissionWebhook?

<details>
<summary>Show Answer</summary>

**Answer: ValidatingAdmissionPolicy uses CEL expressions and runs in-process, while ValidatingAdmissionWebhook calls external HTTP endpoints.**

**Explanation:**
ValidatingAdmissionPolicy (introduced in 1.26) provides better performance and doesn't require external webhook infrastructure, but has less flexibility than webhooks.

</details>

### 4. What is the controller-runtime library and why is it commonly used?

<details>
<summary>Show Answer</summary>

**Answer: controller-runtime is a library that provides common patterns for building Kubernetes controllers, including client caching, leader election, and reconciliation loop management.**

**Explanation:**
Part of the Kubebuilder project, controller-runtime abstracts away boilerplate code and best practices, making it easier to build reliable operators.

</details>

### 5. What is the purpose of conversion webhooks in CRDs?

<details>
<summary>Show Answer</summary>

**Answer: Conversion webhooks convert resources between different API versions of the same CRD.**

**Explanation:**
When a CRD has multiple versions (e.g., v1alpha1, v1beta1, v1), conversion webhooks handle the transformation between versions to support API evolution.

</details>

## Hands-on Questions

### 1. Write a CRD that meets the following requirements:

- Name: WebApp
- Group: apps.example.com
- Fields: replicas (integer, minimum 1), image (string, required)

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.apps.example.com
spec:
  group: apps.example.com
  names:
    kind: WebApp
    plural: webapps
    singular: webapp
    shortNames:
      - wa
  scope: Namespaced
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
              required: ["image"]
              properties:
                replicas:
                  type: integer
                  minimum: 1
                  default: 1
                image:
                  type: string
            status:
              type: object
              properties:
                availableReplicas:
                  type: integer
                conditions:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                      status:
                        type: string
                      lastTransitionTime:
                        type: string
                        format: date-time
      subresources:
        status: {}
      additionalPrinterColumns:
        - name: Replicas
          type: integer
          jsonPath: .spec.replicas
        - name: Available
          type: integer
          jsonPath: .status.availableReplicas
        - name: Age
          type: date
          jsonPath: .metadata.creationTimestamp
```

</details>

### 2. Write a ValidatingAdmissionWebhook configuration that validates all Deployments in the "production" namespace.

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: deployment-validator
webhooks:
  - name: validate-deployment.example.com
    clientConfig:
      service:
        name: webhook-service
        namespace: webhook-system
        path: /validate-deployment
      caBundle: <base64-encoded-ca-cert>
    rules:
      - apiGroups: ["apps"]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["deployments"]
        scope: Namespaced
    namespaceSelector:
      matchLabels:
        environment: production
    failurePolicy: Fail
    sideEffects: None
    admissionReviewVersions: ["v1"]
    timeoutSeconds: 10
```

**Explanation:**
- `namespaceSelector` limits the webhook to namespaces with `environment: production` label
- `failurePolicy: Fail` rejects requests if the webhook is unavailable
- `sideEffects: None` indicates the webhook has no side effects

</details>

### 3. Write a simple reconciliation loop pseudocode for a custom controller.

<details>
<summary>Show Answer</summary>

```go
func (r *WebAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := log.FromContext(ctx)

    // 1. Fetch the WebApp resource
    var webapp appsv1.WebApp
    if err := r.Get(ctx, req.NamespacedName, &webapp); err != nil {
        if errors.IsNotFound(err) {
            // Resource deleted, nothing to do
            return ctrl.Result{}, nil
        }
        return ctrl.Result{}, err
    }

    // 2. Check if being deleted (handle finalizers)
    if !webapp.DeletionTimestamp.IsZero() {
        if containsFinalizer(webapp, finalizerName) {
            // Perform cleanup
            if err := r.cleanupExternalResources(&webapp); err != nil {
                return ctrl.Result{}, err
            }
            // Remove finalizer
            removeFinalizer(&webapp, finalizerName)
            if err := r.Update(ctx, &webapp); err != nil {
                return ctrl.Result{}, err
            }
        }
        return ctrl.Result{}, nil
    }

    // 3. Add finalizer if not present
    if !containsFinalizer(webapp, finalizerName) {
        addFinalizer(&webapp, finalizerName)
        if err := r.Update(ctx, &webapp); err != nil {
            return ctrl.Result{}, err
        }
    }

    // 4. Create or update Deployment
    deployment := r.constructDeployment(&webapp)
    if err := controllerutil.SetControllerReference(&webapp, deployment, r.Scheme); err != nil {
        return ctrl.Result{}, err
    }
    
    if err := r.CreateOrUpdate(ctx, deployment); err != nil {
        return ctrl.Result{}, err
    }

    // 5. Create or update Service
    service := r.constructService(&webapp)
    if err := controllerutil.SetControllerReference(&webapp, service, r.Scheme); err != nil {
        return ctrl.Result{}, err
    }
    
    if err := r.CreateOrUpdate(ctx, service); err != nil {
        return ctrl.Result{}, err
    }

    // 6. Update status
    webapp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
    if err := r.Status().Update(ctx, &webapp); err != nil {
        return ctrl.Result{}, err
    }

    // 7. Requeue after interval for periodic reconciliation
    return ctrl.Result{RequeueAfter: time.Minute * 5}, nil
}
```

**Key Points:**
- Always handle resource not found (may have been deleted)
- Use finalizers for cleanup of external resources
- Set owner references for garbage collection
- Update status subresource separately
- Consider requeue intervals for periodic checks

</details>

## Advanced Questions

### 1. Design a Kubernetes Operator for a complex distributed system.

<details>
<summary>Show Answer</summary>

**CRD Design:**
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: postgresclusters.database.example.com
spec:
  group: database.example.com
  names:
    kind: PostgresCluster
    plural: postgresclusters
    shortNames:
      - pg
  scope: Namespaced
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
              required: ["replicas", "version"]
              properties:
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
                version:
                  type: string
                  enum: ["14", "15", "16"]
                storage:
                  type: object
                  properties:
                    size:
                      type: string
                      default: "10Gi"
                    storageClass:
                      type: string
                backup:
                  type: object
                  properties:
                    enabled:
                      type: boolean
                      default: true
                    schedule:
                      type: string
                      default: "0 2 * * *"
                    retention:
                      type: integer
                      default: 7
            status:
              type: object
              properties:
                phase:
                  type: string
                  enum: ["Creating", "Running", "Upgrading", "Failed", "Deleting"]
                primaryEndpoint:
                  type: string
                replicaEndpoints:
                  type: array
                  items:
                    type: string
                currentVersion:
                  type: string
                conditions:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                      status:
                        type: string
                      reason:
                        type: string
                      message:
                        type: string
                      lastTransitionTime:
                        type: string
                        format: date-time
      subresources:
        status: {}
        scale:
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.readyReplicas
```

**Controller Core Logic:**
- **Phase-based state management** (Creating, Running, Upgrading, Failed)
- **Automatic failure recovery** (Failover when Primary fails)
- **Rolling upgrade strategy** (Upgrade replicas first, then primary)
- **Backup management** (CronJob for scheduled backups)

**Architecture:**
```
PostgresCluster CR
       |
       v
   Controller
       |
       +---> StatefulSet (PostgreSQL pods)
       +---> Service (Primary endpoint)
       +---> Service (Replica endpoint)
       +---> Secret (Credentials)
       +---> ConfigMap (PostgreSQL config)
       +---> CronJob (Backups)
       +---> PodDisruptionBudget
```

</details>

### 2. Explain how to implement a custom scheduler using the scheduler framework.

<details>
<summary>Show Answer</summary>

**Scheduler Plugin Implementation:**

```go
// Plugin implementing multiple extension points
type CustomSchedulerPlugin struct {
    handle framework.Handle
}

// Implement PreFilter - check pod requirements
func (p *CustomSchedulerPlugin) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) (*framework.PreFilterResult, *framework.Status) {
    // Validate pod has required annotations
    if _, ok := pod.Annotations["custom-scheduler/zone"]; !ok {
        return nil, framework.NewStatus(framework.Unschedulable, "missing zone annotation")
    }
    return nil, framework.NewStatus(framework.Success, "")
}

// Implement Filter - exclude unsuitable nodes
func (p *CustomSchedulerPlugin) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    requiredZone := pod.Annotations["custom-scheduler/zone"]
    nodeZone := nodeInfo.Node().Labels["topology.kubernetes.io/zone"]
    
    if requiredZone != nodeZone {
        return framework.NewStatus(framework.Unschedulable, "zone mismatch")
    }
    return framework.NewStatus(framework.Success, "")
}

// Implement Score - rank suitable nodes
func (p *CustomSchedulerPlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    nodeInfo, err := p.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, err.Error())
    }
    
    // Score based on available resources
    allocatable := nodeInfo.Node().Status.Allocatable
    requested := nodeInfo.Requested
    
    cpuScore := calculateResourceScore(allocatable.Cpu(), requested.Cpu)
    memScore := calculateResourceScore(allocatable.Memory(), requested.Memory)
    
    return (cpuScore + memScore) / 2, framework.NewStatus(framework.Success, "")
}

// Register the plugin
func New(_ runtime.Object, h framework.Handle) (framework.Plugin, error) {
    return &CustomSchedulerPlugin{handle: h}, nil
}
```

**Scheduler Configuration:**

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
  - schedulerName: custom-scheduler
    plugins:
      preFilter:
        enabled:
          - name: CustomSchedulerPlugin
      filter:
        enabled:
          - name: CustomSchedulerPlugin
      score:
        enabled:
          - name: CustomSchedulerPlugin
        disabled:
          - name: NodeResourcesBalancedAllocation
```

**Extension Points Summary:**

| Extension Point | Purpose | Runs When |
|----------------|---------|-----------|
| PreFilter | Pod-level checks | Before filtering |
| Filter | Node elimination | For each node |
| PostFilter | Handle unschedulable | When no node fits |
| PreScore | Prepare for scoring | Before scoring |
| Score | Node ranking | For filtered nodes |
| NormalizeScore | Score normalization | After all scores |
| Reserve | Resource reservation | After node selection |
| Permit | Final approval | Before binding |
| PreBind | Pre-binding actions | Before API binding |
| Bind | Actual binding | API server update |
| PostBind | Post-binding cleanup | After binding |

</details>
