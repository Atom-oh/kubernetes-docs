# Linkerd インストールクイズ

2026年10月16日に edge-26.10.1 と charts 2026.10.1 を基準に確認しています。前提条件と検証の範囲全体については、[インストールガイド](../../../service-mesh/linkerd/01-installation.md) を参照してください。

### 1. このガイドで使う正確な公開 CLI を入手する方法はどれですか?

A. `linkerd` という名前のパッケージなら、どれも同じバージョンだと仮定する

B. OS/architecture に合う公式 edge-26.10.1 asset を選び、checksum と client version を検証する

C. `kubectl install linkerd` を使う

D. `--version stable-2.16.0` を解析しない installer に渡す

<details>
<summary>答えと解説</summary>

**答え: B**

ガイドでは公式 release asset のバージョンを固定しています。installer を使う場合は `LINKERD2_VERSION` を指定します。古い install script は非推奨で、現在は既定で edge を使います。stable distribution についてはベンダーの手順に従ってください。Windows 用の release asset 名は `windows.exe` です。`windows-amd64.exe` という名前を作ってはいけません。

</details>

### 2. 新規インストール前に実行する preflight command はどれですか?

A. `linkerd check`

B. `linkerd check --pre`

C. `linkerd verify`

D. `linkerd install --dry-run`

<details>
<summary>答えと解説</summary>

**答え: B**

`check --pre` は API access、Kubernetes の最小 version、Gateway API の前提条件、インストールに必要な権限や準備状況を確認します。後続のすべての Kubernetes version との互換性を証明するものではありません。正確な version matrix を確認し、該当するインストール経路を選ぶ場合は CNI 対応の flag を使ってください。

</details>

### 3. 手動の Helm 経路で必要な identity の素材はどれですか?

A. Envoy image

B. 公開 trust anchor と issuer certificate/private key、またはサポートされている設定済み issuer-secret integration

C. 各 proxy Pod 内の root CA private key

D. Prometheus 設定ファイル

<details>
<summary>答えと解説</summary>

**答え: B**

この経路では control-plane Helm chart は workload identity CA の素材を生成しません。公開 trust anchor と issuer の署名用 credential を用意してください。root private key は Kubernetes の外に保管します。外部 issuer-secret integration を使う場合は、対応する scheme/owner の設定も必要です。

</details>

### 4. パッケージ済み HA profile は、重要な control-plane component の replica をいくつ選びますか?

A. 1

B. 2

C. 3

D. 5

<details>
<summary>答えと解説</summary>

**答え: C**

この profile は、node anti-affinity、PDB、Fail に設定した injection-webhook policy とともに、重要 component を 3 replica 選択します。これは冗長な serving instance であり、quorum voter ではありません。利用可能な node、resource、正常な credential と network path も必要です。replica 数だけでは可用性は保証されません。

</details>

### 5. Viz の主な機能ではないものはどれですか?

A. Web dashboard

B. Prometheus ベースの metrics

C. Canary の自動昇格

D. HTTP traffic tap

<details>
<summary>答えと解説</summary>

**答え: C**

Viz は metrics、dashboard、tap 機能を提供します。Canary の段階的な進行には、別の delivery controller と分析 policy が必要です。現行 Viz chart は外部 Grafana への link を提供します。`grafana.enabled` は同梱 Grafana を deploy したり、無効化したりする設定ではありません。

</details>

### 6. Linkerd mTLS を終端せずに gateway の raw TCP transport を維持できる AWS load balancer はどれですか?

A. ALB HTTP listener

B. dashboard Ingress resource

C. NLB TCP listener

D. Gateway Load Balancer の GENEVE appliance 経路

<details>
<summary>答えと解説</summary>

**答え: C**

Linkerd gateway の transport には TCP passthrough を使います。NLB を internal にするか internet-facing にするかは、別の load balancer 製品の選択ではなく、ネットワーク要件によって決まる scheme の設定です。ガイドの internal NLB 例は、AWS Load Balancer Controller が管理すること、およびリモートネットワークや probe path から到達できることを前提としています。

