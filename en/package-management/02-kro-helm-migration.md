# Helm Chart Migration with Kubernetes Resource Operator (KRO)

> **Supported Versions**: Kubernetes 1.31, 1.32, 1.33
> **Last Updated**: November 24, 2025

## Overview

Kubernetes Resource Operator (KRO) is a new approach to declaratively managing Kubernetes resources. This document explains how to migrate existing Helm charts to KRO and explores the benefits gained through this migration.

## KRO Core Concepts

### What is Kubernetes Resource Operator?

Kubernetes Resource Operator (KRO) is a framework for declaratively defining and managing relationships between Kubernetes resources. KRO is based on the following core concepts:

1. **Declarative Resource Relationships**: Expresses complex application structures by explicitly defining relationships between resources.
2. **State-Based Reconciliation**: Continuously reconciles differences between desired and actual states.
3. **Resource Graph**: Models dependencies and relationships between resources in graph form.
4. **Automated Lifecycle Management**: Automatically handles resource creation, updates, and deletion.

### ResourceGraphDefinition (RGD)

ResourceGraphDefinition (RGD) is a core component of KRO that defines relationships between custom resources and their dependent Kubernetes native resources. RGD provides the following capabilities:

1. **Parent-Child Relationship Definition**: Defines hierarchical structure between parent and child resources.
2. **Template-Based Resource Creation**: Dynamically creates child resources based on parent resource properties.
3. **State Propagation**: Propagates child resource states to parent resources to understand overall application state.
4. **Dependency Management**: Defines dependencies between child resources to ensure correct creation and update order.

### KRO vs Traditional Approaches

KRO has the following differentiators compared to traditional Kubernetes resource management approaches:

| Feature | KRO | Helm | Operator SDK | Kustomize |
|---------|-----|------|--------------|-----------|
| **Resource Relationship Modeling** | Explicit graph | Implicit | Code-based | None |
| **State Propagation** | Automatic | Manual | Code-based | None |
| **Dependency Management** | Declarative | Implicit | Code-based | None |
| **Extensibility** | High | Medium | High | Low |
| **Learning Curve** | Medium | Low | High | Low |
| **GitOps Friendliness** | High | Medium | Medium | High |

### KRO Architecture

KRO consists of the following components:

1. **KRO Controller**: Watches ResourceGraphDefinitions and manages resource graphs.
2. **Resource Graph Engine**: Processes relationships and dependencies between resources.
3. **State Manager**: Tracks and propagates resource states.
4. **Reconciliation Loop**: Reconciles differences between desired and actual states.

```
+-------------------+     +-------------------+     +-------------------+
|  Custom Resource  |     | ResourceGraph     |     | Kubernetes        |
|  (CR)             |<--->| Definition        |<--->| Native Resources  |
+-------------------+     +-------------------+     +-------------------+
         ^                        ^                         ^
         |                        |                         |
         v                        v                         v
+-----------------------------------------------------------------------+
|                          KRO Controller                                |
|                                                                       |
|  +----------------+  +----------------+  +----------------+           |
|  | Resource Graph |  | State Manager  |  | Reconciliation |           |
|  |     Engine     |  |                |  |     Loop       |           |
|  +----------------+  +----------------+  +----------------+           |
+-----------------------------------------------------------------------+
```

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools
- kubectl v1.31 or higher
- Helm v3.10 or higher
- kro CLI v0.5.0 or higher
- A working Kubernetes cluster (EKS, minikube, kind, etc.)

### Installing KRO

```bash
# Install KRO controller
kubectl apply -f https://github.com/kro-project/kro/releases/download/v0.5.0/kro-controller.yaml

# Install KRO CLI
curl -L https://github.com/kro-project/kro/releases/download/v0.5.0/kro-cli-$(uname -s)-$(uname -m) -o kro
chmod +x kro
sudo mv kro /usr/local/bin/

# Verify installation
kubectl get pods -n kro-system
```

## Helm and KRO Comparison

### Helm

Helm is a widely used tool for packaging and deploying Kubernetes applications. Helm has the following characteristics:

- **Template-Based**: Uses Go template language to generate Kubernetes manifests
- **Chart Concept**: Unit for packaging applications
- **Release Management**: Version management of deployed applications
- **Central Repository**: Repository for sharing and reusing charts

