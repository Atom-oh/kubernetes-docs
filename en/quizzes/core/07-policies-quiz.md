# Policies Quiz

This quiz tests your understanding of Kubernetes policy concepts including resource quotas, limit ranges, pod security policies, and network policies.

## Multiple Choice Questions

1. What is the main purpose of ResourceQuota in Kubernetes?
   - A) Limiting pod CPU and memory usage
   - B) Limiting resource creation within a namespace
   - C) Monitoring cluster-wide resource usage
   - D) Managing node resource allocation
   
<details>
<summary>Show Answer</summary>

**Answer: B) Limiting resource creation within a namespace**

**Explanation:**
ResourceQuota limits the total amount of resources that can be created within a namespace. This includes not only computing resources like CPU and memory but also the number of objects such as pods, services, and configmaps. Using ResourceQuota prevents one team from monopolizing all cluster resources.
</details>

2. What is the main function of LimitRange?
   - A) Limiting total namespace resource usage
   - B) Setting default resource requests and limits for individual containers
   - C) Distributing resources between cluster nodes
   - D) Restricting network communication between pods
   
<details>
<summary>Show Answer</summary>

**Answer: B) Setting default resource requests and limits for individual containers**

**Explanation:**
LimitRange defines resource constraints for pods or containers within a namespace. This allows setting default resource requests and limits, or enforcing minimum/maximum resource usage. LimitRange applies to individual resources, while ResourceQuota applies to the entire namespace.
</details>

3. After PodSecurityPolicy (PSP) was removed in Kubernetes v1.25, what mechanism replaced it?
   - A) PodSecurityStandards
   - B) PodSecurityContext
   - C) PodSecurityAdmission
   - D) SecurityContextConstraints
   
<details>
<summary>Show Answer</summary>

**Answer: C) PodSecurityAdmission**

**Explanation:**
PodSecurityPolicy (PSP) was removed in Kubernetes v1.25, and PodSecurityAdmission replaced it. This is a built-in admission controller based on Pod Security Standards, providing three policy levels: Privileged, Baseline, and Restricted. PodSecurityContext is used to configure security settings at the pod level, and SecurityContextConstraints is a similar mechanism used in OpenShift.
</details>

4. What CANNOT be done using NetworkPolicy?
   - A) Restricting traffic to pods from a specific namespace only
   - B) Restricting traffic to a specific IP CIDR range only
   - C) Restricting traffic to a specific port only
   - D) Inspecting payload content of specific protocols
   
<details>
<summary>Show Answer</summary>

**Answer: D) Inspecting payload content of specific protocols**

**Explanation:**
NetworkPolicy provides L3/L4 level firewall policies that control communication between pods. This allows restricting traffic based on specific namespaces, labels, IP CIDR ranges, ports, etc. However, NetworkPolicy cannot perform L7 level inspection (e.g., HTTP headers, payload content). For such functionality, you need to use a service mesh (e.g., Istio) or API gateway.
</details>

5. What is the main purpose of RBAC (Role-Based Access Control) in Kubernetes?
   - A) Controlling network communication between pods
   - B) Managing permissions for users and service accounts
   - C) Limiting resource usage
   - D) Setting pod scheduling policies
   
<details>
<summary>Show Answer</summary>

**Answer: B) Managing permissions for users and service accounts**

**Explanation:**
RBAC (Role-Based Access Control) is a mechanism for controlling access to the Kubernetes API. Through this, you can define what operations users, groups, or service accounts can perform within the cluster. RBAC manages permissions using resources such as Role, ClusterRole, RoleBinding, and ClusterRoleBinding.
</details>

6. Which is the most restrictive of the three policy levels in Pod Security Standards?
   - A) Privileged
   - B) Baseline
   - C) Restricted
   - D) Enforced
   
<details>
<summary>Show Answer</summary>

**Answer: C) Restricted**

**Explanation:**
Pod Security Standards define three policy levels:
- Privileged: No restrictions, all privileges allowed
- Baseline: Prevents known privilege escalation paths
- Restricted: Most restrictive policy with enhanced security settings applied

