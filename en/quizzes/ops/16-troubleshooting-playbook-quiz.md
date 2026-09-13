# Troubleshooting Playbook Quiz

> **Related Document**: [Kubernetes/EKS Troubleshooting Playbook](../../ops/16-troubleshooting-playbook.md)

## Multiple Choice Questions

### 1. FailedScheduling reports one CPU failure, one memory failure, six affinity failures, and eight taint failures. Which interpretation is correct?

- A) Reason counts can overlap; compare individual node states
- B) Exactly the same one node must be short of CPU and memory
- C) All fifteen nodes lack CPU
- D) The scheduler evaluated no nodes

<details>
<summary>Show Answer</summary>

**Answer: A) Reason counts can overlap; compare individual node states**

The scheduler can aggregate multiple reasons per node. Counts alone do not partition nodes into mutually exclusive sets or identify a particular node. Check nodeName and PodScheduled to distinguish scheduling from image/CNI initialization waits.

</details>

### 2. An ECR image pull on an ordinary EC2 worker fails with 401 Unauthorized. What should be checked first?

- A) Docker Hub rate limits
- B) The kubelet image credential path and node role ECR permissions
- C) The container liveness path
- D) The application S3 bucket name

<details>
<summary>Show Answer</summary>

**Answer: B) The kubelet image credential path and node role ECR permissions**

Do not confuse application IRSA with the image-pull identity. Fargate uses the pod execution role. crictl pull does not automatically reuse kubelet credential providers or imagePullSecrets, so it is not an equivalent authentication test.

</details>

### 3. A container has termination reason OOMKilled and exit code 137. What is the appropriate next step?

- A) A long runtime proves a memory leak
- B) Inspect container limits, node pressure, memory time series, and kernel events
- C) Always double the limit immediately
- D) Ignore it as a graceful SIGTERM exit

<details>
<summary>Show Answer</summary>

**Answer: B) Inspect container limits, node pressure, memory time series, and kernel events**

137 commonly represents SIGKILL (128+9); OOMKilled adds evidence of OOM. This does not alone prove a leak or exclusively a container-limit failure. A different reason with 137 needs separate investigation. SIGTERM handling can also produce exit codes other than 143 depending on the application.

</details>

### 4. An IP appears in the ENDPOINTS column for an EndpointSlice. What can you conclude?

- A) Every pod is Ready
- B) Service requests must succeed
- C) The address exists; inspect ready, serving, and terminating separately
- D) All NetworkPolicies allow traffic

<details>
<summary>Show Answer</summary>

**Answer: C) The address exists; inspect ready, serving, and terminating separately**

A not-ready pod can appear with ready=false. Container READY counts also differ from the Pod Ready condition. Missing addresses call for checking selectors, namespaces, and management; selectorless Services can need manually managed EndpointSlices.

</details>

### 5. Which automatic taint corresponds to DiskPressure=True?

- A) node.kubernetes.io/unreachable
- B) node.kubernetes.io/not-ready
- C) node.kubernetes.io/disk-pressure
- D) node.kubernetes.io/memory-pressure

<details>
<summary>Show Answer</summary>

**Answer: C) node.kubernetes.io/disk-pressure**

A node can remain Ready while pressure prevents new scheduling. Inspect inodes as well as free bytes and filesystem layout. Ready=Unknown relates to unreachable; Ready=False relates to not-ready.

</details>

### 6. A PVC uses a WaitForFirstConsumer StorageClass and no consuming pod exists yet. What is the correct interpretation?

- A) It must be a CSI IAM error
- B) A StorageClass named gp3 must be wrong
- C) It can be normal: binding/provisioning waits for the consumer’s scheduling constraints
- D) Delete the PV immediately

<details>
<summary>Show Answer</summary>

**Answer: C) It can be normal: binding/provisioning waits for the consumer’s scheduling constraints**

Behavior depends on volumeBindingMode, not the StorageClass name. The API default is Immediate, so inspect the real value. If the consumer is also Pending, check FailedScheduling and topology constraints. PVC deletion is not the default diagnostic action.

</details>

### 7. An IRSA annotation was added to a service account after the pod was created; the old pod has no injected fields. What next?

- A) Recreate the cluster
- B) Check serviceAccountName and webhook configuration, then recreate pods with impact considered
- C) Grant AdministratorAccess to the node role
- D) Wait for the existing environment to change regardless of service account

<details>
<summary>Show Answer</summary>

**Answer: B) Check serviceAccountName and webhook configuration, then recreate pods with impact considered**

Injection happens at Pod creation; existing pods are not automatically modified. Verify injection and the actual caller after recreation. Another SDK credential provider can take precedence, and node-role fallback is unavailable when IMDS access is blocked.

</details>

### 8. Karpenter reports all available instance types exceed limits for nodepool. What does this mean?

- A) It can occur only when current usage exactly equals the limit
- B) Adding any candidate instance would exceed remaining NodePool headroom
- C) No EC2 instance type exists in the Region
- D) The pod must lack a toleration

<details>
<summary>Show Answer</summary>

**Answer: B) Adding any candidate instance would exceed remaining NodePool headroom**

With current CPU 7, limit 8, and a smallest candidate of 2 CPUs, the error can occur below the limit. Also check other resource limits, DaemonSet overhead, and requirements. A Nominated event does not prove node or pod readiness.

</details>

### 9. In secondary-IP mode, WARM_IP_TARGET=3, MINIMUM_IP_TARGET=6, and one IP is in use. Which interpretation is correct?

- A) Total IPs must be four
- B) Satisfying both targets can require six total and five spare
- C) MINIMUM_IP_TARGET means at least six spare IPs
- D) Too many pods proves subnet exhaustion

<details>
<summary>Show Answer</summary>

**Answer: B) Satisfying both targets can require six total and five spare**

Warm targets spare addresses; minimum is the total in-use-plus-spare floor. IPAM reconciliation, ENI limits, and prefix allocation granularity affect actual counts. Positive IP targets take precedence over WARM_ENI_TARGET. Prefix mode needs supported instances and contiguous /28 blocks; diagnose max-pods separately from real IP exhaustion.

</details>