### Kubernetes Resource Operator (KRO)

KRO is an approach to managing applications using Kubernetes custom resources:

- **Declarative API**: Kubernetes-native resource definition
- **State-Based**: Declare desired state and controller reconciles actual state
- **GitOps Friendly**: Easy integration with version control systems
- **Extensibility**: Extension through Custom Resource Definitions (CRDs)

### Comparison Table

| Feature | Helm | KRO |
|---------|------|-----|
| **Packaging Method** | Chart (tgz archive) | Custom Resource |
| **Template Engine** | Go templates | None (pure YAML) |
| **Version Management** | Release history | Git-based |
| **Rollback Mechanism** | helm rollback | GitOps-based rollback |
| **Dependency Management** | requirements.yaml | ResourceGraphDefinition |
| **Customization** | values.yaml | CR spec |
| **Installation Method** | helm install | kubectl apply |
| **Upgrade Method** | helm upgrade | kubectl apply |
| **Deletion Method** | helm uninstall | kubectl delete |
| **Hooks** | Install/upgrade/delete hooks | Kubernetes event-based |

## Reasons to Migrate from Helm to KRO

1. **Kubernetes Native Approach**: KRO follows Kubernetes' declarative API model for a more consistent experience
2. **Improved Version Management**: Ability to track changes to each resource individually
3. **Fine-Grained Control**: More detailed control at the individual resource level
4. **Simplified Dependency Management**: Easier complex relationship management with explicit dependency declarations
5. **Enhanced Security**: Ability to grant only necessary permissions following the principle of least privilege
6. **Improved State Management**: Automatically propagate and aggregate resource states
7. **GitOps Workflow Integration**: Easy integration with GitOps tools through declarative approach

## Practical Example: Migrating Nginx Helm Chart to KRO

### Existing Helm Chart (values.yaml)

```yaml
# Nginx Helm chart values.yaml
replicaCount: 2

image:
  repository: nginx
  tag: 1.21.0
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  hosts:
    - host: example.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 50m
    memory: 64Mi
```

### KRO Custom Resource Definition

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: nginxapps.kro.example.com
spec:
  group: kro.example.com
  names:
    kind: NginxApp
    listKind: NginxAppList
    plural: nginxapps
    singular: nginxapp
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
              properties:
                replicas:
                  type: integer
                  default: 1
                image:
                  type: object
                  properties:
                    repository:
                      type: string
                    tag:
                      type: string
                    pullPolicy:
                      type: string
                      enum: [Always, IfNotPresent, Never]
                service:
                  type: object
                  properties:
                    type:
                      type: string
                      enum: [ClusterIP, NodePort, LoadBalancer]
                    port:
                      type: integer
                ingress:
                  type: object
                  properties:
                    enabled:
                      type: boolean
                    hosts:
                      type: array
                      items:
                        type: object
                        properties:
                          host:
                            type: string
                          paths:
                            type: array
                            items:
                              type: object
                              properties:
                                path:
                                  type: string
                                pathType:
                                  type: string
                resources:
                  type: object
                  properties:
                    limits:
                      type: object
                      x-kubernetes-preserve-unknown-fields: true
                    requests:
                      type: object
                      x-kubernetes-preserve-unknown-fields: true
