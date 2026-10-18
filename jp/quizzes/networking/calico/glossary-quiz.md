# Calico用語集クイズ

> **関連ドキュメント**: [Calico用語集](../../../networking/calico/glossary.md)
> **最終更新日**: 2026年9月12日

## クイズ

1. CalicoのアーキテクチャにおけるFelixの主な役割は何ですか？
   - A) etcd databaseを管理する
   - B) 各Nodeでnetwork policy ruleとrouteを設定する
   - C) Service trafficをload balanceする
   - D) ServiceのDNS名前解決を提供する

<details>
<summary>解答を表示</summary>

**解答: B) 各Nodeでnetwork policy ruleとrouteを設定する**

**解説:** Felixは、選択されたpolicy dataplaneと該当するrouteを各Nodeに設定します。CNI pluginが通常のPod interfaceを作成・設定し、IPAMを呼び出します。Felixはendpointの状態を追跡してruleを設定しますが、各packetをuserspaceで転送するものではありません。

</details>

2. CalicoにおけるBIRDの名称と機能は何ですか？
   - A) Binary Internet Routing Daemon — container DNSを管理する
   - B) BIRD Internet Routing Daemon — BGPを通じてrouting情報を配布する
   - C) Basic Internal Route Distribution — Service discoveryを処理する
   - D) Broadcast IP Routing Distributor — multicast trafficを管理する

<details>
<summary>解答を表示</summary>

**解答: B) BIRD Internet Routing Daemon — BGPを通じてrouting情報を配布する**

**解説:** BIRDは、BGPを有効にしたCalico profileでrouteを交換します。trafficが直接routingされるかtunnelを使うかは、routing/encapsulationの設計によって決まります。BGPが有効だからといってoverlayがないとは限りません。

</details>

3. CalicoのdeploymentでTyphaは何をしますか？
   - A) Pod間trafficを暗号化する
   - B) datastore更新をcacheし、Felix instanceにfan-outする
   - C) ingress load balancingを提供する
   - D) certificate rotationを管理する

<details>
<summary>解答を表示</summary>

**解答: B) datastore更新をcacheし、Felix instanceにfan-outする**

**解説:** Typhaはdatastoreの変更をcacheしてFelixへ配布することで、clientごとのwatch負荷を減らします。複数replicaや複数のsyncer/watch typeを構成できます。唯一のwatchをすべての環境で必須にするものでも、policy federation serviceでもありません。インストール済みprofileのscalingはoperatorが管理します。

</details>

4. CalicoのIPPoolとIPAMはどのように異なりますか？
   - A) 名前が異なるだけで、同じものである
   - B) IPPoolは利用可能なCIDR範囲を定義し、IPAMはその範囲からの割り当てを管理する
   - C) IPPoolはIPv4用で、IPAMはIPv6用である
   - D) IPPoolはIPAMに置き換えられ、非推奨である

<details>
<summary>解答を表示</summary>

**解答: B) IPPoolは利用可能なCIDR範囲を定義し、IPAMはその範囲からの割り当てを管理する**

**解説:** IPPoolはaddress rangeに加えて、encapsulation、NAT、allocationの適格性を定義します。Calico IPAMは、サポート対象の用途で適格なpoolからaddressを割り当てます。VPC CNIのpolicy-only modeで使うallocatorではなく、IPPoolはKubernetes NodeのPodCIDR別名でもありません。

</details>

5. GlobalNetworkPolicyはKubernetes NetworkPolicyとどのように異なりますか？
   - A) GlobalNetworkPolicyはIPv6でのみ動作する
   - B) GlobalNetworkPolicyはcluster scopeで、tierやdeny ruleなどの追加機能をサポートする
   - C) GlobalNetworkPolicyはKubernetes NetworkPolicyと同様にnamespace scopeである
   - D) GlobalNetworkPolicyは非推奨である

<details>
<summary>解答を表示</summary>

**解答: B) GlobalNetworkPolicyはcluster scopeで、tierやdeny ruleなどの追加機能をサポートする**

**解説:** GlobalNetworkPolicyはcluster scopeであり、selectorによって適用対象のworkloadやHostEndpointを定義します。Calicoのaction、order、tierを追加しますが、すべてのPodに自動適用されるわけではなく、必要なintegrationなしにL7 inspectionを有効にするものでもありません。

