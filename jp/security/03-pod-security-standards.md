# Pod Security Standards (PSS)

> **検証ベースライン**: Kubernetes PSA library v1.36.2; example PSS policy v1.35
> **最終更新**: September 13, 2026

Pod Security Standards (PSS) は、Kubernetes における Pod セキュリティの標準化されたポリシーフレームワークです。このドキュメントでは、PSS の概念、設定方法、および EKS 環境での実装について説明します。

PSS はポリシーを定義し、PSA はそれを適用する組み込みの admission 実装です。特に記載がない限り、このガイドでは**ユーザー名前空間を使用しない通常の Linux Pod**を前提としています。ローカルの upstream ポリシー評価および schema/command チェックは Deployment とは異なります。ライブクラスター、EKS、またはコンテナの実行はテストしていません。例の `v1.35` は固定されたポリシー定義であり、Kubernetes/EKS の最新サポートバージョンに関する主張ではありません。API server がアップグレードされると、`latest` の意味は変わります。

## 目次

1. [PSP から PSS への進化](#evolution-from-psp-to-pss)
2. [Pod Security Admission (PSA) Controller](#pod-security-admission-psa-controller)
3. [セキュリティレベル](#security-levels)
4. [適用モード](#enforcement-modes)
5. [Namespace レベルの設定](#namespace-level-configuration)
6. [PSP から PSS への移行](#migration-from-psp-to-pss)
7. [EKS のデフォルトと設定](#eks-defaults-and-configuration)
8. [セキュリティプロファイルの詳細](#security-profile-details)
9. [例外設定](#exemptions-configuration)
10. [段階的導入のベストプラクティス](#best-practices-for-gradual-adoption)

---

<span id="evolution-from-psp-to-pss"></span>

## PSP から PSS への進化

### PodSecurityPolicy (PSP) の歴史

PodSecurityPolicy (PSP) は Pod セキュリティメカニズムとして Kubernetes 1.3 で初めて導入されました。しかし、以下の問題により Kubernetes 1.21 で非推奨となり、1.25 で完全に削除されました。

```
┌─────────────────────────────────────────────────────────────────┐
│                    Key Issues with PSP                           │
├─────────────────────────────────────────────────────────────────┤
│ 1. Complex RBAC binding requirements                             │
│ 2. Implicit policy application (unclear which policy applies)    │
│ 3. User vs workload permission confusion                         │
│ 4. No warn/audit rollout modes                                               │
│ 5. Limited audit capabilities                                    │
└─────────────────────────────────────────────────────────────────┘
```

### PSS の導入

Pod Security Standards (PSS) と Pod Security Admission (PSA) は Kubernetes 1.22 で alpha として導入され、1.23 で beta となり、1.25 で GA（Generally Available）に到達しました。

![PSP の非推奨化、PSP の削除、1.25 での PSA GA、およびその後のバージョン化されたポリシーの進化を区別するロードマップ。](../.gitbook/assets/en-security-03-pod-security-standards-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-security-03-pod-security-standards-0.html)

> 図の解釈: PSA は 1.25 で GA に到達しました。1.28 は別個の安定化マイルストーンではありません。

### PSP と PSS の比較

| 機能 | PodSecurityPolicy (PSP) | Pod Security Standards (PSS) |
|---------|------------------------|------------------------------|
| **有効化** | 以前の admission plugin | 組み込み PSA plugin によって適用される PSS 定義 |
| **ポリシー定義** | カスタム PSP リソース | 事前定義された 3 つのプロファイル |
| **ポリシーバインディング** | 複雑な RBAC バインディング | 単純な Namespace ラベル |
| **スコープ** | クラスター全体または Namespace | Namespace レベル |
| **ポリシープレビュー** | PSA 形式の warn/audit モードなし。API dry-run は別 | warn/audit モードと API dry-run |
| **監査** | 限定的 | 組み込みの監査サポート |
| **柔軟性** | 高い（きめ細かい制御） | 中程度（標準化されたプロファイル） |
| **複雑さ** | 高い | 低い |

---

## Pod Security Admission (PSA) Controller

### PSA アーキテクチャ

PSA は mutating admission の後、validating admission 中に **API server 内部**で実行されます。認証、認可、schema 検証、その他の admission チェックも適用されます。これは外部 webhook ではなく、この図は PSA と他のすべての validator の間に普遍的な順序があることを示すものではありません。

```text
Request → authentication / authorization → mutating admission
        → validating admission (PSA + other checks) → persistence if accepted
```

### PSA の仕組み

![認証・認可済みの Pod CREATE を簡略化。PSA は API server 内部にあり、201 には他の admission チェックとストレージの成功も必要です。](../.gitbook/assets/en-security-03-pod-security-standards-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-security-03-pod-security-standards-1.html)

> 図の範囲: PSA は API server 内部にあります。Pod CREATE の成功は、適用対象のすべてのチェックに合格した後にのみ永続化されます。PSA の承認だけでは 201 Created は保証されません。

### PSA ステータスの確認

PSA は Kubernetes 1.23 で beta となりデフォルトで有効化され、その後 1.25 で GA に到達しました。明示的な `--enable-admission-plugins=PodSecurity` フラグがないことは、無効化されていることを意味しません。self-managed API server の設定に明示的な無効化がないか確認してください。EKS ではその設定は公開されません。metrics は feature-gate の設定ではなく評価を示します。`/metrics` へのアクセスには認可が必要で、未使用の series は存在しない可能性があります。

```bash
kubectl --context "$PSS_CONTEXT" get namespace "$PSS_NAMESPACE" -o yaml
kubectl --context "$PSS_CONTEXT" get --raw /metrics
```

実際の admission パスをテストするには、以下の positive/negative Pod dry-run controls を使用してください。Deployment の dry-run が成功しただけでコンプライアンスを推測してはいけません。

---

<span id="security-levels"></span>

## セキュリティレベル

PSS は 3 つのセキュリティレベル（プロファイル）を定義します。各レベルでは、段階的に厳しくなるセキュリティ制約が適用されます。

### 1. Privileged

このプロファイルでは PSS の制限は追加されません。コンテナ権限を自動的に有効化することも、RBAC、API 検証、その他の admission ポリシーをバイパスすることもありません。

```yaml
# Privileged profile: PSS imposes no controls; API/RBAC/other policies still apply
# Use cases: System daemons, CNI plugins, monitoring agents

apiVersion: v1
kind: Pod
metadata:
  name: privileged-pod
  namespace: pss-privileged-lab
spec:
  hostNetwork: true      # Allowed
  hostPID: true          # Allowed
  hostIPC: true          # Allowed
  containers:
  - name: privileged-container
    image: nginx
    securityContext:
      privileged: true   # Allowed
      runAsUser: 0    # Allowed
```

**Privileged レベルで許可されるもの:**
- Host network、PID、IPC namespace
- Privileged コンテナ
- すべての capability
- HostPath mount
- 任意の user/group ID

### 2. Baseline

既知の権限昇格を防ぐための最小限の制約を適用します。ほとんどの一般的な workload に適しています。

```yaml
# Baseline level: Prevents known privilege escalations
# Use cases: General applications, web servers, API servers

apiVersion: v1
kind: Pod
metadata:
  name: baseline-pod
spec:
  containers:
  - name: app
    image: nginx
    securityContext:
      # The following are prohibited in Baseline:
      # privileged: true        ❌
      # allowPrivilegeEscalation is not constrained by Baseline

      # The following are allowed in Baseline:
      runAsNonRoot: false      # ✓ (allowed but not recommended)
      readOnlyRootFilesystem: false  # ✓ (allowed)
    ports:
    - containerPort: 80
```

**Baseline レベルの制約:**

| フィールド | 制約 |
|-------|------------|
| HostProcess | Windows HostProcess コンテナは禁止 |
| Host Namespaces | hostNetwork、hostPID、hostIPC は禁止 |
| Privileged Containers | privileged: true は禁止 |
| Capabilities | 明示的な追加は、一覧の Baseline allowlist に限定。`NET_RAW` は含まれない |
| HostPath Volumes | hostPath volume は禁止 |
| Host Ports | 組み込み PSA は未設定/0 を許可。カスタム port allowlist はない |
| AppArmor | 未設定または RuntimeDefault/Localhost。legacy annotation では runtime/default または localhost/* |
| SELinux | 制限された type 値のみ。user/role の設定は禁止 |
| /proc Mount Type | デフォルト値のみ許可 |
| Seccomp | 未設定は許可。指定時は RuntimeDefault または Localhost（Unconfined ではない） |
| Sysctls | PSS バージョンの明示的な sysctl allowlist のみ。すべての kubelet-safe sysctl ではない |

### 3. Restricted

Pod セキュリティ強化のベストプラクティスを適用する、最も制限の厳しいポリシーです。セキュリティに敏感な workload に適しています。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: restricted-pod
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
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir: {}
```

**Restricted レベルの追加制約:**

| フィールド | 制約 |
|-------|------------|
| Volume Types | configMap、csi、downwardAPI、emptyDir、ephemeral、persistentVolumeClaim、projected、secret のみ許可 |
| Privilege Escalation | allowPrivilegeEscalation: false が必要 |
| Running as Non-root | runAsNonRoot: true が必要 |
| Running as Non-root user | 明示的な runAsUser: 0 は禁止（v1.23+）。フィールドは省略可能 |
| Seccomp | RuntimeDefault または Localhost が必要 |
| Capabilities | すべての capability を drop する必要があり、追加できるのは NET_BIND_SERVICE のみ |



制御は、該当する通常、init、ephemeral コンテナに適用されます。Pod レベルの non-root/seccomp 値は継承できますが、競合するコンテナの override は準拠しません。ポリシー v1.34+ では、HTTP/TCP probe と lifecycle hook の空でない `host` も禁止されます。v1.35 では、`hostUsers: false` により non-root チェックが緩和されます。Baseline でも `procMount` が緩和されますが、Restricted では依然として `Unmasked` が禁止されます。これには単なるラベルではなく、実際の user-namespace サポートが必要です。privilege escalation、seccomp、Linux capability に関する Windows 固有の緩和は、この Linux の例とは別です。

### セキュリティレベル比較表

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     Security Level Comparison                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Restriction  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶       │
│               Low                                           High          │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │  Privileged  │    │   Baseline   │    │  Restricted  │               │
│  │              │    │              │    │              │               │
│  │ No           │    │ Prevent      │    │ Security     │               │
│  │ restrictions │    │ known        │    │ best         │               │
│  │              │    │ escalations  │    │ practices    │               │
│  │              │    │              │    │              │               │
│  │ Use cases:   │    │ Use cases:   │    │ Use cases:   │               │
│  │ - CNI        │    │ - General    │    │ - Financial  │               │
│  │ - CSI        │    │   apps       │    │   apps       │               │
│  │ - Monitoring │    │ - Web        │    │ - Healthcare │               │
│  │              │    │   servers    │    │ - Multi-     │               │
│  │              │    │ - API        │    │   tenant     │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

<span id="enforcement-modes"></span>

## 適用モード

PSA は 3 つの適用モードを提供します。これらのモードは、個別にも組み合わせても使用できます。

### 1. enforce

違反する Pod の作成と関連する Pod 更新を拒否します。workload template は warn/audit チェックを受けます。適用は生成された Pod に対して行われます。Namespace の再ラベル付けによって、すでに実行中の Pod が退避されることはありません。

```yaml
# enforce mode: Block Pod creation on violation
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
```

**説明用の応答抜粋（記録されたクラスター実行ではありません）:**
```text
# Attempting to create a policy-violating Pod
$ kubectl apply --dry-run=server -f privileged-pod.yaml -n production
Error from server (Forbidden): error when creating "privileged-pod.yaml":
pods "privileged-pod" is forbidden: violates PodSecurity "restricted:v1.35":
privileged (container "app" must not set securityContext.privileged=true),
allowPrivilegeEscalation != false (container "app" must set
securityContext.allowPrivilegeEscalation=false)
```

### 2. audit

違反 annotation を audit event に追加します。このモード自体はリクエストを拒否しません。これらの event を保持するかどうかは、audit-policy/log-delivery 設定によって決まります。他のモードや admission チェックによっては、依然として拒否される可能性があります。

```yaml
# audit mode: Record violations in audit logs
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
```

**合成された audit-event 抜粋（完全なキャプチャ event ではありません）:**
```json
{
  "kind": "Event",
  "apiVersion": "audit.k8s.io/v1",
  "level": "Metadata",
  "auditID": "00000000-0000-4000-8000-000000000001",
  "stage": "ResponseComplete",
  "requestURI": "/api/v1/namespaces/staging/pods",
  "verb": "create",
  "user": {
    "username": "developer@example.com"
  },
  "objectRef": {
    "resource": "pods",
    "namespace": "staging",
    "name": "my-pod"
  },
  "annotations": {
    "pod-security.kubernetes.io/audit-violations": "privileged (container \"app\" must not set securityContext.privileged=true)"
  }
}
```

### 3. warn

リクエスト自体を拒否せず、クライアントに表示される warning を返します。enforce または他の admission チェックによっては、依然として拒否される可能性があります。

```yaml
# warn mode: Display warning messages on violation
apiVersion: v1
kind: Namespace
metadata:
  name: development
  labels:
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

**説明用の warning 抜粋（記録された実行ではありません）:**
```text
$ kubectl apply --dry-run=server -f non-compliant-pod.yaml -n development
Warning: would violate PodSecurity "restricted:v1.35":
allowPrivilegeEscalation != false (container "app" must set
securityContext.allowPrivilegeEscalation=false),
unrestricted capabilities (container "app" must set
securityContext.capabilities.drop=["ALL"])
pod/my-pod created (server dry run)
```

### モード組み合わせ戦略

最初の Privileged 段階は、より強力な既存ポリシーがない Namespace 専用です。この図に従うために Baseline/Restricted の enforcement を下げてはいけません。

本番環境では、複数のモードを組み合わせることを推奨します。

```yaml
# Recommended configuration: Use mode combinations
apiVersion: v1
kind: Namespace
metadata:
  name: app-namespace
  labels:
    # Current enforcement level
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.35
    # Audit next level
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    # Warn next level
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

```
┌─────────────────────────────────────────────────────────────────┐
│                    Mode Combination Strategy                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: Assess Current State                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ enforce: privileged                                      │   │
│  │ audit: baseline                                          │   │
│  │ warn: baseline                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  Phase 2: Gradual Hardening                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ enforce: baseline                                        │   │
│  │ audit: restricted                                        │   │
│  │ warn: restricted                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  Phase 3: Final Goal                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ enforce: restricted                                      │   │
│  │ audit: restricted                                        │   │
│  │ warn: restricted                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

<span id="namespace-level-configuration"></span>

## Namespace レベルの設定

### 基本的なラベル設定

PSS は Namespace ラベルで設定します。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: secure-namespace
  labels:
    # Format: pod-security.kubernetes.io/<MODE>: <LEVEL>
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

### バージョン指定

特定の Kubernetes バージョンの PSS 定義を使用できます。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: versioned-namespace
  labels:
    # Use PSS definitions from a specific version
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35  # Specific version

    # Using 'latest' applies PSS from current cluster version
    # pod-security.kubernetes.io/enforce-version: latest
```

### 環境別設定の例

```yaml
---
# Development environment: Relaxed policy
apiVersion: v1
kind: Namespace
metadata:
  name: development
  labels:
    environment: development
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/warn: restricted
---
# Staging environment: Intermediate policy
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    environment: staging
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
---
# Production environment: Strict policy
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    environment: production
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### 既存 Namespace へのラベル追加

```bash
# Add labels using kubectl
kubectl label namespace my-namespace \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=v1.35 \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted

# Verify labels
kubectl get namespace my-namespace -o yaml | grep pod-security
```

---

<span id="migration-from-psp-to-pss"></span>

## PSP から PSS への移行

### 移行の概要

PSP から PSS への移行は慎重に計画し、段階的に実施する必要があります。

![移行では、既存の enforcement を維持しながらギャップを評価し、warn/audit を観察し、修復して対象ポリシーを検証します。PSP API のクリーンアップは、過去の 1.24 以前の環境にのみ適用されます。](../.gitbook/assets/en-security-03-pod-security-standards-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-security-03-pod-security-standards-2.html)

> 図の範囲: PSP の分析/削除は過去のものです。観察のために既存のより強力な enforce ポリシーを下げてはいけません。readOnlyRootFilesystem は推奨であり、Restricted の必須要件ではありません。

### ステップ 1: 現在の PSP を分析する

**過去の手順のみ:** 以下の PSP コマンド/リソースは、`policy/v1beta1` がまだ提供されていた古いクラスター（Kubernetes 1.24 まで）、または保存済みの manifest に適用されます。現在のクラスターにはこの PSP を適用しないでください。また、PSP により以前に default/mutate されていたフィールドも棚卸ししてください。PSA はそれらを補完しません。

```bash
# List current PSPs
kubectl get psp

# Get PSP details
kubectl get psp <psp-name> -o yaml

# Check Pods with PSP applied
kubectl get pods --all-namespaces -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}: {.metadata.annotations.kubernetes\.io/psp}{"\n"}{end}'
```

### ステップ 2: PSP を PSS プロファイルにマッピングする

```yaml
# Example: Existing PSP
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: MustRunAsNonRoot
  seLinux:
    rule: RunAsAny
  fsGroup:
    rule: RunAsAny
  supplementalGroups:
    rule: RunAsAny
```

**マッピング結果:** Restricted は候補となる対象であり、同等のポリシーではありません。この PSP には必須の seccomp 制御がなく、PSS が拒否する可能性のある SELinux 設定を許可しています。すべての制御と生成されるすべての Pod を比較してください。選択した 3 つのフィールドでは同等性を確立できません。

### PSP から PSS へのマッピング表

| Workload 要件 | 候補の PSS プロファイル | 必要なレビュー |
|---|---|---|
| Host namespace、privileged コンテナ、または hostPath | Privileged | 例外を分離し、追加の制御を適用する |
| Host アクセスなしだが root process が必要 | Baseline | capability と seccomp を含むすべての Baseline 制御を確認する |
| Non-root、権限昇格なし、ALL を drop | Restricted | volume、seccomp、override、バージョン固有の制御も確認する |

### ステップ 3: テスト環境で検証する

```bash
# Create test namespace
kubectl create namespace pss-test

# Apply restricted in warn mode
kubectl label namespace pss-test \
  pod-security.kubernetes.io/warn=restricted \
  pod-security.kubernetes.io/warn-version=v1.35

# Test existing workload deployment
kubectl apply -f my-deployment.yaml -n pss-test

# Check warnings and modify workloads
```

### ステップ 4: 段階的な適用

```yaml
# Staged migration namespace configuration
apiVersion: v1
kind: Namespace
metadata:
  name: migrating-namespace
  labels:
    # Phase 1: New namespace without a previous stronger enforce policy
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: baseline
    pod-security.kubernetes.io/warn: baseline

    # Phase 2: Apply baseline, monitor restricted
    # pod-security.kubernetes.io/enforce: baseline
    # pod-security.kubernetes.io/audit: restricted
    # pod-security.kubernetes.io/warn: restricted

    # Phase 3: Final restricted enforcement
    # pod-security.kubernetes.io/enforce: restricted
```

### ステップ 5: Workload を修正する

変更前: security context のない通常の `nginx` Pod は Restricted チェックに失敗します。`runAsNonRoot` の追加だけでは不十分です。image user、listener、書き込み可能なパスにも互換性が必要です。修正後の Pod では、upstream の unprivileged image（UID/GID 101）、port 8080、read-only root filesystem と書き込み可能な `/tmp` を使用しています。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: new-pod
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
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir: {}
```

### 移行自動化スクリプト

これは意図的に**レビュー済みの 1 つの Namespace**を対象とし、以前は存在しなかった warn/audit ラベルのみを追加し、enforce を維持し、観測した resource version を使用して同時編集を拒否します。実行すると実際に Namespace を変更します。最初に対象を確認してください。既存のラベルがある場合は、自動的に downgrade するのではなく、手動比較のために失敗させます。warning は以降のリクエストで表示され、実行中のすべての Pod に対する遡及的スキャンとして表示されるものではありません。

```python
#!/usr/bin/env python3
# add-pss-observation.py CONTEXT NAMESPACE
import json, subprocess, sys

if len(sys.argv) != 3:
    raise SystemExit("Usage: add-pss-observation.py CONTEXT NAMESPACE")
context, namespace = sys.argv[1:]
if namespace in {"kube-system", "kube-public", "kube-node-lease"}:
    raise SystemExit("Refusing system namespace; review its workload requirements separately")
base = ["kubectl", "--context", context, "--request-timeout=30s"]
obj = json.loads(subprocess.run(
    base + ["get", "namespace", namespace, "-o", "json"],
    check=True, text=True, capture_output=True).stdout)
labels = obj["metadata"].get("labels", {})
new = {
    "pod-security.kubernetes.io/warn": "restricted",
    "pod-security.kubernetes.io/warn-version": "v1.35",
    "pod-security.kubernetes.io/audit": "restricted",
    "pod-security.kubernetes.io/audit-version": "v1.35",
}
if any(key in labels for key in new):
    raise SystemExit("Existing observation policy: review it; do not overwrite automatically")
subprocess.run(base + [
    "label", "namespace", namespace,
    "--resource-version=" + obj["metadata"]["resourceVersion"],
] + [key + "=" + value for key, value in new.items()], check=True)
```

---

<span id="eks-defaults-and-configuration"></span>

## EKS のデフォルトと設定

### EKS の PSA デフォルト設定

AWS は、EKS 1.23 から PSA がデフォルトで有効化され、すべてのモードのクラスター default は `privileged/latest`、static exemption はないと文書化しています。これらの寛容な default は workload hardening ポリシーではありません。platform tool または administrator により作成された Namespace ラベルが default を override する可能性があります。すべての Namespace が unlabeled であると想定せず、実際の Namespace を確認してください。

```bash
kubectl --context "$PSS_CONTEXT" get namespace "$PSS_NAMESPACE" -o yaml
```

### EKS での PSS の設定

```yaml
# Apply PSS to EKS namespace
apiVersion: v1
kind: Namespace
metadata:
  name: eks-app-namespace
  labels:
    # Example rollout choice, not a universal AWS requirement
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.35
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted

    # EKS-related labels
    app.kubernetes.io/managed-by: eks
```

### EKS システム Namespace に関する考慮事項

Host-access agent は Baseline を満たせませんが、`kube-system` 内のすべての Pod が完全な権限を必要とするわけではありません。正確な add-on version とレンダリングされた Pod spec をレビューしてください。システム Namespace 全体の warn/audit を無効にする一括上書きは避けてください。可能であれば、承認済み host agent を通常の application から分離し、そこに Deployment できるユーザーを制限してください。以下は専用の例示 Namespace であり、既存のシステム Namespace を再ラベル付けする指示ではありません。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: host-agents
  labels:
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

### EKS Add-on と PSS の互換性

| コンポーネント / 典型的な Deployment | PSS レビューポイント |
|---|---|
| VPC CNI `aws-node`、kube-proxy | Host networking または privileged node 操作は Baseline を超過する可能性がある |
| EBS/EFS CSI node DaemonSet | Host mount は Baseline を超過する可能性がある。controller Pod には異なる要件がある |
| Node-level CloudWatch Agent / Fluent Bit | Host log/filesystem アクセスは実際の設定に依存する |
| CoreDNS、AWS Load Balancer Controller、Cluster Autoscaler | レンダリングされた spec を Baseline/Restricted と照合して評価する。コンポーネント名だけでは準拠を証明できない |

EKS Auto Mode の組み込み node component は self-managed add-on とは異なります。この表はレビュー補助であり、テスト済みの互換性 matrix でも、記載されたすべての add-on のインストール要件でもありません。

### EKS Terraform の例

この fragment は 1 つの application Namespace を管理します。Kubernetes provider とその対象 context は別途設定・レビューしてください。provider の初期化、plan、apply は実行していません。既存の Namespace は、競合する Terraform/GitOps 所有権を作成するのではなく、その owner を介して adopt/import してください。ポリシーは意図的に固定され、system-namespace ラベルは変更しません。

```hcl
# Provider authentication/context and ownership must be configured separately.
resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = "my-app"
    labels = {
      "pod-security.kubernetes.io/enforce"         = "restricted"
      "pod-security.kubernetes.io/enforce-version" = "v1.35"
      "pod-security.kubernetes.io/audit"           = "restricted"
      "pod-security.kubernetes.io/audit-version"   = "v1.35"
      "pod-security.kubernetes.io/warn"            = "restricted"
      "pod-security.kubernetes.io/warn-version"    = "v1.35"
      "environment"                              = "production"
    }
  }
}
```

---

<span id="security-profile-details"></span>

## セキュリティプロファイルの詳細

### Privileged プロファイルの詳細

Privileged プロファイルは PSS の制限を課しません。API 検証、RBAC、その他の admission チェックは引き続き有効です。以下の host-root の例はポリシー分析専用であり、Deployment を推奨する workload ではありません。

```yaml
# All options allowed in Privileged profile
apiVersion: v1
kind: Pod
metadata:
  name: privileged-example
spec:
  hostNetwork: true
  hostPID: true
  hostIPC: true
  containers:
  - name: privileged-container
    image: nginx
    securityContext:
      privileged: true
      allowPrivilegeEscalation: true
      runAsUser: 0
      capabilities:
        add:
          - ALL
    volumeMounts:
    - name: host-root
      mountPath: /host
  volumes:
  - name: host-root
    hostPath:
      path: /
      type: Directory
```

### Baseline プロファイルの詳細

```yaml
# Baseline profile restrictions (v1.35)
#
# Prohibited fields and values:
#
# spec.hostNetwork: true prohibited
# spec.hostPID: true prohibited
# spec.hostIPC: true prohibited
#
# spec.containers[*].securityContext.privileged: true prohibited
# spec.initContainers[*].securityContext.privileged: true prohibited
# spec.ephemeralContainers[*].securityContext.privileged: true prohibited
#
# spec.containers[*].securityContext.capabilities.add restricted
#   - Allowed: NET_BIND_SERVICE (only this in Restricted)
#   - Additionally allowed in Baseline: AUDIT_WRITE, CHOWN, DAC_OVERRIDE,
#     FOWNER, FSETID, KILL, MKNOD, NET_BIND_SERVICE,
#     SETFCAP, SETGID, SETPCAP, SETUID, SYS_CHROOT
#
# spec.volumes[*].hostPath prohibited
#
# spec.containers[*].ports[*].hostPort prohibited (except 0)
#
# spec.securityContext.appArmorProfile.type restricted
#   - Allowed: profile omitted, or type RuntimeDefault/Localhost
#   - Prohibited: Unconfined
#
# spec.securityContext.seLinuxOptions.type restricted
#   - Prohibited: Custom types (container_t etc. allowed)
#
# spec.securityContext.seccompProfile.type restricted
#   - Prohibited: Unconfined
#
# spec.securityContext.sysctls restricted
#   - Only the explicit versioned PSS sysctl allowlist

apiVersion: v1
kind: Pod
metadata:
  name: baseline-compliant
spec:
  automountServiceAccountToken: false
  containers:
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    ports:
    - containerPort: 8080
    securityContext:
      capabilities:
        drop: [ALL]
```

### Restricted プロファイルの詳細

Restricted は Baseline に、volume allowlist、non-root 実行、明示的な seccomp、権限昇格の禁止、すべての capability の drop を追加します。`NET_BIND_SERVICE` は許可される唯一の追加ですが、この 8080 listener には不要です。`readOnlyRootFilesystem` は推奨される hardening であり、PSS の要件ではありません。`containerPort` の設定は metadata であり、Nginx を再設定するものではありません。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: restricted-compliant
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
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir: {}
```

### Restricted 準拠 Nginx の完全な例

digest は、Linux amd64/arm64 用の upstream OCI metadata（Nginx 1.30.4、user 101）に照らして確認しました。image layer の pull もコンテナ実行も行っていません。upstream では、port 8080、`/tmp/nginx.pid`、および `/tmp` 配下の一時パスを文書化しています。以下の ConfigMap は、一致する listener と health endpoint を提供します。Deployment より先に同じ Namespace に作成してください。rollout 前に、承認済み環境で startup/readiness を検証してください。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-restricted
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 101  # nginx user
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: nginx
        image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 101
          capabilities:
            drop:
              - ALL
        ports:
        - containerPort: 8080
        resources:
          limits:
            cpu: 100m
            memory: 128Mi
          requests:
            cpu: 50m
            memory: 64Mi
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: tmp
        emptyDir: {}
      - name: config
        configMap:
          name: nginx-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-config
  namespace: production
data:
  default.conf: |
    server {
        listen 8080;
        server_name localhost;

        location / {
            root /usr/share/nginx/html;
            index index.html;
        }

        location /healthz {
            return 200 'OK';
            add_header Content-Type text/plain;
        }
    }
```

---

<span id="exemptions-configuration"></span>

## 例外設定

### クラスターレベルの例外設定

self-managed API server は、この設定を `--admission-control-config-file` 経由で読み込めます。この例ではすべての exemption list を空にしています。exemption は**すべての PSA モード**をスキップします。`usernames` は group、wildcard、将来の Pod の ServiceAccount ではなく、認証済みリクエストの完全一致 username に一致します。controller account を exempt すると、多数の user に代わって作成する Pod のチェックをバイパスしてしまいます。Namespace 名と RuntimeClass 名も完全一致します。例外は、それを使用できるユーザーを別途制約した後にのみ設定してください。

```yaml
# Self-managed API server configuration; not an EKS control-plane setting
apiVersion: apiserver.config.k8s.io/v1
kind: AdmissionConfiguration
plugins:
- name: PodSecurity
  configuration:
    apiVersion: pod-security.admission.config.k8s.io/v1
    kind: PodSecurityConfiguration
    defaults:
      enforce: baseline
      enforce-version: v1.35
      audit: restricted
      audit-version: v1.35
      warn: restricted
      warn-version: v1.35
    exemptions:
      usernames: []
      runtimeClasses: []
      namespaces: []
```

### EKS での例外設定

EKS では、managed API server の AdmissionConfiguration を編集できません。Namespace の `enforce: privileged` は寛容なプロファイルであり、**static exemption ではありません**。warn/audit は依然としてリクエストを評価できます。Namespace への書き込み/Deployment 権限を制限し、host agent を通常の application から分離してください。たとえば、hostNetwork/hostPID/hostPath を設定した node-exporter は Baseline に合格できません。Baseline を設定しても、それらの host access が安全または許可されるわけではありません。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: host-agents
  labels:
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

### RuntimeClass ベースの例外

RuntimeClass は設定済みの CRI runtime handler を選択します。リソースを作成しても gVisor/Kata がインストールされるわけでも、PSA 例外が付与されるわけでもありません。対象となるすべての node が handler をサポートする必要があります（または適切な scheduling constraint を使用します）。この定義だけでは PSA は完全に適用されたままです。

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc
```

self-managed API server で別途設定された `runtimeClasses: ["gvisor"]` exemption のみが PSA をスキップします。その class を選択できるすべてのリクエストが PSA をバイパスできる可能性があります。runtime isolation は admission authorization の代替ではありません。この managed-control-plane 設定は EKS では利用できません。

### Kyverno を使用したきめ細かい例外

Kyverno は PSA による拒否を許可へ変更できません。host agent に例外が必要な場合は、最初に Namespace の PSA プロファイルと Deployment 権限を設計し、その後、狭いスコープの例外を持つ独立して enforcement するポリシーを追加してください。HostPath のみの除外では hostNetwork/hostPID チェックは除外されません。image tag または mutable Pod label だけに基づく一致は authorization ではありません。

レビュー済みのポリシー API とバージョン/非推奨の制限については、[Kyverno policy management](./01-kyverno-policy-management.md) を参照してください。小文字の `validationFailureAction: enforce` を含む legacy `ClusterPolicy` はコピーしないでください。有効な値ではなく、ClusterPolicy は Kyverno 1.19 で非推奨です。置き換えは通常の workload と例外 workload の両方でテストする必要があります。

---

<span id="best-practices-for-gradual-adoption"></span>

## 段階的導入のベストプラクティス

### ステップ 1: 現在の状態を分析する

warn ではなく **enforce** への変更を preview してください。既存 Pod のチェックをトリガーするのは enforce-level/version の変更だけです。この server dry-run はラベルを保存せず、Pod を退避させません。有効な enforce ポリシーが変わらない場合、新たなスキャンはトリガーされません。スキャンは best effort であり、warning を制限/重複排除する可能性があります。何も出力されないことは、完全な workload audit を意味しません。command/authentication の失敗も失敗のままです。

```bash
#!/usr/bin/env bash
# preview-pss.sh: no namespace mutation
set -euo pipefail
: "${PSS_CONTEXT:?Set the approved test context}"
: "${PSS_NAMESPACE:?Set one namespace to inspect}"
kubectl --context "$PSS_CONTEXT" --request-timeout=30s \
  get namespace "$PSS_NAMESPACE" -o yaml
kubectl --context "$PSS_CONTEXT" --request-timeout=30s \
  label namespace "$PSS_NAMESPACE" \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=v1.35 \
  --overwrite --dry-run=server
```

### ステップ 2: 段階的 rollout 戦略

日数範囲は、測定された移行期間ではなく、説明用の計画スケジュールです。明示的な Namespace inventory を使用し、既存のより強力なポリシーを downgrade せず、replacement Pod と rollback capacity のテスト後にのみ進めてください。

```yaml
# Gradual rollout using GitOps

# Phase 1: Monitoring (Day 1-7)
# - Apply warn: baseline to all namespaces
# - Collect and analyze violations

# Phase 2: Development Environment (Day 8-14)
# - Apply enforce: baseline to development namespaces
# - Apply warn: baseline to staging namespaces

# Phase 3: Staging Environment (Day 15-21)
# - Apply enforce: baseline to staging namespaces
# - Apply warn: baseline to production namespaces

# Phase 4: Production Environment (Day 22-28)
# - Apply enforce: baseline to production namespaces
# - Apply warn: restricted to all environments

# Phase 5: Restricted Hardening (Day 29+)
# - Apply enforce: restricted as default for new namespaces
# - Gradually migrate existing namespaces
```

### ステップ 3: Monitoring と Alert を設定する

これらの rule には Prometheus Operator CRD、この PrometheusRule を含む selector、および `pod_security_evaluations_total` を公開する認可済み API-server scrape が必要です。組み込み PSA は `pod-security-webhook` という名前の webhook ではありません。評価 label には decision、policy_level、policy_version、mode、request_operation、resource、subresource が含まれます。**namespace label はありません**。Namespace/request の詳細は、保持された audit event と関連付けてください。metrics が存在しないことは違反がゼロである証拠にはなりません。audit-mode の denial は違反評価を意味し、必ずしも API リクエストの拒否を意味しません。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: pss-violations
  namespace: monitoring
spec:
  groups:
  - name: pod-security-standards
    rules:
    - alert: PSSViolationDetected
      expr: |
        sum by (policy_level, policy_version, mode) (
          increase(pod_security_evaluations_total{mode="enforce",decision="deny"}[5m])
        ) > 0
      labels:
        severity: warning
      annotations:
        summary: "PSA denied a Pod request"
        description: "Policy {{ $labels.policy_level }}:{{ $labels.policy_version }}. Correlate audit logs for namespace and request identity."
    - alert: PSSAuditViolation
      expr: |
        sum by (policy_level, policy_version, mode) (
          increase(pod_security_evaluations_total{mode="audit",decision="deny"}[5m])
        ) > 10
      for: 5m
      labels:
        severity: info
      annotations:
        summary: "PSA audit violations increasing"
        description: "{{ $value }} violating evaluations over five minutes; not a count of unique Pods."
```

### ステップ 4: 自動コンプライアンスチェック

これを workload を所有するプロジェクトに `check-pss.py` として保存してください。前提条件: PyYAML を含む Python 3、互換性のある kubectl、承認済みのクラスター認証情報、ポリシー v1.35 をサポートする Kubernetes API server、および `restricted:v1.35` を明示的に enforce する既存の test Namespace。呼び出し元には、server dry-run であっても Namespace read と Pod create の認可が必要です。クラスター認証情報を信頼できない pull-request code に公開しないでください。

```python
#!/usr/bin/env python3
# check-pss.py CONTEXT NAMESPACE pod.yaml [pod2.yaml ...]
# Requires Python 3 + PyYAML and a preconfigured, authorized kubectl.
import copy, json, subprocess, sys
from pathlib import Path
import yaml

if len(sys.argv) < 4:
    raise SystemExit("Usage: check-pss.py CONTEXT NAMESPACE pod.yaml [...]")
context, namespace, *files = sys.argv[1:]
pods = []
for filename in files:
    docs = list(yaml.safe_load_all(Path(filename).read_text()))
    if not docs or any(not isinstance(p, dict) for p in docs):
        raise SystemExit(f"{filename}: empty/non-object YAML")
    for pod in docs:
        if (pod.get("apiVersion"), pod.get("kind")) != ("v1", "Pod"):
            raise SystemExit(f"{filename}: only explicit v1 Pod test inputs are supported")
        meta = pod.setdefault("metadata", {})
        if meta.get("namespace", namespace) != namespace:
            raise SystemExit(f"{filename}: namespace mismatch")
        meta["namespace"] = namespace
        pods.append(pod)
base = ["kubectl", "--context", context, "--request-timeout=30s"]
ns = json.loads(subprocess.run(
    base + ["get", "namespace", namespace, "-o", "json"],
    check=True, text=True, capture_output=True).stdout)
labels = ns["metadata"].get("labels", {})
if (labels.get("pod-security.kubernetes.io/enforce"),
    labels.get("pod-security.kubernetes.io/enforce-version")) != ("restricted", "v1.35"):
    raise SystemExit("Test namespace must explicitly enforce restricted:v1.35")

def dry_run(pod):
    return subprocess.run(
        base + ["create", "--dry-run=server", "--validate=strict",
                "--namespace", namespace, "-f", "-"],
        input=json.dumps(pod), text=True, capture_output=True)

control = {
    "apiVersion": "v1", "kind": "Pod",
    "metadata": {"generateName": "pss-control-", "namespace": namespace},
    "spec": {
        "automountServiceAccountToken": False,
        "securityContext": {"runAsNonRoot": True, "runAsUser": 65532,
                            "seccompProfile": {"type": "RuntimeDefault"}},
        "containers": [{"name": "probe", "image": "registry.k8s.io/pause:3.10",
                        "securityContext": {"allowPrivilegeEscalation": False,
                                            "capabilities": {"drop": ["ALL"]}}}],
    },
}
good = dry_run(control)
if good.returncode:
    raise SystemExit("Positive control failed; no compliance result:\n" + good.stderr)
bad = copy.deepcopy(control)
bad["spec"]["hostPID"] = True
denied = dry_run(bad)
if denied.returncode == 0 or 'violates PodSecurity "restricted:v1.35"' not in denied.stderr:
    raise SystemExit("Negative control did not confirm PSA rejection:\n" + denied.stderr)
for pod in pods:
    result = dry_run(pod)
    if result.returncode:
        raise SystemExit("Pod dry-run failed:\n" + result.stderr)
print(f"{len(pods)} explicit Pod inputs passed server dry-run in {namespace}")
```

```bash
python3 check-pss.py "$PSS_CONTEXT" "$PSS_NAMESPACE" ./pss-inputs/web-pod.yaml
```

明示的な input list は、init container を含む各 workload の Pod template をカバーする必要があります。この例では、Deployment、空ファイル、誤った Namespace、query failure、enforcement 不足、および exempt/inactive negative-control path を拒否します。template extraction、mutating webhook、scheduling、image startup、将来の runtime behavior には、別のチェックが必要です。negative control は PSA によって拒否される必要があります。その他の error は結論を出せないため、チェックは失敗します。候補の Pod によって選択される別の exemption（たとえば exempt RuntimeClass）も、test-cluster owner が禁止するか別途テストする必要があります。

### ステップ 5: ドキュメントとトレーニング

```markdown
# Pod Security Standards Guidelines

## Checklist for Developers

### When Writing Restricted-Level Pods:

- [ ] Set `spec.securityContext.runAsNonRoot: true`
- [ ] Set `spec.securityContext.seccompProfile.type: RuntimeDefault`
- [ ] Set `allowPrivilegeEscalation: false` on all containers
- [ ] Set `capabilities.drop: ["ALL"]` on all containers
- [ ] Set `readOnlyRootFilesystem: true` (recommended)
- [ ] Use unprivileged images (e.g., nginxinc/nginx-unprivileged)
- [ ] Mount emptyDir for writable paths

### Common Problem Solutions:

1. **nginx fails to bind port 80**
   → Add `NET_BIND_SERVICE` capability or use port 8080

2. **File write failures**
   → Mount emptyDir volumes to required paths

3. **Process runs as root**
   → Use unprivileged base image or add USER directive in Dockerfile
```

---

## トラブルシューティング

### よくあるエラーと解決策

#### 1. "allowPrivilegeEscalation != false" エラー

説明用のエラー抜粋です。YAML は**部分的な Pod-spec 修正**であり、単独で使用できる manifest ではありません。既存のコンテナ image/configuration を保持してください。該当するコンテナ単位の制御は、init および ephemeral コンテナにも適用してください。

```text
allowPrivilegeEscalation != false
```

```yaml
spec:
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
```

#### 2. "unrestricted capabilities" エラー

説明用のエラー抜粋です。YAML は**部分的な Pod-spec 修正**であり、単独で使用できる manifest ではありません。既存のコンテナ image/configuration を保持してください。該当するコンテナ単位の制御は、init および ephemeral コンテナにも適用してください。

```text
unrestricted capabilities
```

```yaml
spec:
  containers:
  - name: app
    securityContext:
      capabilities:
        drop: [ALL]
```

#### 3. "runAsNonRoot != true" エラー

説明用のエラー抜粋です。YAML は**部分的な Pod-spec 修正**であり、単独で使用できる manifest ではありません。既存のコンテナ image/configuration を保持してください。該当するコンテナ単位の制御は、init および ephemeral コンテナにも適用してください。

```text
runAsNonRoot != true
```

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 101
```

#### 4. "seccompProfile" エラー

説明用のエラー抜粋です。YAML は**部分的な Pod-spec 修正**であり、単独で使用できる manifest ではありません。既存のコンテナ image/configuration を保持してください。該当するコンテナ単位の制御は、init および ephemeral コンテナにも適用してください。

```text
seccompProfile must be RuntimeDefault or Localhost
```

```yaml
spec:
  securityContext:
    seccompProfile:
      type: RuntimeDefault
```

### PSS 違反チェックツール

Polaris、kube-score、Trivy は追加の static check を提供しますが、クラスターのバージョン化された PSA ポリシー、exemption、mutation の正確な代替ではありません。レビュー済みのバージョンをインストールし、その CLI help を参照してください。server dry-run の成功は、そのリクエスト、identity、Namespace、時点に限定されます。上記の明示的な Pod control を使用してください。

```bash
# Dry-run check with kubectl
kubectl apply -f my-pod.yaml --dry-run=server

# Check with Polaris
polaris audit --audit-path ./k8s/ --format pretty

# Check with kube-score
kube-score score my-deployment.yaml

# Configuration check with Trivy
trivy config ./k8s/
```

---

## まとめ

Pod Security Standards (PSS) は、Kubernetes で Pod セキュリティを管理するための標準化されたアプローチを提供します。

1. **3 つのセキュリティレベル**: Privileged（すべての権限）、Baseline（既知の昇格を防止）、Restricted（最小権限）
2. **3 つの適用モード**: enforce（ブロック）、audit（ログ）、warn（警告）
3. **Namespace ラベル**: PSP 形式の use binding はなし。RBAC では引き続き Namespace ラベルと workload 作成を制限する必要がある
4. **段階的導入のサポート**: warn/audit モードによる安全な移行

### 推奨事項

- 新しいクラスターでは最初から PSS を有効化する
- 既存クラスターでは warn モードから開始し、段階的に hardening する
- 本番環境では少なくとも Baseline レベルを適用する
- 機密性の高い workload には Restricted レベルを適用する

---

## 参考資料

- [Kubernetes Pod Security Standards 公式ドキュメント](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Pod Security Admission 公式ドキュメント](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- [EKS ベストプラクティスガイド - Pod Security](https://docs.aws.amazon.com/eks/latest/best-practices/pod-security.html)
- [PSP から PSS への移行ガイド](https://kubernetes.io/docs/tasks/configure-pod-container/migrate-from-psp/)

- [PSA Namespace ラベルのプレビューと既存 Pod チェック](https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-namespace-labels/)
- [PSA の設定と例外](https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-admission-controller/)
- [Nginx unprivileged image と書き込み可能なパス](https://github.com/nginx/docker-nginx-unprivileged)
