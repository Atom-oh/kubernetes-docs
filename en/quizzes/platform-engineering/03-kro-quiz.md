# Kube Resource Orchestrator (kro) Quiz

[kro](../../platform-engineering/03-kro.md)

These questions retain the original 20 topics using kro 0.9.4.

## 1. What are kro's core concepts?

<details>
<summary>Show answer</summary>

Define API schemas and resource graphs in RGDs, infer dependencies from CEL references and reconcile instances. kro is not an imperative script runner.

</details>

## 2. Where are managed resource definitions declared?

<details>
<summary>Show answer</summary>

Under spec.resources, using each entry's id and either template or externalRef. The former childResources is not a current RGD field.

</details>

## 3. What does kro provide alongside Helm?

<details>
<summary>Show answer</summary>

A resource-reference graph and continuous instance reconciliation. Helm provides chart rendering and release management; they can work together. Neither is universally better for every workload.

</details>

## 4. How are instance inputs referenced in CEL?

<details>
<summary>Show answer</summary>

Use schema.spec or schema.metadata, such as `${schema.spec.replicas}`. Do not use .parent or Go-template syntax.

</details>

## 5. How is conditional resource inclusion configured?

<details>
<summary>Show answer</summary>

Use Boolean CEL expressions in includeWhen. Changing conditions can add or prune resources, so review lifecycle implications for stateful resources.

</details>

## 6. Where are managed-resource status values projected?

<details>
<summary>Show answer</summary>

Define CEL expressions under spec.schema.status, for example `${deployment.status.availableReplicas}`. statusMappings is not a current field.

</details>

## 7. How are dependencies and readiness ordered?

<details>
<summary>Show answer</summary>

CEL references to other resource IDs infer a DAG. Dependents also wait for readyWhen conditions when present. Cycles are rejected; YAML listing order is not a substitute for dependencies.

</details>

## 8. What happens when an instance is deleted?

<details>
<summary>Show answer</summary>

Current kro uses ApplySet inventory and deletion waves to remove dependents first, retaining a finalizer. Child finalizers can block progress. External-reference targets are not deleted.

</details>

## 9. What watches instance changes?

<details>
<summary>Show answer</summary>

kro's dynamic instance controllers observe changes and reconcile graphs. RGD/GraphRevision validation and compilation affect instance progress.

</details>

## 10. What does kubectl apply do?

<details>
<summary>Show answer</summary>

It creates or updates the CR's desired state, after which controllers reconcile. Apply success is not graph compilation or app readiness and does not guarantee transactional external effects.

</details>

## 11. What is an RGD?

<details>
<summary>Show answer</summary>

ResourceGraphDefinition defines the generated API schema, managed resources and status relationships. It is distinct from an application instance CR.

</details>

## 12. What supplies inputs analogous to Helm values?

<details>
<summary>Show answer</summary>

The generated API instance's spec. Its SimpleSchema types, defaults and bounds must match fields actually consumed by templates.

</details>

## 13. How is another resource referenced?

<details>
<summary>Show answer</summary>

Reference its resource ID directly, such as `${deployment.spec.selector.matchLabels}` or `${service.metadata.name}`. Do not use .children.

</details>

## 14. What tracks managed resources and supports deletion diagnosis?

<details>
<summary>Show answer</summary>

Inspect current ApplySet inventory, owner metadata and internal.kro.run/apply-order deletion waves. Do not treat an invented kro.run/owner annotation as the entire tracking contract.

</details>

## 15. How are input schemas validated?

<details>
<summary>Show answer</summary>

SimpleSchema becomes the generated CRD's OpenAPI schema, which Kubernetes uses to validate instances. RGD structure, graph-compiler CEL type checking and runtime readiness are separate checks.

</details>

## 16. Write the example NginxApp instance.

<details>
<summary>Show answer</summary>

First ensure the RGD is Active and its generated CRD is Established. This instance disables ingress.

```yaml
apiVersion: platform.example.com/v1alpha1
kind: NginxApp
metadata:
  name: reviewed-web
  namespace: example
spec:
  replicas: 2
  image: nginxinc/nginx-unprivileged:1.30.4-alpine
  ingress:
    enabled: false
    className: internal
    host: app.example.com
    tlsSecret: app-tls
```

</details>

## 17. Write the resource entry that creates a Deployment.

<details>
<summary>Show answer</summary>

This is the same template as the guide. readyWhen refers only to the Deployment itself; verify image, namespace and policies in the actual environment.

```yaml
resources:
- id: deployment
  readyWhen:
  - ${deployment.status.availableReplicas >= deployment.spec.replicas}
  - ${deployment.status.observedGeneration >= deployment.metadata.generation}
  template:
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: ${schema.metadata.name}
      namespace: ${schema.metadata.namespace}
      labels:
        app.kubernetes.io/name: ${schema.metadata.name}
    spec:
      replicas: ${schema.spec.replicas}
      selector:
        matchLabels:
          app.kubernetes.io/name: ${schema.metadata.name}
      template:
        metadata:
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
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
            image: ${schema.spec.image}
            ports:
            - name: http
              containerPort: 8080
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop:
                - ALL
            resources:
              requests:
                cpu: 100m
                memory: 64Mi
              limits:
                cpu: 500m
                memory: 128Mi
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

</details>

## 18. Expose availableReplicas in status.

<details>
<summary>Show answer</summary>

This is the status section under RGD spec.schema. Resolution may wait for missing values; it is not comprehensive application health.

```yaml
status:
  availableReplicas: ${deployment.status.availableReplicas}
  serviceIP: ${service.spec.clusterIP}
```

</details>

## 19. Design a dev/staging/prod strategy.

<details>
<summary>Show answer</summary>

Share a validated API contract and image digests while separating namespaces, replicas, ingress and policies per instance. Prepare kro/RGDs/permissions in each cluster and use fleet tooling for synchronization. Unused autoscaling fields do not create an HPA.

</details>

## 20. What are Helm and kro's limits for stateful applications?

<details>
<summary>Show answer</summary>

Neither automatically implements database backup, restore, failover or schema migration. Validate dedicated operator/managed-service behavior and data retention. Restoring a Git spec is not a database rollback; failed latest GraphRevisions do not automatically fall back.

</details>
