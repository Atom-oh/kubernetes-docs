# Kubernetes/EKS Troubleshooting Playbook: Symptom → Diagnosis → Cause → Fix

> **Supported Versions**: Kubernetes 1.33+ (output verified on Amazon EKS 1.36 — control plane v1.36.2-eks-bca9cf6, platform version eks.9), Karpenter 1.4, VPC CNI v1.21, CoreDNS v1.14
> **Last Updated**: September 2, 2026

< [Previous: Zonal Cluster Operations](15-zonal-operations-guide.md) | [Table of Contents](./README.md) >

***

When the pager goes off at 3 a.m. and you open a terminal, what you need is not a concept explanation but **"the next command to type given what I see right now."** This document starts from **symptoms**, not concepts. For each symptom it bundles "what you see → what you run → what the output looks like → the most common causes and how to fix them" into one block.

The event messages and sample output shown here were captured on September 2, 2026 with `kubectl get/describe/events` against this repo's verification EKS cluster (EKS 1.36 — control plane v1.36.2-eks-bca9cf6, platform version eks.9 — with Karpenter 1.4.0, VPC CNI v1.21.1, CoreDNS v1.14.2), or are strings quoted from the official Kubernetes/AWS documentation listed under [References](#references). Only resource names have been generalized.

Deep root-cause analysis (control plane logs, CloudWatch Logs Insights queries, the eight causes of node join failure, and so on) already lives in [EKS Troubleshooting](../eks/09-eks-troubleshooting.md) and [EKS Advanced Debugging](../eks/11-eks-advanced-debugging.md). This page sits in front of those: its job is to **decide within 30 seconds which page to open**, so it links into them rather than repeating their content.

## Table of Contents

