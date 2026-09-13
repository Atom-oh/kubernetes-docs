# Kube Resource Orchestrator (kro)

> **Last Updated**: September 12, 2026 · **Baseline**: kro 0.9.4

## Concepts and Scope

The official name is Kube Resource Orchestrator, a Kubernetes SIG Cloud Provider subproject. A ResourceGraphDefinition (RGD) defines input schemas, relationships and status across Kubernetes resources. After validation and compilation, kro dynamically reconciles instances of the generated CRD.

An RGD defines an API and resource graph; it is not an application instance. The instance's spec supplies inputs and spec.resources templates create objects such as Deployments and Services. Existing CRDs such as ACK resources can participate, but kro does not supply their controllers or AWS IAM permissions.

`${...}` expressions inside YAML use CEL. The former .parent, .children, childResources, resourceKind, statusMappings and Go-template examples are not this API. Do not independently create the same application CRD and compete with the RGD for ownership.

## Comparison with Helm, Kustomize and Operators

| Tool | Primary role and boundary |
| --- | --- |
| Helm | Renders Go-template charts and manages release history. v2 chart dependencies are declared in Chart.yaml. |
| Kustomize | Transforms manifests using bases and patches; it is not a runtime controller. |
| Custom operator | Can implement domain-specific recovery, migrations and backups in code. |
| kro | Infers a resource graph from CEL references and reconciles instances; it does not generate database recovery algorithms. |

A Helm chart can install kro while GitOps manages RGDs and instances. These tools can work together. Moving from Helm to kro does not automatically improve security, recovery or operations. Kubernetes Deployment controllers also continue to manage Deployments originally created by Helm.

## Installation and Permissions

The official repository is kubernetes-sigs/kro; older kro-run paths may redirect. This is an **offline inspection** of a pinned OCI chart. Do not use the former kro-project download URLs or invented CLI installation. This release does not distribute a separate CLI binary; use kubectl and Helm.

```bash
helm template kro oci://registry.k8s.io/kro/charts/kro \
  --version 0.9.4 --namespace kro-system \
  --set rbac.mode=aggregation --include-crds
```

Before installation, verify a supported Kubernetes version, admission policies, namespaces and existing CRDs/controllers. The former 1.31–1.33 list is not presented as current support. Helm upgrade does not automatically update crds/; review the 0.9.4 release and CRD changes through a separate process.

Default rbac.mode=unrestricted grants broad cluster access. The example renders aggregation mode, which still includes base permissions for CRDs, RGDs, GraphRevisions and ConfigMaps. Add permissions for the generated application API and child resources. This ClusterRole allows the example's resource types and can grant access across the cluster. Trusted platform administrators should control RGDs and aggregation labels.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kro:controller:reviewed-nginxapps
  labels:
    rbac.kro.run/aggregate-to-controller: "true"
rules:
  - apiGroups: [platform.example.com]
    resources: [nginxapps]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [platform.example.com]
    resources: [nginxapps/status, nginxapps/finalizers]
    verbs: [get, update, patch]
  - apiGroups: [apps]
    resources: [deployments]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [""]
    resources: [services]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [networking.k8s.io]
    resources: [ingresses]
    verbs: [get, list, watch, create, update, patch, delete]
```

## Complete NginxApp Example

The RGD, instance and RBAC files are also in examples/platform/kro. Ingress defaults to disabled. Before enabling it, prepare an approved IngressClass/controller, host DNS and a TLS Secret in the same namespace. The string className=internal alone does not configure an internal load balancer.

The image uses the same nginx-unprivileged tag as the Helm example. A non-root UID, read-only root and /tmp volume are configured, but image execution was not tested. Verify digests, architecture and policies for deployment.

### ResourceGraphDefinition

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: reviewed-nginxapps
spec:
  schema:
    apiVersion: v1alpha1
    group: platform.example.com
    kind: NginxApp
    scope: Namespaced
    spec:
      replicas: integer | default=2 minimum=1 maximum=5
      image: string | default="nginxinc/nginx-unprivileged:1.30.4-alpine"
      ingress:
        enabled: boolean | default=false
        className: string | default="internal"
        host: string | default="app.example.com"
        tlsSecret: string | default="app-tls"
    status:
      availableReplicas: ${deployment.status.availableReplicas}
      serviceIP: ${service.spec.clusterIP}
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
                      drop: [ALL]
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
    - id: service
      template:
        apiVersion: v1
        kind: Service
        metadata:
          name: ${schema.metadata.name}
          namespace: ${schema.metadata.namespace}
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          type: ClusterIP
          selector: ${deployment.spec.selector.matchLabels}
          ports:
            - name: http
              port: 8080
              targetPort: http
    - id: ingress
      includeWhen:
        - ${schema.spec.ingress.enabled}
      template:
        apiVersion: networking.k8s.io/v1
        kind: Ingress
        metadata:
          name: ${schema.metadata.name}
          namespace: ${schema.metadata.namespace}
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          ingressClassName: ${schema.spec.ingress.className}
          tls:
            - hosts:
                - ${schema.spec.ingress.host}
              secretName: ${schema.spec.ingress.tlsSecret}
          rules:
            - host: ${schema.spec.ingress.host}
              http:
                paths:
                  - path: /
                    pathType: Prefix
                    backend:
                      service:
                        name: ${service.metadata.name}
                        port:
                          number: 8080
```

