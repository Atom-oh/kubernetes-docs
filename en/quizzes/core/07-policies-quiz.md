# Policies Quiz

This quiz tests your understanding of Kubernetes policy concepts including resource quotas, limit ranges, pod security policies, and network policies.

## Multiple Choice Questions

1. What is the main purpose of ResourceQuota in Kubernetes?
   * A) Limiting pod CPU and memory usage
   * B) Limiting resource creation within a namespace
   * C) Monitoring cluster-wide resource usage
   * D) Managing node resource allocation

<details>

<summary>Show Answer</summary>

**Answer: B) Limiting resource creation within a namespace**

**Explanation:** ResourceQuota limits the total amount of resources that can be created within a namespace. This includes not only computing resources like CPU and memory but also the number of objects such as pods, services, and configmaps. Using ResourceQuota prevents one team from monopolizing all cluster resources.

</details>

2. What is the main function of LimitRange?
   * A) Limiting total namespace resource usage
   * B) Setting default resource requests and limits for individual containers
   * C) Distributing resources between cluster nodes
   * D) Restricting network communication between pods

<details>

<summary>Show Answer</summary>

**Answer: B) Setting default resource requests and limits for individual containers**

**Explanation:** LimitRange defines resource constraints for pods or containers within a namespace. This allows setting default resource requests and limits, or enforcing minimum/maximum resource usage. LimitRange applies to individual resources, while ResourceQuota applies to the entire namespace.

</details>

3. After PodSecurityPolicy (PSP) was removed in Kubernetes v1.25, what mechanism replaced it?
   * A) PodSecurityStandards
   * B) PodSecurityContext
   * C) PodSecurityAdmission
   * D) SecurityContextConstraints

<details>

<summary>Show Answer</summary>

**Answer: C) PodSecurityAdmission**

**Explanation:** PodSecurityPolicy (PSP) was removed in Kubernetes v1.25, and PodSecurityAdmission replaced it. This is a built-in admission controller based on Pod Security Standards, providing three policy levels: Privileged, Baseline, and Restricted. PodSecurityContext is used to configure security settings at the pod level, and SecurityContextConstraints is a similar mechanism used in OpenShift.

</details>

4. What CANNOT be done using NetworkPolicy?
   * A) Restricting traffic to pods from a specific namespace only
   * B) Restricting traffic to a specific IP CIDR range only
   * C) Restricting traffic to a specific port only
   * D) Inspecting payload content of specific protocols

<details>

<summary>Show Answer</summary>

**Answer: D) Inspecting payload content of specific protocols**

**Explanation:** NetworkPolicy provides L3/L4 level firewall policies that control communication between pods. This allows restricting traffic based on specific namespaces, labels, IP CIDR ranges, ports, etc. However, NetworkPolicy cannot perform L7 level inspection (e.g., HTTP headers, payload content). For such functionality, you need to use a service mesh (e.g., Istio) or API gateway.

</details>

5. What is the main purpose of RBAC (Role-Based Access Control) in Kubernetes?
   * A) Controlling network communication between pods
   * B) Managing permissions for users and service accounts
   * C) Limiting resource usage
   * D) Setting pod scheduling policies

<details>

<summary>Show Answer</summary>

**Answer: B) Managing permissions for users and service accounts**

**Explanation:** RBAC (Role-Based Access Control) is a mechanism for controlling access to the Kubernetes API. Through this, you can define what operations users, groups, or service accounts can perform within the cluster. RBAC manages permissions using resources such as Role, ClusterRole, RoleBinding, and ClusterRoleBinding.

</details>

6. Which is the most restrictive of the three policy levels in Pod Security Standards?
   * A) Privileged
   * B) Baseline
   * C) Restricted
   * D) Enforced

<details>

<summary>Show Answer</summary>

**Answer: C) Restricted**

**Explanation:** Pod Security Standards define three policy levels:

* Privileged: No restrictions, all privileges allowed
* Baseline: Prevents known privilege escalation paths
* Restricted: Most restrictive policy with enhanced security settings applied

The Restricted policy is the most restrictive, following the principle of least privilege and applying security best practices. This policy prohibits privileged containers, host namespace sharing, host path mounts, and more.

