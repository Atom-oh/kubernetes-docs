# Amazon VPC CNI クイズ

以下の問題で、Amazon VPC CNI の理解度を確認します。

---

1. VPC CNI における IPAMD (L-IPAM Daemon) の主な役割は何ですか？
   - A) Pod DNS 設定の管理
   - B) ENI と IP アドレスの事前割り当ておよび管理
   - C) Network Policy の適用
   - D) ノード間トラフィックの暗号化

<details>
<summary>回答を表示</summary>

**回答: B) ENI と IP アドレスの事前割り当ておよび管理**

**解説:**
IPAMD (L-IPAM Daemon) は各ノードで稼働する daemon であり、ENI (Elastic Network Interface) を管理し、Pod が作成されたときに IP を迅速に割り当てられるよう IP アドレスを事前割り当てします。CNI Binary は kubelet によって呼び出され、IPAMD から IP を受け取り、Pod network namespace を設定します。

</details>

---

2. Secondary IP mode と Prefix Delegation mode の主な違いは何ですか？
   - A) Secondary IP は IPv6 のみをサポートし、Prefix Delegation は IPv4 のみをサポートする
   - B) Secondary IP は個別の IP を割り当て、Prefix Delegation は /28 prefix (16 IP) を割り当てる
   - C) Secondary IP は EKS 専用であり、Prefix Delegation は self-managed cluster 専用である
   - D) Secondary IP は overlay network を使用し、Prefix Delegation は direct routing を使用する

<details>
<summary>回答を表示</summary>

**回答: B) Secondary IP は個別の IP を割り当て、Prefix Delegation は /28 prefix (16 IP) を割り当てる**

**解説:**
Secondary IP mode は各 ENI に個別の IP アドレスを1つずつ割り当てる一方、Prefix Delegation mode は /28 IPv4 prefix (16 IP) をまとめて割り当てます。これにより、ノードあたりでより多くの Pod を実行でき、IP 割り当て速度も向上します。

</details>

---

3. VPC CNI で m5.large instance の最大 Pod 数が 29 である理由は何ですか？
   - A) Kubernetes のデフォルト上限が 29 であるため
   - B) 最大 3 ENI × ENI あたり 10 IP = 30 から、Primary IP 用の ENI 数 (3) を引くため
   - C) AWS soft limit によって制限されるため
   - D) VPC subnet サイズによって制限されるため

<details>
<summary>回答を表示</summary>

**回答: B) 最大 3 ENI × ENI あたり 10 IP = 30 から、Primary IP 用の ENI 数 (3) を引くため**

**解説:**
VPC CNI における最大 Pod 数は、(ENI 数 × ENI あたりの IP 数) - ENI 数として計算されます。m5.large は ENI あたり 10 個の IPv4 アドレスを持つ最大 3 個の ENI をサポートします。各 ENI の Primary IP はノードによって使用されるため、(3 × 10) - 3 = 27 です。実際の数は host networking Pod やその他の要因により多少異なる場合があります。

</details>

---

4. WARM_IP_TARGET environment variable の目的は何ですか？
   - A) Pod に割り当て可能な IP の最大数を設定する
   - B) 各ノードで事前割り当てする予備 IP の数を設定する
   - C) cluster 全体の IP 総数を制限する
   - D) IP アドレスの TTL (Time To Live) を設定する

<details>
<summary>回答を表示</summary>

**回答: B) 各ノードで事前割り当てする予備 IP の数を設定する**

**解説:**
WARM_IP_TARGET は、IPAMD が各ノードで事前割り当てする予備 IP の数を制御します。これにより、新しい Pod が作成されたときに IP をすぐに利用できます。値を大きくすると Pod の起動は高速化しますが、より多くの IP を使用します。一方、値を小さくすると IP 効率は向上しますが、Pod の起動が遅くなる場合があります。

</details>

---

5. VPC CNI の native Network Policy サポートに関する正しい記述はどれですか？
   - A) Network Policy を強制するために内部で Calico を使用する
   - B) v1.14 以降、native eBPF-based Network Policy をサポートする
   - C) EKS では Network Policy はサポートされていない
   - D) Network Policy を強制するために iptables を使用する

<details>
<summary>回答を表示</summary>

**回答: B) v1.14 以降、native eBPF-based Network Policy をサポートする**

**解説:**
VPC CNI v1.14 以降、eBPF に基づく native Kubernetes Network Policy がサポートされています。以前は Calico のような個別の Network Policy engine が必要でしたが、現在は VPC CNI 自体が標準の Kubernetes NetworkPolicy resource を処理できます。

</details>

---

6. Custom Networking (ENIConfig) を使用する主な目的は何ですか？
   - A) Pod DNS server 設定のカスタマイズ
   - B) ノードとは異なる subnet から Pod IP を割り当てる
   - C) カスタム CNI plugin のインストール
   - D) ノードの network interface の名前変更

<details>
<summary>回答を表示</summary>

**回答: B) ノードとは異なる subnet から Pod IP を割り当てる**

**解説:**
Custom Networking は ENIConfig CRD を使用して、ノードとは異なる subnet から Pod IP を割り当てます。これは、ノード subnet の IP が不足している場合、Pod に異なる security group を適用する必要がある場合、またはノードと Pod の network を分離する必要がある場合に有用です。通常は Secondary CIDR (例: 100.64.0.0/16) とともに使用されます。

</details>

---

7. per-Pod Security Group 機能における Trunk ENI と Branch ENI の役割は何ですか？
   - A) Trunk ENI は外部トラフィックを処理し、Branch ENI は内部トラフィックを処理する
   - B) Trunk ENI は Branch ENI をホストするノードのメイン ENI であり、Branch ENI は各 Pod に割り当てられる virtual ENI である
   - C) Trunk ENI は IPv4 用であり、Branch ENI は IPv6 用である
   - D) Trunk ENI と Branch ENI は同一の役割を果たす

<details>
<summary>回答を表示</summary>

**回答: B) Trunk ENI は Branch ENI をホストするノードのメイン ENI であり、Branch ENI は各 Pod に割り当てられる virtual ENI である**

**解説:**
per-Pod Security Group は Trunk/Branch ENI architecture を使用します。Trunk ENI は複数の Branch ENI をホストする、ノードにアタッチされたメイン ENI です。Branch ENI は各 Pod に割り当てられる virtual network interface であり、独立した AWS Security Group enforcement を可能にします。これにより、Pod レベルで詳細な network security control が可能になります。

</details>

---

8. IP 枯渇問題に対する効果的な解決策ではないものはどれですか？
   - A) Prefix Delegation を有効にする
   - B) Secondary CIDR を追加する
   - C) すべての Pod を host network mode に切り替える
   - D) 専用 Pod subnet を使用する Custom Networking を使用する

<details>
<summary>回答を表示</summary>

**回答: C) すべての Pod を host network mode に切り替える**

**解説:**
すべての Pod を host network mode (`hostNetwork: true`) で実行すると技術的には IP 割り当て問題を解決できますが、Pod 間の network isolation がなくなり、port conflict を引き起こす可能性があるため、実用的な解決策ではありません。IP 枯渇に対する適切な解決策には、Prefix Delegation の有効化、Secondary CIDR の追加、Custom Networking の使用、および WARM_IP_TARGET の tuning が含まれます。

</details>