</details>

6. Calicoのpolicy modelにおけるTierとは何ですか？
   - A) trafficを分離するnetwork segment
   - B) policyの評価順序を制御する階層的なgroup
   - C) Calico Enterpriseの料金level
   - D) network暗号化の種類

<details>
<summary>解答を表示</summary>

**解答: B) policyの評価順序を制御する階層的なgroup**

**解説:** Tierはpolicyを優先度別にgroup化します。数値の小さいtier orderから評価し、そのtier内ではpolicy orderに従います。Allow/Denyは終端actionです。Passは次に該当するtierへ処理を渡し、最終的にはprofileへ進みます。security/platform/applicationなどの名前は利用者が定義するもので、必須のdefault階層ではありません。

</details>

7. CalicoのWorkloadEndpointは何を表しますか？
   - A) Kubernetes Service endpoint
   - B) PodまたはVM workloadに関連付けられたnetwork interface
   - C) 外部API endpoint
   - D) storage mount point

<details>
<summary>解答を表示</summary>

**解答: B) PodまたはVM workloadに関連付けられたnetwork interface**

**解説:** WorkloadEndpointは、policyの計算に使うIP/MAC/interface情報、label、profile参照を持つworkload interfaceを表します。通常、そのlifecycleはpluginまたはorchestratorが管理します。Service EndpointSliceでも、実効policy判定をすべて列挙した保存一覧でもありません。

</details>

8. CalicoのBGPPeerとBGPConfigurationはどのような関係ですか？
   - A) 同じresourceの別名である
   - B) BGPConfigurationはglobal BGP設定を行い、BGPPeerは個別のpeering sessionを定義する
   - C) BGPPeerは内部peer用で、BGPConfigurationは外部peer用である
   - D) BGPConfigurationはBGPPeerに置き換えられ、非推奨である

<details>
<summary>解答を表示</summary>

**解答: B) BGPConfigurationはglobal BGP設定を行い、BGPPeerは個別のpeering sessionを定義する**

**解説:** defaultのBGPConfigurationは、ASNやmesh/service advertisement設定などのcluster defaultを定義します。サポート対象のNode単位のoverrideは別設定です。BGPPeerはpeer addressまたはselectorによって、意図するpeering関係を指定します。それだけでsessionや必要なrouteが確立したと保証されるわけではありません。

</details>

9. CalicoのNetworkSetとは何ですか？Ciliumで関連する概念はどれですか？
   - A) Serviceのgroup。Cilium ServiceGroupに相当する
   - B) label付きIP/CIDR set。CIDR policy参照に使うCiliumCIDRGroupが関連する概念である
   - C) namespace collection。Cilium ClusterPolicyに相当する
   - D) DNS zone設定。Cilium DNSPolicyに相当する

<details>
<summary>解答を表示</summary>

**解答: B) label付きIP/CIDR set。CIDR policy参照に使うCiliumCIDRGroupが関連する概念である**

**解説:** CalicoのNetworkSetはnamespace scope、GlobalNetworkSetはcluster scopeであり、どちらもlabel付きIP/CIDR setを提供します。CiliumCIDRGroupはcluster scopeで、Cilium CIDR ruleから`cidrGroupRef`または`cidrGroupSelector`を使って参照できます。関連する概念ですがAPIは異なり、DNS ruleでも相互に置き換えられるmanifestでもありません。

</details>

10. CalicoのHostEndpointの目的は何ですか？
    - A) container endpointを定義する
    - B) host interface（Pod以外のtraffic）にnetwork policyを適用する
    - C) hostのDNSを設定する
    - D) Node labelを管理する

<details>
<summary>解答を表示</summary>

**解答: B) host interface（Pod以外のtraffic）にnetwork policyを適用する**

**解説:** HostEndpointは、host trafficおよび設定されている場合はforwarded trafficにpolicyを適用するためのhost interfaceを表します。作成・enforceする前に、profile、failsafe、管理経路を確認してください。workload policyとhost policyのscopeは異なりますが、forwarded Pod trafficも影響を受けることがあります。

</details>
