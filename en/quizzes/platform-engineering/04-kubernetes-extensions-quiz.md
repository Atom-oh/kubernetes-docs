# Kubernetes Extension Mechanisms Quiz

[Kubernetes extensions](../../platform-engineering/04-kubernetes-extensions.md)

The original 20 question topics have been reviewed against current APIs and behavior.

## 1. What is a CRD for?

<details>
<summary>Show answer</summary>

Register custom resource types and input schemas in the Kubernetes API. A CRD does not itself implement workload behavior.

</details>

## 2. What does a reconciliation loop do?

<details>
<summary>Show answer</summary>

Reconcile observed and desired state while handling repeated events, restarts and conflicts. Avoid needless updates when state already matches.

</details>

## 3. What defines an Operator, and what are its limits?

<details>
<summary>Show answer</summary>

An Operator implements domain knowledge using custom APIs and controllers. Creating them alone does not make backup, failover or upgrades safe.

</details>

## 4. What can a mutating webhook return?

<details>
<summary>Show answer</summary>

An AdmissionReview response allowing/denying the request and optionally carrying JSONPatch. Preserve request UID/version; patch bytes are Base64-encoded.

</details>

## 5. What does a Filter plugin do?

<details>
<summary>Show answer</summary>

Exclude nodes that cannot satisfy Pod requirements. Passing filters does not complete binding or execution.

</details>

## 6. How do aggregation and CRDs differ?

<details>
<summary>Show answer</summary>

CRDs use the existing API server's custom-resource storage/validation. Aggregation delegates to a separate server requiring TLS, authentication, authorization, discovery and storage operations.

</details>

## 7. What does a finalizer provide?

<details>
<summary>Show answer</summary>

It gives a controller an opportunity to finish cleanup before deletion completes. The string executes no cleanup itself; removing it without investigation can leave external resources.

</details>

## 8. When does PostBind run?

<details>
<summary>Show answer</summary>

It is an informational stage after successful binding, not universal error recovery. Implement paths such as Unreserve for failed/cancelled reservations.

</details>

## 9. How is current Istio per-Pod injection controlled?

<details>
<summary>Show answer</summary>

Set sidecar.istio.io/inject in Pod or workload Pod-template labels. Check namespace injection/revision labels and precedence rather than using old annotations as defaults.

</details>

## 10. How are Score results used?

<details>
<summary>Show answer</summary>

Rank feasible nodes, combining normalization and plugin weights. Tie selection and failure handling are also scheduler behavior.

</details>

## 11. Where do CRD schemas and required fields belong?

<details>
<summary>Show answer</summary>

Under spec.versions[].schema.openAPIV3Schema. Top-level required: [spec] and required: [image] within spec enforce different conditions.

</details>

## 12. What must be checked for ownerReferences?

<details>
<summary>Show answer</summary>

Check owner UID, namespace/scope and existing controller ownership. GC depends on propagation/finalizers; matching names do not authorize adopting another workload.

</details>

## 13. How do VAP and validating webhooks differ?

<details>
<summary>Show answer</summary>

ValidatingAdmissionPolicy has been stable since 1.30 and evaluates CEL in-process. Webhooks require remote calls, TLS and availability management. VAP also needs a binding for scope and validationActions.

</details>

## 14. What does controller-runtime provide?

<details>
<summary>Show answer</summary>

Managers, clients/caches, reconciliation setup and leader election. It does not supply custom API types, schemes, RBAC or domain logic; align library and Kubernetes Go module versions.

</details>

## 15. What is a conversion webhook for?

<details>
<summary>Show answer</summary>

Convert representations between API versions of a CRD. Review served/storage versions, storedVersions and semantic preservation. Not every CRD requires a conversion webhook.

</details>

## 16. Write a WebApp CRD requiring image and replicas between 1 and 5.

<details>
<summary>Show answer</summary>

This also requires spec itself and separates status/scale paths. A controller must populate actual status.replicas and selector.

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
    shortNames: [wa]
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: [spec]
          properties:
            spec:
              type: object
              required: [image]
              properties:
                replicas:
                  type: integer
                  default: 1
                  minimum: 1
                  maximum: 5
                image:
                  type: string
                  minLength: 1
                port:
                  type: integer
                  default: 8080
                  minimum: 1
                  maximum: 65535
            status:
              type: object
              properties:
                replicas:
                  type: integer
                availableReplicas:
                  type: integer
                selector:
                  type: string
                observedGeneration:
                  type: integer
                  format: int64
      subresources:
        status: {}
        scale:
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.replicas
          labelSelectorPath: .status.selector
```

</details>

## 17. How should a Deployment-validation webhook be scoped to production?

<details>
<summary>Show answer</summary>

Match apps/v1 deployments CREATE/UPDATE and select kubernetes.io/metadata.name: production. Configure an actual validating server/Service/path, CA bundle, failurePolicy, timeoutSeconds, sideEffects and admissionReviewVersions. The guide's /mutate handler is not a Deployment validator. For a replica bound alone, use its VAP/binding example and match both `deployments` and `deployments/scale`, so HPA and `kubectl scale` updates cannot bypass the limit.

</details>

## 18. Describe a robust reconciliation sequence.

<details>
<summary>Show answer</summary>

Treat NotFound as successful completion. During deletion, finish idempotent cleanup before removing only your finalizer. Persist a finalizer before creating external resources, check child ownership and reconcile owned fields. Retry conflicts and patch changed observed status. Do not label pseudocode as a runnable controller.

</details>

## 19. What is needed when designing a distributed database Operator?

<details>
<summary>Show answer</summary>

Beyond schemas and workload creation, design primary fencing, quorum, replica synchronization, backup/WAL recovery tests, storage lifecycle, migration compatibility and failures. Creating Services, StatefulSets and CronJobs does not establish data safety.

</details>

## 20. How should a custom scheduler be implemented and verified?

<details>
<summary>Show answer</summary>

Compile/register plugins against the exact Kubernetes minor's framework interfaces. Align profile names and Pod schedulerName; test Filter/Score and reservation, permit and binding failures. YAML alone cannot install a plugin. Consider node affinity first for simple zone requirements.

</details>
