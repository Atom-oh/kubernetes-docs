# Calico 入門クイズ

> **関連ドキュメント**: [Calico 入門](../../../networking/calico/01-introduction.md)
> **最終更新**: February 22, 2026

## クイズ

1. Project Calico は当初、何年に開始されましたか？
   - A) 2012
   - B) 2014
   - C) 2016
   - D) 2018

<details>
<summary>回答を表示</summary>

**回答: B) 2014**

**解説:**
Project Calico は、2014 年に Metaswitch で開始されました。その後、世界で最も広く使用されている Kubernetes CNI プラグインの 1 つへと成長しました。2016 年には Calico を商用化するために Tigera が設立され、2019 年には Calico Enterprise がリリースされました。

</details>

2. Tigera を設立し、Calico を商用化したのはどの企業ですか？
   - A) Google
   - B) Red Hat
   - C) Metaswitch の創設者
   - D) VMware

<details>
<summary>回答を表示</summary>

**回答: C) Metaswitch の創設者**

**解説:**
Tigera は 2016 年に、Metaswitch の Project Calico の当初の開発者によって設立されました。現在、Tigera はオープンソースの Calico プロジェクトを維持するとともに、Calico Enterprise や Calico Cloud などの商用製品を提供しています。

</details>

3. 次のうち、Calico のコア機能ではないものはどれですか？
   - A) BGP ベースのルーティング
   - B) sidecar injection を備えた組み込み service mesh
   - C) Kubernetes 標準および拡張 network policy
   - D) eBPF dataplane のサポート

<details>
<summary>回答を表示</summary>

**回答: B) sidecar injection を備えた組み込み service mesh**

**解説:**
Calico は、BGP-based routing、強力な network policy（Kubernetes 標準および Calico 拡張）、eBPF dataplane のサポートによる高性能なネットワーキングを提供します。ただし、Cilium とは異なり、Calico には組み込みの service mesh は含まれていません。service mesh 機能は、Calico Enterprise を通じて個別に利用するか、Istio などの他の service mesh ソリューションと統合することで利用できます。

</details>

4. 従来の overlay network と比較した場合、Calico の BGP-based networking の主な利点は何ですか？
   - A) より簡単な configuration
   - B) より優れた security encryption
   - C) encapsulation overhead のない直接ルーティング
   - D) 組み込み DNS resolution

<details>
<summary>回答を表示</summary>

**回答: C) encapsulation overhead のない直接ルーティング**

**解説:**
Calico の BGP-based networking は、encapsulation（VXLAN や IPIP など）のオーバーヘッドなしに、node 間で packet を直接ルーティングできます。これにより、network performance の向上、latency の低減、既存の network infrastructure との統合の容易化が実現します。従来の overlay network では encapsulation header が追加され、packet size と処理オーバーヘッドが増加します。

</details>

5. Calico はどの環境をサポートしていますか？
   - A) Cloud のみ
   - B) オンプレミスのみ
   - C) Cloud、オンプレミス、hybrid
   - D) Kubernetes のみ、VM サポートなし

<details>
<summary>回答を表示</summary>

**回答: C) Cloud、オンプレミス、hybrid**

**解説:**
Calico は、public cloud（AWS、Azure、GCP）、オンプレミス data center、hybrid deployment を含む複数の環境をサポートする柔軟な networking solution です。Kubernetes container だけでなく、virtual machine や bare-metal workload でも使用できます。

</details>

6. Calico はどの dataplane オプションをサポートしていますか？
   - A) iptables のみ
   - B) eBPF のみ
   - C) iptables と eBPF
   - D) IPVS のみ

<details>
<summary>回答を表示</summary>

**回答: C) iptables と eBPF**

**解説:**
Calico は iptables と eBPF の両方の dataplane をサポートしています。iptables dataplane は従来からある最も成熟したオプションであり、eBPF mode は 2020 年に導入され、CPU 使用量を抑えながら performance を向上させます。ユーザーは、要件と kernel version のサポートに最も適した dataplane を選択できます。

</details>

7. calicoctl とは何ですか？
   - A) Calico 用の graphical user interface
   - B) Calico resource を管理する command-line tool
   - C) Calico 用の Kubernetes operator
   - D) monitoring dashboard

<details>
<summary>回答を表示</summary>

**回答: B) Calico resource を管理する command-line tool**

**解説:**
calicoctl は、network policy、IP pool、BGP configuration、node などの Calico resource を管理するための command-line interface tool です。Calico datastore へ直接アクセスでき、kubectl だけでは容易に実行できない troubleshooting、diagnostics、高度な configuration task に不可欠です。

</details>

8. Calico OSS と Calico Enterprise の関係は何ですか？
   - A) 共有コードのない完全に別個の製品
   - B) Calico Enterprise は Calico OSS を基盤とする商用バージョン
   - C) Calico OSS は Calico Enterprise を優先して非推奨
   - D) Calico Enterprise は Calico Cloud でのみ動作する

<details>
<summary>回答を表示</summary>

**回答: B) Calico Enterprise は Calico OSS を基盤とする商用バージョン**

**解説:**
Calico Enterprise は、オープンソースの Calico project を基盤とする Tigera の商用製品です。advanced threat detection、compliance reporting、multi-cluster management、商用サポートなどの enterprise feature を追加します。コアとなる networking と policy の機能は、両方のバージョンで共有されています。

</details>

9. Calico が eBPF dataplane のサポートを導入したのは何年ですか？
   - A) 2018
   - B) 2019
   - C) 2020
   - D) 2022

<details>
<summary>回答を表示</summary>

**回答: C) 2020**

**解説:**
Calico は 2020 年に eBPF dataplane のサポートを導入しました。これは重要なマイルストーンであり、iptables dataplane より少ない CPU 使用量で、Direct Server Return（DSR）、connection-time load balancing、kube-proxy の置き換えといった機能による performance 向上を Calico にもたらしました。

</details>

10. Calico Cloud とは何ですか？
    - A) managed Kubernetes service
    - B) Calico network security 向け SaaS platform
    - C) cloud storage solution
    - D) Kubernetes 向け CDN service

<details>
<summary>回答を表示</summary>

**回答: B) Calico network security 向け SaaS platform**

**解説:**
2022 年に開始された Calico Cloud は、Calico Enterprise の機能を managed service として提供する Tigera の SaaS（Software as a Service）製品です。enterprise component を自ら管理する運用オーバーヘッドなしに、高度な network security、observability、compliance 機能の deployment と管理を簡素化します。

</details>

---

[学習資料に戻る](../../../networking/calico/01-introduction.md) | [次のクイズ: アーキテクチャ](./02-architecture-quiz.md)