</details>

### 7. 文書化された upgrade 手順の順序はどれですか?

A. data plane の後に control plane と CRD

B. target CLI、CRD、control plane、インストール済み extension、その後 data plane

C. CRD、data plane、その後 control plane

D. CA を削除してから、すべてを再インストールする

<details>
<summary>答えと解説</summary>

**答え: B**

最初に target version の互換性、release note、現在の health を確認してください。trust credential を保持し、各 resource の owner を通じて更新した後、新しい proxy を適用する対象の application Pod を再作成します。CLI extension の更新 manifest は `install` で生成します。`viz upgrade` は subcommand ではありません。サポートされる version skew を守り、resource を削除する前に prune の出力を確認してください。

</details>

### 8. `linkerd install --crds` 自体が行うことは何ですか?

A. CLI binary をインストールする

B. Linkerd CRD の manifest を生成する

C. すべての cluster resource をすぐに適用する

D. 既存の全 application Pod に proxy を inject する

<details>
<summary>答えと解説</summary>

**答え: B**

この command は manifest を出力します。実際のインストールは `kubectl apply`、または選択した deployment owner が行います。Gateway API の前提条件は既定の Linkerd CRD 出力とは別です。その後で control plane をインストールします。

</details>

### 9. edge-26.10.1 では、どの tracing 方法を使いますか?

A. すべての extension が CLI に同梱されているため、`linkerd jaeger install` を実行する

B. サポートされている collector/backend と proxy tracing を設定し、application context propagation を行う

C. Viz をインストールし、すべての分散 trace が保存されると仮定する

D. proxy がすべての application span を再構成できるため、trace header を無視する

<details>
<summary>答えと解説</summary>

**答え: B**

この CLI に jaeger subcommand はなく、公開されている linkerd-jaeger chart の履歴も、選択した release より古いものです。現行の tracing data path を使い、receiver/export の互換性を確認してください。metrics や topology graph は、収集済み分散 trace と同じものではありません。

</details>

### 10. 完全な削除計画で、最初に行うべきことは何ですか?

A. application に proxy が inject されたまま CRD を削除する

B. application の injection 設定と手動 proxy を除去し、workload を再作成して確認してから extension と control plane を削除する

C. すべての namespace をただちに削除する

D. 残存する proxy 付き workload を無視して強制 uninstall する

<details>
<summary>答えと解説</summary>

**答え: B**

まず workload owner を通じて injection 元をすべて除去し、application Pod を再作成して確認します。その後、各 owner を通じてインストール済み extension、control plane、CRD を削除してください。CRD を削除すると、その custom resource も削除されます。CNI の cleanup と namespace の ownership は別途確認してください。削除すると mesh による security/routing も失われます。

</details>

### 11. `linkerd check` で検証できないものはどれですか?

A. Kubernetes API access

B. control-plane certificate の有効性

C. application の business logic

D. control-plane Pod の health

<details>
<summary>答えと解説</summary>

**答え: C**

core health check は business outcome やすべての traffic/security path を検証するものではありません。`check --proxy` を使うと該当する data-plane check が加わり、インストール済み extension には個別の check があります。application test と実トラフィックの検証は分けて実施してください。

</details>

### 12. namespace への自動 proxy injection を要求する annotation はどれですか?

A. `linkerd.io/inject: enabled`

B. `linkerd.io/proxy: true`

C. `sidecar.linkerd.io/inject: true`

D. `linkerd/auto-inject: yes`

<details>
<summary>答えと解説</summary>

**答え: A**

この annotation は、条件を満たす新規 Pod に対する injection を要求します。Pod 単位の override、webhook の除外設定、platform 条件によって動作が変わる場合があるため、すべての新規 Pod に必ず inject される保証ではありません。既存 Pod は再作成が必要です。また、native sidecar が `initContainers` に表示される場合があります。

</details>
