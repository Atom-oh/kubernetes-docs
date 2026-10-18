# パート11: BGPコントロールプレーン、ロードバランサーIP、Egressクイズ

> **Cilium 1.20.2 · 2026-10-15**

1. **ENI IPAMを使うEKSクラスターで、`PodCIDR`タイプの`CiliumBGPAdvertisement`は何を実現しますか？**
   - A) 各ENIのセカンダリIPをすべて/32ルートとしてピアに広告する
   - B) VPCルートテーブルにルートを設定する
   - C) 各ノードからVPC CIDRを広告する
   - D) 実用的な効果はない。ENI IPAMではCiliumが所有するPodCIDRがノードに割り当てられないため、広告できるノード単位のプレフィックスがない

   <details>
   <summary>回答を表示</summary>

   **回答: D) 実用的な効果はない。ENI IPAMではCiliumが所有するPodCIDRがノードに割り当てられないため、広告できるノード単位のプレフィックスがない**

   `PodCIDR`広告が機能するのは、ノードごとにPodCIDRを割り当てるIPAMモード（cluster-pool、Kubernetes host scope）だけです。ENIではPod IPがすでにVPCアドレスであり、VPCによってルーティングされます。BGP Control Planeはクラウドのルートテーブルを設定しません。

   </details>

2. `CiliumBGPPeerConfig`は、ピアに送信する広告をどのように選択しますか？
   - A) `families[].advertisements`を使う。これは`CiliumBGPAdvertisement`オブジェクトの`metadata.labels`に一致させるラベルセレクター
   - B) ピアの`families`エントリで`advertisementType`を照合する
   - C) `peerConfigRef`に広告名を列挙する
   - D) ノードのannotationを使う

   <details>
   <summary>回答を表示</summary>

   **回答: A) `families[].advertisements`を使う。これは`CiliumBGPAdvertisement`オブジェクトの`metadata.labels`に一致させるラベルセレクター**

   ClusterConfigは名前でPeerConfigを参照しますが、PeerConfigは広告オブジェクトのラベルで広告を選択します。一致する広告がなくてもセッションは確立し、何も広告されない状態になります。

   </details>

3. `externalTrafficPolicy: Local`を設定した`LoadBalancer` ServiceをBGPで広告する場合、どのノードからVIPが広告されますか？
   - A) Serviceのリースを持つノードのみ
   - B) クラスター設定で選択されたすべてのノード
   - C) 少なくとも1つのローカルReadyバックエンドを持つノードのみ。ルートはPodに追従する
   - D) コントロールプレーンノードのみ

   <details>
   <summary>回答を表示</summary>

   **回答: C) 少なくとも1つのローカルReadyバックエンドを持つノードのみ。ルートはPodに追従する**

   `Cluster`では、選択されたすべてのノードからVIPが広告されます。`Local`では、Readyなローカルエンドポイントがないノードから広告が取り下げられます。リースはBGPではなくL2 announcementに属します。

   </details>

4. Cilium 1.19から1.20にアップグレードした後、BGPセッションのGrafanaパネルが空になりました。原因として考えられる変更はどれですか？
   - A) BGPメトリクスがoperatorへ移動した
   - B) インスタンス単位のラベル`vrouter`が`instance_name`になったが、1.20のアップグレードノートには記載されていない
   - C) `bgpControlPlane.metrics.enabled`を設定しない限りBGPメトリクスが無効になる
   - D) メトリクスのプレフィックスが`cilium_`から`bgp_`へ変わった

   <details>
   <summary>回答を表示</summary>

   **回答: B) インスタンス単位のラベル`vrouter`が`instance_name`になったが、1.20のアップグレードノートには記載されていない**

   1.19.8のメトリクスドキュメントでは`vrouter`を使いますが、1.20.2では`instance_name`です。古いラベルで絞り込むクエリやアラートは、エラーを出さずに一致しなくなります。

   </details>

5. 2つの`CiliumBGPAdvertisement`オブジェクトが、異なるcommunityと異なる`localPreference`値を使って同じServiceに一致します（Cilium 1.18以降）。何が広告されますか？
   - A) communityの和集合と、最大の`localPreference`
   - B) 最後に適用された広告の属性
   - C) アルファベット順で最初の広告だけ
   - D) 競合のためルートが取り下げられる

   <details>
   <summary>回答を表示</summary>

   **回答: A) communityの和集合と、最大の`localPreference`**

   1.18より前の動作は「最後に一致したものを採用」でした。`localPreference`はiBGPピアにのみ送信される点にも注意してください。

   </details>

