# Cilium Service Mesh アーキテクチャクイズ

このクイズでは、Cilium Service Meshのアーキテクチャ、eBPF datapath、node Envoy proxy、およびCRDモデルについての理解を確認します。

## クイズの問題

### 1. Cilium Service Meshと従来のsidecarベースのservice meshとの主な違いは何ですか？

A. Kubernetesネイティブではない
B. eBPFを使用してLinux kernelレベルでL3/L4トラフィックを処理する
C. すべてのトラフィックをuser spaceで処理する
D. Podごとに複数のproxyを使用する

<details>
<summary>回答を表示</summary>

**回答: B. eBPFを使用してLinux kernelレベルでL3/L4トラフィックを処理する**

**解説:**
Cilium Service Meshは、eBPF（extended Berkeley Packet Filter）を使用して、Linux kernel内でL3/L4トラフィックを直接処理します。これは、すべてのトラフィックをuser-space sidecar proxy経由で処理する従来のservice meshとは根本的に異なります。L7処理が必要な場合にのみ、トラフィックはnodeごとに共有されるEnvoy proxyへ転送されます。

</details>

### 2. Ciliumプログラムが実行できるeBPF hook pointではないものはどれですか？

A. XDP (eXpress Data Path)
B. TC (Traffic Control)
C. Application Layer
D. cgroup

<details>
<summary>回答を表示</summary>

**回答: C. Application Layer**

**解説:**
eBPFプログラムはkernelレベルで実行され、主なhook pointにはXDP（NIC driver）、TC（network stack entry）、Socket Operations（socket level）、およびcgroup（process group）があります。Application Layerはuser spaceにあるため、eBPF hook pointではありません。

</details>

### 3. CiliumのnodeごとのEnvoy proxyモデルの利点は何ですか？

A. より複雑な設定が可能になる
B. Podごとのメモリ使用量が増加する
C. リソース効率と低レイテンシー
D. すべてのトラフィックを暗号化できない

<details>
<summary>回答を表示</summary>

**回答: C. リソース効率と低レイテンシー**

**解説:**
nodeごとに1つのEnvoy proxyを使用すると、Podごとにsidecarをデプロイする場合と比べて、使用メモリを大幅に削減できます。100 Podのclusterでは、Istioは約5GB（Podごとに50MB）を使用しますが、Ciliumは約500MB（nodeごとに100MB）のみを使用します。さらに、L3/L4トラフィックはeBPFで直接処理されるため、レイテンシーが大幅に低減されます。

</details>

### 4. CiliumEnvoyConfig CRDの主な目的は何ですか？

A. Kubernetes network policyを定義する
B. 特定のService向けのEnvoy proxy設定を定義する
C. Pod scheduling ruleを定義する
D. storage classを定義する

<details>
<summary>回答を表示</summary>

**回答: B. 特定のService向けのEnvoy proxy設定を定義する**

**解説:**
CiliumEnvoyConfigはnamespace-scoped CRDであり、特定のService向けにEnvoy proxyの設定（listener、route、clusterなど）を定義します。これにより、HTTP routing、header manipulation、load balancingなどのL7機能を設定できます。

</details>

### 5. Ciliumがkube-proxyを置き換える場合、consistent hashingを提供するload balancing algorithmはどれですか？

A. Random
B. Round Robin
C. Maglev
D. Least Connection

<details>
<summary>回答を表示</summary>

**回答: C. Maglev**

**解説:**
MaglevはGoogleが開発したconsistent hashing algorithmで、CiliumのeBPFベースのload balancerで使用されます。このalgorithmは、backendが変化しても既存の接続の大部分を維持するsession affinityを提供します。O(1)のlookup timeで高いパフォーマンスを実現します。

</details>

### 6. Cilium Identityについて正しい記述はどれですか？

A. IP addressに基づいてworkloadを識別する
B. Pod labelをhash化してnumeric IDを生成する
C. 識別にMAC addressを使用する
D. ユーザーが手動で割り当てる必要がある

<details>
<summary>回答を表示</summary>

**回答: B. Pod labelをhash化してnumeric IDを生成する**

**解説:**
Cilium Identityは、Pod label（namespace、service account、ユーザー定義labelなど）をhash化して一意のnumeric IDを生成します。このIDベースのアプローチには、IP addressが変更されてもpolicyが影響を受けないという利点があります。