The Restricted policy is the most restrictive, following the principle of least privilege and applying security best practices. This policy prohibits privileged containers, host namespace sharing, host path mounts, and more.
</details>

7. What is the role of AdmissionController in Kubernetes?
   - A) User authentication
   - B) Monitoring resource usage
   - C) Validating and modifying API requests
   - D) Pod scheduling
   
<details>
<summary>Show Answer</summary>

**Answer: C) Validating and modifying API requests**

**Explanation:**
AdmissionController is a plugin that intercepts and validates or modifies requests to the Kubernetes API server after they pass authentication and authorization, but before objects are stored in persistent storage. This allows cluster administrators to apply policies for resource creation and modification. For example, PodSecurityAdmission, ResourceQuota, and LimitRanger are implemented as AdmissionControllers.
</details>

8. What is the main function of OPA (Open Policy Agent) Gatekeeper in Kubernetes?
   - A) Cluster monitoring and logging
   - B) Policy-based resource management and validation
   - C) Auto scaling
   - D) Service mesh management
   
<details>
<summary>Show Answer</summary>

**Answer: B) Policy-based resource management and validation**

**Explanation:**
OPA Gatekeeper is an extensible solution for applying policies to Kubernetes clusters. It's based on OPA (Open Policy Agent) and uses CustomResourceDefinitions (CRDs) to define and apply policies. Gatekeeper operates as an AdmissionWebhook to verify that resources created or modified in the cluster comply with defined policies. This enables applying various policies such as security policies, resource limits, and naming conventions.
</details>

9. When creating a pod without specifying resource requests and limits in a namespace with ResourceQuota applied, what happens?
   - A) Pod is created with default resource requests and limits
   - B) Pod creation is rejected
   - C) Pod is created but not scheduled
   - D) Pod is created and can use unlimited resources
   
<details>
<summary>Show Answer</summary>

**Answer: B) Pod creation is rejected**

**Explanation:**
When ResourceQuota is applied to a namespace and quotas are set for computing resources like CPU and memory, all containers in that namespace must explicitly specify resource requests and limits. Otherwise, the API server rejects the pod creation request. This is to accurately track and limit resource usage in namespaces with quotas applied.
</details>

10. What is the main purpose of PriorityClass in Kubernetes?
    - A) Defining pod scheduling priority
    - B) Setting namespace resource allocation priority
    - C) Determining API request processing priority
    - D) Setting node importance levels
    
<details>
<summary>Show Answer</summary>

**Answer: A) Defining pod scheduling priority**

**Explanation:**
PriorityClass defines the scheduling priority of pods. When resources are scarce, higher-priority pods are scheduled before lower-priority ones, and can preempt lower-priority pods if necessary.
</details>

## Short Answer Questions

1. Explain the main differences between ResourceQuota and LimitRange.

<details>
<summary>Show Answer</summary>

**Answer:**
ResourceQuota limits resource usage for the entire namespace, while LimitRange sets resource constraints for individual containers or pods within a namespace.

Key differences:
1. **Scope**: ResourceQuota applies to the entire namespace, LimitRange applies to individual resources (pods, containers, etc.).
2. **Purpose**: ResourceQuota limits total namespace resource usage, while LimitRange controls individual resource usage through default settings, minimum/maximum limits, etc.
3. **Enforcement**: When ResourceQuota is set, resource creation exceeding the quota is rejected. LimitRange applies defaults when resources are created or rejects if limits are exceeded.
4. **Resource types**: ResourceQuota can limit not only CPU and memory but also object counts like pods, services, and PVCs. LimitRange primarily focuses on computing resources like CPU, memory, and storage.
</details>

2. Explain the three policy levels (Privileged, Baseline, Restricted) of Pod Security Standards and their characteristics.

<details>
<summary>Show Answer</summary>

**Answer:**
Pod Security Standards define three policy levels for pod security settings:

1. **Privileged**:
   - Most open policy with almost no restrictions.
   - Allows all privileged operations.
   - Can use host namespaces, host ports, privileged containers, etc.
   - Suitable for development and administrative work, but poses significant security risks in production.

