# Troubleshooting Playbook Quiz

> **Related Document**: [Kubernetes/EKS Troubleshooting Playbook](../../ops/16-troubleshooting-playbook.md)

## Multiple Choice Questions

### 1. A `Pending` pod shows the following `FailedScheduling` event. Which reading of the message is correct?

```
0/15 nodes are available: 1 Insufficient cpu, 1 Insufficient memory,
6 node(s) didn't match Pod's node affinity/selector, 8 node(s) had untolerated taint(s).
```

- A) All 15 nodes are short of CPU and memory
- B) Only one node is eligible for this pod, and that node lacks CPU and memory
- C) The scheduler is broken and could not evaluate any node
- D) Scheduling failed because 8 nodes have too many pods (`Too many pods`)

<details>
<summary>Show Answer</summary>

**Answer: B) Only one node is eligible for this pod, and that node lacks CPU and memory**

**Explanation:**
The scheduler aggregates the rejection reason per node. 8 nodes were rejected by taints with no matching toleration, 6 by a nodeSelector/affinity label mismatch, and the one remaining node lacked CPU and memory. In other words, exactly one node satisfies the scheduling constraints and it is full — so you either widen the toleration/labels or add nodes that satisfy them (with Karpenter, the label key must appear in the NodePool requirements).

</details>

### 2. A pod using a private ECR image is in `ImagePullBackOff`, and the `describe` events show `Failed to pull image "...dkr.ecr...": ... 401 Unauthorized`. What should you suspect first?

- A) An image tag typo
- B) The node IAM role lacks ECR pull permission (`AmazonEC2ContainerRegistryPullOnly` or `ReadOnly`)
- C) The Docker Hub rate limit (`toomanyrequests`)
- D) A private subnet with no NAT/VPC endpoints

<details>
<summary>Show Answer</summary>

**Answer: B) The node IAM role lacks ECR pull permission (`AmazonEC2ContainerRegistryPullOnly` or `ReadOnly`)**

**Explanation:**
What follows `Failed to pull image` is the diagnosis. `401 Unauthorized` / `no basic auth credentials` means registry authentication failed; for ECR the kubelet authenticates with the node IAM role, so check that role's ECR pull permission. A tag typo shows up as `not found` / `manifest unknown`, a network-path problem as `dial tcp ... i/o timeout`, and the Docker Hub limit as `toomanyrequests`.

</details>

### 3. A `CrashLoopBackOff` pod's `lastState.terminated` shows `Reason: OOMKilled`, `Exit Code: 137`. Which statement is correct?

- A) The app detected an error itself and exited with code 1
- B) The kernel sent SIGKILL because the memory limit was exceeded; raise the limit or fix the memory leak
- C) It received SIGTERM and shut down gracefully, so no action is needed
- D) The image architecture (arm64/amd64) does not match the node

<details>
<summary>Show Answer</summary>

**Answer: B) The kernel sent SIGKILL because the memory limit was exceeded; raise the limit or fix the memory leak**

**Explanation:**
Exit code 137 is SIGKILL (128+9). With Reason `OOMKilled` the kernel OOM killer terminated the container for exceeding its memory limit; the same 137 with Reason `Error` is a SIGKILL for another reason, such as a liveness failure where the container did not exit within `terminationGracePeriodSeconds`. A graceful SIGTERM exit is 143, and an architecture mismatch appears as 126 under a shell entrypoint (`cannot execute binary file: Exec format error`) or as Reason `StartError` when the image execs the binary directly. Read the logs from just before the crash with `kubectl logs <pod> -c <container> --previous`.

</details>

### 4. All pods are `1/1 Running`, but requests never reach the Service. The ENDPOINTS column of `kubectl get endpointslices -l kubernetes.io/service-name=<svc>` is empty. What is the most likely cause?

- A) CoreDNS pods are down, so name resolution fails
- B) The Service `selector` does not match the pod labels
- C) `targetPort` differs from the port the container listens on
- D) A NetworkPolicy blocks ingress

<details>
<summary>Show Answer</summary>

**Answer: B) The Service `selector` does not match the pod labels**

