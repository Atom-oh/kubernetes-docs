# EKS Hybrid Nodes Gateway クイズ

1. EKS Hybrid Nodes Gateway はどのような問題を解決しますか？
   - A) control plane connectivity のための VPN/Direct Connect を置き換える
   - B) VXLAN tunnels を使用して VPC と hybrid nodes 間の pod-level networking を自動化し、手動の pod routing を不要にする
   - C) hybrid nodes 向けの managed NAT gateway を提供する
   - D) cloud と on-premises 間のすべての traffic を暗号化する

<details>
<summary>答えを表示</summary>

**回答: B) VXLAN tunnels を使用して VPC と hybrid nodes 間の pod-level networking を自動化し、手動の pod routing を不要にする**

**解説:**
EKS Hybrid Nodes Gateway は、EKS cluster VPC と Hybrid Nodes 上の Kubernetes Pods 間の networking を自動化します。EC2-based gateway nodes と Cilium-managed hybrid nodes の間に VXLAN tunnels を作成し、VPC route table entries を自動的に維持します。これにより、手動の BGP configuration、static routes、または on-premises pod networks を VPC から routable にする必要がなくなります。なお、基本的な node connectivity には VPN/Direct Connect が引き続き必要です。

</details>

---

2. gateway は high availability をどのように維持しますか？
   - A) 複数の gateways にまたがる load balancing による active-active
   - B) Kubernetes Lease-based leader election を備えた Deployment としての 2 つの gateway pods
   - C) automatic failover を備えた AWS-managed redundancy
   - D) Route 53 health checks を使用して複数の Availability Zones で実行する

<details>
<summary>答えを表示</summary>

**回答: B) Kubernetes Lease-based leader election を備えた Deployment としての 2 つの gateway pods**

**解説:**
gateway は、label 付き EC2 nodes 上で 2-pod Deployment として実行されます。Kubernetes Lease-based leader election により、どの pod が active になるかが決まります。leader だけが leader-specific actions、つまり VPC route table entries と CiliumVTEPConfig CRD の管理を行います。leader が失敗すると、leadership は standby pod に移り、その pod が VPC routes を更新して自身の ENI を指すようにします。

</details>

---

3. gateway architecture における CiliumVTEPConfig の役割は何ですか？
   - A) hybrid nodes の Cilium network policies を設定する
   - B) gateway IP を remote VTEP として登録し、hybrid nodes 上の Cilium agents が VPC-bound traffic を gateway の VXLAN tunnel 経由で転送できるようにする
   - C) cluster 全体の Cilium version upgrades を管理する
   - D) VXLAN tunnels の encryption keys を提供する

<details>
<summary>答えを表示</summary>

**回答: B) gateway IP を remote VTEP として登録し、hybrid nodes 上の Cilium agents が VPC-bound traffic を gateway の VXLAN tunnel 経由で転送できるようにする**

**解説:**
gateway leader は CiliumVTEPConfig resource を作成します。各 on-premises hybrid node の Cilium agent はこの configuration を読み取り、gateway IP を remote VTEP (VXLAN Tunnel Endpoint) として登録します。これにより Cilium は、VPC-bound traffic を直接 route しようとするのではなく、gateway の VXLAN tunnel 経由で送信する場所を把握できます。routable pod CIDRs がない場合、直接 route は失敗します。

</details>

---

4. Hybrid Nodes Gateway を使用するための CNI prerequisites は何ですか？
   - A) cloud nodes と hybrid nodes の両方で任意の CNI
   - B) cloud nodes で Cilium、hybrid nodes で VPC CNI
   - C) hybrid nodes で Cilium (VTEP enabled)、cloud nodes で VPC CNI
   - D) cloud nodes と hybrid nodes の両方で VPC CNI

<details>
<summary>答えを表示</summary>

**回答: C) hybrid nodes で Cilium (VTEP enabled)、cloud nodes で VPC CNI**

**解説:**
gateway には次が必要です: (1) hybrid nodes 上の CNI として、VTEP support が enabled の EKS version of Cilium。これにより hybrid nodes が VXLAN tunneling に参加できます。(2) cloud nodes 上の AWS VPC CNI。gateway は、VPC と VXLAN tunnel の間で traffic を転送するために VPC-native routing に依存しているためです。両方の CNIs は gateway を通じて連携し、seamless な pod-to-pod communication を可能にします。