2. **Baseline**:
   - Mid-level policy that prevents known privilege escalation paths.
   - Provides a baseline level of security suitable for most workloads.
   - Restricts privileged containers and host namespace usage.
   - However, some privileged operations (e.g., host path mounts) are still allowed.

3. **Restricted**:
   - Most restrictive policy with enhanced security settings.
   - Follows the principle of least privilege and enforces security best practices.
   - Prohibits privileged containers, host namespaces, host path mounts, and privilege escalation.
   - Forces containers to run as non-root users.
   - Suitable for security-critical production workloads.
</details>

3. Explain how to restrict pods in a specific namespace to communicate only with specific pods in another namespace using NetworkPolicy.

<details>
<summary>Show Answer</summary>

**Answer:**
To restrict pods in a specific namespace to communicate only with specific pods in another namespace using NetworkPolicy:

1. **Apply NetworkPolicy to source namespace**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-specific-communication
  namespace: source-namespace  # Source namespace
spec:
  podSelector: {}  # Apply to all pods
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: destination-namespace  # Destination namespace label
      podSelector:
        matchLabels:
          app: specific-app  # Destination pod label
```

2. **Apply NetworkPolicy to destination namespace**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-specific-namespace
  namespace: destination-namespace  # Destination namespace
spec:
  podSelector:
    matchLabels:
      app: specific-app  # Destination pod label
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: source-namespace  # Source namespace label
```

For this method to work, namespaces must have appropriate labels:
```bash
kubectl label namespace source-namespace name=source-namespace
kubectl label namespace destination-namespace name=destination-namespace
```

NetworkPolicy operates in allow-list mode by default, so once these policies are applied, only explicitly allowed communication is possible and everything else is blocked.
</details>

4. Explain three policy examples that can be implemented using OPA Gatekeeper in Kubernetes.

<details>
<summary>Show Answer</summary>

**Answer:**
Policy examples that can be implemented using OPA Gatekeeper:

1. **Image Registry Restriction**:
   - Policy that forces images to only be pulled from approved registries
   - Example: Allow only company internal registries or specific trusted public registries
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sAllowedRepos
   metadata:
     name: allowed-repos
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       repos:
         - "docker.io/company/"
         - "gcr.io/trusted-project/"
   ```

2. **Enforce Resource Requests and Limits**:
   - Policy that forces all containers to have resource requests and limits set
   - Prevents resource exhaustion and ensures proper resource allocation
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sRequiredResources
   metadata:
     name: container-must-have-limits-and-requests
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       limits:
         - cpu
         - memory
       requests:
         - cpu
         - memory
   ```

3. **Prevent Privileged Containers**:
   - Policy that prohibits running privileged containers
   - Reduces security risks and ensures container isolation
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sPSPPrivilegedContainer
   metadata:
     name: prevent-privileged-containers
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
   ```

(Only three of the above need to be explained)
</details>

5. Explain how to ensure availability of important workloads using PriorityClass in Kubernetes.

<details>
<summary>Show Answer</summary>

**Answer:**
How to ensure availability of important workloads using PriorityClass:

1. **Define PriorityClass**:
   - Create PriorityClasses with various priority levels based on importance
   ```yaml
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: high-priority
   value: 1000000  # Higher value means higher priority
   globalDefault: false
   description: "This priority class should be used for critical production workloads."
   ```

2. **Assign PriorityClass to important workloads**:
   - Add PriorityClass reference to important pods
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: critical-service
   spec:
     priorityClassName: high-priority
     containers:
     - name: app
       image: critical-service:latest
   ```

3. **Leverage Preemption**:
   - When resources are scarce, higher priority pods can preempt (evict) lower priority pods and be scheduled
   - This ensures important workloads can always run

4. **Consider System Priority Classes**:
   - Kubernetes provides system priority classes like system-cluster-critical (2000000000) and system-node-critical (2000001000)
   - User-defined priority classes should generally use values lower than these

