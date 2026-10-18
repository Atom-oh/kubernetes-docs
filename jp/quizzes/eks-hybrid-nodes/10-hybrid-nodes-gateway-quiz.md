# EKS Hybrid Nodes Gatewayクイズ

> **最終更新日**: 2026年9月13日

1. EKS Hybrid Nodes Gatewayはどのような問題を解決しますか？
   - A) control plane接続用のVPN/Direct Connectを置き換える
   - B) Gatewayが管理するPod routeと、VPC・Hybrid Node間のVXLAN転送を自動化する
   - C) Hybrid Node用のmanaged NAT gatewayを提供する
   - D) cloudとon-premises間のすべてのtrafficを暗号化する

<details>
<summary>解答を表示</summary>

**解答: B) Gatewayが管理するPod routeと、VPC・Hybrid Node間のVXLAN転送を自動化する**

**解説:** GatewayはaggregateされたVPC Pod CIDR routeと、ローカルのVXLAN転送状態を設定します。underlayでは、承認済みのprivate connectionを介してGatewayとHybrid NodeのIP間をroutingできる必要があります。route tableの所有者、戻り経路、security ruleを確認してください。インストールしてもすべての手動network作業が不要になるわけではなく、uninstallしてもAWS routeは削除されません。

</details>

---

2. Gatewayはどのようにhigh availabilityを実現しますか？
   - A) 複数Gateway間のload balancingによるactive-active構成
   - B) Kubernetes Lease-based leader electionを使うDeployment内の2つのGateway Pod
   - C) AWS managed redundancyによる自動failover
   - D) Route 53 health checkを使い、複数Availability Zoneで実行する

<details>
<summary>解答を表示</summary>

**解答: B) Kubernetes Lease-based leader electionを使うDeployment内の2つのGateway Pod**

**解説:** chartのdefaultは、2 replica、必須のhost anti-affinity、優先的なAZ anti-affinityです。両方のPodがローカルのtunnel entryを維持し、leaderだけがVPC routeとCiliumVTEPConfigを更新します。Leaseの期限切れ、route置換、Ciliumの収束、アプリケーション復旧の間にtrafficが中断する場合があります。standby replicaを増やしてもthroughputは分散されず、PDBもleaderまたはstandbyを先に置き換える保証にはなりません。

</details>

---

3. Gateway architectureでCiliumVTEPConfigはどの役割を担いますか？
   - A) Hybrid Node向けのCilium network policyを設定する
   - B) Gateway IPをremote VTEPとして登録し、Hybrid Node上のCilium agentがVPC宛trafficをGatewayのVXLAN tunnel経由で転送できるようにする
   - C) cluster全体のCilium version upgradeを管理する
   - D) VXLAN tunnel用の暗号化keyを提供する

<details>
<summary>解答を表示</summary>

**解答: B) Gateway IPをremote VTEPとして登録し、Hybrid Node上のCilium agentがVPC宛trafficをGatewayのVXLAN tunnel経由で転送できるようにする**

**解説:** Gateway 1.0.2は`cilium.io/v2`の`hybrid-gateway`というobjectを管理します。`spec.endpoints`には`name`、`tunnelEndpoint`、`cidr`、`mac`が含まれます。endpointには現在のleader NodeのIPと、実際のVXLAN interfaceのMACを指定します。これは暗号化key用のresourceではなく、VNIもこのCRDのfieldではありません。

</details>

---

4. Hybrid Nodes Gatewayを使うためのCNI prerequisiteはどれですか？
   - A) cloud NodeとHybrid Nodeの両方で任意のCNI
   - B) cloud NodeでCilium、Hybrid NodeでVPC CNI
   - C) VTEP有効かつL7無効のAWS-maintained Ciliumと、正しいcloud Node networking設定
   - D) cloud NodeとHybrid Nodeの両方でVPC CNI

<details>
<summary>解答を表示</summary>

**解答: C) VTEP有効かつL7無効のAWS-maintained Ciliumと、正しいcloud Node networking設定**

**解説:** GatewayのVTEP最低要件を満たすAWS-maintained Cilium branch/versionを使用し、`vtep.enabled=true`と`l7Proxy=false`を設定します。Cilium Ingress/Gateway APIのL7機能はこの設定と併用できません。`aws-node`を使うmanaged/self-managed cloud Nodeでは、ClusterIPからHybrid endpointへのtrafficに対するSNATからHybrid Pod CIDRを除外する必要があります。Auto Modeはnetworkingを標準提供するため、`aws-node` DaemonSetをinstall・設定してはいけません。Pod IPへの直接通信だけではClusterIPの動作を検証できません。