</details>

---

5. gateway はどの VXLAN configuration を使用しますか？
   - A) UDP port 4789 上の VNI 1 (standard VXLAN)
   - B) UDP port 8472 上の VNI 2 (Cilium default)
   - C) UDP port 6081 上の VNI 100 (Geneve)
   - D) UDP port 443 上の VNI 0 (HTTPS encapsulation)

<details>
<summary>答えを表示</summary>

**回答: B) UDP port 8472 上の VNI 2 (Cilium default)**

**解説:**
gateway は、Cilium default VXLAN port である UDP port 8472 上に VNI (VXLAN Network Identifier) 2 を持つ `hybrid_vxlan0` という名前の VXLAN interface を作成します。VXLAN interface 上に FDB (Forwarding Database) entries、ARP entries、routes を設定することで、各 hybrid node への tunnel を確立します。Security groups と on-premises firewalls は、UDP 8472 を双方向に許可する必要があります。

</details>

---

6. gateway は VPC routing をどのように管理しますか？
   - A) BGP を使用して pod routes を VPC router に advertise する
   - B) hybrid pod CIDRs が active gateway の primary ENI を指す VPC route table entries を自動的に作成および維持する
   - C) VPC の main route table を変更して NAT rules を追加する
   - D) Transit Gateway route tables を設定する

<details>
<summary>答えを表示</summary>

**回答: B) hybrid pod CIDRs が active gateway の primary ENI を指す VPC route table entries を自動的に作成および維持する**

**解説:**
gateway の node controller は CiliumNode objects を監視し、hybrid nodes が参加または離脱すると VXLAN tunnels を自動的に追加または削除します。leader pod は VPC route table entries を維持し、各 hybrid pod CIDR を active gateway instance の primary ENI に route します。そのため、gateway の IAM role には ec2:DescribeRouteTables、ec2:CreateRoute、ec2:ReplaceRoute permissions が必要です。

</details>

---

7. EKS Hybrid Nodes Gateway の pricing model は何ですか？
   - A) 処理された data に基づく hourly charge
   - B) hybrid node ごとに 1 時間あたり $0.10 の EKS Hybrid Nodes pricing に含まれる
   - C) gateway 自体に追加料金はないが、gateway nodes の EC2 instance costs は発生する
   - D) 最初の 3 か月は無料で、その後は standard AWS networking charges

<details>
<summary>答えを表示</summary>

**回答: C) gateway 自体に追加料金はないが、gateway nodes の EC2 instance costs は発生する**

**解説:**
EKS Hybrid Nodes Gateway は追加料金なしで提供され、open source (GitHub で利用可能) です。ただし、gateway は VPC 内の EC2 instances 上で実行されるため、gateway nodes には standard EC2 instance costs が発生します。これにより、複雑な BGP や static routing infrastructure を手動で管理する場合と比べて、cost-effective な solution になります。

</details>

---

8. manual pod routing (BGP/static routes) よりも gateway approach を選ぶべきなのはどのような場合ですか？
   - A) cloud と on-premises pods 間で可能な限り低い latency が必要な場合
   - B) operations を簡素化し、webhook communication と AWS service integration を有効にしながら、on-premises pod networks を routable にすることを避けたい場合
   - C) 1000 を超える hybrid nodes がある場合
   - D) hybrid nodes で non-Cilium CNI を使用している場合

<details>
<summary>答えを表示</summary>

**回答: B) operations を簡素化し、webhook communication と AWS service integration を有効にしながら、on-premises pod networks を routable にすることを避けたい場合**

**解説:**
gateway は、複雑な network infrastructure changes (BGP configuration、static route management) を避けたい場合に最適です。自動的に次を有効にします: (1) hybrid nodes 上の control plane-to-webhook communication、(2) cloud と on-premises 間の pod-to-pod traffic、(3) hybrid pods への AWS service connectivity (ALB、NLB、Prometheus)。すでに BGP infrastructure がある場合や、gateway 経由の extra hop を最小限にしたい場合は、manual BGP approach が引き続き好まれることがあります。

</details>