5. **Design Priority Hierarchy**:
   - Define multiple priority levels based on workload importance
   - Example: Production services (900000), Internal tools (500000), Development/Test (100000)
</details>

## Hands-on Questions

1. Create a ResourceQuota that meets the following requirements:
   - Namespace: team-a
   - Maximum 10 pods
   - Maximum 5 services
   - Total CPU requests: 4 cores
   - Total memory requests: 8Gi

<details>
<summary>Show Answer</summary>

**Answer:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-a-quota
  namespace: team-a
spec:
  hard:
    pods: "10"
    services: "5"
    requests.cpu: "4"
    requests.memory: 8Gi
```

How to apply:
```bash
# Create namespace
kubectl create namespace team-a

# Apply ResourceQuota
kubectl apply -f team-a-quota.yaml
```

Check ResourceQuota status:
```bash
kubectl describe resourcequota team-a-quota -n team-a
```
</details>

2. Create a LimitRange that meets the following requirements:
   - Namespace: team-b
   - Container default request: CPU 100m, Memory 256Mi
   - Container default limit: CPU 200m, Memory 512Mi
   - Container maximum limit: CPU 1 core, Memory 2Gi

<details>
<summary>Show Answer</summary>

**Answer:**

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: team-b-limits
  namespace: team-b
spec:
  limits:
  - default:
      cpu: 200m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    max:
      cpu: "1"
      memory: 2Gi
    type: Container
```

How to apply:
```bash
# Create namespace
kubectl create namespace team-b

# Apply LimitRange
kubectl apply -f team-b-limits.yaml
```

Check LimitRange status:
```bash
kubectl describe limitrange team-b-limits -n team-b
```
</details>

3. Create a NetworkPolicy that meets the following requirements:
   - Namespace: web
   - Pods with app label 'frontend' can only communicate with pods with app label 'backend'
   - Backend pods allow communication only on port 8080

<details>
<summary>Show Answer</summary>

**Answer:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-backend-only
  namespace: web
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-allow-frontend-only
  namespace: web
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

How to apply:
```bash
# Create namespace
kubectl create namespace web

# Apply NetworkPolicy
kubectl apply -f web-network-policies.yaml
```

Check NetworkPolicy status:
```bash
kubectl describe networkpolicy -n web
```
</details>

4. Create a PriorityClass and a pod using it with the following requirements:
   - PriorityClass name: high-priority
   - Priority value: 100000
   - Description: "For critical production workloads"
   - Pod name: critical-app
   - Image: nginx

<details>
<summary>Show Answer</summary>

**Answer:**

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 100000
globalDefault: false
description: "For critical production workloads"
---
apiVersion: v1
kind: Pod
metadata:
  name: critical-app
spec:
  priorityClassName: high-priority
  containers:
  - name: nginx
    image: nginx