```

### Creating ResourceGraphDefinition

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: nginxapp-graph
spec:
  resourceKind:
    group: kro.example.com
    kind: NginxApp
    version: v1
  childResources:
    - apiVersion: apps/v1
      kind: Deployment
      nameTemplate: "{{.parent.metadata.name}}"
      template: |
        spec:
          replicas: {{.parent.spec.replicas}}
          selector:
            matchLabels:
              app: {{.parent.metadata.name}}
          template:
            metadata:
              labels:
                app: {{.parent.metadata.name}}
            spec:
              containers:
              - name: nginx
                image: {{.parent.spec.image.repository}}:{{.parent.spec.image.tag}}
                imagePullPolicy: {{.parent.spec.image.pullPolicy}}
                ports:
                - containerPort: {{.parent.spec.service.port}}
                resources:
                  {{- if .parent.spec.resources }}
                  limits:
                    {{- if .parent.spec.resources.limits.cpu }}
                    cpu: {{.parent.spec.resources.limits.cpu}}
                    {{- end }}
                    {{- if .parent.spec.resources.limits.memory }}
                    memory: {{.parent.spec.resources.limits.memory}}
                    {{- end }}
                  requests:
                    {{- if .parent.spec.resources.requests.cpu }}
                    cpu: {{.parent.spec.resources.requests.cpu}}
                    {{- end }}
                    {{- if .parent.spec.resources.requests.memory }}
                    memory: {{.parent.spec.resources.requests.memory}}
                    {{- end }}
                  {{- end }}

    - apiVersion: v1
      kind: Service
      nameTemplate: "{{.parent.metadata.name}}"
      template: |
        spec:
          selector:
            app: {{.parent.metadata.name}}
          ports:
          - port: {{.parent.spec.service.port}}
            targetPort: {{.parent.spec.service.port}}
          type: {{.parent.spec.service.type}}

    - apiVersion: networking.k8s.io/v1
      kind: Ingress
      nameTemplate: "{{.parent.metadata.name}}"
      condition: "{{.parent.spec.ingress.enabled}}"
      template: |
        spec:
          rules:
          {{- range .parent.spec.ingress.hosts }}
          - host: {{.host}}
            http:
              paths:
              {{- range .paths }}
              - path: {{.path}}
                pathType: {{.pathType}}
                backend:
                  service:
                    name: {{$.parent.metadata.name}}
                    port:
                      number: {{$.parent.spec.service.port}}
              {{- end }}
          {{- end }}

  statusMappings:
    - childResource:
        kind: Deployment
        name: "{{.parent.metadata.name}}"
      conditions:
        - type: Available
          mapping:
            type: Ready
      fieldMappings:
        - child: "status.availableReplicas"
          parent: "status.availableReplicas"
        - child: "status.readyReplicas"
          parent: "status.readyReplicas"

    - childResource:
        kind: Service
        name: "{{.parent.metadata.name}}"
      fieldMappings:
        - child: "spec.clusterIP"
          parent: "status.serviceIP"
```

### KRO Custom Resource Instance

```yaml
apiVersion: kro.example.com/v1
kind: NginxApp
metadata:
  name: my-nginx
spec:
  replicas: 2
  image:
    repository: nginx
    tag: 1.21.0
    pullPolicy: IfNotPresent
  service:
    type: ClusterIP
    port: 80
  ingress:
    enabled: true
    hosts:
      - host: example.com
        paths:
          - path: /
            pathType: Prefix
  resources:
    limits:
      cpu: 100m
      memory: 128Mi
    requests:
      cpu: 50m
      memory: 64Mi
```

### Deployment and Verification

```bash
# Apply CRD and RGD
kubectl apply -f nginxapp-crd.yaml
kubectl apply -f nginxapp-rgd.yaml

# Apply custom resource instance
kubectl apply -f my-nginx.yaml

# Verify created resources
kubectl get deployments,services,ingress -l app=my-nginx

# Check custom resource status
kubectl get nginxapp my-nginx -o yaml
```

## KRO Use Cases

### 1. Microservices Application Management

KRO is ideal for managing microservices applications consisting of multiple components. Each microservice can be composed of the following resources:

- Deployment or StatefulSet
- Service
- ConfigMap
- Secret
- HorizontalPodAutoscaler
- PodDisruptionBudget

Using KRO, you can explicitly define relationships between these resources and manage the entire microservice through a single custom resource.

### 2. Database Cluster Management

Database clusters (e.g., PostgreSQL, MySQL) require multiple components and complex configurations. KRO can manage the following resources:

- Master and replica StatefulSets
- Service endpoints
- Persistent volume claims
- Backup and restore jobs
- Monitoring configuration

### 3. Multi-Cluster Application Deployment

KRO can also be used to manage applications spanning multiple Kubernetes clusters. This supports scenarios such as:

- Regional deployments
- Consistent deployment across development, staging, and production environments
- Application management in hybrid cloud environments

## KRO Best Practices

### 1. Resource Graph Design

- **Single Responsibility Principle**: Each custom resource should have a clear single responsibility.
- **Appropriate Abstraction Level**: Choose an appropriate level of abstraction that is neither too detailed nor too abstract.
- **Clear Boundaries**: Clearly define boundaries and responsibilities between resources.
- **Reusability**: Identify common patterns and extract them into reusable components.

### 2. State Management