**Explanation:**
An EndpointSlice lists the IPs of **Ready pods** matched by the Service selector. If every pod is Ready and the slice is still empty, the selector and the pod labels differ (in Helm charts, `selectorLabels` and `podLabels` drifting apart is a common culprit). A wrong `targetPort` shows IPs plus `connection refused`, a NetworkPolicy block shows IPs plus timeouts, and a CoreDNS outage shows `NXDOMAIN`/resolution failures. On Kubernetes 1.33+ `kubectl get endpoints` prints a deprecation warning, so check EndpointSlices instead.

</details>

### 5. A node's conditions show `DiskPressure=True (KubeletHasDiskPressure)`. Which taint does the node controller (kube-controller-manager) add to the node automatically?

- A) `node.kubernetes.io/unreachable`
- B) `node.kubernetes.io/not-ready`
- C) `node.kubernetes.io/disk-pressure`
- D) `node.kubernetes.io/memory-pressure`

<details>
<summary>Show Answer</summary>

**Answer: C) `node.kubernetes.io/disk-pressure`**

**Explanation:**
Each node condition has a matching automatic taint: `DiskPressure` → `node.kubernetes.io/disk-pressure`, `MemoryPressure` → `node.kubernetes.io/memory-pressure`, `PIDPressure` → `node.kubernetes.io/pid-pressure`, `Ready=False` → `node.kubernetes.io/not-ready`, and `Ready=Unknown` (the kubelet stopped posting status, reason `NodeStatusUnknown`) → `node.kubernetes.io/unreachable`. That is why a node can be `Ready` while new pods avoid it with `node(s) had untolerated taint(s)`. DiskPressure is commonly caused by the image cache and container logs filling the root volume, and pods are `Evicted` with `The node was low on resource: ephemeral-storage`.

</details>

### 6. A PVC is `Pending` and `describe pvc` shows only `WaitForFirstConsumer: waiting for first consumer to be created before binding`. No pod that uses this PVC has been deployed yet. What is the correct call?

- A) The StorageClass name is misspelled; check it with `kubectl get sc`
- B) The EBS CSI controller lacks IAM permission
- C) This is normal — `volumeBindingMode: WaitForFirstConsumer` defers volume creation until a pod is scheduled
- D) The PV is in another AZ, causing a `volume node affinity conflict`

<details>
<summary>Show Answer</summary>

**Answer: C) This is normal — `volumeBindingMode: WaitForFirstConsumer` defers volume creation until a pod is scheduled**

**Explanation:**
The `gp2` StorageClass that EKS creates by default uses the `WaitForFirstConsumer` binding mode. A `gp3` StorageClass you create for the EBS CSI driver only does so if you set `volumeBindingMode: WaitForFirstConsumer` explicitly — the API default is `Immediate` — and the `gp3` class on the verification cluster does, as the `kubectl get storageclass` output in the playbook shows. The delay is intentional: the EBS volume is created in the AZ where the pod ends up being scheduled, so a PVC that stays `Pending` while no pod uses it is not a problem. A StorageClass typo appears as `storageclass.storage.k8s.io "<name>" not found`, missing IAM permission as `ProvisioningFailed` + `UnauthorizedOperation`/`AccessDenied`, and an AZ mismatch as `volume node affinity conflict` in the pod's `FailedScheduling` event.

</details>

### 7. AWS API calls from inside a pod are `AccessDenied`, and the denied principal is the node IAM role rather than the service account role. `kubectl get sa` shows the `eks.amazonaws.com/role-arn` annotation, but the pod env has no `AWS_ROLE_ARN`/`AWS_WEB_IDENTITY_TOKEN_FILE`. What are the cause and fix?

- A) The IAM role's permission policy is insufficient → add actions to the policy
- B) The annotation was added **after** the pod was created, so the webhook never injected credentials → `kubectl rollout restart`
- C) There is no OIDC provider → recreate the cluster
- D) The EKS Pod Identity agent is down → restart the agent

<details>
<summary>Show Answer</summary>

**Answer: B) The annotation was added after the pod was created, so the webhook never injected credentials → `kubectl rollout restart`**