```

How to apply:
```bash
kubectl apply -f high-priority-pod.yaml
```

Check PriorityClass and pod status:
```bash
kubectl get priorityclass high-priority
kubectl get pod critical-app
```
</details>

5. Apply the following Pod Security settings:
   - Namespace: restricted-ns
   - Mode: enforce
   - Level: restricted

<details>
<summary>Show Answer</summary>

**Answer:**

In Kubernetes 1.25 and above, you can apply Pod Security Standards by adding labels to the namespace:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: restricted-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

How to apply:
```bash
kubectl apply -f restricted-namespace.yaml
```

Or add labels to an existing namespace:
```bash
kubectl create namespace restricted-ns
kubectl label namespace restricted-ns \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```
</details>

## Advanced Topics

1. Explain the differences between OPA Gatekeeper and Kyverno in Kubernetes and their respective pros and cons.

<details>
<summary>Show Answer</summary>

**Answer:**

**OPA Gatekeeper vs Kyverno Comparison:**

1. **Architecture and Approach**:
   - **OPA Gatekeeper**: Based on Open Policy Agent (OPA), uses the Rego policy language. Defines policies using two CRDs: ConstraintTemplate and Constraint.
   - **Kyverno**: Uses its own policy engine, providing YAML/JSON-based policy definitions. Defines policies using a single Policy CRD.

2. **Policy Language**:
   - **OPA Gatekeeper**: Uses Rego language, powerful but has a steep learning curve.
   - **Kyverno**: Defines policies using YAML syntax similar to Kubernetes resources, more familiar to Kubernetes users.

3. **Features**:
   - **OPA Gatekeeper**: 
     - Powerful policy language for expressing complex policies
     - Can integrate data sources for external data-based decisions
     - Supports policy libraries and reusable templates
   - **Kyverno**: 
     - Built-in resource creation, modification, and validation features
     - Image verification and modification features
     - Can automatically create other resources when resources are created
     - Policy exception handling features

4. **Pros**:
   - **OPA Gatekeeper**:
     - More mature and widely adopted
     - Better suited for complex policy expression
     - Extensive documentation and examples for various use cases
     - OPA ecosystem usable outside of Kubernetes
   - **Kyverno**:
     - Easier learning curve with familiar YAML syntax
     - No separate policy language learning required
     - Built-in resource creation and modification features
     - Simpler setup and configuration

5. **Cons**:
   - **OPA Gatekeeper**:
     - Requires learning Rego language
     - Complex setup and configuration
     - Additional configuration needed for resource modification
   - **Kyverno**:
     - Relatively less mature
     - May have limitations for very complex policy expression
     - Performance may be lower compared to OPA

6. **Selection Criteria**:
   - **Choose OPA Gatekeeper when**:
     - Complex policy logic is needed
     - Already using OPA or familiar with Rego
     - Need consistent policy application across various systems
   - **Choose Kyverno when**:
     - Quick start and easy learning curve are important
     - Team is familiar with Kubernetes resource syntax
     - Resource creation and modification features are needed
     - Only simple policies are needed
</details>

2. Explain the main differences between Pod Security Admission and the previous PodSecurityPolicy (PSP) in Kubernetes.

<details>
<summary>Show Answer</summary>

**Answer:**

**Pod Security Admission vs PodSecurityPolicy (PSP) Comparison:**

1. **Implementation**:
   - **PodSecurityPolicy**: Implemented as API resource (CRD), applied through admission controller.
   - **Pod Security Admission**: Implemented as built-in admission controller, configured through namespace labels.

2. **Configuration Method**:
   - **PodSecurityPolicy**: Cluster admin must create PSP resources and bind them to users/service accounts through RBAC.
   - **Pod Security Admission**: Apply by adding labels to namespaces specifying enforcement level (enforce, audit, warn) and policy level (privileged, baseline, restricted).

3. **Policy Granularity**:
   - **PodSecurityPolicy**: Very fine-grained control possible, can individually configure various security context settings.
   - **Pod Security Admission**: Only provides three predefined policy levels (privileged, baseline, restricted), cannot individually adjust detailed settings.

4. **Ease of Use**:
   - **PodSecurityPolicy**: Complex setup requiring RBAC bindings, configuration errors are common.
   - **Pod Security Admission**: Applied with simple namespace labeling, much easier to use.

5. **Scope**:
   - **PodSecurityPolicy**: Applies to entire cluster or specific users/service accounts.
   - **Pod Security Admission**: Applies per namespace.

6. **Modes**:
   - **PodSecurityPolicy**: Binary approach of apply or not apply.
   - **Pod Security Admission**: Provides three modes (enforce, audit, warn) for gradual application.
     - enforce: Reject pod creation on violation
     - audit: Log violations to audit log
     - warn: Display warning message on violation

7. **Migration and Support**:
   - **PodSecurityPolicy**: Removed in Kubernetes v1.25.
   - **Pod Security Admission**: Available as beta since Kubernetes v1.23, fully replaced PSP in v1.25.

8. **Extensibility**:
   - **PodSecurityPolicy**: High extensibility through custom settings.
   - **Pod Security Admission**: Limited extensibility, additional tools like OPA Gatekeeper or Kyverno may be needed for finer control.
</details>