- **Meaningful State**: Provide meaningful state information to users.
- **State Aggregation**: Appropriately aggregate states from multiple child resources.
- **Condition Definition**: Define clear condition types and statuses.
- **Diagnostic Information**: Include diagnostic information helpful for troubleshooting.

### 3. Version Management

- **API Version Management**: Properly manage custom resource API versions.
- **Conversion Webhooks**: Implement webhooks for version conversion.
- **Backward Compatibility**: Maintain backward compatibility where possible.
- **Gradual Migration**: Introduce large changes gradually.

### 4. Security

- **Least Privilege**: Grant only the minimum necessary permissions to controllers.
- **RBAC Policies**: Define appropriate RBAC policies to control access.
- **Secret Management**: Manage sensitive information as Secrets.
- **Validation Webhooks**: Implement webhooks for input validation.

## Conclusion

Migration from Helm to KRO is an important step toward transitioning to a Kubernetes-native approach. This enables more declarative, extensible, and GitOps-friendly application management. Especially for complex applications, KRO provides more fine-grained control and improved version management.

ResourceGraphDefinition (RGD) is a core concept of KRO, providing mechanisms to explicitly define relationships between resources and propagate states. This allows easier modeling and management of complex application structures.

The migration process requires additional initial work, but provides significant benefits in terms of long-term maintenance and operations. Through a gradual migration approach, you can minimize risk while leveraging the benefits of KRO.

While KRO is still an evolving technology, it represents an important approach showing the future direction of the Kubernetes ecosystem. Concepts like declarative APIs, resource relationship modeling, and state propagation are becoming core principles of cloud-native application management.

## Quiz

To test what you've learned in this chapter, try the [KRO Helm Migration Quiz](../quizzes/package-management/05-kro-helm-migration-quiz.md).

## Helm and KRO Comparison

### Helm

Helm is a widely used tool for packaging and deploying Kubernetes applications. Helm has the following characteristics:

- **Template-Based**: Uses Go template language to generate Kubernetes manifests
- **Chart Concept**: Unit for packaging applications
- **Release Management**: Version management of deployed applications
- **Central Repository**: Repository for sharing and reusing charts

### Kubernetes Resource Operator (KRO)

KRO is an approach to managing applications using Kubernetes custom resources:

- **Declarative API**: Kubernetes-native resource definition
- **State-Based**: Declare desired state and controller reconciles actual state
- **GitOps Friendly**: Easy integration with version control systems
- **Extensibility**: Extension through Custom Resource Definitions (CRDs)

### Comparison Table

| Feature | Helm | KRO |
|---------|------|-----|
| **Packaging Method** | Chart (tgz archive) | Custom Resource |
| **Template Engine** | Go templates | None (pure YAML) |
| **Version Management** | Release history | Git-based |
| **Rollback Mechanism** | helm rollback | GitOps-based rollback |
| **Dependency Management** | requirements.yaml | ResourceGraphDefinition |
| **Customization** | values.yaml | CR spec |
| **Installation Method** | helm install | kubectl apply |
| **Upgrade Method** | helm upgrade | kubectl apply |
| **Deletion Method** | helm uninstall | kubectl delete |
| **Hooks** | Install/upgrade/delete hooks | Kubernetes event-based |

## Reasons to Migrate from Helm to KRO

1. **Kubernetes Native Approach**: KRO follows Kubernetes' declarative API model for a more consistent experience
2. **Improved Version Management**: Ability to track changes to each resource individually
3. **Fine-Grained Control**: More detailed control at the individual resource level
4. **Simplified Dependency Management**: Easier complex relationship management with explicit dependency declarations
5. **Enhanced Security**: Ability to grant only necessary permissions following the principle of least privilege

## Migration Steps

### 1. Helm Chart Analysis

```bash
# Check Helm chart structure
helm template my-chart

# Check generated resources
helm template my-chart | kubectl api-resources --verbs=create -o name | xargs -n 1 grep -l "kind:" | sort -u
```

### 2. Custom Resource Definition (CRD) Creation

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: applications.kro.example.com
spec:
  group: kro.example.com
  names:
    kind: Application
    plural: applications
    singular: application
    shortNames:
      - app
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
              properties:
                # Application configuration schema definition
                replicas:
                  type: integer
                  minimum: 1
                image:
                  type: string
                port:
                  type: integer
              required: ["replicas", "image"]