6. v1の`CiliumBGPPeeringPolicy`とそのコントロールプレーンが削除されたのは、どのリリースですか？
   - A) 1.18
   - B) 1.20
   - C) 1.21
   - D) 1.19

   <details>
   <summary>回答を表示</summary>

   **回答: D) 1.19**

   1.18で非推奨となり、1.19で`pkg/bgpv1`とともに削除されました。そのため、クラスターを1.19にアップグレードする前に`cilium.io/v2` CRDへ移行する必要があります。v2 CRDのv2alpha1コピーは1.20と1.21-preでも引き続き提供されますが、非推奨です。

   </details>

7. Cilium 1.20でマルチホップBGPセッションの障害検出を速くするには、どうすべきですか？
   - A) `CiliumBGPPeerConfig.spec.bfd`でBFDを有効にする
   - B) BFDはサポートされないため、hold/keepaliveタイマーを短くする（CRDの最小値は3と1）。agentの再起動にはGraceful Restartを使う
   - C) `ebgpMultihop`を255にすると高速フェイルオーバーが有効になる
   - D) `connectRetryTimeSeconds: 1`を設定する

   <details>
   <summary>回答を表示</summary>

   **回答: B) BFDはサポートされないため、hold/keepaliveタイマーを短くする（CRDの最小値は3と1）。agentの再起動にはGraceful Restartを使う**

   1.18から1.21-preまでのCRDにはBFDフィールドがありません。よく推奨される9/3秒のタイマー値は積極的な設定例であり、CRDの最小値ではありません。`ebgpMultihop`はTTLだけを設定します。connect-retryは再接続に影響しますが、障害検出には影響しません。

   </details>

8. 既存の`TLSRoute`オブジェクトは`v1alpha2`であり、Gateway API v1.6.1を含むCilium 1.20にアップグレードする予定です。何をすべきですか？
   - A) 何もしない。standard-channelのCRDがオブジェクトを自動変換する
   - B) TLSRouteを削除し、アップグレード後に再作成する
   - C) TLSRouteをバックアップし、Ciliumをアップグレードする前に`v1alpha2`を引き続き含むexperimental-channelのv1.6.1 TLSRoute CRDをインストールする
   - D) standard-channelのv1.6 TLSRoute CRDだけをインストールする。これですべてのバージョンが残る

   <details>
   <summary>回答を表示</summary>

   **回答: C) TLSRouteをバックアップし、Ciliumをアップグレードする前に`v1alpha2`を引き続き含むexperimental-channelのv1.6.1 TLSRoute CRDをインストールする**

   standard-channelのv1.6 TLSRoute CRDをインストールすると、保存済みの`v1alpha2`オブジェクトが読み取り不能になり、消えたように見えます。

   </details>

9. デフォルトのL2 announcementリース設定（duration 15秒、renew deadline 5秒、retry 2秒）では、フェイルオーバー時間はおよそ何秒ですか？
   - A) 2～4秒
   - B) 正確に15秒
   - C) 30～60秒
   - D) 10～20秒

   <details>
   <summary>回答を表示</summary>

   **回答: D) 10～20秒**

   フェイルオーバー時間は`leaseDuration - leaseRenewDeadline`から`leaseDuration + leaseRenewDeadline`の範囲です。3秒/1秒/200ミリ秒に調整すると2～4秒になりますが、API QPSが増えるため、クライアントのレート制限を引き上げてください。

   </details>

10. `CiliumEgressGatewayPolicy`の`egressGateway.nodeSelector`に一致するノードがありません。選択されたPodから宛先CIDRへのトラフィックはどうなりますか？
    - A) ドロップされる
    - B) ランダムなノード経由で送信される
    - C) 通常のノードマスカレードにフォールバックする
    - D) Gatewayが現れるまでキューに入る

    <details>
    <summary>回答を表示</summary>

    **回答: A) ドロップされる**

    1.20.2および1.21.0-pre.3では、Egress Gatewayにヘルスベースのフェイルオーバーやフォールバックはありません。一致するGatewayがない場合、宛先CIDRへのトラフィックはドロップされます。

    </details>
