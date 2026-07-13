# Workload Placement 策略

< [上一页：GPU 集成](./05-gpu-integration.md) | [目录](./README.md) | [下一页：Node 生命周期管理](./07-node-lifecycle.md) >

> **支持的版本**：EKS 1.31+、Karpenter 1.0+
> **最后更新**：February 22, 2026

本文档介绍在 hybrid nodes（混合节点）和 cloud nodes（云节点）之间放置 workloads（工作负载）的策略，包括 node affinity、taints/tolerations，以及使用 Karpenter 实现 cloud bursting。

## Node Affinity 与 Taints/Tolerations

### Hybrid Node Taint 配置

```bash
# Add Taint to on-premises nodes
kubectl taint nodes hybrid-node-001 eks.amazonaws.com/compute-type=hybrid:NoSchedule

# Add additional Taint to GPU nodes
kubectl taint nodes hybrid-gpu-node-001 gpu=true:NoSchedule
```

### 仅限本地运行的 Workload

```yaml
# on-prem-workload.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-processor
  namespace: analytics
spec:
  replicas: 3
  selector:
    matchLabels:
      app: data-processor
  template:
    metadata:
      labels:
        app: data-processor
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: eks.amazonaws.com/compute-type
                operator: In
                values:
                - hybrid
      tolerations:
      - key: eks.amazonaws.com/compute-type
        operator: Equal
        value: hybrid
        effect: NoSchedule
      containers:
      - name: processor
        image: harbor.internal.company.io/analytics/data-processor:v2.1.0
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
```

## GPU Workloads 在本地、CPU Workloads 在 Cloud 中运行的模式

```yaml
# hybrid-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-training
  namespace: ai-workloads
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ml-training
  template:
    metadata:
      labels:
        app: ml-training
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: eks.amazonaws.com/compute-type
                operator: In
                values:
                - hybrid
              - key: nvidia.com/gpu.present
                operator: In
                values:
                - "true"
      tolerations:
      - key: eks.amazonaws.com/compute-type
        operator: Equal
        value: hybrid
        effect: NoSchedule
      - key: gpu
        operator: Equal
        value: "true"
        effect: NoSchedule
      containers:
      - name: trainer
        image: harbor.internal.company.io/ai/model-trainer:v1.0.0
        resources:
          limits:
            nvidia.com/gpu: 4
          requests:
            cpu: "16"
            memory: "64Gi"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference-api
  namespace: ai-workloads
spec:
  replicas: 5
  selector:
    matchLabels:
      app: ml-inference-api
  template:
    metadata:
      labels:
        app: ml-inference-api
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: eks.amazonaws.com/compute-type
                operator: DoesNotExist
      containers:
      - name: api
        image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/ai/inference-api:v1.0.0
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
```

## 使用 Karpenter 进行 Cloud Bursting

当本地容量被耗尽时，自动扩展到 AWS。

### Karpenter NodePool 配置

```yaml
# karpenter-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cloud-burst-pool
spec:
  template:
    metadata:
      labels:
        node-type: cloud-burst
        topology.kubernetes.io/zone: ap-northeast-2a
    spec:
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64"]
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["spot", "on-demand"]
      - key: node.kubernetes.io/instance-type
        operator: In
        values: ["m6i.xlarge", "m6i.2xlarge", "m6i.4xlarge"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiFamily: AL2023
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-hybrid-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-hybrid-cluster
  role: KarpenterNodeRole-my-hybrid-cluster
```

### Topology-Aware Scheduling

```yaml
# topology-aware-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: latency-sensitive-app
spec:
  replicas: 10
  selector:
    matchLabels:
      app: latency-sensitive
  template:
    metadata:
      labels:
        app: latency-sensitive
    spec:
      topologySpreadConstraints:
      - maxSkew: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: latency-sensitive
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: eks.amazonaws.com/compute-type
                operator: In
                values:
                - hybrid
          - weight: 50
            preference:
              matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - ap-northeast-2a
                - ap-northeast-2b
      containers:
      - name: app
        image: harbor.internal.company.io/apps/latency-app:v1.0.0
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"
```

## 使用 Pod Deletion Cost 最大化本地利用率

### 为什么 Pod Deletion Cost 很重要

在 Cloud Bursting 模式中，当流量减少且 workloads scale down 时，**哪些 Pod 会先被移除**非常关键。本地硬件属于沉没成本，应最大限度加以利用，而 cloud Pod 会产生按使用量计费的费用，因此应优先移除。

`controller.kubernetes.io/pod-deletion-cost` annotation 会告知 ReplicaSet controller 在 scale-down 期间应优先删除哪些 Pod。

| Annotation 值 | 行为 |
|-----------------|----------|
| 低值（例如 0，默认值） | 优先删除 |
| 高值（例如 1000） | 最后删除（受保护） |

### 工作原理