```

### 3. ResourceGraphDefinition Concepts and Creation

#### Understanding ResourceGraphDefinition (RGD) Concepts

ResourceGraphDefinition (RGD) is a core concept of KRO that declaratively defines relationships between custom resources and Kubernetes native resources. RGD performs the following important roles:

1. **Resource Relationship Definition**: Explicitly defines relationships between parent and child resources.
2. **Template-Based Resource Creation**: Dynamically creates child resources based on parent resource properties.
3. **State Propagation**: Propagates child resource states to parent resources to understand overall application state.
4. **Lifecycle Management**: Automatically manages child resource creation, updates, and deletion according to parent resource lifecycle.

#### Key Components of RGD

1. **resourceKind**: Specifies the type of custom resource to which the RGD applies.
   - `group`: API group (e.g., kro.example.com)
   - `kind`: Resource kind (e.g., Application)
   - `version`: API version (e.g., v1)

2. **childResources**: Defines the list of child resources to be created from the parent resource.
   - `apiVersion`: Child resource API version
   - `kind`: Child resource kind
   - `nameTemplate`: Template for generating child resource names
   - `template`: Template defining child resource spec

3. **statusMappings**: Defines rules for mapping child resource states to parent resource states.
   - `childResource`: Reference to child resource to get state from
   - `conditions`: Maps child resource conditions to parent resource conditions

4. **dependencies**: Defines dependencies between child resources.
   - `source`: Source resource of dependency
   - `target`: Target resource of dependency
   - `condition`: Dependency condition (e.g., Ready)

#### RGD Template Syntax

RGD templates are based on Go template language and provide the following special variables and functions:

1. **Variables**:
   - `.parent`: Access parent resource (e.g., `.parent.metadata.name`)
   - `.children`: Access other child resources (e.g., `.children.service.metadata.name`)

2. **Functions**:
   - `include`: Include another template
   - `toYaml`: Convert object to YAML format
   - `fromYaml`: Convert YAML string to object
   - `tpl`: Evaluate string as template

#### ResourceGraphDefinition Example

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: application-graph
spec:
  resourceKind:
    group: kro.example.com
    kind: Application
    version: v1
  childResources:
    - apiVersion: apps/v1
      kind: Deployment
      nameTemplate: "{{.parent.metadata.name}}"
      template: |
        spec:
          replicas: {{.parent.spec.replicas}}
          selector:
            matchLabels:
              app: {{.parent.metadata.name}}
          template:
            metadata:
              labels:
                app: {{.parent.metadata.name}}
            spec:
              containers:
              - name: {{.parent.metadata.name}}
                image: {{.parent.spec.image}}
                ports:
                - containerPort: {{.parent.spec.port}}
    - apiVersion: v1
      kind: Service
      nameTemplate: "{{.parent.metadata.name}}"
      template: |
        spec:
          selector:
            app: {{.parent.metadata.name}}
          ports:
          - port: {{.parent.spec.port}}
            targetPort: {{.parent.spec.port}}
          type: ClusterIP
  statusMappings:
    - childResource:
        kind: Deployment
        name: "{{.parent.metadata.name}}"
      conditions:
        - type: Available
          mapping:
            type: Ready
    - childResource:
        kind: Service
        name: "{{.parent.metadata.name}}"
      fieldMappings:
        - child: "spec.clusterIP"
          parent: "status.serviceIP"
  dependencies:
    - source:
        kind: Service
        name: "{{.parent.metadata.name}}"
      target:
        kind: Deployment
        name: "{{.parent.metadata.name}}"
      condition: Available
```

#### Advanced RGD Features

1. **Conditional Child Resource Creation**:
```yaml
childResources:
  - apiVersion: networking.k8s.io/v1
    kind: Ingress
    nameTemplate: "{{.parent.metadata.name}}"
    condition: "{{.parent.spec.ingress.enabled}}"
    template: |
      spec:
        rules:
        {{- range .parent.spec.ingress.hosts }}
        - host: {{.host}}
          http:
            paths:
            {{- range .paths }}
            - path: {{.path}}
              pathType: {{.pathType}}
              backend:
                service:
                  name: {{$.parent.metadata.name}}
                  port:
                    number: {{$.parent.spec.service.port}}
            {{- end }}
        {{- end }}
```