**Explanation:**
IRSA works by having pod-identity-webhook inject the `AWS_ROLE_ARN` and `AWS_WEB_IDENTITY_TOKEN_FILE` env (plus the token volume) **at pod creation time**. If there is no trace of injection, the pod was created before the annotation existed or the SA name differs, and the SDK falls back to the node role because it finds no credentials. Recreating the pods fixes it. An insufficient permission policy (A) looks different — env is fine but a specific API is denied — and Pod Identity (D) is recognizable by the `AWS_CONTAINER_CREDENTIALS_FULL_URI` env.

</details>

### 8. A pod is `Pending`, no new NodeClaim appears, and a Karpenter event says `all available instance types exceed limits for nodepool "graviton"`. What is the cause?

- A) The pod's nodeSelector label key is not in the NodePool requirements
- B) There is no toleration for the NodePool taint
- C) The NodePool `spec.limits` (cpu/memory) has already been reached
- D) EC2 has no capacity in that AZ (`InsufficientInstanceCapacity`)

<details>
<summary>Show Answer</summary>

**Answer: C) The NodePool `spec.limits` (cpu/memory) has already been reached**

**Explanation:**
Karpenter walks every NodePool for a pod and records why each was rejected as an event. `exceed limits` means any instance it could add would push the NodePool past its `spec.limits`; `kubectl get nodepool -o custom-columns=...spec.limits.cpu,...status.resources.cpu` shows the limit and usage equal. A missing label key appears as `label "<key>" does not have known values`, a missing toleration as `did not tolerate <key>=<value>:NoSchedule`, and missing EC2 capacity as `InsufficientInstanceCapacity` in the Karpenter controller logs.

</details>

### 9. Pods on an EKS node stall in `ContainerCreating` with the event `FailedCreatePodSandBox ... plugin type="aws-cni" ... failed to assign an IP address to container`. The subnet's `AvailableIpAddressCount` is in the single digits, and `aws-node` runs with the VPC CNI defaults (`WARM_ENI_TARGET=1`, `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` unset). Which statement is correct?

- A) The `WARM_ENI_TARGET=1` default keeps one whole spare ENI's worth of IPs attached to every node, so the subnet runs out far sooner than the pod count suggests; setting `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` shrinks that warm pool because they take precedence over the warm-ENI rule
- B) Setting `WARM_ENI_TARGET=0` is enough, because `WARM_IP_TARGET` is ignored while `WARM_ENI_TARGET` is set
- C) `ENABLE_PREFIX_DELEGATION=true` adds IPs by attaching more ENIs, so it works on any instance family
- D) `FailedCreatePodSandBox` means the scheduler could not find a node, so this is the same failure as `Too many pods`

<details>
<summary>Show Answer</summary>

**Answer: A) The `WARM_ENI_TARGET=1` default keeps one whole spare ENI's worth of IPs attached to every node, so the subnet runs out far sooner than the pod count suggests; setting `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` shrinks that warm pool because they take precedence over the warm-ENI rule**

**Explanation:**
With the default `WARM_ENI_TARGET=1` alone, ipamd keeps one full spare ENI attached to each node (15 IPs per ENI on an m5.xlarge), so in a small subnet the pre-claimed IPs are exhausted long before the pods are. Once `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` are set they override the warm-ENI rule — the playbook's verification cluster uses `WARM_IP_TARGET=3`, `MINIMUM_IP_TARGET=6`, so a node keeps only 3 spare IPs beyond what its pods use and never fewer than 6 IPs allocated in total (`MINIMUM_IP_TARGET` bounds the total, in-use plus spare — not the spare count). B has the precedence backwards. Prefix delegation (C) assigns /28 prefixes to the existing ENI slots rather than adding ENIs, and it requires Nitro-based instances plus a max-pods recalculation. D confuses two symptoms: `FailedCreatePodSandBox` fires after scheduling, when the kubelet asks the CNI for an IP on a node that has none left; `Too many pods` is the scheduler rejecting the node because `allocatable.pods` is already reached — both share the root cause (no IP to hand out) but occur at different stages.

</details>