### Instance

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

SimpleSchema in schema.spec describes types, defaults and bounds; kro converts it into the generated CRD's OpenAPI schema. CEL schema.metadata/spec refers to the instance, while deployment/service refers to resource IDs. Define projected status under schema.status.

This example's readyWhen checks the Deployment's own availableReplicas and observedGeneration. Without readiness conditions, existence and resolvable references may suffice to advance. readyWhen must return Boolean values and refer only to its own resource ID. Application SLO and database checks remain separate.

The Service references the Deployment selector and the Ingress references the Service name, creating dependencies. Independent resources can share a wave; cycles are rejected. includeWhen controls conditional inclusion and can add or prune resources when conditions change. An externalRef to an existing resource is different from taking ownership to create or delete it.

### Apply Order and Inspection

In an approved cluster, apply reviewed RBAC and the RGD, verify that the RGD is Active and the generated nginxapps.platform.example.com CRD is Established, then apply the instance. Successful kubectl apply is not proof of graph compilation or app readiness.

```bash
kubectl get rgd reviewed-nginxapps -o yaml
kubectl get graphrevisions \
  -l internal.kro.run/resource-graph-definition-name=reviewed-nginxapps
kubectl get crd nginxapps.platform.example.com -o yaml
kubectl get nginxapps.platform.example.com reviewed-web -n example -o yaml
kubectl get deployments,services,ingresses -n example \
  -l app.kubernetes.io/name=reviewed-web
```

## GraphRevisions and Changes

Version 0.9.4 records and compiles immutable GraphRevisions when RGD specs change. A failed latest revision does not automatically fall back to the previous one; instance progress can stop. Inspect GraphAccepted, GraphVerified, GraphRevisionsResolved and error messages, then apply a valid spec.

GraphRevision is an internal.kro.run API. Use it for inspection and diagnosis without assuming stable external tooling contracts. Reverting a Git spec still requires validation in a new revision and does not roll back database data or external effects transactionally.

Group, kind, apiVersion and scope are immutable within an RGD. Distinguish compatible schema evolution from migration to a new API and review existing instances and stored data. Do not assume conversion webhooks are generated automatically.

## Deletion and Ownership

When an instance is deleted, kro uses ApplySet inventory and deletion waves to remove dependents first, retaining its finalizer until managed resources disappear. Child finalizers can block subsequent waves. External references are read-only and are never deleted by kro.

It is inaccurate to say all children are immediately garbage-collected. Inspect ResourcesReady=Unknown/UnderDeletion, inventory and child finalizers. Plan cleanup and retention of instances, RGDs, CRDs and data before removing controllers. CRD deletion also affects instance data.

## Migration and Operations

Review names, selectors, ownership, field managers and GitOps controllers so Helm and kro do not compete for an object. Choose a validated new-name graph with traffic cutover or a reviewed ownership-transfer process. Do not migrate by casually uninstalling a release that owns StatefulSets, PVCs or databases.

Use the same API contract and reviewed image digests across environments, with separate instances for namespaces, replicas, ingress and policies. Fleet tools such as ApplicationSet require kro, RGDs and permissions in each target cluster. kro does not automatically connect to arbitrary remote clusters.

Stateful applications still need database-operator or managed-service backup, restore, failover and migration behavior. Resource reconciliation alone is not data recovery. Bound graph size and permissions, define reusable units and expose only useful status. Do not copy Secret contents into status, labels or logs.

## Verification and References

Both original 504-line guides and 423-line quizzes were reviewed, including 16 unique code blocks and 20 question topics per language. The official kro 0.9.4 chart was rendered in aggregation mode and the RGD structure checked. Its cel-go 0.31.0 dependency compiled and evaluated the 14 unique published expressions. Four synthetic cases covered ingress on/off, insufficient replicas and stale observedGeneration.

These are CEL checks with dynamic synthetic inputs, not validation by the full kro graph compiler, Kubernetes API discovery, generated-CRD admission or a running controller. Containers, Ingress/TLS, databases and cluster resources were not executed.

- [kro 0.9.4](https://github.com/kubernetes-sigs/kro/releases/tag/v0.9.4)
- [Versioned API and source](https://github.com/kubernetes-sigs/kro/tree/v0.9.4)
- [RGD schema](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/concepts/rgd/01-schema.md)
- [Access control](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/01-access-control.md)
- [Graph revisions](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/05-graph-revisions.md)
- [Instance deletion](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/06-instance-deletion.md)

[kro quiz](../quizzes/platform-engineering/03-kro-quiz.md)