2. **References Between Child Resources**:
```yaml
childResources:
  - apiVersion: v1
    kind: ConfigMap
    nameTemplate: "{{.parent.metadata.name}}-config"
    template: |
      data:
        app.properties: |
          server.port={{.parent.spec.port}}

  - apiVersion: apps/v1
    kind: Deployment
    nameTemplate: "{{.parent.metadata.name}}"
    template: |
      spec:
        template:
          spec:
            containers:
            - name: {{.parent.metadata.name}}
              volumeMounts:
              - name: config
                mountPath: /app/config
            volumes:
            - name: config
              configMap:
                name: {{.children.configmap.metadata.name}}
```

3. **State Aggregation and Propagation**:
```yaml
statusMappings:
  - childResource:
      kind: Deployment
      name: "{{.parent.metadata.name}}"
    conditions:
      - type: Available
        mapping:
          type: Ready
    fieldMappings:
      - child: "status.readyReplicas"
        parent: "status.readyCount"
      - child: "status.replicas"
        parent: "status.totalCount"
```
kind: CustomResourceDefinition
metadata:
  name: applications.kro.example.com
spec:
  group: kro.example.com
  names:
    kind: Application
    listKind: ApplicationList
    plural: applications
    singular: application
    shortNames:
      - app
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
              properties:
                # Application property definition
                replicas:
                  type: integer
                  minimum: 0
                image:
                  type: string
                config:
                  type: object
                  x-kubernetes-preserve-unknown-fields: true
```

### 3. Operator Development

```go
package main

import (
    "context"
    "fmt"

    appsv1 "k8s.io/api/apps/v1"
    corev1 "k8s.io/api/core/v1"
    "k8s.io/apimachinery/pkg/api/errors"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/runtime"
    "k8s.io/client-go/kubernetes"
    ctrl "sigs.k8s.io/controller-runtime"
    "sigs.k8s.io/controller-runtime/pkg/client"
    "sigs.k8s.io/controller-runtime/pkg/log"

    krov1 "example.com/kro/api/v1"
)

// ApplicationReconciler reconciles an Application object
type ApplicationReconciler struct {
    client.Client
    Scheme *runtime.Scheme
}

func (r *ApplicationReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := log.FromContext(ctx)

    // Get Application CR
    var app krov1.Application
    if err := r.Get(ctx, req.NamespacedName, &app); err != nil {
        if errors.IsNotFound(err) {
            return ctrl.Result{}, nil
        }
        return ctrl.Result{}, err
    }

    // Create or update Deployment
    deployment := &appsv1.Deployment{
        ObjectMeta: metav1.ObjectMeta{
            Name:      app.Name,
            Namespace: app.Namespace,
        },
        Spec: appsv1.DeploymentSpec{
            Replicas: &app.Spec.Replicas,
            Selector: &metav1.LabelSelector{
                MatchLabels: map[string]string{
                    "app": app.Name,
                },
            },
            Template: corev1.PodTemplateSpec{
                ObjectMeta: metav1.ObjectMeta{
                    Labels: map[string]string{
                        "app": app.Name,
                    },
                },
                Spec: corev1.PodSpec{
                    Containers: []corev1.Container{
                        {
                            Name:  "app",
                            Image: app.Spec.Image,
                        },
                    },
                },
            },
        },
    }

    // Apply Deployment
    if err := r.Create(ctx, deployment); err != nil {
        if !errors.IsAlreadyExists(err) {
            return ctrl.Result{}, err
        }

        // Update if already exists
        if err := r.Update(ctx, deployment); err != nil {
            return ctrl.Result{}, err
        }
    }

    log.Info("Reconciled Application", "name", app.Name)
    return ctrl.Result{}, nil
}
```

### 4. Custom Resource Creation

```yaml
apiVersion: kro.example.com/v1
kind: Application
metadata:
  name: my-application
spec:
  replicas: 3
  image: nginx:latest
  config:
    port: 80
    path: /api
```

## Practical Example: Migrating Nginx Helm Chart to KRO

### Existing Helm Chart (values.yaml)

```yaml
# Nginx Helm chart values.yaml
replicaCount: 2

image:
  repository: nginx
  tag: 1.21.0
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  hosts:
    - host: example.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 50m
    memory: 64Mi