</details>

### 7. CiliumでL7 policyが適用されると、トラフィックフローはどうなりますか？

A. すべてのトラフィックは常にEnvoyを経由する
B. L7 policyを持つトラフィックのみがEnvoyへredirectされる
C. Envoyは完全にbypassされる
D. トラフィックはdropされる

<details>
<summary>回答を表示</summary>

**回答: B. L7 policyを持つトラフィックのみがEnvoyへredirectされる**

**解説:**
効率のため、CiliumはL7 policyを持つトラフィックのみをnode Envoy proxyへredirectします。L3/L4 policyのみ、またはpolicyがないトラフィックはeBPFで直接処理され、kernel内で高速にforwardされます。

</details>

### 8. Ciliumのconnection trackingはどこで実行されますか？

A. user spaceのconntrack daemon
B. eBPF maps
C. Envoy proxy
D. Kubernetes API server

<details>
<summary>回答を表示</summary>

**回答: B. eBPF maps**

**解説:**
Ciliumはconnection trackingにeBPF mapsを使用します。CT（Connection Tracking）mapはkernel内でconnection stateを保存およびlookupし、既存connectionに対するpolicy decisionのcacheと高速な適用を可能にします。

</details>

### 9. CiliumClusterwideNetworkPolicyとCiliumNetworkPolicyの違いは何ですか？

A. 両方とも同じscopeを持つ
B. CiliumClusterwideNetworkPolicyはcluster全体に適用される
C. CiliumNetworkPolicyの方が多くの機能を持つ
D. CiliumClusterwideNetworkPolicyはL7 policyをサポートしない

<details>
<summary>回答を表示</summary>

**回答: B. CiliumClusterwideNetworkPolicyはcluster全体に適用される**

**解説:**
CiliumNetworkPolicyはnamespace-scopedである一方、CiliumClusterwideNetworkPolicyはcluster-wide scopedです。cluster-wide policyは、default deny policyやすべてのnamespaceに適用する必要があるsecurity ruleに役立ちます。どちらのCRDもL7 policyをサポートします。

</details>

### 10. Cilium Service Meshで使用されるSPIFFE IDの形式は何ですか？

A. urn:spiffe:cluster/namespace/pod
B. spiffe://cluster.local/ns/\<namespace\>/sa/\<service-account\>
C. https://spiffe.io/id/\<pod-name\>
D. spiffe:\<namespace\>:\<pod-name\>

<details>
<summary>回答を表示</summary>

**回答: B. spiffe://cluster.local/ns/\<namespace\>/sa/\<service-account\>**

**解説:**
SPIFFE（Secure Production Identity Framework for Everyone）IDは、workloadの一意な識別子です。Cilium Service MeshでSPIREと統合する場合、各workloadには`spiffe://cluster.local/ns/<namespace>/sa/<service-account>`の形式のSPIFFE IDが付与されます。このIDはmTLS authenticationに使用されます。

</details>

### 11. Cilium Agentの役割ではないものはどれですか？

A. eBPFプログラム管理
B. Envoy設定の生成と同期
C. Kubernetes API serverの役割
D. Identity管理

<details>
<summary>回答を表示</summary>

**回答: C. Kubernetes API serverの役割**

**解説:**
Cilium Agentは各node上で実行され、eBPFプログラム管理、policy compilation、Envoy設定の生成・同期、Identity管理、endpoint管理、flow loggingを担当します。Kubernetes API serverはKubernetes control planeの一部であり、Ciliumとは別のものです。

</details>

### 12. Ciliumは同一node上のPod-to-Pod通信に対して、どのような最適化を提供しますか？

A. 常にexternal networkを経由してrouteする
B. network stackをbypassするeBPF経由のdirect kernel path
C. すべてのトラフィックをEnvoyへforwardする
D. 通信できない

<details>
<summary>回答を表示</summary>

**回答: B. network stackをbypassするeBPF経由のdirect kernel path**

**解説:**
同一node上のPod-to-Pod通信では、CiliumはeBPFを使用してdirect kernel path経由でトラフィックをforwardします。これによりLinux network stack全体をbypassし、非常に低いレイテンシー（~0.1ms）を実現します。

</details>