</details>

---

5. Gatewayが使うVXLAN設定はどれですか？
   - A) UDP port 4789のVNI 1（標準VXLAN）
   - B) UDP port 8472のVNI 2（Cilium default）
   - C) UDP port 6081のVNI 100（Geneve）
   - D) UDP port 443のVNI 0（HTTPS encapsulation）

<details>
<summary>解答を表示</summary>

**解答: B) UDP port 8472のVNI 2（Cilium default）**

**解説:** default interfaceは`hybrid_vxlan0`で、VNI 2、UDP 8472を使います。version 1.0.2では、このinterfaceにIPを割り当てません。各Hybrid Nodeのinternal IPとPod CIDRを使って決定的なMACを導出し、FDB/neighbor/onlink route entryを設定します。必要なunderlay UDP経路は双方向で許可してください。VXLAN encapsulationはtrafficを暗号化しません。

</details>

---

6. GatewayはどのようにVPC routingを管理しますか？
   - A) BGPでPod routeをVPC routerに広告する
   - B) Hybrid Pod CIDRをactive Gatewayのprimary ENIに向けるVPC route table entryを自動で作成・維持する
   - C) VPCのmain route tableを変更し、NAT ruleを追加する
   - D) Transit Gateway route tableを設定する

<details>
<summary>解答を表示</summary>

**解答: B) Hybrid Pod CIDRをactive Gatewayのprimary ENIに向けるVPC route table entryを自動で作成・維持する**

**解説:** leaderの初期化処理は、設定済みのaggregate Pod CIDRのrouteを作成または置換してからCiliumVTEPConfigを更新します。別途、CiliumNode eventによって、すべてのGateway replica上のローカルなNode別tunnel entryが更新されます。runtime permissionは`DescribeRouteTables`、`DescribeInstances`、`CreateRoute`、`ReplaceRoute`です。`DeleteRoute`は呼び出しません。Gateway廃止後は、運用者が所有するrouteだけを確認して削除または復元してください。

</details>

---

7. EKS Hybrid Nodes Gatewayの料金体系はどれですか？
   - A) 処理したdata量に応じた時間単位の料金
   - B) Hybrid Node 1台あたり1時間$0.10のEKS Hybrid Nodes料金に含まれる
   - C) Gateway softwareの追加料金はないが、EC2やその他の該当するinfrastructure/traffic料金は発生する
   - D) 最初の3か月は無料で、その後は標準AWS networking料金がかかる

<details>
<summary>解答を表示</summary>

**解答: C) Gateway softwareの追加料金はないが、EC2やその他の該当するinfrastructure/traffic料金は発生する**

**解説:** Gateway software自体に追加料金はありません。EC2、該当するAuto Mode管理料金、storage、AZ間data transfer、private connectivity、observabilityは、clusterとHybrid Nodesの料金に加えて発生する場合があります。合計額はdeploymentとtrafficによって異なり、一律のコスト削減を保証するものではありません。

</details>

---

8. 手動のPod routing（BGP/static route）よりGateway方式を選ぶのはどのような場合ですか？
   - A) cloudとon-premisesのPod間で最低限のlatencyが必要な場合
   - B) AWS Cilium/VTEP profileとGateway hopが設計に適合し、Pod route管理を簡素化できる場合
   - C) Hybrid Nodeが1000台を超える場合
   - D) Hybrid NodeでCilium以外のCNIを使う場合

<details>
<summary>解答を表示</summary>

**解答: B) AWS Cilium/VTEP profileとGateway hopが設計に適合し、Pod route管理を簡素化できる場合**

**解説:** 必要なAWS Cilium/VTEP profileとactive-standbyの追加hopが設計に合う場合、GatewayはPod route管理を簡素化できます。webhookやALB/NLB targetには、それぞれ独自のrouting、戻り経路、remote Pod設定、health check、security ruleが引き続き必要です。route可能なPod networkを手動で用意する方法でも、これらの経路に対応できます。既存のBGP/static routingや、異なるCNI/L7要件がある場合は、別方式が適することがあります。

</details>