```

### KRO Custom Resource Definition

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: nginxapps.kro.example.com
spec:
  group: kro.example.com
  names:
    kind: NginxApp
    listKind: NginxAppList
    plural: nginxapps
    singular: nginxapp
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
              properties:
                replicas:
                  type: integer
                  default: 1
                image:
                  type: object
                  properties:
                    repository:
                      type: string
                    tag:
                      type: string
                    pullPolicy:
                      type: string
                      enum: [Always, IfNotPresent, Never]
                service:
                  type: object
                  properties:
                    type:
                      type: string
                      enum: [ClusterIP, NodePort, LoadBalancer]
                    port:
                      type: integer
                ingress:
                  type: object
                  properties:
                    enabled:
                      type: boolean
                    hosts:
                      type: array
                      items:
                        type: object
                        properties:
                          host:
                            type: string
                          paths:
                            type: array
                            items:
                              type: object
                              properties:
                                path:
                                  type: string
                                pathType:
                                  type: string
                resources:
                  type: object
                  properties:
                    limits:
                      type: object
                      x-kubernetes-preserve-unknown-fields: true
                    requests:
                      type: object
                      x-kubernetes-preserve-unknown-fields: true
```

### KRO Custom Resource Instance

```yaml
apiVersion: kro.example.com/v1
kind: NginxApp
metadata:
  name: my-nginx
spec:
  replicas: 2
  image:
    repository: nginx
    tag: 1.21.0
    pullPolicy: IfNotPresent
  service:
    type: ClusterIP
    port: 80
  ingress:
    enabled: true
    hosts:
      - host: example.com
        paths:
          - path: /
            pathType: Prefix
  resources:
    limits:
      cpu: 100m
      memory: 128Mi
    requests:
      cpu: 50m
      memory: 64Mi
```

### KRO Controller Implementation (Core Logic)

```go
func (r *NginxAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := log.FromContext(ctx)

    // Get NginxApp CR
    var nginxApp krov1.NginxApp
    if err := r.Get(ctx, req.NamespacedName, &nginxApp); err != nil {
        return ctrl.Result{}, client.IgnoreNotFound(err)
    }

    // 1. Reconcile Deployment
    deployment := &appsv1.Deployment{
        ObjectMeta: metav1.ObjectMeta{
            Name:      nginxApp.Name,
            Namespace: nginxApp.Namespace,
        },
    }

    _, err := ctrl.CreateOrUpdate(ctx, r.Client, deployment, func() error {
        // Set owner reference
        if err := ctrl.SetControllerReference(&nginxApp, deployment, r.Scheme); err != nil {
            return err
        }

        // Update Deployment spec
        replicas := int32(nginxApp.Spec.Replicas)
        deployment.Spec.Replicas = &replicas

        // Set labels
        labels := map[string]string{"app": nginxApp.Name}
        deployment.Spec.Selector = &metav1.LabelSelector{MatchLabels: labels}

        // Set pod template
        deployment.Spec.Template.ObjectMeta.Labels = labels
        deployment.Spec.Template.Spec.Containers = []corev1.Container{
            {
                Name:            "nginx",
                Image:           fmt.Sprintf("%s:%s", nginxApp.Spec.Image.Repository, nginxApp.Spec.Image.Tag),
                ImagePullPolicy: corev1.PullPolicy(nginxApp.Spec.Image.PullPolicy),
                Ports: []corev1.ContainerPort{
                    {
                        ContainerPort: nginxApp.Spec.Service.Port,
                    },
                },
                Resources: corev1.ResourceRequirements{
                    Limits:   convertResourceList(nginxApp.Spec.Resources.Limits),
                    Requests: convertResourceList(nginxApp.Spec.Resources.Requests),
                },
            },
        }

        return nil
    })

    if err != nil {
        return ctrl.Result{}, err
    }

    // 2. Reconcile Service
    // 3. Reconcile Ingress (omitted)

    return ctrl.Result{}, nil
}
```

## Conclusion

Migration from Helm to KRO is an important step toward transitioning to a Kubernetes-native approach. This enables more declarative, extensible, and GitOps-friendly application management. Especially for complex applications, KRO provides more fine-grained control and improved version management.

The migration process requires additional initial work, but provides significant benefits in terms of long-term maintenance and operations. Through a gradual migration approach, you can minimize risk while leveraging the benefits of KRO.