1. [30-Second Summary: Symptom → First Command → Most Common Cause](#30-second-summary-symptom--first-command--most-common-cause)
2. [Diagnostic Decision Tree](#diagnostic-decision-tree)
3. [Playbook by Symptom](#playbook-by-symptom)
4. [kubectl Diagnostic Cheat Sheet](#kubectl-diagnostic-cheat-sheet)
5. [Going Deeper: Related Documents](#going-deeper-related-documents)
6. [References](#references)

***

## 30-Second Summary: Symptom → First Command → Most Common Cause

Each symptom cell links to its playbook section below.

| Symptom (what `kubectl get pods`/`nodes` shows) | First command | Most common cause |
|---|---|---|
| [`Pending`](#1-pod-stuck-in-pending) | `kubectl describe pod <pod>` → the `FailedScheduling` message in Events | Not enough resources (`Insufficient cpu/memory`), missing toleration, nodeSelector mismatch, unbound PVC |
| [`ImagePullBackOff` / `ErrImagePull`](#2-imagepullbackoff--errimagepull) | `kubectl describe pod <pod>` → the `Failed to pull image` line | Tag typo, private registry auth (imagePullSecrets/node IAM), ECR region/account mismatch |
| [`CrashLoopBackOff`](#3-crashloopbackoff-exit-137-oomkilled-probe-failures-config-errors) | `kubectl logs <pod> --previous` + check `lastState.terminated` | App fails at startup (exit 1), `OOMKilled` (exit 137), liveness probe failure, missing ConfigMap/Secret |
| [`Running` but READY `0/1`](#4-running-but-not-ready--empty-endpoints) | `kubectl describe pod <pod>` → `Readiness probe failed` | Wrong readiness path/port, waiting on a dependency, sidecar not ready |
| [Requests never reach the Service](#5-service-is-unreachable) | `kubectl get endpointslices -l kubernetes.io/service-name=<svc>` | Selector label mismatch, wrong `targetPort`, NetworkPolicy block, CoreDNS outage |
| [Node `NotReady`](#6-node-notready--kubelet-pressure-diskpressure-memorypressure-pidpressure) | `kubectl describe node <node>` → Conditions | kubelet stopped/network partition, `DiskPressure`, `MemoryPressure`, `PIDPressure` |
| [PVC `Pending`](#7-pvc-stuck-in-pending) | `kubectl describe pvc <pvc>` → Events | `WaitForFirstConsumer` (normal wait), missing/misspelled StorageClass, AZ mismatch |
| [`AccessDenied` in app logs (AWS API)](#8-eks-irsa--pod-identity-accessdenied) | `kubectl get sa <sa> -o yaml` + pod `env \| grep AWS` | IRSA (IAM Roles for Service Accounts) annotation/trust policy error, missing Pod Identity association, pods not restarted |
| [Stuck in `ContainerCreating` + `failed to assign an IP address`](#9-eks-enivpc-cni-ip-exhaustion) | `kubectl describe pod <pod>` → `FailedCreatePodSandBox` | Subnet IP exhaustion, node max-pods reached, `aws-node` unhealthy |
| [Karpenter does not launch a node](#10-eks-karpenter-does-not-launch-a-node) | `kubectl get events -A --field-selector reason=FailedScheduling` | NodePool `limits` reached, requirements/taint mismatch, instance type restriction |

***

## Diagnostic Decision Tree

![Decision tree from "Pod not serving" through five gates — Pending, ImagePullBackOff, CrashLoopBackOff, READY 0/1, READY 1/1 but no response — each paired with its first kubectl command.](../.gitbook/assets/en-ops-16-troubleshooting-playbook-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-16-troubleshooting-playbook-0.html)

The entry point of the tree is always the same: filter to unhealthy pods across all namespaces, then read Warning events in time order.

```bash
# Pods that are neither Running nor Succeeded
kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded

# Recent Warning events (cluster-wide, chronological)
kubectl get events -A --field-selector type=Warning --sort-by=.lastTimestamp | tail -30
```

***

## Playbook by Symptom

### 1. Pod stuck in `Pending`

**Symptom**: STATUS in `kubectl get pods` is `Pending` and READY is `0/1`. No node has been assigned, so `kubectl logs` shows nothing.

**Diagnosis**: the answer is always in the last `FailedScheduling` event from `describe`. The scheduler **aggregates, per node, why each node was rejected**.

```bash
kubectl describe pod <pod> -n <ns> | sed -n '/^Events:/,$p'
```

```
Warning  FailedScheduling  default-scheduler  0/15 nodes are available: 1 Insufficient cpu, 1 Insufficient memory,
  6 node(s) didn't match Pod's node affinity/selector, 8 node(s) had untolerated taint(s).
  no new claims to deallocate, preemption: 0/15 nodes are available:
  1 No preemption victims found for incoming pod, 14 Preemption is not helpful for scheduling.
```

How to read it: of 15 nodes, 8 were rejected by taints, 6 by nodeSelector/affinity, and the 1 remaining node lacked CPU and memory. In other words, **only one node is eligible for this pod and it is full**. `no new claims to deallocate` is appended by the DRA (Dynamic Resource Allocation) plugin; ignore it for pods that do not use ResourceClaims.

**Causes and fixes**:

| Message fragment | Cause | Fix |
|---|---|---|
| `Insufficient cpu` / `Insufficient memory` | Requests exceed remaining node capacity | Right-size requests, check the autoscaler (→ [10. Karpenter](#10-eks-karpenter-does-not-launch-a-node)), inspect `Allocated resources` in `kubectl describe node` |
| `Too many pods` | Node max-pods reached (VPC CNI ENI limit) | → [9. ENI/IP exhaustion](#9-eks-enivpc-cni-ip-exhaustion) |
| `node(s) had untolerated taint(s)` | No toleration for the node taints | List taints with `kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints[*].key`, then add a toleration or adjust the NodePool |
| `node(s) didn't match Pod's node affinity/selector` | No node carries the nodeSelector/affinity label | Check `kubectl get nodes --show-labels`. With Karpenter, the key must appear in NodePool requirements or no node will be created |
| `pod has unbound immediate PersistentVolumeClaims` | The PVC is `Pending` | → [7. PVC Pending](#7-pvc-stuck-in-pending) |
| `node(s) had volume node affinity conflict` | No schedulable node in the AZ where the PV (EBS) lives | Read the PV's `nodeAffinity` zone and provide capacity in that AZ |
| `node(s) didn't match pod topology spread constraints` / `pod anti-affinity rules` | No node satisfies the spread constraint | Relax with `whenUnsatisfiable: ScheduleAnyway` or add nodes |
| No events at all | Scheduler problem, or a misspelled `schedulerName` | Check `kubectl get pod <pod> -o jsonpath='{.spec.schedulerName}'` |

### 2. `ImagePullBackOff` / `ErrImagePull`

**Symptom**: STATUS starts as `ErrImagePull`, then after a few retries becomes `ImagePullBackOff`. The kubelet's pull back-off grows up to a 5-minute cap.

**Diagnosis**:

```bash
kubectl describe pod <pod> -n <ns> | grep -A2 -E "Failed to pull|Back-off pulling"
kubectl get pod <pod> -n <ns> -o jsonpath='{range .spec.containers[*]}{.name}{"\t"}{.image}{"\n"}{end}'
kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.imagePullSecrets}'
```

```
Warning  Failed   kubelet  Failed to pull image "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/app:v1.2.3": ... not found
Warning  Failed   kubelet  Error: ErrImagePull
Normal   BackOff  kubelet  Back-off pulling image "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/app:v1.2.3"
Warning  Failed   kubelet  Error: ImagePullBackOff
```

A healthy pull leaves the pair `Pulling image "..."` → `Successfully pulled image "..." in 4.501s ...`, and an already-cached image logs `Container image "..." already present on machine`. If you see those healthy events and the pod still does not start, the image is not the problem.

**Causes and fixes**:

| What follows `Failed to pull image` | Cause | Fix |
|---|---|---|
| `not found` / `manifest unknown` | Tag typo, tag not pushed yet, wrong repository | Verify with `aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>` |
| `401 Unauthorized` / `no basic auth credentials` | Private registry authentication failed | For ECR, the node IAM role needs `AmazonEC2ContainerRegistryPullOnly` (or `ReadOnly`); for external registries check `imagePullSecrets` |
| ECR URL region/account differs from the cluster | No cross-account pull permission | Add the pulling principal to the ECR repository policy |
| `dial tcp ... i/o timeout` | Private subnet with no NAT/VPC endpoints | Check `com.amazonaws.<region>.ecr.api`, `ecr.dkr`, and the S3 gateway endpoint |
| `toomanyrequests` | Docker Hub rate limit | Mirror through an ECR pull-through cache |

To reproduce from the node itself, `kubectl debug node/<node> -it --image=busybox --profile=sysadmin`, then `chroot /host crictl pull <image>` pulls over the same path the kubelet uses (`--profile=sysadmin` gives the debug container the privileges `crictl` needs; see the [cheat sheet](#kubectl-diagnostic-cheat-sheet)).

### 3. `CrashLoopBackOff` (exit 137 `OOMKilled`, probe failures, config errors)

**Symptom**: STATUS `CrashLoopBackOff`, RESTARTS keeps climbing. The restart delay starts at 10 seconds and doubles up to a 5-minute cap, so the pod looks `Running` for a while, then dies again.

**Diagnosis**: look at three things in order — **termination reason and exit code**, **logs of the previous container**, **Events**.

```bash
# (1) Why did it die: lastState.terminated
kubectl get pod <pod> -n <ns> -o jsonpath='{range .status.containerStatuses[*]}{.name}{"\t"}restarts={.restartCount}{"\t"}reason={.lastState.terminated.reason}{"\t"}exit={.lastState.terminated.exitCode}{"\n"}{end}'

# (2) Logs right before death (the previous container, not the current one)
kubectl logs <pod> -n <ns> -c <container> --previous --tail=100

# (3) Probe/kill events
kubectl describe pod <pod> -n <ns> | sed -n '/^Events:/,$p'
```

Real output — a container with a 128Mi memory limit killed by OOM:

```
    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
      Started:      Mon, 31 Aug 2026 08:55:27 +0000
      Finished:     Tue, 01 Sep 2026 21:13:37 +0000
    Restart Count:  3
```

Read `Started` against `Finished`: this container ran for roughly 36 hours before the kill, which points to a **slow memory leak or a gradual working-set growth**, not a start-up problem. A start-up crash loop looks different — `Finished` comes seconds after `Started`, and RESTARTS climbs within minutes.

**Reading exit codes**:

| Exit Code | Reason | Meaning | Fix |
|---|---|---|---|
| `0` | `Completed` | Process exited normally — in a Deployment this means the app is not staying in the foreground | Run the entrypoint in daemon/foreground mode, or switch to a Job |
| `1` | `Error` | App exited on its own (config error, dependency connection failure) | The stack trace is in `logs --previous` |
| `126` | `Error` | Command found but not executable under a shell entrypoint — missing execute bit, or the shell reporting `cannot execute binary file: Exec format error` (architecture mismatch) | `chmod +x` in the Dockerfile; check arm64/amd64 with `kubectl get nodes -L kubernetes.io/arch` and use a multi-arch image |
| `127` | `Error` | Command not found under a shell entrypoint — path typo, or the binary was never copied into the final image stage | Compare `command`/`args` with what is actually in the image (`kubectl debug ... -- ls <path>`) |
| `137` | `OOMKilled` | Kernel SIGKILL after exceeding the memory limit | Raise the limit or fix the leak. For the JVM check `-XX:MaxRAMPercentage` → [Resource Optimization](10-resource-optimization.md) |
| `137` | `Error` | SIGKILL for another reason — liveness failed and the container did not exit within `terminationGracePeriodSeconds` | Review preStop/graceful shutdown |
| `143` | `Error` | Exited on SIGTERM (may be a normal rollout/eviction) | If it repeats, find who is killing it in Events |

- If the image execs the binary directly (no shell in between), an architecture mismatch does not produce exit 126 at all — the container never starts, and `lastState.terminated` shows Reason `StartError` with `exec format error` in the message. The fix is the same: a multi-arch image, or a nodeSelector on `kubernetes.io/arch`.

**Probe failures**: when these two lines appear as a pair in Events, the problem is usually the probe configuration rather than the application code.

```
Warning  Unhealthy  kubelet  Liveness probe failed: HTTP probe failed with statuscode: 503
Normal   Killing    kubelet  Container app failed liveness probe, will be restarted
```

- If the app is slow to start, add a **`startupProbe`** instead of inflating liveness `initialDelaySeconds` (liveness does not start until the startup probe succeeds).
- A TCP refusal such as `Readiness probe failed: dial tcp 10.0.2.45:8080: connect: connection refused` means first check whether the container port and the probe port differ.

**Configuration reference errors** — strictly speaking not a crash loop; the pod stops at `CreateContainerConfigError`:

```
Warning  Failed  kubelet  Error: configmap "app-config" not found
Warning  Failed  kubelet  Error: secret "db-credentials" not found
```

Compare names and namespaces with `kubectl get cm,secret -n <ns>` and you are done. If the reference is a volume mount, it shows up instead as a `FailedMount` event (`MountVolume.SetUp failed for volume "cfg" : configmap "app-config" not found`).

### 4. `Running` but not Ready / empty Endpoints

**Symptom**: STATUS is `Running` but READY is `0/1` (`1/2` with a sidecar). The Service sends no traffic to this pod, so from the user's side it is "deployed, but 503".

**Diagnosis**:

```bash
kubectl describe pod <pod> -n <ns> | grep -E "Ready|Readiness probe"
kubectl get endpointslices -n <ns> -l kubernetes.io/service-name=<svc>
```

A Service with no Ready pod behind it — the symptom you are hunting for — prints `<unset>` in the ENDPOINTS column (and in PORTS too: the EndpointSlice controller drops the port list when there is no endpoint to carry it). Captured on this cluster from a Service whose selector matched no running pod:

```
NAME            ADDRESSTYPE   PORTS     ENDPOINTS   AGE
api-svc-xd28r   IPv4          <unset>   <unset>     145d
```

For contrast, a healthy Service (kube-dns on the same cluster) lists one IP per Ready pod:

```
NAME             ADDRESSTYPE   PORTS        ENDPOINTS              AGE
kube-dns-xc4bb   IPv4          53,53,9153   10.0.2.106,10.0.3.14   145d
```

`<unset>` (or an empty) ENDPOINTS column means no Ready pod stands behind the Service. On Kubernetes 1.33+ `kubectl get endpoints` prints `Warning: v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice`, so get used to reading EndpointSlices.

**Causes and fixes**:

| Observation | Cause | Fix |
|---|---|---|
| Repeated `Readiness probe failed` in Events | Wrong probe path/port, or the app is still waiting on a dependency (DB, etc.) | Point the probe at the app's real health endpoint. Keep dependency waits in readiness, out of liveness |
| Condition `Ready False` with reason `ReadinessGatesNotReady` | Waiting on a pod readiness gate — typically the AWS Load Balancer Controller's `target-health.elbv2.k8s.aws/*` gate | Find out why the Target Group health check fails → [AWS Load Balancer Controller](../networking/03-aws-lb-controller.md) |
| `1/2` Running, only the app container Ready | Sidecar (istio-proxy, etc.) not ready, or the sidecar started after the app and initial connections failed | Check sidecar logs; convert the sidecar to a native sidecar (`initContainers` + `restartPolicy: Always`) |
| Ready, yet the EndpointSlice is empty | Service selector does not match the pod labels | → [5. Service unreachable](#5-service-is-unreachable) |

### 5. Service is unreachable

**Symptom**: every pod is `1/1 Running`, yet `curl http://<svc>.<ns>.svc.cluster.local` times out/refuses, or name resolution fails.

**Split the diagnosis into three layers**: (a) Service → pod mapping, (b) network policy, (c) DNS.

```bash
# (a) Compare the selector with actual labels
kubectl get svc <svc> -n <ns> -o jsonpath='{.spec.selector}{"\n"}{.spec.ports}{"\n"}'
kubectl get pods -n <ns> -l <key>=<value> -o wide
kubectl get endpointslices -n <ns> -l kubernetes.io/service-name=<svc>

# (b) NetworkPolicies applied to the namespace
kubectl get networkpolicies -n <ns>
kubectl describe networkpolicy <policy> -n <ns>

# (c) CoreDNS status and logs
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50
kubectl get cm -n kube-system coredns -o jsonpath='{.data.Corefile}'
```

**Causes and fixes**:

| Observation | Cause | Fix |
|---|---|---|
| Selector is `{"app":"api"}` but pods are labeled `app=api-server` | Label mismatch → empty EndpointSlice | Unify labels/selector. In Helm charts, `selectorLabels` and `podLabels` drifting apart is a common culprit |
| EndpointSlice has IPs but `connection refused` | `targetPort` differs from the port the container actually listens on | Compare with `kubectl get pod -o jsonpath='{.spec.containers[*].ports}'`. An app bound only to `127.0.0.1` shows the same symptom |
| Fails only from a particular namespace | A `default-deny` NetworkPolicy exists and the ingress allow rule is missing | Check `podSelector`/`namespaceSelector`. With VPC CNI network policy, `kubectl get policyendpoints -n <ns>` shows what is actually enforced → [Network Policies](../security/04-network-policies.md) |
| `nslookup <svc>` returns `NXDOMAIN` | Short name used from another namespace, or CoreDNS outage | Use the FQDN (`<svc>.<ns>.svc.cluster.local`). Confirm CoreDNS pods are `Running` and `/etc/resolv.conf` `nameserver` is the kube-dns ClusterIP (`172.20.0.10` on this cluster) |
| External domain resolution is slow | With the default `ndots:5`, any name with fewer than 5 dots is first tried against every search domain (`<ns>.svc.cluster.local`, `svc.cluster.local`, `cluster.local`, the node's VPC domain) before being queried as an absolute name | Append a trailing `.` to external names, or set `ndots: 2` in `dnsConfig.options` |
| NodePort/LB works only through some nodes | `externalTrafficPolicy: Local` with no pod on that node | Intended behavior. Switch to `Cluster` to accept on all nodes |

To reproduce DNS from a pod's point of view, start a throwaway pod: `kubectl run -it --rm dns-test --image=busybox:1.36 --restart=Never -- nslookup kubernetes.default.svc.cluster.local`. CoreDNS concepts and the Corefile are covered in [Services and Networking](../core/03-services-networking.md#coredns).

### 6. Node `NotReady` / kubelet pressure (`DiskPressure`, `MemoryPressure`, `PIDPressure`)

**Symptom**: `kubectl get nodes` shows `NotReady`, or the node is `Ready` but pods get `Evicted` or new pods avoid it with `node(s) had untolerated taint(s)`.

**Diagnosis**:

```bash
# One-line summary of node conditions
kubectl get nodes -o custom-columns='NAME:.metadata.name,READY:.status.conditions[?(@.type=="Ready")].status,MEM:.status.conditions[?(@.type=="MemoryPressure")].status,DISK:.status.conditions[?(@.type=="DiskPressure")].status,PID:.status.conditions[?(@.type=="PIDPressure")].status'

# Conditions with their reason
kubectl get node <node> -o jsonpath='{range .status.conditions[*]}{.type}{"="}{.status}{" ("}{.reason}{")\n"}{end}'

# Taints the node picked up automatically
kubectl get node <node> -o jsonpath='{.spec.taints}'
```

Healthy node output (with the EKS Node Monitoring Agent installed you also see the `ContainerRuntimeReady`/`NetworkingReady`/`KernelReady`/`StorageReady` conditions):

```
MemoryPressure=False (KubeletHasSufficientMemory)
DiskPressure=False (KubeletHasNoDiskPressure)
PIDPressure=False (KubeletHasSufficientPID)
Ready=True (KubeletReady)
ContainerRuntimeReady=True (ContainerRuntimeIsReady)
NetworkingReady=True (NetworkingIsReady)
KernelReady=True (KernelIsReady)
StorageReady=True (DiskIsReady)
```

**Causes and fixes**:

| Condition / reason | Automatic taint | Cause | Fix |
|---|---|---|---|
| `Ready=Unknown` (`NodeStatusUnknown`, "Kubelet stopped posting node status.") | `node.kubernetes.io/unreachable` | kubelet process died, instance stopped/network partition, API server auth failure | Check the EC2 instance state → SSM/`kubectl debug node` and `journalctl -u kubelet` |
| `Ready=False` | `node.kubernetes.io/not-ready` | Container runtime down, CNI not initialized (`aws-node` unhealthy) | `kubectl get pods -n kube-system -l k8s-app=aws-node -o wide` for that node's aws-node |
| `DiskPressure=True` (`KubeletHasDiskPressure`) | `node.kubernetes.io/disk-pressure` | Image cache/container logs filled the root volume | `crictl rmi --prune`, log rotation, grow the root EBS. Pods are `Evicted` with `The node was low on resource: ephemeral-storage` |
| `MemoryPressure=True` (`KubeletHasInsufficientMemory`) | `node.kubernetes.io/memory-pressure` | Pods with large limits but no requests piled up, insufficient system reservation | Enforce requests (LimitRange), check `kube-reserved`/`system-reserved` |
| `PIDPressure=True` (`KubeletHasInsufficientPID`) | `node.kubernetes.io/pid-pressure` | Fork storm (thread leak) | Find and restart the offending pod, set `podPidsLimit` |

When you need to look inside a node, use this instead of SSH:

```bash
kubectl debug node/<node> -it --image=busybox --profile=sysadmin -- chroot /host
# once inside
journalctl -u kubelet --since "10 min ago" | tail -50
df -h /var/lib/containerd
crictl ps -a | head
```

A node that **never appears** in `kubectl get nodes` (join failure: IAM role/access entry, subnet routing, security group, AMI mismatch) is a separate topic → [EKS Advanced Debugging — Node Join Failure Diagnosis](../eks/11-eks-advanced-debugging.md#node-join-failure-diagnosis-8-common-causes), [EKS Troubleshooting — Node and Pod Issues](../eks/09-eks-troubleshooting.md#node-and-pod-issues). For Karpenter nodes, start with the NodeClaim check in [section 10](#10-eks-karpenter-does-not-launch-a-node).

### 7. PVC stuck in `Pending`

**Symptom**: `kubectl get pvc` shows `Pending`, and the pod using it is `Pending` with `pod has unbound immediate PersistentVolumeClaims`.

**Diagnosis**:

```bash
kubectl get pvc -n <ns>
kubectl describe pvc <pvc> -n <ns> | sed -n '/^Events:/,$p'
kubectl get storageclass
kubectl get pods -n kube-system -l app=ebs-csi-node -o wide     # is the CSI node plugin on that node?
```

```
NAME   PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
gp2    kubernetes.io/aws-ebs   Delete          WaitForFirstConsumer   false                  145d
gp3    ebs.csi.aws.com         Delete          WaitForFirstConsumer   true                   76d
```

**Causes and fixes**: the Events message in `describe pvc` is the diagnosis.

| Events message | Cause | Fix |
|---|---|---|
| `WaitForFirstConsumer: waiting for first consumer to be created before binding` | **Normal.** `volumeBindingMode: WaitForFirstConsumer` defers volume creation until a pod is scheduled | If it is Pending because no pod uses it yet, leave it. If the pod is also Pending, read the pod's `FailedScheduling` |
| `FailedBinding: no persistent volumes available for this claim and no storage class is set` | No `storageClassName` and no default StorageClass | Set `storageClassName: gp3` on the PVC, or annotate an SC with `storageclass.kubernetes.io/is-default-class: "true"` |
| `ProvisioningFailed: storageclass.storage.k8s.io "<name>" not found` | Misspelled StorageClass, manifest copied from another cluster | Use the real name from `kubectl get sc` |
| `ProvisioningFailed: error generating accessibility requirements: no topology key found for node <node>` | The EBS CSI node plugin has not registered on the node the pod landed on (no driver in `CSINode`) | Check the DRIVERS column of `kubectl get csinode <node>`; confirm the `ebs-csi-node` DaemonSet is running on that node |
| `ProvisioningFailed` + `UnauthorizedOperation`/`AccessDenied` | The EBS CSI controller's IRSA/Pod Identity lacks permission | → [8. IRSA/Pod Identity](#8-eks-irsa--pod-identity-accessdenied) — the subject is `ebs-csi-controller-sa` |
| Pod-side `node(s) had volume node affinity conflict` | The existing PV (EBS) is in AZ `ap-northeast-2a` but schedulable nodes are in another AZ | EBS cannot cross AZs. Read the zone with `kubectl get pv <pv> -o jsonpath='{.spec.nodeAffinity}'` and provide capacity there (NodePool zone requirement or nodeSelector) |
| Pod-side `FailedAttachVolume: Multi-Attach error for volume` | An RWO volume is still attached to the previous node (StatefulSet rescheduled after node failure) | Check stale attachments with `kubectl get volumeattachments`. If the node is gone, wait a few minutes for cleanup |

`WaitForFirstConsumer`, StorageClass and dynamic provisioning concepts are in [Storage](../core/04-storage.md#storage-classes); EBS/EFS CSI error patterns are in [EKS Advanced Debugging — Storage Troubleshooting](../eks/11-eks-advanced-debugging.md#6-storage-troubleshooting).

### 8. EKS: IRSA / Pod Identity `AccessDenied`

**Symptom**: the pod is happily `Running`, but the app logs an AWS SDK error.

```
An error occurred (AccessDenied) when calling the AssumeRoleWithWebIdentity operation:
  Not authorized to perform sts:AssumeRoleWithWebIdentity
```

Or the S3/DynamoDB call itself is denied with `... is not authorized to perform: s3:GetObject`, where the denied principal is not the service account role but the **node IAM role** (`assumed-role/<node-role>/i-0abc...`). The latter means credential injection never happened and the SDK fell back to the node role.

**Diagnosis** — first determine which mechanism is in use. The pod's environment variables tell you.

```bash
# Service account annotation (IRSA)
kubectl get sa <sa> -n <ns> -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}'

# Credential-related env injected into the pod
kubectl get pod <pod> -n <ns> -o jsonpath='{range .spec.containers[0].env[*]}{.name}={.value}{"\n"}{end}' | grep ^AWS_
```

| Injected env | Mechanism | Meaning |
|---|---|---|
| `AWS_ROLE_ARN=arn:aws:iam::...:role/<role>` + `AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token` | **IRSA** | Injected by pod-identity-webhook. If absent, the SA annotation was added **after** the pod was created, or the SA name differs |
| `AWS_CONTAINER_CREDENTIALS_FULL_URI` + `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` | **EKS Pod Identity** | `eks-pod-identity-agent` serves credentials at `169.254.170.23`. Injected only when an association exists |
| Neither | None → node role fallback | See the table below |

```bash
# Pod Identity: agent and association
kubectl get pods -n kube-system -l app.kubernetes.io/name=eks-pod-identity-agent
aws eks list-pod-identity-associations --cluster-name <cluster> --namespace <ns> --service-account <sa>

# IRSA: OIDC condition in the trust policy
aws eks describe-cluster --name <cluster> --query 'cluster.identity.oidc.issuer' --output text
aws iam get-role --role-name <role> --query 'Role.AssumeRolePolicyDocument'
```

**Causes and fixes**:

| Observation | Cause | Fix |
|---|---|---|
| No env, but the SA annotation exists | Pod was created before the annotation (the webhook injects only at creation) | `kubectl rollout restart deploy/<name>` |
| No env and no association | Pod Identity association not created, or created for a different SA/namespace | `aws eks create-pod-identity-association ...`, then restart the pods |
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | IRSA trust policy: wrong `Federated` OIDC provider ARN, or the `sub` (`system:serviceaccount:<ns>:<sa>`)/`aud` (`sts.amazonaws.com`) condition does not match | Fix the trust policy. If the cluster was recreated the OIDC issuer changed, so the provider must be recreated too |
| Pod Identity, but `AssumeRole` denied | Trust policy principal is not `pods.eks.amazonaws.com`, or `sts:TagSession` is missing | Allow both `sts:AssumeRole` and `sts:TagSession` in the trust policy |
| Env is fine, only a specific API is `AccessDenied` | The role's permission policy is insufficient (not the trust policy) | Find the `eventName` of the `errorCode: AccessDenied` event in CloudTrail and extend the policy |
| Pod Identity env present but the SDK says `Unable to locate credentials` | SDK too old to support the container credential provider (`FULL_URI`) | Upgrade the SDK — minimum supported versions are listed in the EKS docs |

How IRSA and Pod Identity work and how to set them up is in [EKS Security Best Practices](../security/06-eks-security-best-practices.md#irsa-iam-roles-for-service-accounts) and [EKS Security](../eks/05-eks-security.md#eks-pod-identity); token expiry and webhook issues are in [EKS Advanced Debugging — Control Plane Debugging](../eks/11-eks-advanced-debugging.md#2-control-plane-debugging).

### 9. EKS: ENI/VPC CNI IP exhaustion

**Symptom**: pods stall in `ContainerCreating` with `FailedCreatePodSandBox` in Events:

```
Warning  FailedCreatePodSandBox  kubelet  Failed to create pod sandbox: rpc error: code = Unknown desc =
  failed to setup network for sandbox "...": plugin type="aws-cni" name="aws-cni" failed (add):
  add cmd: failed to assign an IP address to container
```

Or they stay `Pending` at scheduling time with `Too many pods`. Both symptoms share one root: **the node has no IP to hand to the pod**.

**Diagnosis**:

```bash
# Node max-pods (ENIs × (IPs per ENI − 1) + 2). An m6g.large is 29
kubectl get node <node> -o jsonpath='{.status.allocatable.pods}{"\n"}'
kubectl get pods -A --field-selector spec.nodeName=<node> --no-headers | wc -l

# aws-node status and IPAM settings
kubectl get pods -n kube-system -l k8s-app=aws-node -o wide
kubectl get ds -n kube-system aws-node -o jsonpath='{range .spec.template.spec.containers[?(@.name=="aws-node")].env[*]}{.name}={.value}{"\n"}{end}' | grep -E "PREFIX|WARM|MINIMUM|CUSTOM_NETWORK"

# Free IPs in the subnet
aws ec2 describe-subnets --subnet-ids <subnet-id> --query 'Subnets[].{id:SubnetId,az:AvailabilityZone,free:AvailableIpAddressCount}' --output table
```

The VPC CNI **default** is `WARM_ENI_TARGET=1` alone (`WARM_IP_TARGET`/`MINIMUM_IP_TARGET` unset). In that state every node keeps **one whole spare ENI** attached (15 IPs per ENI on an m5.xlarge), so in small subnets IPs run out **much faster than the pod count suggests**. By contrast, this cluster's `aws-node` settings (`ENABLE_PREFIX_DELEGATION=false`, `WARM_ENI_TARGET=1`, `WARM_IP_TARGET=3`, `MINIMUM_IP_TARGET=6`) are an example of an already-shrunk warm pool — once `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` are set they take precedence over the warm-ENI rule, so a node keeps only 3 spare IPs beyond what its pods use, and never fewer than 6 IPs allocated in total (`MINIMUM_IP_TARGET` is a floor on the total — in-use plus spare — not on the spare count).

**Causes and fixes**:

| Observation | Cause | Fix |
|---|---|---|
| Subnet `AvailableIpAddressCount` in single digits | The subnet itself is exhausted; the warm pool pre-claims IPs | Shrink the warm pool with `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` (as in the settings above), add a secondary CIDR (e.g. 100.64.0.0/16) with **custom networking** (`ENIConfig`), and IPv6 in the long run |
| Pods on node = allocatable pods | ENI/IP limit of the instance type | **Prefix delegation** (`ENABLE_PREFIX_DELEGATION=true`, allocates /28 prefixes, requires Nitro instances) plus max-pods recalculation, or a larger instance |
| `aws-node` in `CrashLoopBackOff` on that node | CNI failure itself (missing `AmazonEKS_CNI_Policy`, version mismatch) | `kubectl logs -n kube-system <aws-node-pod> -c aws-node`, and `/var/log/aws-routed-eni/ipamd.log` on the node |
| Using Security Groups for Pods and short of `vpc.amazonaws.com/pod-eni` | Branch ENI limit | Move to instances that support trunk ENIs; confirm `ENABLE_POD_ENI=true` |

IPAM behavior (warm pool, prefix delegation, custom networking) is in [VPC CNI — IP Address Management](../networking/01-vpc-cni.md#ip-address-management); step-by-step IP exhaustion handling is in [EKS Advanced Debugging — Networking Diagnostics](../eks/11-eks-advanced-debugging.md#5-networking-diagnostics) and [EKS Troubleshooting — VPC CNI Issues](../eks/09-eks-troubleshooting.md#networking-issues).

### 10. EKS: Karpenter does not launch a node

**Symptom**: pods are `Pending` and no new NodeClaim appears in `kubectl get nodeclaims`. **Separately from** the default scheduler's `FailedScheduling`, Karpenter records its own reasons as events on the same pod.

**Diagnosis**:

```bash
# Events emitted by Karpenter (source is karpenter)
kubectl get events -n <ns> --field-selector involvedObject.name=<pod> -o custom-columns=REASON:.reason,SRC:.source.component,MSG:.message

# NodePool limits vs current usage
kubectl get nodepool -o custom-columns='NAME:.metadata.name,CPU_LIMIT:.spec.limits.cpu,CPU_USED:.status.resources.cpu,MEM_LIMIT:.spec.limits.memory,MEM_USED:.status.resources.memory,READY:.status.conditions[?(@.type=="Ready")].status'

# NodeClaim progress
kubectl get nodeclaims -o custom-columns='NAME:.metadata.name,TYPE:.metadata.labels.node\.kubernetes\.io/instance-type,LAUNCHED:.status.conditions[?(@.type=="Launched")].status,REGISTERED:.status.conditions[?(@.type=="Registered")].status,READY:.status.conditions[?(@.type=="Ready")].status'

kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter --tail=100
```

A real Karpenter event (it walks every NodePool for one pod and lists why each was rejected):

```
FailedScheduling  karpenter  Failed to schedule pod, incompatible with nodepool "system",
  daemonset overhead={"cpu":"821m","memory":"1350Mi","pods":"10"}, incompatible requirements,
  label "nvidia.com/device-plugin.config" does not have known values;
  incompatible with nodepool "runner-arm", ..., did not tolerate workload-type=ci-runner:NoSchedule;
  all available instance types exceed limits for nodepool "graviton";
  incompatible with nodepool "gpu-ner", ..., incompatible requirements, key node.kubernetes.io/instance-type,
  node.kubernetes.io/instance-type In [g6e.4xlarge] not in node.kubernetes.io/instance-type In [g6.2xlarge g6.4xlarge g6.xlarge]
```

The NodePool status at the same moment showed `graviton` at `CPU_LIMIT 8 / CPU_USED 8` — **exactly at its limit** — which is what `exceed limits` means. Conversely, `Nominated  karpenter  Pod should schedule on: nodeclaim/system-tm4gv` means Karpenter has done its part and is waiting for the node to come up.

**Causes and fixes**:

| Message fragment | Cause | Fix |
|---|---|---|
| `all available instance types exceed limits for nodepool "<np>"` | NodePool `spec.limits` (cpu/memory) reached | Raise the limit, or check whether consolidation is reclaiming idle nodes |
| `label "<key>" does not have known values` | The pod's nodeSelector/affinity key is not in the NodePool `requirements` | Add the key (with its value list) to `spec.template.spec.requirements` of the NodePool |
| `did not tolerate <key>=<value>:NoSchedule` | No toleration for the NodePool `taints` | If the isolation is intentional, use another NodePool; otherwise add the toleration |
| `key node.kubernetes.io/instance-type, ... In [X] not in ... In [Y Z]` | The pod demands an instance type the NodePool does not allow | Align one side. Usually the pod-side requirement is too narrow |
| Large `daemonset overhead={...}` and `Insufficient` | Not enough capacity left after subtracting DaemonSet reservations | Include larger instances in the requirements |
| NodeClaim `LAUNCHED=True, REGISTERED=False` for several minutes | EC2 started but the node cannot join (EC2NodeClass subnet/SG selectors, node IAM role access entry, AMI) | Conditions/Events in `kubectl describe nodeclaim <name>`, EC2 console system log |
| `InsufficientInstanceCapacity` in Karpenter logs | No EC2 capacity for that AZ/instance type (ICE — Insufficient Capacity Error) | Widen instance types, AZs, and capacity-type (spot/on-demand) |
| No events, Karpenter logs quiet | The pod is not a Karpenter candidate (`nodeSelector` points at MNG labels, or scheduling constraints unrelated to Karpenter) | Re-check every node-related constraint in the pod spec |

NodePool/EC2NodeClass structure and detailed troubleshooting are in [Karpenter — Troubleshooting](../autoscaling/02-karpenter.md#troubleshooting) and [EKS Advanced Debugging — Karpenter Provisioning Issues](../eks/11-eks-advanced-debugging.md#karpenter-provisioning-issues).

***

## kubectl Diagnostic Cheat Sheet

Every command used in this document, grouped by purpose. All of them are read-only.

```bash
# ── Status scan ────────────────────────────────────────────────────────
# Unhealthy pods only
kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded
# Restart counts ascending, so the 15 worst pods come LAST (after tail) + last termination reason.
# Reads the first container only ([0]); for multi-container pods check the others separately.
kubectl get pods -A --sort-by='.status.containerStatuses[0].restartCount' \
  -o custom-columns='NS:.metadata.namespace,NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount,REASON:.status.containerStatuses[0].lastState.terminated.reason' | tail -15
# Pods on a given node
kubectl get pods -A --field-selector spec.nodeName=<node> -o wide
# Node conditions + zone + instance type
kubectl get nodes -o custom-columns='NAME:.metadata.name,READY:.status.conditions[?(@.type=="Ready")].status,DISK:.status.conditions[?(@.type=="DiskPressure")].status,MEM:.status.conditions[?(@.type=="MemoryPressure")].status,ZONE:.metadata.labels.topology\.kubernetes\.io/zone,TYPE:.metadata.labels.node\.kubernetes\.io/instance-type'

# ── Events ─────────────────────────────────────────────────────────────
kubectl get events -A --field-selector type=Warning --sort-by=.lastTimestamp | tail -30
kubectl get events -n <ns> --field-selector involvedObject.name=<pod>,reason=FailedScheduling
kubectl events -n <ns> --for pod/<pod> --watch          # follow one object live
kubectl events -A --types=Warning                       # kubectl events subcommand (1.26+)

# ── jsonpath for exactly the fields you need ──────────────────────────
kubectl get pod <pod> -o jsonpath='{.status.containerStatuses[*].lastState.terminated}'
kubectl get pod <pod> -o jsonpath='{range .spec.containers[*]}{.name}{": "}{.resources}{"\n"}{end}'
kubectl get svc <svc> -o jsonpath='{.spec.selector}'
kubectl get sa <sa> -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}'
kubectl get pv <pv> -o jsonpath='{.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions}'

# ── Logs ───────────────────────────────────────────────────────────────
kubectl logs <pod> -c <container> --previous --tail=100   # logs of the dead container
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50  # several pods by label
kubectl logs deploy/<name> --all-containers --since=10m

# ── Debug containers ───────────────────────────────────────────────────
# Attach an ephemeral container to a distroless pod (shares the process namespace)
kubectl debug -it <pod> --image=nicolaka/netshoot --target=<container>
# Copy of the pod with a different image/command
kubectl debug <pod> -it --copy-to=<pod>-debug --container=<container> -- sh
# Node shell without SSH. --profile=sysadmin is a privileged container
kubectl debug node/<node> -it --image=busybox --profile=sysadmin -- chroot /host

# ── Resource usage (requires metrics-server) ───────────────────────────
kubectl top nodes
kubectl top pods -n <ns> --sort-by=memory
# Without metrics-server: "error: Metrics API not available"

# ── Schema lookup ──────────────────────────────────────────────────────
kubectl explain pod.status.containerStatuses.lastState.terminated
kubectl explain nodepool.spec.limits        # works for CRDs too
kubectl api-resources | grep -E "karpenter|k8s.aws"

# ── Rollouts ───────────────────────────────────────────────────────────
kubectl rollout status deploy/<name> -n <ns>
kubectl rollout history deploy/<name> -n <ns>
```

Valid `--profile` values for `kubectl debug` are `legacy`, `general`, `baseline`, `restricted`, `netadmin`, and `sysadmin` (the default is `legacy` or `general` depending on your kubectl version — check `kubectl debug --help`); in a namespace with Pod Security Standards enforced, use `restricted` to pass admission.

***

## Going Deeper: Related Documents

This playbook is the front door that decides "where to go next." Once the cause is narrowed down, move to the documents below.

| Narrowed-down area | Concept document | Deep troubleshooting |
|---|---|---|
| Pod lifecycle, probes, restart policy | [Pods and Workloads](../core/02-pods-and-workloads.md#pod-lifecycle) | [EKS Advanced Debugging — Workload Debugging](../eks/11-eks-advanced-debugging.md#4-workload-debugging) |
| Service, EndpointSlice, CoreDNS, NetworkPolicy | [Services and Networking](../core/03-services-networking.md), [Network Policies](../security/04-network-policies.md) | [EKS Troubleshooting — Networking Issues](../eks/09-eks-troubleshooting.md#networking-issues) |
| PV/PVC/StorageClass, EBS CSI | [Storage](../core/04-storage.md) | [EKS Troubleshooting — Storage Issues](../eks/09-eks-troubleshooting.md#storage-issues) |
| Node join, kubelet, resource pressure | [Cluster Architecture](../core/01-cluster-architecture.md) | [EKS Troubleshooting — Node and Pod Issues](../eks/09-eks-troubleshooting.md#node-and-pod-issues) |
| Karpenter NodePool/NodeClaim | [Karpenter](../autoscaling/02-karpenter.md) | [Scaling Strategies](06-scaling-strategies.md) |
| VPC CNI IPAM, prefix delegation, custom networking | [VPC CNI](../networking/01-vpc-cni.md) | [EKS Networking Part 3: Troubleshooting](../eks/03-eks-networking-part3.md) |
| IRSA, Pod Identity, RBAC | [EKS Security Best Practices](../security/06-eks-security-best-practices.md), [Kubernetes Authentication and Authorization](../security/02-kubernetes-auth-authz.md) | [EKS Troubleshooting — IAM and Authentication Issues](../eks/09-eks-troubleshooting.md#iam-and-authentication-issues) |
| Where the logs are and how to find them | [Logging Overview](../observability/logging/README.md) | [Observability Analysis](08-observability-analysis.md) |
| requests/limits, OOM, JVM memory | [Resource Optimization](10-resource-optimization.md) | [EKS Troubleshooting — Performance Issues](../eks/09-eks-troubleshooting.md#performance-issues) |
| Incident response process, severity, first-5-minutes checklist | — | [EKS Advanced Debugging — Incident Response Framework](../eks/11-eks-advanced-debugging.md#1-incident-response-framework) |

***

## References

Official documentation behind the quoted strings and the rules of thumb in this page.

**Kubernetes**

- [Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/) — the `node.kubernetes.io/*` taints the node controller adds automatically (section 6)
- [Debugging Kubernetes Nodes with kubectl](https://kubernetes.io/docs/tasks/debug/debug-cluster/kubectl-node-debug/) and the [`kubectl debug` reference](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_debug/) — node debug pods and `--profile` values (sections 2, 6, cheat sheet)
- [Debug Running Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/) — ephemeral containers, `--copy-to`, `--target` (cheat sheet)
- [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/) — why `v1 Endpoints` is deprecated since 1.33 (section 4)
- [Debug Services](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/) and [Debugging DNS Resolution](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/) — selector/port/DNS checks and `ndots` (section 5)

**Amazon EKS / AWS**

- [Amazon VPC CNI plugin README](https://github.com/aws/amazon-vpc-cni-k8s/blob/master/README.md) — `WARM_ENI_TARGET`, `WARM_IP_TARGET`, `MINIMUM_IP_TARGET`, `ENABLE_PREFIX_DELEGATION` semantics and precedence (section 9)
- [Assign more IP addresses to Amazon EKS nodes with prefixes](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses.html) — prefix delegation and max-pods recalculation (section 9)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html) and [IAM roles for service accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html) — trust policy shapes and injected environment variables (section 8)
- [Detect node health issues and enable automatic node repair](https://docs.aws.amazon.com/eks/latest/userguide/node-health.html) — the Node Monitoring Agent conditions shown in section 6
- [Troubleshoot problems with Amazon EKS clusters and nodes](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html) — node join failures, `AccessDenied`, CNI errors
- [Karpenter — Troubleshooting](https://karpenter.sh/docs/troubleshooting/) — NodePool limits, requirement mismatches, NodeClaim launch/registration failures (section 10)

***

< [Previous: Zonal Cluster Operations](15-zonal-operations-guide.md) | [Table of Contents](./README.md) >