```
Pod deletion order during scale-down:

Priority 1: Pods with low deletion-cost (cloud) → deleted first
Priority 2: Pods with high deletion-cost (on-prem) → retained

Example: replicas 10 → 4
  Cloud pods (cost=0)      : all 6 deleted
  On-premises pods (cost=1000): all 4 retained
```

### 使用 Mutating Webhook 自动分配

配置一个 Mutating Webhook，在 Pod 创建时根据 node 位置自动分配 deletion-cost。

```yaml
# pod-deletion-cost-webhook.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deletion-cost-webhook
  namespace: kube-system
spec:
  replicas: 2
  selector:
    matchLabels:
      app: deletion-cost-webhook
  template:
    metadata:
      labels:
        app: deletion-cost-webhook
    spec:
      serviceAccountName: deletion-cost-webhook
      containers:
      - name: webhook
        image: harbor.internal.company.io/platform/deletion-cost-webhook:v1.0.0
        ports:
        - containerPort: 8443
        env:
        - name: ON_PREM_COST
          value: "1000"
        - name: CLOUD_COST
          value: "0"
        - name: ON_PREM_LABEL_KEY
          value: "eks.amazonaws.com/compute-type"
        - name: ON_PREM_LABEL_VALUE
          value: "hybrid"
---
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: pod-deletion-cost
webhooks:
- name: deletion-cost.hybrid.eks
  admissionReviewVersions: ["v1"]
  sideEffects: None
  clientConfig:
    service:
      name: deletion-cost-webhook
      namespace: kube-system
      path: /mutate
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE"]
    resources: ["pods"]
  namespaceSelector:
    matchExpressions:
    - key: kubernetes.io/metadata.name
      operator: NotIn
      values: ["kube-system", "kube-node-lease"]
```

### 手动分配（简单方法）

如果不使用 webhook，可以在调度后用 CronJob patch Pod，该 CronJob 会根据每个 Pod 正在运行的 node 分配 deletion-cost。

```bash
#!/bin/bash
# patch-deletion-cost.sh
# Run as CronJob: assign high deletion-cost to pods on on-premises nodes

ON_PREM_NODES=$(kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid \
  -o jsonpath='{.items[*].metadata.name}')

for NODE in $ON_PREM_NODES; do
  PODS=$(kubectl get pods --all-namespaces --field-selector spec.nodeName=$NODE \
    -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}{"\n"}{end}')

  for POD in $PODS; do
    NS=$(echo $POD | cut -d'/' -f1)
    NAME=$(echo $POD | cut -d'/' -f2)
    CURRENT=$(kubectl get pod $NAME -n $NS \
      -o jsonpath='{.metadata.annotations.controller\.kubernetes\.io/pod-deletion-cost}' 2>/dev/null)

    if [ "$CURRENT" != "1000" ]; then
      kubectl annotate pod $NAME -n $NS \
        controller.kubernetes.io/pod-deletion-cost="1000" --overwrite
    fi
  done
done
```

```yaml
# deletion-cost-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: patch-deletion-cost
  namespace: kube-system
spec:
  schedule: "*/5 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: deletion-cost-patcher
          containers:
          - name: patcher
            image: bitnami/kubectl:latest
            command: ["/bin/bash", "/scripts/patch-deletion-cost.sh"]
            volumeMounts:
            - name: script
              mountPath: /scripts
          volumes:
          - name: script
            configMap:
              name: deletion-cost-script
          restartPolicy: OnFailure
```

### 与 Karpenter 集成

Pod deletion cost 与 Karpenter 的 consolidation policies 配合良好：

| 配置 | 作用 |
|--------------|------|
| `pod-deletion-cost` | 在 ReplicaSet scale-down 期间优先移除 cloud Pod |
| Karpenter `WhenEmpty` | 自动移除空的 cloud nodes |
| Karpenter `WhenUnderutilized` | 对利用率不足的 cloud nodes 进行 consolidation |

```yaml
# Karpenter with deletion-cost integration example
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cloud-burst-pool
spec:
  disruption:
    consolidationPolicy: WhenUnderutilized  # Consolidate underutilized nodes
    consolidateAfter: 60s
  # ...remaining config from Karpenter NodePool Configuration above
```

端到端 scale-down 流程：

```mermaid
graph LR
    A[Traffic Decrease] --> B[HPA Scale Down]
    B --> C{Pod Deletion Order}
    C -->|"deletion-cost=0"| D[Cloud Pods Deleted First]
    C -->|"deletion-cost=1000"| E[On-Prem Pods Retained]
    D --> F[Cloud Nodes Empty]
    F --> G[Karpenter Removes Empty Nodes]

    style D fill:#fee,stroke:#c00
    style E fill:#efe,stroke:#0a0
    style G fill:#e8f4fd,stroke:#1976d2
```

---

< [上一页：GPU 集成](./05-gpu-integration.md) | [目录](./README.md) | [下一页：Node 生命周期管理](./07-node-lifecycle.md) >
