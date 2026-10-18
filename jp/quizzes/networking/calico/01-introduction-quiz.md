# Calico 入門クイズ

> **関連ドキュメント**: [Calico 入門](../../../networking/calico/01-introduction.md)
> **最終更新**: 2026年9月12日

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
Project Calico は2014年にMetaswitchで始まりました。Tigeraは2016年に設立されました。プロジェクトの開始時期と、その後の製品リリース時期を混同しないでください。

</details>

2. Calicoの主なメンテナーであり、Calico EnterpriseとCalico Cloudを提供する企業はどこですか？
   - A) Google
   - B) Red Hat
   - C) Tigera
   - D) VMware

<details>
<summary>回答を表示</summary>

**回答: C) Tigera**

**解説:**
Tigeraはコミュニティの貢献者とともにCalicoをメンテナンスし、商用製品も提供しています。「Metaswitchの創設者」は人々を説明する表現であり、質問が尋ねている企業名ではありません。CNCF Landscapeに掲載されていることは、CNCFがプロジェクトを統治していることを意味しません。

</details>

3. デフォルトのCalicoインストールについて、正しくない説明はどれですか？
   - A) BGPベースのルーティング
   - B) すべてのPodにIstio sidecarを自動注入する
   - C) Kubernetes標準および拡張ネットワークポリシー
   - D) eBPFデータプレーンのサポート

<details>
<summary>回答を表示</summary>

**回答: B) すべてのPodにIstio sidecarを自動注入する**

**解説:**
Calicoはネットワーキング、ポリシー、選択可能なデータプレーンを提供します。meshとの統合は別の機能や設定であり、このラボのインストールがIstio sidecarを自動注入するわけではありません。Ciliumのmesh機能にも個別の設定が必要です。CNIの比較では、mesh機能がデフォルトですべて有効だと示唆しないようにしてください。

</details>

4. BGPとunderlay routeを正しく設定した非カプセル化Calicoトポロジーでは、何が可能になりますか？
   - A) より簡単な設定
   - B) より強力な暗号化
   - C) underlayがPod routeをサポートする場合、overlayカプセル化ヘッダーを使わないルーティング
   - D) DNS名前解決を組み込みで提供

<details>
<summary>回答を表示</summary>

**回答: C) underlayがPod routeをサポートする場合、overlayカプセル化ヘッダーを使わないルーティング**

**解説:**
BGPはrouteを配布します。underlayでPod addressをルーティングでき、カプセル化を無効にしている場合、パケットにIPIP／VXLANのwrapperは不要です。BGPとIPIPは併用できるため、BGPを有効にしただけではカプセル化はなくなりません。BGPはトラフィックを暗号化せず、すべてのワークロードでレイテンシーが下がるとも限りません。

</details>

5. 適切なCalico構成と製品エディションは、どの環境で利用できますか？
   - A) クラウドのみ
   - B) オンプレミスのみ
   - C) クラウド、オンプレミス、ハイブリッド
   - D) Kubernetesのみ（VMはサポートしない）

<details>
<summary>回答を表示</summary>

**回答: C) クラウド、オンプレミス、ハイブリッド**

**解説:**
適切なCalico構成と製品エディションは、クラウド、オンプレミス、ハイブリッド環境で利用できます。ただしプラットフォーム、カーネル、データプレーン、エディションによる制約があります。GKE Dataplane V2はCalicoではなくCiliumを使います。VMやWindowsの機能は、Linux Kubernetesの機能と同一ではありません。

</details>

6. CalicoがサポートするLinuxデータプレーンの組み合わせはどれですか？
   - A) iptables のみ
   - B) eBPF のみ
   - C) iptables、nftables、eBPF
   - D) IPVS のみ

<details>
<summary>回答を表示</summary>

**回答: C) iptables、nftables、eBPF**

**解説:**
Calicoはこれら3つのLinuxデータプレーンに対応しています。VXLAN／IPIPなどのカプセル化方式は別の選択項目です。IPVSはkube-proxyのバックエンドであり、Calicoのデータプレーン全体を指すものではありません。カーネル、プラットフォーム、必要な機能に応じて選択してください。このラボではiptablesを明示的に使います。

</details>

7. calicoctl とは何ですか？
   - A) Calicoのグラフィカルユーザーインターフェース
   - B) Calicoリソースを管理するコマンドラインツール
   - C) CalicoのKubernetes operator
   - D) 監視ダッシュボード

<details>
<summary>回答を表示</summary>

**回答: B) Calicoリソースを管理するコマンドラインツール**

**解説:**
calicoctlはCalico resourceを管理し、IPAMやBGP操作などの診断にも使えます。対応するバージョンのクライアントを使用してください。日常的なresource操作の多くは、Calico API serverに対するkubectlでも実行できます。`calicoctl node status`には適切なnode環境が必要であり、ノートPCのkubeconfigだけでは実行できません。

</details>

8. Calico OSS と Calico Enterprise の関係は何ですか？
   - A) コードを共有しない完全に別の製品
   - B) Calico EnterpriseはCalico OSSを基盤とした商用版
   - C) Calico OSSはCalico Enterpriseへの移行のため非推奨
   - D) Calico EnterpriseはCalico Cloudでのみ動作

<details>
<summary>回答を表示</summary>

**回答: B) Calico EnterpriseはCalico OSSを基盤とした商用版**

**解説:**
EnterpriseはCalicoの技術を基盤に商用機能とサポートを追加します。オープンソース版にもpolicy tierやGoldmane／Whiskerによる可観測性があり、本番環境で利用できます。高度な機能がすべて有料、またはOSS版は小規模クラスター専用だと決めつけず、現在の機能マトリクスを確認してください。

</details>

9. CalicoがeBPFデータプレーンのサポートを導入したのは何年ですか？
   - A) 2018
   - B) 2019
   - C) 2020
   - D) 2022

<details>
<summary>回答を表示</summary>

**回答: C) 2020**

**解説:**
2020年2月25日の公式発表では、Calico 3.13向けの新しいデータプレーンがtech previewとして紹介されました。これはGAの発表ではありません。eBPFはLinuxカーネル内で実行され、カーネル自体を置き換えるのではなく、従来のパケット処理の一部を置き換えられます。性能は実際に測定するワークロードによって異なります。

</details>

10. Calico Cloud とは何ですか？
   - A) マネージドKubernetesサービス
   - B) Calicoネットワークセキュリティ向けSaaSプラットフォーム
   - C) クラウドストレージサービス
   - D) Kubernetes向けCDNサービス

<details>
<summary>回答を表示</summary>

**回答: B) Calicoネットワークセキュリティ向けSaaSプラットフォーム**

**解説:**
Calico Cloudは、ネットワークセキュリティと可観測性を提供するTigeraのSaaSです。Kubernetesホスティングサービス、オブジェクトストレージ、CDNではありません。セルフマネージドのEnterpriseとは機能と運用責任が異なり、クラスターの統合や設定は引き続き必要です。この定義に不要な過去のリリース年は省いています。

</details>

---

[学習資料に戻る](../../../networking/calico/01-introduction.md) | [次のクイズ: アーキテクチャ](02-architecture-quiz.md)