</details>

7. What is the role of AdmissionController in Kubernetes?
   * A) User authentication
   * B) Monitoring resource usage
   * C) Validating and modifying API requests
   * D) Pod scheduling

<details>

<summary>Show Answer</summary>

**Answer: C) Validating and modifying API requests**

**Explanation:** AdmissionController is a plugin that intercepts and validates or modifies requests to the Kubernetes API server after they pass authentication and authorization, but before objects are stored in persistent storage. This allows cluster administrators to apply policies for resource creation and modification. For example, PodSecurityAdmission, ResourceQuota, and LimitRanger are implemented as AdmissionControllers.

</details>

8. What is the main function of OPA (Open Policy Agent) Gatekeeper in Kubernetes?
   * A) Cluster monitoring and logging
   * B) Policy-based resource management and validation
   * C) Auto scaling
   * D) Service mesh management

<details>

<summary>Show Answer</summary>

**Answer: B) Policy-based resource management and validation**

**Explanation:** OPA Gatekeeper is an extensible solution for applying policies to Kubernetes clusters. It's based on OPA (Open Policy Agent) and uses CustomResourceDefinitions (CRDs) to define and apply policies. Gatekeeper operates as an AdmissionWebhook to verify that resources created or modified in the cluster comply with defined policies. This enables applying various policies such as security policies, resource limits, and naming conventions.

</details>

9. When creating a pod without specifying resource requests and limits in a namespace with ResourceQuota applied, what happens?
   * A) Pod is created with default resource requests and limits
   * B) Pod creation is rejected
   * C) Pod is created but not scheduled
   * D) Pod is created and can use unlimited resources

<details>

<summary>Show Answer</summary>

**Answer: B) Pod creation is rejected**

**Explanation:** When ResourceQuota is applied to a namespace and quotas are set for computing resources like CPU and memory, all containers in that namespace must explicitly specify resource requests and limits. Otherwise, the API server rejects the pod creation request. This is to accurately track and limit resource usage in namespaces with quotas applied.

</details>

10. What is the main purpose of PriorityClass in Kubernetes?
    * A) Defining pod scheduling priority
    * B) Setting namespace resource allocation priority
    * C) Determining API request processing priority
    * D) Setting node importance levels

<details>

<summary>Show Answer</summary>

### Short Answer Questions

1. Explain the main differences between ResourceQuota and LimitRange.
2. Explain the three policy levels (Privileged, Baseline, Restricted) of Pod Security Standards and their characteristics.
3. Explain how to restrict pods in a specific namespace to communicate only with specific pods in another namespace using NetworkPolicy.
4. Explain three policy examples that can be implemented using OPA Gatekeeper in Kubernetes.
5. Explain how to ensure availability of important workloads using PriorityClass in Kubernetes.

### Hands-on Questions

1. Create a ResourceQuota that meets the following requirements:
   * Namespace: team-a
   * Maximum 10 pods
   * Maximum 5 services
   * Total CPU requests: 4 cores
   * Total memory requests: 8Gi
2. Create a LimitRange that meets the following requirements:
   * Namespace: team-b
   * Container default request: CPU 100m, Memory 256Mi
   * Container default limit: CPU 200m, Memory 512Mi
   * Container maximum limit: CPU 1 core, Memory 2Gi
3. Create a NetworkPolicy that meets the following requirements:
   * Namespace: web
   * Pods with app label 'frontend' can only communicate with pods with app label 'backend'
   * Backend pods allow communication only on port 8080
4. Create a PriorityClass and a pod using it with the following requirements:
   * PriorityClass name: high-priority
   * Priority value: 100000
   * Description: "For critical production workloads"
   * Pod name: critical-app
   * Image: nginx
5. Apply the following Pod Security settings:
   * Namespace: restricted-ns
   * Mode: enforce
   * Level: restricted

### Advanced Topics

1. Explain the differences between OPA Gatekeeper and Kyverno in Kubernetes and their respective pros and cons.
2. Explain the main differences between Pod Security Admission and the previous PodSecurityPolicy (PSP) in Kubernetes.

</details>
